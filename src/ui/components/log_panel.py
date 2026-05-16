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

    # 日志颜色：
    _pool_colors = {
        POOL_FAMILY: "#A9B7C6",
        POOL_RANDOM: "#5DADE2",
        POOL_ELEMENT: "#58D68D",
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

        # 配置颜色 tag（兼容不同 CustomTkinter 版本）
        tb = self._get_textbox()
        for tag_name, color in (("family", "#A9B7C6"), ("random", "#5DADE2"), ("element", "#58D68D")):
            tb.tag_config(tag_name, foreground=color)

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

    def _get_textbox(self):
        """安全获取 CTkTextbox 底层的 Tkinter Text 组件（兼容不同版本）"""
        for attr in ("_text_box", "_textbox"):
            if hasattr(self._text, attr):
                return getattr(self._text, attr)
        raise RuntimeError("无法获取 CTkTextbox 底层 Text 组件，CustomTkinter 版本不兼容")

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

        tb = self._get_textbox()
        tb.configure(state="normal")
        tb.delete("1.0", "end")

        # 倒序显示（最新在上），插入时直接带颜色 tag
        tag_map = {
            POOL_FAMILY: "family",
            POOL_RANDOM: "random",
            POOL_ELEMENT: "element",
        }
        for i in range(len(self._all_lines) - 1, -1, -1):
            if pool_filter is not None and self._all_tags[i] != pool_filter:
                continue
            line = self._all_lines[i]
            tag_name = tag_map.get(self._all_tags[i])
            if tag_name:
                tb.insert("end", line + "\n", (tag_name,))
            else:
                tb.insert("end", line + "\n")

        tb.configure(state="disabled")
