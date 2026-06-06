# =========================================================
# PROYECTO BI - ETL + POSTGRESQL
# =========================================================
# Autor: Equipo Business Intelligence
# Descripción: Proceso ETL completo desde CSV hacia PostgreSQL
# =========================================================

# ---------------------------------------------------------
# LIBRERÍAS
# ---------------------------------------------------------
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import os
import sys

# ---------------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------------
CONFIG = {
    "usuario": "postgres",
    "password": "renata",
    "host": "localhost",
    "puerto": "5432",
    "database": "marketing_bi",
    # AL ESTAR EN LA MISMA CARPETA, SOLO NECESITAMOS EL NOMBRE DEL ARCHIVO:
    "ruta_csv": "social_media_engagement_dataset (2).csv" 
}

# ---------------------------------------------------------
# FUNCIONES AUXILIARES
# ---------------------------------------------------------

def crear_motor(db_name=None):
    """Crea el motor de conexión SQLAlchemy para PostgreSQL."""
    base = CONFIG["database"] if db_name is None else db_name
    url = (
        f"postgresql+psycopg2://{CONFIG['usuario']}:{CONFIG['password']}"
        f"@{CONFIG['host']}:{CONFIG['puerto']}/{base}"
    )
    return create_engine(url)


def verificar_conexion(engine):
    """Verifica que la conexión a PostgreSQL sea exitosa."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Conexión exitosa con PostgreSQL")
        return True
    except SQLAlchemyError as e:
        print(f"❌ Error de conexión: {e}")
        return False


def crear_base_datos_si_no_existe():
    """Crea la base de datos 'marketing_bi' si no existe."""
    engine_temp = create_engine(
        f"postgresql+psycopg2://{CONFIG['usuario']}:{CONFIG['password']}"
        f"@{CONFIG['host']}:{CONFIG['puerto']}/postgres"
    )
    try:
        with engine_temp.connect() as conn:
            conn.execute(text("COMMIT"))
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db"),
                {"db": CONFIG["database"]}
            )
            if not result.fetchone():
                conn.execute(text("COMMIT"))
                conn.execute(text(f'CREATE DATABASE "{CONFIG["database"]}"'))
                print(f"✅ Base de datos '{CONFIG['database']}' creada")
            else:
                print(f"ℹ️  Base de datos '{CONFIG['database']}' ya existe")
    except SQLAlchemyError as e:
        print(f"❌ Error al verificar/crear base de datos: {e}")
        sys.exit(1)


def cargar_dataset(ruta):
    """Carga el dataset CSV y valida su existencia."""
    if not os.path.exists(ruta):
        print(f"❌ Archivo no encontrado: Asegúrate de que '{ruta}' esté en la misma carpeta que este script de Python.")
        sys.exit(1)
    
    df = pd.read_csv(ruta)
    print(f"✅ Dataset cargado: {df.shape[0]} filas x {df.shape[1]} columnas")
    return df


def limpiar_datos(df):
    """Elimina duplicados, nulos y convierte fechas."""
    filas_inicial = len(df)
    
    df = df.drop_duplicates()
    df = df.dropna()
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df = df.dropna(subset=["Timestamp"])
    
    filas_final = len(df)
    print(f"✅ Limpieza completada: {filas_inicial} → {filas_final} filas "
          f"({filas_inicial - filas_final} eliminadas)")
    return df


def transformar_datos(df):
    """Extrae componentes de fecha y calcula métricas derivadas."""
    # Componentes de fecha
    df["Dia"] = df["Timestamp"].dt.day
    df["Mes"] = df["Timestamp"].dt.month
    df["Anio"] = df["Timestamp"].dt.year
    df["Trimestre"] = df["Timestamp"].dt.quarter
    df["Nombre_Mes"] = df["Timestamp"].dt.month_name()
    
    # Métricas derivadas
    df["Interacciones_Totales"] = (
        df["Likes"] + df["Comments"] + df["Shares"] + df["Saves"]
    )
    
    df["Engagement_Rate"] = (
        (df["Interacciones_Totales"] / df["Views"]) * 100
    ).replace([np.inf, -np.inf], 0).round(4)
    
    print("✅ Transformación completada: fechas y métricas calculadas")
    return df


def crear_dimensiones(df):
    """Crea las 4 tablas dimensionales con IDs únicos."""
    dimensiones = {}
    
    # DIM_FECHA
    dim_fecha = df[["Timestamp", "Dia", "Mes", "Anio", "Trimestre", "Nombre_Mes"]].copy()
    dim_fecha = dim_fecha.drop_duplicates().reset_index(drop=True)
    dim_fecha["id_fecha"] = dim_fecha.index + 1
    dimensiones["DIM_FECHA"] = dim_fecha
    
    # DIM_PLATAFORMA
    dim_plataforma = df[["Platform"]].drop_duplicates().reset_index(drop=True)
    dim_plataforma["id_plataforma"] = dim_plataforma.index + 1
    dimensiones["DIM_PLATAFORMA"] = dim_plataforma
    
    # DIM_CONTENIDO
    dim_contenido = df[["Content_Type", "Category", "Hashtag_Count", 
                        "Content_Length", "Has_Media"]].copy()
    dim_contenido = dim_contenido.drop_duplicates().reset_index(drop=True)
    dim_contenido["id_contenido"] = dim_contenido.index + 1
    dimensiones["DIM_CONTENIDO"] = dim_contenido
    
    # DIM_USUARIO
    dim_usuario = df[["Influencer_Tier", "Is_Verified", "Follower_Count"]].copy()
    dim_usuario = dim_usuario.drop_duplicates().reset_index(drop=True)
    dim_usuario["id_usuario"] = dim_usuario.index + 1
    dimensiones["DIM_USUARIO"] = dim_usuario
    
    for nombre, dim in dimensiones.items():
        print(f"   📊 {nombre}: {len(dim)} registros")
    
    print("✅ Dimensiones creadas correctamente")
    return dimensiones


def crear_fact_table(df, dimensiones):
    """Crea la tabla de hechos uniendo con las dimensiones."""
    fact = df.copy()
    
    # Merge con cada dimensión
    fact = fact.merge(dimensiones["DIM_FECHA"], on="Timestamp", how="left")
    fact = fact.merge(dimensiones["DIM_PLATAFORMA"], on="Platform", how="left")
    fact = fact.merge(
        dimensiones["DIM_CONTENIDO"],
        on=["Content_Type", "Category", "Hashtag_Count", "Content_Length", "Has_Media"],
        how="left"
    )
    fact = fact.merge(
        dimensiones["DIM_USUARIO"],
        on=["Influencer_Tier", "Is_Verified", "Follower_Count"],
        how="left"
    )
    
    # Seleccionar columnas finales
    columnas_fact = [
        "Post_ID", "id_fecha", "id_plataforma", "id_contenido", "id_usuario",
        "Likes", "Comments", "Shares", "Views", "Saves",
        "Interacciones_Totales", "Engagement_Rate"
    ]
    
    # Filtrar solo columnas que existan (por seguridad)
    columnas_existentes = [c for c in columnas_fact if c in fact.columns]
    fact_engagement = fact[columnas_existentes].copy()
    
    print(f"✅ Tabla de hechos creada: {fact_engagement.shape[0]} filas x "
          f"{fact_engagement.shape[1]} columnas")
    return fact_engagement


def exportar_a_postgres(engine, dimensiones, fact_engagement):
    """Exporta todas las tablas a PostgreSQL."""
    print("\n📤 Exportando tablas a PostgreSQL...")
    
    # Exportar dimensiones primero
    for nombre, df in dimensiones.items():
        df.to_sql(nombre, engine, if_exists="replace", index=False)
        print(f"   ✅ {nombre} exportada")
    
    # Exportar tabla de hechos
    fact_engagement.to_sql("FACT_ENGAGEMENT", engine, if_exists="replace", index=False)
    print("   ✅ FACT_ENGAGEMENT exportada")
    
    print("✅ Todas las tablas exportadas correctamente")


def verificar_carga(engine):
    """Verifica la integridad de los datos cargados."""
    print("\n🔍 Verificando integridad de datos...")
    
    consulta = """
        SELECT 
            table_name,
            (xpath('/row/cnt/text()', xml_count))[1]::text::int AS total_registros
        FROM (
            SELECT 
                table_name,
                query_to_xml(format('SELECT COUNT(*) AS cnt FROM %I.%I', 
                                    table_schema, table_name), false, true, '') AS xml_count
            FROM information_schema.tables
            WHERE table_schema = 'public' 
            AND table_name IN ('DIM_FECHA', 'DIM_PLATAFORMA', 'DIM_CONTENIDO', 
                              'DIM_USUARIO', 'FACT_ENGAGEMENT')
        ) t
        ORDER BY table_name;
    """
    
    try:
        with engine.connect() as conn:
            resultado = pd.read_sql(consulta, conn)
            print("\n📋 Resumen de tablas en PostgreSQL:")
            print(resultado.to_string(index=False))
            print("\n✅ Verificación completada")
    except SQLAlchemyError as e:
        print(f"⚠️  No se pudo verificar: {e}")


# ---------------------------------------------------------
# FUNCIÓN PRINCIPAL
# ---------------------------------------------------------

def main():
    """Ejecuta el proceso ETL completo."""
    print("=" * 60)
    print("🚀 INICIANDO PROCESO ETL - POSTGRESQL")
    print("=" * 60)
    
    # 1. Crear base de datos si no existe
    print("\n[1/7] Preparando base de datos...")
    crear_base_datos_si_no_existe()
    
    # 2. Crear motor de conexión
    print("\n[2/7] Conectando a PostgreSQL...")
    engine = crear_motor()
    if not verificar_conexion(engine):
        sys.exit(1)
    
    # 3. Cargar dataset
    print("\n[3/7] Cargando dataset...")
    df = cargar_dataset(CONFIG["ruta_csv"])
    
    # 4. Limpiar datos
    print("\n[4/7] Limpiando datos...")
    df = limpiar_datos(df)
    
    # 5. Transformar datos
    print("\n[5/7] Transformando datos...")
    df = transformar_datos(df)
    
    # 6. Crear dimensiones y tabla de hechos
    print("\n[6/7] Construyendo modelo dimensional...")
    dimensiones = crear_dimensiones(df)
    fact_engagement = crear_fact_table(df, dimensiones)
    
    # 7. Exportar a PostgreSQL
    print("\n[7/7] Exportando a PostgreSQL...")
    exportar_a_postgres(engine, dimensiones, fact_engagement)
    
    # Verificación final
    verificar_carga(engine)
    
    print("\n" + "=" * 60)
    print("🎉 PROCESO ETL COMPLETADO EXITOSAMENTE")
    print("=" * 60)


# ---------------------------------------------------------
# EJECUCIÓN
# ---------------------------------------------------------
if __name__ == "__main__":
    main()