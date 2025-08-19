"""
Enhanced Minimalist Photo Viewer — with support for ALL image formats
Optimized version with smooth zoom and pan animations
"""

import sys
import math
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, QThread, Signal, QEasingCurve
from PySide6.QtGui import (QPixmap, QImageReader, QPainter, QWheelEvent, QMouseEvent,
                           QColor, QImage, QGuiApplication, QMovie)
from PySide6.QtWidgets import QApplication, QWidget, QFileDialog


class ImageLoader(QThread):
    """Background thread for loading heavy image formats"""
    imageLoaded = Signal(QPixmap)
    loadFailed = Signal(str)
    
    def __init__(self, path):
        super().__init__()
        self.path = path
    
    def run(self):
        try:
            pixmap = self._load_image_comprehensive(self.path)
            if pixmap and not pixmap.isNull():
                self.imageLoaded.emit(pixmap)
            else:
                self.loadFailed.emit("Failed to load image")
        except Exception as e:
            self.loadFailed.emit(str(e))
    
    def _register_all_plugins(self):
        """Register all available image format plugins"""
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except:
            try:
                from pillow_heif import register_heif_opener
                register_heif_opener()
            except:
                pass
        
        try:
            import pillow_avif
        except:
            try:
                import pillow_avif_plugin
            except:
                pass
    
    def _load_image_comprehensive(self, path: str) -> QPixmap:
        """Comprehensive image loader supporting all formats"""
        self._register_all_plugins()
        
        # First try Qt native formats
        reader = QImageReader(path)
        if reader.canRead():
            qimg = reader.read()
            if qimg and not qimg.isNull():
                return QPixmap.fromImage(qimg)
        
        # Try RAW formats with rawpy
        raw_extensions = {'.cr2', '.cr3', '.nef', '.arw', '.dng', '.raf', '.orf', 
                         '.rw2', '.pef', '.srw', '.x3f', '.mrw', '.dcr', '.kdc', 
                         '.erf', '.mef', '.mos', '.ptx', '.r3d', '.fff', '.iiq'}
        
        if Path(path).suffix.lower() in raw_extensions:
            try:
                import rawpy
                with rawpy.imread(path) as raw:
                    rgb = raw.postprocess()
                h, w, ch = rgb.shape
                bytes_per_line = ch * w
                qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                return QPixmap.fromImage(qimg)
            except Exception as e:
                print(f"RAW processing failed: {e}")
        
        # Try with Pillow
        try:
            from PIL import Image
            im = Image.open(path)
            
            if hasattr(im, 'is_animated') and im.is_animated:
                im.seek(0)
            
            if im.mode not in ('RGBA', 'RGB'):
                im = im.convert('RGBA')
            elif im.mode == 'RGB':
                im = im.convert('RGBA')
                
            data = im.tobytes('raw', 'RGBA')
            qimg = QImage(data, im.width, im.height, QImage.Format_RGBA8888)
            if not qimg.isNull():
                return QPixmap.fromImage(qimg)
        except Exception as e:
            print(f"Pillow loading failed: {e}")
        
        # Try with imageio
        try:
            import imageio.v3 as iio
            img_array = iio.imread(path)
            
            if len(img_array.shape) == 3:
                h, w, c = img_array.shape
                if c == 3:
                    import numpy as np
                    rgba = np.zeros((h, w, 4), dtype=img_array.dtype)
                    rgba[:, :, :3] = img_array
                    rgba[:, :, 3] = 255
                    img_array = rgba
                
                bytes_per_line = 4 * w
                qimg = QImage(img_array.data, w, h, bytes_per_line, QImage.Format_RGBA8888)
                return QPixmap.fromImage(qimg)
                
            elif len(img_array.shape) == 2:
                h, w = img_array.shape
                qimg = QImage(img_array.data, w, h, QImage.Format_Grayscale8)
                return QPixmap.fromImage(qimg)
                
        except Exception as e:
            print(f"ImageIO loading failed: {e}")
        
        # Try with OpenCV
        try:
            import cv2
            import numpy as np
            
            img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            if img is not None:
                if len(img.shape) == 3:
                    if img.shape[2] == 3:
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
                    elif img.shape[2] == 4:
                        img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)
                elif len(img.shape) == 2:
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGBA)
                
                h, w, c = img.shape
                bytes_per_line = c * w
                qimg = QImage(img.data, w, h, bytes_per_line, QImage.Format_RGBA8888)
                return QPixmap.fromImage(qimg)
        except Exception as e:
            print(f"OpenCV loading failed: {e}")
        
        return None


