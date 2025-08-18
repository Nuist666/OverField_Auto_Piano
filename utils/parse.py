from typing import List

from src.event import Event
from utils.constant import *


def _ts_match_to_seconds(m: re.Match) -> float:
    mm = int(m.group(1))
    ss = int(m.group(2))
    ms = int((m.group(3) or "0").ljust(3, "0"))
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
        if tok[0] in ("L", "M", "H"):
            octave = tok[0]
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
    # 延长音情形：恰好两个时间戳且第二个时间 > 第一个
    if len(ts) == 2:
        t1 = _ts_match_to_seconds(ts[0])
        t2 = _ts_match_to_seconds(ts[1])
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


if __name__ == "__main__":
    pass
