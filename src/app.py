import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional
import threading
import time
from collections import deque

from src.player import Player
from src.event import Event
from utils.key_cast_overlay import KeyCastOverlay
from utils.lrcp_recorder import open_recorder_window
from utils.custom_key import CustomKeyMap, KeyMapEditor


class BaseApp:
    def __init__(self, root: tk.Tk, title: str, create_key_display: bool = True):
        self.root = root
        self.root.title(title)
        self.score_text: Optional[str] = None
        self.player: Optional[Player] = None

        # 初始化 ttkbootstrap（如可用），默认主题 superhero
        self._ttkb = None
        self.style = None
        try:
            import ttkbootstrap as ttkb  # type: ignore
            self._ttkb = ttkb
            self.style = ttkb.Style(theme='superhero')
        except Exception:
            self._ttkb = None
            self.style = None

        # 主框架
        self.frm = ttk.Frame(root, padding=(10, 10))
        self.frm.pack(fill="both", expand=True)

        # 乐器选择（钢琴/架子鼓）
        self._create_instrument_frame()
        self._create_file_bar()
        self._create_params_frame()
        self._create_control_frame()
        self._create_tips_frame()

        # 根据参数决定是否创建按键显示框架
        if create_key_display:
            self._create_key_display_frame()

        # 初始化按键显示相关变量（窗口内）
        self.keys = deque(maxlen=14)  # 显示最近maxlen个按键
        self.last_press_time = {}
        self.running = True
        self.key_listener = None  # 键盘监听器实例
        self.key_listener_active = False  # 键盘监听器是否激活

        # 覆盖层（窗口外）默认设置与实例（默认开启）
        self.keycast_settings = {
            "enabled": True,
            "opacity": 0.7,
            "max_keys": 5,
            "display_time": 2.0,
            "position": "bottom_center",
        }
        # 在主 Tk 上创建一个无边框置顶的 Toplevel 作为覆盖层
        try:
            self.keycast_overlay = KeyCastOverlay(self.root, self.keycast_settings)
        except Exception:
            self.keycast_overlay = None

    def _create_instrument_frame(self):
        frm = ttk.LabelFrame(self.frm, text="乐器")
        frm.pack(fill="x", pady=(0, 8))
        self.instrument_var = tk.StringVar(value="piano")
        ttk.Radiobutton(frm, text="钢琴 (.lrcp / .mid)", variable=self.instrument_var, value="piano").pack(side="left",
                                                                                                           padx=4)
        ttk.Radiobutton(frm, text="架子鼓 (.lrcd / .mid)", variable=self.instrument_var, value="drum").pack(side="left",
                                                                                                            padx=8)

    def get_instrument(self) -> str:
        v = self.instrument_var.get().strip().lower()
        return "drum" if v == "drum" else "piano"

    def _create_file_bar(self):
        file_bar = ttk.Frame(self.frm)
        file_bar.pack(fill="x")
        ttk.Button(file_bar, text="载入乐谱", command=self.load_score).pack(side="left")
        self.lbl_file = ttk.Label(file_bar, text="未载入")
        self.lbl_file.pack(side="left", padx=8)

        # 右上角：主题切换（ttkbootstrap 可用时）
        if self.style is not None:
            try:
                # 仅列出 ttkbootstrap 主题
                theme_names = [t for t in self.style.theme_names() if t]
                current_theme = None
                try:
                    current_theme = self.style.theme_use()
                except Exception:
                    current_theme = theme_names[0] if theme_names else ""

                right_box = ttk.Frame(file_bar)
                right_box.pack(side="right")
                ttk.Label(right_box, text="主题：").pack(side="left")
                self.theme_var = tk.StringVar(value=current_theme)
                self.cbo_theme = ttk.Combobox(right_box, width=16, state="readonly", values=theme_names,
                                              textvariable=self.theme_var)
                self.cbo_theme.pack(side="left", padx=4)

                def on_theme_changed(event=None):
                    name = self.theme_var.get()
                    try:
                        self.style.theme_use(name)
                    except Exception:
                        pass

                self.cbo_theme.bind("<<ComboboxSelected>>", on_theme_changed)
            except Exception:
                pass

    def _create_params_frame(self):
        params = ttk.LabelFrame(self.frm, text="参数")
        params.pack(fill="x", pady=8)
        ttk.Label(params, text="速度比例(1.0为原速)：").grid(row=0, column=0, sticky="e")
        self.ent_speed = ttk.Combobox(params, width=8, state="readonly",
                                      values=["0.5", "0.75", "1.0", "1.25", "1.5", "1.75", "2.0", "2.25", "2.5"])
        self.ent_speed.set("1.0")
        self.ent_speed.grid(row=0, column=1, sticky="w", padx=6)
        ttk.Label(params, text="起始倒计时(秒)：").grid(row=0, column=2, sticky="e")
        self.ent_countin = ttk.Combobox(params, width=8, state="readonly", values=["0", "1", "2", "3", "4", "5"])
        self.ent_countin.set("2")
        self.ent_countin.grid(row=0, column=3, sticky="w", padx=6)
        ttk.Label(params, text="全局延迟(毫秒)：").grid(row=0, column=4, sticky="e")
        # Spinbox 使用 ttkbootstrap（如可用）
        if self._ttkb is not None and hasattr(self._ttkb, 'Spinbox'):
            self.ent_latency = self._ttkb.Spinbox(params, width=8, from_=-200, to=200, increment=5)
        else:
            self.ent_latency = tk.Spinbox(params, width=8, from_=-200, to=200, increment=5)
        self.ent_latency.delete(0, "end")
        self.ent_latency.insert(0, "0")
        self.ent_latency.grid(row=0, column=5, sticky="w", padx=6)

        # 添加进度更新频率配置
        ttk.Label(params, text="进度更新频率：").grid(row=1, column=0, sticky="e")
        self.ent_progress_freq = ttk.Combobox(params, width=8, state="readonly", values=["1", "2", "3", "5", "10"])
        self.ent_progress_freq.set("1")
        self.ent_progress_freq.grid(row=1, column=1, sticky="w", padx=6)
        ttk.Label(params, text="(1=每个动作都更新, 2=每2个动作更新, 以此类推)").grid(row=1, column=2, columnspan=4,
                                                                                     sticky="w")

        # 记录参数控件，便于统一禁用/启用
        self.param_widgets = [
            self.ent_speed,
            self.ent_countin,
            self.ent_latency,
            self.ent_progress_freq,
        ]

    def _create_control_frame(self):
        ctrl = ttk.Frame(self.frm)
        ctrl.pack(fill="x", pady=6)
        self.btn_start = ttk.Button(ctrl, text="开始演奏", command=self.toggle_play_pause, state="disabled")
        self.btn_start.pack(side="left", padx=4)
        self.btn_stop = ttk.Button(ctrl, text="停止", command=self.stop_play, state="disabled")
        self.btn_stop.pack(side="left", padx=4)
        # 新增：按键显示设置按钮
        self.btn_keycast = ttk.Button(ctrl, text="按键显示设置", command=self.open_keycast_settings)
        self.btn_keycast.pack(side="left", padx=4)
        # 新增：动作录制按钮（按当前乐器类型）
        self.btn_record = ttk.Button(ctrl, text="动作录制", command=lambda: open_recorder_window(self.root, self.get_instrument()))
        self.btn_record.pack(side="left", padx=4)
        
        # 新增：自定义按键映射按钮
        self.btn_custom_key = ttk.Button(ctrl, text="自定义按键映射", command=self.open_custom_key_map)
        self.btn_custom_key.pack(side="left", padx=4)

        self.lbl_status = ttk.Label(ctrl, text="状态：等待载入乐谱")
        self.lbl_status.pack(side="left", padx=10)

        # 添加进度条框架
        progress_frame = ttk.Frame(self.frm)
        progress_frame.pack(fill="x", pady=4)
        self.lbl_progress = ttk.Label(progress_frame, text="进度：0%")
        self.lbl_progress.pack(side="left", padx=10)
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=300)
        self.progress_bar.pack(side="left", padx=4, fill="x", expand=True)

    def _create_tips_frame(self):
        tips = ttk.LabelFrame(self.frm, text="使用提示")
        tips.pack(fill="x", pady=8)
        ttk.Label(tips, justify="left", anchor="w", text=(
            "1) 乐谱支持延长音：写法 [起始时间][结束时间] TOKENS\n"
            "2) 单时间戳仍可用作短音：[时间] TOKENS\n"
            "3) 载入后切换到游戏窗口，回到本工具点击开始；\n"
            "4) 如无响应尝试以管理员身份运行。"
        )).pack(fill="x")

    def _create_key_display_frame(self):
        """创建按键显示框架（窗口内）"""
        key_frame = ttk.LabelFrame(self.frm, text="按键显示")
        key_frame.pack(fill="x", pady=8)

        # 创建按键显示标签（使用主题样式）
        if self._ttkb is not None:
            self.lbl_keys = self._ttkb.Label(
                key_frame,
                text="等待按键...",
                font=("Consolas", 16, "bold"),
                bootstyle="secondary inverse",
                anchor="center",
                padding=6,
            )
        else:
            self.lbl_keys = ttk.Label(
                key_frame,
                text="等待按键...",
                font=("Consolas", 16, "bold"),
                anchor="center",
            )
        self.lbl_keys.pack(fill="x", padx=4, pady=4)

        # 添加说明文字
        ttk.Label(key_frame, text="实时显示当前按下的按键 (窗口内)", font=("微软雅黑", 9)).pack(anchor="w", padx=4)

    def open_custom_key_map(self):
        """打开自定义按键映射编辑器窗口"""
        # 创建按键映射管理器实例
        key_map_manager = CustomKeyMap()
        
        # 创建新窗口
        win = tk.Toplevel(self.root)
        win.title("自定义按键映射")
        win.transient(self.root)
        win.grab_set()
        
        # 创建按键映射编辑器
        editor = KeyMapEditor(win, key_map_manager)
        
        # 居中显示窗口
        win.update_idletasks()
        width = win.winfo_width()
        height = win.winfo_height()
        x = (win.winfo_screenwidth() // 2) - (width // 2)
        y = (win.winfo_screenheight() // 2) - (height // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")

    def open_keycast_settings(self):
        """打开覆盖层设置窗口"""
        # 备份当前设置用于取消恢复
        current = self.keycast_settings.copy()

        win = tk.Toplevel(self.root)
        win.title("按键显示设置")
        win.transient(self.root)
        win.grab_set()

        # 预设 -> 内部值映射
        pos_map = {
            "左上方": "top_left",
            "右上方": "top_right",
            "左下方": "bottom_left",
            "右下方": "bottom_right",
            "顶部居中": "top_center",
            "底部居中": "bottom_center",
        }
        pos_map_rev = {v: k for k, v in pos_map.items()}

        # 控件变量
        var_enabled = tk.BooleanVar(value=bool(current.get("enabled", True)))
        var_opacity = tk.DoubleVar(value=float(current.get("opacity", 0.7)))
        var_max_keys = tk.IntVar(value=int(current.get("max_keys", 5)))
        var_disp_time = tk.DoubleVar(value=float(current.get("display_time", 2.0)))
        var_position = tk.StringVar(value=pos_map_rev.get(current.get("position", "bottom_center"), "底部居中"))

        row = 0
        ttk.Checkbutton(win, text="打开实时按键显示", variable=var_enabled).grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=8)
        row += 1

        ttk.Label(win, text="透明度(0.2~1.0)：").grid(row=row, column=0, sticky="e", padx=6, pady=6)
        if self._ttkb is not None and hasattr(self._ttkb, 'Scale'):
            opacity_scale = self._ttkb.Scale(win, from_=0.2, to=1.0, orient="horizontal", length=200,
                                             variable=var_opacity)
        else:
            opacity_scale = tk.Scale(win, from_=0.2, to=1.0, orient="horizontal", resolution=0.05, variable=var_opacity,
                                     length=200)
        opacity_scale.grid(row=row, column=1, sticky="w", padx=6)
        row += 1

        ttk.Label(win, text="显示最近几个按键：").grid(row=row, column=0, sticky="e", padx=6, pady=6)
        if self._ttkb is not None and hasattr(self._ttkb, 'Spinbox'):
            maxkeys_spin = self._ttkb.Spinbox(win, from_=1, to=20, textvariable=var_max_keys, width=8)
        else:
            maxkeys_spin = tk.Spinbox(win, from_=1, to=20, textvariable=var_max_keys, width=8)
        maxkeys_spin.grid(row=row, column=1, sticky="w", padx=6)
        row += 1

        ttk.Label(win, text="每个按键显示(秒)：").grid(row=row, column=0, sticky="e", padx=6, pady=6)
        if self._ttkb is not None and hasattr(self._ttkb, 'Spinbox'):
            disptime_spin = self._ttkb.Spinbox(win, from_=0.5, to=10.0, increment=0.5, textvariable=var_disp_time,
                                               width=8)
        else:
            disptime_spin = tk.Spinbox(win, from_=0.5, to=10.0, increment=0.5, textvariable=var_disp_time, width=8)
        disptime_spin.grid(row=row, column=1, sticky="w", padx=6)
        row += 1

        ttk.Label(win, text="位置：").grid(row=row, column=0, sticky="e", padx=6, pady=6)
        ttk.Combobox(win, state="readonly", values=list(pos_map.keys()), textvariable=var_position, width=14).grid(
            row=row, column=1, sticky="w", padx=6)
        row += 1

        # 按钮
        btns = ttk.Frame(win)
        btns.grid(row=row, column=0, columnspan=2, pady=10)

        def on_ok():
            new_cfg = {
                "opacity": max(0.2, min(1.0, float(var_opacity.get()))),
                "max_keys": max(1, min(50, int(var_max_keys.get()))),
                "display_time": max(0.1, float(var_disp_time.get())),
                "position": pos_map.get(var_position.get(), "bottom_center"),
            }
            self.keycast_settings.update(new_cfg)
            # 应用到覆盖层
            if self.keycast_overlay:
                self.keycast_overlay.apply_settings(self.keycast_settings)
                self.keycast_overlay.set_enabled(bool(var_enabled.get()))
            # 同步到记录
            self.keycast_settings["enabled"] = bool(var_enabled.get())
            win.destroy()

        def on_cancel():
            # 取消不更改设置
            win.destroy()

        ttk.Button(btns, text="确认", command=on_ok).pack(side="left", padx=8)
        ttk.Button(btns, text="取消", command=on_cancel).pack(side="left", padx=8)

    def _start_key_listener(self):
        """启动按键监听线程（窗口内展示）"""
        self.keycast_overlay.start_key_listener()
        if self.key_listener_active:
            return  # 已经启动，避免重复启动

        try:
            from pynput import keyboard

            def on_press(key):
                """键盘按下事件"""
                if not self.key_listener_active:
                    return

                try:
                    k = key.char.upper()
                except AttributeError:
                    k = str(key).replace("Key.", "").upper()

                self.keys.append(k)
                self.last_press_time[k] = time.time()
                self._update_key_display()

            # 启动键盘监听器
            self.key_listener = keyboard.Listener(on_press=on_press)
            self.key_listener.start()
            self.key_listener_active = True

            # 启动清理过期按键的线程
            threading.Thread(target=self._cleanup_keys_loop, daemon=True).start()

        except ImportError:
            # 如果没有安装pynput，显示提示信息
            if hasattr(self, 'lbl_keys'):
                self.lbl_keys.config(
                    text="需要安装 pynput 模块\npip install pynput"
                )

    def _stop_key_listener(self):
        """停止按键监听线程"""
        self.keycast_overlay.stop_key_listener()
        if not self.key_listener_active:
            return  # 已经停止，避免重复停止

        self.key_listener_active = False

        if self.key_listener:
            try:
                self.key_listener.stop()
                self.key_listener = None
            except Exception:
                pass

        # 清空按键显示
        self.keys.clear()
        self.last_press_time.clear()
        self._update_key_display()

        # 清空覆盖层显示
        if self.keycast_overlay:
            try:
                self.keycast_overlay.clear_keys()
            except Exception:
                pass

    def _update_key_display(self):
        """更新按键显示（窗口内）"""
        if hasattr(self, 'lbl_keys'):
            if self.keys:
                display_text = "  ".join(self.keys)
                self.lbl_keys.config(text=display_text)
            else:
                self.lbl_keys.config(text="等待按键...")

    def _cleanup_keys_loop(self):
        """后台循环，清理过期按键（窗口内）"""
        while self.running and self.key_listener_active:
            now = time.time()
            removed = False
            for k in list(self.keys):
                if now - self.last_press_time.get(k, 0) > 2.0:  # 2秒后自动清除
                    try:
                        self.keys.remove(k)
                        removed = True
                    except ValueError:
                        pass
            if removed:
                self._update_key_display()
            time.sleep(0.2)

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

    def set_params_enabled(self, enabled: bool):
        """统一设置参数控件的启用/禁用。Combobox 用 readonly 表示可选但不可输入。"""
        for w in getattr(self, 'param_widgets', []):
            try:
                # ttk.Combobox 使用 readonly，其他控件使用 normal/disabled
                if isinstance(w, ttk.Combobox):
                    w.config(state="readonly" if enabled else "disabled")
                else:
                    w.config(state="normal" if enabled else "disabled")
            except Exception:
                pass

    def disable_params(self):
        self.set_params_enabled(False)

    def enable_params(self):
        self.set_params_enabled(True)

    def load_score(self):
        """加载乐谱文件，根据乐器类型支持：
        - 钢琴：.lrcp 或 .mid
        - 架子鼓：.lrcd 或 .mid
        若为 .mid 则自动转换为对应文本格式后解析。
        """
        ins = self.get_instrument()
        if ins == 'piano':
            filetypes = [("钢琴谱/或MIDI", "*.lrcp *.mid *.midi"), ("所有文件", "*.*")]
        else:
            filetypes = [("架子鼓谱/或MIDI", "*.lrcd *.mid *.midi"), ("所有文件", "*.*")]
        path = filedialog.askopenfilename(title="选择乐谱或MIDI文件", filetypes=filetypes)
        if not path:
            return

        ext = os.path.splitext(path)[1].lower()
        # MIDI -> 文本
        if ext in (".mid", ".midi"):
            try:
                if ins == 'piano':
                    from utils.midi2lrcp import midi_to_lrcp_text
                    self.score_text = midi_to_lrcp_text(path)
                else:
                    from utils.midi2lrcd import midi_to_lrcd_text
                    self.score_text = midi_to_lrcd_text(path)
                events = self._parse_score(self.score_text)
                if not events:
                    raise ValueError("未解析出任何事件，请检查格式。")
                self._after_load(path, events)
                return
            except Exception as e:
                messagebox.showerror("转换失败", f"MIDI 转换失败：\n{e}")
                return

        # 文本谱读取
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
            self.enable_params()
            # 停止键盘监听
            self._stop_key_listener()
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
                self._start_key_listener()
            else:
                # 进入暂停
                if hasattr(self.player, 'pause'):
                    self.player.pause()
                    self.btn_start.config(text="继续")
                    self.lbl_status.config(text="已暂停")
                    self._stop_key_listener()
        except Exception:
            try:
                self.stop_play()
            except Exception:
                pass

    def __del__(self):
        """析构函数，清理资源"""
        self.running = False
        if hasattr(self, 'key_listener'):
            try:
                self.key_listener.stop()
            except:
                pass
        if hasattr(self, 'keycast_overlay') and self.keycast_overlay:
            try:
                self.keycast_overlay.close()
            except Exception:
                pass


if __name__ == '__main__':
    pass
