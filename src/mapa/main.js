import './style.css';
import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import VectorTileLayer from 'ol/layer/VectorTile';
import VectorTileSource from 'ol/source/VectorTile';
import MVT from 'ol/format/MVT';
import GeoJSON from 'ol/format/GeoJSON';
import XYZ from 'ol/source/XYZ';
import { Style, Fill, Stroke, Circle } from 'ol/style';

// Servers
const API_BASE = 'http://localhost:8000';
var vectorServer = 'http://localhost:7800/';
var featureServer = 'http://localhost:9000/';

var vectorUrl = vectorServer + 'public.inmuebles/{z}/{x}/{y}.pbf';
var incendioUrl = vectorServer + 'public.riesgo_incendio/{z}/{x}/{y}.pbf';
var geojsonUrl = featureServer + 'collections/public.detalle_calculo_incendio/items?limit=500';

// ===== GLOBAL STATE =====
let currentRole = 'viewer';
let riesgoChart = null;
let modoVisualizacionActual = {
  tipo: 'general',
  id: null,
  nombre: null,
  minimo: 0,
  maximo: 0
};

// ===== JWT UTILITIES =====
function decodeToken(token) {
  try {
    const payload = token.split('.')[1];
    return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
  } catch {
    return null;
  }
}

function isTokenExpired(token) {
  const payload = decodeToken(token);
  if (!payload || !payload.exp) return true;
  return Date.now() / 1000 > payload.exp;
}

function getToken() {
  return localStorage.getItem('access_token');
}

function clearAuth() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

async function refreshAccessToken() {
  const refresh = localStorage.getItem('refresh_token');
  if (!refresh) return false;
  try {
    const res = await fetch(`${API_BASE}/api/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh })
    });
    if (!res.ok) return false;
    const data = await res.json();
    localStorage.setItem('access_token', data.access);
    return true;
  } catch {
    return false;
  }
}

async function apiFetch(url, options = {}, retry = true) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(url, { ...options, headers });

  if (res.status === 401 && retry) {
    const refreshed = await refreshAccessToken();
    if (refreshed) return apiFetch(url, options, false);
    clearAuth();
    showLoginModal();
    throw new Error('Session expired');
  }
  return res;
}

// ===== COLOR HELPERS =====
function getColorByValue(valor, tipo = 'general') {
  if (tipo === 'general') {
    if (valor >= 3.26) return '#ff0000';
    if (valor >= 2.51) return '#ff6600';
    if (valor >= 1.76) return '#ffff00';
    return '#00aa00';
  } else {
    if (valor >= 1.0) return '#ff0000';
    if (valor >= 0.5) return '#ff6600';
    if (valor >= 0.25) return '#ffff00';
    return '#00aa00';
  }
}

function getRiesgoClass(valor, tipo) {
  if (tipo === 'general') {
    if (valor >= 3.26) return 'riesgo-altisimo';
    if (valor >= 2.51) return 'riesgo-alto';
    if (valor >= 1.76) return 'riesgo-medio';
    return 'riesgo-bajo';
  } else {
    if (valor >= 1.0) return 'riesgo-altisimo';
    if (valor >= 0.5) return 'riesgo-alto';
    if (valor >= 0.25) return 'riesgo-medio';
    return 'riesgo-bajo';
  }
}

// ===== MAP LAYERS =====

const baseLayer = new TileLayer({
  source: new XYZ({
    url: 'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png'
  })
});

var incendioLayer = new VectorTileLayer({
  source: new VectorTileSource({
    format: new MVT(),
    url: incendioUrl
  }),
  style: function (feature) {
    const valor = feature.get('riesgo') || 0;
    const color = getColorByValue(valor, 'general');
    return new Style({
      fill: new Fill({ color: color + '99' }),
      stroke: new Stroke({ color: '#000000bf', width: 1 })
    });
  },
  visible: true
});

// GeoJSON source with custom loader (defers load until user is authenticated)
const geojsonSource = new VectorSource({
  format: new GeoJSON(),
  loader: function (extent, resolution, projection, success, failure) {
    const self = this;
    fetch(geojsonUrl)
      .then(r => { if (!r.ok) throw new Error('GeoJSON load failed'); return r.json(); })
      .then(data => {
        const features = new GeoJSON().readFeatures(data, { featureProjection: projection });
        self.addFeatures(features);
        success(features);
      })
      .catch(() => failure());
  }
});

var geojsonLayer = new VectorLayer({
  source: geojsonSource
});

var indicadorLayer = new VectorLayer({
  source: geojsonSource,
  visible: false,
  style: function () { return new Style({}); }
});

var selectionLayer = new VectorLayer({
  source: new VectorSource(),
  style: function () {
    return new Style({
      fill: new Fill({ color: 'rgba(255, 255, 0, 0.45)' }),
      stroke: new Stroke({ color: '#ffaa00', width: 4 }),
      image: new Circle({
        radius: 8,
        fill: new Fill({ color: '#ffaa00' }),
        stroke: new Stroke({ color: '#ffffff', width: 2 })
      })
    });
  }
});

const map = new Map({
  target: 'map',
  view: new View({
    center: [-7973693.872453815, -3900580.7807773366],
    zoom: 17
  }),
  layers: [baseLayer, geojsonLayer, incendioLayer, indicadorLayer, selectionLayer]
});

// ===== AUTH UI =====

function showLoginModal() {
  document.getElementById('login-modal').style.display = 'flex';
  document.getElementById('user-bar').style.display = 'none';
  document.getElementById('login-error').style.display = 'none';
  document.getElementById('login-username').value = '';
  document.getElementById('login-password').value = '';
}

function hideLoginModal() {
  document.getElementById('login-modal').style.display = 'none';
}

function updateUserBar(username, role) {
  const bar = document.getElementById('user-bar');
  bar.style.display = 'flex';
  document.getElementById('user-info').innerHTML =
    `<strong>${username}</strong><span class="role-badge ${role}">${role === 'editor' ? 'Editor' : 'Viewer'}</span>`;


  // Offset map so it isn't hidden behind the user bar
  document.getElementById('map').style.top = '40px';
  document.getElementById('map').style.height = 'calc(100% - 40px)';
}

window.logout = function () {
  clearAuth();
  currentRole = 'viewer';
  cerrarPanel();
  cerrarPanelClases();
  showLoginModal();
  // Clear loaded GeoJSON so it reloads on next login
  geojsonSource.clear();
};

// ===== LOGIN HANDLER =====

document.getElementById('login-form').addEventListener('submit', async function (e) {
  e.preventDefault();
  const btn = document.getElementById('login-btn');
  const errorDiv = document.getElementById('login-error');
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;

  btn.disabled = true;
  btn.textContent = 'Ingresando...';
  errorDiv.style.display = 'none';

  try {
    const res = await fetch(`${API_BASE}/api/token/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    if (res.ok) {
      const data = await res.json();
      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
      const payload = decodeToken(data.access);
      currentRole = payload?.role || 'viewer';
      hideLoginModal();
      updateUserBar(payload?.username || username, currentRole);
      // Trigger GeoJSON load now that user is authenticated
      geojsonSource.refresh();
    } else {
      const err = await res.json().catch(() => ({}));
      errorDiv.textContent = err.detail || 'Usuario o contraseña incorrectos.';
      errorDiv.style.display = 'block';
    }
  } catch {
    errorDiv.textContent = 'No se pudo conectar al servidor.';
    errorDiv.style.display = 'block';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Iniciar Sesión';
  }
});

