"""Qt 主题样式。"""

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

QTextEdit#logPanel {
    background: #15171c;
    border: none;
    border-left: 1px solid #2a2f38;
    color: #8f9aaa;
    padding: 10px;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 12px;
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
    padding: 7px 9px;
    color: #e8ecf2;
    selection-background-color: #365d9d;
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
    border-color: #4b7cc9;
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
}

QListWidget {
    font-size: 14px;
}

QTreeWidget::item,
QListWidget::item,
QTableWidget::item {
    padding: 7px;
}

QTreeWidget::item:selected,
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
    background: #2a2f38;
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
"""
