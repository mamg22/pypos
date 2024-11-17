from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from PySide6 import QtCore, QtWidgets, QtSql, QtGui
from PySide6.QtCore import Qt
from unidecode import unidecode

from .common import DecimalSpinBox, MAX_SAFE_DOUBLE, adjust_value, calculate_margin


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
        search_bar.textEdited.connect(self.search_edit_finished)
        search_bar.setClearButtonEnabled(True)

        layout.addWidget(new_button)
        layout.addStretch()
        layout.addWidget(QtWidgets.QLabel("Buscar:"))
        layout.addWidget(search_bar)

    @QtCore.Slot()
    def emit_new(self) -> None:
        self.new_product.emit()

    @QtCore.Slot()
    def search_edit_finished(self, query: str):
        self.search_submitted.emit(query)


class ProductInfoDialog(QtWidgets.QDialog):
    product_id: int | None

    INSERT_QUERY = """\
    INSERT INTO Products(name, name_simplified, purchase_currency, purchase_value,
         sell_currency, sell_value)
        VALUES
        (:name, :name_simplified, :purchase_currency, :purchase_value,
         :sell_currency, :sell_value)
    """
    LOAD_QUERY = """\
    SELECT name, purchase_currency, purchase_value, sell_currency, sell_value, quantity
    FROM Products p
    INNER JOIN Inventory i
        ON p.id = i.product
    WHERE p.id = :id
    """
    UPDATE_QUERY = """\
    UPDATE Products SET
        name = :name,
        name_simplified = :name_simplified,
        purchase_currency = :purchase_currency,
        purchase_value = :purchase_value,
        sell_currency = :sell_currency,
        sell_value = :sell_value,
        last_update = unixepoch()
    WHERE id = :id
    """

    def __init__(self, product_id: int | None = None) -> None:
        super().__init__()

        self.product_id = product_id

        layout = QtWidgets.QVBoxLayout()

        form_layout = QtWidgets.QFormLayout()

        self.name = QtWidgets.QLineEdit()
        self.name.setMinimumWidth(300)
        # Required format: "word" or "word word..."
        self.name.setValidator(QtGui.QRegularExpressionValidator(R"\S+(\s\S+)*"))
        form_layout.addRow("Nombre:", self.name)

        currencies = [
            # Text: Symbol, UserData: Code
            ("Bs", "VED"),
            ("$", "USD"),
        ]

        purchase_price_layout = QtWidgets.QHBoxLayout()

        self.purchase_currency = QtWidgets.QComboBox()

        for currency in currencies:
            self.purchase_currency.addItem(*currency)
        self.current_purchase_currency = currencies[0][1]

        self.purchase_value = DecimalSpinBox()
        self.purchase_value.setMaximum(MAX_SAFE_DOUBLE)

        purchase_price_layout.addWidget(self.purchase_currency)
        purchase_price_layout.addWidget(self.purchase_value, 1)

        form_layout.addRow("Precio compra:", purchase_price_layout)

        sell_price_layout = QtWidgets.QHBoxLayout()

        self.margin = DecimalSpinBox()
        self.margin.setSuffix("%")
        self.margin.setRange(-MAX_SAFE_DOUBLE, MAX_SAFE_DOUBLE)
        form_layout.addRow("Margen:", self.margin)

        self.sell_currency = QtWidgets.QComboBox()

        for currency in currencies:
            self.sell_currency.addItem(*currency)
        self.current_sell_currency = currencies[0][1]

        self.sell_value = DecimalSpinBox()
        self.sell_value.setMaximum(MAX_SAFE_DOUBLE)

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

        if self.product_id is not None:
            self.load_existing_product(self.product_id)

        self.purchase_currency.currentIndexChanged.connect(self.update_purchase_value)
        self.purchase_value.valueChanged.connect(self.update_sell_value)
        self.margin.valueChanged.connect(self.update_sell_value)
        self.sell_currency.currentIndexChanged.connect(self.update_sell_value)
        self.sell_value.valueChanged.connect(self.update_margin)

    def load_existing_product(self, id: int) -> None:
        query = QtSql.QSqlQuery()
        query.prepare(self.LOAD_QUERY)
        query.bindValue(":id", id)

        if not query.exec():
            print(query.lastError())
            return

        if query.next():
            name = query.value(0)
            purchase_currency = query.value(1)
            purchase_value = Decimal(query.value(2)) / 100
            sell_currency = query.value(3)
            sell_value = Decimal(query.value(4)) / 100
            quantity = query.value(5)

            margin = calculate_margin(
                sell_value,
                adjust_value(purchase_currency, sell_currency, purchase_value),
            )

            self.name.setText(name)

            p_currency = self.purchase_currency.findData(purchase_currency)
            self.purchase_currency.setCurrentIndex(p_currency)
            self.current_purchase_currency = purchase_currency

            self.purchase_value.setValue(float(purchase_value))
            self.margin.setValue(float(margin))
            self.sell_currency.setCurrentIndex(
                self.sell_currency.findData(sell_currency)
            )

            s_currency = self.sell_currency.findData(sell_currency)
            self.sell_currency.setCurrentIndex(s_currency)
            self.current_sell_currency = sell_currency

            self.sell_value.setValue(float(sell_value))
            self.quantity.setValue(quantity)

    @QtCore.Slot()
    def accept(self):
        name = self.name.text().strip()
        purchase_currency = self.purchase_currency.currentData()
        purchase_value = self.purchase_value.decimal_value()
        sell_currency = self.sell_currency.currentData()
        sell_value = self.sell_value.decimal_value()
        quantity = self.quantity.value()

        is_update = self.product_id is not None
        name_simplified = unidecode(name).lower()

        db = QtSql.QSqlDatabase.database()
        db.transaction()

        query = QtSql.QSqlQuery()

        if is_update:
            query_string = self.UPDATE_QUERY
        else:
            query_string = self.INSERT_QUERY

        query.prepare(query_string)

        query.bindValue(":name", name)
        query.bindValue(":name_simplified", name_simplified)
        query.bindValue(":purchase_currency", purchase_currency)
        query.bindValue(":purchase_value", int(purchase_value * 100))
        query.bindValue(":sell_currency", sell_currency)
        query.bindValue(":sell_value", int(sell_value * 100))

        if is_update:
            query.bindValue(":id", self.product_id)

        if not query.exec():
            # 2067 SQLITE_CONSTRAINT_UNIQUE
            if query.lastError().nativeErrorCode() == "2067":
                QtWidgets.QMessageBox.information(
                    self,
                    "Duplicado",
                    "Ya existe un producto registrado con un nombre similar",
                )
            else:
                print(query.lastError())

            db.rollback()
            return

        if is_update:
            query.prepare(
                "UPDATE Inventory SET quantity = :quantity WHERE product = :id"
            )
        else:
            self.product_id = query.lastInsertId()
            query.prepare(
                "INSERT INTO Inventory(product, quantity) VALUES (:id, :quantity)"
            )

        query.bindValue(":id", self.product_id)
        query.bindValue(":quantity", quantity)

        if not query.exec():
            print(query.lastError())
            db.rollback()
            return

        if not db.commit():
            print(query.lastError())
            return

        super().accept()

    @QtCore.Slot()
    def on_reset(self):
        if self.product_id is not None:
            self.load_existing_product(self.product_id)
        else:
            self.name.clear()
            self.purchase_currency.setCurrentIndex(0)
            self.purchase_value.setValue(0)
            self.margin.setValue(0)
            self.sell_currency.setCurrentIndex(0)
            self.sell_value.setValue(0)

    @QtCore.Slot()
    def update_purchase_value(self) -> None:
        purchase_value = self.purchase_value.decimal_value()
        purchase_currency = self.purchase_currency.currentData()

        value = adjust_value(
            self.current_purchase_currency, purchase_currency, purchase_value
        )
        self.current_purchase_currency = purchase_currency

        self.purchase_value.setValue(float(value))

    @QtCore.Slot()
    def update_sell_value(self) -> None:
        purchase_value = self.purchase_value.decimal_value()
        margin = Decimal(1) + self.margin.decimal_value() / 100

        purchase_value = adjust_value(
            self.current_purchase_currency, self.current_sell_currency, purchase_value
        )

        value = purchase_value * margin

        sell_currency = self.sell_currency.currentData()

        value = adjust_value(self.current_sell_currency, sell_currency, value)
        self.current_sell_currency = sell_currency

        with QtCore.QSignalBlocker(self.sell_value):
            self.sell_value.setValue(float(value))

    @QtCore.Slot()
    def update_margin(self) -> None:
        purchase_value = self.purchase_value.decimal_value()
        sell_value = self.sell_value.decimal_value()

        sell_currency = self.sell_currency.currentData()

        purchase_value = adjust_value(
            self.current_purchase_currency, sell_currency, purchase_value
        )
        sell_value = adjust_value(self.current_sell_currency, sell_currency, sell_value)

        margin = calculate_margin(sell_value, purchase_value)

        with QtCore.QSignalBlocker(self.margin):
            self.margin.setValue(float(margin))


