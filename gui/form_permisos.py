# gui/form_permisos.py
from PySide6.QtWidgets import (
    QWidget, QLabel, QComboBox, QVBoxLayout, QHBoxLayout,
    QCheckBox, QPushButton, QMessageBox, QScrollArea,
    QSizePolicy, QGroupBox, QGridLayout
)
from PySide6.QtCore import Qt
from collections import defaultdict, OrderedDict
from database import session
from models import Usuario, Permiso, Rol
from utils.permisos import es_admin, contar_admins_activos

# ====== Mapa de módulos -> lista de acciones (códigos + texto) ======
# Usamos exactamente tu taxonomía/códigos para que se vea 1:1 en UI.
MODULOS = OrderedDict({
    "0000 Módulo Ventas": [
        "0010 (crear) clientes",
        "0020 (crear) garantes",
        "0030 (ver/editar) listado de clientes",
        "0040 (ver/editar) listado de garantes",
        "0050 (ver) listado de ventas",
        "0051 a) Detalle de venta",
        "0052 b) Editar venta",
        "0053 c) Abrir documentos",
        "0054 d) Registrar cobros desde venta",
        "0060 (crear) nueva venta",
    ],
    "0001 Módulo Consultas": [
        "0100 Consultas: selector general",
        "0101 a) ventas por fecha",
        "0102 b) ventas por cliente",
        "0103 c) ventas por producto",
        "0104 d) ventas por calificación de cliente",
        "0105 e) ventas por personal",
        "0106 f) ventas anuladas",
        "0107 g) cobros por fecha",
    ],
    "0002 Módulo Productos": [
        "0200 (crear) categorías",
        "0210 (crear) productos",
        "0220 (ver/editar) listado categorías y productos",
    ],
    "0003 Módulo Personal": [
        "0300 (ver) mi perfil",
        "0310 (crear) personal",
        "0320 (ver/editar) listado de personal",
        "0330 (crear) usuario",
        "0340 (ver/editar) listado de usuarios",
        "0350 Recuperar acceso (blanqueo contraseña)",
        "0360 (otorgar) permisos",
    ],
    "0004 Módulo Configurar tasas": [
        "0400 Configurar tasas",
    ],
    "0005 Módulo Cobros": [
        "0500 Gestión de cobros",
    ],
})

# ====== Plantillas por rol (listas de permisos marcados por defecto) ======
# Nota: Las plantillas solo PRE-MARCAN checkboxes. Luego se puede ajustar a mano.
PLANTILLAS = {
    "Desarrollador (owner_root)": sum(MODULOS.values(), []),
    "Soporte (soporte)": sum(MODULOS.values(), []),
    "Gerente (admin total)": sum(MODULOS.values(), []),
    "Coordinador": (
        MODULOS["0000 Módulo Ventas"] +
        MODULOS["0001 Módulo Consultas"] +
        MODULOS["0002 Módulo Productos"] +
        # Personal (sin 0360 por defecto)
        ["0300 (ver) mi perfil", "0310 (crear) personal", "0320 (ver/editar) listado de personal",
         "0330 (crear) usuario", "0340 (ver/editar) listado de usuarios", "0350 Recuperar acceso (blanqueo contraseña)"] +
        MODULOS["0005 Módulo Cobros"]
    ),
    "Administrativo": (
        MODULOS["0000 Módulo Ventas"] +
        MODULOS["0001 Módulo Consultas"] +
        MODULOS["0005 Módulo Cobros"]
    ),
}

