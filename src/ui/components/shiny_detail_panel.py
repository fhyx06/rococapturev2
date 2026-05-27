"""异色明细页面"""
import customtkinter as ctk

from src.models.constants import POOL_ELEMENT, POOL_FAMILY, POOL_RANDOM, POOL_UNKNOWN
from src.models.save_slot import ShinyRecord


class ShinyDetailPanel(ctk.CTkFrame):
    """展示和管理异色出货记录"""

    _pool_labels = {
        POOL_RANDOM: "随机",
        POOL_FAMILY: "家族",
        POOL_ELEMENT: "属性",
        POOL_UNKNOWN: "未知",
    }

    _columns = (
        ("时间", 84),
        ("池", 36),
        ("赛季", 38),
        ("精灵", 124),
        ("属性", 36),
        ("保底", 38),
        ("", 42),
    )

    def __init__(self, master, on_add=None, on_delete=None, **kwargs):
        super().__init__(master, **kwargs)
        self._on_add = on_add
        self._on_delete = on_delete
        self._records: list[ShinyRecord] = []

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 6))

        ctk.CTkLabel(
            header,
            text="异色明细",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(side="left")

        ctk.CTkButton(
            header,
            text="添加",
            width=62,
            fg_color="#f39c12",
            hover_color="#d68910",
            command=self._handle_add,
        ).pack(side="right", padx=(8, 0))

        self._filter_var = ctk.StringVar(value="全部")
        filter_bar = ctk.CTkSegmentedButton(
            header,
            values=["全部", "随机池", "家族池", "属性池", "未知"],
            variable=self._filter_var,
            command=lambda _: self._refresh_display(),
            width=250,
        )
        filter_bar.pack(side="right")

        columns = ctk.CTkFrame(self, fg_color=("gray82", "gray24"), corner_radius=6)
        columns.pack(fill="x", padx=12, pady=(0, 4))
        for text, width in self._columns:
            ctk.CTkLabel(columns, text=text, width=width, anchor="w").pack(side="left", padx=2, pady=6)

        self._list_frame = ctk.CTkScrollableFrame(self)
        self._list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def load_records(self, records: list[ShinyRecord]):
        self._records = list(records)
        self._refresh_display()

    def _handle_add(self):
        if self._on_add:
            self._on_add()

    def _handle_delete(self, index: int):
        if self._on_delete:
            self._on_delete(index)

    def _refresh_display(self):
        for child in self._list_frame.winfo_children():
            child.destroy()

        filter_map = {
            "全部": None,
            "随机池": POOL_RANDOM,
            "家族池": POOL_FAMILY,
            "属性池": POOL_ELEMENT,
            "未知": POOL_UNKNOWN,
        }
        pool_filter = filter_map.get(self._filter_var.get())

        visible_indexes = [
            index
            for index in range(len(self._records) - 1, -1, -1)
            if pool_filter is None or self._records[index].pool_type == pool_filter
        ]

        if not visible_indexes:
            ctk.CTkLabel(
                self._list_frame,
                text="暂无异色记录",
                text_color=("gray45", "gray60"),
            ).pack(pady=24)
            return

        for index in visible_indexes:
            record = self._records[index]
            row = ctk.CTkFrame(self._list_frame, fg_color="transparent")
            row.pack(fill="x", pady=3)

            values = (
                (self._short_time(record.timestamp), 84),
                (self._pool_labels.get(record.pool_type, record.pool_type), 36),
                (record.season or "-", 38),
                (self._short_text(record.spirit_name or "未知精灵", 13), 124),
                (record.element or "-", 36),
                (str(record.pity_count), 38),
            )
            for text, width in values:
                ctk.CTkLabel(row, text=text, width=width, anchor="w").pack(side="left", padx=2, pady=4)

            ctk.CTkButton(
                row,
                text="删",
                width=38,
                fg_color="#95a5a6",
                hover_color="#7f8c8d",
                command=lambda i=index: self._handle_delete(i),
            ).pack(side="left", padx=2, pady=4)

    @staticmethod
    def _short_time(timestamp: str) -> str:
        if len(timestamp) >= 16:
            return timestamp[5:16]
        return timestamp

    @staticmethod
    def _short_text(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return f"{text[:max_chars - 3]}..."
