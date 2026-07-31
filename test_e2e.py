"""Prueba end-to-end de la API CREDANZA — Fase 2, sesiones 1 y 2.

Corre contra el models.py REAL y un database.py idéntico al real
salvo la URL (SQLite en vez de MySQL).
"""

import hashlib
import os
from datetime import datetime, timedelta

os.environ["API_SECRET_KEY"] = "clave-de-prueba-solo-para-tests"

import pyotp
from fastapi.testclient import TestClient

from database import Session as SessionLocal, engine
from models import Base, Usuario, Cliente, Venta, set_setting
from utils.security import hash_password
from api.main import app

client = TestClient(app)
FALLOS = []


def check(nombre, condicion, detalle=""):
    marca = "PASS" if condicion else "FAIL"
    print(f"[{marca}] {nombre} {detalle}")
    if not condicion:
        FALLOS.append(nombre)


def login(u, p):
    return client.post("/auth/login", json={"usuario": u, "password": p})


def auth(t):
    return {"Authorization": f"Bearer {t}"}


# --- Seed ---
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
SECRET_TOTP = pyotp.random_base32()
s = SessionLocal()
s.add_all([
    Usuario(id=1, nombre="normal", email="n@c.com", password=hash_password("clave12345X"),
            activo=True, last_password_change=datetime.now()),
    Usuario(id=2, nombre="legacy", email="l@c.com",
            password=hashlib.sha256("vieja456789".encode()).hexdigest(), activo=True),
    Usuario(id=3, nombre="con2fa", email="f@c.com", password=hash_password("clave12345X"),
            activo=True, last_password_change=datetime.now(),
            totp_enabled=True, totp_secret=SECRET_TOTP),
    Usuario(id=4, nombre="vencido", email="v@c.com", password=hash_password("clave12345X"),
            activo=True, last_password_change=datetime.now() - timedelta(days=90)),
    Usuario(id=5, nombre="inactivo", email="i@c.com", password=hash_password("clave12345X"),
            activo=False, last_password_change=datetime.now()),
    Usuario(id=6, nombre="sinsetup", email="p@c.com", password=hash_password("clave12345X"),
            activo=True, last_password_change=datetime.now(), require_2fa=True),
    Usuario(id=7, nombre="admin2fa", email="a@c.com", password=hash_password("clave12345X"),
            activo=True, last_password_change=datetime.now(),
            totp_enabled=True, totp_secret=pyotp.random_base32(), totp_set_by_admin=True),
])
set_setting(s, "require_2fa_global", "0")
s.close()

# ============ BLOQUE 1: regresión sesión 1 ============
r = client.get("/health")
check("health", r.status_code == 200)

r = login("normal", "clave12345X")
check("login ok", r.status_code == 200 and r.json()["status"] == "ok")
TOKEN_NORMAL = r.json()["access_token"]
r = client.get("/auth/me", headers=auth(TOKEN_NORMAL))
check("/me con token", r.status_code == 200 and r.json()["nombre"] == "normal")
check("/me sin token → 401", client.get("/auth/me").status_code == 401)

r1 = login("normal", "mala")
r2 = login("noexiste", "mala")
check("password mala → 401 genérico", r1.status_code == 401)
check("usuario inexistente → mismo mensaje", r2.json() == r1.json())
check("inactivo → 401 genérico", login("inactivo", "clave12345X").json() == r1.json())

for _ in range(3):
    login("normal", "mala")
r = login("normal", "mala")
check("5to intento → 423 bloqueado", r.status_code == 423)
check("bloqueado con clave correcta", login("normal", "clave12345X").status_code == 423)
s = SessionLocal(); u = s.get(Usuario, 1); u.lock_until = None; s.commit(); s.close()

r = login("legacy", "vieja456789")
check("login legacy ok", r.status_code == 200 and r.json()["status"] == "ok")
s = SessionLocal(); u = s.get(Usuario, 2)
check("hash migrado a Argon2", u.password.startswith("$argon2")); s.close()

# ============ BLOQUE 2: cambio de contraseña ============
# 2a. Clave vencida → temp_token pwchange
r = login("vencido", "clave12345X")
j = r.json()
check("vencida → password_change_required", j.get("status") == "password_change_required")
check("vencida → viene temp_token", bool(j.get("temp_token")))
check("vencida → sin access_token", "access_token" not in j)
TEMP_PW = j["temp_token"]

# temp_token pwchange NO sirve como sesión
check("temp pwchange rechazado en /me",
      client.get("/auth/me", headers=auth(TEMP_PW)).status_code == 401)