class FormPermisos(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestión de Permisos")
        self.setMinimumSize(980, 680)
        self.setStyleSheet(self.estilo_general())
        self.showMaximized()

        self.permisos_checkboxes = {}  # nombre_permiso -> QCheckBox
        self.perm_objs = {}            # nombre_permiso -> Permiso (DB)

        # Scroll principal
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        contenido = QWidget()
        scroll.setWidget(contenido)
        main_layout = QVBoxLayout(contenido)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(16)

        # Fila superior: Usuario + aplicar plantilla
        fila_top = QHBoxLayout()
        lbl_usuario = QLabel("Seleccionar Usuario *")
        lbl_usuario.setStyleSheet("color: #7b1fa2; font-weight: bold;")
        self.usuario_combo = QComboBox()
        self.usuario_combo.setMinimumHeight(30)
        self.usuario_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.usuario_combo.currentIndexChanged.connect(self.cargar_permisos_usuario)

        fila_top.addWidget(lbl_usuario)
        fila_top.addSpacing(14)
        fila_top.addWidget(self.usuario_combo)

        # Plantillas por rol
        lbl_plant = QLabel("Plantilla por rol:")
        lbl_plant.setStyleSheet("color:#555;")
        self.plantilla_combo = QComboBox()
        self.plantilla_combo.addItem("— Seleccionar —")
        for k in PLANTILLAS.keys():
            self.plantilla_combo.addItem(k)
        self.btn_aplicar_plantilla = QPushButton("Aplicar plantilla (pre-marca)")
        self.btn_aplicar_plantilla.clicked.connect(self.aplicar_plantilla)

        fila_top.addSpacing(24)
        fila_top.addWidget(lbl_plant)
        fila_top.addWidget(self.plantilla_combo)
        fila_top.addWidget(self.btn_aplicar_plantilla)

        main_layout.addLayout(fila_top)

        # Botón seleccionar todos / ninguno
        fila_toggle = QHBoxLayout()
        self.btn_todos = QPushButton("Seleccionar todo")
        self.btn_ninguno = QPushButton("Deseleccionar todo")
        self.btn_todos.clicked.connect(lambda: self._toggle_all(True))
        self.btn_ninguno.clicked.connect(lambda: self._toggle_all(False))
        fila_toggle.addStretch()
        fila_toggle.addWidget(self.btn_todos)
        fila_toggle.addWidget(self.btn_ninguno)
        main_layout.addLayout(fila_toggle)

        # Área de permisos (por módulo)
        self.permisos_container = QVBoxLayout()
        self._construir_ui_permisos()
        main_layout.addLayout(self.permisos_container)

        # Botones guardar/cancelar
        botones_layout = QHBoxLayout()
        botones_layout.addStretch()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_guardar = QPushButton("Guardar Permisos")
        self.btn_guardar.clicked.connect(self.guardar_permisos)
        self.btn_cancelar.clicked.connect(self.close)
        botones_layout.addWidget(self.btn_cancelar)
        botones_layout.addWidget(self.btn_guardar)
        main_layout.addLayout(botones_layout)

        # Layout final
        layout_principal = QVBoxLayout(self)
        layout_principal.addWidget(scroll)

        # Carga inicial
        self.cargar_usuarios()
        self._cargar_perm_objs()
        self.cargar_permisos_usuario()

    def estilo_general(self):
        return """
            QWidget {
                font-size: 14px;
                background-color: #f7f7fb;
            }
            QLabel {
                font-weight: bold;
            }
            QComboBox {
                padding: 6px;
                border: 1px solid #ccc;
                border-radius: 6px;
                background-color: #fff;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 16px;
                padding: 10px 12px;
                background: #ffffff;
            }
            QPushButton {
                background-color: #9c27b0;
                color: white;
                padding: 10px 18px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7b1fa2;
            }
        """

    # ----- Construcción visual por módulos -----
    def _construir_ui_permisos(self):
        # Limpia container si se re-construyera
        while self.permisos_container.count():
            item = self.permisos_container.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        self.permisos_checkboxes.clear()

        for modulo, acciones in MODULOS.items():
            box = QGroupBox(modulo)
            grid = QGridLayout()
            grid.setHorizontalSpacing(16)
            grid.setVerticalSpacing(6)

            for i, nombre_perm in enumerate(acciones):
                cb = QCheckBox(nombre_perm)
                row, col = divmod(i, 2)
                grid.addWidget(cb, row, col)
                self.permisos_checkboxes[nombre_perm] = cb

            box.setLayout(grid)
            self.permisos_container.addWidget(box)

    def _cargar_perm_objs(self):
        """
        Carga a memoria un dict nombre_permiso -> Permiso(DB) para resolver IDs al guardar.
        """
        self.perm_objs.clear()
        todos = session.query(Permiso).all()
        mapa = {p.nombre: p for p in todos}
        self.perm_objs.update(mapa)

    def cargar_usuarios(self):
        self.usuario_combo.clear()
        usuarios = session.query(Usuario).all()
        for u in usuarios:
            self.usuario_combo.addItem(u.nombre, userData=u.id)

    def cargar_permisos_usuario(self):
        usuario_id = self.usuario_combo.currentData()
        usuario = session.query(Usuario).get(usuario_id)
        if not usuario:
            return

        # Desmarcar todo
        for cb in self.permisos_checkboxes.values():
            cb.setChecked(False)

        # Marcar lo que tenga en DB
        nombres_usuario = {p.nombre for p in usuario.permisos}
        for nombre, cb in self.permisos_checkboxes.items():
            if nombre in nombres_usuario:
                cb.setChecked(True)

    def _toggle_all(self, check: bool):
        for cb in self.permisos_checkboxes.values():
            cb.setChecked(check)

    def aplicar_plantilla(self):
        nombre = self.plantilla_combo.currentText()
        if not nombre or nombre == "— Seleccionar —":
            return
        lista = PLANTILLAS.get(nombre, [])
        if not lista:
            return

        # Pre-marcar según plantilla
        # (no desmarca lo demás si quisieras sumar manualmente fuera de la plantilla)
        for perm_name in lista:
            cb = self.permisos_checkboxes.get(perm_name)
            if cb:
                cb.setChecked(True)

        QMessageBox.information(self, "Plantilla aplicada",
                                f"Se pre-marcaron permisos según la plantilla: {nombre}.\nLuego podés ajustar manualmente.")

    def guardar_permisos(self):
        usuario_id = self.usuario_combo.currentData()
        usuario = session.query(Usuario).get(usuario_id)
        if not usuario:
            QMessageBox.warning(self, "Error", "Usuario no válido.")
            return

        # Invariante: no dejar al sistema sin admin
        era_admin = es_admin(usuario)
        total_admins_activos = contar_admins_activos(session)

        # Determinar si tras guardar seguirá siendo admin (por rol)
        tiene_rol_admin = (getattr(usuario, "rol", None)
                           and getattr(usuario.rol, "nombre", "") == "Administrador")

        # Por permisos: si entre los seleccionados hay alguno que consideres "admin total",
        # podrías mapearlo a un nombre específico. En esta versión, el "admin total"
        # lo representamos por el rol (Gerente/Administrador). Si querés un permiso
        # "admin_total" además, agregalo y chequealo acá.
        seguira_siendo_admin = tiene_rol_admin  # (o incluir un permiso "admin_total")

        if era_admin and total_admins_activos == 1 and not seguira_siendo_admin:
            QMessageBox.warning(
                self,
                "No permitido",
                "No podés quitar privilegios de administrador al último administrador activo.\n"
                "Designá a otro administrador y volvé a intentar."
            )
            return

        # Actualizar permisos del usuario con lo tildado
        usuario.permisos.clear()
        for nombre, cb in self.permisos_checkboxes.items():
            if cb.isChecked():
                p = self.perm_objs.get(nombre)
                if p:
                    usuario.permisos.append(p)

        session.commit()
        QMessageBox.information(self, "Éxito", "Permisos actualizados correctamente.")
        self.close()
