import streamlit as st
from db import DataManager
from datetime import datetime
db = DataManager()

# --- FRAGMENTO: MIS OKRS (EMPLEADO) ---
@st.fragment
def render_mis_okrs_empleado(db, user_id_actual):
    c1, c2 = st.columns([3, 1])
    anio_actual = datetime.now().year
    c1.subheader(f"🎯 Mis Objetivos Personales - {anio_actual}")
    
    if c2.button("🔄 Actualizar OKRs", key="btn_ref_mis_okrs", use_container_width=True):
        st.cache_data.clear()

    # 1. Carga de datos fresca
    _, okrs_df, _ = db.load_all_data()
    
    # Filtrar OKRs de la organización
    okrs_org = okrs_df[okrs_df["tipo"] == "Organizacion"]
    
    # FILTRO SENIOR: Solo mis OKRs, del tipo Empleado y del AÑO ACTUAL
    okrs_df.columns = okrs_df.columns.str.strip()
    okrs_df['tipo'] = okrs_df['tipo'].astype(str).str.strip()
    okrs_df['año'] = okrs_df['año'].astype(str).str.strip()
    # FILTRO: Ahora sí, comparamos sobre datos limpios
    mis_okrs = okrs_df[
        (okrs_df["tipo"] == "Empleado") & 
        (okrs_df["id_empleado"] == user_id_actual) &
        (okrs_df["año"] == str(anio_actual))
    ]
    # 2. Formulario para Crear OKR Personal
    with st.expander("➕ Crear mi Objetivo Personalsss"):
        if okrs_org.empty:
            st.warning("No hay OKRs corporativos definidos para vincular.")
        else:
            with st.form("nuevo_okr_personal", clear_on_submit=True):
                okr_corp_opciones = {row["nombre"]: row["id"] for _, row in okrs_org.iterrows()}
                okr_corp_seleccionado = st.selectbox("Vincular a Objetivo Empresa", options=okr_corp_opciones.keys())
                
                nombre = st.text_input("Mi Objetivo")
                descripcion = st.text_area("¿Cómo voy a lograrlo?")
                
                # Nuevo dropdown de estado
                estado = st.selectbox("Estado inicial", ["Nuevo", "En curso", "Completo", "Incompleto"])
                
                if st.form_submit_button("Guardar mi OKR", use_container_width=True):
                    if nombre and descripcion:
                        nuevo_okr = {
                            "nombre": nombre,
                            "descripcion": descripcion,
                            "tipo": "Empleado",
                            "id_empleado": user_id_actual,
                            "link_org": okr_corp_opciones[okr_corp_seleccionado],
                            "año": anio_actual, # Guardado automático del año
                            "estado": estado    # Guardado del estado seleccionado
                        }
                        if db.save_okr(nuevo_okr):
                            st.success(f"OKR para el {anio_actual} creado.")
                            st.rerun(scope="fragment")
                    else:
                        st.warning("Completa los campos obligatorios.")

    st.divider()

    # 3. Listado de mis OKRs del año actual
    if mis_okrs.empty:
        st.info(f"Aún no tienes objetivos personales registrados para el {anio_actual}.")
    else:
        for _, row in mis_okrs.iterrows():
            with st.container(border=True):
                col_txt, col_status, col_del = st.columns([4, 2, 1])
                
                nombre_corp = okrs_org[okrs_org["id"] == row["link_org"]]["nombre"].values
                vinculo = nombre_corp[0] if len(nombre_corp) > 0 else "Desconocido"
                
                with col_txt:
                    st.markdown(f"### {row['nombre']}")
                    st.caption(f"🔗 Vinculado a: **{vinculo}**")
                    st.write(row['descripcion'])
                
                with col_status:
                    # Badge visual según el estado
                    color = "blue" if row['estado'] == "Nuevo" else "orange" if row['estado'] == "En curso" else "green" if row['estado'] == "Completo" else "red"
                    st.markdown(f"**Estado:** :{color}[{row['estado']}]")
                
                with col_del:
                    if st.button("🗑️", key=f"del_mi_okr_{row['id']}"):
                        db.delete_okr(row['id'])
                        st.rerun(scope="fragment")

