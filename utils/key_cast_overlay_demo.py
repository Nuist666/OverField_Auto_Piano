import sys
from typing import Optional, Dict
from collections import deque
import time

from PyQt5 import QtWidgets, QtCore, QtGui

try:
    from pynput import keyboard
except Exception:
    keyboard = None  # type: ignore

DEFAULT_SETTINGS = {
    'enabled': True,
    'opacity': 0.7,
    'max_keys': 5,
    'display_time': 2.0,
    'position': 'bottom_center',
}


class KeyCastOverlay(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, settings: Optional[Dict] = None):
        super().__init__(parent, flags=QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)

        self.settings = DEFAULT_SETTINGS.copy()
        if settings:
            self.settings.update(settings)

        self.resize(800, 80)
        self._apply_position()
        self.setWindowOpacity(float(self.settings.get('opacity', 0.7)))

        self.label = QtWidgets.QLabel('', self)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        f = self.label.font(); f.setFamily('Consolas'); f.setPointSize(20); f.setBold(True)
        self.label.setFont(f)
        self.label.setStyleSheet('QLabel{color:white;background:black;}')
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.label)

        self.keys = deque(maxlen=int(self.settings.get('max_keys', 5)))
        self.last_press_time: Dict[str, float] = {}

        self.listener = None
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._cleanup_once)

        self.set_enabled(bool(self.settings.get('enabled', True)))

    def set_enabled(self, enabled: bool):
        self.settings['enabled'] = enabled
        if enabled:
            self.show()
            self._start_listener()
            self.timer.start(200)
        else:
            self.hide()
            self._stop_listener()
            self.timer.stop()

    def apply_settings(self, new_settings: Dict):
        for k in DEFAULT_SETTINGS:
            if k in new_settings:
                self.settings[k] = new_settings[k]
        try:
            self.setWindowOpacity(float(self.settings.get('opacity', 0.7)))
        except Exception:
            pass
        max_keys = int(self.settings.get('max_keys', 5))
        if max_keys != self.keys.maxlen:
            self.keys = deque(self.keys, maxlen=max_keys)
            self._update_label()
        self._apply_position()

    def close(self):
        self.set_enabled(False)
        try:
            super().close()
        except Exception:
            pass

    def _apply_position(self):
        desktop = QtWidgets.QApplication.desktop()
        rect = desktop.availableGeometry()
        sw, sh = rect.width(), rect.height()
        w, h = self.width(), self.height()
        pos = self.settings.get('position', 'bottom_center')
        if pos == 'top_left':
            x, y = 20, 20
        elif pos == 'top_right':
            x, y = sw - w - 20, 20
        elif pos == 'bottom_left':
            x, y = 20, sh - h - 60
        elif pos == 'bottom_right':
            x, y = sw - w - 20, sh - h - 60
        elif pos == 'top_center':
            x, y = (sw - w) // 2, 20
        else:
            x, y = (sw - w) // 2, sh - h - 60
        self.move(x, y)

    def _start_listener(self):
        if keyboard is None or self.listener is not None:
            return
        def on_press(key):
            try:
                ch = key.char.upper()
            except Exception:
                ch = str(key).replace('Key.', '').upper()
            self.keys.append(ch)
            self.last_press_time[ch] = time.time()
            self._update_label()
        try:
            self.listener = keyboard.Listener(on_press=on_press)
            self.listener.start()
        except Exception:
            self.listener = None

    def _stop_listener(self):
        if self.listener is not None:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None

    def _cleanup_once(self):
        now = time.time()
        disp_time = float(self.settings.get('display_time', 2.0))
        removed = False
        for k in list(self.keys):
            if now - self.last_press_time.get(k, 0) > disp_time:
                try:
                    self.keys.remove(k)
                    removed = True
                except ValueError:
                    pass
        if removed:
            self._update_label()

    def _update_label(self):
        self.label.setText('  '.join(self.keys))


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    overlay = KeyCastOverlay()
    overlay.show()
    sys.exit(app.exec_())
