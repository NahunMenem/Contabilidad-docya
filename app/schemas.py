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