# --- FRAGMENTO: OKRS CORPORATIVOS (MANAGER) ---
@st.fragment
def render_okrs_corporativos(db):
    c1, c2 = st.columns([3, 1])
    c1.subheader("Gestión de OKRs Corporativos")
    if c2.button("🔄 Actualizar OKRs", key="btn_ref_corp", use_container_width=True):
        st.cache_data.clear()

    _, okrs_df, _ = db.load_all_data()
    okrs_org = okrs_df[okrs_df["tipo"] == "Organizacion"]

    with st.expander("➕ Definir Nuevo OKR Corporativo"):
        with st.form("nuevo_okr_org", clear_on_submit=True):
            nombre = st.text_input("Nombre del Objetivo")
            descripcion = st.text_area("Descripción")
            if st.form_submit_button("Crear OKR Corporativo", use_container_width=True):
                nuevo_okr = {
                    "nombre": nombre,
                    "descripcion": descripcion,
                    "tipo": "Organizacion",
                    "id_empleado": ""
                }
                if db.save_okr(nuevo_okr):
                    st.success("Objetivo creado")
                    st.rerun(scope="fragment")

    st.divider()
    if okrs_org.empty:
        st.info("No hay objetivos corporativos definidos.")
    else:
        for index, row in okrs_org.iterrows():
            with st.container(border=True):
                col_txt, col_actions = st.columns([4, 1])
                with col_txt:
                    st.markdown(f"### {row['nombre']}")
                    st.write(row['descripcion'])
                with col_actions:
                    if st.button("📝 Editar", key=f"edit_{row['id']}"):
                        st.session_state[f"editing_{row['id']}"] = True
                    if st.button("🗑️ Borrar", key=f"del_{row['id']}", type="secondary"):
                        db.delete_okr(row['id'])
                        st.rerun(scope="fragment")

                if st.session_state.get(f"editing_{row['id']}", False):
                    with st.form(f"form_edit_{row['id']}"):
                        new_name = st.text_input("Nombre", value=row['nombre'])
                        new_desc = st.text_area("Descripción", value=row['descripcion'])
                        c1, c2 = st.columns(2)
                        if c1.form_submit_button("Guardar"):
                            db.update_okr(row['id'], {"nombre": new_name, "descripcion": new_desc})
                            st.session_state[f"editing_{row['id']}"] = False
                            st.rerun(scope="fragment")
                        if c2.form_submit_button("Cancelar"):
                            st.session_state[f"editing_{row['id']}"] = False
                            st.rerun(scope="fragment")

# --- FRAGMENTO: GESTION EMPLEADOS (MANAGER) ---
@st.fragment
def render_gestion_empleados_fragment(db):
    c1, c2 = st.columns([3, 1])
    c1.subheader("Personal de la Empresa")
    if c2.button("🔄 Actualizar Tabla", key="btn_ref_empl", use_container_width=True):
        st.cache_data.clear()

    # Recarga de datos local al fragmento
    empleados_df, _, _ = db.load_all_data()
    
    st.dataframe(
        empleados_df[["nombre", "email", "rol"]], 
        use_container_width=True, 
        hide_index=True
    )
    
    st.divider()
    with st.expander("➕ Dar de alta nuevo empleado"):
        with st.form("form_registro_empleado", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                u_nom = st.text_input("Nombre Completo")
                u_email = st.text_input("Email Corporativo")
            with col2:
                u_rol = st.selectbox("Rol en el sistema", ["empleado", "manager"])
                u_pass = st.text_input("Contraseña Temporal", type="password")
            
            if st.form_submit_button("Guardar Empleado", use_container_width=True):
                if u_nom and u_email and u_pass:
                    nuevo_empleado = {"nombre": u_nom, "email": u_email, "password": u_pass, "rol": u_rol}
                    if db.save_employee(nuevo_empleado):
                        st.success(f"✅ ¡{u_nom} registrado!")
                        st.rerun(scope="fragment")
                else:
                    st.warning("⚠️ Por favor, completa todos los campos.")

# --- VISTAS PRINCIPALES ---

def render_manager_view(data_manager, empleados_df, okrs_df):
    st.title("🛡️ Panel de Dirección")
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🎯 OKRs Corporativos", "👥 Empleados"])
    
    with tab1:
        st.subheader("Avance de la Compañía")
    with tab2:
        render_okrs_corporativos(data_manager)
    with tab3:
        render_gestion_empleados_fragment(data_manager)

def render_employee_view(user_data, okrs_df, tareas_df):
    st.title(f"🚀 Panel de: {user_data['nombre']}")
    tab1, tab2 = st.tabs(["📉 Mis Objetivos", "📝 Mis Tareas"])
    
    with tab1:
        render_mis_okrs_empleado(db, int(user_data.get('id')))
    
    with tab2:
        st.write("Sección de tareas en desarrollo...")