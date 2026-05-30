"""Qt 应用入口。"""
from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from src.models.constants import SAVES_DIR
from src.services.save_service import SaveService
from src.qt_ui.main_window import QtMainWindow
from src.qt_ui.theme import APP_STYLESHEET


def main() -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("RocoCaptureV2")
    app.setStyleSheet(APP_STYLESHEET)

    saves_dir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), SAVES_DIR)
    save_service = SaveService(saves_dir)
    if not save_service.list_saves():
        save_service.create_save("主账号")

    window = QtMainWindow(save_service)
    window.resize(1280, 780)
    window.show()
    sys.exit(app.exec())
