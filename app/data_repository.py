"""Lectura y escritura de registros de LagartijApp.

Google Sheets es la fuente principal en producción. El CSV es una copia local
útil para desarrollo, descarga y recuperación temporal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

from app.config import (
    COLUMNAS,
    DATA_FILE,
    OLD_DATA_FILE,
    SHEET_FILE_NAME,
    SHEET_WORKSHEET_INDEX,
    TIPO_FLEXIONES,
    TIPO_PLANCHA,
)
from app.time_utils import ahora_chile


@dataclass(frozen=True)
class EstadoDatos:
    fuente: str
    remoto: bool
    mensaje: str = ""
    nivel: str = "ok"  # ok, info, warning, error


class ErrorEscrituraDatos(RuntimeError):
    """Se lanza cuando un registro no pudo guardarse de forma segura."""


def crear_df_vacio() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNAS)


def normalizar_df(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte bases actuales o antiguas al formato oficial."""
    if df.empty:
        return crear_df_vacio()

    if all(c in df.columns for c in COLUMNAS):
        out = df[COLUMNAS].copy()
    elif "fecha" in df.columns and "cantidad" in df.columns:
        out = pd.DataFrame(
            {
                "Fecha": df["fecha"],
                "Tipo_Ejercicio": TIPO_FLEXIONES,
                "Cantidad": df["cantidad"],
                "Peso": None,
                "RPE_Esfuerzo": None,
            }
        )
    elif "fecha" in df.columns and (
        "lagartijas" in df.columns or "plancha_segundos" in df.columns
    ):
        rows: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            fecha = row.get("fecha", ahora_chile().strftime("%Y-%m-%d %H:%M"))
            flexiones = int(row.get("lagartijas", 0) or 0)
            plancha = int(row.get("plancha_segundos", 0) or 0)
            if flexiones > 0:
                rows.append(
                    {
                        "Fecha": fecha,
                        "Tipo_Ejercicio": TIPO_FLEXIONES,
                        "Cantidad": flexiones,
                        "Peso": None,
                        "RPE_Esfuerzo": None,
                    }
                )
            if plancha > 0:
                rows.append(
                    {
                        "Fecha": fecha,
                        "Tipo_Ejercicio": TIPO_PLANCHA,
                        "Cantidad": plancha,
                        "Peso": None,
                        "RPE_Esfuerzo": None,
                    }
                )
        out = pd.DataFrame(rows, columns=COLUMNAS)
    else:
        return crear_df_vacio()

    for col in COLUMNAS:
        if col not in out.columns:
            out[col] = None

    out["Fecha"] = pd.to_datetime(out["Fecha"], errors="coerce")
    out = out.dropna(subset=["Fecha"])
    out["Fecha"] = out["Fecha"].dt.tz_localize(None)

    out["Tipo_Ejercicio"] = out["Tipo_Ejercicio"].astype(str).str.strip()
    out["Cantidad"] = (
        pd.to_numeric(out["Cantidad"], errors="coerce").fillna(0).astype(int)
    )
    out["Peso"] = pd.to_numeric(out["Peso"], errors="coerce")
    out["RPE_Esfuerzo"] = pd.to_numeric(out["RPE_Esfuerzo"], errors="coerce")

    return out[COLUMNAS].sort_values("Fecha").reset_index(drop=True)


def guardar_copia_local(df: pd.DataFrame) -> None:
    normalizar_df(df).to_csv(DATA_FILE, index=False)


def _cargar_copia_local() -> pd.DataFrame:
    if DATA_FILE.exists():
        return normalizar_df(pd.read_csv(DATA_FILE))

    if OLD_DATA_FILE.exists():
        df = normalizar_df(pd.read_csv(OLD_DATA_FILE))
        guardar_copia_local(df)
        return df

    return crear_df_vacio()


def _hay_credenciales_google() -> bool:
    try:
        return "gcp_service_account" in st.secrets
    except Exception:
        return False


@st.cache_resource
def conectar_sheet():
    """Crea una conexión reutilizable con la primera hoja del archivo."""
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=scope,
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open(SHEET_FILE_NAME)
    return spreadsheet.get_worksheet(SHEET_WORKSHEET_INDEX)


