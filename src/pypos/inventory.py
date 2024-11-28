from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import cast

from PySide6 import QtCore, QtWidgets, QtSql, QtGui
from PySide6.QtCore import Qt
from unidecode import unidecode

from .common import (
    DecimalInputDialog,
    DecimalSpinBox,
    MAX_SAFE_DOUBLE,
    QueryCheckFail,
    adjust_value,
    calculate_margin,
    checked_query,
    is_product_in_cart,
    CURRENCY_SYMBOL,
    CURRENCY_FACTOR,
    QUANTITY_FACTOR,
    make_separator,
    settings_group,
    FP_SHORTEST,
)
from .help import HelpDialog
from .inventory_table import InventoryTable


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

        new_button = QtWidgets.QPushButton("&Nuevo")
        self.new_button = new_button

        new_button.clicked.connect(self.new_product)

        self.search_label = QtWidgets.QLabel("&Buscar:")

        search_bar = QtWidgets.QLineEdit()
        self.search_bar = search_bar
        search_bar.textEdited.connect(self.search_submitted)
        search_bar.setClearButtonEnabled(True)

        self.search_label.setBuddy(search_bar)

        layout.addWidget(new_button)
        layout.addStretch()
        layout.addWidget(self.search_label)
        layout.addWidget(search_bar)

    @QtCore.Slot()
    def clear_search(self):
        self.search_bar.clear()


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
        form_layout.addRow("&Nombre:", self.name)

        form_layout.addRow(make_separator())

        purchase_price_layout = QtWidgets.QHBoxLayout()

        self.purchase_currency = QtWidgets.QComboBox()

        for currency, symbol in CURRENCY_SYMBOL.items():
            self.purchase_currency.addItem(symbol, currency)

        self.purchase_value = DecimalSpinBox()
        self.purchase_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.purchase_value.setMaximum(MAX_SAFE_DOUBLE)

        purchase_price_layout.addWidget(self.purchase_currency)
        purchase_price_layout.addWidget(self.purchase_value, 1)

        self.purchase_label = QtWidgets.QLabel("Precio &compra:")
        self.purchase_label.setBuddy(self.purchase_value)

        form_layout.addRow(self.purchase_label, purchase_price_layout)

        sell_price_layout = QtWidgets.QHBoxLayout()

        self.margin = DecimalSpinBox()
        self.margin.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.margin.setSuffix("%")
        self.margin.setRange(-MAX_SAFE_DOUBLE, MAX_SAFE_DOUBLE)

        form_layout.addRow("&Margen:", self.margin)

        self.sell_currency = QtWidgets.QComboBox()

        for currency, symbol in CURRENCY_SYMBOL.items():
            self.sell_currency.addItem(symbol, currency)

        self.sell_value = DecimalSpinBox()
        self.sell_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.sell_value.setMaximum(MAX_SAFE_DOUBLE)

        sell_price_layout.addWidget(self.sell_currency)
        sell_price_layout.addWidget(self.sell_value, 1)

        self.sell_label = QtWidgets.QLabel("Precio &venta:")
        self.sell_label.setBuddy(self.sell_value)

        form_layout.addRow(self.sell_label, sell_price_layout)

        self.profit = DecimalSpinBox()
        self.profit.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.profit.setRange(-MAX_SAFE_DOUBLE, MAX_SAFE_DOUBLE)

        profit_layout = QtWidgets.QHBoxLayout()

        self.profit_currency = QtWidgets.QLabel()
        profit_layout.addWidget(self.profit_currency)
        profit_layout.addWidget(self.profit, 1)

        self.profit_label = QtWidgets.QLabel("&Ganancia:")
        self.profit_label.setBuddy(self.profit)

        form_layout.addRow(self.profit_label, profit_layout)

        form_layout.addRow(make_separator())

        self.quantity = DecimalSpinBox(format_shortest=True)
        self.quantity.setMaximum(MAX_SAFE_DOUBLE)
        self.quantity.setDecimals(3)

        if self.product_id is None:
            form_layout.addRow("E&xistencias:", self.quantity)

        layout.addLayout(form_layout)

        self.setLayout(layout)

        SB = QtWidgets.QDialogButtonBox.StandardButton
        buttons = QtWidgets.QDialogButtonBox(SB.Ok | SB.Cancel | SB.Reset | SB.Help)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.helpRequested.connect(self.help)
        buttons.button(SB.Reset).clicked.connect(self.on_reset)

        layout.addWidget(buttons)

        self.on_reset()

        calc_from_purchase = QtCore.QSettings().value(
            "calc_from_purchase", True, type=bool
        )

        self.purchase_currency.currentIndexChanged.connect(self.update_purchase_value)
        if calc_from_purchase:
            self.purchase_value.valueChanged.connect(self.update_from_margin)
        self.margin.valueChanged.connect(self.update_from_margin)
        self.sell_currency.currentIndexChanged.connect(self.adjust_sell_value)
        self.sell_value.valueChanged.connect(self.update_from_sell_value)
        self.profit.valueChanged.connect(self.update_from_profit)

    def load_existing_product(self, id: int) -> None:
        query = QtSql.QSqlQuery()

        with checked_query(query) as check:
            check(query.prepare(self.LOAD_QUERY))
            query.bindValue(":id", id)

            check(query.exec())

        if query.next():
            name = query.value(0)
            purchase_currency = query.value(1)
            purchase_value = Decimal(query.value(2)) / CURRENCY_FACTOR
            sell_currency = query.value(3)
            sell_value = Decimal(query.value(4)) / CURRENCY_FACTOR
            quantity = Decimal(query.value(5)) / QUANTITY_FACTOR

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
            self.quantity.setValue(float(quantity))

            profit = sell_value - adjust_value(
                self.current_purchase_currency,
                self.current_sell_currency,
                purchase_value,
            )

            self.profit_currency.setText(CURRENCY_SYMBOL[self.current_sell_currency])
            self.profit.setValue(float(profit))

    @QtCore.Slot()
    def help(self):
        HelpDialog.product_help()

    @QtCore.Slot()
    def accept(self):
        name = self.name.text().strip()
        purchase_currency = self.purchase_currency.currentData()
        purchase_value = self.purchase_value.decimal_value()
        sell_currency = self.sell_currency.currentData()
        sell_value = self.sell_value.decimal_value()
        quantity = self.quantity.decimal_value()

        is_update = self.product_id is not None
        name_simplified = unidecode(name).lower()

        if not name:
            QtWidgets.QMessageBox.warning(
                self,
                "Nombre invalido",
                "El nombre del producto está vacío.",
            )
            return

        db = QtSql.QSqlDatabase.database()
        db.transaction()

        query = QtSql.QSqlQuery()

        if is_update:
            query_string = self.UPDATE_QUERY
        else:
            query_string = self.INSERT_QUERY

        try:
            with checked_query(query) as check:
                check(query.prepare(query_string))

                query.bindValue(":name", name)
                query.bindValue(":name_simplified", name_simplified)
                query.bindValue(":purchase_currency", purchase_currency)
                query.bindValue(
                    ":purchase_value", int(purchase_value * CURRENCY_FACTOR)
                )
                query.bindValue(":sell_currency", sell_currency)
                query.bindValue(":sell_value", int(sell_value * CURRENCY_FACTOR))

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
                        check(False)

                    db.rollback()
                    return

                if is_update:
                    check(
                        query.prepare(
                            "UPDATE Inventory SET quantity = :quantity WHERE product = :id"
                        )
                    )
                else:
                    self.product_id = query.lastInsertId()
                    query.prepare(
                        "INSERT INTO Inventory(product, quantity) VALUES (:id, :quantity)"
                    )

                query.bindValue(":id", self.product_id)
                query.bindValue(":quantity", int(quantity * QUANTITY_FACTOR))

                check(query.exec())
        except QueryCheckFail:
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
            settings = QtCore.QSettings()

            with settings_group(settings, "defaults"):
                purchase_currency = cast(
                    str, settings.value("purchase_currency", "VED", type=str)
                )
                sell_currency = cast(
                    str, settings.value("sell_currency", "VED", type=str)
                )
                default_margin = Decimal(
                    cast(str, settings.value("margin", 0, type=str))
                )

            self.name.clear()
            self.purchase_currency.setCurrentIndex(
                self.purchase_currency.findData(purchase_currency)
            )
            self.current_purchase_currency = purchase_currency

            self.purchase_value.setValue(0)

            self.margin.setValue(0)
            self.margin.setValue(float(default_margin))

            self.sell_currency.setCurrentIndex(
                self.sell_currency.findData(sell_currency)
            )
            self.current_sell_currency = sell_currency

            self.sell_value.setValue(0)

            self.profit_currency.setText(CURRENCY_SYMBOL[self.current_sell_currency])

            self.quantity.setValue(0)

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
    def adjust_sell_value(self) -> None:
        sell_value = self.sell_value.decimal_value()
        sell_currency = self.sell_currency.currentData()

        value = adjust_value(self.current_sell_currency, sell_currency, sell_value)
        self.current_sell_currency = sell_currency

        self.sell_value.setValue(float(value))

    # The following requires blocking signals temporarily to avoid the situation
    # where the currently edited spinner is also changed programatically, causing a
    # very unpleasant experience. So each field updates the other two fields by
    # itself

    @QtCore.Slot()
    def update_from_margin(self) -> None:
        purchase_value = self.purchase_value.decimal_value()
        margin = Decimal(1) + self.margin.decimal_value() / 100

        purchase_value = adjust_value(
            self.current_purchase_currency, self.current_sell_currency, purchase_value
        )

        value = purchase_value * margin

        sell_currency = self.sell_currency.currentData()

        value = adjust_value(self.current_sell_currency, sell_currency, value)
        self.current_sell_currency = sell_currency

        with QtCore.QSignalBlocker(self.sell_value), QtCore.QSignalBlocker(self.profit):
            self.sell_value.setValue(float(value))
            self.profit.setValue(float(value - purchase_value))
            self.profit_currency.setText(CURRENCY_SYMBOL[self.current_sell_currency])

    @QtCore.Slot()
    def update_from_sell_value(self) -> None:
        purchase_value = self.purchase_value.decimal_value()
        sell_value = self.sell_value.decimal_value()

        sell_currency = self.sell_currency.currentData()

        purchase_value = adjust_value(
            self.current_purchase_currency, sell_currency, purchase_value
        )
        sell_value = adjust_value(self.current_sell_currency, sell_currency, sell_value)

        margin = calculate_margin(sell_value, purchase_value)
        profit = sell_value - purchase_value

        with QtCore.QSignalBlocker(self.margin), QtCore.QSignalBlocker(self.profit):
            self.margin.setValue(float(margin))
            self.profit.setValue(float(profit))
            self.profit_currency.setText(CURRENCY_SYMBOL[self.current_sell_currency])

    @QtCore.Slot()
    def update_from_profit(self) -> None:
        purchase_value = self.purchase_value.decimal_value()
        profit = self.profit.decimal_value()

        purchase_value = adjust_value(
            self.current_purchase_currency, self.current_sell_currency, purchase_value
        )

        sell_value = purchase_value + profit
        margin = calculate_margin(sell_value, purchase_value)

        with QtCore.QSignalBlocker(self.margin), QtCore.QSignalBlocker(self.sell_value):
            self.margin.setValue(float(margin))
            self.sell_value.setValue(float(sell_value))


