from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    ForeignKey,
    Integer,
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
