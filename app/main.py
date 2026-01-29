from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo
from datetime import datetime
from pathlib import Path
import io, csv, re, unicodedata

HERE = Path(__file__).parent
app = FastAPI(title="Proyecto_Finanzas_TT", version="0.3.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")
templates = Jinja2Templates(directory=str(HERE / "templates"))

# ------------------ In-memory ------------------
INGRESOS: List[Dict[str, Any]] = []
EGRESOS: List[Dict[str, Any]] = []
TRANSFERENCIAS: List[Dict[str, Any]] = []

TZ = ZoneInfo("America/Bogota")
COP_TWO = Decimal("0.01")

SEMESTRES = ["126","226","326","426","526"]
CUENTAS   = ["NEQUI","BANCOLOMBIA_2807","BANCOLOMBIA_1423","DAVIVIENDA","EFECTY"]
DETALLE_BY_CUENTA = {
    "BANCOLOMBIA_1423": ["BANCOLOMBIA","WOMPI","NEQUI","CORRESPONSAL","PAGO INTERESES"],
    "BANCOLOMBIA_2807": ["BANCOLOMBIA","WOMPI","NEQUI","CORRESPONSAL","PAGO INTERESES"],
    "NEQUI": ["NEQUI","NEQUI TRANSFIYA","RECARGA BANCOLOMBIA","RECARGA PSE","RECARGA CORRESPONSAL","PAGO INTERESES","REVERSIÓN PAGO","OTROS BANCOS"],
    "DAVIVIENDA": ["DAVIVIENDA","DAVIPLATA","CORRESPONSAL","PAGO INTERESES"],
    "EFECTY": ["GIRO NACIONAL"]
}
# Métodos sugeridos para EGRESOS por cuenta
EGRESO_METODOS = {
    "NEQUI": ["NEQUI","NEQUI TRANSFIYA","RECARGA BANCOLOMBIA","RECARGA CORRESPONSAL","OTRO"],
    "DAVIVIENDA": ["DAVIVIENDA","DAVIPLATA","CORRESPONSAL","PSE","OTRO"],
    "EFECTY": ["GIRO NACIONAL"],
    "_BANC_": ["TRANSFERENCIA","CORRESPONSAL","PSE","WOMPI","OTRO"],  # para BANCOLOMBIA_*
}

LINEAS = ["L1","L2","L3","L4","L5","L6","L7"]
EMPLEADOS = ["DIANA GOMEZ","BRAYAN PRIMICIERO","ANDREA GELVES","HERNAN DIAZ","DAVID CORDON","JULIANA RIVERA","ASTRID RODRIGUEZ","ALEXIS GOMEZ","ANGELA FERNANDEZ","IVAN MONSALVE","JHOSEP CABRERA","JUANCARLO HIDALGO","FAYBER SALAMANCA","JAVIER MATIZ","CAROLINA MACIAS","KARIME GOMEZ","LADY JAIMES","JOHAN SUAREZ","FELIPE TORRES","JESUS TORRES","MARLON JOYA","ZULAY RODRIGUEZ","STELLA CORZO","LILIANA BARRERA","NATALIA JOYA","MARTHA RAMIREZ","LADY GOMEZ","AMPARO IZAQUITA","MAIRA SANDOVAL","MADELEYNE CORZO","CINTHIA CIFUENTES","DANIELA RIAÑO","PAOLA CACERES","MONICA GUARIN","NICOLLE LEÓN"]
MESES = ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"]
CATS = ["DEVOLUCIÓN","ADELANTO","CARROS","BASE DE DATOS","FAMILIA","FUTBOL_TT","INVENTARIO","INVERSIONES","ITAÚ-APTOS","MERCADO","OCIO","PAGO_NÓMINA","SOFTWARE","VIAJES","VIATICOS","IMPUESTOS","SEGURIDAD_SOCIAL","PRIMAS","CESANTIAS"]
CATS_REQUIEREN_MES = {"ADELANTO","ITAÚ-APTOS","MERCADO","PAGO_NÓMINA","VIATICOS","IMPUESTOS","SEGURIDAD_SOCIAL","PRIMAS"}
CARROS_MOTIVOS = {"MANTENIMIENTO","SOAT","IMPUESTOS","TODO-RIESGO","TECNICOMECANICO"}
CARROS_NOMBRES = {"VERSA","MAZDA","QASHQAI"}

