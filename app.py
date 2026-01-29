"""
El Palomo · Formulador Profesional

App dual:
- Si Streamlit está disponible → interfaz gráfica
- Si NO está disponible → modo consola para pruebas y debug
"""

# ================= PRE-CHECK DE ENTORNO =================
STREAMLIT_AVAILABLE = True
try:
    import streamlit as st
except ModuleNotFoundError:
    STREAMLIT_AVAILABLE = False

import pandas as pd
import unicodedata
import os
from datetime import datetime

# ================= UTILIDADES COMUNES =================
def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = (
        df.columns
        .str.strip()
        .str.upper()
        .map(lambda c: unicodedata.normalize("NFKD", c).encode("ascii", "ignore").decode("utf-8"))
    )
    return df


def calcular_pod_pac(df: pd.DataFrame):
    pod = (df["GRAMOS"] * df["POD"] / 100).sum()
    pac = (df["GRAMOS"] * df["PAC"] / 100).sum()
    return pod, pac


def recomendacion_pac(pac_total, objetivo_min=240):
    if pac_total < objetivo_min:
        delta = objetivo_min - pac_total
        gramos_dextrosa = delta * 1000 / 190
        return f"Para corregir este PAC, agrega ~{gramos_dextrosa:.0f} g de dextrosa"
    return "PAC dentro de rango recomendado"

# ================= MODO CONSOLA =================
if not STREAMLIT_AVAILABLE:
    print("⚠️ Streamlit no está disponible en este entorno")
    print("La app se ejecuta en MODO CONSOLA para pruebas")
    print("Para UI gráfica ejecutar localmente con:\n  streamlit run app.py")

    print("\n--- MODO CONSOLA / DEMOSTRACIÓN ---")

    receta_demo = {
        "INGREDIENTE": ["Leche", "Azúcar", "Dextrosa", "Crema"],
        "GRAMOS": [600, 120, 40, 80],
        "POD": [0, 100, 75, 0],
        "PAC": [0, 190, 190, 0],
    }

    df = pd.DataFrame(receta_demo)

    print("\n📊 Receta demo:")
    print(df.to_string(index=False))

    pod_total, pac_total = calcular_pod_pac(df)

    print(f"\n🔢 POD total: {pod_total:.1f}")
    print(f"❄️ PAC total: {pac_total:.1f}")

    print("\n💡 Recomendación automática:")
    print(recomendacion_pac(pac_total))

    # ================= TESTS =================
    def test_calculo_pod_pac():
        pod, pac = calcular_pod_pac(df)
        assert pod > 0
        assert pac > 0

    def test_normalize_cols():
        dft = pd.DataFrame({"Grása ": [1], "POD": [100]})
        out = normalize_cols(dft)
        assert "GRASA" in out.columns

    test_calculo_pod_pac()
    test_normalize_cols()

    print("\n✔️ Tests ejecutados correctamente")
    raise SystemExit(0)

# ================= STREAMLIT APP =================
st.set_page_config(page_title="El Palomo · Formulador Profesional", layout="wide")
DATA_FILE = "historial_recetas.csv"
PASSWORD = "Palomo2026"

# ================= SEGURIDAD =================
def check_password():
    def password_entered():
        if st.session_state.get("password") == PASSWORD:
            st.session_state["password_ok"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_ok"] = False

    if "password_ok" not in st.session_state:
        st.text_input("🔐 Clave El Palomo", type="password", on_change=password_entered, key="password")
        return False

    if not st.session_state.get("password_ok", False):
        st.error("Acceso denegado")
        return False

    return True

# ================= APP =================
if check_password():
    st.title("🍦 El Palomo · Formulador de Gelato & Sorbete")
    st.info("🧠 Para novatos: POD = dulzor | PAC = control del frío")

    st.success("La app se ha cargado correctamente")
