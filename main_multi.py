#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 钢琴自动演奏 - 多人模式 (去和弦 + 多音时间分散)
说明：
- 针对多人模式中存在的漏音/丢音问题，提供一种退化策略：
  1. 去掉所有和弦（C, Dm, Em, F, G, Am, G7），仅保留单音旋律，减少同时按键数量；
  2. 对同一时间戳内的多音进行“时间分散”，为每个音施加一个相对偏移（毫秒级，可正可负），
     以降低游戏短时间内的输入堆叠，从而减少被丢弃概率；
  3. 偏移在内存中处理，不修改原始 .lrcp 文件。
- 其他参数（速度比例、起始倒计时、全局延迟）与单人模式相同。
偏移输入：
  例如：-15,0,15  表示第一音提前15ms，第二音不变，第三音延后15ms，第4音再循环使用第一偏移(-15ms)依此类推。
  允许范围：-50 ~ 50 (ms)。超过范围自动裁剪。

"""
import tkinter as tk

from src.app_multi import AppMulti


def main():
    root = tk.Tk()
    AppMulti(root)
    root.mainloop()


if __name__ == "__main__":
    main()
