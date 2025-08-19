import os
import pyautogui
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional

from utils.parse import *
from src.player import Player
from src.event import Event
from utils.util import admin_running

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0  # 发送更密集的键
admin_running()


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Windows 钢琴自动演奏")
        self.score_text: Optional[str] = None
        self.events: List[Event] = []
        self.player: Optional[Player] = None

        frm = tk.Frame(root, padx=10, pady=10)
        frm.pack(fill="both", expand=True)

        file_bar = tk.Frame(frm)
        file_bar.pack(fill="x")
        tk.Button(file_bar, text="载入乐谱", command=self.load_score).pack(side="left")
        self.lbl_file = tk.Label(file_bar, text="未载入")
        self.lbl_file.pack(side="left", padx=8)

        params = tk.LabelFrame(frm, text="参数")
        params.pack(fill="x", pady=8)
        tk.Label(params, text="速度比例(1.0为原速)：").grid(row=0, column=0, sticky="e")
        self.ent_speed = tk.Entry(params, width=8)
        self.ent_speed.insert(0, "1.0")
        self.ent_speed.grid(row=0, column=1, sticky="w", padx=6)
        tk.Label(params, text="起始倒计时(秒)：").grid(row=0, column=2, sticky="e")
        self.ent_countin = tk.Entry(params, width=8)
        self.ent_countin.insert(0, "2.0")
        self.ent_countin.grid(row=0, column=3, sticky="w", padx=6)
        tk.Label(params, text="全局延迟(毫秒)：").grid(row=0, column=4, sticky="e")
        self.ent_latency = tk.Entry(params, width=8)
        self.ent_latency.insert(0, "0")
        self.ent_latency.grid(row=0, column=5, sticky="w", padx=6)

        mapping = tk.LabelFrame(frm, text="键位映射（请确保与游戏一致）")
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

        ctrl = tk.Frame(frm)
        ctrl.pack(fill="x", pady=6)
        self.btn_start = tk.Button(ctrl, text="开始演奏", command=self.start_play, state="disabled")
        self.btn_start.pack(side="left", padx=4)
        self.btn_stop = tk.Button(ctrl, text="停止", command=self.stop_play, state="disabled")
        self.btn_stop.pack(side="left", padx=4)
        self.lbl_status = tk.Label(ctrl, text="状态：等待载入乐谱")
        self.lbl_status.pack(side="left", padx=10)

        tips = tk.LabelFrame(frm, text="使用提示")
        tips.pack(fill="x", pady=8)
        tk.Label(tips, justify="left", anchor="w", text=(
            "1) 乐谱支持延长音：写法 [起始时间][结束时间] TOKENS\n"
            "2) 单时间戳仍可用作短音：[时间] TOKENS\n"
            "3) 载入后切换到游戏窗口，回到本工具点击开始；\n"
            "4) 如无响应尝试以管理员身份运行 Python。"
        )).pack(fill="x")

    def load_score(self):
        """加载乐谱文件，支持 .lrcp 或 .mid；若为 .mid 则先自动转换为 .lrcp 再读取"""
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
                self.events = parse_score(self.score_text)
                if not self.events:
                    raise ValueError("未解析出任何事件，请检查格式。")
                self.lbl_file.config(text=os.path.basename(path))
                self.lbl_status.config(text=f"已载入，共 {len(self.events)} 个音符/和弦事件。")
                self.btn_start.config(state="normal")
                return
            except Exception as e:
                messagebox.showerror("转换失败", f"MIDI 转换为 LRCP 失败：\n{e}")
                return

        # 其它情况按文本/谱文件读取
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.score_text = f.read()
            self.events = parse_score(self.score_text)
            if not self.events:
                raise ValueError("未解析出任何事件，请检查格式。")
            self.lbl_file.config(text=os.path.basename(path))
            self.lbl_status.config(text=f"已载入，共 {len(self.events)} 个音符/和弦事件。")
            self.btn_start.config(state="normal")
        except Exception as e:
            messagebox.showerror("载入失败", str(e))

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

        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.lbl_status.config(text="演奏中…（切到游戏保持焦点）")

        def on_done():
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")
            self.lbl_status.config(text="完成/已停止")

        self.player = Player(self.events, countin, latency, speed, on_done)
        self.player.start()

    def stop_play(self):
        if self.player:
            self.player.stop()
            self.player = None


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
