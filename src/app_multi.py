import re
from typing import List
import tkinter as tk

from src.app import BaseApp
from src.event import Event, SimpleEvent
from src.player import Player
from utils.parse import parse_score, preprocess


class AppMulti(BaseApp):
    def __init__(self, root: tk.Tk):
        super().__init__(root, "多人模式 - 自动弹琴 (去和弦+分散)")
        self.player = None
        self.play_events: List[SimpleEvent] = []

        # 添加多人模式特有的UI组件
        self.create_multi_params()
        self.create_multi_tips()

    def create_multi_params(self):
        """创建多人模式特有的参数设置"""
        params = self.frm.winfo_children()[1]  # 获取BaseApp中创建的params框架

        # 多音偏移设置
        tk.Label(params, text="多音偏移(ms):").grid(row=1, column=0, sticky="e")
        self.ent_offsets = tk.Entry(params, width=20)
        self.ent_offsets.insert(0, "-15,0,15")
        self.ent_offsets.grid(row=1, column=1, columnspan=3, sticky="w", padx=4)
        tk.Label(params, text="范围-50~50，按顺序循环应用到同一时间的多个音").grid(
            row=1, column=4, columnspan=2, sticky="w")

    def create_multi_tips(self):
        """创建多人模式特有的提示"""
        tips = tk.LabelFrame(self.frm, text="说明")
        tips.pack(fill="x", pady=8)
        tk.Label(tips, justify="left", anchor="w", text=(
            '多人模式策略:\n'
            '1) 去掉所有和弦，只保留单音。\n'
            '2) 对同一事件中的多个单音按顺序施加时间偏移以分散密度。\n'
            '3) 偏移不修改原谱文件，仅运行时生效。\n'
            '4) 适度调整偏移可减少漏音（建议 -20~20 范围内微调）。'
        )).pack(fill="x")

    def parse_offsets(self) -> List[int]:
        """解析偏移参数"""
        text = self.ent_offsets.get().strip()
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
            except:
                continue
        return offs or [0]

    def parse_score(self, score_text: str) -> List[Event]:
        """解析乐谱（多人模式版本）"""
        return parse_score(score_text, multi=True)

    def update_play_events(self):
        """更新演奏事件（应用偏移）"""
        offsets = self.parse_offsets()
        self.play_events = preprocess(self.events, offsets)

    def start_play(self):
        """开始演奏（多人模式版本）"""
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

        # 每次开始前按当前偏移重新生成
        self.update_play_events()
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.lbl_status.config(text=f'演奏中… (总 {len(self.play_events)} 单音事件)')

        def on_done():
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")
            self.lbl_status.config(text='完成/已停止')

        self.player = Player(self.play_events, countin, latency, speed, on_done)
        self.player.start()


if __name__ == "__main__":
    pass
