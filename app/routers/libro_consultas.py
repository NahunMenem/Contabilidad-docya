import re
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_admin
from ..database import get_db

router = APIRouter(prefix="/contabilidad", tags=["libro-consultas"])

PERIODO_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _parametros(db: Session) -> models.ParametrosFacturacion:
    parametros = db.get(models.ParametrosFacturacion, 1)
    if not parametros:
        parametros = models.ParametrosFacturacion(id=1)
        db.add(parametros)
        db.commit()
        db.refresh(parametros)
    return parametros


@router.get("/parametros-facturacion", response_model=schemas.ParametrosFacturacionOut)
def obtener_parametros(
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    return _parametros(db)


@router.put("/parametros-facturacion", response_model=schemas.ParametrosFacturacionOut)
def actualizar_parametros(
    data: schemas.ParametrosFacturacionUpdate,
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    parametros = _parametros(db)
    for field, value in data.model_dump().items():
        setattr(parametros, field, value)
    db.commit()
    db.refresh(parametros)
    return parametros


@router.get("/registros-consultas", response_model=list[schemas.RegistroConsultaOut])
def listar_registros(
    desde: Optional[date] = Query(default=None),
    hasta: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    stmt = select(models.RegistroConsulta)
    if desde:
        stmt = stmt.where(models.RegistroConsulta.fecha >= desde)
    if hasta:
        stmt = stmt.where(models.RegistroConsulta.fecha <= hasta)
    stmt = stmt.order_by(models.RegistroConsulta.fecha.desc(), models.RegistroConsulta.id.desc())
    return db.scalars(stmt).all()


@router.post("/registros-consultas", response_model=schemas.RegistroConsultaOut, status_code=status.HTTP_201_CREATED)
def crear_registro(
    data: schemas.RegistroConsultaCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    parametros = _parametros(db)
    registro = models.RegistroConsulta(
        **data.model_dump(),
        comision_docya_pct=parametros.comision_docya_pct,
        comision_mp_pct=parametros.comision_mp_pct,
        iva_pct=parametros.iva_pct,
        creado_por=admin.get("email") or admin.get("id") or admin.get("sub"),
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


@router.delete("/registros-consultas/{registro_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_registro(
    registro_id: int,
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    registro = db.get(models.RegistroConsulta, registro_id)
    if not registro:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    db.delete(registro)
    db.commit()


def _validar_periodo(periodo: str) -> None:
    if not PERIODO_RE.match(periodo):
        raise HTTPException(status_code=422, detail='El periodo debe tener formato "YYYY-MM"')


@router.get("/ajustes-iva/{periodo}", response_model=schemas.AjusteIvaOut)
def obtener_ajuste_iva(
    periodo: str,
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    _validar_periodo(periodo)
    ajuste = db.get(models.AjusteIvaMensual, periodo)
    if not ajuste:
        return schemas.AjusteIvaOut(periodo=periodo, otros_creditos=0, notas=None)
    return ajuste


@router.put("/ajustes-iva/{periodo}", response_model=schemas.AjusteIvaOut)
def actualizar_ajuste_iva(
    periodo: str,
    data: schemas.AjusteIvaUpdate,
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    _validar_periodo(periodo)
    ajuste = db.get(models.AjusteIvaMensual, periodo)
    if not ajuste:
        ajuste = models.AjusteIvaMensual(periodo=periodo)
        db.add(ajuste)
    ajuste.otros_creditos = data.otros_creditos
    ajuste.notas = data.notas
    db.commit()
    db.refresh(ajuste)
    return ajuste
