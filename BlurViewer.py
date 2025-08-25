"""
BlurViewer v0.8-alpha
Professional image viewer with advanced format support and smooth animations
"""

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, QThread, Signal
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
        
        # Try Qt native formats first
        reader = QImageReader(path)
        if reader.canRead():
            qimg = reader.read()
            if qimg and not qimg.isNull():
                return QPixmap.fromImage(qimg)
        
        # Special handling for GIF via Pillow
        if path.lower().endswith('.gif'):
            try:
                from PIL import Image
                im = Image.open(path)
                
                if hasattr(im, 'is_animated') and im.is_animated:
                    im.seek(0)
                
                if im.mode != 'RGBA':
                    im = im.convert('RGBA')
                
                data = im.tobytes('raw', 'RGBA')
                qimg = QImage(data, im.width, im.height, QImage.Format_RGBA8888)
                if not qimg.isNull():
                    return QPixmap.fromImage(qimg)
            except Exception:
                pass
        
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
            except Exception:
                pass
        
        # Try with Pillow for other formats
        try:
            from PIL import Image
            im = Image.open(path)
            
            if im.mode not in ('RGBA', 'RGB'):
                im = im.convert('RGBA')
            elif im.mode == 'RGB':
                im = im.convert('RGBA')
                
            data = im.tobytes('raw', 'RGBA')
            qimg = QImage(data, im.width, im.height, QImage.Format_RGBA8888)
            if not qimg.isNull():
                return QPixmap.fromImage(qimg)
        except Exception:
            pass
        
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
                
        except Exception:
            pass
        
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
        except Exception:
            pass
        
        return None


