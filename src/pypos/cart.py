from PySide6 import QtWidgets


class CartWidget(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.cart_table = QtWidgets.QTableWidget()

        main_layout = QtWidgets.QVBoxLayout()

        main_layout.addWidget(self.cart_table)

        self.setLayout(main_layout)
