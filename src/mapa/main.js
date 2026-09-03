import 'ol/ol.css';
import './style.css';

import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import GeoJSON from 'ol/format/GeoJSON';
import XYZ from 'ol/source/XYZ';
import { defaults as defaultControls } from 'ol/control';
import { Style, Fill, Stroke, Circle } from 'ol/style';

// ===== SERVIDORES =====
const API_BASE = 'http://localhost:8000';
const featureServer = 'http://localhost:9000/';

// Amenaza que se muestra si aún no se cargó el selector. Debe coincidir con
// AMENAZA_POR_DEFECTO de api/views.py.
const AMENAZA_POR_DEFECTO = 1;

/** Detalle de riesgo de una amenaza, servido por pg_featureserv. */
function geojsonUrl(amenazaId) {
  return `${featureServer}functions/postgisftw.detalle_calculo/items.json`
       + `?amenaza_id=${amenazaId}&limit=2000`;
}

function detalleInmuebleUrl(amenazaId, inmuebleId) {
  return `${featureServer}functions/postgisftw.detalle_calculo/items.json`
       + `?amenaza_id=${amenazaId}&inmueble_id=${inmuebleId}&limit=1`;
}

// =============================================================================
// ESCALA DE RIESGO — fuente única de verdad en el cliente.
// Debe mantenerse idéntica a api/reports/niveles.py del backend.
// =============================================================================

const NIVELES = [
  { key: 'muyalto', label: 'Muy alto', fill: '#ff0000', fg: '#c20000', tint: '#ffe5e5', min: 3.26, rango: '≥ 3,26' },
  { key: 'alto',    label: 'Alto',     fill: '#ff6600', fg: '#a33f00', tint: '#ffece0', min: 2.51, rango: '2,51 – 3,25' },
  { key: 'medio',   label: 'Medio',    fill: '#ffff00', fg: '#75690a', tint: '#fbf7cc', min: 1.76, rango: '1,76 – 2,50' },
  { key: 'bajo',    label: 'Bajo',     fill: '#00aa00', fg: '#00752b', tint: '#e2f5e2', min: -Infinity, rango: '< 1,76' }
];

// Escala por indicador / sub-indicador (valores ~0–1, no 0–4)
const NIVELES_PARCIAL = [
  { key: 'muyalto', label: 'Muy alto', fill: '#ff0000', fg: '#c20000', tint: '#ffe5e5', min: 1.0 },
  { key: 'alto',    label: 'Alto',     fill: '#ff6600', fg: '#a33f00', tint: '#ffece0', min: 0.5 },
  { key: 'medio',   label: 'Medio',    fill: '#ffff00', fg: '#75690a', tint: '#fbf7cc', min: 0.25 },
  { key: 'bajo',    label: 'Bajo',     fill: '#00aa00', fg: '#00752b', tint: '#e2f5e2', min: -Infinity }
];

// "Sin evaluar": no es un nivel de riesgo (no tiene rango en la escala 0-4),
// así que vive fuera de NIVELES a propósito — api/tests/test_umbrales.py
// verifica que ese array tenga exactamente los 4 niveles de riesgo reales.
// Valores calcados de api/riesgo.py:NO_EVALUADO, que también fijan
// --risk-nulo/--risk-nulo-fg en style.css.
const NO_EVALUADO = { key: 'noeval', label: 'No evaluado', fill: '#9e9e9e', fg: '#5b5f60', tint: '#eef0f0', rango: '—' };

const RIESGO_MAX = 4;

/** Nivel para el índice total (escala 0–4). */
function nivelTotal(valor) {
  const v = Number(valor) || 0;
  return NIVELES.find(n => v >= n.min) || NIVELES[NIVELES.length - 1];
}

/** Nivel para un indicador o sub-indicador (escala ~0–1). */
function nivelParcial(valor) {
  const v = Number(valor) || 0;
  return NIVELES_PARCIAL.find(n => v >= n.min) || NIVELES_PARCIAL[NIVELES_PARCIAL.length - 1];
}

/** Formato numérico chileno: 2.87 -> "2,87" */
function num(valor, decimales = 2) {
  return (Number(valor) || 0).toFixed(decimales).replace('.', ',');
}

function pct(valor, total) {
  if (!total) return '0%';
  return `${Math.round((valor / total) * 100)}%`;
}

function esc(str) {
  return String(str ?? '').replace(/[&<>"']/g, c => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

/** Suma de riesgo_indicador de un detalle_riesgo. */
function riesgoTotalDe(detalle) {
  const inds = (detalle && detalle.indicadores) || [];
  return inds.reduce((sum, i) => sum + (parseFloat(i.riesgo_indicador) || 0), 0);
}

function propsDetalle(feature) {
  const d = feature.get('detalle_riesgo');
  if (typeof d === 'string') {
    try { return JSON.parse(d); } catch { return { indicadores: [] }; }
  }
  return d || { indicadores: [] };
}

/**
 * `indicadores` es `null` cuando el inmueble no tiene ninguna evaluación para
 * la amenaza activa (el `jsonb_agg` de la función SQL no matchea filas), y un
 * array —vacío o no— en cualquier otro caso. Es la señal precisa: nunca hay
 * que inferirlo de `riesgoTotalDe(...) === 0`, que también da 0 con datos reales.
 */
function sinEvaluar(feature) {
  return propsDetalle(feature).indicadores == null;
}

// =============================================================================
// ESTADO
// =============================================================================

const state = {
  role: 'viewer',
  username: '',
  amenazas: [],
  amenazaActiva: null,
  vista: { tipo: 'total', nombre: null },   // 'total' | 'indicador' | 'subindicador'
  inmuebleSeleccionado: null,
  distribucion: [],
  clasesPorSub: {},
  evaluacionesActuales: {}
};

// =============================================================================
// JWT / API
// =============================================================================

function decodeToken(token) {
  try {
    const payload = token.split('.')[1];
    return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
  } catch { return null; }
}

function isTokenExpired(token) {
  const p = decodeToken(token);
  return !p || !p.exp || Date.now() / 1000 > p.exp;
}

const getToken = () => localStorage.getItem('access_token');

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
  } catch { return false; }
}

async function apiFetch(url, options = {}, retry = true) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(url, { ...options, headers });

  if (res.status === 401 && retry) {
    if (await refreshAccessToken()) return apiFetch(url, options, false);
    clearAuth();
    mostrarLogin('Tu sesión expiró, vuelve a ingresar.');
    throw new Error('Session expired');
  }
  return res;
}

// =============================================================================
// UI: toast
// =============================================================================

let toastTimer = null;
function toast(mensaje, tipo = '') {
  const el = document.getElementById('toast');
  el.className = 'toast' + (tipo ? ` toast--${tipo}` : '');
  el.textContent = mensaje;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, 4000);
}

// =============================================================================
// CAPAS DEL MAPA
// =============================================================================

const baseLayer = new TileLayer({
  source: new XYZ({ url: 'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png?key=cb1_2lln_1_b6707636f616ae58f4dfc24e' })
});

