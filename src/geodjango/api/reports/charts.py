"""Gráficos del reporte: donas y mapas coloreados -> PNG (bytes).

Usa el backend 'Agg' (sin display). Las donas replican GraficoRiesgo.tsx y los
mapas replican Mapa.tsx (basemap CARTO Positron + polígonos por nivel).
"""

from io import BytesIO

import matplotlib

matplotlib.use("Agg")  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from . import niveles


def _png(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def donut(filas, titulo):
    """Gráfico de dona a partir de filas {nivel, cantidad, porcentaje}.

    Muestra las porciones con cantidad > 0 etiquetadas "Nº; %" y una leyenda
    con todos los niveles, igual que el frontend.
    """
    sizes, cols, labels = [], [], []
    for f in filas:
        if f["cantidad"] > 0:
            sizes.append(f["cantidad"])
            cols.append(niveles.color(f["nivel"]))
            labels.append(f"{f['cantidad']}; {f['porcentaje']}%")

    fig, ax = plt.subplots(figsize=(4.2, 3.4), dpi=150)
    if sizes:
        ax.pie(
            sizes,
            colors=cols,
            startangle=90,
            counterclock=False,
            labels=labels,
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
    return _png(fig)


def mapa(gdf_color, titulo, leyenda):
    """Mapa coroplético -> PNG.

    `gdf_color`: GeoDataFrame en EPSG:3857 con columna 'color' (hex) por fila.
    `leyenda`: lista de (etiqueta, color_hex) para la leyenda.
    El basemap (CARTO Positron) se intenta cargar; si no hay red, se omite.
    """
    fig, ax = plt.subplots(figsize=(5.6, 6.6), dpi=150)
    gdf_color.plot(
        ax=ax,
        color=gdf_color["color"],
        edgecolor="black",
        linewidth=0.4,
        alpha=0.85,
    )
    try:
        import contextily as cx

        cx.add_basemap(
            ax,
            source=cx.providers.CartoDB.Positron,
            crs=gdf_color.crs.to_string(),
            attribution_size=4,
        )
    except Exception:
        ax.set_facecolor("#f2f2f2")

    ax.set_axis_off()
    ax.set_title(titulo, fontsize=9, fontweight="bold")
    handles = [Patch(facecolor=c, edgecolor="black", label=l) for l, c in leyenda]
    ax.legend(handles=handles, loc="lower left", fontsize=6, frameon=True, title="INCENDIO")
    return _png(fig)