class ProductPreviewWidget(QtWidgets.QFrame):
    current_id: int | None

    PRODUCT_QUERY = """\
        SELECT name, purchase_currency, purchase_value, sell_currency,
               sell_value, last_update, i.quantity, c.quantity as in_cart
        FROM Products p
            INNER JOIN Inventory i
            ON p.id = i.product
            LEFT JOIN Cart c
            ON p.id = c.product
        WHERE p.id = :id"""

    def __init__(self) -> None:
        super().__init__()

        self.current_id = None

        self.setLineWidth(1)
        self.setFrameShape(type(self).Shape.StyledPanel)

        self.setBackgroundRole(QtGui.QPalette.ColorRole.Base)
        self.setAutoFillBackground(True)

        grid = QtWidgets.QGridLayout()
        self.grid = grid
        self.setLayout(grid)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.name_label = QtWidgets.QLabel()

        big_font = self.name_label.font()
        big_font.setPointSize(big_font.pointSize() + 1)
        big_font.setBold(True)
        self.name_label.setFont(big_font)
        self.name_label.setWordWrap(True)
        self.name_label.setTextFormat(Qt.TextFormat.PlainText)

        self.price_label = QtWidgets.QLabel("Precio:")
        self.quantity_label = QtWidgets.QLabel("Existencias:")
        self.purchase_label = QtWidgets.QLabel("Valor de compra:")
        self.last_update_label = QtWidgets.QLabel("Ultimo cambio:")
        self.margin_label = QtWidgets.QLabel("Margen de ganancia:")
        self.profit_label = QtWidgets.QLabel("Ganancia:")
        self.inventory_value_label = QtWidgets.QLabel("Valor total en inventario:")
        self.inventory_sell_value_label = QtWidgets.QLabel("Valor de venta total:")
        self.expected_profit_label = QtWidgets.QLabel("Ganancia total esperada:")

        self.price_value = QtWidgets.QLabel()
        self.price_value.setFont(big_font)
        self.quantity_value = QtWidgets.QLabel()
        self.purchase_value = QtWidgets.QLabel()
        self.last_update_value = QtWidgets.QLabel()
        self.margin_value = QtWidgets.QLabel()
        self.profit_value = QtWidgets.QLabel()
        self.inventory_value_value = QtWidgets.QLabel()
        self.inventory_sell_value_value = QtWidgets.QLabel()
        self.expected_profit_value = QtWidgets.QLabel()

        for value_label in (
            self.price_value,
            self.quantity_value,
            self.purchase_value,
            self.last_update_value,
            self.margin_value,
            self.profit_value,
            self.inventory_value_value,
            self.inventory_sell_value_value,
            self.expected_profit_value,
        ):
            value_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            value_label.setCursor(QtGui.QCursor(Qt.CursorShape.IBeamCursor))

        AF = Qt.AlignmentFlag

        self.grid.addWidget(self.name_label, 0, 0, 1, 2)
        self.grid.addWidget(self.price_label, 0, 3, alignment=AF.AlignTop)
        self.grid.addWidget(
            self.price_value, 0, 4, alignment=(AF.AlignRight | AF.AlignTop)
        )
        self.grid.addWidget(self.quantity_label, 1, 0)
        self.grid.addWidget(self.quantity_value, 1, 1, alignment=AF.AlignRight)
        self.grid.addWidget(self.purchase_label, 2, 0)
        self.grid.addWidget(self.purchase_value, 2, 1, alignment=AF.AlignRight)
        self.grid.addWidget(self.margin_label, 3, 0)
        self.grid.addWidget(self.margin_value, 3, 1, alignment=AF.AlignRight)
        self.grid.addWidget(self.profit_label, 4, 0)
        self.grid.addWidget(self.profit_value, 4, 1, alignment=AF.AlignRight)

        self.grid.addWidget(make_separator("v"), 1, 2, self.grid.rowCount() - 1, 1)

        self.grid.addWidget(self.last_update_label, 1, 3)
        self.grid.addWidget(self.last_update_value, 1, 4, alignment=AF.AlignRight)
        self.grid.addWidget(self.inventory_value_label, 2, 3)
        self.grid.addWidget(self.inventory_value_value, 2, 4, alignment=AF.AlignRight)
        self.grid.addWidget(self.inventory_sell_value_label, 3, 3)
        self.grid.addWidget(
            self.inventory_sell_value_value, 3, 4, alignment=AF.AlignRight
        )
        self.grid.addWidget(self.expected_profit_label, 4, 3)
        self.grid.addWidget(self.expected_profit_value, 4, 4, alignment=AF.AlignRight)

        self.show_product(None)

    @QtCore.Slot(int)
    @QtCore.Slot(type(None))
    def show_product(self, id: int | None):
        self.current_id = id
        self.show()

        product_query = QtSql.QSqlQuery()

        with checked_query(product_query) as check:
            check(product_query.prepare(self.PRODUCT_QUERY))
            product_query.bindValue(":id", id)

            check(product_query.exec())

        if product_query.next():
            (
                name,
                purchase_currency,
                purchase_value,
                sell_currency,
                sell_value,
                last_update,
                quantity,
                in_cart,
            ) = (product_query.value(i) for i in range(product_query.record().count()))

            purchase_symbol = CURRENCY_SYMBOL[purchase_currency]
            purchase_value = Decimal(purchase_value) / CURRENCY_FACTOR
            sell_symbol = CURRENCY_SYMBOL[sell_currency]
            sell_value = Decimal(sell_value) / CURRENCY_FACTOR
            last_update = QtCore.QDateTime.fromSecsSinceEpoch(last_update)
            quantity = Decimal(quantity) / QUANTITY_FACTOR

            if in_cart:
                in_cart = Decimal(in_cart) / QUANTITY_FACTOR
            else:
                in_cart = None

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

            locale = QtCore.QLocale()

            def format_currency(
                value: Decimal, currency: str, precision: int = 2
            ) -> str:
                f_value = float(value)
                return locale.toCurrencyString(f_value, currency + " ", precision)

            self.name_label.setText(f"{name}")
            self.price_value.setText(format_currency(sell_value, sell_symbol))

            quantity = locale.toString(float(quantity), "f", FP_SHORTEST)
            if in_cart:
                in_cart_str = locale.toString(float(in_cart), "f", FP_SHORTEST)
                quantity = f"({in_cart_str} en carrito) {quantity}"

            self.quantity_value.setText(quantity)

            self.purchase_value.setText(
                format_currency(purchase_value, purchase_symbol)
            )
            self.last_update_value.setText(
                locale.toString(last_update, QtCore.QLocale.FormatType.ShortFormat)
            )
            self.margin_value.setText(locale.toString(float(margin), "f", 2) + "%")
            self.profit_value.setText(format_currency(profit, sell_symbol))
            self.inventory_value_value.setText(
                format_currency(inventory_value, sell_symbol)
            )
            self.inventory_sell_value_value.setText(
                format_currency(inventory_sell_value, sell_symbol)
            )
            self.expected_profit_value.setText(
                format_currency(expected_profit, sell_symbol)
            )
            self.show()
        else:
            self.hide()

    @QtCore.Slot()
    def refresh(self) -> None:
        self.show_product(self.current_id)


