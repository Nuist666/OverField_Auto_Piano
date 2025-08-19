import pyautogui
from typing import List, Dict

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0  # 发送更密集的键


class KeySender:
    def __init__(self):
        self.active_count: Dict[str, int] = {}

    def press(self, keys: List[str]):
        for k in keys:
            cnt = self.active_count.get(k, 0) + 1
            self.active_count[k] = cnt
            if cnt == 1:  # 首次按下
                pyautogui.keyDown(k)

    def release(self, keys: List[str]):
        for k in keys:
            cnt = self.active_count.get(k, 0)
            if cnt <= 0:
                continue
            cnt -= 1
            self.active_count[k] = cnt
            if cnt == 0:
                pyautogui.keyUp(k)

    def release_all(self):
        for k in list(self.active_count.keys()):
            while self.active_count.get(k, 0) > 0:
                self.release(k)


key_sender = KeySender()


if __name__ == "__main__":
    pass
