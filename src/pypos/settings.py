from datetime import datetime
from typing import cast

from PySide6 import QtWidgets, QtCore

from .common import DecimalSpinBox, MAX_SAFE_DOUBLE


class ExchangeRateWindow(QtWidgets.QDialog):
    def __init__(self) -> None:
        super().__init__()

        layout = QtWidgets.QVBoxLayout()

        form_layout = QtWidgets.QFormLayout()

        self.exchange_rate = DecimalSpinBox()
        self.exchange_rate.setRange(0.01, MAX_SAFE_DOUBLE)

        self.load_previous_rate()

        form_layout.addRow("Valor dólar", self.exchange_rate)

        layout.addLayout(form_layout)

        self.setLayout(layout)

        SB = QtWidgets.QDialogButtonBox.StandardButton
        buttons = QtWidgets.QDialogButtonBox(SB.Save | SB.Cancel | SB.Reset)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(SB.Reset).clicked.connect(self.load_previous_rate)

        layout.addWidget(buttons)

    @QtCore.Slot()
    def accept(self) -> None:
        settings = QtCore.QSettings()
        settings.setValue("USD-VED-rate", str(self.exchange_rate.decimal_value()))
        settings.setValue("last-rate-update", datetime.now().timestamp())

        super().accept()

    @QtCore.Slot()
    def load_previous_rate(self) -> None:
        settings = QtCore.QSettings()
        current_rate = cast(str, settings.value("USD-VED-rate", 0, type=str))
        self.exchange_rate.setValue(float(current_rate))
