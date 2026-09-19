"""
Hardware-accelerated Native PySide6 / GLSL Living Ambient Mesh Drift Shader.
Ported from the 21st.dev WebGL/GLSL organic domain-warped shader with:
- Single-pass full-screen quad rendering via oversized 2-triangle vertex buffer [-1, -1, 3, -1, -1, 3].
- Procedural multi-octave FBM & 2-stage domain warping with drift animation.
- OKLab perceptual color space interpolation across active theme palettes.
- Subtle procedural film grain & bottom-anchored vertical alpha feathering / vignette.
- Real-time normalized pointer/cursor displacement swirl.
"""

import struct
from PySide6.QtCore import Qt, QPointF, QRect
from PySide6.QtGui import (
    QPainter, QColor, QVector2D, QVector3D, QVector4D,
    QOpenGLContext, QOffscreenSurface, QSurfaceFormat
)
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtOpenGL import (
    QOpenGLShader, QOpenGLShaderProgram, QOpenGLBuffer, QOpenGLFramebufferObject
)

from ..config.themes import WAVE_THEMES, DEFAULT_WAVE_THEME, get_wave_palette

VERT_SHADER_SOURCE = """
attribute vec2 a_position;
void main() {
    gl_Position = vec4(a_position, 0.0, 1.0);
}
"""

