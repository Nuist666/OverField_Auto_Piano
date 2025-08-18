import re

# === 键位映射（根据你的描述硬编码） ===
LOW_MAP = {str(i): k for i, k in zip(range(1, 8), list("asdfghj"))}  # 低音1-7 -> a s d f g h j
MID_MAP = {str(i): k for i, k in zip(range(1, 8), list("qwertyu"))}  # 中音1-7 -> q w e r t y u
HIGH_MAP = {str(i): k for i, k in zip(range(1, 8), list("1234567"))}  # 高音1-7 -> 1 2 3 4 5 6 7
CHORD_MAP = {"C": "z", "Dm": "x", "Em": "c", "F": "v", "G": "b", "Am": "n", "G7": "m"}  # 和弦 -> z x c v b n m

# 允许的音符 token：
TOKEN_NOTE_RE = re.compile(r"(?:(?:[LMH][1-7])|(?:C|Dm|Em|F|G|Am|G7))")
# 时间戳形如：[mm:ss.xxx]，毫秒 .xxx 可省略
TS_RE = re.compile(r"\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]")

