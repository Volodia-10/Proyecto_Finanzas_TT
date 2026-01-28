
// ----------------- CONSTANTES -----------------
const SEMESTRES = ["126","226","326","426","526"];
const CUENTAS = ["NEQUI","BANCOLOMBIA_2807","BANCOLOMBIA_1423","DAVIVIENDA","EFECTY"];
const DETALLE_BY_CUENTA = {
  "BANCOLOMBIA_1423": ["BANCOLOMBIA","WOMPI","NEQUI","CORRESPONSAL","PAGO INTERESES"],
  "BANCOLOMBIA_2807": ["BANCOLOMBIA","WOMPI","NEQUI","CORRESPONSAL","PAGO INTERESES"],
  "NEQUI": ["NEQUI","NEQUI TRANSFIYA","RECARGA BANCOLOMBIA","RECARGA PSE","RECARGA CORRESPONSAL","PAGO INTERESES","REVERSIÓN PAGO","OTROS BANCOS"],
  "DAVIVIENDA": ["DAVIVIENDA","DAVIPLATA","CORRESPONSAL","PAGO INTERESES"],
  "EFECTY": ["GIRO NACIONAL"]
};
const LINEAS = ["L1","L2","L3","L4","L5","L6","L7"];
const EMPLEADOS = ["DIANA GOMEZ","BRAYAN PRIMICIERO","ANDREA GELVES","HERNAN DIAZ","DAVID CORDON","JULIANA RIVERA","ASTRID RODRIGUEZ","ALEXIS GOMEZ","ANGELA FERNANDEZ","IVAN MONSALVE","JHOSEP CABRERA","JUANCARLO HIDALGO","FAYBER SALAMANCA","JAVIER MATIZ","CAROLINA MACIAS","KARIME GOMEZ","LADY JAIMES","JOHAN SUAREZ","FELIPE TORRES","JESUS TORRES","MARLON JOYA","ZULAY RODRIGUEZ","STELLA CORZO","LILIANA BARRERA","NATALIA JOYA","MARTHA RAMIREZ","LADY GOMEZ","AMPARO IZAQUITA","MAIRA SANDOVAL","MADELEYNE CORZO","CINTHIA CIFUENTES","DANIELA RIAÑO","PAOLA CACERES","MONICA GUARIN","NICOLLE LEÓN"];
const MESES = ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"];
const CATS = ["DEVOLUCIÓN","ADELANTO","CARROS","BASE DE DATOS","FAMILIA","FUTBOL_TT","INVENTARIO","INVERSIONES","ITAÚ-APTOS","MERCADO","OCIO","PAGO_NÓMINA","SOFTWARE","VIAJES","VIATICOS","IMPUESTOS","SEGURIDAD_SOCIAL","PRIMAS","CESANTIAS"];
const CATS_REQUIEREN_MES = new Set(["ADELANTO","ITAÚ-APTOS","MERCADO","PAGO_NÓMINA","VIATICOS","IMPUESTOS","SEGURIDAD_SOCIAL","PRIMAS"]);
const CARROS_NOMBRES = ["VERSA","MAZDA","QASHQAI"];
const CARROS_MOTIVOS = ["MANTENIMIENTO","SOAT","IMPUESTOS","TODO-RIESGO","TECNICOMECANICO"];

// ----------------- UTILS -----------------
const upper = s => (s ?? "").toString().toUpperCase();
function stripAccents(s){ return s.normalize("NFD").replace(/\p{Diacritic}/gu, ""); }
function containsNoAccent(haystack, needle){
  return stripAccents(haystack).includes(stripAccents(needle));
}
function formatCOPnum(n){
  return new Intl.NumberFormat("es-CO", { style:"currency", currency:"COP" }).format(n);
}
function parseCOP(inputStr){
  const cleaned = inputStr.replace(/[^0-9,]/g, "").replace(",", ".");
  if(!cleaned) return 0;
  return parseFloat(cleaned);
}
function attachMontoMask(input){
  input.value = "";
  input.addEventListener("input", () => {
    const raw = input.value;
    let normalized = raw.replace(/[.\s]/g,"").replace(/[A-Za-z$]/g,"");
    normalized = normalized.replace(/,/g, ",");
    const parts = normalized.split(",");
    if(parts.length > 2){
      normalized = parts[0] + "," + parts.slice(1).join("").replace(/,/g,"");
    }
    if(normalized.includes(",")){
      const [ent, dec] = normalized.split(",");
      normalized = ent + "," + (dec||"").slice(0,2);
    }
    const [entera, decim] = normalized.split(",");
    const entClean = (entera||"").replace(/\D/g,"");
    const withThousands = entClean.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    const finalStr = decim !== undefined && decim.length>0 ? `$ ${withThousands},${decim}` : (withThousands ? `$ ${withThousands}` : "");
    input.value = finalStr;
  });
  input.addEventListener("blur", () => {
    if(input.value){
      let num = parseCOP(input.value);
      if(num > 0){
        input.value = new Intl.NumberFormat("es-CO", { style:"currency", currency:"COP" , minimumFractionDigits:2}).format(num);
      }else{
        input.value = "";
      }
    }
  });
}

