"""PySide6 主窗口 —— 复现现有核心功能的试验版。"""
from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import Qt, QMargins, QSize, QTimer
from PySide6.QtGui import QIcon, QTextOption
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
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
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
        self.setMinimumWidth(360)
        self._pool_type = pool_type
        self._pity_count = pity_count
        self._fixed_spirit = fixed_spirit
        self._fixed_season = fixed_season
        self._element = element
        self._seasons = load_seasons()
        self._season_by_id = {str(item.get("season", "")): item for item in self._seasons}
        self.result_data: dict | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
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
        if self._pity_count <= 0:
            QMessageBox.warning(self, "无法记录异色", "当前保底为 0，不能通过快捷出货记录添加异色。")
            return
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
        self.setMinimumWidth(400)
        self._slot = slot
        self._seasons = load_seasons()
        self._season_by_id = {str(item.get("season", "")): item for item in self._seasons}
        self.result_data: dict | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

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
        self._family_count_labels: dict[str, list[QLabel]] = {}
        self._element_items: dict[str, QPushButton] = {}
        self._selected_element_name: str | None = None

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
        root.setObjectName("appRoot")
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 顶栏 ──
        top_bar_widget = QWidget()
        top_bar_widget.setObjectName("topBar")
        top_bar = QHBoxLayout(top_bar_widget)
        top_bar.setContentsMargins(16, 10, 16, 10)
        top_bar.setSpacing(8)

        logo = QLabel("RocoCapture V2")
        logo.setObjectName("brandLabel")
        top_bar.addWidget(logo)

        top_bar.addStretch()
        save_label = QLabel("存档:")
        save_label.setObjectName("topBarLabel")
        top_bar.addWidget(save_label)
        self.save_combo = QComboBox()
        self.save_combo.setObjectName("saveCombo")
        self.save_combo.setMinimumWidth(176)
        self.save_combo.currentTextChanged.connect(self._on_save_selected)
        top_bar.addWidget(self.save_combo)

        top_bar.addSpacing(10)
        for text, handler in [
            ("新建", self._create_save),
            ("删除", self._delete_save),
            ("重命名", self._rename_save),
        ]:
            btn = QPushButton(text)
            btn.setMinimumWidth(62)
            btn.clicked.connect(handler)
            top_bar.addWidget(btn)

        top_bar.addSpacing(18)
        for text, handler in [("导入", self._import_save), ("导出", self._export_save)]:
            btn = QPushButton(text)
            btn.setMinimumWidth(62)
            btn.clicked.connect(handler)
            top_bar.addWidget(btn)

        main_layout.addWidget(top_bar_widget)

        # ── 分隔线 ──
        sep = QWidget()
        sep.setObjectName("divider")
        sep.setFixedHeight(1)
        main_layout.addWidget(sep)

        # ── 主体：左侧导航 + 中央堆叠页 + 右侧日志 ──
        body = QHBoxLayout()
        body.setSpacing(0)

        # 左侧导航
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(154)
        self.sidebar.setSpacing(6)
        self.sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sidebar.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for icon, label in [
            ("🎲", "随机池"),
            ("👪", "家族池"),
            ("🔥", "属性池"),
            ("📊", "异色明细"),
            ("⚙️", "设置"),
        ]:
            item = QListWidgetItem(f"{icon}  {label}")
            item.setSizeHint(QSize(124, 48))
            self.sidebar.addItem(item)
        body.addWidget(self.sidebar)

        # 分隔竖线
        vsep = QWidget()
        vsep.setObjectName("divider")
        vsep.setFixedWidth(1)
        body.addWidget(vsep)

        # 中央堆叠页（必须早于 sidebar 信号连接，否则 _on_nav_changed 报错）
        self.page_stack = QStackedWidget()
        self.page_stack.setObjectName("pageStack")
        self._build_random_page()
        self._build_family_page()
        self._build_element_page()
        self._build_shiny_page()
        self._build_settings_page()
        body.addWidget(self.page_stack, 1)

        # 右侧日志
        self.log_text = QTextEdit()
        self.log_text.setObjectName("logPanel")
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.log_text.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.log_text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.log_text.setFixedWidth(248)
        body.addWidget(self.log_text)

        main_layout.addLayout(body, 1)

        # 连接导航信号并设默认页（QStackedWidget 已就绪）
        self.sidebar.currentRowChanged.connect(self._on_nav_changed)
        self.sidebar.setCurrentRow(0)

        self.setCentralWidget(root)
        self.resize(1280, 780)
        self.setMinimumSize(1040, 620)

    def _card_counter(self, label: str, widget_name: str = "") -> tuple[QWidget, QLabel]:
        """创建「大字号计数卡片」：标题行 + 超大计数。返回 (容器, 计数QLabel)。"""
        card = QWidget()
        card.setObjectName("counterCard")
        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(label)
        title.setObjectName("counterTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        count_label = QLabel("0")
        count_label.setObjectName("counterValue")
        count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(count_label)

        if widget_name:
            setattr(self, widget_name, count_label)

        return card, count_label

    def _card_buttons(self) -> QHBoxLayout:
        """创建统一的操作按钮行 [+1] [-1] [重置] [出异色]。返回 layout 供调用方绑定信号。"""
        row = QHBoxLayout()
        row.setSpacing(12)
        for text, role in [
            ("+1", "increase"),
            ("-1", "decrease"),
            ("↺ 重置", "reset"),
            ("★ 出异色", "shiny"),
        ]:
            btn = QPushButton(text)
            btn.setProperty("role", role)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            row.addWidget(btn)
        return row

    def _build_random_page(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)

        # 标题
        header = QLabel("随机池")
        header.setObjectName("pageHeader")
        layout.addWidget(header)

        # 精灵名称输入
        self.random_name = QLineEdit()
        self.random_name.setPlaceholderText("精灵名称（可选，回车=增加）")
        self.random_name.returnPressed.connect(self._random_increase)
        layout.addWidget(self.random_name)

        layout.addSpacing(12)

        # 计数卡片
        card, self.random_count = self._card_counter("保底进度", "random_count")
        layout.addWidget(card)

        layout.addSpacing(16)

        # 操作按钮
        btn_row = self._card_buttons()
        inc, dec, rst, shiny = [btn_row.itemAt(i).widget() for i in range(4)]
        inc.clicked.connect(self._random_increase)
        dec.clicked.connect(self._random_decrease)
        rst.clicked.connect(self._random_reset)
        shiny.clicked.connect(self._random_shiny)
        layout.addLayout(btn_row)

        layout.addStretch()
        self.page_stack.addWidget(page)

    def _build_family_page(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)

        header = QLabel("家族池")
        header.setObjectName("pageHeader")
        layout.addWidget(header)

        # 上半：家族树 + 计数卡片
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.family_tree = QTreeWidget()
        self.family_tree.setColumnCount(1)
        self.family_tree.setHeaderLabels(["精灵"])
        self.family_tree.setHeaderHidden(True)
        self.family_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.family_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.family_tree.setIconSize(QSize(28, 28))
        self.family_tree.setIndentation(16)
        self.family_tree.setRootIsDecorated(True)
        self.family_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.family_tree.currentItemChanged.connect(self._on_family_selected)
        splitter.addWidget(self.family_tree)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(12, 0, 0, 0)

        self.family_detail_title = QLabel("请选择精灵")
        self.family_detail_title.setObjectName("mutedLabel")
        self.family_detail_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.family_detail_title)

        card, self.family_detail_count = self._card_counter("保底进度")
        right_layout.addWidget(card)

        btn_row = self._card_buttons()
        inc, dec, rst, shiny = [btn_row.itemAt(i).widget() for i in range(4)]
        inc.clicked.connect(self._family_increase)
        dec.clicked.connect(self._family_decrease)
        rst.clicked.connect(self._family_reset)
        shiny.clicked.connect(self._family_shiny)
        right_layout.addLayout(btn_row)

        right_layout.addStretch()
        splitter.addWidget(right_widget)
        splitter.setHandleWidth(12)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)
        self.page_stack.addWidget(page)

    def _on_family_selected(self) -> None:
        data = self._selected_family_data()
        if data:
            self.family_detail_title.setText(data["name"])
            count = self._save_svc.current.family_pool.get(data["name"], 0) if self._save_svc.current else 0
            self.family_detail_count.setText(str(count))
            self._set_counter_state(self.family_detail_count, count)

    def _build_element_page(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)

        header = QLabel("属性池")
        header.setObjectName("pageHeader")
        layout.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.element_grid_panel = QWidget()
        self.element_grid_panel.setObjectName("elementGridPanel")
        self.element_grid = QGridLayout(self.element_grid_panel)
        self.element_grid.setContentsMargins(10, 10, 10, 10)
        self.element_grid.setHorizontalSpacing(10)
        self.element_grid.setVerticalSpacing(8)
        splitter.addWidget(self.element_grid_panel)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(12, 0, 0, 0)
        right_widget.setMinimumWidth(260)
        right_widget.setMaximumWidth(340)

        self.element_detail_title = QLabel("请选择属性")
        self.element_detail_title.setObjectName("mutedLabel")
        self.element_detail_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.element_detail_title)

        card, self.element_detail_count = self._card_counter("保底进度")
        right_layout.addWidget(card)

        btn_row = self._card_buttons()
        inc, dec, rst, shiny = [btn_row.itemAt(i).widget() for i in range(4)]
        inc.clicked.connect(self._element_increase)
        dec.clicked.connect(self._element_decrease)
        rst.clicked.connect(self._element_reset)
        shiny.clicked.connect(self._element_shiny)
        right_layout.addLayout(btn_row)

        right_layout.addStretch()
        splitter.addWidget(right_widget)
        splitter.setHandleWidth(12)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)
        self.page_stack.addWidget(page)

    def _on_element_selected(self) -> None:
        element = self._selected_element()
        if element:
            self.element_detail_title.setText(element)
            count = self._save_svc.current.element_pool.get(element, 0) if self._save_svc.current else 0
            self.element_detail_count.setText(str(count))
            self._set_counter_state(self.element_detail_count, count)

    def _build_shiny_page(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)

        header = QLabel("异色明细")
        header.setObjectName("pageHeader")
        layout.addWidget(header)

        top_row = QHBoxLayout()
        top_row.addStretch()
        add_btn = QPushButton("手动添加")
        delete_btn = QPushButton("删除选中")
        add_btn.clicked.connect(self._manual_add_shiny)
        delete_btn.clicked.connect(self._delete_selected_shiny)
        top_row.addWidget(add_btn)
        top_row.addWidget(delete_btn)
        layout.addLayout(top_row)

        self.shiny_table = QTableWidget(0, 6)
        self.shiny_table.setHorizontalHeaderLabels(["时间", "池子", "赛季", "精灵", "属性", "保底"])
        self.shiny_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.shiny_table.verticalHeader().setVisible(False)
        self.shiny_table.verticalHeader().setDefaultSectionSize(42)
        self.shiny_table.setAlternatingRowColors(True)
        self.shiny_table.setIconSize(QSize(32, 32))
        self.shiny_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.shiny_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.shiny_table, 1)

        self.page_stack.addWidget(page)

    def _build_settings_page(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)

        header = QLabel("设置 / 关于")
        header.setObjectName("pageHeader")
        layout.addWidget(header)

        info = QLabel(
            "RocoCapture V2\n\n"
            "洛克王国异色保底追踪工具\n\n"
            "保底规则：\n"
            "  · 满保底 80 抽（红色闪烁）\n"
            "  · 预警阈值 70 抽（橙色提示）\n\n"
            "PySide6 / Qt 重构版"
        )
        info.setObjectName("mutedLabel")
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch()

        self.page_stack.addWidget(page)

    def _on_nav_changed(self, index: int) -> None:
        if index >= 0:
            self.page_stack.setCurrentIndex(index)

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

    @staticmethod
    def _counter_state(count: int) -> str:
        if count >= PITY_MAX:
            return "critical"
        if count >= PITY_WARN_THRESHOLD:
            return "warn"
        return "normal"

    @staticmethod
    def _set_counter_property(label: QLabel, state: str) -> None:
        label.setProperty("state", state)
        label.style().unpolish(label)
        label.style().polish(label)
        label.update()

    def _set_counter_state(self, label: QLabel, count: int) -> None:
        self._set_counter_property(label, self._counter_state(count))

    @staticmethod
    def _refresh_widget_style(widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    def _set_element_card_state(self, button: QPushButton, count: int) -> None:
        button.setProperty("state", self._counter_state(count))
        self._refresh_widget_style(button)

    def _set_family_pity_state(self, label: QLabel, count: int) -> None:
        label.setProperty("state", self._counter_state(count))
        self._refresh_widget_style(label)

    def _can_record_shiny(self, count: int, target: str) -> bool:
        if count > 0:
            return True
        QMessageBox.warning(self, "无法记录异色", f"「{target}」当前保底为 0，先增加保底后再记录异色。")
        return False

    def _update_random_counter_color(self) -> None:
        """随机池计数器颜色 + 闪烁控制。"""
        try:
            count = int(self.random_count.text())
        except ValueError:
            count = 0
        if count >= PITY_MAX:
            if not self._flash_timer.isActive():
                self._flash_timer.start(500)
        else:
            self._flash_timer.stop()
            self._set_counter_state(self.random_count, count)

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
            self._set_counter_property(self.random_count, "critical")
        else:
            self._set_counter_property(self.random_count, "normal")

    # ---------- 增量 UI 刷新（避免全量重建延迟） ----------

    def _update_random_display(self, count: int) -> None:
        """增量更新随机池计数器显示。"""
        self.random_count.setText(str(count))
        self._update_random_counter_color()

    def _update_family_display(self, display_name: str, count: int) -> None:
        """增量更新家族池中指定精灵的计数列文本与颜色。"""
        labels = self._family_count_labels.get(display_name, [])
        for label in labels:
            label.setText(str(count))
            self._set_family_pity_state(label, count)
        # 同步刷新右侧详情卡片
        data = self._selected_family_data()
        if data and data["name"] == display_name:
            self.family_detail_count.setText(str(count))
            self._set_counter_state(self.family_detail_count, count)

    def _update_element_display(self, element: str, count: int) -> None:
        """增量更新属性池中指定属性的计数字段与颜色。"""
        button = self._element_items.get(element)
        if button:
            button.setText(f"{element}\n保底 {count}")
            self._set_element_card_state(button, count)
        # 同步刷新右侧详情卡片
        if self._selected_element() == element:
            self.element_detail_count.setText(str(count))
            self._set_counter_state(self.element_detail_count, count)

    def _family_season_cell(self, label: str) -> QWidget:
        cell = QWidget()
        cell.setObjectName("familySeasonCell")
        cell.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 0, 10, 0)
        layout.setSpacing(0)

        title = QLabel(label)
        title.setObjectName("familySeasonLabel")
        title.setToolTip(label)
        layout.addWidget(title, 1)
        return cell

    def _family_spirit_cell(
        self,
        spirit: dict,
        season_id: str,
        elements: list[str],
        count: int,
    ) -> tuple[QWidget, QLabel]:
        display_name = spirit_display(spirit)
        cell = QWidget()
        cell.setObjectName("familySpiritCell")
        cell.setToolTip(display_name)
        cell.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 3, 10, 3)
        layout.setSpacing(8)

        icon = QLabel()
        icon.setFixedSize(38, 38)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setPixmap(spirit_icon(str(spirit.get("name", "")), season_id).pixmap(36, 36))
        layout.addWidget(icon)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(0)

        no_label = QLabel(f"No.{int(spirit['no']):03d}")
        no_label.setObjectName("familySpiritNo")

        name_label = QLabel(str(spirit.get("name", "")))
        name_label.setObjectName("familySpiritName")
        name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        text_col.addWidget(no_label)
        text_col.addWidget(name_label)
        layout.addLayout(text_col, 1)

        if elements:
            element_row = QWidget()
            element_layout = QHBoxLayout(element_row)
            element_layout.setContentsMargins(0, 0, 0, 0)
            element_layout.setSpacing(4)
            icon_label = QLabel()
            icon_label.setFixedSize(18, 18)
            icon_label.setPixmap(element_icon(elements[0]).pixmap(18, 18))
            element_layout.addWidget(icon_label)

            text = QLabel("/".join(elements))
            text.setObjectName("familySpiritElements")
            text.setToolTip("/".join(elements))
            element_layout.addWidget(text)
            element_layout.addStretch()
            element_row.setFixedWidth(96)
            layout.addWidget(element_row)
        else:
            layout.addSpacing(96)

        count_label = QLabel(str(count))
        count_label.setObjectName("familyPityCount")
        count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        count_label.setFixedWidth(34)
        self._set_family_pity_state(count_label, count)
        layout.addWidget(count_label)
        return cell, count_label

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
        self._family_count_labels.clear()
        for season in load_seasons():
            season_id = str(season.get("season", ""))
            season_label = season.get("label", season_id)
            top = QTreeWidgetItem([season_label])
            top.setSizeHint(0, QSize(0, 42))
            top.setData(0, Qt.ItemDataRole.UserRole, {"is_season": True})
            top.setToolTip(0, season_label)
            self.family_tree.addTopLevelItem(top)
            self.family_tree.setItemWidget(top, 0, self._family_season_cell(season_label))
            for spirit in season.get("spirits", []):
                display_name = spirit_display(spirit)
                elements = spirit.get("elements", [])
                count = slot.family_pool.get(display_name, 0)
                item = QTreeWidgetItem([""])
                item.setSizeHint(0, QSize(0, 54))
                item.setToolTip(0, display_name)
                item.setData(0, Qt.ItemDataRole.UserRole, {
                    "is_season": False,
                    "name": display_name,
                    "season": season_id,
                })
                top.addChild(item)
                cell, count_label = self._family_spirit_cell(spirit, season_id, elements, count)
                self.family_tree.setItemWidget(item, 0, cell)
                self._family_items.setdefault(display_name, []).append(item)
                self._family_count_labels.setdefault(display_name, []).append(count_label)
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
        selected_element = self._selected_element()

        while self.element_grid.count():
            layout_item = self.element_grid.takeAt(0)
            widget = layout_item.widget()
            if widget:
                widget.deleteLater()
        self._element_items.clear()
        self._selected_element_name = None
        for index, element in enumerate(ELEMENTS):
            count = slot.element_pool.get(element, 0)
            button = QPushButton(f"{element}\n保底 {count}")
            button.setObjectName("elementCard")
            button.setProperty("role", "elementCard")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setIcon(element_icon(element))
            button.setIconSize(QSize(30, 30))
            button.setMinimumHeight(58)
            button.clicked.connect(lambda _checked=False, name=element: self._select_element(name))
            self._set_element_card_state(button, count)
            row, column = divmod(index, 2)
            self.element_grid.addWidget(button, row, column)
            self._element_items[element] = button

        for column in range(2):
            self.element_grid.setColumnStretch(column, 1)

        if selected_element in self._element_items:
            self._select_element(selected_element)
        else:
            self.element_detail_title.setText("请选择属性")
            self.element_detail_count.setText("0")
            self._set_counter_state(self.element_detail_count, 0)

    def _select_element(self, element: str) -> None:
        self._selected_element_name = element
        for name, button in self._element_items.items():
            button.setChecked(name == element)
        self._on_element_selected()

    def _load_shiny_records(self, records: list[ShinyRecord]) -> None:
        self.shiny_table.setRowCount(0)
        for index in range(len(records) - 1, -1, -1):
            record = records[index]
            row = self.shiny_table.rowCount()
            self.shiny_table.insertRow(row)
            self.shiny_table.setRowHeight(row, 44)
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
        self.log_text.setPlainText("\n\n".join(lines))

    @staticmethod
    def _pool_label(pool_type: int) -> str:
        mapping = {POOL_RANDOM: "随机", POOL_FAMILY: "家族", POOL_ELEMENT: "属性"}
        return mapping.get(pool_type, "未知")

    def _selected_family_data(self) -> dict | None:
        """获取家族树中当前选中的精灵信息。"""
        item = self.family_tree.currentItem()
        if not item:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict) and not data.get("is_season"):
            return data
        return None

    def _selected_element(self) -> str | None:
        """获取属性列表中当前选中的属性名称。"""
        return self._selected_element_name

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
        if not self._can_record_shiny(slot.random_pool, "随机池"):
            return
        beep()
        dialog = ShinyChoiceDialog(self, POOL_RANDOM, slot.random_pool)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_data:
            self._apply_shiny_record(dialog.result_data)

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
        count = slot.family_pool.get(data["name"], 0)
        if not self._can_record_shiny(count, data["name"]):
            return
        beep()
        dialog = ShinyChoiceDialog(
            self,
            POOL_FAMILY,
            count,
            fixed_spirit=data["name"],
            fixed_season=data["season"],
        )
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_data:
            self._apply_shiny_record(dialog.result_data)

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
        count = slot.element_pool.get(element, 0)
        if not self._can_record_shiny(count, f"{element}属性"):
            return
        beep()
        dialog = ShinyChoiceDialog(self, POOL_ELEMENT, count, element=element)
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
