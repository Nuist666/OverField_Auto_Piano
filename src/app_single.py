import os
import tkinter as tk
from typing import List

from src.app import BaseApp
from src.event import Event
from src.player import Player
from utils.parse import parse_score


class SingleApp(BaseApp):
    def __init__(self, root: tk.Tk):
        super().__init__(root, "Windows 钢琴自动演奏")
        self.events: List[Event] = []

        # 添加单人模式特有的UI元素
        mapping = tk.LabelFrame(self.frm, text="键位映射（请确保与游戏一致）")
        mapping.pack(fill="x", pady=8)

        def row(lbl, txt):
            r = tk.Frame(mapping)
            r.pack(fill="x", pady=1)
            tk.Label(r, text=lbl, width=8, anchor="w").pack(side="left")
            tk.Label(r, text=txt, anchor="w").pack(side="left")

        row("低音 L:", "L1-L7 -> a s d f g h j")
        row("中音 M:", "M1-M7 -> q w e r t y u")
        row("高音 H:", "H1-H7 -> 1 2 3 4 5 6 7")
        row("和弦 :", "C Dm Em F G Am G7 -> z x c v b n m")

    def _parse_score(self, score_text: str) -> List[Event]:
        return parse_score(score_text)

    def _after_load(self, path: str, events: List[Event]):
        self.events = events
        self.lbl_file.config(text=os.path.basename(path))
        self.lbl_status.config(text=f"已载入，共 {len(self.events)} 个音符/和弦事件。")
        self.btn_start.config(state="normal")

    def start_play(self):
        if not self.events:
            return

        try:
            speed = float(self.ent_speed.get())
        except:
            speed = 1.0

        try:
            countin = float(self.ent_countin.get())
        except:
            countin = 2.0

        try:
            latency = int(float(self.ent_latency.get()))
        except:
            latency = 0
            
        try:
            progress_freq = int(float(self.ent_progress_freq.get()))
        except:
            progress_freq = 1

        self.btn_start.config(state="normal", text="暂停")
        self.btn_stop.config(state="normal")
        self.lbl_status.config(text="演奏中…（切到游戏保持焦点）")
        
        # 重置进度条
        self.reset_progress()

        def on_done():
            self.btn_start.config(state="normal", text="开始演奏")
            self.btn_stop.config(state="disabled")
            self.lbl_status.config(text="完成/已停止")
            self.player = None

        self.player = Player(self.events, countin, latency, speed, on_done, self.update_progress, progress_freq)
        self.player.start()


if __name__ == "__main__":
    pass