// ===== APP INIT =====

function initApp() {
  const token = getToken();
  if (token && !isTokenExpired(token)) {
    const payload = decodeToken(token);
    currentRole = payload?.role || 'viewer';
    hideLoginModal();
    updateUserBar(payload?.username || 'Usuario', currentRole);
    geojsonSource.refresh();
  } else {
    clearAuth();
    showLoginModal();
  }
}

// ===== PANEL TOGGLES =====

window.toggleStatsPanel = function () {
  const panel = document.getElementById('stats-panel');
  panel.classList.toggle('visible');
  if (panel.classList.contains('visible')) cargarIndicadores();
};

window.toggleChartPanel = function () {
  const panel = document.getElementById('chart-panel');
  panel.classList.toggle('visible');
  if (panel.classList.contains('visible')) {
    if (modoVisualizacionActual.tipo === 'general') {
      actualizarEstadisticas();
    } else if (modoVisualizacionActual.tipo === 'indicador') {
      const stats = calcularEstadisticasIndicador(modoVisualizacionActual.nombre);
      actualizarGrafico(stats, `Indicador: ${modoVisualizacionActual.nombre}`);
      actualizarResumenEstadisticas(stats);
    } else if (modoVisualizacionActual.tipo === 'subindicador') {
      const stats = calcularEstadisticasSubindicador(modoVisualizacionActual.nombre);
      actualizarGrafico(stats, `Subindicador: ${modoVisualizacionActual.nombre}`);
      actualizarResumenEstadisticas(stats);
    }
  }
};

window.volverVistaGeneral = function () {
  modoVisualizacionActual = { tipo: 'general', id: null, nombre: null, minimo: 0, maximo: 0 };
  incendioLayer.setVisible(true);
  indicadorLayer.setVisible(false);
  document.querySelectorAll('.indicador-header, .subindicador-item').forEach(el => el.classList.remove('active'));
  document.getElementById('btnVistaGeneral').style.display = 'none';
  if (document.getElementById('chart-panel').classList.contains('visible')) actualizarEstadisticas();
};

// ===== INDICATORS PANEL =====