# ------------------ Utils ------------------
def to_decimal_2(x: Decimal) -> Decimal:
    return x.quantize(COP_TWO, rounding=ROUND_HALF_UP)

def now_str() -> str:
    return datetime.now(TZ).strftime("%d/%m/%Y %H:%M:%S")

def normalize_upper(s: Optional[str]) -> Optional[str]:
    if s is None: return s
    return s.upper()

def parse_monto_str_to_decimal(monto_str: str) -> Decimal:
    clean = re.sub(r"[^0-9,]", "", monto_str)
    clean_dot = clean.replace(",", ".")
    dec = Decimal(clean_dot)
    return to_decimal_2(dec)

def calcular_neto_wompi(monto: Decimal, wompi_metodo: Optional[str]) -> Decimal:
    comision_base = (monto * Decimal("0.0265")) + Decimal("700")
    iva = comision_base * Decimal("0.19")
    descuento = comision_base + iva
    if wompi_metodo == "TC":
        descuento += monto * Decimal("0.015")
    return to_decimal_2(monto - descuento)

def export_csv(rows: List[Dict[str, str]], headers: List[str]) -> StreamingResponse:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows: w.writerow([r.get(h, "") for h in headers])
    buf.seek(0)
    return StreamingResponse(iter([buf.read()]), media_type="text/csv")

def export_xlsx(rows: List[Dict[str, str]], headers: List[str], filename: str) -> StreamingResponse:
    try:
        from openpyxl.workbook import Workbook
    except Exception:
        return export_csv(rows, headers)
    wb = Workbook(); ws = wb.active; ws.title = "DATA"
    ws.append(headers)
    for r in rows: ws.append([r.get(h, "") for h in headers])
    stream = io.BytesIO(); wb.save(stream); stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})

# ------------------ Models ------------------
class IngresoIn(BaseModel):
    monto: str
    semestre: str
    cuenta: str
    detalle: str
    wompi_metodo: Optional[str] = None
    incluir_linea_usuario: bool = False
    linea: Optional[str] = None
    usuario: Optional[str] = None

    @validator("monto")
    def v_monto(cls, v):
        clean = re.sub(r"[^0-9,]", "", v or "")
        if not clean: raise ValueError("Monto requerido")
        Decimal(clean.replace(",", "."))
        return v

class Ingreso(BaseModel):
    fecha: str; cantidad: str; semestre: str; banco: str; metodo: str; linea: str; user: str; extra: str

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
    def v_monto(cls, v):
        clean = re.sub(r"[^0-9,]", "", v or "")
        if not clean: raise ValueError("Monto requerido")
        Decimal(clean.replace(",", "."))
        return v

class Egreso(BaseModel):
    fecha: str; cuenta: str; metodo: str; cantidad: str; cantidad_real: str
    semestre: str; categoria: str; razon: str; autorizo: str; responsable: str

class TransferIn(BaseModel):
    monto: str; semestre: str; origen: str; destino: str; costo: Optional[str] = None

class Transfer(BaseModel):
    fecha: str; monto: str; semestre: str; origen: str; destino: str; costo: str

# ------------------ Views ------------------
@app.get("/")
def home(request: Request): return templates.TemplateResponse("index.html", {"request": request})

@app.get("/ingresos/nuevo")
def v_in_nuevo(request: Request): return templates.TemplateResponse("ingresos_form.html", {"request": request})

@app.get("/ingresos")
def v_in_tabla(request: Request): return templates.TemplateResponse("ingresos.html", {"request": request})

