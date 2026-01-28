# app/main.py
from __future__ import annotations

from fastapi import FastAPI, Request, Depends, Form, status
from fastapi.responses import RedirectResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session
from sqlalchemy import func

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import io
import csv
import os

from .database import Base, engine, SessionLocal
from .models import Ingreso, Egreso


# ===================== FastAPI / Templates / Static =====================

app = FastAPI(title="Proyecto Finanzas TT")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)


# ===================== DB Lifecycle =====================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    # Crea tablas si no existen (no borra datos)
    Base.metadata.create_all(bind=engine)


# ===================== Helpers =====================

def to_decimal_monto(monto_str: str) -> Decimal:
    """
    Convierte string de monto con formateo COP a Decimal (2 decimales).
    Acepta entradas tipo: "$ 1.000.000,50" o "1000000.50" o "1.000.000".
    """
    limpio = (monto_str or "").replace("$", "").replace(" ", "")
    # estandariza separadores: quita miles '.' y cambia coma por punto
    limpio = limpio.replace(".", "").replace(",", ".").strip()
    if limpio == "":
        limpio = "0"
    return Decimal(limpio).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def wompi_neto(monto_original: Decimal, metodo_wompi: str | None) -> Decimal:
    """
    Regla WOMPI:
      comisiónBase = montoOriginal*0.0265 + 700
      ivaComision  = comisiónBase*0.19
      descuento    = comisiónBase + ivaComision
      si TC: + retención = montoOriginal*0.015
      neto = montoOriginal - descuento
    """
    comision_base = (monto_original * Decimal("0.0265") + Decimal("700")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    iva_com = (comision_base * Decimal("0.19")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    descuento = (comision_base + iva_com).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if (metodo_wompi or "").upper() == "TC":
        descuento = (descuento + (monto_original * Decimal("0.015"))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    neto = (monto_original - descuento).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return neto


def up(s: str | None, default: str = "-") -> str:
    """Upper seguro."""
    s = (s or "").strip()
    return s.upper() if s else default


# ===================== Home =====================

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ===================== INGRESOS =====================

@app.get("/ingresos/nuevo")
def form_ingreso(request: Request):
    return templates.TemplateResponse("ingresos_form.html", {"request": request})


@app.post("/ingresos/nuevo")
def crear_ingreso(
    monto: str = Form(...),
    semestre: str = Form(...),
    cuenta: str = Form(...),                 # BANCOLOMBIA_1423 / NEQUI / DAVIVIENDA / EFECTIVO / EFECTY ...
    detalle_cuenta: str = Form(...),         # BANCOLOMBIA/WOMPI/NEQUI/... (según CUENTA)
    metodo_wompi: str | None = Form(None),   # PSE / TC (solo si detalle_cuenta == WOMPI)
    flag_linea_user: str | None = Form(None),
    linea: str | None = Form(None),
    user: str | None = Form(None),
    db: Session = Depends(get_db),
):
    monto_original = to_decimal_monto(monto)

    # Cálculo de neto solo si WOMPI
    neto = monto_original
    if up(detalle_cuenta) == "WOMPI":
        neto = wompi_neto(monto_original, metodo_wompi)

    # Mayúsculas y defaults
    semestre_up = up(semestre)
    cuenta_up = up(cuenta)
    metodo_up = up(detalle_cuenta)
    linea_up = up(linea, "PENDIENTE")
    user_up = up(user, "PENDIENTE")

    # Reglas de PAGO INTERESES
    if metodo_up == "PAGO INTERESES":
        semestre_up = "GENERAL"
        linea_up = "GENERAL"
        user_up = "INTERESES"

    nuevo = Ingreso(
        fecha=datetime.now(),
        cantidad=neto,           # neto según reglas
        semestre=semestre_up,
        banco=cuenta_up,
        metodo=metodo_up,        # aquí se muestra WOMPI si aplica (no PSE/TC)
        linea=linea_up,
        user=user_up,
        extra="-",               # reservado p/ transferencias internas
    )

    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    # Redirige a la tabla
    return RedirectResponse(url="/ingresos", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/ingresos")
def view_ingresos(request: Request, db: Session = Depends(get_db)):
    registros = db.query(Ingreso).order_by(Ingreso.fecha.desc()).all()
    return templates.TemplateResponse(
        "ingresos.html",
        {"request": request, "registros": registros},
    )


@app.get("/ingresos/export.csv")
def export_ingresos_csv(db: Session = Depends(get_db)):
    rows = db.query(Ingreso).order_by(Ingreso.fecha.asc()).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["FECHA", "CANTIDAD", "SEMESTRE", "BANCO", "MÉTODO", "LÍNEA", "USER", "EXTRA"])
    for r in rows:
        # FECHA formateada dd/mm/aaaa hh:mm:ss
        fecha_txt = r.fecha.strftime("%d/%m/%Y %H:%M:%S") if r.fecha else ""
        w.writerow([fecha_txt, f"{r.cantidad:.2f}", r.semestre, r.banco, r.metodo, r.linea, r.user, r.extra])

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="ingresos.csv"'},
    )


@app.get("/ingresos/export.xlsx")
def export_ingresos_xlsx(db: Session = Depends(get_db)):
    try:
        from openpyxl import Workbook
    except Exception:
        return JSONResponse(
            {"error": "openpyxl no está instalado. Usa /ingresos/export.csv o agrega openpyxl a requirements.txt"},
            status_code=501,
        )
    rows = db.query(Ingreso).order_by(Ingreso.fecha.asc()).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "INGRESOS"
    ws.append(["FECHA", "CANTIDAD", "SEMESTRE", "BANCO", "MÉTODO", "LÍNEA", "USER", "EXTRA"])
    for r in rows:
        fecha_txt = r.fecha.strftime("%d/%m/%Y %H:%M:%S") if r.fecha else ""
        ws.append([fecha_txt, float(r.cantidad or 0), r.semestre, r.banco, r.metodo, r.linea, r.user, r.extra])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="ingresos.xlsx"'},
    )


# ===================== EGRESOS =====================

@app.get("/egresos/nuevo")
def form_egreso(request: Request):
    return templates.TemplateResponse("egresos_form.html", {"request": request})


@app.post("/egresos/nuevo")
def crear_egreso(
    monto: str = Form(...),
    cuenta: str = Form(...),
    metodo: str = Form(...),                 # PAGO, ENVIO, TARJETA, RETIRO
    semestre: str = Form(...),
    categoria: str = Form(...),
    # NOTA: El front ya debe construir "razon" final:
    #   - si hubo MES: RAZON_MES
    #   - si fue CARROS: NOMBRECARRO_MOTIVO_RAZON (si RAZÓN libre)
    # Si prefieres, también puedes enviar campos extra y concatenar aquí.
    razon: str = Form(...),
    autorizo: str = Form(...),               # JESÚS, FELIPE, MARLON, MONICA, AUTOMATICO
    responsable: str = Form(...),            # JESÚS, FELIPE, MARLON, EMPRESA
    db: Session = Depends(get_db),
):
    cantidad = to_decimal_monto(monto)

    cuenta_up = up(cuenta)
    metodo_up = up(metodo)
    semestre_up = up(semestre)
    categoria_up = up(categoria)
    razon_up = up(razon)
    autorizo_up = up(autorizo)
    responsable_up = up(responsable)

    # 4x1000: si cuenta != EFECTIVO/EFECTY -> cantidad_real = cantidad * 1.004
    if cuenta_up in ("EFECTIVO", "EFECTY"):
        cantidad_real = cantidad
    else:
        cantidad_real = (cantidad * Decimal("1.004")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    nuevo = Egreso(
        fecha=datetime.now(),
        cuenta=cuenta_up,
        metodo=metodo_up,
        cantidad=cantidad,
        cantidad_real=cantidad_real,
        semestre=semestre_up,
        categoria=categoria_up,
        razon=razon_up,
        autorizo=autorizo_up,
        responsable=responsable_up,
    )

    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    return RedirectResponse(url="/egresos", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/egresos")
def view_egresos(request: Request, db: Session = Depends(get_db)):
    registros = db.query(Egreso).order_by(Egreso.fecha.desc()).all()
    return templates.TemplateResponse(
        "egresos.html",
        {"request": request, "registros": registros},
    )


@app.get("/egresos/export.csv")
def export_egresos_csv(db: Session = Depends(get_db)):
    rows = db.query(Egreso).order_by(Egreso.fecha.asc()).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["FECHA", "CUENTA", "MÉTODO", "CANTIDAD", "CANTIDAD REAL",
                "SEMESTRE", "CATEGORIA", "RAZÓN", "AUTORIZÓ", "RESPONSABLE"])
    for r in rows:
        fecha_txt = r.fecha.strftime("%d/%m/%Y %H:%M:%S") if r.fecha else ""
        w.writerow([
            fecha_txt,
            r.cuenta,
            r.metodo,
            f"{r.cantidad:.2f}",
            f"{r.cantidad_real:.2f}",
            r.semestre,
            r.categoria,
            r.razon,
            r.autorizo,
            r.responsable,
        ])

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="egresos.csv"'},
    )


@app.get("/egresos/export.xlsx")
def export_egresos_xlsx(db: Session = Depends(get_db)):
    try:
        from openpyxl import Workbook
    except Exception:
        return JSONResponse(
            {"error": "openpyxl no está instalado. Usa /egresos/export.csv o agrega openpyxl a requirements.txt"},
            status_code=501,
        )
    rows = db.query(Egreso).order_by(Egreso.fecha.asc()).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "EGRESOS"
    ws.append(["FECHA", "CUENTA", "MÉTODO", "CANTIDAD", "CANTIDAD REAL",
               "SEMESTRE", "CATEGORIA", "RAZÓN", "AUTORIZÓ", "RESPONSABLE"])
    for r in rows:
        fecha_txt = r.fecha.strftime("%d/%m/%Y %H:%M:%S") if r.fecha else ""
        ws.append([
            fecha_txt,
            r.cuenta,
            r.metodo,
            float(r.cantidad or 0),
            float(r.cantidad_real or 0),
            r.semestre,
            r.categoria,
            r.razon,
            r.autorizo,
            r.responsable,
        ])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="egresos.xlsx"'},
    )


