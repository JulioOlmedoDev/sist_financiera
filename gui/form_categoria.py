from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QMessageBox, QHBoxLayout, QFrame
)
from PySide6.QtCore import Qt, Signal

from database import session
from models import Categoria, Producto

class FormCategoria(QDialog): # Cambiado a QDialog
    # Señal para comunicar acciones al formulario padre (FormListadoProductos)
    # Argumentos: 'action_type' (str), 'category_id' (int, opcional)
    # Esta señal ahora se usará para comunicar la intención, no para el cierre directo
    category_action_completed = Signal(str, int)

    def __init__(self, categoria_id=None):
        super().__init__()
        self.categoria_id = categoria_id
        self.editando = categoria_id is not None
        
        # Variables para comunicar el resultado al padre
        self.create_new_product_flag = False
        self.newly_created_category_id = None

        # Configuración de la ventana
        self.setWindowTitle("Gestión de Categoría" if not self.editando else "Editar Categoría")
        self.setFixedSize(500, 350)
        
        # Aplicar estilos consistentes
        self.setStyleSheet("""
            QDialog { /* Cambiado a QDialog */
                background-color: #fdfdfd;
                font-size: 14px;
                font-family: Arial, sans-serif;
            }
            QFrame[objectName="main_card"] {
                background-color: #f3e5f5;
                border: 2px solid #9c27b0;
                border-radius: 12px;
                padding: 25px;
            }
            QLabel {
                color: #333;
                font-weight: bold;
            }
            QLineEdit {
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 14px;
                background-color: #fff;
                min-height: 20px;
            }
            QLineEdit:focus {
                border: 2px solid #9c27b0;
            }
            QPushButton {
                background-color: #9c27b0;
                color: white;
                padding: 10px 20px;
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
        """)
        
        # Layout principal de la ventana
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Tarjeta principal con el estilo de categoría
        main_card = QFrame()
        main_card.setObjectName("main_card")
        card_layout = QVBoxLayout(main_card)
        card_layout.setSpacing(15)
        
        # Título principal
        titulo = QLabel("📁 Nueva Categoría" if not self.editando else "📁 Editar Categoría")
        titulo.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #4a148c;
                margin-bottom: 10px;
            }
        """)
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
        
        # Campo nombre
        nombre_label = QLabel("Nombre de la Categoría *")
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
        self.nombre_input.setPlaceholderText("Ingrese el nombre de la categoría...")
        card_layout.addWidget(self.nombre_input)
        
        # Texto de ayuda
        ayuda_label = QLabel("* Campo obligatorio")
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
            # Layout para botón eliminar (izquierda)
            botones_principales = QHBoxLayout()
            
            # Botón eliminar a la izquierda
            self.btn_eliminar = QPushButton("🗑️ Eliminar Categoría")
            self.btn_eliminar.setStyleSheet("""
                QPushButton {
                    background-color: #e53935;
                    min-width: 140px;
                }
                QPushButton:hover {
                    background-color: #c62828;
                }
            """)
            self.btn_eliminar.clicked.connect(self.eliminar_categoria)
            botones_principales.addWidget(self.btn_eliminar)
            
            botones_principales.addStretch()
            
            # Botones principales a la derecha
            self.btn_cancelar = QPushButton("Cancelar")
            self.btn_cancelar.setStyleSheet("""
                QPushButton {
                    background-color: #757575;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #616161;
                }
            """)
            self.btn_cancelar.clicked.connect(self.reject) # Usar reject para QDialog
            
            self.btn_guardar = QPushButton("✏️ Actualizar")
            self.btn_guardar.setStyleSheet("""
                QPushButton {
                    background-color: #4caf50;
                    min-width: 100px;
                }
                QPushButton:hover {
                    background-color: #388e3c;
                }
            """)
            self.btn_guardar.clicked.connect(self.guardar_categoria)
            
            botones_principales.addWidget(self.btn_cancelar)
            botones_principales.addWidget(self.btn_guardar)
            
            card_layout.addLayout(botones_principales)
        else:
            # Solo botones de guardar y cancelar
            botones_layout = QHBoxLayout()
            botones_layout.addStretch()
            
            self.btn_cancelar = QPushButton("Cancelar")
            self.btn_cancelar.setStyleSheet("""
                QPushButton {
                    background-color: #757575;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #616161;
                }
            """)
            self.btn_cancelar.clicked.connect(self.reject) # Usar reject para QDialog
            
            self.btn_guardar = QPushButton("💾 Guardar")
            self.btn_guardar.setStyleSheet("""
                QPushButton {
                    background-color: #4caf50;
                    min-width: 100px;
                }
                QPushButton:hover {
                    background-color: #388e3c;
                }
            """)
            self.btn_guardar.clicked.connect(self.guardar_categoria)
            
            botones_layout.addWidget(self.btn_cancelar)
            botones_layout.addWidget(self.btn_guardar)
            card_layout.addLayout(botones_layout)
        
        main_layout.addWidget(main_card)
        
        # Cargar datos si estamos editando
        if self.editando:
            self.cargar_datos()
        
        # Enfocar el campo de texto
        self.nombre_input.setFocus()

    def cargar_datos(self):
        """Carga los datos de la categoría para edición"""
        try:
            categoria = session.query(Categoria).get(self.categoria_id)
            if categoria:
                self.nombre_input.setText(categoria.nombre)
            else:
                QMessageBox.warning(self, "Error", "Categoría no encontrada")
                self.reject() # Cerrar con reject si no se encuentra
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar datos:\n{str(e)}")
            self.reject() # Cerrar con reject en caso de error

    def guardar_categoria(self):
        """Guarda o actualiza la categoría y maneja el flujo post-guardado."""
        nombre = self.nombre_input.text().strip()
        
        # Validación
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
            QMessageBox.warning(self, "Campo requerido", "Por favor ingrese el nombre de la categoría")
            self.nombre_input.setFocus()
            return
        
        # Resetear estilo del campo
        self.nombre_input.setStyleSheet("")
        
        try:
            if self.editando:
                # Actualizar categoría existente
                categoria = session.query(Categoria).get(self.categoria_id)
                if categoria:
                    categoria.nombre = nombre
                    mensaje_exito = "Categoría actualizada correctamente"
                else:
                    QMessageBox.warning(self, "Error", "Categoría no encontrada")
                    return
            else:
                # Crear nueva categoría
                categoria_existente = session.query(Categoria).filter_by(nombre=nombre).first()
                if categoria_existente:
                    QMessageBox.warning(self, "Categoría duplicada", 
                                  f"Ya existe una categoría con el nombre '{nombre}'")
                    return
                
                categoria = Categoria(nombre=nombre)
                session.add(categoria)
                session.flush() # Obtener el ID antes del commit final
                self.newly_created_category_id = categoria.id # Guardar el ID en la instancia
                mensaje_exito = "Categoría creada correctamente"            

            session.commit()
            print(f"DEBUG: Categoría guardada. ID de la nueva categoría: {self.newly_created_category_id}") # AÑADE ESTA LÍNEA
            
            # Mostrar mensaje de éxito
            info_box = QMessageBox(self)
            info_box.setIcon(QMessageBox.Information)
            info_box.setText(mensaje_exito)
            info_box.setWindowTitle("Éxito")
            info_box.setStandardButtons(QMessageBox.Ok)
            info_box.exec()

            # --- Nuevo flujo de preguntas (para QDialog) ---
            if not self.editando: # Solo para nuevas categorías
                respuesta_nueva_categoria = QMessageBox.question(
                    self, 
                    "Continuar", 
                    "¿Desea crear una nueva categoría?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if respuesta_nueva_categoria == QMessageBox.Yes:
                    self.limpiar_formulario()
                    self.setWindowTitle("Gestión de Categoría")
                    self.editando = False
                    self.nombre_input.setFocus()
                    print("DEBUG: Usuario eligió crear otra categoría. Manteniendo diálogo abierto.") # AÑADE ESTA LÍNEA
                    return 
                else:
                    respuesta_nuevo_producto = QMessageBox.question(
                        self, 
                        "Continuar", 
                        "¿Desea crear un nuevo producto dentro de esta categoría?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    
                    if respuesta_nuevo_producto == QMessageBox.Yes:
                        self.create_new_product_flag = True # Establecer la bandera
                        print(f"DEBUG: Usuario eligió crear nuevo producto. Bandera: {self.create_new_product_flag}. ID: {self.newly_created_category_id}. Aceptando diálogo.") # AÑADE ESTA LÍNEA
                        self.accept() # Cerrar el diálogo con Accepted
                    else:
                        print("DEBUG: Usuario NO eligió crear nuevo producto. Aceptando diálogo.") # AÑADE ESTA LÍNEA
                        self.accept() # Cerrar el diálogo con Accepted (sin crear producto)
            else: # Si estaba editando, simplemente cerrar
                print("DEBUG: Editando categoría. Aceptando diálogo.") # AÑADE ESTA LÍNEA
                self.accept() # Cerrar el diálogo con Accepted
                
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"No se pudo guardar la categoría:\n{str(e)}")
            self.reject() # Cerrar con reject en caso de error

    def eliminar_categoria(self):
        """Elimina la categoría después de confirmación"""
        try:
            categoria = session.query(Categoria).get(self.categoria_id)
            if not categoria:
                QMessageBox.warning(self, "Error", "Categoría no encontrada")
                self.reject()
                return
            
            # Verificar si tiene productos asociados
            productos_count = session.query(Producto).filter_by(categoria_id=self.categoria_id).count()
            
            mensaje = f"¿Estás seguro de eliminar la categoría '{categoria.nombre}'?"
            if productos_count > 0:
                mensaje += f"\n\n⚠️ ATENCIÓN: Esta categoría tiene {productos_count} producto(s) asociado(s)."
                mensaje += "\nAl eliminar la categoría también se eliminarán todos sus productos."
            
            confirm = QMessageBox.question(
                self, 
                "Confirmar eliminación", 
                mensaje,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if confirm == QMessageBox.Yes:
                session.delete(categoria)
                session.commit()
                QMessageBox.information(self, "Éxito", "Categoría eliminada correctamente")
                self.accept() # Cerrar con accept después de eliminar
            else:
                self.reject() # Si no confirma, cerrar con reject
                
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"No se pudo eliminar la categoría:\n{str(e)}")
            self.reject()

    def limpiar_formulario(self):
        """Limpia los campos del formulario."""
        self.nombre_input.clear()
        self.nombre_input.setStyleSheet("") # Resetear estilo de validación
        self.nombre_input.setFocus()
        self.setWindowTitle("Gestión de Categoría") # Asegurarse de que el título sea para "Nueva"
        self.create_new_product_flag = False # Resetear bandera
        self.newly_created_category_id = None # Resetear ID

    def keyPressEvent(self, event):
        """Maneja eventos de teclado"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.guardar_categoria()
        elif event.key() == Qt.Key_Escape:
            self.reject() # Usar reject para QDialog
        else:
            super().keyPressEvent(event)
