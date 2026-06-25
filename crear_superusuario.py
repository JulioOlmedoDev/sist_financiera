from database import get_session
from models import Usuario, Rol, Personal, Permiso
import hashlib
from datetime import date

with get_session() as session:
    admin_existente = session.query(Usuario).filter_by(nombre="admin").first()
    if admin_existente:
        print("El superusuario ya existe.")
    else:
        personal_admin = Personal(
            apellidos="Administrador",
            nombres="Sistema",
            tipo_documento="DNI",
            nro_documento="00000000",
            fecha_nacimiento=date(2000, 1, 1),
            domicilio_personal="Oficina Central",
            localidad="Ciudad",
            provincia="Provincia",
            sexo="Otro",
            estado_civil="Soltero",
            celular_personal="123456789",
            celular_alternativo="",
            email="admin@sistema.com",
            cuil="20-00000000-0",
            fecha_ingreso=date.today(),
            tipo="Coordinador"
        )
        session.add(personal_admin)
        session.flush()

        rol_admin = session.query(Rol).filter_by(nombre="Administrador").first()
        if not rol_admin:
            rol_admin = Rol(nombre="Administrador")
            session.add(rol_admin)
            session.flush()

        password = "admin123"
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        admin_user = Usuario(
            nombre="admin",
            email="admin@sistema.com",
            password=hashed_password,
            rol_id=rol_admin.id,
            personal_id=personal_admin.id
        )

        session.add(admin_user)
        permiso_admin = session.query(Permiso).filter_by(nombre="admin_total").first()
        if permiso_admin and permiso_admin not in admin_user.permisos:
            admin_user.permisos.append(permiso_admin)
        admin_user.activo = True
        admin_user.must_change_password = True
        session.commit()
        print("✅ Superusuario creado correctamente: usuario = admin | contraseña = admin123")
