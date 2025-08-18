from typing import List

from src.event import Event, SimpleEvent
from utils.constant import *


def _ts_match_to_seconds(m: re.Match) -> float:
    mm = int(m.group(1))
    ss = int(m.group(2))
    ms = int((m.group(3) or "0").ljust(3, "0"))
    return mm * 60 + ss + ms / 1000.0


def parse_line(line: str, multi: bool = False) -> List[Event]:
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
            if multi:
                events.append(Event(start=t1, end=t2, keys=keys.copy(), raw_tokens=valid_tokens.copy()))
            else:
                events.append(Event(start=t1, end=t2, keys=keys.copy()))
            return events
    # 其它：全部视为独立 tap
    for m in ts:
        t = _ts_match_to_seconds(m)
        if multi:
            events.append(Event(start=t, end=t, keys=keys.copy(), raw_tokens=valid_tokens.copy()))
        else:
            events.append(Event(start=t, end=t, keys=keys.copy()))
    return events


def parse_score(text: str, multi: bool = True) -> List[Event]:
    events: List[Event] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        events.extend(parse_line(line, multi))
    events.sort(key=lambda e: e.start)
    return events


# 预处理：去和弦 + 多音展开并应用偏移
def preprocess(events: List[Event], offsets_ms: List[int]) -> List[SimpleEvent]:
    result: List[SimpleEvent] = []
    if not offsets_ms:
        offsets_ms = [0]
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


if __name__ == "__main__":
    pass
