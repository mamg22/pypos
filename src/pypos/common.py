from contextlib import contextmanager
from decimal import Decimal, DecimalException
from sys import float_info
from typing import cast

from PySide6 import QtCore, QtWidgets, QtGui, QtSql

LOCALE_DECIMAL_SEP = QtCore.QLocale().decimalPoint()
LOCALE_GROUP_SEP = QtCore.QLocale().groupSeparator()

MAX_SAFE_DOUBLE = 10 ** (float_info.dig - 3)

CURRENCY_SYMBOL = {
    "USD": "$",
    "VED": "Bs",
}


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


def adjust_value(source_currency: str, target_currency: str, value: Decimal) -> Decimal:
    if source_currency == target_currency:
        return value

    rate_src = cast(str, QtCore.QSettings().value("USD-VED-rate", 1, type=str))
    rate = Decimal(rate_src)

    match (source_currency, target_currency):
        case ("VED", "USD"):
            return value / rate
        case ("USD", "VED"):
            return value * rate
        case _:
            raise ValueError(
                "Unknown rate conversion {}->{}".format(
                    source_currency, target_currency
                )
            )


def calculate_margin(sell_value: Decimal, purchase_value: Decimal) -> Decimal:
    try:
        return (sell_value / purchase_value - 1) * 100
    except DecimalException:
        # This will handle extraneous situations such as x/0, 0/0, etc.
        return Decimal(0)


def is_product_in_cart(product_id: int) -> bool:
    query = QtSql.QSqlQuery()
    query.prepare("SELECT count(product) FROM Cart WHERE product = :product")
    query.bindValue(":product", product_id)

    if not query.exec():
        print(query.lastError())
        return False
    query.next()

    return query.value(0) != 0


def make_separator() -> QtWidgets.QFrame:
    separator = QtWidgets.QFrame()
    separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    separator.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)

    return separator


@contextmanager
def settings_group(settings: QtCore.QSettings, group_name: str):
    settings.beginGroup(group_name)
    yield
    settings.endGroup()