/** Estilo por nivel: relleno con alfa + borde blanco fino (según diseño). */
function estiloPorValor(valor, escala) {
  const nivel = escala === 'total' ? nivelTotal(valor) : nivelParcial(valor);
  return new Style({
    fill: new Fill({ color: nivel.fill + '99' }),
    stroke: new Stroke({ color: '#ffffff', width: 1 })
  });
}

/** Relleno gris punteado para inmuebles sin evaluación en la amenaza activa. */
const estiloSinEvaluar = new Style({
  fill: new Fill({ color: NO_EVALUADO.fill + '99' }),
  stroke: new Stroke({ color: '#ffffff', width: 1, lineDash: [4, 3] })
});

/** Vista general: color por índice de riesgo total del inmueble. */
const estiloTotal = feature => sinEvaluar(feature)
  ? estiloSinEvaluar
  : estiloPorValor(riesgoTotalDe(propsDetalle(feature)), 'total');

const geojsonSource = new VectorSource({
  format: new GeoJSON(),
  loader: function (extent, resolution, projection, success, failure) {
    fetch(geojsonUrl(state.amenazaActiva?.id ?? AMENAZA_POR_DEFECTO))
      .then(r => { if (!r.ok) throw new Error('GeoJSON load failed'); return r.json(); })
      .then(data => {
        const features = new GeoJSON().readFeatures(data, { featureProjection: projection });
        this.addFeatures(features);
        success(features);
      })
      .catch(() => failure());
  }
});

/**
 * Relleno transparente —no un Style vacío— para cuando esta capa sólo aporta la
 * geometría clickeable: sin fill, OpenLayers no la considera en
 * `forEachFeatureAtPixel` y el mapa deja de responder al clic.
 */
const estiloClickeable = new Style({ fill: new Fill({ color: 'rgba(0,0,0,0)' }) });

/**
 * Capa principal. En la vista general pinta el índice total; al entrar a un
 * indicador o sub-indicador pasa a transparente y `indicadorLayer` toma el color,
 * pero sigue capturando el clic.
 */
const geojsonLayer = new VectorLayer({
  source: geojsonSource,
  style: estiloTotal
});

const indicadorLayer = new VectorLayer({
  source: geojsonSource,
  visible: false,
  style: () => estiloClickeable
});

const selectionLayer = new VectorLayer({
  source: new VectorSource(),
  style: () => new Style({
    // Selección: contorno oscuro sin relleno (no compite con el nivel "medio")
    stroke: new Stroke({ color: '#16323f', width: 3 }),
    image: new Circle({
      radius: 8,
      fill: new Fill({ color: 'transparent' }),
      stroke: new Stroke({ color: '#16323f', width: 3 })
    })
  })
});

const VISTA_INICIAL = { center: [-7973693.872453815, -3900580.7807773366], zoom: 17 };

const map = new Map({
  target: 'map',
  controls: defaultControls({ zoom: false, rotate: false, attribution: false }),
  view: new View({ center: VISTA_INICIAL.center, zoom: VISTA_INICIAL.zoom }),
  layers: [baseLayer, geojsonLayer, indicadorLayer, selectionLayer]
});

// =============================================================================
// LAYOUT: paneles acoplados
// =============================================================================

const shell = document.getElementById('app-shell');

function actualizarTamanoMapa() {
  map.updateSize();
}
shell.addEventListener('transitionend', e => {
  if (e.propertyName === 'grid-template-columns' || e.propertyName === 'transform') actualizarTamanoMapa();
});

function abrirFicha() {
  shell.classList.remove('is-right-closed');
  setTimeout(actualizarTamanoMapa, 280);
}

function cerrarFicha() {
  shell.classList.add('is-right-closed');
  state.inmuebleSeleccionado = null;
  selectionLayer.getSource().clear();
  setTimeout(actualizarTamanoMapa, 280);
}

function togglePanelIzquierdo() {
  shell.classList.toggle('is-left-closed');
  setTimeout(actualizarTamanoMapa, 280);
}

// =============================================================================
// LOGIN
// =============================================================================

function mostrarLogin(mensajeError) {
  document.getElementById('login-modal').hidden = false;
  shell.hidden = true;
  const err = document.getElementById('login-error');
  if (mensajeError) { err.textContent = mensajeError; err.hidden = false; }
  else { err.hidden = true; }
  document.getElementById('login-password').value = '';
}

function ocultarLogin() {
  document.getElementById('login-modal').hidden = true;
  shell.hidden = false;
  actualizarTamanoMapa();
}

function iniciales(nombre) {
  const partes = String(nombre || '').split(/[.\s_-]+/).filter(Boolean);
  if (!partes.length) return '··';
  if (partes.length === 1) return partes[0].slice(0, 2);
  return (partes[0][0] + partes[partes.length - 1][0]);
}

function pintarUsuario() {
  document.getElementById('user-avatar').textContent = iniciales(state.username);
  document.getElementById('user-chip-name').textContent = state.username || '—';
  document.getElementById('user-chip-role').textContent = state.role === 'editor' ? 'Editor' : 'Observador';
  document.getElementById('ponderadores-card').hidden = state.role !== 'editor';
}

document.getElementById('login-form').addEventListener('submit', async function (e) {
  e.preventDefault();
  const btn = document.getElementById('login-btn');
  const errorDiv = document.getElementById('login-error');
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;

  btn.disabled = true;
  const btnHtml = btn.innerHTML;
  btn.textContent = 'Ingresando…';
  errorDiv.hidden = true;

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
      state.role = payload?.role || 'viewer';
      state.username = payload?.username || username;
      ocultarLogin();
      pintarUsuario();
      await arrancarConsola();
    } else {
      const err = await res.json().catch(() => ({}));
      errorDiv.textContent = err.detail || 'Usuario o contraseña incorrectos.';
      errorDiv.hidden = false;
    }
  } catch {
    errorDiv.textContent = 'No se pudo conectar al servidor.';
    errorDiv.hidden = false;
  } finally {
    btn.disabled = false;
    btn.innerHTML = btnHtml;
  }
});

document.getElementById('btn-logout').addEventListener('click', () => {
  clearAuth();
  state.role = 'viewer';
  state.username = '';
  cerrarFicha();
  cerrarMenus();
  geojsonSource.clear();
  mostrarLogin();
});

// =============================================================================
// AMENAZAS
// =============================================================================

async function cargarAmenazas() {
  const cont = document.getElementById('amenaza-selector');
  try {
    const res = await apiFetch(`${API_BASE}/api/amenazas/`);
    if (!res.ok) throw new Error('amenazas');
    state.amenazas = await res.json();
  } catch (e) {
    if (e.message === 'Session expired') return;
    state.amenazas = [];
  }

  if (!state.amenazas.length) { cont.innerHTML = ''; return; }

  state.amenazaActiva = state.amenazas.find(a => a.id === AMENAZA_POR_DEFECTO)
                     || state.amenazas[0];

  cont.innerHTML = state.amenazas.map(a => {
    const activa = a.id === state.amenazaActiva.id;
    return `<button type="button" role="tab"
              class="amenaza-opt${activa ? ' is-active' : ''}"
              data-amenaza-id="${a.id}"
              aria-selected="${activa}">
              ${esc(a.nombre)}
            </button>`;
  }).join('');

  cont.querySelectorAll('.amenaza-opt').forEach(btn => {
    btn.addEventListener('click', () => seleccionarAmenaza(Number(btn.dataset.amenazaId)));
  });

  pintarTituloAmenaza();
}

