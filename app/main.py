# app/main.py
from __future__ import annotations

import os
from decimal import Decimal
from datetime import date, datetime
from pathlib import Path
from typing import Generator

from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Date,
    Numeric,
    Text,
    func,
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# --------------------------------------------------------------------------------------
# Rutas de archivos
# --------------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# --------------------------------------------------------------------------------------
# Config DB
# - Usa tu URL de Postgres desde .env (por ejemplo DATABASE_URL=postgresql://...).
# - ECHO SQL activable con SQL_ECHO=1 (útil en debugging).
# - Para evitar "Duplicate index" en producción, no llamamos create_all salvo RUN_CREATE_ALL=1
# --------------------------------------------------------------------------------------
DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or os.getenv("SQLALCHEMY_DATABASE_URL")
    or "sqlite:///./local.db"
)

ECHO_SQL = os.getenv("SQL_ECHO", "0") == "1"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=ECHO_SQL,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------------------------------------------------------------------------------------
# Modelos
# --------------------------------------------------------------------------------------
class Ingreso(Base):
    __tablename__ = "ingresos"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    cantidad = Column(Numeric(14, 2), nullable=False)
    semestre = Column(String(10), index=True)
    banco = Column(String(50), index=True)
    metodo = Column(String(50), index=True)
    linea = Column(String(50), index=True)
    user = Column(String(50))
    extra = Column(Text)


class Egreso(Base):
    __tablename__ = "egresos"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    cuenta = Column(String(50), index=True)          # p.ej. Bancolombia / Nequi
    metodo = Column(String(50), index=True)          # p.ej. PSE / Tarjeta / Transferencia
    cantidad = Column(Numeric(14, 2), nullable=False)
    cantidad_real = Column(Numeric(14, 2))           # si aplican comisiones
    semestre = Column(String(10), index=True)
    categoria = Column(String(80), index=True)       # p.ej. Publicidad / Nómina / Servicios
    razon = Column(Text)                             
    autorizo = Column(String(50))
    responsable = Column(String(50))


# Crear tablas sólo si explícitamente se pide
if os.getenv("RUN_CREATE_ALL", "0") == "1":
    Base.metadata.create_all(bind=engine)

# --------------------------------------------------------------------------------------
# App y templates
# --------------------------------------------------------------------------------------
app = FastAPI(title="Proyecto Finanzas TT")

# estáticos: /static -> app/static
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# templates: app/templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# --------------------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------------------
def _parse_decimal(v: str | None) -> Decimal:
    if v is None or v == "":
        return Decimal("0")
    # admitir comas decimales tipo "1.234,56"
    v = v.replace(".", "").replace(",", ".")
    return Decimal(v)


def _parse_date(v: str) -> date:
    # espera YYYY-MM-DD
    return datetime.strptime(v, "%Y-%m-%d").date()


# --------------------------------------------------------------------------------------
# Rutas
# --------------------------------------------------------------------------------------
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# -------------------- INGRESOS --------------------
@app.get("/ingresos")
def listar_ingresos(request: Request, db: Session = Depends(get_db)):
    rows = (
        db.query(Ingreso)
        .order_by(Ingreso.fecha.desc(), Ingreso.id.desc())
        .all()
    )
    return templates.TemplateResponse(
        "ingresos.html",
        {"request": request, "rows": rows},
    )


@app.get("/ingresos/nuevo")
def form_ingreso(request: Request):
    return templates.TemplateResponse("ingresos_nuevo.html", {"request": request})


@app.post("/ingresos/nuevo")
def crear_ingreso(
    request: Request,
    fecha: str = Form(...),
    cantidad: str = Form(...),
    semestre: str = Form(""),
    banco: str = Form(""),
    metodo: str = Form(""),
    linea: str = Form(""),
    user: str = Form(""),
    extra: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        row = Ingreso(
            fecha=_parse_date(fecha),
            cantidad=_parse_decimal(cantidad),
            semestre=semestre.strip(),
            banco=banco.strip(),
            metodo=metodo.strip(),
            linea=linea.strip(),
            user=user.strip(),
            extra=extra.strip(),
        )
        db.add(row)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"No se pudo crear ingreso: {exc}")

    return RedirectResponse(url="/ingresos", status_code=303)


