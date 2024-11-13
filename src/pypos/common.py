from decimal import Decimal
from sys import float_info

from PySide6 import QtCore, QtWidgets, QtGui

LOCALE_DECIMAL_SEP = QtCore.QLocale().decimalPoint()
LOCALE_GROUP_SEP = QtCore.QLocale().groupSeparator()


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


MAX_SAFE_DOUBLE = 10 ** (float_info.dig - 3)
