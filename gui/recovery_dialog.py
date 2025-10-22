# gui/recovery_dialog.py
from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication

from database import session
from models import Usuario
from utils.account_recovery import resetear_password_usuario


class RecoveryDialog(QDialog):
    """
    Diálogo para que un administrador:
    - Genere una clave temporal para un usuario.
    - (Opcional) Desactive 2FA del usuario.
    Muestra la clave temporal y la copia al portapapeles.
    """
    def __init__(self, parent, usuario_obj: Usuario):
        super().__init__(parent)
        self.setWindowTitle("Recuperar acceso de usuario")
        self.setMinimumWidth(520)

        # Guardamos el usuario objetivo (instancia SQLAlchemy)
        # Pista: pasalo desde tu listado de usuarios (fila seleccionada).
        self.usuario = usuario_obj

        # UI
        lay = QVBoxLayout(self)

        lbl_intro = QLabel(
            f"<b>Usuario objetivo:</b> {self.usuario.nombre} &lt;{self.usuario.email}&gt;<br>"
            "Este proceso generará una <b>contraseña temporal</b> y (si marcás la opción) "
            "<b>desactivará el token 2FA</b> para que pueda volver a ingresar."
        )
        lbl_intro.setWordWrap(True)
        lay.addWidget(lbl_intro)

        self.chk_disable_2fa = QCheckBox("Desactivar ingreso con token (2FA) para este usuario")
        lay.addWidget(self.chk_disable_2fa)

        # Botones
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_ok = QPushButton("Generar clave temporal")
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_ok)
        lay.addLayout(btn_row)

        # Resultado
        self.out_label = QLabel("")
        self.out_label.setWordWrap(True)
        self.out_label.setTextFormat(Qt.RichText)
        self.out_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.out_label.hide()
        lay.addWidget(self.out_label)

        # Conexiones
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self._do_recover)

        # Foco
        QTimer.singleShot(0, self._post_init_focus)

    def _post_init_focus(self):
        self.btn_ok.setFocus()

    def _do_recover(self):
        # Confirmación
        extra = " y se desactivará 2FA" if self.chk_disable_2fa.isChecked() else ""
        resp = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Deseás generar una contraseña temporal para <b>{self.usuario.nombre}</b>{extra}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if resp != QMessageBox.Yes:
            return

        try:
            # Refrescamos por seguridad (otra sesión podría haber modificado el registro)
            try:
                session.refresh(self.usuario)
            except Exception:
                pass

            temp = resetear_password_usuario(
                session=session,
                usuario=self.usuario,
                desactivar_2fa=self.chk_disable_2fa.isChecked()
            )

            # Mostrar resultado y copiar al portapapeles
            self.out_label.setText(
                "<b>Listo.</b><br>"
                f"Contraseña temporal de <b>{self.usuario.nombre}</b>: "
                f"<tt style='font-size:14px'>{temp}</tt><br>"
                "<i>(Se copió al portapapeles. Pedile que la cambie en el primer ingreso.)</i>"
            )
            self.out_label.show()

            QGuiApplication.clipboard().setText(temp)

            # Cambiar botón principal a “Cerrar”
            self.btn_ok.setText("Cerrar")
            self.btn_ok.clicked.disconnect()
            self.btn_ok.clicked.connect(self.accept)

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Ocurrió un problema al recuperar el acceso:\n{e}"
            )
