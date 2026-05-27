"""随机池卡片 —— 单个计数 + 精灵名称输入"""
import customtkinter as ctk

from src.ui.components.counter_display import CounterDisplay
from src.utils.beep import beep


class RandomPoolCard(ctk.CTkFrame):
    """随机池：一个计数器 + 精灵名称输入 + 增/减/重置"""

    def __init__(self, master, on_change=None, **kwargs):
        super().__init__(master, **kwargs)
        self._on_change = on_change

        # 标题
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(
            header, text="随机池",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).pack(side="left")

        # 计数显示
        self._counter = CounterDisplay(self)
        self._counter.pack(pady=(0, 8))

        # 精灵名称输入
        name_frame = ctk.CTkFrame(self, fg_color="transparent")
        name_frame.pack(pady=(0, 8))

        ctk.CTkLabel(name_frame, text="精灵名称：").pack(side="left", padx=(0, 4))
        self._name_entry = ctk.CTkEntry(name_frame, width=180, placeholder_text="可选")
        self._name_entry.pack(side="left")
        self._name_entry.bind("<Return>", lambda e: self._do_increase())

        # 按钮行
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 12))

        ctk.CTkButton(btn_frame, text="＋ 增加", width=90, command=self._do_increase).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="－ 减少", width=90, command=self._do_decrease).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_frame, text="重置", width=70,
            fg_color="#e74c3c", hover_color="#c0392b",
            command=self._do_reset,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_frame, text="出异色了！", width=100,
            fg_color="#f39c12", hover_color="#d68910",
            command=self._do_shiny,
        ).pack(side="left", padx=4)

    # ── 外部调用 ──

    def set_count(self, count: int):
        self._counter.set_count(count)

    def get_name(self) -> str:
        return self._name_entry.get().strip()

    def clear_name(self):
        self._name_entry.delete(0, "end")

    # ── 内部操作 ──

    def _do_increase(self):
        beep()
        if self._on_change:
            self._on_change("increase")
        # 仅在有内容时清空，避免清空后 placeholder 消失
        if self._name_entry.get().strip():
            self.clear_name()

    def _do_decrease(self):
        beep()
        if self._on_change:
            self._on_change("decrease")

    def _do_reset(self):
        from src.ui.dialogs.confirm_dialog import ConfirmDialog
        dialog = ConfirmDialog(self.winfo_toplevel(), "确认重置", "确定要重置随机池的保底计数吗？")
        if dialog.result:
            beep()
            if self._on_change:
                self._on_change("reset")

    def _do_shiny(self):
        beep()
        if self._on_change:
            self._on_change("shiny")
