import os
import pyautogui
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional

from utils.parse import *
from utils.util import admin_running
from src.event import Event, SimpleEvent
from src.player import Player

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0
admin_running()


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("多人模式 - 自动弹琴 (去和弦+分散)")
        self.score_text: Optional[str] = None
        self.raw_events: List[Event] = []
        self.play_events: List[SimpleEvent] = []
        self.player: Optional[Player] = None

        frm = tk.Frame(root, padx=10, pady=10)
        frm.pack(fill='both', expand=True)
        file_bar = tk.Frame(frm)
        file_bar.pack(fill='x')
        tk.Button(file_bar, text='载入乐谱', command=self.load_score).pack(side='left')
        self.lbl_file = tk.Label(file_bar, text='未载入')
        self.lbl_file.pack(side='left', padx=8)

        params = tk.LabelFrame(frm, text='参数')
        params.pack(fill='x', pady=8)
        tk.Label(params, text='速度比例:').grid(row=0, column=0, sticky='e')
        self.ent_speed = tk.Entry(params, width=8)
        self.ent_speed.insert(0, '1.0')
        self.ent_speed.grid(row=0, column=1, sticky='w', padx=4)
        tk.Label(params, text='起始倒计时(s):').grid(row=0, column=2, sticky='e')
        self.ent_countin = tk.Entry(params, width=8)
        self.ent_countin.insert(0, '2.0')
        self.ent_countin.grid(row=0, column=3, sticky='w', padx=4)
        tk.Label(params, text='全局延迟(ms):').grid(row=0, column=4, sticky='e')
        self.ent_latency = tk.Entry(params, width=8)
        self.ent_latency.insert(0, '0')
        self.ent_latency.grid(row=0, column=5, sticky='w', padx=4)
        tk.Label(params, text='多音偏移(ms):').grid(row=1, column=0, sticky='e')
        self.ent_offsets = tk.Entry(params, width=20)
        self.ent_offsets.insert(0, '-15,0,15')
        self.ent_offsets.grid(row=1, column=1, columnspan=3, sticky='w', padx=4)
        tk.Label(params, text='范围-50~50，按顺序循环应用到同一时间的多个音').grid(row=1, column=4, columnspan=2, sticky='w')

        ctrl = tk.Frame(frm)
        ctrl.pack(fill='x', pady=6)
        self.btn_start = tk.Button(ctrl, text='开始演奏', command=self.start_play, state='disabled')
        self.btn_start.pack(side='left', padx=4)
        self.btn_stop = tk.Button(ctrl, text='停止', command=self.stop_play, state='disabled')
        self.btn_stop.pack(side='left', padx=4)
        self.lbl_status = tk.Label(ctrl, text='状态：等待载入乐谱')
        self.lbl_status.pack(side='left', padx=10)

        tips = tk.LabelFrame(frm, text='说明')
        tips.pack(fill='x', pady=8)
        tk.Label(tips, justify='left', anchor='w', text=(
            '多人模式策略:\n'
            '1) 去掉所有和弦，只保留单音。\n'
            '2) 对同一事件中的多个单音按顺序施加时间偏移以分散密度。\n'
            '3) 偏移不修改原谱文件，仅运行时生效。\n'
            '4) 适度调整偏移可减少漏音（建议 -20~20 范围内微调）。'
        )).pack(fill='x')

    def load_score(self):
        path = filedialog.askopenfilename(
            title="选择乐谱或MIDI文件(.lrcp/.mid)",
            filetypes=[("所有文件", "*.*")]
        )
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        if ext in (".mid", ".midi"):
            try:
                from utils.midi2lrcp import midi_to_lrcp_text
            except Exception as e:
                messagebox.showerror("载入失败", f"无法导入 MIDI 转换模块，请确认已安装 pretty_midi 等依赖。\n错误：{e}")
                return
            try:
                self.score_text = midi_to_lrcp_text(path)
                self.raw_events = parse_score(self.score_text)
                if not self.raw_events:
                    raise ValueError('未解析出任何事件。')
                self.update_play_events()
                self.lbl_file.config(text=os.path.basename(path))
                self.lbl_status.config(text=f'已载入（原始事件 {len(self.raw_events)} -> 预处理后 {len(self.play_events)} 单音事件）')
                self.btn_start.config(state='normal')
                return
            except Exception as e:
                messagebox.showerror("转换失败", f"MIDI 转换为 LRCP 失败：\n{e}")
                return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.score_text = f.read()
            self.raw_events = parse_score(self.score_text, multi=True)
            if not self.raw_events:
                raise ValueError('未解析出任何事件。')
            self.update_play_events()
            self.lbl_file.config(text=os.path.basename(path))
            self.lbl_status.config(text=f'已载入（原始事件 {len(self.raw_events)} -> 预处理后 {len(self.play_events)} 单音事件）')
            self.btn_start.config(state='normal')
        except Exception as e:
            messagebox.showerror('载入失败', str(e))

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

        # 每次开始前按当前偏移重新生成
        self.update_play_events()
        self.btn_start.config(state='disabled')
        self.btn_stop.config(state='normal')
        self.lbl_status.config(text=f'演奏中… (总 {len(self.play_events)} 单音事件)')

        def on_done():
            self.btn_start.config(state='normal')
            self.btn_stop.config(state='disabled')
            self.lbl_status.config(text='完成/已停止')

        self.player = Player(self.play_events, countin, latency, speed, on_done)
        self.player.start()

    def stop_play(self):
        if self.player:
            self.player.stop()
            self.player = None

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


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
