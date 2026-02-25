import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection


# 1. Configuración de la conexión
# 'gsheets' debe coincidir exactamente con el nombre en tu archivo secrets.toml
conn = st.connection("gsheets", type=GSheetsConnection)

st.set_page_config(page_title="Portal de Subsanación", layout="wide")

# --- CONFIGURACIÓN DE URL ---
# 1. VE A TU HOJA DE GOOGLE -> COMPARTIR -> CUALQUIER PERSONA CON EL ENLACE (LECTOR)
# 2. COPIA EL ID DE TU HOJA (el código largo entre /d/ y /edit)
ID_HOJA = "167-gjcDIqY_1MxJVZe8UwPnO3d--1ssDbQzPWpATpuw" 

# Estas son las URLs directas para leer cada pestaña sin usar conectores pesados
URL_USUARIOS = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/gviz/tq?tqx=out:csv&sheet=usuarios"
URL_PENDIENTES = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/gviz/tq?tqx=out:csv&sheet=subsanarequipo"


# --- FUNCIONES DE CARGA ---
def cargar_datos(url):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip() # Limpia espacios en encabezados
        return df
    except Exception as e:
        st.error(f"Error al cargar CSV: {e}")
        return pd.DataFrame()


# Inyectar CSS para ocultar el encabezado y el menú de Streamlit
estilo_custom = """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        /* Esto asegura que el botón de cerrar sesión en el sidebar no se oculte */
        [data-testid="stSidebarNav"] {display: none;}
        .stButton button {
            width: 100%;
        }
    </style>
"""
st.markdown(estilo_custom, unsafe_allow_html=True)

# --- SISTEMA DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema")
    try:
        df_usuarios = cargar_datos(URL_USUARIOS)
        if not df_usuarios.empty:
            nombre = st.selectbox("Seleccione su nombre:", [""] + df_usuarios['Nombre'].tolist())
            password = st.text_input("Contraseña:", type="password")
            
            if st.button("Entrar"):
                user_row = df_usuarios[(df_usuarios['Nombre'] == nombre) & (df_usuarios['Password'].astype(str) == password)]
                if not user_row.empty:
                    st.session_state.autenticado = True
                    st.session_state.usuario = nombre
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
    except Exception as e:
        st.error(f"Error en Login: {e}")

else:
    # --- 4. APP PRINCIPAL ---
    st.sidebar.title("Menú")
    st.sidebar.write(f"👤 **Gestor:** {st.session_state.usuario}")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

    st.title(f"👋 Panel de Trabajo: {st.session_state.usuario}")
    
    try:
        # 1. Cargar datos de pendientes (Insumos)
        df_p = cargar_datos(URL_PENDIENTES)
        
        if not df_p.empty and 'Gestor' in df_p.columns:
            mis_pendientes = df_p[df_p['Gestor'] == st.session_state.usuario].copy()
            
            if not mis_pendientes.empty:
                if 'Observaciones Gestor' not in mis_pendientes.columns:
                    mis_pendientes['Observaciones Gestor'] = ""
                mis_pendientes['Subsanado'] = False 

                # Definimos las columnas que queremos ver y capturar
                columnas_vista = ["Cod","Doc_NUI","Institución", "Actividad","Documento", "Observación MSC", "Observaciones Gestor", "Subsanado"]

                st.subheader("📋 Documentos con observaciones")
                st.info(f"📊 Tienes **{len(mis_pendientes)}** documentos con observaciones pendientes de gestionar.")
                
                edited_df = st.data_editor(
                    mis_pendientes[columnas_vista],
                    column_config={
                        "Cod": st.column_config.Column(disabled=True),
                        "Institución": st.column_config.Column(disabled=True),
                        "Fecha Revisión": st.column_config.Column(disabled=True),
                        "Actividad": st.column_config.Column(disabled=True),
                        "Doc_NUI": st.column_config.Column(disabled=True),
                        "Documento": st.column_config.Column(disabled=True),
                        "Observación MSC": st.column_config.Column(disabled=True),
                        "Subsanado": st.column_config.CheckboxColumn("¿Listo?", default=False)
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="editor_v12"
                )

                if st.button("💾 Procesar", use_container_width=True):
                    seleccionados = edited_df[edited_df['Subsanado'] == True].copy()
                    
                    if not seleccionados.empty:
                        
                        @st.dialog("Confirmar Registro")
                        def confirmar_ventana(datos):
                            st.write("### Resumen de cambios")
                            # Mostramos solo NUI/Documento para confirmar
                            st.table(datos[["Documento", "Observaciones Gestor"]])
                            
                            if st.button("✅ Confirmar y Guardar"):
                                try:
                                    with st.spinner("Guardando en la base de datos..."):
                                        import gspread
                                        from google.oauth2.service_account import Credentials

                                        # 1. Autenticación Manual con gspread (Salto de seguridad)
                                        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
                                        # Usamos los datos exactos que ya tienes en secrets.toml
                                        secretos_gs = st.secrets["connections"]["gsheets"]
                                        creds = Credentials.from_service_account_info(secretos_gs, scopes=scopes)
                                        client = gspread.authorize(creds)

                                        # 2. Abrir la hoja por ID
                                        sh = client.open_by_key(secretos_gs["spreadsheet"])
                                        
                                        # Intentar abrir la pestaña 'subsanado'
                                        try:
                                            ws = sh.worksheet("subsanado")
                                        except:
                                            # Si no existe, la crea con los encabezados
                                            ws = sh.add_worksheet(title="subsanado", rows="100", cols="20")

                                        # 3. Preparar los datos mínimos solicitados + otros
                                        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        
                                        # Creamos una lista de filas para enviar
                                        filas_a_enviar = []
                                        for _, fila in datos.iterrows():
                                            nueva_fila = [
                                                fila.get('Institución', ''),
                                                fila.get('Doc_NUI', ''),  # Este sería tu NUI_Doc
                                                fila.get('Observación MSC', ''),
                                                fila.get('Observaciones Gestor', ''),
                                                fila.get('Cod', ''),
                                                ahora,                      # Fecha del registro
                                                st.session_state.usuario,    # Gestor
                                                "Subsanado"                 # Estado
                                            ]
                                            filas_a_enviar.append(nueva_fila)

                                        # 4. Escribir (Si la hoja está vacía, ponemos encabezados primero)
                                        if not ws.get_all_values():
                                            encabezados = ["Institución", "NUI_Doc", "Observación MSC", "Observaciones Gestor", "Fecha Registro", "Gestor", "Estado"]
                                            ws.append_row(encabezados)
                                        
                                        ws.append_rows(filas_a_enviar)

                                    st.success("🎉 ¡Datos registrados correctamente en el archivo!")
                                    st.balloons()
                                    st.rerun()

                                except Exception as e:
                                    st.error(f"Error crítico de grabación: {e}")
                                    st.info("Asegúrate de que 'gspread' esté instalado y el correo de la cuenta de servicio sea EDITOR.")
                        
                        confirmar_ventana(seleccionados)
                    else:
                        st.warning("⚠️ Selecciona al menos una casilla.")
            else:
                st.success("🎉 No tienes documentos por subsanar!")
    except Exception as e:

        st.error(f"Error de visualización: {e}")



