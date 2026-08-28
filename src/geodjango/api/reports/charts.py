"""Gráficos del informe: donas y mapas coloreados -> PNG (bytes).

Usa el backend 'Agg' (sin display). Los colores salen siempre de
`api/riesgo.py` a través de `niveles`, nunca escritos a mano aquí.

Todas las figuras devuelven bytes PNG y cierran su figura de matplotlib.
"""

import logging
from io import BytesIO

import matplotlib

matplotlib.use("Agg")  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from . import niveles

log = logging.getLogger(__name__)


# DPI por defecto. El informe embebe los PNG a resolución nativa, así que bajar
# esto reduce el peso del documento casi proporcionalmente.
DPI_MAPA = 110
DPI_DONA = 100

# Todos los mapas del informe cubren la misma extensión, así que las teselas del
# mapa base se descargan una vez y se reutilizan. Antes se pedían de nuevo en
# cada figura: más de veinte descargas por informe.
_BASEMAP_CACHE = {}

#: Se pone en True si alguna descarga del mapa base falló, para que el documento
#: pueda advertirlo en vez de mostrar veinte rectángulos grises sin explicación.
basemap_degradado = False


def limpiar_cache():
    """Vacía la caché de teselas. Llamar al terminar un informe.

    La caché es estado de módulo y el worker de Celery es de larga vida: sin
    esto, un informe sobre otra extensión reutilizaría las teselas equivocadas.
    """
    global basemap_degradado
    _BASEMAP_CACHE.clear()
    basemap_degradado = False


def _png(fig, dpi=None):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white", dpi=dpi)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _dibujar_basemap(ax, crs):
    """Pinta el mapa base bajo los polígonos, reutilizando teselas si ya se pidieron."""
    global basemap_degradado
    try:
        import contextily as cx
    except ImportError:
        log.warning("contextily no está instalado; los mapas quedan sin mapa base")
        basemap_degradado = True
        ax.set_facecolor("#f2f2f2")
        return

    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    # Redondear a 100 m evita que diferencias de milímetros entre figuras
    # generen entradas distintas para la misma extensión.
    clave = (round(xlim[0], -2), round(ylim[0], -2), round(xlim[1], -2), round(ylim[1], -2))

    if clave not in _BASEMAP_CACHE:
        try:
            imagen, extension = cx.bounds2img(
                xlim[0], ylim[0], xlim[1], ylim[1],
                source=cx.providers.CartoDB.Positron,
                ll=False,
            )
            _BASEMAP_CACHE[clave] = (imagen, extension)
        except Exception:
            # No se silencia: sin mapa base el informe sigue siendo válido, pero
            # el lector tiene que saber por qué los mapas salen sobre gris.
            log.warning("No se pudo descargar el mapa base", exc_info=True)
            basemap_degradado = True
            _BASEMAP_CACHE[clave] = None

    tesela = _BASEMAP_CACHE[clave]
    if tesela is None:
        ax.set_facecolor("#f2f2f2")
        return

    imagen, extension = tesela
    ax.imshow(imagen, extent=extension, interpolation="bilinear", zorder=0)
    # imshow reencuadra: se restauran los límites que fijaron los polígonos.
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)


def donut(filas, titulo, *, dpi=None, compacto=False, sin_titulo=False):
    """Dona a partir de filas {nivel, cantidad, porcentaje}.

    Muestra las porciones con cantidad > 0 etiquetadas "Nº; %" y una leyenda con
    todos los niveles, para que dos donas contiguas sean comparables aunque una
    no tenga inmuebles en algún nivel.

    `compacto` reduce tamaño y tipografía para los bloques de media página.
    """
    tamanos, colores, etiquetas = [], [], []
    for f in filas:
        if f["cantidad"] > 0:
            tamanos.append(f["cantidad"])
            colores.append(niveles.color(f["nivel"]))
            etiquetas.append(f"{f['cantidad']}; {f['porcentaje']}%")

    escala = 0.82 if compacto else 1.0
    fig, ax = plt.subplots(figsize=(3.2, 2.9) if compacto else (4.2, 3.4))
    if tamanos:
        ax.pie(
            tamanos,
            colors=colores,
            startangle=90,
            counterclock=False,
            labels=etiquetas,
            labeldistance=1.16,
            wedgeprops=dict(width=0.42, edgecolor="white", linewidth=1),
            textprops=dict(fontsize=7 * escala, color="#333333"),
        )
    else:
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center", fontsize=9)
    ax.set_aspect("equal")
    if not sin_titulo:
        ax.set_title(titulo, fontsize=8.5 * escala, fontweight="bold", pad=10)

    handles = [Patch(facecolor=niveles.color(n), label=n) for n in niveles.NIVELES]
    ax.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=3 if not compacto else 2,
        fontsize=6 * escala,
        frameon=False,
        handlelength=1,
        columnspacing=1,
    )
    return _png(fig, dpi or DPI_DONA)


