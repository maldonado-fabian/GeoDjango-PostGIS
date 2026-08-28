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


def donut(filas, titulo, *, dpi=None):
    """Dona a partir de filas {nivel, cantidad, porcentaje}.

    Muestra las porciones con cantidad > 0 etiquetadas "Nº; %" y una leyenda con
    todos los niveles, para que dos donas contiguas sean comparables aunque una
    no tenga inmuebles en algún nivel.
    """
    tamanos, colores, etiquetas = [], [], []
    for f in filas:
        if f["cantidad"] > 0:
            tamanos.append(f["cantidad"])
            colores.append(niveles.color(f["nivel"]))
            etiquetas.append(f"{f['cantidad']}; {f['porcentaje']}%")

    fig, ax = plt.subplots(figsize=(4.2, 3.4))
    if tamanos:
        ax.pie(
            tamanos,
            colors=colores,
            startangle=90,
            counterclock=False,
            labels=etiquetas,
            labeldistance=1.15,
            wedgeprops=dict(width=0.42, edgecolor="white", linewidth=1),
            textprops=dict(fontsize=7, color="#333333"),
        )
    else:
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center", fontsize=9)
    ax.set_aspect("equal")
    ax.set_title(titulo, fontsize=8.5, fontweight="bold", pad=10)

    handles = [Patch(facecolor=niveles.color(n), label=n) for n in niveles.NIVELES]
    ax.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=3,
        fontsize=6,
        frameon=False,
        handlelength=1,
        columnspacing=1,
    )
    return _png(fig, dpi or DPI_DONA)


def mapa(gdf_color, titulo, leyenda, *, etiqueta_leyenda=None, dpi=None, basemap=True):
    """Mapa coroplético -> PNG.

    `gdf_color`: GeoDataFrame en EPSG:3857 con columna 'color' (hex) por fila.
    `leyenda`: lista de (etiqueta, color_hex).
    `etiqueta_leyenda`: título del recuadro de leyenda. Antes estaba fijo en
    "INCENDIO", de modo que un informe de Sismo rotulaba así sus veinte mapas.
    """
    fig, ax = plt.subplots(figsize=(5.6, 6.6))
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
    ax.set_title(titulo, fontsize=9, fontweight="bold")
    handles = [Patch(facecolor=c, edgecolor="black", label=l) for l, c in leyenda]
    ax.legend(
        handles=handles,
        loc="lower left",
        fontsize=6,
        frameon=True,
        title=etiqueta_leyenda,
    )
    return _png(fig, dpi or DPI_MAPA)
