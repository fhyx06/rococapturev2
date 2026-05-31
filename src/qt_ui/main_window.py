"""PySide6 主窗口 —— 复现现有核心功能的试验版。"""
from __future__ import annotations

import json
import re
from datetime import datetime
from html import escape
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, QMargins, QSize, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QIcon, QTextOption
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
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
    QScrollArea,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)
from src.__about__ import (
    APP_DISPLAY_NAME,
    APP_NAME,
    APP_VERSION,
    GITHUB_RELEASES_URL,
    UPDATE_MANIFEST_URL,
)
from src.utils.beep import beep

from src.assets.season_loader import get_latest_season, load_seasons
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
LOG_FILTER_ALL = "all"
LOG_FILTER_OTHER = "other"
LOG_FILTER_OPTIONS = [
    ("全部", LOG_FILTER_ALL),
    ("家族", POOL_FAMILY),
    ("随机", POOL_RANDOM),
    ("属性", POOL_ELEMENT),
    ("其他", LOG_FILTER_OTHER),
]

# 日志颜色权重：家族使用最频繁，因此最亮；随机次之；属性和其他保持低饱和。
LOG_COLORS = {
    POOL_FAMILY: {"accent": "#f3b34b", "text": "#f1d39a", "bg": "#2b251b"},
    POOL_RANDOM: {"accent": "#78a9ff", "text": "#b9d3ff", "bg": "#1f2736"},
    POOL_ELEMENT: {"accent": "#6fb8a6", "text": "#a8d9ce", "bg": "#1d2b2a"},
    LOG_FILTER_OTHER: {"accent": "#8e98a8", "text": "#b8c0cc", "bg": "#222630"},
}


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


def version_tuple(version: str) -> tuple[int, int, int] | None:
    normalized = version.strip().lower()
    if normalized.startswith("v"):
        normalized = normalized[1:]
    normalized = re.split(r"[-+]", normalized, maxsplit=1)[0]
    parts = normalized.split(".")
    if not parts or len(parts) > 3:
        return None

    numbers: list[int] = []
    for part in parts:
        if not part.isdigit():
            return None
        numbers.append(int(part))
    while len(numbers) < 3:
        numbers.append(0)
    return tuple(numbers)


def is_newer_version(remote_version: str, current_version: str) -> bool:
    remote = version_tuple(remote_version)
    current = version_tuple(current_version)
    if remote is None or current is None:
        return False
    return remote > current


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
            QMessageBox.warning(self, "无法记录异色", "当前保底为 0，怎么出货的？")
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


class AccordionTreeWidget(QTreeWidget):
    """赛季标题单击展开，精灵条目保留正常选择。"""

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            position = event.position().toPoint() if hasattr(event, "position") else event.pos()
            item = self.itemAt(position)
            data = item.data(0, Qt.ItemDataRole.UserRole) if item else None
            if isinstance(data, dict) and data.get("is_season"):
                self.setCurrentItem(item)
                item.setExpanded(not item.isExpanded())
                event.accept()
                return
        super().mousePressEvent(event)


