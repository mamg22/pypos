from contextlib import contextmanager
from decimal import Decimal, DecimalException
from sys import float_info
from typing import cast

from PySide6 import QtCore, QtWidgets, QtGui, QtSql
from PySide6.QtCore import Qt

MAX_SAFE_DOUBLE = 10 ** (float_info.dig - 3)

CURRENCY_SYMBOL = {
    "USD": "$",
    "VED": "Bs",
}


class DecimalSpinBox(QtWidgets.QDoubleSpinBox):
    def decimal_value(self) -> Decimal:
        value_text = str(self.value())
        return Decimal(value_text)


def adjust_value(
    source_currency: str,
    target_currency: str,
    value: Decimal,
    rate: Decimal | None = None,
) -> Decimal:
    if source_currency == target_currency:
        return value

    if rate is None:
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


@contextmanager
def waiting_cursor():
    app = cast(QtWidgets.QApplication, QtWidgets.QApplication.instance())

    if app is not None:
        try:
            app.setOverrideCursor(Qt.CursorShape.WaitCursor)
            yield
        finally:
            app.restoreOverrideCursor()
    else:
        raise RuntimeError("Could not get application instance")
