# Importación masiva de proyectos (CSV) — Diseño

Fecha: 2026-06-05 · Plan 03, tarea 4.3 · Rama: `fix/plan-03-carga-datos`

## Contexto

La carga manual de proyectos campo por campo es el cuello de botella principal del sistema (Plan 03). Los agrimensores suelen cargar varios proyectos de la misma zona. Esta feature permite crear muchos proyectos de una vez a partir de un archivo, controlando errores fila por fila.

Decisiones acordadas con el usuario:

- **Solo se importan proyectos.** Los clientes deben existir previamente.
- Cada fila referencia a su cliente por **ID interno** (`cliente_id`).
- Se provee una **plantilla Excel (.xlsx) descargable** con dos hojas: **Proyectos** (encabezados fijos para cargar) y **Clientes** (referencia ID → Nombre del usuario). No hace falta paso de mapeo manual de columnas.
- La subida acepta **`.xlsx` y `.csv`** (se detecta el formato por la firma de bytes). Usa `openpyxl` para Excel y el módulo `csv` de la stdlib para CSV. **Dependencia agregada: `openpyxl`** (revierte la decisión inicial de "solo CSV", a pedido del usuario para poder tener la lista de clientes en una hoja aparte).
- Flujo de **un solo paso** (Enfoque A): subir → validar todo → crear solo las filas válidas en una transacción → reportar las inválidas sin abortar el lote.

## Arquitectura

Todo vive en `apps/project_admin`. Aislamiento por `request.user` en todo el flujo.

```
[Pantalla Importar /projects/import/]
   ├─ (link) Descargar plantilla  ──► /projects/import/template/  (CSV con encabezados)
   ├─ Tabla de referencia: tus clientes (ID — Nombre)
   └─ Form de subida (.csv)
        │ POST
        ▼
   import_view:
     1. CsvImportForm valida extensión (.csv) y tamaño
     2. parse_and_validate(file, clients_by_id)  →  (válidas, errores)
     3. transaction.atomic(): por cada válida → save() + create_account() + save_in_history()
     4. render reporte: "N creados" + tabla (fila, motivo)
```

### Componentes

- **`importers.py`** (módulo nuevo, puro: sin HTTP ni DB):
  - `TEMPLATE_HEADERS`, `COLUMN_MAP` (encabezado → campo, sin `cliente_id`), `FIELD_TO_HEADER` (inverso, para mensajes), `MAX_ROWS = 1000`, `TIPO_VALUES`/`TIPO_MENS_VALUES`, nombres de hoja `PROJECTS_SHEET`/`CLIENTS_SHEET`.
  - `_rows_from_upload(uploaded_file)`: detecta `.xlsx` (firma `PK`) vs `.csv` y devuelve `(rows, error)` como lista de filas (lista de celdas en texto). Excel: lee la hoja "Proyectos"; CSV: `utf-8-sig` + `csv.reader`.
  - `parse_and_validate(uploaded_file, clients_by_id) -> (valid, errors)`: ignora líneas de comentario (`#`), detecta el encabezado, verifica columnas requeridas, y por fila resuelve `cliente_id` y valida el resto con **`ProjectForm`** (reusa los validadores catastrales del Plan 02). El número reportado es la **línea/fila real** del archivo.
  - `build_template_xlsx(clients) -> bytes`: arma el workbook con hoja "Proyectos" (encabezados) + hoja "Clientes" (`cliente_id`, Nombre).

- **`forms.py` → `CsvImportForm`**: `FileField` con `FileExtensionValidator(['xlsx', 'csv'])` + límite `MAX_UPLOAD_SIZE`.

- **`views.py`**:
  - `import_view(request)`: GET muestra la pantalla; POST commitea las válidas y arma el reporte. Setea `instance.user = request.user` antes de guardar.
  - `import_template_csv(request)`: devuelve el `.xlsx` generado por `build_template_xlsx` con los clientes del usuario.

- **`urls.py`**: `projects/import/` → `import_view`; `projects/import/template/` → `import_template_csv` (descarga `.xlsx`).

- **Templates**: `project_admin/import_form.html` (instrucciones + callout resaltado de valores válidos + descarga; **sin** tabla de clientes, que ahora vive en la hoja "Clientes") y `project_admin/import_result.html` (resumen + tabla de errores).

- **UI**: botón "📥 Importar proyectos" en el listado de proyectos. (El ID del cliente se ve en la hoja "Clientes" de la plantilla; también se muestra en el listado de clientes.)

## Mapeo de columnas

| Columna CSV | Campo modelo | Obligatorio |
|---|---|---|
| `tipo` | type | ✅ (Estado Parcelario / Mensura / Amojonamiento / Relevamiento / Legajo Parcelario) |
| `cliente_id` | client | ✅ (ID de un cliente del usuario) |
| `tipo_mensura` | type_mens | — |
| `partido` / `partida` / `circunscripcion` / `seccion` | partido / partida / circ / sect | — |
| `chacra_num`/`chacra_letra` … `parcela_num`/`parcela_letra` / `subparcela` | chacra_num/chacra_let … / subparcela | — (`_num` solo dígitos) |
| `calle` / `altura` / `piso` / `depto` | street / street_num / floor / dept | — |
| `titular_nombre` / `titular_telefono` / `nro_tramite` | titular_name / titular_phone / process_num | — |

Columnas extra en el archivo se ignoran; columnas opcionales faltantes se toman como vacías.

## Manejo de errores y casos borde

- Los mensajes por fila **nombran la columna del CSV** (ej. `tipo: ...`, `chacra_num: ...`) y para `tipo` listan los valores válidos. El número reportado es la **línea real del archivo** (cuenta comentarios y filas en blanco).
- La plantilla descargada incluye una **guía embebida** como líneas `#` (valores válidos de `tipo`/`tipo_mensura`, obligatorios, etc.). El importador ignora toda línea que empiece con `#`; las líneas de guía no llevan comas para sobrevivir el reguardado de Excel.
- `cliente_id` ajeno/inexistente/no numérico → `cliente N no encontrado` (no expone datos de otros usuarios).
- `tipo` fuera de choices, `_num` no numérico, `nro_tramite` no entero → motivo claro por fila (prefijado con el nombre de la columna).
- Archivo vacío o sin filas de datos → aviso; fila totalmente vacía → se saltea; encoding inválido → mensaje amigable; más de `MAX_ROWS` filas → se procesan las primeras y se avisa.
- El commit es transaccional pero solo sobre las filas válidas; las inválidas nunca abortan el lote.

## Verificación

- **Manual**: descargar plantilla → 4 filas (2 válidas, 1 `tipo` inválido, 1 `cliente_id` ajeno) → subir → "2 creados" + 2 fallidas reportadas; los 2 proyectos quedan con cuenta vacía y en el listado.
- **Aislamiento**: `cliente_id` de otro usuario → "cliente no encontrado".
- `parse_and_validate` es pura → lista para tests unitarios en el Plan 04.
