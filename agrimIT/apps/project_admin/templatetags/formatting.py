from django import template

register = template.Library()


@register.filter
def pesos(value):
    """Formato de moneda es-AR: pesos enteros con separador de miles con punto.

    Ej: Decimal('1234567.00') -> '1.234.567'. None/'' -> '0'.
    Misma lógica que ``apps.project_admin.views._pesos`` para uso en templates.
    """
    try:
        n = int(round(float(value or 0)))
    except (TypeError, ValueError):
        return "0"
    return f"{n:,}".replace(",", ".")