function seleccionarAmenaza(id) {
  const amenaza = state.amenazas.find(a => a.id === id);
  if (!amenaza || amenaza.id === state.amenazaActiva?.id) return;
  state.amenazaActiva = amenaza;
  document.querySelectorAll('.amenaza-opt').forEach(b => {
    const activa = Number(b.dataset.amenazaId) === id;
    b.classList.toggle('is-active', activa);
    b.setAttribute('aria-selected', String(activa));
  });
  pintarTituloAmenaza();
  volverVistaGeneral();
  cerrarFicha();
  // El detalle de riesgo es por amenaza: hay que traer el GeoJSON de nuevo.
  // `refresh()` limpia la fuente y vuelve a invocar el loader, que lee
  // state.amenazaActiva — ya actualizado más arriba.
  geojsonSource.refresh();
}

function pintarTituloAmenaza() {
  document.getElementById('amenaza-titulo').textContent = state.amenazaActiva?.nombre || '—';
}

// =============================================================================
// CONTEXTO TERRITORIAL + LEYENDA
// =============================================================================

function calcularDistribucion() {
  const features = geojsonSource.getFeatures();
  const conteo = { muyalto: 0, alto: 0, medio: 0, bajo: 0, noeval: 0 };
  features.forEach(f => {
    if (sinEvaluar(f)) { conteo.noeval++; return; }
    const nivel = nivelTotal(riesgoTotalDe(propsDetalle(f)));
    conteo[nivel.key]++;
  });
  state.distribucion = [...NIVELES, NO_EVALUADO].map(n => ({ ...n, cantidad: conteo[n.key] }));
  return state.distribucion;
}

function pintarLeyenda() {
  const filas = calcularDistribucion();
  const total = filas.reduce((s, f) => s + f.cantidad, 0);

  document.getElementById('legend-total').textContent =
    total === 1 ? '1 inmueble' : `${total} inmuebles`;

  document.getElementById('legend-rows').innerHTML = filas.map(f => `
    <div class="legend-row">
      <span class="legend-swatch" style="background:${f.fill}"></span>
      <span class="legend-label">${f.label}</span>
      <span class="legend-range">${f.rango}</span>
      <span class="legend-count">${f.cantidad}</span>
    </div>
  `).join('');

  const nInd = contarIndicadores();
  document.getElementById('legend-foot').textContent = nInd
    ? `Suma ponderada de ${nInd} ${nInd === 1 ? 'indicador' : 'indicadores'}, escala 0–${RIESGO_MAX}.`
    : `Escala de riesgo 0–${RIESGO_MAX}.`;

  document.getElementById('contexto-territorial').textContent =
    `${state.amenazaActiva?.nombre || 'Riesgo'} · ${total} inmuebles catastrados`;
}

function contarIndicadores() {
  const f = geojsonSource.getFeatures().find(f => !sinEvaluar(f));
  if (!f) return 0;
  return (propsDetalle(f).indicadores || []).length;
}

// =============================================================================
// PANEL IZQUIERDO: composición del riesgo
// =============================================================================

function agregarIndicadores() {
  const features = geojsonSource.getFeatures();
  const acc = {};

  features.forEach(f => {
    (propsDetalle(f).indicadores || []).forEach(ind => {
      const nombre = ind.indicador_nombre;
      if (!nombre) return;
      if (!acc[nombre]) acc[nombre] = { nombre, peso: ind.peso, valores: [], subs: {} };
      acc[nombre].valores.push(parseFloat(ind.riesgo_indicador) || 0);
      (ind.sub_indicadores || []).forEach(sub => {
        const sn = sub.sub_indicador_nombre;
        if (!sn) return;
        if (!acc[nombre].subs[sn]) acc[nombre].subs[sn] = { nombre: sn, valores: [] };
        acc[nombre].subs[sn].valores.push(parseFloat(sub.riesgo_subindicador) || 0);
      });
    });
  });

  const prom = arr => (arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0);
  const lista = Object.values(acc).map(d => ({
    nombre: d.nombre,
    peso: d.peso,
    promedio: prom(d.valores),
    subs: Object.values(d.subs).map(s => ({ nombre: s.nombre, promedio: prom(s.valores) }))
  }));

  const sumaProm = lista.reduce((s, i) => s + i.promedio, 0);
  lista.forEach(i => { i.aporte = sumaProm ? (i.promedio / sumaProm) * 100 : 0; });
  return lista;
}

function renderizarIndicadores() {
  const cont = document.getElementById('indicadores-container');
  const lista = agregarIndicadores();

  if (!lista.length) {
    cont.innerHTML = '<p class="panel-placeholder">No hay indicadores disponibles.</p>';
    return;
  }

  const maxProm = Math.max(...lista.map(i => i.promedio), 0.0001);

  cont.innerHTML = lista.map(ind => {
    const nivel = nivelParcial(ind.promedio);
    const ancho = Math.min(100, (ind.promedio / maxProm) * 100);
    const pesoTxt = ind.peso != null ? `peso ${Math.round((ind.peso || 0) * 100)}%` : '';
    const nSubs = ind.subs.length;

    const subsHtml = nSubs
      ? ind.subs.map(s => {
          const sn = nivelParcial(s.promedio);
          return `<div class="subindicador-item" data-subindicador="${esc(s.nombre)}">
                    <span class="subindicador-nombre">${esc(s.nombre)}</span>
                    <span class="subindicador-riesgo" style="color:${sn.fg}">${num(s.promedio)}</span>
                  </div>`;
        }).join('')
      : '<p class="panel-placeholder">Sin sub-indicadores.</p>';

    return `
      <div class="indicador-item">
        <div class="indicador-header" data-indicador="${esc(ind.nombre)}">
          <div class="indicador-top">
            <span class="indicador-nombre">${esc(ind.nombre)}</span>
            ${pesoTxt ? `<span class="indicador-peso">${pesoTxt}</span>` : ''}
            <span class="indicador-riesgo" style="background:${nivel.tint};color:${nivel.fg}">${num(ind.promedio)}</span>
            <span class="indicador-toggle">▼</span>
          </div>
          <div class="bar-track"><div class="bar-fill" style="width:${ancho}%;background:${nivel.fill}"></div></div>
          <div class="indicador-foot">
            <span>${nSubs} ${nSubs === 1 ? 'sub-indicador' : 'sub-indicadores'}</span>
            <span>${Math.round(ind.aporte)}% del total</span>
          </div>
        </div>
        <div class="subindicadores-container">${subsHtml}</div>
      </div>
    `;
  }).join('');

  cont.querySelectorAll('.indicador-header').forEach(header => {
    header.addEventListener('click', () => {
      const subCont = header.nextElementSibling;
      const toggle = header.querySelector('.indicador-toggle');
      subCont.classList.toggle('visible');
      toggle.textContent = subCont.classList.contains('visible') ? '▲' : '▼';
      seleccionarIndicador(header.dataset.indicador);
    });
  });

  cont.querySelectorAll('.subindicador-item').forEach(item => {
    item.addEventListener('click', e => {
      e.stopPropagation();
      seleccionarSubindicador(item.dataset.subindicador);
    });
  });
}

