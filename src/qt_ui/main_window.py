"""PySide6 主窗口 —— 复现现有核心功能的试验版。"""
from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from src.utils.beep import beep

from src.assets.icon_loader import get_latest_season, load_seasons
from src.models.constants import (
    COLOR_CRITICAL,
    COLOR_WARN,
    ELEMENTS,
    POOL_ELEMENT,
    POOL_FAMILY,
    POOL_RANDOM,
    POOL_UNKNOWN,
    PITY_MAX,
    PITY_WARN_THRESHOLD,
)
from src.models.save_slot import ActivityLog, SaveSlot, ShinyRecord
from src.services.save_service import SaveService


ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
SPIRITS_DIR = ASSETS_DIR / "spirits"


def spirit_display(spirit: dict) -> str:
    return f"No.{int(spirit['no']):03d} {spirit['name']}"


def primary_element(spirit: dict) -> str:
    elements = spirit.get("elements", [])
    if isinstance(elements, list) and elements:
        return str(elements[0])
    return ""


def element_icon(element: str) -> QIcon:
    path = ICONS_DIR / f"{element}.png"
    return QIcon(str(path)) if path.exists() else QIcon()


def spirit_icon(spirit_name: str, season: str = "") -> QIcon:
    lookup = spirit_name.strip()
    if re.match(r"^No\.\d+\s+", lookup):
        lookup = re.sub(r"^No\.\d+\s+", "", lookup)
    search_dirs = []
    if season:
        search_dirs.append(SPIRITS_DIR / season)
    search_dirs.append(SPIRITS_DIR)
    for directory in search_dirs:
        if not directory.is_dir():
            continue
        for path in directory.iterdir():
            if path.suffix.lower() == ".png" and path.stem.endswith(lookup):
                return QIcon(str(path))
    return QIcon()


class ShinyChoiceDialog(QDialog):
    """快捷出货记录弹窗。"""

    def __init__(
        self,
        parent: QWidget,
        pool_type: str,
        pity_count: int,
        fixed_spirit: str = "",
        fixed_season: str = "",
        element: str = "",
    ):
        super().__init__(parent)
        self.setWindowTitle("记录异色")
        self._pool_type = pool_type
        self._pity_count = pity_count
        self._fixed_spirit = fixed_spirit
        self._fixed_season = fixed_season
        self._element = element
        self._seasons = load_seasons()
        self._season_by_id = {str(item.get("season", "")): item for item in self._seasons}
        self.result_data: dict | None = None

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("当前保底", QLabel(str(pity_count)))
        if element:
            element_row = QWidget()
            element_layout = QHBoxLayout(element_row)
            element_layout.setContentsMargins(0, 0, 0, 0)
            icon_label = QLabel()
            icon_label.setPixmap(element_icon(element).pixmap(20, 20))
            element_layout.addWidget(icon_label)
            element_layout.addWidget(QLabel(element))
            element_layout.addStretch()
            form.addRow("属性", element_row)

        if fixed_spirit:
            form.addRow("赛季", QLabel(fixed_season or "未知赛季"))
            form.addRow("精灵", QLabel(fixed_spirit))
        else:
            self.season_combo = QComboBox()
            for season in self._seasons:
                self.season_combo.addItem(str(season.get("season", "")))
            latest = get_latest_season()
            if latest:
                self.season_combo.setCurrentText(str(latest.get("season", "")))
            self.season_combo.currentTextChanged.connect(self._refresh_spirits)
            form.addRow("赛季", self.season_combo)

            self.spirit_combo = QComboBox()
            form.addRow("精灵", self.spirit_combo)
            self._refresh_spirits(self.season_combo.currentText())

        layout.addLayout(form)
        buttons = QHBoxLayout()
        cancel = QPushButton("取消")
        ok = QPushButton("记录并清空")
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self._accept)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        layout.addLayout(buttons)

    def _refresh_spirits(self, season_id: str) -> None:
        if not hasattr(self, "spirit_combo"):
            return
        self.spirit_combo.clear()
        season = self._season_by_id.get(season_id, {})
        spirits = season.get("spirits", [])
        if self._pool_type == POOL_ELEMENT and self._element:
            spirits = [item for item in spirits if primary_element(item) == self._element]
        for spirit in spirits:
            self.spirit_combo.addItem(spirit_icon(spirit["name"], season_id), spirit_display(spirit))

    def _accept(self) -> None:
        if self._fixed_spirit:
            season = self._fixed_season
            spirit = self._fixed_spirit
        else:
            season = self.season_combo.currentText()
            spirit = self.spirit_combo.currentText()
        if not spirit:
            return
        self.result_data = {
            "pool_type": self._pool_type,
            "season": season,
            "spirit_name": spirit,
            "element": self._element,
            "pity_count": self._pity_count,
            "reset_after_record": True,
        }
        self.accept()


