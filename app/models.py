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


class AjusteIvaMensual(Base):
    __tablename__ = "ajustes_iva_mensuales"
    __table_args__ = {"schema": SCHEMA}

    periodo = Column(Text, primary_key=True)  # 'YYYY-MM'
    otros_creditos = Column(Numeric(12, 2), nullable=False, default=0)
    notas = Column(Text, nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