// ---- Segmentado Riesgo total / Por indicador ----
document.querySelectorAll('.segmented-opt').forEach(btn => {
  btn.addEventListener('click', () => {
    if (btn.dataset.vista === 'total') { volverVistaGeneral(); return; }
    // "Por indicador": si aún no hay uno elegido, entra al primero de la lista
    if (state.vista.tipo === 'total') {
      const primero = document.querySelector('.indicador-header');
      if (primero) {
        primero.nextElementSibling.classList.add('visible');
        primero.querySelector('.indicador-toggle').textContent = '▲';
        seleccionarIndicador(primero.dataset.indicador);
      }
    }
  });
});

function pintarSegmentado() {
  const esTotal = state.vista.tipo === 'total';
  document.querySelectorAll('.segmented-opt').forEach(b => {
    const activa = (b.dataset.vista === 'total') === esTotal;
    b.classList.toggle('is-active', activa);
    b.setAttribute('aria-selected', String(activa));
  });
}

function volverVistaGeneral() {
  state.vista = { tipo: 'total', nombre: null };
  geojsonLayer.setStyle(estiloTotal);
  indicadorLayer.setVisible(false);
  document.querySelectorAll('.indicador-header, .subindicador-item').forEach(el => el.classList.remove('active'));
  pintarSegmentado();
}

function seleccionarIndicador(nombre) {
  state.vista = { tipo: 'indicador', nombre };
  geojsonLayer.setStyle(estiloClickeable);
  indicadorLayer.setVisible(true);
  indicadorLayer.setStyle(feature => {
    if (sinEvaluar(feature)) return estiloSinEvaluar;
    const ind = (propsDetalle(feature).indicadores || []).find(i => i.indicador_nombre === nombre);
    return estiloPorValor(ind?.riesgo_indicador || 0, 'parcial');
  });

  document.querySelectorAll('.indicador-header, .subindicador-item').forEach(el => el.classList.remove('active'));
  const header = document.querySelector(`.indicador-header[data-indicador="${CSS.escape(nombre)}"]`);
  if (header) header.classList.add('active');

  pintarSegmentado();
  indicadorLayer.changed();
}

function seleccionarSubindicador(nombre) {
  state.vista = { tipo: 'subindicador', nombre };
  geojsonLayer.setStyle(estiloClickeable);
  indicadorLayer.setVisible(true);
  indicadorLayer.setStyle(feature => {
    if (sinEvaluar(feature)) return estiloSinEvaluar;
    let valor = 0;
    for (const ind of propsDetalle(feature).indicadores || []) {
      const sub = (ind.sub_indicadores || []).find(s => s.sub_indicador_nombre === nombre);
      if (sub) { valor = sub.riesgo_subindicador || 0; break; }
    }
    return estiloPorValor(valor, 'parcial');
  });

  document.querySelectorAll('.indicador-header, .subindicador-item').forEach(el => el.classList.remove('active'));
  const item = document.querySelector(`.subindicador-item[data-subindicador="${CSS.escape(nombre)}"]`);
  if (item) item.classList.add('active');

  pintarSegmentado();
  indicadorLayer.changed();
}

// =============================================================================
// FICHA DEL INMUEBLE
// =============================================================================

function segmentosEscala() {
  // Anchos proporcionales a los cortes 1,76 / 2,51 / 3,26 / 4,00 sobre la escala 0–4
  return [
    { fill: '#00aa00', w: 44 },
    { fill: '#ffff00', w: 19 },
    { fill: '#ff6600', w: 18 },
    { fill: '#ff0000', w: 19 }
  ];
}

function mostrarFichaInmueble(feature) {
  const props = feature.getProperties();
  const detalle = propsDetalle(feature);
  const noEvaluado = detalle.indicadores == null;
  const indicadores = detalle.indicadores || [];
  const total = riesgoTotalDe(detalle);
  const nivel = nivelTotal(total);
  const inmuebleId = props.id;

  state.inmuebleSeleccionado = { id: inmuebleId, props, detalle };

  // Resalte en el mapa
  selectionLayer.getSource().clear();
  selectionLayer.getSource().addFeature(feature.clone());

  // --- Cabecera ---
  document.getElementById('panel-title').textContent = props.direccion || 'Inmueble sin dirección';

  const metas = [];
  if (props.rol_sii) metas.push(`Rol SII ${props.rol_sii}`);
  if (props.manzana) metas.push(`Manzana ${props.manzana}`);
  if (props.predio) metas.push(`Predio ${props.predio}`);
  if (props.region) metas.push(esc(props.region));
  document.getElementById('ficha-meta').innerHTML =
    metas.map(m => `<span class="meta-chip">${esc(m)}</span>`).join('');

  // --- Cuerpo ---
  const marcador = Math.max(0, Math.min(100, (total / RIESGO_MAX) * 100));
  const segs = segmentosEscala().map(s => `<div class="scale-seg" style="width:${s.w}%;background:${s.fill}"></div>`).join('');

  // Aporte de cada sub-indicador sobre el total ponderado
  const filas = [];
  indicadores.forEach(ind => {
    (ind.sub_indicadores || []).forEach(sub => {
      filas.push({
        nombre: sub.sub_indicador_nombre || '—',
        clase: sub.clase,
        valor: parseFloat(sub.riesgo_subindicador) || 0,
        ponderado: parseFloat(sub.riesgo_subindicador_ponderado) || 0
      });
    });
  });
  const sumaPond = filas.reduce((s, f) => s + f.ponderado, 0);
  const maxValor = Math.max(...filas.map(f => f.valor), 0.0001);

  const filasHtml = filas.length ? filas.map(f => {
    const n = nivelParcial(f.valor);
    const ancho = Math.min(100, (f.valor / maxValor) * 100);
    const aporte = sumaPond ? `${num((f.ponderado / sumaPond) * 100, 1)}%` : '—';
    const claseTxt = f.clase || 'Sin clase';
    const editable = state.role === 'editor';
    return `
      <div class="sub-card" data-subnombre="${esc(f.nombre)}">
        <div class="sub-row">
          <span class="sub-name">${esc(f.nombre)}</span>
          <span class="sub-value" style="color:${n.fg}">${num(f.valor)}</span>
          ${editable ? `<button class="icon-btn btn-editar-sub" style="width:26px;height:26px;background:var(--bg-inset)" title="Editar clase" aria-label="Editar clase de ${esc(f.nombre)}">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.75" stroke-linecap="round" stroke-linejoin="round"><path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/></svg>
          </button>` : ''}
        </div>
        <div class="sub-row">
          <span class="clase-chip" style="background:${n.tint};color:${n.fg}" title="${esc(claseTxt)}">${esc(claseTxt)}</span>
          <div class="sub-bar"><div class="bar-fill" style="width:${ancho}%;background:${n.fill}"></div></div>
          <span class="sub-aporte">${aporte}</span>
        </div>
      </div>`;
  }).join('') : '<p class="panel-placeholder">Este inmueble no tiene evaluaciones registradas.</p>';

  const scoreCardHtml = noEvaluado ? `
    <div class="score-card">
      <div class="score-top">
        <span class="clase-chip" style="background:${NO_EVALUADO.tint};color:${NO_EVALUADO.fg};font-size:14px;padding:6px 14px;">${NO_EVALUADO.label}</span>
      </div>
      <p class="panel-placeholder">Sin evaluación para ${esc(state.amenazaActiva?.nombre || 'esta amenaza')}.</p>
    </div>
  ` : `
    <div class="score-card">
      <div class="score-top">
        <div class="score-value" style="color:${nivel.fg}">${num(total)}</div>
        <div class="score-side">
          <div class="score-level" style="color:${nivel.fg}">Riesgo ${nivel.label.toLowerCase()}</div>
          <div class="score-range">rango ${nivel.rango} · de ${num(RIESGO_MAX)}</div>
        </div>
      </div>
      <div class="scale">
        <div class="scale-bar">${segs}</div>
        <div class="scale-marker" style="left:${marcador}%"></div>
        <div class="scale-ticks">
          <span>0,00</span><span>1,76</span><span>2,51</span><span>3,26</span><span>4,00</span>
        </div>
      </div>
    </div>
  `;

  document.getElementById('panel-content').innerHTML = `
    ${scoreCardHtml}

    <div class="explica">
      <div class="kicker">Qué explica este puntaje</div>
      <div class="explica-list">${filasHtml}</div>
    </div>

    <div id="edit-form-container-${inmuebleId}"></div>
  `;

  document.getElementById('ficha-foot').hidden = state.role !== 'editor';
  document.getElementById('btn-evaluar-inmueble').hidden = !(state.role === 'editor' && noEvaluado);

  if (state.role === 'editor' && inmuebleId && !noEvaluado) {
    cargarEvaluacionesEnFicha(inmuebleId);
  }

  abrirFicha();
}