# ===================== RESÚMENES (básicos) =====================

@app.get("/resumen_ingresos")
def resumen_ingresos(request: Request, db: Session = Depends(get_db)):
    # Suma por (cuenta, semestre)
    data = (
        db.query(Ingreso.banco, Ingreso.semestre, func.coalesce(func.sum(Ingreso.cantidad), 0))
        .group_by(Ingreso.banco, Ingreso.semestre)
        .all()
    )
    # Reorganiza a dict {cuenta: {semestre: total}}
    pivot: dict[str, dict[str, Decimal]] = {}
    total_por_cuenta: dict[str, Decimal] = {}
    total_por_semestre: dict[str, Decimal] = {}

    for banco, semestre, suma in data:
        pivot.setdefault(banco, {})
        pivot[banco][semestre] = Decimal(suma or 0).quantize(Decimal("0.01"))

        total_por_cuenta[banco] = total_por_cuenta.get(banco, Decimal("0")) + Decimal(suma or 0)
        total_por_semestre[semestre] = total_por_semestre.get(semestre, Decimal("0")) + Decimal(suma or 0)

    # Orden sugerido de semestres
    semestres = ["126", "226", "326", "426", "526", "GENERAL"]
    return templates.TemplateResponse(
        "resumen_ingresos.html",
        {
            "request": request,
            "pivot": pivot,
            "semestres": semestres,
            "total_por_cuenta": total_por_cuenta,
            "total_por_semestre": total_por_semestre,
        },
    )


