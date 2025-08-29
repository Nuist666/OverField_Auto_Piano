import os
import tkinter as tk
from tkinter import ttk
from typing import List

from src.app import BaseApp
from src.event import Event
from src.player import Player
from utils.parse import parse_score


class SingleApp(BaseApp):
    def __init__(self, root: tk.Tk):
        super().__init__(root, "Windows 自动演奏 (钢琴/架子鼓)")
        self.events: List[Event] = []

        # 键位映射提示（根据乐器切换刷新）
        self.mapping_frame = ttk.LabelFrame(self.frm, text="键位映射（请确保与游戏一致）")
        self.mapping_frame.pack(fill="x", pady=8)
        self._mapping_rows: List[tk.Widget] = []
        self._render_mapping()

        # 监听乐器切换以更新映射说明
        self.instrument_var.trace_add('write', lambda *_: self._render_mapping())

    def _clear_mapping(self):
        for w in self._mapping_rows:
            try:
                w.destroy()
            except Exception:
                pass
        self._mapping_rows.clear()

    def _render_mapping(self):
        self._clear_mapping()
        def row(lbl, txt):
            r = ttk.Frame(self.mapping_frame)
            r.pack(fill="x", pady=1)
            ttk.Label(r, text=lbl, width=10, anchor="w").pack(side="left")
            ttk.Label(r, text=txt, anchor="w").pack(side="left")
            self._mapping_rows.append(r)
        if self.get_instrument() == 'piano':
            row("低音 L:", "L1-L7 -> a s d f g h j")
            row("中音 M:", "M1-M7 -> q w e r t y u")
            row("高音 H:", "H1-H7 -> 1 2 3 4 5 6 7")
            row("和弦 :", "C Dm Em F G Am G7 -> z x c v b n m")
        else:
            row("架子鼓:", "踩镲闭->1  高音吊镲->2  一嗵鼓->3  二嗵鼓->4  叮叮镲->5")
            row("", "踩镲开->Q  军鼓->W  底鼓->E  落地嗵鼓->R  中音吊镲->T")

    def _parse_score(self, score_text: str) -> List[Event]:
        # 根据乐器决定解析模式
        return parse_score(score_text, multi=False)

    def _after_load(self, path: str, events: List[Event]):
        self.events = events
        self.lbl_file.config(text=os.path.basename(path))
        self.lbl_status.config(text=f"已载入，共 {len(self.events)} 个事件。")
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
        # 禁用参数，避免误输入
        self.disable_params()
        
        # 重置进度条
        self.reset_progress()

        def on_done():
            self.btn_start.config(state="normal", text="开始演奏")
            self.btn_stop.config(state="disabled")
            self.lbl_status.config(text="完成/已停止")
            self.player = None
            # 恢复参数
            self.enable_params()

        self.player = Player(self.events, countin, latency, speed, on_done, self.update_progress, progress_freq)
        self.player.start()


if __name__ == "__main__":
    pass
