import streamlit as st
import pandas as pd

# 1. Configuración de pantalla completa
st.set_page_config(page_title="Historial de Recorrido Moquegua", layout="wide")

# --- CSS PARA VISTA COMPACTA Y ESTILO ---
st.markdown("""
    <style>
    .stTable td, .stTable th { padding: 1px 4px !important; font-size: 10.5px !important; line-height: 1.0 !important; }
    .block-container { padding-top: 0.5rem !important; }
    .busqueda-resaltada {
        background-color: #e8f0fe;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #1a73e8;
        margin-bottom: 20px;
    }
    .etapa-label {
        background-color: #1a73e8;
        color: white;
        padding: 5px;
        border-radius: 5px;
        text-align: center;
        font-weight: bold;
        margin-bottom: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 Paquete Integral: Historial de Recorrido")

# --- 1. INTEGRACIÓN DEL CARGADOR DE ARCHIVO ---
st.sidebar.header("📁 CONFIGURACIÓN")
archivo_subido = st.sidebar.file_uploader("Subir Padron_Seguimiento (Excel)", type=["xlsx"])

if archivo_subido is None:
    st.info("👈 Por favor, sube tu archivo Excel en el menú lateral para activar el sistema.")
    st.stop()

# Si hay archivo, continuamos
archivo_excel = archivo_subido

# --- FUNCIONES DE APOYO ---
def super_limpieza(df):
    """Estandariza columnas y formato de fechas"""
    df.columns = [str(c).upper().strip() for c in df.columns]
    col_dni = next((c for c in df.columns if 'DNI' in c or 'DOCUMENTO' in c), None)
    if col_dni:
        df[col_dni] = df[col_dni].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        df = df.rename(columns={col_dni: 'DNI_BUSQUEDA'})
    
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime('%d/%m/%Y')
        elif 'FECHA' in col or 'FEC' in col:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%d/%m/%Y')
    return df

def priorizar(nombre):
    orden_etapas = ["PREMATUR", "RN NORMAL", "MENOR DE 1", "1 AÑO", "2 AÑO", "3 AÑO", "4 AÑO"]
    nombre_up = str(nombre).upper()
    for i, p in enumerate(orden_etapas):
        if p in nombre_up: return i
    return 99

# --- LÓGICA DE PROCESAMIENTO ---
try:
    xl = pd.ExcelFile(archivo_excel)
    etapas_ordenadas = sorted(xl.sheet_names, key=priorizar)

    # --- SIDEBAR: FILTROS ---
    st.sidebar.divider()
    st.sidebar.header("📂 MENÚ DE GESTIÓN")
    edad_sel = st.sidebar.selectbox("👶 1. Edad del Niño:", etapas_ordenadas)
    
    # Cargar hoja actual
    df_etapa_actual = pd.read_excel(archivo_excel, sheet_name=edad_sel)
    df_etapa_actual = super_limpieza(df_etapa_actual)

    # Filtros dinámicos
    col_dist = next((c for c in df_etapa_actual.columns if 'DISTRITO' in c), "DISTRITO")
    distritos = ["TODOS"] + sorted(df_etapa_actual[col_dist].dropna().unique().tolist())
    dist_sel = st.sidebar.selectbox("📍 2. Distrito:", distritos)
    
    col_eess = next((c for c in df_etapa_actual.columns if 'EESS' in c or 'ESTABLECIMIENTO' in c), "NOM_EESS")
    eess_list = ["TODOS"] + sorted(df_etapa_actual[col_eess].dropna().unique().tolist())
    eess_sel = st.sidebar.selectbox("🏥 3. Establecimiento:", eess_list)

    # Búsqueda de niño
    st.sidebar.divider()
    st.sidebar.markdown('<div class="busqueda-resaltada"><b>✨ BÚSQUEDA DE NIÑO</b></div>', unsafe_allow_html=True)
    busqueda = st.sidebar.text_input("DNI o Apellidos:", placeholder="Escribe aquí...", label_visibility="collapsed")

    # --- SECCIÓN A: HISTORIAL (Si hay búsqueda) ---
    if busqueda:
        @st.cache_data
        def cargar_todo_historial(_file, sheets):
            lista_dfs = []
            for hoja in sheets:
                df = pd.read_excel(_file, sheet_name=hoja)
                df = super_limpieza(df)
                df['ETAPA_AÑO'] = hoja 
                lista_dfs.append(df)
            return pd.concat(lista_dfs, ignore_index=True)

        df_total = cargar_todo_historial(archivo_excel, xl.sheet_names)
        df_historial = df_total[df_total.apply(lambda r: busqueda.upper() in str(r.values).upper(), axis=1)].copy()
        
        if not df_historial.empty:
            df_historial['ORDEN'] = df_historial['ETAPA_AÑO'].apply(priorizar)
            df_historial = df_historial.sort_values('ORDEN')
            
            st.subheader(f"🧒 Historial Clínico de: {busqueda.upper()}")
            idx_cel = next((i for i, c in enumerate(df_historial.columns) if 'CELULAR' in c or 'TEL' in c), 5)
            
            cols = st.columns(len(df_historial))
            for i, (idx, fila) in enumerate(df_historial.iterrows()):
                with cols[i]:
                    st.markdown(f'<div class="etapa-label">{fila["ETAPA_AÑO"]}</div>', unsafe_allow_html=True)
                    datos = fila.iloc[idx_cel + 1:].drop(['ETAPA_AÑO', 'ORDEN'], errors='ignore').to_frame(name="Información")
                    st.table(datos)
        else:
            st.warning("No se encontró historial para esa búsqueda.")

    # --- SECCIÓN B: PADRÓN NOMINAL (Vista General) ---
    st.divider()
    st.subheader(f"📋 Padrón Nominal: {edad_sel}")
    
    df_final = df_etapa_actual.copy()
    if dist_sel != "TODOS": df_final = df_final[df_final[col_dist] == dist_sel]
    if eess_sel != "TODOS": df_final = df_final[df_final[col_eess] == eess_sel]
    
    st.dataframe(df_final, hide_index=True, use_container_width=True)

except Exception as e:
    st.error(f"Error al procesar el Excel: {e}")
