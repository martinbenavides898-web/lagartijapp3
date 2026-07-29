"""Cálculos de progreso, rachas y resúmenes de entrenamiento."""

from datetime import timedelta

import pandas as pd

from app.config import TIPO_DESCANSO, TIPOS_EJERCICIO, TIPOS_RACHA
from app.data_repository import crear_df_vacio
from app.time_utils import hoy_chile


def datos_hoy(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return crear_df_vacio()
    return df[df["Fecha"].dt.date == hoy_chile()]


def total_hoy(df: pd.DataFrame, tipo: str) -> int:
    hoy = datos_hoy(df)
    if hoy.empty:
        return 0
    return int(hoy.loc[hoy["Tipo_Ejercicio"] == tipo, "Cantidad"].sum())


def peso_actual(df: pd.DataFrame) -> float | None:
    if df.empty:
        return None
    pesos = df.dropna(subset=["Peso"])
    pesos = pesos[pesos["Peso"] > 0]
    if pesos.empty:
        return None
    return float(pesos.sort_values("Fecha").iloc[-1]["Peso"])


def fmt(seconds: int) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}:{seconds:02d}"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {seconds}s"


def max_diario(df: pd.DataFrame, tipo: str, excluir_hoy: bool = True) -> int:
    if df.empty:
        return 0
    filtered = df[df["Tipo_Ejercicio"] == tipo].copy()
    if excluir_hoy:
        filtered = filtered[filtered["Fecha"].dt.date != hoy_chile()]
    if filtered.empty:
        return 0
    daily = filtered.groupby(filtered["Fecha"].dt.date)["Cantidad"].sum()
    return int(daily.max()) if not daily.empty else 0


def calcular_racha(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    temp = df[df["Tipo_Ejercicio"].isin(TIPOS_RACHA)].copy()
    temp = temp[
        (
            temp["Tipo_Ejercicio"].isin(TIPOS_EJERCICIO)
            & (temp["Cantidad"] > 0)
        )
        | (temp["Tipo_Ejercicio"] == TIPO_DESCANSO)
    ]
    activas = set(temp["Fecha"].dt.date)
    racha = 0
    current = hoy_chile()
    while current in activas:
        racha += 1
        current -= timedelta(days=1)
    return racha


def fechas_descanso(df: pd.DataFrame) -> set:
    if df.empty:
        return set()
    temp = df[df["Tipo_Ejercicio"] == TIPO_DESCANSO]
    return set(temp["Fecha"].dt.date)


def fechas_activas(df: pd.DataFrame) -> set:
    if df.empty:
        return set()
    temp = df[df["Tipo_Ejercicio"].isin(TIPOS_RACHA)].copy()
    temp = temp[
        (
            temp["Tipo_Ejercicio"].isin(TIPOS_EJERCICIO)
            & (temp["Cantidad"] > 0)
        )
        | (temp["Tipo_Ejercicio"] == TIPO_DESCANSO)
    ]
    return set(temp["Fecha"].dt.date)


def peso_semanal(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    desde = hoy_chile() - timedelta(days=6)
    temp = df[
        (df["Fecha"].dt.date >= desde)
        & df["Peso"].notna()
        & (df["Peso"] > 0)
    ].copy()
    if temp.empty:
        return pd.DataFrame()
    temp["Dia"] = temp["Fecha"].dt.strftime("%d/%m")
    return (
        temp.sort_values("Fecha")
        .groupby("Dia", as_index=False)["Peso"]
        .last()
        .set_index("Dia")
    )


def progreso_diario(df: pd.DataFrame, tipo: str, dias: int = 14) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    desde = hoy_chile() - timedelta(days=dias - 1)
    temp = df[
        (df["Tipo_Ejercicio"] == tipo) & (df["Fecha"].dt.date >= desde)
    ].copy()
    if temp.empty:
        return pd.DataFrame()
    temp["Dia"] = temp["Fecha"].dt.strftime("%d/%m")
    return temp.groupby("Dia", as_index=False)["Cantidad"].sum().set_index("Dia")


def actividad_horaria(df: pd.DataFrame) -> pd.DataFrame:
    hoy = datos_hoy(df)
    empty = pd.DataFrame(columns=["Hora", "Tipo_Ejercicio", "Cantidad"])
    if hoy.empty:
        return empty

    temp = hoy[hoy["Tipo_Ejercicio"].isin(TIPOS_EJERCICIO)].copy()
    if temp.empty:
        return empty

    temp["Hora"] = temp["Fecha"].dt.hour
    resumen = temp.groupby(["Hora", "Tipo_Ejercicio"], as_index=False)[
        "Cantidad"
    ].sum()

    base = pd.DataFrame({"Hora": list(range(24))}).merge(
        pd.DataFrame({"Tipo_Ejercicio": TIPOS_EJERCICIO}), how="cross"
    )
    resumen = base.merge(resumen, on=["Hora", "Tipo_Ejercicio"], how="left")
    resumen["Cantidad"] = resumen["Cantidad"].fillna(0).astype(int)
    return resumen


def pct(valor: int, meta: int) -> float:
    return min(max(valor / meta, 0.0), 1.0) if meta > 0 else 0.0
