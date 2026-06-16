# AgrimIT — Especificación de Rediseño UI/UX y Nuevas Funcionalidades

> **Documento para Claude Code.** Especificación completa para implementar el rediseño visual
> aprobado y las nuevas funcionalidades. El mockup de referencia aprobado por el usuario es
> `design-mockups/agrimit-completo-disenoA.html` — **abrirlo y consultarlo ante cualquier duda
> visual: es la fuente de verdad del diseño.** Los otros dos archivos en esa carpeta son
> propuestas descartadas (solo referencia histórica).

---

## 1. Contexto del proyecto

- **Stack:** Django 5.2.3 · Python · SQLite (dev) / PostgreSQL vía `dj-database-url` (prod, Railway) · Supabase Storage para archivos · WhiteNoise para estáticos · Chart.js (CDN) en frontend. `openpyxl==3.1.5` ya está en `requirements.txt`.
- **Raíz Django:** `agrimIT/` (manage project), settings en `agrimIT/agrimIT/settings/{base,dev,prod}.py`.
- **Apps** (en `agrimIT/apps/`): `accounting`, `clients`, `project_admin`, `teams`, `users`, `utils`.
- **Templates:** `agrimIT/templates/{base,accounting,clients,project_admin,teams,users}/`.
- **Estáticos:** `agrimIT/agrimIT/static/{css,img,js}/`.
- **Idioma de la UI:** español (Argentina). Moneda: pesos, formato `$1.234.567` (separador de miles con punto). **No usar modismos argentinos en textos de UI** (usar español neutro).

### Modelos clave (no modificar salvo lo indicado en §7)

- `project_admin.Project`: `type` (choices: Estado Parcelario, Mensura, Amojonamiento, Relevamiento, Legajo Parcelario), `type_mens`, `client` (FK), `titular_name/phone`, nomenclatura (`partido`, `partida`, `circ`, `sect`, `chacra_num/let`, `quinta_num/let`, `fraccion_num/let`, `manzana_num/let`, `parcela_num/let`, `subparcela`), dirección (`street`, `street_num`, `floor`, `dept`), `inscription_type`, `process_num`, `procedure`, `contact_name/phone`, `closed`, `account` (OneToOne a `accounting.Account`), `user`, `created`.
- `accounting.Account`: `estimated` (presupuesto), `expense`, `advance`, `user`.
- `accounting.AccountMovement`: `account` (FK, related_name=`movements`), `amount`, `movement_type` (`ADV`=Anticipo, `EXP`=Gasto, `EST`=Presupuesto), `description`, `created_at`, `user`.
- `accounting.MonthlyFinancialSummary`: por `user/year/month`: `total_advance`, `total_expenses`, `income_mensura`, `income_est_parc`, `income_leg`, `income_amoj`, `income_relev`.
- `project_admin.Event` (historial), `ProjectNote`, `ProjectFiles`. `teams.Team` y project shares.

### URLs existentes relevantes (mantener nombres)

`index`, `projects`, `projectslisttype`, `projectslist`, `create`, `projectview`, `modification`, `fullmodification`, `delete`, `duplicate`, `close`, `upload`, `download`, `deletefile`, `history`, `search`, `clients`, `clientcreate`, `clientprojectcreate`, `deleteclient`, `balance`, `accounting_display`, `accform`, `chartdata`, `balance_info`, `team_list`, `team_create`, `team_detail`, `project_share`, `project_unshare`, `shared_projects`, `login`, `logout`, `project_notes`, `import_projects`.

### Reglas inviolables

1. **Aislamiento por usuario:** toda query nueva debe filtrar por `request.user` (o proyectos compartidos vía teams cuando corresponda). Es un fix de seguridad ya implementado; no regresionarlo.
2. No romper ningún flujo existente (formularios POST, endpoints AJAX `search`, `chartdata`, `balance_info`, `client_json`).
3. Mantener `{% csrf_token %}` en todos los formularios.
4. No tocar migraciones existentes; solo crear nuevas si esta spec lo indica (§7.7).
5. Correr los tests existentes (`pytest`) tras cada fase; deben seguir pasando.

---

## 2. Sistema de diseño (Design System)