// searchable selects
function makeSelectSearchable(container){
  const input = container.querySelector(".select-search");
  const select = container.querySelector("select");
  if(!input || !select) return;
  const original = Array.from(select.options).map(o => ({value:o.value, text:o.textContent}));
  input.addEventListener("input", () => {
    const q = upper(input.value.trim());
    const filtered = original.filter(o => !q || containsNoAccent(upper(o.text), q));
    const current = select.value;
    select.innerHTML = "";
    filtered.forEach(o => {
      const opt = document.createElement("option");
      opt.value = o.value;
      opt.textContent = o.text;
      select.appendChild(opt);
    });
    if(original[0] && original[0].value === "" && !filtered.find(o=>o.value==="")){
      const opt0 = document.createElement("option");
      opt0.value = "";
      opt0.textContent = "-";
      select.insertBefore(opt0, select.firstChild);
    }
    if(filtered.find(o => o.value === current)){
      select.value = current;
    }else{
      select.value = "";
    }
  });
}

// ----------------- INGRESOS: NUEVO -----------------
(function initNuevoIngreso(){
  const form = document.getElementById("formIngreso");
  if(!form) return;
  const monto = document.getElementById("monto");
  const semestre = document.getElementById("semestre");
  const cuenta = document.getElementById("cuenta");
  const detalle = document.getElementById("detalle");
  const wompiWrap = document.getElementById("wompiMetodoWrap");
  const wompiMetodo = document.getElementById("wompiMetodo");
  const chkLU = document.getElementById("chkLU");
  const luWrap = document.getElementById("luWrap");
  const linea = document.getElementById("linea");
  const usuario = document.getElementById("usuario");
  const toast = document.getElementById("toast");

  attachMontoMask(monto);
  function populate(select, arr){ select.innerHTML = '<option value="">-</option>' + arr.map(v=>`<option>${v}</option>`).join(""); }
  populate(semestre, SEMESTRES);
  populate(cuenta, CUENTAS);
  populate(linea, LINEAS);

  function refreshDetalle(){
    const opts = DETALLE_BY_CUENTA[cuenta.value] || [];
    detalle.innerHTML = '<option value="">-</option>' + opts.map(v=>`<option>${v}</option>`).join("");
    toggleWompi();
  }
  function toggleWompi(){
    if((cuenta.value||"").startsWith("BANCOLOMBIA_") && upper(detalle.value) === "WOMPI"){
      wompiWrap.classList.remove("hidden"); wompiMetodo.required = true;
    }else{
      wompiWrap.classList.add("hidden"); wompiMetodo.required = false; wompiMetodo.value = "";
    }
  }
  cuenta.addEventListener("change", refreshDetalle);
  detalle.addEventListener("change", toggleWompi);
  refreshDetalle();

  chkLU.addEventListener("change", () => {
    if(chkLU.checked){
      luWrap.classList.remove("hidden"); linea.required = true; usuario.required = true;
    }else{
      luWrap.classList.add("hidden"); linea.required = false; usuario.required = false; linea.value = ""; usuario.value = "";
    }
  });
  usuario.addEventListener("input", () => { usuario.value = upper(usuario.value); });

  form.addEventListener("submit", async (e)=>{
    e.preventDefault();
    const payload = {
      monto: monto.value,
      semestre: upper(semestre.value),
      cuenta: upper(cuenta.value),
      detalle: upper(detalle.value),
      wompi_metodo: wompiMetodo.value ? upper(wompiMetodo.value) : null,
      incluir_linea_usuario: chkLU.checked,
      linea: chkLU.checked ? upper(linea.value) : null,
      usuario: chkLU.checked ? upper(usuario.value.trim()) : null
    };
    if(!payload.monto || parseCOP(payload.monto)<=0){ alert("Ingrese un MONTO válido"); return; }
    if(!payload.semestre || !payload.cuenta || !payload.detalle){ alert("Complete los campos obligatorios"); return; }
    if((payload.cuenta||"").startsWith("BANCOLOMBIA_") && payload.detalle==="WOMPI" && !payload.wompi_metodo){ alert("Seleccione MÉTODO DE PAGO (WOMPI)"); return; }

    const res = await fetch("/api/ingresos", { method:"POST", headers:{ "Content-Type":"application/json" }, body: JSON.stringify(payload) });
    if(!res.ok){ const err = await res.json().catch(()=>({detail:"Error"})); alert(err.detail||"Error"); return; }
    toast.classList.remove("hidden"); setTimeout(()=>{ window.location.href="/ingresos"; }, 900);
  });

  document.querySelectorAll(".select-wrap").forEach(makeSelectSearchable);
})();

