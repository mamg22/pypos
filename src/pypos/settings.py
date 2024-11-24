from datetime import datetime
from decimal import Decimal
from typing import cast

from PySide6 import QtWidgets, QtCore

from .common import (
    DecimalSpinBox,
    MAX_SAFE_DOUBLE,
    CURRENCY_SYMBOL,
    TranslatedDialogButtonBox,
    make_separator,
    settings_group,
)


class SettingsWindow(QtWidgets.QDialog):
    def __init__(self) -> None:
        super().__init__()

        layout = QtWidgets.QVBoxLayout()

        form_layout = QtWidgets.QFormLayout()

        self.default_margin = DecimalSpinBox()
        self.default_margin.setRange(-MAX_SAFE_DOUBLE, MAX_SAFE_DOUBLE)
        self.default_margin.setSuffix("%")

        self.default_purchase_currency = QtWidgets.QComboBox()
        self.default_sell_currency = QtWidgets.QComboBox()

        for currency, symbol in CURRENCY_SYMBOL.items():
            self.default_purchase_currency.addItem(symbol, currency)
            self.default_sell_currency.addItem(symbol, currency)

        form_layout.addRow("Margen por defecto:", self.default_margin)
        form_layout.addRow(make_separator())
        form_layout.addRow(
            "Moneda de compra por defecto:", self.default_purchase_currency
        )
        form_layout.addRow("Moneda de venta por defecto", self.default_sell_currency)

        layout.addLayout(form_layout)

        self.setLayout(layout)

        SB = QtWidgets.QDialogButtonBox.StandardButton
        buttons = TranslatedDialogButtonBox(SB.Save | SB.Cancel | SB.Reset)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(SB.Reset).clicked.connect(self.load_previous_settings)

        layout.addWidget(buttons)

        self.load_previous_settings()

    @QtCore.Slot()
    def accept(self) -> None:
        settings = QtCore.QSettings()

        with settings_group(settings, "defaults"):
            settings.setValue("margin", str(self.default_margin.decimal_value()))
            settings.setValue(
                "purchase_currency", self.default_purchase_currency.currentData()
            )
            settings.setValue("sell_currency", self.default_sell_currency.currentData())

        super().accept()

    @QtCore.Slot()
    def load_previous_settings(self) -> None:
        settings = QtCore.QSettings()

        with settings_group(settings, "defaults"):
            margin = Decimal(cast(str, settings.value("margin", 0, type=str)))
            purchase_currency = cast(
                str, settings.value("purchase_currency", "VED", type=str)
            )
            sell_currency = cast(str, settings.value("sell_currency", "VED", type=str))

            self.default_margin.setValue(float(margin))
            self.default_purchase_currency.setCurrentIndex(
                self.default_purchase_currency.findData(purchase_currency)
            )
            self.default_sell_currency.setCurrentIndex(
                self.default_sell_currency.findData(sell_currency)
            )


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
        buttons = TranslatedDialogButtonBox(SB.Save | SB.Cancel | SB.Reset)

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
