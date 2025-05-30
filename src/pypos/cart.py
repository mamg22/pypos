from decimal import Decimal
from typing import cast

from PySide6 import QtCore, QtGui, QtSql, QtWidgets
from PySide6.QtCore import Qt

from .common import (
    FP_SHORTEST,
    QUANTITY_FACTOR,
    DecimalInputDialog,
    adjust_value,
    CURRENCY_SYMBOL,
    CURRENCY_FACTOR,
    checked_query,
)

SB = QtWidgets.QMessageBox.StandardButton


class CartTable(QtWidgets.QTableWidget):
    selected = QtCore.Signal(object)
    double_clicked = QtCore.Signal(int)

    CART_QUERY = """\
    SELECT p.id, name, quantity, sell_currency, sell_value
    FROM Cart c
        INNER JOIN Products p
        ON c.product = p.id
    """

    def __init__(self) -> None:
        super().__init__()

        header_labels = ["Producto", "Precio unitario", "Unidades", "Total"]
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)

        self.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        h_header = self.horizontalHeader()

        h_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        h_header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        h_header.setMinimumSectionSize(h_header.defaultSectionSize())

        self.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Fixed
        )

        self.itemSelectionChanged.connect(self.row_selected)
        self.itemDoubleClicked.connect(self.item_double_clicked)

        self.refresh()

    @QtCore.Slot()
    def refresh(self) -> None:
        db = QtSql.QSqlDatabase.database()
        query = QtSql.QSqlQuery()

        with checked_query(query) as check:
            check(query.prepare(self.CART_QUERY))
            check(query.exec())

        if db.driver().hasFeature(QtSql.QSqlDriver.DriverFeature.QuerySize):
            n_rows = query.size()
        else:
            query.last()
            n_rows = max(query.at() + 1, 0)
            query.seek(QtSql.QSql.Location.BeforeFirstRow.value)

        self.setRowCount(n_rows)

        ItemFlag = Qt.ItemFlag
        row_flags = ItemFlag.ItemIsSelectable | ItemFlag.ItemIsEnabled
        number_align = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight

        locale = QtCore.QLocale()

        for row_num in range(n_rows):
            query.next()
            row_id, name, quantity, sell_currency, int_sell_value = (
                query.value(i) for i in range(query.record().count())
            )
            sell_value = Decimal(int_sell_value) / CURRENCY_FACTOR
            quantity = Decimal(quantity) / QUANTITY_FACTOR

            base_item = QtWidgets.QTableWidgetItem()
            base_item.setFlags(row_flags)
            base_item.setData(Qt.ItemDataRole.UserRole, row_id)

            name_item = base_item.clone()
            name_item.setText(name)

            quantity_item = base_item.clone()
            quantity_item.setText(locale.toString(float(quantity), "f", FP_SHORTEST))
            quantity_item.setTextAlignment(number_align)

            currency_symbol = CURRENCY_SYMBOL[sell_currency] + " "

            unit_item = base_item.clone()
            unit_item.setText(
                locale.toCurrencyString(float(sell_value), currency_symbol, 2)
            )
            unit_item.setTextAlignment(number_align)

            total_value = sell_value * quantity

            total_item = base_item.clone()
            total_item.setText(
                locale.toCurrencyString(float(total_value), currency_symbol, 2)
            )
            total_item.setTextAlignment(number_align)

            for idx, item in enumerate(
                (name_item, unit_item, quantity_item, total_item)
            ):
                self.setItem(row_num, idx, item)

        self.clearSelection()
        self.row_selected()

    @QtCore.Slot()
    def row_selected(self) -> None:
        try:
            item_id = self.selectedItems()[0].data(Qt.ItemDataRole.UserRole)
            self.selected.emit(item_id)
        except IndexError:
            self.selected.emit(None)

    @QtCore.Slot(int)
    def focus_item(self, product_id: int) -> None:
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

    @QtCore.Slot(QtWidgets.QTableWidgetItem)
    def item_double_clicked(self, item: QtWidgets.QTableWidgetItem):
        item_id = item.data(Qt.ItemDataRole.UserRole)
        self.double_clicked.emit(item_id)


