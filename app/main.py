from __future__ import annotations
from fastapi import FastAPI, Depends, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from typing import Optional
from decimal import Decimal
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import io, csv

# ==== BD ====
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from .models import Ingreso, Egreso

# Rutas correctas a /app
BASE_DIR      = Path(__file__).resolve().parent              # app/
TEMPLATES_DIR = str(BASE_DIR / "templates")                  # app/templates
STATIC_DIR    = str(BASE_DIR / "static")                     # app/static

app = FastAPI(title="Proyecto_Finanzas_TT", version="0.3.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# estáticos y jinja
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# ===== Helpers tiempo/formato =====
TZ = ZoneInfo("America/Bogota")
def now_bogota() -> datetime: return datetime.now(TZ)
def fmt_dt(dt: datetime) -> str: return dt.astimezone(TZ).strftime("%d/%m/%Y %H:%M:%S")
def two_dec(v: Decimal) -> Decimal: return v.quantize(Decimal("0.01"))

# Crear tablas (checkfirst)
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

# ====== PÁGINAS (Jinja) ======
@app.get("/")
def home(request: Request):                return templates.TemplateResponse("index.html", {"request": request})
@app.get("/ingresos/nuevo")
def form_ingreso(request: Request):        return templates.TemplateResponse("ingresos_form.html", {"request": request})
@app.get("/ingresos")
def ingresos_tabla(request: Request):      return templates.TemplateResponse("ingresos.html", {"request": request})
@app.get("/ingresos/resumen")
def ingresos_resumen(request: Request):    return templates.TemplateResponse("resumen_ingresos.html", {"request": request})
@app.get("/egresos/nuevo")
def form_egreso(request: Request):         return templates.TemplateResponse("egresos_form.html", {"request": request})
@app.get("/egresos")
def egresos_tabla(request: Request):       return templates.TemplateResponse("egresos.html", {"request": request})
@app.get("/egresos/resumen")
def egresos_resumen(request: Request):     return templates.TemplateResponse("resumen_egresos.html", {"request": request})

# ========= API INGRESOS =========
@app.post("/api/ingresos")
def api_crear_ingreso(payload: dict, db: Session = Depends(get_db)):
    # payload: monto, semestre, cuenta, detalle, wompi_mp?, linea?, user?
    monto_raw = str(payload.get("monto", "0")).replace(".", "").replace("$", "").replace(",", ".").strip()
    monto = Decimal(monto_raw or "0")

    semestre = (payload.get("semestre") or "").upper()
    banco    = (payload.get("cuenta") or "").upper()
    metodo   = (payload.get("detalle") or "").upper()
    wompi_mp = (payload.get("wompi_mp") or "").upper()

    linea = (payload.get("linea") or "PENDIENTE").upper()
    user  = (payload.get("user")  or "PENDIENTE").upper()

    cantidad = monto
    if metodo == "WOMPI" and wompi_mp in ("PSE", "TC"):
        comision_base = monto * Decimal("0.0265") + Decimal("700")
        iva = comision_base * Decimal("0.19")
        descuento = comision_base + iva
        if wompi_mp == "TC":
            descuento += monto * Decimal("0.015")
        cantidad = monto - descuento

    if metodo == "PAGO INTERESES":
        semestre, linea, user = "GENERAL", "GENERAL", "INTERESES"

    ing = Ingreso(
        fecha=now_bogota(),
        cantidad=two_dec(cantidad),
        semestre=semestre, banco=banco, metodo=metodo,
        linea=linea, user=user, extra="-",
    )
    db.add(ing); db.commit(); db.refresh(ing)
    return {"ok": True, "row": {
        "FECHA": fmt_dt(ing.fecha), "CANTIDAD": float(ing.cantidad),
        "SEMESTRE": ing.semestre, "BANCO": ing.banco, "METODO": ing.metodo,
        "LÍNEA": ing.linea, "USER": ing.user, "EXTRA": ing.extra
    }}

@app.get("/api/ingresos")
def api_list_ingresos(
    semestre: Optional[str] = None,
    banco: Optional[str] = None,
    metodo: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Ingreso).order_by(Ingreso.fecha.desc())
    if semestre: q = q.filter(Ingreso.semestre == semestre.upper())
    if banco:    q = q.filter(Ingreso.banco == banco.upper())
    if metodo:   q = q.filter(Ingreso.metodo == metodo.upper())

    rows = [{
        "FECHA": fmt_dt(x.fecha), "CANTIDAD": float(x.cantidad),
        "SEMESTRE": x.semestre, "BANCO": x.banco, "METODO": x.metodo,
        "LÍNEA": x.linea, "USER": x.user, "EXTRA": x.extra
    } for x in q.all()]
    return {"rows": rows}

@app.get("/api/ingresos/export.csv")
def export_ingresos_csv(db: Session = Depends(get_db)):
    q = db.query(Ingreso).order_by(Ingreso.fecha.desc()).all()
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["FECHA","CANTIDAD","SEMESTRE","BANCO","MÉTODO","LÍNEA","USER","EXTRA"])
    for x in q:
        w.writerow([fmt_dt(x.fecha), f"{x.cantidad:.2f}", x.semestre, x.banco, x.metodo, x.linea, x.user, x.extra])
    out.seek(0)
    return StreamingResponse(out, media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="ingresos.csv"'}
    )

