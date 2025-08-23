"""
Enhanced Minimalist Photo Viewer — Optimized Performance Version
Optimized version with improved speed, memory usage, and responsiveness
"""

import sys
import math
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import weakref

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, QThread, Signal, QEasingCurve, QThreadPool, QRunnable
from PySide6.QtGui import (QPixmap, QImageReader, QPainter, QWheelEvent, QMouseEvent,
                           QColor, QImage, QGuiApplication, QMovie, QTransform)
from PySide6.QtWidgets import QApplication, QWidget, QFileDialog


class ImageCache:
    """LRU Cache for loaded images to improve navigation performance"""
    
    def __init__(self, max_size: int = 5):
        self.max_size = max_size
        self.cache: Dict[str, QPixmap] = {}
        self.access_order: List[str] = []
    
    def get(self, path: str) -> Optional[QPixmap]:
        """Get image from cache"""
        if path in self.cache:
            # Move to end (most recently used)
            self.access_order.remove(path)
            self.access_order.append(path)
            return self.cache[path]
        return None
    
    def put(self, path: str, pixmap: QPixmap):
        """Add image to cache"""
        if path in self.cache:
            # Update existing
            self.access_order.remove(path)
        elif len(self.cache) >= self.max_size:
            # Remove least recently used
            lru_path = self.access_order.pop(0)
            del self.cache[lru_path]
        
        self.cache[path] = pixmap
        self.access_order.append(path)
    
    def clear(self):
        """Clear all cached images"""
        self.cache.clear()
        self.access_order.clear()


class PreloadWorker(QRunnable):
    """Background worker for preloading adjacent images"""
    
    def __init__(self, paths: List[str], cache: ImageCache):
        super().__init__()
        self.paths = paths
        self.cache = cache
        self.setAutoDelete(True)
    
    def run(self):
        """Load images in background"""
        for path in self.paths:
            if path not in self.cache.cache:
                try:
                    pixmap = self._load_image_fast(path)
                    if pixmap and not pixmap.isNull():
                        self.cache.put(path, pixmap)
                except Exception:
                    pass  # Silent fail for preloading
    
    def _load_image_fast(self, path: str) -> Optional[QPixmap]:
        """Fast image loading for preloading (no heavy processing)"""
        try:
            # Try Qt native first (fastest)
            reader = QImageReader(path)
            if reader.canRead():
                qimg = reader.read()
                if qimg and not qimg.isNull():
                    return QPixmap.fromImage(qimg)
            
            # Try Pillow for common formats
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
        return None


