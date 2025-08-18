import time
import threading
from typing import List, Tuple

from src.event import Event
from src.key_sender import key_sender


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
            actions: List[Tuple[float, str, List[str]]] = []
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


if __name__ == "__main__":
    pass
