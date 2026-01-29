import streamlit as st
import pandas as pd
import unicodedata
import os
from typing import Optional, Tuple, Dict

# ================= 1. CONFIGURACIÓN =================
st.set_page_config(
    page_title="El Palomo · Formulador",
    page_icon="🍦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

class GelatoEngine:
    """Motor de cálculo y utilidades para normalizar y mezclar ingredientes."""

    COL_MAP = {
        "INGREDIENTES": "INGREDIENTE",
        "PORCENTAJE GRASO": "GRASA",
        "SÓLIDOS TOTALES": "SOLIDOS",
        "SOLIDOS TOTALES": "SOLIDOS",
        "P.O.D": "POD",
        "P.A.C": "PAC",
        "LACTOSA": "LACTOSA",
        "PROTEÍNA": "PROTEINA",
        "PROTEINA": "PROTEINA",
    }

    @staticmethod
    def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
        cols = []
        for c in df.columns:
            if not isinstance(c, str):
                c = str(c)
            c_norm = unicodedata.normalize("NFKD", c.strip()).encode("ascii", "ignore").decode("utf-8").upper()
            cols.append(c_norm)
        df = df.copy()
        df.columns = cols
        rename_map = {k: v for k, v in GelatoEngine.COL_MAP.items() if k in df.columns}
        df = df.rename(columns=rename_map)
        return df

    @staticmethod
    def calculate_mix(receta_df: pd.DataFrame, db_df: pd.DataFrame) -> Tuple[Dict[str, float], float]:
        if receta_df is None or receta_df.empty or db_df is None or db_df.empty:
            return {}, 0.0
        if "INGREDIENTE" not in receta_df.columns or "GRAMOS" not in receta_df.columns:
            return {}, 0.0

        merged = receta_df.merge(db_df, on="INGREDIENTE", how="left")
        for col in ["GRASA", "SOLIDOS", "POD", "PAC", "LACTOSA", "PROTEINA"]:
            if col not in merged.columns:
                merged[col] = 0.0

        merged["GRAMOS"] = pd.to_numeric(merged["GRAMOS"], errors="coerce").fillna(0.0)
        total_peso = float(merged["GRAMOS"].sum())
        if total_peso <= 0:
            return {}, 0.0

        metrics: Dict[str, float] = {}
        targets = ["GRASA", "SOLIDOS", "POD", "PAC", "LACTOSA", "PROTEINA"]

        for t in targets:
            aporte_total = (merged["GRAMOS"] * merged[t] / 100.0).sum()
            if t in ("POD", "PAC"):
                metrics[t] = float(aporte_total * (1000.0 / total_peso))
            else:
                metrics[t] = float((aporte_total / total_peso) * 100.0)

        return metrics, total_peso

def load_database(filename: str = "Ingredientes.csv") -> Optional[pd.DataFrame]:
    if not os.path.exists(filename):
        return None
    try:
        df = pd.read_csv(filename, encoding="utf-8")
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(filename, encoding="latin-1")
        except Exception as e:
            st.error(f"Error leyendo {filename}: {e}")
            return None
    except Exception as e:
        st.error(f"Error leyendo {filename}: {e}")
        return None

    df = GelatoEngine.normalize_cols(df)
    if "INGREDIENTE" not in df.columns:
        st.warning("El CSV cargado no contiene columna 'INGREDIENTE' normalizada.")
    return df

def main():
    c1, c2 = st.columns([0.5, 9])
    with c1:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=50)
        else:
            st.title("🍦")
    with c2:
        st.subheader("El Palomo · Formulador Profesional")

    db = load_database()
    if db is None:
        st.warning("⚠️ No encuentro 'Ingredientes.csv' en el directorio actual.")
        uploaded = st.file_uploader("Sube tu archivo de ingredientes (CSV)", type=["csv"])
        if uploaded:
            try:
                db = GelatoEngine.normalize_cols(pd.read_csv(uploaded))
            except Exception as e:
                st.error(f"Error leyendo el archivo subido: {e}")
                st.stop()
        else:
            st.stop()

    lista_ingredientes = []
    if "INGREDIENTE" in db.columns:
        lista_ingredientes = sorted(db["INGREDIENTE"].dropna().astype(str).unique().tolist())

    col_editor, col_results = st.columns([1.5, 1], gap="large")

    with col_editor:
        st.info("📝 Composición de la Receta")
        if "receta" not in st.session_state:
            st.session_state.receta = pd.DataFrame({"INGREDIENTE": ["" for _ in range(8)], "GRAMOS": [0.0 for _ in range(8)]})

        edited_df = st.data_editor(
            st.session_state.receta,
            column_config={
                "INGREDIENTE": st.column_config.SelectboxColumn("Ingrediente", options=lista_ingredientes, required=False),
                "GRAMOS": st.column_config.NumberColumn("Gramos", min_value=0.0, max_value=100000.0, step=1.0, format="%d g"),
            },
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            height=450,
        )

        st.session_state.receta = edited_df
        receta_clean = (edited_df.dropna(subset=["INGREDIENTE"]).loc[lambda df: df["INGREDIENTE"].astype(str).str.strip() != ""]) 
        receta_clean["GRAMOS"] = pd.to_numeric(receta_clean["GRAMOS"], errors="coerce").fillna(0.0)
        receta_clean = receta_clean[receta_clean["GRAMOS"] > 0].copy()
        if not receta_clean.empty:
            receta_clean = receta_clean.groupby("INGREDIENTE", as_index=False)["GRAMOS"].sum()

    with col_results:
        res, peso = GelatoEngine.calculate_mix(receta_clean, db)
        st.markdown("### ⚖️ Peso Total")
        st.metric("Gramos", f"{peso:.0f} g")

        if peso > 0 and (peso < 990 or peso > 1010):
            st.caption("⚠️ Ajusta a 1000g para mayor precisión")

        if peso <= 0:
            st.info("👈 Agrega ingredientes en la tabla para calcular.")
            return

        st.write("---")
        tipo = st.radio("Objetivo:", ["Gelato 🥛", "Sorbete 🍧", "Custom ⚙️"], horizontal=True)

        if "Gelato" in tipo:
            lims = {"POD": (170, 200), "PAC": (240, 270), "GRASA": (6, 10), "SOLIDOS": (36, 42)}
        elif "Sorbete" in tipo:
            lims = {"POD": (200, 240), "PAC": (280, 320), "GRASA": (0, 0.5), "SOLIDOS": (28, 34)}
        else:
            lims = {"POD": (0, 999), "PAC": (0, 999), "GRASA": (0, 100), "SOLIDOS": (0, 100)}

        def mostrar_metric(label: str, key: str, suffix: str = ""):
            val = res.get(key, 0.0)
            mn, mx = lims.get(key, (0.0, 0.0))
            if "Custom" in tipo:
                delta = None
                delta_color = "normal"
            else:
                if val < mn:
                    delta = f"Bajo ({mn}-{mx})"
                    delta_color = "inverse"
                elif val > mx:
                    delta = f"Alto ({mn}-{mx})"
                    delta_color = "inverse"
                else:
                    delta = "✅ En rango"
                    delta_color = "normal"
            st.metric(label, f"{val:.1f}{suffix}", delta=delta, delta_color=delta_color)

        c1, c2 = st.columns(2)
        with c1:
            mostrar_metric("POD (Dulzor)", "POD")
        with c2:
            mostrar_metric("PAC (Frío)", "PAC")

        c3, c4 = st.columns(2)
        with c3:
            mostrar_metric("Grasa", "GRASA", "%")
        with c4:
            mostrar_metric("Sólidos Tot.", "SOLIDOS", "%")

        with st.expander("Ver detalles (Proteína / Lactosa)", expanded=True):
            c5, c6 = st.columns(2)
            c5.metric("Proteína", f"{res.get('PROTEINA', 0.0):.1f}%")
            c6.metric("Lactosa", f"{res.get('LACTOSA', 0.0):.1f}%")

        pac_actual = res.get("PAC", 0.0)
        if "PAC" in lims and pac_actual < lims["PAC"][0]:
            falta = lims["PAC"][0] - pac_actual
            dex = falta * 1000.0 / 190.0
            st.warning(f"🧊 Falta PAC: agrega aprox. {dex:.0f} g de Dextrosa para mejorar 'coldness'.")

if __name__ == "__main__":
    main()