class OptimizedImageLoader(QThread):
    """Optimized background thread for loading images"""
    imageLoaded = Signal(QPixmap)
    loadFailed = Signal(str)
    
    def __init__(self, path: str, priority: int = 0):
        super().__init__()
        self.path = path
        self.priority = priority  # Higher priority for current image
    
    def run(self):
        try:
            pixmap = self._load_image_optimized(self.path)
            if pixmap and not pixmap.isNull():
                self.imageLoaded.emit(pixmap)
            else:
                self.loadFailed.emit("Failed to load image")
        except Exception as e:
            self.loadFailed.emit(str(e))
    
    def _load_image_optimized(self, path: str) -> Optional[QPixmap]:
        """Optimized image loading with format-specific optimizations"""
        # Quick format detection
        ext = Path(path).suffix.lower()
        
        # Try Qt native first (fastest for supported formats)
        reader = QImageReader(path)
        if reader.canRead():
            # Optimize reading for large images
            if ext in {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}:
                reader.setQuality(85)  # Slightly reduce quality for speed
            qimg = reader.read()
            if qimg and not qimg.isNull():
                return QPixmap.fromImage(qimg)
        
        # Format-specific optimizations
        if ext in {'.cr2', '.cr3', '.nef', '.arw', '.dng'}:
            return self._load_raw_optimized(path)
        elif ext in {'.heic', '.heif'}:
            return self._load_heic_optimized(path)
        elif ext == '.gif':
            return self._load_gif_optimized(path)
        else:
            return self._load_generic_optimized(path)
    
    def _load_raw_optimized(self, path: str) -> Optional[QPixmap]:
        """Optimized RAW loading"""
        try:
            import rawpy
            with rawpy.imread(path) as raw:
                # Use faster postprocessing
                rgb = raw.postprocess(use_camera_wb=True, bright=1.0, 
                                    highlight_mode=rawpy.HighlightMode.BLEND)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            return QPixmap.fromImage(qimg)
        except Exception as e:
            print(f"RAW loading failed: {e}")
            return None
    
    def _load_heic_optimized(self, path: str) -> Optional[QPixmap]:
        """Optimized HEIC loading"""
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
            from PIL import Image
            im = Image.open(path)
            if im.mode != 'RGBA':
                im = im.convert('RGBA')
            data = im.tobytes('raw', 'RGBA')
            qimg = QImage(data, im.width, im.height, QImage.Format_RGBA8888)
            return QPixmap.fromImage(qimg)
        except Exception as e:
            print(f"HEIC loading failed: {e}")
            return None
    
    def _load_gif_optimized(self, path: str) -> Optional[QPixmap]:
        """Optimized GIF loading (first frame only)"""
        try:
            from PIL import Image
            im = Image.open(path)
            if hasattr(im, 'is_animated') and im.is_animated:
                im.seek(0)  # Get first frame only
            if im.mode != 'RGBA':
                im = im.convert('RGBA')
            data = im.tobytes('raw', 'RGBA')
            qimg = QImage(data, im.width, im.height, QImage.Format_RGBA8888)
            return QPixmap.fromImage(qimg)
        except Exception as e:
            print(f"GIF loading failed: {e}")
            return None
    
    def _load_generic_optimized(self, path: str) -> Optional[QPixmap]:
        """Optimized generic loading"""
        try:
            from PIL import Image
            im = Image.open(path)
            if im.mode not in ('RGBA', 'RGB'):
                im = im.convert('RGBA')
            elif im.mode == 'RGB':
                im = im.convert('RGBA')
            data = im.tobytes('raw', 'RGBA')
            qimg = QImage(data, im.width, im.height, QImage.Format_RGBA8888)
            return QPixmap.fromImage(qimg)
        except Exception as e:
            print(f"Generic loading failed: {e}")
            return None


