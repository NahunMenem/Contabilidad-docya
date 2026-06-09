import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_admin
from ..database import get_db

router = APIRouter(prefix="/contabilidad", tags=["libro-consultas"])

PERIODO_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
MONEY = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def _calc_iva(neto: Decimal, iva_pct: Decimal) -> Decimal:
    return _money(neto * iva_pct / Decimal("100"))


def _periodo_rango(periodo: str) -> tuple[date, date]:
    _validar_periodo(periodo)
    anio, mes = map(int, periodo.split("-"))
    desde = date(anio, mes, 1)
    if mes == 12:
        hasta = date(anio, 12, 31)
    else:
        hasta = date(anio, mes + 1, 1)
        hasta = date.fromordinal(hasta.toordinal() - 1)
    return desde, hasta


def _actor(admin: dict) -> str | None:
    return admin.get("email") or admin.get("id") or admin.get("sub")


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
        creado_por=_actor(admin),
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


@router.get("/comprobantes-emitidos", response_model=list[schemas.ComprobanteEmitidoOut])
def listar_comprobantes_emitidos(
    desde: Optional[date] = Query(default=None),
    hasta: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    stmt = select(models.ComprobanteEmitido)
    if desde:
        stmt = stmt.where(models.ComprobanteEmitido.fecha >= desde)
    if hasta:
        stmt = stmt.where(models.ComprobanteEmitido.fecha <= hasta)
    stmt = stmt.order_by(
        models.ComprobanteEmitido.fecha.desc(),
        models.ComprobanteEmitido.punto_venta.desc(),
        models.ComprobanteEmitido.numero.desc(),
    )
    return db.scalars(stmt).all()


def _aplicar_comprobante(target: models.ComprobanteEmitido, data: schemas.ComprobanteEmitidoBase) -> None:
    payload = data.model_dump()
    iva_debito = Decimal("0") if data.estado == "anulado" else _calc_iva(data.importe_neto, data.iva_pct)
    importe_total = Decimal("0") if data.estado == "anulado" else _money(data.importe_neto + iva_debito)
    for field, value in payload.items():
        setattr(target, field, value)
    target.iva_debito = iva_debito
    target.importe_total = importe_total


@router.post("/comprobantes-emitidos", response_model=schemas.ComprobanteEmitidoOut, status_code=status.HTTP_201_CREATED)
def crear_comprobante_emitido(
    data: schemas.ComprobanteEmitidoCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    comprobante = models.ComprobanteEmitido(creado_por=_actor(admin))
    _aplicar_comprobante(comprobante, data)
    db.add(comprobante)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un comprobante con ese tipo, punto de venta y numero")
    db.refresh(comprobante)
    return comprobante


@router.put("/comprobantes-emitidos/{comprobante_id}", response_model=schemas.ComprobanteEmitidoOut)
def actualizar_comprobante_emitido(
    comprobante_id: int,
    data: schemas.ComprobanteEmitidoUpdate,
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    comprobante = db.get(models.ComprobanteEmitido, comprobante_id)
    if not comprobante:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    _aplicar_comprobante(comprobante, data)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un comprobante con ese tipo, punto de venta y numero")
    db.refresh(comprobante)
    return comprobante


@router.delete("/comprobantes-emitidos/{comprobante_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_comprobante_emitido(
    comprobante_id: int,
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    comprobante = db.get(models.ComprobanteEmitido, comprobante_id)
    if not comprobante:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    db.delete(comprobante)
    db.commit()


@router.get("/gastos-compras", response_model=list[schemas.GastoCompraOut])
def listar_gastos_compras(
    desde: Optional[date] = Query(default=None),
    hasta: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    stmt = select(models.GastoCompra)
    if desde:
        stmt = stmt.where(models.GastoCompra.fecha >= desde)
    if hasta:
        stmt = stmt.where(models.GastoCompra.fecha <= hasta)
    stmt = stmt.order_by(models.GastoCompra.fecha.desc(), models.GastoCompra.id.desc())
    return db.scalars(stmt).all()


def _aplicar_gasto(target: models.GastoCompra, data: schemas.GastoCompraBase) -> None:
    payload = data.model_dump()
    iva_credito = _calc_iva(data.importe_neto, data.iva_pct) if data.deducible_iva else Decimal("0")
    importe_total = _money(data.importe_neto + iva_credito + data.percepciones)
    for field, value in payload.items():
        setattr(target, field, value)
    target.iva_credito = iva_credito
    target.importe_total = importe_total


@router.post("/gastos-compras", response_model=schemas.GastoCompraOut, status_code=status.HTTP_201_CREATED)
def crear_gasto_compra(
    data: schemas.GastoCompraCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    gasto = models.GastoCompra(creado_por=_actor(admin))
    _aplicar_gasto(gasto, data)
    db.add(gasto)
    db.commit()
    db.refresh(gasto)
    return gasto


@router.put("/gastos-compras/{gasto_id}", response_model=schemas.GastoCompraOut)
def actualizar_gasto_compra(
    gasto_id: int,
    data: schemas.GastoCompraUpdate,
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    gasto = db.get(models.GastoCompra, gasto_id)
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    _aplicar_gasto(gasto, data)
    db.commit()
    db.refresh(gasto)
    return gasto


@router.delete("/gastos-compras/{gasto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_gasto_compra(
    gasto_id: int,
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    gasto = db.get(models.GastoCompra, gasto_id)
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    db.delete(gasto)
    db.commit()


def _resumen_iva(periodo: str, db: Session) -> schemas.ResumenIvaMensualOut:
    desde, hasta = _periodo_rango(periodo)
    parametros = _parametros(db)
    consultas = db.scalars(
        select(models.RegistroConsulta).where(
            models.RegistroConsulta.fecha >= desde,
            models.RegistroConsulta.fecha <= hasta,
        )
    ).all()
    comprobantes = db.scalars(
        select(models.ComprobanteEmitido).where(
            models.ComprobanteEmitido.fecha >= desde,
            models.ComprobanteEmitido.fecha <= hasta,
            models.ComprobanteEmitido.estado != "anulado",
        )
    ).all()
    gastos = db.scalars(
        select(models.GastoCompra).where(
            models.GastoCompra.fecha >= desde,
            models.GastoCompra.fecha <= hasta,
        )
    ).all()
    ajuste = db.get(models.AjusteIvaMensual, periodo)

    total_consultas = _money(sum((c.precio for c in consultas), Decimal("0")))
    comision_docya = _money(sum((c.precio * c.comision_docya_pct / Decimal("100") for c in consultas), Decimal("0")))
    neto_medicos = _money(sum((c.precio * (Decimal("100") - c.comision_docya_pct) / Decimal("100") for c in consultas), Decimal("0")))
    iva_debito_consultas = _money(sum((c.precio * c.comision_docya_pct / Decimal("100") * c.iva_pct / Decimal("100") for c in consultas), Decimal("0")))
    comision_mp = _money(sum((c.precio * c.comision_mp_pct / Decimal("100") for c in consultas), Decimal("0")))
    margen_docya_post_mp = _money(comision_docya - comision_mp)
    agip_iibb = _money(comision_docya * parametros.iibb_agip_pct / Decimal("100"))
    iva_credito_mp = _money(sum((c.precio * c.comision_mp_pct / Decimal("100") * c.iva_pct / Decimal("100") for c in consultas), Decimal("0")))
    iva_debito_comprobantes = _money(sum((c.iva_debito for c in comprobantes), Decimal("0")))
    iva_credito_gastos = _money(sum((g.iva_credito for g in gastos), Decimal("0")))
    percepciones = _money(sum((g.percepciones for g in gastos), Decimal("0")))
    otros_creditos = _money(ajuste.otros_creditos if ajuste else Decimal("0"))

    iva_debito_total = _money(iva_debito_consultas + iva_debito_comprobantes)
    iva_credito_total = _money(iva_credito_mp + iva_credito_gastos + otros_creditos + percepciones)
    saldo = _money(iva_debito_total - iva_credito_total)

    return schemas.ResumenIvaMensualOut(
        periodo=periodo,
        desde=desde,
        hasta=hasta,
        consultas_cantidad=len(consultas),
        comprobantes_cantidad=len(comprobantes),
        gastos_cantidad=len(gastos),
        total_consultas_paciente=total_consultas,
        neto_medicos_total=neto_medicos,
        comision_docya_neta=comision_docya,
        margen_docya_post_mp=margen_docya_post_mp,
        iva_debito_consultas=iva_debito_consultas,
        iva_debito_comprobantes=iva_debito_comprobantes,
        iva_debito_total=iva_debito_total,
        comision_mp_neta=comision_mp,
        iva_credito_mp=iva_credito_mp,
        agip_base_imponible=comision_docya,
        agip_iibb_pct=parametros.iibb_agip_pct,
        agip_iibb_estimado=agip_iibb,
        iva_credito_gastos=iva_credito_gastos,
        otros_creditos=otros_creditos,
        percepciones=percepciones,
        iva_credito_total=iva_credito_total,
        iva_saldo_tecnico=saldo,
        iva_a_pagar_estimado=max(saldo, Decimal("0")),
        saldo_a_favor_estimado=abs(min(saldo, Decimal("0"))),
        notas_ajuste=ajuste.notas if ajuste else None,
    )


@router.get("/resumen-iva/{periodo}", response_model=schemas.ResumenIvaMensualOut)
def obtener_resumen_iva(
    periodo: str,
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    return _resumen_iva(periodo, db)


@router.get("/arca/checklist/{periodo}", response_model=schemas.ChecklistArcaOut)
def obtener_checklist_arca(
    periodo: str,
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    resumen = _resumen_iva(periodo, db)
    pendientes: list[str] = []
    if resumen.consultas_cantidad == 0 and resumen.comprobantes_cantidad == 0:
        pendientes.append("No hay ventas/consultas cargadas para el periodo")
    if resumen.gastos_cantidad == 0 and resumen.otros_creditos == 0:
        pendientes.append("No hay gastos, percepciones ni otros creditos cargados")
    if resumen.comprobantes_cantidad == 0:
        pendientes.append("Verificar si hubo comprobantes emitidos fuera del libro manual de consultas")
    return schemas.ChecklistArcaOut(
        periodo=periodo,
        listo_para_revisar=len(pendientes) == 0,
        pendientes=pendientes,
        fuentes=[
            "registros_consultas",
            "comprobantes_emitidos",
            "gastos_compras",
            "ajustes_iva_mensuales",
        ],
    )


@router.get("/exportaciones/iva/{periodo}.csv")
def exportar_iva_csv(
    periodo: str,
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    resumen = _resumen_iva(periodo, db)
    rows = [
        ["periodo", resumen.periodo],
        ["desde", resumen.desde.isoformat()],
        ["hasta", resumen.hasta.isoformat()],
        ["consultas_cantidad", str(resumen.consultas_cantidad)],
        ["comprobantes_cantidad", str(resumen.comprobantes_cantidad)],
        ["gastos_cantidad", str(resumen.gastos_cantidad)],
        ["total_consultas_paciente", str(resumen.total_consultas_paciente)],
        ["neto_medicos_total", str(resumen.neto_medicos_total)],
        ["comision_docya_neta", str(resumen.comision_docya_neta)],
        ["comision_mp_absorbida", str(resumen.comision_mp_neta)],
        ["margen_docya_post_mp", str(resumen.margen_docya_post_mp)],
        ["agip_base_imponible", str(resumen.agip_base_imponible)],
        ["agip_iibb_pct", str(resumen.agip_iibb_pct)],
        ["agip_iibb_estimado", str(resumen.agip_iibb_estimado)],
        ["iva_debito_consultas", str(resumen.iva_debito_consultas)],
        ["iva_debito_comprobantes", str(resumen.iva_debito_comprobantes)],
        ["iva_debito_total", str(resumen.iva_debito_total)],
        ["comision_mp_neta", str(resumen.comision_mp_neta)],
        ["iva_credito_mp", str(resumen.iva_credito_mp)],
        ["iva_credito_gastos", str(resumen.iva_credito_gastos)],
        ["otros_creditos", str(resumen.otros_creditos)],
        ["percepciones", str(resumen.percepciones)],
        ["iva_credito_total", str(resumen.iva_credito_total)],
        ["iva_saldo_tecnico", str(resumen.iva_saldo_tecnico)],
        ["iva_a_pagar_estimado", str(resumen.iva_a_pagar_estimado)],
        ["saldo_a_favor_estimado", str(resumen.saldo_a_favor_estimado)],
    ]
    body = "campo,valor\n" + "\n".join(f"{campo},{valor}" for campo, valor in rows) + "\n"
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="docya-iva-{periodo}.csv"'},
    )
