"""Configuración central de LagartijApp.

Este archivo concentra nombres, metas y rutas para evitar valores repetidos
por todo el proyecto.
"""

from pathlib import Path

APP_NAME = "LagartijApp"
APP_TIMEZONE = "America/Santiago"

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT_DIR / "data_lagartijas.csv"
OLD_DATA_FILE = ROOT_DIR / "data_entreno.csv"
STYLES_FILE = ROOT_DIR / "assets" / "styles.css"
TIM_LOGO_FILE = ROOT_DIR / "assets" / "tim_logo.png"
TIM_HERO_FILE = ROOT_DIR / "assets" / "tim_hero.png"
TIM_PEEK_FILE = ROOT_DIR / "assets" / "tim_peek.png"

SHEET_FILE_NAME = "LagartijApp_DB"
SHEET_WORKSHEET_INDEX = 0

COLUMNAS = ["Fecha", "Tipo_Ejercicio", "Cantidad", "Peso", "RPE_Esfuerzo"]

TIPO_FLEXIONES = "Flexiones"
TIPO_PLANCHA = "Plancha"
TIPO_SENTADILLAS = "Sentadillas"
TIPO_ESTOCADAS = "Estocadas"
TIPO_PESO = "Peso"
TIPO_DESCANSO = "Dia Libre"

TIPOS_EJERCICIO = [
    TIPO_FLEXIONES,
    TIPO_PLANCHA,
    TIPO_SENTADILLAS,
    TIPO_ESTOCADAS,
]
TIPOS_RACHA = [*TIPOS_EJERCICIO, TIPO_DESCANSO]

META_FLEXIONES = 50
META_PLANCHA = 120
META_SENTADILLAS = 50
META_ESTOCADAS = 50
