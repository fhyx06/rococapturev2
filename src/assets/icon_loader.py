"""图标资源加载工具"""
from __future__ import annotations

from pathlib import Path
from functools import lru_cache

import customtkinter as ctk
from PIL import Image

# 图标目录：src/assets/icons/
_ICONS_DIR = Path(__file__).resolve().parent / "icons"


@lru_cache(maxsize=None)
def load_element_icon(element: str, size: int = 20) -> ctk.CTkImage | None:
    """
    加载属性图标并缓存。
    :param element: 属性名，如 "火"、"水"
    :param size:    渲染尺寸（正方形），默认 20px
    :return:        CTkImage 或 None（文件不存在时）
    """
    icon_path = _ICONS_DIR / f"{element}.png"
    if not icon_path.exists():
        return None
    img = Image.open(icon_path).convert("RGBA")
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
