import tkinter as tk
from typing import List

from src.app import BaseApp
from src.event import Event
from utils.parse import parse_score


class AppSingle(BaseApp):
    def __init__(self, root: tk.Tk):
        super().__init__(root, "Windows 钢琴自动演奏")

        # 添加单应用特有的UI组件
        self.create_key_mapping()
        self.create_tips()

    def create_key_mapping(self):
        """创建键位映射说明"""
        mapping = tk.LabelFrame(self.frm, text="键位映射（请确保与游戏一致）")
        mapping.pack(fill="x", pady=8)

        def row(lbl, txt):
            r = tk.Frame(mapping)
            r.pack(fill="x", pady=1)
            tk.Label(r, text=lbl, width=8, anchor="w").pack(side="left")
            tk.Label(r, text=txt, anchor="w").pack(side="left")

        row("低音 L:", "L1-L7 -> a s d f g h j")
        row("中音 M:", "M1-M7 -> q w e r t y u")
        row("高音 H:", "H1-H7 -> 1 2 3 4 5 6 7")
        row("和弦 :", "C Dm Em F G Am G7 -> z x c v b n m")

    def create_tips(self):
        """创建使用提示"""
        tips = tk.LabelFrame(self.frm, text="使用提示")
        tips.pack(fill="x", pady=8)
        tk.Label(tips, justify="left", anchor="w", text=(
            "1) 乐谱支持延长音：写法 [起始时间][结束时间] TOKENS\n"
            "2) 单时间戳仍可用作短音：[时间] TOKENS\n"
            "3) 载入后切换到游戏窗口，回到本工具点击开始；\n"
            "4) 如无响应尝试以管理员身份运行 Python。"
        )).pack(fill="x")

    def parse_score(self, score_text: str) -> List[Event]:
        """解析乐谱（单应用版本）"""
        return parse_score(score_text)


if __name__ == "__main__":
    pass