class ManualShinyDialog(QDialog):
    """异色明细页手动补录。"""

    _pool_labels = {
        POOL_RANDOM: "随机池",
        POOL_FAMILY: "家族池",
        POOL_ELEMENT: "属性池",
        POOL_UNKNOWN: "我不记得了",
    }

    def __init__(self, parent: QWidget, slot: SaveSlot):
        super().__init__(parent)
        self.setWindowTitle("手动添加异色记录")
        self._slot = slot
        self._seasons = load_seasons()
        self._season_by_id = {str(item.get("season", "")): item for item in self._seasons}
        self.result_data: dict | None = None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.pool_combo = QComboBox()
        for key, label in self._pool_labels.items():
            self.pool_combo.addItem(label, key)
        self.pool_combo.currentIndexChanged.connect(lambda _: self._on_pool_changed())
        form.addRow("池子", self.pool_combo)

        self.season_combo = QComboBox()
        for season in self._seasons:
            self.season_combo.addItem(str(season.get("season", "")))
        latest = get_latest_season()
        if latest:
            self.season_combo.setCurrentText(str(latest.get("season", "")))
        self.season_combo.currentTextChanged.connect(self._refresh_spirits)
        form.addRow("赛季", self.season_combo)

        self.element_combo = QComboBox()
        for element in ELEMENTS:
            self.element_combo.addItem(element_icon(element), element)
        self.element_combo.currentTextChanged.connect(lambda _: self._on_element_changed())
        form.addRow("属性", self.element_combo)

        self.spirit_combo = QComboBox()
        self.spirit_combo.currentIndexChanged.connect(lambda _: self._refresh_pity())
        form.addRow("精灵", self.spirit_combo)

        self.pity_spin = QSpinBox()
        self.pity_spin.setRange(0, 999)
        form.addRow("保底数", self.pity_spin)

        self.reset_check = QCheckBox("记录后清空对应保底")
        self.reset_check.setChecked(True)
        form.addRow("", self.reset_check)

        layout.addLayout(form)
        buttons = QHBoxLayout()
        cancel = QPushButton("取消")
        ok = QPushButton("添加")
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self._accept)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        layout.addLayout(buttons)

        self._refresh_spirits(self.season_combo.currentText())
        self._on_pool_changed()

    def _on_pool_changed(self) -> None:
        pool_type = self.pool_combo.currentData()
        self.element_combo.setEnabled(pool_type == POOL_ELEMENT)
        self.reset_check.setEnabled(pool_type != POOL_UNKNOWN)
        self.reset_check.setChecked(pool_type != POOL_UNKNOWN)
        self._refresh_spirits(self.season_combo.currentText())
        self._refresh_pity()

    def _on_element_changed(self) -> None:
        self._refresh_spirits(self.season_combo.currentText())
        self._refresh_pity()

    def _refresh_spirits(self, season_id: str) -> None:
        self.spirit_combo.blockSignals(True)
        self.spirit_combo.clear()
        season = self._season_by_id.get(season_id, {})
        spirits = season.get("spirits", [])
        if self.pool_combo.currentData() == POOL_ELEMENT:
            element = self.element_combo.currentText()
            spirits = [item for item in spirits if primary_element(item) == element]
        for spirit in spirits:
            self.spirit_combo.addItem(spirit_icon(spirit["name"], season_id), spirit_display(spirit))
        self.spirit_combo.blockSignals(False)
        self._refresh_pity()

    def _refresh_pity(self) -> None:
        pool_type = self.pool_combo.currentData()
        if pool_type == POOL_RANDOM:
            count = self._slot.random_pool
        elif pool_type == POOL_FAMILY:
            count = self._slot.family_pool.get(self.spirit_combo.currentText(), 0)
        elif pool_type == POOL_ELEMENT:
            count = self._slot.element_pool.get(self.element_combo.currentText(), 0)
        else:
            count = 0
        self.pity_spin.setValue(count)

    def _accept(self) -> None:
        pool_type = self.pool_combo.currentData()
        spirit = self.spirit_combo.currentText()
        if not spirit:
            return
        self.result_data = {
            "pool_type": pool_type,
            "season": self.season_combo.currentText(),
            "spirit_name": spirit,
            "element": self.element_combo.currentText() if pool_type == POOL_ELEMENT else "",
            "pity_count": self.pity_spin.value(),
            "reset_after_record": self.reset_check.isChecked() if pool_type != POOL_UNKNOWN else False,
        }
        self.accept()


