"""图标资源加载工具"""
from __future__ import annotations

import json
import re
from pathlib import Path
from functools import lru_cache

import customtkinter as ctk
from PIL import Image

# 图标目录：src/assets/icons/
_ICONS_DIR = Path(__file__).resolve().parent / "icons"

# 精灵异色图片目录：src/assets/spirits/
_SPIRITS_DIR = Path(__file__).resolve().parent / "spirits"

# 赛季数据目录：src/assets/seasons/
_SEASONS_DIR = Path(__file__).resolve().parent / "seasons"


def _season_sort_key(season_data: dict) -> tuple[int, str]:
    season_id = str(season_data.get("season", ""))
    match = re.search(r"\d+", season_id)
    number = int(match.group()) if match else -1
    return number, season_id


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
def load_spirit_icon(spirit_name: str, size: int = 32, season: str | None = None) -> ctk.CTkImage | None:
    """
    加载精灵异色图标并缓存。

    查找顺序：
      1. spirits/{season}/  （如 spirits/S1/NO.041奇丽草.png）
      2. spirits/           （根目录兜底，兼容旧版文件结构）

    :param spirit_name: 精灵名，支持带编号前缀（如 "No.041 奇丽草"）或纯名（如 "奇丽草"）
    :param size:        渲染尺寸（正方形），默认 32px
    :param season:      赛季标识，如 "S1"、"S2"，None 则只查根目录
    :return:            CTkImage 或 None（文件不存在时）
    """
    if not _SPIRITS_DIR.exists():
        return None

    # 提取纯精灵名（去掉 "No.041 " 前缀）
    lookup = spirit_name.strip()
    if re.match(r"^No\.\d+\s+", lookup):
        lookup = re.sub(r"^No\.\d+\s+", "", lookup)

    # 搜索目录顺序：赛季子目录 → 根目录
    search_dirs: list[Path] = []
    if season:
        search_dirs.append(_SPIRITS_DIR / season)
    search_dirs.append(_SPIRITS_DIR)

    for d in search_dirs:
        if not d.is_dir():
            continue
        for p in d.iterdir():
            if p.suffix.lower() == ".png" and p.stem.endswith(lookup):
                img = Image.open(p).convert("RGBA")
                return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))

    return None


def load_seasons() -> list[dict]:
    """
    扫描 seasons/ 目录，返回按赛季编号排序的赛季数据列表。
    每项格式：{"season": "S1", "label": "...", "spirits": [{"no": 41, "name": "奇丽草"}, ...]}
    """
    if not _SEASONS_DIR.exists():
        return []
    result: list[dict] = []
    for f in sorted(_SEASONS_DIR.glob("*.json")):
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
            result.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return sorted(result, key=_season_sort_key)


def get_latest_season() -> dict | None:
    """返回编号最大的赛季配置；没有赛季配置时返回 None。"""
    seasons = load_seasons()
    if not seasons:
        return None
    return seasons[-1]