function cargarIndicadores() {
  const container = document.getElementById('indicadores-container');
  if (!container) return;
  const features = geojsonLayer.getSource().getFeatures();
  if (features.length === 0) {
    container.innerHTML = '<p style="text-align:center;color:#666;">No hay datos disponibles</p>';
    return;
  }
  const indicadoresObj = {};
  features.forEach(feature => {
    const props = feature.getProperties();
    const detalle = props.detalle_riesgo || { indicadores: [] };
    if (!detalle.indicadores || !Array.isArray(detalle.indicadores)) return;
    detalle.indicadores.forEach(indicador => {
      const nombre = indicador.indicador_nombre;
      if (!nombre) return;
      if (!indicadoresObj[nombre]) indicadoresObj[nombre] = { nombre, valores: [], subindicadores: {} };
      indicadoresObj[nombre].valores.push(parseFloat(indicador.riesgo_indicador) || 0);
      if (indicador.sub_indicadores && Array.isArray(indicador.sub_indicadores)) {
        indicador.sub_indicadores.forEach(sub => {
          const subNombre = sub.sub_indicador_nombre;
          if (!subNombre) return;
          if (!indicadoresObj[nombre].subindicadores[subNombre])
            indicadoresObj[nombre].subindicadores[subNombre] = { nombre: subNombre, valores: [] };
          indicadoresObj[nombre].subindicadores[subNombre].valores.push(parseFloat(sub.riesgo_subindicador) || 0);
        });
      }
    });
  });
  renderizarIndicadores(container, indicadoresObj);
}

function renderizarIndicadores(container, indicadoresObj) {
  if (Object.keys(indicadoresObj).length === 0) {
    container.innerHTML = '<p style="text-align:center;color:#666;">No se encontraron indicadores</p>';
    return;
  }
  let html = '';
  Object.values(indicadoresObj).forEach(data => {
    const indicadorId = data.nombre.replace(/[^a-zA-Z0-9]/g, '-');
    html += `
      <div class="indicador-item">
        <div class="indicador-header" onclick="toggleIndicador(event, this)" data-indicador="${data.nombre}">
          <span class="indicador-nombre">${data.nombre}</span>
          <span><span class="indicador-riesgo"></span><span class="indicador-toggle">▼</span></span>
        </div>
        <div class="subindicadores-container" id="sub-${indicadorId}">
    `;
    const subindicadoresArray = Object.values(data.subindicadores);
    if (subindicadoresArray.length > 0) {
      subindicadoresArray.forEach(subData => {
        const subPromedio = subData.valores.length > 0
          ? subData.valores.reduce((a, b) => a + b, 0) / subData.valores.length : 0;
        html += `
          <div class="subindicador-item"
               onclick="seleccionarSubindicador(event, '${subData.nombre}', ${subPromedio})"
               data-subindicador="${subData.nombre}">
            <span class="subindicador-nombre">${subData.nombre}</span>
            <span class="subindicador-riesgo"></span>
          </div>`;
      });
    } else {
      html += `<div style="padding:10px;color:#999;text-align:center;">Sin subindicadores</div>`;
    }
    html += `</div></div>`;
  });
  container.innerHTML = html;
}

window.toggleIndicador = function (event, header) {
  event.stopPropagation();
  const container = header.nextElementSibling;
  const toggle = header.querySelector('.indicador-toggle');
  container.classList.toggle('visible');
  toggle.textContent = container.classList.contains('visible') ? '▲' : '▼';
  seleccionarIndicador(event, header.dataset.indicador);
};

function calcularEstadisticasIndicador(nombreIndicador) {
  const features = geojsonLayer.getSource().getFeatures();
  const stats = { altisimo: 0, alto: 0, medio: 0, bajo: 0 };
  features.forEach(feature => {
    const props = feature.getProperties();
    const detalle = props.detalle_riesgo || { indicadores: [] };
    const indicador = detalle.indicadores?.find(ind => ind.indicador_nombre === nombreIndicador);
    if (indicador) {
      const valor = parseFloat(indicador.riesgo_indicador) || 0;
      if (valor >= 1.0) stats.altisimo++;
      else if (valor >= 0.5) stats.alto++;
      else if (valor >= 0.25) stats.medio++;
      else stats.bajo++;
    }
  });
  return stats;
}

function calcularEstadisticasSubindicador(nombreSubindicador) {
  const features = geojsonLayer.getSource().getFeatures();
  const stats = { altisimo: 0, alto: 0, medio: 0, bajo: 0 };
  features.forEach(feature => {
    const props = feature.getProperties();
    const detalle = props.detalle_riesgo || { indicadores: [] };
    for (const ind of detalle.indicadores || []) {
      const sub = ind.sub_indicadores?.find(s => s.sub_indicador_nombre === nombreSubindicador);
      if (sub) {
        const valor = parseFloat(sub.riesgo_subindicador) || 0;
        if (valor >= 1.0) stats.altisimo++;
        else if (valor >= 0.5) stats.alto++;
        else if (valor >= 0.25) stats.medio++;
        else stats.bajo++;
        break;
      }
    }
  });
  return stats;
}

