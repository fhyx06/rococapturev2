"""异色记录弹窗"""
import customtkinter as ctk

from src.assets.icon_loader import get_latest_season, load_element_icon, load_seasons
from src.models.constants import ELEMENTS, POOL_ELEMENT, POOL_FAMILY, POOL_RANDOM, POOL_UNKNOWN


POOL_DISPLAY = {
    POOL_RANDOM: "随机池",
    POOL_FAMILY: "家族池",
    POOL_ELEMENT: "属性池",
    POOL_UNKNOWN: "我不记得了",
}


def _spirit_display(spirit: dict) -> str:
    return f"No.{int(spirit['no']):03d} {spirit['name']}"


def _primary_element(spirit: dict) -> str:
    elements = spirit.get("elements", [])
    if isinstance(elements, list) and elements:
        return str(elements[0])
    return ""


class ShinySpiritDialog(ctk.CTkToplevel):
    """快捷记录异色时使用的确认弹窗"""

    def __init__(
        self,
        parent,
        title: str,
        pool_type: str,
        pity_count: int,
        fixed_spirit: str = "",
        fixed_season: str = "",
        element: str = "",
    ):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.result: dict | None = None
        self._pool_type = pool_type
        self._pity_count = pity_count
        self._fixed_spirit = fixed_spirit
        self._fixed_season = fixed_season
        self._element = element
        self._seasons = load_seasons()
        self._season_by_id = {str(s.get("season", "")): s for s in self._seasons}
        self._icon_refs: list = []

        self.grab_set()
        self.transient(parent)
        self.geometry(
            f"+{parent.winfo_rootx() + parent.winfo_width() // 2 - 180}"
            f"+{parent.winfo_rooty() + parent.winfo_height() // 2 - 140}"
        )

        frame = ctk.CTkFrame(self)
        frame.pack(padx=20, pady=20, fill="both", expand=True)

        ctk.CTkLabel(
            frame,
            text=f"{POOL_DISPLAY.get(pool_type, pool_type)} 出异色记录",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(frame, text=f"当前保底数：{pity_count}", anchor="w").pack(fill="x", pady=3)
        if element:
            element_row = ctk.CTkFrame(frame, fg_color="transparent")
            element_row.pack(fill="x", pady=3)
            ctk.CTkLabel(element_row, text="属性：", anchor="w").pack(side="left")
            icon = load_element_icon(element, size=20)
            if icon:
                self._icon_refs.append(icon)
                ctk.CTkLabel(element_row, image=icon, text="", width=24).pack(side="left")
            ctk.CTkLabel(element_row, text=element, anchor="w").pack(side="left")

        if fixed_spirit:
            season_text = fixed_season or "未知赛季"
            ctk.CTkLabel(frame, text=f"赛季：{season_text}", anchor="w").pack(fill="x", pady=3)
            ctk.CTkLabel(frame, text=f"精灵：{fixed_spirit}", anchor="w").pack(fill="x", pady=3)
        else:
            self._build_spirit_picker(frame)

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=(14, 0))
        ctk.CTkButton(btn_frame, text="取消", width=80, command=self._on_cancel).pack(side="left", padx=5)
        ctk.CTkButton(
            btn_frame,
            text="记录并清空",
            width=110,
            fg_color="#f39c12",
            hover_color="#d68910",
            command=self._on_confirm,
        ).pack(side="left", padx=5)

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_window()

    def _build_spirit_picker(self, parent):
        latest = get_latest_season()
        season_values = [str(s.get("season", "")) for s in self._seasons] or [""]
        default_season = str(latest.get("season", "")) if latest else season_values[0]

        ctk.CTkLabel(parent, text="赛季：", anchor="w").pack(fill="x", pady=(8, 2))
        self._season_menu = ctk.CTkOptionMenu(parent, values=season_values, command=self._on_season_change)
        self._season_menu.pack(fill="x")
        self._season_menu.set(default_season)

        ctk.CTkLabel(parent, text="出货精灵：", anchor="w").pack(fill="x", pady=(8, 2))
        self._spirit_menu = ctk.CTkOptionMenu(parent, values=[""])
        self._spirit_menu.pack(fill="x")
        self._refresh_spirit_values(default_season)

    def _on_season_change(self, season_id: str):
        self._refresh_spirit_values(season_id)

    def _refresh_spirit_values(self, season_id: str):
        season = self._season_by_id.get(season_id, {})
        spirits = season.get("spirits", [])
        if self._pool_type == POOL_ELEMENT and self._element:
            spirits = [
                spirit
                for spirit in spirits
                if _primary_element(spirit) == self._element
            ]
        values = [_spirit_display(spirit) for spirit in spirits] or [""]
        self._spirit_menu.configure(values=values)
        self._spirit_menu.set(values[0])

    def _on_confirm(self):
        if self._fixed_spirit:
            season = self._fixed_season
            spirit = self._fixed_spirit
        else:
            season = self._season_menu.get()
            spirit = self._spirit_menu.get()
        if not spirit:
            return
        self.result = {
            "pool_type": self._pool_type,
            "season": season,
            "spirit_name": spirit,
            "element": self._element,
            "pity_count": self._pity_count,
            "reset_after_record": True,
        }
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()


