import streamlit as st
import pandas as pd
import os

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SISTEMA DE SEGUIMIENTO DE ACTIVIDADES DEL NIÑO", layout="wide")

# Nombre del archivo que se guardará permanentemente en el servidor
DB_PROYECTO = "Padron_Seguimiento_Final.xlsx"

# --- ESTILOS CSS (Tu diseño original) ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    [data-testid="stSidebar"] { background-color: #f0f2f6; border-right: 1px solid #ddd; }
    
    .red-moquegua-text {
        font-size: 12px;
        font-weight: bold;
        color: #555;
        margin-bottom: -10px;
        text-transform: uppercase;
    }

    .footer {
        position: fixed;
        left: 0; bottom: 0; width: 100%;
        background-color: #f8f9fa;
        color: #777; text-align: center;
        padding: 10px; font-size: 12px;
        border-top: 1px solid #ddd;
        z-index: 100;
    }

    [data-testid="stTable"] td, [data-testid="stTable"] th {
        color: #000000 !important;
        background-color: #ffffff !important;
        font-size: 13px !important;
    }
    
    .etapa-header {
        background-color: #007bff;
        color: white !important;
        padding: 8px; text-align: center;
        font-weight: bold; border-radius: 5px 5px 0 0;
    }

    .sidebar-title {
        font-weight: bold; color: #555;
        font-size: 13px; margin-top: 15px;
        text-transform: uppercase;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. SISTEMA DE LOGIN
if "password_correct" not in st.session_state:
    st.title("🛡️ Acceso al Sistema")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("INGRESAR"):
        usuarios = {"admin": "moquegua2026", "visitante": "salud123"}
        if u in usuarios and p == usuarios[u]:
            st.session_state["password_correct"] = True
            st.session_state["rol"] = u
            st.rerun()
    st.stop()

# 3. FUNCIONES DE LIMPIEZA Y FECHAS
def limpiar_y_formatear(df):
    df.columns = [str(c).upper().strip() for c in df.columns]
    for c in df.columns:
        # Formatear IDs para evitar el ".0"
        if any(k in c for k in ['DNI', 'CNV', 'CUI']):
            df[c] = df[c].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        
        # Formatear fechas de forma legible
        if pd.api.types.is_datetime64_any_dtype(df[c]) or any(k in c for k in ['FECHA', 'FEC', 'NACIMIENTO']):
            df[c] = pd.to_datetime(df[c], errors='coerce').dt.strftime('%d/%m/%Y')
    return df.fillna("")

# 4. SIDEBAR: GESTIÓN DE ARCHIVOS (Aquí integramos la persistencia)
st.sidebar.markdown('<div class="sidebar-title">📁 CONFIGURACIÓN</div>', unsafe_allow_html=True)

if st.session_state["rol"] == "admin":
    subida = st.sidebar.file_uploader("Actualizar Padrón (REEMPLAZO TOTAL)", type=["xlsx"])
    if subida:
        # ELIMINACIÓN FÍSICA: Borra el archivo viejo del servidor para evitar duplicados
        if os.path.exists(DB_PROYECTO):
            os.remove(DB_PROYECTO)
            
        # ESCRITURA BINARIA: Guarda el archivo de tu PC permanentemente en el host
        with open(DB_PROYECTO, "wb") as f:
            f.write(subida.getbuffer())
        
        # LIMPIEZA DE CACHÉ: Borra la memoria temporal para que el cambio sea instantáneo
        st.cache_data.clear()
        st.cache_resource.clear()
        
        st.sidebar.success("✅ Base de datos reemplazada con éxito")
        st.rerun()

# Control de seguridad: Si no hay archivo, detener la ejecución
if not os.path.exists(DB_PROYECTO):
    st.warning("⚠️ No hay base de datos cargada. Inicie como admin y suba el archivo Excel.")
    st.stop()

# 5. CARGA DE DATOS Y FILTROS
xl = pd.ExcelFile(DB_PROYECTO)
hojas = xl.sheet_names

st.sidebar.markdown('<div class="sidebar-title">📂 MENÚ DE GESTIÓN</div>', unsafe_allow_html=True)
etapa_sel = st.sidebar.selectbox("👶 1. Edad del Niño:", hojas)
df_actual = limpiar_y_formatear(pd.read_excel(DB_PROYECTO, sheet_name=etapa_sel))

# Filtros por Distrito y Establecimiento
dist_col, eess_col = "NOMBRE_DISTRITO", "NOM_EESS"
distritos = ["TODOS"] + sorted(df_actual[dist_col].unique().tolist()) if dist_col in df_actual.columns else ["TODOS"]
dist_sel = st.sidebar.selectbox("📍 2. Distrito:", distritos)

df_filtrado = df_actual.copy()
if dist_sel != "TODOS":
    df_filtrado = df_filtrado[df_filtrado[dist_col] == dist_sel]

establecimientos = ["TODOS"] + sorted(df_filtrado[eess_col].unique().tolist()) if eess_col in df_filtrado.columns else ["TODOS"]
eess_sel = st.sidebar.selectbox("🏥 3. Establecimiento:", establecimientos)

if eess_sel != "TODOS":
    df_filtrado = df_filtrado[df_filtrado[eess_col] == eess_sel]

st.sidebar.markdown("---")
busqueda = st.sidebar.text_input("✨ BÚSQUEDA DE NIÑO (DNI/APELLIDOS)", placeholder="Escriba aquí...").strip().upper()

# 6. CUERPO PRINCIPAL
st.markdown('<p class="red-moquegua-text">RED MOQUEGUA</p>', unsafe_allow_html=True)
st.title("SISTEMA DE SEGUIMIENTO DE ACTIVIDADES DEL NIÑO")

# Motor de Búsqueda Dinámico (Muestra todas las columnas nuevas automáticamente)
if busqueda:
    st.subheader(f"🧒 Historial Encontrado: {busqueda}")
    historial = []
    for h in hojas:
        df_h = limpiar_y_formatear(pd.read_excel(DB_PROYECTO, sheet_name=h))
        # Busca coincidencia en toda la fila
        match = df_h[df_h.apply(lambda r: busqueda in str(r.values).upper(), axis=1)]
        for _, fila in match.iterrows():
            f = fila.copy()
            f['ETAPA_REF'] = h
            historial.append(f)
    
    if historial:
        cols = st.columns(len(historial))
        for i, reg in enumerate(historial):
            with cols[i]:
                st.markdown(f'<div class="etapa-header">{reg["ETAPA_REF"]}</div>', unsafe_allow_html=True)
                # Al usar to_frame, se adaptará a cualquier columna nueva que hayas puesto en el Excel
                st.table(reg.drop('ETAPA_REF').to_frame(name="Información"))
    else:
        st.error("No se encontraron registros con esos datos.")

# 7. VISUALIZACIÓN GENERAL
st.markdown("---")
st.subheader(f"📋 Padrón Nominal: {etapa_sel}")
st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

st.markdown('<div class="footer">PADRON NOMINAL - HISMINSA MOQUEGUA</div>', unsafe_allow_html=True)

# Cierre de sesión
if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state.clear()
    st.rerun()
