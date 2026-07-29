"""Operaciones de entrenamiento que coordinan datos y mensajes de la UI."""

from __future__ import annotations

from typing import Any, Iterable

import pandas as pd
import streamlit as st

from app.config import TIPO_PLANCHA
from app.data_repository import (
    ErrorEscrituraDatos,
    agregar_registro,
    agregar_registros,
)
from app.metrics import fmt, max_diario, total_hoy


def _mostrar_error_y_detener(exc: ErrorEscrituraDatos) -> None:
    st.error(str(exc))
    st.stop()


def guardar_registro_simple(
    df_actual: pd.DataFrame,
    tipo: str,
    cantidad: int,
    peso: float | None = None,
    rpe: int | None = None,
) -> pd.DataFrame:
    """Guarda un registro y muestra un error entendible si falla."""
    try:
        return agregar_registro(df_actual, tipo, cantidad, peso=peso, rpe=rpe)
    except ErrorEscrituraDatos as exc:
        _mostrar_error_y_detener(exc)
        return df_actual


def registrar_lote_con_pr(
    df_actual: pd.DataFrame,
    registros: Iterable[dict[str, Any]],
) -> pd.DataFrame:
    """Guarda un lote completo en una llamada y calcula récords diarios."""
    registros = [
        registro
        for registro in registros
        if int(registro.get("Cantidad", 0)) > 0
    ]
    if not registros:
        return df_actual

    previos: dict[str, int] = {}
    totales_hoy: dict[str, int] = {}
    incrementos: dict[str, int] = {}

    for registro in registros:
        tipo = str(registro["Tipo_Ejercicio"])
        previos.setdefault(tipo, max_diario(df_actual, tipo, excluir_hoy=True))
        totales_hoy.setdefault(tipo, total_hoy(df_actual, tipo))
        incrementos[tipo] = incrementos.get(tipo, 0) + int(registro["Cantidad"])

    try:
        actualizado = agregar_registros(df_actual, registros)
    except ErrorEscrituraDatos as exc:
        _mostrar_error_y_detener(exc)
        return df_actual

    for tipo, incremento in incrementos.items():
        nuevo_total = totales_hoy[tipo] + incremento
        if nuevo_total > previos[tipo]:
            value = fmt(nuevo_total) if tipo == TIPO_PLANCHA else f"{nuevo_total} reps"
            st.session_state.pr_msg.append(f"Record personal: {tipo} — {value}")
            st.session_state.show_balloons = True

    return actualizado


def registrar_con_pr(
    df_actual: pd.DataFrame,
    tipo: str,
    cantidad: int,
    peso: float | None = None,
    rpe: int | None = None,
) -> pd.DataFrame:
    return registrar_lote_con_pr(
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
