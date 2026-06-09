from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from .database import Base

SCHEMA = "contabilidad"
MONEY = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


class ObligacionFiscal(Base):
    __tablename__ = "obligaciones_fiscales"
    __table_args__ = {"schema": SCHEMA}

    id = Column(Integer, primary_key=True)
    nombre = Column(Text, nullable=False, unique=True)
    organismo = Column(Text, nullable=False)
    periodicidad = Column(Text, nullable=False)  # 'mensual' | 'anual'
    dia_vencimiento = Column(SmallInteger, nullable=False)
    mes_vencimiento = Column(SmallInteger, nullable=True)
    notas = Column(Text, nullable=True)
    activa = Column(Boolean, nullable=False, default=True)
    ultimo_periodo_cumplido = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class Presentacion(Base):
    __tablename__ = "presentaciones"
    __table_args__ = (
        UniqueConstraint("obligacion_id", "periodo", name="uq_presentacion_obligacion_periodo"),
        {"schema": SCHEMA},
    )

    id = Column(Integer, primary_key=True)
    obligacion_id = Column(
        Integer,
        ForeignKey(f"{SCHEMA}.obligaciones_fiscales.id", ondelete="CASCADE"),
        nullable=False,
    )
    periodo = Column(Text, nullable=False)
    marcado_por = Column(Text, nullable=True)
    marcado_en = Column(TIMESTAMP(timezone=True), server_default=func.now())


class ParametrosFacturacion(Base):
    __tablename__ = "parametros_facturacion"
    __table_args__ = (
        CheckConstraint("id = 1", name="parametros_facturacion_singleton"),
        {"schema": SCHEMA},
    )

    id = Column(SmallInteger, primary_key=True, default=1)
    comision_docya_pct = Column(Numeric(6, 3), nullable=False, default=20)
    comision_mp_pct = Column(Numeric(6, 3), nullable=False, default=6)
    iva_pct = Column(Numeric(6, 3), nullable=False, default=21)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class RegistroConsulta(Base):
    __tablename__ = "registros_consultas"
    __table_args__ = {"schema": SCHEMA}

    id = Column(Integer, primary_key=True)
    fecha = Column(Date, nullable=False)
    medico = Column(Text, nullable=False)
    tipo = Column(Text, nullable=False)
    precio = Column(Numeric(12, 2), nullable=False)
    comision_docya_pct = Column(Numeric(6, 3), nullable=False)
    comision_mp_pct = Column(Numeric(6, 3), nullable=False)
    iva_pct = Column(Numeric(6, 3), nullable=False)
    creado_por = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    @property
    def comision_docya_importe(self):
        return money(self.precio * self.comision_docya_pct / Decimal("100"))

    @property
    def comision_mp_importe(self):
        return money(self.precio * self.comision_mp_pct / Decimal("100"))

    @property
    def neto_medico_importe(self):
        return money(self.precio * (Decimal("100") - self.comision_docya_pct) / Decimal("100"))

    @property
    def base_despues_mp(self):
        return money(self.precio - self.comision_mp_importe)

    @property
    def margen_docya_post_mp(self):
        return money(self.comision_docya_importe - self.comision_mp_importe)

    @property
    def iva_debito_docya(self):
        return money(self.comision_docya_importe * self.iva_pct / Decimal("100"))

    @property
    def iva_credito_mp(self):
        return money(self.comision_mp_importe * self.iva_pct / Decimal("100"))


class AjusteIvaMensual(Base):
    __tablename__ = "ajustes_iva_mensuales"
    __table_args__ = {"schema": SCHEMA}

    periodo = Column(Text, primary_key=True)  # 'YYYY-MM'
    otros_creditos = Column(Numeric(12, 2), nullable=False, default=0)
    notas = Column(Text, nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class ComprobanteEmitido(Base):
    __tablename__ = "comprobantes_emitidos"
    __table_args__ = (
        UniqueConstraint("tipo_comprobante", "punto_venta", "numero", name="uq_comprobante_emitido"),
        {"schema": SCHEMA},
    )

    id = Column(Integer, primary_key=True)
    fecha = Column(Date, nullable=False)
    tipo_comprobante = Column(Text, nullable=False, default="Factura")
    letra = Column(Text, nullable=False, default="B")
    punto_venta = Column(Integer, nullable=False)
    numero = Column(Integer, nullable=False)
    receptor_nombre = Column(Text, nullable=False)
    receptor_documento = Column(Text, nullable=True)
    condicion_iva_receptor = Column(Text, nullable=True)
    concepto = Column(Text, nullable=False)
    importe_neto = Column(Numeric(12, 2), nullable=False)
    iva_pct = Column(Numeric(6, 3), nullable=False, default=21)
    iva_debito = Column(Numeric(12, 2), nullable=False)
    importe_total = Column(Numeric(12, 2), nullable=False)
    cae = Column(Text, nullable=True)
    cae_vencimiento = Column(Date, nullable=True)
    estado = Column(Text, nullable=False, default="emitido")
    notas = Column(Text, nullable=True)
    creado_por = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class GastoCompra(Base):
    __tablename__ = "gastos_compras"
    __table_args__ = {"schema": SCHEMA}

    id = Column(Integer, primary_key=True)
    fecha = Column(Date, nullable=False)
    proveedor_nombre = Column(Text, nullable=False)
    proveedor_cuit = Column(Text, nullable=True)
    tipo_comprobante = Column(Text, nullable=False, default="Factura")
    letra = Column(Text, nullable=True)
    punto_venta = Column(Integer, nullable=True)
    numero = Column(Integer, nullable=True)
    concepto = Column(Text, nullable=False)
    categoria = Column(Text, nullable=True)
    importe_neto = Column(Numeric(12, 2), nullable=False)
    iva_pct = Column(Numeric(6, 3), nullable=False, default=21)
    iva_credito = Column(Numeric(12, 2), nullable=False)
    percepciones = Column(Numeric(12, 2), nullable=False, default=0)
    importe_total = Column(Numeric(12, 2), nullable=False)
    deducible_iva = Column(Boolean, nullable=False, default=True)
    notas = Column(Text, nullable=True)
    creado_por = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
