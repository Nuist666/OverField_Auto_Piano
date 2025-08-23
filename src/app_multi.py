from typing import List
import os
import re

from PyQt5 import QtWidgets

from src.app import BaseApp
from src.player import Player
from src.event import Event, SimpleEvent
from utils.parse import parse_score, preprocess


class MultiApp(BaseApp):
    def __init__(self):
        super().__init__('多人模式 - 自动弹琴 (去和弦+分散)', create_key_display=False)

        # 多人模式说明
        grp = QtWidgets.QGroupBox('说明')
        v = QtWidgets.QVBoxLayout(grp)
        txt = QtWidgets.QLabel(
            '多人模式策略:\n'
            '1) 去掉所有和弦，只保留单音。\n'
            '2) 对同一事件中的多个单音按顺序施加时间偏移以分散密度。\n'
            '3) 偏移不修改原谱文件，仅运行时生效。\n'
            '4) 适度调整偏移可减少漏音（建议 -20~20 范围内微调）。'
        )
        txt.setWordWrap(True)
        v.addWidget(txt)
        self.layout().addWidget(grp)

        # 在说明后创建按键显示
        self._create_key_display_frame()

        # 参数：偏移输入
        params_grp = self.findChild(QtWidgets.QGroupBox, '参数')
        # 若找不到，则直接加一个行
        form_row = QtWidgets.QHBoxLayout()
        lab = QtWidgets.QLabel('多音偏移(ms):')
        self.ent_offsets = QtWidgets.QLineEdit()
        self.ent_offsets.setFixedWidth(120)
        self.ent_offsets.setText('-15,0,15')
        help_lab = QtWidgets.QLabel('范围-50~50，按顺序循环应用到同一时间的多个音')
        form_row.addWidget(lab)
        form_row.addWidget(self.ent_offsets)
        form_row.addWidget(help_lab)
        self.layout().addLayout(form_row)

        # 可统一控制
        if hasattr(self, 'param_widgets'):
            self.param_widgets.append(self.ent_offsets)

        self.raw_events: List[Event] = []
        self.play_events: List[SimpleEvent] = []

    def _parse_score(self, score_text: str) -> List[Event]:
        return parse_score(score_text, multi=True)

    def _after_load(self, path: str, events: List[Event]):
        self.raw_events = events
        self.update_play_events()
        self.lbl_file.setText(os.path.basename(path))
        self.lbl_status.setText(f'已载入（原始事件 {len(self.raw_events)} -> 预处理后 {len(self.play_events)} 单音事件）')
        self.btn_start.setEnabled(True)

    def start_play(self):
        if not self.play_events:
            return
        try:
            speed = float(self.ent_speed.currentText())
        except Exception:
            speed = 1.0
        try:
            countin = float(self.ent_countin.currentText())
        except Exception:
            countin = 2.0
        try:
            latency = int(self.ent_latency.value())
        except Exception:
            latency = 0
        try:
            progress_freq = int(self.ent_progress_freq.currentText())
        except Exception:
            progress_freq = 1

        # 重新生成
        self.update_play_events()
        self.btn_start.setEnabled(True)
        self.btn_start.setText('暂停')
        self.btn_stop.setEnabled(True)
        self.lbl_status.setText(f'演奏中… (总 {len(self.play_events)} 单音事件)')
        self.reset_progress()
        self.disable_params()

        def on_done():
            self.bus.finished.emit()

        def progress_cb(cur: int, total: int):
            self.bus.progress.emit(cur, total)

        self.player = Player(self.play_events, countin, latency, speed, on_done, progress_cb, progress_freq)
        self.player.start()

    def parse_offsets(self) -> List[int]:
        text = self.ent_offsets.text().strip()
        if not text:
            return [0]
        parts = [p for p in re.split(r'[;,\s]+', text) if p]
        offs: List[int] = []
        for p in parts:
            try:
                v = int(float(p))
                if v < -50:
                    v = -50
                if v > 50:
                    v = 50
                offs.append(v)
            except Exception:
                continue
        return offs or [0]

    def update_play_events(self):
        offsets = self.parse_offsets()
        self.play_events = preprocess(self.raw_events, offsets)


if __name__ == '__main__':
    pass
