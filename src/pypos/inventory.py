from decimal import Decimal
from sys import float_info

from PySide6 import QtCore, QtWidgets, QtSql, QtGui
from PySide6.QtCore import Qt


LOCALE_DECIMAL_SEP = QtCore.QLocale().decimalPoint()
LOCALE_GROUP_SEP = QtCore.QLocale().groupSeparator()


class DecimalSpinBox(QtWidgets.QDoubleSpinBox):
    def validate(self, input: str, pos: int) -> object:
        if LOCALE_GROUP_SEP in input:
            return QtGui.QValidator.State.Invalid
        return super().validate(input, pos)

    def decimal_value(self) -> Decimal:
        value_text = self._fixup_decimal(self.cleanText())
        return Decimal(value_text)

    def _fixup_decimal(self, value: str) -> str:
        return value.replace(LOCALE_DECIMAL_SEP, ".", 1)


class InventoryTopBar(QtWidgets.QWidget):
    new_product = QtCore.Signal()
    search_submitted = QtCore.Signal(str)

    def __init__(self) -> None:
        super().__init__()

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout_margins = layout.contentsMargins()
        layout_margins.setLeft(0)
        layout_margins.setRight(0)
        layout_margins.setTop(0)
        layout.setContentsMargins(layout_margins)

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
    MAX_VALUE = 10 ** (float_info.dig - 3)
    CURRENCY_MAPPING = {
        "Bs": "BSD",
        "$": "USD",
    }
    INSERT_QUERY = """\
    INSERT INTO Products VALUES
        (:name, :purchase_currency, :purchase_value, :margin,
         :sell_currency, :sell_value, unixepoch())
    """

    def __init__(self) -> None:
        super().__init__()

        layout = QtWidgets.QVBoxLayout()

        form_layout = QtWidgets.QFormLayout()

        self.name = QtWidgets.QLineEdit()
        self.name.setMinimumWidth(300)
        form_layout.addRow("Nombre:", self.name)

        purchase_price_layout = QtWidgets.QHBoxLayout()

        self.purchase_currency = QtWidgets.QComboBox()
        self.purchase_currency.addItems(["Bs", "$"])

        self.purchase_value = DecimalSpinBox()
        self.purchase_value.setMaximum(self.MAX_VALUE)

        purchase_price_layout.addWidget(self.purchase_currency)
        purchase_price_layout.addWidget(self.purchase_value, 1)

        form_layout.addRow("Precio compra:", purchase_price_layout)

        sell_price_layout = QtWidgets.QHBoxLayout()

        self.margin = DecimalSpinBox()
        self.margin.setSuffix("%")
        self.margin.setMaximum(self.MAX_VALUE)
        form_layout.addRow("Margen:", self.margin)

        self.sell_currency = QtWidgets.QComboBox()
        self.sell_currency.addItems(["Bs", "$"])

        self.sell_value = DecimalSpinBox()
        self.sell_value.setMaximum(self.MAX_VALUE)

        sell_price_layout.addWidget(self.sell_currency)
        sell_price_layout.addWidget(self.sell_value, 1)

        form_layout.addRow("Precio venta:", sell_price_layout)

        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)

        form_layout.addRow(separator)

        self.quantity = QtWidgets.QSpinBox()
        self.quantity.setMaximum(1_000_000_000)

        form_layout.addRow("Existencias:", self.quantity)

        layout.addLayout(form_layout)

        self.setLayout(layout)

        SB = QtWidgets.QDialogButtonBox.StandardButton
        buttons = QtWidgets.QDialogButtonBox(SB.Ok | SB.Cancel | SB.Reset)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(SB.Reset).clicked.connect(self.on_reset)

        layout.addWidget(buttons)

    @QtCore.Slot()
    def accept(self):
        name = self.name.text()
        purchase_currency = self.purchase_currency.currentText()
        purchase_value = self.purchase_value.decimal_value()
        margin = self.margin.decimal_value()
        sell_currency = self.sell_currency.currentText()
        sell_value = self.sell_value.decimal_value()
        quantity = self.quantity.value()

        query = QtSql.QSqlQuery()
        query.prepare(self.INSERT_QUERY)

        query.bindValue(":name", name)
        query.bindValue(":purchase_currency", purchase_currency)
        query.bindValue(":purchase_value", int(purchase_value * 100))
        query.bindValue(":margin", int(margin * 100))
        query.bindValue(":sell_currency", sell_currency)
        query.bindValue(":sell_value", int(sell_value * 100))

        if not query.exec():
            print(query.lastError())

        item_id = query.lastInsertId()

        query = QtSql.QSqlQuery()
        query.prepare("INSERT INTO Inventory VALUES (:id, :quantity)")

        query.bindValue(":id", item_id)
        query.bindValue(":quantity", quantity)

        if not query.exec():
            print(query.lastError())

        super().accept()

    @QtCore.Slot()
    def on_reset(self):
        self.name.clear()
        self.purchase_currency.setCurrentIndex(0)
        self.purchase_value.setValue(0)
        self.margin.setValue(0)
        self.sell_currency.setCurrentIndex(0)
        self.sell_value.setValue(0)


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

        product_query = QtSql.QSqlQuery()
        prepared = product_query.prepare("""\
            SELECT name, quantity, sell_value
            FROM Products p
                INNER JOIN Inventory i
                ON p.rowid = i.product
            WHERE p.rowid = :id""")

        if not prepared:
            print(product_query.lastError())

        product_query.bindValue(":id", id)

        if not product_query.exec():
            print(product_query.lastError())

        if product_query.next():
            name = product_query.value(0)
            quantity = product_query.value(1)
            price = Decimal(product_query.value(2)) / 100

            self.name_label.setText(f"{name}")
            self.price_label.setText(f"{price:.2f}")
            self.quantity_label.setText(f"Existencias: {quantity}")
            self.show()
        else:
            self.hide()


