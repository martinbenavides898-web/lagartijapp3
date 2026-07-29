"""Componentes HTML pequeños que no dependen de la lógica de guardado."""

import math
from datetime import timedelta

import pandas as pd

from app.config import META_FLEXIONES, META_PLANCHA
from app.metrics import fechas_activas, fechas_descanso, pct
from app.time_utils import hoy_chile


def arrow_polygon(cx: float, cy: float, radius: float, progress: float, size: float) -> str:
    if progress <= 0.02:
        return ""
    progress = min(progress, 0.995)
    angle = math.radians(-90 + 360 * progress)
    x = cx + radius * math.cos(angle)
    y = cy + radius * math.sin(angle)
    tangent = angle + math.pi / 2
    tx, ty = math.cos(tangent), math.sin(tangent)
    nx, ny = math.cos(angle), math.sin(angle)
    return (
        f"{x + tx * size * 0.55:.2f},{y + ty * size * 0.55:.2f} "
        f"{x - tx * size * 0.55 + nx * size * 0.38:.2f},"
        f"{y - ty * size * 0.55 + ny * size * 0.38:.2f} "
        f"{x - tx * size * 0.55 - nx * size * 0.38:.2f},"
        f"{y - ty * size * 0.55 - ny * size * 0.38:.2f}"
    )


def rings_html(flexiones: int, plancha: int) -> str:
    outer_r, inner_r = 100, 62
    outer_c, inner_c = 2 * math.pi * outer_r, 2 * math.pi * inner_r
    flex_progress = pct(flexiones, META_FLEXIONES)
    plan_progress = pct(plancha, META_PLANCHA)
    outer_dash, inner_dash = outer_c * flex_progress, inner_c * plan_progress
    outer_arrow = arrow_polygon(130, 130, outer_r, flex_progress, 26)
    inner_arrow = arrow_polygon(130, 130, inner_r, plan_progress, 22)
    outer_arrow_svg = (
        f'<polygon points="{outer_arrow}" fill="#FF2D55" />' if outer_arrow else ""
    )
    inner_arrow_svg = (
        f'<polygon points="{inner_arrow}" fill="#A1FF00" />' if inner_arrow else ""
    )

    return f"""
<div style="height:280px;display:flex;align-items:center;justify-content:center;background:#1C1C1E;overflow:hidden">
<svg viewBox="0 0 260 260" width="260" height="260" xmlns="http://www.w3.org/2000/svg" style="display:block;overflow:visible;background:#1C1C1E">
  <circle cx="130" cy="130" r="{outer_r}" fill="none" stroke="#5C1828" stroke-width="32" />
  <circle cx="130" cy="130" r="{outer_r}" fill="none" stroke="#FF2D55" stroke-width="32" stroke-linecap="round" stroke-dasharray="{outer_dash:.2f} {outer_c:.2f}" transform="rotate(-90 130 130)" />
  {outer_arrow_svg}
  <circle cx="130" cy="130" r="{inner_r}" fill="none" stroke="#3E650A" stroke-width="32" />
  <circle cx="130" cy="130" r="{inner_r}" fill="none" stroke="#A1FF00" stroke-width="32" stroke-linecap="round" stroke-dasharray="{inner_dash:.2f} {inner_c:.2f}" transform="rotate(-90 130 130)" />
  {inner_arrow_svg}
</svg>
</div>
"""


def calendario_html(df: pd.DataFrame, dias: int = 35) -> str:
    activas = fechas_activas(df)
    descansos = fechas_descanso(df)
    inicio = hoy_chile() - timedelta(days=dias - 1)
    hoy = hoy_chile()
    weekdays = ["L", "M", "X", "J", "V", "S", "D"]
    cells = ""

    for offset in range(dias):
        day = inicio + timedelta(days=offset)
        classes = ["cal-cell"]
        if day > hoy:
            classes.append("cal-future")
        if day in descansos:
            classes.append("cal-rest")
        elif day in activas:
            classes.append("cal-done")
        if day == hoy:
            classes.append("cal-today")

        filled = "cal-done" in classes or "cal-rest" in classes
        weekday_color = "rgba(0,0,0,0.55)" if filled else "rgba(255,255,255,0.45)"
        day_color = "#000000" if filled else "#FFFFFF"
        cells += (
            f'<div class="{" ".join(classes)}">'
            f'<div style="font-size:14px;font-weight:800;color:{day_color};line-height:1">{day.day}</div>'
            f'<div style="font-size:9px;font-weight:700;color:{weekday_color};margin-top:3px">{weekdays[day.weekday()]}</div>'
            "</div>"
        )

    return (
        f'<div class="cal-wrap"><div class="cal-grid">{cells}</div>'
        '<div class="cal-legend">'
        '<span><span class="dot dot-lime"></span>Actividad</span>'
        '<span><span class="dot dot-orange"></span>Dia libre</span>'
        '<span><span class="dot dot-gray"></span>Sin registro</span>'
        "</div></div>"
    )


def descargar_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")
