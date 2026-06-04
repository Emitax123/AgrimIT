# 🗺️ Plan maestro — AgrimIT

Índice y tablero de progreso de los planes derivados de [`../ANALISIS_Y_TAREAS.md`](../ANALISIS_Y_TAREAS.md).

## 📌 Instrucciones para Claude

1. Al trabajar una sección, **abrí el plan temático correspondiente** (links abajo) y seguí sus pasos.
2. Al completar una tarea, **marcá su check en el plan temático Y en el tablero de abajo** (`- [ ]` → `- [x]`).
3. Este archivo es la **fuente de verdad** de "qué falta". El tablero es la vista resumida; el detalle vive en cada plan.
4. Antes de editar código, **verificá el estado actual del archivo** (las líneas del análisis pueden haberse movido).
5. Para cambios de modelos: crear migración. Verificar siempre el aislamiento por usuario.

**Leyenda:** `[ ]` pendiente · `[x]` hecho

---

## 🔢 Orden de trabajo sugerido

1. **Plan 01** (Seguridad + Finanzas) — bajo riesgo, alto valor. ⚠️ Confirmar fórmula de `networth` con el usuario.
2. **Plan 02** (Validaciones).
3. **Plan 03** — carga rápida: tareas 4.1 + 4.2 + 4.6.
4. **Plan 03** — importación masiva: tarea 4.3 (mayor impacto en tiempo).
5. **Plan 04** (Deuda técnica), empezando por tests de control de acceso.

---

## 📋 Planes y tablero de progreso

### [Plan 01 — Seguridad y lógica financiera](01-seguridad-y-finanzas.md)
Bugs de seguridad (IDOR, decoradores, validación de archivos) y errores de cálculo financiero. **Primero.**

- [x] A.1 — Fix IDOR en `clientedislist` (CRÍTICO)
- [x] A.2 — `@login_required` en `deleteclient`
- [x] A.3 — Validación de archivos subidos (extensión + tamaño)
- [x] A.4 — Whitelist de campos en `SearchMixin`
- [x] A.6 — Refuerzo de aislamiento por usuario (dropdown clientes + 3 IDOR más, hallado en testing)
- [ ] A.5 — Rotación de credenciales (acción manual del usuario)
- [x] B.1 — Corregir `Account.networth` → `advance - expense`
- [x] B.2 — `unique_together` con `user` + migración `0005` (aplicada ✓)
- [x] B.3 — Eliminar `except:` silencioso en `mod_view`

### [Plan 02 — Validación de formularios](02-validaciones.md)
Montos validados, `ClientForm` sin exponer `user`, validadores catastrales, typo `phone_number`.

- [ ] Montos como `DecimalField` + rango en `mod_view`
- [ ] `ClientForm` con `exclude` + asignar `user` en vista
- [ ] Validadores de nomenclatura catastral en `Project`
- [ ] Typo `hone_number` → `phone_number` + `RenameField`

### [Plan 03 — Agilizar la carga de datos](03-carga-de-datos.md)
**Prioridad del usuario.** Autocompletado, duplicación, importación masiva, cliente inline.

- [ ] 4.1 — Autocompletar cliente (endpoint JSON + script)
- [ ] 4.2 — Duplicar / clonar proyecto
- [ ] 4.3 — Importación masiva CSV/Excel (mayor multiplicador)
- [ ] 4.4 — Crear cliente inline (modal AJAX)
- [ ] 4.5 — Recordar últimos valores en sesión
- [ ] 4.6 — Carga financiera más rápida

### [Plan 04 — Deuda técnica](04-deuda-tecnica.md)
Tests, refactors, roles de equipo, índices, Redis, CSP, logging. **Al final.**

- [ ] Tests (pytest-django + factory-boy)
- [ ] Mover lógica de negocio a modelos/señales
- [ ] `RoleRequiredMixin` para teams
- [ ] Migrar FBV → CBV con `TenantMixin`
- [ ] Índice `['user', 'flag']` en `Client`
- [ ] Rate limiting → Redis
- [ ] Endurecer CSP
- [ ] Logging estructurado (JSON)
