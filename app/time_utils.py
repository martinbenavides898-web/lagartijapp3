"""Funciones de fecha y hora usadas por toda la aplicación."""

from datetime import date, datetime, timedelta

from app.config import APP_TIMEZONE

try:
    from zoneinfo import ZoneInfo

    CHILE_TZ = ZoneInfo(APP_TIMEZONE)
except Exception:
    CHILE_TZ = None


def ahora_chile() -> datetime:
    """Devuelve la hora chilena sin información de zona horaria.

    Se conserva un datetime sin timezone para mantener compatibilidad con el
    CSV histórico y con las fechas actuales de Google Sheets.
    """
    if CHILE_TZ is not None:
        return datetime.now(CHILE_TZ).replace(tzinfo=None)
    return datetime.utcnow() - timedelta(hours=4)


def hoy_chile() -> date:
    return ahora_chile().date()
