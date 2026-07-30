# -*- coding: utf-8 -*-
"""LagartijApp v4.1 — Fase 0 de orden y persistencia.

La apariencia se mantiene. La lógica se separó en módulos y Google Sheets
pasó a ser la fuente principal de datos.
"""

import altair as alt
import pandas as pd
import streamlit as st
from PIL import Image

from app.components import (
    calendario_html,
    dashboard_html,
    descargar_csv,
    image_data_uri,
)
from app.config import (
    APP_NAME,
    STYLES_FILE,
    TIM_LOGO_FILE,
    TIM_HERO_FILE,
    TIM_PEEK_FILE,
    TIM_DASH_FILE,
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
    page_icon=Image.open(TIM_LOGO_FILE),
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Streamlit interpreta directamente un archivo .css pasado a st.html.
st.html(STYLES_FILE)
st.logo(str(TIM_LOGO_FILE), icon_image=str(TIM_LOGO_FILE))


def sync_deuda(input_key: str, state_key: str) -> None:
    st.session_state[state_key] = int(st.session_state.get(input_key, 0) or 0)


def tim_bar_chart(series, color: str, height: int = 180):
    """Bar chart con fondo azul Tim Energy, evitando el negro por defecto."""
    sdf = series.reset_index()
    sdf.columns = ["Fecha", "Cantidad"]
    sdf["Fecha"] = sdf["Fecha"].astype(str)

    chart = (
        alt.Chart(sdf)
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
        .encode(
            x=alt.X("Fecha:O", title=None, axis=alt.Axis(labelAngle=-90, labelPadding=8)),
            y=alt.Y("Cantidad:Q", title=None),
            color=alt.value(color),
            tooltip=["Fecha", "Cantidad"],
        )
        .properties(height=height)
        .configure_view(strokeWidth=0, fill="#071A52")
        .configure_axis(
            labelColor="#D7E3FF",
            titleColor="#D7E3FF",
            gridColor="rgba(180,210,255,0.12)",
        )
        .configure(background="#071A52")
    )
    st.altair_chart(chart, width="stretch")


def tim_line_chart(pdf, color: str = "#62C5FF", height: int = 260):
    """Line chart con estética azul integrada."""
    ldf = pdf.reset_index()
    if len(ldf.columns) == 2:
        ldf.columns = ["Fecha", "Valor"]
    else:
        ldf = ldf.iloc[:, :2]
        ldf.columns = ["Fecha", "Valor"]
    ldf["Fecha"] = ldf["Fecha"].astype(str)

    chart = (
        alt.Chart(ldf)
        .mark_line(point=True, strokeWidth=3)
        .encode(
            x=alt.X("Fecha:O", title=None, axis=alt.Axis(labelAngle=-35, labelPadding=8)),
            y=alt.Y("Valor:Q", title=None),
            color=alt.value(color),
            tooltip=["Fecha", "Valor"],
        )
        .properties(height=height)
        .configure_view(strokeWidth=0, fill="#071A52")
        .configure_axis(
            labelColor="#D7E3FF",
            titleColor="#D7E3FF",
            gridColor="rgba(180,210,255,0.12)",
        )
        .configure(background="#071A52")
    )
    st.altair_chart(chart, width="stretch")


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
tim_logo_uri = image_data_uri(TIM_LOGO_FILE)
tim_hero_uri = image_data_uri(TIM_HERO_FILE)
tim_peek_uri = image_data_uri(TIM_PEEK_FILE)
tim_dash_uri = image_data_uri(TIM_DASH_FILE)

st.markdown(
    f"""
<div class="ios-topbar">
  <img class="tim-topbar-logo" src="{tim_logo_uri}" alt="Tim">
  <div class="tim-topbar-copy">
    <span class="ios-topbar-title">LagartijApp</span>
    <span class="tim-topbar-subtitle">Muévete un poco. Suma todos los días.</span>
  </div>
  <span class="ios-topbar-date">{fecha_txt}</span>
</div>
""",
    unsafe_allow_html=True,
)

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

st.html(
    dashboard_html(
        flexiones=flex_hoy,
        plancha=plan_hoy,
        sentadillas=sent_hoy,
        estocadas=est_hoy,
        tim_uri=tim_dash_uri,
    )
)


# ─────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────

tab_e, tab_d, tab_p, tab_a = st.tabs(
    ["Entreno", "Oficina / Calle", "Peso", "Análisis"]
)


# ══════════════════════════════════════════════════════════════
# TAB 1 — ENTRENO
# ══════════════════════════════════════════════════════════════

with tab_e:
    with st.container(key="flex_zone"):
        if st.button(
            "FLEXIONES",
            width="stretch",
            key="btn_f5",
        ):
            registrar_con_pr(
                df,
                TIPO_FLEXIONES,
                5,
                peso=peso_ult,
                rpe=rpe_actual,
            )
            st.session_state.guardado_ok = True
            st.rerun()

        mfk = f"mf_{st.session_state.manual_ver}"
        mf = st.number_input(
            "Cantidad exacta de flexiones",
            min_value=0,
            max_value=3000,
            value=0,
            step=1,
            key=mfk,
        )
        if mf > 0 and st.button(
            "GUARDAR FLEXIONES EXACTAS",
            width="stretch",
            key="btn_mf",
        ):
            registrar_con_pr(
                df,
                TIPO_FLEXIONES,
                int(mf),
                peso=peso_ult,
                rpe=rpe_actual,
            )
            st.session_state.manual_ver += 1
            st.session_state.guardado_ok = True
            st.rerun()

    with st.container(key="plan_zone"):
        if st.button(
            "PLANCHA",
            width="stretch",
            key="btn_p10",
        ):
            registrar_con_pr(
                df,
                TIPO_PLANCHA,
                10,
                peso=peso_ult,
                rpe=rpe_actual,
            )
            st.session_state.guardado_ok = True
            st.rerun()

        mpk = f"mp_{st.session_state.manual_ver}"
        mp = st.number_input(
            "Segundos exactos de plancha",
            min_value=0,
            max_value=30000,
            value=0,
            step=5,
            key=mpk,
        )
        if mp > 0 and st.button(
            "GUARDAR PLANCHA EXACTA",
            width="stretch",
            key="btn_mp",
        ):
            registrar_con_pr(
                df,
                TIPO_PLANCHA,
                int(mp),
                peso=peso_ult,
                rpe=rpe_actual,
            )
            st.session_state.manual_ver += 1
            st.session_state.guardado_ok = True
            st.rerun()

    with st.container(key="sent_zone"):
        if st.button(
            "SENTADILLAS",
            width="stretch",
            key="btn_s5",
        ):
            registrar_con_pr(
                df,
                TIPO_SENTADILLAS,
                5,
                peso=peso_ult,
                rpe=rpe_actual,
            )
            st.session_state.guardado_ok = True
            st.rerun()

        msk = f"ms_{st.session_state.manual_ver}"
        ms = st.number_input(
            "Cantidad exacta de sentadillas",
            min_value=0,
            max_value=3000,
            value=0,
            step=1,
            key=msk,
        )
        if ms > 0 and st.button(
            "GUARDAR SENTADILLAS EXACTAS",
            width="stretch",
            key="btn_ms",
        ):
            registrar_con_pr(
                df,
                TIPO_SENTADILLAS,
                int(ms),
                peso=peso_ult,
                rpe=rpe_actual,
            )
            st.session_state.manual_ver += 1
            st.session_state.guardado_ok = True
            st.rerun()

    with st.container(key="est_zone"):
        if st.button(
            "ESTOCADAS",
            width="stretch",
            key="btn_e5",
        ):
            registrar_con_pr(
                df,
                TIPO_ESTOCADAS,
                5,
                peso=peso_ult,
                rpe=rpe_actual,
            )
            st.session_state.guardado_ok = True
            st.rerun()

        mek = f"me_{st.session_state.manual_ver}"
        me = st.number_input(
            "Cantidad exacta de estocadas por pierna",
            min_value=0,
            max_value=3000,
            value=0,
            step=1,
            key=mek,
        )
        if me > 0 and st.button(
            "GUARDAR ESTOCADAS EXACTAS",
            width="stretch",
            key="btn_me",
        ):
            registrar_con_pr(
                df,
                TIPO_ESTOCADAS,
                int(me),
                peso=peso_ult,
                rpe=rpe_actual,
            )
            st.session_state.manual_ver += 1
            st.session_state.guardado_ok = True
            st.rerun()


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
        tim_line_chart(pdf, color="#62C5FF", height=260)
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
                color=alt.Color("activo:N", scale=alt.Scale(domain=["activo", "inactivo"], range=["#9AF06B", "#284A82"]), legend=None),
                tooltip=["Hora", "Tipo_Ejercicio", "Cantidad"],
            )
            .properties(height=240)
            .configure_view(strokeWidth=0, fill="#071A52")
            .configure_axis(labelColor="#AFC2EB", titleColor="#AFC2EB", gridColor="rgba(180,210,255,0.10)")
            .configure(background="#071A52")
        )
        st.altair_chart(chart, width="stretch")
    else:
        st.info("Sin actividad registrada hoy.")

    st.html(
        calendario_html(
            df,
            dias=35,
            tim_uri=tim_peek_uri,
        )
    )

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
        st.markdown('<p style="color:#9AF06B;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;margin-bottom:4px">Flexiones</p>', unsafe_allow_html=True)
        tim_bar_chart(fc, "#9AF06B", height=180)
    
    if not pc.empty:
        st.markdown('<p style="color:#62C5FF;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;margin:8px 0 4px">Plancha</p>', unsafe_allow_html=True)
        tim_bar_chart(pc, "#62C5FF", height=180)
        
    if not sc.empty:
        st.markdown('<p style="color:#48E8D1;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;margin:8px 0 4px">Sentadillas</p>', unsafe_allow_html=True)
        tim_bar_chart(sc, "#48E8D1", height=180)

    if not ec.empty:
        st.markdown('<p style="color:#FFD15C;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;margin:8px 0 4px">Estocadas</p>', unsafe_allow_html=True)
        tim_bar_chart(ec, "#FFD15C", height=180)

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