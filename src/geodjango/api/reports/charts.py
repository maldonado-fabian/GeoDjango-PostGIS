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


def barras_aporte(df, titulo, *, dpi=None, max_filas=None):
    """Aporte de cada sub-indicador al índice, coloreado por clasificación.

    Es el gráfico que se lee de un vistazo; la dispersión de más abajo es su
    justificación. `df` viene de `analytics.diagnostico`.
    """
    from .analytics import SISTEMICO, DIFERENCIADOR, SECUNDARIO

    datos = df.head(max_filas) if max_filas else df
    datos = datos.iloc[::-1]  # barh dibuja de abajo hacia arriba

    color_clase = {
        SISTEMICO: '#2f6f8f',
        DIFERENCIADOR: '#cc5200',
        SECUNDARIO: '#7d8285',
    }
    colores = [color_clase.get(c, '#c7cbcc') for c in datos['clasificacion']]

    alto = max(2.6, 0.26 * len(datos) + 0.9)
    fig, ax = plt.subplots(figsize=(7.2, alto))
    ax.barh(datos['subindicador_nombre'], datos['aporte_pct'], color=colores, height=0.68)

    for y, (pct, medio) in enumerate(zip(datos['aporte_pct'], datos['valor_medio'])):
        ax.text(pct + 0.15, y, f'{pct:.1f}%  (media {medio:.2f})'.replace('.', ','),
                va='center', fontsize=6.5, color='#5b5f60')

    ax.set_xlabel('Aporte al índice de riesgo', fontsize=7)
    ax.set_xlim(0, datos['aporte_pct'].max() * 1.38)
    ax.tick_params(axis='y', labelsize=7)
    ax.tick_params(axis='x', labelsize=6.5)
    ax.set_title(titulo, fontsize=8.5, fontweight='bold', pad=8)
    for lado in ('top', 'right'):
        ax.spines[lado].set_visible(False)

    handles = [Patch(facecolor=c, label=k) for k, c in color_clase.items()]
    ax.legend(handles=handles, loc='lower right', fontsize=6.5, frameon=False)
    return _png(fig, dpi or DPI_DONA)


def dispersion_aporte_correlacion(df, titulo, *, umbral_correlacion=0.40, dpi=None):
    """Aporte frente a capacidad de discriminar, con cuadrantes.

    Cada punto es un sub-indicador, numerado según su fila en la tabla que
    acompaña la figura: veinte nombres sobre la dispersión son ilegibles.

    Los sub-indicadores sin variación (todos los inmuebles con el mismo puntaje)
    se marcan aparte: su correlación es cero por construcción, y ese es el
    hallazgo sistémico más fuerte que puede producir el análisis.
    """
    fig, ax = plt.subplots(figsize=(6.6, 4.4))

    corte_aporte = df.attrs.get('corte_aporte', df['aporte_pct'].median())
    ax.axvline(umbral_correlacion, color='#98a0a3', lw=0.8, ls='--')
    ax.axhline(corte_aporte, color='#98a0a3', lw=0.8, ls='--')

    x_max = max(df['correlacion'].abs().max() * 1.25, umbral_correlacion * 1.8, 0.7)
    y_max = df['aporte_pct'].max() * 1.22

    ax.text(umbral_correlacion / 2, y_max * 0.97, 'SISTÉMICO', fontsize=7,
            fontweight='bold', color='#2f6f8f', ha='center', va='top')
    ax.text((umbral_correlacion + x_max) / 2, y_max * 0.97, 'DIFERENCIADOR', fontsize=7,
            fontweight='bold', color='#cc5200', ha='center', va='top')

    constantes = df['sin_variacion']
    ax.scatter(df.loc[~constantes, 'correlacion'], df.loc[~constantes, 'aporte_pct'],
               s=46, color='#2f6f8f', alpha=0.80, zorder=3, edgecolor='white', linewidth=0.6)
    if constantes.any():
        ax.scatter(df.loc[constantes, 'correlacion'], df.loc[constantes, 'aporte_pct'],
                   s=70, marker='D', color='#c20000', alpha=0.85, zorder=4,
                   edgecolor='white', linewidth=0.6, label='sin variación entre inmuebles')
        ax.legend(loc='lower right', fontsize=6.5, frameon=False)

    for n, (_, fila) in enumerate(df.iterrows(), start=1):
        ax.annotate(str(n), (fila['correlacion'], fila['aporte_pct']),
                    fontsize=6, color='#1c1c1a', zorder=5,
                    xytext=(5, 3), textcoords='offset points')

    ax.set_xlim(min(0, df['correlacion'].min() * 1.2), x_max)
    ax.set_ylim(0, y_max)
    ax.set_xlabel('Correlación con el resto del índice  →  discrimina entre inmuebles', fontsize=7)
    ax.set_ylabel('Aporte al índice (%)', fontsize=7)
    ax.tick_params(labelsize=6.5)
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


