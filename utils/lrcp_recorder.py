#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LRCP/LRCD 实时录制器
- 全局监听键盘按下/释放，依据 README 的键位映射生成 .lrcp 或 .lrcd 文本
- 小窗口包含：开始、暂停、停止、导出、计时、事件数、热键设置、乐器选择
- 录制上限 1 小时；忽略按键：tab、capslock、shift、ctrl、win、alt、f1~f12
- 默认热键：开始 F6、暂停 F7、停止 F8，可在窗口中更改（仅支持 F1~F12 单键作为热键）

可在主程序中通过 open_recorder_window(root, instrument) 打开。
也可独立运行：python utils/lrcp_recorder.py
"""
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, List, Optional, Tuple

try:
    from pynput import keyboard
except Exception:  # 运行时尚未安装
    keyboard = None  # type: ignore

from utils.constant import LOW_MAP, MID_MAP, HIGH_MAP, CHORD_MAP, DRUM_MAP

# 反向映射（按乐器区分）
PIANO_KEY_TO_TOKEN: Dict[str, str] = {}
PIANO_KEY_TO_TOKEN.update({v: f"L{k}" for k, v in LOW_MAP.items()})
PIANO_KEY_TO_TOKEN.update({v: f"M{k}" for k, v in MID_MAP.items()})
PIANO_KEY_TO_TOKEN.update({v: f"H{k}" for k, v in HIGH_MAP.items()})
PIANO_KEY_TO_TOKEN.update({v: k for k, v in CHORD_MAP.items()})

DRUM_KEY_TO_TOKEN: Dict[str, str] = {v: k for k, v in DRUM_MAP.items()}

# 忽略按键列表（统一小写/Key.* 名称）
IGNORE_KEY_NAMES = set([
    'tab', 'caps_lock', 'capslock', 'shift', 'shift_l', 'shift_r',
    'ctrl', 'ctrl_l', 'ctrl_r', 'alt', 'alt_l', 'alt_r', 'alt_gr',
    'cmd', 'cmd_l', 'cmd_r', 'win', 'windows', 'super',
])
# f1~f12
IGNORE_KEY_NAMES.update([f"f{i}" for i in range(1, 13)])

MAX_DURATION_SEC = 60 * 60  # 1 hour

# 符号 -> 数字（处理按住 Shift 的场景）
SHIFT_SYMBOL_TO_DIGIT = {
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7',
}


def seconds_to_ts(sec: float) -> str:
    if sec < 0:
        sec = 0
    m = int(sec // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    return f"[{m:02d}:{s:02d}.{ms:03d}]"


class RecorderWindow:
    """录制器窗口 + 全局键盘监听"""

    def __init__(self, root: tk.Tk, instrument: str = 'piano'):
        if keyboard is None:
            messagebox.showerror("缺少依赖", "需要安装 pynput 模块\n请先执行: pip install pynput")
            return
        ins = (instrument or 'piano').lower()
        if ins not in ('piano', 'drum'):
            ins = 'piano'
        self.instrument = ins
        self._last_instrument = ins

        self.root = root
        self.win = tk.Toplevel(root)
        self.win.title(self._title_prefix())
        self.win.resizable(False, False)
        try:
            self.win.attributes("-topmost", True)
        except Exception:
            pass
        self.win.protocol("WM_DELETE_WINDOW", self.on_close)

        # 状态
        self.is_recording = False
        self.is_paused = False
        self.start_time_monotonic: float = 0.0
        self.pause_started_at: Optional[float] = None
        self.total_paused: float = 0.0

        # 打点：按下中 key -> start_time
        self.pressed_at: Dict[str, float] = {}
        # 完成的事件列表 (start, end, token)
        self.events: List[Tuple[float, float, str]] = []

        # 计时/计数
        self.elapsed_var = tk.StringVar(value="00:00.000")
        self.count_var = tk.IntVar(value=0)

        # 热键设置（仅 F1~F12）
        self.hk_start_var = tk.StringVar(value="F6")
        self.hk_pause_var = tk.StringVar(value="F7")
        self.hk_stop_var = tk.StringVar(value="F8")

        # 乐器选择
        self.var_instrument = tk.StringVar(value=self.instrument)

        self._build_ui()

        # 监听器
        self.listener: Optional[keyboard.Listener] = None
        self._start_global_listener()

        # UI 定时器
        self._tick()

    def _title_prefix(self) -> str:
        return "动作录制 (.lrcd)" if self.instrument == 'drum' else "动作录制 (.lrcp)"

    def _get_mapping_text(self) -> str:
        if self.instrument == 'drum':
            return (
                "- 键位映射（架子鼓）：\n"
                "  踩镲闭->1  高音吊镲->2  一嗵鼓->3  二嗵鼓->4  叮叮镲->5\n"
                "  踩镲开->Q  军鼓->W  底鼓->E  落地嗵鼓->R  中音吊镲->T\n"
            )
        else:
            return (
                "- 键位映射（钢琴）：\n"
                "  低音 L1~L7 -> a s d f g h j\n  中音 M1~M7 -> q w e r t y u\n  高音 H1~H7 -> 1 2 3 4 5 6 7\n  和弦 C/Dm/Em/F/G/Am/G7 -> z x c v b n m\n"
            )

    # UI
    def _build_ui(self):
        frm = tk.Frame(self.win, padx=10, pady=10)
        frm.pack(fill="both", expand=True)

        # 顶部：乐器选择
        insf = tk.LabelFrame(frm, text="乐器")
        insf.pack(fill="x")
        tk.Radiobutton(insf, text="钢琴 (.lrcp)", value='piano', variable=self.var_instrument, command=self._on_instrument_change).pack(side="left", padx=4)
        tk.Radiobutton(insf, text="架子鼓 (.lrcd)", value='drum', variable=self.var_instrument, command=self._on_instrument_change).pack(side="left", padx=6)

        # 中部：计时与计数
        row_top = tk.Frame(frm)
        row_top.pack(fill="x")
        tk.Label(row_top, text="已录制时间：").pack(side="left")
        tk.Label(row_top, textvariable=self.elapsed_var, width=12).pack(side="left")
        tk.Label(row_top, text="  事件数：").pack(side="left")
        tk.Label(row_top, textvariable=self.count_var, width=8).pack(side="left")

        # 控制按钮
        row_btn = tk.Frame(frm)
        row_btn.pack(fill="x", pady=6)
        self.btn_start = tk.Button(row_btn, text="开始录制 (F6)", width=16, command=self.start_record)
        self.btn_start.pack(side="left", padx=4)
        self.btn_pause = tk.Button(row_btn, text="暂停录制 (F7)", width=16, state="disabled", command=self.pause_record)
        self.btn_pause.pack(side="left", padx=4)
        self.btn_stop = tk.Button(row_btn, text="停止录制 (F8)", width=16, state="disabled", command=self.stop_record)
        self.btn_stop.pack(side="left", padx=4)

        # 导出
        row_exp = tk.Frame(frm)
        row_exp.pack(fill="x", pady=4)
        self.btn_export = tk.Button(row_exp, text=("导出 .lrcd" if self.instrument == 'drum' else "导出 .lrcp"), state="disabled", command=self.export_score)
        self.btn_export.pack(side="left", padx=4)

        # 热键设置
        hot = tk.LabelFrame(frm, text="热键设置")
        hot.pack(fill="x", pady=8)
        fkeys = [f"F{i}" for i in range(1, 13)]
        tk.Label(hot, text="开始录制：").grid(row=0, column=0, sticky="e", padx=4, pady=2)
        ttk.Combobox(hot, values=fkeys, state="readonly", width=6, textvariable=self.hk_start_var).grid(row=0, column=1, sticky="w", padx=4)
        tk.Label(hot, text="暂停录制：").grid(row=0, column=2, sticky="e", padx=4, pady=2)
        ttk.Combobox(hot, values=fkeys, state="readonly", width=6, textvariable=self.hk_pause_var).grid(row=0, column=3, sticky="w", padx=4)
        tk.Label(hot, text="停止录制：").grid(row=0, column=4, sticky="e", padx=4, pady=2)
        ttk.Combobox(hot, values=fkeys, state="readonly", width=6, textvariable=self.hk_stop_var).grid(row=0, column=5, sticky="w", padx=4)

        # 提示
        tips = tk.LabelFrame(frm, text="使用提示")
        tips.pack(fill="x", pady=6)
        self.lbl_tips = tk.Label(tips, justify="left", anchor="w")
        self.lbl_tips.pack(fill="x")
        self._refresh_tips()

    def _refresh_tips(self):
        text = (
            "- 打开游戏并聚焦游戏窗口后点击开始或按热键开始录制。\n"
            "- 录制上限 1 小时，超时会自动停止。\n"
            "- 忽略按键：Tab, CapsLock, Shift, Ctrl, Win, Alt, F1~F12。\n"
            "- 游戏内F1~F5及F11~F12被占用，请勿设置为热键\n"
        ) + self._get_mapping_text()
        self.lbl_tips.config(text=text)

    def _on_instrument_change(self):
        new_ins = self.var_instrument.get().lower()
        if new_ins not in ('piano', 'drum'):
            self.var_instrument.set(self.instrument)
            return
        # 录制中不允许切换，避免映射混乱
        if self.is_recording or self.is_paused:
            messagebox.showinfo("提示", "请先停止录制后再切换乐器。")
            # 还原选择
            self.var_instrument.set(self.instrument)
            return
        self.instrument = new_ins
        self._last_instrument = new_ins
        # 更新窗口标题、导出按钮与提示
        try:
            self.win.title(self._title_prefix())
            self.btn_export.config(text=("导出 .lrcd" if self.instrument == 'drum' else "导出 .lrcp"))
            self._refresh_tips()
        except Exception:
            pass

    # 监听
    def _start_global_listener(self):
        def on_press(key):
            try:
                name = self._key_to_name(key)
            except Exception:
                return

            # 热键处理（调度到主线程）
            if name == self.hk_start_var.get().lower():
                self.win.after(0, self.start_record)
                return
            if name == self.hk_pause_var.get().lower():
                self.win.after(0, self.pause_record)
                return
            if name == self.hk_stop_var.get().lower():
                self.win.after(0, self.stop_record)
                return

            # 录制逻辑
            if not self.is_recording or self.is_paused:
                return

            if name in IGNORE_KEY_NAMES:
                return

            # 可映射到 token 的键
            token = self._name_to_token(name)
            if not token:
                return

            # 已按下的不重复记录
            if name in self.pressed_at:
                return

            now = self._now_record_time()
            self.pressed_at[name] = now

        def on_release(key):
            try:
                name = self._key_to_name(key)
            except Exception:
                return

            # 非录制状态直接忽略
            if not self.is_recording:
                return

            # 忽略键或不在映射
            if name in IGNORE_KEY_NAMES:
                return
            token = self._name_to_token(name)
            if not token:
                return

            if name not in self.pressed_at:
                return

            start = self.pressed_at.pop(name)
            end = self._now_record_time()
            # 上限限制
            if end - 0.0001 > MAX_DURATION_SEC:
                end = float(MAX_DURATION_SEC)
            if end < start:
                end = start
            self.events.append((start, end, token))
            # 线程安全更新 UI
            self.win.after(0, lambda: self.count_var.set(len(self.events)))

        self.listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.listener.start()

    def _key_to_name(self, key) -> str:
        # 将 pynput 的 key -> 统一小写名称
        if keyboard is None:
            return ""
        if isinstance(key, keyboard.KeyCode):
            ch = key.char
            if ch is None:
                return ""
            # 处理 shift 数字
            ch = SHIFT_SYMBOL_TO_DIGIT.get(ch, ch)
            return ch.lower()
        else:
            name = str(key).replace("Key.", "").lower()
            # 别名修正
            if name == 'caps_lock':
                name = 'capslock'
            if name == 'cmd':
                name = 'win'
            return name

    def _name_to_token(self, name: str) -> Optional[str]:
        # 仅对单字符或已知映射键有效
        if not name:
            return None
        if self.instrument == 'drum':
            return DRUM_KEY_TO_TOKEN.get(name)
        else:
            return PIANO_KEY_TO_TOKEN.get(name)

    def _now_record_time(self) -> float:
        # 录制起点到现在的相对秒，减去暂停时间
        now = time.perf_counter()
        extra_paused = 0.0
        # 若正在暂停中，实时扣减从暂停开始到当前的时间
        if self.is_paused and self.pause_started_at is not None:
            extra_paused = max(0.0, now - self.pause_started_at)
        return max(0.0, now - self.start_time_monotonic - self.total_paused - extra_paused)

    # 控制
    def start_record(self):
        if self.is_recording and not self.is_paused:
            return
        if not self.is_recording:
            self.is_recording = True
            self.is_paused = False
            self.start_time_monotonic = time.perf_counter()
            self.total_paused = 0.0
            self.events.clear()
            self.pressed_at.clear()
            self.count_var.set(0)
            # 清空上一次生成文本
            if hasattr(self, 'generated_text'):
                try:
                    delattr(self, 'generated_text')
                except Exception:
                    self.generated_text = ''
        else:  # 从暂停恢复
            self.is_paused = False
            if self.pause_started_at is not None:
                self.total_paused += (time.perf_counter() - self.pause_started_at)
                self.pause_started_at = None
        # 按钮状态
        self.btn_start.config(state="disabled")
        self.btn_pause.config(state="normal")
        self.btn_stop.config(state="normal")
        self.btn_export.config(state="disabled")
        # 标题更新
        self.win.title(self._title_prefix() + " - 录制中…")

    def pause_record(self):
        if not self.is_recording:
            return
        if not self.is_paused:
            self.is_paused = True
            self.pause_started_at = time.perf_counter()
            self.btn_start.config(state="normal")
            self.btn_pause.config(state="disabled")
            self.win.title(self._title_prefix() + " - 已暂停")

    def stop_record(self):
        if not self.is_recording:
            return
        # 将仍按下的键补齐到停止时刻
        stop_t = self._now_record_time()
        for name, st in list(self.pressed_at.items()):
            token = self._name_to_token(name)
            if token:
                self.events.append((st, stop_t, token))
        self.pressed_at.clear()

        self.is_recording = False
        self.is_paused = False
        self.pause_started_at = None
        self.btn_start.config(state="normal")
        self.btn_pause.config(state="disabled")
        self.btn_stop.config(state="disabled")
        self.btn_export.config(state="normal")
        self.win.title(self._title_prefix() + " - 已停止，可导出")

        # 自动生成文本（保存在内存）
        self.generated_text = self._build_text()
        # 更新事件计数
        self.count_var.set(len(self.events))

    def _build_text(self) -> str:
        # 将 (start, end, token) 排序并合并相同时间段的 token
        evs = list(self.events)
        evs.sort(key=lambda x: (round(x[0], 6), round(x[1], 6), x[2]))

        # 合并 (start,end) 相同的多个 token
        grouped: Dict[Tuple[int, int], List[str]] = {}
        for st, ed, tok in evs:
            # 以毫秒为单位合并，避免浮点误差
            st_ms = int(round(st * 1000))
            ed_ms = int(round(ed * 1000))
            key = (st_ms, ed_ms)
            grouped.setdefault(key, []).append(tok)

        lines: List[str] = []
        for (st_ms, ed_ms), toks in sorted(grouped.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            st = st_ms / 1000.0
            ed = ed_ms / 1000.0
            ts1 = seconds_to_ts(st)
            ts2 = seconds_to_ts(ed)
            # 一律使用双时间戳表示，兼容延长/短音
            tokens = " ".join(toks)
            lines.append(f"{ts1}{ts2} {tokens}")
        return "\n".join(lines) + ("\n" if lines else "")

    def export_score(self):
        if not getattr(self, 'generated_text', None):
            messagebox.showinfo("提示", "当前没有可导出的录制数据，请先停止录制。")
            return
        if self.instrument == 'drum':
            title = "导出为 .lrcd"
            defext = ".lrcd"
            filetypes = [["LRCD 文件", "*.lrcd"], ["文本文件", "*.txt"], ["所有文件", "*.*"]]
            initfile = "recorded.lrcd"
        else:
            title = "导出为 .lrcp"
            defext = ".lrcp"
            filetypes = [["LRCP 文件", "*.lrcp"], ["文本文件", "*.txt"], ["所有文件", "*.*"]]
            initfile = "recorded.lrcp"
        path = filedialog.asksaveasfilename(
            title=title,
            defaultextension=defext,
            filetypes=filetypes,
            initialfile=initfile,
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.generated_text)
            messagebox.showinfo("成功", f"已保存：{path}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def _tick(self):
        # 更新时间显示；到达上限自动停止
        if self.is_recording:
            el = self._now_record_time()
            if el >= MAX_DURATION_SEC:
                # 超时自动停止
                self.stop_record()
                el = MAX_DURATION_SEC
            self.elapsed_var.set(self._fmt_time(el))
        # 更新按钮热键提示
        self.btn_start.config(text=f"开始录制 ({self.hk_start_var.get()})")
        self.btn_pause.config(text=f"暂停录制 ({self.hk_pause_var.get()})")
        self.btn_stop.config(text=f"停止录制 ({self.hk_stop_var.get()})")

        try:
            self.win.after(50, self._tick)
        except Exception:
            pass

    @staticmethod
    def _fmt_time(sec: float) -> str:
        if sec < 0:
            sec = 0
        m = int(sec // 60)
        s = int(sec % 60)
        ms = int(round((sec - int(sec)) * 1000))
        return f"{m:02d}:{s:02d}.{ms:03d}"

    def on_close(self):
        try:
            if self.listener:
                self.listener.stop()
        except Exception:
            pass
        try:
            self.win.destroy()
        except Exception:
            pass


_singleton_ref: Optional[RecorderWindow] = None


def open_recorder_window(root: tk.Tk, instrument: str = 'piano'):
    """对外 API：打开录制器窗口（单例），instrument in {'piano','drum'}"""
    global _singleton_ref
    try:
        if _singleton_ref is not None:
            # 若窗口仍存在，使其前置
            try:
                _singleton_ref.win.deiconify()
                _singleton_ref.win.lift()
                _singleton_ref.win.focus_set()
                return
            except Exception:
                _singleton_ref = None
        _singleton_ref = RecorderWindow(root, instrument)
    except Exception as e:
        messagebox.showerror("录制器异常", str(e))


if __name__ == "__main__":
    r = tk.Tk()
    r.title("LRCP/LRCD 录制器 - 独立运行")
    ttk.Label(r, text="此窗口仅用于托管录制器，请在弹出的录制器小窗中操作。", padding=10).pack()
    open_recorder_window(r, 'piano')
    r.mainloop()
