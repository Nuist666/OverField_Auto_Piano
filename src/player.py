import time
import threading
from typing import List, Tuple, Union, Optional, Callable

from src.event import Event, SimpleEvent
from src.key_sender import key_sender


class Player(threading.Thread):
    def __init__(self, events: List[Union[Event, SimpleEvent]], start_delay: float, global_latency_ms: int, speed_ratio: float, on_done, progress_callback: Optional[Callable[[int, int], None]] = None, progress_update_freq: int = 1):
        super().__init__(daemon=True)
        self.events = events
        self.start_delay = max(0.0, start_delay)
        self.global_latency = max(0, global_latency_ms) / 1000.0
        self.speed_ratio = max(0.05, speed_ratio)
        self._stop = threading.Event()
        self.on_done = on_done
        self.progress_callback = progress_callback
        self.progress_update_freq = max(1, progress_update_freq)  # 确保至少为1

    def stop(self):
        self._stop.set()

    def run(self):
        total_actions = 0
        try:
            if not self.events:
                return

            temp_e = self.events[0]
            if isinstance(temp_e, Event):
                is_event = True
                actions: List[Tuple[float, str, List[str]]] = []
            else:
                is_event = False
                actions: List[Tuple[float, str, str]] = []

            for e in self.events:
                start = e.start / self.speed_ratio
                end = e.end / self.speed_ratio

                if is_event:
                    keys = e.keys
                else:  # SimpleEvent
                    keys = e.key

                actions.append((start, 'press', keys))
                actions.append((end, 'release', keys))

            # 排序动作表
            actions.sort(key=lambda x: x[0])
            t0 = time.perf_counter() + self.start_delay
            idx = 0
            total_actions = len(actions)

            while idx < total_actions and not self._stop.is_set():
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
                
                # 根据用户配置的频率更新进度
                if self.progress_callback and (idx % self.progress_update_freq == 0 or idx == total_actions):
                    self.progress_callback(idx, total_actions)
                    
        finally:
            # 确保释放所有剩余按键
            key_sender.release_all()
            # 报告完成进度
            if self.progress_callback:
                self.progress_callback(total_actions, total_actions)
            if self.on_done:
                self.on_done()


if __name__ == "__main__":
    pass