class CartTotals(QtWidgets.QFrame):
    def __init__(self) -> None:
        super().__init__()

        self.setLineWidth(1)
        self.setFrameShape(type(self).Shape.StyledPanel)
        self.setBackgroundRole(QtGui.QPalette.ColorRole.Base)
        self.setAutoFillBackground(True)

        self.total_USD = QtWidgets.QLabel()
        self.total_VED = QtWidgets.QLabel()

        price_font = self.total_USD.font()
        price_font.setPointSize(int(price_font.pointSize() * 2.5))

        for label in (self.total_USD, self.total_VED):
            label.setFont(price_font)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            label.setCursor(QtGui.QCursor(Qt.CursorShape.IBeamCursor))

        layout = QtWidgets.QGridLayout()
        layout.addWidget(QtWidgets.QLabel("Total:"), 0, 0)
        layout.addWidget(self.total_VED, 1, 1, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.total_USD, 2, 1, Qt.AlignmentFlag.AlignRight)

        layout.setColumnStretch(0, 1)
        layout.setHorizontalSpacing(10)

        self.setLayout(layout)

        self.refresh()

    @QtCore.Slot()
    def refresh(self) -> None:
        query = QtSql.QSqlQuery()

        with checked_query(query) as check:
            check(
                query.prepare("""\
            SELECT sell_currency, sell_value, quantity
            FROM Cart c
                INNER JOIN Products p
                ON c.product = p.id
            """)
            )
            check(query.exec())

        total_VED = Decimal(0)
        total_USD = Decimal(0)

        while query.next():
            sell_currency = query.value(0)
            sell_value = Decimal(query.value(1)) / CURRENCY_FACTOR
            quantity = Decimal(query.value(2)) / QUANTITY_FACTOR

            total_VED += adjust_value(sell_currency, "VED", sell_value * quantity)
            total_USD += adjust_value(sell_currency, "USD", sell_value * quantity)

        locale = QtCore.QLocale()

        VED_sym, USD_sym = (f"{CURRENCY_SYMBOL[sym]} " for sym in ("VED", "USD"))

        self.total_VED.setText(locale.toCurrencyString(float(total_VED), VED_sym, 2))
        self.total_USD.setText(locale.toCurrencyString(float(total_USD), USD_sym, 2))


class CartActions(QtWidgets.QWidget):
    sale_completed = QtCore.Signal()
    sale_discarded = QtCore.Signal()
    item_deleted = QtCore.Signal(int)
    item_updated = QtCore.Signal(int)
    view_in_inventory = QtCore.Signal(int)

    def __init__(self) -> None:
        super().__init__()

        self.current_id = None

        item_actions = QtWidgets.QGroupBox("Producto seleccionado")
        self.item_actions = item_actions

        self.units_button = QtWidgets.QPushButton("&Unidades...")
        self.view_in_inventory_button = QtWidgets.QPushButton("&Ver en inventario")
        self.delete_button = QtWidgets.QPushButton("Elimina&r del carrito")

        self.item_action_buttons = (
            self.units_button,
            self.view_in_inventory_button,
            self.delete_button,
        )

        item_layout = QtWidgets.QHBoxLayout()
        item_layout.addWidget(self.units_button)
        item_layout.addWidget(self.view_in_inventory_button)
        item_layout.addWidget(self.delete_button)

        item_actions.setLayout(item_layout)

        cart_actions = QtWidgets.QGroupBox("Carrito")

        self.accept_button = QtWidgets.QPushButton("&Aceptar venta")
        self.discard_button = QtWidgets.QPushButton("&Descartar todo")

        cart_layout = QtWidgets.QHBoxLayout()
        cart_layout.addWidget(self.accept_button)
        cart_layout.addWidget(self.discard_button)

        cart_actions.setLayout(cart_layout)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(item_actions)
        layout.addWidget(cart_actions)

        self.setLayout(layout)

        self.units_button.clicked.connect(self.units)
        self.view_in_inventory_button.clicked.connect(self.view_in_inventory_handler)
        self.delete_button.clicked.connect(self.delete)
        self.accept_button.clicked.connect(self.accept_sale)
        self.discard_button.clicked.connect(self.discard_sale)

        self.set_current_id(None)

    @QtCore.Slot(object)
    def set_current_id(self, product_id: int | None) -> None:
        self.current_id = product_id
        enable = product_id is not None

        self.item_actions.setEnabled(enable)

    @QtCore.Slot()
    def accept_sale(self) -> None:
        confirm = QtWidgets.QMessageBox.question(
            self, "Confirmar venta", "¿Está seguro de que desea completar esta venta?"
        )

        if confirm != SB.Yes:
            return

        query = QtSql.QSqlQuery()

        with checked_query(query) as check:
            check(
                query.prepare("""\
            UPDATE Inventory AS i SET quantity = i.quantity - c.quantity
            FROM Cart c
                WHERE i.product = c.product
            """)
            )
            check(query.exec())

            check(query.exec("DELETE FROM Cart"))

        self.sale_completed.emit()

    @QtCore.Slot()
    def discard_sale(self) -> None:
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Descartar venta",
            "¿Está seguro de que desea descartar esta venta?",
            defaultButton=SB.No,
        )

        if confirm != SB.Yes:
            return

        query = QtSql.QSqlQuery()

        with checked_query(query) as check:
            check(query.exec("DELETE FROM Cart"))

        self.sale_discarded.emit()

    @QtCore.Slot()
    def delete(self) -> None:
        if self.current_id is None:
            return

        confirm = QtWidgets.QMessageBox.question(
            self,
            "Eliminar producto",
            "¿Está seguro de que desea eliminar este producto de la venta actual?",
            defaultButton=SB.Yes,
        )

        if confirm != SB.Yes:
            return

        query = QtSql.QSqlQuery()

        with checked_query(query) as check:
            check(query.prepare("DELETE FROM Cart WHERE product = :product"))
            query.bindValue(":product", self.current_id)

            check(query.exec())

        self.item_deleted.emit(self.current_id)
        self.set_current_id(None)

    @QtCore.Slot()
    def units(self) -> None:
        if self.current_id is None:
            return

        query = QtSql.QSqlQuery()

        with checked_query(query) as check:
            check(
                query.prepare("""\
            SELECT p.name, i.quantity as available, coalesce(c.quantity, 0) as in_cart
            FROM Cart c
                INNER JOIN Products p
                ON c.product = p.id
                INNER JOIN Inventory i
                USING (product)
            WHERE c.product = :id
            """)
            )

            query.bindValue(":id", self.current_id)

            check(query.exec())

            check(query.next())

        name = query.value(0)
        available = Decimal(query.value(1)) / QUANTITY_FACTOR
        in_cart = Decimal(query.value(2)) / QUANTITY_FACTOR

        locale = QtCore.QLocale()
        available_str = locale.toString(float(available), "f", FP_SHORTEST)

        quantity, ok = DecimalInputDialog.getDecimal(
            self,
            "Cambiar unidades",
            f"Unidades de este producto:\nDisponibles: {available_str}",
            float(in_cart),
            0.001,
            float(available),
            decimals=3,
            format_shortest=True,
        )

        if ok:
            with checked_query(query) as check:
                check(
                    query.prepare(
                        "UPDATE Cart SET quantity = :quantity WHERE product = :product"
                    )
                )

                query.bindValue(":product", self.current_id)
                query.bindValue(":quantity", int(quantity * QUANTITY_FACTOR))

                check(query.exec())

            self.item_updated.emit(self.current_id)

    @QtCore.Slot()
    def view_in_inventory_handler(self) -> None:
        if self.current_id is not None:
            self.view_in_inventory.emit(self.current_id)