Crear `static/css/design-system.css` con variables y componentes base. Será el **primer** CSS cargado en `base_template.html`. Los CSS por página deben reescribirse usando estas variables; **eliminar progresivamente los `!important`** (hoy abundan en `responsive.css`).

### 2.1 Variables CSS (copiar tal cual)

```css
:root{
  /* Fondos y superficies */
  --bg:#f4f6fa;            /* fondo general de la app */
  --surface:#ffffff;       /* cards y paneles */
  --border:#e6e9f0;        /* bordes sutiles */

  /* Texto */
  --text:#1a2233;          /* principal */
  --text-2:#5b6577;        /* secundario */
  --text-3:#9aa3b5;        /* terciario / placeholders / labels */

  /* Marca (azul AgrimIT original) */
  --primary:#2d72ba;
  --primary-dark:#235c96;
  --primary-soft:#eaf2fa;
  --sb-bg:#2d72ba;         /* sidebar gradiente inicio */
  --sb-bg2:#1d4f85;        /* sidebar gradiente fin */

  /* Semánticos */
  --green:#10b981;  --green-soft:#ecfdf5;
  --red:#ef4444;    --red-soft:#fef2f2;
  --amber:#f59e0b;  --amber-soft:#fffbeb;
  --violet:#8b5cf6; --violet-soft:#f5f3ff;

  /* Forma */
  --radius:14px;
  --shadow:0 1px 3px rgba(16,24,40,.06),0 1px 2px rgba(16,24,40,.04);
  --shadow-lg:0 12px 24px -8px rgba(16,24,40,.12);
}
```

### 2.2 Tipografía

- Fuente: **Inter** (Google Fonts, pesos 400/500/600/700/800), fallback `system-ui, sans-serif`. Reemplaza a Open Sans en `base_template.html`.
- Tamaños: título de página `1.4rem/700`; títulos de panel `.95rem/700`; cuerpo `.85–.9rem`; labels de formulario `.76rem/600` color `--text-2`; microcopy `.72–.75rem` color `--text-3`; valores KPI `1.6rem/800` con `letter-spacing:-.02em`.
- Headers de tabla: `.7rem/600`, `text-transform:uppercase`, `letter-spacing:.06em`, color `--text-3`.

### 2.3 Componentes base (clases del design system)

Tomar el CSS exacto del mockup aprobado. Resumen de inventario:

| Clase | Uso |
|---|---|
| `.btn`, `.btn-primary`, `.btn-ghost`, `.btn-green`, `.btn-red`, `.btn-sm` | Botones. Primario azul marca; ghost con borde; red es *soft* (fondo `--red-soft`, texto `--red`) |
| `.panel`, `.panel .head`, `.panel .body` | Card contenedora estándar con header de 15px 20px y borde inferior |
| `.kpi` (+ `.top`, `.name`, `.icon`, `.value`) | Tarjeta de indicador con hover elevación (`translateY(-3px)`) |
| `.trend`, `.t-up`, `.t-down`, `.t-flat` | Píldora de variación (▲/▼/—) |
| `.badge`, `.b-green/.b-gray/.b-amber/.b-blue/.b-red/.b-violet` | Estados y etiquetas |
| `.chips` | Filtros tipo píldora seleccionables (estado `.on` = fondo `--primary-soft`, borde y texto `--primary`) |
| `.seg` | Control segmentado (estado `.on` = fondo `--primary`, texto blanco) |
| `.month-pick` | Selector de mes con flechas ‹ › |
| `table` + `th/td` estándar | Tablas: filas hover `--primary-soft` si son clickeables (`tr.click`) |
| `.bar`, `.bar-cell` | Barra de progreso fina (7px, gradiente `#2d72ba→#3498db`) |
| `input.std`, `select.std`, `textarea.std`, `label.fl`, `.fgrid` | Formularios: focus con borde `--primary` + ring `--primary-soft` |
| `.toast` | Notificación flotante inferior (reemplaza `alert()` informativos) |
| `.modal-bg` + contenido | Modal centrado con overlay `rgba(15,23,42,.55)` |
| `.kv` | Fila clave-valor con borde punteado (detalle de proyecto) |
| `.nomen .cell` | Celdas de nomenclatura catastral (fondo `--bg`, label uppercase 0.65rem) |
| `.tl`, `.tl-item` | Línea de tiempo del historial (punto azul; `.gr` verde para cobros, `.am` ámbar para modificaciones) |
| `.aging`, `.age-box`, `.age-ok/.age-warn/.age-bad/.age-crit` | Cajas de antigüedad de deuda (borde superior 3px verde/ámbar/naranja/rojo) |
| `.pos` / `.neg` | Montos positivos (verde, bold) / negativos (rojo) |

