from contextlib import contextmanager
from decimal import Decimal, DecimalException
from sys import float_info
from typing import Any, cast

from PySide6 import QtCore, QtWidgets, QtGui, QtSql
from PySide6.QtCore import Qt

MAX_SAFE_DOUBLE = 10 ** (float_info.dig - 3)

CURRENCY_SYMBOL = {
    "USD": "$",
    "VED": "Bs",
}

CURRENCY_FACTOR = 100
QUANTITY_FACTOR = 1000

FP_SHORTEST = QtCore.QLocale.FloatingPointPrecisionOption.FloatingPointShortest


class DecimalSpinBox(QtWidgets.QDoubleSpinBox):
    def __init__(self, *args, format_shortest: bool = False, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.format_shortest = format_shortest

    def decimal_value(self) -> Decimal:
        value_text = str(self.value())
        return Decimal(value_text)

    def textFromValue(self, val: float) -> str:
        if self.format_shortest:
            locale = QtCore.QLocale()
            return locale.toString(val, "f", FP_SHORTEST)
        else:
            return super().textFromValue(val)


class DecimalInputDialog(QtWidgets.QDialog):
    def __init__(self, parent: Any = None, format_shortest: bool = False):
        super().__init__(parent)

        self.label = QtWidgets.QLabel()

        self.spinbox = DecimalSpinBox(format_shortest=format_shortest)

        SB = QtWidgets.QDialogButtonBox.StandardButton
        buttons = QtWidgets.QDialogButtonBox(SB.Ok | SB.Cancel)
        buttons.button(SB.Ok).setDefault(True)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()

        layout.addWidget(self.label)
        layout.addWidget(self.spinbox)
        layout.addWidget(buttons)

        self.setLayout(layout)

    @staticmethod
    def getDecimal(
        parent: Any,
        title: str,
        label: str,
        value: float = 0,
        minValue: float = 0,
        maxValue: float = 2147483647,
        decimals: int = 3,
        step: float = 1,
        format_shortest: bool = False,
    ) -> tuple[Decimal, bool]:
        dialog = DecimalInputDialog(parent, format_shortest)

        dialog.setWindowTitle(title)
        dialog.label.setText(label)

        dialog.spinbox.setValue(value)
        dialog.spinbox.setMinimum(minValue)
        dialog.spinbox.setMaximum(maxValue)
        dialog.spinbox.setDecimals(decimals)
        dialog.spinbox.setSingleStep(step)

        result = dialog.exec()

        if result == DecimalInputDialog.DialogCode.Accepted:
            return dialog.spinbox.decimal_value(), True
        else:
            return Decimal(0), False


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


def make_separator(orientation: str = "h") -> QtWidgets.QFrame:
    separator = QtWidgets.QFrame()

    if orientation == "h":
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    elif orientation == "v":
        separator.setFrameShape(QtWidgets.QFrame.Shape.VLine)
    else:
        raise ValueError(f"Invalid orientation {repr(orientation)}")

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