class CartWidget(QtWidgets.QWidget):
    refresh = QtCore.Signal()
    sale_completed = QtCore.Signal()
    item_deleted = QtCore.Signal(int)
    item_updated = QtCore.Signal(int)
    view_in_inventory = QtCore.Signal(int)

    def __init__(self) -> None:
        super().__init__()

        self.cart_table = CartTable()
        self.cart_totals = CartTotals()
        self.cart_actions = CartActions()

        app = cast(QtGui.QGuiApplication, QtGui.QGuiApplication.instance())

        if app.styleHints().colorScheme() == Qt.ColorScheme.Dark:
            self.cart_icon_image = QtGui.QPixmap(":/assets/Cart-512-light.png")
        else:
            self.cart_icon_image = QtGui.QPixmap(":/assets/Cart-512-dark.png")

        self.cart_icon = QtWidgets.QLabel()
        self.cart_icon.setPixmap(self.cart_icon_image)
        self.cart_icon.setMaximumSize(60, 60)
        self.cart_icon.setScaledContents(True)

        main_layout = QtWidgets.QGridLayout()

        main_layout.addWidget(self.cart_table, 0, 0, 1, 2)
        main_layout.addWidget(self.cart_icon, 1, 0, 1, 1)
        main_layout.addWidget(self.cart_totals, 1, 1, 1, 1)
        main_layout.addWidget(self.cart_actions, 2, 0, 1, 2)

        main_layout.setColumnStretch(1, 1)

        self.setLayout(main_layout)

        self.refresh.connect(self.cart_table.refresh)
        self.refresh.connect(self.cart_totals.refresh)

        self.cart_actions.sale_completed.connect(self.refresh)
        self.cart_actions.sale_completed.connect(self.sale_completed)

        self.cart_actions.sale_discarded.connect(self.refresh)
        self.cart_actions.sale_discarded.connect(self.sale_completed)

        self.cart_actions.item_deleted.connect(self.refresh)
        self.cart_actions.item_deleted.connect(self.item_deleted)
        self.cart_actions.item_updated.connect(self.refresh)
        self.cart_actions.item_updated.connect(self.cart_table.focus_item)
        self.cart_actions.item_updated.connect(self.item_updated)

        self.cart_actions.view_in_inventory.connect(self.view_in_inventory)

        self.cart_table.selected.connect(self.cart_actions.set_current_id)
        self.cart_table.double_clicked.connect(self.cart_actions.units)

    @QtCore.Slot(int)
    def view_in_cart(self, product_id: int) -> None:
        self.cart_table.focus_item(product_id)

    @QtCore.Slot()
    def do_refresh(self) -> None:
        self.refresh.emit()
