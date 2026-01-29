// ======================= CONSTANTES =======================
const SEMESTRES = ["126","226","326","426","526"];
const CUENTAS = ["NEQUI","BANCOLOMBIA_2807","BANCOLOMBIA_1423","DAVIVIENDA","EFECTY"];
const DETALLE_BY_CUENTA = {
  "BANCOLOMBIA_1423": ["BANCOLOMBIA","WOMPI","NEQUI","CORRESPONSAL","PAGO INTERESES"],
  "BANCOLOMBIA_2807": ["BANCOLOMBIA","WOMPI","NEQUI","CORRESPONSAL","PAGO INTERESES"],
  "NEQUI": ["NEQUI","NEQUI TRANSFIYA","RECARGA BANCOLOMBIA","RECARGA PSE","RECARGA CORRESPONSAL","PAGO INTERESES","REVERSIÓN PAGO","OTROS BANCOS"],
  "DAVIVIENDA": ["DAVIVIENDA","DAVIPLATA","CORRESPONSAL","PAGO INTERESES"],
  "EFECTY": ["GIRO NACIONAL"]
};
// métodos sugeridos para egresos
const EGRESO_METODOS = {
  "NEQUI": ["NEQUI","NEQUI TRANSFIYA","RECARGA BANCOLOMBIA","RECARGA CORRESPONSAL","OTRO"],
  "DAVIVIENDA": ["DAVIVIENDA","DAVIPLATA","CORRESPONSAL","PSE","OTRO"],
  "EFECTY": ["GIRO NACIONAL"],
  "_BANC_": ["TRANSFERENCIA","CORRESPONSAL","PSE","WOMPI","OTRO"], // BANCOLOMBIA_*
};
const LINEAS = ["L1","L2","L3","L4","L5","L6","L7"];
const EMPLEADOS = ["DIANA GOMEZ","BRAYAN PRIMICIERO","ANDREA GELVES","HERNAN DIAZ","DAVID CORDON","JULIANA RIVERA","ASTRID RODRIGUEZ","ALEXIS GOMEZ","ANGELA FERNANDEZ","IVAN MONSALVE","JHOSEP CABRERA","JUANCARLO HIDALGO","FAYBER SALAMANCA","JAVIER MATIZ","CAROLINA MACIAS","KARIME GOMEZ","LADY JAIMES","JOHAN SUAREZ","FELIPE TORRES","JESUS TORRES","MARLON JOYA","ZULAY RODRIGUEZ","STELLA CORZO","LILIANA BARRERA","NATALIA JOYA","MARTHA RAMIREZ","LADY GOMEZ","AMPARO IZAQUITA","MAIRA SANDOVAL","MADELEYNE CORZO","CINTHIA CIFUENTES","DANIELA RIAÑO","PAOLA CACERES","MONICA GUARIN","NICOLLE LEÓN"];
const MESES = ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"];
const CATS = ["DEVOLUCIÓN","ADELANTO","CARROS","BASE DE DATOS","FAMILIA","FUTBOL_TT","INVENTARIO","INVERSIONES","ITAÚ-APTOS","MERCADO","OCIO","PAGO_NÓMINA","SOFTWARE","VIAJES","VIATICOS","IMPUESTOS","SEGURIDAD_SOCIAL","PRIMAS","CESANTIAS"];
const CATS_REQUIEREN_MES = new Set(["ADELANTO","ITAÚ-APTOS","MERCADO","PAGO_NÓMINA","VIATICOS","IMPUESTOS","SEGURIDAD_SOCIAL","PRIMAS"]);
const CARROS_NOMBRES = ["VERSA","MAZDA","QASHQAI"];
const CARROS_MOTIVOS = ["MANTENIMIENTO","SOAT","IMPUESTOS","TODO-RIESGO","TECNICOMECANICO"];