### 2.4 Animaciones

- Transiciones generales `.15s`; entrada de vistas `fade` (opacity + translateY(6px), .25s).
- Hover en cards: `translateY(-3px)` + `--shadow-lg`.
- Toast: slide-up `.3s`, autocierre 2,2 s.
- No usar animaciones de más de 300 ms.

---

## 3. Layout global: reemplazo del navbar por sidebar

Reescribir `templates/base/base_template.html`:

### 3.1 Estructura

```html
<!DOCTYPE html>
<html lang="es">
<head>
  … meta viewport, favicon existente, design-system.css, css de página vía block,
  Google Fonts Inter, csrf-token meta, logger.js …
</head>
<body>
  <div class="layout">
    <aside class="sidebar" id="sidebar">…</aside>
    <div class="overlay" id="overlay"></div>
    <main class="main">
      <header class="topbar">{% block topbar %}{% endblock %}</header>
      {% block content %}{% endblock %}
    </main>
  </div>
  <div class="toast" id="toast"></div>
  {% block extra_js %}{% endblock %}
</body>
</html>
```

Consolidar los blocks antiguos (`content`/`index`/`form`/`graph`) en un único `content`; actualizar los 26 templates que extienden la base.

### 3.2 Sidebar (240px fijo, fondo azul marca)

- Fondo: `linear-gradient(180deg, var(--sb-bg), var(--sb-bg2))`. Sin borde derecho.
- **Brand:** placa blanca redondeada (40×40, radius 10px, sombra suave) con `img/logo-cut.png` a 26px de ancho + texto "AgrimIT" blanco 1.18rem/800. Linkea a `{% url 'index' %}`.
- **Navegación** (con icono, orden y secciones exactas):
  - *General:* Inicio → `index` · Balances → `balance` · Cobranzas → `accounting_display` (con contador de cobros pendientes, ver §7.3)
  - *Gestión:* Proyectos → `projects` (contador de activos) · Nuevo proyecto → `create` · Clientes → `clients` (contador) · Historial → `history`
  - *Colaboración:* Grupos → `team_list` · Compartidos → `shared_projects`
- Ítems: texto `rgba(255,255,255,.82)`, hover `rgba(255,255,255,.12)`, **activo = fondo blanco + texto `--primary` + bold + sombra**. Detectar activo comparando `request.resolver_match.url_name` (mapear nombres de URL → ítem).
- Contadores `.count`: fondo `rgba(255,255,255,.18)`; en ítem activo, `--primary-soft`/`--primary`.
- Labels de sección: `.66rem`, uppercase, `rgba(255,255,255,.55)`.
- **Footer:** avatar circular con iniciales del username (gradiente `#3498db→#1d4f85`), nombre del usuario, link "Salir" → `logout` en `#cfe3f7`. Borde superior `rgba(255,255,255,.16)`.
- Los submenús del navbar viejo (tipos de proyecto, balance/cobranzas, grupos) **desaparecen**: sus destinos quedan cubiertos por filtros chips dentro de las páginas y por los ítems del sidebar.

### 3.3 Topbar por página

Cada página define: título (h1) + subtítulo (`.sub`), y a la derecha (`.ml-auto`) sus acciones. El **buscador global** (input + dropdown de resultados AJAX vía `/search/`) vive en el topbar de Inicio y Proyectos; conservar el JS de debounce/fetch existente adaptando estilos (resultados como dropdown `.panel` flotante; ítem = tipo + fecha, clase `closed-project` con badge gris).

### 3.4 Responsive (breakpoints exactos)

