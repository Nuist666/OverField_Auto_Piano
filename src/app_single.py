import os
from typing import List

from PyQt5 import QtWidgets

from src.app import BaseApp
from src.event import Event
from src.player import Player
from utils.parse import parse_score


class SingleApp(BaseApp):
    def __init__(self):
        super().__init__('Windows 钢琴自动演奏')

        # 键位映射说明
        grp = QtWidgets.QGroupBox('键位映射（请确保与游戏一致）')
        v = QtWidgets.QVBoxLayout(grp)
        def add_row(text: str):
            lbl = QtWidgets.QLabel(text)
            v.addWidget(lbl)
        add_row('低音 L:  L1-L7 -> a s d f g h j')
        add_row('中音 M:  M1-M7 -> q w e r t y u')
        add_row('高音 H:  H1-H7 -> 1 2 3 4 5 6 7')
        add_row('和弦   :  C Dm Em F G Am G7 -> z x c v b n m')
        self.layout().addWidget(grp)

        self.events: List[Event] = []

    def _parse_score(self, score_text: str) -> List[Event]:
        return parse_score(score_text)

    def _after_load(self, path: str, events: List[Event]):
        self.events = events
        self.lbl_file.setText(os.path.basename(path))
        self.lbl_status.setText(f'已载入，共 {len(self.events)} 个音符/和弦事件。')
        self.btn_start.setEnabled(True)

    def start_play(self):
        if not getattr(self, 'events', None):
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

        self.btn_start.setEnabled(True)
        self.btn_start.setText('暂停')
        self.btn_stop.setEnabled(True)
        self.lbl_status.setText('演奏中…（切到游戏保持焦点）')
        self.disable_params()
        self.reset_progress()

        def on_done():
            # bridge from worker thread to GUI
            self.bus.finished.emit()

        def progress_cb(cur: int, total: int):
            self.bus.progress.emit(cur, total)

        self.player = Player(self.events, countin, latency, speed, on_done, progress_cb, progress_freq)
        self.player.start()


if __name__ == '__main__':
    pass
