from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Numeric, Integer, Index
from .database import Base

# ========== INGRESOS ==========
class Ingreso(Base):
    __tablename__ = "ingresos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fecha: Mapped["datetime"] = mapped_column(DateTime, index=True, nullable=False)
    cantidad: Mapped["decimal"] = mapped_column(Numeric(14, 2), nullable=False)

    semestre: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    banco: Mapped[str] = mapped_column(String(30), index=True, nullable=False)   # CUENTA
    metodo: Mapped[str] = mapped_column(String(30), index=True, nullable=False)  # DETALLE CUENTA

    linea: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDIENTE")
    user: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDIENTE")
    extra: Mapped[str] = mapped_column(String(50), nullable=False, default="-")  # reservado p/ transferencias

Index("ix_ingresos_semestre_banco", Ingreso.semestre, Ingreso.banco)

# ========== EGRESOS ==========
class Egreso(Base):
    __tablename__ = "egresos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fecha: Mapped["datetime"] = mapped_column(DateTime, index=True, nullable=False)

    cuenta: Mapped[str] = mapped_column(String(30), index=True, nullable=False)   # CUENTA
    metodo: Mapped[str] = mapped_column(String(20), index=True, nullable=False)   # MÉTODO

    cantidad: Mapped["decimal"] = mapped_column(Numeric(14, 2), nullable=False)       # MONTO
    cantidad_real: Mapped["decimal"] = mapped_column(Numeric(14, 2), nullable=False)  # 4x1000 aplicado o igual

    semestre: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    categoria: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    razon: Mapped[str] = mapped_column(String(120), index=True, nullable=False)

    autorizo: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    responsable: Mapped[str] = mapped_column(String(20), index=True, nullable=False)

Index("ix_egresos_semestre_cuenta", Egreso.semestre, Egreso.cuenta)
Index("ix_egresos_categoria", Egreso.categoria)
