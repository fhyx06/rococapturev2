"""应用入口 —— DPI适配、主题设置、窗口启动"""
import sys
import os
import ctypes
from pathlib import Path

import customtkinter as ctk

# 将项目根目录加入 sys.path，确保 src 包可被找到
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.save_service import SaveService
from src.ui.main_window import MainWindow
from src.models.constants import SAVES_DIR


def enable_dpi_awareness():
    """启用 Windows DPI 感知，适配 4K / 高缩放场景"""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except (AttributeError, OSError):
        pass


def setup_theme():
    """设置 CustomTkinter 全局主题"""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    # 高DPI下的全局缩放（150%缩放用1.5因子）
    ctk.set_widget_scaling(1.0)


def main():
    enable_dpi_awareness()
    setup_theme()

    # saves 目录放在 exe 同级（或项目根目录）
    saves_dir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), SAVES_DIR)
    save_service = SaveService(saves_dir)

    # 若没有任何存档，自动创建默认存档「主账号」
    if not save_service.list_saves():
        save_service.create_save("主账号")

    app = MainWindow(save_service)
    app.mainloop()


if __name__ == "__main__":
    main()
