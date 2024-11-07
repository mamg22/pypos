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


SCHEMA: str = """\
DROP TABLE IF EXISTS Products;
DROP TABLE IF EXISTS Inventory;
CREATE TABLE IF NOT EXISTS Products (
    name TEXT NOT NULL,
    value INTEGER NOT NULL,
    currency TEXT NOT NULL,
    margin INTEGER NOT NULL,
    price INTEGER NOT NULL,
    last_update INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS Inventory (
    product INTEGER NOT NULL,
    quantity INTEGER NOT NULL
);
INSERT INTO Products VALUES
    ('Harina', 200, 'USD', '1000', 220, unixepoch()),
    ('Cafe', 200, 'USD', '1000', 220, unixepoch()),
    ('Azucar', 200, 'USD', '1000', 220, unixepoch()),
    ('Arroz', 200, 'USD', '1000', 220, unixepoch()),
    ('Spaghetti', 200, 'USD', '1000', 220, unixepoch()),
    ('Sal', 200, 'USD', '1000', 220, unixepoch()),
    ('Harina de trigo', 200, 'USD', '1000', 220, unixepoch()),
    ('Cerelac', 200, 'USD', '1000', 220, unixepoch()),
    ('Jabon', 200, 'USD', '1000', 220, unixepoch());
INSERT INTO Inventory VALUES
    (1, 5),
    (2, 10),
    (3, 15),
    (4, 20),
    (5, 25),
    (6, 30),
    (7, 35),
    (8, 40),
    (9, 50);
"""


def build_database() -> None:
    for statement in filter(lambda x: x.strip(), SCHEMA.split(";")):
        schema_query = QtSql.QSqlQuery()
        if not schema_query.exec(statement):
            print(schema_query.lastError().text())


def main() -> None:
    app = QtWidgets.QApplication([])

    db = QtSql.QSqlDatabase.addDatabase("QSQLITE")
    db.setDatabaseName("./products.db")
    db.open()

    build_database()

    main_window = MainWindow()
    main_window.resize(800, 600)
    main_window.show()

    sys.exit(app.exec())