// ----------------- INGRESOS: TABLA -----------------
(function initTablaIngresos(){
  const table = document.getElementById("tablaIngresos");
  if(!table) return;
  const tbody = table.querySelector("tbody");
  const filters = document.querySelectorAll(".filter");
  function rowMatchesFilters(tr){
    return Array.from(filters).every(inp => {
      const col = parseInt(inp.dataset.col, 10);
      const val = (inp.value || "").toUpperCase();
      if(!val) return true;
      const cell = tr.children[col];
      return (cell?.textContent || "").toUpperCase().includes(val);
    });
  }
  function applyFilters(){
    tbody.querySelectorAll("tr").forEach(tr => { tr.style.display = rowMatchesFilters(tr) ? "" : "none"; });
  }
  filters.forEach(inp => inp.addEventListener("input", applyFilters));

  fetch("/api/ingresos").then(r=>r.json()).then(rows=>{
    tbody.innerHTML = "";
    rows.forEach(r => {
      const num = parseFloat((r.cantidad||"0").replace(".","").replace(",", "."));
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${r.fecha}</td>
        <td>${formatCOPnum(num)}</td>
        <td>${r.semestre}</td>
        <td>${r.banco}</td>
        <td>${r.metodo}</td>
        <td>${r.linea}</td>
        <td>${r.user}</td>
        <td>${r.extra || ""}</td>`;
      tbody.appendChild(tr);
    });
  });

  function buildSelect(id, label, arr){
    const wrap = document.createElement("div"); 
    wrap.className = "field";
    wrap.innerHTML = `
      <label>${label}</label>
      <div class="select-wrap">
        <select id="${id}" class="searchable">
          <option value="">-</option>
          ${arr.map(v => `<option>${v}</option>`).join("")}
        </select>
      </div>`;
    return wrap;
  }
  document.getElementById("expInCsv")?.addEventListener("click", ()=>{ window.location.href = buildExportUrl("csv"); });
  document.getElementById("expInXlsx")?.addEventListener("click", ()=>{ window.location.href = buildExportUrl("xlsx"); });
})();

// ----------------- RESUMEN INGRESOS -----------------
(function initResumenIngresos(){
  const tabla = document.getElementById("tablaResumen");
  if(!tabla) return;
  const tbody = tabla.querySelector("tbody");
  const kpiTotal = document.getElementById("kpiTotal");
  const kpiCount = document.getElementById("kpiCount");
  const kpiAvg = document.getElementById("kpiAvg");
  const COLS = [...SEMESTRES, "INTERESES", "TOTAL"];

  function parseCantidad(str){ const num = parseFloat(str.replace(".","").replace(",", ".")); return isNaN(num)?0:num; }
  const M = {}; CUENTAS.forEach(c=>{ M[c]=Object.fromEntries(SEMESTRES.map(s=>[s,0])); M[c]["INTERESES"]=0; M[c]["TOTAL"]=0; });

  fetch("/api/ingresos").then(r=>r.json()).then(rows=>{
    const valores = rows.map(r => parseCantidad(r.cantidad));
    const sumTotal = valores.reduce((a,b)=>a+b,0);
    kpiTotal.textContent = formatCOPnum(sumTotal);
    kpiCount.textContent = rows.length.toString();
    kpiAvg.textContent = formatCOPnum(rows.length ? (sumTotal/rows.length) : 0);

    rows.forEach(r=>{
      if(!CUENTAS.includes(r.banco)) return;
      const cant = parseCantidad(r.cantidad);
      if(r.metodo === "PAGO INTERESES"){
        M[r.banco]["INTERESES"] += cant;
      }else if(SEMESTRES.includes(r.semestre)){
        M[r.banco][r.semestre] += cant;
      }
    });
    CUENTAS.forEach(cta=>{ M[cta]["TOTAL"] = SEMESTRES.reduce((acc,s)=>acc+M[cta][s],0)+M[cta]["INTERESES"]; });

    tbody.innerHTML = "";
    CUENTAS.forEach(cta=>{
      const tr = document.createElement("tr");
      const cells = [cta, ...SEMESTRES.map(s=>M[cta][s]), M[cta]["INTERESES"], M[cta]["TOTAL"]];
      tr.innerHTML = cells.map((val,i)=> i===0 ? `<td><b>${val}</b></td>` : `<td>${formatCOPnum(val)}</td>`).join("");
      tbody.appendChild(tr);
    });
    const tTot = document.getElementById("rowTotales").children;
    let granTotal = 0;
    SEMESTRES.forEach((s,idx)=>{
      let colSuma = 0; CUENTAS.forEach(cta=> colSuma += M[cta][s]); tTot[1+idx].textContent = formatCOPnum(colSuma); granTotal += colSuma;
    });
    let interesesCol = 0; CUENTAS.forEach(cta => interesesCol += M[cta]["INTERESES"]);
    tTot[1+SEMESTRES.length].textContent = formatCOPnum(interesesCol); granTotal += interesesCol;
    tTot[1+SEMESTRES.length+1].textContent = formatCOPnum(granTotal);

    const ctxStack = document.getElementById("chartStacked");
    if(ctxStack && window.Chart){
      const datasets = CUENTAS.map(cta => ({ label: cta, data: SEMESTRES.map(s=>M[cta][s]) }));
      new Chart(ctxStack, { type:'bar', data:{ labels: SEMESTRES, datasets }, options:{ plugins:{ legend:{ position:'bottom' } }, scales:{ x:{ stacked:true }, y:{ stacked:true } } } });
    }
    const ctxDonut = document.getElementById("chartDonut");
    if(ctxDonut && window.Chart){
      new Chart(ctxDonut, { type:'doughnut', data:{ labels: CUENTAS, datasets:[{ data: CUENTAS.map(cta=>M[cta]["TOTAL"]) }] }, options:{ plugins:{ legend:{ position:'bottom' } } } });
    }
  });
})();

// ----------------- EGRESOS: NUEVO -----------------
(function initNuevoEgreso(){
  const form = document.getElementById("formEgreso");
  if(!form) return;
  const monto = document.getElementById("e_monto");
  const cuenta = document.getElementById("e_cuenta");
  const metodo = document.getElementById("e_metodo");
  const semestre = document.getElementById("e_semestre");
  const categoria = document.getElementById("e_categoria");
  const dyn = document.getElementById("e_dynamic");
  const autorizo = document.getElementById("e_autorizo");
  const responsable = document.getElementById("e_responsable");
  const toast = document.getElementById("toast");

  attachMontoMask(monto);
  function populate(sel, arr){ sel.innerHTML = '<option value="">-</option>' + arr.map(v=>`<option>${v}</option>`).join(""); }
  populate(cuenta, CUENTAS);
  populate(semestre, SEMESTRES);
  populate(categoria, CATS);

  function buildSelect(id, label, arr){
    const wrap = document.createElement("div"); 
    wrap.className = "field";
    wrap.innerHTML = `
      <label>${label}</label>
      <div class="select-wrap">
        <select id="${id}" class="searchable">
          <option value="">-</option>
          ${arr.map(v => `<option>${v}</option>`).join("")}
        </select>
      </div>`;
    return wrap;
  }
  function buildInput(id, label){
    const wrap = document.createElement("div"); wrap.className="field";
    wrap.innerHTML = `<label>${label}</label><input id="${id}" type="text" placeholder="-">`;
    return wrap;
  }

  function renderDynamic(){
    dyn.innerHTML = "";
    const cat = categoria.value;
    const needsMes = CATS_REQUIEREN_MES.has(cat);
    if(cat === "CARROS"){
      dyn.appendChild(buildSelect("e_nombre_carro","NOMBRE CARRO", CARROS_NOMBRES));
      dyn.appendChild(buildSelect("e_motivo_carro","MOTIVO", CARROS_MOTIVOS));
      dyn.appendChild(buildInput("e_razon","RAZÓN"));
    }else if(cat === "DEVOLUCIÓN"){
      dyn.appendChild(buildSelect("e_razon","RAZÓN", ["CANCELACIÓN","PAGO DE MAS","MALA MIGRACIÓN"]));
    }else if(cat === "ADELANTO" || cat === "PAGO_NÓMINA" || cat === "VIATICOS" || cat === "PRIMAS"){
      dyn.appendChild(buildSelect("e_razon","RAZÓN", EMPLEADOS));
    }else if(cat === "BASE DE DATOS"){
      dyn.appendChild(buildSelect("e_razon","RAZÓN", SEMESTRES));
    }else if(cat === "ITAÚ-APTOS" || cat === "MERCADO"){
      dyn.appendChild(buildSelect("e_razon","RAZÓN", ["JESÚS","FELIPE","MARLON"]));
    }else if(cat === "SOFTWARE"){
      dyn.appendChild(buildSelect("e_razon","RAZÓN", ["CAPITAL_BRANCH","GOOGLE_STORAGE","LOOM","PROTON","PUBLICIDAD","RECARGA_CELULAR"]));
    }else if(cat === "IMPUESTOS"){
      dyn.appendChild(buildSelect("e_razon","RAZÓN", ["INDUSTRIA_Y_COMERCIO","RENTA","IVA","RETEFUENTE"]));
    }else if(cat === "SEGURIDAD_SOCIAL"){
      // no RAZON
    }else if(cat === "CESANTIAS"){
      // razon fija 2025
    }else{
      dyn.appendChild(buildInput("e_razon","RAZÓN"));
    }
    if(needsMes){
      dyn.appendChild(buildSelect("e_mes","MES", MESES));
    }
    dyn.querySelectorAll("input[type=text]").forEach(inp=>{
      inp.addEventListener("input", ()=>{ inp.value = upper(inp.value); });
    });
  }

  categoria.addEventListener("change", renderDynamic);
  renderDynamic();

  form.addEventListener("submit", async (e)=>{
    e.preventDefault();
    const payload = {
      monto: monto.value,
      cuenta: upper(cuenta.value),
      metodo: upper(metodo.value),
      semestre: upper(semestre.value),
      categoria: upper(categoria.value),
      mes: upper(document.getElementById("e_mes")?.value || "" ) || null,
      nombre_carro: upper(document.getElementById("e_nombre_carro")?.value || "" ) || null,
      motivo_carro: upper(document.getElementById("e_motivo_carro")?.value || "" ) || null,
      razon: upper(document.getElementById("e_razon")?.value || "" ) || null,
      autorizo: upper(autorizo.value),
      responsable: upper(responsable.value),
    };
    if(!payload.monto || parseCOP(payload.monto) <= 0){ alert("Ingrese un MONTO válido"); return; }
    if(!payload.cuenta || !payload.metodo || !payload.semestre || !payload.categoria){ alert("Complete los campos obligatorios"); return; }
    if(CATS_REQUIEREN_MES.has(payload.categoria) && !payload.mes){ alert("MES es obligatorio para esta categoría"); return; }
    if(payload.categoria === "CARROS"){
      if(!payload.nombre_carro || !payload.motivo_carro){ alert("NOMBRE CARRO y MOTIVO son obligatorios"); return; }
      if(!payload.razon){ alert("RAZÓN es obligatoria para CARROS"); return; }
    }
    if(["ADELANTO","PAGO_NÓMINA","VIATICOS","PRIMAS","BASE DE DATOS","ITAÚ-APTOS","MERCADO","SOFTWARE","IMPUESTOS","DEVOLUCIÓN"].includes(payload.categoria) && !payload.razon){
      alert("RAZÓN es obligatoria para esta categoría"); return;
    }

    const res = await fetch("/api/egresos", {
      method:"POST",
      headers:{ "Content-Type":"application/json" },
      body: JSON.stringify(payload)
    });
    if(!res.ok){
      const err = await res.json().catch(()=>({detail:"Error"}));
      alert(err.detail || "Error al registrar egreso"); return;
    }
    toast.classList.remove("hidden"); setTimeout(()=>{ window.location.href="/egresos"; }, 900);
  });

})();

// ----------------- EGRESOS: TABLA -----------------
(function initTablaEgresos(){
  const table = document.getElementById("tablaEgresos");
  if(!table) return;
  const tbody = table.querySelector("tbody");
  const filters = document.querySelectorAll(".filter");
  function rowMatchesFilters(tr){
    return Array.from(filters).every(inp => {
      const col = parseInt(inp.dataset.col, 10);
      const val = (inp.value || "").toUpperCase();
      if(!val) return true;
      const cell = tr.children[col];
      return (cell?.textContent || "").toUpperCase().includes(val);
    });
  }
  function applyFilters(){
    tbody.querySelectorAll("tr").forEach(tr => { tr.style.display = rowMatchesFilters(tr) ? "" : "none"; });
  }
  filters.forEach(inp => inp.addEventListener("input", applyFilters));

  fetch("/api/egresos").then(r=>r.json()).then(rows=>{
    tbody.innerHTML = "";
    rows.forEach(r => {
      const n1 = parseFloat((r.cantidad||"0").replace(".","").replace(",", "."));
      const n2 = parseFloat((r.cantidad_real||"0").replace(".","").replace(",", "."));
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${r.fecha}</td>
        <td>${r.cuenta}</td>
        <td>${r.metodo}</td>
        <td>${formatCOPnum(n1)}</td>
        <td>${formatCOPnum(n2)}</td>
        <td>${r.semestre}</td>
        <td>${r.categoria}</td>
        <td>${r.razon}</td>
        <td>${r.autorizo}</td>
        <td>${r.responsable}</td>`;
      tbody.appendChild(tr);
    });
  });

  function buildExportUrl(fmt){
    const params = new URLSearchParams();
    document.querySelectorAll(".filter").forEach((inp, idx)=>{ if(inp.value) params.set("f"+idx, inp.value); });
    const qs = params.toString();
    return `/api/egresos/export?fmt=${fmt}` + (qs ? `&${qs}` : "");
  }
  document.getElementById("expEgCsv")?.addEventListener("click", ()=>{ window.location.href = buildExportUrl("csv"); });
  document.getElementById("expEgXlsx")?.addEventListener("click", ()=>{ window.location.href = buildExportUrl("xlsx"); });
})();