@app.get("/resumen_egresos")
def resumen_egresos(request: Request, db: Session = Depends(get_db)):
    # Suma por (cuenta, semestre) usando cantidad_real (como acordamos)
    data = (
        db.query(Egreso.cuenta, Egreso.semestre, func.coalesce(func.sum(Egreso.cantidad_real), 0))
        .group_by(Egreso.cuenta, Egreso.semestre)
        .all()
    )
    pivot: dict[str, dict[str, Decimal]] = {}
    total_por_cuenta: dict[str, Decimal] = {}
    total_por_semestre: dict[str, Decimal] = {}

    for cuenta, semestre, suma in data:
        pivot.setdefault(cuenta, {})
        pivot[cuenta][semestre] = Decimal(suma or 0).quantize(Decimal("0.01"))

        total_por_cuenta[cuenta] = total_por_cuenta.get(cuenta, Decimal("0")) + Decimal(suma or 0)
        total_por_semestre[semestre] = total_por_semestre.get(semestre, Decimal("0")) + Decimal(suma or 0)

    semestres = ["126", "226", "326", "426", "526"]
    return templates.TemplateResponse(
        "resumen_egresos.html",
        {
            "request": request,
            "pivot": pivot,
            "semestres": semestres,
            "total_por_cuenta": total_por_cuenta,
            "total_por_semestre": total_por_semestre,
        },
    )


# ===================== Endpoint de diagnóstico =====================

@app.get("/__debug/db")
def debug_db(db: Session = Depends(get_db)):
    ingresos = db.query(Ingreso).count()
    egresos = db.query(Egreso).count()

    # Oculta password del engine.url para no filtrar credenciales en logs
    url = engine.url
    safe_url = str(url)
    if url.password:
        safe_url = safe_url.replace(url.password, "*****")

    return JSONResponse({"engine": safe_url, "ingresos": ingresos, "egresos": egresos})
