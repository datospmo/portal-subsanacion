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
ID_EQUIPOS = "1v5JLJcBzJZWfvjh9HQGm7QeD2lJSD66MVeCjfuqWxZ8" 

# Estas son las URLs directas para leer cada pestaña sin usar conectores pesados
URL_USUARIOS = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/gviz/tq?tqx=out:csv&sheet=usuarios"
URL_PENDIENTES = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/gviz/tq?tqx=out:csv&sheet=subsanarequipo"
URL_PAGOS = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/gviz/tq?tqx=out:csv&sheet=pagos"
URL_EQUIPOS = f"https://docs.google.com/spreadsheets/d/{ID_EQUIPOS}/gviz/tq?tqx=out:csv&sheet=PRODUCTOSVISITAS"

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
# Tu código actual mejorado
estilo_custom = """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Oculta el menú lateral de navegación */
        [data-testid="stSidebarNav"] {display: none;}
        
        /* Botones al 100% de ancho */
        .stButton button {
            width: 100%;
        }

        /* OPCIONAL: Quitar el espacio en blanco que queda arriba al ocultar el header */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
        }
    </style>
"""
st.markdown(estilo_custom, unsafe_allow_html=True)

# --- SISTEMA DE LOGIN (MEJORADO) ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'rol' not in st.session_state:
    st.session_state.rol = "GESTOR"

if not st.session_state.autenticado:
    st.title("🔐 Acceso al Sistema")
    try:
        df_usuarios = cargar_datos(URL_USUARIOS)
        if not df_usuarios.empty:
            # Limpieza de espacios en la base de datos de usuarios
            df_usuarios['Nombre'] = df_usuarios['Nombre'].astype(str).str.strip()
            df_usuarios['Password'] = df_usuarios['Password'].astype(str).str.strip()

            # Llaves únicas para cada elemento del formulario
            nombre = st.selectbox("Seleccione su nombre:", [""] + df_usuarios['Nombre'].tolist(), key="login_user_unique")
            password = st.text_input("Contraseña:", type="password", key="login_pass_unique").strip()
            
            # Llave única para el botón de entrar
            if st.button("Entrar", key="btn_entrar_unique"):
                user_row = df_usuarios[(df_usuarios['Nombre'] == nombre) & (df_usuarios['Password'] == password)]
                if not user_row.empty:
                    st.session_state.autenticado = True
                    st.session_state.usuario = nombre
                    # Lógica de Roles
                    if password == "987":
                        st.session_state.rol = "987"
                    else:
                        st.session_state.rol = "GESTOR"
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
    except Exception as e:
        st.error(f"Error en Login: {e}")

