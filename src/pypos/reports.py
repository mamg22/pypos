from decimal import Decimal

from PySide6 import QtCore, QtGui, QtSql, QtWidgets
from PySide6.QtCore import Qt

from .common import adjust_value, CURRENCY_SYMBOL, make_separator


class ReportsWindow(QtWidgets.QDialog):
    def __init__(self) -> None:
        super().__init__()

        layout = QtWidgets.QGridLayout()
        layout.setHorizontalSpacing(40)

        QLabel = QtWidgets.QLabel

        self.total_cost_VED = QLabel()
        self.total_value_VED = QLabel()
        self.total_profit_VED = QLabel()

        self.total_cost_USD = QLabel()
        self.total_value_USD = QLabel()
        self.total_profit_USD = QLabel()

        for label in (
            getattr(self, attrname)
            for attrname in dir(self)
            if attrname.startswith("total_")
        ):
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            label.setCursor(QtGui.QCursor(Qt.CursorShape.IBeamCursor))
            label.setAlignment(Qt.AlignmentFlag.AlignRight)

        SB = QtWidgets.QDialogButtonBox.StandardButton
        buttons = QtWidgets.QDialogButtonBox(SB.Ok)

        layout.addWidget(QLabel("Total valor de inventario:"), 0, 0)
        layout.addWidget(self.total_value_VED, 0, 1)
        layout.addWidget(self.total_value_USD, 0, 2)

        layout.addWidget(QLabel("Total costo de inventario:"), 1, 0)
        layout.addWidget(self.total_cost_VED, 1, 1)
        layout.addWidget(self.total_cost_USD, 1, 2)

        separator = make_separator()

        layout.addWidget(separator, 2, 0, 1, layout.columnCount())

        layout.addWidget(QLabel("Ganancia total esperada:"), 3, 0)
        layout.addWidget(self.total_profit_VED, 3, 1)
        layout.addWidget(self.total_profit_USD, 3, 2)

        layout.addWidget(
            buttons,
            layout.rowCount(),
            0,
            1,
            layout.columnCount(),
        )

        self.setLayout(layout)

        self.load_report()

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def load_report(self) -> None:
        query = QtSql.QSqlQuery()

        ok = query.exec("""\
        SELECT purchase_currency, purchase_value, sell_currency, sell_value, quantity
        FROM Products p
            INNER JOIN Inventory i
            ON p.id = i.product
        """)

        if not ok:
            print(query.lastError())
            return

        total_cost_VED = Decimal(0)
        total_value_VED = Decimal(0)

        while query.next():
            purchase_currency = query.value(0)
            purchase_value = Decimal(query.value(1))
            sell_currency = query.value(2)
            sell_value = Decimal(query.value(3))
            quantity = query.value(4)

            total_cost_VED += (
                adjust_value(purchase_currency, "VED", purchase_value) * quantity
            )
            total_value_VED += adjust_value(sell_currency, "VED", sell_value) * quantity

        total_profit_VED = total_value_VED - total_cost_VED

        locale = QtCore.QLocale()

        def format_currency(value: Decimal, symbol: str, precision: int) -> str:
            f_value = float(value)
            return locale.toCurrencyString(f_value, symbol, precision)

        total_cost_USD = adjust_value("VED", "USD", total_cost_VED)
        total_value_USD = adjust_value("VED", "USD", total_value_VED)
        total_profit_USD = adjust_value("VED", "USD", total_profit_VED)

        symbol = CURRENCY_SYMBOL["VED"] + " "

        self.total_cost_VED.setText(format_currency(total_cost_VED, symbol, 2))
        self.total_value_VED.setText(format_currency(total_value_VED, symbol, 2))
        self.total_profit_VED.setText(format_currency(total_profit_VED, symbol, 2))

        symbol = CURRENCY_SYMBOL["USD"] + " "

        self.total_cost_USD.setText(format_currency(total_cost_USD, symbol, 2))
        self.total_value_USD.setText(format_currency(total_value_USD, symbol, 2))
        self.total_profit_USD.setText(format_currency(total_profit_USD, symbol, 2))