window.seleccionarIndicador = function (event, nombreIndicador) {
  if (event) event.stopPropagation();
  modoVisualizacionActual = { tipo: 'indicador', id: nombreIndicador, nombre: nombreIndicador };
  incendioLayer.setVisible(false);
  indicadorLayer.setVisible(true);
  indicadorLayer.setStyle(function (feature) {
    const props = feature.getProperties();
    const detalle = props.detalle_riesgo || { indicadores: [] };
    const indicador = detalle.indicadores?.find(ind => ind.indicador_nombre === nombreIndicador);
    const valor = indicador?.riesgo_indicador || 0;
    const color = getColorByValue(valor, 'indicador');
    return new Style({
      fill: new Fill({ color: color + '99' }),
      stroke: new Stroke({ color: '#000000bf', width: 1 })
    });
  });
  document.querySelectorAll('.indicador-header').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.subindicador-item').forEach(el => el.classList.remove('active'));
  for (let header of document.querySelectorAll('.indicador-header')) {
    if (header.dataset.indicador === nombreIndicador) { header.classList.add('active'); break; }
  }
  document.getElementById('btnVistaGeneral').style.display = 'block';
  if (document.getElementById('chart-panel').classList.contains('visible')) {
    const stats = calcularEstadisticasIndicador(nombreIndicador);
    actualizarGrafico(stats, `Indicador: ${nombreIndicador}`);
    actualizarResumenEstadisticas(stats);
  }
  indicadorLayer.changed();
};

window.seleccionarSubindicador = function (event, nombreSubindicador, promedio) {
  if (event) event.stopPropagation();
  modoVisualizacionActual = { tipo: 'subindicador', id: nombreSubindicador, nombre: nombreSubindicador };
  incendioLayer.setVisible(false);
  indicadorLayer.setVisible(true);
  indicadorLayer.setStyle(function (feature) {
    const props = feature.getProperties();
    const detalle = props.detalle_riesgo || { indicadores: [] };
    let valor = 0;
    for (const ind of detalle.indicadores || []) {
      const sub = ind.sub_indicadores?.find(s => s.sub_indicador_nombre === nombreSubindicador);
      if (sub) { valor = sub.riesgo_subindicador || 0; break; }
    }
    const color = getColorByValue(valor, 'subindicador');
    return new Style({
      fill: new Fill({ color: color + '99' }),
      stroke: new Stroke({ color: '#000000bf', width: 1 })
    });
  });
  document.querySelectorAll('.indicador-header').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.subindicador-item').forEach(el => el.classList.remove('active'));
  event.currentTarget.classList.add('active');
  document.getElementById('btnVistaGeneral').style.display = 'block';
  if (document.getElementById('chart-panel').classList.contains('visible')) {
    const stats = calcularEstadisticasSubindicador(nombreSubindicador);
    actualizarGrafico(stats, `Subindicador: ${nombreSubindicador}`);
    actualizarResumenEstadisticas(stats);
  }
  indicadorLayer.changed();
  console.log(`Mostrando subindicador: ${nombreSubindicador} (promedio: ${promedio.toFixed(2)})`);
};

// ===== CHART =====

function calcularEstadisticasRiesgo() {
  const features = geojsonLayer.getSource().getFeatures();
  const stats = { altisimo: 0, alto: 0, medio: 0, bajo: 0 };
  features.forEach(feature => {
    const props = feature.getProperties();
    const indicadores = (props.detalle_riesgo || {}).indicadores || [];
    const riesgoTotal = indicadores.reduce((sum, ind) => sum + (parseFloat(ind.riesgo_indicador) || 0), 0);
    if (riesgoTotal >= 3.26) stats.altisimo++;
    else if (riesgoTotal >= 2.51) stats.alto++;
    else if (riesgoTotal >= 1.76) stats.medio++;
    else stats.bajo++;
  });
  return stats;
}

function actualizarResumenEstadisticas(stats) {
  const summaryDiv = document.getElementById('stats-summary');
  if (!summaryDiv) return;
  const total = Object.values(stats).reduce((a, b) => a + b, 0);
  const categorias = [
    { key: 'altisimo', label: 'Muy Alto', color: '#ff0000' },
    { key: 'alto', label: 'Alto', color: '#ff6600' },
    { key: 'medio', label: 'Medio', color: '#ffff00' },
    { key: 'bajo', label: 'Bajo', color: '#00aa00' }
  ];
  summaryDiv.innerHTML = categorias.map(cat => {
    const valor = stats[cat.key];
    const porcentaje = total > 0 ? ((valor / total) * 100).toFixed(1) : 0;
    return `<div class="stat-card ${cat.key}">
      <div class="stat-label">${cat.label}</div>
      <div class="stat-value">${valor}</div>
      <div class="stat-percentage">${porcentaje}%</div>
    </div>`;
  }).join('');
}

function actualizarGrafico(stats, titulo = 'Distribución de Riesgo General') {
  const canvas = document.getElementById('riesgoChart');
  if (!canvas) return;
  const total = Object.values(stats).reduce((a, b) => a + b, 0);
  if (riesgoChart) riesgoChart.destroy();
  const chartTitle = document.getElementById('chart-title');
  if (chartTitle) chartTitle.textContent = titulo;
  riesgoChart = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: [
        `Muy Alto (${stats.altisimo})`, `Alto (${stats.alto})`,
        `Medio (${stats.medio})`, `Bajo (${stats.bajo})`
      ],
      datasets: [{
        data: [stats.altisimo, stats.alto, stats.medio, stats.bajo],
        backgroundColor: ['#ff0000', '#ff6600', '#ffff00', '#00aa00'],
        borderColor: 'rgba(255,255,255,0.9)',
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      cutout: '60%',
      plugins: {
        legend: { position: 'bottom', labels: { font: { size: 10, family: "'Space Mono', monospace" }, color: '#64748b' } },
        tooltip: {
          callbacks: {
            label: function (context) {
              const value = context.raw || 0;
              const percentage = ((value / total) * 100).toFixed(1);
              return `${context.label}: ${value} (${percentage}%)`;
            }
          }
        }
      }
    }
  });
}

