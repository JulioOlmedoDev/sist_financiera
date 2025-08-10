from PySide6.QtWidgets import (
    QMainWindow, QLabel, QMenuBar, QMenu, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QFrame, QScrollArea, QSizePolicy,
    QStackedWidget, QToolButton, QMessageBox, QDialog
)
from PySide6.QtGui import QAction, QPixmap, QIcon, QFont, QColor, QPalette
from PySide6.QtCore import Qt, QSize, QTimer, QEvent, Signal, QPoint

from gui.form_cliente import FormCliente
from gui.form_venta import FormVenta
from gui.form_categoria import FormCategoria
from gui.form_producto import FormProducto
from gui.form_personal import FormPersonal
from gui.form_garante import FormGarante
from gui.form_usuario import FormUsuario
from gui.form_permisos import FormPermisos
from utils.permisos import tiene_permiso
from gui.form_consultas import FormConsultas
from gui.form_gestion_clientes import FormGestionClientes
from gui.form_gestion_garantes import FormGestionGarantes
from gui.form_listado_ventas import FormVentas
from gui.form_cobro import FormCobro
from gui.dialog_tasas import DialogTasas
from gui.form_listado_productos import FormListadoProductos
from gui.form_gestion_personal import FormGestionPersonal
from gui.form_listado_usuarios import FormListadoUsuarios


class BotonNavegacion(QPushButton):
    """Botón personalizado para la navegación"""
    def __init__(self, texto, icono=None, parent=None):
        super().__init__(parent)
        self.setText(texto)
        self.setMinimumHeight(50)
        self.setCursor(Qt.PointingHandCursor)
        
        if icono:
            self.setIcon(QIcon(icono))
            self.setIconSize(QSize(24, 24))
        
        # Estilo para botones de navegación
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                color: #e0e0e0;
                font-size: 16px;
                font-weight: bold;
                text-align: left;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)

