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


class CartWidget(QtWidgets.QWidget):
    refresh = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()

        self.cart_table = CartTable()
        self.cart_totals = CartTotals()

        main_layout = QtWidgets.QGridLayout()

        main_layout.addWidget(self.cart_table, 0, 0, 1, 2)
        main_layout.addWidget(self.cart_totals, 1, 1, 1, 1)

        main_layout.setColumnStretch(0, 1)

        self.setLayout(main_layout)

        self.refresh.connect(self.cart_table.refresh)
        self.refresh.connect(self.cart_totals.refresh)