class QtMainWindow(QMainWindow):
    """Qt 试验版主窗口。"""

    def __init__(self, save_service: SaveService):
        super().__init__()
        self._save_svc = save_service
        self._family_items: dict[str, list[QTreeWidgetItem]] = {}
        self._element_items: dict[str, QListWidgetItem] = {}

        # 保底临界闪烁定时器
        self._flash_timer = QTimer(self)
        self._flash_timer.timeout.connect(self._toggle_flash)
        self._flash_on = False

        self.setWindowTitle("RocoCaptureV2 Qt 试验版")
        icon_path = ICONS_DIR / "app_icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._build_ui()
        saves = self._save_svc.list_saves()
        if saves:
            self._switch_save(saves[0])
        self._refresh_save_combo()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)

        top = QHBoxLayout()
        top.addWidget(QLabel("存档"))
        self.save_combo = QComboBox()
        self.save_combo.currentTextChanged.connect(self._on_save_selected)
        top.addWidget(self.save_combo, 1)
        new_btn = QPushButton("新建")
        delete_btn = QPushButton("删除")
        new_btn.clicked.connect(self._create_save)
        delete_btn.clicked.connect(self._delete_save)
        top.addWidget(new_btn)
        top.addWidget(delete_btn)
        rename_btn = QPushButton("重命名")
        rename_btn.clicked.connect(self._rename_save)
        top.addWidget(rename_btn)
        import_btn = QPushButton("导入")
        import_btn.clicked.connect(self._import_save)
        top.addWidget(import_btn)
        export_btn = QPushButton("导出")
        export_btn.clicked.connect(self._export_save)
        top.addWidget(export_btn)
        root_layout.addLayout(top)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.tabs = QTabWidget()
        self._build_random_tab()
        self._build_family_tab()
        self._build_element_tab()
        self._build_shiny_tab()
        splitter.addWidget(self.tabs)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.log_text.setMinimumWidth(360)
        splitter.addWidget(self.log_text)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        root_layout.addWidget(splitter, 1)

        self.setCentralWidget(root)

    def _build_random_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.random_count = QLabel("0")
        self.random_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.random_count.setStyleSheet("font-size: 48px; font-weight: 700;")
        layout.addWidget(self.random_count)
        self.random_name = QLineEdit()
        self.random_name.setPlaceholderText("精灵名称（可选）")
        self.random_name.returnPressed.connect(self._random_increase)
        layout.addWidget(self.random_name)
        buttons = QHBoxLayout()
        for text, handler in (
            ("增加", self._random_increase),
            ("减少", self._random_decrease),
            ("重置", self._random_reset),
            ("出异色", self._random_shiny),
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        layout.addStretch()
        self.tabs.addTab(tab, "随机池")

    def _build_family_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.family_tree = QTreeWidget()
        self.family_tree.setColumnCount(3)
        self.family_tree.setHeaderLabels(["精灵", "属性", "保底"])
        self.family_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.family_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.family_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.family_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.family_tree, 1)
        buttons = QHBoxLayout()
        for text, handler in (
            ("增加", self._family_increase),
            ("减少", self._family_decrease),
            ("重置", self._family_reset),
            ("出异色", self._family_shiny),
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.tabs.addTab(tab, "家族池")

    def _build_element_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.element_list = QListWidget()
        self.element_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.element_list, 1)
        buttons = QHBoxLayout()
        for text, handler in (
            ("增加", self._element_increase),
            ("减少", self._element_decrease),
            ("重置", self._element_reset),
            ("出异色", self._element_shiny),
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.tabs.addTab(tab, "属性池")

    def _build_shiny_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        top = QHBoxLayout()
        add_btn = QPushButton("手动添加")
        delete_btn = QPushButton("删除选中")
        add_btn.clicked.connect(self._manual_add_shiny)
        delete_btn.clicked.connect(self._delete_selected_shiny)
        top.addStretch()
        top.addWidget(add_btn)
        top.addWidget(delete_btn)
        layout.addLayout(top)

        self.shiny_table = QTableWidget(0, 6)
        self.shiny_table.setHorizontalHeaderLabels(["时间", "池子", "赛季", "精灵", "属性", "保底"])
        self.shiny_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.shiny_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.shiny_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.shiny_table, 1)
        self.tabs.addTab(tab, "异色明细")

    def _refresh_save_combo(self) -> None:
        current = self._save_svc.current_name or ""
        self.save_combo.blockSignals(True)
        self.save_combo.clear()
        self.save_combo.addItems(self._save_svc.list_saves())
        if current:
            self.save_combo.setCurrentText(current)
        self.save_combo.blockSignals(False)

    def _on_save_selected(self, name: str) -> None:
        if name and name != self._save_svc.current_name:
            self._switch_save(name)

    def _switch_save(self, name: str) -> None:
        try:
            slot = self._save_svc.load_save(name)
        except Exception as exc:
            QMessageBox.critical(self, "错误", str(exc))
            return
        self._load_slot(slot)

    def _create_save(self) -> None:
        name, ok = QInputDialogCompat.get_text(self, "新建存档", "存档名称")
        if not ok or not name.strip():
            return
        try:
            self._save_svc.create_save(name.strip())
            beep()
            self._refresh_save_combo()
            self._switch_save(name.strip())
        except Exception as exc:
            QMessageBox.critical(self, "错误", str(exc))

    def _delete_save(self) -> None:
        name = self._save_svc.current_name
        if not name:
            return
        if len(self._save_svc.list_saves()) <= 1:
            QMessageBox.warning(self, "无法删除", "至少需要保留一个存档。")
            return
        reply = QMessageBox.question(self, "确认删除", f"确定删除存档「{name}」吗？")
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self._save_svc.delete_save(name)
            beep()
            saves = self._save_svc.list_saves()
            if saves:
                self._switch_save(saves[0])
            self._refresh_save_combo()
        except Exception as exc:
            QMessageBox.critical(self, "错误", str(exc))

    def _rename_save(self) -> None:
        """重命名当前存档。"""
        name = self._save_svc.current_name
        if not name:
            QMessageBox.information(self, "提示", "没有可重命名的存档。")
            return
        new_name, ok = QInputDialogCompat.get_text(self, "重命名存档", "新名称：")
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip()
        if new_name == name:
            return
        try:
            self._save_svc.rename_save(name, new_name)
            beep()
            self._refresh_save_combo()
            self._switch_save(new_name)
        except Exception as exc:
            QMessageBox.critical(self, "错误", str(exc))

    def _import_save(self) -> None:
        """从 JSON 文件导入存档。"""
        path, _ = QFileDialog.getOpenFileName(
            self, "导入存档", "", "JSON 文件 (*.json);;所有文件 (*)"
        )
        if not path:
            return
        try:
            slot = self._save_svc.import_save(path)
            beep()
            self._refresh_save_combo()
            self._switch_save(slot.name)
            QMessageBox.information(self, "导入成功", f"已导入存档「{slot.name}」。")
        except Exception as exc:
            QMessageBox.critical(self, "导入失败", str(exc))

    def _export_save(self) -> None:
        """导出当前存档为 JSON 文件。"""
        slot = self._save_svc.current
        if not slot:
            QMessageBox.information(self, "提示", "没有可导出的存档。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出存档", f"{slot.name}.json", "JSON 文件 (*.json);;所有文件 (*)"
        )
        if not path:
            return
        try:
            self._save_svc.export_save(path)
            beep()
            QMessageBox.information(self, "导出成功", f"已导出至：{path}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))

    def _load_slot(self, slot: SaveSlot) -> None:
        self.random_count.setText(str(slot.random_pool))
        self._update_random_counter_color()
        self._load_family_tree(slot)
        self._load_element_list(slot)
        self._load_shiny_records(slot.shiny_records)
        self._load_logs(slot.logs)

    # ---------- 保底颜色 & 闪烁 ----------

    @staticmethod
    def _pity_color(count: int) -> str:
        """根据保底数返回对应的 CSS 颜色值。"""
        if count >= PITY_MAX:
            return COLOR_CRITICAL
        if count >= PITY_WARN_THRESHOLD:
            return COLOR_WARN
        return ""

    def _update_random_counter_color(self) -> None:
        """随机池计数器颜色 + 闪烁控制。"""
        try:
            count = int(self.random_count.text())
        except ValueError:
            count = 0
        color = self._pity_color(count)
        if count >= PITY_MAX:
            if not self._flash_timer.isActive():
                self._flash_timer.start(500)
        else:
            self._flash_timer.stop()
            self.random_count.setStyleSheet(
                f"font-size: 48px; font-weight: 700; color: {color};" if color
                else "font-size: 48px; font-weight: 700;"
            )

    def _toggle_flash(self) -> None:
        """闪烁定时器回调：交替显示红色/默认色。"""
        self._flash_on = not self._flash_on
        try:
            count = int(self.random_count.text())
        except ValueError:
            return
        if count < PITY_MAX:
            self._flash_timer.stop()
            return
        if self._flash_on:
            self.random_count.setStyleSheet(
                f"font-size: 48px; font-weight: 700; color: {COLOR_CRITICAL};"
            )
        else:
            self.random_count.setStyleSheet("font-size: 48px; font-weight: 700;")

    # ---------- 增量 UI 刷新（避免全量重建延迟） ----------

    def _update_random_display(self, count: int) -> None:
        """增量更新随机池计数器显示。"""
        self.random_count.setText(str(count))
        self._update_random_counter_color()

    def _update_family_display(self, display_name: str, count: int) -> None:
        """增量更新家族池中指定精灵的计数列文本与颜色。"""
        items = self._family_items.get(display_name, [])
        if not items:
            return  # 从未加载过（极端情况），回退全量加载
        for item in items:
            item.setText(2, str(count))
            color = self._pity_color(count)
            if color:
                item.setForeground(2, QColor(color))
            else:
                # 还原默认前景色
                item.setData(2, Qt.ItemDataRole.ForegroundRole, None)

    def _update_element_display(self, element: str, count: int) -> None:
        """增量更新属性池中指定属性的计数字段与颜色。"""
        item = self._element_items.get(element)
        if not item:
            return
        item.setText(f"{element}    {count}")
        color = self._pity_color(count)
        if color:
            item.setForeground(QColor(color))
        else:
            # 还原默认前景色（QListWidgetItem: setData(role, value)，2 个参数）
            item.setData(Qt.ItemDataRole.ForegroundRole, None)

    def _load_family_tree(self, slot: SaveSlot) -> None:
        # 记住哪些赛季节点是展开的 + 当前选中的精灵名称
        expanded_seasons: set[str] = set()
        selected_spirit: str | None = None
        for i in range(self.family_tree.topLevelItemCount()):
            item = self.family_tree.topLevelItem(i)
            if item and item.isExpanded():
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(data, dict) and data.get("is_season"):
                    expanded_seasons.add(item.text(0))
        current = self.family_tree.currentItem()
        if current:
            data = current.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, dict) and not data.get("is_season"):
                selected_spirit = data.get("name")

        self.family_tree.clear()
        self._family_items.clear()
        for season in load_seasons():
            season_id = str(season.get("season", ""))
            top = QTreeWidgetItem([season.get("label", season_id), "", ""])
            top.setData(0, Qt.ItemDataRole.UserRole, {"is_season": True})
            self.family_tree.addTopLevelItem(top)
            for spirit in season.get("spirits", []):
                display_name = spirit_display(spirit)
                elements = spirit.get("elements", [])
                count = slot.family_pool.get(display_name, 0)
                item = QTreeWidgetItem([
                    display_name,
                    "/".join(elements),
                    str(count),
                ])
                item.setIcon(0, spirit_icon(spirit["name"], season_id))
                if elements:
                    item.setIcon(1, element_icon(elements[0]))
                color = self._pity_color(count)
                if color:
                    item.setForeground(2, QColor(color))
                item.setData(0, Qt.ItemDataRole.UserRole, {
                    "is_season": False,
                    "name": display_name,
                    "season": season_id,
                })
                top.addChild(item)
                self._family_items.setdefault(display_name, []).append(item)
            # 恢复展开状态：原来展开的继续保持展开
            top.setExpanded(season.get("label", season_id) in expanded_seasons)
        # 恢复选中精灵
        if selected_spirit and selected_spirit in self._family_items:
            # 选中第一个匹配的 item（同一精灵可能出现在多个赛季）
            items = self._family_items[selected_spirit]
            if items:
                self.family_tree.setCurrentItem(items[0])
                # 确保其父节点展开
                parent = items[0].parent()
                if parent:
                    parent.setExpanded(True)

    def _load_element_list(self, slot: SaveSlot) -> None:
        # 记住当前选中的属性
        selected_element: str | None = None
        item = self.element_list.currentItem()
        if item:
            selected_element = item.data(Qt.ItemDataRole.UserRole)

        self.element_list.clear()
        self._element_items.clear()
        for element in ELEMENTS:
            count = slot.element_pool.get(element, 0)
            item = QListWidgetItem(element_icon(element), f"{element}    {count}")
            color = self._pity_color(count)
            if color:
                item.setForeground(QColor(color))
            item.setData(Qt.ItemDataRole.UserRole, element)
            self.element_list.addItem(item)
            self._element_items[element] = item
            # 恢复选中状态
            if element == selected_element:
                self.element_list.setCurrentItem(item)

    def _load_shiny_records(self, records: list[ShinyRecord]) -> None:
        self.shiny_table.setRowCount(0)
        for index in range(len(records) - 1, -1, -1):
            record = records[index]
            row = self.shiny_table.rowCount()
            self.shiny_table.insertRow(row)
            self.shiny_table.setVerticalHeaderItem(row, QTableWidgetItem(str(index)))
            element = record.element or self._element_for_record(record)
            values = [
                record.timestamp,
                self._pool_label(record.pool_type),
                record.season or "-",
                record.spirit_name or "未知精灵",
                element or "-",
                str(record.pity_count),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 3:
                    item.setIcon(spirit_icon(record.spirit_name, record.season))
                elif col == 4 and element:
                    item.setIcon(element_icon(element))
                self.shiny_table.setItem(row, col, item)

    def _load_logs(self, logs: list[ActivityLog]) -> None:
        lines = [f"[{self._pool_label(log.pool_type)}] {log.format_display()}" for log in reversed(logs)]
        self.log_text.setPlainText("\n".join(lines))

    @staticmethod
    def _pool_label(pool_type: int) -> str:
        mapping = {POOL_RANDOM: "随机", POOL_FAMILY: "家族", POOL_ELEMENT: "属性"}
        return mapping.get(pool_type, "未知")

    def _after_operation(self, logs: list[ActivityLog]) -> None:
        """仅保存存档并刷新日志面板（日志重建极快，不拖性能）。"""
        if not logs:
            return
        self._save_svc.save_current()
        slot = self._save_svc.current
        if slot:
            self._load_logs(slot.logs)

    def _random_increase(self) -> None:
        slot = self._save_svc.current
        if not slot:
            return
        beep()
        logs = slot.random_increase(self.random_name.text().strip())
        self.random_name.clear()
        self._after_operation(logs)
        self._update_random_display(slot.random_pool)

    def _random_decrease(self) -> None:
        slot = self._save_svc.current
        if slot:
            beep()
            self._after_operation(slot.random_decrease())
            self._update_random_display(slot.random_pool)

    def _random_reset(self) -> None:
        slot = self._save_svc.current
        if slot and self._confirm("确定重置随机池吗？"):
            beep()
            self._after_operation(slot.random_reset())
            self._update_random_display(slot.random_pool)

    def _random_shiny(self) -> None:
        slot = self._save_svc.current
        if not slot:
            return
        beep()
        dialog = ShinyChoiceDialog(self, POOL_RANDOM, slot.random_pool)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_data:
            self._apply_shiny_record(dialog.result_data)

    def _selected_family_data(self) -> dict | None:
        item = self.family_tree.currentItem()
        if not item:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("is_season"):
            return None
        return data

    def _family_increase(self) -> None:
        slot = self._save_svc.current
        data = self._selected_family_data()
        if slot and data:
            beep()
            self._after_operation(slot.family_increase(data["name"]))
            self._update_family_display(data["name"], slot.family_pool.get(data["name"], 0))

    def _family_decrease(self) -> None:
        slot = self._save_svc.current
        data = self._selected_family_data()
        if slot and data:
            beep()
            self._after_operation(slot.family_decrease(data["name"]))
            self._update_family_display(data["name"], slot.family_pool.get(data["name"], 0))

    def _family_reset(self) -> None:
        slot = self._save_svc.current
        data = self._selected_family_data()
        if slot and data and self._confirm(f"确定重置「{data['name']}」吗？"):
            beep()
            self._after_operation(slot.family_reset(data["name"]))
            self._update_family_display(data["name"], slot.family_pool.get(data["name"], 0))

    def _family_shiny(self) -> None:
        slot = self._save_svc.current
        data = self._selected_family_data()
        if not slot or not data:
            return
        beep()
        dialog = ShinyChoiceDialog(
            self,
            POOL_FAMILY,
            slot.family_pool.get(data["name"], 0),
            fixed_spirit=data["name"],
            fixed_season=data["season"],
        )
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_data:
            self._apply_shiny_record(dialog.result_data)

    def _selected_element(self) -> str:
        item = self.element_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else ""

    def _element_increase(self) -> None:
        slot = self._save_svc.current
        element = self._selected_element()
        if slot and element:
            beep()
            self._after_operation(slot.element_increase(element))
            self._update_element_display(element, slot.element_pool.get(element, 0))

    def _element_decrease(self) -> None:
        slot = self._save_svc.current
        element = self._selected_element()
        if slot and element:
            beep()
            self._after_operation(slot.element_decrease(element))
            self._update_element_display(element, slot.element_pool.get(element, 0))

    def _element_reset(self) -> None:
        slot = self._save_svc.current
        element = self._selected_element()
        if slot and element and self._confirm(f"确定重置「{element}」属性吗？"):
            beep()
            self._after_operation(slot.element_reset(element))
            self._update_element_display(element, slot.element_pool.get(element, 0))

    def _element_shiny(self) -> None:
        slot = self._save_svc.current
        element = self._selected_element()
        if not slot or not element:
            return
        beep()
        dialog = ShinyChoiceDialog(self, POOL_ELEMENT, slot.element_pool.get(element, 0), element=element)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_data:
            self._apply_shiny_record(dialog.result_data)

    def _manual_add_shiny(self) -> None:
        slot = self._save_svc.current
        if not slot:
            return
        beep()
        dialog = ManualShinyDialog(self, slot)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_data:
            self._apply_shiny_record(dialog.result_data)

    def _delete_selected_shiny(self) -> None:
        slot = self._save_svc.current
        row = self.shiny_table.currentRow()
        if not slot or row < 0:
            return
        index_item = self.shiny_table.verticalHeaderItem(row)
        if index_item is None:
            return
        index = int(index_item.text())
        if self._confirm("确定删除这条异色记录吗？") and slot.delete_shiny_record(index):
            beep()
            self._save_svc.save_current()
            self._load_slot(slot)

    def _apply_shiny_record(self, data: dict) -> None:
        slot = self._save_svc.current
        if not slot:
            return
        pool_type = data.get("pool_type", POOL_UNKNOWN)
        spirit_name = data.get("spirit_name", "")
        element = data.get("element", "")
        reset_after_record = data.get("reset_after_record", True)

        slot.add_shiny_record(
            pool_type=pool_type,
            spirit_name=spirit_name,
            pity_count=data.get("pity_count", 0),
            season=data.get("season", ""),
            element=element,
            reset_after_record=reset_after_record,
        )
        if reset_after_record:
            if pool_type == POOL_RANDOM:
                slot.clear_random_pool()
            elif pool_type == POOL_FAMILY:
                slot.clear_family_pool(spirit_name)
            elif pool_type == POOL_ELEMENT:
                slot.clear_element_pool(element)
        self._save_svc.save_current()
        self._load_slot(slot)

    def _element_for_record(self, record: ShinyRecord) -> str:
        for season in load_seasons():
            if record.season and str(season.get("season", "")) != record.season:
                continue
            for spirit in season.get("spirits", []):
                if spirit_display(spirit) == record.spirit_name:
                    return primary_element(spirit)
        return ""

    @staticmethod
    def _pool_label(pool_type: str) -> str:
        return {
            POOL_RANDOM: "随机",
            POOL_FAMILY: "家族",
            POOL_ELEMENT: "属性",
            POOL_UNKNOWN: "未知",
        }.get(pool_type, pool_type)

    def _confirm(self, message: str) -> bool:
        reply = QMessageBox.question(self, "确认", message)
        if reply == QMessageBox.StandardButton.Yes:
            beep()
            return True
        return False


class QInputDialogCompat:
    """局部封装，避免主窗口实现里散落输入框代码。"""

    @staticmethod
    def get_text(parent: QWidget, title: str, label: str) -> tuple[str, bool]:
        dialog = QDialog(parent)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(label))
        edit = QLineEdit()
        layout.addWidget(edit)
        buttons = QHBoxLayout()
        cancel = QPushButton("取消")
        ok = QPushButton("确定")
        cancel.clicked.connect(dialog.reject)
        ok.clicked.connect(dialog.accept)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        layout.addLayout(buttons)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        return edit.text(), accepted
