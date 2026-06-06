// ========================================================
// DASHBOARD.JS - INTERACTIVIDAD ANIMADA DE ALTO NIVEL
// ========================================================

let charts = {};

function formatearNumero(valor) {
    if (valor === undefined || valor === null || isNaN(valor)) return "0";
    return Number(Math.floor(valor)).toLocaleString('es-MX');
}

/**
 * ANIMACIÓN FLUIDA MATEMÁTICA PARA LOS CONTADORES DE LAS TARJETAS
 */
function animarNumero(idElemento, valorFinal, esPorcentaje = false) {
    const elemento = document.getElementById(idElemento);
    if (!elemento) return;

    const valorLimpio = parseFloat(valorFinal) || 0;
    const valorInicial = parseFloat(elemento.innerText.replace(/[^0-9.]/g, '')) || 0;
    
    if (valorInicial === valorLimpio) {
        elemento.innerText = esPorcentaje ? `${valorLimpio.toFixed(2)} %` : formatearNumero(valorLimpio);
        return;
    }

    const duracion = 850; 
    const inicioTiempo = performance.now();

    function actualizarCuadro(tiempoActual) {
        const progreso = Math.min((tiempoActual - inicioTiempo) / duracion, 1);
        const cubicEaseOut = 1 - Math.pow(1 - progreso, 3);
        const valorActual = valorInicial + (valorLimpio - valorInicial) * cubicEaseOut;
        
        if (esPorcentaje) {
            elemento.innerText = `${valorActual.toFixed(2).replace('.', ',')} %`;
        } else {
            elemento.innerText = formatearNumero(valorActual);
        }

        if (progreso < 1) {
            requestAnimationFrame(actualizarCuadro);
        } else {
            elemento.innerText = esPorcentaje ? `${valorLimpio.toFixed(2).replace('.', ',')} %` : formatearNumero(valorLimpio);
        }
    }

    requestAnimationFrame(actualizarCuadro);
}

function traducirFiltro(valor) {
    if (!valor) return 'all';
    const v = valor.trim().toLowerCase();
    if (v === 'todos' || v === 'todas' || v === 'all') return 'all';
    if (v === 'twitter (x)') return 'Twitter';
    if (v === 'artículo') return 'Article';
    if (v === 'imagen') return 'Image';
    if (v === 'historia') return 'Story';
    if (v === 'carrusel') return 'Carousel';
    if (v === 'enlace') return 'Link';
    if (v === 'video') return 'Video';
    return valor;
}

async function actualizarDashboard() {
    const plataformaVisual = document.getElementById('filtro-plataforma')?.value || 'all';
    const contenidoVisual = document.getElementById('filtro-contenido')?.value || 'all';
    
    const plataforma = traducirFiltro(plataformaVisual);
    const contenido = traducirFiltro(contenidoVisual);
    
    const queryParams = `?plataforma=${plataforma}&contenido=${contenido}`;

    try {
        await actualizarKPIs(queryParams);
        await actualizarGraficoLineas(queryParams);
        await actualizarGraficoDoughnut(queryParams);
        await actualizarGraficoBarras(queryParams);
        await actualizarTablaCampanas(queryParams);
    } catch (error) {
        console.error("Error actualizando la interfaz corporativa:", error);
    }
}

// 1. KPIs
async function actualizarKPIs(queryParams) {
    const res = await fetch(`/api/kpis${queryParams}`);
    const data = await res.json();
    
    const tasa = data.tasa_engagement ?? data.TASA_ENGAGEMENT ?? 0;
    const interacciones = data.interacciones_totales ?? data.INTERACCIONES_TOTALES ?? 0;
    const alcance = data.alcance_total ?? data.ALCANCE_TOTAL ?? 0;
    const conversiones = data.conversiones ?? data.CONVERSIONES ?? 0;
    const impresiones = data.impresiones ?? data.IMPRESIONES ?? 0;

    animarNumero('kpi-tasa', tasa, true);
    animarNumero('kpi-interacciones', interacciones);
    animarNumero('kpi-alcance', alcance);
    animarNumero('kpi-conversiones', conversiones);
    animarNumero('kpi-impresiones', impresiones);
}

// 2. EVOLUCIÓN (LÍNEAS SUAVES TRANSICIONALES)
async function actualizarGraficoLineas(queryParams) {
    const canvas = document.getElementById('lineChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const res = await fetch(`/api/evolucion-engagement${queryParams}`);
    const data = await res.json();
    
    const labelsMeses = data.map(d => d.nombre_mes || d.NOMBRE_MES || "Mes");
    const valoresEngagement = data.map(d => {
        const val = d.engagement_rate !== undefined ? d.engagement_rate : d.ENGAGEMENT_RATE;
        return parseFloat(val) || 0;
    });

    if (charts.line) {
        charts.line.data.labels = labelsMeses;
        charts.line.data.datasets[0].data = valoresEngagement;
        charts.line.update();
    } else {
        charts.line = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labelsMeses,
                datasets: [{
                    label: 'Engagement Rate (%)',
                    data: valoresEngagement,
                    borderColor: '#6b001a',
                    backgroundColor: 'rgba(107, 0, 26, 0.05)',
                    fill: true,
                    tension: 0.35,
                    borderWidth: 3,
                    pointBackgroundColor: '#6b001a',
                    pointRadius: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { 
                    y: { beginAtZero: true, ticks: { callback: function(value) { return value + ' %'; } } },
                    x: { grid: { display: false } }
                }
            }
        });
    }
}

