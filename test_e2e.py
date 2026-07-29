"""Prueba end-to-end del flujo de autenticación de la API CREDANZA."""

import hashlib
import os
from datetime import datetime, timedelta

os.environ["API_SECRET_KEY"] = "clave-de-prueba-solo-para-tests"

import pyotp
from fastapi.testclient import TestClient

from database import SessionLocal, engine
from models import Base, Usuario, set_setting
from utils.security import hash_password
from api.main import app

client = TestClient(app)
FALLOS = []


def check(nombre, condicion, detalle=""):
    marca = "PASS" if condicion else "FAIL"
    print(f"[{marca}] {nombre} {detalle}")
    if not condicion:
        FALLOS.append(nombre)


# --- Seed ---
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
SECRET_TOTP = pyotp.random_base32()
s = SessionLocal()
s.add_all([
    Usuario(id=1, nombre="normal", email="n@c.com", password=hash_password("clave123"),
            activo=True, last_password_change=datetime.now()),
    Usuario(id=2, nombre="legacy", email="l@c.com",
            password=hashlib.sha256("vieja456".encode()).hexdigest(), activo=True),
    Usuario(id=3, nombre="con2fa", email="f@c.com", password=hash_password("clave123"),
            activo=True, last_password_change=datetime.now(),
            totp_enabled=True, totp_secret=SECRET_TOTP),
    Usuario(id=4, nombre="vencido", email="v@c.com", password=hash_password("clave123"),
            activo=True, last_password_change=datetime.now() - timedelta(days=90)),
    Usuario(id=5, nombre="inactivo", email="i@c.com", password=hash_password("clave123"),
            activo=False, last_password_change=datetime.now()),
    Usuario(id=6, nombre="sin2fa_politica", email="p@c.com", password=hash_password("clave123"),
            activo=True, last_password_change=datetime.now(), require_2fa=True),
])
set_setting(s, "require_2fa_global", "0")
s.commit()
s.close()

# --- 1. Health ---
r = client.get("/health")
check("health", r.status_code == 200 and r.json()["status"] == "ok")

# --- 2. Login exitoso simple + /me ---
r = client.post("/auth/login", json={"usuario": "normal", "password": "clave123"})
check("login ok", r.status_code == 200 and r.json()["status"] == "ok", str(r.json())[:80])
token = r.json()["access_token"]
r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
check("/me con token", r.status_code == 200 and r.json()["nombre"] == "normal")

# --- 3. /me sin token y con token basura ---
check("/me sin token → 401", client.get("/auth/me").status_code == 401)
r = client.get("/auth/me", headers={"Authorization": "Bearer basura"})
check("/me token inválido → 401", r.status_code == 401)

# --- 4. Password incorrecta → mensaje genérico; usuario inexistente → mismo mensaje ---
r1 = client.post("/auth/login", json={"usuario": "normal", "password": "mala"})
r2 = client.post("/auth/login", json={"usuario": "noexiste", "password": "mala"})
check("password mala → 401 genérico", r1.status_code == 401)
check("usuario inexistente → mismo mensaje", r2.json() == r1.json())

# --- 5. Usuario inactivo → mismo error genérico ---
r = client.post("/auth/login", json={"usuario": "inactivo", "password": "clave123"})
check("inactivo → 401 genérico", r.status_code == 401 and r.json() == r1.json())

# --- 6. Bloqueo a los 5 intentos (ya hubo 1 fallo del test 4) ---
for _ in range(3):
    client.post("/auth/login", json={"usuario": "normal", "password": "mala"})
r = client.post("/auth/login", json={"usuario": "normal", "password": "mala"})  # 5to
check("5to intento → 423 bloqueado", r.status_code == 423, r.json().get("detail", ""))
r = client.post("/auth/login", json={"usuario": "normal", "password": "clave123"})
check("bloqueado incluso con clave correcta", r.status_code == 423)
# liberar el lock para no ensuciar el resto
s = SessionLocal()
u = s.get(Usuario, 1); u.lock_until = None; s.commit(); s.close()

# --- 7. Migración de hash legacy ---
r = client.post("/auth/login", json={"usuario": "legacy", "password": "vieja456"})
check("login legacy ok", r.status_code == 200 and r.json()["status"] == "ok")
s = SessionLocal()
u = s.query(Usuario).filter_by(nombre="legacy").first()
check("hash migrado a Argon2", u.password.startswith("$argon2"))
check("last_password_change seteado", u.last_password_change is not None)
s.close()
r = client.post("/auth/login", json={"usuario": "legacy", "password": "vieja456"})
check("re-login post-migración ok", r.status_code == 200 and r.json()["status"] == "ok")

# --- 8. Contraseña vencida (>60 días) → sin token ---
r = client.post("/auth/login", json={"usuario": "vencido", "password": "clave123"})
j = r.json()
check("vencida → password_change_required", j.get("status") == "password_change_required")
check("vencida → NO emite token", "access_token" not in j)

# --- 9. 2FA configurado → dos pasos ---
r = client.post("/auth/login", json={"usuario": "con2fa", "password": "clave123"})
j = r.json()
check("2fa → status 2fa_required", j.get("status") == "2fa_required")
check("2fa → NO emite access_token", "access_token" not in j)
temp = j["temp_token"]
# temp_token NO debe servir como token de sesión
r = client.get("/auth/me", headers={"Authorization": f"Bearer {temp}"})
check("temp_token rechazado en /me", r.status_code == 401)
# código incorrecto
r = client.post("/auth/verify-2fa", json={"temp_token": temp, "code": "000000"})
check("código 2FA malo → 401", r.status_code == 401)
# código correcto
codigo = pyotp.TOTP(SECRET_TOTP, digits=6, interval=30).now()
r = client.post("/auth/verify-2fa", json={"temp_token": temp, "code": codigo})
check("código 2FA ok → token de sesión", r.status_code == 200 and "access_token" in r.json())
token2 = r.json()["access_token"]
r = client.get("/auth/me", headers={"Authorization": f"Bearer {token2}"})
check("/me con token post-2FA", r.status_code == 200 and r.json()["nombre"] == "con2fa")

# --- 10. Política exige 2FA pero usuario no lo configuró ---
r = client.post("/auth/login", json={"usuario": "sin2fa_politica", "password": "clave123"})
check("require_2fa sin setup → 2fa_setup_required",
      r.json().get("status") == "2fa_setup_required")

# --- 11. Política GLOBAL de 2FA (SystemSetting) ---
s = SessionLocal(); set_setting(s, "require_2fa_global", "1"); s.commit(); s.close()
r = client.post("/auth/login", json={"usuario": "normal", "password": "clave123"})
check("global 2FA → usuario normal ahora pide setup",
      r.json().get("status") == "2fa_setup_required")
s = SessionLocal(); set_setting(s, "require_2fa_global", "0"); s.commit(); s.close()

print()
print("RESULTADO:", "TODO OK" if not FALLOS else f"FALLARON: {FALLOS}")
raise SystemExit(1 if FALLOS else 0)
