import math
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QBrush, QPixmap, QImage, QPainterPath, 
    QRadialGradient, QLinearGradient
)
from ..config.themes import WAVE_THEMES, DEFAULT_WAVE_THEME, get_wave_palette

class FluidMeshGradient:
    """
    Samsung One UI 'SoundAssistant' Flex Volume Multi-Blob Dynamic Cloud Engine:
    - Dynamic Curated Color Palettes (Twilight Mauve, Nordic Frost, Neon Sunset, Forest Mist, Pastel Pop, Deep Ocean).
    - 8 Independent dynamic radial emitters mapped adaptively to the 4-color palette.
    - Asynchronous multi-frequency harmonic trajectories & swirling orbital mechanics.
    - Independent dynamic radius pulsing between 140px and 360px.
    - 4-Stop soft exponential alpha diffusion (Center ~0.20-0.28, Mid ~0.12, Edge ~0.03, Boundary 0.0).
    - Additive Screen Blend mode creating luminous, evolving cloud volumes without gray banding.
    - Frosted halftone micro-dot grid overlay with vertical alpha feathering.
    - Lower ~20-25% screen anchor envelope.
    """
    def __init__(self, theme_name: str = DEFAULT_WAVE_THEME):
        self._dot_tile = None
        self._init_halftone_tile()
        self._theme_name = theme_name
        self._palette = [QColor(c) for c in get_wave_palette(theme_name)]

    def set_theme(self, theme_name: str):
        """Sets the active wave color palette theme dynamically."""
        self._theme_name = theme_name
        self._palette = [QColor(c) for c in get_wave_palette(theme_name)]

    def _init_halftone_tile(self):
        """Pre-renders a tileable 6x6 pixel-perfect micro-dot raster tile."""
        tile_size = 6
        img = QImage(tile_size, tile_size, QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)

        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # Crisp 1.2px circular dot with rgba(255, 255, 255, 0.14)
        dot_color = QColor(255, 255, 255, 36)
        p.setBrush(QBrush(dot_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(tile_size / 2.0, tile_size / 2.0), 0.65, 0.65)
        p.end()

        self._dot_tile = QPixmap.fromImage(img)

    def draw(self, painter: QPainter, width: int, height: int, phase: float, theme_name: str = None):
        """
        Renders the multi-blob evolving fluid cloud simulation and micro-dot mesh raster.
        Operates in <4ms frame time on standard CPU rasterization.
        """
        if width <= 0 or height <= 0:
            return

        if theme_name and theme_name != self._theme_name:
            self.set_theme(theme_name)

        palette = self._palette
        c0, c1, c2, c3 = palette[0], palette[1], palette[2], palette[3]

        w = float(width)
        h = float(height)

        # Natural sloping lower envelope (250px bottom-left to 60px bottom-right)
        y_start = h - 250.0
        y_end = h - 60.0

        # Offscreen render bounds strictly confined to the lower envelope
        glow_top = max(0.0, y_start - 180.0)
        glow_height = int(h - glow_top)
        if glow_height <= 0:
            return

        theta = phase * 2.0 * math.pi

        # 8 Dynamic Radial Emitters with Asynchronous Swirl & Breathing Oscillations
        # Mapped to 4 Palette Swatches:
        # c0 (Highlight): Emitters 0, 2
        # c1 (Mid-tone): Emitters 1, 3, 5
        # c2 (Shadow/Atmosphere): Emitters 4, 6
        # c3 (Deep Anchor): Emitter 7
        blobs = [
            # 1. Color 0 (Highlight) - Clockwise elliptical swirl
            {
                "t": 0.12,
                "color": c0,
                "alpha_peak": 66,  # ~0.26
                "dx": 85.0 * math.sin(1.1 * theta + 0.3) + 30.0 * math.cos(0.5 * theta + 1.2),
                "dy": 35.0 * math.cos(1.1 * theta + 0.3) + 15.0 * math.sin(0.7 * theta + 2.0),
                "radius": max(140.0, min(360.0, w * 0.22 + 40.0 * math.sin(0.75 * theta + 0.4)))
            },
            # 2. Color 1 (Mid-tone) - Counter-clockwise vortex loop
            {
                "t": 0.24,
                "color": c1,
                "alpha_peak": 68,  # ~0.27
                "dx": 75.0 * math.cos(0.95 * theta + 1.8) - 25.0 * math.sin(1.4 * theta + 0.5),
                "dy": -40.0 * math.sin(0.95 * theta + 1.8) + 20.0 * math.cos(0.6 * theta + 2.5),
                "radius": max(150.0, min(360.0, w * 0.26 + 45.0 * math.sin(0.65 * theta + 1.8)))
            },
            # 3. Color 0 (Highlight) - High-frequency breathing cross-drift
            {
                "t": 0.38,
                "color": c0,
                "alpha_peak": 64,  # ~0.25
                "dx": 95.0 * math.sin(0.8 * theta + 3.1) + 40.0 * math.cos(1.3 * theta + 1.0),
                "dy": 42.0 * math.cos(1.2 * theta + 0.8) + 18.0 * math.sin(0.4 * theta + 3.4),
                "radius": max(140.0, min(350.0, w * 0.24 + 48.0 * math.sin(0.9 * theta + 2.1)))
            },
            # 4. Color 1 (Mid-tone) - Figure-8 Lissajous center cloud body
            {
                "t": 0.52,
                "color": c1,
                "alpha_peak": 72,  # ~0.28
                "dx": 100.0 * math.sin(0.7 * theta + 0.9),
                "dy": 48.0 * math.sin(1.4 * theta + 1.8),
                "radius": max(160.0, min(360.0, w * 0.28 + 52.0 * math.sin(0.85 * theta + 0.7)))
            },
            # 5. Color 2 (Shadow/Atmosphere) - Vertical surging atmospheric billow
            {
                "t": 0.65,
                "color": c2,
                "alpha_peak": 68,  # ~0.27
                "dx": 70.0 * math.cos(1.05 * theta + 2.4) + 30.0 * math.sin(0.6 * theta + 0.2),
                "dy": 52.0 * math.sin(0.85 * theta + 2.7) + 22.0 * math.cos(1.1 * theta + 1.5),
                "radius": max(150.0, min(350.0, w * 0.27 + 44.0 * math.sin(0.7 * theta + 3.0)))
            },
            # 6. Color 1 (Mid-tone) - Clockwise wandering swell
            {
                "t": 0.78,
                "color": c1,
                "alpha_peak": 66,  # ~0.26
                "dx": 80.0 * math.sin(0.9 * theta + 4.2) + 35.0 * math.cos(0.75 * theta + 2.1),
                "dy": 38.0 * math.cos(0.9 * theta + 4.2) + 16.0 * math.sin(0.5 * theta + 0.9),
                "radius": max(140.0, min(340.0, w * 0.25 + 40.0 * math.sin(0.8 * theta + 1.6)))
            },
            # 7. Color 2 (Shadow/Atmosphere) - Counter-phase deep atmospheric wave
            {
                "t": 0.88,
                "color": c2,
                "alpha_peak": 70,  # ~0.27
                "dx": 65.0 * math.cos(1.15 * theta + 1.5) - 25.0 * math.sin(0.5 * theta + 3.8),
                "dy": 35.0 * math.sin(1.15 * theta + 1.5) + 15.0 * math.cos(0.8 * theta + 1.1),
                "radius": max(140.0, min(320.0, w * 0.23 + 36.0 * math.sin(0.95 * theta + 0.5)))
            },
            # 8. Color 3 (Deep Base Anchor) - Dense contrast anchor at lowest boundary
            {
                "t": 0.95,
                "color": c3,
                "alpha_peak": 74,  # ~0.29
                "dx": 50.0 * math.sin(0.8 * theta + 5.0) + 20.0 * math.cos(0.6 * theta + 2.0),
                "dy": 24.0 * math.cos(0.8 * theta + 5.0) + 10.0 * math.sin(0.4 * theta + 1.0),
                "radius": max(130.0, min(300.0, w * 0.22 + 28.0 * math.sin(0.6 * theta + 2.2)))
            }
        ]

        # 1. Render Fluid Radial Blooms with Additive Screen Blending
        fluid_layer = QImage(int(w), glow_height, QImage.Format_ARGB32_Premultiplied)
        fluid_layer.fill(Qt.GlobalColor.transparent)

        p_fluid = QPainter(fluid_layer)
        p_fluid.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p_fluid.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        p_fluid.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)

        for b in blobs:
            base_x = b["t"] * w
            base_y = (y_start + (y_end - y_start) * b["t"]) - glow_top

            cx = base_x + b["dx"]
            cy = base_y + b["dy"]
            rad = b["radius"]

            c = b["color"]
            peak = b["alpha_peak"]

            # 4-Stop Soft Exponential Radial Diffusion Falloff Curve:
            grad = QRadialGradient(QPointF(cx, cy), rad)
            grad.setColorAt(0.0, QColor(c.red(), c.green(), c.blue(), peak))
            grad.setColorAt(0.45, QColor(c.red(), c.green(), c.blue(), int(peak * 0.46)))
            grad.setColorAt(0.85, QColor(c.red(), c.green(), c.blue(), int(peak * 0.12)))
            grad.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), 0))

            p_fluid.setBrush(QBrush(grad))
            p_fluid.setPen(Qt.PenStyle.NoPen)
            p_fluid.drawEllipse(QPointF(cx, cy), rad, rad)

        # 2. Overlay Micro-Dot Matrix Raster
        if self._dot_tile and not self._dot_tile.isNull():
            p_fluid.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            p_fluid.fillRect(0, 0, int(w), glow_height, QBrush(self._dot_tile))

        # 3. Apply Smooth Vertical Alpha Feathering on Top Boundary
        p_fluid.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        feather_grad = QLinearGradient(0, 0, 0, glow_height)
        feather_grad.setColorAt(0.0, QColor(0, 0, 0, 0))     # Invisible transition at upper edge
        feather_grad.setColorAt(0.28, QColor(0, 0, 0, 85))
        feather_grad.setColorAt(0.65, QColor(0, 0, 0, 215))
        feather_grad.setColorAt(1.0, QColor(0, 0, 0, 255))   # Solid anchor at bottom
        p_fluid.fillRect(0, 0, int(w), glow_height, QBrush(feather_grad))
        p_fluid.end()

        # 4. Composite final fluid mesh to the main canvas
        painter.drawImage(0, int(glow_top), fluid_layer)
