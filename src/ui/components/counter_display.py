"""带预警颜色的计数显示组件"""
import customtkinter as ctk
from src.models.constants import PITY_MAX, PITY_WARN_THRESHOLD, COLOR_NORMAL, COLOR_WARN, COLOR_CRITICAL


class CounterDisplay(ctk.CTkLabel):
    """显示保底计数，根据阈值自动变色"""

    def __init__(self, master, font=None, **kwargs):
        if font is None:
            font = ctk.CTkFont(size=28, weight="bold")
        super().__init__(master, text="0", font=font, **kwargs)
        self._count = 0

    def set_count(self, count: int):
        self._count = count
        self.configure(text=str(count))
        self._apply_color()

    def _apply_color(self):
        if self._count >= PITY_MAX:
            self.configure(text_color=COLOR_CRITICAL)
        elif self._count >= PITY_WARN_THRESHOLD:
            self.configure(text_color=COLOR_WARN)
        else:
            self.configure(text_color=COLOR_NORMAL)