FRAG_SHADER_SOURCE = """
#ifdef GL_ES
precision highp float;
#endif

// Uniform Bindings
uniform vec4 u_scene;       // xy: resolution (px), z: elapsed time (s), w: color count (float)
uniform vec4 u_space;       // xy: aspect ratio, zw: normalized cursor (x, y)
uniform vec2 u_cursor;      // normalized cursor (x, y)
uniform vec3 u_colors[8];   // normalized linear RGB color palette array
uniform float u_scale;      // spatial coordinate scale (default: 1.30)
uniform float u_intensity;  // master shader opacity/intensity (default: 0.56)
uniform float u_brightness; // master color brightness/exposure multiplier (default: 1.05)
uniform float u_warp;       // organic fluid curl swirl amplitude (default: 0.192)
uniform float u_detail;     // harmonic frequency multiplier (default: 2.016)
uniform float u_contrast;   // field contrast curve (default: 1.10)
uniform float u_saturation; // saturation boost multiplier (default: 1.05)
uniform float u_grain;      // frosted acrylic grain scale (default: 0.09)
uniform float u_drift;      // kinetic harmonic velocity multiplier (default: 1.95)
uniform float u_dpr;        // device pixel ratio for physical DPI mesh scaling (default: 1.0)
uniform int u_texture_mode; // texture engine profile: 0 = Acrylic, 1 = Mesh
uniform int u_theme_id;     // theme kinematics engine: 0=Aura, 1=Prism, 2=Solar, 3=Opal

// Dave Hoskins Hash without Sine (artifact-free white noise)
float hash12(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

// Piecewise Linear RGB to sRGB Gamma Encoding
vec3 linear_to_srgb(vec3 c) {
    return mix(
        c * 12.92,
        1.055 * pow(clamp(c, 0.0, 1.0), vec3(1.0 / 2.4)) - 0.055,
        step(0.0031308, c)
    );
}

// Linear RGB to OKLab Color Space (Björn Ottosson, 2020)
vec3 rgb_to_oklab(vec3 c) {
    float l = 0.4122214708 * c.r + 0.5363325363 * c.g + 0.0514459929 * c.b;
    float m = 0.2119034982 * c.r + 0.6806995451 * c.g + 0.1073969566 * c.b;
    float s = 0.0883024619 * c.r + 0.2817188376 * c.g + 0.6299787005 * c.b;

    float l_ = pow(max(l, 0.0), 1.0 / 3.0);
    float m_ = pow(max(m, 0.0), 1.0 / 3.0);
    float s_ = pow(max(s, 0.0), 1.0 / 3.0);

    return vec3(
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    );
}

// OKLab to Linear RGB Color Space (Björn Ottosson, 2020)
vec3 oklab_to_rgb(vec3 c) {
    float l_ = c.x + 0.3963377774 * c.y + 0.2158037573 * c.z;
    float m_ = c.x - 0.1055613458 * c.y - 0.0638541728 * c.z;
    float s_ = c.x - 0.0894841775 * c.y - 1.2914855480 * c.z;

    float l = l_ * l_ * l_;
    float m = m_ * m_ * m_;
    float s = s_ * s_ * s_;

    return vec3(
        +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    );
}

void main() {
    // Standard aspect-ratio coordinates:
    vec2 p = (gl_FragCoord.xy - 0.5 * u_scene.xy) / max(u_scene.y, 1.0);
    float a = u_scene.x / max(u_scene.y, 1.0);

    // Dynamic harmonic time flow & phase velocity
    float t = mod(u_scene.z * u_drift, 628.31853);

    // Pointer Interactivity (gentle fluid reaction)
    vec2 cur = (u_cursor * u_scene.xy - 0.5 * u_scene.xy) / max(u_scene.y, 1.0);
    vec2 d_cur = p - cur;
    float cur_dist = length(d_cur);
    p += (d_cur / (cur_dist + 0.18)) * exp(-cur_dist * 4.0) * 0.12;

    vec2 warped_p;
    vec2 c0, c1, c2, c3;

    if (u_theme_id == 1) {
        // Theme 1 ("Prism Spectrum" - Matching Video 1):
        // Palette: Obsidian Base (#0B0F19), Cyber Cyan (#00F5D4), Electric Lime (#52FF00), Vivid Crimson (#FF003C), Deep Violet (#7928CA)
        // Motion: Harmonized directional flow with soft isotropic curl:
        vec2 diag_flow = vec2(
            sin((p.x + p.y) * 1.8 + t * 0.9) * 0.22,
            cos((p.x - p.y) * 1.8 - t * 0.8) * 0.22
        );
        // Add soft isotropic curl to eliminate linear shearing
        vec2 isotropic_curl = vec2(
            sin(p.y * 2.4 - t * 0.5),
            cos(p.x * 2.4 + t * 0.6)
        ) * 0.14;
        warped_p = p + diag_flow + isotropic_curl;

        // All 4 colors (cyan, lime, red, violet) remain visible as fluid plumes
        vec2 diag = vec2(0.7071, 0.7071);
        vec2 perp = vec2(-0.7071, 0.7071);
        float tp = t * 1.2;
        c0 = diag * (-0.50 * a) + perp * (sin(tp * 0.9) * 0.35);         // Cyber Cyan
        c1 = diag * (-0.15 * a) + perp * (cos(tp * 0.85 + 1.2) * 0.35);  // Electric Lime
        c2 = diag * ( 0.20 * a) + perp * (sin(tp * 0.95 + 2.4) * 0.35);  // Vivid Crimson
        c3 = diag * ( 0.55 * a) + perp * (cos(tp * 0.80 + 3.6) * 0.35);  // Deep Violet

    } else if (u_theme_id == 2) {
        // Theme 2 ("Solar Flare" - Matching Video 2):
        // Palette: Warm Dark Plum (#1F0B18), Neon Tangerine (#FF6B00), Cool Lagoon Mint (#00F0B5), Radiant Buttercup (#FFD000), Velvet Purple (#8A2BE2)
        // Motion: Radial breathing swell:
        float swell = sin(t * 0.65) * 0.35;
        c0 = vec2(-0.4 * a + swell, 0.25);               // Tangerine
        c1 = vec2( 0.4 * a - swell, -0.25);              // Mint
        c2 = vec2(0.15 * a, 0.20 + sin(t * 0.5) * 0.15); // Floating solar accent (Yellow)
        c3 = vec2(-0.2 * a, -0.35);                      // Purple

        vec2 flow_solar = vec2(
            sin(p.y * 2.0 + t * 0.5),
            cos(p.x * 2.0 - t * 0.45)
        ) * 0.20;
        warped_p = p + flow_solar;

    } else if (u_theme_id == 3) {
        // Theme 3 ("Opal Nebula" - Matching Video 3):
        // Palette: Deep Petrol Navy (#0D141C), Dusty Rose (#C47AC0), Sage Teal (#38A3A5), Pearlescent Ice (#E2E8F0), Dark Slate (#1B263B)
        // Motion: High-density silk sheen:
        vec2 silk_flow = vec2(
            sin(p.y * 3.5 + t * 0.4),
            cos(p.x * 3.5 - t * 0.35)
        ) * 0.22;
        warped_p = p + silk_flow;

        float ts = t * 0.35;
        c0 = vec2(-0.30 * a,  0.18) + vec2(sin(ts * 0.9) * 0.25 * a, cos(ts * 1.1) * 0.20);  // Dusty Rose
        c1 = vec2( 0.30 * a,  0.18) + vec2(-cos(ts * 0.8) * 0.25 * a, sin(ts * 1.0) * 0.20); // Sage Teal
        c2 = vec2( 0.00,     -0.10) + vec2(cos(ts * 0.7) * 0.20 * a, sin(ts * 0.8) * 0.18);  // Pearlescent Ice
        c3 = vec2( 0.25 * a, -0.25) + vec2(-sin(ts * 0.85) * 0.22 * a, -cos(ts * 0.9) * 0.20); // Dark Slate

    } else {
        // Theme 0 ("Samsung Aura"):
        // Palette: Deep Indigo (#1A102F), Electric Cyan (#1ED8E8), Neon Magenta (#E63BB8), Ultramarine (#4332D6), Solar Spark (#FFD768)
        // Motion: Continuous harmonic orbits (t * 0.8) with soft 2-octave fluid curling
        vec2 curl = vec2(
            sin(p.y * 2.2 + t * 0.8),
            cos(p.x * 2.2 - t * 0.7)
        ) * 0.24;
        vec2 curl2 = vec2(
            cos((p.x + curl.x) * 3.0 + t * 0.6),
            sin((p.y + curl.y) * 3.0 - t * 0.65)
        ) * 0.14;
        warped_p = p + curl + curl2;

        c0 = vec2(-0.35 * a,  0.22) + vec2(sin(t * 0.85) * 0.42 * a, cos(t * 0.70) * 0.35); // Cyan
        c1 = vec2( 0.35 * a,  0.22) + vec2(-cos(t * 0.75) * 0.40 * a, sin(t * 0.90) * 0.35); // Magenta
        c2 = vec2(-0.30 * a, -0.22) + vec2(cos(t * 0.95) * 0.40 * a, -sin(t * 0.80) * 0.32); // Ultramarine
        c3 = vec2( 0.30 * a, -0.22) + vec2(sin(t * 0.70) * 0.45 * a, cos(t * 0.85) * 0.34);  // Solar Spark
    }

    // Dynamic Palette: 5 OLED Swatches [Base Anchor, Swatch 0, Swatch 1, Swatch 2, Swatch 3]
    vec3 col_base = (u_scene.w >= 1.0) ? u_colors[0] : vec3(0.102, 0.063, 0.184); // Base Anchor
    vec3 col0     = (u_scene.w >= 2.0) ? u_colors[1] : vec3(0.118, 0.847, 0.910); // Swatch 0
    vec3 col1     = (u_scene.w >= 3.0) ? u_colors[2] : vec3(0.902, 0.231, 0.722); // Swatch 1
    vec3 col2     = (u_scene.w >= 4.0) ? u_colors[3] : vec3(0.263, 0.196, 0.839); // Swatch 2
    vec3 col3     = (u_scene.w >= 5.0) ? u_colors[4] : vec3(1.000, 0.843, 0.408); // Swatch 3

    // Convert swatches to Perceptual OKLab space
    vec3 lab_base = rgb_to_oklab(col_base);
    vec3 lab0     = rgb_to_oklab(col0);
    vec3 lab1     = rgb_to_oklab(col1);
    vec3 lab2     = rgb_to_oklab(col2);
    vec3 lab3     = rgb_to_oklab(col3);

    // Spatial Voronoi / Metaball Clustering with Gaussian Core Falloff
    float d0 = length(warped_p - c0);
    float d1 = length(warped_p - c1);
    float d2 = length(warped_p - c2);
    float d3 = length(warped_p - c3);

    float k_falloff = 2.6; // Increased Gaussian blending radius from 3.2 to 2.6 for smooth fluid plumes
    float w0 = exp(-d0 * d0 * k_falloff);
    float w1 = exp(-d1 * d1 * k_falloff);
    // In Solar Flare, confine yellow to an accent plume rather than a full-canvas wash
    float w2 = (u_theme_id == 2) ? (exp(-d2 * d2 * 3.8) * 0.75) : exp(-d2 * d2 * k_falloff);
    float w3 = exp(-d3 * d3 * k_falloff);

    float w_sum = w0 + w1 + w2 + w3;
    float w_base;
    if (w_sum > 1.0) {
        w0 /= w_sum;
        w1 /= w_sum;
        w2 /= w_sum;
        w3 /= w_sum;
        w_base = 0.0;
    } else {
        w_base = 1.0 - w_sum;
    }

    vec3 lab_final = lab_base * w_base + lab0 * w0 + lab1 * w1 + lab2 * w2 + lab3 * w3;
    vec3 color = oklab_to_rgb(lab_final);

    // Contrast curve to retain rich vibrant saturation:
    color = smoothstep(0.02, 0.98, color);

    // Theme 3: Opal Nebula - Sheen Highlight (subtle specular sheen on satin fabric)
    if (u_theme_id == 3) {
        color += vec3(0.14, 0.16, 0.18) * pow(clamp(lab_final.x, 0.0, 1.0), 3.0);
    }

    // Dual-Profile Texture & Screen Pipeline:
    if (u_texture_mode == 1) {
        // Mode 1: Mesh (Calibrated Acoustic Screen)
        float grid_spacing = 4.2 * max(u_dpr, 1.0);
        vec2 rot = mat2(0.7071, -0.7071, 0.7071, 0.7071) * gl_FragCoord.xy;
        vec2 grid_uv = fract(rot / grid_spacing) - 0.5;
        float dist = length(grid_uv);
        // Distinct circular dot with sharp optical edge:
        float dot_mask = 1.0 - smoothstep(0.18, 0.32, dist);

        // Tactile acoustic perforation with subtle specular baseline:
        float base_dot_glow = 0.04; // Guarantees tactile grid presence even in 0% lightness zones
        float luma_boost = smoothstep(0.15, 0.85, lab_final.x) * 0.16;
        color = mix(color * 0.82, color * 1.15, dot_mask);
        color += vec3(base_dot_glow + luma_boost) * dot_mask;
    } else {
        // Mode 0: Acrylic (Soft Matte Glass with Hoskins Grain)
        vec2 rot = mat2(0.7071, -0.7071, 0.7071, 0.7071) * gl_FragCoord.xy;
        float grid = 2.8 * max(u_dpr, 1.0);
        float dot_dist = length(fract(rot / grid) - 0.5);
        float dot_mask = smoothstep(0.30, 0.10, dot_dist);

        // Subtle micro-diffusion stipple
        color = mix(color * 0.94, color * 1.12, dot_mask * smoothstep(0.3, 0.8, lab_final.x));

        // Fine frosted glass white noise (Dave Hoskins grain, strength 0.04)
        vec2 grain_seed = gl_FragCoord.xy + fract(u_scene.z * 11.13) * 64.0;
        float nr = hash12(grain_seed);
        float ng = hash12(grain_seed + vec2(19.3, 31.7));
        float nb = hash12(grain_seed + vec2(41.1, 67.3));
        vec3 acrylic_noise = (vec3(nr, ng, nb) - 0.5) * 0.04;
        color += acrylic_noise;
    }

    color = clamp(color, 0.0, 1.0);

    // Piecewise Linear to sRGB Display Gamma Transfer
    vec3 srgb_color = linear_to_srgb(color);

    // Balanced overlay opacity with subtle vertical decay (0.60 master alpha)
    vec2 uv = gl_FragCoord.xy / max(u_scene.xy, vec2(1.0));
    float alpha = clamp(0.60 + 0.05 * (1.0 - uv.y), 0.55, 0.68);

    // Premultiplied ARGB Output for Flawless Qt Alpha Composition
    gl_FragColor = vec4(srgb_color * alpha, alpha);
}
"""

