from typing import List
from dataclasses import dataclass


@dataclass
class Event:
    start: float  # 按下时间（秒）
    end: float  # 释放时间（秒），若与 start 相同表示立刻松开（tap）
    keys: List[str]  # 同步触发的一组按键（和弦/多音）


if __name__ == "__main__":
    pass
