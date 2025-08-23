#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 钢琴自动演奏 - 可视化脚本 (PyQt5)
功能：
- 载入乐谱（LRC 风格时间戳），解析为事件队列
- 支持延长音：一行两个时间戳 [start][end] TOKENS -> 按下后保持到 end 再释放
- 单时间戳仍兼容，视为即刻点按（tap）
- 一键开始/停止自动按键（模拟键盘）
- 支持节奏倍速、起始延迟（倒计时）、全局延迟（打穿游戏输入延迟）
- 面板展示按键映射关系，便于校对
注意：
- 需在 Windows 上运行，并确保游戏窗口在“开始演奏”后处于焦点
- 发送键盘事件默认使用 pynput
"""

from PyQt5 import QtWidgets

from src.app_single import SingleApp
from utils.util import admin_running


def main():
    admin_running()
    app = QtWidgets.QApplication([])
    win = SingleApp()
    win.show()
    app.exec_()


if __name__ == "__main__":
    main()
