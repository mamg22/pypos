from datetime import datetime
from pathlib import Path
import sys
from typing import cast

from PySide6 import QtCore, QtWidgets, QtSql

from . import inventory, settings
from .cart import CartWidget
from .reports import ReportsWindow
from . import resources as resources  # Only for the side effects


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.inventory = inventory.InventoryWidget()
        self.cart = CartWidget()

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.tabBar().setExpanding(True)
        self.tabs.tabBar().setDocumentMode(True)

        self.tabs.addTab(self.inventory, "&Inventario")
        self.tabs.addTab(self.cart, "&Carrito")

        self.setCentralWidget(self.tabs)

        self.exchange_rate = QtWidgets.QLabel()
        rate_font = self.exchange_rate.font()
        rate_font.setPointSize(rate_font.pointSize() + 2)
        self.exchange_rate.setFont(rate_font)
        self.update_rate()

        self.rate_check_timer = QtCore.QTimer(self)
        self.rate_check_timer.timeout.connect(self.update_rate)
        # Every 30 minutes
        self.rate_check_timer.start(30 * 60 * 1000)

        self.statusBar().addPermanentWidget(self.exchange_rate, 1)

        app_menu = QtWidgets.QMenu("A&plicación")

        reports_action = app_menu.addAction("&Reportes...")
        reports_action.triggered.connect(self.show_reports)
        exit_action = app_menu.addAction("&Salir")
        exit_action.triggered.connect(self.bye)

        options_menu = QtWidgets.QMenu("&Opciones")
        rate_action = options_menu.addAction("&Tasa de cambio...")
        rate_action.triggered.connect(self.show_rate_window)
        settings_action = options_menu.addAction("&Configuración...")
        settings_action.triggered.connect(self.show_settings_window)

        self.menuBar().addMenu(app_menu)
        self.menuBar().addMenu(options_menu)

        self.inventory.cart_item.connect(self.cart.refresh)
        self.inventory.view_in_cart.connect(self.cart.view_in_cart)
        self.inventory.view_in_cart.connect(self.show_cart)

        self.cart.sale_completed.connect(self.inventory.refresh)
        self.cart.item_deleted.connect(self.inventory.refresh)
        self.cart.item_updated.connect(self.inventory.update_item)
        self.cart.view_in_inventory.connect(self.focus_inventory_item)

    @QtCore.Slot()
    def update_rate(self) -> None:
        settings = QtCore.QSettings()
        value = str(settings.value("USD-VED-rate", 0))
        last_update = cast(str | None, settings.value("last-rate-update", None))

        WARN_STYLE = "QLabel {color: red;}"

        label = "Tasa dólar: "

        if last_update is not None:
            last_update = int(last_update)

            last_update_date = datetime.fromtimestamp(last_update)

            locale = QtCore.QLocale()
            date = locale.toString(
                QtCore.QDateTime.fromSecsSinceEpoch(last_update).date(),
                QtCore.QLocale.FormatType.ShortFormat,
            )

            label += f"{value} Bs, {date}"

            if last_update_date.date() < datetime.now().date():
                self.exchange_rate.setStyleSheet(WARN_STYLE)
                label += " (Desactualizada)"
            else:
                self.exchange_rate.setStyleSheet("")
        else:
            label += "No establecido"
            self.exchange_rate.setStyleSheet(WARN_STYLE)

        self.exchange_rate.setText(label)

    @QtCore.Slot()
    def show_rate_window(self) -> None:
        rate_dialog = settings.ExchangeRateWindow()
        result = rate_dialog.exec()
        if result == rate_dialog.DialogCode.Accepted:
            self.update_rate()
            self.inventory.refresh()
            self.cart.do_refresh()

    @QtCore.Slot()
    def show_settings_window(self) -> None:
        settings_dialog = settings.SettingsWindow()
        result = settings_dialog.exec()
        if result == settings_dialog.DialogCode.Accepted:
            pass

    @QtCore.Slot(int)
    def focus_inventory_item(self, product_id: int) -> None:
        self.inventory.focus_inventory_item(product_id)
        self.tabs.setCurrentWidget(self.inventory)

    @QtCore.Slot()
    def show_cart(self) -> None:
        self.tabs.setCurrentWidget(self.cart)

    @QtCore.Slot()
    def show_reports(self) -> None:
        reports_window = ReportsWindow()
        reports_window.exec()

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
    sell_currency TEXT NOT NULL,
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
    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName("mamg22")
    app.setApplicationName("pypos")

    translator = QtCore.QTranslator()
    translator.load(
        QtCore.QLocale(),
        "qtbase",
        "_",
        QtCore.QLibraryInfo.path(QtCore.QLibraryInfo.LibraryPath.TranslationsPath),
    )
    app.installTranslator(translator)

    appdata_dir = Path(
        QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.StandardLocation.AppDataLocation
        )
    )
    appdata_dir.mkdir(parents=True, exist_ok=True)

    db_file = appdata_dir / "products.db"

    db = QtSql.QSqlDatabase.addDatabase("QSQLITE")
    db.setDatabaseName(str(db_file))

    if not db.open():
        QtWidgets.QMessageBox.critical(
            QtWidgets.QWidget(),
            "Error de base de datos",
            """\
            <html>Error al conectar con la base de datos. Verifique si:
                <ul>
                    <li>Tiene espacio disponible el dispositivo</li>
                    <li>Los directorios de datos de aplicación
                    estén disponibles para escritura.</li>
                </ul>
            </html>
            """,
        )
        return
    else:
        build_database()

    main_window = MainWindow()

    main_window.resize(800, 600)
    main_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