class ProductPreviewWidget(QtWidgets.QFrame):
    current_id: int | None

    PRODUCT_QUERY = """\
        SELECT name, purchase_currency, purchase_value, sell_currency,
               sell_value, last_update, quantity
        FROM Products p
            INNER JOIN Inventory i
            ON p.id = i.product
        WHERE p.id = :id"""

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
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.name_label = QtWidgets.QLabel()

        name_font = self.name_label.font()
        name_font.setPointSize(name_font.pointSize() + 1)
        name_font.setBold(True)
        self.name_label.setFont(name_font)

        self.price_label = QtWidgets.QLabel()
        self.quantity_label = QtWidgets.QLabel()
        self.purchase_label = QtWidgets.QLabel()
        self.last_update_label = QtWidgets.QLabel()
        self.margin_label = QtWidgets.QLabel()
        self.profit_label = QtWidgets.QLabel()
        self.inventory_value_label = QtWidgets.QLabel()
        self.inventory_sell_value_label = QtWidgets.QLabel()
        self.expected_profit_label = QtWidgets.QLabel()

        self.grid.addWidget(self.name_label, 0, 0)
        self.grid.addWidget(
            self.price_label, 0, 1, alignment=Qt.AlignmentFlag.AlignRight
        )
        self.grid.addWidget(self.quantity_label, 1, 0)
        self.grid.addWidget(self.purchase_label, 2, 0)
        self.grid.addWidget(self.last_update_label, 3, 0)
        self.grid.addWidget(self.margin_label, 4, 0)
        self.grid.addWidget(self.profit_label, 5, 0)
        self.grid.addWidget(self.inventory_value_label, 6, 0)
        self.grid.addWidget(self.inventory_sell_value_label, 7, 0)
        self.grid.addWidget(self.expected_profit_label, 8, 0)

        self.show_product(None)

    @QtCore.Slot(int)
    @QtCore.Slot(type(None))
    def show_product(self, id: int | None):
        self.current_id = id
        self.show()

        product_query = QtSql.QSqlQuery()
        prepared = product_query.prepare(self.PRODUCT_QUERY)

        if not prepared:
            print(product_query.lastError())

        product_query.bindValue(":id", id)

        if not product_query.exec():
            print(product_query.lastError())

        if product_query.next():
            (
                name,
                purchase_currency,
                purchase_value,
                sell_currency,
                sell_value,
                last_update,
                quantity,
            ) = (product_query.value(i) for i in range(product_query.record().count()))

            purchase_value = Decimal(purchase_value) / 100
            sell_value = Decimal(sell_value) / 100
            last_update = datetime.fromtimestamp(last_update)

            margin = calculate_margin(
                sell_value,
                adjust_value(purchase_currency, sell_currency, purchase_value),
            )
            profit = sell_value - adjust_value(
                purchase_currency, sell_currency, purchase_value
            )
            inventory_value = purchase_value * quantity
            inventory_sell_value = sell_value * quantity
            expected_profit = inventory_sell_value - adjust_value(
                purchase_currency, sell_currency, inventory_value
            )

            self.name_label.setText(f"{name}")
            self.price_label.setText(f"{sell_currency} {sell_value:.2f}")
            self.quantity_label.setText(f"Existencias: {quantity}")
            self.purchase_label.setText(
                f"Valor de compra: {purchase_currency} {purchase_value}"
            )
            self.last_update_label.setText(f"Último cambio: {last_update}")
            self.margin_label.setText(f"Margen de ganancia: {margin:.2f}%")
            self.profit_label.setText(f"Ganancia: {sell_currency} {profit:.2f}")
            self.inventory_value_label.setText(
                f"Valor total del inventario: {purchase_currency} {inventory_value:.2f}"
            )
            self.inventory_sell_value_label.setText(
                f"Valor total de venta: {sell_currency} {inventory_sell_value:.2f}"
            )
            self.expected_profit_label.setText(
                f"Ganancia total esperada: {sell_currency} {expected_profit:.2f}"
            )
            self.show()
        else:
            self.hide()

    @QtCore.Slot()
    def refresh(self) -> None:
        self.show_product(self.current_id)


