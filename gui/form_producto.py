from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, # Cambiado a QDialog
    QComboBox, QMessageBox, QHBoxLayout, QFrame
)
from PySide6.QtCore import Qt
from database import get_session
from models import Producto, Categoria
from sqlalchemy.exc import IntegrityError
from utils.guards import require_perm_or_close
from utils.permisos import tiene_permiso_match
from utils.dialogos import confirmar
from utils.estilos import PALETA

class FormProducto(QDialog):  # ...
    def __init__(self, producto_id=None, parent=None, usuario=None):
        super().__init__(parent)
        self.producto_id = producto_id
        self.editando = producto_id is not None
        # --- seguridad: guard interna ---
        self.usuario = usuario or getattr(parent, "usuario", None)

        # Elegimos tokens según si estamos editando o creando para dar mensajes más precisos
        tokens = ("0220", "editar_producto") if self.editando else ("0210", "crear_producto")
        if not require_perm_or_close(self, self.usuario, *tokens):
            return
        # --- fin guard ---
        
        # Configuración de la ventana
        self.setWindowTitle("Gestión de Producto" if not self.editando else "Editar Producto")
        self.setFixedSize(600, 480) # Aumentar altura para más espacio y evitar cortes

        self.setModal(True)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        
        # Aplicar estilos consistentes
        self.setStyleSheet(f"""
            QDialog {{ /* Cambiado a QDialog */
                background-color: #fdfdfd;
                font-size: 14px;
                font-family: Arial, sans-serif;
            }}
            QFrame[objectName="main_card"] {{
                background-color: #f3e5f5;
                border: 2px solid #9c27b0;
                border-radius: 12px;
                padding: 0px;
            }}
            QLabel {{
                color: #333;
                font-weight: bold;
            }}
            QLineEdit, QComboBox {{
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 14px;
                background-color: #fff;
                min-height: 20px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 2px solid #9c27b0;
            }}
            QPushButton {{
                background-color: {PALETA['identidad']['primario']};
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
                min-height: 30px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {PALETA['identidad']['primario_hover']};
            }}
            QPushButton:pressed {{
                background-color: {PALETA['identidad']['primario_pressed']};
            }}
        """)
        
        # Layout principal de la ventana
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Tarjeta principal con el estilo de categoría
        main_card = QFrame()
        main_card.setObjectName("main_card")
        card_layout = QVBoxLayout(main_card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)

        
        # Título principal
        titulo = QLabel()
        titulo.setTextFormat(Qt.RichText)
        titulo.setText(
            f'<div style="line-height:135%; padding-bottom:2px; color:#4a148c; '
            f'font-weight:700; font-size:20px;">'
            f'📦 {"Nuevo Producto" if not self.editando else "Editar Producto"}'
            f'</div>'
        )

        card_layout.addWidget(titulo)
        
        # Línea separadora
        linea = QFrame()
        linea.setFrameShape(QFrame.HLine)
        linea.setStyleSheet("""
            QFrame {
                color: #9c27b0;
                background-color: #9c27b0;
                border: none;
                height: 2px;
                margin: 5px 0px;
            }
        """)
        card_layout.addWidget(linea)
        
        # Campo Nombre del producto
        nombre_label = QLabel("Nombre del Producto *")
        nombre_label.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: bold;
                color: #7b1fa2;
                margin-bottom: 5px;
            }
        """)
        card_layout.addWidget(nombre_label)
        
        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText("Ingrese el nombre del producto...")
        # Si el usuario tipea, limpiar estilos de error
        self.nombre_input.textChanged.connect(lambda: self.nombre_input.setStyleSheet(""))

        card_layout.addWidget(self.nombre_input)
        
        # Campo Categoría
        categoria_label = QLabel("Categoría *")
        categoria_label.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: bold;
                color: #7b1fa2;
                margin-top: 10px; /* Mantener un poco de margen superior para separar del input anterior */
                /* margin-bottom: 0px; Eliminar para que el spacing del layout maneje la separación */
            }
        """)
        card_layout.addWidget(categoria_label)
        
        self.categoria_combo = QComboBox()
        self.cargar_categorias()
        card_layout.addWidget(self.categoria_combo)
        
        # Texto de ayuda
        ayuda_label = QLabel("* Campos obligatorios")
        ayuda_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #666;
                font-style: italic;
                font-weight: normal;
                margin-top: 5px;
            }
        """)
        card_layout.addWidget(ayuda_label)
        
        # Separador antes de botones
        separador = QFrame()
        separador.setFrameShape(QFrame.HLine)
        separador.setStyleSheet("""
            QFrame {
                color: #ce93d8;
                background-color: #ce93d8;
                border: none;
                height: 1px;
                margin: 10px 0px;
            }
        """)
        card_layout.addWidget(separador)
        
        # Botones de acción
        if self.editando:
            botones_principales = QHBoxLayout()
            
            self.btn_eliminar = QPushButton("Eliminar")
            self.btn_eliminar.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PALETA['acciones']['eliminar']};
                    min-width: 140px;
                }}
                QPushButton:hover {{
                    background-color: {PALETA['acciones']['eliminar_hover']};
                }}
            """)
            self.btn_eliminar.clicked.connect(self.eliminar_producto)
            botones_principales.addWidget(self.btn_eliminar)

            botones_principales.addStretch()

            self.btn_cancelar = QPushButton("Cancelar")
            self.btn_cancelar.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PALETA['acciones']['cancelar']};
                    min-width: 80px;
                }}
                QPushButton:hover {{
                    background-color: {PALETA['acciones']['cancelar_hover']};
                }}
            """)
            self.btn_cancelar.clicked.connect(self.reject)

            self.btn_guardar = QPushButton("Actualizar")
            self.btn_guardar.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PALETA['acciones']['guardar']};
                    min-width: 100px;
                }}
                QPushButton:hover {{
                    background-color: {PALETA['acciones']['guardar_hover']};
                }}
            """)
            self.btn_guardar.clicked.connect(self.guardar_producto)
            for b in (self.btn_eliminar, self.btn_cancelar, self.btn_guardar):
                b.setFixedSize(150, 44)   # mismo tamaño que Categoría

            self.btn_eliminar.setToolTip("Eliminar definitivamente el producto")
            self.btn_cancelar.setToolTip("Cerrar sin guardar")
            self.btn_guardar.setToolTip("Guardar cambios")

            self.btn_guardar.setDefault(True)
            self.btn_guardar.setAutoDefault(True)
            self.btn_cancelar.setAutoDefault(False)
            self.btn_eliminar.setAutoDefault(False)
            
            botones_principales.addWidget(self.btn_cancelar)
            botones_principales.addWidget(self.btn_guardar)
            
            card_layout.addLayout(botones_principales)
        else:
            botones_layout = QHBoxLayout()
            botones_layout.addStretch()
            
            self.btn_cancelar = QPushButton("Cancelar")
            self.btn_cancelar.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PALETA['acciones']['cancelar']};
                    min-width: 80px;
                }}
                QPushButton:hover {{
                    background-color: {PALETA['acciones']['cancelar_hover']};
                }}
            """)
            self.btn_cancelar.clicked.connect(self.reject)

            self.btn_guardar = QPushButton("Guardar")
            self.btn_guardar.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PALETA['acciones']['guardar']};
                    min-width: 100px;
                }}
                QPushButton:hover {{
                    background-color: {PALETA['acciones']['guardar_hover']};
                }}
            """)
            self.btn_guardar.clicked.connect(self.guardar_producto)

            # Tooltips y botón por defecto
            self.btn_cancelar.setToolTip("Cerrar sin guardar")
            self.btn_guardar.setToolTip("Guardar producto")

            self.btn_guardar.setDefault(True)
            self.btn_guardar.setAutoDefault(True)
            self.btn_cancelar.setAutoDefault(False)
            
            botones_layout.addWidget(self.btn_cancelar)
            botones_layout.addWidget(self.btn_guardar)
            card_layout.addLayout(botones_layout)
        
        main_layout.addWidget(main_card)
        
        # Cargar datos si estamos editando
        if self.editando:
            self.cargar_datos()
        
        # Enfocar el campo de texto
        self.nombre_input.setFocus()

    def cargar_categorias(self):
        """Carga las categorías en el QComboBox."""
        self.categoria_combo.clear()
        with get_session() as session:
            categorias = session.query(Categoria).all()
            if not categorias:
                self.categoria_combo.addItem("No hay categorías", userData=None)
                self.categoria_combo.setEnabled(False)
                return
            self.categoria_combo.setEnabled(True)
            for c in categorias:
                self.categoria_combo.addItem(c.nombre, userData=c.id)

    def cargar_datos(self):
        """Carga los datos del producto para edición."""
        try:
            with get_session() as session:
                producto = session.get(Producto, self.producto_id)
                if producto:
                    self.nombre_input.setText(producto.nombre)
                    index = self.categoria_combo.findData(producto.categoria_id)
                    if index >= 0:
                        self.categoria_combo.setCurrentIndex(index)
                else:
                    QMessageBox.warning(self, "Error", "Producto no encontrado")
                    self.reject()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar datos:\n{str(e)}")
            self.reject()

    def guardar_producto(self):
        """Guarda o actualiza el producto."""
        nombre = self.nombre_input.text().strip()
        categoria_id = self.categoria_combo.currentData()
        # Permiso para crear/editar producto (defensa en profundidad)
        if self.editando:
            if not tiene_permiso_match(self.usuario, "0220", "editar_producto"):
                QMessageBox.warning(self, "Acceso denegado", "No tenés permiso para editar productos.")
                return
        else:
            if not tiene_permiso_match(self.usuario, "0210", "crear_producto"):
                QMessageBox.warning(self, "Acceso denegado", "No tenés permiso para crear productos.")
                return
        
        # Validación visual y lógica
        if not nombre:
            self.nombre_input.setStyleSheet("""
                QLineEdit {
                    border: 2px solid #e53935;
                    background-color: #ffebee;
                    padding: 10px;
                    border-radius: 4px;
                    font-size: 14px;
                    min-height: 20px;
                }
            """)
            QMessageBox.warning(self, "Campo requerido", "Por favor ingrese el nombre del producto.")
            self.nombre_input.setFocus()
            return
        else:
            self.nombre_input.setStyleSheet("") # Resetear estilo
        
        if categoria_id is None:
            self.categoria_combo.setStyleSheet("""
                QComboBox {
                    border: 2px solid #e53935;
                    background-color: #ffebee;
                    padding: 10px;
                    border-radius: 4px;
                    font-size: 14px;
                    min-height: 20px;
                }
            """)
            QMessageBox.warning(self, "Campo requerido", "Por favor seleccione una categoría.")
            self.categoria_combo.setFocus()
            return
        else:
            self.categoria_combo.setStyleSheet("") # Resetear estilo

        try:
            with get_session() as session:
                if self.editando:
                    producto = session.get(Producto, self.producto_id)
                    if producto:
                        producto.nombre = nombre
                        producto.categoria_id = categoria_id
                        mensaje_exito = "Producto actualizado correctamente"
                    else:
                        QMessageBox.warning(self, "Error", "Producto no encontrado")
                        return
                else:
                    producto = Producto(nombre=nombre, categoria_id=categoria_id)
                    session.add(producto)
                    mensaje_exito = "Producto guardado correctamente"
                session.commit()
            QMessageBox.information(self, "Éxito", mensaje_exito)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el producto:\n{str(e)}")
            self.reject()

    def eliminar_producto(self):
        # Permiso para eliminar producto
        if not tiene_permiso_match(self.usuario, "0220", "eliminar_producto"):
            QMessageBox.warning(self, "Acceso denegado", "No tenés permiso para eliminar productos.")
            return

        """Elimina el producto después de confirmación."""
        if confirmar(self, "Eliminar", "¿Eliminar este producto?"):
            try:
                with get_session() as session:
                    producto = session.get(Producto, self.producto_id)
                    if producto:
                        session.delete(producto)
                        session.commit()
                        print("DEBUG: Producto eliminado OK")
                    else:
                        QMessageBox.warning(self, "Error", "Producto no encontrado.")
                        self.reject()
                        return
                QMessageBox.information(self, "Eliminado", "Producto eliminado correctamente.")
                self.accept()
            except IntegrityError:
                print("DEBUG: IntegrityError al eliminar producto (tiene ventas)")
                QMessageBox.warning(self, "No se puede eliminar",
                                    "Este producto tiene ventas registradas y no puede eliminarse.")
                self.reject()
            except Exception as e:
                print(f"DEBUG: Error inesperado al eliminar producto: {e}")
                QMessageBox.critical(self, "Error", f"No se pudo eliminar:\n{e}")
                self.reject()
        else:
            self.reject()

    def keyPressEvent(self, event):
        """Maneja eventos de teclado."""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.guardar_producto()
        elif event.key() == Qt.Key_Escape:
            self.reject() 
        else:
            super().keyPressEvent(event)
