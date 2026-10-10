import sys
import os
import json
import threading
import requests
import keyboard
import subprocess
from rapidfuzz import fuzz
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QMetaObject, pyqtSlot
from PyQt6.QtGui import QPixmap, QIcon, QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLineEdit, QLabel, QFrame, QPushButton, QScrollArea,
    QSystemTrayIcon, QMenu
)

CURRENT_VERSION = "1.0"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

# ==========================================
# СТИЛИ И КОНСТАНТЫ
# ==========================================
COLOR_BG_MAIN = "rgba(20, 20, 20, 248)"
COLOR_BG_CARD = "rgba(255, 255, 255, 8)"
COLOR_BORDER = "#2b2b2b"
COLOR_BORDER_HOVER = "#27272a"
COLOR_ACCENT = "#EFCC68"
COLOR_TEXT_MAIN = "#ffffff"
COLOR_TEXT_MUTED = "#a1a1aa"
COLOR_TEXT_DIM = "#71717a"
COLOR_TEXT_INACTIVE = "#898989"
COLOR_STAR_INACTIVE = "#52525b"

STYLE_CARD = f"background-color: {COLOR_BG_CARD}; border-radius: 12px; border: 1px solid {COLOR_BORDER};"
STYLE_LABEL_TRANSPARENT = "background: transparent; border: none;"

CONFIG_FILE = resource_path("config.json")
KEYWORDS_MAP_FILE = resource_path(os.path.join("database", "keywords_map.json"))

custom_keywords = {}
if os.path.exists(KEYWORDS_MAP_FILE):
    with open(KEYWORDS_MAP_FILE, "r", encoding="utf-8") as f:
        custom_keywords = json.load(f)

def load_initial_config():
    hotkey, hw_accel = "alt+w", True
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                hotkey = cfg.get("hotkey", hotkey)
                hw_accel = cfg.get("hardware_acceleration", hw_accel)
        except Exception:
            pass
    return hotkey, hw_accel

def check_remote_status():
    url = "https://raw.githubusercontent.com/JeWebcool/Webcool-RP-Helper/refs/heads/main/status.json"
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            if not data.get("active", True):
                sys.exit(0)
            if data.get("version", "1.0") != CURRENT_VERSION:
                download_url = data.get("download_url")
                if download_url:
                    exe_path = sys.executable
                    new_exe_path = exe_path + ".new"
                    r = requests.get(download_url, stream=True)
                    if r.status_code == 200:
                        with open(new_exe_path, "wb") as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                        bat_path = os.path.join(os.path.dirname(exe_path), "update.bat")
                        with open(bat_path, "w", encoding="utf-8") as bat:
                            bat.write(f"""
                            @echo off
                            timeout /t 2 /nobreak > nul
                            move /y "{new_exe_path}" "{exe_path}"
                            start "" "{exe_path}"
                            del "%~f0"
                            """)
                        subprocess.Popen(bat_path, shell=True)
                        sys.exit(0)
    except Exception as e:
        print(f"Ошибка проверки обновлений: {e}")