else:
   # --- 4. APP PRINCIPAL ---
    import pandas as pd

    st.sidebar.title("Menú")
    st.sidebar.write(f"👤 **Usuario:** {st.session_state.usuario}")
    st.sidebar.write(f"🔑 **Rol:** {st.session_state.rol}")
    
    if st.sidebar.button("Cerrar Sesión", key="btn_cerrar_sesion"):
        st.session_state.autenticado = False
        st.rerun()

    st.title(f"👋 Panel de Consultas: {st.session_state.usuario}")
    
    # Limpieza básica y rápida del usuario actual
    usuario_actual = str(st.session_state.usuario).strip().upper()
    
    try:
        # Cargar bases de datos
        df_p = cargar_datos(URL_PENDIENTES)
        df_equipo = cargar_datos(URL_EQUIPOS)
        df_pagos_all = cargar_datos(URL_PAGOS)
        
        mis_gestores = []
        
        # --- DEFINIR LISTA DE GESTORES SEGÚN ROL ---
        if str(st.session_state.rol) == "987":
            # Extraer columnas A (0) Coordinadora y B (1) Gestor de la matriz de equipos
            coordinadoras_eq = df_equipo.iloc[:, 0].astype(str).str.strip().str.upper()
            gestores_eq = df_equipo.iloc[:, 1].astype(str).str.strip().str.upper()
            
            # Lista de gestores exactos para esta coordinadora
            mis_gestores = gestores_eq[coordinadoras_eq == usuario_actual].unique().tolist()
            
            # Se auto-agrega por si tiene registros a su propio nombre
            if usuario_actual not in mis_gestores:
                mis_gestores.append(usuario_actual)
                
            
        else:
            # Si es Gestor, su lista es solo él mismo
            mis_gestores = [usuario_actual]

        # ==========================================
        # --- TABLA 1: PENDIENTES ---
        # ==========================================
        if not df_p.empty:
            # Aprovechamos tu nueva estructura: Col A (0) Coordinadora, Col B (1) Gestor
            df_p['Coord_Limpia'] = df_p.iloc[:, 0].astype(str).str.strip().str.upper()
            df_p['Gestor_Limpio'] = df_p.iloc[:, 1].astype(str).str.strip().str.upper()
            
            # Capturamos el nombre real de la columna B por si acaso no se llama exactamente "Gestor"
            nombre_col_gestor = df_p.columns[1]

            if str(st.session_state.rol) == "987":
                # Si es coordinadora, traemos TODO lo que tenga su nombre en la Columna A
                mis_pendientes = df_p[df_p['Coord_Limpia'] == usuario_actual].copy()
            else:
                # Si es gestor, traemos TODO lo que tenga su nombre en la Columna B
                mis_pendientes = df_p[df_p['Gestor_Limpio'] == usuario_actual].copy()
            
            if not mis_pendientes.empty:
                if 'Observaciones Gestor' not in mis_pendientes.columns:
                    mis_pendientes['Observaciones Gestor'] = ""
                mis_pendientes['Subsanado'] = False 

                st.subheader("📋 Documentos con observaciones")
                st.info(f"📊 {len(mis_pendientes)} registros con observaciones.")
                
                # Armamos las columnas dinámicamente para evitar errores si les cambiaste el nombre
                columnas_base = ["Cod", "Doc_NUI", "Institución", "Actividad", "Documento", "Observación MSC"]
                columnas_existentes = [c for c in columnas_base if c in mis_pendientes.columns]
                columnas_vista = [nombre_col_gestor] + columnas_existentes + ["Observaciones Gestor", "Subsanado"]
                
                config_columnas = {
                    nombre_col_gestor: st.column_config.Column("Gestor Responsable", disabled=True),
                    "Cod": st.column_config.Column(disabled=True),
                    "Institución": st.column_config.Column(disabled=True),
                    "Actividad": st.column_config.Column(disabled=True),
                    "Doc_NUI": st.column_config.Column(disabled=True),
                    "Documento": st.column_config.Column(disabled=True),
                    "Observación MSC": st.column_config.Column(disabled=True),
                    "Subsanado": st.column_config.CheckboxColumn("¿Listo?", default=False)
                }

                edited_df = st.data_editor(
                    mis_pendientes[columnas_vista],
                    column_config=config_columnas,
                    hide_index=True,
                    use_container_width=True,
                    key="editor_pendientes"
                )

                if st.button("💾 Procesar Selección", use_container_width=True, key="btn_procesar"):
                    seleccionados = edited_df[edited_df['Subsanado'] == True].copy()
                    if not seleccionados.empty:
                        @st.dialog("Confirmar Registro")
                        def confirmar_ventana(datos):
                            st.write("### Resumen de cambios")
                            st.table(datos[["Documento", "Observaciones Gestor"]])
                            if st.button("✅ Confirmar y Guardar", key="btn_confirmar"):
                                try:
                                    with st.spinner("Guardando..."):
                                        import gspread
                                        from google.oauth2.service_account import Credentials
                                        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
                                        secretos_gs = st.secrets["connections"]["gsheets"]
                                        creds = Credentials.from_service_account_info(secretos_gs, scopes=scopes)
                                        client = gspread.authorize(creds)
                                        sh = client.open_by_key(secretos_gs["spreadsheet"])
                                        try:
                                            ws = sh.worksheet("subsanado")
                                        except:
                                            ws = sh.add_worksheet(title="subsanado", rows="100", cols="20")

                                        from datetime import datetime
                                        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        filas_a_enviar = []
                                        for _, fila in datos.iterrows():
                                            nueva_fila = [
                                                fila.get('Institución', ''),
                                                fila.get('Doc_NUI', ''),
                                                fila.get('Observación MSC', ''),
                                                fila.get('Observaciones Gestor', ''),
                                                fila.get('Cod', ''),
                                                ahora,
                                                st.session_state.usuario,
                                                "Subsanado"
                                            ]
                                            filas_a_enviar.append(nueva_fila)

                                        if not ws.get_all_values():
                                            encabezados = ["Institución", "NUI_Doc", "Observación MSC", "Observaciones Gestor", "Cod", "Fecha Registro", "Registrado_Por", "Estado"]
                                            ws.append_row(encabezados)
                                        
                                        ws.append_rows(filas_a_enviar)
                                    st.success("🎉 ¡Datos registrados!")
                                    st.balloons()
                                    import time
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error al grabar: {e}")
                        confirmar_ventana(seleccionados)
                    else:
                        st.warning("⚠️ Selecciona al menos una casilla.")
            else:
                st.success("🎉 No hay documentos por subsanar en este momento.")

