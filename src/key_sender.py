import pyautogui
from typing import List, Dict


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


key_sender = KeySender()


if __name__ == "__main__":
    pass