class BlurViewer(QWidget):
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
        self.rotation = 0.0
        
        # Directory navigation
        self.current_directory = None
        self.image_files = []
        self.current_index = -1

        # Transform state
        self.target_scale = 1.0
        self.current_scale = 1.0
        self.target_offset = QPointF(0, 0)
        self.current_offset = QPointF(0, 0)
        self.fit_scale = 1.0
        
        # Zoom limits
        self.min_scale = 0.1
        self.max_scale = 20.0
        
        # Animation parameters
        self.lerp_factor = 0.15
        self.pan_friction = 0.88
        
        # Navigation animation
        self.navigation_animation = False
        self.navigation_direction = 0
        self.navigation_progress = 0.0
        self.old_pixmap = None
        self.new_pixmap = None
        
        # Interaction state
        self.is_panning = False
        self.last_mouse_pos = QPointF(0, 0)
        self.pan_velocity = QPointF(0, 0)
        
        # Opening animation
        self.opening_animation = True
        self.opening_scale = 0.8
        self.opening_opacity = 0.0
        
        # Closing animation
        self.closing_animation = False
        self.closing_scale = 1.0
        self.closing_opacity = 1.0
        
        # Background fade
        self.background_opacity = 0.0
        self.target_background_opacity = 200.0
        
        # Fullscreen state
        self.is_fullscreen = False
        self.saved_scale = 1.0
        self.saved_offset = QPointF(0, 0)
        
        # Performance optimization
        self.update_pending = False
        self.loading_thread: ImageLoader | None = None

        # Main animation timer
        self.timer = QTimer(self)
        self.timer.setInterval(16)  # 60 FPS
        self.timer.timeout.connect(self.animate)
        self.timer.start()

        # Load image
        if image_path:
            self.load_image(image_path)
        else:
            self.open_dialog_and_load()

    def get_image_files_in_directory(self, directory_path: str):
        """Get list of supported image files in directory"""
        if not directory_path:
            return []
        
        directory = Path(directory_path)
        if not directory.is_dir():
            return []
        
        # Supported extensions
        supported_exts = {
            '.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff', '.tif', '.ico', '.svg',
            '.pbm', '.pgm', '.ppm', '.xbm', '.xpm',
            '.cr2', '.cr3', '.nef', '.arw', '.dng', '.raf', '.orf', '.rw2', '.pef', '.srw',
            '.x3f', '.mrw', '.dcr', '.kdc', '.erf', '.mef', '.mos', '.ptx', '.r3d', '.fff', '.iiq',
            '.heic', '.heif', '.avif', '.jxl',
            '.fits', '.hdr', '.exr', '.pic', '.psd'
        }
        
        image_files = []
        try:
            for file_path in directory.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in supported_exts:
                    image_files.append(str(file_path))
        except (OSError, PermissionError):
            return []
        
        return sorted(image_files, key=lambda x: Path(x).name.lower())

    def setup_directory_navigation(self, image_path: str):
        """Setup directory navigation for the current image"""
        if not image_path:
            return
        
        path_obj = Path(image_path)
        self.current_directory = str(path_obj.parent)
        self.image_files = self.get_image_files_in_directory(self.current_directory)
        
        try:
            self.current_index = self.image_files.index(str(path_obj))
        except ValueError:
            self.current_index = -1

    def navigate_to_image(self, direction: int):
        """Navigate to next/previous image in directory"""
        if not self.image_files or self.current_index == -1 or self.navigation_animation:
            return
        
        new_index = (self.current_index + direction) % len(self.image_files)
        if new_index == self.current_index:
            return
        
        # Setup slide animation only in windowed mode
        if not self.is_fullscreen:
            self.old_pixmap = self.pixmap
            self.navigation_direction = direction
            self.navigation_progress = 0.0
            self.navigation_animation = True
        
        self.current_index = new_index
        new_path = self.image_files[self.current_index]
        
        # Load new image in background
        if self.loading_thread and self.loading_thread.isRunning():
            self.loading_thread.quit()
            self.loading_thread.wait()
        
        self.loading_thread = ImageLoader(new_path)
        self.loading_thread.imageLoaded.connect(self._on_navigation_image_loaded)
        self.loading_thread.loadFailed.connect(self._on_load_failed)
        self.loading_thread.start()
    
    def _on_navigation_image_loaded(self, pixmap: QPixmap):
        """Handle successful navigation image loading"""
        if self.is_fullscreen:
            # Instant change in fullscreen mode
            self.pixmap = pixmap
            self.rotation = 0.0
            self._fit_to_fullscreen_instant()
        else:
            # Use slide animation in windowed mode
            self.new_pixmap = pixmap
            self.rotation = 0.0
            screen_geom = QApplication.primaryScreen().availableGeometry()
            screen_center = QPointF(screen_geom.center())
            self.target_offset = screen_center

    def close_application(self):
        """Start closing animation and exit"""
        if not self.closing_animation:
            self.closing_animation = True
            self.target_background_opacity = 0.0
            QTimer.singleShot(500, QApplication.instance().quit)

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
            QTimer.singleShot(0, QApplication.instance().quit)

    def load_image(self, path: str):
        """Load image with comprehensive format support"""
        self.image_path = path
        self.setup_directory_navigation(path)
        
        # Reset animations
        if self.pixmap:
            self.opening_animation = True
            self.opening_scale = 0.95
            self.opening_opacity = 0.2
        
        # Stop any existing movie
        if self.movie:
            self.movie.stop()
            self.movie = None
        
        # Background loading
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
        self.rotation = 0.0
        self._setup_image_display()

    def _on_load_failed(self, error: str):
        """Handle loading failure"""
        if self.navigation_animation:
            self.navigation_animation = False
            self.old_pixmap = None
            self.new_pixmap = None
        
        if not self.pixmap:
            print("Failed to load image. Install required libraries:")
            print("pip install pillow rawpy imageio opencv-python pillow-heif pillow-avif-plugin")
            QTimer.singleShot(3000, QApplication.instance().quit)

    def _setup_image_display(self):
        """Setup display parameters after image is loaded"""
        if not self.pixmap or self.pixmap.isNull():
            return

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
        self.current_scale = self.fit_scale * 0.8
        
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
        self.background_opacity = 0.0
        self.target_background_opacity = 200.0
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

    def _calculate_effective_dimensions(self):
        """Calculate effective image dimensions considering rotation"""
        if self.rotation % 180 == 90:  # 90° or 270°
            return self.pixmap.height(), self.pixmap.width()
        else:  # 0° or 180°
            return self.pixmap.width(), self.pixmap.height()

    def zoom_to(self, new_scale: float, focus_point: QPointF = None):
        """Zoom to specific scale with focus point"""
        if not self.pixmap:
            return
        
        # Restrict zoom in fullscreen mode
        if self.is_fullscreen:
            screen_geom = QApplication.primaryScreen().geometry()
            if self.pixmap.width() > 0 and self.pixmap.height() > 0:
                effective_width, effective_height = self._calculate_effective_dimensions()
                scale_x = screen_geom.width() / effective_width
                scale_y = screen_geom.height() / effective_height
                min_fullscreen_scale = min(scale_x, scale_y)
                new_scale = max(min_fullscreen_scale, new_scale)
        
        # Clamp scale
        new_scale = max(self.min_scale, min(self.max_scale, new_scale))
        
        # Determine focus point
        if focus_point is None:
            focus_point = self.current_offset
        elif not self.point_in_image(focus_point):
            focus_point = self.current_offset
        
        # Calculate the point in image space that should stay under the focus
        old_scale = self.current_scale
        if old_scale > 0:
            dx = focus_point.x() - self.current_offset.x()
            dy = focus_point.y() - self.current_offset.y()
            
            scale_ratio = new_scale / old_scale
            new_dx = dx * scale_ratio
            new_dy = dy * scale_ratio
            
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

    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        self.is_fullscreen = not self.is_fullscreen
        
        if self.is_fullscreen:
            self.saved_scale = self.target_scale
            self.saved_offset = QPointF(self.target_offset)
            self.showFullScreen()
            self.target_background_opacity = 250.0
            self._fit_to_fullscreen()
        else:
            self.showNormal()
            screen_geom = QApplication.primaryScreen().availableGeometry()
            self.resize(screen_geom.width(), screen_geom.height())
            self.move(screen_geom.topLeft())
            self.target_scale = self.saved_scale
            self.target_offset = self.saved_offset
            self.target_background_opacity = 200.0

    def _fit_to_fullscreen(self):
        """Fit image to fullscreen with animation"""
        if not self.pixmap:
            return
        
        screen_geom = QApplication.primaryScreen().geometry()
        screen_center = QPointF(screen_geom.center())
        
        if self.pixmap.width() > 0 and self.pixmap.height() > 0:
            effective_width, effective_height = self._calculate_effective_dimensions()
            scale_x = screen_geom.width() / effective_width
            scale_y = screen_geom.height() / effective_height
            fit_scale = min(scale_x, scale_y)
        else:
            fit_scale = 1.0
        
        self.target_scale = fit_scale
        self.target_offset = screen_center

    def _fit_to_fullscreen_instant(self):
        """Fit image to fullscreen instantly without animation"""
        if not self.pixmap:
            return
        
        screen_geom = QApplication.primaryScreen().geometry()
        screen_center = QPointF(screen_geom.center())
        
        if self.pixmap.width() > 0 and self.pixmap.height() > 0:
            effective_width, effective_height = self._calculate_effective_dimensions()
            scale_x = screen_geom.width() / effective_width
            scale_y = screen_geom.height() / effective_height
            fit_scale = min(scale_x, scale_y)
        else:
            fit_scale = 1.0
        
        self.target_scale = fit_scale
        self.current_scale = fit_scale
        self.target_offset = screen_center
        self.current_offset = screen_center
        self.schedule_update()

    def wheelEvent(self, e: QWheelEvent):
        """Handle zoom with mouse wheel"""
        if not self.pixmap:
            return
        
        delta = e.angleDelta().y() / 120.0
        zoom_factor = 1.0 + (delta * 0.15)  # 15% per step
        new_scale = self.target_scale * zoom_factor
        self.zoom_to(new_scale, e.position())
        e.accept()

    def mousePressEvent(self, e: QMouseEvent):
        """Handle mouse press"""
        if e.button() == Qt.LeftButton:
            if self.point_in_image(e.position()):
                self.is_panning = True
                self.last_mouse_pos = e.position()
                self.pan_velocity = QPointF(0, 0)
                e.accept()
            else:
                # Exit only in windowed mode
                if not self.is_fullscreen:
                    self.close_application()
        elif e.button() == Qt.RightButton:
            self.close_application()

    def mouseMoveEvent(self, e: QMouseEvent):
        """Handle mouse move"""
        if self.is_panning:
            delta = e.position() - self.last_mouse_pos
            self.current_offset += delta
            self.target_offset = QPointF(self.current_offset)
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
        
        if self.is_fullscreen:
            screen_geom = QApplication.primaryScreen().geometry()
            if self.pixmap.width() > 0 and self.pixmap.height() > 0:
                effective_width, effective_height = self._calculate_effective_dimensions()
                scale_x = screen_geom.width() / effective_width
                scale_y = screen_geom.height() / effective_height
                fullscreen_fit_scale = min(scale_x, scale_y)
                
                if abs(self.current_scale - fullscreen_fit_scale) < 0.01:
                    self.zoom_to(1.0, e.position())
                else:
                    self._fit_to_fullscreen()
            e.accept()
            return
        
        if abs(self.target_scale - self.fit_scale) < 0.01:
            self.zoom_to(1.0, e.position())
        else:
            self.fit_to_screen()
        
        e.accept()

    def animate(self):
        """Main animation loop"""
        needs_update = False
        
        # Navigation slide animation
        if self.navigation_animation:
            self.navigation_progress += 0.08
            
            if self.navigation_progress >= 1.0:
                self.navigation_progress = 1.0
                self.navigation_animation = False
                
                if self.new_pixmap:
                    self.pixmap = self.new_pixmap
                    self.new_pixmap = None
                self.old_pixmap = None
                
            needs_update = True
        
        # Opening animation
        if self.opening_animation:
            self.opening_scale += (1.0 - self.opening_scale) * 0.15
            self.opening_opacity += (1.0 - self.opening_opacity) * 0.2
            
            if abs(self.opening_scale - 1.0) < 0.01 and abs(self.opening_opacity - 1.0) < 0.01:
                self.opening_scale = 1.0
                self.opening_opacity = 1.0
                self.opening_animation = False
            
            needs_update = True
        
        # Closing animation
        if self.closing_animation:
            target_scale = 0.7
            target_opacity = 0.0
            
            self.closing_scale += (target_scale - self.closing_scale) * 0.25
            self.closing_opacity += (target_opacity - self.closing_opacity) * 0.25
            
            needs_update = True
        
        # Background fade animation
        if not self.navigation_animation:
            bg_diff = self.target_background_opacity - self.background_opacity
            if abs(bg_diff) > 1.0:
                self.background_opacity += bg_diff * 0.15
                needs_update = True
            else:
                self.background_opacity = self.target_background_opacity
        
        # Pan inertia
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
            self.close_application()
            return

        if e.key() == Qt.Key_F11:
            self.toggle_fullscreen()
            e.accept()
            return

        # Directory navigation with A and D keys
        key_text = e.text().lower()
        if e.key() == Qt.Key_A or key_text == 'a' or key_text == 'ф':
            self.navigate_to_image(-1)
            e.accept()
            return
        elif e.key() == Qt.Key_D or key_text == 'd' or key_text == 'в':
            self.navigate_to_image(1)
            e.accept()
            return

        # Zoom with +/- keys
        if e.key() == Qt.Key_Plus or e.key() == Qt.Key_Equal:
            if self.pixmap:
                screen_geom = QApplication.primaryScreen().availableGeometry()
                screen_center = QPointF(screen_geom.center())
                new_scale = self.target_scale * 1.2
                self.zoom_to(new_scale, screen_center)
            e.accept()
            return
        elif e.key() == Qt.Key_Minus:
            if self.pixmap:
                screen_geom = QApplication.primaryScreen().availableGeometry()
                screen_center = QPointF(screen_geom.center())
                new_scale = self.target_scale / 1.2
                self.zoom_to(new_scale, screen_center)
            e.accept()
            return

        # Copy to clipboard
        if e.modifiers() & Qt.ControlModifier:
            if e.key() == Qt.Key_C or key_text == 'c' or key_text == 'с':
                if self.pixmap:
                    QGuiApplication.clipboard().setPixmap(self.pixmap)
                return

        # Rotate
        if e.key() == Qt.Key_R or key_text == 'r' or key_text == 'к':
            self.rotation = (self.rotation + 90) % 360
            if self.is_fullscreen:
                self._fit_to_fullscreen_instant()
            else:
                self.update()
            return
        
        # Fit to screen
        if (e.key() == Qt.Key_F or key_text == 'f' or key_text == 'а' or 
            e.key() == Qt.Key_Space):
            if self.is_fullscreen:
                self._fit_to_fullscreen()
            else:
                self.fit_to_screen()
            return

        super().keyPressEvent(e)

    def paintEvent(self, event):
        """Main paint event"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Draw dark background with smooth fade
        bg_color = QColor(0, 0, 0, int(self.background_opacity))
        painter.fillRect(self.rect(), bg_color)

        # Navigation slide animation
        if self.navigation_animation and self.old_pixmap and self.new_pixmap:
            self._draw_slide_animation(painter)
        elif self.pixmap:
            self._draw_single_image(painter, self.pixmap)

    def _draw_slide_animation(self, painter):
        """Draw sliding animation between two images"""
        t = self.navigation_progress
        eased_t = 1 - pow(1 - t, 3)  # Ease out cubic
        
        screen_width = self.width()
        slide_distance = screen_width * 1.2
        
        if self.navigation_direction > 0:  # Right arrow - move left
            old_x_offset = -slide_distance * eased_t
            new_x_offset = slide_distance * (1 - eased_t)
        else:  # Left arrow - move right
            old_x_offset = slide_distance * eased_t
            new_x_offset = -slide_distance * (1 - eased_t)
        
        # Draw old image
        painter.save()
        painter.translate(old_x_offset, 0)
        painter.setOpacity(1.0 - eased_t * 0.3)
        self._draw_single_image(painter, self.old_pixmap)
        painter.restore()
        
        # Draw new image
        painter.save()
        painter.translate(new_x_offset, 0)
        painter.setOpacity(0.7 + eased_t * 0.3)
        self._draw_single_image(painter, self.new_pixmap)
        painter.restore()

    def _draw_single_image(self, painter, pixmap):
        """Draw a single image with current transforms"""
        if not pixmap or pixmap.isNull():
            return

        # Calculate image dimensions
        final_scale = self.current_scale
        if self.opening_animation:
            final_scale *= self.opening_scale
        elif self.closing_animation:
            final_scale *= self.closing_scale
            
        img_w = pixmap.width() * final_scale
        img_h = pixmap.height() * final_scale

        # Draw image
        painter.save()
        painter.translate(self.current_offset)
        
        if self.rotation != 0:
            painter.rotate(self.rotation)
        
        # Set opacity for animations
        current_opacity = painter.opacity()
        if self.opening_animation:
            painter.setOpacity(current_opacity * self.opening_opacity)
        elif self.closing_animation:
            painter.setOpacity(current_opacity * self.closing_opacity)
        
        # Draw the pixmap centered
        target_rect = QRectF(-img_w / 2, -img_h / 2, img_w, img_h)
        source_rect = QRectF(pixmap.rect())
        
        painter.drawPixmap(target_rect, pixmap, source_rect)
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

    viewer = BlurViewer(path)
    viewer.show()

    sys.exit(app.exec())