def barras_aporte(df, titulo, *, dpi=None):
    """Cuánto aporta cada factor al índice de riesgo, de mayor a menor.

    `df` viene de `analytics.aporte_por_factor`: columnas factor_nombre,
    valor_medio, aporte_pct. Barras de un solo color, ordenadas por aporte.
    """
    datos = df.iloc[::-1]  # barh dibuja de abajo hacia arriba

    alto = max(2.4, 0.32 * len(datos) + 0.8)
    fig, ax = plt.subplots(figsize=(6.6, alto))
    ax.barh(datos['factor_nombre'], datos['aporte_pct'], color='#2f6f8f', height=0.62)

    for y, (pct, medio) in enumerate(zip(datos['aporte_pct'], datos['valor_medio'])):
        ax.text(pct + 0.15, y, f'{pct:.0f}%  (promedio {medio:.2f})'.replace('.', ','),
                va='center', fontsize=6.5, color='#5b5f60')

    ax.set_xlabel('Aporte al índice de riesgo', fontsize=7)
    ax.set_xlim(0, datos['aporte_pct'].max() * 1.42)
    ax.tick_params(axis='y', labelsize=7)
    ax.tick_params(axis='x', labelsize=6.5)
    ax.set_title(titulo, fontsize=8.5, fontweight='bold', pad=8)
    for lado in ('top', 'right'):
        ax.spines[lado].set_visible(False)
    return _png(fig, dpi or DPI_DONA)


def distribucion_indice(series_por_amenaza, titulo, *, dpi=None):
    """Histograma del índice con las bandas de nivel al fondo.

    Hace legible lo que hoy el informe resume en un solo número: dónde se
    concentran los inmuebles y cuánto se dispersan.
    """
    from api import riesgo

    fig, ax = plt.subplots(figsize=(7.0, 3.2))

    for nivel in riesgo.NIVELES_ASC:
        ax.axvspan(nivel.minimo, riesgo.techo(nivel), color=nivel.color, alpha=0.13, zorder=0)

    colores_linea = ['#1c1c1a', '#2f6f8f', '#56727f']
    for i, (nombre, serie) in enumerate(series_por_amenaza.items()):
        ax.hist(serie, bins=24, range=(riesgo.ESCALA_MIN, riesgo.ESCALA_MAX),
                histtype='step', linewidth=1.6, zorder=3,
                color=colores_linea[i % len(colores_linea)],
                label=f'{nombre} (mediana {serie.median():.2f})'.replace('.', ','))
        ax.axvline(serie.median(), color=colores_linea[i % len(colores_linea)],
                   lw=0.9, ls=':', zorder=4)

    ax.set_xlim(riesgo.ESCALA_MIN, riesgo.ESCALA_MAX)
    ax.set_xlabel('Índice de riesgo', fontsize=7)
    ax.set_ylabel('Nº de inmuebles', fontsize=7)
    ax.tick_params(labelsize=6.5)
    ax.set_title(titulo, fontsize=8.5, fontweight='bold', pad=8)
    ax.legend(fontsize=6.5, frameon=False)
    for lado in ('top', 'right'):
        ax.spines[lado].set_visible(False)
    return _png(fig, dpi or DPI_DONA)


#: Proporciones del mapa. La compacta es más ancha que alta para que el bloque
#: entero quepa en media página y dos figuras compartan hoja.
FIGSIZE_MAPA = (5.6, 6.6)
FIGSIZE_MAPA_COMPACTO = (4.4, 3.9)


def mapa(gdf_color, titulo, leyenda, *, etiqueta_leyenda=None, dpi=None, basemap=True,
         compacto=False, sin_titulo=False):
    """Mapa coroplético -> PNG.

    `gdf_color`: GeoDataFrame en EPSG:3857 con columna 'color' (hex) por fila.
    `leyenda`: lista de (etiqueta, color_hex).
    `etiqueta_leyenda`: título del recuadro de leyenda. Antes estaba fijo en
    "INCENDIO", de modo que un informe de Sismo rotulaba así sus veinte mapas.
    `compacto`: proporción y tipografía reducidas, para dos figuras por página.
    """
    escala = 0.78 if compacto else 1.0
    fig, ax = plt.subplots(figsize=FIGSIZE_MAPA_COMPACTO if compacto else FIGSIZE_MAPA)
    gdf_color.plot(
        ax=ax,
        color=gdf_color["color"],
        edgecolor="black",
        linewidth=0.4,
        alpha=0.85,
        zorder=2,
    )
    if basemap:
        _dibujar_basemap(ax, gdf_color.crs)
    else:
        ax.set_facecolor("#f2f2f2")

    ax.set_axis_off()
    # En modo compacto el título lo pone el documento, no la figura: así el
    # bloque de media página no gasta alto en repetirlo.
    if not sin_titulo:
        ax.set_title(titulo, fontsize=9 * escala, fontweight="bold")

    handles = [Patch(facecolor=c, edgecolor="black", label=l) for l, c in leyenda]
    leyenda_ax = ax.legend(
        handles=handles,
        loc="lower left",
        fontsize=6 * escala,
        frameon=True,
        title=etiqueta_leyenda,
        borderpad=0.4,
        labelspacing=0.3,
    )
    if leyenda_ax.get_title():
        leyenda_ax.get_title().set_fontsize(6 * escala)
    return _png(fig, dpi or DPI_MAPA)
