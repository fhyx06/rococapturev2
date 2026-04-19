"""家族池卡片 —— S1 赛季异色追踪总览（手风琴）"""
import customtkinter as ctk

from src.ui.components.counter_display import CounterDisplay
from src.utils.beep import beep
from src.assets.icon_loader import load_spirit_icon, list_s1_spirits


class FamilyPoolCard(ctk.CTkFrame):
    """家族池：S1 赛季异色追踪总览手风琴，支持选中后增加/减少/重置"""

    def __init__(self, master, on_change=None, **kwargs):
        super().__init__(master, **kwargs)
        self._on_change = on_change
        self._counters: dict[str, CounterDisplay] = {}
        self._selected: str | None = None

        # ── 底部按钮（先 pack bottom，确保始终固定在底部） ──
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(side="bottom", pady=(0, 12))

        ctk.CTkButton(btn_frame, text="＋ 增加", width=80, command=self._do_increase).pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="－ 减少", width=80, command=self._do_decrease).pack(side="left", padx=3)
        ctk.CTkButton(
            btn_frame, text="重置", width=60,
            fg_color="#e74c3c", hover_color="#c0392b",
            command=self._do_reset,
        ).pack(side="left", padx=3)

        # ── 标题 ──
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(
            header, text="🏠", width=24,
            font=ctk.CTkFont(size=14),
            anchor="e",
        ).pack(side="left", padx=(0, 2))
        ctk.CTkLabel(
            header, text="家族池",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).pack(side="left")

        # ── 搜索框 ──
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=12, pady=(0, 4))

        self._search_entry = ctk.CTkEntry(search_frame, width=200, placeholder_text="🔍 搜索精灵...")
        self._search_entry.pack(side="left")
        self._search_entry.bind("<KeyRelease>", lambda e: self._filter_list())

        # ── S1 手风琴标题 ──
        self._s1_expanded = True
        title_btn = ctk.CTkButton(
            self,
            text="▼  S1 赛季异色追踪总览",
            anchor="w",
            fg_color=("gray80", "gray25"),
            hover_color=("gray70", "gray30"),
            text_color=("gray10", "gray90"),
            font=ctk.CTkFont(size=13, weight="bold"),
            height=30,
            command=self._toggle_s1,
        )
        title_btn.pack(fill="x", padx=12, pady=(0, 2))
        self._s1_title_btn = title_btn

        # ── 滚动列表区（填充剩余空间） ──
        self._scroll_frame = ctk.CTkScrollableFrame(self)
        self._scroll_frame.pack(fill="both", expand=True, padx=12, pady=(0, 4))

        # 构建所有 S1 精灵行
        self._s1_spirit_icons: dict[str, ctk.CTkImage | None] = {}
        for no, name in list_s1_spirits():
            self._create_s1_row(no, name)

    # ── S1 行构建 ──

    def _create_s1_row(self, no: int, name: str):
        """创建一行精灵条目（图标+编号+名称+计数器+进度条）"""
        display_name = f"No.{no:03d} {name}"
        icon = load_spirit_icon(name, size=36)
        self._s1_spirit_icons[name] = icon  # 防止 GC

        row = ctk.CTkFrame(self._scroll_frame, fg_color="transparent", cursor="hand2")
        row.pack(fill="x", pady=3)
        row._spirit_name = display_name  # type: ignore

        # 图标
        if icon:
            img_label = ctk.CTkLabel(row, image=icon, text="", width=44)
        else:
            img_label = ctk.CTkLabel(row, text="?", width=44, font=ctk.CTkFont(size=20))
        img_label.pack(side="left", padx=(4, 6), pady=3)

        # 编号
        no_label = ctk.CTkLabel(
            row, text=f"No.{no:03d}",
            width=60, anchor="w",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60"),
        )
        no_label.pack(side="left", padx=(0, 4))

        # 精灵名
        name_label = ctk.CTkLabel(
            row, text=name,
            width=80, anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        name_label.pack(side="left", padx=(0, 6))

        # 计数器
        counter = CounterDisplay(row, font=ctk.CTkFont(size=20, weight="bold"))
        counter.set_count(0)
        self._counters[display_name] = counter
        counter.pack(side="left", padx=(0, 8))

        # 进度条
        progress = ctk.CTkProgressBar(row, width=110)
        progress.pack(side="left", padx=(0, 8))
        progress.set(0)
        row._progress = progress  # type: ignore
        row._counter = counter  # type: ignore

        # 点击选中
        def on_click(event, r=row, n=display_name):
            self._select(n, r)
        row.bind("<Button-1>", on_click)
        img_label.bind("<Button-1>", on_click)
        no_label.bind("<Button-1>", on_click)
        name_label.bind("<Button-1>", on_click)
        counter.bind("<Button-1>", on_click)

    # ── 手风琴折叠 ──

    def _toggle_s1(self):
        """展开/收起 S1 总览"""
        self._s1_expanded = not self._s1_expanded
        if self._s1_expanded:
            self._scroll_frame.pack(fill="both", expand=True, padx=12, pady=(0, 4))
            self._s1_title_btn.configure(text="▼  S1 赛季异色追踪总览")
        else:
            self._scroll_frame.pack_forget()
            self._s1_title_btn.configure(text="▶  S1 赛季异色追踪总览")

    # ── 搜索过滤 ──

    def _filter_list(self):
        query = self._search_entry.get().strip().lower()
        for widget in self._scroll_frame.winfo_children():
            name = getattr(widget, "_spirit_name", "")
            # 同时匹配名称和纯数字编号（如输入 "41" 可匹配 "No.041"）
            match_text = name.lower()
            num_only = "".join(c for c in match_text if c.isdigit())
            if query and query not in match_text and query not in num_only:
                widget.pack_forget()
            else:
                widget.pack(fill="x", pady=3)

    # ── 外部调用：同步数据 ──

    def refresh_from_data(self, family_pool: dict[str, int]):
        """根据存档数据刷新所有计数器和进度条"""
        self._selected = None
        for widget in self._scroll_frame.winfo_children():
            if hasattr(widget, "_selected"):
                widget.configure(fg_color="transparent")
                del widget._selected  # type: ignore

        for widget in self._scroll_frame.winfo_children():
            display_name = getattr(widget, "_spirit_name", None)
            if display_name is None:
                continue
            count = family_pool.get(display_name, 0)
            counter = getattr(widget, "_counter", None)
            progress = getattr(widget, "_progress", None)
            if counter:
                counter.set_count(count)
                self._counters[display_name] = counter
            if progress:
                progress.set(min(count / 80, 1.0))

    def update_counter(self, name: str, count: int):
        if name in self._counters:
            self._counters[name].set_count(count)
        for widget in self._scroll_frame.winfo_children():
            if getattr(widget, "_spirit_name", None) == name:
                progress = getattr(widget, "_progress", None)
                if progress:
                    progress.set(min(count / 80, 1.0))
                break

    # ── 内部方法 ──

    def _select(self, name: str, row: ctk.CTkFrame):
        for widget in self._scroll_frame.winfo_children():
            if hasattr(widget, "_selected"):
                widget.configure(fg_color="transparent")
                del widget._selected  # type: ignore

        row.configure(fg_color=("gray85", "gray25"))
        row._selected = True  # type: ignore
        self._selected = name

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