class HoverScrollController(QObject):
    """内容可滚动时预留滚动条宽度，鼠标移入后显示滑块。"""

    def __init__(self, area: QAbstractScrollArea):
        super().__init__(area)
        self._area = area
        area.setProperty("scrollHover", "false")
        area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.installEventFilter(self)
        area.verticalScrollBar().rangeChanged.connect(lambda *_: self.sync_scrollbar_policy())
        QTimer.singleShot(0, self.sync_scrollbar_policy)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._area:
            if event.type() == QEvent.Type.Enter:
                self.set_scroll_hover(True)
            elif event.type() == QEvent.Type.Leave:
                self.set_scroll_hover(False)
        return super().eventFilter(watched, event)

    def set_scroll_hover(self, enabled: bool) -> None:
        self._area.setProperty("scrollHover", "true" if enabled else "false")
        for widget in (self._area, self._area.verticalScrollBar()):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        self._area.viewport().update()
        self._area.verticalScrollBar().update()

    def sync_scrollbar_policy(self) -> None:
        policy = (
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
            if self._area.verticalScrollBar().maximum() > 0
            else Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        if self._area.verticalScrollBarPolicy() != policy:
            self._area.setVerticalScrollBarPolicy(policy)


def install_hover_scrollbar(area: QAbstractScrollArea) -> HoverScrollController:
    controller = HoverScrollController(area)
    area._hover_scroll_controller = controller
    return controller


class HoverScrollArea(QScrollArea):
    """内容可滚动时预留滚动条宽度，鼠标移入后显示滑块。"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._hover_scroll_controller = install_hover_scrollbar(self)


class ManualShinyDialog(QDialog):
    """异色明细页手动补录。"""

    _pool_labels = {
        POOL_RANDOM: "随机池",
        POOL_FAMILY: "家族池",
        POOL_ELEMENT: "属性池",
        POOL_UNKNOWN: "我不知道",
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
        if self.pity_spin.value() <= 0:
            QMessageBox.warning(self, "无法添加异色记录", "保底数必须大于 0。")
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


class ShinyRecordCard(QWidget):
    """异色记录卡片。"""

    clicked = Signal(int)

    def __init__(
        self,
        index: int,
        record: ShinyRecord,
        element: str,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._index = index
        self.setObjectName("shinyRecordCard")
        self.setProperty("pool", record.pool_type)
        self.setProperty("selected", "false")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        tooltip = record.format_display()
        if record.pool_type == POOL_ELEMENT and element:
            tooltip = f"{tooltip}\n属性：{element}"
        self.setToolTip(tooltip)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 16, 8)
        layout.setSpacing(7)

        icon = QLabel()
        icon.setObjectName("shinyCardIcon")
        icon.setFixedSize(38, 38)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setPixmap(spirit_icon(record.spirit_name, record.season).pixmap(34, 34))
        layout.addWidget(icon)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(4)

        title = QLabel(self._title_text(record))
        title.setObjectName("shinyCardTitle")
        title.setWordWrap(False)
        title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        title.setToolTip(self._title_text(record))
        text_col.addWidget(title)

        date = QLabel(self._display_timestamp(record.timestamp))
        date.setObjectName("shinyCardMeta")
        date.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        text_col.addWidget(date)

        layout.addLayout(text_col, 1)

        pity_col = QVBoxLayout()
        pity_col.setContentsMargins(0, 0, 0, 0)
        pity_col.setSpacing(0)
        pity_col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pity_value = QLabel(str(record.pity_count))
        pity_value.setObjectName("shinyPityValue")
        pity_value.setProperty("state", self._pity_state(record.pity_count))
        pity_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pity_col.addWidget(pity_value)

        pity_label = QLabel("保底")
        pity_label.setObjectName("shinyPityLabel")
        pity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pity_col.addWidget(pity_label)

        layout.addLayout(pity_col)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._index)
            event.accept()
            return
        super().mousePressEvent(event)

    @staticmethod
    def _title_text(record: ShinyRecord) -> str:
        return ShinyRecordCard._display_spirit_name(record.spirit_name)

    @staticmethod
    def _display_timestamp(timestamp: str) -> str:
        try:
            parsed = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError):
            return timestamp or "未知时间"
        return f"{parsed.year}-{parsed.month}-{parsed.day} {parsed:%H:%M:%S}"

    @staticmethod
    def _display_spirit_name(spirit_name: str) -> str:
        name = (spirit_name or "").strip()
        if name:
            return name
        return "未知精灵"

    @staticmethod
    def _pity_state(count: int) -> str:
        if count >= PITY_MAX:
            return "critical"
        if count >= PITY_WARN_THRESHOLD:
            return "warn"
        return "normal"


class QtMainWindow(QMainWindow):
    """Qt 试验版主窗口。"""

    def __init__(self, save_service: SaveService):
        super().__init__()
        self._save_svc = save_service
        self._seasons = load_seasons()
        self._family_items: dict[str, list[QTreeWidgetItem]] = {}
        self._family_count_labels: dict[str, list[QLabel]] = {}
        self._element_items: dict[str, QPushButton] = {}
        self._selected_element_name: str | None = None
        self._shiny_column_layouts: dict[str, QVBoxLayout] = {}
        self._shiny_cards: dict[int, ShinyRecordCard] = {}
        self._selected_shiny_index: int | None = None
        self._network_manager = QNetworkAccessManager(self)
        self._update_reply: QNetworkReply | None = None
        self._update_sources: list[dict[str, str]] = []
        self._update_source_index = 0
        self._update_errors: list[str] = []

        # 保底临界闪烁定时器
        self._flash_timer = QTimer(self)
        self._flash_timer.timeout.connect(self._toggle_flash)
        self._flash_on = False

        self.setWindowTitle(f"{APP_DISPLAY_NAME} v{APP_VERSION}")
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

        logo = QLabel(f"{APP_DISPLAY_NAME}  v{APP_VERSION}")
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
            ("🐾", "家族池"),
            ("🔥", "属性池"),
            ("✨", "异色明细"),
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
        log_column = QWidget()
        log_column.setObjectName("logColumn")
        log_column.setFixedWidth(248)
        log_layout = QVBoxLayout(log_column)
        log_layout.setContentsMargins(12, 12, 10, 12)
        log_layout.setSpacing(10)

        log_header = QHBoxLayout()
        log_header.setContentsMargins(0, 0, 0, 0)
        log_title = QLabel("日志")
        log_title.setObjectName("logTitle")
        log_header.addWidget(log_title)
        log_header.addStretch()

        self.log_filter_combo = QComboBox()
        self.log_filter_combo.setObjectName("logFilterCombo")
        for label, value in LOG_FILTER_OPTIONS:
            self.log_filter_combo.addItem(label, value)
        self.log_filter_combo.currentIndexChanged.connect(self._on_log_filter_changed)
        log_header.addWidget(self.log_filter_combo)
        log_layout.addLayout(log_header)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("logPanel")
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.log_text.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        install_hover_scrollbar(self.log_text)
        log_layout.addWidget(self.log_text, 1)
        body.addWidget(log_column)

        main_layout.addLayout(body, 1)

        # 连接导航信号并设默认页（QStackedWidget 已就绪）
        self.sidebar.currentRowChanged.connect(self._on_nav_changed)
        self.sidebar.setCurrentRow(0)
        # 窗口大小
        self.setCentralWidget(root)
        self.resize(1260, 780)
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

    def _card_buttons(self, compact: bool = False) -> QHBoxLayout | QGridLayout:
        """创建统一的操作按钮行 [+1] [-1] [重置] [出异色]。返回 layout 供调用方绑定信号。"""
        row = QGridLayout() if compact else QHBoxLayout()
        row.setSpacing(12)
        for index, (text, role) in enumerate([
            ("+1", "increase"),
            ("-1", "decrease"),
            ("↺ 重置", "reset"),
            ("★ 出异色", "shiny"),
        ]):
            btn = QPushButton(text)
            btn.setProperty("role", role)
            if compact:
                btn.setProperty("compact", "true")
                btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if compact:
                row.addWidget(btn, index // 2, index % 2)
            else:
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
        self.random_name.setPlaceholderText("精灵名称（可选，回车增加）")
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

        self.family_tree = AccordionTreeWidget()
        self.family_tree.setObjectName("familyTree")
        self.family_tree.setColumnCount(1)
        self.family_tree.setHeaderLabels(["精灵"])
        self.family_tree.setHeaderHidden(True)
        self.family_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.family_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.family_tree.setIconSize(QSize(28, 28))
        self.family_tree.setIndentation(16)
        self.family_tree.setRootIsDecorated(True)
        self.family_tree.setExpandsOnDoubleClick(False)
        install_hover_scrollbar(self.family_tree)
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

        btn_row = self._card_buttons(compact=True)
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
        layout.setSpacing(14)

        top_row = QHBoxLayout()
        header = QLabel("异色明细")
        header.setObjectName("pageHeader")
        top_row.addWidget(header)
        top_row.addStretch()

        season_label = QLabel("赛季")
        season_label.setObjectName("topBarLabel")
        self.shiny_season_combo = QComboBox()
        self.shiny_season_combo.setObjectName("shinySeasonCombo")
        self.shiny_season_combo.setMinimumWidth(96)
        for season in self._seasons:
            season_id = str(season.get("season", ""))
            self.shiny_season_combo.addItem(season_id, season_id)
        latest = get_latest_season()
        if latest:
            self.shiny_season_combo.setCurrentText(str(latest.get("season", "")))
        self.shiny_season_combo.currentIndexChanged.connect(self._on_shiny_season_changed)
        top_row.addWidget(season_label)
        top_row.addWidget(self.shiny_season_combo)

        add_btn = QPushButton("手动添加")
        self.delete_shiny_btn = QPushButton("删除选中")
        self.delete_shiny_btn.setEnabled(False)
        add_btn.clicked.connect(self._manual_add_shiny)
        self.delete_shiny_btn.clicked.connect(self._delete_selected_shiny)
        top_row.addWidget(add_btn)
        top_row.addWidget(self.delete_shiny_btn)
        layout.addLayout(top_row)

        columns = QHBoxLayout()
        columns.setSpacing(12)
        self._shiny_column_layouts.clear()
        for pool_type, title in [
            (POOL_RANDOM, "🎲 随机池记录"),
            (POOL_FAMILY, "🐾 家族池记录"),
            (POOL_ELEMENT, "🔥 属性池记录"),
        ]:
            column = QWidget()
            column.setObjectName("shinyColumn")
            column.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            column_layout = QVBoxLayout(column)
            column_layout.setContentsMargins(12, 12, 12, 12)
            column_layout.setSpacing(10)

            title_label = QLabel(title)
            title_label.setObjectName("shinyColumnTitle")
            column_layout.addWidget(title_label)

            scroll = HoverScrollArea()
            scroll.setObjectName("shinyScroll")
            scroll.setWidgetResizable(True)
            content = QWidget()
            content.setObjectName("shinyColumnContent")
            cards_layout = QVBoxLayout(content)
            cards_layout.setContentsMargins(0, 0, 0, 0)
            cards_layout.setSpacing(10)
            scroll.setWidget(content)
            column_layout.addWidget(scroll, 1)

            self._shiny_column_layouts[pool_type] = cards_layout
            columns.addWidget(column, 1)

        layout.addLayout(columns, 1)

        self.page_stack.addWidget(page)

    def _build_settings_page(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)

        header = QLabel("设置 / 关于")
        header.setObjectName("pageHeader")
        layout.addWidget(header)

        info = QLabel(
            f"{APP_DISPLAY_NAME}\n v{APP_VERSION}\n\n"
            "洛克王国异色保底追踪工具\n\n"
            "保底规则：\n"
            "  · 满保底 80 抽（真有人吃满吗？）\n"
            "  · 预警阈值 70 抽\n\n"
            "PySide6 / Qt 重构版\n"
        )
        info.setObjectName("mutedLabel")
        info.setWordWrap(True)
        layout.addWidget(info)

        update_row = QHBoxLayout()
        self.update_check_btn = QPushButton("检查更新")
        self.update_check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_check_btn.clicked.connect(self._check_for_updates)
        self.update_status = QLabel("GitHub Releases")
        self.update_status.setObjectName("mutedLabel")
        self.update_status.setWordWrap(True)
        update_row.addWidget(self.update_check_btn)
        update_row.addWidget(self.update_status, 1)
        layout.addLayout(update_row)

        layout.addStretch()

        self.page_stack.addWidget(page)

    def _check_for_updates(self) -> None:
        if self._update_reply is not None:
            return

        self.update_check_btn.setEnabled(False)
        self.update_check_btn.setText("检查中...")
        self._update_sources = [
            {"name": "版本清单", "url": UPDATE_MANIFEST_URL},
        ]
        self._update_source_index = 0
        self._update_errors = []
        self._request_update_source()

    def _request_update_source(self) -> None:
        if self._update_source_index >= len(self._update_sources):
            self._finish_update_check()
            message = "\n\n".join(self._update_errors) or "无法连接到版本检查源。"
            self.update_status.setText("检查失败，请稍后重试")
            self._show_update_error(message)
            return

        source = self._current_update_source()
        self.update_status.setText(f"正在连接{source['name']}...")
        request = QNetworkRequest(QUrl(source["url"]))
        request.setRawHeader(b"Accept", b"application/json")
        request.setRawHeader(b"User-Agent", f"{APP_NAME}/{APP_VERSION}".encode("utf-8"))
        request.setAttribute(
            QNetworkRequest.Attribute.CacheLoadControlAttribute,
            QNetworkRequest.CacheLoadControl.AlwaysNetwork,
        )
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
        )
        if hasattr(request, "setTransferTimeout"):
            request.setTransferTimeout(10000)

        reply = self._network_manager.get(request)
        self._update_reply = reply
        reply.finished.connect(self._on_update_reply_finished)

    def _current_update_source(self) -> dict[str, str]:
        if 0 <= self._update_source_index < len(self._update_sources):
            return self._update_sources[self._update_source_index]
        return {"name": "版本检查源", "url": ""}

    def _finish_update_check(self) -> None:
        self.update_check_btn.setEnabled(True)
        self.update_check_btn.setText("检查更新")

    def _on_update_reply_finished(self) -> None:
        reply = self._update_reply
        if reply is None:
            return
        self._handle_update_reply(reply)

    def _handle_update_reply(self, reply: QNetworkReply) -> None:
        source = self._current_update_source()
        self._update_reply = None

        try:
            status_code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            payload = bytes(reply.readAll()).decode("utf-8", errors="replace")
            if reply.error() != QNetworkReply.NetworkError.NoError:
                message = self._format_update_error(status_code, payload, reply.errorString(), source["name"])
                self._try_next_update_source(message)
                return

            try:
                data = json.loads(payload)
            except json.JSONDecodeError as exc:
                self._try_next_update_source(f"{source['name']}：版本信息不是有效 JSON。{exc}")
                return

            release_info = self._parse_update_payload(data)
            tag_name = release_info["tag_name"]
            if not tag_name:
                self._try_next_update_source(f"{source['name']}：未获取到版本号。")
                return

            if is_newer_version(tag_name, APP_VERSION):
                self._finish_update_check()
                self.update_status.setText(f"发现新版本 {tag_name}（{source['name']}）")
                reply_button = QMessageBox.question(
                    self,
                    "发现新版本",
                    f"发现新版本 {tag_name}，当前版本 v{APP_VERSION}。\n是否打开 GitHub 下载地址？",
                )
                if reply_button == QMessageBox.StandardButton.Yes:
                    QDesktopServices.openUrl(QUrl(release_info["open_url"]))
                return

            self._finish_update_check()
            self.update_status.setText(f"当前已是最新版本 v{APP_VERSION}（{source['name']}）")
            QMessageBox.information(self, "检查更新", f"当前已是最新版本：v{APP_VERSION}")
        except (TypeError, KeyError) as exc:
            self._finish_update_check()
            self.update_status.setText("检查失败，版本信息解析异常")
            QMessageBox.warning(self, "检查更新失败", str(exc))
        finally:
            reply.deleteLater()

    def _try_next_update_source(self, message: str) -> None:
        self._update_errors.append(message)
        self._update_source_index += 1
        if self._update_source_index < len(self._update_sources):
            next_source = self._current_update_source()
            self.update_status.setText(f"{next_source['name']}重试中...")
            self._request_update_source()
            return

        self._finish_update_check()
        self.update_status.setText("检查失败，请稍后重试")
        self._show_update_error("\n\n".join(self._update_errors))

    @staticmethod
    def _parse_update_payload(data: dict) -> dict[str, str]:
        version = str(data.get("tag_name") or data.get("version") or "").strip()
        if version and not version.lower().startswith("v"):
            version = f"v{version}"
        open_url = str(
            data.get("download_url")
            or data.get("release_url")
            or GITHUB_RELEASES_URL
        )
        return {
            "tag_name": version,
            "open_url": open_url,
        }

    def _format_update_error(
        self,
        status_code: object,
        payload: str,
        network_message: str,
        source_name: str = "版本检查源",
    ) -> str:
        json_message = self._json_error_message(payload)
        status_text = f"{source_name} HTTP {status_code}" if status_code else f"{source_name} 网络请求失败"

        if status_code == 403:
            detail = json_message or "版本检查源暂时拒绝了本次请求。"
            return f"{status_text}：{detail}\n可能是访问频率限制、防盗链配置、网络代理或服务临时不可用。"
        if status_code == 404:
            detail = json_message or "没有找到版本清单。"
            return f"{status_text}：{detail}\n请确认 latest.json 已发布。"
        if status_code:
            detail = json_message or network_message or "版本检查源返回了异常响应。"
            return f"{status_text}：{detail}"
        return network_message or "无法连接到版本检查源，请检查网络后重试。"

    @staticmethod
    def _json_error_message(payload: str) -> str:
        if not payload.strip():
            return ""
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return payload.strip()[:240]
        message = data.get("message", "")
        return str(message).strip()

    def _show_update_error(self, message: str) -> None:
        reply_button = QMessageBox.question(
            self,
            "检查更新失败",
            f"{message}\n\n是否打开 Releases 页面手动查看？",
        )
        if reply_button == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl(GITHUB_RELEASES_URL))

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
                    expanded_seasons.add(str(data.get("season", "")))
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
            top = QTreeWidgetItem([""])
            top.setSizeHint(0, QSize(0, 42))
            top.setData(0, Qt.ItemDataRole.UserRole, {
                "is_season": True,
                "season": season_id,
                "label": season_label,
            })
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
            top.setExpanded(season_id in expanded_seasons)
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
        selected_season = self._selected_shiny_season()
        for cards_layout in self._shiny_column_layouts.values():
            while cards_layout.count():
                item = cards_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        self._shiny_cards.clear()
        self._selected_shiny_index = None
        if hasattr(self, "delete_shiny_btn"):
            self.delete_shiny_btn.setEnabled(False)

        grouped: dict[str, list[tuple[int, ShinyRecord]]] = {
            POOL_RANDOM: [],
            POOL_FAMILY: [],
            POOL_ELEMENT: [],
        }
        for index in range(len(records) - 1, -1, -1):
            record = records[index]
            if selected_season and record.season != selected_season:
                continue
            grouped[self._shiny_display_pool(record)].append((index, record))

        for pool_type, cards_layout in self._shiny_column_layouts.items():
            pool_records = grouped.get(pool_type, [])
            if not pool_records:
                empty = QLabel("暂无记录")
                empty.setObjectName("shinyEmptyLabel")
                empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cards_layout.addWidget(empty)
                cards_layout.addStretch()
                continue
            for index, record in pool_records:
                element = record.element or self._element_for_record(record)
                card = ShinyRecordCard(
                    index=index,
                    record=record,
                    element=element,
                )
                card.clicked.connect(self._select_shiny_record)
                cards_layout.addWidget(card)
                self._shiny_cards[index] = card
            cards_layout.addStretch()

    def _select_shiny_record(self, index: int) -> None:
        if self._selected_shiny_index == index:
            self._selected_shiny_index = None
        else:
            self._selected_shiny_index = index
        for card_index, card in self._shiny_cards.items():
            card.set_selected(card_index == self._selected_shiny_index)
        if hasattr(self, "delete_shiny_btn"):
            self.delete_shiny_btn.setEnabled(self._selected_shiny_index is not None)

    def _on_shiny_season_changed(self) -> None:
        slot = self._save_svc.current
        if slot:
            self._load_shiny_records(slot.shiny_records)

    def _selected_shiny_season(self) -> str:
        if hasattr(self, "shiny_season_combo"):
            return str(self.shiny_season_combo.currentData() or "")
        latest = get_latest_season()
        return str(latest.get("season", "")) if latest else ""

    @staticmethod
    def _shiny_display_pool(record: ShinyRecord) -> str:
        if record.pool_type in {POOL_RANDOM, POOL_FAMILY, POOL_ELEMENT}:
            return record.pool_type
        return POOL_RANDOM

    def _load_logs(self, logs: list[ActivityLog]) -> None:
        selected_filter = self._selected_log_filter()
        visible_logs = [
            log for log in reversed(logs)
            if self._log_matches_filter(log, selected_filter)
        ]
        if not visible_logs:
            label = self._log_filter_label(selected_filter)
            self.log_text.setHtml(
                "<html><body style='margin:0; padding:0;'>"
                f"<div style='color:#667285; padding:10px 2px;'>暂无{escape(label)}日志</div>"
                "</body></html>"
            )
            return

        rows = [self._log_row_html(log) for log in visible_logs]
        self.log_text.setHtml(
            "<html><body style='margin:0; padding:0; "
            "font-family:\"Cascadia Mono\", \"Consolas\", monospace; font-size:12px;'>"
            f"{''.join(rows)}</body></html>"
        )

    def _on_log_filter_changed(self) -> None:
        slot = self._save_svc.current
        if slot:
            self._load_logs(slot.logs)

    def _selected_log_filter(self) -> str:
        if hasattr(self, "log_filter_combo"):
            return str(self.log_filter_combo.currentData() or LOG_FILTER_ALL)
        return LOG_FILTER_ALL

    @staticmethod
    def _log_pool_key(pool_type: str) -> str:
        if pool_type in {POOL_RANDOM, POOL_FAMILY, POOL_ELEMENT}:
            return pool_type
        return LOG_FILTER_OTHER

    def _log_matches_filter(self, log: ActivityLog, selected_filter: str) -> bool:
        if selected_filter == LOG_FILTER_ALL:
            return True
        return self._log_pool_key(log.pool_type) == selected_filter

    @staticmethod
    def _log_filter_label(selected_filter: str) -> str:
        for label, value in LOG_FILTER_OPTIONS:
            if value == selected_filter:
                return label
        return "对应"

    def _log_row_html(self, log: ActivityLog) -> str:
        pool_key = self._log_pool_key(log.pool_type)
        colors = LOG_COLORS.get(pool_key, LOG_COLORS[LOG_FILTER_OTHER])
        label = escape(self._pool_label(log.pool_type))
        text = escape(log.format_display())
        return (
            "<div style='"
            "margin:0 0 10px 0; padding:7px 8px; border-radius:6px; "
            f"border-left:2px solid {colors['accent']}; background:{colors['bg']};"
            "'>"
            f"<span style='color:{colors['accent']}; font-weight:700;'>[{label}]</span>"
            f"<span style='color:{colors['text']};'> {text}</span>"
            "</div>"
        )

    @staticmethod
    def _pool_label(pool_type: str) -> str:
        mapping = {POOL_RANDOM: "随机", POOL_FAMILY: "家族", POOL_ELEMENT: "属性", POOL_UNKNOWN: "其他"}
        return mapping.get(pool_type, "其他")

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
        if not slot or self._selected_shiny_index is None:
            return
        if self._confirm("确定删除这条异色记录吗？") and slot.delete_shiny_record(self._selected_shiny_index):
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