@app.get("/api/ingresos/export.xlsx")
def export_ingresos_xlsx(db: Session = Depends(get_db)):
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active; ws.title = "INGRESOS"
    ws.append(["FECHA","CANTIDAD","SEMESTRE","BANCO","MÉTODO","LÍNEA","USER","EXTRA"])
    for x in db.query(Ingreso).order_by(Ingreso.fecha.desc()).all():
        ws.append([fmt_dt(x.fecha), float(x.cantidad), x.semestre, x.banco, x.metodo, x.linea, x.user, x.extra])
    bio = io.BytesIO(); wb.save(bio); bio.seek(0)
    return StreamingResponse(bio,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="ingresos.xlsx"'}
    )

# ========= API EGRESOS =========
@app.post("/api/egresos")
def api_crear_egreso(payload: dict, db: Session = Depends(get_db)):
    monto_raw = str(payload.get("monto", "0")).replace(".", "").replace("$", "").replace(",", ".").strip()
    monto = Decimal(monto_raw or "0")

    cuenta    = (payload.get("cuenta") or "").upper()
    metodo    = (payload.get("metodo") or "").upper()
    semestre  = (payload.get("semestre") or "").upper()
    categoria = (payload.get("categoria") or "").upper()

    mes          = (payload.get("mes") or "").upper()
    razon_val    = (payload.get("razon") or "").upper()
    nombre_carro = (payload.get("nombre_carro") or "").upper()
    motivo_carro = (payload.get("motivo_carro") or "").upper()

    autorizo    = (payload.get("autorizo") or "").upper()
    responsable = (payload.get("responsable") or "").upper()

    # 4x1000 salvo EFECTIVO/EFECTY
    cantidad_real = monto if cuenta in ("EFECTIVO", "EFECTY") else (monto * Decimal("1.004"))

    # RAZÓN con reglas
    if categoria == "CARROS":
        razon_final = f"{nombre_carro}_{motivo_carro}_{razon_val}".strip("_")
    elif categoria == "SEGURIDAD_SOCIAL":
        razon_final = f"SS_{mes}_2026"
    elif categoria in {"ADELANTO","ITAU-APTOS","MERCADO","PAGO_NÓMINA","VIATICOS","IMPUESTOS","PRIMAS"}:
        razon_final = f"{razon_val}_{mes}" if mes else razon_val
    elif categoria == "CESANTIAS":
        razon_final = "2025"
    else:
        razon_final = razon_val

    eg = Egreso(
        fecha=now_bogota(),
        cuenta=cuenta, metodo=metodo,
        cantidad=two_dec(monto), cantidad_real=two_dec(cantidad_real),
        semestre=semestre, categoria=categoria, razon=razon_final,
        autorizo=autorizo, responsable=responsable
    )
    db.add(eg); db.commit(); db.refresh(eg)

    return {"ok": True, "row": {
        "FECHA": fmt_dt(eg.fecha), "CUENTA": eg.cuenta, "MÉTODO": eg.metodo,
        "CANTIDAD": float(eg.cantidad), "CANTIDAD_REAL": float(eg.cantidad_real),
        "SEMESTRE": eg.semestre, "CATEGORIA": eg.categoria, "RAZÓN": eg.razon,
        "AUTORIZÓ": eg.autorizo, "RESPONSABLE": eg.responsable
    }}

@app.get("/api/egresos")
def api_list_egresos(
    semestre: Optional[str] = None,
    cuenta: Optional[str] = None,
    categoria: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Egreso).order_by(Egreso.fecha.desc())
    if semestre:  q = q.filter(Egreso.semestre == semestre.upper())
    if cuenta:    q = q.filter(Egreso.cuenta == cuenta.upper())
    if categoria: q = q.filter(Egreso.categoria == categoria.upper())

    rows = [{
        "FECHA": fmt_dt(x.fecha), "CUENTA": x.cuenta, "MÉTODO": x.metodo,
        "CANTIDAD": float(x.cantidad), "CANTIDAD_REAL": float(x.cantidad_real),
        "SEMESTRE": x.semestre, "CATEGORIA": x.categoria, "RAZÓN": x.razon,
        "AUTORIZÓ": x.autorizo, "RESPONSABLE": x.responsable
    } for x in q.all()]
    return {"rows": rows}

@app.get("/api/egresos/export.csv")
def export_egresos_csv(db: Session = Depends(get_db)):
    q = db.query(Egreso).order_by(Egreso.fecha.desc()).all()
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["FECHA","CUENTA","MÉTODO","CANTIDAD","CANTIDAD_REAL","SEMESTRE","CATEGORÍA","RAZÓN","AUTORIZÓ","RESPONSABLE"])
    for x in q:
        w.writerow([fmt_dt(x.fecha), x.cuenta, x.metodo, f"{x.cantidad:.2f}", f"{x.cantidad_real:.2f}",
                    x.semestre, x.categoria, x.razon, x.autorizo, x.responsable])
    out.seek(0)
    return StreamingResponse(out, media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="egresos.csv"'}
    )

@app.get("/api/egresos/export.xlsx")
def export_egresos_xlsx(db: Session = Depends(get_db)):
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active; ws.title = "EGRESOS"
    ws.append(["FECHA","CUENTA","MÉTODO","CANTIDAD","CANTIDAD_REAL","SEMESTRE","CATEGORÍA","RAZÓN","AUTORIZÓ","RESPONSABLE"])
    for x in db.query(Egreso).order_by(Egreso.fecha.desc()).all():
        ws.append([fmt_dt(x.fecha), x.cuenta, x.metodo, float(x.cantidad), float(x.cantidad_real),
                   x.semestre, x.categoria, x.razon, x.autorizo, x.responsable])
    bio = io.BytesIO(); wb.save(bio); bio.seek(0)
    return StreamingResponse(bio,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename=\"egresos.xlsx\"'}
    )
