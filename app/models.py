from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, DateTime, Numeric, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


# =========================
#        INGRESOS
# =========================
class Ingreso(Base):
    __tablename__ = "ingresos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Fecha exacta del registro (dd/mm/aaaa hh:mm:ss en UI; aquí guardamos datetime)
    fecha: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)

    # MONTO neto (ya con reglas WOMPI cuando aplique)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # Catálogos seleccionados en el formulario
    semestre: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    banco: Mapped[str] = mapped_column(String(30), index=True, nullable=False)     # CUENTA
    metodo: Mapped[str] = mapped_column(String(30), index=True, nullable=False)    # DETALLE CUENTA

    # Campos opcionales de línea y usuario
    linea: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDIENTE")
    user: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDIENTE")

    # Reservado para futuras TRANSFERENCIAS INTERNAS
    extra: Mapped[str] = mapped_column(String(50), nullable=False, default="-")


# Índices útiles para filtros/consultas
Index("ix_ingresos_semestre_banco", Ingreso.semestre, Ingreso.banco)


# =========================
#        EGRESOS
# =========================
class Egreso(Base):
    __tablename__ = "egresos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)

    # Origen y método
    cuenta: Mapped[str] = mapped_column(String(30), index=True, nullable=False)    # CUENTA
    metodo: Mapped[str] = mapped_column(String(20), index=True, nullable=False)    # MÉTODO (PAGO/ENVIO/TARJETA/RETIRO)

    # Montos (bruto y real con 4x1000 aplicado cuando aplique)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    cantidad_real: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # Clasificación
    semestre: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    categoria: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    # Si hay MES u otras piezas (CARROS: NOMBRE_CARRO_MOTIVO_RAZON), se serializa aquí
    razon: Mapped[str] = mapped_column(String(120), index=True, nullable=False)

    # Control interno
    autorizo: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    responsable: Mapped[str] = mapped_column(String(20), index=True, nullable=False)


# Índices útiles para filtros/consultas
Index("ix_egresos_semestre_cuenta", Egreso.semestre, Egreso.cuenta)