- `≤1100px`: grids de 2 columnas pasan a 1 (`.grid`, `.grid2`, `.dgrid`, `.bal-grid`).
- `≤860px`: sidebar oculto (`translateX(-100%)`), botón hamburguesa `.hamb` visible en cada topbar, overlay oscuro al abrir, cierre por overlay/click en ítem/resize >860. Padding de `.main` baja a 16px. Columnas marcadas `.hide-m` se ocultan en tablas. Bloquear scroll del body con menú abierto.
- Eliminar el archivo `responsive.css` actual cuando todas las páginas estén migradas (su lógica queda absorbida por el nuevo CSS por componente, mobile-first y sin `!important`).

---

## 4. Rediseño página por página

Para cada template: respetar **exactamente** la vista equivalente del mockup (`agrimit-completo-disenoA.html`, secciones `#view-*`). No inventar variantes.

### 4.1 `base/Index.html` — vista `#view-dash`
- Topbar: "Buen día, {{ user.first_name|default:user.username }} 👋" + subtítulo "Resumen del estudio — {mes año}" + buscador + botón "+ Nuevo proyecto".
- 4 KPI: Proyectos activos (`+N este mes` comparando con mes anterior), Ingresos del mes (% vs mes anterior), **Por cobrar** (suma de saldos, clickeable → Cobranzas, ver §7.3), Clientes.
- Grid 2fr/1fr: tabla "Proyectos recientes" (últimos 5; columnas Proyecto/Cliente/Partida/Estado; fila → `projectview`) + panel "Actividad reciente" (últimos 5 `Event` del usuario con icono según `Event.type` y tiempo relativo).
- Backend: ampliar la view `index` para proveer estos datos.

### 4.2 `project_admin/project_list_template.html` — `#view-proj`
- Toolbar: chips por tipo (Todos + los 5 `TYPE_CHOICES`) — son **links** a `projects`/`projectslisttype` manteniendo el querystring de página; segmento Activos/Cerrados/Todos (nuevo parámetro GET `estado`, default `activos`; ajustar la view).
- Cards de proyecto `.pcard`: tipo (700) + badge de estado (Activo verde / Cerrado gris), meta (cliente bold, partido·partida, dirección, fecha 📅), footer con `ID {{pk}}`. Cerrado ya NO usa fondo verde manzana: solo el badge.
- Botón "📥 Importar" (ghost) y "+ Nuevo" (primary) en topbar. Paginación con el componente `.pagination`.

### 4.3 `project_admin/project_template.html` (detalle) — `#view-det`
- Header: botón volver `←` (history.back o `projects`), h1 "{tipo} — {cliente}", fila de badges: estado, `ID {{pk}}`, `Creado {{created|date:"d/m/Y"}}`, `Trámite N° {{process_num}}` (si existe), `{{type_mens}}` si es Mensura.
- Acciones (derecha): 📝 Notas · 👥 Compartir · 📋 Duplicar (POST con confirm) · **🧾 Factura (nueva, §7.7)** · ✓ Terminar (verde, solo si no closed) · Eliminar (red soft, POST con confirm).
- Grid 1.05fr/1.6fr. Columna izquierda: panel "Cliente y titular" (filas `.kv`: cliente, teléfono, titular, tel. titular, contacto; conservar los flujos "¿Es titular?", modificar titular y agregar contacto como formularios inline que se despliegan); panel "Finanzas" (presupuesto/cobrado/gastos con links "Modificar" que despliegan los mini-forms POST existentes a `modification`, y `.saldo-box` con **Saldo a cobrar = estimated − advance**; link "Ver movimientos →" a `accounting_display` pk); panel "Archivo adjunto" (icono 📄, nombre, descargar/eliminar; o flujo de subida existente si no hay archivo).
- Columna derecha: panel "Nomenclatura catastral" con grid `.nomen` (Partido, Partida, Circuns., Sección, Fracción `num — let`, Quinta, Chacra, Manzana, Parcela, Subparcela, Inscripción) + caja 📍 dirección; link "Modificación completa →" a `fullmodification`; panel "Movimientos del proyecto" (lista `.movs`: ↑ verde anticipos, ↓ rojo gastos, descripción y fecha, monto `.pos/.neg`; "+ Nuevo movimiento" → `accform`); panel "Compartido con" (badges violeta por team + gestión unshare).
- Campos vacíos: mostrar "—" (nunca strings vacíos).

