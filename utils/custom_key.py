import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from typing import Dict, List

from utils.constant import update_key_maps

# 默认键位配置
DEFAULT_KEY_MAPS = {
    "开放空间": {
        "low_map": {str(i): k for i, k in zip(range(1, 8), list("asdfghj"))},
        "mid_map": {str(i): k for i, k in zip(range(1, 8), list("qwertyu"))},
        "high_map": {str(i): k for i, k in zip(range(1, 8), list("1234567"))}
    },
    "原神": {
        "low_map": {str(i): k for i, k in zip(range(1, 8), list("zxcvbnm"))},
        "mid_map": {str(i): k for i, k in zip(range(1, 8), list("asdfghj"))},
        "high_map": {str(i): k for i, k in zip(range(1, 8), list("qwertyu"))}
    }
}

CONFIG_FILE = "key_map_config.json"


class CustomKeyMap:
    """自定义键位映射管理类"""

    def __init__(self):
        self.current_profile = "开放空间"
        self.key_maps = DEFAULT_KEY_MAPS.copy()
        self.load_config()

    def load_config(self):
        """从配置文件加载键位配置"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 兼容旧版本配置（移除和弦映射）
                    for profile_name, profile_data in config.get("profiles", {}).items():
                        if "chord_map" in profile_data:
                            del profile_data["chord_map"]
                    self.key_maps.update(config.get("profiles", {}))
                    self.current_profile = config.get("current_profile", "开放空间")
        except Exception as e:
            print(f"加载配置文件失败: {e}")

    def save_config(self):
        """保存键位配置到文件"""
        try:
            config = {
                "current_profile": self.current_profile,
                "profiles": self.key_maps
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置文件失败: {e}")

    def get_current_map(self) -> Dict:
        """获取当前配置的键位映射"""
        return self.key_maps.get(self.current_profile, DEFAULT_KEY_MAPS["开放空间"])

    def get_profile_names(self) -> List[str]:
        """获取所有配置文件的名称"""
        return list(self.key_maps.keys())

    def create_profile(self, name: str, profile_data: Dict):
        """创建新的键位配置"""
        if name in self.key_maps:
            return False
        self.key_maps[name] = profile_data
        self.save_config()
        return True

    def update_profile(self, name: str, profile_data: Dict):
        """更新键位配置"""
        if name not in self.key_maps:
            return False
        self.key_maps[name] = profile_data
        self.save_config()
        return True

    def delete_profile(self, name: str):
        """删除键位配置"""
        if name in ["开放空间", "原神"]:
            return False  # 不允许删除默认配置
        if name in self.key_maps:
            del self.key_maps[name]
            if self.current_profile == name:
                self.current_profile = "开放空间"
            self.save_config()
            return True
        return False

    def set_current_profile(self, profile_name: str):
        """设置当前使用的配置"""
        if profile_name in self.key_maps:
            self.current_profile = profile_name
            self.save_config()
            return True
        return False


class KeyMapEditor:
    """键位自定义映射界面"""

    def __init__(self, master, key_map_manager: CustomKeyMap):
        self.master = master
        self.manager = key_map_manager
        self.current_profile = self.manager.current_profile
        self.setup_ui()
        self.load_current_profile()

    def setup_ui(self):
        """设置UI界面"""
        self.master.title("钢琴键位自定义映射")
        self.master.geometry("350x470")

        # 主框架
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置文件选择
        ttk.Label(main_frame, text="选择配置:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(main_frame, textvariable=self.profile_var, state="readonly")
        self.profile_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        self.profile_combo.bind('<<ComboboxSelected>>', self.on_profile_change)

        # 新建配置按钮
        ttk.Button(main_frame, text="新建配置", command=self.create_new_profile).grid(row=0, column=2, padx=5)

        # 配置名称编辑
        ttk.Label(main_frame, text="配置名称:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.name_var).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)

        # 笔记本控件
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)

        # 低音区标签页
        low_frame = ttk.Frame(notebook, padding="10")
        notebook.add(low_frame, text="低音区 (L1-L7)")
        self.setup_key_frame(low_frame, "low")

        # 中音区标签页
        mid_frame = ttk.Frame(notebook, padding="10")
        notebook.add(mid_frame, text="中音区 (M1-M7)")
        self.setup_key_frame(mid_frame, "mid")

        # 高音区标签页
        high_frame = ttk.Frame(notebook, padding="10")
        notebook.add(high_frame, text="高音区 (H1-H7)")
        self.setup_key_frame(high_frame, "high")

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=10)

        ttk.Button(button_frame, text="保存当前配置", command=self.save_profile).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="删除当前配置", command=self.delete_profile).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="应用当前配置", command=self.apply_changes).pack(side=tk.LEFT, padx=5)

        # 配置网格权重
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        self.update_profile_list()

    def setup_key_frame(self, parent, key_type):
        """设置音区键位框架"""
        for i in range(7):
            note_num = i + 1
            ttk.Label(parent, text=f"{key_type.upper()} {note_num}:").grid(row=i, column=0, sticky=tk.W, pady=2)
            var = tk.StringVar()
            entry = ttk.Entry(parent, textvariable=var, width=5)
            entry.grid(row=i, column=1, sticky=tk.W, pady=2, padx=5)
            setattr(self, f"{key_type}_{note_num}_var", var)

    def update_profile_list(self):
        """更新配置文件列表"""
        profiles = self.manager.get_profile_names()
        self.profile_combo['values'] = profiles
        if self.current_profile in profiles:
            self.profile_var.set(self.current_profile)

    def load_current_profile(self):
        """加载当前配置"""
        profile = self.manager.get_current_map()
        self.name_var.set(self.current_profile)

        # 加载低音区
        for i in range(1, 8):
            var = getattr(self, f"low_{i}_var")
            var.set(profile["low_map"].get(str(i), ""))

        # 加载中音区
        for i in range(1, 8):
            var = getattr(self, f"mid_{i}_var")
            var.set(profile["mid_map"].get(str(i), ""))

        # 加载高音区
        for i in range(1, 8):
            var = getattr(self, f"high_{i}_var")
            var.set(profile["high_map"].get(str(i), ""))

    def on_profile_change(self, event):
        """配置文件变更事件"""
        self.current_profile = self.profile_var.get()
        self.manager.set_current_profile(self.current_profile)
        self.load_current_profile()

    def create_new_profile(self):
        """创建新配置"""
        name = f"custom_{len(self.manager.key_maps) + 1}"
        new_profile = DEFAULT_KEY_MAPS["开放空间"].copy()

        if self.manager.create_profile(name, new_profile):
            self.update_profile_list()
            self.profile_var.set(name)
            self.on_profile_change(None)

    def save_profile(self):
        """保存当前配置"""
        profile_data = {
            "low_map": {},
            "mid_map": {},
            "high_map": {}
        }

        # 收集低音区
        for i in range(1, 8):
            var = getattr(self, f"low_{i}_var")
            key_val = var.get().strip()
            if key_val:  # 只保存非空的键位
                profile_data["low_map"][str(i)] = key_val

        # 收集中音区
        for i in range(1, 8):
            var = getattr(self, f"mid_{i}_var")
            key_val = var.get().strip()
            if key_val:
                profile_data["mid_map"][str(i)] = key_val

        # 收集高音区
        for i in range(1, 8):
            var = getattr(self, f"high_{i}_var")
            key_val = var.get().strip()
            if key_val:
                profile_data["high_map"][str(i)] = key_val

        if self.manager.update_profile(self.current_profile, profile_data):
            messagebox.showinfo("成功", "配置保存成功！")

    def delete_profile(self):
        """删除当前配置"""
        if self.current_profile in ["开放空间", "原神"]:
            messagebox.showwarning("警告", "不能删除默认配置！")
            return

        if messagebox.askyesno("确认", f"确定要删除配置 '{self.current_profile}' 吗？"):
            if self.manager.delete_profile(self.current_profile):
                self.update_profile_list()
                self.load_current_profile()
                messagebox.showinfo("成功", "配置已删除！")

    def apply_changes(self):
        """应用更改"""
        # 保存当前配置
        self.save_profile()

        # 获取当前键位映射
        current_map = self.manager.get_current_map()
        
        # 更新键位映射
        update_key_maps(
            low_map=current_map["low_map"],
            mid_map=current_map["mid_map"],
            high_map=current_map["high_map"]
        )

        # 显示成功消息
        messagebox.showinfo("成功", "配置已应用！")


def show_key_map_editor():
    root = tk.Tk()
    manager = CustomKeyMap()
    editor = KeyMapEditor(root, manager)
    root.mainloop()


if __name__ == "__main__":
    show_key_map_editor()
