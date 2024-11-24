from decimal import Decimal

from PySide6 import QtSql, QtWidgets
from PySide6.QtCore import Qt

from .common import (
    TranslatedDialogButtonBox,
    adjust_value,
    CURRENCY_SYMBOL,
    make_separator,
)


class ReportsWindow(QtWidgets.QDialog):
    def __init__(self) -> None:
        super().__init__()

        layout = QtWidgets.QGridLayout()
        layout.setHorizontalSpacing(40)

        QLabel = QtWidgets.QLabel

        self.total_cost_VED = QLabel()
        self.total_value_VED = QLabel()
        self.total_profit_VED = QLabel()

        self.total_cost_VED.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.total_value_VED.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.total_profit_VED.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.total_cost_USD = QLabel()
        self.total_value_USD = QLabel()
        self.total_profit_USD = QLabel()

        self.total_cost_USD.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.total_value_USD.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.total_profit_USD.setAlignment(Qt.AlignmentFlag.AlignRight)

        SB = QtWidgets.QDialogButtonBox.StandardButton
        buttons = TranslatedDialogButtonBox(SB.Ok)

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
            purchase_value = Decimal(query.value(1)) / 100
            sell_currency = query.value(2)
            sell_value = Decimal(query.value(3)) / 100
            quantity = query.value(4)

            total_cost_VED += (
                adjust_value(purchase_currency, "VED", purchase_value) * quantity
            )
            total_value_VED += adjust_value(sell_currency, "VED", sell_value) * quantity

        total_profit_VED = total_value_VED - total_cost_VED

        total_cost_USD = adjust_value("VED", "USD", total_cost_VED)
        total_value_USD = adjust_value("VED", "USD", total_value_VED)
        total_profit_USD = adjust_value("VED", "USD", total_profit_VED)

        total_format = f"{CURRENCY_SYMBOL['VED']} {{:.2f}}"

        self.total_cost_VED.setText(total_format.format(total_cost_VED))
        self.total_value_VED.setText(total_format.format(total_value_VED))
        self.total_profit_VED.setText(total_format.format(total_profit_VED))

        total_format = f"{CURRENCY_SYMBOL['USD']} {{:.2f}}"

        self.total_cost_USD.setText(total_format.format(total_cost_USD))
        self.total_value_USD.setText(total_format.format(total_value_USD))
        self.total_profit_USD.setText(total_format.format(total_profit_USD))
