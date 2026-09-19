import os
import gc
import math
from pathlib import Path
from PySide6.QtCore import Qt, QRect, QRectF, QPoint, QPointF, QSize, Signal, QTimer, QThreadPool
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPixmap, QImage, QPainterPath, 
    QLinearGradient, QFont, QCursor, QKeySequence, QGuiApplication
)
from PySide6.QtWidgets import (
    QWidget, QFrame, QHBoxLayout, QLabel, QApplication, QFileDialog,
    QGraphicsDropShadowEffect, QPushButton
)
from .styles import COLORS, HEADER_TITLE_STYLE, FONT_FAMILY, get_theme_tokens
from .icon_generator import IconGenerator
from .action_pill import ActionPillWidget
from .toast import show_quick_toast, ToastManager
from .fluid_mesh import FluidMeshShaderWidget, FluidMeshGradient
from ..utils.path_security import validate_save_directory, sanitize_filename
from ..capture.ocr_engine import OCRWorker
from ..config.themes import DEFAULT_WAVE_THEME, WAVE_THEMES

class HeaderBadge(QWidget):
    """
    Clean, uncluttered top-left header with large bold Google Sans Flex typography.
    """
    def __init__(self, parent=None, theme: str = "dark"):
        super().__init__(parent)
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._theme = theme

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        self.title_lbl = QLabel("MaterialSnap", self)
        self.title_lbl.setObjectName("HeaderTitleLarge")

        # Soft text glow/shadow for crisp readability
        self.shadow = QGraphicsDropShadowEffect(self.title_lbl)
        self.shadow.setBlurRadius(20)
        self.shadow.setOffset(0, 3)
        self.title_lbl.setGraphicsEffect(self.shadow)

        self.set_theme(theme)
        layout.addWidget(self.title_lbl)

    def set_theme(self, theme: str):
        self._theme = theme
        tokens = get_theme_tokens(theme)
        text_col = tokens["text_primary"]
        shadow_col = QColor(0, 0, 0, 30) if theme == "light" else QColor(0, 0, 0, 190)
        self.title_lbl.setStyleSheet(f"""
            QLabel#HeaderTitleLarge {{
                color: {text_col};
                font-family: {FONT_FAMILY};
                font-size: 28px;
                font-weight: 800;
                letter-spacing: -0.5px;
                background: transparent;
            }}
        """)
        self.shadow.setColor(shadow_col)


