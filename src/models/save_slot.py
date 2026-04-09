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
    POOL_RANDOM,
    POOL_FAMILY,
    POOL_ELEMENT,
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
            ACTION_INCREASE: "增加",
            ACTION_DECREASE: "减少",
            ACTION_RESET: "重置",
            ACTION_DELETE: "删除",
        }
        action_text = action_map.get(self.action, self.action)
        if self.target:
            return f"[{self.timestamp}] {action_text} | {self.target} (总:{self.count_after})"
        return f"[{self.timestamp}] {action_text} (总:{self.count_after})"


class SaveSlot:
    """一个存档的完整数据"""

    def __init__(self, name: str):
        self.name = name
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.random_pool: int = 0
        self.family_pool: dict[str, int] = {}
        self.element_pool: dict[str, int] = {}
        self.global_counter: int = 0
        self.logs: list[ActivityLog] = []

    # ── 随机池操作 ──

    def random_increase(self, spirit_name: str = "") -> list[ActivityLog]:
        self.random_pool += 1
        self.global_counter += 1
        self._touch()
        log = ActivityLog(POOL_RANDOM, ACTION_INCREASE, spirit_name or "随机池", self.random_pool)
        self.logs.append(log)
        return [log]

    def random_decrease(self, spirit_name: str = "") -> list[ActivityLog]:
        if self.random_pool > 0:
            self.random_pool -= 1
            self.global_counter = max(0, self.global_counter - 1)
            self._touch()
            log = ActivityLog(POOL_RANDOM, ACTION_DECREASE, spirit_name or "随机池", self.random_pool)
            self.logs.append(log)
            return [log]
        return []

    def random_reset(self) -> list[ActivityLog]:
        if self.random_pool == 0:
            return []
        diff = self.random_pool
        self.random_pool = 0
        self.global_counter = max(0, self.global_counter - diff)
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
        self.global_counter += 1
        self._touch()
        log = ActivityLog(POOL_FAMILY, ACTION_INCREASE, spirit_name, self.family_pool[spirit_name])
        self.logs.append(log)
        return [log]

    def family_decrease(self, spirit_name: str) -> list[ActivityLog]:
        if spirit_name not in self.family_pool or self.family_pool[spirit_name] <= 0:
            return []
        self.family_pool[spirit_name] -= 1
        self.global_counter = max(0, self.global_counter - 1)
        self._touch()
        log = ActivityLog(POOL_FAMILY, ACTION_DECREASE, spirit_name, self.family_pool[spirit_name])
        self.logs.append(log)
        return [log]

    def family_reset(self, spirit_name: str) -> list[ActivityLog]:
        if spirit_name not in self.family_pool or self.family_pool[spirit_name] == 0:
            return []
        diff = self.family_pool[spirit_name]
        self.family_pool[spirit_name] = 0
        self.global_counter = max(0, self.global_counter - diff)
        self._touch()
        log = ActivityLog(POOL_FAMILY, ACTION_RESET, spirit_name, 0)
        self.logs.append(log)
        return [log]

    def family_delete(self, spirit_name: str) -> list[ActivityLog]:
        if spirit_name not in self.family_pool:
            return []
        diff = self.family_pool[spirit_name]
        del self.family_pool[spirit_name]
        self.global_counter = max(0, self.global_counter - diff)
        self._touch()
        log = ActivityLog(POOL_FAMILY, ACTION_DELETE, spirit_name, 0)
        self.logs.append(log)
        return [log]

    # ── 全局计数操作 ──

    def global_reset(self) -> list[ActivityLog]:
        """将全局计数单独归零（异色提前出现时使用）"""
        if self.global_counter == 0:
            return []
        self.global_counter = 0
        self._touch()
        log = ActivityLog("global", ACTION_RESET, "全局计数", 0)
        self.logs.append(log)
        return [log]

    # ── 属性池操作 ──

    def element_increase(self, element: str) -> list[ActivityLog]:
        if element not in self.element_pool:
            self.element_pool[element] = 0
        self.element_pool[element] += 1
        self.global_counter += 1
        self._touch()
        log = ActivityLog(POOL_ELEMENT, ACTION_INCREASE, element, self.element_pool[element])
        self.logs.append(log)
        return [log]

    def element_decrease(self, element: str) -> list[ActivityLog]:
        if element not in self.element_pool or self.element_pool[element] <= 0:
            return []
        self.element_pool[element] -= 1
        self.global_counter = max(0, self.global_counter - 1)
        self._touch()
        log = ActivityLog(POOL_ELEMENT, ACTION_DECREASE, element, self.element_pool[element])
        self.logs.append(log)
        return [log]

    def element_reset(self, element: str) -> list[ActivityLog]:
        if element not in self.element_pool or self.element_pool[element] == 0:
            return []
        diff = self.element_pool[element]
        self.element_pool[element] = 0
        self.global_counter = max(0, self.global_counter - diff)
        self._touch()
        log = ActivityLog(POOL_ELEMENT, ACTION_RESET, element, 0)
        self.logs.append(log)
        return [log]

    # ── 序列化 ──

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "random_pool": self.random_pool,
            "family_pool": copy.deepcopy(self.family_pool),
            "element_pool": copy.deepcopy(self.element_pool),
            "global_counter": self.global_counter,
            "logs": [log.to_dict() for log in self.logs],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SaveSlot:
        slot = cls(data["name"])
        slot.created_at = data.get("created_at", slot.created_at)
        slot.updated_at = data.get("updated_at", slot.updated_at)
        slot.random_pool = data.get("random_pool", 0)
        slot.family_pool = data.get("family_pool", {})
        slot.element_pool = data.get("element_pool", {})
        slot.global_counter = data.get("global_counter", 0)
        slot.logs = [ActivityLog.from_dict(log_data) for log_data in data.get("logs", [])]
        return slot

    def _touch(self):
        self.updated_at = datetime.now().isoformat()
