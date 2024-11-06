from decimal import Decimal
import sqlite3

from PySide6 import QtCore, QtWidgets
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


class InventoryTopBar(QtWidgets.QWidget):
    new_product = QtCore.Signal()
    search_submitted = QtCore.Signal(str)

    def __init__(self) -> None:
        super().__init__()

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)

        new_button = QtWidgets.QPushButton("Nuevo")
        self.new_button = new_button

        new_button.clicked.connect(self.emit_new)

        search_bar = QtWidgets.QLineEdit()
        self.search_bar = search_bar
        search_bar.editingFinished.connect(self.search_edit_finished)

        layout.addWidget(new_button)
        layout.addStretch()
        layout.addWidget(QtWidgets.QLabel("Buscar:"))
        layout.addWidget(search_bar)

    @QtCore.Slot()
    def emit_new(self) -> None:
        self.new_product.emit()

    @QtCore.Slot()
    def search_edit_finished(self):
        text = self.search_bar.text()
        self.search_submitted.emit(text)


class ProductInfoDialog(QtWidgets.QDialog):
    def __init__(self) -> None:
        super().__init__()

        layout = QtWidgets.QVBoxLayout()

        form_layout = QtWidgets.QFormLayout()

        self.name = QtWidgets.QLineEdit()
        self.name.setMinimumWidth(300)
        form_layout.addRow("Nombre:", self.name)

        self.currency = QtWidgets.QComboBox()
        self.currency.addItems(["Bs", "$"])

        form_layout.addRow("Moneda:", self.currency)

        layout.addLayout(form_layout)

        self.setLayout(layout)

        SB = QtWidgets.QDialogButtonBox.StandardButton
        buttons = QtWidgets.QDialogButtonBox(SB.Ok | SB.Cancel | SB.Reset)

        buttons.accepted.connect(self.accepted)
        buttons.rejected.connect(self.rejected)
        buttons.button(SB.Reset).clicked.connect(self.on_reset)

        layout.addWidget(buttons)

        self.accepted.connect(self.on_accept)
        self.rejected.connect(self.on_reject)

    @QtCore.Slot()
    def on_accept(self):
        name = self.name.text()
        currency = self.currency.currentText()

        print(name, currency)

        self.close()

    @QtCore.Slot()
    def on_reject(self):
        self.close()

    @QtCore.Slot()
    def on_reset(self):
        self.name.clear()
        self.currency.setCurrentIndex(0)


class ProductPreviewWidget(QtWidgets.QFrame):
    current_id: int | None

    def __init__(self) -> None:
        super().__init__()

        self.current_id = None

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

        self.show_product(None)

    @QtCore.Slot(int)
    @QtCore.Slot(type(None))
    def show_product(self, id: int | None):
        self.current_id = id
        self.show()
        cur = conn.execute("SELECT name, 10, price FROM Product WHERE rowid = ?", (id,))

        result = cur.fetchone()

        if result is not None:
            name, quantity, price = result

            self.name_label.setText(f"{name}")
            self.price_label.setText(str(price))
            self.quantity_label.setText(f"Cantidad: {quantity}")
        else:
            self.hide()


class ProductTable(QtWidgets.QTableWidget):
    selected = QtCore.Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(0, 4, parent)

        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Item", "Cantidad", "$", "Bs"])
        self.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Fixed
        )
        self.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Fixed
        )

        self.itemSelectionChanged.connect(self.row_selected)

        self.refresh_table()

    @QtCore.Slot(str)
    @QtCore.Slot(type(None))
    def refresh_table(self, query: str | None = None):
        q = "WHERE name LIKE '%' || ? || '%'" if query is not None else ""
        p = (query,) if query is not None else tuple()

        n_rows = conn.execute("SELECT COUNT() FROM Product " + q, p).fetchone()[0]

        self.setRowCount(n_rows)

        cur = conn.execute(
            "SELECT rowid, name, abs(random() % 50), price*rowid, price*rowid*42.60 "
            "FROM Product " + q,
            p,
        )

        ItemFlag = Qt.ItemFlag
        row_flags = ItemFlag.ItemIsSelectable | ItemFlag.ItemIsEnabled
        number_align = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight

        for row_num, row in enumerate(cur.fetchall()):
            row_id = row[0]
            for idx, value in enumerate(row[1:]):
                item = QtWidgets.QTableWidgetItem(str(value))

                if isinstance(value, int | float | Decimal):
                    item.setTextAlignment(number_align)
                item.setFlags(row_flags)
                item.setData(Qt.ItemDataRole.UserRole, row_id)

                self.setItem(row_num, idx, item)

    @QtCore.Slot()
    def row_selected(self):
        try:
            item_id = self.selectedItems()[0].data(Qt.ItemDataRole.UserRole)
            self.selected.emit(item_id)
        except IndexError:
            self.selected.emit(None)


class InventoryWidget(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        topbar = InventoryTopBar()
        topbar.new_product.connect(self.new)
        topbar.search_submitted.connect(self.log_search)

        product_table = ProductTable(self)
        self.product_table = product_table

        topbar.search_submitted.connect(self.product_table.refresh_table)

        self.layout().addWidget(topbar)
        self.layout().addWidget(product_table)
        self.preview = ProductPreviewWidget()
        self.layout().addWidget(self.preview)

        self.product_table.selected.connect(self.preview.show_product)

    @QtCore.Slot(str)
    def log_search(self, query: str):
        print(query)

    @QtCore.Slot()
    def new(self):
        w = ProductInfoDialog()
        w.exec()
