from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QFrame, QMessageBox, QScrollArea, QSizePolicy, QDialog
)
from PySide6.QtCore import Qt, QSize, QTimer
from database import get_session
from models import Categoria, Producto
from gui.form_categoria import FormCategoria
from gui.form_producto import FormProducto
from utils.guards import require_perm_or_close
from utils.permisos import tiene_permiso_match
from sqlalchemy.exc import IntegrityError
from utils.dialogos import confirmar
from utils.estilos import PALETA


class FormListadoProductos(QWidget):
    def __init__(self, parent=None, usuario=None):
        super().__init__(parent)
        # --- seguridad: guard interna ---
        self.usuario = usuario or getattr(parent, "usuario", None)
        tokens = ("0220", "ver_listado_productos")  # token para ver el listado de productos
        if not require_perm_or_close(self, self.usuario, *tokens):
            return
        # --- fin guard ---
        self.setWindowTitle("Gestión de Categorías y Productos")
        
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
        btn_nueva_categoria = QPushButton("Nueva Categoría")
        btn_nueva_categoria.setObjectName("btn_nueva_categoria")
        i = PALETA["identidad"]
        btn_nueva_categoria.setStyleSheet(f"""
            QPushButton {{
                background-color: {i['primario']};
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {i['primario_hover']};
            }}
        """)
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
        pal_i = PALETA["identidad"]
        pal_a = PALETA["acciones"]
        # Limpiar layout existente (excepto título y botón superior)
        while self.layout_principal.count() > 2:
            child = self.layout_principal.takeAt(2)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self.clear_layout(child.layout())
        
        try:
            with get_session() as session:
                categorias = session.query(Categoria).all()
                productos_por_cat = {
                    cat.id: session.query(Producto).filter_by(categoria_id=cat.id).all()
                    for cat in categorias
                }
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el listado:\n{e}")
            return

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
            productos = productos_por_cat.get(cat.id, [])
            
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
                    btn_editar_prod = QPushButton("✎")
                    btn_editar_prod.setObjectName("btn_editar_prod")
                    btn_editar_prod.setToolTip("Editar producto")
                    btn_editar_prod.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {pal_i['primario']};
                            color: white;
                            padding: 6px 12px;
                            min-width: 35px;
                            max-width: 35px;
                            border: none;
                            border-radius: 4px;
                            font-weight: bold;
                        }}
                        QPushButton:hover {{
                            background-color: {pal_i['primario_hover']};
                        }}
                    """)
                    btn_editar_prod.clicked.connect(lambda checked=False, p_id=prod.id: self.abrir_editar_producto(p_id))

                    btn_eliminar_prod = QPushButton("✕")
                    btn_eliminar_prod.setObjectName("btn_eliminar_prod")
                    btn_eliminar_prod.setToolTip("Eliminar producto")
                    btn_eliminar_prod.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {pal_a['eliminar']};
                            color: white;
                            padding: 6px 12px;
                            min-width: 35px;
                            max-width: 35px;
                            border: none;
                            border-radius: 4px;
                            font-weight: bold;
                        }}
                        QPushButton:hover {{
                            background-color: {pal_a['eliminar_hover']};
                        }}
                    """)
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
            
            btn_nuevo_prod = QPushButton("Nuevo Producto")
            btn_nuevo_prod.setObjectName("btn_nuevo_prod")
            btn_nuevo_prod.setStyleSheet(f"""
                QPushButton {{
                    background-color: {pal_i['primario']};
                    color: white;
                    padding: 8px 16px;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {pal_i['primario_hover']};
                }}
            """)
            btn_nuevo_prod.clicked.connect(lambda checked=False, c_id=cat.id: self.abrir_nuevo_producto(c_id))

            btn_editar_cat = QPushButton("Editar Categoría")
            btn_editar_cat.setObjectName("btn_editar_cat")
            btn_editar_cat.setStyleSheet(f"""
                QPushButton {{
                    background-color: {pal_i['primario']};
                    color: white;
                    padding: 8px 16px;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {pal_i['primario_hover']};
                }}
            """)
            btn_editar_cat.clicked.connect(lambda checked=False, c_id=cat.id: self.abrir_editar_categoria(c_id))

            btn_eliminar_cat = QPushButton("Eliminar Categoría")
            btn_eliminar_cat.setObjectName("btn_eliminar_cat")
            btn_eliminar_cat.setStyleSheet(f"""
                QPushButton {{
                    background-color: {pal_a['eliminar']};
                    color: white;
                    padding: 8px 16px;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {pal_a['eliminar_hover']};
                }}
            """)
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
        dialog = FormCategoria(parent=self, usuario=self.usuario)
        print("DEBUG: Abriendo FormCategoria como diálogo modal.")
        result = dialog.exec()
        print(f"DEBUG: FormCategoria se cerró con resultado: {result} (Accepted={QDialog.Accepted}, Rejected={QDialog.Rejected})")
        print(f"DEBUG: create_new_product_flag={dialog.create_new_product_flag} | newly_created_category_id={dialog.newly_created_category_id}")

        if result == QDialog.Accepted:
            if dialog.create_new_product_flag:
                cat_id = dialog.newly_created_category_id
                print(f"DEBUG: Se pidió crear producto. cat_id={cat_id}")
                # 👉 Deferimos al próximo ciclo del event loop
                QTimer.singleShot(0, lambda cid=cat_id: self.abrir_nuevo_producto(cid))
                # ⚠️ Importante: no refrescar ahora; dejalo para después de cerrar FormProducto
                return
            else:
                print("DEBUG: No se solicitó crear producto.")
                self.cargar_listado()
        else:
            print("DEBUG: FormCategoria fue cancelado o hubo un error.")
            self.cargar_listado()


    def abrir_editar_categoria(self, categoria_id):
        """Abre el formulario para editar una categoría existente como un QDialog modal."""
        dialog = FormCategoria(categoria_id, parent=self, usuario=self.usuario)
        if dialog.exec() == QDialog.Accepted:
            self.cargar_listado() # Refrescar el listado principal
        else:
            self.cargar_listado() # Refrescar el listado si se canceló o hubo error

    def abrir_nuevo_producto(self, categoria_id=None):
        """Abre el formulario para crear un nuevo producto como un QDialog modal."""
        print(f"DEBUG: abrir_nuevo_producto llamado con categoria_id: {categoria_id}")
        dialog = FormProducto(parent=self)

        # Preseleccionar la categoría si se proporciona un ID
        if categoria_id is not None:
            dialog.cargar_categorias()  # Asegurarse de que las categorías estén cargadas
            index = dialog.categoria_combo.findData(categoria_id)
            if index >= 0:
                dialog.categoria_combo.setCurrentIndex(index)
            else:
                QMessageBox.warning(self, "Error", "La categoría seleccionada no se encontró en el listado de productos.")

        result = dialog.exec()  # Modal síncrono
        print(f"DEBUG: FormProducto se cerró con resultado: {result} (Accepted={QDialog.Accepted}, Rejected={QDialog.Rejected})")

        self.cargar_listado()

    def abrir_editar_producto(self, producto_id):
        """Abre el formulario para editar un producto existente como un QDialog modal."""
        dialog = FormProducto(producto_id, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.cargar_listado() # Refrescar el listado principal
        else:
            self.cargar_listado() # Refrescar el listado si se canceló o hubo error

    def eliminar_categoria(self, categoria_id):
        """Elimina una categoría después de confirmación (si no tiene productos)."""
        try:
            with get_session() as session:
                cat = session.get(Categoria, categoria_id)
                if not cat:
                    QMessageBox.warning(self, "Error", "Categoría no encontrada")
                    return
                cat_nombre = cat.nombre
                productos_count = session.query(Producto).filter_by(categoria_id=categoria_id).count()

            if productos_count > 0:
                QMessageBox.information(
                    self,
                    "No se puede eliminar",
                    f"Esta categoría tiene {productos_count} producto(s) asociado(s).\n"
                    "Primero eliminá o reasigná esos productos."
                )
                return

            if not confirmar(self, "Confirmar eliminación",
                             f"¿Estás seguro de eliminar la categoría '{cat_nombre}'?"):
                return

            with get_session() as session:
                cat = session.get(Categoria, categoria_id)
                if cat:
                    session.delete(cat)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Categoría eliminada correctamente")
            self.cargar_listado()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo eliminar la categoría:\n{str(e)}")

    def eliminar_producto(self, producto_id):
        """Elimina un producto después de confirmación"""
        try:
            with get_session() as session:
                prod = session.get(Producto, producto_id)
                if not prod:
                    QMessageBox.warning(self, "Error", "Producto no encontrado")
                    return
                prod_nombre = prod.nombre

            if not confirmar(self, "Confirmar eliminación",
                             f"¿Estás seguro de eliminar el producto '{prod_nombre}'?"):
                return

            with get_session() as session:
                prod = session.get(Producto, producto_id)
                if prod:
                    session.delete(prod)
                    session.commit()
            QMessageBox.information(self, "Éxito", "Producto eliminado correctamente")
            self.cargar_listado()

        except IntegrityError:
            QMessageBox.warning(
                self,
                "No se puede eliminar",
                "Este producto tiene ventas registradas y no puede eliminarse."
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo eliminar el producto:\n{str(e)}")
