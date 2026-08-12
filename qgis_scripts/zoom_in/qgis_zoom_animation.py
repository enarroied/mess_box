"""
QGIS 3.44 - Smooth 2D zoom-in animation frame renderer (center-point + zoom levels).

Run this from the QGIS Python Console's script editor:
  Plugins > Python Console > "Show Editor" button > open this file > Run script.

Renders each frame offscreen with QgsMapRendererCustomPainterJob, independent
of your visible canvas. Zoom is expressed the same way Google Maps / OSM /
XYZ tile services express it: a "zoom level" where each +1 halves the
ground distance shown per pixel. You only need to set the center point and,
optionally, tweak the zoom range - sensible defaults are provided.

After running, combine the frames into a video with ffmpeg (command is
printed at the end).
"""

import os

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsMapRendererCustomPainterJob,
    QgsMapSettings,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
)
from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtGui import QImage, QPainter

# --------------------------------------------------------------------------
# CONFIGURE THIS - the only thing you MUST set
# --------------------------------------------------------------------------

# Center point of the zoom, in plain longitude/latitude (EPSG:4326 - WGS84),
# i.e. the numbers you'd copy out of Google Maps or "Copy coordinates".
CENTER_LON = 1.849704
CENTER_LAT = 42.934394

# --------------------------------------------------------------------------
# DEFAULTS - override if you want, otherwise leave as-is
# --------------------------------------------------------------------------

# Zoom levels: 0 = whole world, ~18-20 = building level.
# Satellite basemaps are usually crisp up to about 18-19.
ZOOM_START = 2
ZOOM_END = 12

# Output video frame size (pixels).
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080

# Animation length.
FPS = 30
DURATION_SECONDS = 6
NUM_FRAMES = FPS * DURATION_SECONDS

# Where frames get written.
OUTPUT_DIR = os.path.expanduser("~/qgis_zoom_frames")

# Background colour behind transparent areas (irrelevant if a basemap
# layer covers the whole extent, which it should).
BACKGROUND_COLOR = Qt.white

# Meters/pixel at zoom 0 for 256px tiles - the standard XYZ/slippy-map
# convention (Google Maps, OSM, Esri, Mapbox, etc. all use this).
WEB_MERCATOR_INITIAL_RESOLUTION = 156543.03392804097

# --------------------------------------------------------------------------
# EASING - controls the *feel* of the zoom (Google Maps style: slow start,
# fast middle, slow settle). Change or remove if you want linear zoom.
# --------------------------------------------------------------------------


def ease_in_out_cubic(t: float) -> float:
    if t < 0.5:
        return 4 * t**3
    return 1 - pow(-2 * t + 2, 3) / 2


def zoom_to_resolution(zoom: float) -> float:
    return WEB_MERCATOR_INITIAL_RESOLUTION / (2**zoom)


def extent_for_zoom(
    center: QgsPointXY, zoom: float, out_width_px: int, out_height_px: int
) -> QgsRectangle:
    resolution = zoom_to_resolution(zoom)
    half_w = (out_width_px * resolution) / 2
    half_h = (out_height_px * resolution) / 2
    return QgsRectangle(
        center.x() - half_w,
        center.y() - half_h,
        center.x() + half_w,
        center.y() + half_h,
    )


def render_frame(extent: QgsRectangle, layers, crs, out_path: str) -> None:
    settings = QgsMapSettings()
    settings.setLayers(layers)
    settings.setBackgroundColor(BACKGROUND_COLOR)
    settings.setOutputSize(QSize(OUTPUT_WIDTH, OUTPUT_HEIGHT))
    settings.setExtent(extent)
    settings.setDestinationCrs(crs)

    image = QImage(QSize(OUTPUT_WIDTH, OUTPUT_HEIGHT), QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    job = QgsMapRendererCustomPainterJob(settings, painter)
    job.start()
    job.waitForFinished()
    painter.end()

    image.save(out_path)


def main() -> None:
    project = QgsProject.instance()

    # FIX: Get ONLY visible layers in exact Layers Panel drawing order (Top to Bottom)
    root = project.layerTreeRoot()
    layers = [
        node.layer()
        for node in root.findLayers()
        if node.isVisible() and node.layer() is not None
    ]

    if not layers:
        raise RuntimeError(
            "No visible layers loaded in the project - nothing to render."
        )

    crs = project.crs()
    if crs.authid() != "EPSG:3857":
        print(
            f"Warning: project CRS is {crs.authid()}, not EPSG:3857. "
            "Zoom-level math assumes Web Mercator meters - results may look off."
        )

    # Convert your lon/lat center into the project's CRS.
    src_crs = QgsCoordinateReferenceSystem("EPSG:4326")
    transform = QgsCoordinateTransform(src_crs, crs, project)
    center_point = transform.transform(QgsPointXY(CENTER_LON, CENTER_LAT))

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for i in range(NUM_FRAMES):
        t = i / (NUM_FRAMES - 1) if NUM_FRAMES > 1 else 1.0
        eased = ease_in_out_cubic(t)
        zoom = ZOOM_START + (ZOOM_END - ZOOM_START) * eased

        extent = extent_for_zoom(center_point, zoom, OUTPUT_WIDTH, OUTPUT_HEIGHT)
        out_path = os.path.join(OUTPUT_DIR, f"frame_{i:04d}.png")
        render_frame(extent, layers, crs, out_path)

    print(f"Done. {NUM_FRAMES} frames written to {OUTPUT_DIR}")


main()
