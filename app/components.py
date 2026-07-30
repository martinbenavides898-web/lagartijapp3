"""Componentes visuales de LagartijApp."""

from __future__ import annotations

import base64
import math
from datetime import timedelta
from pathlib import Path

import pandas as pd

from app.config import META_FLEXIONES, META_PLANCHA
from app.metrics import fechas_activas, fechas_descanso, pct
from app.time_utils import hoy_chile


def image_data_uri(path: Path) -> str:
    """Convierte una imagen local a URI para incrustarla en el encabezado."""
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def arrow_polygon(
    cx: float,
    cy: float,
    radius: float,
    progress: float,
    size: float,
) -> str:
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
    """Devuelve los anillos Tim Energy como SVG sin fondo negro."""
    outer_r, inner_r = 104, 66
    outer_c, inner_c = 2 * math.pi * outer_r, 2 * math.pi * inner_r

    flex_progress = pct(flexiones, META_FLEXIONES)
    plan_progress = pct(plancha, META_PLANCHA)

    outer_dash = outer_c * flex_progress
    inner_dash = inner_c * plan_progress

    outer_arrow = arrow_polygon(140, 140, outer_r, flex_progress, 23)
    inner_arrow = arrow_polygon(140, 140, inner_r, plan_progress, 19)

    outer_arrow_svg = (
        f'<polygon points="{outer_arrow}" fill="#9AF06B" />'
        if outer_arrow
        else ""
    )
    inner_arrow_svg = (
        f'<polygon points="{inner_arrow}" fill="#62C5FF" />'
        if inner_arrow
        else ""
    )

    return f"""
<svg
  class="tim-ring-svg"
  xmlns="http://www.w3.org/2000/svg"
  viewBox="0 0 280 280"
  role="img"
  aria-label="Progreso de flexiones y plancha"
>
  <defs>
    <filter id="greenGlow" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="5" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
    <filter id="blueGlow" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="4" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>

  <circle
    cx="140" cy="140" r="{outer_r}"
    fill="none" stroke="#27523A" stroke-width="30"
  />
  <circle
    cx="140" cy="140" r="{outer_r}"
    fill="none" stroke="#9AF06B" stroke-width="30"
    stroke-linecap="round"
    stroke-dasharray="{outer_dash:.2f} {outer_c:.2f}"
    transform="rotate(-90 140 140)"
    filter="url(#greenGlow)"
  />
  {outer_arrow_svg}

  <circle
    cx="140" cy="140" r="{inner_r}"
    fill="none" stroke="#214A7A" stroke-width="28"
  />
  <circle
    cx="140" cy="140" r="{inner_r}"
    fill="none" stroke="#62C5FF" stroke-width="28"
    stroke-linecap="round"
    stroke-dasharray="{inner_dash:.2f} {inner_c:.2f}"
    transform="rotate(-90 140 140)"
    filter="url(#blueGlow)"
  />
  {inner_arrow_svg}
</svg>
"""


def dashboard_html(
    flexiones: int,
    plancha: int,
    sentadillas: int,
    estocadas: int,
    tim_uri: str,
) -> str:
    """Dashboard diario con Tim integrado en la misma composición."""
    return f"""
<div class="rings-master-card tim-dashboard">
  <div class="tim-ring-panel">
    {rings_html(flexiones, plancha)}

    <div class="tim-ring-integrated">
      <img class="tim-peek-dashboard" src="{tim_uri}" alt="Tim">
      <div class="tim-today-copy">
        <span>HOY</span>
        <strong>{flexiones}</strong>
        <small>FLEXIONES</small>
      </div>
    </div>
  </div>

  <div class="tim-stats-grid">
    <div class="ring-stat tim-stat-flex">
      <div class="ring-stat-label">Flexiones</div>
      <div class="ring-stat-value c-pink">{flexiones}</div>
    </div>

    <div class="ring-stat tim-stat-plan">
      <div class="ring-stat-label">Plancha</div>
      <div class="ring-stat-value c-lime">{plancha}s</div>
    </div>

    <div class="ring-stat tim-stat-sent">
      <div class="ring-stat-label">Sentadillas</div>
      <div class="ring-stat-value c-cyan">{sentadillas}</div>
    </div>

    <div class="ring-stat tim-stat-est">
      <div class="ring-stat-label">Estocadas</div>
      <div class="ring-stat-value c-orange">{estocadas}</div>
    </div>
  </div>
</div>
"""


def calendario_html(
    df: pd.DataFrame,
    dias: int = 35,
    tim_uri: str = "",
) -> str:
    """Calendario con Tim integrado dentro del mismo recuadro."""
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
        weekday_color = (
            "rgba(7,17,35,0.58)"
            if filled
            else "rgba(222,234,255,0.58)"
        )
        day_color = "#071123" if filled else "#F7FAFF"

        cells += (
            f'<div class="{" ".join(classes)}">'
            f'<div class="cal-day" style="color:{day_color}">{day.day}</div>'
            f'<div class="cal-wd" style="color:{weekday_color}">'
            f"{weekdays[day.weekday()]}</div>"
            "</div>"
        )

    return f"""
<div class="calendar-showcase">
  <div class="calendar-tim-zone">
    <div class="calendar-tim-glow"></div>
    <img class="calendar-tim-img" src="{tim_uri}" alt="Tim observando el calendario">
  </div>

  <div class="calendar-main">
    <div class="calendar-header">
      <div>
        <div class="card-label">ÚLTIMOS 35 DÍAS</div>
        <div class="card-title">Calendario</div>
        <div class="card-sub">
          Verde: actividad · Naranjo: día libre · Azul: sin registro
        </div>
      </div>
    </div>

    <div class="cal-wrap">
      <div class="cal-grid">{cells}</div>
      <div class="cal-legend">
        <span><span class="dot dot-lime"></span>Actividad</span>
        <span><span class="dot dot-orange"></span>Día libre</span>
        <span><span class="dot dot-gray"></span>Sin registro</span>
      </div>
    </div>
  </div>
</div>
"""


def descargar_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")