def _df_desde_sheet(sheet) -> pd.DataFrame:
    """Lee las primeras cinco columnas del Sheet de forma tolerante."""
    values = sheet.get_all_values()
    if not values:
        sheet.append_row(COLUMNAS, value_input_option="RAW")
        return crear_df_vacio()

    first_row = [str(value).strip() for value in values[0]]
    first_row_lower = [value.lower() for value in first_row]

    # Si la primera fila parece encabezado, se excluye del contenido.
    header_tokens = {"fecha", "timestamp", "tipo_ejercicio", "cantidad", "peso"}
    parece_encabezado = bool(set(first_row_lower) & header_tokens)
    data_rows = values[1:] if parece_encabezado else values

    rows: list[list[Any]] = []
    for raw_row in data_rows:
        padded = list(raw_row[: len(COLUMNAS)])
        padded.extend([""] * (len(COLUMNAS) - len(padded)))
        if not any(str(value).strip() for value in padded):
            continue
        rows.append(padded)

    return normalizar_df(pd.DataFrame(rows, columns=COLUMNAS))


@st.cache_data(ttl=30, show_spinner=False)
def _cargar_sheet_cache() -> pd.DataFrame:
    return _df_desde_sheet(conectar_sheet())


def cargar_datos() -> tuple[pd.DataFrame, EstadoDatos]:
    """Carga Google Sheets y actualiza el espejo CSV.

    Si Google no está configurado o falla, devuelve la copia local y comunica
    explícitamente el modo de funcionamiento.
    """
    local = _cargar_copia_local()

    if not _hay_credenciales_google():
        return local, EstadoDatos(
            fuente="CSV local",
            remoto=False,
            mensaje="Google Sheets no está configurado en este entorno.",
            nivel="info",
        )

    try:
        remote = _cargar_sheet_cache()
        if remote.empty and not local.empty:
            return local, EstadoDatos(
                fuente="CSV local de respaldo",
                remoto=False,
                mensaje=(
                    "Google Sheets está vacío, por lo que se conservó la copia "
                    "local para evitar ocultar el historial."
                ),
                nivel="warning",
            )

        guardar_copia_local(remote)
        return remote, EstadoDatos(
            fuente="Google Sheets",
            remoto=True,
            mensaje="Sincronización correcta.",
            nivel="ok",
        )
    except Exception as exc:
        nivel = "warning" if not local.empty else "error"
        return local, EstadoDatos(
            fuente="CSV local de respaldo",
            remoto=False,
            mensaje=f"No se pudo leer Google Sheets: {exc}",
            nivel=nivel,
        )


def _valor_sheet(value: Any) -> Any:
    if value is None or value == "":
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return value


def agregar_registros(
    df_actual: pd.DataFrame,
    registros: Iterable[dict[str, Any]],
) -> pd.DataFrame:
    """Guarda uno o varios registros en una única operación remota.

    En producción, Google Sheets se escribe primero. Si esa escritura falla,
    no se informa éxito al usuario. Después se actualiza el espejo CSV.
    """
    fecha_actual = ahora_chile()
    normalized_records: list[dict[str, Any]] = []

    for registro in registros:
        normalized_records.append(
            {
                "Fecha": registro.get("Fecha", fecha_actual),
                "Tipo_Ejercicio": str(registro["Tipo_Ejercicio"]),
                "Cantidad": int(registro.get("Cantidad", 0)),
                "Peso": registro.get("Peso"),
                "RPE_Esfuerzo": registro.get("RPE_Esfuerzo"),
            }
        )

    if not normalized_records:
        return normalizar_df(df_actual)

    nuevo_df = normalizar_df(pd.DataFrame(normalized_records, columns=COLUMNAS))

    if _hay_credenciales_google():
        rows = []
        for _, row in nuevo_df.iterrows():
            rows.append(
                [
                    row["Fecha"].strftime("%Y-%m-%d %H:%M:%S"),
                    row["Tipo_Ejercicio"],
                    int(row["Cantidad"]),
                    _valor_sheet(row["Peso"]),
                    _valor_sheet(row["RPE_Esfuerzo"]),
                ]
            )

        try:
            conectar_sheet().append_rows(rows, value_input_option="USER_ENTERED")
            _cargar_sheet_cache.clear()
        except Exception as exc:
            raise ErrorEscrituraDatos(
                f"Google Sheets rechazó el guardado. No se registró la rutina: {exc}"
            ) from exc

    if df_actual.empty:
        combinado = nuevo_df
    else:
        combinado = normalizar_df(pd.concat([df_actual, nuevo_df], ignore_index=True))
    guardar_copia_local(combinado)
    return combinado


def agregar_registro(
    df_actual: pd.DataFrame,
    tipo: str,
    cantidad: int,
    peso: float | None = None,
    rpe: int | None = None,
) -> pd.DataFrame:
    return agregar_registros(
        df_actual,
        [
            {
                "Tipo_Ejercicio": tipo,
                "Cantidad": cantidad,
                "Peso": peso,
                "RPE_Esfuerzo": rpe,
            }
        ],
    )
