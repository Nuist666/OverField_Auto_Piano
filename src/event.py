from typing import List
from dataclasses import dataclass


@dataclass
class Event:
    start: float  # 按下时间（秒）
    end: float  # 释放时间（秒），若与 start 相同表示立刻松开（tap）
    keys: List[str]  # 同步触发的一组按键（和弦/多音）
    raw_tokens: List[str] = None  # 保留原始 token 便于和弦过滤


@dataclass
class SimpleEvent:  # 预处理后用于播放的单音事件
    start: float
    end: float
    key: str


if __name__ == "__main__":
    pass