class LawCard(QFrame):
    clicked_signal = pyqtSignal(object)

    def __init__(self, law_code: str, article_num: str, article_data: dict, active: bool = False, parent=None):
        super().__init__(parent)
        self.is_active = active
        self.article_data = article_data
        
        text_content = article_data.get("text", "") or article_data.get("name", "") or article_data.get("chapter", "")
        self.setFixedSize(300, 85)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        
        self.code_lbl = QLabel(law_code)
        self.code_lbl.setFixedHeight(18)
        self.code_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.code_lbl)
        
        self.article_lbl = QLabel(str(article_num))
        self.article_lbl.setFixedHeight(18)
        header_layout.addWidget(self.article_lbl)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        if len(text_content) > 70:
            text_content = text_content[:70].strip() + "..."
            
        self.text_lbl = QLabel(text_content)
        self.text_lbl.setWordWrap(True)
        self.text_lbl.setFixedHeight(30)
        layout.addWidget(self.text_lbl)
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_style()

    def setActive(self, active: bool):
        self.is_active = active
        self.update_style()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.clicked_signal.emit(self)

    def update_style(self):
        if self.is_active:
            self.setStyleSheet("LawCard { background-color: rgba(255, 255, 255, 18); border-radius: 12px; }")
            self.code_lbl.setStyleSheet(f"{STYLE_LABEL_TRANSPARENT} background-color: {COLOR_BORDER}; color: {COLOR_TEXT_MAIN}; font-family: 'Roboto'; font-size: 9px; font-weight: bold; border-radius: 6px; padding: 0px 6px;")
            self.article_lbl.setStyleSheet(f"{STYLE_LABEL_TRANSPARENT} color: {COLOR_ACCENT}; font-family: 'Roboto'; font-size: 11px; font-weight: bold;")
            self.text_lbl.setStyleSheet(f"{STYLE_LABEL_TRANSPARENT} color: {COLOR_TEXT_MAIN}; font-family: 'Roboto'; font-size: 10px;")
        else:
            self.setStyleSheet("LawCard { background-color: transparent; border-radius: 12px; } LawCard:hover { background-color: rgba(255, 255, 255, 8); border-radius: 10px; }")
            self.code_lbl.setStyleSheet(f"{STYLE_LABEL_TRANSPARENT} background-color: {COLOR_BORDER}; color: {COLOR_TEXT_INACTIVE}; font-family: 'Roboto'; font-size: 9px; font-weight: bold; border-radius: 6px; padding: 0px 6px;")
            self.article_lbl.setStyleSheet(f"{STYLE_LABEL_TRANSPARENT} color: {COLOR_TEXT_INACTIVE}; font-family: 'Roboto'; font-size: 11px; font-weight: bold;")
            self.text_lbl.setStyleSheet(f"{STYLE_LABEL_TRANSPARENT} color: {COLOR_TEXT_INACTIVE}; font-family: 'Roboto'; font-size: 10px;")