class InventoryProductActions(QtWidgets.QWidget):
    product_id: int | None

    deleted = QtCore.Signal()
    edit_requested = QtCore.Signal(int)
    cart_item = QtCore.Signal(int, int)

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

        self.to_cart_button.clicked.connect(self.product_carted)
        self.quantity_button.clicked.connect(self.product_quantity)
        self.edit_button.clicked.connect(self.product_edit)
        self.delete_button.clicked.connect(self.product_delete)

        self.setLayout(layout)

        self.set_product(None)

    @QtCore.Slot(type(None))
    @QtCore.Slot(int)
    def set_product(self, product_id: int | None) -> None:
        self.product_id = product_id
        if product_id is not None:
            self.show()
        else:
            self.hide()

    @QtCore.Slot()
    def product_carted(self) -> None:
        if self.product_id is None:
            return

        query = QtSql.QSqlQuery()
        query.prepare("""\
        SELECT name, i.quantity as available, coalesce(c.quantity, 0) as in_cart
        FROM Products p
            INNER JOIN Inventory i
            ON i.product = p.id
            LEFT JOIN Cart c
            ON c.product = p.id
        WHERE p.id = :id
        """)

        query.bindValue(":id", self.product_id)

        if not query.exec():
            print(query.lastError())
            return
        query.next()

        name = query.value(0)
        available = query.value(1)
        in_cart = query.value(2)

        if available <= 0:
            QtWidgets.QMessageBox.warning(
                self,
                "No hay existencias",
                f'No hay existencias de "{name}" para agregar al carrito.',
            )
            return

        quantity, ok = QtWidgets.QInputDialog.getInt(
            self, "Agregar al carrito", f"Unidades de {name}:", in_cart, 1, available
        )

        if ok:
            query.prepare("""\
            INSERT INTO Cart(product, quantity) VALUES (:product, :quantity)
            ON CONFLICT(product)
                DO UPDATE SET quantity = :quantity
            """)

            query.bindValue(":product", self.product_id)
            query.bindValue(":quantity", quantity)

            if not query.exec():
                print(query.lastError())
                return

            self.cart_item.emit(self.product_id, quantity)

    @QtCore.Slot()
    def product_quantity(self) -> None:
        if self.product_id is not None:
            print("QUANTITY", self.product_id)

    @QtCore.Slot()
    def product_edit(self) -> None:
        if self.product_id is not None:
            self.edit_requested.emit(self.product_id)

    @QtCore.Slot()
    def product_delete(self) -> None:
        if self.product_id is not None:
            StandardButton = QtWidgets.QMessageBox.StandardButton
            confirm = QtWidgets.QMessageBox.warning(
                self,
                "¿Eliminar?",
                "¿Está seguro de que desea eliminar este producto?\nEsta acción no se puede deshacer.",
                buttons=(StandardButton.Yes | StandardButton.No),
                defaultButton=StandardButton.No,
            )

            if confirm == StandardButton.Yes:
                query = QtSql.QSqlQuery()
                query.prepare("DELETE FROM Products WHERE id = :id")
                query.bindValue(":id", self.product_id)

                if not query.exec():
                    print(query.lastError())
                else:
                    self.deleted.emit()