### 4.4 `project_admin/form.html` y `full_mod_template.html` — `#view-form`
- Panel único max-width 880px. Tipo de trabajo como **chips** (mapear al select real con JS: chips actualizan un `<input hidden>`/select; si type=Mensura mostrar select `type_mens`).
- Cliente: select `.std` con opción "+ Crear nuevo cliente" que abre el flujo AJAX existente (`client_create_ajax`).
- Secciones tituladas "NOMENCLATURA" y "UBICACIÓN" con `.fgrid` (autofit 190px). Inputs num/letra pueden agruparse "Fracción (N°/letra)" en dos inputs compactos lado a lado.
- Acciones: Cancelar (ghost) + Crear proyecto / Guardar (primary), alineados a la derecha.
- Mantener django-widget-tweaks o renderizado manual de los forms existentes aplicando clase `std`; mostrar errores de campo bajo el input en `.72rem` color `--red`.

### 4.5 `clients/clients_template.html` — `#view-cli`
- Pasar de cards a **tabla**: Cliente (+badge violeta "fijo" si `flag`), Teléfono (hide-m), Proyectos (badge azul con count), Facturado 2026 (hide-m; suma de `advance` de sus proyectos del año, anotación en la view), Acciones (Ver proyectos → `projectslist` pk · + Proyecto → `clientprojectcreate` · Eliminar con confirm que avisa que borra proyectos asociados).
- Topbar: buscador local (filtra filas client-side) + "+ Crear cliente".
- `create_client_template.html`: mismo patrón de formulario que §4.4.

### 4.6 `accounting/balance.html` — `#view-bal` (ver §7.1, §7.2, §7.5, §7.6)
### 4.7 `accounting/accounting_history.html` (Cobranzas) — `#view-cob` (ver §7.3, §7.4)
### 4.8 `accounting/account_form.html`
- Formulario simple en panel: tipo de movimiento (seg o select), monto, descripción; botones estándar.

### 4.9 `project_admin/history_template.html` — `#view-hist`
- Línea de tiempo `.tl` agrupada por "{Mes Año}" (`.tl-month`). Cada `Event`: fecha `.when`, mensaje `.what` con strong en lo relevante; clase `.gr` para eventos de cobro, `.am` para modificaciones, default azul. Mantener links a proyecto/cliente.
- Panel max-width 760px. Segmento de filtro (Todo/Proyectos/Clientes/Cobros) filtrando por `Event.type` (GET param).

### 4.10 Teams (`team_list`, `team_detail`, `team_form`, `shared_projects`, `project_share_form`) — `#view-teams`
- `team_list`: grid de 2 paneles por grupo: header con "⬡ {nombre}" + badge Admin/Miembro; cuerpo con "N miembros · N proyectos compartidos", fila de avatares (iniciales, gradientes variados, "+N" si >4), acciones (Ver detalle, Invitar/Salir, Eliminar si admin).
- Panel inferior "Proyectos compartidos conmigo": tabla Proyecto/Dueño/Grupo/Compartido/Permiso (badge azul Lectura, violeta Edición).
- `team_detail` y forms: paneles y componentes estándar.

### 4.11 `users/login.html`
- Página sin sidebar (no extiende la base o usa base mínima): card centrada (max-width 400px) sobre fondo `--bg`, logo completo (`img/logo.png`) arriba, inputs `.std`, botón primary full-width, errores en `--red`.

### 4.12 Notas (`project_notes.html`), Import (`import_form/result`), `files_template`
- Migrar a paneles/formularios del design system. Notas: cards con título, descripción, fecha y acciones editar/eliminar.

---

## 5. JavaScript

- Conservar: `logger.js`, búsqueda global (debounce 300ms, fetch `/search/`), validaciones de upload.
- Nuevo `static/js/ui.js`: toggle sidebar móvil + overlay, `toast(msg)` global, helper para desplegar mini-forms "Modificar" (reemplaza los listeners repetidos de `project_template`), cierre de modal por click en fondo.
- Reemplazar `alert()`/`confirm()` informativos por toast; **mantener `confirm()` nativo** para acciones destructivas (eliminar proyecto/cliente/archivo, dejar de compartir, duplicar).
- Charts: ver §7.1. `Chart.defaults.font.family="'Inter',sans-serif"; Chart.defaults.color='#5b6577';`.

---

## 6. Iconografía y assets