# Resumen de ingresos (por semestre y por banco)
@app.get("/resumen_ingresos")
def resumen_ingresos(request: Request, db: Session = Depends(get_db)):
    por_semestre = (
        db.query(Ingreso.semestre, func.sum(Ingreso.cantidad).label("total"))
        .group_by(Ingreso.semestre)
        .order_by(Ingreso.semestre.desc())
        .all()
    )
    por_banco = (
        db.query(Ingreso.banco, func.sum(Ingreso.cantidad).label("total"))
        .group_by(Ingreso.banco)
        .order_by(func.sum(Ingreso.cantidad).desc())
        .all()
    )
    total = db.query(func.sum(Ingreso.cantidad)).scalar() or Decimal("0")

    return templates.TemplateResponse(
        "resumen_ingresos.html",
        {
            "request": request,
            "por_semestre": por_semestre,
            "por_banco": por_banco,
            "total": total,
        },
    )


# -------------------- EGRESOS --------------------
@app.get("/egresos")
def listar_egresos(request: Request, db: Session = Depends(get_db)):
    rows = (
        db.query(Egreso)
        .order_by(Egreso.fecha.desc(), Egreso.id.desc())
        .all()
    )
    return templates.TemplateResponse(
        "egresos.html",
        {"request": request, "rows": rows},
    )


@app.get("/egresos/nuevo")
def form_egreso(request: Request):
    return templates.TemplateResponse("egresos_nuevo.html", {"request": request})


@app.post("/egresos/nuevo")
def crear_egreso(
    request: Request,
    fecha: str = Form(...),
    cuenta: str = Form(""),
    metodo: str = Form(""),
    cantidad: str = Form(...),
    cantidad_real: str = Form(""),
    semestre: str = Form(""),
    categoria: str = Form(""),
    razon: str = Form(""),
    autorizo: str = Form(""),
    responsable: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        row = Egreso(
            fecha=_parse_date(fecha),
            cuenta=cuenta.strip(),
            metodo=metodo.strip(),
            cantidad=_parse_decimal(cantidad),
            cantidad_real=_parse_decimal(cantidad_real) if cantidad_real else None,
            semestre=semestre.strip(),
            categoria=categoria.strip(),
            razon=razon.strip(),
            autorizo=autorizo.strip(),
            responsable=responsable.strip(),
        )
        db.add(row)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"No se pudo crear egreso: {exc}")

    return RedirectResponse(url="/egresos", status_code=303)


# Resumen de egresos (por semestre, categoría y cuenta)
@app.get("/resumen_egresos")
def resumen_egresos(request: Request, db: Session = Depends(get_db)):
    por_semestre = (
        db.query(Egreso.semestre, func.sum(Egreso.cantidad).label("total"))
        .group_by(Egreso.semestre)
        .order_by(Egreso.semestre.desc())
        .all()
    )
    por_categoria = (
        db.query(Egreso.categoria, func.sum(Egreso.cantidad).label("total"))
        .group_by(Egreso.categoria)
        .order_by(func.sum(Egreso.cantidad).desc())
        .all()
    )
    por_cuenta = (
        db.query(Egreso.cuenta, func.sum(Egreso.cantidad).label("total"))
        .group_by(Egreso.cuenta)
        .order_by(func.sum(Egreso.cantidad).desc())
        .all()
    )
    total = db.query(func.sum(Egreso.cantidad)).scalar() or Decimal("0")

    return templates.TemplateResponse(
        "resumen_egresos.html",
        {
            "request": request,
            "por_semestre": por_semestre,
            "por_categoria": por_categoria,
            "por_cuenta": por_cuenta,
            "total": total,
        },
    )