function actualizarEstadisticas() {
  actualizarGrafico(calcularEstadisticasRiesgo(), 'Distribución de Riesgo General');
  actualizarResumenEstadisticas(calcularEstadisticasRiesgo());
}

// ===== INFO PANEL =====

window.cerrarPanel = function () {
  document.getElementById('info-panel').style.display = 'none';
  selectionLayer.getSource().clear();
};

window.toggleSection = function (header) {
  header.classList.toggle('collapsed');
  const content = header.nextElementSibling;
  if (content) content.classList.toggle('collapsed');
};

function mostrarPanelInmueble(coordenada, feature) {
  var props = feature.getProperties();
  var panel = document.getElementById('info-panel');
  var content = document.getElementById('panel-content');
  if (!panel || !content) return;

  selectionLayer.getSource().clear();
  var clonedFeature = feature.clone();
  selectionLayer.getSource().addFeature(clonedFeature);

  var detalleRiesgo = props.detalle_riesgo || { indicadores: [] };
  var indicadores = detalleRiesgo.indicadores || [];
  var riesgoTotal = indicadores.reduce((sum, ind) => sum + (parseFloat(ind.riesgo_indicador) || 0), 0);

  var riesgoClass = 'bajo';
  if (riesgoTotal >= 3.26) riesgoClass = 'altisimo';
  else if (riesgoTotal >= 2.51) riesgoClass = 'alto';
  else if (riesgoTotal >= 1.76) riesgoClass = 'medio';

  const inmuebleId = props.id;

  var html = `
    <div class="datos-generales">
      <h4>Detalles del Inmueble</h4>
      <p><strong>Dirección:</strong> ${props.direccion || 'N/A'}</p>
      <p><strong>Rol SII:</strong> ${props.rol_sii || 'N/A'}</p>
      <p><strong>Manzana:</strong> ${props.manzana || 'N/A'}</p>
      <p><strong>Predio:</strong> ${props.predio || 'N/A'}</p>
      <p><strong>Riesgo Total:</strong> <span class="riesgo-badge ${riesgoClass}">${riesgoTotal.toFixed(2)}</span></p>
    </div>
  `;

  // Editor-only: edit property metadata button
  if (currentRole === 'editor' && inmuebleId) {
    html += `
      <button class="btn-edit-inmueble" onclick="mostrarFormEdicion(${inmuebleId}, ${JSON.stringify({
        direccion: props.direccion || '',
        region: props.region || '',
        manzana: props.manzana || '',
        predio: props.predio || ''
      }).replace(/"/g, '&quot;')})">
        ✏️ Editar Datos del Inmueble
      </button>
      <div id="edit-form-container-${inmuebleId}"></div>
    `;
  }

  if (indicadores.length === 0) {
    html += '<p style="text-align:center;color:#666;">No hay indicadores disponibles</p>';
  } else {
    // For editors: each sub-indicator row gets a data-subind attribute for later injection
    const isEditor = currentRole === 'editor' && inmuebleId;
    const extraHeader = isEditor ? '<th>Editar Valor</th>' : '';

    indicadores.forEach((indicador, idx) => {
      var riesgoInd = parseFloat(indicador.riesgo_indicador) || 0;
      var indClass = riesgoInd >= 2.0 ? 'alto' : (riesgoInd >= 1.0 ? 'medio' : 'bajo');
      html += `
        <div class="collapsible-section">
          <div class="section-header" onclick="toggleSection(this)">
            <span>${indicador.indicador_nombre || 'Indicador ' + (idx + 1)}</span>
            <span>
              <span class="riesgo-badge ${indClass}" style="margin-right:10px;">${riesgoInd.toFixed(2)}</span>
              <span class="toggle-icon">▼</span>
            </span>
          </div>
          <div class="section-content">
            <p><strong>Peso:</strong> ${((indicador.peso || 0) * 100).toFixed(0)}%</p>
            <table class="info-table">
              <thead><tr><th>Sub-indicador</th><th>Clase</th><th>Riesgo</th>${extraHeader}</tr></thead>
              <tbody>
      `;
      (indicador.sub_indicadores || []).forEach(sub => {
        var riesgoSub = parseFloat(sub.riesgo_subindicador) || 0;
        var riesgoPond = parseFloat(sub.riesgo_subindicador_ponderado) || 0;
        var subClass = riesgoSub >= 2.0 ? 'alto' : (riesgoSub >= 1.0 ? 'medio' : 'bajo');
        const subNombre = sub.sub_indicador_nombre || 'N/A';
        const editCell = isEditor
          ? `<td class="eval-edit-cell" data-subind="${subNombre}"><span class="eval-val-loading" style="color:#aaa;font-size:11px;">cargando…</span></td>`
          : '';
        html += `
          <tr class="riesgo-${subClass}">
            <td>${subNombre}</td>
            <td>${sub.clase || 'N/A'}</td>
            <td>${riesgoSub.toFixed(2)} <small style="color:#666;">(${(riesgoPond * 100).toFixed(1)}%)</small></td>
            ${editCell}
          </tr>
        `;
      });
      html += `</tbody></table></div></div>`;
    });
  }

  content.innerHTML = html;
  panel.style.display = 'flex';
  document.getElementById('panel-title').innerHTML =
    props.direccion ? `Inmueble: ${props.direccion}` : 'Detalles del Inmueble';

  // Load evaluaciones async and inject edit inputs for editors
  if (currentRole === 'editor' && inmuebleId) {
    cargarEvaluacionesEnPanel(inmuebleId);
  }
}