class ManualShinyDialog(ctk.CTkToplevel):
    """异色明细页的手动补录弹窗"""

    _pool_value_map = {value: key for key, value in POOL_DISPLAY.items()}

    def __init__(
        self,
        parent,
        random_count: int,
        family_pool: dict[str, int],
        element_pool: dict[str, int],
    ):
        super().__init__(parent)
        self.title("手动添加异色记录")
        self.resizable(False, False)
        self.result: dict | None = None
        self._random_count = random_count
        self._family_pool = family_pool
        self._element_pool = element_pool
        self._seasons = load_seasons()
        self._season_by_id = {str(s.get("season", "")): s for s in self._seasons}
        self._element_icon_ref = None

        self.grab_set()
        self.transient(parent)
        self.geometry(
            f"+{parent.winfo_rootx() + parent.winfo_width() // 2 - 190}"
            f"+{parent.winfo_rooty() + parent.winfo_height() // 2 - 190}"
        )

        frame = ctk.CTkFrame(self)
        frame.pack(padx=20, pady=20, fill="both", expand=True)

        ctk.CTkLabel(
            frame,
            text="手动添加异色记录",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(frame, text="出货池子：", anchor="w").pack(fill="x", pady=(4, 2))
        self._pool_menu = ctk.CTkOptionMenu(
            frame,
            values=list(POOL_DISPLAY.values()),
            command=lambda _: self._on_pool_change(),
        )
        self._pool_menu.pack(fill="x")
        self._pool_menu.set(POOL_DISPLAY[POOL_RANDOM])

        latest = get_latest_season()
        season_values = [str(s.get("season", "")) for s in self._seasons] or [""]
        default_season = str(latest.get("season", "")) if latest else season_values[0]

        ctk.CTkLabel(frame, text="赛季：", anchor="w").pack(fill="x", pady=(8, 2))
        self._season_menu = ctk.CTkOptionMenu(frame, values=season_values, command=self._on_season_change)
        self._season_menu.pack(fill="x")
        self._season_menu.set(default_season)

        ctk.CTkLabel(frame, text="出货精灵：", anchor="w").pack(fill="x", pady=(8, 2))
        self._spirit_menu = ctk.CTkOptionMenu(
            frame,
            values=[""],
            command=lambda _: self._refresh_pity_default(),
        )
        self._spirit_menu.pack(fill="x")

        self._element_label = ctk.CTkLabel(frame, text="属性：", anchor="w")
        self._element_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self._element_icon_label = ctk.CTkLabel(self._element_frame, text="", width=28)
        self._element_icon_label.pack(side="left")
        self._element_menu = ctk.CTkOptionMenu(
            self._element_frame,
            values=ELEMENTS,
            command=lambda _: self._on_element_change(),
        )
        self._element_menu.pack(side="left", fill="x", expand=True)
        self._element_menu.set(ELEMENTS[0])

        self._pity_label = ctk.CTkLabel(frame, text="保底数：", anchor="w")
        self._pity_label.pack(fill="x", pady=(8, 2))
        self._pity_entry = ctk.CTkEntry(frame, width=120)
        self._pity_entry.pack(fill="x")

        self._reset_var = ctk.IntVar(value=1)
        self._reset_check = ctk.CTkCheckBox(frame, text="记录后清空对应保底", variable=self._reset_var)
        self._reset_check.pack(anchor="w", pady=(10, 0))

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=(14, 0))
        ctk.CTkButton(btn_frame, text="取消", width=80, command=self._on_cancel).pack(side="left", padx=5)
        ctk.CTkButton(
            btn_frame,
            text="添加",
            width=80,
            fg_color="#f39c12",
            hover_color="#d68910",
            command=self._on_confirm,
        ).pack(side="left", padx=5)

        self._refresh_spirit_values(default_season)
        self._on_pool_change()

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_window()

    def _on_season_change(self, season_id: str):
        self._refresh_spirit_values(season_id)
        self._refresh_pity_default()

    def _on_element_change(self):
        self._update_element_icon()
        self._refresh_spirit_values(self._season_menu.get())
        self._refresh_pity_default()

    def _refresh_spirit_values(self, season_id: str):
        season = self._season_by_id.get(season_id, {})
        spirits = season.get("spirits", [])
        pool_type = self._pool_value_map.get(self._pool_menu.get(), POOL_RANDOM)
        if pool_type == POOL_ELEMENT:
            element = self._element_menu.get()
            spirits = [
                spirit
                for spirit in spirits
                if _primary_element(spirit) == element
            ]
        values = [_spirit_display(spirit) for spirit in spirits] or [""]
        self._spirit_menu.configure(values=values)
        self._spirit_menu.set(values[0])

    def _on_pool_change(self):
        pool_type = self._pool_value_map.get(self._pool_menu.get(), POOL_RANDOM)
        if pool_type == POOL_ELEMENT:
            self._element_label.pack(fill="x", pady=(8, 2), before=self._pity_label)
            self._element_frame.pack(fill="x", before=self._pity_label)
            self._update_element_icon()
        else:
            self._element_label.pack_forget()
            self._element_frame.pack_forget()

        if pool_type == POOL_UNKNOWN:
            self._reset_var.set(0)
            self._reset_check.configure(state="disabled")
        else:
            self._reset_check.configure(state="normal")
            self._reset_var.set(1)
        self._refresh_spirit_values(self._season_menu.get())
        self._refresh_pity_default()

    def _update_element_icon(self):
        icon = load_element_icon(self._element_menu.get(), size=22)
        self._element_icon_ref = icon
        if icon:
            self._element_icon_label.configure(image=icon, text="")
        else:
            self._element_icon_label.configure(image=None, text="")

    def _refresh_pity_default(self):
        pool_type = self._pool_value_map.get(self._pool_menu.get(), POOL_RANDOM)
        if pool_type == POOL_RANDOM:
            count = self._random_count
        elif pool_type == POOL_FAMILY:
            count = self._family_pool.get(self._spirit_menu.get(), 0)
        elif pool_type == POOL_ELEMENT:
            count = self._element_pool.get(self._element_menu.get(), 0)
        else:
            count = 0
        self._pity_entry.delete(0, "end")
        self._pity_entry.insert(0, str(count))

    def _on_confirm(self):
        spirit = self._spirit_menu.get()
        if not spirit:
            return
        try:
            pity_count = max(0, int(self._pity_entry.get().strip() or 0))
        except ValueError:
            return
        pool_type = self._pool_value_map.get(self._pool_menu.get(), POOL_RANDOM)
        self.result = {
            "pool_type": pool_type,
            "season": self._season_menu.get(),
            "spirit_name": spirit,
            "element": self._element_menu.get() if pool_type == POOL_ELEMENT else "",
            "pity_count": pity_count,
            "reset_after_record": bool(self._reset_var.get()) if pool_type != POOL_UNKNOWN else False,
        }
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()
