# Guía detallada — Fase 0 de LagartijApp

## 1. Qué estamos haciendo realmente

La Fase 0 no busca agregar funciones nuevas. Su objetivo es convertir el proyecto
actual en una base confiable para que después podamos rediseñarlo, conectar
running y agregar inteligencia artificial sin que todo dependa de un único
archivo gigante.

Piensa en esto como ordenar una casa antes de ampliarla:

- `streamlit_app.py` queda encargado de mostrar pantallas y responder a botones.
- `data_repository.py` se encarga solamente de guardar y leer datos.
- `metrics.py` calcula récords, rachas y resúmenes.
- `components.py` construye los anillos y el calendario.
- `styles.css` concentra la apariencia.

La aplicación visible se mantiene casi igual en esta fase.

---

## 2. Cambio más importante: Google Sheets es la fuente principal

### Antes

1. La app leía `data_lagartijas.csv`.
2. Al registrar algo, lo agregaba primero a Google Sheets.
3. También lo agregaba al CSV de la máquina temporal de Streamlit.
4. Cuando Streamlit reconstruía la máquina, volvía a aparecer el CSV guardado en
   GitHub, aunque Google Sheets tuviera registros más nuevos.

### Ahora

1. La app intenta leer Google Sheets al iniciar.
2. Si funciona, esos datos construyen todo el dashboard.
3. La app crea además una copia local en CSV.
4. Si Google Sheets falla, se muestra una advertencia y se usa el CSV de respaldo.
5. La barra lateral indica la fuente actual:
   - `Datos: Google Sheets` significa funcionamiento normal.
   - `Datos: CSV local de respaldo` significa que debes revisar la conexión.

El CSV ya no debe considerarse la base de datos oficial.

---

## 3. Cambio de seguridad: una rutina completa se guarda de una vez

Antes, el botón `FUI AL BAÑO` hacía cuatro solicitudes separadas:

1. Flexiones.
2. Plancha.
3. Sentadillas.
4. Estocadas.

Si la tercera solicitud fallaba, podías quedar con una rutina incompleta.

Ahora se construyen las cuatro filas y se envían con una sola llamada a Google
Sheets. La deuda de flexiones y plancha usa el mismo sistema por lote.

---

## 4. Preparación antes de subir cualquier archivo

### 4.1 Respaldar Google Sheets

1. Abre `LagartijApp_DB` en Google Sheets.
2. En el menú superior, entra a `Archivo`.
3. Selecciona `Descargar`.
4. Descarga una copia como Microsoft Excel o CSV.
5. Guarda esa copia en tu computador con una fecha, por ejemplo:

```text
LagartijApp_DB_respaldo_2026-07-29.xlsx
```

No vamos a borrar datos, pero este respaldo permite experimentar tranquilo.

### 4.2 Revisar la primera fila

En la primera hoja de `LagartijApp_DB`, las columnas A a E deben corresponder a:

```text
A: Fecha
B: Tipo_Ejercicio
C: Cantidad
D: Peso
E: RPE_Esfuerzo
```

Una sexta columna antigua no molesta. El nuevo código solo toma las primeras
cinco columnas.

### 4.3 No tocar los secretos

No subas ninguno de estos elementos a GitHub:

- `.streamlit/secrets.toml`
- `private_key`
- archivos JSON de la cuenta de servicio
- capturas donde aparezca la clave completa

Los secretos actuales de Streamlit Cloud pueden mantenerse tal como están.

---

## 5. Método recomendado: probar en una rama separada

No reemplaces directamente `main`. Primero crearemos una rama de prueba llamada
`fase-0-orden`.

### 5.1 Abrir un Codespace

1. Entra al repositorio `lagartijapp2` en GitHub.
2. Presiona el botón verde `Code`.
3. Abre la pestaña `Codespaces`.
4. Abre tu Codespace existente o crea uno nuevo.
5. Espera hasta ver el editor y la terminal.

### 5.2 Crear la rama

En la terminal del Codespace ejecuta:

```bash
git checkout -b fase-0-orden
```

Para confirmar la rama:

```bash
git branch --show-current
```

Debe responder:

```text
fase-0-orden
```

### 5.3 Subir el ZIP limpio

1. Descarga `lagartijapp_fase0_repo.zip` desde el chat.
2. En el explorador de archivos del Codespace, haz clic derecho sobre la carpeta
   raíz del repositorio.
3. Elige `Upload...`.
4. Sube el ZIP.
5. En la terminal ejecuta:

```bash
unzip -o lagartijapp_fase0_repo.zip
rm lagartijapp_fase0_repo.zip
```

El comando `unzip -o` reemplaza los archivos antiguos que tengan el mismo nombre
y agrega las carpetas nuevas.

### 5.4 Eliminar dos archivos antiguos

El proyecto anterior tenía archivos en ubicaciones incorrectas:

```bash
rm -f gitignore.txt devcontainer.json launch.json
```

El nuevo proyecto usa correctamente:

```text
.gitignore
.devcontainer/devcontainer.json
.vscode/launch.json
```

### 5.5 Sacar el CSV personal del historial de Git

Ejecuta:

```bash
git rm --cached data_lagartijas.csv
```

Este comando deja de rastrear el archivo en Git, pero normalmente conserva la
copia local. Si Git responde que el archivo no está rastreado, no es un problema.

Comprueba que existe el archivo de ejemplo:

```bash
ls data_lagartijas.example.csv
```

---

## 6. Instalar y comprobar

### 6.1 Instalar dependencias

```bash
python -m pip install -r requirements.txt
```

### 6.2 Ejecutar pruebas de datos

```bash
python tests/test_phase0.py
```

Debes ver seis líneas que comienzan con `OK:`.

Las pruebas comprueban:

- El formato actual del CSV.
- La migración de formatos antiguos.
- La lectura de una hoja con sexta columna extra.
- El guardado local por lote.
- Que un lote remoto utiliza una sola llamada.
- Que una hoja remota vacía no tape un respaldo local con datos.

### 6.3 Ejecutar el arranque simulado

```bash
python tests/smoke_test_app.py
```

Debe aparecer:

```text
OK: streamlit_app.py completó un arranque simulado
```

### 6.4 Ejecutar la app

```bash
streamlit run streamlit_app.py
```

Codespaces debería abrir automáticamente el puerto 8501. Si aparece una
notificación, presiona `Open in Browser`.

En Codespaces probablemente verás:

```text
Datos: CSV local
```

Eso es normal porque los secretos de Streamlit Cloud no se copian al Codespace.
Esta prueba sirve para revisar que la interfaz abra y que los botones funcionen
localmente.

---

## 7. Revisar los cambios antes de enviarlos

Ejecuta:

```bash
git status
```

Luego:

```bash
git diff --stat
```

Deberías ver:

- `streamlit_app.py` modificado.
- Nuevas carpetas `app/`, `assets/`, `.streamlit/`, `.devcontainer/`, `.vscode/`
  y `tests/`.
- `gitignore.txt`, `devcontainer.json` y `launch.json` eliminados.
- `data_lagartijas.csv` retirado del seguimiento.

No debe aparecer `secrets.toml`.

---

## 8. Guardar la rama en GitHub

```bash
git add .
git commit -m "Fase 0: ordenar datos y estructura de LagartijApp"
git push -u origin fase-0-orden
```

Esto no modifica todavía la aplicación principal porque el despliegue actual usa
la rama `main`.

---

## 9. Crear una aplicación temporal de prueba en Streamlit

Esta es la parte más segura porque permite probar Google Sheets sin tocar la app
principal.

1. Entra a tu espacio de Streamlit Community Cloud.
2. Presiona `Create app`.
3. Selecciona el repositorio `lagartijapp2`.
4. En `Branch`, escribe `fase-0-orden`.
5. En `Main file path`, escribe `streamlit_app.py`.
6. Usa un nombre temporal, por ejemplo `lagartijapp-fase0-test`.
7. En la configuración avanzada, copia los mismos secretos que usa la app actual.
8. Despliega.

No copies la clave desde GitHub. Cópiala desde la configuración segura de la app
actual o desde el archivo privado original.

---

## 10. Lista exacta de pruebas en la app temporal

Realiza estas pruebas en orden:

### Prueba A — lectura histórica

1. Abre la barra lateral.
2. Confirma que diga `Datos: Google Sheets`.
3. Revisa que el total y los registros históricos coincidan con Google Sheets.

### Prueba B — registro individual

1. Presiona `+ 5 Flexiones` una sola vez.
2. Confirma el mensaje de guardado.
3. Abre `LagartijApp_DB`.
4. Verifica que aparezca una sola fila nueva.
5. Actualiza el navegador.
6. Confirma que las cinco flexiones permanezcan.

### Prueba C — rutina express

1. Anota la última fila actual de Google Sheets.
2. Presiona `FUI AL BAÑO` una sola vez.
3. Comprueba que aparezcan cuatro filas nuevas:
   - Flexiones: 5
   - Plancha: 20
   - Sentadillas: 5
   - Estocadas: 5
4. Las cuatro deben tener una hora prácticamente idéntica.

### Prueba D — reinicio real

1. En Streamlit, abre la administración de la app temporal.
2. Elige `Reboot`.
3. Cuando vuelva a iniciar, confirma que el historial siga intacto.

### Prueba E — logs

Revisa los logs. No deberían aparecer las advertencias anteriores sobre:

```text
use_container_width
st.components.v1.html
inotify instance limit reached
```

---

## 11. Pasar la Fase 0 a producción

Solo después de completar todas las pruebas:

1. Abre GitHub.
2. Entra al repositorio.
3. GitHub ofrecerá crear un Pull Request desde `fase-0-orden`.
4. Crea el Pull Request.
5. Revisa que no incluya secretos.
6. Presiona `Merge pull request`.
7. Confirma el merge hacia `main`.

La aplicación principal debería detectar el cambio de GitHub y actualizarse.
Si cambió `requirements.txt`, puede hacer una reconstrucción completa.

---

## 12. Qué hacer si algo falla

### La app dice `CSV local de respaldo`

La interfaz está funcionando, pero Google Sheets no pudo leerse. Revisa:

1. Que los secretos estén cargados en la app temporal.
2. Que `client_email` sea correcto.
3. Que `LagartijApp_DB` esté compartido con ese `client_email` como editor.
4. Que el nombre del archivo sea exactamente `LagartijApp_DB`.
5. Que la clave privada conserve BEGIN, END y saltos de línea válidos.

### La app abre, pero no muestra datos

Revisa la primera fila de Google Sheets y que las fechas estén en la columna A.

### El botón muestra error de Google Sheets

La nueva versión no finge que guardó. Si la escritura remota falla, muestra el
error y detiene el proceso para evitar que creas que el registro está seguro.

### La app temporal falla completamente

No mezcles la rama. La aplicación principal sigue usando `main` y debería seguir
intacta.

---

## 13. Resultado esperado al terminar

Al terminar la Fase 0 tendremos:

- Una base de datos remota que realmente alimenta el dashboard.
- Un respaldo CSV automático.
- Guardados múltiples más seguros.
- Un archivo principal mucho más corto.
- CSS separado.
- Dependencias reproducibles.
- Configuración ordenada.
- Una base lista para el rediseño Lagartija.

La siguiente fase será visual. Ahí sí reemplazaremos la identidad Apple sin tocar
nuevamente la lógica de persistencia.