@app.get("/ingresos/resumen")
def v_in_resumen(request: Request): return templates.TemplateResponse("resumen_ingresos.html", {"request": request})

@app.get("/egresos/nuevo")
def v_eg_nuevo(request: Request): return templates.TemplateResponse("egresos_form.html", {"request": request})

@app.get("/egresos")
def v_eg_tabla(request: Request): return templates.TemplateResponse("egresos.html", {"request": request})

@app.get("/egresos/resumen")
def v_eg_resumen(request: Request): return templates.TemplateResponse("resumen_egresos.html", {"request": request})

@app.get("/transferencias/nuevo")
def v_tr_nuevo(request: Request): return templates.TemplateResponse("transferencias_nuevo.html", {"request": request})

@app.get("/transferencias")
def v_tr_hist(request: Request): return templates.TemplateResponse("transferencias.html", {"request": request})

@app.get("/saldos")
def v_saldos(request: Request): return templates.TemplateResponse("saldos.html", {"request": request})

# ------------------ API Ingresos ------------------
@app.get("/api/ingresos")
def api_ing_list():
    def pf(x): return datetime.strptime(x["fecha"], "%d/%m/%Y %H:%M:%S")
    return sorted(INGRESOS, key=pf, reverse=True)

@app.post("/api/ingresos")
def api_ing_create(data: IngresoIn):
    semestre = normalize_upper(data.semestre.strip())
    cuenta = normalize_upper(data.cuenta.strip())
    detalle = normalize_upper(data.detalle.strip())
    wompi_metodo = normalize_upper(data.wompi_metodo) if data.wompi_metodo else None
    incluir_lu = bool(data.incluir_linea_usuario)

    if cuenta not in CUENTAS: raise HTTPException(422, "Cuenta inválida")
    if semestre not in SEMESTRES: raise HTTPException(422, "Semestre inválido")
    if detalle not in [*DETALLE_BY_CUENTA.get(cuenta, [])]: raise HTTPException(422, "Detalle inválido para la cuenta")

    monto = parse_monto_str_to_decimal(data.monto)

    linea_final = "PENDIENTE"; usuario_final = "PENDIENTE"; semestre_final = semestre
    if detalle == "PAGO INTERESES":
        semestre_final, linea_final, usuario_final = "GENERAL", "GENERAL", "INTERESES"
    else:
        if incluir_lu:
            if not data.linea or not data.usuario:
                raise HTTPException(422, "LÍNEA y USUARIO obligatorios con el checkbox activo.")
            linea_final = normalize_upper(data.linea); usuario_final = normalize_upper(data.usuario)

    if (cuenta.startswith("BANCOLOMBIA_")) and (detalle == "WOMPI"):
        if wompi_metodo not in ("PSE","TC"): raise HTTPException(422, "MÉTODO Wompi: PSE o TC.")
        neto = calcular_neto_wompi(monto, wompi_metodo); metodo_tabla = "WOMPI"
    else:
        neto = monto; metodo_tabla = detalle

    reg = Ingreso(
        fecha=now_str(), cantidad=f"{neto:.2f}".replace(".", ","),
        semestre=semestre_final, banco=cuenta, metodo=metodo_tabla,
        linea=linea_final, user=usuario_final, extra="-"
    ).dict()
    INGRESOS.append(reg)
    return {"ok": True}
# ------------------ API Egresos ------------------
@app.get("/api/egresos")
def api_eg_list():
    def pf(x): return datetime.strptime(x["fecha"], "%d/%m/%Y %H:%M:%S")
    return sorted(EGRESOS, key=pf, reverse=True)

