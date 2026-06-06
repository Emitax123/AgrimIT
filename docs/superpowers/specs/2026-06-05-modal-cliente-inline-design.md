# Spec — Modal "Nuevo cliente" inline (Plan 03, tarea 4.4)

Fecha: 2026-06-05 · Rama: `fix/plan-03-carga-datos`

## Objetivo
Permitir crear un cliente sin salir del formulario de proyecto, dejándolo
seleccionado y sin perder los datos ya cargados del proyecto.

## Decisiones (acordadas con el usuario)
- El modal es la **única vía de alta** de cliente desde el form de proyecto.
  Los inputs manuales `client-name` / `client-phone` pasan a ser **solo-lectura**
  (display del cliente elegido, autocompletado por la tarea 4.1).
- Campos del modal: **mínimo** — `Nombre` (requerido) + `Teléfono`.

## Backend
1. **Nuevo endpoint AJAX** en `apps/clients/views.py`:
   - Ruta `clients/create/ajax/`, name `client_create_ajax`.
   - `@login_required`, solo POST.
   - Crea `Client(user=request.user, name, phone, flag=True)` (mismo patrón que
     el alta existente; `id_type` default `DNI`, `id_number` vacío).
   - Registra evento `'newc'` vía `save_client_history`.
   - Éxito → `JsonResponse({'id': pk, 'name': name})`.
   - Nombre vacío → `JsonResponse({'error': ...}, status=400)`.
2. **Limpieza de `create_view`** (project_admin): se elimina el branch que creaba
   un cliente "a medias" desde `client-name` al guardar. Si no llega
   `client-list` / `client-pk`, se re-renderiza el form con un mensaje de error
   (red de seguridad; el JS ya lo impide antes).

## Frontend (`templates/project_admin/form.html`)
- Botón **"+ Nuevo cliente"** junto al `<select id="client-list">`.
- Modal propio (HTML + CSS, sin librería) con inputs Nombre/Teléfono,
  botones Guardar/Cancelar y zona de error.
- JS: submit → `fetch` POST con CSRF → en éxito agrega `<option>` al dropdown,
  lo selecciona, dispara `change` (reusa el autofill 4.1) y cierra/limpia el
  modal. Errores se muestran dentro del modal. Sin recarga → no se pierde el form.
- Inputs `client-name`/`client-phone`: `readonly`, sin `required`. La validación
  de submit pasa a exigir un cliente seleccionado en el dropdown.

## Aislamiento por usuario
El endpoint crea siempre con `user=request.user` y nunca lee clientes ajenos.
El dropdown ya filtra `user=request.user, flag=True`.

## Testing
Test del endpoint nuevo (primer test del repo): requiere login, crea cliente
scoped al user, devuelve JSON correcto, rechaza nombre vacío con 400.
