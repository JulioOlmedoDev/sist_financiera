"""
Servicio de clientes: primer recurso de negocio de la API.

Establece el patrón CRUD que se replicará en garantes, personal, productos, etc.

PENDIENTE (próxima sesión): integrar el sistema de permisos granulares
(require_perm_or_close de la desktop) como dependencia de FastAPI, una vez
definido el mapeo código de permiso → endpoint. Por ahora los endpoints exigen
sesión autenticada.
"""

from typing import Optional, Tuple, List

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from database import get_session
from models import Cliente


class DocumentoDuplicado(Exception):
    """Ya existe un cliente con ese tipo y número de documento
    (viola uq_clientes_tipo_nro)."""


class ClienteConVentas(Exception):
    """El cliente tiene ventas asociadas y no puede eliminarse."""


def _a_dict(cliente: Cliente) -> dict:
    """Extrae los datos a un dict plano antes de cerrar la sesión
    (evita DetachedInstanceError con sesiones por operación)."""
    return {
        "id": cliente.id,
        "apellidos": cliente.apellidos,
        "nombres": cliente.nombres,
        "tipo_documento": cliente.tipo_documento,
        "nro_documento": cliente.nro_documento,
        "fecha_nacimiento": cliente.fecha_nacimiento,
        "ocupacion": cliente.ocupacion,
        "domicilio_personal": cliente.domicilio_personal,
        "localidad": cliente.localidad,
        "provincia": cliente.provincia,
        "lugar_trabajo_nombre": cliente.lugar_trabajo_nombre,
        "domicilio_laboral": cliente.domicilio_laboral,
        "sexo": cliente.sexo,
        "estado_civil": cliente.estado_civil,
        "celular_personal": cliente.celular_personal,
        "celular_trabajo": cliente.celular_trabajo,
        "email": cliente.email,
        "calificacion": cliente.calificacion,
        "descripcion": cliente.descripcion,
    }


def listar(
    buscar: Optional[str], pagina: int, tamanio: int
) -> Tuple[List[dict], int]:
    """Listado paginado con búsqueda por apellidos, nombres o nro de documento."""
    with get_session() as session:
        query = session.query(Cliente)
        if buscar:
            patron = "%{}%".format(buscar.strip())
            query = query.filter(
                or_(
                    Cliente.apellidos.like(patron),
                    Cliente.nombres.like(patron),
                    Cliente.nro_documento.like(patron),
                )
            )
        total = query.count()
        filas = (
            query.order_by(Cliente.apellidos, Cliente.nombres)
            .offset((pagina - 1) * tamanio)
            .limit(tamanio)
            .all()
        )
        return [_a_dict(c) for c in filas], total


def obtener(cliente_id: int) -> Optional[dict]:
    with get_session() as session:
        cliente = session.get(Cliente, cliente_id)
        return _a_dict(cliente) if cliente else None


def crear(datos: dict) -> dict:
    with get_session() as session:
        cliente = Cliente(**datos)
        session.add(cliente)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise DocumentoDuplicado() from exc
        return _a_dict(cliente)


def actualizar(cliente_id: int, datos: dict) -> Optional[dict]:
    """Actualización parcial: aplica solo los campos presentes en `datos`."""
    with get_session() as session:
        cliente = session.get(Cliente, cliente_id)
        if cliente is None:
            return None
        for campo, valor in datos.items():
            setattr(cliente, campo, valor)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise DocumentoDuplicado() from exc
        return _a_dict(cliente)


def eliminar(cliente_id: int) -> bool:
    """Devuelve False si el cliente no existe. Lanza ClienteConVentas si
    tiene ventas asociadas (protección de integridad del negocio)."""
    with get_session() as session:
        cliente = session.get(Cliente, cliente_id)
        if cliente is None:
            return False
        session.delete(cliente)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise ClienteConVentas() from exc
        return True
