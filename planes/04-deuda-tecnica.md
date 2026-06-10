# Plan 04 — Deuda técnica

[← Plan maestro](PLAN_MAESTRO.md)

> **Prioridad:** BAJA — mejoras de fondo, ejecutar al final.
> Cubre la sección 5 de `../ANALISIS_Y_TAREAS.md`.
> Verificá el estado actual de cada archivo antes de editar.

---

### 1. Sin tests
No hay suite automatizada. Sugerido: `pytest-django` + `factory-boy`.

- [x] Configurar `pytest-django` + `factory-boy` (`pytest.ini`, `conftest.py` con factories, `requirements-dev.txt`)
- [x] Tests de control de acceso (un usuario no ve/edita datos de otro) — 24 tests en `tests/test_access_control.py`
  - Hallazgo: `full_mod_view` hacía `.get(pk)` sin `try/except` → 500 en cross-user. Endurecido a `redirect('projects')` como sus hermanas.
- [x] Tests de lógica financiera (`networth`, resúmenes mensuales) — 7 tests en `tests/test_financial_logic.py`
- [x] Fix `.gitignore`: la regla `test_*.py` ignoraba toda la suite; anclada a la raíz (`/test_*.py`)

### 2. Lógica de negocio en vistas
Cálculo de patrimonio y actualización de `MonthlyFinancialSummary` viven en `accounting/views.py`.

- [ ] Mover a métodos de modelo o señales `post_save` sobre `AccountMovement`

### 3. Roles de equipo sin uso
`TeamMembership.ROLE_CHOICES` (`member`/`viewer`) existe pero no se aplica en autorización.

- [ ] Crear un `RoleRequiredMixin`
- [ ] Aplicarlo en las vistas de `teams`

### 4. Duplicación de filtrado por usuario
El patrón `filter(user=request.user)` se repite en 15+ vistas FBV.

- [ ] Migrar progresivamente a las CBV base que ya aplican `TenantMixin`

### 5. Índice faltante
`Client` se consulta con `filter(user=..., flag=True)` frecuentemente.

- [x] Agregar `Index(fields=['user', 'flag'])` al modelo `Client` + migración (`0004`)

### 6. Rate limiting con `LocMemCache` en prod
No es distribuido (no escala entre workers de gunicorn).

- [ ] Migrar a Redis (ya previsto en `.env`)

### 7. CSP permisivo
`middleware.py` permite `'unsafe-inline'` en scripts/estilos.

- [x] Endurecer la política CSP — agregadas `object-src 'none'`, `base-uri 'self'`, `frame-ancestors 'self'`, `form-action 'self'` (+ tests).
- [ ] Pendiente (follow-up): quitar `'unsafe-inline'` de `script-src`/`style-src` migrando a nonces por request (requiere refactor de los `<script>` y `style=""` inline en plantillas).

### 8. Logging en prod
Solo stdout.

- [x] Logging estructurado (JSON) para Railway — `JSONFormatter` propio (sin deps) que incluye los `extra=`; handlers de consola de `prod.py` en JSON.

---

## Verificación

- [ ] `pytest` corre y los tests de control de acceso + financieros pasan.
- [ ] Confirmar que el cálculo financiero sigue funcionando tras moverlo a modelos/señales.
- [ ] Probar que un `viewer` no puede ejecutar acciones de `member` en teams.
- [ ] Verificar que las consultas a `Client` usan el índice nuevo (EXPLAIN).
- [ ] Confirmar rate limiting distribuido con Redis entre múltiples workers.