// =============================================================================
// EDITOR: cambio de clase por sub-indicador
// =============================================================================

async function cargarEvaluacionesEnFicha(inmuebleId) {
  try {
    // Acotar a la amenaza activa: si no, la ficha mezcla los sub-indicadores de
    // todas las amenazas evaluadas para el inmueble.
    const amenazaId = state.amenazaActiva?.id ?? AMENAZA_POR_DEFECTO;
    const [evRes, clasesRes] = await Promise.all([
      apiFetch(`${API_BASE}/api/evaluacion/inmueble/${inmuebleId}/?amenaza_id=${amenazaId}`),
      apiFetch(`${API_BASE}/api/clases/?amenaza_id=${amenazaId}`)
    ]);
    if (!evRes.ok || !clasesRes.ok) throw new Error('Error cargando evaluaciones');

    const evaluaciones = await evRes.json();
    const todasClases = await clasesRes.json();

    state.evaluacionesActuales = {};
    evaluaciones.forEach(e => {
      state.evaluacionesActuales[e.sub_indicador_nombre] = {
        id: e.id, valor: e.valor, subId: e.id_subindicador
      };
    });

    state.clasesPorSub = {};
    todasClases.forEach(c => {
      (state.clasesPorSub[c.sub_indicador] ||= []).push({ nombre: c.nombre, valor: c.valor });
    });
    Object.values(state.clasesPorSub).forEach(arr => arr.sort((a, b) => a.valor - b.valor));

    document.querySelectorAll('.btn-editar-sub').forEach(btn => {
      btn.addEventListener('click', () => abrirEdicionSub(btn.closest('.sub-card')));
    });
  } catch (e) {
    if (e.message !== 'Session expired') toast('No se pudieron cargar las clases editables.', 'error');
  }
}

function abrirEdicionSub(card) {
  if (!card || card.querySelector('.eval-clase-select')) return;

  const nombre = card.dataset.subnombre;
  const ev = state.evaluacionesActuales[nombre];
  if (!ev) { toast('Este sub-indicador no tiene evaluación registrada.', 'error'); return; }

  const clases = state.clasesPorSub[ev.subId] || [];
  if (!clases.length) { toast('Este sub-indicador no tiene clases definidas.', 'error'); return; }

  const chip = card.querySelector('.clase-chip');
  const options = clases.map(c =>
    `<option value="${c.valor}"${c.valor === ev.valor ? ' selected' : ''}>${esc(c.nombre)}</option>`
  ).join('');

  const select = document.createElement('select');
  select.className = 'eval-clase-select';
  select.innerHTML = options;
  select.setAttribute('aria-label', `Clase de ${nombre}`);

  const msg = document.createElement('span');
  msg.className = 'eval-msg';

  chip.replaceWith(select);
  select.after(msg);
  select.focus();

  select.addEventListener('change', () => guardarEvaluacion(card, ev.id, select, msg));
}

async function guardarEvaluacion(card, evaluacionId, select, msg) {
  const valor = parseInt(select.value, 10);
  if (isNaN(valor)) return;

  select.disabled = true;
  card.classList.add('is-saving');
  card.classList.remove('is-error');
  msg.className = 'eval-msg eval-msg--wait';
  msg.textContent = '…';

  try {
    const res = await apiFetch(`${API_BASE}/api/evaluacion/actualizar/${evaluacionId}/`, {
      method: 'PATCH',
      body: JSON.stringify({ valor })
    });

    if (res.ok) {
      msg.className = 'eval-msg eval-msg--ok';
      msg.textContent = '✓';
      const nombre = card.dataset.subnombre;
      if (state.evaluacionesActuales[nombre]) state.evaluacionesActuales[nombre].valor = valor;
      await actualizarFeatureEnMapa(state.inmuebleSeleccionado?.id);
      setTimeout(() => { msg.textContent = ''; msg.className = 'eval-msg'; }, 3000);
    } else {
      throw new Error('save failed');
    }
  } catch (e) {
    if (e.message !== 'Session expired') {
      card.classList.add('is-error');
      msg.className = 'eval-msg eval-msg--err';
      msg.textContent = '✗';
      toast('No se pudo guardar el cambio. Reintenta.', 'error');
    }
  } finally {
    select.disabled = false;
    card.classList.remove('is-saving');
  }
}

async function actualizarFeatureEnMapa(inmuebleId) {
  if (!inmuebleId) return;
  try {
    const amenazaId = state.amenazaActiva?.id ?? AMENAZA_POR_DEFECTO;
    const res = await fetch(detalleInmuebleUrl(amenazaId, inmuebleId));
    if (!res.ok) throw new Error('feature not found');
    // La función devuelve un FeatureCollection aunque traiga un solo inmueble.
    const geojsonFeature = (await res.json()).features?.[0];
    if (!geojsonFeature) throw new Error('feature not found');

    const existing = geojsonSource.getFeatures().find(f => f.get('id') === inmuebleId);
    if (existing && geojsonFeature.properties) {
      Object.entries(geojsonFeature.properties).forEach(([k, v]) => existing.set(k, v));
      geojsonSource.changed();
      // Refrescar la ficha y los agregados con el dato nuevo
      mostrarFichaInmueble(existing);
      renderizarIndicadores();
      pintarLeyenda();
    }
    geojsonLayer.changed();
  } catch {
    geojsonSource.clear();
    geojsonSource.refresh();
  }
}