- Logo: `img/logo-cut.png` en sidebar y factura; `img/logo.png` en login. No crear assets nuevos.
- Iconos: caracteres unicode/emoji como en el mockup (⌂ ◔ $ ▤ ✚ ◉ ↺ ⬡ ⇄ 🔍 📄 💰 👥 ⏰ 📝 📋 🧾 ⇩ ‹ › ←). No agregar librerías de iconos.

---

## 7. Nuevas funcionalidades

### 7.1 Balances: KPIs comparativos (Punto 1)

**Backend** (`accounting/views.py`):
- Nueva función `get_balance_kpis(user, year, month) -> dict`: obtiene `MonthlyFinancialSummary` del mes y del mes anterior (manejar enero→diciembre del año previo). Devuelve para ingresos (`total_advance`), gastos (`total_expenses`), neto (`advance−expenses`) y proyectos facturados (count de proyectos del usuario con movimientos ADV en el mes): valor actual, valor anterior y `delta_pct` (None si anterior es 0 o no existe).
- Inyectar en el contexto de `balance`.

**Frontend** (`balance.html`): 4 `.kpi` con `.trend`: `t-up` verde si mejora, `t-down` rojo si empeora (para gastos: subir = `t-down`), `t-flat` si None/0 ("— sin datos previos"). Formato: `▲ 12,4% vs {mes anterior}`.

### 7.2 Balances: navegación de mes con flechas (Punto 3)

- Reemplazar el `input type="month"` + botón "Hecho" por `.month-pick`: `‹` `{Mes Año}` `›`.
- Implementación server-side simple: las flechas son links `?year=Y&month=M` (la view `balance` ya debe aceptar GET además del POST actual; mantener compatibilidad con el POST existente). Deshabilitar `›` si el mes es el actual.
- Segmento Mes/Trimestre/Año al lado: **fase 2 opcional** — si se implementa, agrega agregación de 3/12 `MonthlyFinancialSummary`; si no, ocultarlo.

### 7.3 Cobranzas: cuentas por cobrar con aging (Punto 4)

**Definición:** saldo de un proyecto = `account.estimated − account.advance`, considerando solo proyectos **no cerrados** con `estimated > 0` y saldo > 0. Antigüedad = días desde el último movimiento ADV (`AccountMovement.created_at` máx.), o desde `project.created` si nunca cobró.

**Backend:** nueva función `get_receivables(user) -> dict` en `accounting/views.py`:
- Lista de `{project, client, last_payment_date, saldo, days}` ordenada por days desc.
- Buckets: `al_dia` (<30), `b30_60`, `b60_90`, `b90` (+90), cada uno con total y count. Total general.
- Integrarla al contexto de `accounting_mov_display` (solo cuando no se está viendo un proyecto puntual) y exponer el count total para el contador del sidebar y el KPI "Por cobrar" del Index (vía context processor liviano o helper llamado en `index`).

**Frontend** (`accounting_history.html`): panel superior "Cuentas por cobrar — $TOTAL en N proyectos" con `.aging` (4 `.age-box`) + tabla: Proyecto (`#pk tipo`), Cliente, Último cobro (hide-m), Saldo (`.neg`), Antigüedad (badge: verde <30, ámbar 30-60, naranja `#fff7ed/#c2410c` 60-90, rojo +90), acción 🧾 Factura (link a §7.7).
- Debajo, panel "Movimientos": tabla Proyecto/Cliente/Movimiento (badges: Anticipo verde, Gasto rojo, Modificación ámbar para montos negativos)/Monto (`.pos`/`.neg` con −)/Fecha. Mantener filtro por rango de fechas existente (inputs `.std` compactos en el header del panel) y el toggle de descripción al click en el badge (mantener data-description).

### 7.4 Exportación a Excel y PDF (Punto 5)

