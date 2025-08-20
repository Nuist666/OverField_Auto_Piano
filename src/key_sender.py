from pynput.keyboard import Controller, Key
from typing import List, Dict


class KeySender:
    def __init__(self):
        self.active_count: Dict[str, int] = {}
        self.keyboard = Controller()

        # 特殊键映射表
        self.special_keys = {
            'ctrl': Key.ctrl, 'control': Key.ctrl,
            'alt': Key.alt, 'menu': Key.alt,  # Windows中alt对应menu
            'shift': Key.shift,
            'enter': Key.enter, 'return': Key.enter,
            'space': Key.space,
            'tab': Key.tab,
            'esc': Key.esc, 'escape': Key.esc,
            'backspace': Key.backspace,
            'delete': Key.delete, 'del': Key.delete,
            'insert': Key.insert, 'ins': Key.insert,
            'home': Key.home,
            'end': Key.end,
            'pageup': Key.page_up, 'pgup': Key.page_up,
            'pagedown': Key.page_down, 'pgdn': Key.page_down,
            'up': Key.up,
            'down': Key.down,
            'left': Key.left,
            'right': Key.right,
            'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4,
            'f5': Key.f5, 'f6': Key.f6, 'f7': Key.f7, 'f8': Key.f8,
            'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12,
            'caps_lock': Key.caps_lock,
            'num_lock': Key.num_lock,
            'scroll_lock': Key.scroll_lock,
            'print_screen': Key.print_screen,
            'pause': Key.pause,
        }

    def _get_key(self, key_str: str):
        """将字符串转换为pynput的Key对象或字符"""
        key_str_lower = key_str.lower()
        if key_str_lower in self.special_keys:
            return self.special_keys[key_str_lower]
        return key_str

    def press(self, keys: List[str]):
        for k in keys:
            cnt = self.active_count.get(k, 0) + 1
            self.active_count[k] = cnt
            if cnt == 1:  # 首次按下
                try:
                    key_obj = self._get_key(k)
                    self.keyboard.press(key_obj)
                except Exception as e:
                    print(f"按下键 {k} 时出错: {e}")

    def release(self, keys: List[str]):
        for k in keys:
            cnt = self.active_count.get(k, 0)
            if cnt <= 0:
                continue
            cnt -= 1
            self.active_count[k] = cnt
            if cnt == 0:
                try:
                    key_obj = self._get_key(k)
                    self.keyboard.release(key_obj)
                except Exception as e:
                    print(f"释放键 {k} 时出错: {e}")

    def release_all(self):
        for k in list(self.active_count.keys()):
            while self.active_count.get(k, 0) > 0:
                self.release([k])

    def tap(self, keys: List[str]):
        """模拟按下并立即释放（用于单次触发）"""
        self.press(keys)
        self.release(keys)


key_sender = KeySender()

if __name__ == "__main__":
    # 测试代码
    import time

    # 测试普通按键
    print("测试普通按键...")
    key_sender.press(['a', 'b'])
    time.sleep(1)
    key_sender.release(['a', 'b'])

    # 测试特殊按键
    print("测试特殊按键...")
    key_sender.press(['ctrl', 'c'])
    time.sleep(0.5)
    key_sender.release(['ctrl', 'c'])

    # 测试多次按下同一键
    print("测试多次按下...")
    key_sender.press(['shift'])
    key_sender.press(['shift'])  # 第二次按下
    time.sleep(1)
    key_sender.release(['shift'])  # 第一次释放
    key_sender.release(['shift'])  # 第二次释放

    print("测试完成")