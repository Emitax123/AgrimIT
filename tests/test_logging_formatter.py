"""Tests del JSONFormatter de logging estructurado (Plan 04, item 8)."""
import json
import logging

from agrimIT.logging_formatters import JSONFormatter


def _record(**extra):
    record = logging.LogRecord(
        name="apps.project_admin", level=logging.INFO, pathname=__file__,
        lineno=10, msg="evento %s", args=("x",), exc_info=None,
    )
    for k, v in extra.items():
        setattr(record, k, v)
    return record


def test_salida_es_json_valido_con_campos_estandar():
    out = JSONFormatter().format(_record())
    data = json.loads(out)  # no debe lanzar
    assert data["level"] == "INFO"
    assert data["logger"] == "apps.project_admin"
    assert data["message"] == "evento x"  # args interpolados
    assert "time" in data


def test_incluye_campos_extra():
    out = JSONFormatter().format(_record(user_id=42, project_id=7))
    data = json.loads(out)
    assert data["user_id"] == 42
    assert data["project_id"] == 7


def test_valor_no_serializable_cae_a_string():
    out = JSONFormatter().format(_record(obj=object()))
    data = json.loads(out)
    assert isinstance(data["obj"], str)


def test_incluye_traceback_si_hay_excepcion():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        record = logging.LogRecord(
            name="x", level=logging.ERROR, pathname=__file__, lineno=1,
            msg="fallo", args=(), exc_info=sys.exc_info(),
        )
    data = json.loads(JSONFormatter().format(record))
    assert "exc_info" in data
    assert "ValueError" in data["exc_info"]