class InventoryProductActions(QtWidgets.QWidget):
    product_id: int | None

    def __init__(self) -> None:
        super().__init__()

        layout = QtWidgets.QVBoxLayout()

        self.to_cart_button = QtWidgets.QPushButton("Agregar al Carrito")
        self.quantity_button = QtWidgets.QPushButton("Existencias")
        self.edit_button = QtWidgets.QPushButton("Editar")
        self.delete_button = QtWidgets.QPushButton("Eliminar")

        layout.addWidget(self.to_cart_button)
        layout.addWidget(self.quantity_button)
        layout.addWidget(self.edit_button)
        layout.addWidget(self.delete_button)

        self.setLayout(layout)

        self.set_product(None)

    @QtCore.Slot()
    def set_product(self, product_id: int | None) -> None:
        self.product_id = product_id
        if product_id is not None:
            self.show()
        else:
            self.hide()


class ProductTable(QtWidgets.QTableWidget):
    query: str | None
    selected = QtCore.Signal(int)

    TABLE_QUERY = """
    SELECT p.rowid, name, quantity, sell_value
    FROM Products p
        INNER JOIN Inventory i
        ON p.rowid = i.product
    {where_clause}
    ORDER BY
        CASE
            WHEN like(:name || '%', name) THEN 1
            WHEN like(concat('% ', :name, '%'), name) THEN 2
            ELSE 3
        END, name
    """

    def __init__(self, parent=None) -> None:
        super().__init__(0, 4, parent)

        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Item", "Existencias", "$", "Bs"])
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
        self.verticalHeader().hide()

        self.itemSelectionChanged.connect(self.row_selected)

        self.set_query(None)

    @QtCore.Slot(str)
    def set_query(self, query: str | None) -> None:
        if query is not None and query.strip():
            self.query = query
        else:
            self.query = None
        self.refresh_table()

    @QtCore.Slot(str)
    @QtCore.Slot(type(None))
    def refresh_table(self):
        where_clause = (
            " WHERE name LIKE concat('%', :name, '%')" if self.query is not None else ""
        )

        db = QtSql.QSqlDatabase.database()
        product_query = QtSql.QSqlQuery()

        product_query.prepare(self.TABLE_QUERY.format(where_clause=where_clause))
        if self.query is not None:
            product_query.bindValue(":name", self.query)

        if not product_query.exec():
            print(product_query.lastError())

        if db.driver().hasFeature(QtSql.QSqlDriver.DriverFeature.QuerySize):
            n_rows = product_query.size()
        else:
            product_query.last()
            n_rows = max(product_query.at() + 1, 0)
            product_query.seek(QtSql.QSql.Location.BeforeFirstRow.value)

        self.setRowCount(n_rows)

        ItemFlag = Qt.ItemFlag
        row_flags = ItemFlag.ItemIsSelectable | ItemFlag.ItemIsEnabled
        number_align = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight

        for row_num in range(n_rows):
            product_query.next()
            row_id, name, quantity, sell_value = (
                product_query.value(i) for i in range(product_query.record().count())
            )
            sell_value = Decimal(sell_value) / 100
            for idx, value in enumerate((name, quantity, sell_value, sell_value)):
                item = QtWidgets.QTableWidgetItem(str(value))

                if isinstance(value, int | float | Decimal):
                    item.setTextAlignment(number_align)
                    item.setText(f"{value:.2f}")
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
        self.topbar = topbar
        topbar.new_product.connect(self.new)
        topbar.search_submitted.connect(self.log_search)

        product_table = ProductTable(self)
        self.product_table = product_table

        topbar.search_submitted.connect(self.product_table.set_query)

        layout.addWidget(topbar)
        layout.addWidget(product_table)

        bottom = QtWidgets.QHBoxLayout()
        self.bottom = bottom
        self.preview = ProductPreviewWidget()
        self.product_actions = InventoryProductActions()

        bottom.addWidget(self.preview, 1)
        bottom.addWidget(self.product_actions)

        layout.addLayout(bottom)

        self.product_table.selected.connect(self.preview.show_product)
        self.product_table.selected.connect(self.product_actions.set_product)

    @QtCore.Slot(str)
    def log_search(self, query: str):
        print(query)

    @QtCore.Slot()
    def new(self):
        w = ProductInfoDialog()
        result = w.exec()
        if result == ProductInfoDialog.DialogCode.Accepted:
            self.product_table.refresh_table()