def matriz_cruzada(matriz, nombre_x, nombre_y, titulo, *, dpi=None):
    """Contingencia entre los niveles de dos amenazas.

    Escala de grises a propósito: pintar un conteo con la paleta de riesgo lo
    haría leer como un mapa de riesgo y engañaría.
    """
    fig, ax = plt.subplots(figsize=(4.6, 4.0))
    valores = matriz.values
    ax.imshow(valores, cmap='Blues', aspect='auto')

    total = valores.sum() or 1
    umbral = valores.max() * 0.6 if valores.max() else 1
    for i in range(valores.shape[0]):
        for j in range(valores.shape[1]):
            n = valores[i, j]
            ax.text(j, i, f'{n}\n{n / total * 100:.0f}%'.replace('.', ','),
                    ha='center', va='center', fontsize=6.5,
                    color='white' if n > umbral else '#1c1c1a')

    ax.set_xticks(range(len(matriz.columns)))
    ax.set_xticklabels(matriz.columns, fontsize=6.5, rotation=30, ha='right')
    ax.set_yticks(range(len(matriz.index)))
    ax.set_yticklabels(matriz.index, fontsize=6.5)
    ax.set_xlabel(nombre_x, fontsize=7)
    ax.set_ylabel(nombre_y, fontsize=7)
    ax.set_title(titulo, fontsize=8.5, fontweight='bold', pad=8)
    return _png(fig, dpi or DPI_DONA)


def dispersion_amenazas(df, nombre_x, nombre_y, titulo, *, dpi=None):
    """Índice de una amenaza frente al de otra, con el cuadrante crítico marcado."""
    from api import riesgo

    datos = df[df['indice_a'].notna() & df['indice_b'].notna()]
    corte = riesgo.ALTO.minimo

    fig, ax = plt.subplots(figsize=(4.8, 4.2))
    ax.axvspan(corte, riesgo.ESCALA_MAX, ymin=0, ymax=1, color='#ffe5e5', alpha=0.55, zorder=0)
    ax.axhspan(corte, riesgo.ESCALA_MAX, xmin=0, xmax=1, color='#ffe5e5', alpha=0.55, zorder=0)

    for valor in (riesgo.MEDIO.minimo, riesgo.ALTO.minimo, riesgo.MUY_ALTO.minimo):
        ax.axvline(valor, color='#c7cbcc', lw=0.7, zorder=1)
        ax.axhline(valor, color='#c7cbcc', lw=0.7, zorder=1)

    ax.scatter(datos['indice_a'], datos['indice_b'], s=16, alpha=0.55,
               color='#2f6f8f', edgecolor='none', zorder=3)

    r = df.attrs.get('correlacion', float('nan'))
    n_ambas = df.attrs.get('n_altos_en_ambas', 0)
    ax.set_title(titulo, fontsize=8.5, fontweight='bold', pad=8)
    ax.text(0.03, 0.97, f'r = {r:.3f}'.replace('.', ',') + f'\n{n_ambas} inmuebles altos en ambas',
            transform=ax.transAxes, fontsize=6.5, va='top', color='#5b5f60')

    ax.set_xlim(riesgo.ESCALA_MIN, riesgo.ESCALA_MAX)
    ax.set_ylim(riesgo.ESCALA_MIN, riesgo.ESCALA_MAX)
    ax.set_xlabel(f'Índice {nombre_x.lower()}', fontsize=7)
    ax.set_ylabel(f'Índice {nombre_y.lower()}', fontsize=7)
    ax.tick_params(labelsize=6.5)
    for lado in ('top', 'right'):
        ax.spines[lado].set_visible(False)
    return _png(fig, dpi or DPI_DONA)


def barras_manzanas(df, titulo, *, n=10, dpi=None):
    """Manzanas con mayor proporción de inmuebles en Alto o Muy Alto.

    Anota el número de inmuebles evaluados en cada barra: una manzana con 6 de 6
    no debe leerse igual que una con 6 de 40.
    """
    datos = df.head(n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(6.4, max(2.4, 0.34 * len(datos) + 0.8)))

    colores = [niveles.color(n_) for n_ in datos['nivel_medio']]
    ax.barh(datos['manzana'].astype(str), datos['pct_alto_mas'],
            color=colores, edgecolor='#5b5f60', linewidth=0.4, height=0.66)

    for y, (pct, n_ev, medio) in enumerate(
            zip(datos['pct_alto_mas'], datos['n_evaluados'], datos['indice_medio'])):
        ax.text(pct + 1.2, y,
                f'{pct:.0f}%  ({n_ev} inm., índice {medio:.2f})'.replace('.', ','),
                va='center', fontsize=6.5, color='#5b5f60')

    ax.set_xlim(0, 128)
    ax.set_xlabel('% de inmuebles en riesgo alto o muy alto', fontsize=7)
    ax.set_ylabel('Manzana', fontsize=7)
    ax.tick_params(labelsize=6.5)
    ax.set_title(titulo, fontsize=8.5, fontweight='bold', pad=8)
    for lado in ('top', 'right'):
        ax.spines[lado].set_visible(False)
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
