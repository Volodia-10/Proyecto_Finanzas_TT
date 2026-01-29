
# Proyecto_Finanzas_TT (Step 2: EGRESOS + Export + Filtros)
- EGRESOS completos (formulario condicional, tabla, resumen con filtros y gráficos).
- Exportar **CSV/XLSX** para **INGRESOS** y **EGRESOS**, respetando filtros activos.
- Selects **buscables** (contiene, sin acentos) en todo el sistema.
- Estilo oscuro, zebra, bordes, celdas centradas, fecha `dd/mm/aaaa hh:mm:ss`.

## Ejecutar
```bash
pip install fastapi uvicorn pydantic openpyxl
uvicorn app.main:app --reload --port 8000
```

## Rutas
- Inicio: `/`
- Ingresos: `/ingresos/nuevo`, `/ingresos`, `/ingresos/resumen`
- Egresos: `/egresos/nuevo`, `/egresos`, `/egresos/resumen`

## Exportar
- Ingresos: botones en la tabla → llama `/api/ingresos/export2?fmt=csv|xlsx&f0=...`
- Egresos: botones en la tabla → llama `/api/egresos/export?fmt=csv|xlsx&f0=...&f1=...`

## Editar colores
- `static/styles.css` líneas 1–12.