// ===== EDITOR: INMUEBLE FORM =====

window.mostrarFormEdicion = function (id, props) {
  const container = document.getElementById(`edit-form-container-${id}`);
  if (!container) return;

  // Toggle: if form is already open, close it
  if (container.innerHTML.trim() !== '') {
    container.innerHTML = '';
    return;
  }

  container.innerHTML = `
    <div class="edit-inmueble-form">
      <h4>✏️ Editar Inmueble #${id}</h4>
      <div class="edit-field">
        <label>Dirección</label>
        <input type="text" id="edit-direccion-${id}" value="${props.direccion || ''}">
      </div>
      <div class="edit-field">
        <label>Región</label>
        <input type="text" id="edit-region-${id}" value="${props.region || ''}">
      </div>
      <div class="edit-field">
        <label>Manzana</label>
        <input type="text" id="edit-manzana-${id}" value="${props.manzana || ''}">
      </div>
      <div class="edit-field">
        <label>Predio</label>
        <input type="text" id="edit-predio-${id}" value="${props.predio || ''}">
      </div>
      <div class="edit-actions">
        <button class="btn-save" onclick="guardarEdicionInmueble(${id})">Guardar</button>
        <button class="btn-cancel" onclick="document.getElementById('edit-form-container-${id}').innerHTML=''">Cancelar</button>
      </div>
      <div id="edit-feedback-${id}" class="edit-feedback"></div>
    </div>
  `;
};