// =============================================================================
// EDITOR: formulario de datos del inmueble
// =============================================================================

document.getElementById('btn-editar-inmueble').addEventListener('click', () => {
  const sel = state.inmuebleSeleccionado;
  if (!sel) return;
  const cont = document.getElementById(`edit-form-container-${sel.id}`);
  if (!cont) return;

  if (cont.innerHTML.trim() !== '') { cont.innerHTML = ''; return; }

  const p = sel.props;
  cont.innerHTML = `
    <div class="edit-inmueble-form">
      <h4>Editar datos del inmueble</h4>
      <div class="edit-field">
        <label for="edit-direccion-${sel.id}">Dirección</label>
        <input type="text" id="edit-direccion-${sel.id}" value="${esc(p.direccion || '')}">
      </div>
      <div class="edit-field">
        <label for="edit-region-${sel.id}">Región</label>
        <input type="text" id="edit-region-${sel.id}" value="${esc(p.region || '')}">
      </div>
      <div class="edit-field">
        <label for="edit-manzana-${sel.id}">Manzana</label>
        <input type="text" id="edit-manzana-${sel.id}" value="${esc(p.manzana || '')}">
      </div>
      <div class="edit-field">
        <label for="edit-predio-${sel.id}">Predio</label>
        <input type="text" id="edit-predio-${sel.id}" value="${esc(p.predio || '')}">
      </div>
      <div class="edit-actions">
        <button class="btn btn--primary btn-save" id="btn-guardar-inmueble">Guardar</button>
        <button class="btn btn--ghost" id="btn-cancelar-inmueble">Cancelar</button>
      </div>
      <div id="edit-feedback-${sel.id}" class="edit-feedback"></div>
    </div>
  `;

  document.getElementById('btn-cancelar-inmueble').addEventListener('click', () => { cont.innerHTML = ''; });
  document.getElementById('btn-guardar-inmueble').addEventListener('click', () => guardarEdicionInmueble(sel.id));
  cont.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
});

async function guardarEdicionInmueble(id) {
  const feedback = document.getElementById(`edit-feedback-${id}`);
  const saveBtn = document.getElementById('btn-guardar-inmueble');

  const data = {
    direccion: document.getElementById(`edit-direccion-${id}`)?.value || '',
    region: document.getElementById(`edit-region-${id}`)?.value || '',
    manzana: document.getElementById(`edit-manzana-${id}`)?.value || '',
    predio: document.getElementById(`edit-predio-${id}`)?.value || ''
  };

  saveBtn.disabled = true;
  saveBtn.textContent = 'Guardando…';
  feedback.className = 'edit-feedback';

  try {
    const res = await apiFetch(`${API_BASE}/api/inmuebles/actualizar/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });

    if (res.ok) {
      feedback.className = 'edit-feedback success';
      feedback.textContent = 'Cambios guardados correctamente.';
      toast('Inmueble actualizado.', 'ok');
      await actualizarFeatureEnMapa(id);
    } else {
      const err = await res.json().catch(() => ({}));
      feedback.className = 'edit-feedback error';
      feedback.textContent = Object.values(err).flat().join(' ') || 'No se pudo guardar.';
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
}

// =============================================================================
// EDITOR: administrar clases
// =============================================================================

const clasesModal = document.getElementById('clases-panel');

document.getElementById('btn-administrar-clases').addEventListener('click', abrirPanelClases);
document.getElementById('btn-cerrar-clases').addEventListener('click', cerrarPanelClases);
document.getElementById('clases-backdrop').addEventListener('click', cerrarPanelClases);

function cerrarPanelClases() { clasesModal.hidden = true; }

async function abrirPanelClases() {
  clasesModal.hidden = false;
  const content = document.getElementById('clases-panel-content');
  content.innerHTML = '<p class="panel-placeholder">Cargando clases…</p>';

  try {
    const [clasesRes, subRes] = await Promise.all([
      apiFetch(`${API_BASE}/api/clases/`),
      apiFetch(`${API_BASE}/api/subindicadores/`)
    ]);
    if (!clasesRes.ok || !subRes.ok) throw new Error('Error al cargar datos');

    const clases = await clasesRes.json();
    const subindicadores = await subRes.json();

    const subMap = {};
    subindicadores.forEach(s => { subMap[s.id] = s.nombre; });

    const grouped = {};
    clases.forEach(c => {
      const nombre = subMap[c.sub_indicador] || `Sub-indicador ${c.sub_indicador}`;
      (grouped[nombre] ||= []).push(c);
    });

    const html = Object.entries(grouped).map(([subNombre, items]) => `
      <div class="clase-group">
        <div class="clase-group-title">${esc(subNombre)}</div>
        ${items.map(c => `
          <div class="clase-row">
            <span class="clase-nombre">${esc(c.nombre)}</span>
            <input type="number" class="clase-valor-input" id="clase-val-${c.id}" value="${c.valor}" min="0" max="4" aria-label="Valor de ${esc(c.nombre)}">
            <button class="btn btn--ghost btn-clase-save" data-clase-id="${c.id}">Guardar</button>
            <span class="clase-msg" id="clase-msg-${c.id}"></span>
          </div>
        `).join('')}
      </div>
    `).join('');

    content.innerHTML = html || '<p class="panel-placeholder">No hay clases definidas.</p>';

    content.querySelectorAll('.btn-clase-save').forEach(btn => {
      btn.addEventListener('click', () => guardarClase(Number(btn.dataset.claseId)));
    });
  } catch (e) {
    if (e.message !== 'Session expired') {
      content.innerHTML = '<p class="panel-placeholder">Error al cargar las clases.</p>';
    }
  }
}

async function guardarClase(id) {
  const input = document.getElementById(`clase-val-${id}`);
  const msg = document.getElementById(`clase-msg-${id}`);
  const btn = input?.closest('.clase-row')?.querySelector('.btn-clase-save');
  if (!input) return;

  const valor = parseInt(input.value, 10);
  if (isNaN(valor)) { msg.textContent = '✗'; return; }

  if (btn) btn.disabled = true;
  msg.textContent = '…';

  try {
    const res = await apiFetch(`${API_BASE}/api/clases/actualizar/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify({ valor })
    });
    msg.textContent = res.ok ? '✓' : '✗';
    if (res.ok) toast('Clase actualizada. El recálculo afecta a todos los inmuebles.', 'ok');
  } catch (e) {
    if (e.message !== 'Session expired') msg.textContent = '✗';
  } finally {
    if (btn) btn.disabled = false;
    setTimeout(() => { msg.textContent = ''; }, 3000);
  }
}

