/* ======== Datos maestros ======== */
const SEMESTRES = ["126","226","326","426","GENERAL"];

const CUENTAS_INGRESO = [
  "BANCOLOMBIA_1423","DAVIVIENDA_8183","NEQUI","WOMPI","EFECTIVO","EFECTY"
];

// qué mostrar en “Detalle de cuenta / Método”
const DETALLE_POR_CUENTA = {
  "BANCOLOMBIA_1423": ["BANCOLOMBIA"],
  "DAVIVIENDA_8183":  ["DAVIVIENDA"],
  "NEQUI":            ["NEQUI"],
  "EFECTIVO":         ["EFECTIVO"],
  "EFECTY":           ["EFECTY"],
  "WOMPI":            ["WOMPI PSE","WOMPI TC"] // UI muestra PSE/TC, backend recibe metodo=WOMPI + wompi_mp=PSE|TC
};

const CUENTAS_EGRESO = [
  "BANCOLOMBIA_1423","DAVIVIENDA_8183","NEQUI","EFECTIVO","EFECTY"
];

const METODOS_EGRESO = ["PAGO","COMPRA","TRANSFERENCIA","GIRO","OTRO"];

// *** Categorías (las que usabas en tu main.py “bueno”) ***
const CATEGORIAS_EGRESO = [
  "ALQUILER / SERVICIO",
  "CARROS",
  "SEGURIDAD_SOCIAL",
  "ADELANTO",
  "ITAU-APTOS",
  "MERCADO",
  "PAGO_NÓMINA",
  "VIATICOS",
  "IMPUESTOS",
  "PRIMAS",
  "CESANTIAS",
  "OTROS"
];

const PERSONAS = ["JESÚS","TT","PENDIENTE"];

/* ======== Utilidades UI ======== */
function populateSelect(id, items, withPlaceholder = false) {
  const sel = document.getElementById(id);
  sel.innerHTML = "";
  if (withPlaceholder) {
    const opt = document.createElement("option");
    opt.value = ""; opt.disabled = true; opt.selected = true; opt.hidden = true;
    opt.textContent = "Selecciona…";
    sel.appendChild(opt);
  }
  items.forEach(t => {
    const o = document.createElement("option");
    o.value = t; o.textContent = t;
    sel.appendChild(o);
  });
}
function setPlaceholder(id) {
  const sel = document.getElementById(id);
  sel.innerHTML = "";
  const opt = document.createElement("option");
  opt.value = ""; opt.disabled = true; opt.selected = true; opt.hidden = true;
  opt.textContent = "Selecciona…";
  sel.appendChild(opt);
}
function val(id){ return document.getElementById(id).value; }
function getSel(id){ const v = val(id); return v === "" ? "" : v; }

/* ======== Máscara COP ======== */
function attachMoneyMask(id){
  const el = document.getElementById(id);
  el.addEventListener("input", () => {
    const digits = el.value.replace(/[^\d]/g,"");
    if (!digits) { el.value = "$ 0"; return; }
    el.value = "$ " + Number(digits).toLocaleString("es-CO");
  });
  // estado inicial
  if (!el.value) el.value = "$ 0";
}
function getMoneyValue(id){
  const el = document.getElementById(id);
  const digits = (el.value || "").replace(/[^\d]/g,"");
  return digits ? digits : "0";
}

/* ======== Extras para reglas de servidor ======== */
function extraMesDesdeRazon(razon){
  // si razón tiene _MES al final (EJ: DETALLE_JUNIO) intentamos extraerlo
  const m = razon.split("_").pop();
  const meses = ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"];
  return meses.includes(m?.toUpperCase()) ? m.toUpperCase() : "";
}
function extraCarroDesdeRazon(razon){
  // formato NOMBRECARRO_MOTIVO_RAZON
  const parts = razon.split("_");
  return { nombre: parts[0] || "", motivo: parts[1] || "" };
}
