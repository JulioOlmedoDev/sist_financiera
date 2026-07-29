# CREDANZA API — Fase 2, Sesión 1 (CODER 4)

Esqueleto FastAPI + autenticación completa. La desktop app **no se toca**: la API corre en paralelo.

## Estructura (colocar dentro de `sist_financiera/`)

```
api/
├── __init__.py
├── main.py                  # App FastAPI + /health
├── config.py                # Lectura de .env, validación fail-fast
├── tokens.py                # JWT (PyJWT): scopes session / preauth:2fa
├── schemas.py               # Contratos Pydantic
├── deps.py                  # get_current_user (Bearer)
├── routers/
│   └── auth.py              # POST /auth/login, POST /auth/verify-2fa, GET /auth/me
└── services/
    └── auth_service.py      # Lógica de login (réplica exacta de login_form.py)
```

Reusa `models.py`, `database.py` y `utils/security.py` de la raíz — cero duplicación.

## Instalación

1. Agregar a `requirements.txt`:
   ```
   fastapi==0.116.1
   uvicorn[standard]==0.35.0
   pyjwt==2.10.1
   ```
   (o las versiones que resuelva pip; PyJWT en lugar de python-jose por mantenimiento activo y sin CVEs abiertos)

2. `pip install fastapi "uvicorn[standard]" pyjwt`

3. Agregar al `.env`:
   ```
   API_SECRET_KEY=<generar con: python -c "import secrets; print(secrets.token_hex(32))">
   ```

## Ejecución (desde la raíz del repo, importante para los imports)

```bash
uvicorn api.main:app --reload
```

Documentación interactiva automática: http://127.0.0.1:8000/docs

## Prueba rápida con curl

```bash
# Login simple
curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario": "TU_USUARIO", "password": "TU_CLAVE"}'

# Si devolvió status "2fa_required", segundo paso:
curl -s -X POST http://127.0.0.1:8000/auth/verify-2fa \
  -H "Content-Type: application/json" \
  -d '{"temp_token": "<temp_token>", "code": "123456"}'

# Endpoint protegido
curl -s http://127.0.0.1:8000/auth/me \
  -H "Authorization: Bearer <access_token>"
```

## Contrato de /auth/login

| Resultado | HTTP | Cuerpo |
|---|---|---|
| Credenciales malas / usuario inactivo | 401 | detail genérico (no revela cuál falló) |
| Cuenta bloqueada | 423 | detail con minutos restantes |
| Cambio de contraseña obligatorio/vencida | 200 | `status: password_change_required` (sin token) |
| 2FA exigido pero no configurado | 200 | `status: 2fa_setup_required` (sin token) |
| Falta código TOTP | 200 | `status: 2fa_required` + `temp_token` (5 min) |
| Login completo | 200 | `status: ok` + `access_token` (8 hs) |

## Verificación realizada (entorno Claude, stubs fieles al spec + SQLite)

24 checks end-to-end en verde: login ok + /me, mensaje genérico idéntico para
password mala / usuario inexistente / inactivo, bloqueo exacto al 5to intento
(incluso con clave correcta), migración legacy SHA-256→Argon2 con re-login,
contraseña vencida sin token, flujo 2FA de dos pasos, temp_token rechazado en
/me, código TOTP malo rechazado, require_2fa por usuario y global (SystemSetting).

`test_e2e.py` se incluye como referencia; para correrlo contra tu repo real hay
que adaptar el seed (usa `SessionLocal` del stub de database).

## Supuestos a confirmar con tu código real (revisar antes del primer commit)

1. `get_setting(session, "require_2fa_global", "0")` — confirmar la CLAVE exacta
   que usa la desktop app y el formato del valor (asumí "1"/"true" = activado).
2. Nombres de relaciones `Usuario.permisos/rol/personal` — coinciden con tu spec.
3. Fallos de código 2FA NO incrementan `failed_attempts` (decisión mía; confirmar
   qué hace hoy la desktop app y alinear si difiere).
4. `last_password_change = None` se trata como "no vencida" (no se puede calcular).

## Commits chicos sugeridos

1. `Agregar dependencias FastAPI, uvicorn y PyJWT`
2. `Crear esqueleto de API con configuración y health check`
3. `Implementar emisión y validación de tokens JWT con scopes`
4. `Implementar servicio de login replicando lógica de escritorio`
5. `Agregar endpoints /auth/login, /auth/verify-2fa y /auth/me`

## Próxima sesión (no incluido hoy)

- Endpoint de cambio de contraseña (destraba `password_change_required`)
- Endpoint de configuración de 2FA con QR (destraba `2fa_setup_required`)
- Primer recurso de negocio (ej. clientes) para validar el patrón CRUD
