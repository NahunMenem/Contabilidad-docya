from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_admin
from ..database import get_db

router = APIRouter(prefix="/contabilidad/obligaciones", tags=["obligaciones"])


@router.get("", response_model=list[schemas.ObligacionOut])
def listar_obligaciones(
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    return db.scalars(
        select(models.ObligacionFiscal).order_by(models.ObligacionFiscal.id)
    ).all()


@router.post("", response_model=schemas.ObligacionOut, status_code=status.HTTP_201_CREATED)
def crear_obligacion(
    data: schemas.ObligacionCreate,
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    existente = db.scalar(
        select(models.ObligacionFiscal).where(models.ObligacionFiscal.nombre == data.nombre)
    )
    if existente:
        raise HTTPException(status_code=409, detail="Ya existe una obligacion con ese nombre")

    obligacion = models.ObligacionFiscal(**data.model_dump())
    db.add(obligacion)
    db.commit()
    db.refresh(obligacion)
    return obligacion


@router.put("/{obligacion_id}", response_model=schemas.ObligacionOut)
def actualizar_obligacion(
    obligacion_id: int,
    data: schemas.ObligacionUpdate,
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    obligacion = db.get(models.ObligacionFiscal, obligacion_id)
    if not obligacion:
        raise HTTPException(status_code=404, detail="Obligacion no encontrada")

    for field, value in data.model_dump().items():
        setattr(obligacion, field, value)

    db.commit()
    db.refresh(obligacion)
    return obligacion


@router.delete("/{obligacion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_obligacion(
    obligacion_id: int,
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    obligacion = db.get(models.ObligacionFiscal, obligacion_id)
    if not obligacion:
        raise HTTPException(status_code=404, detail="Obligacion no encontrada")

    db.delete(obligacion)
    db.commit()


@router.post("/{obligacion_id}/marcar-presentada", response_model=schemas.ObligacionOut)
def marcar_presentada(
    obligacion_id: int,
    data: schemas.MarcarPresentadaIn,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    obligacion = db.get(models.ObligacionFiscal, obligacion_id)
    if not obligacion:
        raise HTTPException(status_code=404, detail="Obligacion no encontrada")

    if not obligacion.ultimo_periodo_cumplido or data.periodo > obligacion.ultimo_periodo_cumplido:
        obligacion.ultimo_periodo_cumplido = data.periodo

    ya_registrada = db.scalar(
        select(models.Presentacion).where(
            models.Presentacion.obligacion_id == obligacion_id,
            models.Presentacion.periodo == data.periodo,
        )
    )
    if not ya_registrada:
        db.add(
            models.Presentacion(
                obligacion_id=obligacion_id,
                periodo=data.periodo,
                marcado_por=admin.get("email") or admin.get("id") or admin.get("sub"),
            )
        )

    db.commit()
    db.refresh(obligacion)
    return obligacion
