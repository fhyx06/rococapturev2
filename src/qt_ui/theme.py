"""Qt 主题样式。"""
from pathlib import Path


_CHEVRON_DOWN_ICON = (
    Path(__file__).resolve().parents[1] / "assets" / "icons" / "chevron_down.svg"
).as_posix()
_CHEVRON_RIGHT_ICON = (
    Path(__file__).resolve().parents[1] / "assets" / "icons" / "chevron_right.svg"
).as_posix()

APP_STYLESHEET = """
QMainWindow,
QDialog {
    background: #181a1f;
    color: #dce2ea;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}

QDialog QWidget,
QDialog QLabel,
QDialog QCheckBox {
    color: #dce2ea;
}

QDialog QComboBox,
QDialog QLineEdit,
QDialog QSpinBox {
    min-height: 28px;
}

QDialog QPushButton {
    min-width: 72px;
}

QDialog {
    border: 1px solid #303746;
}

QWidget#appRoot,
QWidget#pageStack {
    background: #1b1e24;
}

QWidget#topBar {
    background: #181a1f;
}

QWidget#divider {
    background: #2a2f38;
}

QLabel#brandLabel {
    color: #78a9ff;
    font-size: 19px;
    font-weight: 700;
}

QLabel#topBarLabel {
    color: #aab4c3;
    font-size: 13px;
}

QLabel#pageHeader {
    color: #eef3f8;
    font-size: 20px;
    font-weight: 700;
}

QLabel#mutedLabel {
    color: #8e98a8;
    font-size: 14px;
}

QListWidget#sidebar {
    background: #111318;
    border: none;
    padding: 12px 10px;
    color: #aeb8c7;
    outline: 0;
    font-size: 14px;
}

QListWidget#sidebar::item {
    min-height: 44px;
    padding: 8px 10px;
    border-radius: 10px;
}

QListWidget#sidebar::item:hover {
    background: #1c222b;
    color: #eef3f8;
}

QListWidget#sidebar::item:selected {
    background: #243044;
    color: #ffffff;
}

QWidget#logColumn {
    background: #15171c;
    border-left: 1px solid #2a2f38;
}

QLabel#logTitle {
    color: #eef3f8;
    font-size: 13px;
    font-weight: 700;
    border: none;
}

QComboBox#logFilterCombo {
    min-width: 78px;
    min-height: 24px;
    padding: 3px 26px 3px 9px;
}

QTextEdit#logPanel {
    background: transparent;
    border: none;
    color: #8f9aaa;
    padding: 0 2px 0 0;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 12px;
    line-height: 140%;
}

QWidget#counterCard {
    background: #20242b;
    border: 1px solid #303746;
    border-radius: 16px;
}

QLabel#counterTitle {
    color: #8e98a8;
    font-size: 13px;
    border: none;
}

QLabel#counterValue {
    color: #e8ecf2;
    font-size: 64px;
    font-weight: 700;
    border: none;
}

QLabel#counterValue[state="warn"] {
    color: #f39c12;
}

QLabel#counterValue[state="critical"] {
    color: #e74c3c;
}

QLineEdit,
QComboBox,
QSpinBox {
    background: #20242b;
    border: 1px solid #303746;
    border-radius: 7px;
    color: #e8ecf2;
    selection-background-color: #365d9d;
}

QLineEdit,
QSpinBox {
    padding: 7px 9px;
}

QComboBox {
    padding: 7px 30px 7px 9px;
}

QComboBox::drop-down {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid #303746;
    border-top-right-radius: 7px;
    border-bottom-right-radius: 7px;
    background: transparent;
}

QComboBox::down-arrow {
    image: url("__CHEVRON_DOWN_ICON__");
    width: 9px;
    height: 9px;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background: #20242b;
    border: 1px solid #303746;
    color: #e8ecf2;
    selection-background-color: #28364c;
    selection-color: #ffffff;
    padding: 4px;
}

QLineEdit:focus,
QComboBox:focus,
QSpinBox:focus {
    border-color: #465164;
}

QComboBox:focus::drop-down {
    border-left-color: #465164;
}

QComboBox#saveCombo:focus {
    border-color: #384151;
}

QComboBox#saveCombo:focus::drop-down {
    border-left-color: #384151;
}

QPushButton {
    background: #252b35;
    border: 1px solid #384151;
    border-radius: 7px;
    color: #dce2ea;
    padding: 7px 12px;
}

QPushButton:hover {
    background: #2d3542;
    border-color: #48566a;
}

QPushButton:pressed {
    background: #202631;
}

QPushButton[role="increase"] {
    background: #1d3328;
    border-color: #2f7d57;
    color: #bff4d2;
    font-size: 18px;
    padding: 10px 24px;
}

QPushButton[role="decrease"] {
    background: #372226;
    border-color: #8a3a46;
    color: #ffccd3;
    font-size: 18px;
    padding: 10px 24px;
}

QPushButton[role="reset"] {
    background: #252b35;
    border-color: #465164;
    color: #dce2ea;
    font-size: 18px;
    padding: 10px 18px;
}

QPushButton[role="shiny"] {
    background: #b7791f;
    border-color: #e0a536;
    color: #fff8e6;
    font-size: 18px;
    font-weight: 700;
    padding: 10px 18px;
}

QPushButton[role="shiny"]:hover {
    background: #c98923;
}

QPushButton[compact="true"] {
    min-width: 96px;
    min-height: 36px;
    font-size: 15px;
    padding: 8px 10px;
}

QTreeWidget,
QListWidget,
QTableWidget {
    background: #20242b;
    alternate-background-color: #1c2027;
    border: 1px solid #303746;
    border-radius: 10px;
    color: #dce2ea;
    outline: 0;
}

QTreeWidget {
    font-size: 14px;
    padding: 6px 4px 6px 6px;
}

QTreeWidget::branch {
    background: transparent;
}

QTreeWidget::branch:hover {
    background: #242a34;
}

QTreeWidget::branch:selected {
    background: #28364c;
}

QTreeWidget::branch:has-children:closed {
    image: url("__CHEVRON_RIGHT_ICON__");
}

QTreeWidget::branch:has-children:open {
    image: url("__CHEVRON_DOWN_ICON__");
}

QTreeWidget::item {
    padding: 0;
    border: 0;
    background: transparent;
}

QTreeWidget::item:hover {
    background: #242a34;
}

QTreeWidget::item:selected {
    background: #28364c;
    color: #ffffff;
}

QListWidget {
    font-size: 14px;
}

QWidget#familySpiritCell {
    background: transparent;
}

QWidget#familySeasonCell {
    background: transparent;
}

QLabel#familySeasonLabel {
    color: #eef3f8;
    font-size: 14px;
    font-weight: 700;
    border: none;
}

QLabel#familySpiritNo {
    color: #8e98a8;
    font-size: 11px;
    border: none;
}

QLabel#familySpiritName {
    color: #eef3f8;
    font-size: 14px;
    font-weight: 700;
    border: none;
}

QLabel#familySpiritElements {
    color: #aeb8c7;
    font-size: 12px;
    border: none;
}

QLabel#familyPityCount {
    color: #eef3f8;
    font-size: 16px;
    font-weight: 700;
    border: none;
}

QLabel#familyPityCount[state="warn"] {
    color: #f39c12;
}

QLabel#familyPityCount[state="critical"] {
    color: #e74c3c;
}

QWidget#elementGridPanel {
    background: #20242b;
    border: 1px solid #303746;
    border-radius: 10px;
}

QPushButton[role="elementCard"] {
    background: #252b35;
    border: 1px solid #384151;
    border-radius: 10px;
    color: #dce2ea;
    padding: 8px 12px;
    text-align: left;
    font-size: 14px;
    font-weight: 600;
}

QPushButton[role="elementCard"]:hover {
    background: #242a34;
    border-color: #48566a;
}

QPushButton[role="elementCard"]:checked {
    background: #28364c;
    border-color: #5d88cf;
    color: #ffffff;
}

QPushButton[role="elementCard"][state="warn"] {
    color: #f3b34b;
    border-color: #9a6c2e;
}

QPushButton[role="elementCard"][state="critical"] {
    color: #ff8e8e;
    border-color: #a84b4b;
}

QWidget#shinyColumn {
    background: #20242b;
    border: 1px solid #303746;
    border-radius: 10px;
}

QLabel#shinyColumnTitle {
    color: #eef3f8;
    font-size: 15px;
    font-weight: 700;
    border: none;
}

QScrollArea#shinyScroll,
QWidget#shinyColumnContent {
    background: transparent;
    border: none;
}

QScrollArea#shinyScroll QScrollBar:horizontal,
QTreeWidget#familyTree QScrollBar:horizontal,
QTextEdit#logPanel QScrollBar:horizontal {
    height: 0;
    background: transparent;
    border: none;
}

QScrollArea#shinyScroll QScrollBar:vertical,
QTreeWidget#familyTree QScrollBar:vertical,
QTextEdit#logPanel QScrollBar:vertical {
    background: transparent;
    border: none;
    width: 6px;
    margin: 0;
}

QScrollArea#shinyScroll QScrollBar::handle:vertical,
QTreeWidget#familyTree QScrollBar::handle:vertical,
QTextEdit#logPanel QScrollBar::handle:vertical {
    background: transparent;
    border-radius: 3px;
    min-height: 28px;
}

QScrollArea#shinyScroll QScrollBar::add-page:vertical,
QScrollArea#shinyScroll QScrollBar::sub-page:vertical,
QScrollArea#shinyScroll QScrollBar::groove:vertical,
QTreeWidget#familyTree QScrollBar::add-page:vertical,
QTreeWidget#familyTree QScrollBar::sub-page:vertical,
QTreeWidget#familyTree QScrollBar::groove:vertical,
QTextEdit#logPanel QScrollBar::add-page:vertical,
QTextEdit#logPanel QScrollBar::sub-page:vertical,
QTextEdit#logPanel QScrollBar::groove:vertical {
    background: transparent;
    border: none;
}

QScrollArea#shinyScroll QScrollBar::add-line:vertical,
QScrollArea#shinyScroll QScrollBar::sub-line:vertical,
QTreeWidget#familyTree QScrollBar::add-line:vertical,
QTreeWidget#familyTree QScrollBar::sub-line:vertical,
QTextEdit#logPanel QScrollBar::add-line:vertical,
QTextEdit#logPanel QScrollBar::sub-line:vertical {
    background: transparent;
    border: none;
    height: 0;
    width: 0;
}

QScrollArea#shinyScroll QScrollBar::up-arrow:vertical,
QScrollArea#shinyScroll QScrollBar::down-arrow:vertical,
QTreeWidget#familyTree QScrollBar::up-arrow:vertical,
QTreeWidget#familyTree QScrollBar::down-arrow:vertical,
QTextEdit#logPanel QScrollBar::up-arrow:vertical,
QTextEdit#logPanel QScrollBar::down-arrow:vertical {
    background: transparent;
    border: none;
    height: 0;
    width: 0;
}

QScrollArea#shinyScroll[scrollHover="true"] QScrollBar::handle:vertical,
QTreeWidget#familyTree[scrollHover="true"] QScrollBar::handle:vertical,
QTextEdit#logPanel[scrollHover="true"] QScrollBar::handle:vertical {
    background: #34404f;
}

QScrollArea#shinyScroll QScrollBar::handle:vertical:hover,
QTreeWidget#familyTree QScrollBar::handle:vertical:hover,
QTextEdit#logPanel QScrollBar::handle:vertical:hover {
    background: #4a5a70;
}

QWidget#shinyRecordCard {
    background: #252b35;
    border: 1px solid #384151;
    border-radius: 8px;
    min-height: 58px;
}

QWidget#shinyRecordCard:hover {
    background: #2a313d;
    border-color: #506079;
}

QWidget#shinyRecordCard[selected="true"] {
    background: #28364c;
    border-color: #6d99df;
}

QWidget#shinyRecordCard[pool="random"] {
    border-left: 3px solid #78a9ff;
}

QWidget#shinyRecordCard[pool="family"] {
    border-left: 3px solid #f3b34b;
}

QWidget#shinyRecordCard[pool="element"] {
    border-left: 3px solid #52d6b1;
}

QWidget#shinyRecordCard[pool="unknown"] {
    border-left: 3px solid #8e98a8;
}

QLabel#shinyCardIcon {
    border: none;
}

QLabel#shinyCardTitle {
    color: #eef3f8;
    font-size: 14px;
    font-weight: 700;
    border: none;
}

QLabel#shinyCardMeta {
    color: #aeb8c7;
    font-size: 12px;
    border: none;
}

QLabel#shinyPityValue {
    color: #74d99f;
    font-size: 28px;
    font-weight: 800;
    border: none;
    min-width: 42px;
}

QLabel#shinyPityValue[state="warn"] {
    color: #f3b34b;
}

QLabel#shinyPityValue[state="critical"] {
    color: #ff8e8e;
}

QLabel#shinyPityLabel {
    color: #7f8a9a;
    font-size: 11px;
    border: none;
}

QLabel#shinyEmptyLabel {
    color: #6f7a8a;
    border: 1px dashed #384151;
    border-radius: 8px;
    padding: 22px 8px;
}

QListWidget::item,
QTableWidget::item {
    padding: 7px;
}

QListWidget::item:selected,
QTableWidget::item:selected {
    background: #28364c;
    color: #ffffff;
}

QHeaderView::section {
    background: #252b35;
    border: 0;
    border-bottom: 1px solid #303746;
    border-right: 1px solid #303746;
    color: #9da8b8;
    padding: 7px 8px;
    font-weight: 600;
}

QTableView QTableCornerButton::section,
QTableCornerButton::section {
    background: #252b35;
    border: 0;
}

QTableCornerButton::section {
    background: #252b35;
    border: 0;
    border-bottom: 1px solid #303746;
    border-right: 1px solid #303746;
}

QSplitter::handle {
    background: #1b1e24;
    border-left: 1px solid #252b35;
    border-right: 1px solid #252b35;
}

QScrollBar:vertical,
QScrollBar:horizontal {
    background: #181a1f;
    border: none;
    width: 10px;
    height: 10px;
}

QScrollBar::handle:vertical,
QScrollBar::handle:horizontal {
    background: #3a4351;
    border-radius: 5px;
}

QScrollBar::add-line,
QScrollBar::sub-line {
    width: 0;
    height: 0;
}

QListWidget#sidebar QScrollBar:vertical,
QListWidget#sidebar QScrollBar:horizontal {
    width: 0;
    height: 0;
    background: transparent;
}

""".replace("__CHEVRON_DOWN_ICON__", _CHEVRON_DOWN_ICON).replace(
    "__CHEVRON_RIGHT_ICON__", _CHEVRON_RIGHT_ICON
)
