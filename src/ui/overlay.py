import os
import gc
import math
from pathlib import Path
from PySide6.QtCore import Qt, QRect, QPoint, QPointF, QSize, Signal, QTimer
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPixmap, QImage, QPainterPath, 
    QLinearGradient, QFont, QCursor, QKeySequence, QGuiApplication
)
from PySide6.QtWidgets import (
    QWidget, QFrame, QHBoxLayout, QLabel, QApplication, QFileDialog,
    QGraphicsDropShadowEffect
)
from .styles import COLORS, HEADER_TITLE_STYLE, FONT_FAMILY
from .icon_generator import IconGenerator
from .action_pill import ActionPillWidget
from .toast import show_quick_toast
from .fluid_mesh import FluidMeshGradient
from ..utils.path_security import validate_save_directory, sanitize_filename

class HeaderBadge(QWidget):
    """
    Clean, uncluttered top-left header with large bold Google Sans Flex typography.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.title_lbl = QLabel("MaterialSnap", self)
        self.title_lbl.setObjectName("HeaderTitleLarge")
        self.title_lbl.setStyleSheet(f"""
            QLabel#HeaderTitleLarge {{
                color: #FFFFFF;
                font-family: {FONT_FAMILY};
                font-size: 28px;
                font-weight: 800;
                letter-spacing: -0.5px;
                background: transparent;
            }}
        """)

        # Soft text glow/shadow for crisp readability
        shadow = QGraphicsDropShadowEffect(self.title_lbl)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 190))
        shadow.setOffset(0, 3)
        self.title_lbl.setGraphicsEffect(shadow)

        layout.addWidget(self.title_lbl)

class ScreenshotOverlay(QWidget):
    """
    Full-screen HiDPI freeze overlay with ultra-calm fluid gradient waves and 50% thinner pearl border.
    """
    sig_closed = Signal()

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        
        # Window attributes for multi-screen seamless overlay
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | 
            Qt.FramelessWindowHint | 
            Qt.Tool | 
            Qt.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
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
        self.header_badge = HeaderBadge(self)

        # Living Acrylic Fluid Mesh Gradient Renderer
        self.fluid_mesh = FluidMeshGradient()

        # Floating Action Pill
        self.action_pill = ActionPillWidget(self)
        self.action_pill.hide()
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
        self.anim_phase = (self.anim_phase + 0.0012) % 1.0
        if self.isVisible():
            self.update()

    def reload_config(self):
        """Immediately reloads configuration and updates active wave theme."""
        theme_name = self.config_manager.get("wave_theme", "Twilight Mauve")
        self.fluid_mesh.set_theme(theme_name)

    def start_capture(self, composite_pixmap: QPixmap, virtual_rect: QRect):
        """Initializes overlay with fresh screen capture and displays across all displays."""
        self.reload_config()
        self.bg_pixmap = composite_pixmap
        self.virtual_rect = virtual_rect
        self.selection_rect = QRect()
        self.has_selection = False
        self.is_dragging = False
        self.action_pill.hide()

        # Set geometry spanning all monitors
        self.setGeometry(virtual_rect)
        
        # Position clean header at top-left with generous margin
        if self.config_manager.get("show_title", True):
            self.header_badge.adjustSize()
            self.header_badge.move(36, 30)
            self.header_badge.show()
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

    def _do_copy(self):
        """Copies selection to clipboard and shows toast."""
        crop = self._get_active_crop()
        if not crop.isNull():
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(crop)
            show_quick_toast("Screenshot copied to clipboard", icon_type="copy")
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

            folder_name = target_path.parent.name
            show_quick_toast(f"Saved to {folder_name} • Click to open", folder_to_open=str(target_path.parent), icon_type="folder")
        except Exception as err:
            print(f"[Overlay] Error saving screenshot: {err}")
            show_quick_toast("Failed to save screenshot (check permissions)")

        self.close_overlay()

    def _do_select_fullscreen(self):
        """Selects entire virtual screen geometry."""
        self.selection_rect = QRect(0, 0, self.width(), self.height())
        self.has_selection = True
        self.is_dragging = False
        self.update()
        self.action_pill.position_smartly(self.selection_rect, self.rect())

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
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.selection_rect = QRect(self.start_pos, self.current_pos).normalized()
            
            if self.selection_rect.width() > 6 and self.selection_rect.height() > 6:
                self.has_selection = True
                self.action_pill.position_smartly(self.selection_rect, self.rect())
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

        # 2. Draw +10% darkened scrim (alpha 140 / ~0.55)
        scrim_color = QColor(10, 12, 16, 140)
        
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

        # Fill Dark Scrim
        painter.fillPath(scrim_path, QBrush(scrim_color))

        # 3. Draw Living Acrylic Fluid Mesh Gradient inside Scrim Region (if enabled)
        if self.config_manager.get("enable_fluid_wave", True):
            wave_theme = self.config_manager.get("wave_theme", "Twilight Mauve")
            painter.save()
            painter.setClipPath(scrim_path)
            self.fluid_mesh.draw(painter, self.width(), self.height(), self.anim_phase, theme_name=wave_theme)
            painter.restore()

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
        Draws dynamic glowing selection border with a smooth, delicate monochromatic gradient
        gently drifting over time.
        """
        # Outer soft ambient glow
        glow_pen = QPen(QColor(255, 255, 255, 30), 3.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
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

        # Strict monochromatic luminous gradient
        grad = QLinearGradient(QPointF(x1, y1), QPointF(x2, y2))
        grad.setColorAt(0.0, QColor("#FFFFFF"))
        grad.setColorAt(0.35, QColor("#E8EAED"))
        grad.setColorAt(0.70, QColor("#D0D3D8"))
        grad.setColorAt(1.0, QColor("#FFFFFF"))

        # Refined crisp stroke
        border_pen = QPen(QBrush(grad), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(border_pen)
        painter.drawRoundedRect(norm_rect, 6, 6)

    def _draw_dimension_chip(self, painter: QPainter, rect: QRect, text: str):
        """Draws dimension chip with capsule rounding and Google Sans Flex."""
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

        chip_rect = QRect(chip_x, chip_y, chip_w, chip_h)
        
        # 100% capsule pill rounding
        path = QPainterPath()
        path.addRoundedRect(chip_rect, chip_h / 2, chip_h / 2)
        painter.fillPath(path, QColor(24, 25, 28, 225))
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1))
        painter.drawPath(path)

        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(chip_rect, Qt.AlignCenter, text)

    def _draw_loupe_magnifier(self, painter: QPainter, pos: QPoint):
        """Draws a pixel magnifier loupe near the cursor."""
        if self.bg_pixmap.isNull():
            return

        size = 110
        zoom = 8
        half_src = size // (2 * zoom)

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

        loupe_rect = QRect(lx, ly, size, size)

        path = QPainterPath()
        path.addRoundedRect(loupe_rect, 14, 14)

        painter.save()
        painter.setClipPath(path)

        scaled_img = src_crop.scaled(size, size, Qt.IgnoreAspectRatio, Qt.FastTransformation)
        painter.drawImage(loupe_rect, scaled_img)

        center_x = lx + size // 2
        center_y = ly + size // 2
        painter.setPen(QPen(QColor(255, 255, 255, 180), 1.2))
        painter.drawLine(center_x - 8, center_y, center_x + 8, center_y)
        painter.drawLine(center_x, center_y - 8, center_x, center_y + 8)

        sample_x = max(0, min(pos.x() - src_x, src_crop.width() - 1))
        sample_y = max(0, min(pos.y() - src_y, src_crop.height() - 1))
        pixel_color = src_crop.pixelColor(sample_x, sample_y)
        hex_code = pixel_color.name().upper()

        info_rect = QRect(lx, ly + size - 20, size, 20)
        painter.fillRect(info_rect, QColor(20, 20, 22, 230))
        painter.setFont(QFont("Consolas", 8, QFont.Bold))
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(info_rect, Qt.AlignCenter, hex_code)

        painter.restore()

        # 1.4px Monochromatic border
        painter.setPen(QPen(QColor(255, 255, 255, 180), 1.4))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(loupe_rect, 14, 14)
