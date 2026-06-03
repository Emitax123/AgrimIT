# Plan 04 — Deuda técnica

[← Plan maestro](PLAN_MAESTRO.md)

> **Prioridad:** BAJA — mejoras de fondo, ejecutar al final.
> Cubre la sección 5 de `../ANALISIS_Y_TAREAS.md`.
> Verificá el estado actual de cada archivo antes de editar.

---

### 1. Sin tests
No hay suite automatizada. Sugerido: `pytest-django` + `factory-boy`.

- [ ] Configurar `pytest-django` + `factory-boy`
- [ ] Tests de control de acceso (un usuario no ve/edita datos de otro)
- [ ] Tests de lógica financiera (`networth`, resúmenes mensuales)

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

- [ ] Agregar `Index(fields=['user', 'flag'])` al modelo `Client` + migración

### 6. Rate limiting con `LocMemCache` en prod
No es distribuido (no escala entre workers de gunicorn).

- [ ] Migrar a Redis (ya previsto en `.env`)

### 7. CSP permisivo
`middleware.py` permite `'unsafe-inline'` en scripts/estilos.

- [ ] Endurecer la política CSP cuando sea posible

### 8. Logging en prod
Solo stdout.

- [ ] Considerar logging estructurado (JSON) para Railway

---

## Verificación

- [ ] `pytest` corre y los tests de control de acceso + financieros pasan.
- [ ] Confirmar que el cálculo financiero sigue funcionando tras moverlo a modelos/señales.
- [ ] Probar que un `viewer` no puede ejecutar acciones de `member` en teams.
- [ ] Verificar que las consultas a `Client` usan el índice nuevo (EXPLAIN).
- [ ] Confirmar rate limiting distribuido con Redis entre múltiples workers.
