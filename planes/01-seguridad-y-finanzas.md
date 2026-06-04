# Plan 01 — Seguridad y lógica financiera

[← Plan maestro](PLAN_MAESTRO.md)

> **Prioridad:** ALTA — primer plan a ejecutar. Bajo riesgo, alto valor.
> Cubre las secciones 1 (bugs de seguridad) y 2 (lógica financiera) de `../ANALISIS_Y_TAREAS.md`.
> Verificá el estado actual de cada archivo antes de editar (las líneas pueden haberse movido).

---

## Parte A — Bugs de seguridad

### A.1 IDOR en `clientedislist` — CRÍTICO
**Archivo:** `agrimIT/apps/clients/views.py`

Cualquier usuario autenticado puede ocultar el cliente de otro cambiando el `pk` en la URL, porque la consulta no filtra por dueño.

```python
# ❌ actual
@login_required
def clientedislist(request, pk):
    client = Client.objects.get(pk=pk)   # sin filtro por usuario
    client.not_listed = True
    client.save()
    return redirect('clients')

# ✅ fix
@login_required
def clientedislist(request, pk):
    client = get_object_or_404(Client, pk=pk, user=request.user)
    client.not_listed = True
    client.save()
    return redirect('clients')
```

- [x] Filtrar por `user=request.user` con `get_object_or_404`
- [x] Confirmar que `get_object_or_404` está importado en el módulo

### A.2 `deleteclient` sin `@login_required`
**Archivo:** `agrimIT/apps/clients/views.py`

La vista ya filtra por `user=request.user`, pero le falta el decorador. Agregarlo por defensa en capas.

- [x] Agregar `@login_required` a `deleteclient`

### A.3 Validación de archivos subidos
**Archivo:** `agrimIT/apps/project_admin/forms.py` (`FileFieldForm` / `MultipleFileField`)

`file_field = forms.FileField()` no valida extensión, tipo MIME, tamaño ni cantidad antes de enviar a Supabase.

- [x] Lista blanca de extensiones (`.pdf`, `.jpg`, `.jpeg`, `.png`, `.dwg`, `.docx`) vía `FileExtensionValidator`
- [x] Límite de tamaño por archivo (`MAX_UPLOAD_SIZE`, basado en `FILE_UPLOAD_MAX_MEMORY_SIZE`, con mensaje claro en `clean_file_field`)
- [x] Límite de cantidad de archivos — N/A: `FileFieldForm` (el que usa `upload_files`) sube de a un archivo. `MultipleFileField` no se usa en el flujo de carga.

### A.4 Whitelist de campos buscables en `SearchMixin`
**Archivo:** `agrimIT/apps/utils/mixins.py`

`Q(**{f"{field}__icontains": ...})` construye el lookup dinámicamente. El `field` viene de config interna (riesgo bajo), pero conviene validarlo contra una lista blanca para no exponer relaciones por error.

- [x] Validar `field` contra los campos reales del modelo (`_meta.get_fields()`); los desconocidos se ignoran y se loguean

### A.5 Rotación de credenciales — acción manual del usuario
El `.env` está en `.gitignore` y no está versionado, pero contiene `SECRET_KEY`, password de PostgreSQL y key de Supabase en texto plano. Si alguna vez se compartió, rotar.

- [ ] (Usuario) Verificar si el `.env` se compartió y rotar credenciales si corresponde

---

## Parte B — Lógica financiera

### B.1 `Account.networth` usa un campo inexistente
**Archivo:** `agrimIT/apps/accounting/models.py`

```python
# ❌ 'expenses' no existe (el campo es 'expense')
@property
def networth(self):
    return self.expenses - self.advance
```

Fórmula probable esperada:

```python
@property
def networth(self):
    return self.estimated - self.expense - self.advance
```

> ⚠️ **CONFIRMAR LA FÓRMULA CON EL USUARIO** antes de cerrar. La relación entre `estimated` (presupuesto), `expense` (gasto) y `advance` (anticipo) define el saldo. No asumir.

- [x] Confirmar fórmula correcta con el usuario → **`advance - expense`** (ganancia neta)
- [x] Corregir `networth` con la fórmula confirmada

### B.2 `MonthlyFinancialSummary.unique_together` sin `user`
**Archivo:** `agrimIT/apps/accounting/models.py`

```python
# ❌ dos usuarios no pueden tener el mismo año/mes
class Meta:
    unique_together = ['year', 'month']

# ✅
unique_together = ['user', 'year', 'month']
```

- [x] Agregar `user` al `unique_together` (+ índice `acc_summary_user_ym_idx`)
- [ ] Validar que no existan filas en conflicto en datos actuales (chequear antes de migrar)
- [x] Migración creada a mano: `0005_alter_monthlyfinancialsummary_user.py` — ⏳ pendiente correr `migrate` (no se pudo en este entorno: venv roto / Python 3.11 ausente)

### B.3 Conversión de montos con `except:` silencioso
**Archivo:** `agrimIT/apps/project_admin/views.py` (`mod_view`)

```python
# ❌ traga cualquier error y convierte dato malo en 0,00
try:
    project_instance.account.estimated = Dec(price)
except:
    project_instance.account.estimated = Dec("0,00")
```

- [x] Reemplazar `except:` por captura específica (`InvalidOperation`, `ValueError`, `TypeError`) en los 3 bloques (price/adv/gasto)
- [x] Devolver error en vez de cero silencioso (render con mensaje por campo + warning logueado)

---

## Verificación

- [ ] Loguearse con dos usuarios distintos y confirmar que el usuario B no puede ocultar/borrar clientes del usuario A (probar `pk` ajeno en la URL → 404).
- [ ] Subir un archivo con extensión/tamaño inválido y confirmar que el form lo rechaza con mensaje claro.
- [ ] Verificar `networth` con valores conocidos según la fórmula confirmada.
- [ ] Confirmar que la migración de `MonthlyFinancialSummary` corre sin conflictos y que dos usuarios pueden tener el mismo año/mes.
- [ ] Cargar un monto inválido en `mod_view` y confirmar que aparece error de form (no `0,00` silencioso).
