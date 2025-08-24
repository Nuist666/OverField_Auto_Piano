import re

# === 键位映射（钢琴） ===
LOW_MAP = {str(i): k for i, k in zip(range(1, 8), list("asdfghj"))}  # 低音1-7 -> a s d f g h j
MID_MAP = {str(i): k for i, k in zip(range(1, 8), list("qwertyu"))}  # 中音1-7 -> q w e r t y u
HIGH_MAP = {str(i): k for i, k in zip(range(1, 8), list("1234567"))}  # 高音1-7 -> 1 2 3 4 5 6 7
CHORD_MAP = {"C": "z", "Dm": "x", "Em": "c", "F": "v", "G": "b", "Am": "n", "G7": "m"}  # 和弦 -> z x c v b n m
CHORD_TOKENS = set(CHORD_MAP.keys())

# 钢琴 token： 低中高音 + 和弦
TOKEN_NOTE_RE = re.compile(r"(?:(?:[LMH][1-7])|(?:C|Dm|Em|F|G|Am|G7))")

# === 键位映射（架子鼓） ===
# token -> 键位
DRUM_MAP = {
    "踩镲闭": "1",     # Closed Hi-Hat
    "高音吊镲": "2",   # Crash Cymbal 1
    "一嗵鼓": "3",     # High Tom
    "二嗵鼓": "4",     # Mid Tom / Hi-Mid Tom
    "叮叮镲": "5",     # Ride Bell
    "踩镲开": "q",     # Open Hi-Hat
    "军鼓": "w",       # Snare
    "底鼓": "e",       # Bass Drum
    "落地嗵鼓": "r",   # Floor Tom
    "中音吊镲": "t",   # Ride Cymbal 1 / Crash 2
}
DRUM_TOKENS = set(DRUM_MAP.keys())
DRUM_TOKEN_RE = re.compile(r"(?:" + "|".join(map(re.escape, DRUM_TOKENS)) + r")")

# 时间戳形如：[mm:ss.xxx]，毫秒 .xxx 可省略
TS_RE = re.compile(r"\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]")

