"""Carga completa de la app usando dobles mínimos de Streamlit.

No reemplaza una prueba visual en Streamlit Cloud, pero detecta imports rotos,
nombres inexistentes y errores ejecutados durante el arranque normal.
"""

from pathlib import Path
import runpy
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class SessionState(dict):
    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


class Context:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


fake_st = types.ModuleType("streamlit")
fake_st.secrets = {}
fake_st.session_state = SessionState()
fake_st.sidebar = Context()


def cache_resource(func):
    return func


def cache_data(*args, **kwargs):
    def decorator(func):
        func.clear = lambda: None
        return func
    return decorator


fake_st.cache_resource = cache_resource
fake_st.cache_data = cache_data
fake_st.set_page_config = lambda *args, **kwargs: None
fake_st.html = lambda *args, **kwargs: None
fake_st.image = lambda *args, **kwargs: None
fake_st.image = lambda *args, **kwargs: None
fake_st.markdown = lambda *args, **kwargs: None
fake_st.caption = lambda *args, **kwargs: None
fake_st.warning = lambda *args, **kwargs: None
fake_st.error = lambda *args, **kwargs: None
fake_st.info = lambda *args, **kwargs: None
fake_st.success = lambda *args, **kwargs: None
fake_st.balloons = lambda *args, **kwargs: None
fake_st.rerun = lambda *args, **kwargs: None
fake_st.stop = lambda *args, **kwargs: None
fake_st.button = lambda *args, **kwargs: False
fake_st.number_input = lambda *args, **kwargs: kwargs.get("value", 0)
fake_st.slider = lambda *args, **kwargs: args[3] if len(args) > 3 else kwargs.get("value", 1)
fake_st.columns = lambda specs, **kwargs: [Context() for _ in specs]
fake_st.tabs = lambda labels, **kwargs: [Context() for _ in labels]
fake_st.line_chart = lambda *args, **kwargs: None
fake_st.altair_chart = lambda *args, **kwargs: None
fake_st.bar_chart = lambda *args, **kwargs: None
fake_st.dataframe = lambda *args, **kwargs: None
fake_st.download_button = lambda *args, **kwargs: False
sys.modules["streamlit"] = fake_st

sys.modules["gspread"] = types.ModuleType("gspread")

fake_altair = types.ModuleType("altair")
sys.modules["altair"] = fake_altair

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

runpy.run_path(str(ROOT / "streamlit_app.py"), run_name="__main__")
print("OK: streamlit_app.py completó un arranque simulado")