window.guardarEdicionInmueble = async function (id) {
  const feedback = document.getElementById(`edit-feedback-${id}`);
  const saveBtn = document.querySelector(`#edit-form-container-${id} .btn-save`);

  const data = {
    direccion: document.getElementById(`edit-direccion-${id}`)?.value || '',
    region: document.getElementById(`edit-region-${id}`)?.value || '',
    manzana: document.getElementById(`edit-manzana-${id}`)?.value || '',
    predio: document.getElementById(`edit-predio-${id}`)?.value || ''
  };

  saveBtn.disabled = true;
  saveBtn.textContent = 'Guardando...';
  feedback.className = 'edit-feedback';
  feedback.style.display = 'none';

  try {
    const res = await apiFetch(`${API_BASE}/api/inmuebles/actualizar/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });

    if (res.ok) {
      feedback.className = 'edit-feedback success';
      feedback.textContent = 'Cambios guardados correctamente.';
      // Reload GeoJSON data to reflect updates
      geojsonSource.clear();
      geojsonSource.refresh();
    } else {
      const err = await res.json().catch(() => ({}));
      feedback.className = 'edit-feedback error';
      feedback.textContent = JSON.stringify(err);
    }
  } catch (e) {
    if (e.message !== 'Session expired') {
      feedback.className = 'edit-feedback error';
      feedback.textContent = 'Error de conexión.';
    }
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = 'Guardar';
  }
};

// ===== EDITOR: EVALUACION VALOR =====

async function cargarEvaluacionesEnPanel(inmuebleId) {
  try {
    const [evRes, clasesRes] = await Promise.all([
      apiFetch(`${API_BASE}/api/evaluacion/inmueble/${inmuebleId}/`),
      apiFetch(`${API_BASE}/api/clases/`)
    ]);
    if (!evRes.ok || !clasesRes.ok) throw new Error('Error cargando evaluaciones');

    const evaluaciones = await evRes.json();
    const todasClases  = await clasesRes.json();

    // sub_indicador_nombre → { id, valor, id_subindicador }
    const evalLookup = {};
    evaluaciones.forEach(e => {
      evalLookup[e.sub_indicador_nombre] = { id: e.id, valor: e.valor, subId: e.id_subindicador };
    });

    // sub_indicador_id → [{ nombre, valor }] sorted by valor asc
    const clasesLookup = {};
    todasClases.forEach(c => {
      if (!clasesLookup[c.sub_indicador]) clasesLookup[c.sub_indicador] = [];
      clasesLookup[c.sub_indicador].push({ nombre: c.nombre, valor: c.valor });
    });
    Object.values(clasesLookup).forEach(arr => arr.sort((a, b) => a.valor - b.valor));

    document.querySelectorAll('.eval-edit-cell').forEach(cell => {
      const subNombre = cell.dataset.subind;
      const ev = evalLookup[subNombre];
      if (!ev) {
        cell.innerHTML = '<span style="color:#ccc;font-size:11px;">—</span>';
        return;
      }

      const clases = clasesLookup[ev.subId] || [];
      if (clases.length === 0) {
        // Fallback to number input if no classes defined for this sub-indicator
        cell.innerHTML = `
          <div style="display:flex;align-items:center;gap:4px;">
            <input type="number" class="clase-valor-input" id="eval-input-${ev.id}"
                   value="${ev.valor}" min="0" max="5" style="width:52px;">
            <button class="btn-clase-save" onclick="guardarEvaluacion(${ev.id}, ${inmuebleId})">✓</button>
            <span class="clase-msg" id="eval-msg-${ev.id}"></span>
          </div>`;
        return;
      }

      const options = clases.map(c =>
        `<option value="${c.valor}"${c.valor === ev.valor ? ' selected' : ''}>${c.nombre}</option>`
      ).join('');

      cell.innerHTML = `
        <div style="display:flex;align-items:center;gap:4px;">
          <select class="eval-clase-select" id="eval-select-${ev.id}"
                  onchange="guardarEvaluacion(${ev.id}, ${inmuebleId})">
            ${options}
          </select>
          <span class="clase-msg" id="eval-msg-${ev.id}"></span>
        </div>`;
    });
  } catch (e) {
    if (e.message !== 'Session expired') {
      document.querySelectorAll('.eval-val-loading').forEach(el => { el.textContent = '—'; });
    }
  }
}

window.guardarEvaluacion = async function (evaluacionId, inmuebleId) {
  const select = document.getElementById(`eval-select-${evaluacionId}`);
  const input  = document.getElementById(`eval-input-${evaluacionId}`);
  const el = select || input;
  const msg = document.getElementById(`eval-msg-${evaluacionId}`);

  if (!el) return;
  const valor = parseInt(el.value, 10);
  if (isNaN(valor) || valor < 0) {
    if (msg) { msg.textContent = '✗'; msg.style.color = 'red'; }
    return;
  }

  if (el) el.disabled = true;
  if (msg) { msg.textContent = '…'; msg.style.color = '#aaa'; }

  try {
    const res = await apiFetch(`${API_BASE}/api/evaluacion/actualizar/${evaluacionId}/`, {
      method: 'PATCH',
      body: JSON.stringify({ valor })
    });

    if (res.ok) {
      if (msg) { msg.textContent = '✓'; msg.style.color = '#4caf50'; }
      await actualizarFeatureEnMapa(inmuebleId);
    } else {
      if (msg) { msg.textContent = '✗'; msg.style.color = 'red'; }
    }
  } catch (e) {
    if (e.message !== 'Session expired' && msg) { msg.textContent = '✗'; msg.style.color = 'red'; }
  } finally {
    if (el) el.disabled = false;
    setTimeout(() => { if (msg) msg.textContent = ''; }, 3000);
  }
};

async function actualizarFeatureEnMapa(inmuebleId) {
  try {
    // Fetch only the updated single feature from pg_featureserv
    const res = await fetch(
      `${featureServer}collections/public.detalle_calculo_incendio/items/${inmuebleId}`
    );
    if (!res.ok) throw new Error('feature not found');
    const geojsonFeature = await res.json();

    // Update properties in-place on the existing source feature (no clear/reload flash)
    const existing = geojsonSource.getFeatures().find(f => f.get('id') === inmuebleId);
    if (existing && geojsonFeature.properties) {
      Object.entries(geojsonFeature.properties).forEach(([k, v]) => existing.set(k, v));
      geojsonSource.changed();
    }

    // Expire VectorTile cache so new risk colors load for the affected tiles
    incendioLayer.getSource().refresh();
  } catch {
    // Fallback: full reload if single-feature fetch fails
    geojsonSource.clear();
    geojsonSource.refresh();
  }
}

// ===== EDITOR: CLASSES PANEL =====

window.abrirPanelClases = function () {
  const panel = document.getElementById('clases-panel');
  panel.style.display = 'flex';
  cargarClases();
};

window.cerrarPanelClases = function () {
  document.getElementById('clases-panel').style.display = 'none';
};

async function cargarClases() {
  const content = document.getElementById('clases-panel-content');
  content.innerHTML = '<p style="text-align:center;color:#666;">Cargando...</p>';

  try {
    const [clasesRes, subRes] = await Promise.all([
      apiFetch(`${API_BASE}/api/clases/`),
      apiFetch(`${API_BASE}/api/subindicadores/`)
    ]);

    if (!clasesRes.ok || !subRes.ok) throw new Error('Error al cargar datos');

    const clases = await clasesRes.json();
    const subindicadores = await subRes.json();

    // Group clases by sub-indicator
    const subMap = {};
    subindicadores.forEach(s => { subMap[s.id] = s.nombre; });

    const grouped = {};
    clases.forEach(c => {
      const subNombre = subMap[c.sub_indicador] || `SubIndicador ${c.sub_indicador}`;
      if (!grouped[subNombre]) grouped[subNombre] = [];
      grouped[subNombre].push(c);
    });

    let html = '';
    Object.entries(grouped).forEach(([subNombre, items]) => {
      html += `<div class="clase-group"><div class="clase-group-title">${subNombre}</div>`;
      items.forEach(c => {
        html += `
          <div class="clase-row">
            <span class="clase-nombre">${c.nombre}</span>
            <input type="number" class="clase-valor-input" id="clase-val-${c.id}" value="${c.valor}" min="0" max="5">
            <button class="btn-clase-save" onclick="guardarClase(${c.id})">Guardar</button>
            <span class="clase-msg" id="clase-msg-${c.id}"></span>
          </div>
        `;
      });
      html += `</div>`;
    });

    content.innerHTML = html || '<p style="text-align:center;color:#666;">No hay clases.</p>';
  } catch (e) {
    if (e.message !== 'Session expired') {
      content.innerHTML = '<p style="color:red;text-align:center;">Error al cargar clases.</p>';
    }
  }
}

window.guardarClase = async function (id) {
  const input = document.getElementById(`clase-val-${id}`);
  const msg = document.getElementById(`clase-msg-${id}`);
  const btn = input?.closest('.clase-row')?.querySelector('.btn-clase-save');

  if (!input) return;
  const valor = parseInt(input.value, 10);
  if (isNaN(valor)) { msg.textContent = '✗ Inválido'; msg.style.color = 'red'; return; }

  if (btn) btn.disabled = true;
  msg.textContent = '...';
  msg.style.color = '#aaa';

  try {
    const res = await apiFetch(`${API_BASE}/api/clases/actualizar/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify({ valor })
    });

    if (res.ok) {
      msg.textContent = '✓';
      msg.style.color = '#4caf50';
    } else {
      msg.textContent = '✗';
      msg.style.color = 'red';
    }
  } catch (e) {
    if (e.message !== 'Session expired') { msg.textContent = '✗'; msg.style.color = 'red'; }
  } finally {
    if (btn) btn.disabled = false;
    setTimeout(() => { msg.textContent = ''; }, 3000);
  }
};