class VentanaPrincipal(QMainWindow):
    def __init__(self, usuario):
        super().__init__()
        self.usuario = usuario  # Usuario logueado
        self.setWindowTitle(f"CREDANZA - Sistema de Gestión")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(1000, 700)
        
        # Estado de navegación
        self.menu_actual = "principal"  # "principal" o el nombre del módulo
        
        # Aplicar estilo global
        self.aplicar_estilo()
        
        # Widget central
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Layout principal (horizontal)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Crear sidebar
        self.crear_sidebar()
        
        # Crear área de contenido
        self.crear_area_contenido()
        
        # Inicializar la pantalla de bienvenida
        self.mostrar_bienvenida()

    def aplicar_estilo(self):
        # Estilo global de la aplicación
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #424242;
                font-size: 14px;
            }
            QLabel#titulo {
                color: #7b1fa2;
                font-size: 24px;
                font-weight: bold;
            }
            QLabel#subtitulo {
                color: #9c27b0;
                font-size: 18px;
                font-weight: bold;
            }
            QLabel#bienvenida {
                color: #7b1fa2;
                font-size: 32px;
                font-weight: bold;
            }
            QPushButton {
                background-color: #9c27b0;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7b1fa2;
            }
            QPushButton:pressed {
                background-color: #6a1b9a;
            }
            QFrame#sidebar {
                background-color: #4a148c;
                border-right: 1px solid #3e1178;
            }
            QFrame#header {
                background-color: white;
                border-bottom: 1px solid #e0e0e0;
            }
            QFrame#content {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
        """)

    def crear_sidebar(self):
        # Frame para la barra lateral
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMinimumWidth(250)
        self.sidebar.setMaximumWidth(250)

        
        # Layout para la barra lateral
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(10, 20, 10, 20)
        self.sidebar_layout.setSpacing(5)
        
        # Logo
        self.logo_label = QLabel()
        logo_pixmap = QPixmap("static/logo.jpg")
        self.logo_label.setPixmap(logo_pixmap.scaled(200, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.sidebar_layout.addWidget(self.logo_label)
        
        # Nombre de usuario
        self.user_label = QLabel(f"Bienvenido,\n{self.usuario.nombre}")
        self.user_label.setStyleSheet("color: white; font-size: 16px; margin-top: 10px;")
        self.user_label.setAlignment(Qt.AlignCenter)
        self.sidebar_layout.addWidget(self.user_label)
        
        # Separador
        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setFrameShadow(QFrame.Sunken)
        self.separator.setStyleSheet("background-color: rgba(255, 255, 255, 0.2); margin: 15px 0;")
        self.sidebar_layout.addWidget(self.separator)
        
        # Contenedor para los menús (principal y submenús)
        self.menu_container = QWidget()
        self.menu_layout = QVBoxLayout(self.menu_container)
        self.menu_layout.setContentsMargins(0, 0, 0, 0)
        self.menu_layout.setSpacing(5)
        
        # Crear menú principal
        self.crear_menu_principal()
        
        # Añadir contenedor de menús al sidebar
        self.sidebar_layout.addWidget(self.menu_container)
        
        # Espaciador
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.sidebar_layout.addWidget(spacer)
        
        # Botón de cerrar sesión
        btn_logout = BotonNavegacion("  Cerrar Sesión", "static/icons/log-out.png")
        self.sidebar_layout.addWidget(btn_logout)
        btn_logout.clicked.connect(self.cerrar_sesion)

        
        # Añadir sidebar al layout principal
        self.main_layout.addWidget(self.sidebar)

    def crear_menu_principal(self):
        """Crea el menú principal con los módulos"""
        # Limpiar el contenedor de menús
        self.limpiar_layout(self.menu_layout)
        
        # Botón de inicio
        btn_inicio = BotonNavegacion("  Inicio", "static/icons/home.png")
        btn_inicio.clicked.connect(lambda: self.mostrar_formulario_inicio())
        self.menu_layout.addWidget(btn_inicio)
        
        # Módulo de Ventas
        if any(tiene_permiso(self.usuario, p) for p in ["cargar_cliente", "crear_venta"]):
            btn_ventas = BotonNavegacion("  Ventas", "static/icons/shopping-cart.png")
            btn_ventas.clicked.connect(lambda: self.mostrar_submenu("ventas"))
            self.menu_layout.addWidget(btn_ventas)
        
        # Módulo de Consultas
        if tiene_permiso(self.usuario, "ver_ventas"):
            btn_consultas = BotonNavegacion("  Consultas", "static/icons/search.png")
            btn_consultas.clicked.connect(lambda: self.mostrar_submenu("consultas"))
            self.menu_layout.addWidget(btn_consultas)
        
        # Módulo de Productos
        if any(tiene_permiso(self.usuario, p) for p in ["crear_categoria", "crear_producto"]):
            btn_productos = BotonNavegacion("  Productos", "static/icons/package.png")
            btn_productos.clicked.connect(lambda: self.mostrar_submenu("productos"))
            self.menu_layout.addWidget(btn_productos)
        
        # Módulo de Personal
        if any(tiene_permiso(self.usuario, p) for p in ["cargar_personal", "asignar_usuario", "asignar_permisos"]):
            btn_personal = BotonNavegacion("  Personal", "static/icons/users.png")
            btn_personal.clicked.connect(lambda: self.mostrar_submenu("personal"))
            self.menu_layout.addWidget(btn_personal)

        # Configuración de Tasas
        btn_tasas = BotonNavegacion("  Configurar Tasas", "static/icons/percent.png")
        btn_tasas.clicked.connect(self.abrir_dialog_tasas)
        self.menu_layout.addWidget(btn_tasas)
        
        # Módulo de Cobros
        btn_cobros = BotonNavegacion("  Cobros", "static/icons/credit-card.png")
        btn_cobros.clicked.connect(lambda: self.mostrar_submenu("cobros"))
        self.menu_layout.addWidget(btn_cobros)
        
        # Actualizar estado
        self.menu_actual = "principal"

    def mostrar_submenu(self, modulo):
        """Muestra el submenú correspondiente al módulo seleccionado"""
        # Limpiar el contenedor de menús
        self.limpiar_layout(self.menu_layout)
        
        # Botón para volver al menú principal
        btn_volver = BotonNavegacion("  Volver al menú", "static/icons/arrow-left.png")
        btn_volver.clicked.connect(self.crear_menu_principal)
        self.menu_layout.addWidget(btn_volver)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: rgba(255, 255, 255, 0.2); margin: 10px 0;")
        self.menu_layout.addWidget(separator)
        
        # Título del módulo
        titulo_modulo = QLabel(f"  Módulo: {modulo.capitalize()}")
        titulo_modulo.setStyleSheet("color: white; font-size: 16px; font-weight: bold; margin: 5px 0;")
        self.menu_layout.addWidget(titulo_modulo)

        # ✅ NUEVO: actualizar título superior
        self.titulo_pagina.setText(modulo.capitalize())
        
        # Opciones según el módulo
        if modulo == "ventas":
            if tiene_permiso(self.usuario, "cargar_cliente"):
                btn_clientes = BotonNavegacion("  Clientes", "static/icons/users.png")
                btn_clientes.clicked.connect(self.abrir_form_cliente)
                self.menu_layout.addWidget(btn_clientes)
                
                btn_garantes = BotonNavegacion("  Garantes", "static/icons/user-check.png")
                btn_garantes.clicked.connect(self.abrir_form_garante)
                self.menu_layout.addWidget(btn_garantes)

                btn_gestion_clientes = BotonNavegacion("  Listado de Clientes", "static/icons/list.png")
                btn_gestion_clientes.clicked.connect(self.abrir_gestion_clientes)
                self.menu_layout.addWidget(btn_gestion_clientes)
            
                btn_gestion_garantes = BotonNavegacion("  Listado de Garantes", "static/icons/list.png")
                btn_gestion_garantes.clicked.connect(self.abrir_gestion_garantes)
                self.menu_layout.addWidget(btn_gestion_garantes)

                btn_listado_ventas = BotonNavegacion("  Listado de Ventas", "static/icons/list.png")
                btn_listado_ventas.clicked.connect(self.abrir_listado_ventas)
                self.menu_layout.addWidget(btn_listado_ventas)


            if tiene_permiso(self.usuario, "crear_venta"):
                btn_ventas = BotonNavegacion("  Ventas", "static/icons/dollar-sign.png")
                btn_ventas.clicked.connect(self.abrir_form_venta)
                self.menu_layout.addWidget(btn_ventas)
        
        elif modulo == "consultas":
            btn_consultas = BotonNavegacion("  Consultas Generales", "static/icons/search.png")
            btn_consultas.clicked.connect(self.abrir_form_consultas)
            self.menu_layout.addWidget(btn_consultas)


        elif modulo == "productos":
            if tiene_permiso(self.usuario, "crear_categoria"):
                btn_categorias = BotonNavegacion("  Categorías", "static/icons/tag.png")
                btn_categorias.clicked.connect(self.abrir_form_categoria)
                self.menu_layout.addWidget(btn_categorias)
            
            if tiene_permiso(self.usuario, "crear_producto"):
                btn_productos = BotonNavegacion("  Productos", "static/icons/box.png")
                btn_productos.clicked.connect(self.abrir_form_producto)
                self.menu_layout.addWidget(btn_productos)

            # ✅ Agregado: botón para ver listado de categorías y productos
            btn_listado = BotonNavegacion("  Listado", "static/icons/list.png")
            btn_listado.clicked.connect(self.abrir_listado_productos)
            self.menu_layout.addWidget(btn_listado)

        elif modulo == "personal":
            if tiene_permiso(self.usuario, "cargar_personal"):
                btn_personal = BotonNavegacion("  Personal", "static/icons/user-plus.png")
                btn_personal.clicked.connect(self.abrir_form_personal)
                self.menu_layout.addWidget(btn_personal)

                btn_gestion_personal = BotonNavegacion("  Listado de Personal", "static/icons/list.png")
                btn_gestion_personal.clicked.connect(self.abrir_gestion_personal)
                self.menu_layout.addWidget(btn_gestion_personal)

            if tiene_permiso(self.usuario, "asignar_usuario"):
                btn_usuarios = BotonNavegacion("  Usuarios", "static/icons/user.png")
                btn_usuarios.clicked.connect(self.abrir_form_usuario)
                self.menu_layout.addWidget(btn_usuarios)

                # ✅ NUEVO: Botón para ver el listado de usuarios
                btn_listado_usuarios = BotonNavegacion("  Listado de Usuarios", "static/icons/list.png")
                btn_listado_usuarios.clicked.connect(self.abrir_listado_usuarios)
                self.menu_layout.addWidget(btn_listado_usuarios)

            if tiene_permiso(self.usuario, "asignar_permisos"):
                btn_permisos = BotonNavegacion("  Permisos", "static/icons/shield.png")
                btn_permisos.clicked.connect(self.abrir_form_permisos)
                self.menu_layout.addWidget(btn_permisos)
        
        elif modulo == "cobros":
            btn_gestion_cobros = BotonNavegacion("  Gestión de Cobros", "static/icons/credit-card.png")
            btn_gestion_cobros.clicked.connect(self.abrir_form_cobros)
            self.menu_layout.addWidget(btn_gestion_cobros)

        
        # Actualizar estado
        self.menu_actual = modulo

    def limpiar_layout(self, layout):
        """Limpia todos los widgets de un layout"""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

    def crear_area_contenido(self):
        # Contenedor principal para el contenido
        self.content_container = QWidget()
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Header
        self.header = QFrame()
        self.header.setObjectName("header")
        self.header.setMinimumHeight(60)
        self.header.setMaximumHeight(60)
        
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        self.titulo_pagina = QLabel("Inicio")
        self.titulo_pagina.setObjectName("titulo")
        header_layout.addWidget(self.titulo_pagina)
        
        content_layout.addWidget(self.header)
        
        # Área de contenido con scroll
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        
        # Widget para contener el contenido real
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(20)
        
        self.scroll_area.setWidget(self.content_widget)
        content_layout.addWidget(self.scroll_area)
        
        # Añadir el contenedor de contenido al layout principal
        self.main_layout.addWidget(self.content_container, 1)
        
        # Crear un stacked widget para manejar múltiples formularios
        self.stacked_widget = QStackedWidget()
        self.content_layout.addWidget(self.stacked_widget)

    def mostrar_bienvenida(self):
        # Crear widget de bienvenida
        welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(welcome_widget)
        welcome_layout.setAlignment(Qt.AlignCenter)

        # Logo grande
        logo_label = QLabel()
        logo_pixmap = QPixmap("static/logo.jpg")
        logo_label.setPixmap(logo_pixmap.scaled(300, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(logo_label)

        # Mensaje de bienvenida
        bienvenida_label = QLabel(f"Bienvenido al Sistema CREDANZA")
        bienvenida_label.setObjectName("bienvenida")
        bienvenida_label.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(bienvenida_label)

        # Nombre de usuario
        usuario_label = QLabel(f"{self.usuario.nombre}")
        usuario_label.setObjectName("subtitulo")
        usuario_label.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(usuario_label)

        # Fecha actual
        from datetime import datetime
        fecha_label = QLabel(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")
        fecha_label.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(fecha_label)

        # Mostrar usando la función estándar (para que se actualice el título y el contenido)
        self.mostrar_formulario(welcome_widget, "Inicio")

        # Asegurar que estamos en el menú principal
        if self.menu_actual != "principal":
            self.crear_menu_principal()


    def limpiar_contenido(self):
        # Limpiar el layout de contenido
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

    def mostrar_formulario(self, formulario, titulo):
        # Actualizar título
        self.titulo_pagina.setText(titulo)
        
        # Limpiar el contenido actual
        self.limpiar_contenido()
        
        # Crear un frame para el formulario
        form_frame = QFrame()
        form_frame.setObjectName("content")
        form_layout = QVBoxLayout(form_frame)
        
        # Añadir el formulario al frame
        form_layout.addWidget(formulario)
        
        # Añadir el frame al contenido
        self.content_layout.addWidget(form_frame)

    def abrir_form_cliente(self):
        formulario = FormCliente()
        self.mostrar_formulario(formulario, "Gestión de Clientes")

    def abrir_form_garante(self):
        formulario = FormGarante()
        self.mostrar_formulario(formulario, "Gestión de Garantes")

    def abrir_form_venta(self):
        formulario = FormVenta()
        formulario.sale_saved.connect(self.abrir_listado_ventas)
        self.mostrar_formulario(formulario, "Gestión de Ventas")

    def abrir_form_categoria(self):
        formulario = FormCategoria()
        self.mostrar_formulario(formulario, "Gestión de Categorías")

    def abrir_form_producto(self):
        formulario = FormProducto()
        self.mostrar_formulario(formulario, "Gestión de Productos")

    def abrir_form_personal(self):
        formulario = FormPersonal()
        self.mostrar_formulario(formulario, "Gestión de Personal")

    def abrir_form_usuario(self):
        formulario = FormUsuario()
        self.mostrar_formulario(formulario, "Gestión de Usuarios")

    def abrir_form_permisos(self):
        formulario = FormPermisos()
        self.mostrar_formulario(formulario, "Gestión de Permisos")

    def abrir_form_consultas(self):
        formulario = FormConsultas()
        self.mostrar_formulario(formulario, "Consultas Generales")

    def abrir_gestion_clientes(self):
        formulario = FormGestionClientes()
        self.mostrar_formulario(formulario, "Gestión de Clientes")

    def abrir_gestion_garantes(self):
        formulario = FormGestionGarantes()
        self.mostrar_formulario(formulario, "Gestión de Garantes")

    def abrir_listado_ventas(self):
        formulario = FormVentas()
        self.mostrar_formulario(formulario, "Listado de Ventas")

    def abrir_form_cobros(self):
        # Antes: lo embebías en el área central
        # formulario = FormCobro()
        # self.mostrar_formulario(formulario, "Gestión de Cobros")

        # Ahora: misma modalidad que desde Listado de Ventas
        self.form_cobros = FormCobro()
        self.form_cobros.setWindowModality(Qt.ApplicationModal)
        self.form_cobros.setAttribute(Qt.WA_DeleteOnClose)
        self.form_cobros.showMaximized()


    def cerrar_sesion(self):
        from PySide6.QtWidgets import QApplication
        confirm = QMessageBox.question(
            self, "Cerrar sesión", "¿Estás seguro de que querés cerrar sesión?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            QApplication.quit()

    def abrir_dialog_tasas(self):
        dlg = DialogTasas()
        if dlg.exec() == QDialog.Accepted:
            QMessageBox.information(self, "Tasas", "Tasas actualizadas correctamente.")

    def abrir_listado_productos(self):
        formulario = FormListadoProductos()
        self.mostrar_formulario(formulario, "Listado de Categorías y Productos")

    def abrir_gestion_personal(self):
        formulario = FormGestionPersonal()
        self.mostrar_formulario(formulario, "Listado de Personal")

    def abrir_listado_usuarios(self):
        from gui.form_listado_usuarios import FormListadoUsuarios
        self.mostrar_formulario(FormListadoUsuarios(), "Listado de Usuarios")

    def mostrar_formulario_inicio(self):
        self.titulo_pagina.setText("Inicio")
        self.limpiar_contenido()
        self.mostrar_bienvenida()





