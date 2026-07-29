# LagartijApp

Aplicación personal de hábitos y entrenamiento construida con Streamlit.
Registra flexiones, plancha, sentadillas, estocadas, peso, RPE y días libres.

## Estado del proyecto

Esta versión corresponde a la **Fase 0 de orden y persistencia**:

- Google Sheets es la fuente principal de datos.
- El CSV funciona como espejo local y respaldo de desarrollo.
- Las rutinas múltiples se guardan mediante una sola llamada a Google Sheets.
- La lógica fue separada en módulos sin cambiar todavía la apariencia.
- Se reemplazaron APIs antiguas de Streamlit.
- Se fijaron las versiones de las dependencias.

## Estructura

```text
.
├── streamlit_app.py            # Pantallas, botones y flujo principal
├── app/
│   ├── config.py               # Nombres, metas y rutas
│   ├── time_utils.py           # Hora de Chile
│   ├── data_repository.py      # Google Sheets y CSV
│   ├── metrics.py              # Rachas, récords y resúmenes
│   ├── components.py           # Anillos y calendario HTML
│   └── workout_service.py      # Guardados y avisos de récord
├── assets/
│   └── styles.css              # Estilo visual actual
├── .streamlit/
│   └── config.toml             # Configuración de Streamlit
├── tests/
│   └── test_phase0.py          # Pruebas básicas de datos
└── requirements.txt
```

## Ejecutar localmente

```bash
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

Sin un archivo local `.streamlit/secrets.toml`, la app entra en modo CSV local.
Nunca subas `secrets.toml` ni una clave privada al repositorio.

## Probar la lógica de datos

```bash
python tests/test_phase0.py
python tests/smoke_test_app.py
```

## Configuración de Google Sheets

El archivo de Google debe llamarse `LagartijApp_DB`. La primera hoja debe usar,
como mínimo, estas cinco columnas en este orden:

```text
Fecha | Tipo_Ejercicio | Cantidad | Peso | RPE_Esfuerzo
```

Puede existir una sexta columna antigua; esta versión la ignora al leer.

Consulta `GUIA_FASE_0.md` antes de desplegar.
