import os
import sys
from PIL import Image
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QSizePolicy, QGroupBox
)
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QImage

class WallpaperCropper(QMainWindow):
    def __init__(self):
        super().__init__()
        # Basic properties
        self.current_image = None
        self.monitors = self.get_monitor_info()
        self.dragging = False
        self.drag_start = None
        self.crop_rect = None
        self.resize_handle = None
        self.handle_size = 5
        self.resize_mode = None
        
        # Calculate total width and height of monitors
        self.total_width = sum(monitor.width() for monitor in self.monitors)
        self.total_height = max(monitor.height() for monitor in self.monitors)
        # Calculate the aspect ratio based on both monitors
        self.target_aspect_ratio = self.total_width / self.total_height
        
        # Initialize caching properties
        self.cached_scaled_pixmap = None
        self.last_label_size = None
        self._preview_counter = 0
        
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Dual Monitor Wallpaper Cropper')
        self.setGeometry(100, 100, 1200, 800)
        
        # Modern dark theme styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
            }
            QPushButton {
                background-color: #2d89ef;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3999ff;
            }
            QPushButton:pressed {
                background-color: #2076d8;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
            QGroupBox {
                color: #ffffff;
                border: 2px solid #333333;
                border-radius: 10px;
                margin-top: 1.5em;
                padding: 15px;
                background-color: #242424;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                padding: 0 15px;
                color: #2d89ef;
                font-weight: bold;
                font-size: 14px;
            }
        """)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(25)
        layout.setContentsMargins(30, 30, 30, 30)

        # Create image display area with modern styling
        self.image_label = QLabel()
        self.image_label.setMinimumSize(800, 400)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #242424;
                border-radius: 10px;
                border: 2px solid #333333;
            }
        """)
        layout.addWidget(self.image_label)

        # Create preview area with modern styling
        preview_layout = QHBoxLayout()
        preview_layout.setSpacing(20)
        
        # Left monitor preview
        preview_group1 = QGroupBox(f"Monitor 1 ({self.monitor_info[0]['resolution']} - {self.monitor_info[0]['ratio']})")
        preview_layout1 = QVBoxLayout(preview_group1)
        preview_layout1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Create a container widget for the bezel effect
        left_container = QWidget()
        left_container.setStyleSheet("""
            QWidget {
                background-color: #242424;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        left_container_layout = QVBoxLayout(left_container)
        left_container_layout.setContentsMargins(10, 10, 10, 10)
        
        self.left_preview = QLabel()
        self.left_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_preview.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border: none;
            }
        """)
        left_container_layout.addWidget(self.left_preview)
        preview_layout1.addWidget(left_container)
        
        # Right monitor preview
        preview_group2 = QGroupBox(f"Monitor 2 ({self.monitor_info[1]['resolution']} - {self.monitor_info[1]['ratio']})")
        preview_layout2 = QVBoxLayout(preview_group2)
        preview_layout2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Create a container widget for the bezel effect
        right_container = QWidget()
        right_container.setStyleSheet("""
            QWidget {
                background-color: #242424;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        right_container_layout = QVBoxLayout(right_container)
        right_container_layout.setContentsMargins(10, 10, 10, 10)
        
        self.right_preview = QLabel()
        self.right_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.right_preview.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border: none;
            }
        """)
        right_container_layout.addWidget(self.right_preview)
        preview_layout2.addWidget(right_container)
        
        preview_layout.addWidget(preview_group1)
        preview_layout.addWidget(preview_group2)
        layout.addLayout(preview_layout)

        # Create button layout with modern styling
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        # Load button
        load_button = QPushButton('Load Image')
        load_button.setCursor(Qt.CursorShape.PointingHandCursor)
        load_button.setMinimumWidth(150)
        button_layout.addWidget(load_button)
        load_button.clicked.connect(self.load_image)
        
        # Save button
        save_button = QPushButton('Save')
        save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        save_button.setMinimumWidth(150)
        button_layout.addWidget(save_button)
        save_button.clicked.connect(self.split_and_save)
        
        # Exit button
        exit_button = QPushButton('Exit')
        exit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        exit_button.setMinimumWidth(150)
        exit_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;  /* Red color for exit */
            }
            QPushButton:hover {
                background-color: #e04755;
            }
            QPushButton:pressed {
                background-color: #c82333;
            }
        """)
        button_layout.addWidget(exit_button)
        exit_button.clicked.connect(self.close)  # Qt's built-in close method
        
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Setup event handling
        self.image_label.mousePressEvent = self.mouse_press_event
        self.image_label.mouseMoveEvent = self.mouse_move_event
        self.image_label.mouseReleaseEvent = self.mouse_release_event

        # Update preview sizes to match monitor aspect ratio
        single_monitor_ratio = self.total_width / (2 * self.total_height)  # Divide by 2 for single monitor
        preview_width = 320  # Base width
        preview_height = int(preview_width / single_monitor_ratio)
        
        self.left_preview.setFixedSize(preview_width, preview_height)
        self.right_preview.setFixedSize(preview_width, preview_height)

        # Set margins for preview layouts
        preview_layout1.setContentsMargins(15, 25, 15, 15)
        preview_layout2.setContentsMargins(15, 25, 15, 15)

    def get_monitor_info(self):
        """Get information about connected monitors"""
        monitors = []
        for screen in QApplication.screens():
            geometry = screen.geometry()
            monitors.append(geometry)
            # Store additional info about each monitor
            self.monitor_info = []
            for screen in QApplication.screens():
                info = {
                    'geometry': screen.geometry(),
                    'resolution': f"{screen.geometry().width()}x{screen.geometry().height()}",
                    'ratio': f"{screen.geometry().width()}/{screen.geometry().height()}"
                }
                self.monitor_info.append(info)
        return monitors

    def load_image(self):
        """Load an image file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_path:
            try:
                print(f"Loading image from: {file_path}")
                self.current_image = Image.open(file_path)
                print(f"Image loaded successfully. Size: {self.current_image.size}, Mode: {self.current_image.mode}")
                
                # Reset caching properties
                self.cached_scaled_pixmap = None
                self.last_label_size = None
                
                # Initialize crop rectangle
                image_rect = self.get_image_display_rect()
                self.crop_rect = self.calculate_initial_crop_rect(image_rect)
                
                # Force a complete update
                self._do_update()
                
            except Exception as e:
                print(f"Error loading image: {str(e)}")
                import traceback
                traceback.print_exc()

    def _do_update(self):
        """Perform the actual display update"""
        if not self.current_image:
            print("No image loaded")
            return

        try:
            current_size = (self.image_label.width(), self.image_label.height())
            
            # Initialize cached_scaled_pixmap if needed
            if self.cached_scaled_pixmap is None or self.last_label_size != current_size:
                pixmap = self.pil_to_pixmap(self.current_image)
                if pixmap and not pixmap.isNull():
                    self.cached_scaled_pixmap = pixmap.scaled(
                        self.image_label.width(),
                        self.image_label.height(),
                        Qt.AspectRatioMode.KeepAspectRatio
                    )
                    self.last_label_size = current_size
                else:
                    return
            
            # Create display pixmap
            display_pixmap = QPixmap(self.image_label.size())
            display_pixmap.fill(QColor('#2a2a2a'))
            
            # Draw the cached scaled image
            painter = QPainter(display_pixmap)
            if self.cached_scaled_pixmap and not self.cached_scaled_pixmap.isNull():
                x = (self.image_label.width() - self.cached_scaled_pixmap.width()) // 2
                y = (self.image_label.height() - self.cached_scaled_pixmap.height()) // 2
                painter.drawPixmap(x, y, self.cached_scaled_pixmap)
            
                # Draw crop rectangle and handles
                if self.crop_rect:
                    # Set up semi-transparent white fill
                    painter.setBrush(QColor(255, 255, 255, 30))  # Last parameter is alpha (0-255)
                    painter.setPen(QPen(QColor('#ffffff'), 2))  # White border
                    painter.drawRect(self.crop_rect)
                    
                    # Draw middle line
                    middle_x = self.crop_rect.x() + self.crop_rect.width() // 2
                    painter.setPen(QPen(QColor('#ffffff'), 1, Qt.PenStyle.DashLine))  # Dashed white line
                    painter.drawLine(
                        middle_x, 
                        self.crop_rect.top(),
                        middle_x, 
                        self.crop_rect.bottom()
                    )
                    
                    # Draw resize handles
                    handle_size = self.handle_size
                    painter.setPen(QPen(QColor('#ffffff'), 1))
                    painter.setBrush(QColor('#ffffff'))  # Solid white handles
                    
                    corners = [
                        self.crop_rect.topLeft(),
                        self.crop_rect.topRight(),
                        self.crop_rect.bottomRight(),
                        self.crop_rect.bottomLeft()
                    ]
                    
                    for corner in corners:
                        painter.drawRect(
                            corner.x() - handle_size, 
                            corner.y() - handle_size,
                            handle_size * 2, 
                            handle_size * 2
                        )
            
            painter.end()
            self.image_label.setPixmap(display_pixmap)
            
            # Update previews with reduced frequency during dragging
            if not self.dragging or self._preview_counter == 0:
                self.update_cropped_previews(self.crop_rect)
            self._preview_counter = (self._preview_counter + 1) % 3
                
        except Exception as e:
            print(f"Error in _do_update: {str(e)}")
            import traceback
            traceback.print_exc()

    def get_image_display_rect(self):
        """Get the rectangle where the image is actually displayed"""
        if not self.current_image:
            return QRect()

        # Convert PIL image to QPixmap for display
        pixmap = self.pil_to_pixmap(self.current_image)
        
        # Calculate scaled dimensions
        scaled_pixmap = pixmap.scaled(
            self.image_label.width(),
            self.image_label.height(),
            Qt.AspectRatioMode.KeepAspectRatio
        )
        
        # Calculate position to center the image
        x = (self.image_label.width() - scaled_pixmap.width()) // 2
        y = (self.image_label.height() - scaled_pixmap.height()) // 2
        
        return QRect(x, y, scaled_pixmap.width(), scaled_pixmap.height())

    def calculate_initial_crop_rect(self, image_rect):
        """Calculate initial crop rectangle position and size"""
        # Calculate the target height and width maintaining monitor aspect ratio
        if image_rect.width() / image_rect.height() > self.target_aspect_ratio:
            # Image is wider than needed, constrain by height
            rect_height = int(image_rect.height() * 0.8)  # Use 80% of available height
            rect_width = int(rect_height * self.target_aspect_ratio)
        else:
            # Image is taller than needed, constrain by width
            rect_width = int(image_rect.width() * 0.8)  # Use 80% of available width
            rect_height = int(rect_width / self.target_aspect_ratio)
        
        # Center the rectangle in the image
        x = image_rect.x() + (image_rect.width() - rect_width) // 2
        y = image_rect.y() + (image_rect.height() - rect_height) // 2
        
        return QRect(x, y, rect_width, rect_height)

    def get_resize_handle(self, pos):
        """Determine if position is on a resize handle"""
        if not self.crop_rect:
            return None
        
        # Define handle regions including edges, not just corners
        handle_hit_size = self.handle_size * 3
        handles = {
            'top_left': QRect(
                self.crop_rect.left() - handle_hit_size,
                self.crop_rect.top() - handle_hit_size,
                handle_hit_size * 2,
                handle_hit_size * 2
            ),
            'top': QRect(
                self.crop_rect.left() + handle_hit_size,
                self.crop_rect.top() - handle_hit_size,
                self.crop_rect.width() - handle_hit_size * 2,
                handle_hit_size * 2
            ),
            'top_right': QRect(
                self.crop_rect.right() - handle_hit_size,
                self.crop_rect.top() - handle_hit_size,
                handle_hit_size * 2,
                handle_hit_size * 2
            ),
            'right': QRect(
                self.crop_rect.right() - handle_hit_size,
                self.crop_rect.top() + handle_hit_size,
                handle_hit_size * 2,
                self.crop_rect.height() - handle_hit_size * 2
            ),
            'bottom_right': QRect(
                self.crop_rect.right() - handle_hit_size,
                self.crop_rect.bottom() - handle_hit_size,
                handle_hit_size * 2,
                handle_hit_size * 2
            ),
            'bottom': QRect(
                self.crop_rect.left() + handle_hit_size,
                self.crop_rect.bottom() - handle_hit_size,
                self.crop_rect.width() - handle_hit_size * 2,
                handle_hit_size * 2
            ),
            'bottom_left': QRect(
                self.crop_rect.left() - handle_hit_size,
                self.crop_rect.bottom() - handle_hit_size,
                handle_hit_size * 2,
                handle_hit_size * 2
            ),
            'left': QRect(
                self.crop_rect.left() - handle_hit_size,
                self.crop_rect.top() + handle_hit_size,
                handle_hit_size * 2,
                self.crop_rect.height() - handle_hit_size * 2
            )
        }
        
        for handle_name, handle_rect in handles.items():
            if handle_rect.contains(pos):
                return handle_name
        return None

    def mouse_press_event(self, event):
        """Handle mouse press events"""
        pos = event.pos()
        
        # Check if clicking on a resize handle
        self.resize_mode = self.get_resize_handle(pos)
        if self.resize_mode:
            self.dragging = True
            self.drag_start = pos
            return
        
        # Check if clicking inside crop rectangle for moving
        if self.crop_rect:
            # Create a slightly larger rect for hit testing
            hit_rect = QRect(self.crop_rect)
            hit_rect.adjust(-5, -5, 5, 5)  # Expand hit area by 5 pixels in each direction
            if hit_rect.contains(pos):
                self.dragging = True
                self.resize_mode = None  # Indicate we're moving, not resizing
                self.drag_start = pos
                return

    def mouse_move_event(self, event):
        """Handle mouse move events"""
        if not self.dragging or not self.drag_start:
            return

        pos = event.pos()
        delta = pos - self.drag_start
        image_rect = self.get_image_display_rect()

        if self.resize_mode:
            new_rect = QRect(self.crop_rect)
            
            # Calculate aspect ratio constraints
            min_width = 200
            min_height = int(min_width / self.target_aspect_ratio)
            
            # Handle different resize modes including edges
            if 'left' in self.resize_mode:
                new_left = max(image_rect.left(), 
                             min(new_rect.left() + delta.x(), 
                                 new_rect.right() - min_width))
                width_change = new_rect.left() - new_left
                new_rect.setLeft(int(new_left))
                
                # Maintain aspect ratio
                height_change = width_change / self.target_aspect_ratio
                if 'top' in self.resize_mode:
                    new_rect.setTop(int(new_rect.top() - height_change))
                elif 'bottom' in self.resize_mode:
                    new_rect.setBottom(int(new_rect.bottom() + height_change))
                else:
                    # Center vertically
                    new_rect.setTop(int(new_rect.top() - height_change/2))
                    new_rect.setBottom(int(new_rect.bottom() + height_change/2))
            
            elif 'right' in self.resize_mode:
                new_right = min(image_rect.right(), 
                              max(new_rect.right() + delta.x(), 
                                  new_rect.left() + min_width))
                width_change = new_right - new_rect.right()
                new_rect.setRight(int(new_right))
                
                # Maintain aspect ratio
                height_change = width_change / self.target_aspect_ratio
                if 'top' in self.resize_mode:
                    new_rect.setTop(int(new_rect.top() - height_change))
                elif 'bottom' in self.resize_mode:
                    new_rect.setBottom(int(new_rect.bottom() + height_change))
                else:
                    # Center vertically
                    new_rect.setTop(int(new_rect.top() - height_change/2))
                    new_rect.setBottom(int(new_rect.bottom() + height_change/2))
            
            elif 'top' in self.resize_mode:
                new_top = max(image_rect.top(), 
                             min(new_rect.top() + delta.y(), 
                                 new_rect.bottom() - min_height))
                height_change = new_rect.top() - new_top
                new_rect.setTop(int(new_top))
                
                # Maintain aspect ratio
                width_change = height_change * self.target_aspect_ratio
                new_rect.setLeft(int(new_rect.left() - width_change/2))
                new_rect.setRight(int(new_rect.right() + width_change/2))
            
            elif 'bottom' in self.resize_mode:
                new_bottom = min(image_rect.bottom(), 
                               max(new_rect.bottom() + delta.y(), 
                                   new_rect.top() + min_height))
                height_change = new_bottom - new_rect.bottom()
                new_rect.setBottom(int(new_bottom))
                
                # Maintain aspect ratio
                width_change = height_change * self.target_aspect_ratio
                new_rect.setLeft(int(new_rect.left() - width_change/2))
                new_rect.setRight(int(new_rect.right() + width_change/2))
            
            # Regular dragging (moving the rectangle)
            else:
                # Keep rectangle within image bounds
                new_x = new_rect.x() + delta.x()
                new_y = new_rect.y() + delta.y()
                
                # Constrain to image boundaries
                if new_x < image_rect.left():
                    new_x = image_rect.left()
                elif new_x + new_rect.width() > image_rect.right():
                    new_x = image_rect.right() - new_rect.width()
                    
                if new_y < image_rect.top():
                    new_y = image_rect.top()
                elif new_y + new_rect.height() > image_rect.bottom():
                    new_y = image_rect.bottom() - new_rect.height()
                
                new_rect.moveTopLeft(QPoint(int(new_x), int(new_y)))

            # Ensure the rectangle stays within bounds and maintains minimum size
            if (new_rect.width() >= min_width and 
                new_rect.height() >= min_height and
                image_rect.contains(new_rect)):
                self.crop_rect = new_rect
        else:
            # Handle moving the entire rectangle
            new_rect = QRect(self.crop_rect)
            new_x = new_rect.x() + delta.x()
            new_y = new_rect.y() + delta.y()
            
            # Constrain to image boundaries
            if new_x < image_rect.left():
                new_x = image_rect.left()
            elif new_x + new_rect.width() > image_rect.right():
                new_x = image_rect.right() - new_rect.width()
                
            if new_y < image_rect.top():
                new_y = image_rect.top()
            elif new_y + new_rect.height() > image_rect.bottom():
                new_y = image_rect.bottom() - new_rect.height()
            
            new_rect.moveTopLeft(QPoint(int(new_x), int(new_y)))
            self.crop_rect = new_rect

        self.drag_start = pos
        self.update_display()

    def mouse_release_event(self, event):
        """Handle mouse release events"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.drag_start = None
            self.resize_mode = None  # Reset resize mode

    def split_and_save(self):
        """Split and save the wallpaper"""
        if not self.current_image:
            return

        try:
            # Get the image display area and crop rectangle
            image_rect = self.get_image_display_rect()
            if not self.crop_rect:
                return

            # Get original image dimensions
            orig_width, orig_height = self.current_image.size
            
            # Calculate scaling factors from display coordinates to original image
            scale_x = orig_width / image_rect.width()
            scale_y = orig_height / image_rect.height()

            # Calculate crop coordinates in original image space
            x1 = max(0, int((self.crop_rect.x() - image_rect.x()) * scale_x))
            y1 = max(0, int((self.crop_rect.y() - image_rect.y()) * scale_y))
            x2 = min(orig_width, int((self.crop_rect.right() - image_rect.x()) * scale_x))
            y2 = min(orig_height, int((self.crop_rect.bottom() - image_rect.y()) * scale_y))

            # Calculate the middle point for splitting
            middle_x = x1 + (x2 - x1) // 2

            # Crop left and right portions
            monitor1_crop = self.current_image.crop((x1, y1, middle_x, y2))
            monitor2_crop = self.current_image.crop((middle_x, y1, x2, y2))

            # Save dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Wallpapers", "", "Images (*.png *.jpg *.jpeg)"
            )
            
            if file_path:
                # Split the file path to add suffixes
                base_name = os.path.splitext(file_path)[0]
                ext = os.path.splitext(file_path)[1]
                
                # Save both images
                monitor1_path = f"{base_name}_left{ext}"
                monitor2_path = f"{base_name}_right{ext}"
                
                monitor1_crop.save(monitor1_path)
                monitor2_crop.save(monitor2_path)
                
                print(f"Saved wallpapers:\n{monitor1_path}\n{monitor2_path}")

        except Exception as e:
            print(f"Error in split_and_save: {str(e)}")
            import traceback
            traceback.print_exc()

    def pil_to_pixmap(self, pil_image):
        """Convert PIL image to QPixmap"""
        try:
            # Ensure image is in RGB mode
            if pil_image.mode != "RGB":
                print(f"Converting image from {pil_image.mode} to RGB")  # Debug print
                pil_image = pil_image.convert("RGB")
            
            # Get image data
            width, height = pil_image.size
            bytes_per_line = 3 * width
            
            # Convert PIL image to QImage
            image_data = pil_image.tobytes("raw", "RGB")
            qimage = QImage(image_data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            
            if qimage.isNull():
                raise ValueError("Failed to create QImage")
            
            # Convert QImage to QPixmap
            pixmap = QPixmap.fromImage(qimage)
            
            if pixmap.isNull():
                raise ValueError("Failed to create QPixmap")
            
            return pixmap
            
        except Exception as e:
            print(f"Error in pil_to_pixmap: {str(e)}")
            import traceback
            traceback.print_exc()
            return QPixmap()

    def update_cropped_previews(self, rect):
        """Update preview windows with split monitor views"""
        if not self.current_image or not rect or not self.cached_scaled_pixmap:
            return

        try:
            # Get the actual image display area
            image_rect = self.get_image_display_rect()
            
            # Calculate relative position within the image rect
            rel_x = rect.x() - image_rect.x()
            rel_y = rect.y() - image_rect.y()
            
            # Split the crop rectangle exactly in half for dual monitors
            half_width = rect.width() // 2
            
            # Create left and right crop rectangles relative to the scaled image
            left_rect = QRect(
                rel_x,
                rel_y,
                half_width,
                rect.height()
            )
            
            right_rect = QRect(
                rel_x + half_width,  # Start from middle
                rel_y,
                half_width,
                rect.height()
            )
            
            # Create preview pixmaps from the correct portions of the scaled image
            if (left_rect.right() <= self.cached_scaled_pixmap.width() and 
                right_rect.right() <= self.cached_scaled_pixmap.width()):
                left_preview = self.cached_scaled_pixmap.copy(left_rect)
                right_preview = self.cached_scaled_pixmap.copy(right_rect)
                
                # Get preview dimensions that match monitor aspect ratio
                single_monitor_ratio = self.total_width / (2 * self.total_height)  # Single monitor ratio
                preview_width = self.left_preview.width()
                preview_height = int(preview_width / single_monitor_ratio)
                
                # Scale previews to match preview window size
                left_preview = left_preview.scaled(
                    preview_width,
                    preview_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                right_preview = right_preview.scaled(
                    preview_width,
                    preview_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                # Set the previews directly
                self.left_preview.setPixmap(left_preview)
                self.right_preview.setPixmap(right_preview)
                
        except Exception as e:
            print(f"Error updating previews: {str(e)}")
            import traceback
            traceback.print_exc()

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if not self.crop_rect:
            return
        
        step = 1
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            step = 10
        
        if event.key() == Qt.Key.Key_Left:
            self.crop_rect.moveLeft(max(
                self.get_image_display_rect().left(),
                self.crop_rect.left() - step
            ))
        # ... similar for other arrow keys ...
        
        self.update_display()

    def update_display(self):
        """Update the main display with crop rectangle and handles"""
        if not self.current_image:
            return

        # Use QTimer for smoother updates during dragging
        if hasattr(self, '_update_timer'):
            self._update_timer.stop()
        
        if self.dragging:
            # Reduce update frequency during dragging
            if not hasattr(self, '_update_timer'):
                self._update_timer = QTimer()
                self._update_timer.timeout.connect(self._do_update)
            self._update_timer.start(16)  # ~60 FPS
        else:
            self._do_update()

def main():
    app = QApplication(sys.argv)
    window = WallpaperCropper()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 