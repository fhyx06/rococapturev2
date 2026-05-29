"""家族池卡片 —— 多赛季异色追踪总览（数据驱动手风琴）"""
import customtkinter as ctk

from src.ui.components.counter_display import CounterDisplay
from src.utils.beep import beep
from src.assets.icon_loader import load_element_icon, load_spirit_icon, load_seasons


class FamilyPoolCard(ctk.CTkFrame):
    """
    家族池：从 src/assets/seasons/*.json 动态加载赛季配置，
    每个赛季渲染为一个可折叠的手风琴块。
    新增赛季只需放置对应 JSON 文件，无需修改任何代码。
    """

    def __init__(self, master, on_change=None, **kwargs):
        super().__init__(master, **kwargs)
        self._on_change = on_change
        self._counters: dict[str, list[CounterDisplay]] = {}  # display_name → CounterDisplay 列表
        self._selected: str | None = None
        self._selected_season: str = ""
        self._season_sections: list[dict] = []
        self._icon_refs: list = []  # 防止图片被 GC

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
        ctk.CTkButton(
            btn_frame, text="出异色了！", width=96,
            fg_color="#f39c12", hover_color="#d68910",
            command=self._do_shiny,
        ).pack(side="left", padx=3)

        # ── 标题 ──
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(
            header, text="家族池",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).pack(side="left")

        # ── 搜索框 ──
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=12, pady=(0, 4))

        self._search_entry = ctk.CTkEntry(search_frame, width=200, placeholder_text="搜索精灵...")
        self._search_entry.pack(side="left")
        self._search_entry.bind("<KeyRelease>", lambda e: self._filter_list())

        # ── 外层滚动区（容纳所有赛季） ──
        self._outer_scroll = ctk.CTkScrollableFrame(self)
        self._outer_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 4))

        # ── 动态加载所有赛季 ──
        seasons = load_seasons()
        if not seasons:
            ctk.CTkLabel(
                self._outer_scroll,
                text="未找到赛季配置\n请在 src/assets/seasons/ 放置 JSON 文件",
                text_color=("gray50", "gray60"),
            ).pack(pady=20)
        for season_data in seasons:
            self._build_season_section(season_data)

    # ──────────────────── 构建赛季块 ────────────────────

    def _build_season_section(self, season_data: dict):
        """为一个赛季创建折叠头 + 精灵行容器"""
        season_id = season_data.get("season", "?")
        label = season_data.get("label", f"{season_id} 赛季追踪")
        spirits = season_data.get("spirits", [])

        # 折叠按钮
        header_btn = ctk.CTkButton(
            self._outer_scroll,
            text=f"▼  {label}",
            anchor="w",
            fg_color=("gray80", "gray25"),
            hover_color=("gray70", "gray30"),
            text_color=("gray10", "gray90"),
            font=ctk.CTkFont(size=13, weight="bold"),
            height=30,
        )
        header_btn.pack(fill="x", pady=(4, 2))

        # 精灵行容器（默认折叠，不 pack）
        body_frame = ctk.CTkFrame(self._outer_scroll, fg_color="transparent")

        section: dict = {
            "season": season_id,
            "label": label,
            "expanded": False,
            "header_btn": header_btn,
            "body_frame": body_frame,
        }
        self._season_sections.append(section)

        # 绑定折叠/展开
        header_btn.configure(command=lambda s=section: self._toggle_section(s))

        # 默认显示折叠箭头
        header_btn.configure(text=f"▶  {label}")

        # 构建精灵行
        for spirit in spirits:
            self._create_spirit_row(
                body_frame,
                spirit["no"],
                spirit["name"],
                season_id,
                spirit.get("elements", []),
            )

    def _create_spirit_row(self, parent: ctk.CTkFrame, no: int, name: str, season: str, elements: list[str]):
        """创建一行精灵条目（图标 + 编号 + 名称 + 计数器 + 进度条）"""
        display_name = f"No.{no:03d} {name}"
        icon = load_spirit_icon(name, size=36, season=season)
        if icon:
            self._icon_refs.append(icon)  # 防 GC

        row = ctk.CTkFrame(parent, fg_color="transparent", cursor="hand2")
        row.pack(fill="x", pady=3)
        row._spirit_name = display_name  # type: ignore
        row._season = season  # type: ignore

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

        # 属性图标
        element_labels = []
        for element in elements:
            element_icon = load_element_icon(element, size=18)
            if not element_icon:
                continue
            self._icon_refs.append(element_icon)
            element_label = ctk.CTkLabel(row, image=element_icon, text="", width=20)
            element_label.pack(side="left", padx=(0, 2), pady=3)
            element_labels.append(element_label)

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
        self._counters.setdefault(display_name, []).append(counter)
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

        for widget in (row, img_label, no_label, *element_labels, name_label, counter):
            widget.bind("<Button-1>", on_click)

    # ──────────────────── 手风琴折叠 ────────────────────

    def _toggle_section(self, section: dict):
        """手风琴：展开当前，收起其他所有"""
        for s in self._season_sections:
            if s is section:
                # 切换当前：折叠→展开，或展开→折叠
                s["expanded"] = not s["expanded"]
            elif s["expanded"]:
                # 收起其他已展开的
                s["expanded"] = False
                s["body_frame"].pack_forget()
                s["header_btn"].configure(text=f"▶  {s['label']}")

        if section["expanded"]:
            # 用 after= 确保 body 紧跟在 header_btn 之后，避免布局错乱
            section["body_frame"].pack(fill="x", pady=(0, 4), after=section["header_btn"])
            section["header_btn"].configure(text=f"▼  {section['label']}")
        else:
            section["body_frame"].pack_forget()
            section["header_btn"].configure(text=f"▶  {section['label']}")

    # ──────────────────── 搜索过滤（跨所有赛季） ────────────────────

    def _filter_list(self):
        query = self._search_entry.get().strip().lower()
        for section in self._season_sections:
            for widget in section["body_frame"].winfo_children():
                name = getattr(widget, "_spirit_name", "")
                match_text = name.lower()
                num_only = "".join(c for c in match_text if c.isdigit())
                if query and query not in match_text and query not in num_only:
                    widget.pack_forget()
                else:
                    widget.pack(fill="x", pady=3)

    # ──────────────────── 外部调用：同步数据 ────────────────────

    def refresh_from_data(self, family_pool: dict[str, int]):
        """根据存档数据刷新所有计数器和进度条"""
        self._selected = None
        self._selected_season = ""
        for section in self._season_sections:
            for widget in section["body_frame"].winfo_children():
                # 清除选中高亮
                if hasattr(widget, "_selected"):
                    widget.configure(fg_color="transparent")
                    try:
                        del widget._selected  # type: ignore
                    except AttributeError:
                        pass
                # 刷新计数
                display_name = getattr(widget, "_spirit_name", None)
                if display_name is None:
                    continue
                count = family_pool.get(display_name, 0)
                counter = getattr(widget, "_counter", None)
                progress = getattr(widget, "_progress", None)
                if counter:
                    counter.set_count(count)
                if progress:
                    progress.set(min(count / 80, 1.0))

    def update_counter(self, name: str, count: int):
        """单条更新计数器与进度条"""
        for counter in self._counters.get(name, []):
            counter.set_count(count)
        for section in self._season_sections:
            for widget in section["body_frame"].winfo_children():
                if getattr(widget, "_spirit_name", None) == name:
                    progress = getattr(widget, "_progress", None)
                    if progress:
                        progress.set(min(count / 80, 1.0))

    # ──────────────────── 内部方法 ────────────────────

    def _select(self, name: str, row: ctk.CTkFrame):
        """选中一行，清除其他所有赛季的选中状态"""
        for section in self._season_sections:
            for widget in section["body_frame"].winfo_children():
                if hasattr(widget, "_selected"):
                    widget.configure(fg_color="transparent")
                    try:
                        del widget._selected  # type: ignore
                    except AttributeError:
                        pass
        row.configure(fg_color=("gray85", "gray25"))
        row._selected = True  # type: ignore
        self._selected = name
        self._selected_season = getattr(row, "_season", "")

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

    def _do_shiny(self):
        if not self._selected:
            return
        beep()
        if self._on_change:
            self._on_change("shiny", self._selected, self._selected_season)
