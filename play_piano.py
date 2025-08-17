#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 钢琴自动演奏 - 可视化脚本 (Tkinter)
功能：
- 载入乐谱（LRC 风格时间戳），解析为事件队列
- 支持延长音：一行两个时间戳 [start][end] TOKENS -> 按下后保持到 end 再释放
- 单时间戳仍兼容，视为即刻点按（tap）
- 一键开始/停止自动按键（模拟键盘）
- 支持节奏倍速、起始延迟（倒计时）、全局延迟（打穿游戏输入延迟）
- 面板展示按键映射关系，便于校对
注意：
- 需在 Windows 上运行，并确保游戏窗口在“开始演奏”后处于焦点
- 发送键盘事件默认使用 keyboard（可更改 USE_KEYBOARD_LIB）
"""
import os
import re
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

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
TOKEN_NOTE_RE = re.compile(r"(?:(?:[LMH][1-7])|(?:C|Dm|Em|F|G|Am|G7))")
# 时间戳形如：[mm:ss.xxx]，毫秒 .xxx 可省略
TS_RE = re.compile(r"\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]")

@dataclass
class Event:
    start: float          # 按下时间（秒）
    end: float            # 释放时间（秒），若与 start 相同表示立刻松开（tap）
    keys: List[str]       # 同步触发的一组按键（和弦/多音）

# === 解析 ===

def _ts_match_to_seconds(m: re.Match) -> float:
    mm = int(m.group(1)); ss = int(m.group(2)); ms = int((m.group(3) or "0").ljust(3, "0"))
    return mm * 60 + ss + ms / 1000.0

def parse_line(line: str) -> List[Event]:
    """解析一行：
    1) 延长音： [start][end] TOKENS  -> 在 start 按下，在 end 释放
    2) 多个独立时间： [t1][t2] TOKENS 但若 t1==t2 或未按升序，可视为两个独立 tap
    3) 单时间戳： [t] TOKENS -> tap
    4) 兼容旧写法：多个时间戳后跟 token -> 分别 tap
    """
    ts = list(TS_RE.finditer(line))
    if not ts:
        return []
    tail_start = ts[-1].end()
    tokens_str = line[tail_start:].strip()
    if not tokens_str:
        return []
    tokens = tokens_str.split()
    valid_tokens = [tok for tok in tokens if TOKEN_NOTE_RE.fullmatch(tok)]
    if not valid_tokens:
        return []

    # token -> key
    keys: List[str] = []
    for tok in valid_tokens:
        if tok[0] in ("L","M","H"):
            octave = tok[0]; num = tok[1]
            if octave == "L": keys.append(LOW_MAP[num])
            elif octave == "M": keys.append(MID_MAP[num])
            else: keys.append(HIGH_MAP[num])
        else:
            keys.append(CHORD_MAP[tok])

    events: List[Event] = []
    # 延长音情形：恰好两个时间戳且第二个时间 > 第一个
    if len(ts) == 2:
        t1 = _ts_match_to_seconds(ts[0]); t2 = _ts_match_to_seconds(ts[1])
        if t2 > t1:  # 视为延长音
            events.append(Event(start=t1, end=t2, keys=keys.copy()))
            return events
    # 其它：全部视为独立 tap
    for m in ts:
        t = _ts_match_to_seconds(m)
        events.append(Event(start=t, end=t, keys=keys.copy()))
    return events

def parse_score(text: str) -> List[Event]:
    events: List[Event] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        events.extend(parse_line(line))
    events.sort(key=lambda e: e.start)
    return events

# === 发送按键 ===
class KeySender:
    def __init__(self):
        self.active_count: Dict[str, int] = {}

    def press(self, keys: List[str]):
        for k in keys:
            cnt = self.active_count.get(k, 0) + 1
            self.active_count[k] = cnt
            if cnt == 1:  # 首次按下
                try:
                    if USE_KEYBOARD_LIB:
                        keyboard.press(k)
                    else:
                        pyautogui.keyDown(k)
                except Exception:
                    pass

    def release(self, keys: List[str]):
        for k in keys:
            cnt = self.active_count.get(k, 0)
            if cnt <= 0:
                continue
            cnt -= 1
            self.active_count[k] = cnt
            if cnt == 0:
                try:
                    if USE_KEYBOARD_LIB:
                        keyboard.release(k)
                    else:
                        pyautogui.keyUp(k)
                except Exception:
                    pass

key_sender = KeySender()

# === 播放线程 ===
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
            # 按速度缩放
            scaled: List[Event] = [Event(start=e.start / self.speed_ratio, end=e.end / self.speed_ratio, keys=e.keys) for e in self.events]
            # 构造动作表 (time, type, keys)
            actions: List[Tuple[float,str,List[str]]] = []
            for e in scaled:
                actions.append((e.start, 'press', e.keys))
                actions.append((e.end, 'release', e.keys))
            actions.sort(key=lambda x: x[0])
            t0 = time.perf_counter() + self.start_delay
            idx = 0
            while idx < len(actions) and not self._stop.is_set():
                now = time.perf_counter()
                target = t0 + actions[idx][0] + self.global_latency
                wait = target - now
                if wait > 0:
                    time.sleep(min(wait, 0.01))
                    continue
                _time, typ, keys = actions[idx]
                if typ == 'press':
                    key_sender.press(keys)
                else:
                    key_sender.release(keys)
                idx += 1
        finally:
            # 确保释放所有剩余按键
            key_sender.release(list(key_sender.active_count.keys()))
            if self.on_done:
                self.on_done()

# === UI ===
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
        self.ent_speed = tk.Entry(params, width=8); self.ent_speed.insert(0, "1.0"); self.ent_speed.grid(row=0, column=1, sticky="w", padx=6)
        tk.Label(params, text="起始倒计时(秒)：").grid(row=0, column=2, sticky="e")
        self.ent_countin = tk.Entry(params, width=8); self.ent_countin.insert(0, "2.0"); self.ent_countin.grid(row=0, column=3, sticky="w", padx=6)
        tk.Label(params, text="全局延迟(毫秒)：").grid(row=0, column=4, sticky="e")
        self.ent_latency = tk.Entry(params, width=8); self.ent_latency.insert(0, "0"); self.ent_latency.grid(row=0, column=5, sticky="w", padx=6)

        mapping = tk.LabelFrame(frm, text="键位映射（请确保与游戏一致）")
        mapping.pack(fill="x", pady=8)
        def row(lbl, txt): r = tk.Frame(mapping); r.pack(fill="x", pady=1); tk.Label(r, text=lbl, width=8, anchor="w").pack(side="left"); tk.Label(r, text=txt, anchor="w").pack(side="left")
        row("低音 L:", "L1-L7 -> a s d f g h j")
        row("中音 M:", "M1-M7 -> q w e r t y u")
        row("高音 H:", "H1-H7 -> 1 2 3 4 5 6 7")
        row("和弦 :", "C Dm Em F G Am G7 -> z x c v b n m")

        ctrl = tk.Frame(frm); ctrl.pack(fill="x", pady=6)
        self.btn_start = tk.Button(ctrl, text="开始演奏", command=self.start_play, state="disabled"); self.btn_start.pack(side="left", padx=4)
        self.btn_stop = tk.Button(ctrl, text="停止", command=self.stop_play, state="disabled"); self.btn_stop.pack(side="left", padx=4)
        self.lbl_status = tk.Label(ctrl, text="状态：等待载入乐谱"); self.lbl_status.pack(side="left", padx=10)

        tips = tk.LabelFrame(frm, text="使用提示")
        tips.pack(fill="x", pady=8)
        tk.Label(tips, justify="left", anchor="w", text=(
            "1) 乐谱支持延长音：写法 [起始时间][结束时间] TOKENS\n"
            "2) 单时间戳仍可用作短音：[时间] TOKENS\n"
            "3) 载入后切换到游戏窗口，回到本工具点击开始；\n"
            "4) 如无响应尝试以管理员身份运行 Python。"
        )).pack(fill="x")

    def load_score(self):
        path = filedialog.askopenfilename(title="选择乐谱文件(.lrcp)", filetypes=[("Piano LRC", "*.lrcp"), ("文本", "*.txt"), ("所有文件", "*.*")])
        if not path: return
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
        if not self.events: return
        try: speed = float(self.ent_speed.get())
        except: speed = 1.0
        try: countin = float(self.ent_countin.get())
        except: countin = 2.0
        try: latency = int(float(self.ent_latency.get()))
        except: latency = 0
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

# === 入口 ===
def main():
    root = tk.Tk(); App(root); root.mainloop()

if __name__ == "__main__":
    main()
