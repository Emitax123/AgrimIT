# AgrimIT — Análisis técnico y plan de tareas

> Documento de handoff para Claude Code. Contiene hallazgos con rutas/líneas concretas y tareas accionables ordenadas por prioridad. Verificá siempre el estado actual del archivo antes de editar, ya que las líneas pueden haberse movido.

**Stack:** Django 5.2 · SQLite (dev) / PostgreSQL en Railway (prod) · Supabase (solo storage de archivos) · apps: `users`, `clients`, `project_admin`, `accounting`, `teams`, `utils`.

**Dominio:** Gestión de proyectos y finanzas para agrimensores. La carga manual de datos es el cuello de botella principal del usuario.

---

## 0. Resumen ejecutivo

Arquitectura sólida (multi-tenancy vía `TenantMixin`, settings separados, transacciones atómicas, buen uso de `select_related`/`prefetch_related`, módulo de equipos bien modelado). Los problemas se concentran en: **un IDOR real**, **errores de lógica financiera**, **falta de validación de montos y archivos**, y **un flujo de carga de datos 100% manual sin atajos**.

Prioridades:
1. Corregir bugs de seguridad y de cálculo financiero (bajo riesgo, alto valor).
2. Agregar validación de montos y archivos.
3. Agilizar la carga de datos (objetivo declarado del usuario).
4. Deuda técnica: tests, mover lógica de negocio a modelos/señales, roles de equipo.

---

## 1. Bugs de seguridad (corregir primero)

### 1.1 IDOR en `clientedislist` — CRÍTICO
**Archivo:** `agrimIT/apps/clients/views.py`

```python
@login_required
def clientedislist(request, pk):
    client = Client.objects.get(pk=pk)   # ❌ sin filtro por usuario
    client.not_listed = True
    client.save()
    return redirect('clients')
```

Cualquier usuario autenticado puede ocultar el cliente de otro cambiando el `pk` en la URL.

**Fix:** filtrar por dueño y manejar el `DoesNotExist`.

```python
@login_required
def clientedislist(request, pk):
    client = get_object_or_404(Client, pk=pk, user=request.user)
    client.not_listed = True
    client.save()
    return redirect('clients')
```

### 1.2 `deleteclient` sin `@login_required`
**Archivo:** `agrimIT/apps/clients/views.py`

La vista filtra por `user=request.user`, pero le falta el decorador `@login_required`. Agregarlo por consistencia y defensa en capas.

### 1.3 Validación de archivos subidos ausente
**Archivo:** `agrimIT/apps/project_admin/forms.py` (`FileFieldForm` / `MultipleFileField`)

`file_field = forms.FileField()` no valida extensión, tipo MIME, tamaño ni cantidad antes de enviar a Supabase. Agregar:
- Lista blanca de extensiones (p. ej. `.pdf`, `.jpg`, `.png`, `.dwg`, `.docx`).
- Límite de tamaño por archivo (ya existe `FILE_UPLOAD_MAX_MEMORY_SIZE = 10MB` en `prod.py`; validarlo también en el form con un mensaje claro).
- Límite de cantidad de archivos.

### 1.4 Construcción dinámica de `Q(**{f"{field}__icontains": ...}})` en `SearchMixin`
**Archivo:** `agrimIT/apps/utils/mixins.py`

El nombre de campo viene de configuración interna, no del usuario, así que el riesgo es bajo, pero conviene validar `field` contra una lista blanca de campos buscables para evitar exponer relaciones por error.

### 1.5 Rotación de credenciales (acción del usuario, no código)
El `.env` está correctamente en `.gitignore` y **no** está versionado. Aun así contiene `SECRET_KEY`, password de PostgreSQL y key de Supabase en texto plano. Si el archivo se compartió alguna vez, rotar esas credenciales.

---

## 2. Errores de lógica financiera (corregir)

### 2.1 `Account.networth` usa un campo inexistente
**Archivo:** `agrimIT/apps/accounting/models.py`

```python
@property
def networth(self):
    return self.expenses - self.advance   # ❌ 'expenses' no existe (es 'expense')
```

El campo del modelo es `expense` (singular), no `expenses` → esto rompe o calcula mal el patrimonio. Revisar la fórmula correcta del negocio. Lo esperado probablemente sea:

```python
@property
def networth(self):
    return self.estimated - self.expense - self.advance
```

> ⚠️ Confirmar la fórmula con el usuario antes de cerrar: la relación entre `estimated` (presupuesto), `expense` (gasto) y `advance` (anticipo) define el saldo. No asumir sin validar.

### 2.2 `MonthlyFinancialSummary.unique_together` sin `user`
**Archivo:** `agrimIT/apps/accounting/models.py`

```python
class Meta:
    unique_together = ['year', 'month']   # ❌ falta 'user'
```

Dos usuarios distintos no pueden tener el mismo año/mes. Cambiar a:

```python
unique_together = ['user', 'year', 'month']
```

Generar la migración correspondiente (`makemigrations accounting`). Si ya hay datos, validar que no existan filas en conflicto antes de migrar.

### 2.3 Conversión de montos con `except:` silencioso
**Archivo:** `agrimIT/apps/project_admin/views.py` (`mod_view`)

```python
try:
    project_instance.account.estimated = Dec(price)
except:
    project_instance.account.estimated = Dec("0,00")   # ❌ traga cualquier error
```

Problemas: captura genérica (`except:`), y un dato mal cargado se convierte silenciosamente en 0,00. Reemplazar por captura específica (`InvalidOperation`, `ValueError`, `TypeError`) y devolver un error de formulario en vez de cero silencioso.

---

## 3. Validación de formularios

### 3.1 Montos como texto sin validar
**Archivo:** `agrimIT/apps/accounting/forms.py` (`ManualAccountEntryForm`)

