# -*- coding: utf-8 -*-
"""LagartijApp v4.1 — Fase 0 de orden y persistencia.

La apariencia se mantiene. La lógica se separó en módulos y Google Sheets
pasó a ser la fuente principal de datos.
"""

import altair as alt
import streamlit as st

from app.components import calendario_html, descargar_csv, rings_html
from app.config import (
    APP_NAME,
    STYLES_FILE,
    TIPO_DESCANSO,
    TIPO_ESTOCADAS,
    TIPO_FLEXIONES,
    TIPO_PESO,
    TIPO_PLANCHA,
    TIPO_SENTADILLAS,
)
from app.data_repository import cargar_datos
from app.metrics import (
    actividad_horaria,
    datos_hoy,
    fmt,
    max_diario,
    peso_actual,
    peso_semanal,
    progreso_diario,
    total_hoy,
)
from app.time_utils import hoy_chile
from app.workout_service import (
    guardar_registro_simple,
    registrar_con_pr,
    registrar_lote_con_pr,
)

st.set_page_config(
    page_title=APP_NAME,
    page_icon="L",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Streamlit interpreta directamente un archivo .css pasado a st.html.
st.html(STYLES_FILE)


def sync_deuda(input_key: str, state_key: str) -> None:
    st.session_state[state_key] = int(st.session_state.get(input_key, 0) or 0)


# ─────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────

defaults = {
    "show_balloons": False,
    "pr_msg": [],
    "deuda_flex": 0,
    "deuda_plan": 0,
    "deuda_ver": 0,
    "manual_ver": 0,
    "express_ok": False,
    "deuda_ok": False,
    "guardado_ok": False,
    "sick_ok": False,
    "datos_version": 0,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────

df, estado_datos = cargar_datos()

if estado_datos.nivel == "warning":
    st.warning(estado_datos.mensaje)
elif estado_datos.nivel == "error":
    st.error(estado_datos.mensaje)

with st.sidebar:
    st.caption(f"Datos: {estado_datos.fuente}")
    st.markdown("**Peso diario**")
    peso_sidebar = st.number_input("Peso (kg)", min_value=0.0, max_value=300.0, value=0.0, step=0.1, format="%.1f", key="peso_sidebar")
    
    st.markdown('<div class="btn-subtle">', unsafe_allow_html=True)
    if st.button("Guardar peso", width="stretch", key="btn_guardar_peso_sidebar"):
        if peso_sidebar > 0:
            guardar_registro_simple(df, TIPO_PESO, 0, peso=float(peso_sidebar))
            st.session_state.guardado_ok = True
            st.rerun()
        else:
            st.warning("Ingresa un peso valido.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Dia libre**")
    st.caption("Mantiene la racha activa.")
    st.markdown('<div class="btn-subtle">', unsafe_allow_html=True)
    if st.button("Marcar dia libre", width="stretch", key="btn_dia_libre_sidebar"):
        hd = datos_hoy(df)
        ya = not hd.empty and (hd["Tipo_Ejercicio"] == TIPO_DESCANSO).any()
        if ya:
            st.warning("Ya marcaste dia libre hoy.")
        else:
            guardar_registro_simple(df, TIPO_DESCANSO, 0)
            st.session_state.sick_ok = True
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Esfuerzo (RPE)**")
    rpe_actual = st.slider("RPE", 1, 10, 7, help="1 = facil · 10 = maximo")


# ─────────────────────────────────────────────────────────────
# CÁLCULOS
# ─────────────────────────────────────────────────────────────

flex_hoy = total_hoy(df, TIPO_FLEXIONES)
plan_hoy = total_hoy(df, TIPO_PLANCHA)
sent_hoy = total_hoy(df, TIPO_SENTADILLAS)
est_hoy = total_hoy(df, TIPO_ESTOCADAS)

peso_ult = peso_actual(df)

pr_flex = max_diario(df, TIPO_FLEXIONES, excluir_hoy=False)
pr_plan = max_diario(df, TIPO_PLANCHA, excluir_hoy=False)
pr_sent = max_diario(df, TIPO_SENTADILLAS, excluir_hoy=False)
pr_est = max_diario(df, TIPO_ESTOCADAS, excluir_hoy=False)



# ─────────────────────────────────────────────────────────────
# TOP BAR + BOTÓN SUPERIOR
# ─────────────────────────────────────────────────────────────

fecha_txt = hoy_chile().strftime("%d/%m/%Y")

st.markdown(f"""
<div class="ios-topbar">
  <span class="ios-topbar-title">LagartijApp</span>
  <span class="ios-topbar-date">{fecha_txt}</span>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="btn-top-bath">', unsafe_allow_html=True)

if st.button("FUI AL BAÑO", width="stretch", key="btn_top_bath"):
    registrar_lote_con_pr(
        df,
        [
            {"Tipo_Ejercicio": TIPO_FLEXIONES, "Cantidad": 5, "Peso": peso_ult, "RPE_Esfuerzo": rpe_actual},
            {"Tipo_Ejercicio": TIPO_PLANCHA, "Cantidad": 20, "Peso": peso_ult, "RPE_Esfuerzo": rpe_actual},
            {"Tipo_Ejercicio": TIPO_SENTADILLAS, "Cantidad": 5, "Peso": peso_ult, "RPE_Esfuerzo": rpe_actual},
            {"Tipo_Ejercicio": TIPO_ESTOCADAS, "Cantidad": 5, "Peso": peso_ult, "RPE_Esfuerzo": rpe_actual},
        ],
    )
    st.session_state.express_ok = True
    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# MENSAJES
# ─────────────────────────────────────────────────────────────

if st.session_state.show_balloons:
    st.balloons()
    st.session_state.show_balloons = False

for msg in st.session_state.pr_msg:
    st.success(msg)

st.session_state.pr_msg = []

if st.session_state.express_ok:
    st.success("Rutina express completada: +5 Flex, +20s Plancha, +5 Sentadillas, +5 Estocadas.")
    st.session_state.express_ok = False

if st.session_state.deuda_ok:
    st.success("Deuda saldada.")
    st.session_state.deuda_ok = False

if st.session_state.guardado_ok:
    st.success("Guardado.")
    st.session_state.guardado_ok = False

if st.session_state.sick_ok:
    st.success("Dia libre registrado.")
    st.session_state.sick_ok = False


# ─────────────────────────────────────────────────────────────
# DASHBOARD DE ANILLOS Y ESTADÍSTICAS
# ─────────────────────────────────────────────────────────────

st.markdown('<div class="rings-master-card">', unsafe_allow_html=True)
col_ring, col_data = st.columns([1.05, 0.95])

with col_ring:
    st.markdown('<div class="ring-visual-wrap">', unsafe_allow_html=True)
    st.image(rings_html(flex_hoy, plan_hoy), width=260)
    st.markdown("</div>", unsafe_allow_html=True)

with col_data:
    st.markdown(f"""
<div class="ring-data-stack">
  <div class="ring-stat">
    <div class="ring-stat-label">Flexiones</div>
    <div class="ring-stat-value c-pink">{flex_hoy}</div>
  </div>
  <div class="ring-stat">
    <div class="ring-stat-label">Plancha</div>
    <div class="ring-stat-value c-lime">{plan_hoy}s</div>
  </div>
  <div class="ring-stat">
    <div class="ring-stat-label">Sentadillas</div>
    <div class="ring-stat-value c-cyan">{sent_hoy}</div>
  </div>
  <div class="ring-stat">
    <div class="ring-stat-label">Estocadas (X Pierna)</div>
    <div class="ring-stat-value c-orange">{est_hoy}</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────

tab_e, tab_d, tab_p, tab_a = st.tabs(["Entreno", "Oficina / Calle", "Peso", "Analisis"])


# ══════════════════════════════════════════════════════════════
# TAB 1 — ENTRENO
# ══════════════════════════════════════════════════════════════

with tab_e:
    # ── FLEXIONES ──
    st.markdown("""
<div class="exercise-card">
  <div class="card-label">Ejercicio</div>
  <div class="exercise-title c-pink">FLEXIONES</div>
  <div class="exercise-subtitle">Un toque registra 5 repeticiones.</div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="btn-pink">', unsafe_allow_html=True)
    if st.button("+ 5 Flexiones", width="stretch", key="btn_f5"):
        registrar_con_pr(df, TIPO_FLEXIONES, 5, peso=peso_ult, rpe=rpe_actual)
        st.session_state.guardado_ok = True
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    mfk = f"mf_{st.session_state.manual_ver}"
    st.markdown('<div class="manual-row">', unsafe_allow_html=True)
    mf = st.number_input("Cantidad exacta de flexiones", min_value=0, max_value=3000, value=0, step=1, key=mfk)
    st.markdown("</div>", unsafe_allow_html=True)
    if mf > 0:
        st.markdown('<div class="btn-pink">', unsafe_allow_html=True)
        if st.button("Guardar flexiones", width="stretch", key="btn_mf"):
            registrar_con_pr(df, TIPO_FLEXIONES, int(mf), peso=peso_ult, rpe=rpe_actual)
            st.session_state.manual_ver += 1
            st.session_state.guardado_ok = True
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── PLANCHA ──
    st.markdown("""
<div class="exercise-card">
  <div class="card-label">Ejercicio</div>
  <div class="exercise-title c-lime">PLANCHA</div>
  <div class="exercise-subtitle">Un toque registra 10 segundos.</div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="btn-lime">', unsafe_allow_html=True)
    if st.button("+ 10 segundos", width="stretch", key="btn_p10"):
        registrar_con_pr(df, TIPO_PLANCHA, 10, peso=peso_ult, rpe=rpe_actual)
        st.session_state.guardado_ok = True
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    mpk = f"mp_{st.session_state.manual_ver}"
    st.markdown('<div class="manual-row">', unsafe_allow_html=True)
    mp = st.number_input("Segundos exactos de plancha", min_value=0, max_value=30000, value=0, step=5, key=mpk)
    st.markdown("</div>", unsafe_allow_html=True)
    if mp > 0:
        st.markdown('<div class="btn-lime">', unsafe_allow_html=True)
        if st.button("Guardar plancha", width="stretch", key="btn_mp"):
            registrar_con_pr(df, TIPO_PLANCHA, int(mp), peso=peso_ult, rpe=rpe_actual)
            st.session_state.manual_ver += 1
            st.session_state.guardado_ok = True
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── SENTADILLAS ──
    st.markdown("""
<div class="exercise-card">
  <div class="card-label">Ejercicio</div>
  <div class="exercise-title c-cyan">SENTADILLAS</div>
  <div class="exercise-subtitle">Un toque registra 5 repeticiones.</div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="btn-cyan">', unsafe_allow_html=True)
    if st.button("+ 5 Sentadillas", width="stretch", key="btn_s5"):
        registrar_con_pr(df, TIPO_SENTADILLAS, 5, peso=peso_ult, rpe=rpe_actual)
        st.session_state.guardado_ok = True
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    msk = f"ms_{st.session_state.manual_ver}"
    st.markdown('<div class="manual-row">', unsafe_allow_html=True)
    ms = st.number_input("Cantidad exacta de sentadillas", min_value=0, max_value=3000, value=0, step=1, key=msk)
    st.markdown("</div>", unsafe_allow_html=True)
    if ms > 0:
        st.markdown('<div class="btn-cyan">', unsafe_allow_html=True)
        if st.button("Guardar sentadillas", width="stretch", key="btn_ms"):
            registrar_con_pr(df, TIPO_SENTADILLAS, int(ms), peso=peso_ult, rpe=rpe_actual)
            st.session_state.manual_ver += 1
            st.session_state.guardado_ok = True
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── ESTOCADAS ──
    st.markdown("""
<div class="exercise-card">
  <div class="card-label">Ejercicio</div>
  <div class="exercise-title c-orange">ESTOCADAS</div>
  <div class="exercise-subtitle">Un toque registra 5 repeticiones (por pierna).</div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="btn-orange-big">', unsafe_allow_html=True)
    if st.button("+ 5 Estocadas (x pierna)", width="stretch", key="btn_e5"):
        registrar_con_pr(df, TIPO_ESTOCADAS, 5, peso=peso_ult, rpe=rpe_actual)
        st.session_state.guardado_ok = True
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    mek = f"me_{st.session_state.manual_ver}"
    st.markdown('<div class="manual-row">', unsafe_allow_html=True)
    me = st.number_input("Cantidad exacta de estocadas (x pierna)", min_value=0, max_value=3000, value=0, step=1, key=mek)
    st.markdown("</div>", unsafe_allow_html=True)
    if me > 0:
        st.markdown('<div class="btn-orange-big">', unsafe_allow_html=True)
        if st.button("Guardar estocadas", width="stretch", key="btn_me"):
            registrar_con_pr(df, TIPO_ESTOCADAS, int(me), peso=peso_ult, rpe=rpe_actual)
            st.session_state.manual_ver += 1
            st.session_state.guardado_ok = True
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 2 — DEUDA / OFICINA
# ══════════════════════════════════════════════════════════════

with tab_d:
    st.markdown(f"""
<div class="fit-card">
  <div class="card-label">Modo Oficina / Calle</div>
  <div class="card-title">Deuda pendiente</div>
  <div class="card-sub">Acumula lo que debes y saldalo de un toque.</div>
  <div class="debt-display">
    <div class="debt-number">{st.session_state.deuda_flex} flex &nbsp;/&nbsp; {fmt(st.session_state.deuda_plan)}</div>
    <div class="debt-sub">Pendiente ahora</div>
  </div>
</div>
""", unsafe_allow_html=True)

    dv = st.session_state.deuda_ver
    dfk = f"df_{dv}"
    dpk = f"dp_{dv}"

    st.number_input("Flexiones pendientes", min_value=0, max_value=3000, value=st.session_state.deuda_flex, step=5, key=dfk, on_change=sync_deuda, args=(dfk, "deuda_flex"))
    st.number_input("Segundos de plancha pendientes", min_value=0, max_value=30000, value=st.session_state.deuda_plan, step=10, key=dpk, on_change=sync_deuda, args=(dpk, "deuda_plan"))

    st.markdown('<div class="btn-orange">', unsafe_allow_html=True)
    if st.button("Saldar deuda", width="stretch", key="btn_saldar"):
        fd = int(st.session_state.deuda_flex)
        pd_ = int(st.session_state.deuda_plan)
        registros_deuda = []
        if fd > 0:
            registros_deuda.append({"Tipo_Ejercicio": TIPO_FLEXIONES, "Cantidad": fd, "Peso": peso_ult, "RPE_Esfuerzo": rpe_actual})
        if pd_ > 0:
            registros_deuda.append({"Tipo_Ejercicio": TIPO_PLANCHA, "Cantidad": pd_, "Peso": peso_ult, "RPE_Esfuerzo": rpe_actual})

        if registros_deuda:
            registrar_lote_con_pr(df, registros_deuda)

        if fd > 0 or pd_ > 0:
            st.session_state.deuda_flex = 0
            st.session_state.deuda_plan = 0
            st.session_state.deuda_ver += 1
            st.session_state.deuda_ok = True
            st.rerun()
        else:
            st.warning("No hay deuda pendiente.")
    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 3 — PESO
# ══════════════════════════════════════════════════════════════

with tab_p:
    st.markdown("""
<div class="fit-card">
  <div class="card-label">Peso</div>
  <div class="card-title">Registro de peso</div>
  <div class="card-sub">Ingresa tu peso actual y guardalo. Abajo se muestra la evolucion semanal.</div>
</div>
""", unsafe_allow_html=True)

    peso_tab = st.number_input("Peso actual (kg)", min_value=0.0, max_value=300.0, value=0.0, step=0.1, format="%.1f", key="peso_tab")

    st.markdown('<div class="btn-blue">', unsafe_allow_html=True)
    if st.button("Guardar peso", width="stretch", key="btn_guardar_peso_tab"):
        if peso_tab > 0:
            guardar_registro_simple(df, TIPO_PESO, 0, peso=float(peso_tab))
            st.session_state.guardado_ok = True
            st.rerun()
        else:
            st.warning("Ingresa un peso valido.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("""
<div class="fit-card" style="margin-top:16px">
  <div class="card-label">Peso</div>
  <div class="card-title">Evolucion semanal</div>
  <div class="card-sub">Ultimos 7 dias registrados.</div>
</div>
""", unsafe_allow_html=True)

    pdf = peso_semanal(df)
    if not pdf.empty:
        st.line_chart(pdf, width="stretch", height=260, color="#0A84FF")
    else:
        st.info("Sin registros de peso aun.")


# ══════════════════════════════════════════════════════════════
# TAB 4 — ANALISIS
# ══════════════════════════════════════════════════════════════

with tab_a:
    st.markdown("""
<div class="fit-card">
  <div class="card-label">Hoy</div>
  <div class="card-title">Actividad horaria</div>
  <div class="card-sub">Distribucion de registros por hora local de Chile.</div>
</div>
""", unsafe_allow_html=True)

    hdf = actividad_horaria(df)
    if not hdf.empty and hdf["Cantidad"].sum() > 0:
        hdf["activo"] = hdf["Cantidad"].apply(lambda x: "activo" if x > 0 else "inactivo")
        chart = (
            alt.Chart(hdf)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("Hora:O", title="Hora"),
                y=alt.Y("Cantidad:Q", title=""),
                color=alt.Color("activo:N", scale=alt.Scale(domain=["activo", "inactivo"], range=["#00FFFF", "#3A3A3C"]), legend=None),
                tooltip=["Hora", "Tipo_Ejercicio", "Cantidad"],
            )
            .properties(height=240)
            .configure_view(strokeWidth=0)
            .configure_axis(labelColor="#8E8E93", titleColor="#8E8E93", gridColor="rgba(255,255,255,0.06)")
            .configure(background="#000000")
        )
        st.altair_chart(chart, width="stretch")
    else:
        st.info("Sin actividad registrada hoy.")

    st.markdown("""
<div class="fit-card">
  <div class="card-label">Ultimos 35 dias</div>
  <div class="card-title">Calendario</div>
  <div class="card-sub">Verde: actividad. Naranja: dia libre. Gris: sin registro.</div>
</div>
""", unsafe_allow_html=True)

    st.markdown(calendario_html(df, dias=35), unsafe_allow_html=True)

    st.markdown(f"""
<div class="impact-grid" style="margin-top:16px">
  <div class="impact-card">
    <div class="impact-label">Record Flexiones</div>
    <div class="impact-val c-pink">{pr_flex}</div>
  </div>
  <div class="impact-card">
    <div class="impact-label">Record Plancha</div>
    <div class="impact-val c-lime">{fmt(pr_plan)}</div>
  </div>
  <div class="impact-card">
    <div class="impact-label">Record Sentadillas</div>
    <div class="impact-val c-cyan">{pr_sent}</div>
  </div>
  <div class="impact-card">
    <div class="impact-label">Record Estocadas</div>
    <div class="impact-val c-orange">{pr_est}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="fit-card" style="margin-top:16px">
  <div class="card-label">14 dias</div>
  <div class="card-title">Progreso</div>
</div>
""", unsafe_allow_html=True)

    fc = progreso_diario(df, TIPO_FLEXIONES, 14)
    pc = progreso_diario(df, TIPO_PLANCHA, 14)
    sc = progreso_diario(df, TIPO_SENTADILLAS, 14)
    ec = progreso_diario(df, TIPO_ESTOCADAS, 14)

    if not fc.empty:
        st.markdown('<p style="color:#FF2D55;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;margin-bottom:4px">Flexiones</p>', unsafe_allow_html=True)
        st.bar_chart(fc, width="stretch", height=180, color="#FF2D55")
    
    if not pc.empty:
        st.markdown('<p style="color:#A1FF00;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;margin:8px 0 4px">Plancha</p>', unsafe_allow_html=True)
        st.bar_chart(pc, width="stretch", height=180, color="#A1FF00")
        
    if not sc.empty:
        st.markdown('<p style="color:#00FFFF;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;margin:8px 0 4px">Sentadillas</p>', unsafe_allow_html=True)
        st.bar_chart(sc, width="stretch", height=180, color="#00FFFF")

    if not ec.empty:
        st.markdown('<p style="color:#FF9500;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;margin:8px 0 4px">Estocadas</p>', unsafe_allow_html=True)
        st.bar_chart(ec, width="stretch", height=180, color="#FF9500")

    st.markdown("""
<div class="fit-card" style="margin-top:16px">
  <div class="card-label">CSV</div>
  <div class="card-title">Base de datos</div>
</div>
""", unsafe_allow_html=True)

    st.dataframe(df.sort_values("Fecha", ascending=False), width="stretch", hide_index=True)

    st.markdown('<div class="btn-blue">', unsafe_allow_html=True)
    st.download_button(label="Descargar CSV", data=descargar_csv(df), file_name="data_lagartijas.csv", mime="text/csv", width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)