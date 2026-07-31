# CREDANZA API — Fase 2 (CODER 4)

Backend FastAPI que se interpone entre la app de escritorio y MySQL.
La desktop app no se toca: la API corre en paralelo.

## Ejecución (desde la raíz del repo)

```bash
uvicorn api.main:app --reload
```

Documentación interactiva: http://127.0.0.1:8000/docs

## Requisitos en .env

```
API_SECRET_KEY=<generar con: python -c "import secrets; print(secrets.token_hex(32))">
```

Opcionales: `API_ACCESS_TOKEN_MINUTES` (480), `API_PREAUTH_TOKEN_MINUTES` (5),
`API_SETUP_2FA_TOKEN_MINUTES` (10).

## Endpoints

### Autenticación

| Endpoint | Auth | Descripción |
|---|---|---|
| POST /auth/login | — | Login por nombre de usuario. Réplica exacta de la desktop: bloqueo a los 5 intentos (15 min), migración legacy SHA-256→Argon2, expiración 60 días, política 2FA global/por usuario. |
| POST /auth/verify-2fa | temp_token 2fa | Segundo paso: código TOTP de 6 dígitos (valid_window=1). |
| POST /auth/change-password | sesión o temp_token pwchange | Reglas de ChangePasswordDialog: mínimo 10 caracteres, no puede contener el nombre de usuario. Resetea must_change_password, intentos y bloqueo. |
| POST /auth/2fa/setup/init | sesión o temp_token setup | Genera secret + otpauth_uri (issuer CREDANZA). Nada se persiste: el secret viaja firmado en setup_token. |
| POST /auth/2fa/setup/confirm | sesión o temp_token setup | Verifica el código contra el secret pendiente y recién ahí activa el 2FA. |
| POST /auth/2fa/disable | sesión | Desactiva 2FA de autoservicio. 403 si fue impuesto por admin (totp_set_by_admin). |
| GET /auth/me | sesión | Datos del usuario autenticado. |

### Estados del login (campo `status` con HTTP 200)

- `ok` → viene access_token (8 hs).
- `password_change_required` → viene temp_token (5 min) para /auth/change-password; luego re-login.
- `2fa_setup_required` → viene temp_token (5 min) para /auth/2fa/setup/*; luego re-login.
- `2fa_required` → viene temp_token (5 min) para /auth/verify-2fa.

Errores: 401 credenciales inválidas (mensaje genérico), 423 cuenta bloqueada.

### Clientes (patrón CRUD de referencia)

Todos exigen sesión autenticada.

| Endpoint | Descripción |
|---|---|
| GET /clientes?buscar=&pagina=1&tamanio=50 | Listado paginado; busca en apellidos, nombres y nro_documento. |
| GET /clientes/{id} | Detalle (404 si no existe). |
| POST /clientes | Alta (409 si tipo+nro de documento duplicado). |
| PUT /clientes/{id} | Actualización parcial: solo aplica los campos enviados. |
| DELETE /clientes/{id} | Baja (409 si tiene ventas asociadas, 404 si no existe). |

PENDIENTE: mapear el sistema de permisos granulares (códigos de guards.py)
a los endpoints como dependencia de FastAPI.

## Diseño de tokens (JWT, HS256)

Scopes: `session` (acceso), `preauth:2fa`, `preauth:pwchange`, `preauth:2fa_setup`
(intermedios de login, 5 min, solo sirven para su endpoint), `2fa_setup_pending`
(transporta el secret TOTP firmado entre init y confirm, 10 min).

## Verificación

52 checks end-to-end en verde contra el models.py real y un database.py
idéntico al real (SQLite): regresión completa de sesión 1 + cambio de
contraseña (validaciones, temp_token, sesión), setup 2FA (no-persistencia
hasta código válido, issuer, reconfiguración segura), disable (autoservicio
ok / impuesto por admin 403) y CRUD de clientes (duplicados, búsqueda,
paginación, integridad con ventas).

## Notas

- La confirmación por doble entrada de contraseña es responsabilidad del
  cliente (UI); la API valida las reglas de fondo.
- Fidelidad desktop: last_password_change se escribe con utcnow() (como
  ChangePasswordDialog) aunque el login compara con now() local — desfase
  de horas, irrelevante para el umbral de 60 días. Pendiente de unificar.
- Los endpoints de gestión por admin (imponer 2FA, recuperar acceso,
  ABM de usuarios) quedan para una sesión posterior.
