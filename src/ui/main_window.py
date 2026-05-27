"""主窗口 —— 整合三个池子、日志面板、存档管理"""
import os
from PIL import Image, ImageTk
import customtkinter as ctk

from src.models.save_slot import SaveSlot
from src.models.constants import (
    ELEMENTS,
    POOL_RANDOM, POOL_FAMILY, POOL_ELEMENT, POOL_UNKNOWN,
)
from src.services.save_service import SaveService
from src.ui.components.random_pool_card import RandomPoolCard
from src.ui.components.family_pool_card import FamilyPoolCard
from src.ui.components.element_pool_card import ElementPoolCard
from src.ui.components.log_panel import LogPanel
from src.ui.components.shiny_detail_panel import ShinyDetailPanel
from src.ui.dialogs.confirm_dialog import ConfirmDialog, CreateSaveDialog
from src.ui.dialogs.shiny_dialog import ManualShinyDialog, ShinySpiritDialog


class MainWindow(ctk.CTk):
    def __init__(self, save_service: SaveService):
        super().__init__()
        self._save_svc = save_service

        self.title("RocoCaptureV2 — 洛克王国异色保底追踪")
        self.geometry("1100x820")
        self.minsize(920, 700)


        # 窗口图标（左上角 + 任务栏）
        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "app_icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
            # wm_iconphoto 修复 Windows 任务栏不显示自定义图标的问题
            img = Image.open(icon_path)
            self._icon_photo = ImageTk.PhotoImage(img.resize((32, 32), Image.LANCZOS))
            self.wm_iconphoto(False, self._icon_photo)

        # ── 顶栏：存档选择 ──
        self._build_top_bar()

        # ── 主体区域 ──
        self._build_body()

        # ── 尝试自动加载 ──
        saves = self._save_svc.list_saves()
        if saves:
            self._switch_save(saves[0])
            self._refresh_save_menu()
        else:
            self._set_empty_state()

    # ────────────────────── 布局构建 ──────────────────────

    def _build_top_bar(self):
        top = ctk.CTkFrame(self, height=50)
        top.pack(fill="x", padx=10, pady=(10, 5))
        top.pack_propagate(False)

        # 存档选择器
        ctk.CTkLabel(top, text="存档：", font=ctk.CTkFont(size=13)).pack(side="left", padx=(8, 4))

        self._save_menu = ctk.CTkOptionMenu(top, values=[""], command=self._on_save_selected)
        self._save_menu.pack(side="left", padx=(0, 6))
        self._save_menu.set("")

        ctk.CTkButton(top, text="新建", width=56, command=self._create_save).pack(side="left", padx=2)
        ctk.CTkButton(
            top, text="删除", width=56,
            fg_color="#95a5a6", hover_color="#7f8c8d",
            command=self._delete_save,
        ).pack(side="left", padx=2)

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # 左侧：三个池子（Tab 切换）
        left = ctk.CTkFrame(body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 5))

        self._tabview = ctk.CTkTabview(left)
        self._tabview.pack(fill="both", expand=True, padx=5, pady=5)

        tab_random = self._tabview.add("随机池")
        tab_family = self._tabview.add("家族池")
        tab_element = self._tabview.add("属性池")
        tab_shiny = self._tabview.add("异色明细")

        self._random_card = RandomPoolCard(tab_random, on_change=self._on_random_change)
        self._random_card.pack(fill="both", expand=True, padx=5, pady=5)

        self._family_card = FamilyPoolCard(tab_family, on_change=self._on_family_change)
        self._family_card.pack(fill="both", expand=True, padx=5, pady=5)

        self._element_card = ElementPoolCard(tab_element, on_change=self._on_element_change)
        self._element_card.pack(fill="both", expand=True, padx=5, pady=5)

        self._shiny_panel = ShinyDetailPanel(
            tab_shiny,
            on_add=self._manual_add_shiny_record,
            on_delete=self._delete_shiny_record,
        )
        self._shiny_panel.pack(fill="both", expand=True, padx=5, pady=5)

        # 右侧：日志面板
        self._log_panel = LogPanel(body)
        self._log_panel.pack(side="right", fill="both", padx=(5, 0))

    # ────────────────────── 存档管理 ──────────────────────

    def _refresh_save_menu(self):
        saves = self._save_svc.list_saves()
        self._save_menu.configure(values=saves if saves else [""])
        if self._save_svc.current_name:
            self._save_menu.set(self._save_svc.current_name)
        elif saves:
            self._save_menu.set(saves[0])
        else:
            self._save_menu.set("")

    def _on_save_selected(self, name: str):
        if name and name != self._save_svc.current_name:
            self._switch_save(name)

    def _create_save(self):
        existing = self._save_svc.list_saves()
        dialog = CreateSaveDialog(self, existing)
        if dialog.result:
            try:
                self._save_svc.create_save(dialog.result)
                self._refresh_save_menu()
                self._switch_save(dialog.result)
            except Exception as e:
                self._show_error(str(e))

    def _delete_save(self):
        name = self._save_svc.current_name
        if not name:
            return
        # 唯一存档不可删除
        if len(self._save_svc.list_saves()) <= 1:
            self._show_error("至少需要保留一个存档，无法删除。")
            return
        dialog = ConfirmDialog(self, "确认删除存档", f"确定要删除存档「{name}」吗？\n此操作不可撤销。")
        if dialog.result:
            try:
                self._save_svc.delete_save(name)
                self._refresh_save_menu()
                saves = self._save_svc.list_saves()
                if saves:
                    self._switch_save(saves[0])
                    self._refresh_save_menu()
                else:
                    self._set_empty_state()
            except Exception as e:
                self._show_error(str(e))

    def _switch_save(self, name: str):
        try:
            slot = self._save_svc.load_save(name)
            self._load_slot_data(slot)
        except Exception as e:
            self._show_error(str(e))

    # ────────────────────── 数据加载 ──────────────────────

    def _load_slot_data(self, slot: SaveSlot):
        # 随机池
        self._random_card.set_count(slot.random_pool)

        # 家族池
        self._family_card.refresh_from_data(slot.family_pool)

        # 属性池
        for elem in ELEMENTS:
            self._element_card.update_counter(elem, slot.element_pool.get(elem, 0))

        # 日志
        display_texts = [log.format_display() for log in slot.logs]
        pool_types = [log.pool_type for log in slot.logs]
        self._log_panel.load_logs(display_texts, pool_types)

        # 异色明细
        self._shiny_panel.load_records(slot.shiny_records)

    def _set_empty_state(self):
        self._random_card.set_count(0)
        self._family_card.refresh_from_data({})
        for elem in ELEMENTS:
            self._element_card.update_counter(elem, 0)
        self._log_panel.clear_logs()
        self._shiny_panel.load_records([])

    # ────────────────────── 池子操作回调 ──────────────────────

    def _on_random_change(self, action: str, *args):
        slot = self._save_svc.current
        if not slot:
            return
        logs = []
        if action == "increase":
            name = self._random_card.get_name() or ""
            logs = slot.random_increase(name)
        elif action == "decrease":
            logs = slot.random_decrease()
        elif action == "reset":
            logs = slot.random_reset()
        elif action == "shiny":
            self._record_random_shiny(slot)
            return

        # 随机池计数实时刷新
        self._random_card.set_count(slot.random_pool)
        self._after_operation(slot, logs)

    def _on_family_change(self, action: str, spirit_name: str = "", season: str = ""):
        slot = self._save_svc.current
        if not slot:
            return
        logs = []
        if action == "increase":
            logs = slot.family_increase(spirit_name)
            self._family_card.update_counter(spirit_name, slot.family_pool.get(spirit_name, 0))
        elif action == "decrease":
            logs = slot.family_decrease(spirit_name)
            self._family_card.update_counter(spirit_name, slot.family_pool.get(spirit_name, 0))
        elif action == "reset":
            logs = slot.family_reset(spirit_name)
            self._family_card.update_counter(spirit_name, 0)
        elif action == "shiny":
            self._record_family_shiny(slot, spirit_name, season)
            return

        self._after_operation(slot, logs)

    def _on_element_change(self, action: str, element: str = ""):
        slot = self._save_svc.current
        if not slot:
            return
        logs = []
        if action == "increase":
            logs = slot.element_increase(element)
        elif action == "decrease":
            logs = slot.element_decrease(element)
        elif action == "reset":
            logs = slot.element_reset(element)
        elif action == "shiny":
            self._record_element_shiny(slot, element)
            return

        self._after_operation(slot, logs)
        self._element_card.update_counter(element, slot.element_pool.get(element, 0))

    def _record_random_shiny(self, slot: SaveSlot):
        dialog = ShinySpiritDialog(
            self,
            "记录随机池异色",
            POOL_RANDOM,
            slot.random_pool,
        )
        if dialog.result:
            self._apply_shiny_record(slot, dialog.result)

    def _record_family_shiny(self, slot: SaveSlot, spirit_name: str, season: str):
        if not spirit_name:
            return
        dialog = ShinySpiritDialog(
            self,
            "记录家族池异色",
            POOL_FAMILY,
            slot.family_pool.get(spirit_name, 0),
            fixed_spirit=spirit_name,
            fixed_season=season,
        )
        if dialog.result:
            self._apply_shiny_record(slot, dialog.result)

    def _record_element_shiny(self, slot: SaveSlot, element: str):
        if not element:
            return
        dialog = ShinySpiritDialog(
            self,
            "记录属性池异色",
            POOL_ELEMENT,
            slot.element_pool.get(element, 0),
            element=element,
        )
        if dialog.result:
            self._apply_shiny_record(slot, dialog.result)

    def _manual_add_shiny_record(self):
        slot = self._save_svc.current
        if not slot:
            return
        dialog = ManualShinyDialog(
            self,
            random_count=slot.random_pool,
            family_pool=slot.family_pool,
            element_pool=slot.element_pool,
        )
        if dialog.result:
            self._apply_shiny_record(slot, dialog.result)

    def _delete_shiny_record(self, index: int):
        slot = self._save_svc.current
        if not slot or index < 0 or index >= len(slot.shiny_records):
            return
        record = slot.shiny_records[index]
        dialog = ConfirmDialog(
            self,
            "确认删除异色记录",
            f"确定要删除「{record.spirit_name or '未知精灵'}」的异色记录吗？",
        )
        if dialog.result and slot.delete_shiny_record(index):
            self._shiny_panel.load_records(slot.shiny_records)
            self._save_svc.save_current()

    def _apply_shiny_record(self, slot: SaveSlot, data: dict):
        pool_type = data.get("pool_type", POOL_UNKNOWN)
        spirit_name = data.get("spirit_name", "")
        season = data.get("season", "")
        element = data.get("element", "")
        pity_count = data.get("pity_count", 0)
        reset_after_record = data.get("reset_after_record", True)

        log = slot.add_shiny_record(
            pool_type=pool_type,
            spirit_name=spirit_name,
            pity_count=pity_count,
            season=season,
            element=element,
            reset_after_record=reset_after_record,
        )

        if reset_after_record:
            if pool_type == POOL_RANDOM:
                slot.clear_random_pool()
                self._random_card.set_count(slot.random_pool)
            elif pool_type == POOL_FAMILY:
                slot.clear_family_pool(spirit_name)
                self._family_card.update_counter(spirit_name, slot.family_pool.get(spirit_name, 0))
            elif pool_type == POOL_ELEMENT:
                slot.clear_element_pool(element)
                self._element_card.update_counter(element, slot.element_pool.get(element, 0))

        self._log_panel.add_log(log.format_display(), log.pool_type)
        self._shiny_panel.load_records(slot.shiny_records)
        self._save_svc.save_current()

    def _after_operation(self, slot: SaveSlot, logs):
        """操作后统一更新：日志、持久化"""
        if logs:
            for log in logs:
                self._log_panel.add_log(log.format_display(), log.pool_type)
        self._save_svc.save_current()

    # ── 辅助 ──

    def _show_error(self, message: str):
        dialog = ctk.CTkToplevel(self)
        dialog.title("错误")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry(f"+{self.winfo_rootx() + 200}+{self.winfo_rooty() + 200}")
        ctk.CTkLabel(dialog, text=message, text_color="#e74c3c").pack(padx=20, pady=15)
        ctk.CTkButton(dialog, text="确定", width=80, command=dialog.destroy).pack(pady=(0, 15))