const upper = s => (s ?? "").toString().toUpperCase();
function formatCOPnum(n){ return new Intl.NumberFormat("es-CO", { style:"currency", currency:"COP" }).format(n); }
function parseCOP(str){ const c = (str||"").replace(/[^0-9,]/g,"").replace(",","."); return c? parseFloat(c):0; }
function attachMontoMask(input){
  if(!input) return;
  input.addEventListener("input", () => {
    let raw = input.value.replace(/[.\s$]/g,"");
    if(!raw){ input.value=""; return; }
    const parts = raw.split(",");
    if(parts.length>2){ raw = parts[0]+","+parts.slice(1).join(""); }
    if(raw.includes(",")){ const [en,de] = raw.split(","); raw = `${en},${(de||"").slice(0,2)}`; }
    const [ent,deci] = raw.split(",");
    const withThousands = (ent||"").replace(/\D/g,"").replace(/\B(?=(\d{3})+(?!\d))/g,".");
    input.value = deci!==undefined ? `$ ${withThousands},${deci}` : `$ ${withThousands}`;
  });
  input.addEventListener("blur", ()=> {
    if(!input.value) return;
    const n = parseCOP(input.value);
    input.value = new Intl.NumberFormat("es-CO",{style:"currency",currency:"COP",minimumFractionDigits:2}).format(n);
  });
}
function hydrateSelect(sel, arr){ if(!sel) return; sel.innerHTML = '<option value="">-</option>' + arr.map(v=>`<option>${v}</option>`).join(""); }
function egresoMetodosPorCuenta(c){
  if(c.startsWith("BANCOLOMBIA_")) return EGRESO_METODOS["_BANC_"];
  return EGRESO_METODOS[c] || ["OTRO"];
}

// ======================= INGRESOS (form) ==================
(function(){
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

  attachMontoMask(monto);
  hydrateSelect(semestre, SEMESTRES);
  hydrateSelect(cuenta, CUENTAS);
  hydrateSelect(linea, LINEAS);

  function refreshDetalle(){
    hydrateSelect(detalle, DETALLE_BY_CUENTA[cuenta.value] || []);
    toggleWompi();
  }
  function toggleWompi(){
    if((cuenta.value||"").startsWith("BANCOLOMBIA_") && upper(detalle.value)==="WOMPI"){
      wompiWrap.classList.remove("hidden"); wompiMetodo.required = true;
    }else{
      wompiWrap.classList.add("hidden"); wompiMetodo.required = false; wompiMetodo.value="";
    }
  }
  cuenta.addEventListener("change", refreshDetalle);
  detalle.addEventListener("change", toggleWompi);
  refreshDetalle();

  chkLU.addEventListener("change", ()=>{
    if(chkLU.checked){ luWrap.classList.remove("hidden"); linea.required = true; usuario.required = true; }
    else{ luWrap.classList.add("hidden"); linea.required = false; usuario.required = false; linea.value=""; usuario.value=""; }
  });
  usuario?.addEventListener("input", ()=>{ usuario.value = upper(usuario.value); });

  form.addEventListener("submit", async (e)=>{
    e.preventDefault();
    const payload = {
      monto: monto.value, semestre: upper(semestre.value),
      cuenta: upper(cuenta.value), detalle: upper(detalle.value),
      wompi_metodo: wompiMetodo?.value ? upper(wompiMetodo.value) : null,
      incluir_linea_usuario: chkLU.checked,
      linea: chkLU.checked ? upper(linea.value) : null,
      usuario: chkLU.checked ? upper(usuario.value.trim()) : null
    };
    if(!payload.monto || parseCOP(payload.monto)<=0) return alert("Ingrese MONTO válido");
    if(!payload.semestre || !payload.cuenta || !payload.detalle) return alert("Complete los campos obligatorios");
    if((payload.cuenta||"").startsWith("BANCOLOMBIA_") && payload.detalle==="WOMPI" && !payload.wompi_metodo) return alert("Seleccione MÉTODO Wompi");

    const res = await fetch("/api/ingresos",{method:"POST",headers:{ "Content-Type":"application/json" },body:JSON.stringify(payload)});
    if(!res.ok){ const err=await res.json().catch(()=>({detail:"Error"})); return alert(err.detail||"Error"); }
    document.getElementById("toast").classList.remove("hidden");
    setTimeout(()=> location.href="/ingresos", 700);
  });
})();

