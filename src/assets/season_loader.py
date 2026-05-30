"""赛季配置读取工具。"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path


_SEASONS_DIR = Path(__file__).resolve().parent / "seasons"


def _season_sort_key(season_data: dict) -> tuple[int, str]:
    season_id = str(season_data.get("season", ""))
    match = re.search(r"\d+", season_id)
    number = int(match.group()) if match else -1
    return number, season_id


@lru_cache(maxsize=1)
def load_seasons() -> list[dict]:
    """扫描 seasons 目录，返回按赛季编号排序的赛季数据。"""
    if not _SEASONS_DIR.exists():
        return []

    seasons: list[dict] = []
    for path in sorted(_SEASONS_DIR.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as fp:
                seasons.append(json.load(fp))
        except (json.JSONDecodeError, OSError):
            continue
    return sorted(seasons, key=_season_sort_key)


def get_latest_season() -> dict | None:
    """返回编号最大的赛季配置；没有赛季配置时返回 None。"""
    seasons = load_seasons()
    if not seasons:
        return None
    return seasons[-1]