// ===== KML DOWNLOAD =====

window.descargarKML = async function () {
  const btn = document.getElementById('btn-descargar-kml');
  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Generando…';

  try {
    const res = await apiFetch(`${API_BASE}/api/crear-kml-detalle/`);
    if (!res.ok) throw new Error('Error al generar KML');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'Incendio_Detalle.kml';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (e) {
    if (e.message !== 'Session expired') alert('No se pudo generar el archivo KML.');
  } finally {
    btn.disabled = false;
    btn.textContent = original;
  }
};

// ===== PDF DOWNLOAD (resumen global, generación asíncrona con Celery) =====

window.descargarPDF = async function () {
  const btn = document.getElementById('btn-descargar-pdf');
  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Generando…';

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  try {
    // 1) Encolar la generación
    const resGen = await apiFetch(`${API_BASE}/api/generar-pdf-resumen/`, {
      method: 'POST',
      body: JSON.stringify({ amenaza_id: 1 }),
    });
    if (!resGen.ok) throw new Error('Error al iniciar la generación');
    const { task_id } = await resGen.json();

    // 2) Poll del estado hasta terminar
    for (;;) {
      await sleep(1500);
      const resEst = await apiFetch(`${API_BASE}/api/generar-pdf-resumen/estado/${task_id}/`);
      if (!resEst.ok) throw new Error('Error consultando el estado');
      const { estado } = await resEst.json();
      if (estado === 'SUCCESS') break;
      if (estado === 'FAILURE') throw new Error('La generación del PDF falló');
      btn.textContent = 'Generando…';
    }

    // 3) Descargar el PDF
    btn.textContent = 'Descargando…';
    const resPdf = await apiFetch(`${API_BASE}/api/generar-pdf-resumen/descargar/${task_id}/`);
    if (!resPdf.ok) throw new Error('Error al descargar el PDF');
    const blob = await resPdf.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'Resumen_Riesgo_Incendio.pdf';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (e) {
    if (e.message !== 'Session expired') alert('No se pudo generar el PDF de resumen.');
  } finally {
    btn.disabled = false;
    btn.textContent = original;
  }
};

// ===== MAP EVENTS =====

map.on('click', function (evt) {
  var feature = map.forEachFeatureAtPixel(evt.pixel, function (f, layer) {
    return layer === geojsonLayer ? f : null;
  });
  if (!feature) {
    feature = map.forEachFeatureAtPixel(evt.pixel, function (f, layer) {
      return layer === incendioLayer ? f : null;
    });
  }
  if (feature) mostrarPanelInmueble(evt.coordinate, feature);
});

map.on('pointermove', function (evt) {
  const hit = map.hasFeatureAtPixel(map.getEventPixel(evt.originalEvent), {
    layerFilter: l => l !== selectionLayer
  });
  map.getTargetElement().style.cursor = hit ? 'pointer' : '';
});

geojsonLayer.getSource().on('featuresloadend', function () {
  const features = geojsonLayer.getSource().getFeatures();
  console.log(`GeoJSON cargado: ${features.length} features`);
  if (document.getElementById('stats-panel').classList.contains('visible')) cargarIndicadores();
  if (document.getElementById('chart-panel').classList.contains('visible')) actualizarEstadisticas();
});

// ===== START =====
initApp();
