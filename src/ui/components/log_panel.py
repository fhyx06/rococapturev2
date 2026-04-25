"""日志面板组件"""
import customtkinter as ctk

from src.models.constants import POOL_RANDOM, POOL_FAMILY, POOL_ELEMENT


class LogPanel(ctk.CTkFrame):
    """操作日志面板 —— 展示最近的操作记录"""

    # 日志池子类型 → 显示前缀
    _pool_labels = {
        POOL_RANDOM: "[随机]",
        POOL_FAMILY: "[家族]",
        POOL_ELEMENT: "[属性]",
    }

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # 标题栏
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 4))

        ctk.CTkLabel(
            header, text="操作日志",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left")

        # 过滤按钮
        self._filter_var = ctk.StringVar(value="all")
        filter_frame = ctk.CTkSegmentedButton(
            header,
            values=["全部", "随机池", "家族池", "属性池"],
            variable=self._filter_var,
            command=self._on_filter_change,
            width=300,
        )
        filter_frame.pack(side="right")

        # 日志文本区域 width：日志区域宽度
        self._text = ctk.CTkTextbox(self, height=180, width=450, state="disabled",
                                     font=ctk.CTkFont(size=13, family="Consolas"))
        self._text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._all_lines: list[str] = []
        self._all_tags: list[str] = []  # 每行对应的pool_type

    # ── 外部调用 ──

    def add_log(self, display_text: str, pool_type: str):
        """新增一条日志"""
        icon = self._pool_labels.get(pool_type, "[其他]")
        line = f"{icon} {display_text}"
        self._all_lines.append(line)
        self._all_tags.append(pool_type)
        self._refresh_display()

    def load_logs(self, display_texts: list[str], pool_types: list[str]):
        """批量加载日志（初始化时）"""
        self._all_lines.clear()
        self._all_tags.clear()
        for text, tag in zip(display_texts, pool_types):
            icon = self._pool_labels.get(tag, "📌")
            self._all_lines.append(f"{icon} {text}")
            self._all_tags.append(tag)
        self._refresh_display()

    def clear_logs(self):
        self._all_lines.clear()
        self._all_tags.clear()
        self._refresh_display()

    # ── 内部方法 ──

    def _on_filter_change(self, value: str):
        self._refresh_display()

    def _refresh_display(self):
        filter_map = {
            "全部": None,
            "随机池": POOL_RANDOM,
            "家族池": POOL_FAMILY,
            "属性池": POOL_ELEMENT,
        }
        pool_filter = filter_map.get(self._filter_var.get())

        self._text.configure(state="normal")
        self._text.delete("1.0", "end")

        # 倒序显示（最新在上）
        lines_to_show = []
        tags_to_show = []
        for i in range(len(self._all_lines) - 1, -1, -1):
            if pool_filter is None or self._all_tags[i] == pool_filter:
                lines_to_show.append(self._all_lines[i])

        if lines_to_show:
            self._text.insert("1.0", "\n".join(lines_to_show))
        self._text.configure(state="disabled")