@app.post("/api/egresos")
def api_eg_create(data: EgresoIn):
    cuenta = normalize_upper(data.cuenta.strip())
    metodo = normalize_upper(data.metodo.strip())
    semestre = normalize_upper(data.semestre.strip())
    categoria = normalize_upper(data.categoria.strip())
    if cuenta not in CUENTAS: raise HTTPException(422, "Cuenta inválida")
    if semestre not in SEMESTRES: raise HTTPException(422, "Semestre inválido")
    if categoria not in CATS: raise HTTPException(422, "Categoría inválida")
    monto = parse_monto_str_to_decimal(data.monto)

    mes = normalize_upper(data.mes) if data.mes else None
    nombre_carro = normalize_upper(data.nombre_carro) if data.nombre_carro else None
    motivo_carro = normalize_upper(data.motivo_carro) if data.motivo_carro else None
    razon = normalize_upper(data.razon) if data.razon else None
    autorizo = normalize_upper(data.autorizo.strip())
    responsable = normalize_upper(data.responsable.strip())

    if categoria in CATS_REQUIEREN_MES and not mes:
        raise HTTPException(422, "MES es obligatorio para esta categoría.")
    if categoria == "CARROS":
        if (nombre_carro not in CARROS_NOMBRES) or (motivo_carro not in CARROS_MOTIVOS):
            raise HTTPException(422, "NOMBRE CARRO y MOTIVO válidos.")
        if not razon: raise HTTPException(422, "RAZÓN es obligatoria para CARROS.")
    if categoria in {"ADELANTO","PAGO_NÓMINA","VIATICOS","PRIMAS","BASE DE DATOS","ITAÚ-APTOS","MERCADO","SOFTWARE","IMPUESTOS","DEVOLUCIÓN"} and not razon:
        raise HTTPException(422, "RAZÓN es obligatoria para esta categoría.")

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

    cantidad = monto
    cantidad_real = monto if cuenta == "EFECTY" else to_decimal_2(monto * Decimal("1.004"))

    reg = Egreso(
        fecha=now_str(), cuenta=cuenta, metodo=metodo,
        cantidad=f"{cantidad:.2f}".replace(".", ","), cantidad_real=f"{cantidad_real:.2f}".replace(".", ","),
        semestre=semestre, categoria=categoria, razon=razon_final,
        autorizo=autorizo, responsable=responsable
    ).dict()
    EGRESOS.append(reg)
    return {"ok": True}

# ------------------ API Transferencias ------------------
@app.get("/api/transferencias")
def api_tr_list():
    def pf(x): return datetime.strptime(x["fecha"], "%d/%m/%Y %H:%M:%S")
    return sorted(TRANSFERENCIAS, key=pf, reverse=True)

@app.post("/api/transferencias")
def api_tr_create(data: TransferIn):
    monto = parse_monto_str_to_decimal(data.monto)
    costo = parse_monto_str_to_decimal(data.costo) if data.costo else Decimal("0")
    origen = normalize_upper(data.origen.strip()); destino = normalize_upper(data.destino.strip())
    semestre = normalize_upper(data.semestre.strip())
    if origen not in CUENTAS or destino not in CUENTAS: raise HTTPException(422, "Cuenta origen/destino inválida")
    if origen == destino: raise HTTPException(422, "ORIGEN y DESTINO no pueden ser iguales")
    if semestre not in SEMESTRES: raise HTTPException(422, "Semestre inválido")

    fecha = now_str()
    TRANSFERENCIAS.append(Transfer(
        fecha=fecha, monto=f"{monto:.2f}".replace(".", ","), semestre=semestre,
        origen=origen, destino=destino, costo=f"{costo:.2f}".replace(".", ",")
    ).dict())

    # Ingreso automático en DESTINO
    INGRESOS.append(dict(
        fecha=fecha, cantidad=f"{monto:.2f}".replace(".", ","), semestre=semestre,
        banco=destino, metodo="TRANSF_INT", linea="PENDIENTE", user="PENDIENTE", extra=f"ORIGEN:{origen}"
    ))
    # Comisión (si hay) como EGRESO en ORIGEN
    if costo > 0:
        EGRESOS.append(dict(
            fecha=fecha, cuenta=origen, metodo="COMISION",
            cantidad=f"{costo:.2f}".replace(".", ","), cantidad_real=f"{(costo if origen=='EFECTY' else to_decimal_2(costo*Decimal('1.004'))):.2f}".replace(".", ","),
            semestre=semestre, categoria="OCIO", razon=f"COMISION_TRANSF_{origen}_A_{destino}",
            autorizo="AUTOMATICO", responsable="EMPRESA"
        ))
    return {"ok": True}