# 2b. Validaciones (réplica de ChangePasswordDialog)
r = client.post("/auth/change-password", json={"new_password": "corta1"}, headers=auth(TEMP_PW))
check("clave <10 chars → 400", r.status_code == 400)
r = client.post("/auth/change-password", json={"new_password": "xxVENCIDOxx99"}, headers=auth(TEMP_PW))
check("clave contiene nombre → 400", r.status_code == 400, r.json().get("detail", ""))

# 2c. Cambio válido con temp_token
r = client.post("/auth/change-password", json={"new_password": "NuevaClaveSegura1"}, headers=auth(TEMP_PW))
check("cambio con temp_token → ok", r.status_code == 200 and r.json()["status"] == "ok")
check("clave vieja ya no sirve", login("vencido", "clave12345X").status_code == 401)
r = login("vencido", "NuevaClaveSegura1")
check("clave nueva → login ok", r.status_code == 200 and r.json()["status"] == "ok")
s = SessionLocal(); u = s.get(Usuario, 4)
check("must_change_password=False y attempts=0",
      u.must_change_password is False and u.failed_attempts == 0
      and u.last_password_change > datetime.utcnow() - timedelta(minutes=5))
s.close()

# 2d. Cambio con token de sesión (flujo Mi Perfil)
r = client.post("/auth/change-password", json={"new_password": "OtraClaveValida22"}, headers=auth(TOKEN_NORMAL))
check("cambio con sesión → ok", r.status_code == 200)
check("login con clave nueva (perfil)", login("normal", "OtraClaveValida22").json().get("status") == "ok")

# 2e. Sin token → 401
check("cambio sin token → 401",
      client.post("/auth/change-password", json={"new_password": "LoQueSea12345"}).status_code == 401)

# ============ BLOQUE 3: setup de 2FA ============
# 3a. Política exige 2FA sin configurar → temp_token de setup
r = login("sinsetup", "clave12345X")
j = r.json()
check("require_2fa sin setup → 2fa_setup_required", j.get("status") == "2fa_setup_required")
check("setup_required → viene temp_token", bool(j.get("temp_token")))
TEMP_SETUP = j["temp_token"]
check("temp setup rechazado en /me",
      client.get("/auth/me", headers=auth(TEMP_SETUP)).status_code == 401)

# 3b. init con temp_token
r = client.post("/auth/2fa/setup/init", headers=auth(TEMP_SETUP))
j = r.json()
check("setup/init → 200 con secret+uri+token",
      r.status_code == 200 and all(k in j for k in ("secret", "otpauth_uri", "setup_token")))
check("uri con issuer CREDANZA", "CREDANZA" in j.get("otpauth_uri", ""))
check("init NO persiste el secret aún",
      (lambda: (lambda u: u.totp_enabled is False and u.totp_secret is None)(
          SessionLocal().get(Usuario, 6)))())
SECRET_NUEVO, SETUP_TOKEN = j["secret"], j["setup_token"]

# 3c. confirm con código malo → 401 y sigue sin persistir
r = client.post("/auth/2fa/setup/confirm",
                json={"setup_token": SETUP_TOKEN, "code": "000000"}, headers=auth(TEMP_SETUP))
check("confirm código malo → 401", r.status_code == 401)

# 3d. confirm con código válido → activa
codigo = pyotp.TOTP(SECRET_NUEVO, digits=6, interval=30).now()
r = client.post("/auth/2fa/setup/confirm",
                json={"setup_token": SETUP_TOKEN, "code": codigo}, headers=auth(TEMP_SETUP))
check("confirm código ok → 2FA activado", r.status_code == 200)
s = SessionLocal(); u = s.get(Usuario, 6)
check("secret persistido y enabled=True",
      u.totp_enabled is True and u.totp_secret == SECRET_NUEVO
      and u.totp_set_by_admin is False)
s.close()

# 3e. Próximo login → flujo 2FA de dos pasos completo
r = login("sinsetup", "clave12345X")
j = r.json()
check("post-setup → login pide 2fa_required", j.get("status") == "2fa_required")
codigo = pyotp.TOTP(SECRET_NUEVO, digits=6, interval=30).now()
r = client.post("/auth/verify-2fa", json={"temp_token": j["temp_token"], "code": codigo})
check("verify-2fa post-setup → token sesión", r.status_code == 200 and "access_token" in r.json())

