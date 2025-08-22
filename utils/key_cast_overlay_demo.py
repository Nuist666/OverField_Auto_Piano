import tkinter as tk
from pynput import keyboard
from collections import deque
import threading
import time
from typing import Optional, Dict

# 默认设置
DEFAULT_SETTINGS = {
    "enabled": True,           # 默认开启
    "opacity": 0.7,           # 0.0~1.0
    "max_keys": 5,            # 显示最近几个按键
    "display_time": 2.0,      # 每个按键显示多久（秒）
    "position": "bottom_center",  # 位置：top_left/top_right/bottom_left/bottom_right/bottom_center/top_center
}


class KeyCastOverlay:
    """
    可嵌入到现有 Tk 应用中的按键叠加层。
    - 若传入 master（主窗口/根窗口），将创建一个 Toplevel 充当叠加层，不会自启 mainloop；
    - 若不传 master，可独立运行：调用 run_demo() 启动其自身的 mainloop。
    """

    def __init__(self, master: Optional[tk.Misc] = None, settings: Optional[Dict] = None):
        self.master = master
        self._own_root = master is None
        self._running_cleanup = False
        self._cleanup_thread: Optional[threading.Thread] = None
        self.listener: Optional[keyboard.Listener] = None

        # 合并设置
        self.settings: Dict = DEFAULT_SETTINGS.copy()
        if settings:
            self.settings.update(settings)

        # 初始化窗口
        if self._own_root:
            self.root = tk.Tk()
            self.window = self.root  # 独立运行时直接用 root 作为窗口
        else:
            self.root = None
            self.window = tk.Toplevel(self.master)

        self.window.overrideredirect(True)  # 去掉窗口边框
        self.window.attributes("-topmost", True)  # 置顶
        self.window.attributes("-alpha", float(self.settings.get("opacity", 0.7)))

        # 固定窗口大小（可按需调整）
        self.w, self.h = 600, 80
        self._apply_position()

        # 标签显示按键
        self.label = tk.Label(
            self.window,
            text="",
            font=("Consolas", 24, "bold"),
            fg="white",
            bg="black"
        )
        self.label.pack(expand=True, fill="both")

        # 按键缓存
        self.keys = deque(maxlen=int(self.settings.get("max_keys", 5)))
        self.last_press_time: Dict[str, float] = {}

        # 根据 enabled 初始化显示/监听
        self.set_enabled(bool(self.settings.get("enabled", False)))

        # 关闭回调
        self.window.protocol("WM_DELETE_WINDOW", self.close)

    # ---------- 公共方法 ----------
    def set_enabled(self, enabled: bool):
        self.settings["enabled"] = enabled
        if enabled:
            self.window.deiconify()
            self._start_listener()
            self._start_cleanup_loop()
        else:
            self.window.withdraw()
            self._stop_listener()
            self._stop_cleanup_loop()

    def apply_settings(self, new_settings: Dict):
        # 仅更新已知键
        for k in DEFAULT_SETTINGS.keys():
            if k in new_settings:
                self.settings[k] = new_settings[k]

        # 应用窗口属性
        try:
            self.window.attributes("-alpha", float(self.settings.get("opacity", 0.7)))
        except Exception:
            pass

        # 更新最多按键数量
        max_keys = int(self.settings.get("max_keys", 5))
        if max_keys != self.keys.maxlen:
            new_deque = deque(self.keys, maxlen=max_keys)
            self.keys = new_deque
            self._schedule_display_update()

        # 位置
        self._apply_position()

        # 若开关变化外部会再调用 set_enabled，这里不处理 enabled

    def close(self):
        self.set_enabled(False)
        try:
            if self._own_root and self.root is not None:
                self.root.destroy()
            else:
                self.window.destroy()
        except Exception:
            pass

    # ---------- 内部方法 ----------
    def _apply_position(self):
        # 计算窗口位置
        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()
        pos = self.settings.get("position", "bottom_center")
        w, h = self.w, self.h

        if pos == "top_left":
            x, y = 20, 20
        elif pos == "top_right":
            x, y = sw - w - 20, 20
        elif pos == "bottom_left":
            x, y = 20, sh - h - 60
        elif pos == "bottom_right":
            x, y = sw - w - 20, sh - h - 60
        elif pos == "top_center":
            x, y = (sw - w) // 2, 20
        else:  # bottom_center
            x, y = (sw - w) // 2, sh - h - 60

        try:
            self.window.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    def _start_listener(self):
        if self.listener is not None:
            return
        def on_press(key):
            try:
                k = key.char.upper()
            except AttributeError:
                k = str(key).replace("Key.", "").upper()
            self.keys.append(k)
            self.last_press_time[k] = time.time()
            self._schedule_display_update()
        try:
            self.listener = keyboard.Listener(on_press=on_press)
            self.listener.start()
        except Exception:
            self.listener = None

    def _stop_listener(self):
        if self.listener is not None:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None

    def _start_cleanup_loop(self):
        if self._running_cleanup:
            return
        self._running_cleanup = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def _stop_cleanup_loop(self):
        self._running_cleanup = False
        # 线程为 daemon，不必 join

    def _cleanup_loop(self):
        while self._running_cleanup:
            now = time.time()
            disp_time = float(self.settings.get("display_time", 2.0))
            removed = False
            for k in list(self.keys):
                if now - self.last_press_time.get(k, 0) > disp_time:
                    try:
                        self.keys.remove(k)
                        removed = True
                    except ValueError:
                        pass
            if removed:
                self._schedule_display_update()
            time.sleep(0.2)

    def _schedule_display_update(self):
        # 保证在主线程更新 UI
        def _do():
            self.label.config(text="  ".join(self.keys))
        try:
            self.window.after(0, _do)
        except Exception:
            pass

    # ---------- 独立运行演示 ----------
    def run_demo(self):
        if not self._own_root:
            return  # 非独立模式不负责 mainloop
        # 独立模式下默认启用
        self.set_enabled(True)
        try:
            self.root.mainloop()
        finally:
            self.close()


if __name__ == "__main__":
    # 独立运行演示
    KeyCastOverlay().run_demo()