// =============================================================================
// EDITOR: nueva evaluación (inmuebles sin evaluar)
// =============================================================================

const evaluarModal = document.getElementById('evaluar-panel');
const evaluarFoot = document.getElementById('evaluar-panel-foot');
const evaluarBtnGuardar = document.getElementById('btn-guardar-evaluacion-lote');
const evaluarFeedback = document.getElementById('evaluar-feedback');

document.getElementById('btn-evaluar-inmueble').addEventListener('click', () => {
  if (state.inmuebleSeleccionado) abrirModalEvaluar(state.inmuebleSeleccionado.id);
});
document.getElementById('btn-cerrar-evaluar').addEventListener('click', cerrarModalEvaluar);
document.getElementById('evaluar-backdrop').addEventListener('click', cerrarModalEvaluar);

function cerrarModalEvaluar() {
  evaluarModal.hidden = true;
  evaluarFoot.hidden = true;
  evaluarBtnGuardar.disabled = true;
  evaluarFeedback.className = 'edit-feedback';
  evaluarFeedback.textContent = '';
}

/** Trae el roster completo de sub-indicadores de la amenaza activa y arma el formulario. */
async function abrirModalEvaluar(inmuebleId) {
  const amenazaId = state.amenazaActiva?.id ?? AMENAZA_POR_DEFECTO;
  const amenazaNombre = state.amenazaActiva?.nombre || '';
  evaluarModal.hidden = false;
  evaluarFoot.hidden = true;
  document.getElementById('evaluar-panel-title').textContent =
    amenazaNombre ? `Evaluar inmueble · ${amenazaNombre}` : 'Evaluar inmueble';
  const content = document.getElementById('evaluar-panel-content');
  content.innerHTML = '<p class="panel-placeholder">Cargando sub-indicadores…</p>';

  try {
    const [indRes, subRes, clasesRes] = await Promise.all([
      apiFetch(`${API_BASE}/api/indicadores/?amenaza_id=${amenazaId}`),
      apiFetch(`${API_BASE}/api/subindicadores/?amenaza_id=${amenazaId}`),
      apiFetch(`${API_BASE}/api/clases/?amenaza_id=${amenazaId}`)
    ]);
    if (!indRes.ok || !subRes.ok || !clasesRes.ok) throw new Error('Error al cargar datos');

    const indicadores = await indRes.json();
    const subindicadores = await subRes.json();
    const clases = await clasesRes.json();

    const clasesPorSub = {};
    clases.forEach(c => { (clasesPorSub[c.sub_indicador] ||= []).push(c); });
    Object.values(clasesPorSub).forEach(arr => arr.sort((a, b) => a.valor - b.valor));

    const subsPorIndicador = {};
    subindicadores.forEach(s => { (subsPorIndicador[s.indicador] ||= []).push(s); });

    const html = indicadores.map(ind => {
      const subs = subsPorIndicador[ind.id] || [];
      if (!subs.length) return '';
      return `
        <div class="clase-group">
          <div class="clase-group-title">${esc(ind.nombre)}</div>
          ${subs.map(s => {
            const opciones = clasesPorSub[s.id] || [];
            return `
              <div class="clase-row">
                <span class="clase-nombre">${esc(s.nombre)}</span>
                <select class="eval-clase-select" data-subindicador-id="${s.id}" aria-label="Clase de ${esc(s.nombre)}">
                  <option value="">Seleccionar…</option>
                  ${opciones.map(c => `<option value="${c.valor}">${esc(c.nombre)}</option>`).join('')}
                </select>
              </div>`;
          }).join('')}
        </div>`;
    }).join('');

    content.innerHTML = html || '<p class="panel-placeholder">Esta amenaza no tiene sub-indicadores definidos.</p>';
    evaluarFoot.hidden = false;

    const selects = content.querySelectorAll('.eval-clase-select');
    const revisarCompletitud = () => {
      evaluarBtnGuardar.disabled = ![...selects].every(s => s.value !== '');
    };
    selects.forEach(s => s.addEventListener('change', revisarCompletitud));
    revisarCompletitud();

    evaluarBtnGuardar.onclick = () => guardarEvaluacionLote(inmuebleId, amenazaId, selects);
  } catch (e) {
    if (e.message !== 'Session expired') {
      content.innerHTML = '<p class="panel-placeholder">Error al cargar los sub-indicadores.</p>';
    }
  }
}

async function guardarEvaluacionLote(inmuebleId, amenazaId, selects) {
  const evaluaciones = [...selects].map(s => ({
    id_subindicador: Number(s.dataset.subindicadorId),
    valor: Number(s.value)
  }));

  evaluarBtnGuardar.disabled = true;
  evaluarBtnGuardar.textContent = 'Guardando…';
  evaluarFeedback.className = 'edit-feedback';

  try {
    const res = await apiFetch(`${API_BASE}/api/evaluacion/inmueble/${inmuebleId}/crear-lote/`, {
      method: 'POST',
      body: JSON.stringify({ amenaza_id: amenazaId, evaluaciones })
    });

    if (res.ok) {
      toast('Evaluación creada.', 'ok');
      cerrarModalEvaluar();
      await actualizarFeatureEnMapa(inmuebleId);
    } else {
      const err = await res.json().catch(() => ({}));
      evaluarFeedback.className = 'edit-feedback error';
      evaluarFeedback.textContent = Object.values(err).flat().join(' ') || 'No se pudo guardar la evaluación.';
      evaluarBtnGuardar.disabled = false;
    }
  } catch (e) {
    if (e.message !== 'Session expired') {
      evaluarFeedback.className = 'edit-feedback error';
      evaluarFeedback.textContent = 'Error de conexión.';
      evaluarBtnGuardar.disabled = false;
    }
  } finally {
    evaluarBtnGuardar.textContent = 'Guardar evaluación';
  }
}

// =============================================================================
// EXPORTACIONES
// =============================================================================

document.getElementById('btn-descargar-kml').addEventListener('click', async () => {
  cerrarMenus();
  toast('Generando KML…');
  try {
    const amenazaId = state.amenazaActiva?.id ?? AMENAZA_POR_DEFECTO;
    const res = await apiFetch(`${API_BASE}/api/crear-kml-detalle/?amenaza_id=${amenazaId}`);
    if (!res.ok) throw new Error('Error al generar KML');
    const nombre = (state.amenazaActiva?.nombre || 'Riesgo').replace(/\s+/g, '_');
    descargarBlob(await res.blob(), `${nombre}_Detalle.kml`);
    toast('KML descargado.', 'ok');
  } catch (e) {
    if (e.message !== 'Session expired') toast('No se pudo generar el archivo KML.', 'error');
  }
});