class ProductQuantityDialog(QtWidgets.QDialog):
    def __init__(self, product_id: int) -> None:
        super().__init__()

        self.product_id = product_id

        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        self.product_name = QtWidgets.QLabel()
        self.product_name.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.product_name, 0, 0, 1, 2)

        self.absolute_quantity = DecimalSpinBox(format_shortest=True)
        self.absolute_quantity.setMaximum(MAX_SAFE_DOUBLE)
        self.absolute_quantity.setDecimals(3)

        self.absolute_label = QtWidgets.QLabel("&En inventario:")
        self.absolute_label.setBuddy(self.absolute_quantity)

        layout.addWidget(self.absolute_label, 1, 0)
        layout.addWidget(self.absolute_quantity, 1, 1)

        layout.addWidget(make_separator(), 2, 0, 1, 2)

        self.relative_quantity = DecimalSpinBox(format_shortest=True)
        self.relative_quantity.setMaximum(MAX_SAFE_DOUBLE)
        self.relative_quantity.setDecimals(3)

        self.relative_label = QtWidgets.QLabel("&Ingresar/Egresar:")
        self.relative_label.setBuddy(self.relative_quantity)

        layout.addWidget(self.relative_label, 3, 0)
        layout.addWidget(self.relative_quantity, 3, 1)

        layout.addWidget(make_separator(), 4, 0, 1, 2)

        SB = QtWidgets.QDialogButtonBox.StandardButton
        buttons = QtWidgets.QDialogButtonBox(SB.Ok | SB.Cancel | SB.Reset)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(SB.Reset).clicked.connect(self.on_reset)

        layout.addWidget(buttons, layout.rowCount(), 0, 1, layout.columnCount())

        self.absolute_quantity.valueChanged.connect(self.apply_absolute)
        self.relative_quantity.valueChanged.connect(self.apply_relative)

        self.load_from_stored()

    @QtCore.Slot()
    def load_from_stored(self):
        query = QtSql.QSqlQuery()

        with checked_query(query) as check:
            check(
                query.prepare("""\
            SELECT name, quantity
            FROM Inventory i
                INNER JOIN Products p
                ON i.product = p.id
            WHERE product = :product
            """)
            )

            query.bindValue(":product", self.product_id)

            check(query.exec())

            check(query.next())

        name = query.value(0)
        quantity = Decimal(query.value(1)) / QUANTITY_FACTOR

        self.product_name.setText(f"Existencias de:\n{name}")
        self.stored_quantity = quantity

        self.absolute_quantity.setValue(float(quantity))
        self.relative_quantity.setMinimum(-float(quantity))

    @QtCore.Slot()
    def on_reset(self):
        self.relative_quantity.setValue(0)
        self.absolute_quantity.setValue(float(self.stored_quantity))

    @QtCore.Slot()
    def accept(self):
        quantity = self.absolute_quantity.decimal_value()

        query = QtSql.QSqlQuery()
        with checked_query(query) as check:
            check(
                query.prepare("""\
            UPDATE Inventory SET quantity = :quantity WHERE product = :product
            """)
            )

            query.bindValue(":product", self.product_id)
            query.bindValue(":quantity", int(quantity * QUANTITY_FACTOR))

            check(query.exec())

        super().accept()

    @QtCore.Slot()
    def apply_absolute(self) -> None:
        absolute_quantity = self.absolute_quantity.decimal_value()

        with QtCore.QSignalBlocker(self.relative_quantity):
            self.relative_quantity.setValue(
                float(absolute_quantity - self.stored_quantity)
            )

    @QtCore.Slot()
    def apply_relative(self) -> None:
        relative_quantity = self.relative_quantity.decimal_value()

        with QtCore.QSignalBlocker(self.absolute_quantity):
            self.absolute_quantity.setValue(
                float(self.stored_quantity + relative_quantity)
            )