class ImageViewer(QWidget):
    def __init__(self, image_path: str | None = None):
        super().__init__()
        
        # Window setup
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAcceptDrops(True)

        # Image state
        self.pixmap: QPixmap | None = None
        self.image_path = None
        self.movie: QMovie | None = None
        self.is_animated = False

        # Transform state - разделяем target и current для плавной анимации
        self.target_scale = 1.0
        self.current_scale = 1.0
        self.target_offset = QPointF(0, 0)
        self.current_offset = QPointF(0, 0)
        self.rotation = 0.0
        
        # Zoom limits
        self.min_scale = 0.1
        self.max_scale = 20.0
        self.fit_scale = 1.0  # Масштаб для "поместить в экран"
        
        # Animation parameters
        self.lerp_factor = 0.15  # Скорость сглаживания (чем меньше, тем плавнее)
        self.zoom_sensitivity = 0.001  # Чувствительность зума
        self.pan_friction = 0.88  # Трение для инерции панорамирования
        
        # Interaction state
        self.is_panning = False
        self.last_mouse_pos = QPointF(0, 0)
        self.pan_velocity = QPointF(0, 0)
        self.zoom_center = QPointF(0, 0)
        
        # Opening animation
        self.opening_animation = True
        self.opening_scale = 0.8
        self.opening_opacity = 0.0
        
        # Performance optimization
        self.update_pending = False
        
        # Loading thread
        self.loading_thread: ImageLoader | None = None

        # Main animation timer
        self.timer = QTimer(self)
        self.timer.setInterval(16)  # ~60 FPS
        self.timer.timeout.connect(self.animate)
        self.timer.start()

        # Load image
        if image_path:
            self.load_image(image_path)
        else:
            self.open_dialog_and_load()

    def get_supported_formats(self):
        """Get comprehensive list of supported formats"""
        base_formats = [
            "*.png", "*.jpg", "*.jpeg", "*.bmp", "*.gif", "*.webp", "*.tiff", "*.tif", 
            "*.ico", "*.svg", "*.pbm", "*.pgm", "*.ppm", "*.xbm", "*.xpm"
        ]
        
        raw_formats = [
            "*.cr2", "*.cr3", "*.nef", "*.arw", "*.dng", "*.raf", "*.orf", 
            "*.rw2", "*.pef", "*.srw", "*.x3f", "*.mrw", "*.dcr", "*.kdc", 
            "*.erf", "*.mef", "*.mos", "*.ptx", "*.r3d", "*.fff", "*.iiq"
        ]
        
        modern_formats = ["*.heic", "*.heif", "*.avif", "*.jxl"]
        scientific_formats = ["*.fits", "*.hdr", "*.exr", "*.pic", "*.psd"]
        
        return base_formats + raw_formats + modern_formats + scientific_formats

    def open_dialog_and_load(self):
        formats = self.get_supported_formats()
        filter_str = f"All Supported Images ({' '.join(formats)})"
        
        fname, _ = QFileDialog.getOpenFileName(
            self, "Open image", str(Path.home()), filter_str
        )
        if fname:
            self.load_image(fname)
        else:
            QApplication.instance().quit()

    def load_image(self, path: str):
        """Load image with comprehensive format support"""
        self.image_path = path
        
        # Check for animated GIF
        if path.lower().endswith('.gif'):
            try:
                self.movie = QMovie(path)
                if self.movie.isValid():
                    self.is_animated = True
                    self.movie.jumpToFrame(0)
                    self.pixmap = self.movie.currentPixmap()
                    self._setup_image_display()
                    return
            except:
                pass
        
        # Background loading for other formats
        if self.loading_thread and self.loading_thread.isRunning():
            self.loading_thread.quit()
            self.loading_thread.wait()
        
        self.loading_thread = ImageLoader(path)
        self.loading_thread.imageLoaded.connect(self._on_image_loaded)
        self.loading_thread.loadFailed.connect(self._on_load_failed)
        self.loading_thread.start()

    def _on_image_loaded(self, pixmap: QPixmap):
        """Handle successful image loading"""
        self.pixmap = pixmap
        self.is_animated = False
        self._setup_image_display()

    def _on_load_failed(self, error: str):
        """Handle loading failure"""
        print(f"Failed to load image: {error}")
        print("Supported libraries status:")
        
        libs = ["PIL", "rawpy", "imageio", "cv2", "pillow_heif", "pillow_avif"]
        for lib in libs:
            try:
                __import__(lib)
                print(f"  ✓ {lib}")
            except ImportError:
                print(f"  ✗ {lib}")
        
        print("\nTo install missing libraries:")
        print("pip install pillow rawpy imageio opencv-python pillow-heif pillow-avif-plugin")
        
        QApplication.instance().quit()

    def _setup_image_display(self):
        """Setup display parameters after image is loaded"""
        if not self.pixmap or self.pixmap.isNull():
            return

        # Get screen geometry
        screen_geom = QApplication.primaryScreen().availableGeometry()
        
        # Calculate fit-to-screen scale
        if self.pixmap.width() > 0 and self.pixmap.height() > 0:
            scale_x = (screen_geom.width() * 0.9) / self.pixmap.width()
            scale_y = (screen_geom.height() * 0.9) / self.pixmap.height()
            self.fit_scale = min(scale_x, scale_y, 1.0)
        else:
            self.fit_scale = 1.0

        # Set initial transform
        self.target_scale = self.fit_scale
        self.current_scale = self.fit_scale * 0.8  # Start smaller for opening animation
        
        # Center the image
        screen_center = QPointF(screen_geom.center())
        self.target_offset = screen_center
        self.current_offset = screen_center

        # Setup window
        self.resize(screen_geom.width(), screen_geom.height())
        self.move(screen_geom.topLeft())

        # Reset animation states
        self.opening_animation = True
        self.opening_scale = 0.8
        self.opening_opacity = 0.0
        
        # Reset velocities
        self.pan_velocity = QPointF(0, 0)

        self.schedule_update()

    def get_image_bounds(self) -> QRectF:
        """Get the bounds of the image in screen coordinates"""
        if not self.pixmap:
            return QRectF()
        
        img_w = self.pixmap.width() * self.current_scale
        img_h = self.pixmap.height() * self.current_scale
        
        return QRectF(
            self.current_offset.x() - img_w / 2,
            self.current_offset.y() - img_h / 2,
            img_w,
            img_h
        )

    def point_in_image(self, point: QPointF) -> bool:
        """Check if point is inside the image"""
        bounds = self.get_image_bounds()
        return bounds.contains(point)

    def zoom_to(self, new_scale: float, focus_point: QPointF = None):
        """Zoom to specific scale with focus point"""
        if not self.pixmap:
            return
        
        # Clamp scale
        new_scale = max(self.min_scale, min(self.max_scale, new_scale))
        
        # Determine focus point
        if focus_point is None:
            focus_point = self.current_offset
        elif not self.point_in_image(focus_point):
            # Mouse outside image - focus on image center
            focus_point = self.current_offset
        
        # Calculate the point in image space that should stay under the focus
        old_scale = self.current_scale
        if old_scale > 0:
            # Vector from image center to focus point
            dx = focus_point.x() - self.current_offset.x()
            dy = focus_point.y() - self.current_offset.y()
            
            # How this vector should change with new scale
            scale_ratio = new_scale / old_scale
            new_dx = dx * scale_ratio
            new_dy = dy * scale_ratio
            
            # Calculate new offset to keep focus point fixed
            self.target_offset = QPointF(
                focus_point.x() - new_dx,
                focus_point.y() - new_dy
            )
        
        self.target_scale = new_scale

    def fit_to_screen(self):
        """Fit image to screen"""
        if not self.pixmap:
            return
        
        screen_geom = QApplication.primaryScreen().availableGeometry()
        screen_center = QPointF(screen_geom.center())
        
        self.target_scale = self.fit_scale
        self.target_offset = screen_center

    def wheelEvent(self, e: QWheelEvent):
        """Handle zoom with mouse wheel"""
        if not self.pixmap:
            return
        
        # Get zoom delta
        delta = e.angleDelta().y() / 120.0  # Standard wheel step
        
        # Calculate zoom factor with smooth scaling
        zoom_factor = 1.0 + (delta * 0.15)  # 15% per step
        
        # Apply zoom
        new_scale = self.target_scale * zoom_factor
        self.zoom_to(new_scale, e.position())
        
        e.accept()

    def mousePressEvent(self, e: QMouseEvent):
        """Handle mouse press"""
        if e.button() == Qt.LeftButton:
            if self.point_in_image(e.position()):
                # Start panning
                self.is_panning = True
                self.last_mouse_pos = e.position()
                self.pan_velocity = QPointF(0, 0)
                e.accept()
            else:
                # Click outside image - exit
                QApplication.instance().quit()
        elif e.button() == Qt.RightButton:
            QApplication.instance().quit()

    def mouseMoveEvent(self, e: QMouseEvent):
        """Handle mouse move"""
        if self.is_panning:
            # Calculate movement delta
            delta = e.position() - self.last_mouse_pos
            
            # Apply movement directly to current position for immediate response
            self.current_offset += delta
            self.target_offset = QPointF(self.current_offset)
            
            # Store velocity for inertia
            self.pan_velocity = delta * 0.6
            
            self.last_mouse_pos = e.position()
            self.schedule_update()
            e.accept()

    def mouseReleaseEvent(self, e: QMouseEvent):
        """Handle mouse release"""
        if e.button() == Qt.LeftButton:
            self.is_panning = False
            e.accept()

    def mouseDoubleClickEvent(self, e: QMouseEvent):
        """Handle double click - toggle between fit and 100%"""
        if not self.pixmap:
            return
        
        if abs(self.target_scale - self.fit_scale) < 0.01:
            # Currently at fit scale, zoom to 100%
            self.zoom_to(1.0, e.position())
        else:
            # Zoom to fit
            self.fit_to_screen()
        
        e.accept()

    def animate(self):
        """Main animation loop"""
        needs_update = False
        
        # Opening animation
        if self.opening_animation:
            self.opening_scale += (1.0 - self.opening_scale) * 0.12
            self.opening_opacity += (1.0 - self.opening_opacity) * 0.15
            
            if abs(self.opening_scale - 1.0) < 0.01 and abs(self.opening_opacity - 1.0) < 0.01:
                self.opening_scale = 1.0
                self.opening_opacity = 1.0
                self.opening_animation = False
            
            needs_update = True
        
        # Pan inertia (when not actively panning)
        if not self.is_panning:
            if abs(self.pan_velocity.x()) > 0.1 or abs(self.pan_velocity.y()) > 0.1:
                self.target_offset += self.pan_velocity
                self.pan_velocity *= self.pan_friction
                needs_update = True
            else:
                self.pan_velocity = QPointF(0, 0)
        
        # Smooth interpolation to target values
        scale_diff = self.target_scale - self.current_scale
        offset_diff = self.target_offset - self.current_offset
        
        if abs(scale_diff) > 0.001:
            self.current_scale += scale_diff * self.lerp_factor
            needs_update = True
        else:
            self.current_scale = self.target_scale
        
        if abs(offset_diff.x()) > 0.1 or abs(offset_diff.y()) > 0.1:
            self.current_offset += offset_diff * self.lerp_factor
            needs_update = True
        else:
            self.current_offset = self.target_offset
        
        # Update display if needed
        if needs_update:
            self.schedule_update()

    def schedule_update(self):
        """Schedule update to avoid excessive redraws"""
        if not self.update_pending:
            self.update_pending = True
            QTimer.singleShot(0, self._do_update)

    def _do_update(self):
        """Perform the actual update"""
        self.update_pending = False
        self.update()

    def dragEnterEvent(self, event):
        """Handle drag enter"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Handle file drop"""
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if Path(path).is_file():
                self.load_image(path)

    def keyPressEvent(self, e):
        """Handle keyboard input"""
        if e.key() == Qt.Key_Escape:
            QApplication.instance().quit()
            return

        # Copy to clipboard (Ctrl+C or Ctrl+С)
        if e.modifiers() & Qt.ControlModifier:
            key_text = e.text().lower()
            if e.key() == Qt.Key_C or key_text == 'c' or key_text == 'с':
                if self.pixmap:
                    QGuiApplication.clipboard().setPixmap(self.pixmap)
                return

        # Rotate (R or К)
        key_text = e.text().lower()
        if e.key() == Qt.Key_R or key_text == 'r' or key_text == 'к':
            self.rotation = (self.rotation + 90) % 360
            self.update()
            return
        
        # Fit to screen (F or А)
        if e.key() == Qt.Key_F or key_text == 'f' or key_text == 'а':
            self.fit_to_screen()
            return

        super().keyPressEvent(e)

    def paintEvent(self, event):
        """Main paint event"""
        if not self.pixmap:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Draw dark background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 200))

        # Calculate image dimensions
        img_w = self.pixmap.width() * self.current_scale * self.opening_scale
        img_h = self.pixmap.height() * self.current_scale * self.opening_scale

        # Draw image
        painter.save()
        painter.translate(self.current_offset)
        
        if self.rotation != 0:
            painter.rotate(self.rotation)
        
        if self.opening_animation:
            painter.setOpacity(self.opening_opacity)
        
        # Draw the pixmap centered
        target_rect = QRectF(-img_w / 2, -img_h / 2, img_w, img_h)
        source_rect = QRectF(self.pixmap.rect())
        
        painter.drawPixmap(target_rect, self.pixmap, source_rect)
        painter.restore()

    def closeEvent(self, event):
        """Clean up on close"""
        if self.loading_thread and self.loading_thread.isRunning():
            self.loading_thread.quit()
            self.loading_thread.wait()
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    path = None
    if len(sys.argv) >= 2:
        path = sys.argv[1]

    viewer = ImageViewer(path)
    viewer.show()

    sys.exit(app.exec())