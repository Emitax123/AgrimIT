# Importación masiva de proyectos (CSV) — Diseño

Fecha: 2026-06-05 · Plan 03, tarea 4.3 · Rama: `fix/plan-03-carga-datos`

## Contexto

La carga manual de proyectos campo por campo es el cuello de botella principal del sistema (Plan 03). Los agrimensores suelen cargar varios proyectos de la misma zona. Esta feature permite crear muchos proyectos de una vez a partir de un archivo, controlando errores fila por fila.

Decisiones acordadas con el usuario:

- **Solo se importan proyectos.** Los clientes deben existir previamente.
- Cada fila referencia a su cliente por **ID interno** (`cliente_id`).
- Se provee una **plantilla CSV descargable** con encabezados fijos → no hace falta paso de mapeo manual de columnas.
- Formato **CSV** únicamente, con el módulo `csv` de la stdlib (**cero dependencias nuevas**; el proyecto no tiene pandas/openpyxl).
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
  - `TEMPLATE_HEADERS`: lista ordenada de encabezados.
  - `COLUMN_MAP`: dict `encabezado_csv → campo_modelo` (sin `cliente_id`, que se maneja aparte).
  - `MAX_ROWS = 1000`: tope por lote.
  - `parse_and_validate(uploaded_file, clients_by_id) -> (valid, errors)`:
    - Decodifica UTF-8 con BOM (`utf-8-sig`); `csv.DictReader`.
    - Verifica encabezados requeridos (`tipo`, `cliente_id`); si faltan → error de archivo `(0, motivo)`.
    - Por fila (numerada desde 2): saltea filas totalmente vacías; resuelve `cliente_id` contra `clients_by_id`; valida el resto con **`ProjectForm`** (reusa los validadores catastrales del Plan 02, exige `type`, hace opcionales `titular_*`/`type_mens`).
    - Devuelve `valid = [(nro_fila, instancia_sin_guardar_con_client)]` y `errors = [(nro_fila, motivo)]`.

- **`forms.py` → `CsvImportForm`**: `FileField` con `FileExtensionValidator(['csv'])` + límite `MAX_UPLOAD_SIZE`, espejando el `FileFieldForm` existente.

- **`views.py`**:
  - `import_view(request)`: GET muestra la pantalla; POST commitea las válidas y arma el reporte. Setea `instance.user = request.user` antes de guardar.
  - `import_template_csv(request)`: `HttpResponse` `text/csv` con `Content-Disposition: attachment`, BOM para Excel y la fila de encabezados.

- **`urls.py`**: `projects/import/` → `import_view`; `projects/import/template/` → `import_template_csv`.

- **Templates**: `project_admin/import_form.html` (instrucciones + descarga + tabla de clientes + subida) y `project_admin/import_result.html` (resumen + tabla de errores).

- **UI**: botón "📥 Importar proyectos" en el listado de proyectos; mostrar el ID en el listado de clientes (`clients_template.html`) para que el usuario conozca los `cliente_id`.

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

- `cliente_id` ajeno/inexistente/no numérico → `cliente N no encontrado` (no expone datos de otros usuarios).
- `tipo` fuera de choices, `_num` no numérico, `nro_tramite` no entero → motivo claro por fila (prefijado con la etiqueta del campo).
- Archivo vacío o sin filas de datos → aviso; fila totalmente vacía → se saltea; encoding inválido → mensaje amigable; más de `MAX_ROWS` filas → se procesan las primeras y se avisa.
- El commit es transaccional pero solo sobre las filas válidas; las inválidas nunca abortan el lote.

## Verificación

- **Manual**: descargar plantilla → 4 filas (2 válidas, 1 `tipo` inválido, 1 `cliente_id` ajeno) → subir → "2 creados" + 2 fallidas reportadas; los 2 proyectos quedan con cuenta vacía y en el listado.
- **Aislamiento**: `cliente_id` de otro usuario → "cliente no encontrado".
- `parse_and_validate` es pura → lista para tests unitarios en el Plan 04.
