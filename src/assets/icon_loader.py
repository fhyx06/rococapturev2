"""图标资源加载工具"""
from __future__ import annotations

import re
from pathlib import Path
from functools import lru_cache

import customtkinter as ctk
from PIL import Image

# 图标目录：src/assets/icons/
_ICONS_DIR = Path(__file__).resolve().parent / "icons"

# 精灵异色图片目录：src/assets/spirits/
_SPIRITS_DIR = Path(__file__).resolve().parent / "spirits"


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


@lru_cache(maxsize=None)
def load_spirit_icon(spirit_name: str, size: int = 32) -> ctk.CTkImage | None:
    """
    加载精灵异色图标并缓存。文件名格式为 NO.xxx精灵名.png。
    spirit_name 可以是纯精灵名（如 "奇丽草"）或带编号格式（如 "No.041 奇丽草"），
    函数会自动提取末尾的精灵名进行匹配。
    :param spirit_name: 精灵名（支持带/不带编号前缀）
    :param size:        渲染尺寸（正方形），默认 32px
    :return:            CTkImage 或 None（文件不存在时）
    """
    if not _SPIRITS_DIR.exists():
        return None
    # 若带编号前缀（如 "No.041 奇丽草"），提取空格后的纯名
    lookup = spirit_name.strip()
    if re.match(r"^No\.\d+\s+", lookup):
        lookup = re.sub(r"^No\.\d+\s+", "", lookup)
    for p in _SPIRITS_DIR.iterdir():
        if p.suffix.lower() == ".png" and p.stem.endswith(lookup):
            img = Image.open(p).convert("RGBA")
            return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    return None


def list_s1_spirits() -> list[tuple[int, str]]:
    """
    扫描 spirits 目录，返回按编号排序的 (编号, 精灵名) 列表。
    文件名格式：NO.041奇丽草.png
    """
    if not _SPIRITS_DIR.exists():
        return []
    result: list[tuple[int, str]] = []
    pattern = re.compile(r"^NO\.(\d+)(.+)$")
    for p in _SPIRITS_DIR.iterdir():
        if p.suffix.lower() != ".png":
            continue
        m = pattern.match(p.stem)
        if m:
            result.append((int(m.group(1)), m.group(2)))
    result.sort(key=lambda x: x[0])
    return result
