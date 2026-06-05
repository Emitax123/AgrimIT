# Plan 03 — Agilizar la carga de datos

[← Plan maestro](PLAN_MAESTRO.md)

> **Prioridad del usuario** — la carga manual es el cuello de botella principal.
> Cubre la sección 4 de `../ANALISIS_Y_TAREAS.md`.
> Verificá el estado actual de cada archivo antes de editar.

**Estado actual:** todo es manual, campo por campo. Un proyecto tiene ~30 campos visibles (12 de nomenclatura catastral fragmentada), de los cuales solo 2 son obligatorios (`type` y cliente). No hay autocompletado, duplicación, plantillas ni importación. Crear un cliente desde el flujo de proyecto obliga a cambiar de página.

Tareas ordenadas por relación impacto/esfuerzo.

---

### 4.1 Autocompletar datos del cliente al seleccionarlo — esfuerzo bajo
Hoy el dropdown de clientes (`form.html`) solo deshabilita inputs manuales.

- [x] Crear endpoint JSON `clients/<pk>/json/` que devuelva `name`, `phone`, `email`, `id_type`, `id_number`
- [x] Filtrar **siempre** por `user=request.user`
- [x] Script que rellene los campos del form al seleccionar un cliente

### 4.2 Duplicar / clonar proyecto — esfuerzo bajo-medio
Los agrimensores cargan varios proyectos de la misma zona con nomenclatura casi idéntica (cambia la parcela).

- [x] Acción "Duplicar" que copie un `Project` (sin su `Account` ni movimientos, o con `Account` vacío)
- [x] Ruta nueva + vista que clone la instancia (`pk=None`, `save()`)
- [x] Abrir el form de edición con el delta para ajustar lo que cambia

### 4.3 Importación masiva CSV/Excel — esfuerzo medio, MAYOR multiplicador
La mejora de mayor impacto en tiempo. Aplica a `Project`, `Client` y `AccountMovement`.

- [ ] Pantalla de import con subida de archivo
- [ ] Mapeo de columnas → campos del modelo
- [ ] Previsualización y validación fila por fila
- [ ] Commit transaccional
- [ ] Reportar filas con error sin abortar todo el lote
- [ ] Usar `pandas`/`openpyxl` o `csv` stdlib

### 4.4 Crear cliente inline (modal AJAX) — esfuerzo medio

- [ ] Modal "+ Nuevo cliente" dentro del form de proyecto
- [ ] Crear cliente vía POST AJAX y dejarlo seleccionado
- [ ] No perder lo ya cargado en el formulario

### 4.5 Recordar últimos valores — esfuerzo bajo

- [ ] Pre-cargar `partido` / `circ` / `sect` con los del último proyecto creado por el usuario en la sesión

### 4.6 Carga financiera más rápida — esfuerzo bajo
**Archivo:** `account_form.html`

- [x] Botones de monto rápido (aditivos + botón Limpiar)
- [ ] ~~Fecha por defecto = hoy~~ — N/A: `AccountMovement.created_at` es `auto_now_add`, no hay input de fecha editable
- [x] Mostrar en cabecera el contexto del proyecto (cliente + nomenclatura)

---

## Verificación

- [ ] Seleccionar un cliente en el form de proyecto y confirmar que los campos se autocompletan (y que no expone clientes de otros usuarios).
- [ ] Duplicar un proyecto y confirmar que se crea una copia editable sin arrastrar movimientos financieros.
- [ ] Importar un CSV con filas válidas e inválidas → las válidas se cargan, las inválidas se reportan sin abortar.
- [ ] Crear un cliente desde el modal sin perder los datos ya cargados en el proyecto.
- [ ] Confirmar pre-carga de últimos valores y mejoras del form financiero.
