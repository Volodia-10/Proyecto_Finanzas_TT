from __future__ import annotations
from sqlalchemy import Column, Integer, String, DateTime, Numeric
from .database import Base

class Ingreso(Base):
    __tablename__ = "ingresos"
    id       = Column(Integer, primary_key=True, index=True)
    fecha    = Column(DateTime, index=True)
    cantidad = Column(Numeric(12,2))
    semestre = Column(String(20))
    banco    = Column(String(50))   # cuenta
    metodo   = Column(String(50))   # detalle o WOMPI
    linea    = Column(String(50))
    user     = Column(String(80))
    extra    = Column(String(120))

class Egreso(Base):
    __tablename__ = "egresos"
    id            = Column(Integer, primary_key=True, index=True)
    fecha         = Column(DateTime, index=True)
    cuenta        = Column(String(50))
    metodo        = Column(String(50))
    cantidad      = Column(Numeric(12,2))   # neto
    cantidad_real = Column(Numeric(12,2))   # con 4x1000
    semestre      = Column(String(20))
    categoria     = Column(String(50))
    razon         = Column(String(120))
    autorizo      = Column(String(50))
    responsable   = Column(String(50))
