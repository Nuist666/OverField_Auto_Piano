import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from src.player import Player
from src.event import Event


class BaseApp:
    def __init__(self, root: tk.Tk, title: str):
        self.root = root
        self.root.title(title)
        self.score_text: Optional[str] = None
        self.player: Optional[Player] = None

        self.frm = tk.Frame(root, padx=10, pady=10)
        self.frm.pack(fill="both", expand=True)

        self._create_file_bar()
        self._create_params_frame()
        self._create_control_frame()
        self._create_tips_frame()

    def _create_file_bar(self):
        file_bar = tk.Frame(self.frm)
        file_bar.pack(fill="x")
        tk.Button(file_bar, text="载入乐谱", command=self.load_score).pack(side="left")
        self.lbl_file = tk.Label(file_bar, text="未载入")
        self.lbl_file.pack(side="left", padx=8)

    def _create_params_frame(self):
        params = tk.LabelFrame(self.frm, text="参数")
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
        
        # 添加进度更新频率配置
        tk.Label(params, text="进度更新频率：").grid(row=1, column=0, sticky="e")
        self.ent_progress_freq = tk.Entry(params, width=8)
        self.ent_progress_freq.insert(0, "1")
        self.ent_progress_freq.grid(row=1, column=1, sticky="w", padx=6)
        tk.Label(params, text="(1=每个动作都更新, 2=每2个动作更新, 以此类推)").grid(row=1, column=2, columnspan=4, sticky="w")

    def _create_control_frame(self):
        ctrl = tk.Frame(self.frm)
        ctrl.pack(fill="x", pady=6)
        self.btn_start = tk.Button(ctrl, text="开始演奏", command=self.toggle_play_pause, state="disabled")
        self.btn_start.pack(side="left", padx=4)
        self.btn_stop = tk.Button(ctrl, text="停止", command=self.stop_play, state="disabled")
        self.btn_stop.pack(side="left", padx=4)
        self.lbl_status = tk.Label(ctrl, text="状态：等待载入乐谱")
        self.lbl_status.pack(side="left", padx=10)
        
        # 添加进度条框架
        progress_frame = tk.Frame(self.frm)
        progress_frame.pack(fill="x", pady=4)
        self.lbl_progress = tk.Label(progress_frame, text="进度：0%")
        self.lbl_progress.pack(side="left", padx=10)
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=300)
        self.progress_bar.pack(side="left", padx=4, fill="x", expand=True)

    def _create_tips_frame(self):
        tips = tk.LabelFrame(self.frm, text="使用提示")
        tips.pack(fill="x", pady=8)
        tk.Label(tips, justify="left", anchor="w", text=(
            "1) 乐谱支持延长音：写法 [起始时间][结束时间] TOKENS\n"
            "2) 单时间戳仍可用作短音：[时间] TOKENS\n"
            "3) 载入后切换到游戏窗口，回到本工具点击开始；\n"
            "4) 如无响应尝试以管理员身份运行 Python。"
        )).pack(fill="x")

    def update_progress(self, current: int, total: int):
        """更新进度条和进度标签"""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar['value'] = percentage
            self.lbl_progress.config(text=f"进度：{percentage}% ({current}/{total})")
        else:
            self.progress_bar['value'] = 0
            self.lbl_progress.config(text="进度：0%")

    def reset_progress(self):
        """重置进度条"""
        self.progress_bar['value'] = 0
        self.lbl_progress.config(text="进度：0%")

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
                events = self._parse_score(self.score_text)
                if not events:
                    raise ValueError("未解析出任何事件，请检查格式。")
                self._after_load(path, events)
                return
            except Exception as e:
                messagebox.showerror("转换失败", f"MIDI 转换为 LRCP 失败：\n{e}")
                return

        # 其它情况按文本/谱文件读取
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.score_text = f.read()
            events = self._parse_score(self.score_text)
            if not events:
                raise ValueError("未解析出任何事件，请检查格式。")
            self._after_load(path, events)
        except Exception as e:
            messagebox.showerror("载入失败", str(e))

    def _parse_score(self, score_text: str) -> List[Event]:
        """子类实现具体的解析逻辑"""
        raise NotImplementedError

    def _after_load(self, path: str, events: List[Event]):
        """子类实现加载后的处理逻辑"""
        raise NotImplementedError

    def start_play(self):
        """子类实现开始播放逻辑"""
        raise NotImplementedError

    def stop_play(self):
        if self.player:
            self.player.stop()
            self.player = None
            self.reset_progress()
            # 恢复按钮与状态
            self.btn_start.config(state="normal", text="开始演奏")
            self.btn_stop.config(state="disabled")
            self.lbl_status.config(text="完成/已停止")

    def toggle_play_pause(self):
        """开始/暂停/继续 切换。若未开始则调用子类的 start_play。"""
        if not self.player:
            # 未开始：启动
            self.start_play()
            return
        # 已有 player：切换暂停/继续
        try:
            if hasattr(self.player, 'is_paused') and self.player.is_paused():
                self.player.resume()
                self.btn_start.config(text="暂停")
                self.lbl_status.config(text="演奏中…")
            else:
                # 进入暂停
                if hasattr(self.player, 'pause'):
                    self.player.pause()
                    self.btn_start.config(text="继续")
                    self.lbl_status.config(text="已暂停")
        except Exception:
            try:
                self.stop_play()
            except Exception:
                pass


if __name__ == '__main__':
    pass
