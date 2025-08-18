import os
import tkinter as tk
from typing import List, Optional
from tkinter import filedialog, messagebox

from src.event import Event
from src.player import Player


class BaseApp:
    def __init__(self, root: tk.Tk, title: str):
        self.root = root
        self.root.title(title)

        # 窗口居中设置
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = 700
        window_height = 400
        position_top = int(screen_height / 2 - window_height / 2)
        position_left = int(screen_width / 2 - window_width / 2)
        self.root.geometry(f'{window_width}x{window_height}+{position_left}+{position_top}')

        self.score_text: Optional[str] = None
        self.events: List[Event] = []
        self.player: Optional[Player] = None

        self.create_widgets()

    def create_widgets(self):
        """创建基本界面组件，子类可扩展"""
        self.frm = tk.Frame(self.root, padx=10, pady=10)
        self.frm.pack(fill="both", expand=True)

        # 文件加载栏
        self.create_file_bar()

        # 参数设置栏
        self.create_params_frame()

        # 控制按钮栏
        self.create_control_frame()

    def create_file_bar(self):
        """创建文件加载相关UI"""
        file_bar = tk.Frame(self.frm)
        file_bar.pack(fill="x")
        tk.Button(file_bar, text="载入乐谱", command=self.load_score).pack(side="left")
        self.lbl_file = tk.Label(file_bar, text="未载入")
        self.lbl_file.pack(side="left", padx=8)

    def create_params_frame(self):
        """创建参数设置UI"""
        params = tk.LabelFrame(self.frm, text="参数")
        params.pack(fill="x", pady=8)

        # 速度比例
        tk.Label(params, text="速度比例(1.0为原速)：").grid(row=0, column=0, sticky="e")
        self.ent_speed = tk.Entry(params, width=8)
        self.ent_speed.insert(0, "1.0")
        self.ent_speed.grid(row=0, column=1, sticky="w", padx=6)

        # 起始倒计时
        tk.Label(params, text="起始倒计时(秒)：").grid(row=0, column=2, sticky="e")
        self.ent_countin = tk.Entry(params, width=8)
        self.ent_countin.insert(0, "2.0")
        self.ent_countin.grid(row=0, column=3, sticky="w", padx=6)

        # 全局延迟
        tk.Label(params, text="全局延迟(毫秒)：").grid(row=0, column=4, sticky="e")
        self.ent_latency = tk.Entry(params, width=8)
        self.ent_latency.insert(0, "0")
        self.ent_latency.grid(row=0, column=5, sticky="w", padx=6)

    def create_control_frame(self):
        """创建控制按钮UI"""
        ctrl = tk.Frame(self.frm)
        ctrl.pack(fill="x", pady=6)
        self.btn_start = tk.Button(ctrl, text="开始演奏", command=self.start_play, state="disabled")
        self.btn_start.pack(side="left", padx=4)
        self.btn_stop = tk.Button(ctrl, text="停止", command=self.stop_play, state="disabled")
        self.btn_stop.pack(side="left", padx=4)
        self.lbl_status = tk.Label(ctrl, text="状态：等待载入乐谱")
        self.lbl_status.pack(side="left", padx=10)

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
                self.events = self.parse_score(self.score_text)
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
            self.events = self.parse_score(self.score_text)
            if not self.events:
                raise ValueError("未解析出任何事件，请检查格式。")
            self.lbl_file.config(text=os.path.basename(path))
            self.lbl_status.config(text=f"已载入，共 {len(self.events)} 个音符/和弦事件。")
            self.btn_start.config(state="normal")
        except Exception as e:
            messagebox.showerror("载入失败", str(e))

    def parse_score(self, score_text: str) -> List[Event]:
        """解析乐谱，子类必须实现"""
        raise NotImplementedError("子类必须实现 parse_score 方法")

    def start_play(self):
        """开始演奏，子类可重写"""
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
        """停止演奏"""
        if self.player:
            self.player.stop()
            self.player = None


if __name__ == "__main__":
    pass