// ----------------- RESUMEN EGRESOS -----------------
(function initResumenEgresos(){
  const matNeto = document.getElementById("matNeto");
  if(!matNeto) return;
  const matReal = document.getElementById("matReal");
  const catNeto = document.getElementById("catNeto").querySelector("tbody");
  const catReal = document.getElementById("catReal").querySelector("tbody");
  const kN = document.getElementById("kpiEgNeto");
  const kR = document.getElementById("kpiEgReal");
  const kD = document.getElementById("kpiEgDiff");
  const kC = document.getElementById("kpiEgCount");
  const chipsCtas = document.getElementById("fCtas");
  const chipsSems = document.getElementById("fSems");
  const btnNeto = document.getElementById("btnNeto");
  const btnReal = document.getElementById("btnReal");

  let selectedCtas = new Set(CUENTAS);
  let selectedSems = new Set(SEMESTRES);
  let rows = [];

  function buildChips(container, items, selectedSet){
    container.innerHTML = "";
    items.forEach(it => {
      const d = document.createElement("div");
      d.className = "chip active";
      d.textContent = it;
      d.addEventListener("click", ()=>{
        if(selectedSet.has(it)){ selectedSet.delete(it); d.classList.remove("active"); }
        else { selectedSet.add(it); d.classList.add("active"); }
        recalc();
      });
      container.appendChild(d);
    });
  }
  buildChips(chipsCtas, CUENTAS, selectedCtas);
  buildChips(chipsSems, SEMESTRES, selectedSems);

  function parseN(s){ return parseFloat((s||"0").replace(".","").replace(",", ".")) || 0; }

  function recalc(){
    const frows = rows.filter(r => selectedCtas.has(r.cuenta) && selectedSems.has(r.semestre));
    kC.textContent = frows.length.toString();
    const totalN = frows.reduce((a,r)=>a+parseN(r.cantidad),0);
    const totalR = frows.reduce((a,r)=>a+parseN(r.cantidad_real),0);
    kN.textContent = formatCOPnum(totalN);
    kR.textContent = formatCOPnum(totalR);
    kD.textContent = formatCOPnum(totalR-totalN);

    const PMN = {}; const PMR = {};
    CUENTAS.forEach(c => { PMN[c] = Object.fromEntries(SEMESTRES.map(s=>[s,0])); PMR[c] = Object.fromEntries(SEMESTRES.map(s=>[s,0])); });
    frows.forEach(r => {
      PMN[r.cuenta][r.semestre] += parseN(r.cantidad);
      PMR[r.cuenta][r.semestre] += parseN(r.cantidad_real);
    });
    const tbN = matNeto.querySelector("tbody"); tbN.innerHTML = "";
    CUENTAS.forEach(c => {
      const tr = document.createElement("tr");
      const vals = [c, ...SEMESTRES.map(s=>PMN[c][s]), SEMESTRES.reduce((a,s)=>a+PMN[c][s],0)];
      tr.innerHTML = vals.map((v,i)=> i===0?`<td><b>${v}</b></td>`:`<td>${formatCOPnum(v)}</td>`).join("");
      tbN.appendChild(tr);
    });
    const nt = document.getElementById("matNetoTot").children;
    let grand = 0;
    SEMESTRES.forEach((s,idx)=>{ let col=0; CUENTAS.forEach(c=> col+=PMN[c][s]); nt[1+idx].textContent = formatCOPnum(col); grand += col; });
    nt[1+SEMESTRES.length].textContent = formatCOPnum(grand);

    const tbR = matReal.querySelector("tbody"); tbR.innerHTML = "";
    CUENTAS.forEach(c => {
      const tr = document.createElement("tr");
      const vals = [c, ...SEMESTRES.map(s=>PMR[c][s]), SEMESTRES.reduce((a,s)=>a+PMR[c][s],0)];
      tr.innerHTML = vals.map((v,i)=> i===0?`<td><b>${v}</b></td>`:`<td>${formatCOPnum(v)}</td>`).join("");
      tbR.appendChild(tr);
    });
    const rt = document.getElementById("matRealTot").children;
    let grandR = 0;
    SEMESTRES.forEach((s,idx)=>{ let col=0; CUENTAS.forEach(c=> col+=PMR[c][s]); rt[1+idx].textContent = formatCOPnum(col); grandR += col; });
    rt[1+SEMESTRES.length].textContent = formatCOPnum(grandR);

    const catMapN = {}; const catMapR = {};
    frows.forEach(r => {
      catMapN[r.categoria] = (catMapN[r.categoria]||0) + parseN(r.cantidad);
      catMapR[r.categoria] = (catMapR[r.categoria]||0) + parseN(r.cantidad_real);
    });
    function renderCat(tb, m){
      tb.innerHTML = "";
      CATS.forEach(c => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${c}</td><td>${formatCOPnum(m[c]||0)}</td>`;
        tb.appendChild(tr);
      });
    }
    renderCat(catNeto, catMapN);
    renderCat(catReal, catMapR);

    const ctxS = document.getElementById("egChartStacked");
    const ctxD = document.getElementById("egChartDonut");
    if(ctxS && window.Chart){
      if(window.egS) window.egS.destroy();
      const datasets = CUENTAS.map(c=>({ label:c, data: SEMESTRES.map(s=> (btnNeto.classList.contains("primary")? PMN[c][s] : PMR[c][s]) ) }));
      window.egS = new Chart(ctxS, { type:'bar', data:{ labels: SEMESTRES, datasets }, options:{ plugins:{ legend:{ position:'bottom' } }, scales:{ x:{ stacked:true }, y:{ stacked:true } } } });
    }
    if(ctxD && window.Chart){
      if(window.egD) window.egD.destroy();
      const m = btnNeto.classList.contains("primary") ? catMapN : catMapR;
      const labels = CATS;
      const data = labels.map(l=>m[l]||0);
      window.egD = new Chart(ctxD, { type:'doughnut', data:{ labels, datasets:[{ data }]}, options:{ plugins:{ legend:{ position:'bottom' } } } });
    }
  }

  fetch("/api/egresos").then(r=>r.json()).then(rs=>{ rows = rs; recalc(); });
  btnNeto.addEventListener("click", ()=>{ btnNeto.classList.add("primary"); btnReal.classList.remove("primary"); recalc(); });
  btnReal.addEventListener("click", ()=>{ btnReal.classList.add("primary"); btnNeto.classList.remove("primary"); recalc(); });
})();
