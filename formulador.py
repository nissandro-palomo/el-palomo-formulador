import streamlit as st
import pandas as pd
import unicodedata

# ------------------ SEGURIDAD ------------------
def check_password():
    def password_entered():
        if st.session_state["password"] == "Palomo2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input(
            "🔐 Introduce la clave de El Palomo",
            type="password",
            on_change=password_entered,
            key="password"
        )
        return False

    elif not st.session_state["password_correct"]:
        st.text_input(
            "❌ Clave incorrecta",
            type="password",
            on_change=password_entered,
            key="password"
        )
        st.error("Acceso denegado")
        return False

    return True


# ------------------ APP ------------------
if check_password():

    st.set_page_config(
        page_title="El Palomo - Formulador",
        layout="wide"
    )

    st.title("🍦 El Palomo · Formulador Profesional v1.0")

    # -------- CARGA DE DATOS --------
    @st.cache_data
    def load_db():
        df = pd.read_csv("ingredientes.csv")

        df.columns = (
            df.columns
            .str.strip()
            .str.upper()
            .map(lambda c: unicodedata.normalize("NFKD", c)
                 .encode("ascii", "ignore")
                 .decode("utf-8"))
        )

        return df

    db = load_db()

    st.sidebar.header("🧪 Nueva Receta")
    num_ingredients = st.sidebar.number_input(
        "¿Cuántos ingredientes?",
        min_value=1,
        max_value=15,
        value=5
    )

    st.markdown("### Balance de la Mezcla")

    headers = ["Ingrediente", "Gramos", "Grasa", "Sólidos", "POD", "PAC", "Proteína"]
    cols = st.columns([3, 2, 1, 1, 1, 1, 1])

    for col, h in zip(cols, headers):
        col.write(f"**{h}**")

    recipe = []

    for i in range(num_ingredients):
        c1, c2, c3, c4, c5, c6, c7 = st.columns([3, 2, 1, 1, 1, 1, 1])

        ingredient = c1.selectbox(
            f"Ingrediente {i+1}",
            db.iloc[:, 0].unique(),
            key=f"ing_{i}"
        )

        grams = c2.number_input(
            "g",
            min_value=0,
            max_value=10000,
            value=0,
            key=f"g_{i}"
        )

        if grams > 0:
            row = db[db.iloc[:, 0] == ingredient].iloc[0]

            fat = grams * row.get("PORCENTAJE GRASO", 0) / 1000
            solids = grams * row.get("SOLIDOS TOTALES", 0) / 1000
            pod = grams * row.get("POD", 0) / 1000
            pac = grams * row.get("PAC", 0) / 1000
            protein = grams * row.get("PROTEINA", 0) / 1000

            for c, v in zip(
                [c3, c4, c5, c6, c7],
                [fat, solids, pod, pac, protein]
            ):
                c.write(f"{v:.2f}")

            recipe.append({
                "W": grams,
                "G": fat,
                "S": solids,
                "POD": pod,
                "PAC": pac,
                "P": protein
            })

    if recipe:
        df_r = pd.DataFrame(recipe)
        total_weight = df_r["W"].sum()

        if total_weight > 0:
            st.markdown("---")
            t1, t2, t3, t4 = st.columns(4)

            t1.metric(
                "Grasa Total %",
                f"{df_r['G'].sum() / total_weight * 100:.2f} %"
            )
            t2.metric(
                "Sólidos Totales %",
                f"{df_r['S'].sum() / total_weight * 100:.2f} %"
            )
            t3.metric("POD Total", f"{df_r['POD'].sum():.0f}")
            t4.metric("PAC Total", f"{df_r['PAC'].sum():.0f}")

