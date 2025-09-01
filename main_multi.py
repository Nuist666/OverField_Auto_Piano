#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk

from src.app_multi import MultiApp
from utils.util import admin_running


def main():
    admin_running()
    try:
        import ttkbootstrap as ttkb
        root = ttkb.Window(themename="superhero")
    except Exception:
        root = tk.Tk()
    MultiApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