class InventoryProductActions(QtWidgets.QWidget):
    product_id: int | None

    deleted = QtCore.Signal()
    edit_requested = QtCore.Signal(int)
    cart_item = QtCore.Signal(int, Decimal)
    view_in_cart = QtCore.Signal(int)
    product_updated = QtCore.Signal(int)

    def __init__(self) -> None:
        super().__init__()

        layout = QtWidgets.QHBoxLayout()

        self.to_cart_button = QtWidgets.QPushButton("&Agregar al Carrito")
        self.quantity_button = QtWidgets.QPushButton("E&xistencias")
        self.edit_button = QtWidgets.QPushButton("&Editar")
        self.delete_button = QtWidgets.QPushButton("Elimina&r")
        self.view_in_cart_button = QtWidgets.QPushButton("&Ver en Carrito")

        layout.addWidget(self.to_cart_button)
        layout.addWidget(self.quantity_button)
        layout.addWidget(self.edit_button)
        layout.addWidget(self.delete_button)
        layout.addWidget(self.view_in_cart_button)

        self.to_cart_button.clicked.connect(self.product_carted)
        self.quantity_button.clicked.connect(self.product_quantity)
        self.edit_button.clicked.connect(self.product_edit)
        self.delete_button.clicked.connect(self.product_delete)
        self.view_in_cart_button.clicked.connect(self.view_in_cart_handler)

        self.setLayout(layout)

        self.set_product(None)

    @QtCore.Slot(type(None))
    @QtCore.Slot(int)
    def set_product(self, product_id: int | None) -> None:
        self.product_id = product_id

        enabled = product_id is not None
        self.setVisible(enabled)
        self.setEnabled(enabled)

        if self.product_id is None:
            return

        in_cart = is_product_in_cart(self.product_id)

        self.to_cart_button.setEnabled(not in_cart)
        self.quantity_button.setEnabled(not in_cart)
        self.edit_button.setEnabled(not in_cart)
        self.delete_button.setEnabled(not in_cart)
        self.view_in_cart_button.setEnabled(in_cart)

    @QtCore.Slot()
    def product_carted(self) -> None:
        if self.product_id is None:
            return

        query = QtSql.QSqlQuery()

        with checked_query(query) as check:
            check(
                query.prepare("""\
            SELECT name, i.quantity as available, coalesce(c.quantity, 0) as in_cart
            FROM Products p
                INNER JOIN Inventory i
                ON i.product = p.id
                LEFT JOIN Cart c
                ON c.product = p.id
            WHERE p.id = :id
            """)
            )

            query.bindValue(":id", self.product_id)

            check(query.exec())
            check(query.next())

        name = query.value(0)
        available = Decimal(query.value(1)) / QUANTITY_FACTOR
        in_cart = query.value(2)

        if in_cart:
            return

        if available <= 0:
            QtWidgets.QMessageBox.warning(
                self,
                "No hay existencias",
                "No hay existencias de este producto para agregar al carrito.",
            )
            return

        avail_str = QtCore.QLocale().toString(float(available), "f", FP_SHORTEST)

        quantity, ok = DecimalInputDialog.getDecimal(
            self,
            "Agregar al carrito",
            f"Unidades para agregar al carrito:\nDisponibles: {avail_str}",
            1,
            0.001,
            float(available),
            3,
            format_shortest=True,
        )

        if ok:
            with checked_query(query) as check:
                check(
                    query.prepare("""\
                INSERT INTO Cart(product, quantity) VALUES (:product, :quantity)
                ON CONFLICT(product)
                    DO UPDATE SET quantity = :quantity
                """)
                )

                query.bindValue(":product", self.product_id)
                query.bindValue(":quantity", int(quantity * QUANTITY_FACTOR))

                check(query.exec())

            self.cart_item.emit(self.product_id, quantity)

    @QtCore.Slot()
    def product_quantity(self) -> None:
        if self.product_id is None:
            return

        quantity_dialog = ProductQuantityDialog(self.product_id)
        result = quantity_dialog.exec()
        if result == ProductQuantityDialog.DialogCode.Accepted:
            self.product_updated.emit(self.product_id)

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

                with checked_query(query) as check:
                    check(query.prepare("DELETE FROM Products WHERE id = :id"))
                    query.bindValue(":id", self.product_id)

                    check(query.exec())

                self.deleted.emit()

    @QtCore.Slot()
    def view_in_cart_handler(self) -> None:
        if self.product_id is not None:
            self.view_in_cart.emit(self.product_id)