class ScreenshotOverlay(QWidget):
    """
    Full-screen HiDPI freeze overlay with ultra-calm fluid gradient waves and 50% thinner pearl border.
    """
    sig_closed = Signal()

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self._current_theme = self.config_manager.get("theme", "dark")
        
        # Window attributes for multi-screen seamless overlay
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | 
            Qt.FramelessWindowHint | 
            Qt.Tool | 
            Qt.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)

        # Screenshot background data
        self.bg_pixmap = QPixmap()
        self.virtual_rect = QRect()

        # Selection state
        self.is_dragging = False
        self.start_pos = QPoint()
        self.current_pos = QPoint()
        self.selection_rect = QRect()
        self.has_selection = False

        # Top-left Minimalist Header
        self.header_badge = HeaderBadge(self, theme=self.config_manager.get("theme", "dark"))
        self.header_badge.move(24, 20)
        self.header_badge.raise_()

        # Living Acrylic Fluid Mesh Gradient Renderer
        self.fluid_mesh = FluidMeshGradient()

        # Floating Action Pill
        self.action_pill = ActionPillWidget(self)
        self.action_pill.hide()
        self.action_pill.sig_ocr.connect(self._do_ocr)
        self.action_pill.sig_copy.connect(self._do_copy)
        self.action_pill.sig_save.connect(self._do_save)
        self.action_pill.sig_fullscreen.connect(self._do_select_fullscreen)
        self.action_pill.sig_cancel.connect(self.close_overlay)

        # 60 FPS Fluid Mesh & Dynamic Gradient Animation Timer
        self.anim_phase = 0.0
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(16) # ~60 FPS
        self.anim_timer.timeout.connect(self._on_anim_tick)

    def _on_anim_tick(self):
        """Advances morphing cloud mesh and selection border animation."""
        self.anim_phase += 0.016
        if self.isVisible():
            self.update()

    def reload_config(self):
        """Immediately reloads configuration and updates active wave theme, texture mode, and theme."""
        theme_name = self.config_manager.get("wave_theme", DEFAULT_WAVE_THEME)
        texture_mode = self.config_manager.get("wave_texture_mode", "Acrylic")
        theme = self.config_manager.get("theme", "dark")
        self._current_theme = theme
        self.fluid_mesh.set_theme(theme_name)
        self.fluid_mesh.set_texture_mode(texture_mode)
        self.action_pill.set_theme(theme)
        self.header_badge.set_theme(theme)

    def start_capture(self, composite_pixmap: QPixmap, virtual_rect: QRect):
        """Initializes overlay with fresh screen capture and displays across all displays."""
        self.reload_config()
        self.bg_pixmap = composite_pixmap
        self.virtual_rect = virtual_rect
        self.selection_rect = QRect()
        self.has_selection = False
        self.is_dragging = False
        self.action_pill.hide()
        self.fluid_mesh.set_cursor(0.5, 0.5)

        # Set geometry spanning all monitors
        self.setGeometry(virtual_rect)
        
        # Position clean header at top-left with generous margin
        if self.config_manager.get("show_title", True):
            self.header_badge.adjustSize()
            self.header_badge.move(24, 20)
            self.header_badge.show()
            self.header_badge.raise_()
        else:
            self.header_badge.hide()

        self.anim_phase = 0.0
        self.anim_timer.start()

        self.show()
        self.raise_()
        self.activateWindow()

    def close_overlay(self):
        """Closes the overlay and releases resources."""
        self.anim_timer.stop()
        self.hide()
        self.action_pill.hide()
        # Immediate memory deallocation
        self.bg_pixmap = QPixmap()
        self.selection_rect = QRect()
        self.has_selection = False
        self.is_dragging = False
        gc.collect()
        self.sig_closed.emit()

    def _get_active_crop(self) -> QPixmap:
        """Returns cropped QPixmap of current selection (or whole screen)."""
        if self.has_selection and not self.selection_rect.isEmpty():
            r = self.selection_rect.normalized()
            return self.bg_pixmap.copy(r)
        return self.bg_pixmap

    def _do_ocr(self):
        """Extracts text from selection asynchronously and copies directly to clipboard."""
        crop = self._get_active_crop()
        if crop.isNull():
            self.close_overlay()
            return

        # Multi-Monitor DPI: extract full fidelity QImage
        qimage = crop.toImage()
        self.close_overlay()

        def on_ocr_success(text: str):
            if text and text.strip():
                clean_text = text.strip()
                clipboard = QApplication.clipboard()
                clipboard.setText(clean_text)
                ToastManager.show("Text extracted and copied", variant="success")
            else:
                ToastManager.show("Failed to recognize text", variant="error")

        def on_ocr_error(err_msg: str):
            print(f"[Overlay] OCR extraction error: {err_msg}")
            ToastManager.show("Failed to recognize text", variant="error")

        worker = OCRWorker(qimage)
        worker.sig_finished.connect(on_ocr_success)
        worker.sig_error.connect(on_ocr_error)
        self._active_ocr_worker = worker
        worker.finished.connect(lambda: setattr(self, '_active_ocr_worker', None))
        worker.start()

    def _do_copy(self):
        """Copies selection to clipboard and shows toast."""
        crop = self._get_active_crop()
        if not crop.isNull():
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(crop)
            ToastManager.show("Copied to clipboard", variant="success")
        self.close_overlay()

    def _do_save(self, prompt_custom_folder: bool = False):
        """Saves screenshot to disk with robust permission, sanitization, and directory fallbacks."""
        crop = self._get_active_crop()
        if crop.isNull():
            self.close_overlay()
            return

        save_dir = validate_save_directory(self.config_manager.get("save_directory"))

        from datetime import datetime
        default_name = f"Screenshot_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.png"
        target_path = save_dir / default_name

        if prompt_custom_folder:
            chosen_path, _ = QFileDialog.getSaveFileName(
                self, "Save Screenshot As", str(target_path), "PNG Image (*.png);;JPEG Image (*.jpg)"
            )
            if not chosen_path:
                return
            chosen_p = Path(chosen_path)
            safe_filename = sanitize_filename(chosen_p.name, fallback=default_name)
            chosen_dir = validate_save_directory(str(chosen_p.parent))
            target_path = chosen_dir / safe_filename

        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            fmt = "JPEG" if target_path.suffix.lower() in [".jpg", ".jpeg"] else "PNG"
            saved = crop.save(str(target_path), fmt)
            if not saved:
                raise IOError(f"Failed to write image data to {target_path}")
            
            if self.config_manager.get("auto_copy_clipboard", True):
                QApplication.clipboard().setPixmap(crop)

            ToastManager.show("Saved to disk", variant="info", folder_to_open=str(target_path.parent))
        except Exception as err:
            print(f"[Overlay] Error saving screenshot: {err}")
            ToastManager.show("Failed to save screenshot", variant="error")

        self.close_overlay()

    def _do_select_fullscreen(self):
        """Selects entire virtual screen geometry."""
        self.selection_rect = QRect(0, 0, self.width(), self.height())
        self.has_selection = True
        self.is_dragging = False
        self.update()
        self.action_pill.position_smartly(self.selection_rect, self.rect())
        self.action_pill.show()
        self.action_pill.setWindowOpacity(1.0)
        self.action_pill.raise_()

    # Mouse interaction handlers
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            if self.action_pill.isVisible() and self.action_pill.geometry().contains(pos):
                super().mousePressEvent(event)
                return

            self.is_dragging = True
            self.has_selection = False
            self.start_pos = pos
            self.current_pos = pos
            self.selection_rect = QRect(self.start_pos, self.current_pos)
            self.action_pill.hide()
            self.update()
        elif event.button() == Qt.RightButton:
            if self.has_selection:
                self.has_selection = False
                self.selection_rect = QRect()
                self.action_pill.hide()
                self.update()
            else:
                self.close_overlay()

    def mouseMoveEvent(self, event):
        self.current_pos = event.position().toPoint()
        if self.is_dragging:
            self.selection_rect = QRect(self.start_pos, self.current_pos).normalized()
        
        # Pass normalized cursor coordinates (OpenGL UV space: y inverted) to shader
        if self.width() > 0 and self.height() > 0 and hasattr(self, 'fluid_mesh'):
            nx = max(0.0, min(1.0, self.current_pos.x() / float(self.width())))
            ny = max(0.0, min(1.0, 1.0 - (self.current_pos.y() / float(self.height()))))
            self.fluid_mesh.set_cursor(nx, ny)

        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.selection_rect = QRect(self.start_pos, self.current_pos).normalized()
            
            if self.selection_rect.width() > 6 and self.selection_rect.height() > 6:
                self.has_selection = True
                self.action_pill.position_smartly(self.selection_rect, self.rect())
                self.action_pill.show()
                self.action_pill.setWindowOpacity(1.0)
                self.action_pill.raise_()
            else:
                self.has_selection = False
                self.action_pill.hide()
            self.update()

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key_Escape:
            self.close_overlay()
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            self._do_copy()
        elif key == Qt.Key_C and (modifiers & Qt.ControlModifier):
            self._do_copy()
        elif key == Qt.Key_S and (modifiers & Qt.ControlModifier):
            prompt = bool(modifiers & Qt.ShiftModifier)
            self._do_save(prompt)
        elif key == Qt.Key_F:
            self._do_select_fullscreen()
        elif key in (Qt.Key_T, Qt.Key_O):
            self._do_ocr()
        else:
            super().keyPressEvent(event)

    # Painting and Shader Effects
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # 1. Draw base captured desktop
        if not self.bg_pixmap.isNull():
            painter.drawPixmap(0, 0, self.bg_pixmap)

        # 2. Draw balanced scrim: dark QColor(15, 12, 28, 140) vs light QColor(255, 255, 255, 160)
        theme = getattr(self, '_current_theme', 'dark')
        if theme == "light":
            scrim_color = QColor(255, 255, 255, 160)
        else:
            scrim_color = QColor(15, 12, 28, 140)
        
        norm_rect = self.selection_rect.normalized() if (self.is_dragging or self.has_selection) else QRect()

        # Build Scrim Path (Full screen minus selection cutout)
        full_path = QPainterPath()
        full_path.addRect(self.rect())

        if norm_rect.isValid() and norm_rect.width() > 0 and norm_rect.height() > 0:
            cutout_path = QPainterPath()
            cutout_path.addRoundedRect(norm_rect, 6, 6)
            scrim_path = full_path.subtracted(cutout_path)
        else:
            scrim_path = full_path

        # Fill Scrim
        painter.fillPath(scrim_path, QBrush(scrim_color))

        # 3. Draw Living Acrylic Fluid Mesh Gradient inside Scrim Region with SourceOver Blending
        if self.config_manager.get("enable_fluid_wave", True):
            wave_theme = self.config_manager.get("wave_theme", DEFAULT_WAVE_THEME)
            texture_mode = self.config_manager.get("wave_texture_mode", "Acrylic")
            painter.save()
            painter.setClipPath(scrim_path)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            try:
                self.fluid_mesh.draw(
                    painter, self.width(), self.height(), self.anim_phase,
                    theme_name=wave_theme, texture_mode=texture_mode
                )
            except Exception as e:
                print(f"[Overlay] Fluid wave render error: {e}")
            finally:
                painter.restore()
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        # Force CompositionMode_SourceOver for all subsequent UI elements
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        # 4. Draw Active Selection Border (Refined pearl/pastel gradient)
        if norm_rect.isValid() and norm_rect.width() > 0 and norm_rect.height() > 0:
            self._draw_selection_glow_border(painter, norm_rect)
            
            # Dimension badge (e.g. 1920 × 1080 px)
            dim_text = f"{norm_rect.width()} × {norm_rect.height()} px"
            self._draw_dimension_chip(painter, norm_rect, dim_text)

        # 5. Draw Precision Magnifier Loupe
        if self.config_manager.get("show_magnifier", True) and (self.is_dragging or not self.has_selection):
            self._draw_loupe_magnifier(painter, self.current_pos)

    def _draw_selection_glow_border(self, painter: QPainter, norm_rect: QRect):
        """
        Draws dynamic glowing selection border with a smooth, delicate gradient
        gently drifting over time.
        """
        painter.save()
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        theme = getattr(self, '_current_theme', 'dark')
        is_light = (theme == "light")

        # Outer soft ambient glow
        glow_col = QColor(0, 0, 0, 20) if is_light else QColor(255, 255, 255, 30)
        glow_pen = QPen(glow_col, 3.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(glow_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(norm_rect, 6, 6)

        # Gentle continuous drifting angle
        p = self.anim_phase
        angle = p * 2 * math.pi
        cx = norm_rect.center().x()
        cy = norm_rect.center().y()
        rx = norm_rect.width() / 2
        ry = norm_rect.height() / 2

        x1 = cx + math.cos(angle) * rx
        y1 = cy + math.sin(angle) * ry
        x2 = cx - math.cos(angle) * rx
        y2 = cy - math.sin(angle) * ry

        grad = QLinearGradient(QPointF(x1, y1), QPointF(x2, y2))
        if is_light:
            grad.setColorAt(0.0, QColor("#18181B"))
            grad.setColorAt(0.35, QColor("#3F3F46"))
            grad.setColorAt(0.70, QColor("#71717A"))
            grad.setColorAt(1.0, QColor("#18181B"))
        else:
            grad.setColorAt(0.0, QColor("#FFFFFF"))
            grad.setColorAt(0.35, QColor("#E8EAED"))
            grad.setColorAt(0.70, QColor("#D0D3D8"))
            grad.setColorAt(1.0, QColor("#FFFFFF"))

        # Refined crisp stroke
        border_pen = QPen(QBrush(grad), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(border_pen)
        painter.drawRoundedRect(norm_rect, 6, 6)
        painter.restore()

    def _draw_dimension_chip(self, painter: QPainter, rect: QRect, text: str):
        """Draws dimension chip with capsule rounding and Google Sans Flex."""
        painter.save()
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        font = QFont("Google Sans Flex", 10, QFont.DemiBold)
        font.setStyleHint(QFont.SansSerif)
        painter.setFont(font)
        fm = painter.fontMetrics()
        text_w = fm.horizontalAdvance(text)
        text_h = fm.height()

        chip_w = text_w + 18
        chip_h = text_h + 8

        chip_x = rect.left() + 4
        chip_y = rect.top() - chip_h - 6
        if chip_y < 10:
            chip_y = rect.bottom() + 6

        chip_rect = QRectF(chip_x + 0.5, chip_y + 0.5, chip_w - 1.0, chip_h - 1.0)
        
        theme = getattr(self, '_current_theme', 'dark')
        tokens = get_theme_tokens(theme)
        is_light = (theme == "light")

        # 100% capsule pill rounding
        path = QPainterPath()
        path.addRoundedRect(chip_rect, (chip_h - 1.0) / 2, (chip_h - 1.0) / 2)
        chip_bg = QColor(255, 255, 255, 235) if is_light else QColor(24, 25, 28, 225)
        painter.fillPath(path, chip_bg)
        border_color = QColor(tokens["border_subtle"])
        painter.setPen(QPen(border_color, 1.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)

        painter.setPen(QColor(tokens["text_primary"]))
        painter.drawText(chip_rect, Qt.AlignCenter, text)
        painter.restore()

    def _draw_loupe_magnifier(self, painter: QPainter, pos: QPoint):
        """Draws a pixel magnifier loupe near the cursor."""
        if self.bg_pixmap.isNull():
            return

        size = 112
        zoom = 8
        half_src = 7

        bg_r = self.bg_pixmap.rect()
        src_x = max(0, min(pos.x() - half_src, bg_r.width() - half_src * 2))
        src_y = max(0, min(pos.y() - half_src, bg_r.height() - half_src * 2))
        src_rect = QRect(src_x, src_y, half_src * 2, half_src * 2)
        
        src_crop = self.bg_pixmap.copy(src_rect).toImage()
        if src_crop.isNull() or src_crop.width() == 0 or src_crop.height() == 0:
            return

        lx = pos.x() + 24
        ly = pos.y() + 24
        if lx + size > self.width() - 10:
            lx = pos.x() - size - 24
        if ly + size > self.height() - 10:
            ly = pos.y() - size - 24

        loupe_rect = QRectF(lx + 0.5, ly + 0.5, size - 1.0, size - 1.0)

        path = QPainterPath()
        path.addRoundedRect(loupe_rect, 14, 14)

        painter.save()
        painter.setClipPath(path)

        scaled_img = src_crop.scaled(size, size, Qt.IgnoreAspectRatio, Qt.FastTransformation)
        painter.drawImage(QRect(lx, ly, size, size), scaled_img)

        center_x = float(lx + size / 2.0)
        center_y = float(ly + size / 2.0)

        # Dual-Stroke High-Contrast Crosshair:
        # 1. Dark outer shadow for legibility over pure white / light pixels
        shadow_pen = QPen(QColor(0, 0, 0, 160), 2.4, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(shadow_pen)
        painter.drawLine(QPointF(center_x - 8, center_y), QPointF(center_x + 8, center_y))
        painter.drawLine(QPointF(center_x, center_y - 8), QPointF(center_x, center_y + 8))

        # 2. Pure white inner crosshair
        white_pen = QPen(QColor("#FFFFFF"), 1.2, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(white_pen)
        painter.drawLine(QPointF(center_x - 8, center_y), QPointF(center_x + 8, center_y))
        painter.drawLine(QPointF(center_x, center_y - 8), QPointF(center_x, center_y + 8))

        sample_x = max(0, min(pos.x() - src_x, src_crop.width() - 1))
        sample_y = max(0, min(pos.y() - src_y, src_crop.height() - 1))
        pixel_color = src_crop.pixelColor(sample_x, sample_y)
        hex_code = pixel_color.name().upper()

        # Token-aligned metadata container (#232529 / surface_card)
        info_rect = QRectF(lx + 0.5, ly + size - 22.5, size - 1.0, 22.0)
        painter.fillRect(info_rect, QColor(35, 37, 41, 235))
        painter.setPen(QPen(QColor(COLORS.get("border_divider", "#26292E")), 1.0))
        painter.drawLine(QPointF(info_rect.left(), info_rect.top()), QPointF(info_rect.right(), info_rect.top()))

        font = QFont("Google Sans Flex", 9, QFont.Bold)
        font.setStyleHint(QFont.Monospace)
        painter.setFont(font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(info_rect, Qt.AlignCenter, hex_code)

        painter.restore()

        # Crisp 1px Monochromatic Solid Border (#2A2D32)
        solid_border = QColor(COLORS.get("border_solid", "#2A2D32"))
        painter.setPen(QPen(solid_border, 1.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
