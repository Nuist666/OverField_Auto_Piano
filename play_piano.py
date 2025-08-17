#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 钢琴自动演奏 - 可视化脚本 (Tkinter)
功能：
- 载入乐谱（LRC 风格时间戳），解析为事件队列
- 一键开始/停止自动按键（模拟键盘）
- 支持节奏倍速、起始延迟（倒计时）、全局延迟（打穿游戏输入延迟）
- 面板展示按键映射关系，便于校对
注意：
- 需在 Windows 上运行，并确保游戏窗口在“开始演奏”后处于焦点
- 发送键盘事件默认使用 pyautogui（通用），也可切换为 keyboard 库（更低级，但可能需要管理员权限）
"""
import os
import re
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from dataclasses import dataclass
from typing import List, Tuple, Optional

# === 依赖：pyautogui（默认） / keyboard（可选） ===
USE_KEYBOARD_LIB = True  # 如使用 keyboard，请置 True 并安装：pip install keyboard
try:
    if USE_KEYBOARD_LIB:
        import keyboard  # 可能需要管理员权限
    else:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0  # 发送更密集的键
except Exception as e:
    print("依赖导入失败：", e)

# === 键位映射（根据你的描述硬编码） ===
LOW_MAP = {str(i): k for i, k in zip(range(1, 8), list("asdfghj"))}      # 低音1-7 -> a s d f g h j
MID_MAP = {str(i): k for i, k in zip(range(1, 8), list("qwertyu"))}      # 中音1-7 -> q w e r t y u
HIGH_MAP = {str(i): k for i, k in zip(range(1, 8), list("1234567"))}     # 高音1-7 -> 1 2 3 4 5 6 7
CHORD_MAP = {"C":"z","Dm":"x","Em":"c","F":"v","G":"b","Am":"n","G7":"m"} # 和弦 -> z x c v b n m

# 允许的音符 token：
# L1-L7（低音），M1-M7（中音），H1-H7（高音），以及和弦名（C Dm Em F G Am G7）
TOKEN_NOTE_RE = re.compile(r"(?:(?:[LMH][1-7])|(?:C|Dm|Em|F|G|Am|G7))")

# 时间戳形如：[mm:ss.xxx]，毫秒 .xxx 可省略
TS_RE = re.compile(r"\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]")

@dataclass
class Event:
    t: float             # 触发时间（秒）
    keys: List[str]      # 同步触发的一组按键（和弦/多音）

def parse_line(line: str) -> List[Tuple[float, List[str]]]:
    """
    解析一行，可能包含多个时间戳。格式：
    [mm:ss.xxx] TOKENS...
    同一时间戳后面用空格分隔的多个 token 表示“同时触发”。
    同一行如果有多个时间戳，则认为它们分别作用于相同的 token 片段（与 LRC 类似）。
    例如：
      [00:01.200] M1 M3  -> 在 1.200s 同时按下 M1 与 M3
      [00:02.000][00:03.000] C -> 在 2.000s 和 3.000s 分别按下和弦 C
    """
    # 提取所有时间戳
    ts = list(TS_RE.finditer(line))
    if not ts:
        return []
    # 时间戳后面的内容
    tail_start = ts[-1].end()
    tokens_str = line[tail_start:].strip()
    if not tokens_str:
        return []

    # 校验 token
    tokens = tokens_str.split()
    valid_tokens = [tok for tok in tokens if TOKEN_NOTE_RE.fullmatch(tok)]
    if not valid_tokens:
        return []

    # 将 token 转为具体按键
    keys = []
    for tok in valid_tokens:
        if tok[0] in ("L","M","H"):
            octave = tok[0]
            num = tok[1]
            if octave == "L":
                keys.append(LOW_MAP[num])
            elif octave == "M":
                keys.append(MID_MAP[num])
            else:
                keys.append(HIGH_MAP[num])
        else:
            # 和弦
            keys.append(CHORD_MAP[tok])

    # 对每个时间戳创建一组事件
    events = []
    for m in ts:
        mm = int(m.group(1))
        ss = int(m.group(2))
        ms = int((m.group(3) or "0").ljust(3, "0"))
        t = mm * 60 + ss + ms / 1000.0
        events.append((t, keys.copy()))
    return events

def parse_score(text: str) -> List[Event]:
    events: List[Event] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parsed = parse_line(line)
        for t, keys in parsed:
            events.append(Event(t=t, keys=keys))
    # 按时间排序
    events.sort(key=lambda e: e.t)
    return events

def send_keys(keys: List[str]):
    """同一时刻的多键并发触发：先 press 再 release。"""
    if not keys:
        return
    if USE_KEYBOARD_LIB:
        # keyboard 库：按下再释放
        for k in keys:
            try: keyboard.press(k)
            except: pass
        for k in keys:
            try: keyboard.release(k)
            except: pass
    else:
        # pyautogui：逐个 tap（足够快，基本同时）
        for k in keys:
            try: 
                # pyautogui.press 会 press+release
                # 为了更紧凑的和弦，可用 keyDown 再 keyUp
                pyautogui.keyDown(k)
            except: 
                pass
        for k in keys:
            try: pyautogui.keyUp(k)
            except: pass

class Player(threading.Thread):
    def __init__(self, events: List[Event], start_delay: float, global_latency_ms: int, speed_ratio: float, on_done):
        super().__init__(daemon=True)
        self.events = events
        self.start_delay = max(0.0, start_delay)
        self.global_latency = max(0, global_latency_ms) / 1000.0
        self.speed_ratio = max(0.05, speed_ratio)
        self._stop = threading.Event()
        self.on_done = on_done

    def stop(self):
        self._stop.set()

    def run(self):
        try:
            if not self.events:
                return
            # 将速度比率应用到事件时间轴
            scaled = [Event(t=e.t / self.speed_ratio, keys=e.keys) for e in self.events]
            t0 = time.perf_counter() + self.start_delay
            idx = 0
            while idx < len(scaled) and not self._stop.is_set():
                now = time.perf_counter()
                target = t0 + scaled[idx].t + self.global_latency
                wait = target - now
                if wait > 0:
                    time.sleep(min(wait, 0.01))
                    continue
                # 触发这个事件
                send_keys(scaled[idx].keys)
                idx += 1
        finally:
            if self.on_done:
                self.on_done()

class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Windows 钢琴自动演奏")
        self.score_text: Optional[str] = None
        self.events: List[Event] = []
        self.player: Optional[Player] = None

        # UI —— 控件
        frm = tk.Frame(root, padx=10, pady=10)
        frm.pack(fill="both", expand=True)

        # 文件操作
        file_bar = tk.Frame(frm)
        file_bar.pack(fill="x")
        tk.Button(file_bar, text="载入乐谱", command=self.load_score).pack(side="left")
        self.lbl_file = tk.Label(file_bar, text="未载入")
        self.lbl_file.pack(side="left", padx=8)

        # 参数
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

        # 映射表
        mapping = tk.LabelFrame(frm, text="键位映射（请确保与游戏一致）")
        mapping.pack(fill="x", pady=8)

        def row(lbl, txt):
            r = tk.Frame(mapping); r.pack(fill="x", pady=1)
            tk.Label(r, text=lbl, width=8, anchor="w").pack(side="left")
            tk.Label(r, text=txt, anchor="w").pack(side="left")

        row("低音 L:", "L1-L7 -> a s d f g h j")
        row("中音 M:", "M1-M7 -> q w e r t y u")
        row("高音 H:", "H1-H7 -> 1 2 3 4 5 6 7")
        row("和弦 :", "C Dm Em F G Am G7 -> z x c v b n m")

        # 控制
        ctrl = tk.Frame(frm); ctrl.pack(fill="x", pady=6)
        self.btn_start = tk.Button(ctrl, text="开始演奏", command=self.start_play, state="disabled")
        self.btn_start.pack(side="left", padx=4)
        self.btn_stop = tk.Button(ctrl, text="停止", command=self.stop_play, state="disabled")
        self.btn_stop.pack(side="left", padx=4)
        self.lbl_status = tk.Label(ctrl, text="状态：等待载入乐谱")
        self.lbl_status.pack(side="left", padx=10)

        # 说明
        tips = tk.LabelFrame(frm, text="使用提示")
        tips.pack(fill="x", pady=8)
        tk.Label(tips, justify="left", anchor="w", text=(
            "1) 点击“载入乐谱”选择 .lrcp 文件；\n"
            "2) 切回游戏窗口；设置好镜头；\n"
            "3) 回到本工具，点击“开始演奏”；倒计时后开始；\n"
            "4) 期间可按“停止”随时中止。\n"
            "建议：若无响应，尝试以管理员身份运行 Python。"
        )).pack(fill="x")

    def load_score(self):
        path = filedialog.askopenfilename(
            title="选择乐谱文件(.lrcp)",
            filetypes=[("Piano LRC", "*.lrcp"), ("文本", "*.txt"), ("所有文件", "*.*")]
        )
        if not path: 
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.score_text = f.read()
            self.events = parse_score(self.score_text)
            if not self.events:
                raise ValueError("未解析出任何事件，请检查格式。")
            self.lbl_file.config(text=os.path.basename(path))
            self.lbl_status.config(text=f"已载入，共 {len(self.events)} 个事件。")
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
