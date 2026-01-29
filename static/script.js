/* ==== Formateo de dinero en inputs ==== */
function formatMoneyInput(el) {
  const raw = (el.value || "").toString();
  const digits = raw.replace(/[^\d,.\-]/g, "");

  const lastComma = digits.lastIndexOf(",");
  const lastDot   = digits.lastIndexOf(".");
  let decSep = null;
  if (lastComma !== -1 || lastDot !== -1) decSep = lastComma > lastDot ? "," : ".";

  let intPart = digits, decPart = "";
  if (decSep) {
    const p = digits.lastIndexOf(decSep);
    intPart = digits.slice(0, p).replace(/[^\d\-]/g, "");
    decPart = digits.slice(p + 1).replace(/[^\d]/g, "").slice(0, 2);
  } else intPart = digits.replace(/[^\d\-]/g, "");

  const negative = intPart.startsWith("-");
  const abs = intPart.replace("-", "") || "0";
  let pretty = Number(abs).toLocaleString("es-CO");
  if (negative) pretty = "-" + pretty;
  if (decSep && decPart) pretty += decSep + decPart;
  el.value = pretty;
}
function normalizeMoney(text) {
  if (!text) return "0";
  let s = text.toString().trim().replace(/[^\d,.\-]/g, "");
  const lastComma = s.lastIndexOf(","), lastDot = s.lastIndexOf(".");
  if (lastComma > lastDot) s = s.replace(/\./g, "").replace(",", ".");
  else if (lastDot > lastComma) s = s.replace(/,/g, "");
  else if (s.includes(",")) s = s.replace(/\./g, "").replace(",", ".");
  return s || "0";
}
document.addEventListener("input", (e)=>{
  if (e.target && e.target.matches("[data-money]")) formatMoneyInput(e.target);
});

/* ==== Helpers de tablas ==== */
function fmtCOP(n){ return (n ?? 0).toLocaleString("es-CO", {maximumFractionDigits:2}); }
function el(tag, attrs={}, ...children){
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([k,v])=>{
    if(k==="class") node.className=v;
    else if(k==="html") node.innerHTML=v;
    else node.setAttribute(k,v);
  });
  children.forEach(c => node.append(c));
  return node;
}
