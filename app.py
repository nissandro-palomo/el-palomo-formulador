import streamlit as st
import pandas as pd
import numpy as np
import unicodedata
import os

# ================= 1. CONFIGURACIÓN (Limpia) =================
st.set_page_config(
    page_title="El Palomo · Formulador",
    page_icon="🍦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    /* 1. Fondo general y textos */
    .stApp {
        background-color: #ffffff;
    }
    h1, h2, h3 {
        color: #2fb692 !important; /* Títulos en Verde Azulado */
    }
    
    /* 2. Métricas y Tarjetas */
    div[data-testid="stMetricValue"] {
        color: #e643aa; /* Números en Rosa Palomo */
        font-weight: 800 !important;
    }
    div[data-testid="metric-container"] {
        background-color: #f0fdf4; /* Fondo muy sutil */
        border-left: 5px solid #2fb692; /* Borde Verde */
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    
    /* 3. Botones y Selectores */
    .stButton > button {
        background-color: #e643aa !important;
        color: white !important;
        border-radius: 8px;
        border: none;
    }
    .stSelectbox label, .stNumberInput label {
        color: #2fb692 !important;
        font-weight: bold;
    }
    
    /* 4. Alertas Personalizadas */
    .stAlert {
        background-color: #afffb8; /* Fondo Menta para avisos */
        color: #1a5c48; /* Texto oscuro para contraste */
    }
    
    /* 5. Ajustes de la Tabla */
    iframe[title="streamlit.data_editor"] {
        border: 1px solid #8feeff !important;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# CSS MÍNIMO (Solo para ajustar espacios, sin tocar colores)
st.markdown("""
    <style>
    /* Reducir espacio superior excesivo */
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    
    /* Ajuste para que las métricas se vean más compactas */
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    </style>
""", unsafe_allow_html=True)

class GelatoEngine:
    """Motor de cálculo aislado."""
    
    COL_MAP = {
        'INGREDIENTES': 'INGREDIENTE',
        'PORCENTAJE GRASO': 'GRASA',
        'SÓLIDOS TOTALES': 'SOLIDOS',
        'SOLIDOS TOTALES': 'SOLIDOS',
        'P.O.D': 'POD',
        'P.A.C': 'PAC',
        'LACTOSA': 'LACTOSA',
        'PROTEÍNA': 'PROTEINA',
        'PROTEINA': 'PROTEINA'
    }

    @staticmethod
    def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = (df.columns
                      .astype(str)
                      .str.strip()
                      .str.upper()
                      .map(lambda x: unicodedata.normalize('NFKD', x)
                           .encode('ascii', 'ignore').decode('utf-8')))
        df = df.rename(columns=GelatoEngine.COL_MAP)
        return df

    @staticmethod
    def calculate_mix(receta_df: pd.DataFrame, db_df: pd.DataFrame):
        if receta_df is None or receta_df.empty or db_df is None:
            return {}, 0

        merged = receta_df.merge(db_df, on='INGREDIENTE', how='left').fillna(0)
        total_peso = merged['GRAMOS'].sum()
        if total_peso == 0:
            return {}, 0

        metrics = {}
        targets = ['GRASA', 'SOLIDOS', 'POD', 'PAC', 'LACTOSA', 'PROTEINA']
        
        for t in targets:
            if t in merged.columns:
                aporte_total = (merged['GRAMOS'] * merged[t] / 100).sum()
                if t in ['POD', 'PAC']:
                    # POD / PAC se expresan en g por litro (escala distinta)
                    metrics[t] = aporte_total * (1000.0 / total_peso)
                else:
                    metrics[t] = (aporte_total / total_peso) * 100.0
            else:
                metrics[t] = 0.0
        
        return metrics, total_peso

# ================= 2. DATA LAYER =================
def load_database():
    filename = "Ingredientes.csv"
    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename)
            return GelatoEngine.normalize_cols(df)
        except Exception as e:
            st.warning(f"Error leyendo {filename}: {e}")
    return None

# ================= 3. APP UI (Visualmente Robusta) =================
def main():
    # --- HEADER ---
    c1, c2 = st.columns([0.5, 9])
    with c1:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=50)
        else:
            st.title("🍦")
    with c2:
        st.subheader("El Palomo · Formulador Profesional")

    # --- CARGA DATOS ---
    db = load_database()
    if db is None:
        st.warning("⚠️ No encuentro 'Ingredientes.csv'")
        uploaded = st.file_uploader("Sube tu archivo", type=['csv'])
        if uploaded:
            try:
                db = GelatoEngine.normalize_cols(pd.read_csv(uploaded))
            except Exception as e:
                st.error(f"No se pudo leer el archivo: {e}")
                st.stop()
        else:
            st.stop()
            
    lista_ingredientes = sorted(db['INGREDIENTE'].dropna().unique().tolist())

    # --- DIVISIÓN DE PANTALLA ---
    col_editor, col_results = st.columns([1.5, 1], gap="large")

    # === IZQUIERDA: EDITOR ===
    with col_editor:
        st.info("📝 **Composición de la Receta**")
        
        if 'receta' not in st.session_state:
            st.session_state.receta = pd.DataFrame(
                {'INGREDIENTE': [None]*8, 'GRAMOS': [0.0]*8}
            )

        edited_df = st.data_editor(
            st.session_state.receta,
            column_config={
                "INGREDIENTE": st.column_config.SelectboxColumn(
                    "Ingrediente",
                    options=lista_ingredientes,
                    required=False,
                    width="large"
                ),
                "GRAMOS": st.column_config.NumberColumn(
                    "Gramos",
                    min_value=0,
                    max_value=10000,
                    step=1,
                    format="%d g"
                )
            },
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            height=450
        )
        
        # Limpieza
        receta_clean = edited_df.dropna(subset=['INGREDIENTE'])
        receta_clean = receta_clean[receta_clean['INGREDIENTE'] != ""]
        receta_clean = receta_clean[receta_clean['GRAMOS'] > 0]

    # === DERECHA: RESULTADOS (Nativos de Streamlit) ===
    with col_results:
        res, peso = GelatoEngine.calculate_mix(receta_clean, db)
        
        # 1. Peso Total
        with st.container():
            cols_peso = st.columns([3, 1])
            cols_peso[0].markdown("### ⚖️ Peso Total")
            cols_peso[1].metric("Gramos", f"{peso:.0f}", delta=None, label_visibility="collapsed")

            if peso > 0 and (peso < 990 or peso > 1010):
                st.caption("⚠️ Ajusta a 1000g para mayor precisión")

        if peso > 0:
            st.write("---")
            # Configuración de Rangos
            tipo = st.radio("Objetivo:", ["Gelato 🥛", "Sorbete 🍧", "Custom ⚙️"], horizontal=True)
            
            if "Gelato" in tipo:
                lims = {'POD':(170,200), 'PAC':(240,270), 'GRASA':(6,10), 'SOLIDOS':(36,42)}
            elif "Sorbete" in tipo:
                lims = {'POD':(200,240), 'PAC':(280,320), 'GRASA':(0,0.5), 'SOLIDOS':(28,34)}
            else:
                lims = {'POD':(0,999), 'PAC':(0,999), 'GRASA':(0,100), 'SOLIDOS':(0,100)}

            # --- VISUALIZACIÓN DE MÉTRICAS ---
            def mostrar_metric(label, key, suffix=""):
                val = res.get(key, 0.0)
                mn, mx = lims.get(key, (0,0))
                
                delta_val = None
                delta_color = "normal"

                if val < mn:
                    delta_val = f"Bajo ({mn}-{mx})"
                    delta_color = "inverse"
                elif val > mx:
                    delta_val = f"Alto ({mn}-{mx})"
                    delta_color = "inverse"
                else:
                    delta_val = "✅ En rango"
                    delta_color = "normal"

                if "Custom" in tipo:
                    delta_val = None

                # Mostrar con un decimal si es porcentaje o valor
                display = f"{val:.1f}{suffix}"
                st.metric(label, display, delta=delta_val, delta_color=delta_color)

            # Fila 1: POD / PAC
            c1, c2 = st.columns(2)
            with c1: mostrar_metric("POD (Dulzor)", "POD")
            with c2: mostrar_metric("PAC (Frío)", "PAC")
            
            # Fila 2: Grasa / Sólidos
            c3, c4 = st.columns(2)
            with c3: mostrar_metric("Grasa", "GRASA", "%")
            with c4: mostrar_metric("Sólidos Tot.", "SOLIDOS", "%")

            # Fila 3: Secundarios
            with st.expander("Ver detalles (Proteína / Lactosa)", expanded=True):
                c5, c6 = st.columns(2)
                c5.metric("Proteína", f"{res.get('PROTEINA',0):.1f}%")
                c6.metric("Lactosa", f"{res.get('LACTOSA',0):.1f}%")
                
            # --- CONSEJOS ---
            pac_actual = res.get('PAC', 0)
            if pac_actual < lims['PAC'][0]:
                falta = lims['PAC'][0] - pac_actual
                dex = falta * 1000.0 / 190.0
                st.warning(f"🧊 **Falta PAC:** El helado estará duro. Agrega aprox. **{dex:.0f}g** de Dextrosa.")

        else:
            st.info("👈 Agrega ingredientes en la tabla para calcular.")

if __name__ == "__main__":
    main()