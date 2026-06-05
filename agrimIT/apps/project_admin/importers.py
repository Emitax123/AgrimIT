"""Importación masiva de proyectos desde CSV.

Módulo puro (sin HTTP ni acceso a base de datos): recibe el archivo subido y un
diccionario de clientes del usuario, y devuelve las instancias de ``Project``
válidas (sin guardar) más la lista de errores por fila. La vista se encarga de
persistir las válidas en una transacción.

Reusa ``ProjectForm`` para validar cada fila, de modo que hereda los validadores
catastrales (``solo_digitos``), las choices de ``type`` y la opcionalidad de los
campos de titular/mensura definida en el formulario.
"""

import csv
import io

from .forms import ProjectForm

# Columna que identifica al cliente por su ID interno. Se valida aparte porque
# ``ProjectForm`` excluye el campo ``client`` (lo asigna la vista).
CLIENT_COLUMN = 'cliente_id'

# Encabezado CSV -> campo del modelo Project. Única fuente de verdad del mapeo.
COLUMN_MAP = {
    'tipo': 'type',
    'tipo_mensura': 'type_mens',
    'partido': 'partido',
    'partida': 'partida',
    'circunscripcion': 'circ',
    'seccion': 'sect',
    'chacra_num': 'chacra_num',
    'chacra_letra': 'chacra_let',
    'quinta_num': 'quinta_num',
    'quinta_letra': 'quinta_let',
    'fraccion_num': 'fraccion_num',
    'fraccion_letra': 'fraccion_let',
    'manzana_num': 'manzana_num',
    'manzana_letra': 'manzana_let',
    'parcela_num': 'parcela_num',
    'parcela_letra': 'parcela_let',
    'subparcela': 'subparcela',
    'calle': 'street',
    'altura': 'street_num',
    'piso': 'floor',
    'depto': 'dept',
    'titular_nombre': 'titular_name',
    'titular_telefono': 'titular_phone',
    'nro_tramite': 'process_num',
}

# Orden de columnas en la plantilla descargable (tipo y cliente_id primero).
TEMPLATE_HEADERS = [
    'tipo',
    CLIENT_COLUMN,
    'tipo_mensura',
    'partido',
    'partida',
    'circunscripcion',
    'seccion',
    'chacra_num',
    'chacra_letra',
    'quinta_num',
    'quinta_letra',
    'fraccion_num',
    'fraccion_letra',
    'manzana_num',
    'manzana_letra',
    'parcela_num',
    'parcela_letra',
    'subparcela',
    'calle',
    'altura',
    'piso',
    'depto',
    'titular_nombre',
    'titular_telefono',
    'nro_tramite',
]

# Encabezados sin los que el archivo no se puede procesar.
REQUIRED_HEADERS = ['tipo', CLIENT_COLUMN]

# Tope de filas de datos por lote, para evitar abusos.
MAX_ROWS = 1000


def _form_errors_to_text(form):
    """Aplana los errores de un ProjectForm a un texto legible por fila."""
    parts = []
    for field, error_list in form.errors.items():
        label = form.fields[field].label if field in form.fields else field
        parts.append(f"{label}: {' '.join(error_list)}")
    return '; '.join(parts)


def parse_and_validate(uploaded_file, clients_by_id):
    """Parsea y valida un CSV de proyectos.

    Args:
        uploaded_file: el archivo subido (objeto file-like con bytes).
        clients_by_id: dict ``{int: Client}`` con los clientes del usuario.

    Returns:
        ``(valid, errors)`` donde
        ``valid`` es ``[(nro_fila, instancia_Project_sin_guardar)]`` con ``client``
        ya asignado (falta ``user``, que pone la vista), y
        ``errors`` es ``[(nro_fila, motivo)]``. Un error a nivel de archivo se
        reporta como ``(0, motivo)``.
    """
    valid = []
    errors = []

    # Decodificar (UTF-8 con BOM opcional, el que escribe Excel).
    try:
        raw = uploaded_file.read()
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        return [], [(0, 'No se pudo leer el archivo. Guardalo como CSV con codificación UTF-8.')]

    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        return [], [(0, 'El archivo está vacío o no tiene encabezados.')]

    headers = {h.strip() for h in reader.fieldnames if h}
    missing = [h for h in REQUIRED_HEADERS if h not in headers]
    if missing:
        return [], [(0, f"Faltan columnas requeridas: {', '.join(missing)}. "
                        f"Descargá la plantilla para usar el formato correcto.")]

    data_rows = 0
    # enumerate desde 2: fila 1 es el encabezado.
    for row_num, row in enumerate(reader, start=2):
        # Normalizar valores (None -> '' y trim).
        values = {(k or '').strip(): (v or '').strip() for k, v in row.items()}

        # Saltear filas completamente vacías.
        if not any(values.get(h) for h in TEMPLATE_HEADERS):
            continue

        data_rows += 1
        if data_rows > MAX_ROWS:
            errors.append((row_num, f"Se superó el tope de {MAX_ROWS} filas; el resto se ignoró."))
            break

        # Resolver el cliente por ID interno.
        client_raw = values.get(CLIENT_COLUMN, '')
        try:
            client = clients_by_id[int(client_raw)]
        except (ValueError, KeyError):
            errors.append((row_num, f"cliente «{client_raw or '(vacío)'}» no encontrado."))
            continue

        # Construir los datos del proyecto y validarlos con ProjectForm.
        form_data = {
            field: values.get(header, '')
            for header, field in COLUMN_MAP.items()
            if header in values
        }
        form = ProjectForm(form_data)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.client = client
            instance.account = None
            instance.closed = False
            valid.append((row_num, instance))
        else:
            errors.append((row_num, _form_errors_to_text(form)))

    if data_rows == 0 and not errors:
        return [], [(0, 'El archivo no tiene filas de datos.')]

    return valid, errors
