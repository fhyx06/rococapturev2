"""存档数据模型"""
from __future__ import annotations

import copy
from datetime import datetime
from typing import Any

from src.models.constants import (
    PITY_MAX,
    ACTION_INCREASE,
    ACTION_DECREASE,
    ACTION_RESET,
    ACTION_DELETE,
    ACTION_SHINY,
    POOL_RANDOM,
    POOL_FAMILY,
    POOL_ELEMENT,
    POOL_UNKNOWN,
)


class ActivityLog:
    """单条操作日志"""

    def __init__(
        self,
        pool_type: str,
        action: str,
        target: str = "",
        count_after: int = 0,
        timestamp: str | None = None,
    ):
        self.timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.pool_type = pool_type
        self.action = action
        self.target = target
        self.count_after = count_after

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "pool_type": self.pool_type,
            "action": self.action,
            "target": self.target,
            "count_after": self.count_after,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActivityLog:
        return cls(
            timestamp=data.get("timestamp"),
            pool_type=data["pool_type"],
            action=data["action"],
            target=data.get("target", ""),
            count_after=data.get("count_after", 0),
        )

    def format_display(self) -> str:
        """格式化为日志显示文本"""
        action_map = {
            ACTION_INCREASE: "+",
            ACTION_DECREASE: "-",
            ACTION_RESET: "重置",
            ACTION_DELETE: "删除",
            ACTION_SHINY: "出异色",
        }
        action_text = action_map.get(self.action, self.action)
        count_label = "保底" if self.action == ACTION_SHINY else "总"
        timestamp = self._short_timestamp()
        if self.target:
            target = self._short_target()
            return f"{timestamp} {action_text} {target} {count_label}:{self.count_after}"
        return f"{timestamp} {action_text} {count_label}:{self.count_after}"

    def _short_timestamp(self) -> str:
        if len(self.timestamp) >= 16:
            return self.timestamp[5:16]
        return self.timestamp

    def _short_target(self) -> str:
        if len(self.target) <= 18:
            return self.target
        return f"{self.target[:15]}..."


class ShinyRecord:
    """单条异色出货记录"""

    def __init__(
        self,
        pool_type: str,
        spirit_name: str,
        pity_count: int,
        season: str = "",
        element: str = "",
        reset_after_record: bool = True,
        timestamp: str | None = None,
    ):
        self.timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.pool_type = pool_type
        self.season = season
        self.spirit_name = spirit_name
        self.element = element
        try:
            count = int(pity_count)
        except (TypeError, ValueError):
            count = 0
        self.pity_count = max(0, count)
        self.reset_after_record = reset_after_record

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "pool_type": self.pool_type,
            "season": self.season,
            "spirit_name": self.spirit_name,
            "element": self.element,
            "pity_count": self.pity_count,
            "reset_after_record": self.reset_after_record,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ShinyRecord:
        return cls(
            timestamp=data.get("timestamp"),
            pool_type=data.get("pool_type", POOL_UNKNOWN),
            season=data.get("season", ""),
            spirit_name=data.get("spirit_name", ""),
            element=data.get("element", ""),
            pity_count=data.get("pity_count", 0),
            reset_after_record=data.get("reset_after_record", True),
        )

    def format_display(self) -> str:
        pool_map = {
            POOL_RANDOM: "随机池",
            POOL_FAMILY: "家族池",
            POOL_ELEMENT: "属性池",
            POOL_UNKNOWN: "未知池",
        }
        pool_text = pool_map.get(self.pool_type, self.pool_type)
        season_text = self.season or "未知赛季"
        spirit_text = self.spirit_name or "未知精灵"
        element_text = f" / {self.element}" if self.element else ""
        return f"[{self.timestamp}] {pool_text} / {season_text} / {spirit_text}{element_text} | 保底:{self.pity_count}"


