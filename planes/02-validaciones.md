# Plan 02 — Validación de formularios

[← Plan maestro](PLAN_MAESTRO.md)

> **Prioridad:** MEDIA — ejecutar después del Plan 01.
> Cubre la sección 3 de `../ANALISIS_Y_TAREAS.md`.
> Verificá el estado actual de cada archivo antes de editar.

---

### 1. Montos como texto sin validar
**Archivo:** `agrimIT/apps/accounting/forms.py` (`ManualAccountEntryForm`)

`amount` se maneja como `TextInput` sin validación.

```python
amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0)
# widget numérico
```

- [ ] Cambiar `amount` a `DecimalField` con `max_digits=12, decimal_places=2, min_value=0` y widget numérico
- [ ] Agregar validación de rango a `price` / `adv` / `gasto` en `mod_view` (`apps/project_admin/views.py`)

### 2. `ClientForm` con `fields = '__all__'`
**Archivo:** `agrimIT/apps/clients/forms.py`

Expone el campo `user`.

- [ ] Cambiar a `exclude = ['user', 'flag', 'not_listed']` (o campos explícitos)
- [ ] Asignar `user = request.user` en la vista al guardar

### 3. Validadores en el modelo `Project`
**Archivo:** `agrimIT/apps/project_admin/models.py`

Campos de nomenclatura catastral (`circ`, `sect`, `chacra_num`, etc.) son `CharField(blank=True)` sin validación de patrón.

- [ ] Agregar `validators` donde el formato sea conocido (p. ej. numéricos)
- [ ] Generar migración si los cambios afectan el esquema

### 4. Typo en el modelo `User`
**Archivo:** `agrimIT/apps/users/models.py`

`hone_number` → `phone_number`.

- [ ] Buscar usos de `hone_number` en templates / forms / vistas
- [ ] Renombrar el campo a `phone_number`
- [ ] Generar migración con `RenameField`
- [ ] Actualizar todas las referencias encontradas

---

## Verificación

- [ ] Enviar el form de monto con texto no numérico o negativo → rechazo con error claro.
- [ ] Confirmar que `ClientForm` ya no muestra/permite editar `user`, y que `user` se asigna correctamente al crear.
- [ ] Cargar nomenclatura catastral con formato inválido → error de validación.
- [ ] Confirmar que `phone_number` funciona en alta/edición de usuario y que no quedaron referencias a `hone_number`.