`amount` se maneja como `TextInput` sin validación. Usar `forms.DecimalField(max_digits=12, decimal_places=2, min_value=0)` con widget numérico. Agregar validación de rango también a `price`/`adv`/`gasto` en `mod_view`.

### 3.2 `ClientForm` con `fields = '__all__'`
**Archivo:** `agrimIT/apps/clients/forms.py`

Expone el campo `user`. Cambiar a campos explícitos o `exclude = ['user', 'flag', 'not_listed']` y asignar `user` en la vista.

### 3.3 Validadores en el modelo `Project`
**Archivo:** `agrimIT/apps/project_admin/models.py`

Campos de nomenclatura catastral (`circ`, `sect`, `chacra_num`, etc.) son `CharField(blank=True)` sin validación de patrón. Agregar `validators` donde el formato sea conocido (p. ej. numéricos).

### 3.4 Typo en el modelo `User`
**Archivo:** `agrimIT/apps/users/models.py`

`hone_number` → debería ser `phone_number`. Requiere migración con `RenameField`. Buscar usos en templates/forms/vistas antes de renombrar.

---

## 4. Agilizar la carga de datos (PRIORIDAD del usuario)

**Estado actual:** todo es manual, campo por campo. Un proyecto tiene ~30 campos visibles (12 de ellos de nomenclatura catastral fragmentada), de los cuales solo 2 son obligatorios (`type` y cliente). No hay autocompletado, duplicación, plantillas ni importación. Crear un cliente desde el flujo de proyecto obliga a cambiar de página.

Tareas ordenadas por relación impacto/esfuerzo:

### 4.1 Autocompletar datos del cliente al seleccionarlo (esfuerzo bajo)
Hoy el dropdown de clientes (`form.html`) solo deshabilita los inputs manuales. Crear un endpoint JSON `clients/<pk>/json/` que devuelva `name`, `phone`, `email`, `id_type`, `id_number`, y un pequeño script que rellene los campos al seleccionar. Filtrar siempre por `user=request.user`.

### 4.2 Duplicar / clonar proyecto (esfuerzo bajo-medio)
Los agrimensores cargan varios proyectos de la misma zona con nomenclatura casi idéntica (mismo partido/circunscripción/sección, cambia la parcela). Agregar acción "Duplicar" que copie un `Project` (sin su `Account` ni movimientos, o con `Account` vacío) y abra el form de edición con el delta. Ruta nueva + vista que clone instancia (`pk=None`, `save()`).

### 4.3 Importación masiva CSV/Excel (esfuerzo medio, MAYOR multiplicador)
Pantalla de import con: subida de archivo, mapeo de columnas → campos del modelo, previsualización y validación fila por fila, commit transaccional. Aplica a `Project`, `Client` y `AccountMovement`. Usar `pandas`/`openpyxl` o el `csv` stdlib. Reportar filas con error sin abortar todo el lote.

### 4.4 Crear cliente inline (modal AJAX) (esfuerzo medio)
Modal "+ Nuevo cliente" dentro del form de proyecto que cree el cliente vía POST AJAX y lo deje seleccionado, sin perder lo ya cargado en el formulario.

### 4.5 Recordar últimos valores (esfuerzo bajo)
Pre-cargar `partido`/`circ`/`sect` con los del último proyecto creado por el usuario en la sesión (son los que más se repiten dentro de una jornada).

### 4.6 Carga financiera más rápida (esfuerzo bajo)
En `account_form.html`: botones de monto rápido, fecha por defecto = hoy, y mostrar en cabecera el contexto del proyecto (cliente + nomenclatura) para no tener que recordarlo.

---

## 5. Deuda técnica (mejoras de fondo)

- **Sin tests.** No hay suite automatizada. Empezar por tests de las vistas con control de acceso (que un usuario no vea/edite datos de otro) y de la lógica financiera (`networth`, resúmenes mensuales). Sugerido: `pytest-django` + `factory-boy`.
- **Lógica de negocio en vistas.** Cálculo de patrimonio y actualización de `MonthlyFinancialSummary` viven en `accounting/views.py`. Mover a métodos de modelo o señales `post_save` sobre `AccountMovement`.
- **Roles de equipo sin uso.** `TeamMembership.ROLE_CHOICES` (`member`/`viewer`) existe pero no se aplica en autorización. Crear un `RoleRequiredMixin` y usarlo en las vistas de teams.
- **Duplicación de filtrado por usuario.** El patrón `filter(user=request.user)` se repite en 15+ vistas FBV. Migrarlas progresivamente a las CBV base que ya aplican `TenantMixin`.
- **Índice faltante.** `Client` se consulta con `filter(user=..., flag=True)` frecuentemente; agregar `Index(fields=['user', 'flag'])`.
- **Rate limiting con `LocMemCache` en prod.** No es distribuido (no escala entre workers de gunicorn). Migrar a Redis (ya aparece previsto en `.env`).
- **CSP permisivo.** `middleware.py` permite `'unsafe-inline'` en scripts/estilos. Endurecer cuando se pueda.
- **Logging en prod.** Solo stdout. Considerar logging estructurado (JSON) para Railway.

---

## 6. Orden de trabajo sugerido

1. Sección 1 (seguridad) + Sección 2 (lógica financiera) — bajo riesgo, alto valor. **Confirmar la fórmula de `networth` con el usuario.**
2. Sección 3 (validaciones).
3. Sección 4.1 + 4.2 + 4.6 (agilización rápida de carga).
4. Sección 4.3 (importación masiva) — la mejora de mayor impacto en tiempo.
5. Sección 5 (deuda técnica), empezando por tests de control de acceso.

> Para cada cambio: crear migración cuando toque modelos, correr la suite (cuando exista) y verificar manualmente el aislamiento por usuario.
