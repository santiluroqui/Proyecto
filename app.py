from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import OperationalError
import traceback

app = Flask(__name__)
CORS(app)

import os

DB_CONFIG = {
    'host': os.environ.get('DB_HOST'),
    'database': os.environ.get('DB_NAME'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'port': os.environ.get('DB_PORT'),
    'client_encoding': 'utf8'
}

def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except OperationalError as e:
        print(f"❌ Error de conexión: {e}")
        raise

@app.route('/')
def index():
    return render_template('index.html')

# ========================================================
# 1. API DE KPIs
# ========================================================
@app.route('/api/kpis')
def get_kpis():
    conn = None
    try:
        plataforma = request.args.get('plataforma', 'all')
        contenido = request.args.get('contenido', 'all')
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = '''
            SELECT 
                ROUND(AVG(fe."Engagement_Rate")::numeric, 2) as tasa_engagement,
                SUM(fe."Likes" + fe."Comments" + fe."Shares" + fe."Saves") as interacciones_totales,
                SUM(fe."Views") as alcance_total,
                SUM(fe."Saves") as conversiones,
                SUM(fe."Views" * 2) as impresiones
            FROM "FACT_ENGAGEMENT" fe
            JOIN "DIM_PLATAFORMA" dp ON fe."id_plataforma" = dp."id_plataforma"
            JOIN "DIM_CONTENIDO" dc ON fe."id_contenido" = dc."id_contenido"
        '''
        
        conditions = []
        params = {}
        
        if plataforma != 'all':
            conditions.append('dp."Platform" = %(plataforma)s')
            params['plataforma'] = plataforma
            
        if contenido != 'all':
            conditions.append('dc."Content_Type" = %(contenido)s')
            params['contenido'] = contenido
            
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
            
        cursor.execute(query, params)
        resultado = cursor.fetchone()
        
        if not resultado or resultado['interacciones_totales'] is None:
            resultado = {
                'tasa_engagement': 0,
                'interacciones_totales': 0,
                'alcance_total': 0,
                'conversiones': 0,
                'impresiones': 0
            }
            
        cursor.close()
        conn.close()
        return jsonify(resultado)
    except Exception as e:
        print(f"❌ [KPIs] ERROR: {e}")
        return jsonify({'error': str(e)}), 500

# ========================================================
# 2. API DE EVOLUCIÓN
# ========================================================
@app.route('/api/evolucion-engagement')
def get_evolucion():
    conn = None
    try:
        plataforma = request.args.get('plataforma', 'all')
        contenido = request.args.get('contenido', 'all')

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = '''
            SELECT
                df."Mes" as num_mes,
                df."Nombre_Mes" as nombre_mes,
                ROUND(AVG(fe."Engagement_Rate")::numeric, 2) as engagement_rate
            FROM "FACT_ENGAGEMENT" fe

            JOIN "DIM_FECHA" df
                ON fe."id_fecha" = df."id_fecha"

            JOIN "DIM_PLATAFORMA" dp
                ON fe."id_plataforma" = dp."id_plataforma"

            JOIN "DIM_CONTENIDO" dc
                ON fe."id_contenido" = dc."id_contenido"
        '''

        conditions = []
        params = {}

        if plataforma != 'all':
            conditions.append('dp."Platform" = %(plataforma)s')
            params['plataforma'] = plataforma

        if contenido != 'all':
            conditions.append('dc."Content_Type" = %(contenido)s')
            params['contenido'] = contenido

        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

        query += '''
            GROUP BY
                df."Mes",
                df."Nombre_Mes"
            ORDER BY
                df."Mes"
        '''

        cursor.execute(query, params)
        resultados = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(resultados)

    except Exception as e:
        print(f"❌ [Evolución] ERROR: {e}")
        traceback.print_exc()

        if conn:
            conn.close()

        return jsonify([])

# ========================================================
# 3. API DE DISTRIBUCIÓN (GRÁFICO DE DONA)
# ========================================================
@app.route('/api/distribucion-plataformas')
def get_distribucion():
    conn = None
    try:
        plataforma = request.args.get('plataforma', 'all')
        contenido = request.args.get('contenido', 'all')
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = '''
            SELECT 
                dp."Platform" as nombre_plataforma,
                SUM(fe."Likes" + fe."Comments" + fe."Shares" + fe."Saves") as total_interacciones
            FROM "FACT_ENGAGEMENT" fe
            JOIN "DIM_PLATAFORMA" dp ON fe."id_plataforma" = dp."id_plataforma"
            JOIN "DIM_CONTENIDO" dc ON fe."id_contenido" = dc."id_contenido"
        '''
        
        conditions = []
        params = {}
        
        if plataforma != 'all':
            conditions.append('dp."Platform" = %(plataforma)s')
            params['plataforma'] = plataforma
        if contenido != 'all':
            conditions.append('dc."Content_Type" = %(contenido)s')
            params['contenido'] = contenido
            
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
            
        query += ' GROUP BY dp."Platform" ORDER BY total_interacciones DESC'
        
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return jsonify(resultados)
    except Exception as e:
        print(f"❌ [Distribución] ERROR: {e}")
        return jsonify({'error': str(e)}), 500

# ========================================================
# 4. API DE RENDIMIENTO (GRÁFICO DE BARRAS)
# ========================================================
@app.route('/api/tipo-contenido')
def get_tipo_contenido():
    conn = None
    try:
        plataforma = request.args.get('plataforma', 'all')
        contenido = request.args.get('contenido', 'all')
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = '''
            SELECT 
                dc."Content_Type" as tipo_contenido,
                SUM(fe."Likes" + fe."Comments" + fe."Shares" + fe."Saves") as total_interacciones
            FROM "FACT_ENGAGEMENT" fe
            JOIN "DIM_PLATAFORMA" dp ON fe."id_plataforma" = dp."id_plataforma"
            JOIN "DIM_CONTENIDO" dc ON fe."id_contenido" = dc."id_contenido"
        '''
        
        conditions = []
        params = {}
        
        if plataforma != 'all':
            conditions.append('dp."Platform" = %(plataforma)s')
            params['plataforma'] = plataforma
        if contenido != 'all':
            conditions.append('dc."Content_Type" = %(contenido)s')
            params['contenido'] = contenido
            
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
            
        query += ' GROUP BY dc."Content_Type" ORDER BY total_interacciones DESC'
        
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return jsonify(resultados)
    except Exception as e:
        print(f"❌ [Tipo Contenido] ERROR: {e}")
        return jsonify({'error': str(e)}), 500

# ========================================================
# 5. API DE CAMPAÑAS (TABLA DETALLADA)
# ========================================================
@app.route('/api/campanas')
def get_campanas():
    conn = None
    try:
        plataforma = request.args.get('plataforma', 'all')
        contenido = request.args.get('contenido', 'all')
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = '''
            SELECT 
                dc."Category" as nombre_campana,
                SUM(fe."Likes" + fe."Comments" + fe."Shares" + fe."Saves") as interacciones_totales,
                SUM(fe."Views") as alcance_total,
                ROUND(AVG(fe."Engagement_Rate")::numeric, 2) as engagement_rate
            FROM "FACT_ENGAGEMENT" fe
            JOIN "DIM_PLATAFORMA" dp ON fe."id_plataforma" = dp."id_plataforma"
            JOIN "DIM_CONTENIDO" dc ON fe."id_contenido" = dc."id_contenido"
        '''
        
        conditions = []
        params = {}
        
        if plataforma != 'all':
            conditions.append('dp."Platform" = %(plataforma)s')
            params['plataforma'] = plataforma
        if contenido != 'all':
            conditions.append('dc."Content_Type" = %(contenido)s')
            params['contenido'] = contenido
            
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
            
        query += ' GROUP BY dc."Category" ORDER BY interacciones_totales DESC LIMIT 10'
        
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return jsonify(resultados)
    except Exception as e:
        print(f"❌ [Campañas] ERROR: {e}")
        return jsonify({'error': str(e)}), 500

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )