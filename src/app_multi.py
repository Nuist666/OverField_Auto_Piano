import os
import re
import tkinter as tk
from typing import List

from src.app import BaseApp
from src.player import Player
from src.event import Event, SimpleEvent
from utils.parse import parse_score, preprocess


class MultiApp(BaseApp):
    def __init__(self, root: tk.Tk):
        super().__init__(root, "多人模式 - 自动弹琴 (去和弦+分散)", create_key_display=False)
        self.raw_events: List[Event] = []
        self.play_events: List[SimpleEvent] = []

        # 修改提示信息为多人模式特有
        tips = self.frm.winfo_children()[-1]  # 获取最后一个子元素（tips）
        tips.config(text="说明")
        tk.Label(tips, justify="left", anchor="w", text=(
            '多人模式策略:\n'
            '1) 去掉所有和弦，只保留单音。\n'
            '2) 对同一事件中的多个单音按顺序施加时间偏移以分散密度。\n'
            '3) 偏移不修改原谱文件，仅运行时生效。\n'
            '4) 适度调整偏移可减少漏音（建议 -20~20 范围内微调）。'
        )).pack(fill="x")
        
        # 在说明框架之后添加独立的按键显示框架（窗口内）
        self._create_key_display_frame()

        # 添加多人模式特有的参数 - 使用正确的行数
        params = self.frm.winfo_children()[1]  # 获取第二个子元素（params）
        tk.Label(params, text="多音偏移(ms):").grid(row=2, column=0, sticky="e")
        self.ent_offsets = tk.Entry(params, width=11)
        self.ent_offsets.insert(0, "-15,0,15")
        self.ent_offsets.grid(row=2, column=1, columnspan=3, sticky="w", padx=4)
        tk.Label(params, text="范围-50~50，按顺序循环应用到同一时间的多个音").grid(row=2, column=2, columnspan=2, sticky="w")
        # 把偏移输入框加入可统一控制的参数控件
        if hasattr(self, 'param_widgets'):
            self.param_widgets.append(self.ent_offsets)

    def _parse_score(self, score_text: str) -> List[Event]:
        return parse_score(score_text, multi=True)

    def _after_load(self, path: str, events: List[Event]):
        self.raw_events = events
        self.update_play_events()
        self.lbl_file.config(text=os.path.basename(path))
        self.lbl_status.config(text=f'已载入（原始事件 {len(self.raw_events)} -> 预处理后 {len(self.play_events)} 单音事件）')
        self.btn_start.config(state="normal")

    def start_play(self):
        if not self.play_events:
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

        # 每次开始前按当前偏移重新生成
        self.update_play_events()
        # 开始后：启用停止按钮；开始按钮显示为“暂停”并保持可点击
        self.btn_start.config(state="normal", text="暂停")
        self.btn_stop.config(state="normal")
        self.lbl_status.config(text=f'演奏中… (总 {len(self.play_events)} 单音事件)')
        
        # 重置进度条
        self.reset_progress()
        # 禁用参数，避免误输入
        self.disable_params()

        def on_done():
            self.btn_start.config(state="normal", text="开始演奏")
            self.btn_stop.config(state="disabled")
            self.lbl_status.config(text='完成/已停止')
            self.player = None
            # 恢复参数
            self.enable_params()

        self.player = Player(self.play_events, countin, latency, speed, on_done, self.update_progress, progress_freq)
        self.player.start()

    def parse_offsets(self) -> List[int]:
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

    def update_play_events(self):
        offsets = self.parse_offsets()
        self.play_events = preprocess(self.raw_events, offsets)


if __name__ == '__main__':
    pass
