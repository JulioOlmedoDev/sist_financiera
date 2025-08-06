from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QFrame, QMessageBox, QScrollArea, QSizePolicy, QDialog # Importar QDialog
)
from PySide6.QtCore import Qt, QSize
from database import session
from models import Categoria, Producto
from gui.form_categoria import FormCategoria
from gui.form_producto import FormProducto

class FormListadoProductos(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestión de Categorías y Productos")
        self.showMaximized()
        
        # Crear scroll area principal
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        # Widget contenedor principal
        contenido = QWidget()
        scroll.setWidget(contenido)
        
        # Layout principal del contenido
        self.layout_principal = QVBoxLayout(contenido)
        self.layout_principal.setContentsMargins(30, 30, 30, 30)
        self.layout_principal.setSpacing(25)  # Más espacio entre categorías
        
        # Título principal
        titulo = QLabel("Gestión de Categorías y Productos")
        titulo.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #7b1fa2;
                margin-bottom: 10px;
            }
        """)
        self.layout_principal.addWidget(titulo)
        
        # Botón para nueva categoría
        botones_superiores = QHBoxLayout()
        btn_nueva_categoria = QPushButton("➕ Nueva Categoría")
        btn_nueva_categoria.setObjectName("btn_nueva_categoria")
        btn_nueva_categoria.clicked.connect(self.abrir_nueva_categoria)
        botones_superiores.addWidget(btn_nueva_categoria)
        botones_superiores.addStretch()
        self.layout_principal.addLayout(botones_superiores)
        
        # Aplicar estilos generales
        self.setStyleSheet("""
            QWidget {
                font-size: 14px;
                background-color: #fdfdfd;
                font-family: Arial, sans-serif;
            }
            QLabel {
                font-weight: bold;
                color: #333;
            }
            QFrame[objectName="categoria_frame"] {
                background-color: #f3e5f5;
                border: 2px solid #9c27b0;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
            }
            QFrame[objectName="productos_frame"] {
                background-color: #ffffff;
                border: 1px solid #e1bee7;
                border-radius: 8px;
                padding: 15px;
                margin: 10px 0px;
            }
            QFrame[objectName="producto_item"] {
                background-color: #fafafa;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
                margin: 4px 0px;
            }
            QFrame[objectName="vacio_frame"] {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 16px;
            }
            QPushButton {
                background-color: #9c27b0;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
                min-height: 30px;
                border: none;
            }
            QPushButton:hover {
                background-color: #7b1fa2;
            }
            QPushButton:pressed {
                background-color: #6a1b9a;
            }
            QPushButton[objectName="btn_nueva_categoria"] {
                background-color: #4caf50;
                padding: 10px 20px;
            }
            QPushButton[objectName="btn_nueva_categoria"]:hover {
                background-color: #388e3c;
            }
            QPushButton[objectName="btn_editar_cat"] {
                background-color: #9c27b0;
            }
            QPushButton[objectName="btn_editar_cat"]:hover {
                background-color: #7b1fa2;
            }
            QPushButton[objectName="btn_eliminar_cat"] {
                background-color: #e53935;
            }
            QPushButton[objectName="btn_eliminar_cat"]:hover {
                background-color: #c62828;
            }
            QPushButton[objectName="btn_nuevo_prod"] {
                background-color: #4caf50;
            }
            QPushButton[objectName="btn_nuevo_prod"]:hover {
                background-color: #388e3c;
            }
            QPushButton[objectName="btn_editar_prod"] {
                background-color: #5c6bc0;
                padding: 6px 12px;
                min-width: 35px;
                max-width: 35px;
            }
            QPushButton[objectName="btn_editar_prod"]:hover {
                background-color: #3f51b5;
            }
            QPushButton[objectName="btn_eliminar_prod"] {
                background-color: #ef5350;
                padding: 6px 12px;
                min-width: 35px;
                max-width: 35px;
            }
            QPushButton[objectName="btn_eliminar_prod"]:hover {
                background-color: #e53935;
            }
        """)
        
        # Layout principal de la ventana
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        
        # Cargar datos iniciales
        self.cargar_listado()

    def clear_layout(self, layout):
        """Limpia un layout recursivamente"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self.clear_layout(child.layout())

    def cargar_listado(self):
        """Carga el listado de categorías y productos"""
        # Limpiar layout existente (excepto título y botón superior)
        while self.layout_principal.count() > 2:
            child = self.layout_principal.takeAt(2)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self.clear_layout(child.layout())
        
        categorias = session.query(Categoria).all()
        
        if not categorias:
            # Mostrar mensaje cuando no hay categorías
            frame_vacio = QFrame()
            frame_vacio.setObjectName("vacio_frame")
            layout_vacio = QVBoxLayout(frame_vacio)
            
            label_vacio = QLabel("📂 No hay categorías registradas")
            label_vacio.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    color: #666;
                    text-align: center;
                    padding: 20px;
                }
            """)
            label_vacio.setAlignment(Qt.AlignCenter)
            layout_vacio.addWidget(label_vacio)
            
            self.layout_principal.addWidget(frame_vacio)
            return
        
        # Agregar cada categoría como un frame separado
        for i, cat in enumerate(categorias):
            # Frame principal de la categoría con color distintivo
            frame = QFrame()
            frame.setObjectName("categoria_frame")
            frame_layout = QVBoxLayout(frame)
            frame_layout.setSpacing(15)
            
            # Encabezado de categoría con estilo destacado
            header_layout = QHBoxLayout()
            
            # Número de categoría y nombre
            numero_cat = QLabel(f"#{i+1}")
            numero_cat.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    font-weight: bold;
                    color: #7b1fa2;
                    background-color: white;
                    border: 2px solid #7b1fa2;
                    border-radius: 15px;
                    padding: 5px 10px;
                    min-width: 30px;
                    max-width: 50px;
                }
            """)
            numero_cat.setAlignment(Qt.AlignCenter)
            
            label_cat = QLabel(f"📁 {cat.nombre}")
            label_cat.setStyleSheet("""
                QLabel {
                    font-size: 20px;
                    font-weight: bold;
                    color: #4a148c;
                    margin-left: 10px;
                }
            """)
            
            header_layout.addWidget(numero_cat)
            header_layout.addWidget(label_cat)
            header_layout.addStretch()
            frame_layout.addLayout(header_layout)
            
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
            frame_layout.addWidget(linea)
            
            # Productos de la categoría
            productos = session.query(Producto).filter_by(categoria_id=cat.id).all()
            
            if productos:
                # Título de sección de productos
                titulo_productos = QLabel(f"Productos ({len(productos)})")
                titulo_productos.setStyleSheet("""
                    QLabel {
                        font-size: 16px;
                        font-weight: bold;
                        color: #6a1b9a;
                        margin: 5px 0px;
                    }
                """)
                frame_layout.addWidget(titulo_productos)
                
                # Contenedor para productos
                productos_frame = QFrame()
                productos_frame.setObjectName("productos_frame")
                productos_layout = QVBoxLayout(productos_frame)
                productos_layout.setSpacing(8)
                
                for j, prod in enumerate(productos):
                    # Frame individual para cada producto
                    producto_frame = QFrame()
                    producto_frame.setObjectName("producto_item")
                    fila_prod = QHBoxLayout(producto_frame)
                    fila_prod.setSpacing(8)
                    fila_prod.setContentsMargins(8, 8, 8, 8)
                    
                    # Número del producto
                    num_prod = QLabel(f"{j+1}.")
                    num_prod.setStyleSheet("""
                        QLabel {
                            font-size: 12px;
                            font-weight: bold;
                            color: #666;
                            min-width: 20px;
                        }
                    """)
                    fila_prod.addWidget(num_prod)
                    
                    # Información del producto
                    lbl_prod = QLabel(f"📦 {prod.nombre}")
                    lbl_prod.setStyleSheet("""
                        QLabel {
                            font-size: 14px;
                            font-weight: bold;
                            color: #333;
                        }
                    """)
                    fila_prod.addWidget(lbl_prod)
                    
                    # Información adicional del producto si existe
                    if hasattr(prod, 'precio') and prod.precio:
                        lbl_precio = QLabel(f"- Precio: ${prod.precio}")
                        lbl_precio.setStyleSheet("""
                            QLabel {
                                font-size: 12px;
                                color: #666;
                                font-weight: normal;
                            }
                        """)
                        fila_prod.addWidget(lbl_precio)
                    
                    fila_prod.addStretch()
                    
                    # Botones de acción para producto
                    btn_editar_prod = QPushButton("✏️")
                    btn_editar_prod.setObjectName("btn_editar_prod")
                    btn_editar_prod.setToolTip("Editar producto")
                    btn_editar_prod.clicked.connect(lambda checked=False, p_id=prod.id: self.abrir_editar_producto(p_id))
                    
                    btn_eliminar_prod = QPushButton("🗑️")
                    btn_eliminar_prod.setObjectName("btn_eliminar_prod")
                    btn_eliminar_prod.setToolTip("Eliminar producto")
                    btn_eliminar_prod.clicked.connect(lambda checked=False, p_id=prod.id: self.eliminar_producto(p_id))
                    
                    fila_prod.addWidget(btn_editar_prod)
                    fila_prod.addWidget(btn_eliminar_prod)
                    
                    productos_layout.addWidget(producto_frame)
                
                frame_layout.addWidget(productos_frame)
            else:
                # Mensaje cuando no hay productos
                no_productos_frame = QFrame()
                no_productos_frame.setObjectName("productos_frame")
                no_productos_layout = QVBoxLayout(no_productos_frame)
                
                no_productos = QLabel("📦 No hay productos en esta categoría")
                no_productos.setStyleSheet("""
                    QLabel {
                        font-size: 14px;
                        color: #666;
                        font-style: italic;
                        padding: 15px;
                        font-weight: normal;
                        text-align: center;
                    }
                """)
                no_productos.setAlignment(Qt.AlignCenter)
                no_productos_layout.addWidget(no_productos)
                frame_layout.addWidget(no_productos_frame)
            
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
            frame_layout.addWidget(separador)
            
            # Botones de acción para categoría
            botones_layout = QHBoxLayout()
            botones_layout.setSpacing(12)
            botones_layout.setContentsMargins(0, 5, 0, 0)
            
            btn_nuevo_prod = QPushButton("➕ Nuevo Producto")
            btn_nuevo_prod.setObjectName("btn_nuevo_prod")
            btn_nuevo_prod.clicked.connect(lambda checked=False, c_id=cat.id: self.abrir_nuevo_producto(c_id))
            
            btn_editar_cat = QPushButton("✏️ Editar Categoría")
            btn_editar_cat.setObjectName("btn_editar_cat")
            btn_editar_cat.clicked.connect(lambda checked=False, c_id=cat.id: self.abrir_editar_categoria(c_id))
            
            btn_eliminar_cat = QPushButton("🗑️ Eliminar Categoría")
            btn_eliminar_cat.setObjectName("btn_eliminar_cat")
            btn_eliminar_cat.clicked.connect(lambda checked=False, c_id=cat.id: self.eliminar_categoria(c_id))
            
            botones_layout.addWidget(btn_nuevo_prod)
            botones_layout.addStretch()
            botones_layout.addWidget(btn_editar_cat)
            botones_layout.addWidget(btn_eliminar_cat)
            
            frame_layout.addLayout(botones_layout)
            
            # Agregar el frame al layout principal
            self.layout_principal.addWidget(frame)
        
        # Agregar stretch al final
        self.layout_principal.addStretch()
    def abrir_nueva_categoria(self):
        """Abre el formulario para crear una nueva categoría como un QDialog modal."""
        dialog = FormCategoria()
        print("DEBUG: Abriendo FormCategoria como diálogo modal.") # AÑADE ESTA LÍNEA
        
        result = dialog.exec() # Almacenar el resultado para depuración
        print(f"DEBUG: FormCategoria se cerró con resultado: {result} (Accepted={QDialog.Accepted}, Rejected={QDialog.Rejected})") # AÑADE ESTA LÍNEA
        print(f"DEBUG: Bandera create_new_product_flag de FormCategoria: {dialog.create_new_product_flag}") # AÑADE ESTA LÍNEA
        print(f"DEBUG: ID de la nueva categoría de FormCategoria: {dialog.newly_created_category_id}") # AÑADE ESTA LÍNEA

        if result == QDialog.Accepted:
            self.cargar_listado() # Refrescar el listado principal
            if dialog.create_new_product_flag:
                # Si el usuario eligió crear un nuevo producto, abrir el formulario de producto
                print("DEBUG: FormCategoria indicó crear nuevo producto. Llamando a abrir_nuevo_producto.") # AÑADE ESTA LÍNEA
                self.abrir_nuevo_producto(dialog.newly_created_category_id)
        else:
            print("DEBUG: FormCategoria fue cancelado o hubo un error.") # AÑADE ESTA LÍNEA
            self.cargar_listado() # Refrescar el listado si se canceló o hubo error

    def abrir_editar_categoria(self, categoria_id):
        """Abre el formulario para editar una categoría existente como un QDialog modal."""
        dialog = FormCategoria(categoria_id)
        if dialog.exec() == QDialog.Accepted:
            self.cargar_listado() # Refrescar el listado principal
        else:
            self.cargar_listado() # Refrescar el listado si se canceló o hubo error

    def abrir_nuevo_producto(self, categoria_id=None):
        """Abre el formulario para crear un nuevo producto como un QDialog modal."""
        print(f"DEBUG: abrir_nuevo_producto llamado con categoria_id: {categoria_id}") # AÑADE ESTA LÍNEA
        dialog = FormProducto()
        
        # Preseleccionar la categoría si se proporciona un ID
        if categoria_id is not None:
            dialog.cargar_categorias() # Asegurarse de que las categorías estén cargadas
            index = dialog.categoria_combo.findData(categoria_id)
            if index >= 0:
                dialog.categoria_combo.setCurrentIndex(index)
            else:
                QMessageBox.warning(self, "Error", "La categoría seleccionada no se encontró en el listado de productos.")
        
        result = dialog.exec() # Almacenar el resultado para depuración
        print(f"DEBUG: FormProducto se cerró con resultado: {result} (Accepted={QDialog.Accepted}, Rejected={QDialog.Rejected})") # AÑADE ESTA LÍNEA
        
        if result == QDialog.Accepted:
            self.cargar_listado() # Refrescar el listado principal
        else:
            self.cargar_listado() # Refrescar el listado si se canceló o hubo error

    def abrir_editar_producto(self, producto_id):
        """Abre el formulario para editar un producto existente como un QDialog modal."""
        dialog = FormProducto(producto_id)
        if dialog.exec() == QDialog.Accepted:
            self.cargar_listado() # Refrescar el listado principal
        else:
            self.cargar_listado() # Refrescar el listado si se canceló o hubo error

    def eliminar_categoria(self, categoria_id):
        """Elimina una categoría después de confirmación"""
        try:
            cat = session.query(Categoria).get(categoria_id)
            productos_count = session.query(Producto).filter_by(categoria_id=categoria_id).count()
            
            mensaje = f"¿Estás seguro de eliminar la categoría '{cat.nombre}'?"
            if productos_count > 0:
                mensaje += f"\n\nEsto también eliminará {productos_count} producto(s) asociado(s)."
            
            confirm = QMessageBox.question(
                self, 
                "Confirmar eliminación", 
                mensaje,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if confirm == QMessageBox.Yes:
                session.delete(cat)
                session.commit()
                QMessageBox.information(self, "Éxito", "Categoría eliminada correctamente")
                self.cargar_listado()
                
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"No se pudo eliminar la categoría:\n{str(e)}")

    def eliminar_producto(self, producto_id):
        """Elimina un producto después de confirmación"""
        try:
            prod = session.query(Producto).get(producto_id)
            confirm = QMessageBox.question(
                self, 
                "Confirmar eliminación", 
                f"¿Estás seguro de eliminar el producto '{prod.nombre}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if confirm == QMessageBox.Yes:
                session.delete(prod)
                session.commit()
                QMessageBox.information(self, "Éxito", "Producto eliminado correctamente")
                self.cargar_listado()
                
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"No se pudo eliminar el producto:\n{str(e)}")

    # El método handle_category_action ya no es necesario con el uso de QDialog.exec()
    # y el manejo directo del resultado en abrir_nueva_categoria.
    # def handle_category_action(self, action_type: str, category_id: int):
    #     """Maneja las acciones emitidas por FormCategoria."""
    #     self.cargar_listado()
    #     if action_type == 'new_product':
    #         self.abrir_nuevo_producto(category_id)
    #     if hasattr(self, 'cat_win') and self.cat_win.isVisible():
    #         self.cat_win.close()