class OptimizedImageViewer(QWidget):
    def __init__(self, image_path: Optional[str] = None):
        super().__init__()
        
        # Window setup
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAcceptDrops(True)

        # Image state
        self.pixmap: Optional[QPixmap] = None
        self.image_path = None
        self.movie: Optional[QMovie] = None
        self.is_animated = False
        
        # Directory navigation with caching
        self.current_directory = None
        self.image_files: List[str] = []
        self.current_index = -1
        self.image_cache = ImageCache(max_size=7)  # Cache more images
        
        # Preloading
        self.preload_threadpool = QThreadPool()
        self.preload_threadpool.setMaxThreadCount(2)  # Limit background threads

        # Transform state - optimized interpolation
        self.target_scale = 1.0
        self.current_scale = 1.0
        self.target_offset = QPointF(0, 0)
        self.current_offset = QPointF(0, 0)
        self.rotation = 0.0
        
        # Zoom limits
        self.min_scale = 0.1
        self.max_scale = 20.0
        self.fit_scale = 1.0
        
        # Optimized animation parameters
        self.lerp_factor = 0.2  # Faster interpolation
        self.zoom_sensitivity = 0.001
        self.pan_friction = 0.85  # Less friction for faster response
        
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
        self.zoom_center = QPointF(0, 0)
        
        # Optimized animation states
        self.opening_animation = True
        self.opening_scale = 0.8
        self.opening_opacity = 0.0
        
        self.closing_animation = False
        self.closing_scale = 1.0
        self.closing_opacity = 1.0
        
        # Background fade
        self.background_opacity = 0.0
        self.target_background_opacity = 200.0
        
        # Performance optimization
        self.update_pending = False
        self.last_update_time = 0
        self.frame_skip_threshold = 16  # Skip frames if too fast
        
        # Loading thread
        self.loading_thread: Optional[OptimizedImageLoader] = None

        # Optimized animation timer
        self.timer = QTimer(self)
        self.timer.setInterval(16)  # 60 FPS
        self.timer.timeout.connect(self.animate)
        self.timer.start()

        # Load image
        if image_path:
            self.load_image(image_path)
        else:
            self.open_dialog_and_load()

    def get_image_files_in_directory(self, directory_path: str) -> List[str]:
        """Get list of supported image files in directory (optimized)"""
        if not directory_path:
            return []
        
        directory = Path(directory_path)
        if not directory.is_dir():
            return []
        
        # Optimized extension set (frozen for faster lookups)
        supported_exts = frozenset({
            '.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff', '.tif', '.ico', '.svg',
            '.pbm', '.pgm', '.ppm', '.xbm', '.xpm',
            '.cr2', '.cr3', '.nef', '.arw', '.dng', '.raf', '.orf', '.rw2', '.pef', '.srw',
            '.x3f', '.mrw', '*.dcr', '*.kdc', '*.erf', '*.mef', '*.mos', '*.ptx', '*.r3d', '*.fff', '*.iiq',
            '.heic', '.heif', '.avif', '.jxl',
            '.fits', '.hdr', '.exr', '.pic', '.psd'
        })
        
        # Use list comprehension for better performance
        try:
            image_files = [
                str(file_path) for file_path in directory.iterdir()
                if file_path.is_file() and file_path.suffix.lower() in supported_exts
            ]
            return sorted(image_files, key=lambda x: Path(x).name.lower())
        except (OSError, PermissionError) as e:
            print(f"Error reading directory {directory_path}: {e}")
            return []

    def setup_directory_navigation(self, image_path: str):
        """Setup directory navigation with preloading"""
        if not image_path:
            return
        
        path_obj = Path(image_path)
        self.current_directory = str(path_obj.parent)
        self.image_files = self.get_image_files_in_directory(self.current_directory)
        
        # Find current image index
        try:
            self.current_index = self.image_files.index(str(path_obj))
        except ValueError:
            self.current_index = -1
        
        # Start preloading adjacent images
        self._preload_adjacent_images()

    def _preload_adjacent_images(self):
        """Preload images adjacent to current one"""
        if not self.image_files or self.current_index == -1:
            return
        
        # Get paths to preload (current ± 2 images)
        preload_paths = []
        for offset in [-2, -1, 1, 2]:
            idx = self.current_index + offset
            if 0 <= idx < len(self.image_files):
                path = self.image_files[idx]
                if path not in self.image_cache.cache:
                    preload_paths.append(path)
        
        if preload_paths:
            worker = PreloadWorker(preload_paths, self.image_cache)
            self.preload_threadpool.start(worker)

    def navigate_to_image(self, direction: int):
        """Navigate to next/previous image with optimized loading"""
        if not self.image_files or self.current_index == -1:
            return
        
        if self.navigation_animation:
            return
        
        new_index = (self.current_index + direction) % len(self.image_files)
        if new_index == self.current_index:
            return
        
        # Check cache first
        new_path = self.image_files[new_index]
        cached_pixmap = self.image_cache.get(new_path)
        
        if cached_pixmap:
            # Use cached image immediately
            self._switch_to_image(new_index, cached_pixmap)
        else:
            # Load from disk
            self._load_for_navigation(new_index, new_path)
    
    def _switch_to_image(self, new_index: int, pixmap: QPixmap):
        """Switch to image immediately (from cache)"""
        self.old_pixmap = self.pixmap
        self.navigation_direction = 1 if new_index > self.current_index else -1
        self.navigation_progress = 0.0
        self.navigation_animation = True
        
        self.current_index = new_index
        self.pixmap = pixmap
        self._setup_image_display()
        
        # Start preloading for new position
        self._preload_adjacent_images()
    
    def _load_for_navigation(self, new_index: int, new_path: str):
        """Load image for navigation"""
        self.old_pixmap = self.pixmap
        self.navigation_direction = 1 if new_index > self.current_index else -1
        self.navigation_progress = 0.0
        self.navigation_animation = True
        
        self.current_index = new_index
        
        # Stop existing thread
        if self.loading_thread and self.loading_thread.isRunning():
            self.loading_thread.quit()
            self.loading_thread.wait()
        
        # Load with high priority
        self.loading_thread = OptimizedImageLoader(new_path, priority=1)
        self.loading_thread.imageLoaded.connect(self._on_navigation_image_loaded)
        self.loading_thread.loadFailed.connect(self._on_load_failed)
        self.loading_thread.start()

    def _on_navigation_image_loaded(self, pixmap: QPixmap):
        """Handle successful navigation image loading"""
        self.new_pixmap = pixmap
        # Cache the loaded image
        if self.current_index >= 0 and self.current_index < len(self.image_files):
            self.image_cache.put(self.image_files[self.current_index], pixmap)

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

    def load_image(self, path: str, is_navigation: bool = False):
        """Load image with optimized loading"""
        self.image_path = path
        
        if not is_navigation:
            self.setup_directory_navigation(path)
        
        # Reset animations
        if self.pixmap and not is_navigation:
            self.opening_animation = True
            self.opening_scale = 0.95
            self.opening_opacity = 0.2
        elif is_navigation:
            self.opening_animation = True
            self.opening_scale = 0.98
            self.opening_opacity = 0.7
        
        # Stop any existing movie
        if self.movie:
            self.movie.stop()
            self.movie = None
            self.is_animated = False
        
        # Check cache first
        cached_pixmap = self.image_cache.get(path)
        if cached_pixmap:
            self._on_image_loaded(cached_pixmap)
            return
        
        # Background loading
        if self.loading_thread and self.loading_thread.isRunning():
            self.loading_thread.quit()
            self.loading_thread.wait()
        
        self.loading_thread = OptimizedImageLoader(path)
        self.loading_thread.imageLoaded.connect(self._on_image_loaded)
        self.loading_thread.loadFailed.connect(self._on_load_failed)
        self.loading_thread.start()

    def _on_image_loaded(self, pixmap: QPixmap):
        """Handle successful image loading"""
        self.pixmap = pixmap
        self.is_animated = False
        
        # Cache the loaded image
        if self.image_path:
            self.image_cache.put(self.image_path, pixmap)
        
        self._setup_image_display()

    def _on_load_failed(self, error: str):
        """Handle loading failure"""
        print(f"Failed to load image: {error}")
        
        if self.navigation_animation:
            self.navigation_animation = False
            self.old_pixmap = None
            self.new_pixmap = None
        
        if not self.pixmap:
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
            QTimer.singleShot(3000, QApplication.instance().quit)

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

    def zoom_to(self, new_scale: float, focus_point: Optional[QPointF] = None):
        """Zoom to specific scale with focus point"""
        if not self.pixmap:
            return
        
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

    def wheelEvent(self, e: QWheelEvent):
        """Handle zoom with mouse wheel"""
        if not self.pixmap:
            return
        
        delta = e.angleDelta().y() / 120.0
        zoom_factor = 1.0 + (delta * 0.15)
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
        
        if abs(self.target_scale - self.fit_scale) < 0.01:
            self.zoom_to(1.0, e.position())
        else:
            self.fit_to_screen()
        
        e.accept()

    def animate(self):
        """Optimized animation loop"""
        import time
        current_time = time.time() * 1000
        
        # Frame rate limiting
        if current_time - self.last_update_time < self.frame_skip_threshold:
            return
        
        self.last_update_time = current_time
        needs_update = False
        
        # Navigation slide animation
        if self.navigation_animation:
            self.navigation_progress += 0.1  # Faster animation
            
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
            self.opening_scale += (1.0 - self.opening_scale) * 0.2  # Faster
            self.opening_opacity += (1.0 - self.opening_opacity) * 0.25  # Faster
            
            if abs(self.opening_scale - 1.0) < 0.01 and abs(self.opening_opacity - 1.0) < 0.01:
                self.opening_scale = 1.0
                self.opening_opacity = 1.0
                self.opening_animation = False
            
            needs_update = True
        
        # Closing animation
        if self.closing_animation:
            target_scale = 0.7
            target_opacity = 0.0
            
            self.closing_scale += (target_scale - self.closing_scale) * 0.3  # Faster
            self.closing_opacity += (target_opacity - self.closing_opacity) * 0.3  # Faster
            
            needs_update = True
        
        # Background fade animation
        if not self.navigation_animation:
            bg_diff = self.target_background_opacity - self.background_opacity
            if abs(bg_diff) > 1.0:
                self.background_opacity += bg_diff * 0.2  # Faster
                needs_update = True
            else:
                self.background_opacity = self.target_background_opacity
        
        # Pan inertia (optimized)
        if not self.is_panning:
            if abs(self.pan_velocity.x()) > 0.1 or abs(self.pan_velocity.y()) > 0.1:
                self.target_offset += self.pan_velocity
                self.pan_velocity *= self.pan_friction
                needs_update = True
            else:
                self.pan_velocity = QPointF(0, 0)
        
        # Optimized interpolation
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
            self.close_application()
            return

        # Navigation with arrow keys
        if e.key() == Qt.Key_Left:
            self.navigate_to_image(-1)
            e.accept()
            return
        elif e.key() == Qt.Key_Right:
            self.navigate_to_image(1)
            e.accept()
            return

        # Copy to clipboard
        if e.modifiers() & Qt.ControlModifier:
            key_text = e.text().lower()
            if e.key() == Qt.Key_C or key_text == 'c' or key_text == 'с':
                if self.pixmap:
                    QGuiApplication.clipboard().setPixmap(self.pixmap)
                return

        # Rotate
        key_text = e.text().lower()
        if e.key() == Qt.Key_R or key_text == 'r' or key_text == 'к':
            self.rotation = (self.rotation + 90) % 360
            self.update()
            return
        
        # Fit to screen
        if (e.key() == Qt.Key_F or key_text == 'f' or key_text == 'а' or 
            e.key() == Qt.Key_Space):
            self.fit_to_screen()
            return

        super().keyPressEvent(e)

    def paintEvent(self, event):
        """Optimized paint event"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Draw dark background
        bg_color = QColor(0, 0, 0, int(self.background_opacity))
        painter.fillRect(self.rect(), bg_color)

        # Navigation slide animation
        if self.navigation_animation and self.old_pixmap and self.new_pixmap:
            self._draw_slide_animation(painter)
        # Normal drawing
        elif self.pixmap:
            self._draw_single_image(painter, self.pixmap)

    def _draw_slide_animation(self, painter):
        """Draw sliding animation between two images"""
        t = self.navigation_progress
        eased_t = 1 - pow(1 - t, 3)
        
        screen_width = self.width()
        slide_distance = screen_width * 1.2
        
        if self.navigation_direction > 0:
            old_x_offset = -slide_distance * eased_t
            new_x_offset = slide_distance * (1 - eased_t)
        else:
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
        
        # Clear cache to free memory
        self.image_cache.clear()
        
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    path = None
    if len(sys.argv) >= 2:
        path = sys.argv[1]

    viewer = OptimizedImageViewer(path)
    viewer.show()

    sys.exit(app.exec())