// ======================= INGRESOS (tabla/resumen) =========
(function(){
  const table = document.getElementById("tablaIngresos");
  if(table){
    const tbody = table.querySelector("tbody");
    const filters = document.querySelectorAll(".filter");
    const applyFilters = ()=> tbody.querySelectorAll("tr").forEach(tr=>{
      const ok = Array.from(filters).every(inp=>{
        const col = +inp.dataset.col, val = (inp.value||"").toUpperCase();
        return !val || (tr.children[col]?.textContent||"").toUpperCase().includes(val);
      });
      tr.style.display = ok? "":"none";
    });
    filters.forEach(i=> i.addEventListener("input", applyFilters));
    fetch("/api/ingresos").then(r=>r.json()).then(rows=>{
      tbody.innerHTML="";
      rows.forEach(r=>{
        const num = parseFloat((r.cantidad||"0").replace(".","").replace(",", "."));
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${r.fecha}</td><td>${formatCOPnum(num)}</td><td>${r.semestre}</td><td>${r.banco}</td><td>${r.metodo}</td><td>${r.linea}</td><td>${r.user}</td><td>${r.extra||""}</td>`;
        tbody.appendChild(tr);
      });
    });
    const buildExport = fmt => `/api/ingresos/export2?fmt=${fmt}`;
    document.getElementById("expInCsv")?.addEventListener("click", ()=> location.href = buildExport("csv"));
    document.getElementById("expInXlsx")?.addEventListener("click", ()=> location.href = buildExport("xlsx"));
  }
})();
(function(){
  const tabla = document.getElementById("tablaResumen");
  if(!tabla) return;
  const tbody = tabla.querySelector("tbody");
  const kpiTotal = document.getElementById("kpiTotal");
  const kpiCount = document.getElementById("kpiCount");
  const kpiAvg = document.getElementById("kpiAvg");
  const M = {}; CUENTAS.forEach(c=>{ M[c]=Object.fromEntries(SEMESTRES.map(s=>[s,0])); M[c]["INTERESES"]=0; M[c]["TOTAL"]=0; });
  const parseCant = s=> parseFloat((s||"0").replace(".","").replace(",", "."))||0;

  fetch("/api/ingresos").then(r=>r.json()).then(rows=>{
    const vals = rows.map(r=>parseCant(r.cantidad));
    const sum = vals.reduce((a,b)=>a+b,0);
    kpiTotal.textContent = formatCOPnum(sum);
    kpiCount.textContent = String(rows.length);
    kpiAvg.textContent = formatCOPnum(rows.length? (sum/rows.length):0);

    rows.forEach(r=>{
      if(!CUENTAS.includes(r.banco)) return;
      const c=parseCant(r.cantidad);
      if(r.metodo==="PAGO INTERESES") M[r.banco]["INTERESES"]+=c;
      else if(SEMESTRES.includes(r.semestre)) M[r.banco][r.semestre]+=c;
    });
    CUENTAS.forEach(cta=> M[cta]["TOTAL"]=SEMESTRES.reduce((a,s)=>a+M[cta][s],0)+M[cta]["INTERESES"]);

    tbody.innerHTML="";
    CUENTAS.forEach(cta=>{
      const tr=document.createElement("tr");
      const cells=[cta, ...SEMESTRES.map(s=>M[cta][s]), M[cta]["INTERESES"], M[cta]["TOTAL"]];
      tr.innerHTML = cells.map((v,i)=> i===0?`<td><b>${v}</b></td>`:`<td>${formatCOPnum(v)}</td>`).join("");
      tbody.appendChild(tr);
    });
    const tTot = document.getElementById("rowTotales").children;
    let grand=0; SEMESTRES.forEach((s,i)=>{ let col=0; CUENTAS.forEach(c=> col+=M[c][s]); tTot[1+i].textContent=formatCOPnum(col); grand+=col; });
    let inter=0; CUENTAS.forEach(c=> inter+=M[c]["INTERESES"]); tTot[1+SEMESTRES.length].textContent=formatCOPnum(inter); grand+=inter;
    tTot[1+SEMESTRES.length+1].textContent = formatCOPnum(grand);

    if(window.Chart){
      const ctxStack=document.getElementById("chartStacked");
      const ctxDonut=document.getElementById("chartDonut");
      if(ctxStack) new Chart(ctxStack,{type:'bar',data:{labels:SEMESTRES,datasets:CUENTAS.map(cta=>({label:cta,data:SEMESTRES.map(s=>M[cta][s])}))},options:{plugins:{legend:{position:'bottom'}},scales:{x:{stacked:true},y:{stacked:true}}}});
      if(ctxDonut) new Chart(ctxDonut,{type:'doughnut',data:{labels:CUENTAS,datasets:[{data:CUENTAS.map(c=>M[c]["TOTAL"])}]},options:{plugins:{legend:{position:'bottom'}}}});
    }
  });
})();

// ======================= EGRESOS ===========================
(function(){
  const form = document.getElementById("formEgreso");
  if(form){
    const monto = document.getElementById("e_monto");
    const cuenta = document.getElementById("e_cuenta");
    const metodo = document.getElementById("e_metodo");
    const semestre = document.getElementById("e_semestre");
    const categoria = document.getElementById("e_categoria");
    const dyn = document.getElementById("e_dynamic");
    const autorizo = document.getElementById("e_autorizo");
    const responsable = document.getElementById("e_responsable");

    attachMontoMask(monto);
    hydrateSelect(cuenta, CUENTAS);
    hydrateSelect(semestre, SEMESTRES);
    hydrateSelect(categoria, CATS);

    function hydrateMetodo(){
      const c = upper(cuenta.value||"");
      const list = c.startsWith("BANCOLOMBIA_") ? EGRESO_METODOS["_BANC_"] : (EGRESO_METODOS[c]||["OTRO"]);
      hydrateSelect(metodo, list);
    }
    cuenta.addEventListener("change", hydrateMetodo);
    hydrateMetodo();

    function buildSelect(id,label,arr){
      const wrap = document.createElement("div"); wrap.className="field";
      wrap.innerHTML = `<label>${label}</label><select id="${id}"><option value="">-</option>${arr.map(v=>`<option>${v}</option>`).join("")}</select>`;
      return wrap;
    }
    function buildInput(id,label){
      const w = document.createElement("div"); w.className="field";
      w.innerHTML = `<label>${label}</label><input id="${id}" type="text" placeholder="-">`;
      return w;
    }

    function renderDyn(){
      dyn.innerHTML="";
      const cat = categoria.value;
      const needsMes = CATS_REQUIEREN_MES.has(cat);
      if(cat==="CARROS"){
        dyn.appendChild(buildSelect("e_nombre_carro","NOMBRE CARRO", CARROS_NOMBRES));
        dyn.appendChild(buildSelect("e_motivo_carro","MOTIVO", CARROS_MOTIVOS));
        dyn.appendChild(buildInput("e_razon","RAZÓN"));
      }else if(cat==="DEVOLUCIÓN"){
        dyn.appendChild(buildSelect("e_razon","RAZÓN", ["CANCELACIÓN","PAGO DE MAS","MALA MIGRACIÓN"]));
      }else if(["ADELANTO","PAGO_NÓMINA","VIATICOS","PRIMAS"].includes(cat)){
        dyn.appendChild(buildSelect("e_razon","RAZÓN", EMPLEADOS));
      }else if(cat==="BASE DE DATOS"){
        dyn.appendChild(buildSelect("e_razon","RAZÓN", SEMESTRES));
      }else if(["ITAÚ-APTOS","MERCADO"].includes(cat)){
        dyn.appendChild(buildSelect("e_razon","RAZÓN", ["JESÚS","FELIPE","MARLON"]));
      }else if(cat==="SOFTWARE"){
        dyn.appendChild(buildSelect("e_razon","RAZÓN", ["CAPITAL_BRANCH","GOOGLE_STORAGE","LOOM","PROTON","PUBLICIDAD","RECARGA_CELULAR"]));
      }else if(cat==="IMPUESTOS"){
        dyn.appendChild(buildSelect("e_razon","RAZÓN", ["INDUSTRIA_Y_COMERCIO","RENTA","IVA","RETEFUENTE"]));
      }else if(cat==="CESANTIAS"){
        // razon fija 2025 (backend)
      }else{
        dyn.appendChild(buildInput("e_razon","RAZÓN"));
      }
      if(needsMes){ dyn.appendChild(buildSelect("e_mes","MES", MESES)); }
    }
    categoria.addEventListener("change", renderDyn); renderDyn();

    form.addEventListener("submit", async (e)=>{
      e.preventDefault();
      const payload = {
        monto: monto.value, cuenta: upper(cuenta.value), metodo: upper(metodo.value),
        semestre: upper(semestre.value), categoria: upper(categoria.value),
        mes: upper(document.getElementById("e_mes")?.value || "" ) || null,
        nombre_carro: upper(document.getElementById("e_nombre_carro")?.value || "" ) || null,
        motivo_carro: upper(document.getElementById("e_motivo_carro")?.value || "" ) || null,
        razon: upper(document.getElementById("e_razon")?.value || "" ) || null,
        autorizo: upper(autorizo.value), responsable: upper(responsable.value),
      };
      if(!payload.monto || parseCOP(payload.monto)<=0) return alert("Ingrese MONTO válido");
      if(!payload.cuenta || !payload.metodo || !payload.semestre || !payload.categoria) return alert("Complete obligatorios");
      if(CATS_REQUIEREN_MES.has(payload.categoria) && !payload.mes) return alert("MES es obligatorio");
      if(payload.categoria==="CARROS"){
        if(!payload.nombre_carro || !payload.motivo_carro) return alert("Complete NOMBRE/MOTIVO");
        if(!payload.razon) return alert("RAZÓN obligatoria");
      }
      if(["ADELANTO","PAGO_NÓMINA","VIATICOS","PRIMAS","BASE DE DATOS","ITAÚ-APTOS","MERCADO","SOFTWARE","IMPUESTOS","DEVOLUCIÓN"].includes(payload.categoria) && !payload.razon){
        return alert("RAZÓN obligatoria");
      }

      const res = await fetch("/api/egresos",{method:"POST",headers:{ "Content-Type":"application/json" },body:JSON.stringify(payload)});
      if(!res.ok){ const err=await res.json().catch(()=>({detail:"Error"})); return alert(err.detail||"Error"); }
      document.getElementById("toast").classList.remove("hidden");
      setTimeout(()=> location.href="/egresos", 700);
    });
  }

  const table = document.getElementById("tablaEgresos");
  if(table){
    const tbody = table.querySelector("tbody");
    const filters = document.querySelectorAll(".filter");
    const applyFilters = ()=> tbody.querySelectorAll("tr").forEach(tr=>{
      const ok = Array.from(filters).every(inp=>{
        const col = +inp.dataset.col, val = (inp.value||"").toUpperCase();
        return !val || (tr.children[col]?.textContent||"").toUpperCase().includes(val);
      });
      tr.style.display = ok? "":"none";
    });
    filters.forEach(i=> i.addEventListener("input", applyFilters));

    fetch("/api/egresos").then(r=>r.json()).then(rows=>{
      tbody.innerHTML="";
      rows.forEach(r=>{
        const n1 = parseFloat((r.cantidad||"0").replace(".","").replace(",", "."));
        const n2 = parseFloat((r.cantidad_real||"0").replace(".","").replace(",", "."));
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${r.fecha}</td><td>${r.cuenta}</td><td>${r.metodo}</td><td>${formatCOPnum(n1)}</td><td>${formatCOPnum(n2)}</td><td>${r.semestre}</td><td>${r.categoria}</td><td>${r.razon}</td><td>${r.autorizo}</td><td>${r.responsable}</td>`;
        tbody.appendChild(tr);
      });
    });

    const buildExport = fmt => `/api/egresos/export?fmt=${fmt}`;
    document.getElementById("expEgCsv")?.addEventListener("click", ()=> location.href = buildExport("csv"));
    document.getElementById("expEgXlsx")?.addEventListener("click", ()=> location.href = buildExport("xlsx"));
  }
})();

