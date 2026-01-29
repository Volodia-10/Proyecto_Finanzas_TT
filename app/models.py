from sqlalchemy import Column, Integer, String, DateTime, Numeric
from .database import Base

class Ingreso(Base):
    __tablename__ = "ingresos"

    id        = Column(Integer, primary_key=True, index=True)
    fecha     = Column(DateTime(timezone=True), nullable=False)
    cantidad  = Column(Numeric(12, 2), nullable=False)

    semestre  = Column(String(32),  nullable=False)
    banco     = Column(String(32),  nullable=False)
    metodo    = Column(String(32),  nullable=False)
    linea     = Column(String(64),  nullable=False)
    user      = Column(String(64),  nullable=False)
    extra     = Column(String(128), nullable=False)

class Egreso(Base):
    __tablename__ = "egresos"

    id            = Column(Integer, primary_key=True, index=True)
    fecha         = Column(DateTime(timezone=True), nullable=False)
    cuenta        = Column(String(32),  nullable=False)
    metodo        = Column(String(32),  nullable=False)
    cantidad      = Column(Numeric(12, 2), nullable=False)
    cantidad_real = Column(Numeric(12, 2), nullable=False)

    semestre      = Column(String(32),  nullable=False)
    categoria     = Column(String(64),  nullable=False)
    razon         = Column(String(128), nullable=False)
    autorizo      = Column(String(64),  nullable=False)
    responsable   = Column(String(64),  nullable=False)