class InventoryWidget(QtWidgets.QWidget):
    cart_item = QtCore.Signal(int, Decimal)
    view_in_cart = QtCore.Signal(int)
    update_item = QtCore.Signal(int)

    def __init__(self) -> None:
        super().__init__()

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        topbar = InventoryTopBar()
        self.topbar = topbar
        topbar.new_product.connect(self.new)

        inventory_table = InventoryTable(self)
        self.inventory_table = inventory_table

        topbar.search_submitted.connect(self.inventory_table.set_query)

        self.preview = ProductPreviewWidget()
        self.product_actions = InventoryProductActions()

        preview_scroller = QtWidgets.QScrollArea()
        self.preview_scroller = preview_scroller

        preview_scroller.setWidget(self.preview)
        preview_scroller.setWidgetResizable(True)

        self.splitter = QtWidgets.QSplitter()
        self.splitter.setOrientation(Qt.Orientation.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(inventory_table)
        self.splitter.addWidget(self.preview_scroller)
        self.splitter.setSizes([0, 125])
        self.splitter.setStretchFactor(0, 1)

        layout.addWidget(topbar)

        layout.addWidget(self.splitter, 1)
        layout.addWidget(self.product_actions)

        self.inventory_table.selected.connect(self.preview.show_product)
        self.inventory_table.selected.connect(self.product_actions.set_product)
        self.inventory_table.selected.connect(self.toggle_bottom)

        self.inventory_table.double_clicked.connect(self.product_actions.product_carted)

        self.product_actions.deleted.connect(self.inventory_table.handle_deleted)
        self.product_actions.edit_requested.connect(self.edit)
        self.product_actions.cart_item.connect(self.cart_item)
        self.product_actions.cart_item.connect(self.inventory_table.update_item)
        self.product_actions.cart_item.connect(self.preview.show_product)
        self.product_actions.cart_item.connect(self.product_actions.set_product)
        self.product_actions.view_in_cart.connect(self.view_in_cart)
        self.product_actions.product_updated.connect(self.inventory_table.update_item)
        self.product_actions.product_updated.connect(self.preview.show_product)

        self.update_item.connect(self.inventory_table.update_item)

        self.toggle_bottom(None)

    @QtCore.Slot(object)
    def toggle_bottom(self, product_id: int | None) -> None:
        bottom_visible = product_id is not None
        self.preview.setVisible(bottom_visible)
        self.product_actions.setVisible(bottom_visible)
        self.preview_scroller.setVisible(bottom_visible)

    @QtCore.Slot()
    def new(self):
        dialog = ProductInfoDialog()
        result = dialog.exec()
        if result == ProductInfoDialog.DialogCode.Accepted:
            self.inventory_table.refresh_table()
            self.inventory_table.focus_product(dialog.product_id)

    @QtCore.Slot(int)
    def edit(self, product_id: int) -> None:
        dialog = ProductInfoDialog(product_id)
        result = dialog.exec()
        if result == ProductInfoDialog.DialogCode.Accepted:
            self.inventory_table.refresh_table()
            self.inventory_table.focus_product(product_id)
            self.preview.show_product(product_id)

    @QtCore.Slot()
    def refresh(self) -> None:
        current_id = self.preview.current_id
        self.inventory_table.refresh_table()
        self.inventory_table.focus_product(current_id)
        self.preview.refresh()

    @QtCore.Slot()
    def focus_inventory_item(self, product_id: int) -> None:
        self.topbar.clear_search()
        self.inventory_table.set_query(None)
        self.inventory_table.focus_product(product_id)
