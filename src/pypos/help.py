from typing import Any

from PySide6 import QtGui, QtWidgets
from PySide6.QtCore import Qt


class HelpDialog(QtWidgets.QDialog):
    def __init__(self, help_text: str, parent: Any = None) -> None:
        super().__init__(parent)

        self.text_box = QtWidgets.QTextEdit(help_text)
        self.text_box.setReadOnly(True)

        # cursor = self.text_box.textCursor()
        # block_format = QtGui.QTextBlockFormat()
        # block_format.setLineHeight(
        #     150.0, QtGui.QTextBlockFormat.LineHeightTypes.ProportionalHeight.value
        # )
        #
        # cursor.clearSelection()
        # cursor.select(QtGui.QTextCursor.SelectionType.Document)
        # cursor.setBlockFormat(block_format)

        SB = QtWidgets.QDialogButtonBox.StandardButton
        self.buttons = QtWidgets.QDialogButtonBox(SB.Close)

        self.buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(self.text_box)
        layout.addWidget(self.buttons)

        self.resize(600, 400)

    @staticmethod
    def inventory_help():
        dialog = HelpDialog(INVENTORY_HELP)
        dialog.exec()

    @staticmethod
    def cart_help():
        dialog = HelpDialog(CART_HELP)
        dialog.exec()

    @staticmethod
    def general_help():
        dialog = HelpDialog(GENERAL_HELP)
        dialog.exec()


INVENTORY_HELP = """\
<html>
<h2>Inventario</h2>
<p>
    El inventario presenta la tabla de productos registrados en el sistema,
    junto con la cantidad disponible, su precio y valor equivalente. Puede
    desplazarse a través de la tabla de productos usando el puntero o las
    teclas de movimiento (flechas). Al hacer click sobre una de las filas,
    se seleccionará el producto indicado por la fila.
</p>
<p>
    En la parte superior se encuentra la barra de búsqueda, con ésta podrá
    encontrar rápidamente cualquier producto. A la izquieda está el botón
    de <kbd>Nuevo</kbd>, el cual le permitirá registrar un nuevo producto,
    indicando todos los detalles necesarios.
</p>
<p>
    Al seleccionar un producto, se mostrará un panel con información adicional
    sobre este producto, incluyendo el precio de compra y venta, margen de
    ganancia, último cambio e información del valor de todo el inventario para
    ese producto.
</p>
<p>
    Debajo de éste panel, se encuentran las acciones que puede hacer sobre este
    producto:
</p>
<ul>
    <li>
        <kbd>Agregar al Carrito</kbd>: Agregar el producto a la venta actual;
        preguntará cuantas unidades del producto agregar.
    </li>
    <li>
        <kbd>Existencias</kbd>: Mostrará una ventana para cambiar cuantas
        existencias del producto se encuentran en el inventario. La opción de
        <kbd>Ingresar/Egresar</kbd> permitirá facilmente registrar la entrada
        o salida de mercancía especificando sólo la cantidad de producto que
        se sumará o restará a lo que está guardado.
    </li>
    <li>
        <kbd>Editar</kbd>: Muestra una ventana para editar los detalles del
        producto: Nombre y su precio de compra o venta.
    </li>
    <li>
        <kbd>Eliminar</kbd>: Permitirá eliminar un producto del inventario. Usese
        con cuidado, pues esta acción no se puede deshacer.
    </li>
    <li>
        <kbd>Ver en carrito</kbd>:
        Mostrará y seleccionará el producto en la vista del Carrito.
    </li>
</ul>
<p>
La disponibilidad de las opciones dependerá si el producto se encuentra o no en el
carrito.
</p>
</html>
"""

CART_HELP = """\
<html>
<h2>Carrito</h2>
<p>
    El carrito contiene productos seleccionados del inventario. Calculará el
    monto total de cada producto y mostrará la suma total de todos los productos.
    Hacer click sobre una de las filas seleccionará el producto de esa fila.
    Puede desplazarse a través de esta tabla con el puntero o las flechas
    direccionales.
</p>
<p>
    Abajo se encuentran las siguientes opciones:
</p>
<ul>
    <li>
        <kbd>Completar venta</kbd>: Resta del inventario las cantidades que indica
        cada producto en el carrito, y luego vaciará la lista del carrito.
    </li>
    <li>
        <kbd>Descartar todo</kbd>: Vaciará la lista del carrito sin afectar el
        inventario.
    </li>
</ul>
<p>
    Al seleccionar un producto en el carrito, se habilitan las siguientes:
</p>
<ul>
    <li>
        <kbd>Cantidad...</kbd>: Permite cambiar la cantidad del producto que se
        encuentra actualmente en el carrito.
    </li>
    <li>
        <kbd>Ver en inventario</kbd>: Mostrará y seleccionará el producto en la
        vista del Inventario.
    </li>
    <li>
        <kbd>Eliminar del carrito</kbd>: Borrará sólo el producto seleccionado
        de la lista del carrito.
    </li>
</ul>
</html>
"""


GENERAL_HELP = """\
<html>
<h2>Ayuda general</h2>
<p>
    Esta aplicación provee un sistema de gestión para inventarios de diversos
    productos, con diversas funciones para facilitar la administración y actualización
    del inventario, así como también un cómodo sistema de carrito de compras que
    permite registrar facilmente la salida de productos.
</p>
<p>
    Abajo se encuentra la barra de estado, la cual provee información sobre la
    tasa de dólar configurada, así como también la fecha de la última vez que
    se cambió. Si la tasa esta desactualizada, la aplicación le hará saber
    resaltandolo en la barra de estado.
</p>
<p>
    En la barra de menús se encuentran diversas funciones de la aplicación:
</p>
<p>
<kbd>Aplicación > Reportes</kbd>: Genera un reporte con:
<ul>
    <li>
        Valor total del inventario: Suma del valor de venta de todos los productos en inventario.
    </li>
    <li>
        Costo total del inventario: Suma del valor de compra de todos los productos.
    </li>
    <li>
        Ganancia esperada: Suma del estimado de ganancia de todos los productos.
    </li>
</p>
<p>
<kbd>Opciones > Tasa de cambio...</kbd>: Permite cambiar la tasa del dólar utilizada para las
operaciones.
</p>
<p>
<kbd>Opciones > Configuración...</kbd>: Ajustes varios del funcionamiento de la aplicación;
puede ajustar el porcentaje de margen de ganancia por defecto que se usará para calcular precios
de venta, y la moneda por defecto utilizada al marcar precios en nuevos productos.
</p>
<p>
<kbd>Ayuda</kbd>: Ayuda sobre el uso de la aplicación.
</p>
<p>
    Varias opciones y botones en esta aplicación presentan una letra subrayada
    en su texto (Como <u>e</u>sto), indica que puede acceder rápidamente a esa
    función usando el teclado mediante una combinación de teclas presionando la
    tecla <kbd>Alt</kbd> junto con la letra subrayada. Por ejemplo, para agregar
    un producto al carrito desde la vista de Inventario, puede presionar
    <kbd>Alt</kbd> más la tecla <kbd>A</kbd>, cumpliendo la misma función que
    presionar el botón de <kbd>Agregar al Carrito</kbd>.
</p>
</html>
"""
