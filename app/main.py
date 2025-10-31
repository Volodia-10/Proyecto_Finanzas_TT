
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo
from datetime import datetime
import re, io, csv, unicodedata

app = FastAPI(title="Proyecto_Finanzas_TT", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# ---- In-memory DB ----
INGRESOS: List[Dict[str, Any]] = []
EGRESOS: List[Dict[str, Any]] = []

TZ = ZoneInfo("America/Bogota")
COP_TWO = Decimal("0.01")

def to_decimal_2(value: Decimal) -> Decimal:
    return value.quantize(COP_TWO, rounding=ROUND_HALF_UP)

def calcular_neto_wompi(monto: Decimal, wompi_metodo: Optional[str]) -> Decimal:
    comision_base = (monto * Decimal("0.0265")) + Decimal("700")
    iva = comision_base * Decimal("0.19")
    descuento = comision_base + iva
    if wompi_metodo == "TC":
        descuento += monto * Decimal("0.015")
    neto = monto - descuento
    return to_decimal_2(neto)

def now_formatted() -> str:
    dt = datetime.now(TZ)
    return dt.strftime("%d/%m/%Y %H:%M:%S")

def normalize_upper(s: Optional[str]) -> Optional[str]:
    if s is None:
        return s
    return s.upper()

def strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def parse_monto_str_to_decimal(monto_str: str) -> Decimal:
    clean = re.sub(r"[^0-9,]", "", monto_str)
    clean_dot = clean.replace(",", ".")
    dec = Decimal(clean_dot)
    return to_decimal_2(dec)

# ---------- MODELS (INGRESOS) ----------
class IngresoIn(BaseModel):
    monto: str = Field(...)
    semestre: str
    cuenta: str
    detalle: str
    wompi_metodo: Optional[str] = None
    incluir_linea_usuario: bool = False
    linea: Optional[str] = None
    usuario: Optional[str] = None

    @validator("monto")
    def validate_monto(cls, v):
        if not isinstance(v, str):
            raise ValueError("monto debe ser string formateado")
        clean = re.sub(r"[^0-9,]", "", v)
        if clean.count(",") > 1:
            raise ValueError("Formato de monto inválido")
        clean_dot = clean.replace(",", ".")
        try:
            dec = Decimal(clean_dot)
        except Exception:
            raise ValueError("Monto inválido")
        if dec <= 0:
            raise ValueError("Monto debe ser positivo")
        return v

class Ingreso(BaseModel):
    fecha: str
    cantidad: str
    semestre: str
    banco: str
    metodo: str
    linea: str
    user: str
    extra: str

# ---------- MODELS (EGRESOS) ----------
CATS_REQUIEREN_MES = {
    "ADELANTO","ITAÚ-APTOS","MERCADO","PAGO_NÓMINA","VIATICOS","IMPUESTOS","SEGURIDAD_SOCIAL","PRIMAS"
}
CARROS_MOTIVOS = {"MANTENIMIENTO","SOAT","IMPUESTOS","TODO-RIESGO","TECNICOMECANICO"}
CARROS_NOMBRES = {"VERSA","MAZDA","QASHQAI"}

class EgresoIn(BaseModel):
    monto: str
    cuenta: str
    metodo: str
    semestre: str
    categoria: str
    mes: Optional[str] = None
    nombre_carro: Optional[str] = None
    motivo_carro: Optional[str] = None
    razon: Optional[str] = None
    autorizo: str
    responsable: str

    @validator("monto")
    def validate_monto(cls, v):
        if not isinstance(v, str):
            raise ValueError("monto debe ser string formateado")
        clean = re.sub(r"[^0-9,]", "", v)
        if clean.count(",") > 1:
            raise ValueError("Formato de monto inválido")
        clean_dot = clean.replace(",", ".")
        try:
            dec = Decimal(clean_dot)
        except Exception:
            raise ValueError("Monto inválido")
        if dec <= 0:
            raise ValueError("Monto debe ser positivo")
        return v

class Egreso(BaseModel):
    fecha: str
    cuenta: str
    metodo: str
    cantidad: str
    cantidad_real: str
    semestre: str
    categoria: str
    razon: str
    autorizo: str
    responsable: str

@app.get("/")
def index():
    return FileResponse("static/index.html")

# ---------- INGRESOS ROUTES ----------
@app.get("/ingresos/nuevo")
def ingresos_nuevo():
    return FileResponse("static/ingresos_nuevo.html")

@app.get("/ingresos")
def ingresos_tabla():
    return FileResponse("static/ingresos.html")

@app.get("/ingresos/resumen")
def ingresos_resumen():
    return FileResponse("static/resumen_ingresos.html")

@app.get("/api/ingresos")
def api_list_ingresos():
    def parse_fecha(fecha: str):
        return datetime.strptime(fecha, "%d/%m/%Y %H:%M:%S")
    ordered = sorted(INGRESOS, key=lambda x: parse_fecha(x["fecha"]), reverse=True)
    return JSONResponse(content=ordered)

@app.post("/api/ingresos")
def api_create_ingreso(data: IngresoIn):
    semestre = normalize_upper(data.semestre.strip())
    cuenta = normalize_upper(data.cuenta.strip())
    detalle = normalize_upper(data.detalle.strip())
    wompi_metodo = normalize_upper(data.wompi_metodo) if data.wompi_metodo else None
    incluir_lu = bool(data.incluir_linea_usuario)

    monto = parse_monto_str_to_decimal(data.monto)

    linea_final = None
    usuario_final = None
    semestre_final = semestre

    if detalle == "PAGO INTERESES":
        semestre_final = "GENERAL"
        linea_final = "GENERAL"
        usuario_final = "INTERESES"
    else:
        if incluir_lu:
            if not data.linea or not data.usuario:
                raise HTTPException(status_code=422, detail="LÍNEA y USUARIO son obligatorios cuando se marca la casilla.")
            linea_final = normalize_upper(data.linea.strip())
            usuario_final = normalize_upper(data.usuario.strip())
        else:
            linea_final = "PENDIENTE"
            usuario_final = "PENDIENTE"

    if (cuenta.startswith("BANCOLOMBIA_")) and (detalle == "WOMPI"):
        if wompi_metodo not in ("PSE", "TC"):
            raise HTTPException(status_code=422, detail="MÉTODO DE PAGO (WOMPI) es obligatorio (PSE o TC).")
        neto = calcular_neto_wompi(monto, wompi_metodo)
        metodo_tabla = "WOMPI"
    else:
        neto = to_decimal_2(monto)
        metodo_tabla = detalle

    fecha = now_formatted()
    reg = Ingreso(
        fecha=fecha,
        cantidad=f"{neto:.2f}".replace(".", ","),
        semestre=semestre_final,
        banco=cuenta,
        metodo=metodo_tabla,
        linea=linea_final,
        user=usuario_final,
        extra="-",
    ).dict()

    INGRESOS.append(reg)
    return {"ok": True, "message": "INGRESO REGISTRADO CON ÉXITO"}

# ---------- EGRESOS ROUTES ----------
@app.get("/egresos/nuevo")
def egresos_nuevo():
    return FileResponse("static/egresos_nuevo.html")

@app.get("/egresos")
def egresos_tabla():
    return FileResponse("static/egresos.html")

@app.get("/egresos/resumen")
def egresos_resumen():
    return FileResponse("static/resumen_egresos.html")

@app.get("/api/egresos")
def api_list_egresos():
    def parse_fecha(fecha: str):
        return datetime.strptime(fecha, "%d/%m/%Y %H:%M:%S")
    ordered = sorted(EGRESOS, key=lambda x: parse_fecha(x["fecha"]), reverse=True)
    return JSONResponse(content=ordered)

@app.post("/api/egresos")
def api_create_egreso(data: EgresoIn):
    cuenta = normalize_upper(data.cuenta.strip())
    metodo = normalize_upper(data.metodo.strip())
    semestre = normalize_upper(data.semestre.strip())
    categoria = normalize_upper(data.categoria.strip())

    mes = normalize_upper(data.mes) if data.mes else None
    nombre_carro = normalize_upper(data.nombre_carro) if data.nombre_carro else None
    motivo_carro = normalize_upper(data.motivo_carro) if data.motivo_carro else None
    razon = normalize_upper(data.razon) if data.razon else None
    autorizo = normalize_upper(data.autorizo.strip())
    responsable = normalize_upper(data.responsable.strip())

    monto = parse_monto_str_to_decimal(data.monto)

    if categoria in CATS_REQUIEREN_MES and not mes:
        raise HTTPException(status_code=422, detail="MES es obligatorio para esta categoría.")
    if categoria == "CARROS":
        if (nombre_carro not in CARROS_NOMBRES) or (motivo_carro not in CARROS_MOTIVOS):
            raise HTTPException(status_code=422, detail="NOMBRE CARRO y MOTIVO son obligatorios y válidos.")
        if not razon:
            raise HTTPException(status_code=422, detail="RAZÓN es obligatoria para CARROS.")
    if categoria in {"ADELANTO","PAGO_NÓMINA","VIATICOS","PRIMAS","BASE DE DATOS","ITAÚ-APTOS","MERCADO","SOFTWARE","IMPUESTOS","DEVOLUCIÓN"}:
        if not razon:
            raise HTTPException(status_code=422, detail="RAZÓN es obligatoria para esta categoría.")

    if categoria == "SEGURIDAD_SOCIAL":
        razon_final = f"SS_{mes}_2026"
    elif categoria == "CARROS":
        razon_final = f"{nombre_carro}_{motivo_carro}_{razon}"
    elif categoria == "CESANTIAS":
        razon_final = "2025"
    elif categoria in CATS_REQUIEREN_MES:
        razon_final = f"{razon}_{mes}"
    else:
        razon_final = razon or "-"

    cantidad = to_decimal_2(monto)
    if cuenta == "EFECTY":
        cantidad_real = cantidad
    else:
        cantidad_real = to_decimal_2(monto * Decimal("1.004"))

    fecha = now_formatted()
    reg = Egreso(
        fecha=fecha,
        cuenta=cuenta,
        metodo=metodo,
        cantidad=f"{cantidad:.2f}".replace(".", ","),
        cantidad_real=f"{cantidad_real:.2f}".replace(".", ","),
        semestre=semestre,
        categoria=categoria,
        razon=razon_final,
        autorizo=autorizo,
        responsable=responsable,
    ).dict()
    EGRESOS.append(reg)
    return {"ok": True, "message": "EGRESO REGISTRADO CON ÉXITO"}

# ---------- EXPORT HELPERS ----------
def apply_filters(rows: List[Dict[str,str]], filters: Dict[int,str], columns: List[str]) -> List[Dict[str,str]]:
    if not filters:
        return rows
    res = []
    for r in rows:
        ok = True
        for idx, fval in filters.items():
            if fval is None or fval == "":
                continue
            col = columns[idx]
            cell = str(r.get(col, ""))
            if strip_accents(fval.lower()) not in strip_accents(cell.lower()):
                ok = False
                break
        if ok:
            res.append(r)
    return res

def export_csv(rows: List[Dict[str, str]], headers: List[str]) -> StreamingResponse:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows:
        w.writerow([r.get(h, "") for h in headers])
    buf.seek(0)
    return StreamingResponse(iter([buf.read()]), media_type="text/csv")

def export_xlsx(rows: List[Dict[str, str]], headers: List[str], filename: str) -> StreamingResponse:
    try:
        import openpyxl
        from openpyxl.workbook import Workbook
    except Exception:
        return export_csv(rows, headers)
    wb = Workbook()
    ws = wb.active
    ws.title = "DATA"
    ws.append(headers)
    for r in rows:
        ws.append([r.get(h, "") for h in headers])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={
        "Content-Disposition": f'attachment; filename="{filename}"'
    })

