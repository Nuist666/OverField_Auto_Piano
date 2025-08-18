#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 钢琴自动演奏 - 多人模式 (去和弦 + 多音时间分散)
说明：
- 针对多人模式中存在的漏音/丢音问题，提供一种退化策略：
  1. 去掉所有和弦（C, Dm, Em, F, G, Am, G7），仅保留单音旋律，减少同时按键数量；
  2. 对同一时间戳内的多音进行“时间分散”，为每个音施加一个相对偏移（毫秒级，可正可负），
     以降低游戏短时间内的输入堆叠，从而减少被丢弃概率；
  3. 偏移在内存中处理，不修改原始 .lrcp 文件。
- 其他参数（速度比例、起始倒计时、全局延迟）与单人模式相同。

用法：
  python play_piano_multi.py

偏移输入：
  例如：-15,0,15  表示第一音提前15ms，第二音不变，第三音延后15ms，第4音再循环使用第一偏移(-15ms)依此类推。
  允许范围：-50 ~ 50 (ms)。超过范围自动裁剪。

"""
import os
import re
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

USE_KEYBOARD_LIB = True
try:
    if USE_KEYBOARD_LIB:
        import keyboard
    else:
        import pyautogui

        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0
except Exception as e:
    print("依赖导入失败：", e)

LOW_MAP = {str(i): k for i, k in zip(range(1, 8), list("asdfghj"))}
MID_MAP = {str(i): k for i, k in zip(range(1, 8), list("qwertyu"))}
HIGH_MAP = {str(i): k for i, k in zip(range(1, 8), list("1234567"))}
CHORD_MAP = {"C": "z", "Dm": "x", "Em": "c", "F": "v", "G": "b", "Am": "n", "G7": "m"}
CHORD_TOKENS = set(CHORD_MAP.keys())
TOKEN_NOTE_RE = re.compile(r"(?:(?:[LMH][1-7])|(?:C|Dm|Em|F|G|Am|G7))")
TS_RE = re.compile(r"\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]")


@dataclass
class Event:
    start: float
    end: float
    keys: List[str]  # 原始按键(已映射为键盘键)
    raw_tokens: List[str]  # 保留原始 token 便于和弦过滤


# 解析函数与单人版类似，但保留原始 token

def _ts_match_to_seconds(m: re.Match) -> float:
    mm = int(m.group(1));
    ss = int(m.group(2));
    ms = int((m.group(3) or "0").ljust(3, "0"))
    return mm * 60 + ss + ms / 1000.0


def parse_line(line: str) -> List[Event]:
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
    # map tokens -> keys
    keys: List[str] = []
    for tok in valid_tokens:
        if tok[0] in ("L", "M", "H"):
            octave = tok[0];
            num = tok[1]
            if octave == "L":
                keys.append(LOW_MAP[num])
            elif octave == "M":
                keys.append(MID_MAP[num])
            else:
                keys.append(HIGH_MAP[num])
        else:
            keys.append(CHORD_MAP[tok])
    events: List[Event] = []
    if len(ts) == 2:
        t1 = _ts_match_to_seconds(ts[0]);
        t2 = _ts_match_to_seconds(ts[1])
        if t2 > t1:
            events.append(Event(start=t1, end=t2, keys=keys.copy(), raw_tokens=valid_tokens.copy()))
            return events
    for m in ts:
        t = _ts_match_to_seconds(m)
        events.append(Event(start=t, end=t, keys=keys.copy(), raw_tokens=valid_tokens.copy()))
    return events


def parse_score(text: str) -> List[Event]:
    ev: List[Event] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        ev.extend(parse_line(line))
    ev.sort(key=lambda e: e.start)
    return ev


# 发送按键
class KeySender:
    def __init__(self):
        self.active_count: Dict[str, int] = {}

    def press(self, k: str):
        cnt = self.active_count.get(k, 0) + 1
        self.active_count[k] = cnt
        if cnt == 1:
            try:
                if USE_KEYBOARD_LIB:
                    keyboard.press(k)
                else:
                    pyautogui.keyDown(k)
            except Exception:
                pass

    def release(self, k: str):
        cnt = self.active_count.get(k, 0)
        if cnt <= 0: return
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

    def release_all(self):
        for k in list(self.active_count.keys()):
            while self.active_count.get(k, 0) > 0:
                self.release(k)


key_sender = KeySender()


@dataclass
class SimpleEvent:  # 预处理后用于播放的单音事件
    start: float
    end: float
    key: str


class Player(threading.Thread):
    def __init__(self, events: List[SimpleEvent], start_delay: float, global_latency_ms: int, speed_ratio: float,
                 on_done):
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
            if not self.events: return
            scaled: List[SimpleEvent] = [SimpleEvent(e.start / self.speed_ratio, e.end / self.speed_ratio, e.key) for e
                                         in self.events]
            actions: List[Tuple[float, str, str]] = []
            for e in scaled:
                actions.append((e.start, 'press', e.key))
                actions.append((e.end, 'release', e.key))
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
                _, typ, k = actions[idx]
                if typ == 'press':
                    key_sender.press(k)
                else:
                    key_sender.release(k)
                idx += 1
        finally:
            key_sender.release_all()
            if self.on_done: self.on_done()


# 预处理：去和弦 + 多音展开并应用偏移

def preprocess(events: List[Event], offsets_ms: List[int]) -> List[SimpleEvent]:
    result: List[SimpleEvent] = []
    if not offsets_ms: offsets_ms = [0]
    # clamp offsets
    offsets_ms = [max(-50, min(50, o)) for o in offsets_ms]
    for ev in events:
        # 过滤掉和弦 token
        filtered_pairs = [(tok, key) for tok, key in zip(ev.raw_tokens, ev.keys) if tok not in CHORD_TOKENS]
        if not filtered_pairs:
            continue  # 全是和弦被去掉
        # 现在我们有若干单音（可能>1），给每个分配偏移
        for idx, (tok, key) in enumerate(filtered_pairs):
            off_ms = offsets_ms[idx % len(offsets_ms)]
            off = off_ms / 1000.0
            s = ev.start + off
            e = ev.end + off
            # 不改变原本延长时长；若是 tap (start==end) 仍保持同时释放
            result.append(SimpleEvent(start=s, end=e, key=key))
    # 冲突情况下仍然按时间排序
    result.sort(key=lambda x: x.start)
    return result


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("多人模式 - 自动弹琴 (去和弦+分散)")
        self.score_text: Optional[str] = None
        self.raw_events: List[Event] = []
        self.play_events: List[SimpleEvent] = []
        self.player: Optional[Player] = None

        frm = tk.Frame(root, padx=10, pady=10);
        frm.pack(fill='both', expand=True)
        file_bar = tk.Frame(frm);
        file_bar.pack(fill='x')
        tk.Button(file_bar, text='载入乐谱', command=self.load_score).pack(side='left')
        self.lbl_file = tk.Label(file_bar, text='未载入');
        self.lbl_file.pack(side='left', padx=8)

        params = tk.LabelFrame(frm, text='参数');
        params.pack(fill='x', pady=8)
        tk.Label(params, text='速度比例:').grid(row=0, column=0, sticky='e')
        self.ent_speed = tk.Entry(params, width=8);
        self.ent_speed.insert(0, '1.0');
        self.ent_speed.grid(row=0, column=1, sticky='w', padx=4)
        tk.Label(params, text='起始倒计时(s):').grid(row=0, column=2, sticky='e')
        self.ent_countin = tk.Entry(params, width=8);
        self.ent_countin.insert(0, '2.0');
        self.ent_countin.grid(row=0, column=3, sticky='w', padx=4)
        tk.Label(params, text='全局延迟(ms):').grid(row=0, column=4, sticky='e')
        self.ent_latency = tk.Entry(params, width=8);
        self.ent_latency.insert(0, '0');
        self.ent_latency.grid(row=0, column=5, sticky='w', padx=4)
        tk.Label(params, text='多音偏移(ms):').grid(row=1, column=0, sticky='e')
        self.ent_offsets = tk.Entry(params, width=20);
        self.ent_offsets.insert(0, '-15,0,15');
        self.ent_offsets.grid(row=1, column=1, columnspan=3, sticky='w', padx=4)
        tk.Label(params, text='范围-50~50，按顺序循环应用到同一时间的多个音').grid(row=1, column=4, columnspan=2,
                                                                                  sticky='w')

        ctrl = tk.Frame(frm);
        ctrl.pack(fill='x', pady=6)
        self.btn_start = tk.Button(ctrl, text='开始演奏', command=self.start_play, state='disabled');
        self.btn_start.pack(side='left', padx=4)
        self.btn_stop = tk.Button(ctrl, text='停止', command=self.stop_play, state='disabled');
        self.btn_stop.pack(side='left', padx=4)
        self.lbl_status = tk.Label(ctrl, text='状态：等待载入乐谱');
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

    def parse_offsets(self) -> List[int]:
        text = self.ent_offsets.get().strip()
        if not text: return [0]
        parts = [p for p in re.split(r'[;,\s]+', text) if p]
        offs: List[int] = []
        for p in parts:
            try:
                v = int(float(p))
                if v < -50: v = -50
                if v > 50: v = 50
                offs.append(v)
            except:
                continue
        return offs or [0]

    def load_score(self):
        path = filedialog.askopenfilename(title='选择乐谱文件(.lrcp)', filetypes=[('Piano LRC', '*.lrcp'), ('文本', '*.txt'), ('所有文件', '*.*')])
        if not path: return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.score_text = f.read()
            self.raw_events = parse_score(self.score_text)
            if not self.raw_events:
                raise ValueError('未解析出任何事件。')
            self.update_play_events()
            self.lbl_file.config(text=os.path.basename(path))
            self.lbl_status.config(
                text=f'已载入（原始事件 {len(self.raw_events)} -> 预处理后 {len(self.play_events)} 单音事件）')
            self.btn_start.config(state='normal')
        except Exception as e:
            messagebox.showerror('载入失败', str(e))

    def update_play_events(self):
        offsets = self.parse_offsets()
        self.play_events = preprocess(self.raw_events, offsets)

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


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