// ======================= TRANSFERENCIAS ===================
(function(){
  const form = document.getElementById("formTransfer");
  if(form){
    const monto = document.getElementById("t_monto");
    const semestre = document.getElementById("t_semestre");
    const origen = document.getElementById("t_origen");
    const destino = document.getElementById("t_destino");
    const costo = document.getElementById("t_costo");

    attachMontoMask(monto); attachMontoMask(costo);
    hydrateSelect(semestre, SEMESTRES);
    hydrateSelect(origen, CUENTAS);
    hydrateSelect(destino, CUENTAS);

    form.addEventListener("submit", async (e)=>{
      e.preventDefault();
      const payload = { monto:monto.value, semestre:upper(semestre.value), origen:upper(origen.value), destino:upper(destino.value), costo:(costo.value||"")||null };
      if(!payload.monto || parseCOP(payload.monto)<=0) return alert("Ingrese MONTO");
      if(!payload.semestre || !payload.origen || !payload.destino) return alert("Complete campos");
      if(payload.origen===payload.destino) return alert("ORIGEN y DESTINO no pueden ser iguales");
      const res = await fetch("/api/transferencias",{method:"POST",headers:{ "Content-Type":"application/json" },body:JSON.stringify(payload)});
      if(!res.ok){ const err=await res.json().catch(()=>({detail:"Error"})); return alert(err.detail||"Error"); }
      document.getElementById("toast").classList.remove("hidden");
      setTimeout(()=> location.href="/transferencias", 700);
    });
  }

  const tabla = document.getElementById("tablaTransf");
  if(tabla){
    const tbody = tabla.querySelector("tbody");
    fetch("/api/transferencias").then(r=>r.json()).then(rows=>{
      tbody.innerHTML="";
      rows.forEach(r=>{
        const m = parseFloat((r.monto||"0").replace(".","").replace(",", "."));
        const c = parseFloat((r.costo||"0").replace(".","").replace(",", "."));
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${r.fecha}</td><td>${formatCOPnum(m)}</td><td>${r.semestre}</td><td>${r.origen}</td><td>${r.destino}</td><td>${formatCOPnum(c)}</td>`;
        tbody.appendChild(tr);
      });
    });
  }

  const saldos = document.getElementById("tablaSaldos");
  if(saldos){
    const tbody = saldos.querySelector("tbody");
    const btnCsv = document.getElementById("expSaldosCsv");
    const btnXlsx = document.getElementById("expSaldosXlsx");
    fetch("/api/saldos").then(r=>r.json()).then(rows=>{
      tbody.innerHTML="";
      rows.forEach(r=>{
        const tr = document.createElement("tr");
        const n = x => parseFloat((x||"0").replace(".","").replace(",", "."));
        tr.innerHTML = `<td><b>${r["CUENTA"]}</b></td><td>${formatCOPnum(n(r["INGRESOS"]))}</td><td>${formatCOPnum(n(r["EGRESOS"]))}</td><td>${formatCOPnum(n(r["TRANSF (+)"]))}</td><td>${formatCOPnum(n(r["TRANSF (-)"]))}</td><td>${formatCOPnum(n(r["SALDO"]))}</td>`;
        tbody.appendChild(tr);
      });
    });
    btnCsv?.addEventListener("click", ()=> location.href="/api/saldos/export?fmt=csv");
    btnXlsx?.addEventListener("click", ()=> location.href="/api/saldos/export?fmt=xlsx");
  }
})();
