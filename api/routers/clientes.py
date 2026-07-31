"""Endpoints CRUD de clientes — patrón de referencia para los demás recursos."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.deps import get_current_user
from api.schemas import (
    ClienteCreate,
    ClienteListResponse,
    ClienteOut,
    ClienteUpdate,
)
from api.services import clientes_service
from api.services.auth_service import UsuarioActual

router = APIRouter(
    prefix="/clientes",
    tags=["clientes"],
    dependencies=[Depends(get_current_user)],  # toda la sección exige sesión
)

MSG_NO_ENCONTRADO = "Cliente no encontrado"
MSG_DOC_DUPLICADO = "Ya existe un cliente con ese tipo y número de documento"


@router.get("", response_model=ClienteListResponse)
def listar_clientes(
    buscar: Optional[str] = Query(
        default=None, description="Busca en apellidos, nombres y nro de documento"
    ),
    pagina: int = Query(default=1, ge=1),
    tamanio: int = Query(default=50, ge=1, le=200),
) -> ClienteListResponse:
    items, total = clientes_service.listar(buscar, pagina, tamanio)
    return ClienteListResponse(items=items, total=total, pagina=pagina, tamanio=tamanio)


@router.get("/{cliente_id}", response_model=ClienteOut)
def obtener_cliente(cliente_id: int) -> ClienteOut:
    cliente = clientes_service.obtener(cliente_id)
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=MSG_NO_ENCONTRADO
        )
    return ClienteOut(**cliente)


@router.post("", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def crear_cliente(datos: ClienteCreate) -> ClienteOut:
    try:
        cliente = clientes_service.crear(datos.model_dump())
    except clientes_service.DocumentoDuplicado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=MSG_DOC_DUPLICADO
        )
    return ClienteOut(**cliente)


@router.put("/{cliente_id}", response_model=ClienteOut)
def actualizar_cliente(cliente_id: int, datos: ClienteUpdate) -> ClienteOut:
    try:
        cliente = clientes_service.actualizar(
            cliente_id, datos.model_dump(exclude_unset=True)
        )
    except clientes_service.DocumentoDuplicado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=MSG_DOC_DUPLICADO
        )
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=MSG_NO_ENCONTRADO
        )
    return ClienteOut(**cliente)


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cliente(cliente_id: int) -> None:
    try:
        eliminado = clientes_service.eliminar(cliente_id)
    except clientes_service.ClienteConVentas:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El cliente tiene ventas asociadas y no puede eliminarse.",
        )
    if not eliminado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=MSG_NO_ENCONTRADO
        )
