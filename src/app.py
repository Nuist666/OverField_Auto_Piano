from typing import List, Optional, Deque
from collections import deque
import os
import time

from PyQt5 import QtWidgets, QtCore

from src.player import Player
from src.event import Event
from utils.key_cast_overlay_demo import KeyCastOverlay
from utils.lrcp_recorder import open_recorder_window

try:
    from pynput import keyboard as pynput_keyboard
except Exception:
    pynput_keyboard = None  # type: ignore


class SignalBus(QtCore.QObject):
    progress = QtCore.pyqtSignal(int, int)
    finished = QtCore.pyqtSignal()
    status = QtCore.pyqtSignal(str)


class BaseApp(QtWidgets.QWidget):
    def __init__(self, title: str, create_key_display: bool = True, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(820, 520)

        self.score_text: Optional[str] = None
        self.player: Optional[Player] = None

        self.bus = SignalBus(self)
        self.bus.progress.connect(self.on_progress_update)
        self.bus.finished.connect(self.on_player_done)
        self.bus.status.connect(self.on_status)

        self.v_main = QtWidgets.QVBoxLayout(self)
        self.v_main.setContentsMargins(10, 10, 10, 10)

        self._create_file_bar()
        self._create_params_frame()
        self._create_control_frame()
        self._create_tips_frame()

        if create_key_display:
            self._create_key_display_frame()

        # key display in-window variables
        self.keys: Deque[str] = deque(maxlen=14)
        self.last_press_time = {}
        self.running = True

        # key overlay default settings
        self.keycast_settings = {
            'enabled': True,
            'opacity': 0.7,
            'max_keys': 5,
            'display_time': 2.0,
            'position': 'bottom_center',
        }
        try:
            self.keycast_overlay = KeyCastOverlay(settings=self.keycast_settings)
        except Exception:
            self.keycast_overlay = None

        # start local key listener for in-window display
        self._start_key_listener()
        self._cleanup_timer = QtCore.QTimer(self)
        self._cleanup_timer.timeout.connect(self._cleanup_keys_once)
        self._cleanup_timer.start(200)

    # ---------- UI builders ----------
    def _create_file_bar(self):
        bar = QtWidgets.QHBoxLayout()
        self.v_main.addLayout(bar)
        self.btn_load = QtWidgets.QPushButton('载入乐谱')
        self.btn_load.clicked.connect(self.load_score)
        bar.addWidget(self.btn_load)
        self.lbl_file = QtWidgets.QLabel('未载入')
        bar.addWidget(self.lbl_file)
        bar.addStretch()

    def _create_params_frame(self):
        grp = QtWidgets.QGroupBox('参数')
        grid = QtWidgets.QGridLayout(grp)

        grid.addWidget(QtWidgets.QLabel('速度比例(1.0为原速)：'), 0, 0)
        self.ent_speed = QtWidgets.QComboBox()
        self.ent_speed.addItems(['0.5', '0.75', '1.0', '1.25', '1.5', '1.75', '2.0', '2.25', '2.5'])
        self.ent_speed.setCurrentText('1.0')
        self.ent_speed.setEditable(False)
        self.ent_speed.setFixedWidth(90)
        grid.addWidget(self.ent_speed, 0, 1)

        grid.addWidget(QtWidgets.QLabel('起始倒计时(秒)：'), 0, 2)
        self.ent_countin = QtWidgets.QComboBox()
        self.ent_countin.addItems(['0', '1', '2', '3', '4', '5'])
        self.ent_countin.setCurrentText('2')
        self.ent_countin.setEditable(False)
        self.ent_countin.setFixedWidth(90)
        grid.addWidget(self.ent_countin, 0, 3)

        grid.addWidget(QtWidgets.QLabel('全局延迟(毫秒)：'), 0, 4)
        self.ent_latency = QtWidgets.QSpinBox()
        self.ent_latency.setRange(-200, 200)
        self.ent_latency.setSingleStep(5)
        self.ent_latency.setValue(0)
        self.ent_latency.setFixedWidth(90)
        grid.addWidget(self.ent_latency, 0, 5)

        grid.addWidget(QtWidgets.QLabel('进度更新频率：'), 1, 0)
        self.ent_progress_freq = QtWidgets.QComboBox()
        self.ent_progress_freq.addItems(['1', '2', '3', '5', '10'])
        self.ent_progress_freq.setCurrentText('1')
        self.ent_progress_freq.setFixedWidth(90)
        grid.addWidget(self.ent_progress_freq, 1, 1)

        grid.addWidget(QtWidgets.QLabel('(1=每个动作都更新, 2=每2个动作更新, 以此类推)'), 1, 2, 1, 4)

        self.v_main.addWidget(grp)

        # track param widgets for enable/disable
        self.param_widgets = [
            self.ent_speed,
            self.ent_countin,
            self.ent_latency,
            self.ent_progress_freq,
        ]

    def _create_control_frame(self):
        h = QtWidgets.QHBoxLayout()
        self.v_main.addLayout(h)
        self.btn_start = QtWidgets.QPushButton('开始演奏')
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self.toggle_play_pause)
        h.addWidget(self.btn_start)
        self.btn_stop = QtWidgets.QPushButton('停止')
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_play)
        h.addWidget(self.btn_stop)

        self.btn_keycast = QtWidgets.QPushButton('按键显示设置')
        self.btn_keycast.clicked.connect(self.open_keycast_settings)
        h.addWidget(self.btn_keycast)

        self.btn_record = QtWidgets.QPushButton('动作录制')
        self.btn_record.clicked.connect(lambda: open_recorder_window(self))
        h.addWidget(self.btn_record)

        self.lbl_status = QtWidgets.QLabel('状态：等待载入乐谱')
        h.addWidget(self.lbl_status)
        h.addStretch()

        # progress
        h2 = QtWidgets.QHBoxLayout()
        self.v_main.addLayout(h2)
        self.lbl_progress = QtWidgets.QLabel('进度：0%')
        h2.addWidget(self.lbl_progress)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(18)
        h2.addWidget(self.progress_bar, 1)

    def _create_tips_frame(self):
        grp = QtWidgets.QGroupBox('使用提示')
        layout = QtWidgets.QVBoxLayout(grp)
        lbl = QtWidgets.QLabel(
            '1) 乐谱支持延长音：写法 [起始时间][结束时间] TOKENS\n'
            '2) 单时间戳仍可用作短音：[时间] TOKENS\n'
            '3) 载入后切换到游戏窗口，回到本工具点击开始；\n'
            '4) 如无响应尝试以管理员身份运行。'
        )
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        self.v_main.addWidget(grp)

    def _create_key_display_frame(self):
        grp = QtWidgets.QGroupBox('按键显示')
        v = QtWidgets.QVBoxLayout(grp)
        self.lbl_keys = QtWidgets.QLabel('等待按键...')
        f = self.font(); f.setFamily('Consolas'); f.setPointSize(14); f.setBold(True)
        self.lbl_keys.setFont(f)
        self.lbl_keys.setStyleSheet('QLabel{color:white;background:#C0C0C0;padding:8px;}')
        self.lbl_keys.setAlignment(QtCore.Qt.AlignCenter)
        v.addWidget(self.lbl_keys)
        hint = QtWidgets.QLabel('实时显示当前按下的按键 (窗口内)')
        hint.setStyleSheet('color: gray')
        v.addWidget(hint)
        self.v_main.addWidget(grp)

    # ---------- Key display (window-internal) ----------
    def _start_key_listener(self):
        if pynput_keyboard is None:
            if hasattr(self, 'lbl_keys'):
                self.lbl_keys.setText('需要安装 pynput 模块\npip install pynput')
                self.lbl_keys.setStyleSheet('QLabel{color:red;background:lightgray;padding:8px;}')
            return

        def on_press(key):
            try:
                ch = key.char.upper()
            except Exception:
                ch = str(key).replace('Key.', '').upper()
            self.keys.append(ch)
            self.last_press_time[ch] = time.time()
            self._update_key_display()

        try:
            self.key_listener = pynput_keyboard.Listener(on_press=on_press)
            self.key_listener.start()
        except Exception:
            self.key_listener = None

    def _cleanup_keys_once(self):
        now = time.time()
        removed = False
        for k in list(self.keys):
            if now - self.last_press_time.get(k, 0) > 2.0:
                try:
                    self.keys.remove(k)
                    removed = True
                except ValueError:
                    pass
        if removed:
            self._update_key_display()

    def _update_key_display(self):
        if hasattr(self, 'lbl_keys'):
            if self.keys:
                self.lbl_keys.setText('  '.join(self.keys))
            else:
                self.lbl_keys.setText('等待按键...')

    # ---------- Progress helpers ----------
    def on_progress_update(self, current: int, total: int):
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.lbl_progress.setText(f'进度：{percentage}% ({current}/{total})')
        else:
            self.progress_bar.setValue(0)
            self.lbl_progress.setText('进度：0%')

    def reset_progress(self):
        self.progress_bar.setValue(0)
        self.lbl_progress.setText('进度：0%')

    def on_player_done(self):
        # called in GUI thread via signal
        self.btn_start.setEnabled(True)
        self.btn_start.setText('开始演奏')
        self.btn_stop.setEnabled(False)
        self.lbl_status.setText('完成/已停止')
        self.player = None
        self.enable_params()

    def on_status(self, text: str):
        self.lbl_status.setText(text)

    def set_params_enabled(self, enabled: bool):
        for w in getattr(self, 'param_widgets', []):
            w.setEnabled(enabled)

    def disable_params(self):
        self.set_params_enabled(False)

    def enable_params(self):
        self.set_params_enabled(True)

    # ---------- Actions ----------
    def load_score(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, '选择乐谱或MIDI文件(.lrcp/.mid)', '', '所有文件 (*.*)')
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.mid', '.midi'):
            try:
                from utils.midi2lrcp import midi_to_lrcp_text
                self.score_text = midi_to_lrcp_text(path)
                events = self._parse_score(self.score_text)
                if not events:
                    raise ValueError('未解析出任何事件，请检查格式。')
                self._after_load(path, events)
                return
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, '转换失败', f'MIDI 转换为 LRCP 失败：\n{e}')
                return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.score_text = f.read()
            events = self._parse_score(self.score_text)
            if not events:
                raise ValueError('未解析出任何事件，请检查格式。')
            self._after_load(path, events)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, '载入失败', str(e))

    def _parse_score(self, score_text: str) -> List[Event]:
        raise NotImplementedError

    def _after_load(self, path: str, events: List[Event]):
        raise NotImplementedError

    def start_play(self):
        raise NotImplementedError

    def stop_play(self):
        if self.player:
            self.player.stop()
            self.player = None
            self.reset_progress()
            self.enable_params()
            self.btn_start.setEnabled(True)
            self.btn_start.setText('开始演奏')
            self.btn_stop.setEnabled(False)
            self.lbl_status.setText('完成/已停止')

    def toggle_play_pause(self):
        if not self.player:
            self.start_play()
            return
        try:
            if hasattr(self.player, 'is_paused') and self.player.is_paused():
                self.player.resume()
                self.btn_start.setText('暂停')
                self.lbl_status.setText('演奏中…')
            else:
                if hasattr(self.player, 'pause'):
                    self.player.pause()
                    self.btn_start.setText('继续')
                    self.lbl_status.setText('已暂停')
        except Exception:
            try:
                self.stop_play()
            except Exception:
                pass

    def open_keycast_settings(self):
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle('按键显示设置')
        layout = QtWidgets.QFormLayout(dlg)

        var_enabled = QtWidgets.QCheckBox('打开实时按键显示')
        var_enabled.setChecked(bool(self.keycast_settings.get('enabled', True)))

        spin_opacity = QtWidgets.QDoubleSpinBox()
        spin_opacity.setRange(0.2, 1.0)
        spin_opacity.setSingleStep(0.05)
        spin_opacity.setValue(float(self.keycast_settings.get('opacity', 0.7)))

        spin_max = QtWidgets.QSpinBox()
        spin_max.setRange(1, 50)
        spin_max.setValue(int(self.keycast_settings.get('max_keys', 5)))

        spin_disp = QtWidgets.QDoubleSpinBox()
        spin_disp.setRange(0.1, 10.0)
        spin_disp.setSingleStep(0.1)
        spin_disp.setValue(float(self.keycast_settings.get('display_time', 2.0)))

        pos_map = {
            '左上方': 'top_left',
            '右上方': 'top_right',
            '左下方': 'bottom_left',
            '右下方': 'bottom_right',
            '顶部居中': 'top_center',
            '底部居中': 'bottom_center',
        }
        pos_rev = {v: k for k, v in pos_map.items()}
        cmb_pos = QtWidgets.QComboBox()
        cmb_pos.addItems(list(pos_map.keys()))
        current = pos_rev.get(self.keycast_settings.get('position', 'bottom_center'), '底部居中')
        idx = cmb_pos.findText(current)
        cmb_pos.setCurrentIndex(max(0, idx))

        layout.addRow(var_enabled)
        layout.addRow('透明度(0.2~1.0)：', spin_opacity)
        layout.addRow('显示最近几个按键：', spin_max)
        layout.addRow('每个按键显示(秒)：', spin_disp)
        layout.addRow('位置：', cmb_pos)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(btns)

        def on_ok():
            new_cfg = {
                'opacity': max(0.2, min(1.0, float(spin_opacity.value()))),
                'max_keys': max(1, min(50, int(spin_max.value()))),
                'display_time': max(0.1, float(spin_disp.value())),
                'position': pos_map.get(cmb_pos.currentText(), 'bottom_center'),
            }
            self.keycast_settings.update(new_cfg)
            self.keycast_settings['enabled'] = bool(var_enabled.isChecked())
            if self.keycast_overlay:
                self.keycast_overlay.apply_settings(self.keycast_settings)
                self.keycast_overlay.set_enabled(bool(var_enabled.isChecked()))
            dlg.accept()

        def on_cancel():
            dlg.reject()

        btns.accepted.connect(on_ok)
        btns.rejected.connect(on_cancel)
        dlg.exec_()

    def closeEvent(self, e):
        self.running = False
        if hasattr(self, 'key_listener') and self.key_listener:
            try:
                self.key_listener.stop()
            except Exception:
                pass
        if hasattr(self, 'keycast_overlay') and self.keycast_overlay:
            try:
                self.keycast_overlay.close()
            except Exception:
                pass
        super().closeEvent(e)