class OverlayHelper(QWidget):
    toggle_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.load_config()
        self._init_window_flags()
        self.load_laws_data()
        self.initUI()
        
        self.oldPos = QPoint()
        self.toggle_signal.connect(self.toggle_visibility)
        self.init_global_hotkey()
        self.init_tray_icon()

    def load_config(self):
        self.hotkey, self.hardware_acceleration = load_initial_config()

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"hotkey": self.hotkey, "hardware_acceleration": self.hardware_acceleration}, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения конфига: {e}")

    def _init_window_flags(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def init_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = resource_path(os.path.join("assets", "images", "logo.png"))
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        self.tray_icon.setToolTip("Webcool RP Helper")
            
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Открыть / Скрыть хелпер")
        show_action.triggered.connect(self.toggle_visibility)
        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("Выход")
        quit_action.triggered.connect(QApplication.quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(lambda r: self.toggle_visibility() if r == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray_icon.show()

    def init_global_hotkey(self):
        try:
            keyboard.unhook_all()
            keyboard.add_hotkey(self.hotkey, lambda: self.toggle_signal.emit(), suppress=True)
        except Exception as e:
            print(f"Не удалось зарегистрировать глобальную горячую клавишу: {e}")

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self._force_foreground_focus()
            self.activateWindow()
            self.search_input.setFocus()
            if self.search_input.text():
                self.search_input.selectAll()

    def _force_foreground_focus(self):
        try:
            import ctypes
            user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
            hwnd = int(self.winId())
            fg_hwnd = user32.GetForegroundWindow()
            if fg_hwnd and fg_hwnd != hwnd:
                pid = ctypes.c_ulong()
                fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, ctypes.byref(pid))
                curr_thread = kernel32.GetCurrentThreadId()
                if fg_thread and fg_thread != curr_thread:
                    user32.AttachThreadInput(curr_thread, fg_thread, True)
                    user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0040)
                    user32.SetForegroundWindow(hwnd)
                    user32.AttachThreadInput(curr_thread, fg_thread, False)
        except Exception as e:
            print(f"Ошибка принудительного перехвата фокуса: {e}")

    def load_laws_data(self):
        self.all_articles = []
        database_dir = resource_path("database")
        if not os.path.exists(database_dir):
            return

        excluded_files = {"config.json", "keywords_map.json"}
        for filename in os.listdir(database_dir):
            if filename.endswith(".json") and filename not in excluded_files:
                try:
                    with open(os.path.join(database_dir, filename), "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for item in data:
                                art_num = str(item.get("article", ""))
                                if art_num:
                                    self.all_articles.append({
                                        "code": item.get("code", "ЗК"), 
                                        "article": art_num, 
                                        "chapter": item.get("chapter", ""),
                                        "data": item
                                    })
                except Exception as e:
                    print(f"Ошибка чтения {filename}: {e}")

    def initUI(self):
        main_layout = self.layout() if self.layout() else QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        self.wrapper = QWidget(self)
        self.wrapper.setStyleSheet(f"""
            QWidget {{ background-color: {COLOR_BG_MAIN}; border: 1px solid {COLOR_BORDER}; border-radius: 20px; }}
            QLineEdit {{ background: transparent; color: {COLOR_TEXT_MAIN}; border: none; font-family: 'Roboto'; font-size: 16px; }}
            QPushButton.icon-btn {{ background-color: transparent; border: none; border-radius: 16px; }}
            QPushButton.icon-btn:hover {{ background-color: {COLOR_BORDER_HOVER}; }}
        """)
        
        wrapper_layout = QVBoxLayout(self.wrapper)
        wrapper_layout.setContentsMargins(24, 16, 24, 16)
        wrapper_layout.setSpacing(12)
        wrapper_layout.addLayout(self._create_search_bar_layout())
        
        # Результаты поиска
        self.results_container = QWidget()
        self.results_container.setStyleSheet(STYLE_LABEL_TRANSPARENT)
        res_layout = QVBoxLayout(self.results_container)
        res_layout.setContentsMargins(0, 0, 0, 0)
        res_layout.setSpacing(0)
        
        h_divider = QFrame()
        h_divider.setFrameShape(QFrame.Shape.HLine)
        h_divider.setFixedHeight(1)
        h_divider.setStyleSheet(f"background-color: {COLOR_BORDER_HOVER}; border: none;")
        res_layout.addWidget(h_divider)
        res_layout.addLayout(self._create_content_split_layout())
        wrapper_layout.addWidget(self.results_container)

        # Настройки
        self.settings_container = QWidget()
        self.settings_container.setStyleSheet(STYLE_LABEL_TRANSPARENT)
        set_layout = QVBoxLayout(self.settings_container)
        set_layout.setContentsMargins(0, 12, 0, 0)
        set_layout.setSpacing(12)
        set_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        s_divider = QFrame()
        s_divider.setFrameShape(QFrame.Shape.HLine)
        s_divider.setFixedHeight(1)
        s_divider.setStyleSheet(f"background-color: {COLOR_BORDER_HOVER}; border: none;")
        set_layout.addWidget(s_divider)

        set_layout.addWidget(self._create_setting_card("Горячая клавиша", self._create_keys_widget()))
        set_layout.addWidget(self._create_setting_card("Аппаратное ускорение", self._create_accel_widget()))
        wrapper_layout.addWidget(self.settings_container)

        self.results_container.hide()
        self.settings_container.hide()
        self.is_settings_open = False
        self.setFixedSize(830, 96)
        main_layout.addWidget(self.wrapper)

    def _create_search_bar_layout(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        self.logo_lbl = QLabel()
        self.logo_lbl.setStyleSheet(STYLE_LABEL_TRANSPARENT)
        logo_path = resource_path(os.path.join("assets", "images", "logo.png"))
        if os.path.exists(logo_path):
            self.logo_lbl.setPixmap(QPixmap(logo_path).scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.logo_lbl.setText("🛡️")
        layout.addWidget(self.logo_lbl)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Статья, преступление или номер...")
        self.search_input.textChanged.connect(self.on_search_changed)
        self.search_input.returnPressed.connect(self.on_enter_pressed)
        layout.addWidget(self.search_input, stretch=1)
        
        layout.addWidget(self._create_icon_btn(resource_path(os.path.join("assets", "images", "mic.png")), "🎤", self.toggle_mic))
        
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background-color: {COLOR_BORDER_HOVER}; border: none;")
        layout.addWidget(sep)
        
        layout.addWidget(self._create_icon_btn(resource_path(os.path.join("assets", "images", "settings.png")), "⚙", self.open_settings))
        return layout

    def _create_icon_btn(self, img_path: str, fallback_txt: str, callback) -> QPushButton:
        btn = QPushButton()
        btn.setProperty("class", "icon-btn")
        btn.setFixedSize(32, 32)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if os.path.exists(img_path):
            btn.setIcon(QIcon(QPixmap(img_path).scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)))
        else:
            btn.setText(fallback_txt)
            btn.setStyleSheet(f"color: {COLOR_TEXT_MAIN}; border: none; background: transparent;")
        btn.clicked.connect(callback)
        return btn

    def _create_content_split_layout(self) -> QHBoxLayout:
        split_layout = QHBoxLayout()
        split_layout.setContentsMargins(0, 12, 0, 0)
        split_layout.setSpacing(16)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        self.left_container = QWidget()
        self.left_container.setStyleSheet(STYLE_LABEL_TRANSPARENT)
        self.left_layout = QVBoxLayout(self.left_container)
        self.left_container.setFixedWidth(315)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(8)
        self.left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.left_container)
        self.cards = []
        split_layout.addWidget(self.scroll_area)
        
        self.v_divider = QFrame()
        self.v_divider.setFrameShape(QFrame.Shape.VLine)
        self.v_divider.setFixedWidth(1)
        self.v_divider.setStyleSheet(f"background-color: {COLOR_BORDER_HOVER}; border: none;")
        split_layout.addWidget(self.v_divider)
        
        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.right_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        self.right_content = QWidget()
        self.right_content.setStyleSheet(STYLE_LABEL_TRANSPARENT)
        self.right_content_layout = QVBoxLayout(self.right_content)
        self.right_content_layout.setContentsMargins(0, 16, 0, 0)
        self.right_content_layout.setSpacing(12)
        self.right_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.right_scroll.setWidget(self.right_content)
        
        right_pane = QWidget()
        right_pane.setStyleSheet(STYLE_LABEL_TRANSPARENT)
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(8, 0, 8, 0)
        right_layout.addWidget(self.right_scroll)
        split_layout.addWidget(right_pane, stretch=1)
        
        return split_layout

    def _create_setting_card(self, title: str, content_widget: QWidget) -> QFrame:
        card = QFrame()
        card.setFixedHeight(64)
        card.setStyleSheet(STYLE_CARD)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 0, 16, 0)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {COLOR_TEXT_MAIN}; font-family: 'Roboto'; font-size: 13px; font-weight: bold; {STYLE_LABEL_TRANSPARENT}")
        layout.addWidget(title_lbl)
        layout.addStretch()
        layout.addWidget(content_widget)
        return card

    def _create_keys_widget(self) -> QWidget:
        container = QWidget()
        container.setStyleSheet(STYLE_LABEL_TRANSPARENT)
        self.keys_container_layout = QHBoxLayout(container)
        self.keys_container_layout.setContentsMargins(0, 0, 0, 0)
        self.keys_container_layout.setSpacing(6)
        self.update_key_buttons(self.hotkey)
        return container

    def _create_accel_widget(self) -> QPushButton:
        self.accel_btn = QPushButton("ВКЛ" if self.hardware_acceleration else "ВЫКЛ")
        self.accel_btn.setFixedHeight(32)
        self.accel_btn.setMinimumWidth(56)
        self.accel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_accel_button_style()
        self.accel_btn.clicked.connect(self.toggle_hardware_acceleration)
        return self.accel_btn

    def update_accel_button_style(self):
        accel_bg = COLOR_ACCENT if self.hardware_acceleration else COLOR_BORDER
        accel_color = "#000000" if self.hardware_acceleration else COLOR_TEXT_MAIN
        self.accel_btn.setText("ВКЛ" if self.hardware_acceleration else "ВЫКЛ")
        self.accel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {accel_bg}; color: {accel_color};
                border: 1px solid {COLOR_BORDER_HOVER}; border-radius: 8px;
                font-family: 'Roboto'; font-size: 12px; font-weight: bold; padding: 0px 8px;
            }}
            QPushButton:hover {{ border-color: {COLOR_ACCENT}; }}
        """)

    def resize_window(self, mode: str):
        if self.isMaximized():
            self.showNormal()
        if mode == "search":
            self.settings_container.hide()
            self.results_container.show()
            self.setFixedSize(830, 576)
        elif mode == "settings":
            self.results_container.hide()
            self.settings_container.show()
            self.setFixedSize(830, 280)
        else:
            self.results_container.hide()
            self.settings_container.hide()
            self.setFixedSize(830, 96)

    def on_search_changed(self, text: str):
        self.is_settings_open = False
        if text.strip():
            self.filter_articles(text)
            self.resize_window("search")
        else:
            self.resize_window("closed")

    def open_settings(self):
        self.is_settings_open = not self.is_settings_open
        if self.is_settings_open:
            self.resize_window("settings")
        else:
            self.resize_window("search" if self.search_input.text().strip() else "closed")

    def toggle_hardware_acceleration(self):
        self.hardware_acceleration = not self.hardware_acceleration
        self.save_config()
        self.update_accel_button_style()

    def update_key_buttons(self, hotkey_str: str):
        while self.keys_container_layout.count():
            item = self.keys_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for part in hotkey_str.upper().split("+"):
            btn = QPushButton(part.strip())
            btn.setFixedHeight(32)
            btn.setMinimumWidth(36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_BORDER}; color: {COLOR_TEXT_MAIN};
                    border: 1px solid {COLOR_BORDER_HOVER}; border-radius: 8px;
                    font-family: 'Roboto'; font-size: 12px; font-weight: bold; padding: 0px 8px;
                }}
                QPushButton:hover {{ border-color: {COLOR_ACCENT}; }}
            """)
            btn.clicked.connect(self.record_new_hotkey)
            self.keys_container_layout.addWidget(btn)

    def record_new_hotkey(self):
        while self.keys_container_layout.count():
            item = self.keys_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        recording_btn = QPushButton("Нажмите клавиши...")
        recording_btn.setFixedHeight(32)
        recording_btn.setStyleSheet(f"QPushButton {{ background-color: {COLOR_ACCENT}; color: #000000; border-radius: 8px; font-family: 'Roboto'; font-size: 11px; font-weight: bold; padding: 0px 10px; }}")
        self.keys_container_layout.addWidget(recording_btn)

        def listen_key():
            try:
                recorded = keyboard.read_hotkey(suppress=False)
                if recorded:
                    self.hotkey = recorded.lower().replace(" ", "")
                    self.save_config()
                    self.init_global_hotkey()
            except Exception as e:
                print(f"Ошибка записи клавиши: {e}")
            QMetaObject.invokeMethod(self, "refresh_keys_ui", Qt.ConnectionType.QueuedConnection)

        threading.Thread(target=listen_key, daemon=True).start()

    @pyqtSlot()
    def refresh_keys_ui(self):
        self.update_key_buttons(self.hotkey)

    def filter_articles(self, query: str):
        while self.left_layout.count():
            item = self.left_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.cards = []
        query = query.strip().lower()
        if not query:
            return

        scored_articles = []
        for art in self.all_articles:
            art_num = str(art["article"]).lower()
            name_text = (art["data"].get("name", "") or "").lower()
            body_text = (art["data"].get("text", "") or "").lower()
            punishment_text = (art["data"].get("punishment_text", "") or "").lower()
            
            code = art.get("code", "")
            raw_art_num = str(art["article"])
            raw_keywords = custom_keywords.get(f"{code}:{raw_art_num}", []) or custom_keywords.get(raw_art_num, [])
            keywords = [kw.lower() for kw in raw_keywords]
            
            score = 0
            if art_num == query: score += 10000
            elif art_num.startswith(query): score += 5000
            elif query in art_num: score += 2000

            if query in name_text: score += 4000
            for kw in keywords:
                if query in kw or kw in query: score += 3500

            name_ratio = fuzz.partial_ratio(query, name_text)
            if name_ratio > 75: score += name_ratio * 20

            for kw in keywords:
                kw_ratio = fuzz.ratio(query, kw)
                if kw_ratio > 80: score += kw_ratio * 25

            if query in body_text or query in punishment_text: score += 500
            if score > 0: scored_articles.append((score, art))

        scored_articles.sort(key=lambda x: x[0], reverse=True)
        matched = [art for score, art in scored_articles]

        if matched:
            self.scroll_area.show()
            self.v_divider.show()
            for i, art in enumerate(matched[:15]):
                card = LawCard(art["code"], art["article"], art["data"], active=(i == 0))
                card.clicked_signal.connect(self.handle_card_clicked)
                self.cards.append(card)
                self.left_layout.addWidget(card)
            self.show_article_details(matched[0])
        else:
            self.scroll_area.hide()
            self.v_divider.hide()
            self._show_no_results_state()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _show_no_results_state(self):
        self._clear_layout(self.right_content_layout)
        
        container = QWidget()
        container.setStyleSheet(STYLE_LABEL_TRANSPARENT)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 40, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        icon_path = resource_path(os.path.join("assets", "images", "no_results.png"))
        if os.path.exists(icon_path):
            icon_lbl = QLabel()
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_lbl.setStyleSheet(STYLE_LABEL_TRANSPARENT)
            icon_lbl.setPixmap(QPixmap(icon_path).scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            layout.addWidget(icon_lbl)
        else:
            emoji_lbl = QLabel("🔍")
            emoji_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            emoji_lbl.setStyleSheet(f"font-size: 32px; {STYLE_LABEL_TRANSPARENT}")
            layout.addWidget(emoji_lbl)

        title_lbl = QLabel("Похожих пунктов нет")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet(f"color: {COLOR_TEXT_MAIN}; font-family: 'Roboto'; font-size: 16px; font-weight: bold; {STYLE_LABEL_TRANSPARENT}")
        layout.addWidget(title_lbl)

        desc_lbl = QLabel("По вашему запросу ничего не найдено в базе данных законов.")
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-family: 'Roboto'; font-size: 12px; {STYLE_LABEL_TRANSPARENT}")
        layout.addWidget(desc_lbl)

        self.right_content_layout.addWidget(container)

    def create_info_card(self, title: str, content_widget) -> QFrame:
        card = QFrame()
        card.setFixedHeight(64)
        card.setStyleSheet(STYLE_CARD)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-family: 'Roboto'; font-size: 10px; {STYLE_LABEL_TRANSPARENT}")
        layout.addWidget(title_lbl)
        
        if isinstance(content_widget, QWidget):
            layout.addWidget(content_widget)
        elif isinstance(content_widget, QHBoxLayout):
            layout.addLayout(content_widget)
        return card

    def _add_section_card(self, title: str, items: list):
        if not items:
            return
        card = QFrame()
        card.setStyleSheet(STYLE_CARD)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)
        
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"color: {COLOR_ACCENT}; font-family: 'Roboto'; font-size: 11px; font-weight: bold; {STYLE_LABEL_TRANSPARENT}")
        layout.addWidget(t_lbl)
        
        for item in items:
            lbl = QLabel(item)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-family: 'Roboto'; font-size: 11px; line-height: 140%; {STYLE_LABEL_TRANSPARENT}")
            layout.addWidget(lbl)
        self.right_content_layout.addWidget(card)

    def show_article_details(self, art_item: dict):
        code, art_num, raw_chapter, data = art_item["code"], art_item["article"], art_item.get("chapter", ""), art_item["data"]
        
        self._clear_layout(self.right_content_layout)
                
        art_header_row = QHBoxLayout()
        art_header_row.setContentsMargins(0, 0, 0, 0)
        art_header_row.setSpacing(8)
        art_header_row.setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        det_code_lbl = QLabel(code)
        det_code_lbl.setStyleSheet(f"background-color: {COLOR_BORDER}; color: {COLOR_TEXT_MAIN}; font-family: 'Roboto'; font-size: 10px; font-weight: bold; border-radius: 6px; padding: 3px 8px;")
        art_header_row.addWidget(det_code_lbl)

        det_word_lbl = QLabel("Статья")
        det_word_lbl.setStyleSheet(f"color: {COLOR_ACCENT}; font-family: 'Roboto'; font-size: 9px; {STYLE_LABEL_TRANSPARENT} margin-bottom: -3px;")
        art_header_row.addWidget(det_word_lbl)
        
        det_num_lbl = QLabel(art_num)
        det_num_lbl.setStyleSheet(f"color: {COLOR_ACCENT}; font-family: 'Roboto'; font-size: 16px; font-weight: bold; {STYLE_LABEL_TRANSPARENT}")
        art_header_row.addWidget(det_num_lbl)
        art_header_row.addStretch()
        
        full_text = f"{code} Статья {art_num}\n"
        if data.get('text'): full_text += f"Текст: {data.get('text')}\n"
        if data.get('punishment_text'): full_text += f"Наказание: {data.get('punishment_text')}\n"
            
        copy_btn = self._create_icon_btn(resource_path(os.path.join("assets", "images", "copy.png")), "📋", lambda: QApplication.clipboard().setText(full_text))
        art_header_row.addWidget(copy_btn)
        
        header_container = QWidget()
        header_container.setStyleSheet(STYLE_LABEL_TRANSPARENT)
        header_container.setLayout(art_header_row)
        self.right_content_layout.addWidget(header_container)

        clean_chapter = raw_chapter
        for prefix in ["Особенная часть. ", "Общая часть. ", "Особенная часть ", "Общая часть "]:
            if clean_chapter.startswith(prefix):
                clean_chapter = clean_chapter[len(prefix):]
                break

        if clean_chapter:
            chap_lbl = QLabel()
            font = QFont('Roboto', 9)
            font.setWeight(QFont.Weight.Thin)
            chap_lbl.setFont(font)
            chap_lbl.setText(QFontMetrics(font).elidedText(clean_chapter.upper(), Qt.TextElideMode.ElideRight, 460))
            chap_lbl.setStyleSheet(f"color: {COLOR_TEXT_DIM}; font-family: 'Roboto'; font-size: 9px; font-weight: 300; {STYLE_LABEL_TRANSPARENT}")
            self.right_content_layout.addWidget(chap_lbl)

        punishment = data.get("punishment_text", "")
        if punishment:
            pun_card = QFrame()
            pun_card.setStyleSheet(STYLE_CARD)
            p_layout = QVBoxLayout(pun_card)
            p_layout.setContentsMargins(14, 12, 14, 12)
            p_layout.setSpacing(4)
            p_title = QLabel("Наказание")
            p_title.setStyleSheet(f"color: {COLOR_ACCENT}; font-family: 'Roboto'; font-size: 11px; font-weight: bold; {STYLE_LABEL_TRANSPARENT}")
            p_layout.addWidget(p_title)
            p_text = QLabel(punishment)
            p_text.setWordWrap(True)
            p_text.setStyleSheet(f"color: {COLOR_TEXT_MAIN}; font-family: 'Roboto'; font-size: 13px; font-weight: bold; {STYLE_LABEL_TRANSPARENT}")
            p_layout.addWidget(p_text)
            self.right_content_layout.addWidget(pun_card)

        top_cards_row = QHBoxLayout()
        top_cards_row.setContentsMargins(0, 0, 0, 0)
        top_cards_row.setSpacing(8)
        has_cards = False
        
        priority_val = data.get("wanted_level")
        if priority_val:
            stars_layout = QHBoxLayout()
            stars_layout.setContentsMargins(0, 0, 0, 0)
            stars_layout.setSpacing(4)
            for s in range(1, 6):
                active = s <= int(priority_val)
                star_lbl = QLabel()
                star_lbl.setFixedSize(16, 16)
                star_lbl.setStyleSheet(STYLE_LABEL_TRANSPARENT)
                star_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                icon_path = resource_path(os.path.join("assets", "images", "star_fill.png" if active else "star_outline.png"))
                if os.path.exists(icon_path):
                    star_lbl.setPixmap(QPixmap(icon_path).scaled(14, 14, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                else:
                    star_lbl.setText("★" if active else "☆")
                    star_lbl.setStyleSheet(f"color: {COLOR_ACCENT if active else COLOR_STAR_INACTIVE}; font-size: 14px; {STYLE_LABEL_TRANSPARENT}")
                stars_layout.addWidget(star_lbl)
            stars_layout.addStretch()
            top_cards_row.addWidget(self.create_info_card("Розыск", stars_layout), stretch=1)
            has_cards = True
            
        law_type = (data.get("type") or "").upper()
        if law_type in ["F", "R"]:
            j_badge = QLabel("Федеральная" if law_type == "F" else "Региональная")
            j_badge.setStyleSheet(f"color: {COLOR_TEXT_MAIN}; font-family: 'Roboto'; font-size: 12px; font-weight: bold; {STYLE_LABEL_TRANSPARENT}")
            top_cards_row.addWidget(self.create_info_card("Юрисдикция", j_badge), stretch=1)
            has_cards = True
            
        if has_cards:
            self.right_content_layout.addLayout(top_cards_row)

        art_text = data.get("text", "")
        if art_text:
            txt_lbl = QLabel(f'<p style="color: {COLOR_TEXT_MAIN}; font-family: \'Roboto\'; font-size: 12px; line-height: 160%; margin: 0;">{art_text}</p>')
            txt_lbl.setWordWrap(True)
            txt_lbl.setStyleSheet(STYLE_LABEL_TRANSPARENT)
            self.right_content_layout.addWidget(txt_lbl)

        # Подпункты (subparts)
        for sub in data.get("subparts", []):
            sub_card = QFrame()
            sub_card.setStyleSheet(STYLE_CARD)
            s_layout = QVBoxLayout(sub_card)
            s_layout.setContentsMargins(14, 12, 14, 12)
            s_layout.setSpacing(6)
            
            s_title = QLabel(f"Пункт {art_num}.{sub.get('sub', '')}")
            s_title.setStyleSheet(f"color: {COLOR_ACCENT}; font-family: 'Roboto'; font-size: 11px; font-weight: bold; {STYLE_LABEL_TRANSPARENT}")
            s_layout.addWidget(s_title)
            
            s_text = QLabel(sub.get("text", ""))
            s_text.setWordWrap(True)
            s_text.setStyleSheet(f"color: {COLOR_TEXT_MAIN}; font-family: 'Roboto'; font-size: 12px; line-height: 140%; {STYLE_LABEL_TRANSPARENT}")
            s_layout.addWidget(s_text)
            
            if sub.get("nested"):
                nested_container = QVBoxLayout()
                nested_container.setContentsMargins(10, 6, 0, 0)
                nested_container.setSpacing(6)
                for nest in sub.get("nested", []):
                    nest_lbl = QLabel(f"• {art_num}.{sub.get('sub', '')}.{nest.get('sub', '')} {nest.get('text', '')}")
                    nest_lbl.setWordWrap(True)
                    nest_lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-family: 'Roboto'; font-size: 11px; line-height: 140%; {STYLE_LABEL_TRANSPARENT}")
                    nested_container.addWidget(nest_lbl)
                s_layout.addLayout(nested_container)
            self.right_content_layout.addWidget(sub_card)

        # Примечания, комментарии, исключения
        self._add_section_card("Примечания", data.get("notes", []))
        self._add_section_card("Комментарий / Пояснение", data.get("comments", []))
        self._add_section_card("Исключение", data.get("exceptions", []))

    def handle_card_clicked(self, selected_card):
        for card in self.cards:
            is_selected = (card == selected_card)
            card.setActive(is_selected)
            if is_selected:
                chapter_name = next((art.get("chapter", "") for art in self.all_articles if art["article"] == card.article_lbl.text() and art["data"] == card.article_data), "")
                self.show_article_details({
                    "code": card.code_lbl.text(),
                    "article": card.article_lbl.text(),
                    "chapter": chapter_name,
                    "data": card.article_data
                })

    def toggle_mic(self):
        print("Микрофон активирован, слушаю...")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.oldPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.oldPos
            self.move(self.pos() + delta)
            self.oldPos = event.globalPosition().toPoint()

    def on_enter_pressed(self):
        query = self.search_input.text().strip()
        if not query or self.cards:
            return
        print(f"Запрос к ИИ: {query}")


if __name__ == '__main__':
    check_remote_status()
    _, hw_accel_enabled = load_initial_config()
    if not hw_accel_enabled:
        os.environ["QT_OPENGL"] = "software"
    
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    
    window = OverlayHelper()
    window.show()
    screen = app.primaryScreen().geometry()
    window.move((screen.width() - window.width()) // 2, 150)
    
    sys.exit(app.exec())