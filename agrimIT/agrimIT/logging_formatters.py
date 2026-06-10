"""Formatter de logging estructurado (JSON) para produccion (Railway).

Emite una linea JSON por registro. Ademas de los campos estandar, incluye
cualquier atributo extra pasado via `logger.info(msg, extra={...})` (las vistas
ya loguean `user_id`, `project_id`, etc.), lo que hace los logs consultables.
"""
import json
import logging

# Atributos estandar de un LogRecord: lo que NO este aca se considera "extra".
_STANDARD_ATTRS = set(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "level": record.levelname,
            "time": self.formatTime(record, self.datefmt),
            "logger": record.name,
            "module": record.module,
            "message": record.getMessage(),
        }

        if record.exc_info:
            data["exc_info"] = self.formatException(record.exc_info)

        # Adjuntar los `extra=` (atributos no estandar), serializando lo que no
        # sea JSON-able como string para nunca romper el handler.
        for key, value in record.__dict__.items():
            if key in _STANDARD_ATTRS or key in data or key.startswith("_"):
                continue
            try:
                json.dumps(value)
                data[key] = value
            except (TypeError, ValueError):
                data[key] = str(value)

        return json.dumps(data, ensure_ascii=False)