// 3. DISTRIBUCIÓN POR PLATAFORMA (DONA DE ALTA CALIDAD)
async function actualizarGraficoDoughnut(queryParams) {
    const canvas = document.getElementById('doughnutChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const res = await fetch(`/api/distribucion-plataformas${queryParams}`);
    const data = await res.json();
    
    const labelsPlat = data.map(d => d.nombre_plataforma || d.NOMBRE_PLATAFORMA);
    const valoresPlat = data.map(d => parseInt(d.total_interacciones || d.TOTAL_INTERACCIONES) || 0);

    if (charts.doughnut) {
        charts.doughnut.data.labels = labelsPlat;
        charts.doughnut.data.datasets[0].data = valoresPlat;
        charts.doughnut.update();
    } else {
        charts.doughnut = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labelsPlat,
                datasets: [{
                    data: valoresPlat,
                    backgroundColor: ['#3a0011', '#540015', '#6b001a', '#870f2b', '#a82343', '#c93c5d', '#555555'],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { 
                    legend: { position: 'right', labels: { boxWidth: 12, font: { size: 11 } } } 
                },
                cutout: '65%'
            }
        });
    }
}

// 4. INTERACCIONES POR TIPO DE CONTENIDO (BARRAS CORPORATIVAS)
async function actualizarGraficoBarras(queryParams) {
    const canvas = document.getElementById('barChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const res = await fetch(`/api/tipo-contenido${queryParams}`);
    const data = await res.json();
    
    const labelsCont = data.map(d => d.tipo_contenido || d.TIPO_CONTENIDO);
    const valoresCont = data.map(d => parseInt(d.total_interacciones || d.TOTAL_INTERACCIONES) || 0);

    if (charts.bar) {
        charts.bar.data.labels = labelsCont;
        charts.bar.data.datasets[0].data = valoresCont;
        charts.bar.update();
    } else {
        charts.bar = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labelsCont,
                datasets: [{
                    data: valoresCont,
                    backgroundColor: '#6b001a',
                    borderRadius: 4,
                    barThickness: 24
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { 
                    y: { beginAtZero: true },
                    x: { grid: { display: false } }
                }
            }
        });
    }
}

// 5. RENDIMIENTO POR CAMPAÑA (TABLA INYECTADA)
async function actualizarTablaCampanas(queryParams) {
    const tbody = document.querySelector('#campaignTable tbody');
    if (!tbody) return;
    tbody.innerHTML = ''; 

    const res = await fetch(`/api/campanas${queryParams}`);
    const data = await res.json();
    
    data.forEach(camp => {
        const nombre = camp.nombre_campana || camp.NOMBRE_CAMPANA;
        const interacciones = camp.interacciones_totales || camp.INTERACCIONES_TOTALES;
        const alcance = camp.alcance_total || camp.ALCANCE_TOTAL;
        const rate = camp.engagement_rate || camp.ENGAGEMENT_RATE;

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${nombre}</strong></td>
            <td>${formatearNumero(interacciones)}</td>
            <td>${formatearNumero(alcance)}</td>
            <td><span style="color: var(--primary-color); font-weight:700;">${rate ?? 0} %</span></td>
        `;
        tbody.appendChild(tr);
    });
}

// CAMBIO 5: Lógica de visibilidad de secciones
function mostrarSeccion(seccion) {
    const kpis = document.getElementById('seccion-kpis');
    const evolucion = document.getElementById('seccion-evolucion');
    const contenido = document.getElementById('seccion-contenido');

    // Resetear visibilidad por defecto
    kpis.style.display = 'grid';
    evolucion.style.display = 'grid';
    contenido.style.display = 'grid';

    switch(seccion) {
        case 'contenido':
            kpis.style.display = 'none';
            evolucion.style.display = 'none';
            break;
        case 'campanas':
            kpis.style.display = 'none';
            evolucion.style.display = 'none';
            break;
        case 'audiencia':
            evolucion.style.display = 'none';
            contenido.style.display = 'none';
            break;
        case 'tendencias':
            kpis.style.display = 'none';
            contenido.style.display = 'none';
            break;
        case 'resumen':
        default:
            break;
    }
}

// CAMBIO 6: Registro inicial con manejo de navegación
document.addEventListener('DOMContentLoaded', () => {
    actualizarDashboard();

    document.getElementById('filtro-plataforma')
        ?.addEventListener('change', actualizarDashboard);

    document.getElementById('filtro-contenido')
        ?.addEventListener('change', actualizarDashboard);

    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();

            document.querySelectorAll('.nav-item').forEach(btn => {
                btn.classList.remove('active');
            });

            this.classList.add('active');

            const seccion = this.dataset.section;
            mostrarSeccion(seccion);
        });
    });
});