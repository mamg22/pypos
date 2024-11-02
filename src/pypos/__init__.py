from decimal import Decimal
import sqlite3
import sys

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt

conn = sqlite3.connect(":memory:")

conn.executescript("""\
CREATE TABLE IF NOT EXISTS Product (
    name TEXT NOT NULL,
    value INTEGER NOT NULL,
    currency TEXT NOT NULL,
    margin INTEGER NOT NULL,
    price INTEGER NOT NULL,
    last_update INTEGER NOT NULL
);
INSERT INTO Product VALUES
    ('Harina', 200, 'USD', '1000', 220, unixepoch()),
    ('Cafe', 200, 'USD', '1000', 220, unixepoch()),
    ('Azucar', 200, 'USD', '1000', 220, unixepoch()),
    ('Arroz', 200, 'USD', '1000', 220, unixepoch()),
    ('Spaghetti', 200, 'USD', '1000', 220, unixepoch()),
    ('Sal', 200, 'USD', '1000', 220, unixepoch()),
    ('Harina de trigo', 200, 'USD', '1000', 220, unixepoch()),
    ('Cerelac', 200, 'USD', '1000', 220, unixepoch()),
    ('Jabon', 200, 'USD', '1000', 220, unixepoch());
""")


class ProductPreviewWidget(QtWidgets.QFrame):
    def __init__(self) -> None:
        super().__init__()

        self.setLineWidth(1)
        self.setFrameShape(type(self).Shape.StyledPanel)

        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), palette.base().color())
        self.setPalette(palette)

        grid = QtWidgets.QGridLayout()
        self.grid = grid
        self.setLayout(grid)

        self.name_label = QtWidgets.QLabel()

        name_font = self.name_label.font()
        name_font.setPointSize(name_font.pointSize() + 1)
        name_font.setBold(True)
        self.name_label.setFont(name_font)

        self.price_label = QtWidgets.QLabel()
        self.quantity_label = QtWidgets.QLabel()

        self.grid.addWidget(self.name_label, 0, 0)
        self.grid.addWidget(
            self.price_label, 0, 1, alignment=Qt.AlignmentFlag.AlignRight
        )
        self.grid.addWidget(self.quantity_label, 1, 0)

    @QtCore.Slot(tuple)
    def show_product(self, product: tuple):
        _, name, quantity, price, _ = product

        self.name_label.setText(f"{name}")
        self.price_label.setText(str(price))
        self.quantity_label.setText(f"Cantidad: {quantity}")


class InventoryWidget(QtWidgets.QWidget):
    selected = QtCore.Signal(tuple)

    def __init__(self) -> None:
        super().__init__()

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        inventory_table = QtWidgets.QTableWidget(0, 4, self)
        self.inventory_table = inventory_table
        inventory_table.setColumnCount(4)
        inventory_table.setHorizontalHeaderLabels(["Item", "Cantidad", "$", "Bs"])
        inventory_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        inventory_table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        inventory_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Fixed
        )
        inventory_table.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        inventory_table.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Fixed
        )

        n_rows = conn.execute("SELECT COUNT() FROM Product").fetchone()[0]

        inventory_table.setRowCount(n_rows)

        cur = conn.execute(
            "SELECT rowid, name, abs(random() % 50), price*rowid, price*rowid*42.60 FROM Product"
        )

        ItemFlag = Qt.ItemFlag
        row_flags = ItemFlag.ItemIsSelectable | ItemFlag.ItemIsEnabled
        number_align = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight

        for row_num, row in enumerate(cur.fetchall()):
            for idx, value in enumerate(row[1:]):
                item = QtWidgets.QTableWidgetItem(str(value))

                if isinstance(value, int | float | Decimal):
                    item.setTextAlignment(number_align)
                item.setFlags(row_flags)
                item.setData(Qt.ItemDataRole.UserRole, row)

                inventory_table.setItem(row_num, idx, item)

        self.inventory_table.itemSelectionChanged.connect(self.activated)

        self.layout().addWidget(inventory_table)
        self.preview = ProductPreviewWidget()
        self.layout().addWidget(self.preview)

        self.selected.connect(self.preview.show_product)

    @QtCore.Slot()
    def activated(self):
        d = self.inventory_table.selectedItems()[0].data(Qt.ItemDataRole.UserRole)
        self.selected.emit(d)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        panes = {
            "Inventario": InventoryWidget(),
            "Carrito": QtWidgets.QWidget(),
        }

        self.stack = QtWidgets.QTabWidget()
        self.stack.tabBar().setExpanding(True)
        self.stack.tabBar().setDocumentMode(True)

        for name, widget in panes.items():
            self.stack.addTab(widget, name)

        self.setCentralWidget(self.stack)

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