**Excel (openpyxl, ya instalado):**
- `GET /balance/export/xlsx/?year=Y` → nombre `agrimit_balance_{Y}.xlsx`. Hoja "Balance {Y}": encabezado con logo-texto, tabla Mes/Proyectos/Ingresos/Gastos/Neto + fila Total; formato moneda `#,##0`; header con relleno azul `2D72BA` y texto blanco.
- `GET /accounting/export/xlsx/?start=&end=` → movimientos del rango (mismas columnas que la tabla) + hoja 2 "Por cobrar" con el aging.
- Views: `export_balance_xlsx`, `export_movements_xlsx` en `accounting/views.py`, con `login_required`, filtrado por user, `HttpResponse` con content-type `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.

**PDF:** usar **xhtml2pdf** (agregar `xhtml2pdf==0.2.16` a requirements) renderizando templates HTML print-friendly: `GET /balance/export/pdf/` (resumen del año: KPIs + tabla mensual) y el PDF de factura (§7.7). Si xhtml2pdf da problemas en Railway, fallback aceptable: vista HTML imprimible + `window.print()`.

**Frontend:** botones "⇩ Excel" y "⇩ PDF" (ghost) en topbar de Balances y Cobranzas.

### 7.5 Balances: filtros por tipo de trabajo (Punto 6)

- Chips bajo el toolbar: "Todos los tipos" + 5 tipos. Al seleccionar (GET `?tipo=`), la view recalcula KPIs y gráfico anual usando las columnas por tipo de `MonthlyFinancialSummary` (`income_mensura`, `income_est_parc`, `income_leg`, `income_amoj`, `income_relev`). Nota: esas columnas son neto por tipo; con filtro activo mostrar KPI de Neto y ocultar (o marcar "todos los tipos") Ingresos/Gastos brutos si no hay desglose disponible.
- El doughnut además filtra client-side por click en leyenda (comportamiento nativo de Chart.js — gratis).

### 7.6 Balances: Top 5 clientes (Punto 7)

**Backend:** `get_top_clients(user, year, n=5)`: agregación sobre `AccountMovement` (type ADV, año, user) → join a `account.project.client`: `{client, projects_count, total}` orden desc, top 5.
**Frontend:** panel "Top 5 clientes — {Y}" con tabla `#`, Cliente, Proyectos (badge), Facturado (`.pos`), barra `.bar` proporcional al máximo. Link "Ver todos →" a Clientes.

**Estructura de la página Balances** (orden vertical): toolbar (month-pick + chips tipo + export) → 4 KPIs → grid2: gráfico anual (izq) + doughnut por tipo (der) → grid2: Top 5 clientes (izq) + Detalle mensual (der).
- **Gráfico anual:** Chart.js mixto: barras Ingresos `#2d72ba` (borderRadius 6, maxBarThickness 24), barras Gastos `#fda4af`, línea "Neto acumulado" `#10b981` (tension .35). Interaction `mode:'index', intersect:false`; ticks Y `'$'+(v/1e6)+'M'`; tooltips con formato moneda es-AR; leyenda bottom con pointStyle.
- **Doughnut:** cutout 62%, colores `['#2d72ba','#3498db','#10b981','#f59e0b','#94a3b8']`, borde blanco 3px, hoverOffset 10.
- **Detalle mensual:** tabla Mes/Proy./Ingresos(hide-m)/Neto(`.pos`)/barra proporcional; título "Detalle mensual — Neto anual $X".
- Eliminar la tabla repetitiva actual (header "Mes/Proyectos/Ganancia Neta" repetido por cada mes).
- Mensaje "No existen registros del mes M/Y" → estado vacío dentro de un panel, con el month-pick siempre visible.

### 7.7 Factura no oficial por proyecto (NUEVO)

**Modelo nuevo** (`users/models.py`): `StudioProfile` (OneToOne a User): `studio_name` (default "Estudio de Agrimensura"), `professional_name`, `license_number` (matrícula), `address`, `phone`, `email`, `cbu`, `alias`, `payment_terms` (texto libre). Migración + admin + página simple de edición (o sección en admin de Django si se quiere mínimo). Crear con `get_or_create` al emitir factura.

**View** (`accounting/views.py`): `invoice_view(request, pk)` → `GET /accounting/invoice/<pk>/`, name=`invoice`. Valida ownership (user o compartido con permiso). Contexto: proyecto, cliente, titular, nomenclatura resumida (partido/partida/dirección), `account.estimated`, lista de movimientos ADV (fecha+descripción+monto), total pagos, saldo, `StudioProfile`, número de documento `f"{project.pk:04d}-{year}"`, fecha de emisión.

