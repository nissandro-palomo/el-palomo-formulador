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

    receta_demo = {
        "INGREDIENTE": ["Leche", "Azúcar", "Dextrosa", "Crema"],
        "GRAMOS": [600, 120, 40, 80],
        "POD": [0, 100, 75, 0],
        "PAC": [0, 190, 190, 0],
    }

    df = pd.DataFrame(receta_demo)
    print("\n📊 Receta demo")
    print(df)

    pod_total, pac_total = calcular_pod_pac(df)
    print(f"POD total: {pod_total:.1f}")
    print(f"PAC total: {pac_total:.1f}")
    print(recomendacion_pac(pac_total))

    # ================= TESTS =================
    def test_calculo():
        p, a = calcular_pod_pac(df)
        assert p > 0
        assert a > 0

    def test_normalize():
        dft = pd.DataFrame({"Grása ": [1], "POD": [100]})
        out = normalize_cols(dft)
        assert "GRASA" in out.columns

    test_calculo()
    test_normalize()
    print("✔️ Tests OK – Fin modo consola")

else:
    # ================= STREAMLIT APP =================
    st.set_page_config(page_title="El Palomo · Formulador Profesional", layout="wide")
    PASSWORD = "Palomo2026"

    # ================= SEGURIDAD =================
    def check_password():
        def password_entered():
            st.session_state["password_ok"] = st.session_state.get("password") == PASSWORD
            st.session_state.pop("password", None)

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

        tab_db, tab_form, tab_res = st.tabs([
            "📚 Ingredientes",
            "🧪 Formulación",
            "📊 Resultados"
        ])

        # ================= BASE DE INGREDIENTES =================
        with tab_db:
            st.markdown("## 📚 Base de ingredientes")
            uploaded = st.file_uploader("Carga tu CSV de ingredientes", type=["csv"])

            if uploaded:
                db = normalize_cols(pd.read_csv(uploaded))
                st.dataframe(db, use_container_width=True)
            else:
                db = None
                st.warning("Carga un CSV para habilitar la base")

        # ================= FORMULACIÓN =================
        with tab_form:
            st.markdown("## 🍨 Tipo de receta")
            tipo = st.radio("Selecciona el tipo", ["Gelato", "Sorbete"], horizontal=True)

            if tipo == "Gelato":
                objetivo_pac = (220, 260)
                objetivo_pod = (160, 200)
            else:
                objetivo_pac = (260, 320)
                objetivo_pod = (200, 260)

            st.markdown("## 🧪 Construcción de receta")
            num = st.number_input("Cantidad de ingredientes", 1, 15, 4)
            ingredientes = []

            for i in range(int(num)):
                c1, c2, c3, c4 = st.columns([3, 2, 1, 1])

                if db is not None:
                    nombre = c1.selectbox(f"Ingrediente {i+1}", db.iloc[:, 0].unique(), key=f"ing_{i}")
                    fila = db[db.iloc[:, 0] == nombre].iloc[0]
                    pod = float(fila.get("POD", 0))
                    pac = float(fila.get("PAC", 0))
                else:
                    nombre = c1.text_input(f"Ingrediente {i+1}", key=f"ing_{i}")
                    pod = c3.number_input("POD", 0.0, 200.0, 0.0, key=f"pod_{i}")
                    pac = c4.number_input("PAC", 0.0, 300.0, 0.0, key=f"pac_{i}")

                gramos = c2.number_input("Gramos", 0.0, 5000.0, 0.0, key=f"g_{i}")
                c3.markdown(f"**{pod}**")
                c4.markdown(f"**{pac}**")

                if gramos > 0:
                    ingredientes.append({
                        "INGREDIENTE": nombre,
                        "GRAMOS": gramos,
                        "POD": pod,
                        "PAC": pac,
                    })

        # ================= RESULTADOS =================
        with tab_res:
            if ingredientes:
                df = pd.DataFrame(ingredientes)
                pod_total, pac_total = calcular_pod_pac(df)

                st.dataframe(df, use_container_width=True)
                c1, c2 = st.columns(2)
                c1.metric("POD total", f"{pod_total:.1f}")
                c2.metric("PAC total", f"{pac_total:.1f}")

                if not (objetivo_pod[0] <= pod_total <= objetivo_pod[1]):
                    st.warning(f"POD fuera de rango {objetivo_pod}")
                else:
                    st.success("POD correcto")

                if not (objetivo_pac[0] <= pac_total <= objetivo_pac[1]):
                    st.warning(f"PAC fuera de rango {objetivo_pac}")
                    st.info(recomendacion_pac(pac_total, objetivo_pac[0]))
                else:
                    st.success("PAC correcto")
            else:
                st.info("Agrega ingredientes para ver resultados")
