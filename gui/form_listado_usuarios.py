from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QScrollArea, QSizePolicy, QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt
from database import get_session
from models import Usuario, Personal, Rol
from gui.form_usuario import FormUsuario
from utils.dialogos import confirmar
from utils.estilos import PALETA
from utils.guards import require_perm_or_close

class FormListadoUsuarios(QWidget):
    def __init__(self, parent=None, usuario=None):
        super().__init__(parent)
        self.usuario = usuario
        # --- GUARDIA DE ACCESO ---
        if not require_perm_or_close(
            self, self.usuario, "0340", "listado de usuarios",
            msg="No tenés permisos para acceder a la gestión de usuarios."
        ):
            return

        rol = getattr(self.usuario, "rol", None)
        nombre_rol = getattr(rol, "nombre", "").lower() if rol else ""

        # Misma regla que en FormUsuario
        permisos_autorizados = ["owner", "administrador", "gerente"]

        if nombre_rol not in permisos_autorizados:
            QMessageBox.warning(self, "Acceso denegado",
                                "No tenés permisos para acceder a la gestión de usuarios.")
            self.close()
            return

        self.setWindowTitle("Listado de Usuarios")

        self.setStyleSheet("""
            QWidget {
                background-color: #fdfdfd;
                font-size: 14px;
            }
            QLabel {
                font-weight: bold;
                font-size: 18px;
                color: #333;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #ccc;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
        """)

        self.setContentsMargins(20, 20, 20, 20)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        contenido = QWidget()
        scroll.setWidget(contenido)

        layout = QVBoxLayout(contenido)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        titulo = QLabel("Listado de Usuarios")
        titulo.setStyleSheet("color: #6a1b9a;")
        layout.addWidget(titulo)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(6)
        self.tabla.setHorizontalHeaderLabels(["ID", "Nombre", "Email", "Rol", "Personal", "Activo"])
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SingleSelection)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.itemSelectionChanged.connect(self.actualizar_estado_boton)
        layout.addWidget(self.tabla)

        botones = QHBoxLayout()
        botones.addStretch()
        i = PALETA["identidad"]

        self.btn_editar = QPushButton("Editar")
        self.btn_editar.setStyleSheet(f"""
            QPushButton {{ background-color: {i['primario']}; color: white; }}
            QPushButton:hover {{ background-color: {i['primario_hover']}; }}
        """)

        self.btn_estado = QPushButton("Activar/Desactivar")
        self.btn_estado.setStyleSheet(f"""
            QPushButton {{ background-color: {i['primario']}; color: white; }}
            QPushButton:hover {{ background-color: {i['primario_hover']}; }}
        """)

        self.btn_editar.clicked.connect(self.editar_usuario)
        self.btn_estado.clicked.connect(self.cambiar_estado_usuario)

        botones.addWidget(self.btn_editar)
        botones.addWidget(self.btn_estado)

        layout.addLayout(botones)

        principal = QVBoxLayout(self)
        principal.addWidget(scroll)

        self.cargar_datos()
        self.actualizar_estado_boton()

    def cargar_datos(self):
        self.tabla.setRowCount(0)
        with get_session() as session:
            usuarios = session.query(Usuario).all()

            for i, u in enumerate(usuarios):
                self.tabla.insertRow(i)
                self.tabla.setItem(i, 0, QTableWidgetItem(str(u.id)))
                self.tabla.setItem(i, 1, QTableWidgetItem(u.nombre or ""))
                self.tabla.setItem(i, 2, QTableWidgetItem(u.email or ""))

                # Rol
                rol_nombre = ""
                if getattr(u, "rol_id", None):
                    r = session.query(Rol).get(u.rol_id)
                    rol_nombre = r.nombre if r else ""
                self.tabla.setItem(i, 3, QTableWidgetItem(rol_nombre))

                # Personal
                personal = session.query(Personal).get(u.personal_id)
                nombre_personal = f"{personal.apellidos}, {personal.nombres}" if personal else ""
                self.tabla.setItem(i, 4, QTableWidgetItem(nombre_personal))

                # Activo
                estado = "Sí" if u.activo else "No"
                self.tabla.setItem(i, 5, QTableWidgetItem(estado))

    def usuario_seleccionado(self):
        fila = self.tabla.currentRow()
        if fila == -1:
            return None
        return int(self.tabla.item(fila, 0).text())

    def editar_usuario(self):
        usuario_id = self.usuario_seleccionado()
        if not usuario_id:
            QMessageBox.warning(self, "Selección requerida", "Seleccioná un usuario de la lista.")
            return
        with get_session() as session:
            u = session.query(Usuario).get(usuario_id)
            personal_id = u.personal_id if u else None
        self.abrir_form_usuario(personal_id)

    def cambiar_estado_usuario(self):
        usuario_id = self.usuario_seleccionado()
        if not usuario_id:
            QMessageBox.warning(self, "Selección requerida", "Seleccioná un usuario de la lista.")
            return

        from models import Rol as RolModel

        try:
            with get_session() as session:
                usuario = session.query(Usuario).get(usuario_id)
                if not usuario:
                    return
                activo = usuario.activo
                rol_nombre = usuario.rol.nombre if usuario.rol else ""
                nombre_usuario = usuario.nombre or "(sin nombre)"

                if activo and rol_nombre == "Administrador":
                    admins_activos = session.query(Usuario).join(RolModel).filter(
                        RolModel.nombre == "Administrador",
                        Usuario.activo == True
                    ).count()
                    if admins_activos <= 1:
                        QMessageBox.warning(
                            self,
                            "Acción no permitida",
                            "No se puede desactivar al único administrador activo del sistema."
                        )
                        return

            if activo:
                ok = confirmar(self, "Desactivar", f"¿Desactivar al usuario «{nombre_usuario}»?")
            else:
                ok = confirmar(self, "Reactivar", f"¿Reactivar al usuario «{nombre_usuario}»?")

            if not ok:
                return

            with get_session() as session:
                usuario = session.query(Usuario).get(usuario_id)
                if usuario:
                    usuario.activo = not activo
                    session.commit()
            if activo:
                QMessageBox.information(self, "Listo",
                                        f"El usuario «{nombre_usuario}» fue desactivado.")
            else:
                QMessageBox.information(self, "Listo",
                                        f"El usuario «{nombre_usuario}» fue reactivado.")
        except Exception as e:
            print(f"[ERROR cambiar_estado_usuario] {e}")
            QMessageBox.critical(self, "Error",
                                 "No se pudo cambiar el estado del usuario. Intentá nuevamente.")

        self.cargar_datos()
        self.actualizar_estado_boton()

    def actualizar_estado_boton(self):
        fila = self.tabla.currentRow()
        if fila == -1:
            self.btn_estado.setText("Activar/Desactivar")
            return
        item = self.tabla.item(fila, 5)
        if item and item.text() == "Sí":
            self.btn_estado.setText("Desactivar")
        else:
            self.btn_estado.setText("Reactivar")

    def abrir_form_usuario(self, personal_id=None):
        self.form = FormUsuario(usuario=self.usuario)
        if personal_id:
            index = self.form.personal_combo.findData(personal_id)
            if index != -1:
                self.form.personal_combo.setCurrentIndex(index)
        self.form.usuario_guardado.connect(self.cargar_datos)
        self.form.showMaximized()


