from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from PIL import Image, ImageQt
import qrcode, pyotp
from database import session

ISSUER = "CREDANZA"  # lo que verá el usuario en su app de autenticación


class TwoFactorSetupDialog(QDialog):
    def __init__(self, parent, usuario):
        super().__init__(parent)
        self.usuario = usuario
        self.setWindowTitle("Configurar verificación en dos pasos (2FA)")
        self.setMinimumWidth(480)

        # Generamos un secreto NUEVO (solo se guarda si se valida el código)
        self.secret = pyotp.random_base32()
        self.totp = pyotp.TOTP(self.secret, digits=6, interval=30)

        # URI para apps (Google Authenticator, Authy, etc.)
        cuenta = self.usuario.email or self.usuario.nombre
        self.prov_uri = self.totp.provisioning_uri(name=f"{ISSUER}:{cuenta}", issuer_name=ISSUER)

        layout = QVBoxLayout(self)

        info = QLabel(
            "1) Escaneá el QR con Google Authenticator / Authy.\n"
            "2) Ingresá el código de 6 dígitos que ves en la app.\n"
            "3) Guardá para activar el 2FA en tu cuenta."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # QR
        self.qr_label = QLabel(alignment=Qt.AlignCenter)
        layout.addWidget(self.qr_label)
        self._render_qr()

        # Clave manual
        form = QFormLayout()
        self.secret_edit = QLineEdit(self.secret)
        self.secret_edit.setReadOnly(True)
        form.addRow("Clave manual:", self.secret_edit)

        self.code_edit = QLineEdit()
        self.code_edit.setMaxLength(6)
        self.code_edit.setPlaceholderText("Código de 6 dígitos")
        form.addRow("Código:", self.code_edit)
        layout.addLayout(form)

        # Botones
        btns = QHBoxLayout()
        btns.addStretch()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_ok = QPushButton("Activar 2FA")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self._activate)
        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_ok)
        layout.addLayout(btns)

        # Si ya estaba habilitado, avisamos (podría usarse para reconfigurar)
        if getattr(self.usuario, "totp_enabled", False):
            aviso = QLabel("Ya tenés 2FA activo. Si reconfigurás, reemplazará tu clave anterior.")
            aviso.setStyleSheet("color:#7b1fa2;")
            layout.insertWidget(0, aviso)

    def _render_qr(self):
        """
        Genera el QR desde self.prov_uri y lo muestra en self.qr_label.
        """
        # Generar el QR (objeto PIL.Image.Image)
        img = qrcode.make(self.prov_uri)
        # En qrcode 8.x, img puede ser un wrapper -> obtener la PIL real si aplica
        if hasattr(img, "get_image"):
            img = img.get_image()

        # PIL.Image -> QImage -> QPixmap
        qimage = ImageQt.ImageQt(img)
        pixmap = QPixmap.fromImage(qimage)

        # Ajustes del label y colocar el QR
        self.qr_label.setMinimumSize(220, 220)
        self.qr_label.setScaledContents(True)
        self.qr_label.setPixmap(pixmap)

    def _activate(self):
        code = (self.code_edit.text() or "").strip()
        if not code.isdigit() or len(code) != 6:
            QMessageBox.warning(self, "Código inválido", "Ingresá un código de 6 dígitos.")
            return

        # Permitimos una pequeña ventana de tolerancia por desfasaje de reloj
        if not self.totp.verify(code, valid_window=1):
            QMessageBox.critical(self, "Código incorrecto", "El código no es válido. Probá con el código actual.")
            return

        # Guardar en DB (ahora sí)
        self.usuario.totp_secret = self.secret
        self.usuario.totp_enabled = True
        session.commit()

        QMessageBox.information(self, "Listo", "2FA activado correctamente.")
        self.accept()
