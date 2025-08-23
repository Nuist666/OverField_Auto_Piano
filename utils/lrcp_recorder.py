#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LRCP 实时录制器 (PyQt5)
- 全局监听键盘按下/释放，依据 README 的键位映射生成 .lrcp 文本
- 小窗口包含：开始、暂停、停止、导出、计时、事件数、热键设置
- 录制上限 1 小时；忽略按键：tab、capslock、shift、ctrl、win、alt、f1~f12
- 默认热键：开始 F6、暂停 F7、停止 F8，可在窗口中更改（仅支持 F1~F12 单键作为热键）

可在主程序中通过 open_recorder_window(parent) 打开。
也可独立运行：python utils/lrcp_recorder.py
"""
import time
from typing import Dict, List, Optional, Tuple

from PyQt5 import QtWidgets, QtCore

try:
    from pynput import keyboard
except Exception:
    keyboard = None  # type: ignore

from utils.constant import LOW_MAP, MID_MAP, HIGH_MAP, CHORD_MAP

KEY_TO_TOKEN: Dict[str, str] = {}
KEY_TO_TOKEN.update({v: f"L{k}" for k, v in LOW_MAP.items()})
KEY_TO_TOKEN.update({v: f"M{k}" for k, v in MID_MAP.items()})
KEY_TO_TOKEN.update({v: f"H{k}" for k, v in HIGH_MAP.items()})
KEY_TO_TOKEN.update({v: k for k, v in CHORD_MAP.items()})

IGNORE_KEY_NAMES = set([
    'tab', 'caps_lock', 'capslock', 'shift', 'shift_l', 'shift_r',
    'ctrl', 'ctrl_l', 'ctrl_r', 'alt', 'alt_l', 'alt_r', 'alt_gr',
    'cmd', 'cmd_l', 'cmd_r', 'win', 'windows', 'super',
])
# f1~f12 不计入录制事件，但允许作为热键（热键检测独立于忽略列表）
IGNORE_KEY_NAMES.update([f"f{i}" for i in range(1, 13)])

MAX_DURATION_SEC = 60 * 60  # 1 hour

SHIFT_SYMBOL_TO_DIGIT = {
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7',
}


def seconds_to_ts(sec: float) -> str:
    if sec < 0:
        sec = 0
    m = int(sec // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    return f"[{m:02d}:{s:02d}.{ms:03d}]"


class RecorderWindow(QtWidgets.QDialog):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        if keyboard is None:
            QtWidgets.QMessageBox.critical(self, '缺少依赖', '需要安装 pynput 模块\n请先执行: pip install pynput')
            self.setResult(QtWidgets.QDialog.Rejected)
            self.close()
            return
        self.setWindowTitle('动作录制 (.lrcp)')
        self.setModal(False)
        # 移除右上角帮助按钮
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)
        self.setFixedWidth(520)

        # 状态
        self.is_recording = False
        self.is_paused = False
        self.start_time_monotonic: float = 0.0
        self.pause_started_at: Optional[float] = None
        self.total_paused: float = 0.0

        self.pressed_at: Dict[str, float] = {}
        self.events: List[Tuple[float, float, str]] = []

        self.elapsed_var = QtWidgets.QLabel('00:00.000')
        self.count_var = QtWidgets.QLabel('0')

        self.hk_start = QtWidgets.QComboBox(); self.hk_start.addItems([f'F{i}' for i in range(1, 13)]); self.hk_start.setCurrentText('F6')
        self.hk_pause = QtWidgets.QComboBox(); self.hk_pause.addItems([f'F{i}' for i in range(1, 13)]); self.hk_pause.setCurrentText('F7')
        self.hk_stop = QtWidgets.QComboBox(); self.hk_stop.addItems([f'F{i}' for i in range(1, 13)]); self.hk_stop.setCurrentText('F8')

        self._build_ui()

        # 监听器
        self.listener = None           # 记录事件的低层监听
        self.hk_listener = None        # 全局热键监听
        self._start_global_listener()
        self._setup_hotkeys()

        # 当热键配置变化时，重建全局热键
        self.hk_start.currentTextChanged.connect(self._setup_hotkeys)
        self.hk_pause.currentTextChanged.connect(self._setup_hotkeys)
        self.hk_stop.currentTextChanged.connect(self._setup_hotkeys)

        self.ui_timer = QtCore.QTimer(self)
        self.ui_timer.timeout.connect(self._tick)
        self.ui_timer.start(50)

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        row_top = QtWidgets.QHBoxLayout()
        row_top.addWidget(QtWidgets.QLabel('已录制时间：'))
        row_top.addWidget(self.elapsed_var)
        row_top.addSpacing(10)
        row_top.addWidget(QtWidgets.QLabel('事件数：'))
        row_top.addWidget(self.count_var)
        layout.addLayout(row_top)

        row_btn = QtWidgets.QHBoxLayout()
        self.btn_start = QtWidgets.QPushButton('开始录制 (F6)'); self.btn_start.clicked.connect(self.start_record)
        self.btn_pause = QtWidgets.QPushButton('暂停录制 (F7)'); self.btn_pause.setEnabled(False); self.btn_pause.clicked.connect(self.pause_record)
        self.btn_stop = QtWidgets.QPushButton('停止录制 (F8)'); self.btn_stop.setEnabled(False); self.btn_stop.clicked.connect(self.stop_record)
        row_btn.addWidget(self.btn_start); row_btn.addWidget(self.btn_pause); row_btn.addWidget(self.btn_stop)
        layout.addLayout(row_btn)

        row_exp = QtWidgets.QHBoxLayout()
        self.btn_export = QtWidgets.QPushButton('导出 .lrcp'); self.btn_export.setEnabled(False); self.btn_export.clicked.connect(self.export_lrcp)
        row_exp.addWidget(self.btn_export)
        row_exp.addStretch()
        layout.addLayout(row_exp)

        hot = QtWidgets.QGroupBox('热键设置')
        grid = QtWidgets.QGridLayout(hot)
        grid.addWidget(QtWidgets.QLabel('开始录制：'), 0, 0)
        grid.addWidget(self.hk_start, 0, 1)
        grid.addWidget(QtWidgets.QLabel('暂停录制：'), 0, 2)
        grid.addWidget(self.hk_pause, 0, 3)
        grid.addWidget(QtWidgets.QLabel('停止录制：'), 0, 4)
        grid.addWidget(self.hk_stop, 0, 5)
        layout.addWidget(hot)

        tips = QtWidgets.QGroupBox('使用提示')
        v = QtWidgets.QVBoxLayout(tips)
        lab = QtWidgets.QLabel(
            '- 打开游戏并聚焦游戏窗口后点击开始或按热键开始录制。\n'
            '- 录制上限 1 小时，超时会自动停止。\n'
            '- 忽略按键：Tab, CapsLock, Shift, Ctrl, Win, Alt, F1~F12。\n'
            '- 游戏内F1~F5及F11~F12被占用，请勿设置为热键\n'
            '- 键位映射：\n'
            '  低音 L1~L7 -> a s d f g h j\n  中音 M1~M7 -> q w e r t y u\n  高音 H1~H7 -> 1 2 3 4 5 6 7\n  和弦 C/Dm/Em/F/G/Am/G7 -> z x c v b n m\n'
        )
        lab.setWordWrap(True)
        v.addWidget(lab)
        layout.addWidget(tips)

    def _setup_hotkeys(self):
        """使用 pynput.keyboard.GlobalHotKeys 注册全局热键，支持在焦点不在本窗口时触发。"""
        if keyboard is None:
            return
        # 停止旧的热键监听
        if getattr(self, 'hk_listener', None) is not None:
            try:
                self.hk_listener.stop()
            except Exception:
                pass
            self.hk_listener = None
        try:
            start_key = f"<{self.hk_start.currentText().lower()}>"
            pause_key = f"<{self.hk_pause.currentText().lower()}>"
            stop_key = f"<{self.hk_stop.currentText().lower()}>"
            mapping = {
                start_key: lambda: QtCore.QTimer.singleShot(0, self.start_record),
                pause_key: lambda: QtCore.QTimer.singleShot(0, self.pause_record),
                stop_key:  lambda: QtCore.QTimer.singleShot(0, self.stop_record),
            }
            self.hk_listener = keyboard.GlobalHotKeys(mapping)
            self.hk_listener.start()
        except Exception:
            self.hk_listener = None

    def _start_global_listener(self):
        if keyboard is None:
            return
        def on_press(key):
            # 仅负责录制用的按键按下记录（热键另由 GlobalHotKeys 处理）
            try:
                name = self._key_to_name(key)
            except Exception:
                return
            if not self.is_recording or self.is_paused:
                return
            if name in IGNORE_KEY_NAMES:
                return
            token = self._name_to_token(name)
            if not token:
                return
            if name in self.pressed_at:
                return
            now = self._now_record_time()
            self.pressed_at[name] = now
        def on_release(key):
            try:
                name = self._key_to_name(key)
            except Exception:
                return
            if not self.is_recording:
                return
            if name in IGNORE_KEY_NAMES:
                return
            token = self._name_to_token(name)
            if not token:
                return
            if name not in self.pressed_at:
                return
            start = self.pressed_at.pop(name)
            end = self._now_record_time()
            if end - 0.0001 > MAX_DURATION_SEC:
                end = float(MAX_DURATION_SEC)
            if end < start:
                end = start
            self.events.append((start, end, token))
            # 录制过程中实时更新事件数
            QtCore.QTimer.singleShot(0, lambda: self.count_var.setText(str(len(self.events))))
        self.listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.listener.start()

    def _key_to_name(self, key) -> str:
        if keyboard is None:
            return ''
        if isinstance(key, keyboard.KeyCode):
            ch = key.char
            if ch is None:
                return ''
            ch = SHIFT_SYMBOL_TO_DIGIT.get(ch, ch)
            return ch.lower()
        else:
            name = str(key).replace('Key.', '').lower()
            if name == 'caps_lock':
                name = 'capslock'
            if name == 'cmd':
                name = 'win'
            return name

    def _name_to_token(self, name: str) -> Optional[str]:
        if not name:
            return None
        return KEY_TO_TOKEN.get(name)

    def _now_record_time(self) -> float:
        now = time.perf_counter()
        extra_paused = 0.0
        if self.is_paused and self.pause_started_at is not None:
            extra_paused = max(0.0, now - self.pause_started_at)
        return max(0.0, now - self.start_time_monotonic - self.total_paused - extra_paused)

    # 控制
    def start_record(self):
        if self.is_recording and not self.is_paused:
            return
        if not self.is_recording:
            self.is_recording = True
            self.is_paused = False
            self.start_time_monotonic = time.perf_counter()
            self.total_paused = 0.0
            self.events.clear()
            self.pressed_at.clear()
            self.count_var.setText('0')
            if hasattr(self, 'generated_text'):
                try:
                    delattr(self, 'generated_text')
                except Exception:
                    self.generated_text = ''
        else:
            self.is_paused = False
            if self.pause_started_at is not None:
                self.total_paused += (time.perf_counter() - self.pause_started_at)
                self.pause_started_at = None
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self.btn_export.setEnabled(False)
        self.setWindowTitle('动作录制 (.lrcp) - 录制中…')

    def pause_record(self):
        if not self.is_recording:
            return
        if not self.is_paused:
            self.is_paused = True
            self.pause_started_at = time.perf_counter()
            self.btn_start.setEnabled(True)
            self.btn_pause.setEnabled(False)
            self.setWindowTitle('动作录制 (.lrcp) - 已暂停')

    def stop_record(self):
        if not self.is_recording:
            return
        stop_t = self._now_record_time()
        for name, st in list(self.pressed_at.items()):
            token = self._name_to_token(name)
            if token:
                self.events.append((st, stop_t, token))
        self.pressed_at.clear()

        self.is_recording = False
        self.is_paused = False
        self.pause_started_at = None
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.btn_export.setEnabled(True)
        self.setWindowTitle('动作录制 (.lrcp) - 已停止，可导出')

        self.generated_text = self._build_lrcp_text()
        self.count_var.setText(str(len(self.events)))

    def _build_lrcp_text(self) -> str:
        evs = list(self.events)
        evs.sort(key=lambda x: (round(x[0], 6), round(x[1], 6), x[2]))
        grouped: Dict[Tuple[int, int], List[str]] = {}
        for st, ed, tok in evs:
            st_ms = int(round(st * 1000))
            ed_ms = int(round(ed * 1000))
            key = (st_ms, ed_ms)
            grouped.setdefault(key, []).append(tok)
        lines: List[str] = []
        for (st_ms, ed_ms), toks in sorted(grouped.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            st = st_ms / 1000.0
            ed = ed_ms / 1000.0
            ts1 = seconds_to_ts(st)
            ts2 = seconds_to_ts(ed)
            tokens = ' '.join(toks)
            lines.append(f"{ts1}{ts2} {tokens}")
        return '\n'.join(lines) + ('\n' if lines else '')

    def export_lrcp(self):
        if not getattr(self, 'generated_text', None):
            QtWidgets.QMessageBox.information(self, '提示', '当前没有可导出的录制数据，请先停止录制。')
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, '导出为 .lrcp', 'recorded.lrcp', 'LRCP 文件 (*.lrcp);;文本文件 (*.txt);;所有文件 (*.*)')
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.generated_text)
            QtWidgets.QMessageBox.information(self, '成功', f'已保存：{path}')
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, '保存失败', str(e))

    def _tick(self):
        # 动态更新时间显示与事件数
        if self.is_recording:
            el = self._now_record_time()
            if el >= MAX_DURATION_SEC:
                self.stop_record()
                el = MAX_DURATION_SEC
            self.elapsed_var.setText(self._fmt_time(el))
            # 确保录制过程中事件数实时更新
            self.count_var.setText(str(len(self.events)))
        self.btn_start.setText(f"开始录制 ({self.hk_start.currentText()})")
        self.btn_pause.setText(f"暂停录制 ({self.hk_pause.currentText()})")
        self.btn_stop.setText(f"停止录制 ({self.hk_stop.currentText()})")

    @staticmethod
    def _fmt_time(sec: float) -> str:
        if sec < 0:
            sec = 0
        m = int(sec // 60)
        s = int(sec % 60)
        ms = int(round((sec - int(sec)) * 1000))
        return f"{m:02d}:{s:02d}.{ms:03d}"

    def closeEvent(self, e):
        try:
            if self.listener:
                self.listener.stop()
        except Exception:
            pass
        try:
            if getattr(self, 'hk_listener', None):
                self.hk_listener.stop()
        except Exception:
            pass
        super().closeEvent(e)


_singleton_ref: Optional[RecorderWindow] = None


def open_recorder_window(parent: Optional[QtWidgets.QWidget] = None):
    global _singleton_ref
    try:
        if _singleton_ref is not None:
            try:
                _singleton_ref.show()
                _singleton_ref.raise_()
                _singleton_ref.activateWindow()
                return
            except Exception:
                _singleton_ref = None
        _singleton_ref = RecorderWindow(parent)
        _singleton_ref.show()
    except Exception as e:
        QtWidgets.QMessageBox.critical(parent, '录制器异常', str(e))


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    w = RecorderWindow()
    w.show()
    app.exec_()