class SaveSlot:
    """一个存档的完整数据"""

    def __init__(self, name: str):
        self.name = name
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.random_pool: int = 0
        self.family_pool: dict[str, int] = {}
        self.element_pool: dict[str, int] = {}
        self.logs: list[ActivityLog] = []
        self.shiny_records: list[ShinyRecord] = []

    # ── 随机池操作 ──

    def random_increase(self, spirit_name: str = "") -> list[ActivityLog]:
        self.random_pool += 1
        self._touch()
        log = ActivityLog(POOL_RANDOM, ACTION_INCREASE, spirit_name or "随机池", self.random_pool)
        self.logs.append(log)
        return [log]

    def random_decrease(self, spirit_name: str = "") -> list[ActivityLog]:
        if self.random_pool > 0:
            self.random_pool -= 1
            self._touch()
            log = ActivityLog(POOL_RANDOM, ACTION_DECREASE, spirit_name or "随机池", self.random_pool)
            self.logs.append(log)
            return [log]
        return []

    def random_reset(self) -> list[ActivityLog]:
        if self.random_pool == 0:
            return []
        self.random_pool = 0
        self._touch()
        log = ActivityLog(POOL_RANDOM, ACTION_RESET, "随机池", 0)
        self.logs.append(log)
        return [log]

    # ── 家族池操作 ──

    def family_add(self, spirit_name: str) -> list[ActivityLog]:
        spirit_name = spirit_name.strip()
        if not spirit_name or spirit_name in self.family_pool:
            return []
        self.family_pool[spirit_name] = 0
        self._touch()
        log = ActivityLog(POOL_FAMILY, ACTION_INCREASE, spirit_name, 0)
        self.logs.append(log)
        return [log]

    def family_increase(self, spirit_name: str) -> list[ActivityLog]:
        if spirit_name not in self.family_pool:
            return []
        self.family_pool[spirit_name] += 1
        self._touch()
        log = ActivityLog(POOL_FAMILY, ACTION_INCREASE, spirit_name, self.family_pool[spirit_name])
        self.logs.append(log)
        return [log]

    def family_decrease(self, spirit_name: str) -> list[ActivityLog]:
        if spirit_name not in self.family_pool or self.family_pool[spirit_name] <= 0:
            return []
        self.family_pool[spirit_name] -= 1
        self._touch()
        log = ActivityLog(POOL_FAMILY, ACTION_DECREASE, spirit_name, self.family_pool[spirit_name])
        self.logs.append(log)
        return [log]

    def family_reset(self, spirit_name: str) -> list[ActivityLog]:
        if spirit_name not in self.family_pool or self.family_pool[spirit_name] == 0:
            return []
        self.family_pool[spirit_name] = 0
        self._touch()
        log = ActivityLog(POOL_FAMILY, ACTION_RESET, spirit_name, 0)
        self.logs.append(log)
        return [log]

    def family_delete(self, spirit_name: str) -> list[ActivityLog]:
        if spirit_name not in self.family_pool:
            return []
        del self.family_pool[spirit_name]
        self._touch()
        log = ActivityLog(POOL_FAMILY, ACTION_DELETE, spirit_name, 0)
        self.logs.append(log)
        return [log]

    # ── 属性池操作 ──

    def element_increase(self, element: str) -> list[ActivityLog]:
        if element not in self.element_pool:
            self.element_pool[element] = 0
        self.element_pool[element] += 1
        self._touch()
        log = ActivityLog(POOL_ELEMENT, ACTION_INCREASE, element, self.element_pool[element])
        self.logs.append(log)
        return [log]

    def element_decrease(self, element: str) -> list[ActivityLog]:
        if element not in self.element_pool or self.element_pool[element] <= 0:
            return []
        self.element_pool[element] -= 1
        self._touch()
        log = ActivityLog(POOL_ELEMENT, ACTION_DECREASE, element, self.element_pool[element])
        self.logs.append(log)
        return [log]

    def element_reset(self, element: str) -> list[ActivityLog]:
        if element not in self.element_pool or self.element_pool[element] == 0:
            return []
        self.element_pool[element] = 0
        self._touch()
        log = ActivityLog(POOL_ELEMENT, ACTION_RESET, element, 0)
        self.logs.append(log)
        return [log]

    # ── 异色记录 ──

    def add_shiny_record(
        self,
        pool_type: str,
        spirit_name: str,
        pity_count: int,
        season: str = "",
        element: str = "",
        reset_after_record: bool = True,
    ) -> ActivityLog:
        record = ShinyRecord(
            pool_type=pool_type,
            spirit_name=spirit_name,
            pity_count=pity_count,
            season=season,
            element=element,
            reset_after_record=reset_after_record,
        )
        self.shiny_records.append(record)
        target = spirit_name or "未知精灵"
        if element:
            target = f"{target} / {element}"
        log = ActivityLog(pool_type, ACTION_SHINY, target, pity_count)
        self.logs.append(log)
        self._touch()
        return log

    def clear_random_pool(self) -> None:
        self.random_pool = 0
        self._touch()

    def clear_family_pool(self, spirit_name: str) -> None:
        if spirit_name in self.family_pool:
            self.family_pool[spirit_name] = 0
            self._touch()

    def clear_element_pool(self, element: str) -> None:
        if element in self.element_pool:
            self.element_pool[element] = 0
            self._touch()

    def delete_shiny_record(self, index: int) -> bool:
        if index < 0 or index >= len(self.shiny_records):
            return False
        del self.shiny_records[index]
        self._touch()
        return True

    # ── 序列化 ──

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "random_pool": self.random_pool,
            "family_pool": copy.deepcopy(self.family_pool),
            "element_pool": copy.deepcopy(self.element_pool),
            "logs": [log.to_dict() for log in self.logs],
            "shiny_records": [record.to_dict() for record in self.shiny_records],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SaveSlot:
        slot = cls(data["name"])
        slot.created_at = data.get("created_at", slot.created_at)
        slot.updated_at = data.get("updated_at", slot.updated_at)
        slot.random_pool = data.get("random_pool", 0)
        slot.family_pool = data.get("family_pool", {})
        slot.element_pool = data.get("element_pool", {})
        slot.logs = [ActivityLog.from_dict(log_data) for log_data in data.get("logs", [])]
        slot.shiny_records = [
            ShinyRecord.from_dict(record_data)
            for record_data in data.get("shiny_records", [])
        ]
        return slot

    def _touch(self):
        self.updated_at = datetime.now().isoformat()
