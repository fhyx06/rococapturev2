"""存档读写服务 —— 负责JSON文件的加载、保存、列表管理"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

from src.models.save_slot import SaveSlot
from src.models.constants import SAVES_DIR
from src.assets.icon_loader import list_s1_spirits


class SaveService:
    """管理存档的CRUD与持久化"""

    def __init__(self, saves_dir: str | Path | None = None):
        self.saves_dir = Path(saves_dir or SAVES_DIR)
        self.saves_dir.mkdir(parents=True, exist_ok=True)

        # 当前加载的存档
        self._current: SaveSlot | None = None
        # 当前存档对应的文件路径
        self._current_path: Path | None = None

    # ── 存档列表 ──

    def list_saves(self) -> list[str]:
        """返回所有存档文件名（不含扩展名）"""
        result = []
        for f in self.saves_dir.glob("*.json"):
            name = f.stem
            if name:  # 跳过空文件名
                result.append(name)
        return sorted(result)

    # ── 创建 ──

    def create_save(self, name: str) -> SaveSlot:
        """创建新存档并立即保存到磁盘；默认预填 S1 赛季全部异色精灵"""
        name = name.strip()
        if not name:
            raise ValueError("存档名不能为空")
        path = self._save_path(name)
        if path.exists():
            raise FileExistsError(f"存档 '{name}' 已存在")
        slot = SaveSlot(name)
        # 首次新建存档：预填 S1 全部异色精灵（格式：No.041 奇丽草）
        for no, spirit in list_s1_spirits():
            display_name = f"No.{no:03d} {spirit}"
            slot.family_pool[display_name] = 0
        self._write_json(path, slot.to_dict())
        self._current = slot
        self._current_path = path
        return slot

    # ── 加载 ──

    def load_save(self, name: str) -> SaveSlot:
        """从磁盘加载存档"""
        path = self._save_path(name)
        if not path.exists():
            raise FileNotFoundError(f"存档 '{name}' 不存在")
        data = self._read_json(path)
        slot = SaveSlot.from_dict(data)
        self._current = slot
        self._current_path = path
        return slot

    # ── 保存（实时持久化） ──

    def save_current(self) -> None:
        """将当前存档写入磁盘"""
        if self._current is None or self._current_path is None:
            return
        self._write_json(self._current_path, self._current.to_dict())

    def with_auto_save(self) -> Callable[[], None]:
        """返回一个无参函数，调用时自动保存当前存档。
        用法: after_modify = save_svc.with_auto_save(); slot.xxx(); after_modify()
        """
        return self.save_current

    # ── 删除 ──

    def delete_save(self, name: str) -> None:
        """删除指定存档文件"""
        path = self._save_path(name)
        if not path.exists():
            raise FileNotFoundError(f"存档 '{name}' 不存在")
        path.unlink()
        if self._current and self._current.name == name:
            self._current = None
            self._current_path = None

    # ── 重命名 ──

    def rename_save(self, old_name: str, new_name: str) -> None:
        old_path = self._save_path(old_name)
        new_path = self._save_path(new_name)
        if not old_path.exists():
            raise FileNotFoundError(f"存档 '{old_name}' 不存在")
        if new_path.exists():
            raise FileExistsError(f"存档 '{new_name}' 已存在")
        old_path.rename(new_path)
        if self._current and self._current.name == old_name:
            self._current.name = new_name
            self._current_path = new_path

    # ── 属性 ──

    @property
    def current(self) -> SaveSlot | None:
        return self._current

    @property
    def current_name(self) -> str | None:
        return self._current.name if self._current else None

    # ── 内部方法 ──

    def _save_path(self, name: str) -> Path:
        return self.saves_dir / f"{name}.json"

    @staticmethod
    def _read_json(path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _write_json(path: Path, data: dict) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