# 3f. Setup desde el perfil (con sesión) — reconfiguración de con2fa
r = login("con2fa", "clave12345X")
codigo = pyotp.TOTP(SECRET_TOTP, digits=6, interval=30).now()
r = client.post("/auth/verify-2fa", json={"temp_token": r.json()["temp_token"], "code": codigo})
TOKEN_CON2FA = r.json()["access_token"]
r = client.post("/auth/2fa/setup/init", headers=auth(TOKEN_CON2FA))
check("init con sesión → ya_activo=True", r.status_code == 200 and r.json()["ya_activo"] is True)
s = SessionLocal(); u = s.get(Usuario, 3)
check("reconfigurar NO pisa el secret vigente", u.totp_secret == SECRET_TOTP); s.close()

# ============ BLOQUE 4: desactivar 2FA ============
# 4a. Autoservicio → puede
r = client.post("/auth/2fa/disable", headers=auth(TOKEN_CON2FA))
check("disable autoservicio → ok", r.status_code == 200)
s = SessionLocal(); u = s.get(Usuario, 3)
check("disable limpia secret y flag", u.totp_enabled is False and u.totp_secret is None); s.close()

# 4b. Impuesto por admin → 403
r = login("admin2fa", "clave12345X")
s = SessionLocal(); sec = s.get(Usuario, 7).totp_secret; s.close()
codigo = pyotp.TOTP(sec, digits=6, interval=30).now()
r = client.post("/auth/verify-2fa", json={"temp_token": r.json()["temp_token"], "code": codigo})
TOKEN_ADMIN2FA = r.json()["access_token"]
r = client.post("/auth/2fa/disable", headers=auth(TOKEN_ADMIN2FA))
check("disable con totp_set_by_admin → 403", r.status_code == 403)

# ============ BLOQUE 5: CRUD clientes ============
H = auth(TOKEN_ADMIN2FA)

check("clientes sin token → 401 o 403",
      client.get("/clientes").status_code in (401, 403))

r = client.post("/clientes", headers=H, json={
    "apellidos": "García", "nombres": "María",
    "tipo_documento": "DNI", "nro_documento": "30111222",
    "localidad": "Río Cuarto", "provincia": "Córdoba",
    "fecha_nacimiento": "1985-04-12",
})
check("crear cliente → 201", r.status_code == 201, str(r.json())[:60])
CID = r.json()["id"]

r = client.post("/clientes", headers=H, json={
    "apellidos": "Otro", "nombres": "Distinto",
    "tipo_documento": "DNI", "nro_documento": "30111222",
})
check("documento duplicado → 409", r.status_code == 409)

r = client.get(f"/clientes/{CID}", headers=H)
check("obtener cliente", r.status_code == 200 and r.json()["apellidos"] == "García")
check("cliente inexistente → 404", client.get("/clientes/99999", headers=H).status_code == 404)

client.post("/clientes", headers=H, json={"apellidos": "Pérez", "nombres": "Juan",
                                          "tipo_documento": "DNI", "nro_documento": "28555666"})
r = client.get("/clientes", headers=H, params={"buscar": "Garc"})
check("búsqueda por apellido", r.status_code == 200 and r.json()["total"] == 1
      and r.json()["items"][0]["nro_documento"] == "30111222")
r = client.get("/clientes", headers=H)
check("listado total=2 paginado", r.json()["total"] == 2 and len(r.json()["items"]) == 2)

r = client.put(f"/clientes/{CID}", headers=H, json={"celular_personal": "358-4001122"})
check("update parcial", r.status_code == 200 and r.json()["celular_personal"] == "358-4001122"
      and r.json()["apellidos"] == "García")

# Cliente con venta asociada → no se puede borrar
s = SessionLocal()
s.add(Venta(cliente_id=CID, fecha=datetime.now().date(), monto=100000, num_cuotas=12))
s.commit(); VID = s.query(Venta).first().id; s.close()
r = client.delete(f"/clientes/{CID}", headers=H)
check("delete con ventas → 409", r.status_code == 409, r.json().get("detail", "")[:50])
s = SessionLocal(); s.query(Venta).delete(); s.commit(); s.close()
r = client.delete(f"/clientes/{CID}", headers=H)
check("delete sin ventas → 204", r.status_code == 204)
check("delete inexistente → 404", client.delete("/clientes/99999", headers=H).status_code == 404)

print()
print("RESULTADO:", "TODO OK ({} checks)".format(
    len([1 for _ in range(1)]) if FALLOS else 0) if FALLOS else "TODO OK")
print("RESULTADO FINAL:", "TODO OK" if not FALLOS else f"FALLARON: {FALLOS}")
raise SystemExit(1 if FALLOS else 0)
