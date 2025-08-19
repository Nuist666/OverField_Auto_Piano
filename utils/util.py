import sys
import ctypes


# ===== 管理员权限检查 =====
def admin_running():
    try:
        flag = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        flag = False
    if not flag:
        print("请求管理员权限...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()


if __name__ == "__main__":
    pass
