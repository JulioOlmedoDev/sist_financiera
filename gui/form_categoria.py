from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QMessageBox, QHBoxLayout, QFrame
)
from PySide6.QtCore import Qt, Signal

from database import session
from models import Categoria, Producto
from utils.guards import require_perm_or_close

class FormCategoria(QDialog):
    category_action_completed = Signal(str, int)

    def __init__(self, categoria_id=None, parent=None, usuario=None):
        super().__init__(parent)        
        self.categoria_id = categoria_id
        self.editando = categoria_id is not None
        # --- seguridad: guard interna ---
        # Preferimos el usuario explícito pasado; si no vino, intentar obtenerlo del parent (VentanaPrincipal)
        self.usuario = usuario or getattr(parent, "usuario", None)

        # Si no tiene permiso: require_perm_or_close mostrará mensaje y cerrará/rechazará el diálogo.
        # IMPORTANTE: si devuelve False debemos salir del __init__ para no inicializar el resto del diálogo.
        if not require_perm_or_close(self, self.usuario, "0200", "crear_categoria"):
            return
        
        # Variables para comunicar el resultado al padre
        self.create_new_product_flag = False
        self.newly_created_category_id = None

        # Configuración de la ventana
        self.setWindowTitle("Gestión de Categoría" if not self.editando else "Editar Categoría")
        self.setFixedSize(600, 440)

        # Hacer el diálogo explícitamente modal y ocultar el botón de ayuda
        self.setModal(True)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

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
                padding: 0px;
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
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)

        
        # Título principal
        titulo = QLabel()
        titulo.setTextFormat(Qt.RichText)
        titulo.setText(
            f'<div style="line-height:135%; padding-bottom:2px; color:#4a148c; '
            f'font-weight:700; font-size:20px;">'
            f'📁 {"Nueva Categoría" if not self.editando else "Editar Categoría"}'
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
        # Si el usuario tipea, limpiar estilos de error
        self.nombre_input.textChanged.connect(lambda: self.nombre_input.setStyleSheet(""))

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
            self.btn_eliminar = QPushButton("🗑️ Eliminar")
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
            self.btn_cancelar.clicked.connect(self.reject)
            
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
            for b in (self.btn_eliminar, self.btn_cancelar, self.btn_guardar):
                b.setFixedSize(150, 44)

            self.btn_eliminar.setToolTip("Eliminar definitivamente la categoría")
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
            self.btn_cancelar.clicked.connect(self.reject)
            
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

            # Tooltips y botón por defecto
            self.btn_cancelar.setToolTip("Cerrar sin guardar")
            self.btn_guardar.setToolTip("Guardar categoría")

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

    def cargar_datos(self):
        """Carga los datos de la categoría para edición"""
        try:
            categoria = session.get(Categoria, self.categoria_id)
            if categoria:
                self.nombre_input.setText(categoria.nombre)
            else:
                QMessageBox.warning(self, "Error", "Categoría no encontrada")
                self.reject() 
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar datos:\n{str(e)}")
            self.reject()

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
                categoria = session.get(Categoria, self.categoria_id)
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
                self.newly_created_category_id = categoria.id 
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

            # --- Nuevo flujo post-guardado (para QDialog) ---
            if not self.editando:  # Solo para nuevas categorías
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Question)
                msg.setWindowTitle("Continuar")
                msg.setText("¿Qué querés hacer ahora?")
                btn_otra = msg.addButton("➕ Otra categoría", QMessageBox.YesRole)
                btn_prod = msg.addButton("➕ Nuevo producto", QMessageBox.AcceptRole)
                btn_cerrar = msg.addButton("Cerrar", QMessageBox.RejectRole)
                msg.exec()

                clicked = msg.clickedButton()

                if clicked is btn_otra:
                    print("DEBUG: Usuario eligió crear otra categoría. Mantener diálogo abierto.")
                    self.limpiar_formulario()
                    self.setWindowTitle("Gestión de Categoría")
                    self.editando = False
                    self.nombre_input.setFocus()
                    return

                elif clicked is btn_prod:
                    print(f"DEBUG: Usuario eligió crear producto. category_id={self.newly_created_category_id}")
                    self.create_new_product_flag = True
                    self.accept()

                else:
                    print("DEBUG: Usuario eligió Cerrar.")
                    self.accept()

            else:
                print("DEBUG: Editando categoría. Aceptando diálogo.")
                self.accept()
                
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"No se pudo guardar la categoría:\n{str(e)}")
            self.reject() 

    def eliminar_categoria(self):
        """Elimina la categoría si no tiene productos asociados."""
        try:
            categoria = session.get(Categoria, self.categoria_id)
            if not categoria:
                QMessageBox.warning(self, "Error", "Categoría no encontrada")
                self.reject()
                return

            productos_count = session.query(Producto).filter_by(categoria_id=self.categoria_id).count()
            if productos_count > 0:
                print(f"DEBUG: Intento de eliminar categoría con {productos_count} producto(s)")
                QMessageBox.information(
                    self,
                    "No se puede eliminar",
                    f"Esta categoría tiene {productos_count} producto(s) asociado(s).\n"
                    "Primero eliminá o reasigná esos productos."
                )
                return

            confirm = QMessageBox.question(
                self,
                "Confirmar eliminación",
                f"¿Estás seguro de eliminar la categoría '{categoria.nombre}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                session.delete(categoria)
                session.commit()
                print("DEBUG: Categoría eliminada OK")
                QMessageBox.information(self, "Éxito", "Categoría eliminada correctamente")
                self.accept()
            else:
                print("DEBUG: Usuario canceló eliminación de categoría")
                return

        except Exception as e:
            session.rollback()
            print(f"DEBUG: Error inesperado al eliminar categoría: {e}")
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
            self.reject() 
        else:
            super().keyPressEvent(event)
