from datetime import datetime
import sys
from typing import cast

from PySide6 import QtCore, QtWidgets, QtSql

from . import inventory, settings
from .cart import CartWidget


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.inventory = inventory.InventoryWidget()
        self.cart = CartWidget()

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.tabBar().setExpanding(True)
        self.tabs.tabBar().setDocumentMode(True)

        self.tabs.addTab(self.inventory, "Inventario")
        self.tabs.addTab(self.cart, "Carrito")

        self.setCentralWidget(self.tabs)

        self.exchange_rate = QtWidgets.QLabel()
        rate_font = self.exchange_rate.font()
        rate_font.setPointSize(rate_font.pointSize() + 2)
        self.exchange_rate.setFont(rate_font)
        self.update_rate()

        self.statusBar().addPermanentWidget(self.exchange_rate, 1)

        app_menu = QtWidgets.QMenu("Aplicación")
        exit_action = app_menu.addAction("Salir")
        exit_action.triggered.connect(self.bye)

        options_menu = QtWidgets.QMenu("Opciones")
        settings_action = options_menu.addAction("Tasa de cambio...")
        settings_action.triggered.connect(self.show_rate_window)

        self.menuBar().addMenu(app_menu)
        self.menuBar().addMenu(options_menu)

        self.inventory.cart_item.connect(self.cart.refresh)
        self.inventory.view_in_cart.connect(self.cart.view_in_cart)
        self.inventory.view_in_cart.connect(self.show_cart)

        self.cart.sale_completed.connect(self.inventory.refresh)
        self.cart.view_in_inventory.connect(self.focus_inventory_item)

    @QtCore.Slot()
    def update_rate(self) -> None:
        settings = QtCore.QSettings()
        value = str(settings.value("USD-VED-rate", 0))
        last_update = cast(float | None, settings.value("last-rate-update", None))
        if last_update is not None:
            last_update_date = datetime.fromtimestamp(float(last_update))
            self.exchange_rate.setText(
                f"Tasa dólar: {value} Bs, {last_update_date:%d de %B %Y}"
            )
        else:
            self.exchange_rate.setText("Tasa dólar: No establecido")

    @QtCore.Slot()
    def show_rate_window(self) -> None:
        rate_dialog = settings.ExchangeRateWindow()
        result = rate_dialog.exec()
        if result == rate_dialog.DialogCode.Accepted:
            self.update_rate()
            self.inventory.refresh()

    @QtCore.Slot(int)
    def focus_inventory_item(self, product_id: int) -> None:
        self.inventory.product_table.set_query(None)
        self.inventory.product_table.focus_product(product_id)
        self.tabs.setCurrentWidget(self.inventory)

    @QtCore.Slot()
    def show_cart(self) -> None:
        self.tabs.setCurrentWidget(self.cart)

    @QtCore.Slot()
    def bye(self):
        self.close()


SCHEMA: list[str] = [
    "PRAGMA foreign_keys = on;",
    """\
CREATE TABLE IF NOT EXISTS Products (
    id INTEGER PRIMARY KEY NOT NULL,
    name TEXT NOT NULL UNIQUE,
    name_simplified TEXT NOT NULL UNIQUE,
    purchase_currency TEXT NOT NULL,
    purchase_value INTEGER NOT NULL,
    sell_currency INTEGER NOT NULL,
    sell_value INTEGER NOT NULL,
    last_update INTEGER NOT NULL DEFAULT (unixepoch())
);
""",
    """\
CREATE TABLE IF NOT EXISTS Inventory (
    product INTEGER NOT NULL PRIMARY KEY,
    quantity INTEGER NOT NULL,
    FOREIGN KEY (product) REFERENCES Products(id)
        ON DELETE CASCADE
);
""",
    """\
CREATE TABLE IF NOT EXISTS Cart (
    product INTEGER NOT NULL PRIMARY KEY,
    quantity INTEGER NOT NULL,
    FOREIGN KEY (product) REFERENCES Products(id)
        ON DELETE RESTRICT
);
""",
]


def build_database() -> None:
    for statement in SCHEMA:
        schema_query = QtSql.QSqlQuery()
        if not schema_query.exec(statement):
            print(schema_query.lastError().text())


def main() -> None:
    app = QtWidgets.QApplication([])
    app.setOrganizationName("m2software")
    app.setApplicationName("pypos")

    db = QtSql.QSqlDatabase.addDatabase("QSQLITE")
    db.setDatabaseName("./products.db")
    db.open()

    build_database()

    main_window = MainWindow()
    main_window.resize(800, 600)
    main_window.show()

    sys.exit(app.exec())
