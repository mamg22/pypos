from PySide6 import QtCore, QtWidgets

from .common import adjust_value, MAX_SAFE_DOUBLE, DecimalSpinBox


class ConverterDialog(QtWidgets.QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)

        self.setModal(False)
        self.setWindowTitle("Convertidor de moneda")

        self.form = QtWidgets.QFormLayout()

        self.value_VED = DecimalSpinBox()
        self.value_USD = DecimalSpinBox()

        self.form.addRow("&Bolívares (Bs):", self.value_VED)
        self.form.addRow("&Dólares ($):", self.value_USD)

        for spinbox in (self.value_VED, self.value_USD):
            spinbox.setMaximum(MAX_SAFE_DOUBLE)

        SB = QtWidgets.QDialogButtonBox.StandardButton
        self.buttons = QtWidgets.QDialogButtonBox(SB.Close)

        self.buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        layout.addLayout(self.form)
        layout.addWidget(self.buttons)

        self.value_VED.valueChanged.connect(self.update_from_VED)
        self.value_USD.valueChanged.connect(self.update_from_USD)

    @QtCore.Slot()
    def update_from_VED(self) -> None:
        value_VED = self.value_VED.decimal_value()
        adjusted = adjust_value("VED", "USD", value_VED)

        with QtCore.QSignalBlocker(self.value_USD):
            self.value_USD.setValue(float(adjusted))

    @QtCore.Slot()
    def update_from_USD(self) -> None:
        value_USD = self.value_USD.decimal_value()
        adjusted = adjust_value("USD", "VED", value_USD)

        with QtCore.QSignalBlocker(self.value_VED):
            self.value_VED.setValue(float(adjusted))
