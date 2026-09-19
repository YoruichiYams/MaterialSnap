# MaterialSnap — Actionable Engineering Roadmap & Implementation Diffs

This roadmap specifies the exact, sequential, atomic implementation steps required to resolve all 14 defects documented in [`RIGOROUS_AUDIT_REPORT.md`](file:///c:/Users/Gleb/Desktop/%E3%85%A4/Workspace/MaterialSnap/RIGOROUS_AUDIT_REPORT.md). Each step contains unambiguous, ready-to-apply unified code diffs.

---

## Phase 1: Hardware-Accelerated Wave Shader & Compositing Pipeline

### Step 1.1: Fix Linear RGB Color Space, Full Canvas Envelope & Brightness in GLSL
**Target File:** [`src/ui/fluid_mesh.py`](file:///c:/Users/Gleb/Desktop/%E3%85%A4/Workspace/MaterialSnap/src/ui/fluid_mesh.py)  
**Resolves:** DEF-001, DEF-002, DEF-004, DEF-005

```diff
--- a/src/ui/fluid_mesh.py
+++ b/src/ui/fluid_mesh.py
@@ -40,6 +40,7 @@
 uniform vec3 u_colors[8];   // normalized linear RGB color palette array
 uniform float u_scale;      // noise spatial scale (default: 1.30)
 uniform float u_intensity;  // master shader opacity/intensity (default: 0.56)
+uniform float u_brightness; // master color brightness/exposure multiplier (default: 1.25)
 uniform float u_warp;       // domain warping displacement amplitude (default: 0.192)
 uniform float u_detail;     // fbm octave frequency multiplier (default: 2.016)
 uniform float u_contrast;   // field contrast curve (default: 1.167)
@@ -131,6 +132,15 @@
     return clamp(oklab_to_rgb(col_lab), 0.0, 1.0);
 }
 
+// Piecewise Linear RGB to sRGB Gamma Encoding
+vec3 linear_to_srgb(vec3 c) {
+    return mix(
+        c * 12.92,
+        1.055 * pow(clamp(c, 0.0, 1.0), vec3(1.0 / 2.4)) - 0.055,
+        step(0.0031308, c)
+    );
+}
+
 void main() {
     vec2 uv = gl_FragCoord.xy / max(u_scene.xy, vec2(1.0));
     float aspect = u_scene.x / max(u_scene.y, 1.0);
@@ -155,16 +165,16 @@
     vec3 color = sample_palette(f);
 
     // Subtle High-Frequency Film Grain (desktop-optimized)
     float grain = (fract(sin(dot(uv * 1000.0, vec2(12.9898, 78.233)) + fract(u_scene.z * 17.1)) * 43758.5453) - 0.5) * u_grain;
-    color = clamp(color + grain, 0.0, 1.0);
+    color = clamp(color * u_brightness + grain, 0.0, 1.0);
+
+    // Convert linear color to display sRGB
+    vec3 srgb_color = linear_to_srgb(color);
 
-    // Subtle Vignette and Top Alpha Feathering
-    // uv.y in OpenGL: 0.0 is viewport bottom, 1.0 is viewport top.
-    // Feather from dense bottom (1.0) to zero alpha at top (0.0) for legibility.
-    float alpha = clamp(0.75 * (1.0 - smoothstep(0.0, 0.85, uv.y)), 0.0, 0.85) * u_intensity;
+    // Smooth, organic vertical envelope across full screen canvas
+    float alpha = clamp(u_intensity * (0.85 - 0.40 * smoothstep(0.0, 1.0, uv.y)), 0.0, 0.85);
 
     // Premultiplied ARGB output for flawless Qt alpha composition
-    gl_FragColor = vec4(color * alpha, alpha);
+    gl_FragColor = vec4(srgb_color * alpha, alpha);
 }
 """
@@ -201,6 +211,7 @@
         # Uniform parameters as specified in architecture
         self.scale = 1.30
         self.intensity = 0.56
+        self.brightness = 1.25
         self.warp = 0.192
         self.detail = 2.016
         self.contrast = 1.167
@@ -272,7 +283,7 @@
             # Cache uniform locations for maximum runtime efficiency
             uniform_names = [
                 'u_scene', 'u_space', 'u_cursor', 'u_scale', 'u_intensity',
-                'u_warp', 'u_detail', 'u_contrast', 'u_grain', 'u_drift'
+                'u_brightness', 'u_warp', 'u_detail', 'u_contrast', 'u_grain', 'u_drift'
             ]
             for name in uniform_names:
                 self._uniform_locs[name] = self._program.uniformLocation(name)
@@ -333,6 +344,7 @@
         for name, val in [
             ('u_scale', self.scale),
             ('u_intensity', self.intensity),
+            ('u_brightness', self.brightness),
             ('u_warp', self.warp),
             ('u_detail', self.detail),
             ('u_contrast', self.contrast),
@@ -395,7 +407,7 @@
             uniform_names = [
                 'u_scene', 'u_space', 'u_cursor', 'u_scale', 'u_intensity',
-                'u_warp', 'u_detail', 'u_contrast', 'u_grain', 'u_drift'
+                'u_brightness', 'u_warp', 'u_detail', 'u_contrast', 'u_grain', 'u_drift'
             ]
             for name in uniform_names:
                 self._offscreen_uniform_locs[name] = self._offscreen_program.uniformLocation(name)
@@ -428,12 +440,12 @@
         if theme_name and theme_name != self._theme_name:
             self.set_theme(theme_name)
 
-        self.set_time(phase * 100.0)
+        self.set_time(phase)
 
-        # Ambient bottom envelope (32% screen height or min 280px)
-        band_h = min(height, max(280, int(height * 0.32)))
-        y_top = height - band_h
+        # Full-canvas ambient render
+        band_h = height
+        y_top = 0
 
         # Half-resolution render for 60 FPS performance and zero CPU load
         render_w = max(1, width // 2)
         render_h = max(1, band_h // 2)
@@ -476,6 +488,7 @@
             for name, val in [
                 ('u_scale', self.scale),
                 ('u_intensity', self.intensity),
+                ('u_brightness', self.brightness),
                 ('u_warp', self.warp),
                 ('u_detail', self.detail),
                 ('u_contrast', self.contrast),
```

---

### Step 1.2: Continuous Time Drift & Scrim Composition in Overlay
**Target File:** [`src/ui/overlay.py`](file:///c:/Users/Gleb/Desktop/%E3%85%A4/Workspace/MaterialSnap/src/ui/overlay.py)  
**Resolves:** DEF-003, DEF-004

```diff
--- a/src/ui/overlay.py
+++ b/src/ui/overlay.py
@@ -111,7 +111,7 @@
     def _on_anim_tick(self):
         """Advances morphing cloud mesh and selection border animation."""
-        self.anim_phase = (self.anim_phase + 0.0012) % 1.0
+        self.anim_phase += 0.016 # Monotonic elapsed seconds (16ms per tick)
         if self.isVisible():
             self.update()
 
@@ -358,12 +358,13 @@
         # Fill Dark Scrim
         painter.fillPath(scrim_path, QBrush(scrim_color))
 
-        # 3. Draw Living Acrylic Fluid Mesh Gradient inside Scrim Region (if enabled)
+        # 3. Draw Living Acrylic Fluid Mesh Gradient with Luminous Screen Blending
         if self.config_manager.get("enable_fluid_wave", True):
             wave_theme = self.config_manager.get("wave_theme", "Twilight Mauve")
             painter.save()
             painter.setClipPath(scrim_path)
+            painter.setCompositionMode(QPainter.CompositionMode_Screen)
             self.fluid_mesh.draw(painter, self.width(), self.height(), self.anim_phase, theme_name=wave_theme)
             painter.restore()
```

---

## Phase 2: Subpixel Geometry & Drop Shadow Margins

### Step 2.1: Fix HeaderBadge Drop Shadow Truncation
**Target File:** [`src/ui/overlay.py`](file:///c:/Users/Gleb/Desktop/%E3%85%A4/Workspace/MaterialSnap/src/ui/overlay.py)  
**Resolves:** DEF-009

```diff
--- a/src/ui/overlay.py
+++ b/src/ui/overlay.py
@@ -30,7 +30,7 @@
         self.setAttribute(Qt.WA_TranslucentBackground, True)
 
         layout = QHBoxLayout(self)
-        layout.setContentsMargins(0, 0, 0, 0)
+        layout.setContentsMargins(20, 20, 20, 20) # Allocates room for 20px blur shadow
 
         self.title_lbl = QLabel("MaterialSnap", self)
@@ -137,7 +137,7 @@
         if self.config_manager.get("show_title", True):
             self.header_badge.adjustSize()
-            self.header_badge.move(36, 30)
+            self.header_badge.move(16, 10) # Compensate for 20px internal layout margin
             self.header_badge.show()
```

---

### Step 2.2: Fix Action Pill Shadow Truncation & Coordinate Alignment
**Target File:** [`src/ui/action_pill.py`](file:///c:/Users/Gleb/Desktop/%E3%85%A4/Workspace/MaterialSnap/src/ui/action_pill.py)  
**Resolves:** DEF-007

```diff
--- a/src/ui/action_pill.py
+++ b/src/ui/action_pill.py
@@ -85,7 +85,7 @@
         self.setAttribute(Qt.WA_TranslucentBackground, True)
         self.setCursor(Qt.PointingHandCursor)
         self.setMouseTracking(True)
-        self.shadow_margin = 16
+        self.shadow_margin = 20 # Allocates 20px > 14px blur + 4px offset (18px)
 
         self._entry_anim_group = None
         self._exit_anim = None
```

---

### Step 2.3: Fix Toast Notification Shadow Truncation & Docking Calculation
**Target File:** [`src/ui/toast.py`](file:///c:/Users/Gleb/Desktop/%E3%85%A4/Workspace/MaterialSnap/src/ui/toast.py)  
**Resolves:** DEF-008, DEF-014

```diff
--- a/src/ui/toast.py
+++ b/src/ui/toast.py
@@ -71,7 +71,7 @@
         self.duration_ms = max(1000, duration_ms)
         self.action_callback = action_callback
         self._remaining_ms = self.duration_ms
-        self.shadow_margin = 16
+        self.shadow_margin = 20 # Allocates 20px > 14px blur + 4px offset (18px)
 
         # Two-layer composition: Root widget is transparent viewport wrapper
@@ -267,6 +267,8 @@
         if self._state in (ToastState.CLOSED, ToastState.EXITING):
             return
 
+        if self.slide_in_anim and self.slide_in_anim.state() == QPropertyAnimation.Running:
+            self.slide_in_anim.stop()
         if self.repack_anim and self.repack_anim.state() == QPropertyAnimation.Running:
             self.repack_anim.stop()
```

---

### Step 2.4: Fix Magnifier Loupe 1:1 Pixel Math & Solid Token Borders
**Target File:** [`src/ui/overlay.py`](file:///c:/Users/Gleb/Desktop/%E3%85%A4/Workspace/MaterialSnap/src/ui/overlay.py)  
**Resolves:** DEF-011

```diff
--- a/src/ui/overlay.py
+++ b/src/ui/overlay.py
@@ -433,7 +433,7 @@
-        chip_rect = QRect(chip_x, chip_y, chip_w, chip_h)
+        chip_rect = QRectF(chip_x + 0.5, chip_y + 0.5, chip_w - 1.0, chip_h - 1.0)
         
         # 100% capsule pill rounding
         path = QPainterPath()
@@ -440,7 +440,7 @@
         painter.fillPath(path, QColor(24, 25, 28, 225))
-        painter.setPen(QPen(QColor(255, 255, 255, 20), 1))
+        border_color = QColor(COLORS.get("border_glass", "#2A2D32"))
+        painter.setPen(QPen(border_color, 1.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
         painter.drawPath(path)
 
@@ -450,9 +450,9 @@
     def _draw_loupe_magnifier(self, painter: QPainter, pos: QPoint):
         """Draws a pixel magnifier loupe near the cursor."""
         if self.bg_pixmap.isNull():
             return
 
-        size = 110
+        size = 112 # Exactly 14 src pixels * 8 zoom (integer square grid)
         zoom = 8
-        half_src = size // (2 * zoom)
+        half_src = 7
 
@@ -517,7 +517,8 @@
-        painter.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
+        solid_border = QColor(COLORS.get("border_solid", "#2A2D32"))
+        painter.setPen(QPen(solid_border, 1.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
         painter.setBrush(Qt.NoBrush)
         painter.drawPath(path)
```

---

## Phase 3: QComboBox Popup & Settings Dialog Rendering

### Step 3.1: Eliminate Black Square Corners on CleanComboBox Popup
**Target File:** [`src/ui/settings_dialog.py`](file:///c:/Users/Gleb/Desktop/%E3%85%A4/Workspace/MaterialSnap/src/ui/settings_dialog.py)  
**Resolves:** DEF-006

```diff
--- a/src/ui/settings_dialog.py
+++ b/src/ui/settings_dialog.py
@@ -254,10 +254,12 @@
     def _configure_popup(self):
         v = self.view()
         if v:
-            v.setAutoFillBackground(True)
+            v.setAutoFillBackground(False)
+            v.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
             if v.viewport():
-                v.viewport().setAutoFillBackground(True)
+                v.viewport().setAutoFillBackground(False)
+                v.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
             w = v.window()
             if w and w != self and w != self.window():
                 w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
```

---

### Step 3.2: Eliminate QSS `rgba()` Aliasing on Dialog Close Button
**Target File:** [`src/ui/settings_dialog.py`](file:///c:/Users/Gleb/Desktop/%E3%85%A4/Workspace/MaterialSnap/src/ui/settings_dialog.py)  
**Resolves:** DEF-010

```diff
--- a/src/ui/settings_dialog.py
+++ b/src/ui/settings_dialog.py
@@ -423,10 +423,10 @@
                 border-radius: 16px;
             }
             QToolButton:hover {
-                background-color: rgba(255, 255, 255, 0.12);
+                background-color: #26282D;
             }
             QToolButton:pressed {
-                background-color: rgba(255, 255, 255, 0.18);
+                background-color: #2F333A;
             }
         """)
```

---

## Phase 4: Iconography Vector Parity & Multi-DPI Resolution

### Step 4.1: Mathematical QPainterPath Definitions for User Reference Icons
**Target File:** [`src/ui/icon_generator.py`](file:///c:/Users/Gleb/Desktop/%E3%85%A4/Workspace/MaterialSnap/src/ui/icon_generator.py)  
**Resolves:** DEF-012, DEF-013

```diff
--- a/src/ui/icon_generator.py
+++ b/src/ui/icon_generator.py
@@ -11,8 +11,9 @@
     @staticmethod
     def _create_multi_dpi_icon(size: int, render_fn) -> QIcon:
-        """Helper to create a QIcon containing both 1x and 2x HiDPI pixmap representations."""
+        """Helper to create a QIcon containing 1.0x, 1.25x, 1.5x, and 2.0x HiDPI pixmap representations."""
         icon = QIcon()
-        for scale in [1.0, 2.0]:
+        for scale in [1.0, 1.25, 1.5, 2.0]:
             px_size = int(size * scale)
             pix = QPixmap(px_size, px_size)
             pix.fill(Qt.transparent)
@@ -76,17 +77,35 @@
     @classmethod
     def create_copy_icon(cls, size: int = 24, color: str = "#FFFFFF") -> QIcon:
+        """Dual layered sheets: solid front sheet with folded notch + background outline."""
         def render(painter: QPainter, s: int):
             pen = QPen(QColor(color), 1.9, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
             painter.setPen(pen)
             painter.setBrush(Qt.NoBrush)
 
-            # Front rect
-            painter.drawRoundedRect(QRectF(s * 0.3, s * 0.3, s * 0.55, s * 0.55), 2.5, 2.5)
-            # Back rect outline
+            # 1. Background Sheet Outline (Top-Left)
             back_path = QPainterPath()
-            back_path.moveTo(s * 0.2, s * 0.65)
+            back_path.moveTo(s * 0.2, s * 0.55)
             back_path.lineTo(s * 0.2, s * 0.2)
-            back_path.lineTo(s * 0.65, s * 0.2)
+            back_path.lineTo(s * 0.55, s * 0.2)
             painter.drawPath(back_path)
 
+            # 2. Solid Front Sheet with Folded Notch (Bottom-Right)
+            fx1, fy1 = s * 0.34, s * 0.34
+            fx2, fy2 = s * 0.80, s * 0.80
+            notch = s * 0.16
+
+            front = QPainterPath()
+            front.moveTo(fx1, fy1)
+            front.lineTo(fx2 - notch, fy1)
+            front.lineTo(fx2, fy1 + notch)
+            front.lineTo(fx2, fy2)
+            front.lineTo(fx1, fy2)
+            front.closeSubpath()
+
+            painter.fillPath(front, QBrush(QColor("#1E1F22")))
+            painter.drawPath(front)
+
+            # Fold Triangle
+            fold = QPainterPath()
+            fold.moveTo(fx2 - notch, fy1)
+            fold.lineTo(fx2 - notch, fy1 + notch)
+            fold.lineTo(fx2, fy1 + notch)
+            painter.drawPath(fold)
+
         return cls._create_multi_dpi_icon(size, render)
 
     @classmethod
     def create_save_icon(cls, size: int = 24, color: str = "#FFFFFF") -> QIcon:
+        """Retro 3.5\" floppy disk silhouette with shutter and label cutouts."""
         def render(painter: QPainter, s: int):
             pen = QPen(QColor(color), 1.9, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
             painter.setPen(pen)
             painter.setBrush(Qt.NoBrush)
 
-            # Download arrow & tray
-            painter.drawLine(QPointF(s * 0.5, s * 0.2), QPointF(s * 0.5, s * 0.6))
-            painter.drawLine(QPointF(s * 0.32, s * 0.44), QPointF(s * 0.5, s * 0.62))
-            painter.drawLine(QPointF(s * 0.68, s * 0.44), QPointF(s * 0.5, s * 0.62))
-
-            # Bottom tray
-            tray = QPainterPath()
-            tray.moveTo(s * 0.22, s * 0.6)
-            tray.lineTo(s * 0.22, s * 0.78)
-            tray.lineTo(s * 0.78, s * 0.78)
-            tray.lineTo(s * 0.78, s * 0.6)
-            painter.drawPath(tray)
+            # Outer Floppy Silhouette with top-right beveled notch
+            x1, y1 = s * 0.20, s * 0.20
+            x2, y2 = s * 0.80, s * 0.80
+            bevel = s * 0.12
+
+            disk = QPainterPath()
+            disk.moveTo(x1, y1)
+            disk.lineTo(x2 - bevel, y1)
+            disk.lineTo(x2, y1 + bevel)
+            disk.lineTo(x2, y2)
+            disk.lineTo(x1, y2)
+            disk.closeSubpath()
+            painter.drawPath(disk)
+
+            # Shutter Cutout (top center)
+            shutter = QPainterPath()
+            shutter.addRect(QRectF(s * 0.34, y1, s * 0.32, s * 0.22))
+            painter.drawPath(shutter)
+
+            # Label Area Cutout (bottom center)
+            label_path = QPainterPath()
+            label_path.addRoundedRect(QRectF(s * 0.28, s * 0.50, s * 0.44, s * 0.24), 2.0, 2.0)
+            painter.drawPath(label_path)
 
         return cls._create_multi_dpi_icon(size, render)
 
     @classmethod
     def create_close_icon(cls, size: int = 24, color: str = "#FFFFFF") -> QIcon:
+        """Thick geometric diagonal cross ('X')."""
         def render(painter: QPainter, s: int):
-            pen = QPen(QColor(color), 2.0, Qt.SolidLine, Qt.RoundCap)
+            pen = QPen(QColor(color), 2.8, Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin)
             painter.setPen(pen)
-            painter.drawLine(QPointF(s * 0.3, s * 0.3), QPointF(s * 0.7, s * 0.7))
-            painter.drawLine(QPointF(s * 0.7, s * 0.3), QPointF(s * 0.3, s * 0.7))
+            painter.drawLine(QPointF(s * 0.28, s * 0.28), QPointF(s * 0.72, s * 0.72))
+            painter.drawLine(QPointF(s * 0.72, s * 0.28), QPointF(s * 0.28, s * 0.72))
 
         return cls._create_multi_dpi_icon(size, render)
 
     @classmethod
     def create_fullscreen_icon(cls, size: int = 24, color: str = "#FFFFFF") -> QIcon:
+        """Dashed corner brackets with 4 diagonal expansion arrows."""
         def render(painter: QPainter, s: int):
-            pen = QPen(QColor(color), 1.9, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
+            pen = QPen(QColor(color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
             painter.setPen(pen)
 
-            m = s * 0.25
-            l = s * 0.2
-            # Top-left corner
-            painter.drawLine(QPointF(m, m + l), QPointF(m, m))
-            painter.drawLine(QPointF(m, m), QPointF(m + l, m))
-            # Top-right corner
-            painter.drawLine(QPointF(s - m - l, m), QPointF(s - m, m))
-            painter.drawLine(QPointF(s - m, m), QPointF(s - m, m + l))
-            # Bottom-left corner
-            painter.drawLine(QPointF(m, s - m - l), QPointF(m, s - m))
-            painter.drawLine(QPointF(m, s - m), QPointF(m + l, s - m))
-            # Bottom-right corner
-            painter.drawLine(QPointF(s - m - l, s - m), QPointF(s - m, s - m))
-            painter.drawLine(QPointF(s - m, s - m), QPointF(s - m, s - m - l))
+            m = s * 0.18
+            l = s * 0.16
+            # 4 Corner Brackets
+            painter.drawLine(QPointF(m, m + l), QPointF(m, m))
+            painter.drawLine(QPointF(m, m), QPointF(m + l, m))
+            painter.drawLine(QPointF(s - m - l, m), QPointF(s - m, m))
+            painter.drawLine(QPointF(s - m, m), QPointF(s - m, m + l))
+            painter.drawLine(QPointF(m, s - m - l), QPointF(m, s - m))
+            painter.drawLine(QPointF(m, s - m), QPointF(m + l, s - m))
+            painter.drawLine(QPointF(s - m - l, s - m), QPointF(s - m, s - m))
+            painter.drawLine(QPointF(s - m, s - m), QPointF(s - m, s - m - l))
+
+            # 4 Diagonal Expansion Arrows
+            c = s / 2.0
+            d_in = s * 0.08
+            d_out = s * 0.22
+            # Diagonal vectors: (-1,-1), (1,-1), (-1,1), (1,1)
+            for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
+                p1 = QPointF(c + dx * d_in, c + dy * d_in)
+                p2 = QPointF(c + dx * d_out, c + dy * d_out)
+                painter.drawLine(p1, p2)
 
         return cls._create_multi_dpi_icon(size, render)
 
     @classmethod
     def create_ocr_icon(cls, size: int = 24, color: str = "#FFFFFF") -> QIcon:
+        """Typographic serif ligature 'Aa'."""
         def render(painter: QPainter, s: int):
-            pen = QPen(QColor(color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
-            painter.setPen(pen)
-            painter.setBrush(Qt.NoBrush)
-
-            c_len = s * 0.16
-            # Top-Left Bracket
-            ...
-            # Crisp Centered 'T' (Text glyph)
-            t_pen = QPen(QColor(color), 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
-            painter.setPen(t_pen)
-            painter.drawLine(QPointF(s * 0.32, s * 0.36), QPointF(s * 0.68, s * 0.36))
-            painter.drawLine(QPointF(s * 0.5, s * 0.36), QPointF(s * 0.5, s * 0.68))
+            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
+            pen = QPen(QColor(color), 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
+            painter.setPen(pen)
+
+            # Capital Serif 'A' (Left)
+            # Apex, Left Leg, Right Leg, Crossbar, Serifs
+            painter.drawLine(QPointF(s * 0.32, s * 0.24), QPointF(s * 0.18, s * 0.76))
+            painter.drawLine(QPointF(s * 0.32, s * 0.24), QPointF(s * 0.46, s * 0.76))
+            painter.drawLine(QPointF(s * 0.24, s * 0.58), QPointF(s * 0.40, s * 0.58))
+            # Left Leg Serif Foot
+            painter.drawLine(QPointF(s * 0.14, s * 0.76), QPointF(s * 0.22, s * 0.76))
+            # Right Leg Serif Foot
+            painter.drawLine(QPointF(s * 0.42, s * 0.76), QPointF(s * 0.50, s * 0.76))
+
+            # Lowercase Serif 'a' (Right)
+            # Stem on right with bottom hook
+            painter.drawLine(QPointF(s * 0.74, s * 0.42), QPointF(s * 0.74, s * 0.72))
+            painter.drawLine(QPointF(s * 0.74, s * 0.72), QPointF(s * 0.79, s * 0.76))
+            # Rounded bowl
+            bowl = QPainterPath()
+            bowl.addEllipse(QRectF(s * 0.52, s * 0.46, s * 0.22, s * 0.28))
+            painter.drawPath(bowl)
+            # Top hood/arch
+            painter.drawLine(QPointF(s * 0.54, s * 0.44), QPointF(s * 0.74, s * 0.42))
 
         return cls._create_multi_dpi_icon(size, render)
```

---

## Phase 5: Verification & Validation Checklist

1. Run full unit and integration test suite:
   ```powershell
   pytest tests/
   ```
2. Verify that `CleanComboBox` popup has 0 black corner pixels at `(0,0)` and `(w-1, 0)`.
3. Verify that `FluidMeshShaderWidget` outputs sRGB encoded non-zero pixels under screen blending.
4. Verify that action pill drop shadow extends 20px with zero horizontal clipping.
5. Recompile standalone binary and run binary IPC smoke test:
   ```powershell
   .\build.bat
   pytest tests/test_z_exe_binary.py
   ```
