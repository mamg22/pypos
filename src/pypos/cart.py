from decimal import Decimal

from PySide6 import QtCore, QtSql, QtWidgets
from PySide6.QtCore import Qt


class CartTable(QtWidgets.QTableWidget):
    CART_QUERY = """\
    SELECT p.id, name, quantity, sell_currency, sell_value
    FROM Cart c
        INNER JOIN Products p
        ON c.product = p.id
    """

    def __init__(self) -> None:
        super().__init__()

        header_labels = ["Item", "Precio unitario", "Unidades", "Total"]
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)

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

        self.refresh()

    @QtCore.Slot()
    def refresh(self) -> None:
        db = QtSql.QSqlDatabase.database()
        query = QtSql.QSqlQuery()

        query.prepare(self.CART_QUERY)

        if not query.exec():
            print(query.lastError())
            return

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

        for row_num in range(n_rows):
            query.next()
            row_id, name, quantity, sell_currency, int_sell_value = (
                query.value(i) for i in range(query.record().count())
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

            currency_symbol = "$" if sell_currency == "USD" else "Bs"

            unit_item = base_item.clone()
            unit_item.setText(f"{currency_symbol} {sell_value:.2f}")
            unit_item.setTextAlignment(number_align)

            total_value = sell_value * quantity

            total_item = base_item.clone()
            total_item.setText(f"{currency_symbol} {total_value:.2f}")
            total_item.setTextAlignment(number_align)

            for idx, item in enumerate(
                (name_item, unit_item, quantity_item, total_item)
            ):
                self.setItem(row_num, idx, item)


class CartTotals(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.total_dolar = QtWidgets.QLabel()

        total_font = self.total_dolar.font()
        total_font.setPointSize(total_font.pointSize() * 3)
        self.total_dolar.setFont(total_font)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Total:"))
        layout.addWidget(self.total_dolar)

        layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.setLayout(layout)

        self.refresh()

    @QtCore.Slot()
    def refresh(self) -> None:
        query = QtSql.QSqlQuery()
        query.prepare("""\
        SELECT coalesce(sum(p.sell_value * c.quantity), 0)
        FROM Cart c
            INNER JOIN Products p
            ON c.product = p.id
        """)

        if not query.exec():
            print(query.lastError())
            raise ValueError()

        query.next()
        total = Decimal(query.value(0)) / 100

        self.total_dolar.setText(f"Bs {total:.2f}")


class CartActions(QtWidgets.QWidget):
    units = QtCore.Signal()
    view_in_inventory = QtCore.Signal()
    delete = QtCore.Signal()

    sale_completed = QtCore.Signal()
    sale_discarded = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()

        self.current_id = None

        item_actions = QtWidgets.QGroupBox("Producto seleccionado")
        self.item_actions = item_actions

        self.units_button = QtWidgets.QPushButton("Unidades...")
        self.view_in_inventory_button = QtWidgets.QPushButton("Ver en inventario")
        self.delete_button = QtWidgets.QPushButton("Eliminar del carrito")

        self.item_action_buttons = (
            self.units_button,
            self.view_in_inventory_button,
            self.delete_button,
        )

        item_layout = QtWidgets.QVBoxLayout()
        item_layout.addWidget(self.units_button)
        item_layout.addWidget(self.view_in_inventory_button)
        item_layout.addWidget(self.delete_button)

        item_actions.setLayout(item_layout)

        cart_actions = QtWidgets.QGroupBox("Carrito")

        self.accept_button = QtWidgets.QPushButton("Completar venta")
        self.discard_button = QtWidgets.QPushButton("Descartar todo")

        cart_layout = QtWidgets.QVBoxLayout()
        cart_layout.addWidget(self.accept_button)
        cart_layout.addWidget(self.discard_button)

        cart_actions.setLayout(cart_layout)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(item_actions)
        layout.addWidget(cart_actions)

        self.setLayout(layout)

        self.units_button.clicked.connect(self.units)
        self.view_in_inventory_button.clicked.connect(self.view_in_inventory)
        self.delete_button.clicked.connect(self.delete)
        self.accept_button.clicked.connect(self.accept_sale)
        self.discard_button.clicked.connect(self.discard_sale)

        self.update_buttons()

    @QtCore.Slot()
    def update_buttons(self) -> None:
        enable = self.current_id is not None

        self.item_actions.setEnabled(enable)

    @QtCore.Slot()
    def accept_sale(self) -> None:
        SB = QtWidgets.QMessageBox.StandardButton

        confirm = QtWidgets.QMessageBox.question(
            self, "Confirmar venta", "¿Está seguro de que desea completar esta venta?"
        )

        if confirm != SB.Yes:
            return

        query = QtSql.QSqlQuery()
        query.prepare("""\
        UPDATE Inventory AS i SET quantity = i.quantity - c.quantity
        FROM Cart c
            WHERE i.product = c.product
        """)

        if not query.exec():
            print(query.lastError())
            return

        if not query.exec("DELETE FROM Cart"):
            print(query.lastError())
            return

        self.sale_completed.emit()

    @QtCore.Slot()
    def discard_sale(self) -> None:
        SB = QtWidgets.QMessageBox.StandardButton

        confirm = QtWidgets.QMessageBox.question(
            self,
            "Descartar venta",
            "¿Está seguro de que desea descartar esta venta?",
            defaultButton=SB.No,
        )

        if confirm.value != SB.Yes:
            return

        query = QtSql.QSqlQuery()

        if not query.exec("DELETE FROM Cart"):
            print(query.lastError())
            return

        self.sale_discarded.emit()


class CartWidget(QtWidgets.QWidget):
    refresh = QtCore.Signal()
    sale_completed = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()

        self.cart_table = CartTable()
        self.cart_totals = CartTotals()
        self.cart_actions = CartActions()

        main_layout = QtWidgets.QGridLayout()

        main_layout.addWidget(self.cart_table, 0, 0, 1, 2)
        main_layout.addWidget(self.cart_totals, 1, 1, 1, 1)
        main_layout.addWidget(self.cart_actions, 1, 0, 1, 1)

        main_layout.setColumnStretch(1, 1)

        self.setLayout(main_layout)

        self.refresh.connect(self.cart_table.refresh)
        self.refresh.connect(self.cart_totals.refresh)

        self.cart_actions.sale_completed.connect(self.refresh)
        self.cart_actions.sale_completed.connect(self.sale_completed)

        self.cart_actions.sale_discarded.connect(self.refresh)