/** Encola el informe de la amenaza activa, hace polling del estado y lo descarga. */
async function generarInforme() {
  cerrarMenus();
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  toast('Generando informe…');

  try {
    const resGen = await apiFetch(`${API_BASE}/api/generar-pdf-resumen/`, {
      method: 'POST',
      body: JSON.stringify({ amenaza_id: state.amenazaActiva?.id ?? AMENAZA_POR_DEFECTO })
    });
    if (!resGen.ok) throw new Error('Error al iniciar la generación');
    const { task_id } = await resGen.json();

    for (;;) {
      await sleep(1500);
      const resEst = await apiFetch(`${API_BASE}/api/generar-pdf-resumen/estado/${task_id}/`);
      if (!resEst.ok) throw new Error('Error consultando el estado');
      const { estado } = await resEst.json();
      if (estado === 'SUCCESS') break;
      if (estado === 'FAILURE') throw new Error('La generación del PDF falló');
    }

    const resPdf = await apiFetch(`${API_BASE}/api/generar-pdf-resumen/descargar/${task_id}/`);
    if (!resPdf.ok) throw new Error('Error al descargar el PDF');
    // El nombre lleva la amenaza: el informe de Sismo y el de Incendio no
    // deben quedar indistinguibles en la carpeta de descargas.
    const nombre = (state.amenazaActiva?.nombre || 'Riesgo').replace(/\s+/g, '_');
    descargarBlob(await resPdf.blob(), `Informe_${nombre}.pdf`);
    toast('Informe descargado.', 'ok');
  } catch (e) {
    if (e.message !== 'Session expired') toast('No se pudo generar el informe.', 'error');
  }
}

document.getElementById('btn-descargar-pdf').addEventListener('click', generarInforme);

function descargarBlob(blob, nombre) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = nombre;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// =============================================================================
// MENÚS
// =============================================================================

function cerrarMenus() {
  document.getElementById('export-menu').hidden = true;
  document.getElementById('user-menu').hidden = true;
  document.getElementById('btn-export').setAttribute('aria-expanded', 'false');
  document.getElementById('user-chip').setAttribute('aria-expanded', 'false');
}

function alternarMenu(botonId, menuId) {
  const menu = document.getElementById(menuId);
  const abierto = !menu.hidden;
  cerrarMenus();
  if (!abierto) {
    menu.hidden = false;
    document.getElementById(botonId).setAttribute('aria-expanded', 'true');
  }
}

document.getElementById('btn-export').addEventListener('click', e => {
  e.stopPropagation();
  alternarMenu('btn-export', 'export-menu');
});
document.getElementById('user-chip').addEventListener('click', e => {
  e.stopPropagation();
  alternarMenu('user-chip', 'user-menu');
});
document.addEventListener('click', cerrarMenus);
document.querySelectorAll('.menu').forEach(m => m.addEventListener('click', e => e.stopPropagation()));

// =============================================================================
// BÚSQUEDA
// =============================================================================

const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('search-results');

searchInput.addEventListener('input', () => {
  const q = searchInput.value.trim().toLowerCase();
  if (q.length < 2) { searchResults.hidden = true; return; }

  const matches = geojsonSource.getFeatures().filter(f => {
    const p = f.getProperties();
    return [p.direccion, p.rol_sii, p.manzana, p.predio]
      .some(v => String(v ?? '').toLowerCase().includes(q));
  }).slice(0, 20);

  if (!matches.length) {
    searchResults.innerHTML = '<div class="search-empty">Sin resultados.</div>';
    searchResults.hidden = false;
    return;
  }

  searchResults.innerHTML = matches.map((f, i) => {
    const p = f.getProperties();
    const nivel = nivelTotal(riesgoTotalDe(propsDetalle(f)));
    return `<button class="search-item" data-idx="${i}">
              <span class="legend-swatch" style="background:${nivel.fill}"></span>
              <span class="search-item-main">
                <span class="search-item-dir">${esc(p.direccion || 'Sin dirección')}</span>
                <span class="search-item-sub">Rol SII ${esc(p.rol_sii || '—')}${p.manzana ? ` · Mz ${esc(p.manzana)}` : ''}</span>
              </span>
            </button>`;
  }).join('');
  searchResults.hidden = false;

  searchResults.querySelectorAll('.search-item').forEach(btn => {
    btn.addEventListener('click', () => {
      const feature = matches[Number(btn.dataset.idx)];
      irAFeature(feature);
      searchResults.hidden = true;
      searchInput.value = '';
    });
  });
});

searchInput.addEventListener('keydown', e => {
  if (e.key === 'Escape') { searchResults.hidden = true; searchInput.blur(); }
});
document.addEventListener('click', e => {
  if (!e.target.closest('.topbar-search')) searchResults.hidden = true;
});

function irAFeature(feature) {
  const geom = feature.getGeometry();
  if (!geom) return;
  map.getView().fit(geom.getExtent(), { duration: 500, maxZoom: 19, padding: [80, 80, 80, 80] });
  mostrarFichaInmueble(feature);
}

// =============================================================================
// CONTROLES DEL MAPA
// =============================================================================

document.getElementById('btn-zoom-in').addEventListener('click', () => {
  const v = map.getView();
  v.animate({ zoom: v.getZoom() + 1, duration: 220 });
});
document.getElementById('btn-zoom-out').addEventListener('click', () => {
  const v = map.getView();
  v.animate({ zoom: v.getZoom() - 1, duration: 220 });
});
document.getElementById('btn-centrar').addEventListener('click', () => {
  map.getView().animate({ center: VISTA_INICIAL.center, zoom: VISTA_INICIAL.zoom, duration: 400 });
});

document.getElementById('btn-toggle-left').addEventListener('click', togglePanelIzquierdo);
document.getElementById('btn-cerrar-ficha').addEventListener('click', cerrarFicha);

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    if (!evaluarModal.hidden) cerrarModalEvaluar();
    else if (!clasesModal.hidden) cerrarPanelClases();
    else if (!shell.classList.contains('is-right-closed')) cerrarFicha();
  }
});

// =============================================================================
// EVENTOS DEL MAPA
// =============================================================================

map.on('click', function (evt) {
  const feature = map.forEachFeatureAtPixel(evt.pixel, (f, layer) =>
    (layer === geojsonLayer || layer === indicadorLayer) ? f : null
  );
  if (feature) mostrarFichaInmueble(feature);
});

map.on('pointermove', function (evt) {
  const hit = map.hasFeatureAtPixel(map.getEventPixel(evt.originalEvent), {
    layerFilter: l => l !== selectionLayer
  });
  map.getTargetElement().style.cursor = hit ? 'pointer' : '';
});

geojsonSource.on('featuresloadend', function () {
  renderizarIndicadores();
  pintarLeyenda();
});

geojsonSource.on('featuresloaderror', function () {
  toast('No se pudieron cargar los datos del mapa.', 'error');
});

// =============================================================================
// ARRANQUE
// =============================================================================

async function arrancarConsola() {
  shell.classList.add('is-right-closed');
  await cargarAmenazas();
  geojsonSource.refresh();
  actualizarTamanoMapa();
}

async function init() {
  const token = getToken();
  if (token && !isTokenExpired(token)) {
    const payload = decodeToken(token);
    state.role = payload?.role || 'viewer';
    state.username = payload?.username || 'Usuario';
    ocultarLogin();
    pintarUsuario();
    await arrancarConsola();
  } else {
    clearAuth();
    mostrarLogin();
  }
}

init();
