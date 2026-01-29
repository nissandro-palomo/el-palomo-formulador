import streamlit as st
import pandas as pd
import numpy as np
import unicodedata
import os

# ================= 1. CONFIGURACIÓN Y ESTILOS =================
st.set_page_config(
    page_title="El Palomo · Formulador Cloud",
    page_icon="🍦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS Optimizado (Tema Cyber/Neón)
st.markdown("""
<style>
:root {
  --primary: #ff4499; /* Rosa Neón */
  --bg-app:  #000000; /* Negro Puro */
  --bg-card: #0a0047; /* Azul Marino Profundo */
  --border:  #004687; /* Azul Rey */
  --text:    #ffffff; /* Blanco */
}

/* Ajuste de Estructura para Móvil y Nube */
.block-container {
    padding-top: 3rem !important;
    padding-bottom: 3rem !important;
    max-width: 98% !important;
}

/* Estilos Globales */
.stApp { background-color: var(--bg-app) !important; color: var(--text) !important; }
h1, h2, h3, p, label, .stMarkdown { color: var(--text) !important; }

/* Tarjetas y Contenedores */
div[data-testid="metric-container"], 
.stDataFrame, 
iframe[title="streamlit.data_editor"],
.css-1r6slb0 {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
}

/* Métricas */
div[data-testid="stMetricValue"] {
    color: var(--primary) !important;
    font-size: 1.4rem !important;
    text-shadow: 0 0 8px rgba(255, 68, 153, 0.4);
}
div[data-testid="stMetricLabel"] { font-size: 0.8rem !important; opacity: 0.8; }

/* Inputs */
.stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
    background-color: var(--bg-card) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
}

/* Botones */
.stButton > button {
    background-color: var(--primary) !important;
    color: white !important;
    border: none !important;
    font-weight: bold !important;
    border-radius: 8px !important;
    width: 100%; /* Botones full width en móvil */
}

/* Alertas */
div[data-testid="stAlert"] {
    background-color: rgba(10, 0, 71, 0.9) !important;
    border: 1px solid var(--primary) !important;
    color: white !important;
    border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)

# ================= 2. MOTOR LÓGICO =================
class GelatoEngine:
    COL_MAP = {
        'INGREDIENTES': 'INGREDIENTE', 'PORCENTAJE GRASO': 'GRASA',
        'SÓLIDOS TOTALES': 'SOLIDOS', 'SOLIDOS TOTALES': 'SOLIDOS',
        'P.O.D': 'POD', 'P.A.C': 'PAC', 'PROTEÍNA': 'PROTEINA'
    }

    @staticmethod
    def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = (df.columns.astype(str).str.strip().str.upper()
                      .map(lambda x: unicodedata.normalize('NFKD', x)
                           .encode('ascii', 'ignore').decode('utf-8')))
        df = df.rename(columns=GelatoEngine.COL_MAP)
        return df

    @staticmethod
    def calculate_mix(receta_df: pd.DataFrame, db_df: pd.DataFrame):
        if receta_df is None or receta_df.empty or db_df is None: return {}, 0
        
        merged = receta_df.merge(db_df, on='INGREDIENTE', how='left').fillna(0)
        total_peso = merged['GRAMOS'].sum()
        if total_peso == 0: return {}, 0

        metrics = {}
        targets = ['GRASA', 'SOLIDOS', 'POD', 'PAC', 'PROTEINA', 'LACTOSA']
        
        for t in targets:
            if t in merged.columns:
                metrics[t] = ((merged['GRAMOS'] * merged[t] / 100).sum() / total_peso) * 100.0
            else:
                metrics[t] = 0.0
        return metrics, total_peso

# ================= 3. CAPA DE DATOS (CON CACHÉ CLOUD) =================
@st.cache_data(ttl=3600) # <--- ¡ESTO ES CRUCIAL PARA LA NUBE! Guarda datos 1 hora
def load_database_cloud():
    # Intenta cargar archivo local primero (para cuando subas el CSV al repo)
    filename = "Ingredientes.csv" 
    if os.path.exists(filename):
        try:
            return GelatoEngine.normalize_cols(pd.read_csv(filename))
        except: pass
    return None

# ================= 4. UI PRINCIPAL =================
def main():
    # --- HEADER ---
    c1, c2 = st.columns([1, 8])
    with c1:
        if os.path.exists("logo.png"): st.image("logo.png", width=60)
        else: st.markdown("## 🍦")
    with c2:
        st.markdown("<h3 style='margin:0; padding-top:10px;'>Formulador Cloud</h3>", unsafe_allow_html=True)

    # --- CARGA DATOS ---
    db = load_database_cloud()
    
    # Si no hay archivo en el repo, pide subirlo (Modo Contingencia)
    if db is None:
        st.warning("☁️ Sube tu base de datos (.csv) para empezar")
        uploaded = st.file_uploader("Arrastra tu archivo aquí", type=['csv'])
        if uploaded: 
            db = GelatoEngine.normalize_cols(pd.read_csv(uploaded))
        else: 
            st.stop()
            
    lista_ingredientes = sorted(db['INGREDIENTE'].dropna().unique().tolist())

    # --- LAYOUT CLOUD ---
    col_editor, col_results = st.columns([1.5, 1], gap="medium")

    # === EDITOR ===
    with col_editor:
        st.caption("📝 Tu Receta")
        if 'receta' not in st.session_state:
            st.session_state.receta = pd.DataFrame({'INGREDIENTE': [None]*8, 'GRAMOS': [0.0]*8})

        edited_df = st.data_editor(
            st.session_state.receta,
            column_config={
                "INGREDIENTE": st.column_config.SelectboxColumn("Ingrediente", options=lista_ingredientes, width="medium"),
                "GRAMOS": st.column_config.NumberColumn("Gramos", min_value=0, max_value=5000, format="%d g")
            },
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True
        )
        receta_clean = edited_df.dropna(subset=['INGREDIENTE'])
        receta_clean = receta_clean[(receta_clean['INGREDIENTE'] != "") & (receta_clean['GRAMOS'] > 0)]

    # === RESULTADOS ===
    with col_results:
        res, peso = GelatoEngine.calculate_mix(receta_clean, db)
        
        # Barra de Peso
        st.caption(f"⚖️ Total: **{peso:.0f}g**")
        st.progress(min(peso/1000, 1.0))
        
        if peso > 0:
            st.write("---")
            # Selector Tipo
            tipo = st.radio("Objetivo", ["Gelato 🥛", "Sorbete 🍧", "Custom ⚙️"], horizontal=True, label_visibility="collapsed")
            
            if "Gelato" in tipo:   lims = {'POD':(17,20), 'PAC':(24,27), 'GRASA':(6,10), 'SOLIDOS':(36,42)}
            elif "Sorbete" in tipo: lims = {'POD':(20,24), 'PAC':(28,32), 'GRASA':(0,0.5), 'SOLIDOS':(28,34)}
            else:                   lims = {'POD':(0,99), 'PAC':(0,99), 'GRASA':(0,100), 'SOLIDOS':(0,100)}

            # Métricas
            c_a, c_b = st.columns(2)
            c_c, c_d = st.columns(2)
            
            def check_rango(val, key):
                if "Custom" in tipo: return "normal"
                mn, mx = lims.get(key, (0,0))
                return "inverse" if (val < mn or val > mx) else "normal"

            c_a.metric("POD", f"{res.get('POD',0):.1f}", delta_color=check_rango(res.get('POD',0), 'POD'))
            c_b.metric("PAC", f"{res.get('PAC',0):.1f}", delta_color=check_rango(res.get('PAC',0), 'PAC'))
            c_c.metric("Grasa", f"{res.get('GRASA',0):.1f}%")
            c_d.metric("Sólidos", f"{res.get('SOLIDOS',0):.1f}%")

            # Consejos PAC
            pac_actual = res.get('PAC', 0)
            if pac_actual < lims['PAC'][0]:
                dex_g = ((lims['PAC'][0] - pac_actual) * 10.0) / 1.73
                st.warning(f"💡 Sube +{dex_g:.0f}g Dextrosa")

            # Tarjeta Temp. Vitrina (Cloud Style)
            factor = -2.0 if "Gelato" in tipo else -2.5
            temp = pac_actual / factor if pac_actual > 0 else 0
            
            st.markdown(f"""
            <div style="margin-top:15px; background:linear-gradient(135deg, #0a0047, #240046); 
                 border:1px solid #ff4499; border-radius:10px; padding:12px; display:flex; justify-content:space-between; align-items:center;">
                <div><span style="color:#fff; font-size:0.8rem;">🌡️ VITRINA</span><br><span style="color:#8feeff; font-size:0.7rem;">Factor {factor}</span></div>
                <div style="color:#ff4499; font-size:1.8rem; font-weight:800;">{temp:.1f}°C</div>
            </div>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
