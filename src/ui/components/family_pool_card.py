"""家族池卡片 —— 精灵列表 + 搜索 + 增删操作"""
import customtkinter as ctk

from src.ui.components.counter_display import CounterDisplay
from src.utils.beep import beep


class FamilyPoolCard(ctk.CTkFrame):
    """家族池：可添加多个精灵，各自独立计数"""

    def __init__(self, master, on_change=None, **kwargs):
        super().__init__(master, **kwargs)
        self._on_change = on_change
        self._counters: dict[str, CounterDisplay] = {}
        self._selected: str | None = None

        # 标题
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(
            header, text="🏠 家族池",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(side="left")

        # 搜索 + 添加
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=12, pady=(0, 4))

        self._search_entry = ctk.CTkEntry(input_frame, width=160, placeholder_text="🔍 搜索精灵...")
        self._search_entry.pack(side="left", padx=(0, 6))
        self._search_entry.bind("<KeyRelease>", lambda e: self._filter_list())

        self._add_entry = ctk.CTkEntry(input_frame, width=140, placeholder_text="添加精灵名")
        self._add_entry.pack(side="left", padx=(0, 4))
        self._add_entry.bind("<Return>", lambda e: self._do_add())

        ctk.CTkButton(input_frame, text="＋", width=36, command=self._do_add).pack(side="left")

        # 滚动列表区域
        self._list_frame = ctk.CTkScrollableFrame(self, height=220)
        self._list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 4))

        # 选中精灵的操作按钮
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 12))

        ctk.CTkButton(btn_frame, text="＋ 增加", width=80, command=self._do_increase).pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="－ 减少", width=80, command=self._do_decrease).pack(side="left", padx=3)
        ctk.CTkButton(
            btn_frame, text="重置", width=60,
            fg_color="#e74c3c", hover_color="#c0392b",
            command=self._do_reset,
        ).pack(side="left", padx=3)
        ctk.CTkButton(
            btn_frame, text="删除", width=60,
            fg_color="#95a5a6", hover_color="#7f8c8d",
            command=self._do_delete,
        ).pack(side="left", padx=3)

    # ── 外部调用：同步数据 ──

    def refresh_from_data(self, family_pool: dict[str, int]):
        """根据存档数据刷新整个列表"""
        self._counters.clear()
        for widget in self._list_frame.winfo_children():
            widget.destroy()
        self._selected = None

        for name, count in family_pool.items():
            self._create_row(name, count)

    def update_counter(self, name: str, count: int):
        if name in self._counters:
            self._counters[name].set_count(count)

    def remove_row(self, name: str):
        if name in self._counters:
            del self._counters[name]
        for widget in self._list_frame.winfo_children():
            row_name = getattr(widget, "_spirit_name", None)
            if row_name == name:
                widget.destroy()
                break
        if self._selected == name:
            self._selected = None

    # ── 内部方法 ──

    def _create_row(self, name: str, count: int) -> ctk.CTkFrame:
        row = ctk.CTkFrame(self._list_frame, fg_color="transparent", cursor="hand2")
        row.pack(fill="x", pady=2)
        row._spirit_name = name  # type: ignore

        # 选中高亮
        counter = CounterDisplay(row, font=ctk.CTkFont(size=18, weight="bold"))
        counter.set_count(count)
        self._counters[name] = counter

        label = ctk.CTkLabel(row, text=name, width=140, anchor="w")
        label.pack(side="left", padx=(4, 8))
        counter.pack(side="left", padx=(0, 8))

        # 进度条 (count / 80)
        progress = ctk.CTkProgressBar(row, width=100)
        progress.pack(side="left", padx=(0, 8))
        progress.set(min(count / 80, 1.0))

        row._progress = progress  # type: ignore
        row._counter = counter  # type: ignore

        def on_click(event, r=row, n=name):
            self._select(n, r)

        row.bind("<Button-1>", on_click)
        label.bind("<Button-1>", on_click)
        counter.bind("<Button-1>", on_click)

        return row

    def _select(self, name: str, row: ctk.CTkFrame):
        # 取消之前的选中
        for widget in self._list_frame.winfo_children():
            if hasattr(widget, "_selected"):
                widget.configure(fg_color="transparent")
                del widget._selected  # type: ignore

        row.configure(fg_color=("gray85", "gray25"))
        row._selected = True  # type: ignore
        self._selected = name

    def _filter_list(self):
        query = self._search_entry.get().strip().lower()
        for widget in self._list_frame.winfo_children():
            name = getattr(widget, "_spirit_name", "")
            if query and query not in name.lower():
                widget.pack_forget()
            else:
                widget.pack(fill="x", pady=2)

    def _do_add(self):
        name = self._add_entry.get().strip()
        if not name:
            return
        beep()
        if self._on_change:
            self._on_change("add", name)
        self._add_entry.delete(0, "end")

    def _do_increase(self):
        if not self._selected:
            return
        beep()
        if self._on_change:
            self._on_change("increase", self._selected)

    def _do_decrease(self):
        if not self._selected:
            return
        beep()
        if self._on_change:
            self._on_change("decrease", self._selected)

    def _do_reset(self):
        if not self._selected:
            return
        from src.ui.dialogs.confirm_dialog import ConfirmDialog
        dialog = ConfirmDialog(
            self.winfo_toplevel(), "确认重置",
            f"确定要重置「{self._selected}」的保底计数吗？",
        )
        if dialog.result:
            beep()
            if self._on_change:
                self._on_change("reset", self._selected)

    def _do_delete(self):
        if not self._selected:
            return
        from src.ui.dialogs.confirm_dialog import ConfirmDialog
        dialog = ConfirmDialog(
            self.winfo_toplevel(), "确认删除",
            f"确定要删除「{self._selected}」吗？此操作不可撤销。",
        )
        if dialog.result:
            beep()
            if self._on_change:
                self._on_change("delete", self._selected)