**Template** `templates/accounting/invoice.html` (standalone, no extiende base): replicar el modal del mockup como página:
- Barra superior no imprimible (`.inv-tools`): ✕ Volver · ⇩ PDF (link a `?format=pdf` vía xhtml2pdf) · 🖨 Imprimir (`window.print()`).
- Hoja `.inv-page`: header con logo-cut + datos del estudio (izq) y a la derecha píldora **"PRESUPUESTO / RECIBO X"**, "N° {número}", fecha. Borde inferior 3px `--primary`.
- Dos cajas `.inv-meta`: Cliente (nombre, teléfono, titular) y Trabajo (tipo + #pk, partido·partida, dirección).
- Tabla de conceptos: "Honorarios profesionales — {tipo}" `$estimated`; cada pago ADV como fila "−$monto" en verde con fecha.
- Totales: Subtotal, Pagos recibidos (−), **Saldo** (fila con borde superior 2px, 800).
- Pie `.inv-foot`: **"Documento no válido como factura oficial. Emitido a modo informativo por AgrimIT."** + forma de pago (CBU/alias del perfil).
- `@media print`: ocultar `.inv-tools`, fondo blanco, sin sombras ni border-radius, márgenes de hoja A4.

**Puntos de entrada:** botón 🧾 Factura en detalle de proyecto y en cada fila de la tabla de cuentas por cobrar.

---

## 8. Plan de implementación por fases

Cada fase termina con: `pytest` verde + revisión visual manual (desktop 1440px, tablet 900px, móvil 390px).

1. **Fase 1 — Fundación:** `design-system.css`, nuevo `base_template.html` (sidebar+topbar+responsive), `ui.js`, Inter. Migrar Index. Actualizar los `{% block %}` de todos los templates para que no rompan (aunque conserven su CSS viejo temporalmente).
2. **Fase 2 — Gestión:** project_list, project detail, form/full_mod, clients (+anotaciones de la view), notas, import, files.
3. **Fase 3 — Finanzas:** balance.html completo (7.1, 7.2, 7.5, 7.6), accounting_history con aging (7.3), account_form.
4. **Fase 4 — Exportes y factura:** 7.4 (xlsx+pdf), 7.7 (StudioProfile + invoice). Nuevas URLs: `balance/export/xlsx/`, `balance/export/pdf/`, `export/xlsx/` (movimientos), `invoice/<pk>/`.
5. **Fase 5 — Colaboración y pulido:** teams, login, historial, eliminación de CSS legacy (`responsive.css`, estilos inline de templates), barrido final de `!important`, QA responsive completo.

## 9. Criterios de aceptación

- [ ] Ninguna página usa el navbar superior viejo; sidebar presente y activo correcto en todas.
- [ ] Logo real visible en sidebar, login y factura.
- [ ] Paleta exclusivamente vía variables CSS; cero colores hardcodeados nuevos fuera de `design-system.css` y configs de Chart.js.
- [ ] Balances: KPIs con % vs mes anterior, flechas de mes funcionales, filtro por tipo, top 5 clientes, export Excel/PDF descargables.
- [ ] Cobranzas: aging 4 franjas con totales correctos (verificar a mano contra datos de prueba: `generate_test_data`).
- [ ] Factura: imprime solo la hoja (sin UI), muestra leyenda de no oficial, números correctos (estimated − ADV = saldo).
- [ ] Mobile 390px: sidebar colapsable, tablas sin scroll horizontal (columnas hide-m), formularios usables.
- [ ] Todos los formularios existentes siguen posteando correctamente (probar: crear proyecto, modificar presupuesto, nuevo movimiento, crear cliente, compartir proyecto, subir archivo).
- [ ] `pytest` completo en verde.
- [ ] Aislamiento por usuario verificado en cada query nueva (KPIs, receivables, top clients, exports, invoice).

## 10. Fuera de alcance (no hacer)

- No cambiar lógica de negocio de cuentas/movimientos ni señales existentes.
- No cambiar el esquema de URLs existente (solo agregar las nuevas de §7.4 y §7.7).
- No introducir frameworks frontend (React/Tailwind/etc.) ni librerías de iconos; CSS y JS vanilla.
- No tocar la integración Supabase ni el sistema de logging.
- No implementar el segmento Trimestre/Año de Balances si excede el tiempo (ocultarlo).