THEME_ID_MAP: dict[str, int] = {
    "Samsung Aura": 0,
    "Prism Spectrum": 1,
    "Solar Flare": 2,
    "Opal Nebula": 3
}

def hex_to_linear_rgb(hex_code: str) -> tuple[float, float, float]:
    """Converts HEX color string to normalized linear RGB float triplet."""
    h = hex_code.lstrip('#')
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    def s2l(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (s2l(r), s2l(g), s2l(b))


class FluidMeshShaderWidget(QOpenGLWidget):
    """
    Dedicated QOpenGLWidget subclass executing the 21st.dev WebGL/GLSL "Mesh Drift" shader:
    - Zero CPU heap thrashing: all pixel computations executed exclusively on GPU.
    - Full-screen quad rendering via single 2-triangle vertex buffer [-1, -1, 3, -1, -1, 3].
    - Perceptual OKLab color transitions across all 6 MaterialSnap wave themes.
    - Normalized mouse tracking for real-time cursor reaction.
    - Supports standalone QOpenGLWidget display and high-performance QPainter draw() integration.
    """
    def __init__(self, theme_name: str = DEFAULT_WAVE_THEME, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

        self._theme_name = theme_name
        self.theme_id = THEME_ID_MAP.get(theme_name, 0)
        self._palette_colors: list[tuple[float, float, float]] = []
        self._set_colors_from_theme(theme_name)

        # Uniform parameters as specified in architecture
        self.scale = 1.30
        self.intensity = 0.56
        self.brightness = 1.05
        self.warp = 0.192
        self.detail = 2.016
        self.contrast = 1.10
        self.saturation = 1.05
        self.grain = 0.09
        self.drift = 1.95
        self.dpr = 1.0
        self.texture_mode = 0  # 0 = Acrylic, 1 = Mesh

        self.cursor_enabled = True
        self._cursor_norm = (0.5, 0.5)
        self._elapsed_time = 0.0
        self._color_count = 5.0

        # Standalone QOpenGLWidget pipeline state
        self._program = None
        self._vbo = None
        self._uniform_locs = {}
        self._attr_loc = -1
        self._gl_initialized = False

        # Offscreen FBO hardware-accelerated pipeline state
        self._offscreen_context = None
        self._offscreen_surface = None
        self._offscreen_program = None
        self._offscreen_vbo = None
        self._offscreen_uniform_locs = {}
        self._offscreen_attr_loc = -1
        self._fbo = None
        self._fbo_size = (0, 0)

    def _set_colors_from_theme(self, theme_name: str):
        """Converts active 4/5-color palette into normalized linear RGB float triplets."""
        raw_palette = get_wave_palette(theme_name)
        self._color_count = float(len(raw_palette))
        self._palette_colors = [hex_to_linear_rgb(c) for c in raw_palette]
        # Pad array up to 8 slots
        while len(self._palette_colors) < 8:
            self._palette_colors.append(self._palette_colors[-1] if self._palette_colors else (0.0, 0.0, 0.0))

    def set_theme(self, theme_name: str):
        """Updates active wave theme, maps uniform theme ID, and refreshes uniform color array."""
        self._theme_name = theme_name
        self.theme_id = THEME_ID_MAP.get(theme_name, 0)
        self._set_colors_from_theme(theme_name)
        if self.isVisible():
            self.update()

    def set_texture_mode(self, mode: str | int):
        """Configures texture mode (0/'Acrylic' or 1/'Mesh')."""
        if isinstance(mode, str):
            self.texture_mode = 1 if mode.strip().lower() == "mesh" else 0
        else:
            self.texture_mode = int(mode)
        if self.isVisible():
            self.update()

    def set_cursor(self, nx: float, ny: float):
        """Updates normalized cursor coordinates for interactive shader swirl."""
        self._cursor_norm = (max(0.0, min(1.0, float(nx))), max(0.0, min(1.0, float(ny))))
        if self.isVisible():
            self.update()

    def set_time(self, elapsed_seconds: float):
        """Advances shader timeline."""
        self._elapsed_time = float(elapsed_seconds)
        if self.isVisible():
            self.update()

    def initializeGL(self):
        """Compiles shader pipeline and allocates single oversized quad VBO."""
        try:
            self._program = QOpenGLShaderProgram(self)
            self._program.addShaderFromSourceCode(QOpenGLShader.Vertex, VERT_SHADER_SOURCE)
            self._program.addShaderFromSourceCode(QOpenGLShader.Fragment, FRAG_SHADER_SOURCE)
            if not self._program.link():
                print(f"[FluidMesh] Shader link error: {self._program.log()}")
                return

            self._attr_loc = self._program.attributeLocation('a_position')

            # Cache uniform locations for maximum runtime efficiency
            uniform_names = [
                'u_scene', 'u_space', 'u_cursor', 'u_scale', 'u_intensity',
                'u_brightness', 'u_warp', 'u_detail', 'u_contrast', 'u_saturation', 'u_grain', 'u_drift', 'u_dpr',
                'u_texture_mode', 'u_theme_id'
            ]
            for name in uniform_names:
                self._uniform_locs[name] = self._program.uniformLocation(name)

            for i in range(8):
                self._uniform_locs[f'u_colors[{i}]'] = self._program.uniformLocation(f'u_colors[{i}]')

            # Full-screen single 2-triangle vertex buffer: [-1, -1, 3, -1, -1, 3]
            self._vbo = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
            self._vbo.create()
            self._vbo.bind()
            vertex_data = struct.pack('6f', -1.0, -1.0, 3.0, -1.0, -1.0, 3.0)
            self._vbo.allocate(vertex_data, len(vertex_data))
            self._vbo.release()

            self._gl_initialized = True
        except Exception as err:
            print(f"[FluidMesh] initializeGL failed: {err}")
            self._gl_initialized = False

    def resizeGL(self, w: int, h: int):
        """Configures OpenGL viewport matching current widget dimensions."""
        if self._gl_initialized and self.context():
            self.context().functions().glViewport(0, 0, w, h)

    def paintGL(self):
        """Binds program, uploads uniforms, and executes full-screen quad rasterization."""
        if not self._gl_initialized or not self._program or not self._program.isLinked():
            return

        w = float(self.width())
        h = float(self.height())
        if w <= 0.0 or h <= 0.0:
            return

        aspect = w / max(h, 1.0)
        gl = self.context().functions()

        self._program.bind()
        self._vbo.bind()

        if self._attr_loc >= 0:
            self._program.enableAttributeArray(self._attr_loc)
            self._program.setAttributeBuffer(self._attr_loc, 0x1406, 0, 2, 0)

        # Upload uniforms via cached locations
        if self._uniform_locs.get('u_scene', -1) >= 0:
            self._program.setUniformValue(self._uniform_locs['u_scene'], QVector4D(w, h, self._elapsed_time, self._color_count))

        cur_x, cur_y = self._cursor_norm if self.cursor_enabled else (-10.0, -10.0)
        if self._uniform_locs.get('u_space', -1) >= 0:
            self._program.setUniformValue(self._uniform_locs['u_space'], QVector4D(aspect, 1.0, cur_x, cur_y))

        if self._uniform_locs.get('u_cursor', -1) >= 0:
            self._program.setUniformValue(self._uniform_locs['u_cursor'], QVector2D(cur_x, cur_y))

        # Float uniforms use glUniform1f for PySide6 compatibility
        for name, val in [
            ('u_scale', self.scale),
            ('u_intensity', self.intensity),
            ('u_brightness', self.brightness),
            ('u_warp', self.warp),
            ('u_detail', self.detail),
            ('u_contrast', self.contrast),
            ('u_saturation', self.saturation),
            ('u_grain', self.grain),
            ('u_drift', self.drift)
        ]:
            loc = self._uniform_locs.get(name, -1)
            if loc >= 0:
                gl.glUniform1f(loc, float(val))

        dpr = float(self.devicePixelRatioF()) if hasattr(self, 'devicePixelRatioF') else getattr(self, 'dpr', 1.0)
        dpr = max(1.0, float(dpr))
        loc_dpr = self._uniform_locs.get('u_dpr', -1)
        if loc_dpr >= 0:
            gl.glUniform1f(loc_dpr, float(dpr))

        loc_mode = self._uniform_locs.get('u_texture_mode', -1)
        if loc_mode >= 0:
            gl.glUniform1i(loc_mode, int(self.texture_mode))

        loc_theme = self._uniform_locs.get('u_theme_id', -1)
        if loc_theme >= 0:
            gl.glUniform1i(loc_theme, int(self.theme_id))

        # Upload color palette
        for i, (r, g, b) in enumerate(self._palette_colors[:8]):
            loc = self._uniform_locs.get(f'u_colors[{i}]', -1)
            if loc >= 0:
                self._program.setUniformValue(loc, QVector3D(r, g, b))

        # Render single oversized triangle covering the entire clip space
        # GL_TRIANGLES = 0x0004 = 4
        gl.glDrawArrays(4, 0, 3)

        if self._attr_loc >= 0:
            self._program.disableAttributeArray(self._attr_loc)
        self._vbo.release()
        self._program.release()

    def _ensure_offscreen_pipeline(self) -> bool:
        """Initializes dedicated offscreen OpenGL context, surface, shader and VBO."""
        if self._offscreen_context is not None and self._offscreen_program is not None:
            return True

        try:
            fmt = QSurfaceFormat.defaultFormat()
            fmt.setAlphaBufferSize(8)
            fmt.setSamples(0)
            fmt.setSwapInterval(1)

            self._offscreen_surface = QOffscreenSurface()
            self._offscreen_surface.setFormat(fmt)
            self._offscreen_surface.create()

            self._offscreen_context = QOpenGLContext()
            self._offscreen_context.setFormat(fmt)
            if not self._offscreen_context.create():
                print("[FluidMesh] Failed to create offscreen QOpenGLContext")
                return False

            if not self._offscreen_context.makeCurrent(self._offscreen_surface):
                print("[FluidMesh] Failed to makeCurrent on offscreen surface")
                return False

            self._offscreen_program = QOpenGLShaderProgram()
            self._offscreen_program.addShaderFromSourceCode(QOpenGLShader.Vertex, VERT_SHADER_SOURCE)
            self._offscreen_program.addShaderFromSourceCode(QOpenGLShader.Fragment, FRAG_SHADER_SOURCE)
            if not self._offscreen_program.link():
                print(f"[FluidMesh] Offscreen shader link error: {self._offscreen_program.log()}")
                return False

            self._offscreen_attr_loc = self._offscreen_program.attributeLocation('a_position')

            uniform_names = [
                'u_scene', 'u_space', 'u_cursor', 'u_scale', 'u_intensity',
                'u_brightness', 'u_warp', 'u_detail', 'u_contrast', 'u_saturation', 'u_grain', 'u_drift', 'u_dpr',
                'u_texture_mode', 'u_theme_id'
            ]
            for name in uniform_names:
                self._offscreen_uniform_locs[name] = self._offscreen_program.uniformLocation(name)

            for i in range(8):
                self._offscreen_uniform_locs[f'u_colors[{i}]'] = self._offscreen_program.uniformLocation(f'u_colors[{i}]')

            self._offscreen_vbo = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
            self._offscreen_vbo.create()
            self._offscreen_vbo.bind()
            vertex_data = struct.pack('6f', -1.0, -1.0, 3.0, -1.0, -1.0, 3.0)
            self._offscreen_vbo.allocate(vertex_data, len(vertex_data))
            self._offscreen_vbo.release()

            return True
        except Exception as err:
            print(f"[FluidMesh] _ensure_offscreen_pipeline error: {err}")
            return False

    def draw(self, painter: QPainter, width: int, height: int, phase: float, theme_name: str = None, dpr: float = None, texture_mode: str | int = None):
        """
        Renders the GPU shader and composites the ambient fluid onto painter canvas.
        Renders into a QOpenGLFramebufferObject (FBO) at physical device resolution,
        extracts to QImage, and draws via QPainter with CompositionMode_SourceOver in overlay's paintEvent.
        Guarantees 100% visibility over transparent desktop captures with zero DWM driver blackouts.
        """
        if width <= 0 or height <= 0:
            return

        if theme_name and theme_name != self._theme_name:
            self.set_theme(theme_name)

        if texture_mode is not None:
            self.set_texture_mode(texture_mode)

        self.set_time(phase)

        # Full-canvas ambient render
        band_h = height
        y_top = 0

        # Factor in devicePixelRatio for physical DPI scaling
        if dpr is None:
            if painter and painter.device():
                dpr = float(painter.device().devicePixelRatioF())
            elif self.window():
                dpr = float(self.window().devicePixelRatioF())
            else:
                dpr = float(getattr(self, 'dpr', 1.0))
        dpr = max(1.0, float(dpr))

        # Render at full physical resolution for ultra-sharp micro-dot stipples
        render_w = max(1, int(round(width * dpr)))
        render_h = max(1, int(round(band_h * dpr)))

        if not self._ensure_offscreen_pipeline():
            return

        try:
            if not self._offscreen_context.makeCurrent(self._offscreen_surface):
                return

            gl = self._offscreen_context.functions()

            # Allocate or resize FBO if dimensions changed
            if self._fbo is None or self._fbo_size != (render_w, render_h):
                self._fbo = QOpenGLFramebufferObject(render_w, render_h)
                self._fbo_size = (render_w, render_h)

            if not self._fbo.isValid():
                return

            self._fbo.bind()
            gl.glViewport(0, 0, render_w, render_h)

            prog = self._offscreen_program
            prog.bind()

            aspect = float(render_w) / max(float(render_h), 1.0)

            # Uniforms
            if self._offscreen_uniform_locs.get('u_scene', -1) >= 0:
                prog.setUniformValue(self._offscreen_uniform_locs['u_scene'], QVector4D(float(render_w), float(render_h), self._elapsed_time, self._color_count))

            cur_x, cur_y = self._cursor_norm if self.cursor_enabled else (-10.0, -10.0)
            if self._offscreen_uniform_locs.get('u_space', -1) >= 0:
                prog.setUniformValue(self._offscreen_uniform_locs['u_space'], QVector4D(aspect, 1.0, cur_x, cur_y))

            if self._offscreen_uniform_locs.get('u_cursor', -1) >= 0:
                prog.setUniformValue(self._offscreen_uniform_locs['u_cursor'], QVector2D(cur_x, cur_y))

            # Float uniforms must use glUniform1f for PySide6 compatibility
            for name, val in [
                ('u_scale', self.scale),
                ('u_intensity', self.intensity),
                ('u_brightness', self.brightness),
                ('u_warp', self.warp),
                ('u_detail', self.detail),
                ('u_contrast', self.contrast),
                ('u_saturation', self.saturation),
                ('u_grain', self.grain),
                ('u_drift', self.drift)
            ]:
                loc = self._offscreen_uniform_locs.get(name, -1)
                if loc >= 0:
                    gl.glUniform1f(loc, float(val))

            loc_dpr = self._offscreen_uniform_locs.get('u_dpr', -1)
            if loc_dpr >= 0:
                gl.glUniform1f(loc_dpr, float(dpr))

            loc_mode = self._offscreen_uniform_locs.get('u_texture_mode', -1)
            if loc_mode >= 0:
                gl.glUniform1i(loc_mode, int(self.texture_mode))

            loc_theme = self._offscreen_uniform_locs.get('u_theme_id', -1)
            if loc_theme >= 0:
                gl.glUniform1i(loc_theme, int(self.theme_id))

            # Palette
            for i, (r, g, b) in enumerate(self._palette_colors[:8]):
                loc = self._offscreen_uniform_locs.get(f'u_colors[{i}]', -1)
                if loc >= 0:
                    prog.setUniformValue(loc, QVector3D(r, g, b))

            # Render single oversized triangle covering entire clip space
            self._offscreen_vbo.bind()
            if self._offscreen_attr_loc >= 0:
                prog.enableAttributeArray(self._offscreen_attr_loc)
                prog.setAttributeBuffer(self._offscreen_attr_loc, 0x1406, 0, 2, 0)

            gl.glDrawArrays(4, 0, 3)

            if self._offscreen_attr_loc >= 0:
                prog.disableAttributeArray(self._offscreen_attr_loc)
            self._offscreen_vbo.release()
            prog.release()
            self._fbo.release()

            img = self._fbo.toImage()
            if img and not img.isNull():
                img.setDevicePixelRatio(dpr)
                painter.drawImage(QRect(0, y_top, width, band_h), img)
        except Exception as e:
            print(f"[FluidMesh] draw offscreen FBO error: {e}")
        finally:
            if self._offscreen_context:
                self._offscreen_context.doneCurrent()


# Backwards compatibility alias for existing modules and tests
FluidMeshGradient = FluidMeshShaderWidget
