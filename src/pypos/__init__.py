from decimal import Decimal
import sqlite3
import sys

from PySide6 import QtCore, QtWidgets, QtSql

from pypos import inventory


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.inventory = inventory.InventoryWidget()
        self.cart = QtWidgets.QWidget()

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.tabBar().setExpanding(True)
        self.tabs.tabBar().setDocumentMode(True)

        self.tabs.addTab(self.inventory, "Inventario")
        self.tabs.addTab(self.cart, "Carrito")

        self.setCentralWidget(self.tabs)

        self.exchange_rate = QtWidgets.QLabel("$ BCV: 42.89 Bs")
        rate_font = self.exchange_rate.font()
        rate_font.setPointSize(rate_font.pointSize() + 2)
        self.exchange_rate.setFont(rate_font)

        self.statusBar().addPermanentWidget(self.exchange_rate, 1)

        file_menu = QtWidgets.QMenu("File")
        file_menu.addAction("Save")
        file_menu.addSeparator()
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.bye)
        self.menuBar().addMenu(file_menu)

    @QtCore.Slot()
    def bye(self):
        self.close()


def main() -> None:
    app = QtWidgets.QApplication([])

    main_window = MainWindow()
    main_window.resize(800, 600)
    main_window.show()

    sys.exit(app.exec())
