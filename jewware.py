import sys
import random
import time
import requests
import os
from PIL import Image
import mss

from PyQt6.QtCore import Qt, QTimer, QPoint, QPointF, QRectF, QSize
from PyQt6.QtWidgets import (QApplication, QWidget, QSlider, QComboBox, 
                             QLabel, QHBoxLayout, QVBoxLayout, QFrame, 
                             QCheckBox, QPushButton, QMessageBox, QTabWidget,
                             QLineEdit, QColorDialog, QFileDialog)
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QPixmap, QPolygonF, QImage, QKeyEvent, QIcon

# --- CONSTANTS & STYLING ---
FLAG_BLUE = QColor("#0038A8")
CROSSHAIR_GREEN = QColor("#00FF00")
PANEL_BG = "#1e1e24"
FRAME_BG = "#2d2d34"
ACCENT_BLUE = "#3498db"

DEFAULT_HEBREW_TEXTS = ["שלום", "ישראל", "תל אביב", "ירושלים", "שמחה", "אהבה", "חברות", "חיים"]

class ImmersiveOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.center_angle = 0.0
        self.is_rotating = False
        self.rotation_speed = 240.0  
        
        # Crosshair configurations
        self.crosshair_size = 55
        self.offset_x = 0
        self.offset_y = 0
        self.target_monitor = None
        
        # Flashbang state engine
        self.flash_active = False
        self.flash_opacity = 0.0
        self.flash_duration = 0.6  
        self.flash_start_time = 0.0
        
        # Custom element pools
        self.ambient_texts = list(DEFAULT_HEBREW_TEXTS)
        self.custom_images = [] 
        
        # Configuration rules from panel
        self.text_color = QColor(FLAG_BLUE)
        self.min_text_size = 16
        self.max_text_size = 28
        self.image_display_size = 80
        
        # Separated bouncing sizes
        self.bounce_star_size = 55
        self.bounce_image_size = 55
        
        # SEPARATED TARGET COUNTS
        self.bounce_star_target_count = 4
        self.bounce_image_target_count = 4
        
        self.spawn_text_enabled = True
        self.spawn_star_enabled = True
        self.spawn_image_enabled = True
        
        self.elements = []
        self.bouncing_enabled = True
        self.bouncing_speed_multiplier = 3.0
        self.bouncing_symbols = []
        
        self.pixmap_menorah = None
        self.init_window()
        self.load_external_images()
        
        self.spawn_timer = QTimer(self)
        self.spawn_timer.timeout.connect(self.spawn_element)
        self.spawn_timer.start(300)

    def init_window(self):
        self.setWindowTitle("JewWare Overlay")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |       
            Qt.WindowType.WindowStaysOnTopHint |                     
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.ToolTip | 
            Qt.WindowType.BypassWindowManagerHint 
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def load_external_images(self):
        url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSChDvj-wIzNi3FLl28dcJ_cTa5TYm-YINsCr7m9BwrYw&s=10"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            self.pixmap_menorah = QPixmap()
            self.pixmap_menorah.loadFromData(response.content)
        except Exception:
            self.pixmap_menorah = None

    def trigger_flashbang(self):
        self.flash_active = True
        self.flash_start_time = time.time()
        self.flash_opacity = 1.0
        self.update()

    def spawn_element(self):
        if not self.target_monitor or self.flash_active:
            return
            
        m = self.target_monitor
        rx = random.randint(m['left'] + 50, m['left'] + m['width'] - 100)
        ry = random.randint(m['top'] + 50, m['top'] + m['height'] - 100)
        
        choices = []
        if self.spawn_text_enabled and self.ambient_texts:
            choices.append("text")
        if self.spawn_star_enabled:
            choices.append("star")
        if self.spawn_image_enabled and (self.pixmap_menorah or self.custom_images):
            choices.append("image")
            
        if not choices:
            return
            
        choice = random.choice(choices)
        current_time = time.time()
        
        if choice == "text":
            self.elements.append({
                'type': 'text', 'x': rx, 'y': ry,
                'content': random.choice(self.ambient_texts),
                'size': random.randint(self.min_text_size, self.max_text_size), 
                'spawn_time': current_time
            })
        elif choice == "image":
            img_pool = []
            if self.pixmap_menorah:
                img_pool.append(self.pixmap_menorah)
            img_pool.extend(self.custom_images)
            
            if img_pool:
                raw_img = random.choice(img_pool)
                sz = self.image_display_size
                scaled = raw_img.scaled(sz, sz, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.elements.append({
                    'type': 'image', 'x': rx, 'y': ry,
                    'content': scaled, 'spawn_time': current_time
                })
        elif choice == "star":
            self.elements.append({
                'type': 'star', 'x': rx, 'y': ry,
                'size': random.randint(40, 70),
                'rotation_speed': random.choice([-180, -90, 90, 180]),
                'spawn_time': current_time
            })

    def sync_bouncing_array(self):
        if not self.bouncing_enabled:
            self.bouncing_symbols.clear()
            return
            
        # Count current categories
        stars = [s for s in self.bouncing_symbols if s['type'] == 'star']
        menorahs = [s for s in self.bouncing_symbols if s['type'] == 'menorah']
        
        # Prune if over limits
        while len(stars) > self.bounce_star_target_count:
            stars.pop()
        while len(menorahs) > self.bounce_image_target_count:
            menorahs.pop()
            
        w = self.width() if self.width() > 100 else 1920
        h = self.height() if self.height() > 100 else 1080

        # Refill stars
        while len(stars) < self.bounce_star_target_count:
            stars.append({
                'type': 'star', 'image': None,
                'x': random.uniform(50, w - 100), 'y': random.uniform(50, h - 100),
                'vx': random.choice([-3, -1.5, 1.5, 3]), 'vy': random.choice([-3, -1.5, 1.5, 3]),
                'rot': random.uniform(0, 360), 'rot_vel': random.uniform(40, 110)
            })
            
        # Refill images
        img_pool = []
        if self.pixmap_menorah: img_pool.append(self.pixmap_menorah)
        img_pool.extend(self.custom_images)
        
        if img_pool:
            while len(menorahs) < self.bounce_image_target_count:
                menorahs.append({
                    'type': 'menorah', 'image': random.choice(img_pool),
                    'x': random.uniform(50, w - 100), 'y': random.uniform(50, h - 100),
                    'vx': random.choice([-3, -1.5, 1.5, 3]), 'vy': random.choice([-3, -1.5, 1.5, 3]),
                    'rot': random.uniform(0, 360), 'rot_vel': random.uniform(40, 110)
                })
        
        self.bouncing_symbols = stars + menorahs

    def update_values(self, size, x, y, monitor, rotating, speed):
        self.crosshair_size = size
        self.offset_x = x
        self.offset_y = y
        self.target_monitor = monitor
        self.is_rotating = rotating
        self.rotation_speed = speed
        
        if not rotating:
            self.center_angle = 0.0
            
        if monitor:
            self.setGeometry(monitor['left'], monitor['top'], monitor['width'], monitor['height'])
        self.update()

    def advance_animation(self, dt):
        current_time = time.time()
        
        if self.is_rotating:
            self.center_angle += self.rotation_speed * dt
            self.center_angle %= 360
            
        if self.flash_active:
            elapsed = current_time - self.flash_start_time
            if elapsed >= self.flash_duration:
                self.flash_active = False
                self.flash_opacity = 0.0
            else:
                self.flash_opacity = 1.0 - (elapsed / self.flash_duration)
                
        if self.bouncing_enabled:
            self.sync_bouncing_array()
            w = self.width() if self.width() > 100 else 1920
            h = self.height() if self.height() > 100 else 1080
            mult = self.bouncing_speed_multiplier
            
            for s in self.bouncing_symbols:
                s['x'] += s['vx'] * mult
                s['y'] += s['vy'] * mult
                s['rot'] += s['rot_vel'] * dt
                
                pad = self.bounce_image_size if s['type'] == 'menorah' else self.bounce_star_size
                
                if s['x'] <= 0 or s['x'] >= w - pad:
                    s['vx'] *= -1
                    s['x'] = max(0, min(s['x'], w - pad))
                if s['y'] <= 0 or s['y'] >= h - pad:
                    s['vy'] *= -1
                    s['y'] = max(0, min(s['y'], h - pad))
        else:
            self.bouncing_symbols.clear()
                
        self.elements = [el for el in self.elements if current_time - el['spawn_time'] < 2.0]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        current_time = time.time()

        if not self.target_monitor:
            return

        if not self.flash_active:
            for el in self.elements:
                age = current_time - el['spawn_time']
                opacity = max(0.0, min(1.0, 1.0 - (age / 2.0)))
                painter.setOpacity(opacity)

                local_x = el['x'] - self.geometry().x()
                local_y = el['y'] - self.geometry().y()

                if el['type'] == 'text':
                    painter.setPen(self.text_color)
                    painter.setFont(QFont("Arial", el['size'], QFont.Weight.Bold))
                    painter.drawText(local_x, local_y, el['content'])
                elif el['type'] == 'image':
                    painter.drawPixmap(local_x, local_y, el['content'])
                elif el['type'] == 'star':
                    painter.save()
                    painter.translate(local_x, local_y)
                    painter.rotate(el['rotation_speed'] * age)
                    
                    s = el['size']
                    h_tri = (3**0.5 / 2) * s
                    r = h_tri / 3
                    R = 2 * r
                    
                    painter.setPen(QPen(FLAG_BLUE, 2))
                    painter.drawPolygon(QPolygonF([QPointF(0, -R), QPointF(-(s/2), r), QPointF((s/2), r)]))
                    painter.drawPolygon(QPolygonF([QPointF(0, R), QPointF(-(s/2), -r), QPointF((s/2), -r)]))
                    painter.restore()

        if self.bouncing_enabled and not self.flash_active:
            painter.setOpacity(1.0)
            for s in self.bouncing_symbols:
                painter.save()
                sz = self.bounce_image_size if s['type'] == 'menorah' else self.bounce_star_size
                cx = s['x'] + (sz / 2.0)
                cy = s['y'] + (sz / 2.0)
                painter.translate(cx, cy)
                painter.rotate(s['rot'])
                
                if s['type'] == 'star':
                    h_tri = (3**0.5 / 2) * sz
                    r = h_tri / 3
                    R = 2 * r
                    painter.setPen(QPen(FLAG_BLUE, 3))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawPolygon(QPolygonF([QPointF(0, -R), QPointF(-(sz/2), r), QPointF((sz/2), r)]))
                    painter.drawPolygon(QPolygonF([QPointF(0, R), QPointF(-(sz/2), -r), QPointF((sz/2), -r)]))
                elif s['type'] == 'menorah' and s['image']:
                    scaled = s['image'].scaled(sz, sz, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    painter.drawPixmap(int(-sz/2), int(-sz/2), scaled)
                    
                painter.restore()

        painter.setOpacity(1.0)
        cx = (self.width() / 2.0) + self.offset_x
        cy = (self.height() / 2.0) + self.offset_y
        
        s = self.crosshair_size
        h_tri = (3**0.5 / 2) * s
        r = h_tri / 3
        R = 2 * r
        
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.center_angle)
        
        painter.setPen(QPen(FLAG_BLUE, 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        painter.drawPolygon(QPolygonF([QPointF(0, -R), QPointF(-(s/2.0), r), QPointF((s/2.0), r)]))
        painter.drawPolygon(QPolygonF([QPointF(0, R), QPointF(-(s/2.0), -r), QPointF((s/2.0), -r)]))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(CROSSHAIR_GREEN)
        dot_r = 2.5
        painter.drawEllipse(QRectF(-dot_r, -dot_r, dot_r * 2, dot_r * 2))
        painter.restore()

        if self.flash_active and self.flash_opacity > 0.0:
            painter.setOpacity(self.flash_opacity)
            painter.fillRect(self.rect(), QColor(255, 255, 255))


class ControlPanel(QWidget):
    def __init__(self):
        super().__init__()
        # Keep window present, frameless, and running so shortcuts work flawlessly
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            QWidget {{ background-color: {PANEL_BG}; color: white; font-family: Arial; font-size: 12px; }}
            QFrame#TitleBar {{ background-color: {FRAME_BG}; }}
            QTabBar::tab {{ background: #2d2d34; color: #bbb; padding: 8px 16px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }}
            QTabBar::tab:selected {{ background: {PANEL_BG}; color: white; font-weight: bold; border-bottom: 2px solid {ACCENT_BLUE}; }}
            QTabWidget::panel {{ border: 1px solid #2d2d34; background-color: {PANEL_BG}; }}
            QLineEdit {{ background-color: #2d2d34; border: 1px solid #555; padding: 4px; color: white; border-radius: 3px; }}
            QPushButton {{ background-color: #2d2d34; border: 1px solid #555; padding: 5px 10px; color: white; border-radius: 3px; }}
            QPushButton:hover {{ background-color: #3d3d45; border-color: {ACCENT_BLUE}; }}
        """)
        self.resize(890, 690)
        
        self.sct = mss.mss()
        self.monitors = self.sct.monitors[1:]
        
        self.drag_position = QPoint()
        self.preview_w, self.preview_h = 380, 285
        self.next_flash_time = 0.0
        
        self.target_shortcut_key = Qt.Key.Key_Asterisk  
        self.target_shortcut_text = "*"
        self.is_recording_shortcut = False
        self.is_ui_minimized = False # Virtual invisibility state variable
        
        self.overlay = ImmersiveOverlay()
        
        if self.monitors:
            self.overlay.target_monitor = self.monitors[0]
            
        self.overlay.show()
        self.build_ui()
        
        self.clock = time.time()
        self.last_preview_time = 0.0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_loops)
        self.timer.start(7) 
        
        self.reset_flashbang_scheduler()
        self.sync_to_overlay()

    def build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        title_bar = QFrame()
        title_bar.setObjectName("TitleBar")
        title_bar.setFixedHeight(40)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(15, 0, 0, 0)
        title_layout.setSpacing(0)
        
        title_label = QLabel("Jew-Ware 3000 Premium Edition")
        title_label.setStyleSheet("font-weight: bold; font-size: 13px; color: white; background: transparent;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        minimize_btn = QPushButton("🗕")
        minimize_btn.setFixedSize(45, 40)
        minimize_btn.setStyleSheet("background: transparent; border: none; font-size: 12px; color: white; border-radius: 0px;")
        minimize_btn.clicked.connect(self.toggle_global_ui_visibility)
        title_layout.addWidget(minimize_btn)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(45, 40)
        close_btn.setStyleSheet("background: transparent; border: none; font-size: 14px; color: white; border-radius: 0px;")
        close_btn.clicked.connect(self.close_all)
        title_layout.addWidget(close_btn)
        
        main_layout.addWidget(title_bar)
        
        body_frame = QFrame()
        body_layout = QHBoxLayout(body_frame)
        body_layout.setContentsMargins(15, 15, 15, 15)
        body_layout.setSpacing(15)
        
        self.tabs = QTabWidget()
        
        tab_core = QWidget()
        core_layout = QVBoxLayout(tab_core)
        core_layout.setSpacing(10)
        
        core_layout.addWidget(QLabel("Target Screen Monitor Display:"))
        self.monitor_combo = QComboBox()
        self.monitor_combo.addItems([f"Display {i+1} ({m['width']}x{m['height']})" for i, m in enumerate(self.monitors)])
        self.monitor_combo.currentIndexChanged.connect(self.sync_to_overlay)
        self.monitor_combo.setStyleSheet("background-color: #2d2d34; padding: 4px; border: 1px solid #555; color: white;")
        core_layout.addWidget(self.monitor_combo)
        
        self.spin_checkbox = QCheckBox("Spin Crosshair Active Loop")
        self.spin_checkbox.setChecked(True)
        self.spin_checkbox.stateChanged.connect(self.sync_to_overlay)
        core_layout.addWidget(self.spin_checkbox)
        
        self.speed_slider = self.create_valued_slider(core_layout, "Spin Velocity Speed:", 50, 720, 240, "°/s")
        self.size_slider = self.create_valued_slider(core_layout, "Crosshair Vector Size:", 10, 200, 55, "")
        self.x_slider = self.create_valued_slider(core_layout, "Target Alignment Offset X:", -500, 500, 0, "")
        self.y_slider = self.create_valued_slider(core_layout, "Target Alignment Offset Y:", -500, 500, 0, "")
        core_layout.addStretch()
        
        tab_fx = QWidget()
        fx_layout = QVBoxLayout(tab_fx)
        fx_layout.setSpacing(10)
        
        self.flash_checkbox = QCheckBox("Random Flashbang Interceptor")
        self.flash_checkbox.stateChanged.connect(self.reset_flashbang_scheduler)
        fx_layout.addWidget(self.flash_checkbox)
        
        self.flash_min_slider = self.create_valued_slider(fx_layout, "Flash Random Minimum (Secs):", 1, 60, 5, "s")
        self.flash_max_slider = self.create_valued_slider(fx_layout, "Flash Random Maximum (Secs):", 2, 120, 15, "s")
        
        fx_layout.addWidget(QFrame()) 
        
        self.bounce_checkbox = QCheckBox("Bouncing Israel Symbols Toggle")
        self.bounce_checkbox.setChecked(True)
        self.bounce_checkbox.stateChanged.connect(self.on_bounce_toggle_adjusted)
        fx_layout.addWidget(self.bounce_checkbox)
        
        self.bounce_speed_slider = self.create_valued_slider(fx_layout, "Bouncing Travel Speed Rate:", 1, 15, 3, "x")
        
        # SEPARATED COUNTS
        self.bounce_star_count_slider = self.create_valued_slider(fx_layout, "Bouncing Symbols (Stars) Count:", 0, 30, 4, "")
        self.bounce_image_count_slider = self.create_valued_slider(fx_layout, "Bouncing Images (Menorahs) Count:", 0, 30, 4, "")
        
        # SEPARATED SIZES
        self.bounce_star_size_slider = self.create_valued_slider(fx_layout, "Bouncing Symbols (Stars) Size:", 15, 200, 55, "px")
        self.bounce_image_size_slider = self.create_valued_slider(fx_layout, "Bouncing Images (Menorahs) Size:", 15, 200, 55, "px")
        
        fx_layout.addWidget(QFrame())
        
        self.fps_slider = self.create_valued_slider(fx_layout, "Refresh Smoothness Engine Rate:", 10, 144, 144, " FPS")
        fx_layout.addStretch()
        
        tab_custom = QWidget()
        custom_layout = QVBoxLayout(tab_custom)
        custom_layout.setSpacing(10)
        
        hk_hbox = QHBoxLayout()
        hk_hbox.addWidget(QLabel("Hide / Show Toggle Hotkey Shortcut:"))
        self.btn_shortcut_binder = QPushButton("*")
        self.btn_shortcut_binder.clicked.connect(self.initiate_shortcut_recording)
        self.btn_shortcut_binder.setStyleSheet("background-color: #27ae60; font-weight: bold;")
        hk_hbox.addWidget(self.btn_shortcut_binder)
        custom_layout.addLayout(hk_hbox)
        
        tgl_row = QHBoxLayout()
        self.chk_txt = QCheckBox("Spawn Text")
        self.chk_txt.setChecked(True)
        self.chk_txt.stateChanged.connect(self.update_overlay_rules)
        self.chk_star = QCheckBox("Spawn Stars")
        self.chk_star.setChecked(True)
        self.chk_star.stateChanged.connect(self.update_overlay_rules)
        self.chk_img = QCheckBox("Spawn Images")
        self.chk_img.setChecked(True)
        self.chk_img.stateChanged.connect(self.update_overlay_rules)
        tgl_row.addWidget(self.chk_txt)
        tgl_row.addWidget(self.chk_star)
        tgl_row.addWidget(self.chk_img)
        custom_layout.addLayout(tgl_row)
        
        txt_settings = QHBoxLayout()
        btn_color = QPushButton("Pick Text Color")
        btn_color.clicked.connect(self.pick_text_color_dialog)
        txt_settings.addWidget(btn_color)
        custom_layout.addLayout(txt_settings)
        
        self.txt_min_sz = self.create_valued_slider(custom_layout, "Min Font Display Size:", 8, 48, 16, "px")
        self.txt_max_sz = self.create_valued_slider(custom_layout, "Max Font Display Size:", 12, 72, 28, "px")
        self.img_sz_slider = self.create_valued_slider(custom_layout, "Random Spawner Images Scale:", 20, 200, 80, "px")
        
        add_text_layout = QHBoxLayout()
        self.text_input_field = QLineEdit()
        self.text_input_field.setPlaceholderText("Enter custom text / Hebrew phrase...")
        btn_add_txt = QPushButton("Add Word")
        btn_add_txt.clicked.connect(self.append_custom_string)
        add_text_layout.addWidget(self.text_input_field)
        add_text_layout.addWidget(btn_add_txt)
        custom_layout.addLayout(add_text_layout)
        
        btn_upload_img = QPushButton("Add Custom Image File (.png/.jpg)")
        btn_upload_img.clicked.connect(self.upload_custom_image_file)
        custom_layout.addWidget(btn_upload_img)
        custom_layout.addStretch()
        
        self.tabs.addTab(tab_core, "Core Align")
        self.tabs.addTab(tab_fx, "FX Engines")
        self.tabs.addTab(tab_custom, "Custom Pools")
        
        body_layout.addWidget(self.tabs, 1)
        
        self.preview_canvas = QLabel()
        self.preview_canvas.setFixedSize(self.preview_w, self.preview_h)
        self.preview_canvas.setStyleSheet("background-color: black; border: 1px solid #555;")
        self.preview_canvas.mousePressEvent = self.canvas_mouse_event
        self.preview_canvas.mouseMoveEvent = self.canvas_mouse_event
        body_layout.addWidget(self.preview_canvas)
        
        main_layout.addWidget(body_frame)

    def create_valued_slider(self, layout, label_text, min_val, max_val, default_val, suffix=""):
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel(label_text))
        val_lbl = QLabel(f"{default_val}{suffix}")
        val_lbl.setStyleSheet("color: #3498db; font-weight: bold;")
        hbox.addWidget(val_lbl, 0, Qt.AlignmentFlag.AlignRight)
        layout.addLayout(hbox)
        
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        
        def value_updated(v):
            val_lbl.setText(f"{v}{suffix}")
            self.on_slider_change()
            self.update_overlay_rules()
            
        slider.valueChanged.connect(value_updated)
        layout.addWidget(slider)
        return slider

    def keyPressEvent(self, event: QKeyEvent):
        if self.is_recording_shortcut:
            self.target_shortcut_key = event.key()
            self.target_shortcut_text = event.text()
            key_name = event.text().upper() if event.text() else f"KEY {event.key()}"
            
            if event.key() == Qt.Key.Key_F12: key_name = "F12"
            elif event.key() == Qt.Key.Key_F11: key_name = "F11"
            elif event.key() == Qt.Key.Key_F10: key_name = "F10"
            elif event.key() == Qt.Key.Key_F9: key_name = "F9"
            elif event.key() == Qt.Key.Key_Asterisk or event.text() == "*": key_name = "*"
            
            self.btn_shortcut_binder.setText(key_name)
            self.btn_shortcut_binder.setStyleSheet("background-color: #27ae60; font-weight: bold;")
            self.is_recording_shortcut = False
            event.accept()
            return

        is_asterisk = (event.key() == Qt.Key.Key_Asterisk or event.text() == "*" or 
                       (self.target_shortcut_text == "*" and event.text() == "*"))
        
        if is_asterisk or event.key() == self.target_shortcut_key:
            self.toggle_global_ui_visibility()
            event.accept()
            return
            
        super().keyPressEvent(event)

    def initiate_shortcut_recording(self):
        self.is_recording_shortcut = True
        self.btn_shortcut_binder.setText("[ PRESS ANY KEY ]")
        self.btn_shortcut_binder.setStyleSheet("background-color: #e74c3c; font-weight: bold;")

    def toggle_global_ui_visibility(self):
        # FIX: Instead of minimizing/hiding the window (which kills input listening),
        # we slide the window opacity to 0% and toggle flags so the hotkey still works cleanly!
        if self.is_ui_minimized:
            self.setWindowOpacity(1.0)
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
            self.show()
            self.activateWindow()
            self.is_ui_minimized = False
        else:
            self.setWindowOpacity(0.0)
            # Makes it non-interactive to clicks while invisible, but keeps keyboard focus
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowTransparentForInput)
            self.show()
            self.is_ui_minimized = True

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def canvas_mouse_event(self, event):
        idx = self.monitor_combo.currentIndex()
        if idx >= len(self.monitors): return
        m = self.monitors[idx]
        
        dx = event.position().x() - (self.preview_w / 2.0)
        dy = event.position().y() - (self.preview_h / 2.0)
        
        scale_x = m['width'] / self.preview_w
        scale_y = m['height'] / self.preview_h
        
        real_x = int(dx * scale_x)
        real_y = int(dy * scale_y)
        
        real_x = max(-500, min(500, real_x))
        real_y = max(-500, min(500, real_y))
        
        self.x_slider.setValue(real_x)
        self.y_slider.setValue(real_y)

    def on_slider_change(self):
        self.sync_to_overlay()

    def on_bounce_toggle_adjusted(self):
        self.overlay.bouncing_enabled = self.bounce_checkbox.isChecked()
        self.sync_to_overlay()

    def pick_text_color_dialog(self):
        color = QColorDialog.getColor(self.overlay.text_color, self, "Select Text Ambient Color")
        if color.isValid():
            self.overlay.text_color = color

    def append_custom_string(self):
        text = self.text_input_field.text().strip()
        if text:
            self.overlay.ambient_texts.append(text)
            self.text_input_field.clear()

    def upload_custom_image_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Custom Symbol Image Asset", "", "Images (*.png *.jpg *.jpeg)")
        if file_path and os.path.exists(file_path):
            pm = QPixmap(file_path)
            if not pm.isNull():
                self.overlay.custom_images.append(pm)

    def update_overlay_rules(self):
        self.overlay.spawn_text_enabled = self.chk_txt.isChecked()
        self.overlay.spawn_star_enabled = self.chk_star.isChecked()
        self.overlay.spawn_image_enabled = self.chk_img.isChecked()
        
        min_v = self.txt_min_sz.value()
        max_v = self.txt_max_sz.value()
        if min_v >= max_v:
            max_v = min_v + 2
            self.txt_max_sz.setValue(max_v)
            
        self.overlay.min_text_size = min_v
        self.overlay.max_text_size = max_v
        self.overlay.image_display_size = self.img_sz_slider.value()
        
        # Bind separated sizes
        self.overlay.bounce_star_size = self.bounce_star_size_slider.value()
        self.overlay.bounce_image_size = self.bounce_image_size_slider.value()
        
        # Bind separated counts
        self.overlay.bounce_star_target_count = self.bounce_star_count_slider.value()
        self.overlay.bounce_image_target_count = self.bounce_image_count_slider.value()
        
        self.overlay.bouncing_speed_multiplier = float(self.bounce_speed_slider.value())
        
        desired_fps = self.fps_slider.value()
        new_interval = int(1000 / desired_fps)
        if self.timer.interval() != new_interval:
            self.timer.setInterval(new_interval)

    def on_flash_slider_adjusted(self):
        if self.flash_min_slider.value() >= self.flash_max_slider.value():
            self.flash_max_slider.setValue(self.flash_min_slider.value() + 1)

    def reset_flashbang_scheduler(self):
        self.on_flash_slider_adjusted()
        if self.flash_checkbox.isChecked():
            wait_time = random.uniform(self.flash_min_slider.value(), self.flash_max_slider.value())
            self.next_flash_time = time.time() + wait_time
        self.sync_to_overlay()

    def sync_to_overlay(self):
        idx = self.monitor_combo.currentIndex()
        if idx < len(self.monitors):
            self.overlay.update_values(
                self.size_slider.value(),
                self.x_slider.value(),
                self.y_slider.value(),
                self.monitors[idx],
                self.spin_checkbox.isChecked(),
                self.speed_slider.value()
            )

    def update_loops(self):
        now = time.time()
        dt = now - self.clock
        self.clock = now
        
        if self.flash_checkbox.isChecked() and now >= self.next_flash_time:
            self.overlay.trigger_flashbang()
            self.reset_flashbang_scheduler()
            
        self.overlay.advance_animation(dt)
        self.generate_spinning_taskbar_icon()
        
        if now - self.last_preview_time >= 0.066:
            self.render_live_preview()
            self.last_preview_time = now

    def generate_spinning_taskbar_icon(self):
        try:
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.translate(32, 32)
            painter.rotate(self.overlay.center_angle)
            
            s = 42
            h_tri = (3**0.5 / 2) * s
            r = h_tri / 3
            R = 2 * r
            
            painter.setPen(QPen(FLAG_BLUE, 5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolygon(QPolygonF([QPointF(0, -R), QPointF(-(s/2), r), QPointF((s/2), r)]))
            painter.drawPolygon(QPolygonF([QPointF(0, R), QPointF(-(s/2), -r), QPointF((s/2), -r)]))
            painter.end()
            
            self.setWindowIcon(QIcon(pixmap))
        except Exception:
            pass

    def render_live_preview(self):
        idx = self.monitor_combo.currentIndex()
        if idx >= len(self.monitors) or self.is_ui_minimized: return
        m = self.monitors[idx]
        
        try:
            sct_img = self.sct.grab(m)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            img = img.resize((self.preview_w, self.preview_h), Image.Resampling.NEAREST)
            
            qimg = QImage(img.tobytes(), img.size[0], img.size[1], QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            scale_x = self.preview_w / m['width']
            scale_y = self.preview_h / m['height']
            
            pcx = (self.preview_w / 2.0) + (self.x_slider.value() * scale_x)
            pcy = (self.preview_h / 2.0) + (self.y_slider.value() * scale_y)
            
            s = self.size_slider.value() * ((scale_x + scale_y) / 2.0)
            h_tri = (3**0.5 / 2) * s
            r = h_tri / 3
            R = 2 * r
            
            painter.save()
            painter.translate(pcx, pcy)
            painter.rotate(self.overlay.center_angle)
            
            painter.setPen(QPen(FLAG_BLUE, 2))
            painter.drawPolygon(QPolygonF([QPointF(0, -R), QPointF(-(s/2), r), QPointF((s/2), r)]))
            painter.drawPolygon(QPolygonF([QPointF(0, R), QPointF(-(s/2), -r), QPointF((s/2), -r)]))
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(CROSSHAIR_GREEN)
            painter.drawEllipse(QRectF(-2, -2, 4, 4))
            painter.restore()
            
            if self.overlay.flash_active:
                painter.setOpacity(self.overlay.flash_opacity)
                painter.fillRect(pixmap.rect(), QColor(255, 255, 255))
                
            painter.end()
            self.preview_canvas.setPixmap(pixmap)
        except Exception:
            pass

    def close_all(self):
        self.overlay.close()
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    warn_text = (
        "made by DaVibeCodah: github.com/DaVibeCodah" 
        "\n\n\n\nPHOTOSENSITIVITY / EPILEPSY WARNING\n\n"
        "This software contains rapid changes in brightness, dynamic animations, "
        "and random bright white full-screen flashes (Flashbang feature).\n\n"
        "If you have a history of epilepsy, seizures, or photosensitivity, "
        "please click Cancel to abort immediately. Do you wish to proceed?"
    )
    
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Warning)
    msg_box.setWindowTitle("Epilepsy Warning - Jew-Ware 3000")
    msg_box.setText(warn_text)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
    msg_box.setDefaultButton(QMessageBox.StandardButton.Cancel)
    msg_box.setStyleSheet("background-color: #1e1e24; color: white; QPushButton { background-color: #2d2d34; color: white; min-width: 70px; padding: 4px; border: 1px solid #555; }")
    
    if msg_box.exec() != QMessageBox.StandardButton.Ok:
        sys.exit(0)

    app.setStyleSheet("""
        QSlider::groove:horizontal { height: 6px; background: #2d2d34; border-radius: 3px; }
        QSlider::handle:horizontal { background: #3498db; width: 14px; margin-top: -4px; margin-bottom: -4px; border-radius: 7px; }
        QCheckBox { color: white; }
        QCheckBox::indicator { width: 14px; height: 14px; background-color: #2d2d34; border: 1px solid #555; }
        QCheckBox::indicator:checked { background-color: #3498db; }
    """)
    
    panel = ControlPanel()
    panel.show()
    sys.exit(app.exec())
