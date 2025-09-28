from PySide6.QtWidgets import (
    QMainWindow, QLabel, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QFrame, QScrollArea, QSizePolicy,
    QStackedWidget, QMessageBox, QDialog
)
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt, QSize

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
    """Botón personalizado para la navegación con soporte de estado activo."""
    def __init__(self, texto, icono=None, parent=None):
        super().__init__(parent)
        self.setText(texto)
        self.setMinimumHeight(50)
        self.setCursor(Qt.PointingHandCursor)
        if icono:
            self.setIcon(QIcon(icono))
            self.setIconSize(QSize(24, 24))
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                color: #e0e0e0;
                font-size: 16px;
                font-weight: bold;
                text-align: left;
                padding: 10px 14px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.10);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.18);
            }
            /* Estado activo persistente */
            QPushButton[active="true"] {
                background-color: rgba(255, 255, 255, 0.18);
                border: 1px solid rgba(255, 255, 255, 0.25);
                color: #ffffff;
            }
            QPushButton[active="true"]:hover {
                background-color: rgba(255, 255, 255, 0.22);
            }
        """)

    def set_active(self, is_active: bool):
        self.setProperty("active", is_active)
        # Forzar refresco del stylesheet
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class VentanaPrincipal(QMainWindow):
    def __init__(self, usuario):
        super().__init__()
        if not usuario:
            QMessageBox.critical(self, "Sesión requerida", "Debés iniciar sesión para usar el sistema.")
            from PySide6.QtWidgets import QApplication
            QApplication.quit()
            return
        self.usuario = usuario  # Usuario logueado
        self.setWindowTitle("CREDANZA - Sistema de Gestión")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(1000, 700)

        # Estado de navegación
        self.menu_actual = "principal"
        self.active_menu_btn = None
        self.active_sub_btn = None

        # Estilo global
        self.aplicar_estilo()

        # Widget central
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Layout principal
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Sidebar + Contenido
        self.crear_sidebar()
        self.crear_area_contenido()

        # Bienvenida
        self.mostrar_bienvenida()

    # ---------- Estilos ----------
    def aplicar_estilo(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #f5f5f5; }
            QLabel { color: #424242; font-size: 14px; }
            QLabel#titulo { color: #7b1fa2; font-size: 24px; font-weight: bold; }
            QLabel#subtitulo { color: #9c27b0; font-size: 18px; font-weight: bold; }
            QLabel#bienvenida { color: #7b1fa2; font-size: 32px; font-weight: bold; }
            QPushButton {
                background-color: #9c27b0; color: white; border: none; border-radius: 4px;
                padding: 8px 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: #7b1fa2; }
            QPushButton:pressed { background-color: #6a1b9a; }
            QFrame#sidebar { background-color: #4a148c; border-right: 1px solid #3e1178; }
            QFrame#header { background-color: white; border-bottom: 1px solid #e0e0e0; }
            QFrame#content { background-color: white; border-radius: 8px; border: 1px solid #e0e0e0; }
        """)

    # ---------- Sidebar ----------
    def crear_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMinimumWidth(250)
        self.sidebar.setMaximumWidth(250)

        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(10, 20, 10, 20)
        self.sidebar_layout.setSpacing(5)

        # Logo
        self.logo_label = QLabel()
        logo_pixmap = QPixmap("static/logo.jpg")
        self.logo_label.setPixmap(logo_pixmap.scaled(200, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.sidebar_layout.addWidget(self.logo_label)

        # Usuario
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

        # Contenedor de menús
        self.menu_container = QWidget()
        self.menu_layout = QVBoxLayout(self.menu_container)
        self.menu_layout.setContentsMargins(0, 0, 0, 0)
        self.menu_layout.setSpacing(5)

        # Menú principal
        self.crear_menu_principal()

        self.sidebar_layout.addWidget(self.menu_container)

        # Espaciador
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.sidebar_layout.addWidget(spacer)

        # Logout
        btn_logout = BotonNavegacion("  Cerrar Sesión", "static/icons/log-out.png")
        btn_logout.clicked.connect(self.cerrar_sesion)
        self.sidebar_layout.addWidget(btn_logout)

        # Añadir sidebar
        self.main_layout.addWidget(self.sidebar)

    def _on_click(self, setter, button, action_no_args):
        """Helper para marcar activo y luego ejecutar la acción."""
        def handler():
            setter(button)
            action_no_args()
        return handler

    def _set_active_menu_btn(self, btn):
        if self.active_menu_btn and self.active_menu_btn is not btn:
            self.active_menu_btn.set_active(False)
        self.active_menu_btn = btn
        if btn:
            btn.set_active(True)

    def _set_active_sub_btn(self, btn):
        if self.active_sub_btn and self.active_sub_btn is not btn:
            self.active_sub_btn.set_active(False)
        self.active_sub_btn = btn
        if btn:
            btn.set_active(True)

    def crear_menu_principal(self):
        self.limpiar_layout(self.menu_layout)

        # Inicio
        btn_inicio = BotonNavegacion("  Inicio", "static/icons/home.png")
        btn_inicio.clicked.connect(self._on_click(self._set_active_menu_btn, btn_inicio, self.mostrar_formulario_inicio))
        self.menu_layout.addWidget(btn_inicio)

        # Ventas
        if any(tiene_permiso(self.usuario, p) for p in ["cargar_cliente", "crear_venta"]):
            btn_ventas = BotonNavegacion("  Ventas", "static/icons/shopping-cart.png")
            btn_ventas.clicked.connect(self._on_click(self._set_active_menu_btn, btn_ventas, lambda: self.mostrar_submenu("ventas")))
            self.menu_layout.addWidget(btn_ventas)

        # Consultas
        if tiene_permiso(self.usuario, "ver_ventas"):
            btn_consultas = BotonNavegacion("  Consultas", "static/icons/search.png")
            btn_consultas.clicked.connect(self._on_click(self._set_active_menu_btn, btn_consultas, lambda: self.mostrar_submenu("consultas")))
            self.menu_layout.addWidget(btn_consultas)

        # Productos
        if any(tiene_permiso(self.usuario, p) for p in ["crear_categoria", "crear_producto"]):
            btn_productos = BotonNavegacion("  Productos", "static/icons/package.png")
            btn_productos.clicked.connect(self._on_click(self._set_active_menu_btn, btn_productos, lambda: self.mostrar_submenu("productos")))
            self.menu_layout.addWidget(btn_productos)

        # Personal
        if any(tiene_permiso(self.usuario, p) for p in ["cargar_personal", "asignar_usuario", "asignar_permisos"]):
            btn_personal = BotonNavegacion("  Personal", "static/icons/users.png")
            btn_personal.clicked.connect(self._on_click(self._set_active_menu_btn, btn_personal, lambda: self.mostrar_submenu("personal")))
            self.menu_layout.addWidget(btn_personal)

        # Tasas (no cambia al submenú)
        btn_tasas = BotonNavegacion("  Configurar Tasas", "static/icons/percent.png")
        btn_tasas.clicked.connect(self._on_click(self._set_active_menu_btn, btn_tasas, self.abrir_dialog_tasas))
        self.menu_layout.addWidget(btn_tasas)

        # Cobros
        btn_cobros = BotonNavegacion("  Cobros", "static/icons/credit-card.png")
        btn_cobros.clicked.connect(self._on_click(self._set_active_menu_btn, btn_cobros, lambda: self.mostrar_submenu("cobros")))
        self.menu_layout.addWidget(btn_cobros)

        self.menu_actual = "principal"
        # Reset subactivo al volver al menú principal
        if self.active_sub_btn:
            self.active_sub_btn.set_active(False)
            self.active_sub_btn = None

    # ---------- Submenús ----------
    def mostrar_submenu(self, modulo):
        self.limpiar_layout(self.menu_layout)

        # Volver al menú principal
        btn_volver = BotonNavegacion("  Volver al menú", "static/icons/arrow-left.png")
        btn_volver.clicked.connect(self.crear_menu_principal)
        self.menu_layout.addWidget(btn_volver)

        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: rgba(255, 255, 255, 0.2); margin: 10px 0;")
        self.menu_layout.addWidget(separator)

        # Título módulo en sidebar
        titulo_modulo = QLabel(f"  Módulo: {modulo.capitalize()}")
        titulo_modulo.setStyleSheet("color: white; font-size: 16px; font-weight: bold; margin: 5px 0;")
        self.menu_layout.addWidget(titulo_modulo)

        # Título superior
        self.titulo_pagina.setText(modulo.capitalize())

        # Reset subactivo al entrar a un submenú nuevo
        if self.active_sub_btn:
            self.active_sub_btn.set_active(False)
            self.active_sub_btn = None

        # Construcción según módulo + vista inicial por defecto
        if modulo == "ventas":
            if tiene_permiso(self.usuario, "cargar_cliente"):
                btn_clientes = BotonNavegacion("  Clientes", "static/icons/users.png")
                btn_clientes.clicked.connect(self._on_click(self._set_active_sub_btn, btn_clientes, self.abrir_form_cliente))
                self.menu_layout.addWidget(btn_clientes)

                btn_garantes = BotonNavegacion("  Garantes", "static/icons/user-check.png")
                btn_garantes.clicked.connect(self._on_click(self._set_active_sub_btn, btn_garantes, self.abrir_form_garante))
                self.menu_layout.addWidget(btn_garantes)

                btn_gestion_clientes = BotonNavegacion("  Listado de Clientes", "static/icons/list.png")
                btn_gestion_clientes.clicked.connect(self._on_click(self._set_active_sub_btn, btn_gestion_clientes, self.abrir_gestion_clientes))
                self.menu_layout.addWidget(btn_gestion_clientes)

                btn_gestion_garantes = BotonNavegacion("  Listado de Garantes", "static/icons/list.png")
                btn_gestion_garantes.clicked.connect(self._on_click(self._set_active_sub_btn, btn_gestion_garantes, self.abrir_gestion_garantes))
                self.menu_layout.addWidget(btn_gestion_garantes)

                btn_listado_ventas = BotonNavegacion("  Listado de Ventas", "static/icons/list.png")
                btn_listado_ventas.clicked.connect(self._on_click(self._set_active_sub_btn, btn_listado_ventas, self.abrir_listado_ventas))
                self.menu_layout.addWidget(btn_listado_ventas)

            if tiene_permiso(self.usuario, "crear_venta"):
                btn_ventas = BotonNavegacion("  Nueva Venta", "static/icons/dollar-sign.png")
                btn_ventas.clicked.connect(self._on_click(self._set_active_sub_btn, btn_ventas, self.abrir_form_venta))
                self.menu_layout.addWidget(btn_ventas)

            # Vista inicial por defecto
            if 'btn_listado_ventas' in locals():
                self._set_active_sub_btn(btn_listado_ventas)
            self.abrir_listado_ventas()

        elif modulo == "consultas":
            btn_consultas = BotonNavegacion("  Consultas Generales", "static/icons/search.png")
            btn_consultas.clicked.connect(self._on_click(self._set_active_sub_btn, btn_consultas, self.abrir_form_consultas))
            self.menu_layout.addWidget(btn_consultas)

            self._set_active_sub_btn(btn_consultas)
            self.abrir_form_consultas()

        elif modulo == "productos":
            if tiene_permiso(self.usuario, "crear_categoria"):
                btn_categorias = BotonNavegacion("  Categorías", "static/icons/tag.png")
                btn_categorias.clicked.connect(self._on_click(self._set_active_sub_btn, btn_categorias, self.abrir_form_categoria))
                self.menu_layout.addWidget(btn_categorias)

            if tiene_permiso(self.usuario, "crear_producto"):
                btn_productos = BotonNavegacion("  Productos", "static/icons/box.png")
                btn_productos.clicked.connect(self._on_click(self._set_active_sub_btn, btn_productos, self.abrir_form_producto))
                self.menu_layout.addWidget(btn_productos)

            btn_listado = BotonNavegacion("  Listado", "static/icons/list.png")
            btn_listado.clicked.connect(self._on_click(self._set_active_sub_btn, btn_listado, self.abrir_listado_productos))
            self.menu_layout.addWidget(btn_listado)

            self._set_active_sub_btn(btn_listado)
            self.abrir_listado_productos()

        elif modulo == "personal":
            if tiene_permiso(self.usuario, "cargar_personal"):
                btn_personal = BotonNavegacion("  Personal", "static/icons/user-plus.png")
                btn_personal.clicked.connect(self._on_click(self._set_active_sub_btn, btn_personal, self.abrir_form_personal))
                self.menu_layout.addWidget(btn_personal)

                btn_gestion_personal = BotonNavegacion("  Listado de Personal", "static/icons/list.png")
                btn_gestion_personal.clicked.connect(self._on_click(self._set_active_sub_btn, btn_gestion_personal, self.abrir_gestion_personal))
                self.menu_layout.addWidget(btn_gestion_personal)

            if tiene_permiso(self.usuario, "asignar_usuario"):
                btn_usuarios = BotonNavegacion("  Usuarios", "static/icons/user.png")
                btn_usuarios.clicked.connect(self._on_click(self._set_active_sub_btn, btn_usuarios, self.abrir_form_usuario))
                self.menu_layout.addWidget(btn_usuarios)

                btn_listado_usuarios = BotonNavegacion("  Listado de Usuarios", "static/icons/list.png")
                btn_listado_usuarios.clicked.connect(self._on_click(self._set_active_sub_btn, btn_listado_usuarios, self.abrir_listado_usuarios))
                self.menu_layout.addWidget(btn_listado_usuarios)

            if tiene_permiso(self.usuario, "asignar_permisos"):
                btn_permisos = BotonNavegacion("  Permisos", "static/icons/shield.png")
                btn_permisos.clicked.connect(self._on_click(self._set_active_sub_btn, btn_permisos, self.abrir_form_permisos))
                self.menu_layout.addWidget(btn_permisos)

            self._set_active_sub_btn(btn_gestion_personal if 'btn_gestion_personal' in locals() else None)
            self.abrir_gestion_personal()

        elif modulo == "cobros":
            btn_gestion_cobros = BotonNavegacion("  Gestión de Cobros", "static/icons/credit-card.png")
            btn_gestion_cobros.clicked.connect(self._on_click(self._set_active_sub_btn, btn_gestion_cobros, self.abrir_form_cobros))
            self.menu_layout.addWidget(btn_gestion_cobros)

            # Portada con botón central (no resalta submenú por defecto)
            portada = QWidget()
            lay = QVBoxLayout(portada)
            lay.setAlignment(Qt.AlignCenter)

            lbl = QLabel("Módulo Cobros")
            lbl.setObjectName("subtitulo")
            lbl.setAlignment(Qt.AlignCenter)
            lay.addWidget(lbl)

            btn_abrir = QPushButton("Abrir Gestión de Cobros")
            btn_abrir.setIcon(QIcon("static/icons/credit-card.png"))
            btn_abrir.setIconSize(QSize(32, 32))
            btn_abrir.setFixedSize(280, 60)
            btn_abrir.setStyleSheet("""
                QPushButton {
                    background-color: #9c27b0;
                    color: white;
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 8px 12px;
                }
                QPushButton:hover { background-color: #7b1fa2; }
                QPushButton:pressed { background-color: #6a1b9a; }
            """)
            btn_abrir.clicked.connect(self.abrir_form_cobros)
            lay.addWidget(btn_abrir)

            self.mostrar_formulario(portada, "Cobros")

        self.menu_actual = modulo

    # ---------- Utilidades ----------
    def limpiar_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

    # ---------- Contenido ----------
    def crear_area_contenido(self):
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # Header fijo
        self.header = QFrame()
        self.header.setObjectName("header")
        self.header.setMinimumHeight(60)
        self.header.setMaximumHeight(60)

        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        self.titulo_pagina = QLabel("Inicio")
        self.titulo_pagina.setObjectName("titulo")
        header_layout.addWidget(self.titulo_pagina)

        self.content_layout.addWidget(self.header)

        # Área central: StackedWidget
        self.content_stack = QStackedWidget()
        self.content_layout.addWidget(self.content_stack, 1)

        self.main_layout.addWidget(self.content_container, 1)

    def _wrap_scroll(self, widget):
        frame = QFrame()
        frame.setObjectName("content")
        v = QVBoxLayout(frame)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(20)
        v.addWidget(widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(frame)
        return scroll

    def mostrar_bienvenida(self):
        welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(welcome_widget)
        welcome_layout.setAlignment(Qt.AlignCenter)

        logo_label = QLabel()
        logo_pixmap = QPixmap("static/logo.jpg")
        logo_label.setPixmap(logo_pixmap.scaled(300, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(logo_label)

        bienvenida_label = QLabel("Bienvenido al Sistema CREDANZA")
        bienvenida_label.setObjectName("bienvenida")
        bienvenida_label.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(bienvenida_label)

        usuario_label = QLabel(f"{self.usuario.nombre}")
        usuario_label.setObjectName("subtitulo")
        usuario_label.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(usuario_label)

        from datetime import datetime
        fecha_label = QLabel(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")
        fecha_label.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(fecha_label)

        self.mostrar_formulario(welcome_widget, "Inicio")

        if self.menu_actual != "principal":
            self.crear_menu_principal()

    def mostrar_formulario(self, formulario, titulo):
        self.titulo_pagina.setText(titulo)

        contenedor = self._wrap_scroll(formulario)

        old = self.content_stack.currentWidget()

        # Evitar parpadeo durante el swap
        self.content_stack.setUpdatesEnabled(False)
        self.content_stack.addWidget(contenedor)
        self.content_stack.setCurrentWidget(contenedor)
        if old and old is not contenedor:
            self.content_stack.removeWidget(old)
            old.deleteLater()
        self.content_stack.setUpdatesEnabled(True)


    # ---------- Abrir formularios ----------
    def abrir_form_cliente(self):
        self.mostrar_formulario(FormCliente(), "Gestión de Clientes")

    def abrir_form_garante(self):
        self.mostrar_formulario(FormGarante(), "Gestión de Garantes")

    def abrir_form_venta(self):
        formulario = FormVenta(usuario_actual=self.usuario)
        formulario.sale_saved.connect(self.abrir_listado_ventas)
        self.mostrar_formulario(formulario, "Gestión de Ventas")

    def abrir_form_categoria(self):
        # Abrir como QDialog modal (NO usar mostrar_formulario acá)
        dlg = FormCategoria(parent=self)
        print("DEBUG: Abriendo FormCategoria (menú Productos > Categorías)")
        result = dlg.exec()
        print(f"DEBUG: Cerró FormCategoria. result={result} | flag={dlg.create_new_product_flag} | cat_id={dlg.newly_created_category_id}")

        if result == QDialog.Accepted and dlg.create_new_product_flag and dlg.newly_created_category_id:
            # Si el usuario eligió "+Producto", abrir FormProducto con la categoría preseleccionada
            cat_id = dlg.newly_created_category_id
            print(f"DEBUG: Abrir FormProducto con categoría preseleccionada (cat_id={cat_id})")
            prod = FormProducto(parent=self)
            # Asegurar combo cargado y preseleccionar
            prod.cargar_categorias()
            idx = prod.categoria_combo.findData(cat_id)
            if idx >= 0:
                prod.categoria_combo.setCurrentIndex(idx)
            else:
                QMessageBox.warning(self, "Aviso", "No encontré la categoría recién creada en el combo.")
            prod.exec()

        # Al cerrar (haya o no producto), refrescá la vista de listado del panel central
        self.abrir_listado_productos()

    def abrir_form_producto(self):
        # También como QDialog modal para ser consistente
        print("DEBUG: Abriendo FormProducto (menú Productos > Productos)")
        dlg = FormProducto(parent=self)
        dlg.exec()
        # Tras cerrar, refrescar el listado del panel central
        self.abrir_listado_productos()


    def abrir_form_personal(self):
        self.mostrar_formulario(FormPersonal(), "Gestión de Personal")

    def abrir_form_usuario(self):
        self.mostrar_formulario(FormUsuario(), "Gestión de Usuarios")

    def abrir_form_permisos(self):
        self.mostrar_formulario(FormPermisos(), "Gestión de Permisos")

    def abrir_form_consultas(self):
        self.mostrar_formulario(FormConsultas(), "Consultas Generales")

    def abrir_gestion_clientes(self):
        from PySide6.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.mostrar_formulario(FormGestionClientes(), "Gestión de Clientes")
        finally:
            QApplication.restoreOverrideCursor()


    def abrir_gestion_garantes(self):
        self.mostrar_formulario(FormGestionGarantes(), "Gestión de Garantes")

    def abrir_listado_ventas(self):
        from PySide6.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.mostrar_formulario(FormVentas(usuario_actual=self.usuario), "Listado de Ventas")
        finally:
            QApplication.restoreOverrideCursor()


    def abrir_form_cobros(self):
        self.form_cobros = FormCobro(usuario_actual=self.usuario) 
        self.form_cobros.setWindowModality(Qt.ApplicationModal)
        self.form_cobros.setAttribute(Qt.WA_DeleteOnClose)
        self.form_cobros.showMaximized()

    # ---------- Diálogos y sesión ----------
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

    # ---------- Listados y otros ----------
    def abrir_listado_productos(self):
        from PySide6.QtWidgets import QApplication  
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.mostrar_formulario(FormListadoProductos(), "Listado de Categorías y Productos")
        finally:
            QApplication.restoreOverrideCursor()

    def abrir_gestion_personal(self):
        self.mostrar_formulario(FormGestionPersonal(), "Listado de Personal")

    def abrir_listado_usuarios(self):
        self.mostrar_formulario(FormListadoUsuarios(), "Listado de Usuarios")

    # ---------- Inicio ----------
    def mostrar_formulario_inicio(self):
        # Marca Inicio activo en menú y vuelve a bienvenida
        self.mostrar_bienvenida()
