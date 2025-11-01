from PySide6.QtWidgets import (
    QMainWindow, QLabel, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QFrame, QScrollArea, QSizePolicy,
    QStackedWidget, QMessageBox, QDialog, QMenu, QToolButton, QWidgetAction
)
from PySide6.QtGui import QPixmap, QIcon, QKeySequence, QShortcut
from PySide6.QtCore import Qt, QSize
from PySide6.QtCore import QTimer, QEvent
from PySide6.QtWidgets import QApplication

from gui.form_cliente import FormCliente
from gui.form_venta import FormVenta
from gui.form_categoria import FormCategoria
from gui.form_producto import FormProducto
from gui.form_personal import FormPersonal
from gui.form_garante import FormGarante
from gui.form_usuario import FormUsuario
from gui.form_permisos import FormPermisos
from utils.permisos import tiene_permiso, tiene_permiso_match
from gui.form_consultas import FormConsultas
from gui.form_gestion_clientes import FormGestionClientes
from gui.form_gestion_garantes import FormGestionGarantes
from gui.form_listado_ventas import FormVentas
from gui.form_cobro import FormCobro
from gui.dialog_tasas import DialogTasas
from gui.form_listado_productos import FormListadoProductos
from gui.form_gestion_personal import FormGestionPersonal
from gui.form_listado_usuarios import FormListadoUsuarios
from gui.form_mi_perfil import FormMiPerfil
from gui.change_password_dialog import ChangePasswordDialog
from gui.recovery_dialog import RecoveryDialog
from gui.lock_screen import LockScreenDialog
from models import Personal
from zoneinfo import ZoneInfo


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
            QApplication.quit()
            return
        self.usuario = usuario  # Usuario logueado
        print("DEBUG Rol:", getattr(getattr(self.usuario, "rol", None), "nombre", None))
        print("DEBUG Permisos:", [p.nombre for p in (self.usuario.permisos or [])])

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

        self._sc_lock = QShortcut(QKeySequence("Ctrl+L"), self)
        self._sc_lock.activated.connect(self.bloquear_pantalla)

        # ---- Auto-logout por inactividad (mover acá) ----
        self._idle_minutes = 10
        self._idle_ms = int(self._idle_minutes * 60 * 1000)
        self._idle_timer = QTimer(self)
        self._idle_prompt_open = False
        self._idle_timer.setSingleShot(True)  # single-shot y lo rearmamos en cada interacción
        self._idle_timer.timeout.connect(self._on_idle_timeout)
        self._idle_timer.start(self._idle_ms)

        # filtro global (toda la app), no solo la ventana
        QApplication.instance().installEventFilter(self)

        # Atajo Ctrl+L para bloquear pantalla
        self._lock_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        self._lock_shortcut.activated.connect(self.bloquear_pantalla)

    def _circle_avatar(self, path: str, size: int = 24) -> QIcon:
        pm = QPixmap(path)
        if pm.isNull():
            pm = QPixmap(size, size)
            pm.fill(Qt.lightGray)
        pm = pm.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

        from PySide6.QtGui import QPainter, QPainterPath
        circ = QPixmap(size, size); circ.fill(Qt.transparent)
        p = QPainter(circ); p.setRenderHint(QPainter.Antialiasing, True)
        path_circle = QPainterPath(); path_circle.addEllipse(0, 0, size, size)
        p.setClipPath(path_circle); p.drawPixmap(0, 0, pm); p.end()
        return QIcon(circ)

    # ---------- Estilos ----------
    def aplicar_estilo(self):
        base = """
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
        """

        # Estilo del botón de perfil (QToolButton en forma de "pill") y del QMenu
        perfil = """
            /* Pastilla de perfil (QToolButton) */
            QToolButton {
                padding: 8px 14px;
                border: 1px solid #d9c6ef;
                border-radius: 20px;      /* pill */
                background: #ffffff;
                color: #4a148c;
                font-weight: 700;
                font-size: 15px;
            }
            QToolButton:hover { background: #f7f2ff; }
            QToolButton:pressed { background: #efe6ff; }

            /* Botón Bloquear (morado sólido, como antes) */
            QPushButton#btnBloquear {
                background-color: #9c27b0;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-weight: 700;
                padding: 6px 12px;
            }
            QPushButton#btnBloquear:hover { background-color: #7b1fa2; }
            QPushButton#btnBloquear:pressed { background-color: #6a1b9a; }

            /* Menú PRO (más grande y pulido) */
            QMenu {
                background: #ffffff;
                border: 1px solid #e4e4e7;
                border-radius: 12px;
                padding: 10px;               /* más aire interno */
                min-width: 260px;            /* ancho mínimo más cómodo */
            }
            QMenu::separator {
                height: 1px;
                background: #eeeeee;
                margin: 8px 10px;            /* separadores con más respiro */
            }
            
            /* ÚNICO indicador del menú en la pastilla de perfil */
            QToolButton::menu-indicator {
                subcontrol-origin: padding;
                subcontrol-position: right center;   /* flecha a la derecha */
                width: 12px;
                height: 12px;
                padding-left: 8px;                   /* respiro entre icono y flecha */
            }            
        """
        perfil += """
            /* Tarjeta superior del menú de perfil */
            #menuUserCard {
                border-radius: 10px;
                padding: 10px 12px;
                background: #fafafa;
                margin: 4px 4px 8px 4px;
            }
            #menuUserName {
                font-weight: 700;
                font-size: 15px;
                color: #2b2b2b;
            }
            #menuUserMeta {
                font-size: 12px;
                color: #7c7c7c;
            }
        """
        perfil += """
            /* Encabezado de grupo (CUENTA / SEGURIDAD) en formato chip */
            #menuGroupHeader {
                padding: 6px 10px;
                margin: 4px 8px 6px 8px;
                font-weight: 800;
                font-size: 12px;
                letter-spacing: 0.7px;
                color: #6b21a8;                /* violeta más oscuro */
                background: #faf5ff;           /* fondo muy suave */
                border-left: 3px solid #9c27b0;/* acento a la izquierda */
                border-radius: 6px;
            }

            /* Acciones con look de botón fantasma */
            QMenu::item {
                padding: 10px 12px;
                margin: 4px 6px;
                border: 1px solid #ede7f6;     /* borde suave */
                border-radius: 10px;
                font-weight: 600;
                font-size: 15px;
                color: #424242;
                background: #ffffff;           /* base blanco */
            }
            QMenu::item:selected {
                background: #f3e8ff;           /* hover violeta suave */
                border-color: #d6c3ff;         /* borde un poco más marcado */
                color: #4a148c;
            }
            QMenu::item:pressed {
                background: #efe6ff;
            }
        """

        self.setStyleSheet(base + perfil)

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
        if (
            tiene_permiso_match(self.usuario, "cargar_cliente", "0010")   # (crear) clientes
            or tiene_permiso_match(self.usuario, "crear_venta", "0060")   # (crear) nueva venta
        ):
            btn_ventas = BotonNavegacion("  Ventas", "static/icons/shopping-cart.png")
            btn_ventas.clicked.connect(self._on_click(self._set_active_menu_btn, btn_ventas, lambda: self.mostrar_submenu("ventas")))
            self.menu_layout.addWidget(btn_ventas)

        # Consultas
        if tiene_permiso_match(self.usuario, "consultas", "0100", "ver_ventas"):
            btn_consultas = BotonNavegacion("  Consultas", "static/icons/search.png")
            btn_consultas.clicked.connect(self._on_click(self._set_active_menu_btn, btn_consultas, lambda: self.mostrar_submenu("consultas")))
            self.menu_layout.addWidget(btn_consultas)

        # Productos
        if (
            tiene_permiso_match(self.usuario, "crear_categoria", "0200")
            or tiene_permiso_match(self.usuario, "crear_producto", "0210")
        ):
            btn_productos = BotonNavegacion("  Productos", "static/icons/package.png")
            btn_productos.clicked.connect(self._on_click(self._set_active_menu_btn, btn_productos, lambda: self.mostrar_submenu("productos")))
            self.menu_layout.addWidget(btn_productos)

        # Personal
        if (
            tiene_permiso_match(self.usuario, "0310", "cargar_personal")
            or tiene_permiso_match(self.usuario, "0330", "0340", "asignar_usuario", "listado_usuarios")
            or tiene_permiso_match(self.usuario, "0360", "asignar_permisos")
            or tiene_permiso_match(self.usuario, "0300", "mi perfil")   # <-- habilita el módulo con Mi perfil
        ):
            btn_personal = BotonNavegacion("  Personal", "static/icons/users.png")
            btn_personal.clicked.connect(self._on_click(self._set_active_menu_btn, btn_personal, lambda: self.mostrar_submenu("personal")))
            self.menu_layout.addWidget(btn_personal)

        # Tasas (no cambia al submenú)
        if tiene_permiso_match(self.usuario, "configurar_tasas", "0400"):
            btn_tasas = BotonNavegacion("  Configurar Tasas", "static/icons/percent.png")
            btn_tasas.clicked.connect(self._on_click(self._set_active_menu_btn, btn_tasas, self.abrir_dialog_tasas))
            self.menu_layout.addWidget(btn_tasas)


        # Cobros
        if tiene_permiso_match(self.usuario, "cobros", "0500", "gestion cobros"):
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
            # Clientes
            if tiene_permiso_match(self.usuario, "0010", "cargar_cliente"):
                btn_clientes = BotonNavegacion("  Clientes", "static/icons/users.png")
                btn_clientes.clicked.connect(self._on_click(self._set_active_sub_btn, btn_clientes, self.abrir_form_cliente))
                self.menu_layout.addWidget(btn_clientes)

            # Garantes
            if tiene_permiso_match(self.usuario, "0020", "cargar_garante"):
                btn_garantes = BotonNavegacion("  Garantes", "static/icons/user-check.png")
                btn_garantes.clicked.connect(self._on_click(self._set_active_sub_btn, btn_garantes, self.abrir_form_garante))
                self.menu_layout.addWidget(btn_garantes)

            # Listados
            if tiene_permiso_match(self.usuario, "0030", "listado_clientes"):
                btn_gestion_clientes = BotonNavegacion("  Listado de Clientes", "static/icons/list.png")
                btn_gestion_clientes.clicked.connect(self._on_click(self._set_active_sub_btn, btn_gestion_clientes, self.abrir_gestion_clientes))
                self.menu_layout.addWidget(btn_gestion_clientes)

            if tiene_permiso_match(self.usuario, "0040", "listado_garantes"):
                btn_gestion_garantes = BotonNavegacion("  Listado de Garantes", "static/icons/list.png")
                btn_gestion_garantes.clicked.connect(self._on_click(self._set_active_sub_btn, btn_gestion_garantes, self.abrir_gestion_garantes))
                self.menu_layout.addWidget(btn_gestion_garantes)

            if tiene_permiso_match(self.usuario, "0050", "listado_ventas", "ver_ventas"):
                btn_listado_ventas = BotonNavegacion("  Listado de Ventas", "static/icons/list.png")
                btn_listado_ventas.clicked.connect(self._on_click(self._set_active_sub_btn, btn_listado_ventas, self.abrir_listado_ventas))
                self.menu_layout.addWidget(btn_listado_ventas)

            # Nueva venta
            if tiene_permiso_match(self.usuario, "0060", "crear_venta"):
                btn_ventas = BotonNavegacion("  Nueva Venta", "static/icons/dollar-sign.png")
                btn_ventas.clicked.connect(self._on_click(self._set_active_sub_btn, btn_ventas, self.abrir_form_venta))
                self.menu_layout.addWidget(btn_ventas)

            # Vista inicial por defecto (si tiene listado)
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
            if tiene_permiso_match(self.usuario, "crear_categoria", "0200"):
                btn_categorias = BotonNavegacion("  Categorías", "static/icons/tag.png")
                btn_categorias.clicked.connect(self._on_click(self._set_active_sub_btn, btn_categorias, self.abrir_form_categoria))
                self.menu_layout.addWidget(btn_categorias)

            if tiene_permiso_match(self.usuario, "crear_producto", "0210"):
                btn_productos = BotonNavegacion("  Productos", "static/icons/box.png")
                btn_productos.clicked.connect(self._on_click(self._set_active_sub_btn, btn_productos, self.abrir_form_producto))
                self.menu_layout.addWidget(btn_productos)

            btn_listado = BotonNavegacion("  Listado", "static/icons/list.png")
            btn_listado.clicked.connect(self._on_click(self._set_active_sub_btn, btn_listado, self.abrir_listado_productos))
            self.menu_layout.addWidget(btn_listado)

            self._set_active_sub_btn(btn_listado)
            self.abrir_listado_productos()

        elif modulo == "personal":
            btn_mi_perfil = BotonNavegacion("  Mi perfil", "static/icons/user-circle.png")
            btn_mi_perfil.clicked.connect(self._on_click(self._set_active_sub_btn, btn_mi_perfil, self.abrir_mi_perfil))
            self.menu_layout.addWidget(btn_mi_perfil)

            if tiene_permiso_match(self.usuario, "cargar_personal", "0310"):
                btn_personal = BotonNavegacion("  Personal", "static/icons/user-plus.png")
                btn_personal.clicked.connect(self._on_click(self._set_active_sub_btn, btn_personal, self.abrir_form_personal))
                self.menu_layout.addWidget(btn_personal)

                btn_gestion_personal = BotonNavegacion("  Listado de Personal", "static/icons/list.png")
                btn_gestion_personal.clicked.connect(self._on_click(self._set_active_sub_btn, btn_gestion_personal, self.abrir_gestion_personal))
                self.menu_layout.addWidget(btn_gestion_personal)

            if tiene_permiso_match(self.usuario, "asignar_usuario", "0330", "0340"):
                btn_usuarios = BotonNavegacion("  Usuarios", "static/icons/user.png")
                btn_usuarios.clicked.connect(self._on_click(self._set_active_sub_btn, btn_usuarios, self.abrir_form_usuario))
                self.menu_layout.addWidget(btn_usuarios)

                btn_listado_usuarios = BotonNavegacion("  Listado de Usuarios", "static/icons/list.png")
                btn_listado_usuarios.clicked.connect(self._on_click(self._set_active_sub_btn, btn_listado_usuarios, self.abrir_listado_usuarios))
                self.menu_layout.addWidget(btn_listado_usuarios)

                btn_recovery = BotonNavegacion("  Recuperar acceso", "static/icons/shield.png")
                btn_recovery.clicked.connect(self._on_click(self._set_active_sub_btn, btn_recovery, self.abrir_recuperar_acceso))
                self.menu_layout.addWidget(btn_recovery)

            if tiene_permiso(self.usuario, "asignar_permisos"):
                btn_permisos = BotonNavegacion("  Permisos", "static/icons/shield.png")
                btn_permisos.clicked.connect(self._on_click(self._set_active_sub_btn, btn_permisos, self.abrir_form_permisos))
                self.menu_layout.addWidget(btn_permisos)

            self._set_active_sub_btn(btn_gestion_personal if 'btn_gestion_personal' in locals() else None)
            self.abrir_gestion_personal()

        elif modulo == "cobros":
            if tiene_permiso_match(self.usuario, "0500", "cobros", "gestion cobros"):
                btn_gestion_cobros = BotonNavegacion("  Gestión de Cobros", "static/icons/credit-card.png")
                btn_gestion_cobros.clicked.connect(self._on_click(self._set_active_sub_btn, btn_gestion_cobros, self.abrir_form_cobros))
                self.menu_layout.addWidget(btn_gestion_cobros)

                # Portada con botón central
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

                # 👈 mover acá adentro
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

        # Espaciador para empujar los botones a la derecha
        header_layout.addStretch()

        # --- Botón Bloquear pantalla ---
        self.btn_bloquear = QPushButton("Bloquear pantalla")
        self.btn_bloquear.setFixedHeight(32)
        self.btn_bloquear.setToolTip("Bloquear pantalla (Ctrl+L)")
        self.btn_bloquear.clicked.connect(self.bloquear_pantalla)
        self.btn_bloquear.setObjectName("btnBloquear")
        header_layout.addWidget(self.btn_bloquear)

        # --- Badge de Usuario con menú (avatar + nombre) ---
        self.btn_user = QToolButton(self.header)
        self.btn_user.setPopupMode(QToolButton.InstantPopup)
        self.btn_user.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.btn_user.setAutoRaise(True)  # look minimalista
        self.btn_user.setFixedHeight(36)
        self.btn_user.setCursor(Qt.PointingHandCursor)
        self.btn_user.setLayoutDirection(Qt.RightToLeft)

        self._refresh_user_badge()          # texto + icono
        self.btn_user.setMenu(self._build_profile_menu())  # menú inicial
        header_layout.addWidget(self.btn_user)


        # --- Botón Cambiar contraseña ---
        #self.btn_cambiar_pass = QPushButton("Cambiar contraseña")
        #self.btn_cambiar_pass.setFixedHeight(32)
        #self.btn_cambiar_pass.clicked.connect(self.abrir_cambiar_contrasena)
        #header_layout.addWidget(self.btn_cambiar_pass)

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
        # Mostrar último acceso ANTERIOR (no el actual)
        ultimo = "—"
        try:
            dt_prev = getattr(self.usuario, "previous_login_at", None)
            if dt_prev:
                if dt_prev.tzinfo is None:  # guardado en UTC naive
                    dt_prev = dt_prev.replace(tzinfo=ZoneInfo("UTC"))
                dt_local = dt_prev.astimezone(ZoneInfo("America/Argentina/Cordoba"))
                ultimo = dt_local.strftime('%d/%m/%Y %H:%M')
            else:
                ultimo = "Primera vez"
        except Exception:
            pass

        ultimo_login_label = QLabel(f"Último acceso: {ultimo}")
        ultimo_login_label.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(ultimo_login_label)

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

    def abrir_mi_perfil(self):
        self.mostrar_formulario(FormMiPerfil(self.usuario), "Mi perfil")


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

    def abrir_cambiar_contrasena(self):
        dlg = ChangePasswordDialog(self, self.usuario)
        dlg.exec()

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

    def abrir_recuperar_acceso(self):
        dlg = RecoveryDialog(self, self.usuario)
        dlg.exec()

    # ---------- Inicio ----------
    def mostrar_formulario_inicio(self):
        # Marca Inicio activo en menú y vuelve a bienvenida
        self.mostrar_bienvenida()

    def _reset_idle_timer(self):
        t = getattr(self, "_idle_timer", None)
        # No rearmar mientras el diálogo de inactividad está abierto
        if t and not getattr(self, "_idle_prompt_open", False):
            t.start(self._idle_ms)

    def eventFilter(self, obj, event):
        # Si hay diálogo abierto, no rearmes el timer con eventos de usuario
        if getattr(self, "_idle_prompt_open", False):
            return super().eventFilter(obj, event)

        if event.type() in (
            QEvent.MouseMove, QEvent.MouseButtonPress, QEvent.MouseButtonRelease,
            QEvent.KeyPress, QEvent.KeyRelease, QEvent.Wheel,
            QEvent.TouchBegin, QEvent.TouchUpdate, QEvent.TouchEnd,
            QEvent.FocusIn, QEvent.WindowActivate
        ):
            self._reset_idle_timer()
        return super().eventFilter(obj, event)

    def _on_idle_timeout(self):
        # Evitar abrir múltiples diálogos
        if getattr(self, "_idle_prompt_open", False):
            return
        self._idle_prompt_open = True
        try:
            # Detener el timer mientras mostramos el diálogo
            t = getattr(self, "_idle_timer", None)
            if t:
                t.stop()

            resp = QMessageBox.question(
                self,
                "Sesión inactiva",
                f"Pasaron más de {self._idle_minutes} minutos sin actividad.\n¿Querés continuar la sesión?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if resp == QMessageBox.Yes:
                self._reset_idle_timer()  # única rearmada
            else:
                QApplication.quit()
        finally:
            self._idle_prompt_open = False

    def bloquear_pantalla(self):
        # Pausar temporizador de inactividad mientras está bloqueado
        try:
            if hasattr(self, "_idle_timer"):
                self._idle_timer.stop()
            # Evitar que quede un prompt de inactividad pendiente
            if hasattr(self, "_idle_prompt_open"):
                self._idle_prompt_open = False

            dlg = LockScreenDialog(self, self.usuario)
            dlg.exec()  # modal; vuelve cuando desbloquea o cierra sesión
        finally:
            # Si no cerró la app, rearmar el timer
            if hasattr(self, "_idle_timer"):
                self._idle_timer.start(self._idle_ms)

    def abrir_configurar_2fa(self):
        from gui.two_factor_setup import TwoFactorSetupDialog
        dlg = TwoFactorSetupDialog(self, self.usuario)
        if dlg.exec() == QDialog.Accepted:
            # al activarse 2FA, actualizamos menú y badge
            self.btn_user.setMenu(self._build_profile_menu())
            self._refresh_user_badge()

    def _build_profile_menu(self) -> QMenu:
        """Arma el menú del badge de usuario según el estado (2FA on/off)."""
        menu = QMenu(self)

        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 6)
        menu.setGraphicsEffect(shadow)

        # Tarjeta superior con avatar + nombre
        from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout
        user_card_act = QWidgetAction(menu)

        user_card = QWidget()
        user_card.setObjectName("menuUserCard")
        hl = QHBoxLayout(user_card)
        hl.setContentsMargins(8, 6, 8, 6)
        hl.setSpacing(10)

        # Avatar redondo 36x36
        avatar_lbl = QLabel()
        avatar_icon = self._circle_avatar("static/icon.png", 36)
        avatar_lbl.setPixmap(avatar_icon.pixmap(36, 36))
        avatar_lbl.setFixedSize(36, 36)
        hl.addWidget(avatar_lbl)

        # Nombre + meta
        vl = QVBoxLayout()
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(2)

        name_lbl = QLabel(self._display_user_text())
        name_lbl.setObjectName("menuUserName")
        vl.addWidget(name_lbl)

        # Línea meta (p.ej. “Mi perfil y seguridad”)
        meta_lbl = QLabel("Mi perfil y seguridad")
        meta_lbl.setObjectName("menuUserMeta")
        vl.addWidget(meta_lbl)

        hl.addLayout(vl)
        user_card_act.setDefaultWidget(user_card)
        menu.addAction(user_card_act)

        header1 = QWidgetAction(menu)
        lbl1 = QLabel("CUENTA")
        lbl1.setObjectName("menuGroupHeader")
        header1.setDefaultWidget(lbl1)
        menu.addAction(header1)

        act_mi_perfil = menu.addAction("Mi perfil")
        act_mi_perfil.setIcon(QIcon("static/icons/user-circle.png"))
        act_mi_perfil.triggered.connect(self.abrir_mi_perfil)

        menu.addSeparator()
        header2 = QWidgetAction(menu)
        lbl2 = QLabel("SEGURIDAD")
        lbl2.setObjectName("menuGroupHeader")
        header2.setDefaultWidget(lbl2)
        menu.addAction(header2)

        act_cambiar = menu.addAction("Cambiar contraseña…")
        act_cambiar.setIcon(QIcon("static/icons/lock.png"))
        act_cambiar.triggered.connect(self.abrir_cambiar_contrasena)

        # Alterna según 2FA
        if getattr(self.usuario, "totp_enabled", False):
            act_2fa = menu.addAction("Desactivar ingreso con token")
            act_2fa.setIcon(QIcon("static/icons/shield.png"))
            act_2fa.triggered.connect(self.desactivar_2fa)
        else:
            act_2fa = menu.addAction("Activar ingreso con token")
            act_2fa.setIcon(QIcon("static/icons/shield.png")) 
            act_2fa.triggered.connect(self.abrir_configurar_2fa)

        menu.addSeparator()
        act_lock = menu.addAction("Bloquear pantalla")
        act_lock.setIcon(QIcon("static/icons/lock.png"))  
        act_lock.triggered.connect(self.bloquear_pantalla)

        act_logout = menu.addAction("Cerrar sesión")
        act_logout.setIcon(QIcon("static/icons/log-out.png"))  
        act_logout.triggered.connect(self.cerrar_sesion)
        # spacer inferior para terminar con aire
        bottom_spacer = QWidgetAction(menu)
        _bottom = QWidget(); _bottom.setFixedHeight(6)
        bottom_spacer.setDefaultWidget(_bottom)
        menu.addAction(bottom_spacer)

        return menu
    
    def _display_user_text(self) -> str:
        """
        Muestra: USERNAME - APELLIDO, Nombre (iniciales mayúsculas).
        Usa únicamente la FK usuarios.personal_id (sin heurísticas).
        """
        username = (self.usuario.nombre or "").upper()
        per = getattr(self.usuario, "personal", None)

        if not per and getattr(self.usuario, "personal_id", None):
            try:
                from database import session
                per = session.get(Personal, self.usuario.personal_id)
            except Exception:
                per = None

        if per and (getattr(per, "apellidos", None) or getattr(per, "nombres", None)):
            apellido_upper = (per.apellidos or "").strip().upper()
            nombre_cap = " ".join(p.capitalize() for p in (per.nombres or "").strip().split())
            return f"{username} - {apellido_upper}, {nombre_cap}" if apellido_upper or nombre_cap else username
        else:
            return username

    def _refresh_user_badge(self) -> None:
        """Actualiza texto e icono del QToolButton de usuario."""
        # icono (usa fallback si falta)
        icon_path = "static/icon.png"
        if not QPixmap(icon_path).isNull():
            self.btn_user.setIcon(self._circle_avatar(icon_path, 22))
            self.btn_user.setIconSize(QSize(22, 22))

        self.btn_user.setText(self._display_user_text())
        self.btn_user.setToolTip("Mi perfil y seguridad")

    def desactivar_2fa(self):
        """Apaga el 2FA del usuario actual desde el menú de perfil."""
        from PySide6.QtWidgets import QMessageBox
        from database import session
        ok = QMessageBox.question(
            self, "Desactivar ingreso con token",
            "¿Seguro que querés desactivar el ingreso con token (2FA) para tu cuenta?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if ok != QMessageBox.Yes:
            return
        try:
            self.usuario.totp_enabled = False
            self.usuario.totp_secret = None
            session.commit()
            QMessageBox.information(self, "Listo", "Se desactivó el ingreso con token.")
            self.btn_user.setMenu(self._build_profile_menu())
            self._refresh_user_badge()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo desactivar: {e}")
