import streamlit as st
import pandas as pd
import numpy as np
import unicodedata
import os

# Carga de estilos externos (styles.css)
def load_styles():
    css_path = "styles.css"
    if os.path.exists(css_path):
        try:
            with open(css_path, "r", encoding="utf-8") as f:
                st.markdown(f"<style>{{f.read()}}</style>", unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"No se pudo cargar styles.css: {{e}}");
    else:
        st.info("styles.css no encontrado — se usan estilos por defecto.")

# ================= 1. CONFIGURACIÓN (Limpia) =================
st.set_page_config(
    page_title="El Palomo · Formulador",
    page_icon="🍦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Cargar estilos externos (separado)
load_styles()

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
        df.columns = (df.columns
                      .str.strip()
                      .str.upper()
                      .map(lambda x: unicodedata.normalize('NFKD', x)
                           .encode('ascii', 'ignore').decode('utf-8')))
        df = df.rename(columns=GelatoEngine.COL_MAP)
        return df

    @staticmethod
    def calculate_mix(receta_df: pd.DataFrame, db_df: pd.DataFrame):
        if receta_df.empty or db_df is None:
            return {}, 0

        merged = receta_df.merge(db_df, on='INGREDIENTE', how='left').fillna(0)
        total_peso = merged['GRAMOS'].sum()
        if total_peso == 0: return {}, 0

        metrics = {}
        targets = ['GRASA', 'SOLIDOS', 'POD', 'PAC', 'LACTOSA', 'PROTEINA']
        
        for t in targets:
            if t in merged.columns:
                aporte_total = (merged['GRAMOS'] * merged[t] / 100).sum()
                if t in ['POD', 'PAC']:
                    metrics[t] = aporte_total * (1000 / total_peso)
                else:
                    metrics[t] = (aporte_total / total_peso) * 100
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
        except:
            pass
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
            db = GelatoEngine.normalize_cols(pd.read_csv(uploaded))
        else:
            st.stop()
            
    lista_ingredientes = sorted(db['INGREDIENTE'].unique().tolist())

    # --- DIVISIÓN DE PANTALLA ---
    # Usamos un ratio 60% / 40% para dar más aire a los números
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
                    width="large" # Más ancho para leer bien
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
            height=450 # Altura fija cómoda
        )
        
        # Limpieza
        receta_clean = edited_df.dropna(subset=['INGREDIENTE'])
        receta_clean = receta_clean[receta_clean['INGREDIENTE'] != ""]
        receta_clean = receta_clean[receta_clean['GRAMOS'] > 0]

    # === DERECHA: RESULTADOS (Nativos de Streamlit) ===
    with col_results:
        res, peso = GelatoEngine.calculate_mix(receta_clean, db)
        
        # 1. Peso Total (Usando contenedor nativo para borde)
        with st.container(border=True):
            cols_peso = st.columns([3, 1])
            cols_peso[0].markdown("### ⚖️ Peso Total")
            
            delta_color = "normal"
            if 990 <= peso <= 1010: delta_color = "off" # Gris si está bien
            else: delta_color = "inverse" # Rojo/Verde si está mal
            
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
            # Función helper para mostrar métrica con color nativo
            def mostrar_metric(label, key, suffix=""):
                val = res.get(key, 0)
                mn, mx = lims.get(key, (0,0))
                
                # Determinamos el "delta" (flechita y color)
                delta_val = None
                delta_color = "off" # Gris por defecto
                
                if val < mn: 
                    delta_val = f"Bajo ({{mn}}-{{mx}})"
                    delta_color = "inverse" # Rojo
                elif val > mx:
                    delta_val = f"Alto ({{mn}}-{{mx}})"
                    delta_color = "inverse" # Rojo
                else:
                    delta_val = "✅ En rango"
                    delta_color = "normal" # Verde
                
                if "Custom" in tipo: delta_val = None

                st.metric(label, f"{{val:.1f}}{suffix}", delta=delta_val, delta_color=delta_color)

            # Fila 1: POD / PAC (Lo más importante)
            c1, c2 = st.columns(2)
            with c1: mostrar_metric("POD (Dulzor)", "POD")
            with c2: mostrar_metric("PAC (Frío)", "PAC")
            
            # Fila 2: Grasa / Sólidos
            c3, c4 = st.columns(2)
            with c3: mostrar_metric("Grasa", "GRASA", "%")
            with c4: mostrar_metric("Sólidos Tot.", "SOLIDOS", "%")

            # Fila 3: Secundarios (En contenedor gris o transparente)
            with st.expander("Ver detalles (Proteína / Lactosa)", expanded=True):
                c5, c6 = st.columns(2)
                c5.metric("Proteína", f"{{res.get('PROTEINA',0):.1f}}%")
                c6.metric("Lactosa", f"{{res.get('LACTOSA',0):.1f}}%")
                
            # --- CONSEJOS ---
            pac_actual = res.get('PAC', 0)
            if pac_actual < lims['PAC'][0]:
                falta = lims['PAC'][0] - pac_actual
                dex = falta * 1000 / 190
                st.warning(f"🧊 **Falta PAC:** El helado estará duro. Agrega aprox. **{{dex:.0f}}g** de Dextrosa.")

        else:
            st.info("👈 Agrega ingredientes en la tabla para calcular.")

if __name__ == "__main__":
    main()