@app.get("/api/egresos/export")
def export_egresos(fmt: str = Query("csv"),
                   f0: Optional[str] = None, f1: Optional[str] = None, f2: Optional[str] = None,
                   f3: Optional[str] = None, f4: Optional[str] = None, f5: Optional[str] = None,
                   f6: Optional[str] = None, f7: Optional[str] = None, f8: Optional[str] = None,
                   f9: Optional[str] = None):
    headers = ["FECHA","CUENTA","MÉTODO","CANTIDAD","CANTIDAD REAL","SEMESTRE","CATEGORÍA","RAZÓN","AUTORIZÓ","RESPONSABLE"]
    rows = [{
        "FECHA": r["fecha"],
        "CUENTA": r["cuenta"],
        "MÉTODO": r["metodo"],
        "CANTIDAD": r["cantidad"],
        "CANTIDAD REAL": r["cantidad_real"],
        "SEMESTRE": r["semestre"],
        "CATEGORÍA": r["categoria"],
        "RAZÓN": r["razon"],
        "AUTORIZÓ": r["autorizo"],
        "RESPONSABLE": r["responsable"],
    } for r in EGRESOS]
    filters = {i: v for i, v in enumerate([f0,f1,f2,f3,f4,f5,f6,f7,f8,f9]) if v}
    rows = apply_filters(rows, filters, headers)
    filename = f"EGRESOS_export.xlsx"
    if fmt.lower() == "xlsx":
        return export_xlsx(rows, headers, filename)
    return export_csv(rows, headers)

@app.get("/api/ingresos/export2")
def export_ingresos2(fmt: str = Query("csv"),
                     f0: Optional[str] = None, f1: Optional[str] = None, f2: Optional[str] = None,
                     f3: Optional[str] = None, f4: Optional[str] = None, f5: Optional[str] = None,
                     f6: Optional[str] = None, f7: Optional[str] = None):
    headers = ["FECHA","CANTIDAD","SEMESTRE","BANCO","MÉTODO","LÍNEA","USER","EXTRA"]
    rows = [{ 
        "FECHA": r["fecha"],
        "CANTIDAD": r["cantidad"],
        "SEMESTRE": r["semestre"],
        "BANCO": r["banco"],
        "MÉTODO": r["metodo"],
        "LÍNEA": r["linea"],
        "USER": r["user"],
        "EXTRA": r.get("extra","")
    } for r in INGRESOS]
    filters = {i: v for i, v in enumerate([f0,f1,f2,f3,f4,f5,f6,f7]) if v}
    rows = apply_filters(rows, filters, headers)
    filename = f"INGRESOS_export.xlsx"
    if fmt.lower() == "xlsx":
        return export_xlsx(rows, headers, filename)
    return export_csv(rows, headers)
