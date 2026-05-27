"""属性池卡片 —— 18种属性的网格展示，含属性图标"""
import customtkinter as ctk

from src.models.constants import ELEMENTS, PITY_WARN_THRESHOLD, PITY_MAX, COLOR_WARN, COLOR_CRITICAL
from src.utils.beep import beep
from src.assets.icon_loader import load_element_icon


class ElementPoolCard(ctk.CTkFrame):
    """属性池：18种属性各自独立计数，网格展示"""

    def __init__(self, master, on_change=None, **kwargs):
        super().__init__(master, **kwargs)
        self._on_change = on_change
        self._counters: dict[str, ctk.CTkLabel] = {}
        self._progress_bars: dict[str, ctk.CTkProgressBar] = {}
        self._selected: str | None = None
        self._rows: dict[str, ctk.CTkFrame] = {}

        # 标题
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(
            header, text="属性池",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).pack(side="left")

        # 网格区域（可滚动）
        grid_frame = ctk.CTkScrollableFrame(self, height=240)
        grid_frame.pack(fill="both", expand=True, padx=12, pady=(0, 4))

        for element in ELEMENTS:
            self._create_element_cell(grid_frame, element)

        # 操作按钮
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(4, 12))

        ctk.CTkButton(btn_frame, text="＋ 增加", width=80, command=self._do_increase).pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="－ 减少", width=80, command=self._do_decrease).pack(side="left", padx=3)
        ctk.CTkButton(
            btn_frame, text="重置", width=60,
            fg_color="#e74c3c", hover_color="#c0392b",
            command=self._do_reset,
        ).pack(side="left", padx=3)
        ctk.CTkButton(
            btn_frame, text="出异色了！", width=96,
            fg_color="#f39c12", hover_color="#d68910",
            command=self._do_shiny,
        ).pack(side="left", padx=3)

    def _create_element_cell(self, parent, element: str):
        cell = ctk.CTkFrame(parent, cursor="hand2", corner_radius=8)
        cell.pack(fill="x", pady=3, padx=2)
        cell._element_name = element  # type: ignore

        # ── 图标（24×24，无图标时占位保持对齐）
        icon = load_element_icon(element, size=24)
        if icon:
            icon_label = ctk.CTkLabel(cell, image=icon, text="", width=30)
        else:
            icon_label = ctk.CTkLabel(cell, text="", width=30)
        icon_label.pack(side="left", padx=(10, 4), pady=4)

        # ── 属性名
        label = ctk.CTkLabel(cell, text=element, width=52, anchor="w",
                             font=ctk.CTkFont(size=16, weight="bold"))
        label.pack(side="left", padx=(0, 6), pady=4)

        # ── 计数
        counter = ctk.CTkLabel(cell, text="0", width=36, anchor="center",
                               font=ctk.CTkFont(size=18, weight="bold"))
        counter.pack(side="left", padx=(0, 6), pady=4)
        self._counters[element] = counter

        # ── 进度条
        progress = ctk.CTkProgressBar(cell, width=100)
        progress.pack(side="left", padx=(0, 10), pady=4)
        progress.set(0)
        self._progress_bars[element] = progress

        cell._counter_label = counter   # type: ignore
        cell._progress_bar = progress   # type: ignore
        self._rows[element] = cell

        # 点击整行均可选中
        def on_click(event, e=element, c=cell):
            self._select(e, c)

        for widget in (cell, icon_label, label, counter):
            widget.bind("<Button-1>", on_click)

    def _select(self, element: str, cell: ctk.CTkFrame):
        for e, row in self._rows.items():
            row.configure(fg_color="transparent")
        cell.configure(fg_color=("gray85", "gray25"))
        self._selected = element

    # ── 外部调用 ──

    def update_counter(self, element: str, count: int):
        if element not in self._counters:
            return
        label = self._counters[element]
        label.configure(text=str(count))
        if count >= PITY_MAX:
            label.configure(text_color=COLOR_CRITICAL)
        elif count >= PITY_WARN_THRESHOLD:
            label.configure(text_color=COLOR_WARN)
        else:
            label.configure(text_color="#ffffff")
        self._progress_bars[element].set(min(count / PITY_MAX, 1.0))

    # ── 内部操作 ──

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
            f"确定要重置「{self._selected}」属性的保底计数吗？",
        )
        if dialog.result:
            beep()
            if self._on_change:
                self._on_change("reset", self._selected)

    def _do_shiny(self):
        if not self._selected:
            return
        beep()
        if self._on_change:
            self._on_change("shiny", self._selected)
