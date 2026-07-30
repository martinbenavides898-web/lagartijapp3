from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import types

# Stubs mínimos para probar la lógica sin instalar Streamlit ni Google.
fake_streamlit = types.ModuleType("streamlit")
fake_streamlit.secrets = {}
fake_streamlit.cache_resource = lambda func: func

def fake_cache_data(*args, **kwargs):
    def decorator(func):
        func.clear = lambda: None
        return func
    return decorator

fake_streamlit.cache_data = fake_cache_data
sys.modules["streamlit"] = fake_streamlit
sys.modules["gspread"] = types.ModuleType("gspread")

google = types.ModuleType("google")
google_oauth2 = types.ModuleType("google.oauth2")
google_service = types.ModuleType("google.oauth2.service_account")

class FakeCredentials:
    @classmethod
    def from_service_account_info(cls, *args, **kwargs):
        return cls()

google_service.Credentials = FakeCredentials
sys.modules["google"] = google
sys.modules["google.oauth2"] = google_oauth2
sys.modules["google.oauth2.service_account"] = google_service
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd

from app import data_repository as repo
from app.config import COLUMNAS, TIPO_FLEXIONES, TIPO_PLANCHA


def test_normaliza_csv_actual():
    source = pd.DataFrame(
        [
            {
                "Fecha": "2026-07-29 12:30:00",
                "Tipo_Ejercicio": TIPO_FLEXIONES,
                "Cantidad": "5",
                "Peso": "85.4",
                "RPE_Esfuerzo": "7",
            }
        ]
    )
    result = repo.normalizar_df(source)
    assert list(result.columns) == COLUMNAS
    assert result.iloc[0]["Cantidad"] == 5
    assert result.iloc[0]["Peso"] == 85.4


def test_normaliza_fechas_mixtas():
    source = pd.DataFrame(
        [
            {
                "Fecha": "16/06/2026 12:30:00",
                "Tipo_Ejercicio": TIPO_FLEXIONES,
                "Cantidad": 5,
                "Peso": None,
                "RPE_Esfuerzo": 7,
            },
            {
                "Fecha": "2026-07-29 19:50:00",
                "Tipo_Ejercicio": TIPO_FLEXIONES,
                "Cantidad": 1,
                "Peso": None,
                "RPE_Esfuerzo": 1,
            },
        ]
    )
    result = repo.normalizar_df(source)
    assert len(result) == 2
    assert result["Cantidad"].sum() == 6


def test_normaliza_formato_antiguo():
    source = pd.DataFrame(
        [{"fecha": "2026-07-29 12:30:00", "lagartijas": 10, "plancha_segundos": 30}]
    )
    result = repo.normalizar_df(source)
    assert len(result) == 2
    assert set(result["Tipo_Ejercicio"]) == {TIPO_FLEXIONES, TIPO_PLANCHA}


def test_lectura_sheet_ignora_columna_extra():
    class FakeSheet:
        def get_all_values(self):
            return [
                ["Fecha", "Tipo_Ejercicio", "Cantidad", "Peso", "RPE_Esfuerzo", "Notas"],
                ["2026-07-29 12:30:00", TIPO_FLEXIONES, "5", "85.4", "7", "texto"],
            ]

    result = repo._df_desde_sheet(FakeSheet())
    assert len(result) == 1
    assert list(result.columns) == COLUMNAS
    assert result.iloc[0]["Cantidad"] == 5


def test_fechas_mixtas_no_se_pierden():
    source = pd.DataFrame([
        {"Fecha": "29/07/2026 19:50:00", "Tipo_Ejercicio": TIPO_FLEXIONES, "Cantidad": 5, "Peso": "", "RPE_Esfuerzo": 7},
        {"Fecha": "2026-07-29 19:51:00", "Tipo_Ejercicio": TIPO_PLANCHA, "Cantidad": 20, "Peso": "", "RPE_Esfuerzo": 7},
    ])
    result = repo.normalizar_df(source)
    assert len(result) == 2


def test_guardado_local_en_lote():
    current = repo.crear_df_vacio()
    with TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "data.csv"
        with patch.object(repo, "DATA_FILE", temp_file), patch.object(
            repo, "_hay_credenciales_google", return_value=False
        ):
            result = repo.agregar_registros(
                current,
                [
                    {"Tipo_Ejercicio": TIPO_FLEXIONES, "Cantidad": 5},
                    {"Tipo_Ejercicio": TIPO_PLANCHA, "Cantidad": 20},
                ],
            )
        assert len(result) == 2
        assert temp_file.exists()
        saved = pd.read_csv(temp_file)
        assert len(saved) == 2


def test_guardado_remoto_usa_una_sola_llamada_para_lote():
    class FakeSheet:
        def __init__(self):
            self.calls = []

        def append_rows(self, rows, value_input_option=None):
            self.calls.append((rows, value_input_option))

    fake_sheet = FakeSheet()
    current = repo.crear_df_vacio()
    with TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "data.csv"
        with patch.object(repo, "DATA_FILE", temp_file), patch.object(
            repo, "_hay_credenciales_google", return_value=True
        ), patch.object(repo, "conectar_sheet", return_value=fake_sheet):
            result = repo.agregar_registros(
                current,
                [
                    {"Tipo_Ejercicio": TIPO_FLEXIONES, "Cantidad": 5},
                    {"Tipo_Ejercicio": TIPO_PLANCHA, "Cantidad": 20},
                ],
            )

    assert len(result) == 2
    assert len(fake_sheet.calls) == 1
    assert len(fake_sheet.calls[0][0]) == 2


def test_sheet_vacio_conserva_respaldo_local():
    local = pd.DataFrame(
        [{
            "Fecha": "2026-07-29 12:30:00",
            "Tipo_Ejercicio": TIPO_FLEXIONES,
            "Cantidad": 5,
            "Peso": None,
            "RPE_Esfuerzo": 7,
        }]
    )
    with patch.object(repo, "_cargar_copia_local", return_value=repo.normalizar_df(local)), patch.object(
        repo, "_hay_credenciales_google", return_value=True
    ), patch.object(repo, "_cargar_sheet_cache", return_value=repo.crear_df_vacio()):
        result, status = repo.cargar_datos()

    assert len(result) == 1
    assert status.remoto is False
    assert status.nivel == "warning"


if __name__ == "__main__":
    tests = [
        test_normaliza_csv_actual,
        test_normaliza_fechas_mixtas,
        test_normaliza_formato_antiguo,
        test_lectura_sheet_ignora_columna_extra,
        test_fechas_mixtas_no_se_pierden,
        test_guardado_local_en_lote,
        test_guardado_remoto_usa_una_sola_llamada_para_lote,
        test_sheet_vacio_conserva_respaldo_local,
    ]
    for test in tests:
        test()
        print(f"OK: {test.__name__}")
