"""
apps/tareas/analitica.py — Analítica de Registro de Tareas con scikit-learn.

Dos preguntas que el dashboard descriptivo (`services.calcular_resumen`) no responde:

1. **¿Voy a más o a menos?** → `tendencia_semanal`: regresión lineal (`LinearRegression`)
   sobre las horas por semana. Devuelve la pendiente (h/semana), el R² y la proyección
   de la semana siguiente.
2. **¿Qué días se salen de lo normal?** → `dias_atipicos`: `IsolationForest` sobre
   (horas del día, n.º de registros), detrás de un `StandardScaler` en un `Pipeline`.

Decisiones que no se ven leyendo el código:

- **Las semanas sin actividad cuentan como 0** (`serie_semanal` reindexa el rango
  completo). Si se omitieran, una pausa de un mes no movería la tendencia: la regresión
  vería semanas "consecutivas" que no lo son.
- **Mínimos de datos** (`MIN_SEMANAS`, `MIN_DIAS`): por debajo se devuelve `None`/`[]`
  en vez de un modelo ajustado a 2 puntos. Una recta por dos puntos tiene R² = 1 y no
  dice nada; reportarla sería información falsa con apariencia de rigor.
- **`random_state` fijo**: el IsolationForest es aleatorio; sin semilla, la misma base
  daría días atípicos distintos en cada recarga.
- **`contamination=0.05`** (el 5 % más raro), no `"auto"`: medido sobre la base real
  (169 días), `"auto"` marcaba 48 días (28 %) — una lista que nadie revisa no detecta
  nada. La contrapartida es asumida: con una fracción fija SIEMPRE sale algún día, así
  que la pregunta que responde es "¿cuáles son mis días más raros?", no "¿hay algo raro?".
- **`motivo`** lo decide el rasgo más desviado (z-score), no solo las horas: un día de
  horas normales con 9 registros es raro por los registros, y decir "menos horas de lo
  habitual" sería explicar mal lo que el modelo vio.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

MIN_SEMANAS = 4
MIN_DIAS = 10
CONTAMINACION = 0.05

MOTIVOS = {
    ("horas", True): "más horas de lo habitual",
    ("horas", False): "menos horas de lo habitual",
    ("registros", True): "más registros de lo habitual",
    ("registros", False): "menos registros de lo habitual",
}


def serie_semanal(df: pd.DataFrame) -> pd.Series:
    """Horas por semana (índice = lunes), con las semanas vacías del rango a 0."""
    if df.empty:
        return pd.Series(dtype="float64", name="horas")
    lunes = df["fecha"] - pd.to_timedelta(df["fecha"].dt.weekday, unit="D")
    semanal = df.groupby(lunes)["horas"].sum()
    rango = pd.date_range(semanal.index.min(), semanal.index.max(), freq="7D")
    return semanal.reindex(rango, fill_value=0.0).rename_axis("semana").rename("horas")


def tendencia_semanal(df: pd.DataFrame) -> dict | None:
    """Recta de mínimos cuadrados sobre las horas semanales, o `None` si hay pocas semanas.

    `ajuste` trae, por semana, las horas reales y las que predice la recta: el informe
    PDF y la UI dibujan ambas sin volver a ajustar el modelo.
    """
    semanal = serie_semanal(df)
    if len(semanal) < MIN_SEMANAS:
        return None

    x = np.arange(len(semanal)).reshape(-1, 1)
    y = semanal.to_numpy()
    modelo = LinearRegression().fit(x, y)
    pendiente = float(modelo.coef_[0])
    ajuste = (
        semanal.to_frame()
        .assign(ajustada=modelo.predict(x))
        .round(2)
        .reset_index()
        .assign(semana=lambda d: d["semana"].dt.strftime("%Y-%m-%d"))
    )
    return {
        "semanas": len(semanal),
        "pendiente": round(pendiente, 2),
        "r2": round(float(modelo.score(x, y)), 3),
        # Horas no negativas: una tendencia a la baja no proyecta "-2 h".
        "proyeccion": round(max(0.0, float(modelo.predict([[len(semanal)]])[0])), 2),
        "direccion": "sube" if pendiente > 0.05 else "baja" if pendiente < -0.05 else "estable",
        "ajuste": ajuste.to_dict("records"),
    }


def dias_atipicos(df: pd.DataFrame) -> list[dict]:
    """Días con un volumen anómalo de horas/registros según un IsolationForest.

    Cada día es un punto (horas, registros). Se escala antes de aislar: sin el
    `StandardScaler`, las horas (0-15) pesarían distinto que los registros (1-5) solo
    por su unidad. `puntaje` < 0 = atípico; cuanto más negativo, más raro.
    """
    diario = df.groupby("fecha").agg(horas=("horas", "sum"), registros=("horas", "size"))
    if len(diario) < MIN_DIAS:
        return []

    modelo = make_pipeline(
        StandardScaler(),
        IsolationForest(contamination=CONTAMINACION, random_state=0),
    )
    rasgos = diario[["horas", "registros"]]
    # z-score por rasgo: el de mayor |z| explica el día; su signo dice si sobra o falta.
    z = (rasgos - rasgos.mean()) / rasgos.std(ddof=0).replace(0, 1)
    rasgo = z.abs().idxmax(axis=1)
    sobra = z.to_numpy()[np.arange(len(z)), rasgos.columns.get_indexer(rasgo)] > 0
    atipicos = (
        diario.assign(
            etiqueta=modelo.fit_predict(rasgos),
            puntaje=modelo.decision_function(rasgos),
            motivo=[MOTIVOS[clave] for clave in zip(rasgo, sobra, strict=True)],
        )
        .query("etiqueta == -1")
        .sort_values("puntaje")
        .reset_index()
    )
    return (
        atipicos.assign(
            fecha=atipicos["fecha"].dt.strftime("%Y-%m-%d"),
            horas=atipicos["horas"].round(2),
            puntaje=atipicos["puntaje"].round(3),
        )[["fecha", "horas", "registros", "puntaje", "motivo"]]
        .to_dict("records")
    )


def calcular_analitica(df: pd.DataFrame) -> dict:
    """Salida de `tareas/analitica/`: tendencia + atípicos + los mínimos exigidos.

    `requisitos` viaja en la respuesta para que la UI explique POR QUÉ no hay tendencia
    ("faltan semanas") en vez de mostrar un hueco.
    """
    return {
        "tendencia": tendencia_semanal(df),
        "atipicos": dias_atipicos(df),
        "requisitos": {"min_semanas": MIN_SEMANAS, "min_dias": MIN_DIAS},
    }
