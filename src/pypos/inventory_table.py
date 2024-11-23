from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from .inventory_model import InventoryModel


class InventoryTable(QtWidgets.QWidget):
    query: str | None

    selected = QtCore.Signal(object)  # Actually `int | None`

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.query = None

        self.table = QtWidgets.QTableView()
        self.model = InventoryModel()

        self.table.setModel(self.model)

        h_header = self.table.horizontalHeader()

        h_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Fixed)
        h_header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)

        self.table.verticalHeader().hide()

        self.table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.table)

        layout.setContentsMargins(0, 0, 0, 0)

        self.table.selectionModel().selectionChanged.connect(self.row_selected)

    def keyReleaseEvent(self, event: QtGui.QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.table.selectionModel().clearSelection()

    @QtCore.Slot(str)
    def set_query(self, query: str | None) -> None:
        self.model.set_query(query)
        self.auto_focus()

    @QtCore.Slot()
    def refresh_table(self):
        self.model.load_data()
        self.auto_focus()

    def auto_focus(self):
        sel_model = self.table.selectionModel()

        if self.model.rowCount() > 0 and self.model.query:
            sel_model.select(
                self.model.index(0, 0),
                sel_model.SelectionFlag.Select | sel_model.SelectionFlag.Rows,
            )
        else:
            sel_model.clearSelection()

    @QtCore.Slot(QtCore.QItemSelection)
    def row_selected(self, selected: QtCore.QItemSelection):
        try:
            item = selected.indexes()[0]
            id = self.model.data(item, Qt.ItemDataRole.UserRole)
            self.selected.emit(id)
        except IndexError:
            self.selected.emit(None)

    @QtCore.Slot(int)
    def focus_product(self, product_id: int) -> None:
        found = self.model.index_for_id(product_id)

        while not found.isValid() and self.model.canFetchMore(QtCore.QModelIndex()):
            self.model.fetchMore(QtCore.QModelIndex())
            found = self.model.index_for_id(product_id)

        if found:
            self.table.selectRow(found.row())
            self.table.scrollTo(found)