# ==========================================
        # --- SEGUNDA TABLA: PAGOS ---
        # ==========================================
        if not df_pagos_all.empty:
            st.divider()
            st.subheader("💰 Estado de validación y pago")

            # 1. Normalización de datos para filtrado
            df_pagos_all['Coord_Limpia'] = df_pagos_all.iloc[:, 0].astype(str).str.strip().str.upper()
            df_pagos_all['Gestor_Limpio'] = df_pagos_all.iloc[:, 1].astype(str).str.strip().str.upper()

            # 2. Filtrado inicial por Rol (Creamos df_pagos_user)
            if str(st.session_state.rol) == "987":
                df_pagos_user = df_pagos_all[df_pagos_all['Coord_Limpia'] == usuario_actual].copy()
            else:
                df_pagos_user = df_pagos_all[df_pagos_all['Gestor_Limpio'] == usuario_actual].copy()

            if not df_pagos_user.empty:
                # --- BLOQUE DE MÉTRICAS (Primero) ---
                col_estado_doc = "Estado Documento"
                col_estado_pago = "Estado Pago"

                if col_estado_doc in df_pagos_user.columns and col_estado_pago in df_pagos_user.columns:
                    status_doc = df_pagos_user[col_estado_doc].astype(str).str.strip().str.upper()
                    status_pago = df_pagos_user[col_estado_pago].astype(str).str.strip().str.upper()

                    total_reg = len(df_pagos_user)
                    docs_si = status_doc.isin(['SI', 'SÍ']).sum()
                    docs_no = status_doc.isin(['NO']).sum()
                    docs_rev = total_reg - docs_si - docs_no

                    pagos_por_cobrar = status_pago.isin(['POR COBRAR']).sum()
                    pagos_en_revision = status_pago.isin(['REVISIÓN', 'EN REVISIÓN']).sum()
                    pagos_hechos = status_pago.isin(['PAGADO', 'PAGADOS']).sum()

                    st.markdown(f"**Resumen de registros:** {total_reg}")
                    st.write("📄 **Validación de Documentos:**")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Aprobados (SÍ)", docs_si)
                    m2.metric("No Validados (NO)", docs_no)
                    m3.metric("En Revisión", docs_rev)

                    st.write("💳 **Estatus de Pagos:**")
                    m4, m5, m6 = st.columns(3)
                    m4.metric("Por Cobrar", pagos_por_cobrar)
                    m5.metric("Revisión", pagos_en_revision)
                    m6.metric("Pagados", pagos_hechos)
                    st.divider()

                # --- FILTRO DE BÚSQUEDA (Después de métricas, antes de la tabla) ---
                busqueda_t2 = st.text_input("🔍 Filtrar resultados de la tabla inferior:", key="search_t2")
                
                if busqueda_t2:
                    mask = df_pagos_user.apply(lambda row: row.astype(str).str.contains(busqueda_t2, case=False).any(), axis=1)
                    df_pagos_user_display = df_pagos_user[mask]
                else:
                    df_pagos_user_display = df_pagos_user

                # --- RENDERIZADO DE LA TABLA ---
                columnas_mostrar = ["Profesional", "Producto", "IE", "Fecha Registro", "Estado Documento", "Estado Pago"]
                if str(st.session_state.rol) == "987":
                    nombre_real_gestor = df_pagos_all.columns[1]
                    if nombre_real_gestor not in columnas_mostrar:
                        columnas_mostrar.insert(0, nombre_real_gestor)

                cols_finales = [c for c in columnas_mostrar if c in df_pagos_user_display.columns]
                
                st.dataframe(
                    df_pagos_user_display[cols_finales],
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("No se encontraron registros de pagos.")



# ==========================================
        # --- TABLA 3: MATRIZ DE SEGUIMIENTO ---
        # ==========================================
        if not df_equipo.empty:
            st.divider()
            st.subheader("📊 Resumen de Avance por Visita")
            
            # --- PARCHE DE DISEÑO CSS ---
            st.markdown("""
                <style>
                    table th:nth-child(1), table td:nth-child(1),
                    table th:nth-child(2), table td:nth-child(2) {
                        white-space: nowrap !important;
                        min-width: 150px !important;
                        text-align: left !important;
                    }
                    table { font-size: 12px !important; }
                </style>
            """, unsafe_allow_html=True)

            df_m = df_equipo.copy()
            df_m.columns = [str(c).strip() for c in df_m.columns]

            col_coordinadora = 'COOR'
            col_gestor = 'RESPONSABLE' 

            if col_coordinadora in df_m.columns and col_gestor in df_m.columns:
                df_m['__COORD_LIMPIA'] = df_m[col_coordinadora].astype(str).str.strip().str.upper()
                df_m['__GESTOR_LIMPIA'] = df_m[col_gestor].astype(str).str.strip().str.upper()
                
                if str(st.session_state.rol) == "987":
                    df_resumen = df_m[df_m['__COORD_LIMPIA'] == usuario_actual].copy()
                else:
                    df_resumen = df_m[df_m['__GESTOR_LIMPIA'] == usuario_actual].copy()

                if not df_resumen.empty:
                    # --- BLOQUE DE FILTRO (Ubicado en la parte superior de la tabla) ---
                    busqueda_t3 = st.text_input("🔍 Buscar en Matriz (Responsable, Código IE...):", key="search_t3")
                    
                    if busqueda_t3:
                        # Filtramos los datos base antes de pivotar
                        mask = df_resumen.apply(lambda row: row.astype(str).str.contains(busqueda_t3, case=False).any(), axis=1)
                        df_resumen = df_resumen[mask]

                    # Solo procedemos si el filtro no dejó la tabla vacía
                    if not df_resumen.empty:
                        try:
                            # Ajuste de nombre de columna IE por si tiene espacios
                            col_id_sede = 'COD_IE' if 'COD_IE' in df_resumen.columns else 'COD_IE'
                            col_conteo = df_resumen.columns[0] 

                            # Creamos la matriz dinámica con los datos (posiblemente filtrados)
                            matriz_pivote = pd.pivot_table(
                                df_resumen, 
                                values=col_conteo, 
                                index=[col_gestor, col_id_sede], 
                                columns=['N_VISIT', 'CODACT', 'DOC'], 
                                aggfunc='count',
                                fill_value=0
                            )

                            matriz_pivote['Total'] = matriz_pivote.sum(axis=1)
                            matriz_pivote.columns = [' / '.join(map(str, col)) for col in matriz_pivote.columns]
                            
                            st.table(matriz_pivote)
                            
                        except Exception as e_pivote:
                            st.error(f"Error al estructurar la matriz: {e_pivote}")
                    else:
                        st.info("No hay coincidencias para la búsqueda realizada.")
                else:
                    st.warning("No hay datos para mostrar.")

    except Exception as e:
        st.error(f"Error general en la aplicación: {e}")


    except Exception as e:

        st.error(f"Error general en la aplicación: {e}")
