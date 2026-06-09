from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

Periodicidad = Literal["mensual", "anual"]


class ObligacionBase(BaseModel):
    nombre: str
    organismo: str
    periodicidad: Periodicidad
    # Las anuales caen en un mes fijo y pueden vencer hasta el dia 31; las
    # mensuales no, porque no todos los meses tienen dias 29-31 (ej. febrero).
    dia_vencimiento: int = Field(ge=1, le=31)
    mes_vencimiento: Optional[int] = Field(default=None, ge=1, le=12)
    notas: Optional[str] = None
    activa: bool = True

    @model_validator(mode="after")
    def _validar_dia_segun_periodicidad(self):
        if self.periodicidad == "mensual" and self.dia_vencimiento > 28:
            raise ValueError("Una obligacion mensual no puede vencer despues del dia 28 (no todos los meses tienen 29-31)")
        return self


class ObligacionCreate(ObligacionBase):
    pass


class ObligacionUpdate(ObligacionBase):
    pass


class ObligacionOut(ObligacionBase):
    id: int
    ultimo_periodo_cumplido: Optional[str] = None

    class Config:
        from_attributes = True


class MarcarPresentadaIn(BaseModel):
    periodo: str = Field(description='Periodo cumplido, formato "YYYY-MM" (mensual) o "YYYY" (anual)')


class ParametrosFacturacionOut(BaseModel):
    comision_docya_pct: Decimal
    comision_mp_pct: Decimal
    iva_pct: Decimal

    class Config:
        from_attributes = True


class ParametrosFacturacionUpdate(BaseModel):
    comision_docya_pct: Decimal = Field(ge=0, le=100)
    comision_mp_pct: Decimal = Field(ge=0, le=100)
    iva_pct: Decimal = Field(ge=0, le=100)


class RegistroConsultaCreate(BaseModel):
    fecha: date
    medico: str = Field(min_length=1)
    tipo: str = Field(min_length=1)
    precio: Decimal = Field(ge=0)


class RegistroConsultaOut(BaseModel):
    id: int
    fecha: date
    medico: str
    tipo: str
    precio: Decimal
    comision_docya_pct: Decimal
    comision_mp_pct: Decimal
    iva_pct: Decimal

    class Config:
        from_attributes = True


class AjusteIvaOut(BaseModel):
    periodo: str
    otros_creditos: Decimal
    notas: Optional[str] = None

    class Config:
        from_attributes = True


class AjusteIvaUpdate(BaseModel):
    otros_creditos: Decimal = Field(ge=0)
    notas: Optional[str] = None


EstadoComprobante = Literal["borrador", "emitido", "anulado"]


class ComprobanteEmitidoBase(BaseModel):
    fecha: date
    tipo_comprobante: str = Field(default="Factura", min_length=1)
    letra: str = Field(default="B", min_length=1, max_length=2)
    punto_venta: int = Field(ge=1)
    numero: int = Field(ge=1)
    receptor_nombre: str = Field(min_length=1)
    receptor_documento: Optional[str] = None
    condicion_iva_receptor: Optional[str] = None
    concepto: str = Field(min_length=1)
    importe_neto: Decimal = Field(ge=0)
    iva_pct: Decimal = Field(default=Decimal("21"), ge=0, le=100)
    cae: Optional[str] = None
    cae_vencimiento: Optional[date] = None
    estado: EstadoComprobante = "emitido"
    notas: Optional[str] = None


class ComprobanteEmitidoCreate(ComprobanteEmitidoBase):
    pass


class ComprobanteEmitidoUpdate(ComprobanteEmitidoBase):
    pass


class ComprobanteEmitidoOut(ComprobanteEmitidoBase):
    id: int
    iva_debito: Decimal
    importe_total: Decimal

    class Config:
        from_attributes = True


class GastoCompraBase(BaseModel):
    fecha: date
    proveedor_nombre: str = Field(min_length=1)
    proveedor_cuit: Optional[str] = None
    tipo_comprobante: str = Field(default="Factura", min_length=1)
    letra: Optional[str] = Field(default=None, max_length=2)
    punto_venta: Optional[int] = Field(default=None, ge=1)
    numero: Optional[int] = Field(default=None, ge=1)
    concepto: str = Field(min_length=1)
    categoria: Optional[str] = None
    importe_neto: Decimal = Field(ge=0)
    iva_pct: Decimal = Field(default=Decimal("21"), ge=0, le=100)
    percepciones: Decimal = Field(default=Decimal("0"), ge=0)
    deducible_iva: bool = True
    notas: Optional[str] = None


class GastoCompraCreate(GastoCompraBase):
    pass


class GastoCompraUpdate(GastoCompraBase):
    pass


class GastoCompraOut(GastoCompraBase):
    id: int
    iva_credito: Decimal
    importe_total: Decimal

    class Config:
        from_attributes = True


class ResumenIvaMensualOut(BaseModel):
    periodo: str
    desde: date
    hasta: date
    consultas_cantidad: int
    comprobantes_cantidad: int
    gastos_cantidad: int
    total_consultas_paciente: Decimal
    comision_docya_neta: Decimal
    iva_debito_consultas: Decimal
    iva_debito_comprobantes: Decimal
    iva_debito_total: Decimal
    comision_mp_neta: Decimal
    iva_credito_mp: Decimal
    iva_credito_gastos: Decimal
    otros_creditos: Decimal
    percepciones: Decimal
    iva_credito_total: Decimal
    iva_saldo_tecnico: Decimal
    iva_a_pagar_estimado: Decimal
    saldo_a_favor_estimado: Decimal
    notas_ajuste: Optional[str] = None


class ChecklistArcaOut(BaseModel):
    periodo: str
    listo_para_revisar: bool
    pendientes: list[str]
    fuentes: list[str]
