from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from PySide6 import QtCore, QtGui, QtSql
from PySide6.QtCore import Qt
from unidecode import unidecode

from .common import CURRENCY_SYMBOL, adjust_value


@dataclass(frozen=True, slots=True)
class Product:
    id: int
    name: str
    sell_currency: str
    sell_value: Decimal
    quantity: int
    in_cart: int | None


class InventoryModel(QtCore.QAbstractTableModel):
    products: list[Product]
    id_index_map: dict[int, int]
    query: str | None
    result_size: int

    # If there's a query
    #      Rank prefix matches first,
    #      then by word prefix match,
    #      then the rest;
    #      Items with same rank are sorted by name
    # If no query, then just sort by name
    LOAD_QUERY = """\
    SELECT p.id, name, i.quantity, sell_currency, sell_value, c.quantity as in_cart
    FROM Products p
        INNER JOIN Inventory i
        ON p.id = i.product
        LEFT JOIN Cart c
        ON p.id = c.product
    """
    WHERE_CLAUSE = """\
    WHERE name_simplified LIKE concat('%', :name_simplified, '%') ESCAPE '\\'
    """
    ORDER_CLAUSE = """\
    ORDER BY
        iif(length(:name_simplified),
            CASE
                WHEN like(:name_simplified || '%', name_simplified, '\\')
                    THEN 1
                WHEN like(concat('% ', :name_simplified, '%'), name_simplified, '\\')
                    THEN 2
                ELSE 3
            END,
            NULL
        ),
        name_simplified
    """

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)

        self.products = []
        self.id_index_map = {}
        self.query = None
        self.result_size = 0

        self.load_data()

    def load_data(self):
        try:
            self.beginResetModel()
            self.products.clear()
            self.id_index_map.clear()

            query = QtSql.QSqlQuery()

            query_str = "SELECT count(id) FROM Products "

            if self.query is not None:
                query_str += self.WHERE_CLAUSE

            query.prepare(query_str)
            query.bindValue(":name_simplified", self.query)

            query.exec()
            query.next()

            self.result_size = query.value(0)

            self.fetchMore(QtCore.QModelIndex())
        finally:
            self.endResetModel()

    def canFetchMore(
        self, parent: QtCore.QModelIndex | QtCore.QPersistentModelIndex
    ) -> bool:
        if parent.isValid():
            return False

        return len(self.products) < self.result_size

    def fetchMore(
        self, parent: QtCore.QModelIndex | QtCore.QPersistentModelIndex
    ) -> None:
        if parent.isValid():
            return

        start = len(self.products)
        to_fetch = min(self.result_size - start, 64)

        query = QtSql.QSqlQuery()
        query_str = self.LOAD_QUERY

        if self.query is not None:
            query_str += self.WHERE_CLAUSE

        query_str += self.ORDER_CLAUSE
        query_str += f"LIMIT {to_fetch} OFFSET {start}"

        query.prepare(query_str)
        query.bindValue(":name_simplified", self.query)

        query.exec()

        n_recs = query.record().count()

        self.beginInsertRows(QtCore.QModelIndex(), start, start + to_fetch - 1)

        while query.next():
            row_id, name, quantity, sell_currency, int_sell_value, in_cart = (
                query.value(i) for i in range(n_recs)
            )
            sell_value = Decimal(int_sell_value) / 100

            product = Product(
                row_id, name, sell_currency, sell_value, quantity, in_cart
            )

            self.id_index_map[row_id] = len(self.products)
            self.products.append(product)

        self.endInsertRows()

    def set_query(self, query: str | None):
        if query is not None and query != "":
            self.query = (
                unidecode(query)
                .lower()
                .replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
                .replace(" ", "%")
            )
        else:
            self.query = None

        self.load_data()

    def rowCount(
        self,
        parent: QtCore.QModelIndex
        | QtCore.QPersistentModelIndex = QtCore.QModelIndex(),
    ) -> int:
        if parent.isValid():
            return 0
        return len(self.products)

    def columnCount(
        self,
        parent: QtCore.QModelIndex
        | QtCore.QPersistentModelIndex = QtCore.QModelIndex(),
    ) -> int:
        if parent.isValid():
            return 0
        return 4

    def data(
        self,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid():
            return

        IDR = Qt.ItemDataRole

        product = self.products[index.row()]

        if role == IDR.DisplayRole:
            match index.column():
                case 0:
                    return product.name
                case 1:
                    if product.in_cart:
                        return f"({product.in_cart}) {product.quantity}"
                    return product.quantity
                case 2:
                    locale = QtCore.QLocale()
                    return locale.toCurrencyString(
                        float(product.sell_value),
                        CURRENCY_SYMBOL[product.sell_currency] + " ",
                        2,
                    )
                case 3:
                    sell_currency = "VED" if product.sell_currency == "USD" else "USD"
                    sell_value = adjust_value(
                        product.sell_currency, sell_currency, product.sell_value
                    )
                    locale = QtCore.QLocale()
                    return locale.toCurrencyString(
                        float(sell_value),
                        CURRENCY_SYMBOL[sell_currency] + " ",
                        2,
                    )

        elif role == IDR.BackgroundRole and product.in_cart:
            return QtGui.QBrush(QtGui.QPalette().alternateBase().color().darker(105))

        elif role == IDR.TextAlignmentRole:
            align = Qt.AlignmentFlag.AlignVCenter

            if index.column() > 0:
                align |= Qt.AlignmentFlag.AlignRight
            else:
                align |= Qt.AlignmentFlag.AlignLeft

            return align

        elif role == IDR.UserRole:
            return product.id

    HEADERS = ["Producto", "Existencias", "Precio", "Equivalente"]

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return

        if orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]

        return None

    def index_for_id(self, product_id: int) -> QtCore.QModelIndex:
        try:
            idx = self.id_index_map[product_id]
            return self.index(idx, 0)
        except KeyError:
            return QtCore.QModelIndex()

    def update_item(self, product_id: int):
        query = QtSql.QSqlQuery()
        query.prepare(self.LOAD_QUERY + " WHERE id = :id")
        query.bindValue(":id", product_id)

        query.exec()

        n_recs = query.record().count()

        if query.next():
            row_id, name, quantity, sell_currency, int_sell_value, in_cart = (
                query.value(i) for i in range(n_recs)
            )
            sell_value = Decimal(int_sell_value) / 100

            product = Product(
                row_id, name, sell_currency, sell_value, quantity, in_cart
            )

            index_row = self.id_index_map[row_id]
            self.products[index_row] = product

            self.dataChanged.emit(self.index(index_row, 0), self.index(index_row, 3))
