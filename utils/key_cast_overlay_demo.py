import tkinter as tk
from pynput import keyboard
from collections import deque
import threading
import time

MAX_KEYS = 5  # 显示最近几个按键
DISPLAY_TIME = 2.0  # 每个按键显示多久（秒）


class KeyCastOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)  # 去掉窗口边框
        self.root.attributes("-topmost", True)  # 窗口置顶
        self.root.attributes("-alpha", 0.7)  # 半透明

        # 设置窗口大小和位置（屏幕底部居中）
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 400, 80
        x, y = (sw - w) // 2, sh - h - 50
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        # 标签显示按键
        self.label = tk.Label(
            self.root,
            text="",
            font=("Consolas", 24, "bold"),
            fg="white",
            bg="black"
        )
        self.label.pack(expand=True, fill="both")

        # 按键缓存
        self.keys = deque(maxlen=MAX_KEYS)
        self.last_press_time = {}

        # 键盘监听器
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()

        # 后台线程定时清理过期按键
        self.running = True
        threading.Thread(target=self.cleanup_loop, daemon=True).start()

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.mainloop()

    def on_press(self, key):
        """键盘按下事件"""
        try:
            k = key.char.upper()
        except AttributeError:
            k = str(key).replace("Key.", "").upper()

        self.keys.append(k)
        self.last_press_time[k] = time.time()
        self.update_display()

    def update_display(self):
        """更新显示内容"""
        self.label.config(text="  ".join(self.keys))

    def cleanup_loop(self):
        """后台循环，清理过期按键"""
        while self.running:
            now = time.time()
            removed = False
            for k in list(self.keys):
                if now - self.last_press_time.get(k, 0) > DISPLAY_TIME:
                    try:
                        self.keys.remove(k)
                        removed = True
                    except ValueError:
                        pass
            if removed:
                self.update_display()
            time.sleep(0.2)

    def close(self):
        self.running = False
        self.listener.stop()
        self.root.destroy()


if __name__ == "__main__":
    KeyCastOverlay()