class ProductTable(QtWidgets.QTableWidget):
    query: str | None
    selected = QtCore.Signal(object)

    TABLE_QUERY = """
    SELECT p.id, name, quantity, sell_currency, sell_value
    FROM Products p
        INNER JOIN Inventory i
        ON p.id = i.product
    {where_clause}
    ORDER BY
        CASE
            WHEN like(:name_simplified || '%', name_simplified) THEN 1
            WHEN like(concat('% ', :name_simplified, '%'), name_simplified) THEN 2
            ELSE 3
        END, name_simplified
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
        if query is not None:
            self.query = query.strip() or None
        else:
            self.query = None
        self.refresh_table()

    @QtCore.Slot(str)
    @QtCore.Slot(type(None))
    def refresh_table(self):
        where_clause = (
            " WHERE name_simplified LIKE concat('%', :name_simplified, '%')"
            if self.query is not None
            else ""
        )

        db = QtSql.QSqlDatabase.database()
        product_query = QtSql.QSqlQuery()

        product_query.prepare(self.TABLE_QUERY.format(where_clause=where_clause))
        if self.query is not None:
            query = unidecode(self.query).lower()
            product_query.bindValue(":name_simplified", query)

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
            row_id, name, quantity, sell_currency, int_sell_value = (
                product_query.value(i) for i in range(product_query.record().count())
            )
            sell_value = Decimal(int_sell_value) / 100

            base_item = QtWidgets.QTableWidgetItem()
            base_item.setFlags(row_flags)
            base_item.setData(Qt.ItemDataRole.UserRole, row_id)

            name_item = base_item.clone()
            name_item.setText(name)

            quantity_item = base_item.clone()
            quantity_item.setText(str(quantity))
            quantity_item.setTextAlignment(number_align)

            dolar_value = adjust_value(sell_currency, "USD", sell_value)
            dolar_item = base_item.clone()
            dolar_item.setText(f"{dolar_value:.2f}")
            dolar_item.setTextAlignment(number_align)

            bs_value = adjust_value(sell_currency, "VED", sell_value)
            bs_item = base_item.clone()
            bs_item.setText(f"{bs_value:.2f}")
            bs_item.setTextAlignment(number_align)

            for idx, item in enumerate((name_item, quantity_item, dolar_item, bs_item)):
                self.setItem(row_num, idx, item)

        if n_rows > 0 and self.query:
            self.selectRow(0)
        else:
            self.clearSelection()
        self.row_selected()

    @QtCore.Slot()
    def row_selected(self):
        try:
            item_id = self.selectedItems()[0].data(Qt.ItemDataRole.UserRole)
            self.selected.emit(item_id)
        except IndexError:
            self.selected.emit(None)

    @QtCore.Slot(int)
    def focus_product(self, product_id: int) -> None:
        model = self.model()

        if model.hasIndex(0, 0):
            found = model.match(
                model.index(0, 0),
                Qt.ItemDataRole.UserRole,
                product_id,
                flags=Qt.MatchFlag.MatchExactly,
            )
            if found:
                idx = found[0]
                self.selectRow(idx.row())
                self.scrollTo(idx)


class InventoryWidget(QtWidgets.QWidget):
    cart_item = QtCore.Signal(int, int)

    def __init__(self) -> None:
        super().__init__()

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        topbar = InventoryTopBar()
        self.topbar = topbar
        topbar.new_product.connect(self.new)

        product_table = ProductTable(self)
        self.product_table = product_table

        topbar.search_submitted.connect(self.product_table.set_query)

        layout.addWidget(topbar)
        layout.addWidget(product_table)

        bottom = QtWidgets.QHBoxLayout()
        self.preview = ProductPreviewWidget()
        self.product_actions = InventoryProductActions()

        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.addWidget(self.preview, 1)
        bottom.addWidget(self.product_actions)

        bottom_widget = QtWidgets.QWidget()
        bottom_widget.setLayout(bottom)

        layout.addWidget(bottom_widget)
        self.bottom = bottom_widget

        self.product_table.selected.connect(self.preview.show_product)
        self.product_table.selected.connect(self.product_actions.set_product)
        self.product_table.selected.connect(self.toggle_bottom)

        self.product_actions.deleted.connect(self.product_table.refresh_table)
        self.product_actions.edit_requested.connect(self.edit)
        self.product_actions.cart_item.connect(self.cart_item)

        self.toggle_bottom(None)

    @QtCore.Slot(object)
    def toggle_bottom(self, product_id: int | None) -> None:
        if product_id is not None:
            self.bottom.show()
        else:
            self.bottom.hide()

    @QtCore.Slot()
    def new(self):
        w = ProductInfoDialog()
        result = w.exec()
        if result == ProductInfoDialog.DialogCode.Accepted:
            self.product_table.refresh_table()

    @QtCore.Slot(int)
    def edit(self, product_id: int) -> None:
        dialog = ProductInfoDialog(product_id)
        result = dialog.exec()
        if result == ProductInfoDialog.DialogCode.Accepted:
            self.product_table.refresh_table()
            self.product_table.focus_product(product_id)

    @QtCore.Slot()
    def refresh(self) -> None:
        current_id = self.preview.current_id
        self.product_table.refresh_table()
        self.product_table.focus_product(current_id)
        self.preview.refresh()