# ------------------ API Export/Helpers ------------------
@app.get("/api/ingresos/export2")
def export_ingresos(fmt: str = Query("csv"), **filters):
    headers = ["FECHA","CANTIDAD","SEMESTRE","BANCO","MÉTODO","LÍNEA","USER","EXTRA"]
    rows = [{ "FECHA":r["fecha"], "CANTIDAD":r["cantidad"], "SEMESTRE":r["semestre"], "BANCO":r["banco"], "MÉTODO":r["metodo"], "LÍNEA":r["linea"], "USER":r["user"], "EXTRA":r.get("extra","") } for r in INGRESOS]
    if fmt.lower()=="xlsx": return export_xlsx(rows, headers, "INGRESOS.xlsx")
    return export_csv(rows, headers)

@app.get("/api/egresos/export")
def export_egresos(fmt: str = Query("csv"), **filters):
    headers = ["FECHA","CUENTA","MÉTODO","CANTIDAD","CANTIDAD REAL","SEMESTRE","CATEGORÍA","RAZÓN","AUTORIZÓ","RESPONSABLE"]
    rows = [{ "FECHA":r["fecha"], "CUENTA":r["cuenta"], "MÉTODO":r["metodo"], "CANTIDAD":r["cantidad"], "CANTIDAD REAL":r["cantidad_real"], "SEMESTRE":r["semestre"], "CATEGORÍA":r["categoria"], "RAZÓN":r["razon"], "AUTORIZÓ":r["autorizo"], "RESPONSABLE":r["responsable"] } for r in EGRESOS]
    if fmt.lower()=="xlsx": return export_xlsx(rows, headers, "EGRESOS.xlsx")
    return export_csv(rows, headers)

def _compute_saldos() -> List[Dict[str,str]]:
    def to_num(s): return float((s or "0").replace(".","").replace(",", ".")) if isinstance(s,str) else float(s or 0)
    I = {c:0.0 for c in CUENTAS}; E = {c:0.0 for c in CUENTAS}; Tin={c:0.0 for c in CUENTAS}; Tout={c:0.0 for c in CUENTAS}
    for r in INGRESOS: I[r["banco"]] += to_num(r["cantidad"])
    for r in EGRESOS:  E[r["cuenta"]] += to_num(r["cantidad"])
    for r in TRANSFERENCIAS:
        Tin[r["destino"]]  += to_num(r["monto"])
        Tout[r["origen"]]  += to_num(r["monto"])
    rows=[]
    for c in CUENTAS:
        saldo = (I[c]+Tin[c]) - (E[c]+Tout[c])
        rows.append({
            "CUENTA": c,
            "INGRESOS": f"{I[c]:.2f}".replace(".", ","),
            "EGRESOS": f"{E[c]:.2f}".replace(".", ","),
            "TRANSF (+)": f"{Tin[c]:.2f}".replace(".", ","),
            "TRANSF (-)": f"{Tout[c]:.2f}".replace(".", ","),
            "SALDO": f"{saldo:.2f}".replace(".", ","),
        })
    return rows

@app.get("/api/saldos")
def api_saldos(): return _compute_saldos()

@app.get("/api/saldos/export")
def api_saldos_export(fmt: str = Query("csv")):
    headers = ["CUENTA","INGRESOS","EGRESOS","TRANSF (+)","TRANSF (-)","SALDO"]
    rows = _compute_saldos()
    if fmt.lower()=="xlsx": return export_xlsx(rows, headers, "SALDOS.xlsx")
    return export_csv(rows, headers)
