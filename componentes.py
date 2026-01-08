import streamlit as st
from db import DataManager
from datetime import datetime
import time

db = DataManager()
anio_actual = datetime.now().year

# --- FRAGMENTO: DASHBOARD MANAGER (NUEVO) ---
@st.fragment
def render_manager_dashboard(db):
    st.subheader(f"📊 Progreso Global del Equipo - {anio_actual}")
    
    # 1. Carga de datos
    empleados_df, okrs_df, tareas_df = db.load_all_data()
    
    # Limpieza rápida para el cruce de datos
    okrs_df['id_empleado'] = okrs_df['id_empleado'].astype(str).str.replace(".0", "", regex=False).str.strip()
    tareas_df['link_okr'] = tareas_df['link_okr'].astype(str).str.replace(".0", "", regex=False).str.strip()
    empleados_df['id'] = empleados_df['id'].astype(str).str.replace(".0", "", regex=False).str.strip()

    # Solo mostramos a los que tienen rol 'empleado'
    solo_empleados = empleados_df[empleados_df['rol'] == 'empleado']

    if solo_empleados.empty:
        st.info("No hay empleados registrados.")
        return

    for _, emp in solo_empleados.iterrows():
        # Obtenemos OKRs de este empleado para el año actual
        okrs_emp = okrs_df[
            (okrs_df['id_empleado'] == emp['id']) & 
            (okrs_df['año'].astype(str) == str(anio_actual)) &
            (okrs_df['tipo'].str.strip() == "Empleado")
        ]
        
        with st.container(border=True):
            col_info, col_prog = st.columns([1, 2])
            with col_info:
                st.write(f"👤 **{emp['nombre']}**")
                st.caption(f"OKRs: {len(okrs_emp)}")
            
            with col_prog:
                if not okrs_emp.empty:
                    progresos = []
                    for _, okr in okrs_emp.iterrows():
                        t_okr = tareas_df[tareas_df['link_okr'] == str(okr['id'])]
                        if not t_okr.empty:
                            puntos = t_okr['estado'].map({"Hecho": 1.0, "Haciendo": 0.5, "Pendiente": 0.0}).sum()
                            progresos.append(puntos / len(t_okr))
                        else:
                            progresos.append(0.0)
                    
                    promedio = sum(progresos) / len(progresos)
                    st.progress(float(promedio))
                    st.write(f"Cumplimiento: **{int(promedio*100)}%**")
                else:
                    st.caption("Sin objetivos este año")

# --- FRAGMENTO: MIS OKRS (EMPLEADO) ---
@st.fragment
def render_mis_okrs_empleado(db, user_id_actual):
    c1, c2 = st.columns([3, 1])
    c1.subheader(f"🎯 Mis Objetivos Personales - {anio_actual}")
    
    if c2.button("🔄 Actualizar OKRs", key="btn_ref_mis_okrs", use_container_width=True):
        with st.spinner("Actualizando..."): # AGREGADO SPINNER
            st.cache_data.clear()
            time.sleep(0.5)

    # 1. Carga de datos fresca
    _, okrs_df, tareas_df = db.load_all_data()
    if not tareas_df.empty:
        tareas_df.columns = tareas_df.columns.str.strip()
        tareas_df['link_okr'] = tareas_df['link_okr'].astype(str).str.replace(".0", "", regex=False).str.strip()
    
    okrs_org = okrs_df[okrs_df["tipo"] == "Organizacion"]
    
    okrs_df.columns = okrs_df.columns.str.strip()
    okrs_df['tipo'] = okrs_df['tipo'].astype(str).str.strip()
    okrs_df['año'] = okrs_df['año'].astype(str).str.strip()
    
    mis_okrs = okrs_df[
        (okrs_df["tipo"] == "Empleado") & 
        (okrs_df["id_empleado"].astype(str) == str(user_id_actual)) &
        (okrs_df["año"] == str(anio_actual))
    ]
    
    with st.expander("Nuevo Objetivo Personal"):
        if okrs_org.empty:
            st.warning("No hay OKRs corporativos definidos para vincular.")
        else:
            with st.form("nuevo_okr_personal", clear_on_submit=True):
                okr_corp_opciones = {row["nombre"]: row["id"] for _, row in okrs_org.iterrows()}
                okr_corp_seleccionado = st.selectbox("Vincular a Objetivo Empresa", options=okr_corp_opciones.keys())
                nombre = st.text_input("Mi Objetivo")
                descripcion = st.text_area("¿Cómo voy a lograrlo?")
                estado = st.selectbox("Estado inicial", ["Nuevo", "En curso", "Completo", "Incompleto"])
                
                if st.form_submit_button("Guardar mi OKR", use_container_width=True):
                    if nombre and descripcion:
                        nuevo_okr = {
                            "nombre": nombre, "descripcion": descripcion, "tipo": "Empleado",
                            "id_empleado": user_id_actual, "link_org": okr_corp_opciones[okr_corp_seleccionado],
                            "año": anio_actual, "estado": estado
                        }
                        if db.save_okr(nuevo_okr):
                            st.success(f"OKR para el {anio_actual} creado.")
                            st.rerun(scope="fragment")
                    else:
                        st.warning("Completa los campos obligatorios.")

    st.divider()

    if mis_okrs.empty:
        st.info(f"Aún no tienes objetivos personales registrados.")
    else:
        for _, row in mis_okrs.iterrows():
            with st.container(border=True):
                col_txt, col_status, col_del = st.columns([4, 2, 0.5])
                with col_txt:
                    st.markdown(f"### {row['nombre']}")
                    st.write(row['descripcion'])
                with col_status:
                    color = "blue" if row['estado'] == "Nuevo" else "orange" if row['estado'] == "En curso" else "green"
                    st.markdown(f"**Estado:** :{color}[{row['estado']}]")
                with col_del:
                    if st.button("🗑️", key=f"del_okr_{row['id']}"):
                        db.delete_okr(row['id'])
                        st.rerun(scope="fragment")

                with st.expander(f"📝 Tareas de este objetivo"):
                    mis_tareas = tareas_df[tareas_df["link_okr"] == str(row["id"])] if not tareas_df.empty else []
                    with st.form(key=f"form_tarea_{row['id']}", clear_on_submit=True):
                        c1, c2, c3 = st.columns([3, 2, 1])
                        t_nombre = c1.text_input("Nueva tarea")
                        t_estado = c2.selectbox("Estado", ["Pendiente", "Haciendo", "Hecho"], key=f"st_{row['id']}")
                        if c3.form_submit_button("➕"):
                            if t_nombre:
                                db.save_tarea({"nombre": t_nombre, "estado": t_estado, "link_okr": str(row["id"]), "id_empleado": user_id_actual})
                                st.rerun(scope="fragment")

                    if len(mis_tareas) > 0:
                        for _, t in mis_tareas.iterrows():
                            t_col1, t_col2, t_col3 = st.columns([4, 2, 1])
                            t_col1.write(f"• {t['nombre']}")
                            nuevo_e = t_col2.selectbox("E", ["Pendiente", "Haciendo", "Hecho"], 
                                                      index=["Pendiente", "Haciendo", "Hecho"].index(t['estado']),
                                                      key=f"upd_t_{t['id']}", label_visibility="collapsed")
                            if nuevo_e != t['estado']:
                                db.update_tarea(t['id'], {"estado": nuevo_e})
                                st.rerun(scope="fragment")
                            if t_col3.button("❌", key=f"del_t_{t['id']}"):
                                db.delete_tarea(t['id']); st.rerun(scope="fragment")

# --- FRAGMENTO: OKRS CORPORATIVOS (MANAGER) ---
@st.fragment
def render_okrs_corporativos(db):
    c1, c2 = st.columns([3, 1])
    c1.subheader("Gestión de OKRs Corporativos")
    if c2.button("🔄 Actualizar OKRs", key="btn_ref_corp", use_container_width=True):
        with st.spinner("Cargando..."): # AGREGADO SPINNER
            st.cache_data.clear()
            time.sleep(0.5)

    _, okrs_df, _ = db.load_all_data()
    okrs_org = okrs_df[okrs_df["tipo"] == "Organizacion"]

    with st.expander("➕ Definir Nuevo OKR Corporativo"):
        with st.form("nuevo_okr_org", clear_on_submit=True):
            nombre = st.text_input("Nombre del Objetivo")
            descripcion = st.text_area("Descripción")
            if st.form_submit_button("Crear OKR Corporativo", use_container_width=True):
                if db.save_okr({"nombre": nombre, "descripcion": descripcion, "tipo": "Organizacion", "id_empleado": "", "año": anio_actual}):
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
                        db.delete_okr(row['id']); st.rerun(scope="fragment")

# --- FRAGMENTO: GESTION EMPLEADOS (MANAGER) ---
@st.fragment
def render_gestion_empleados_fragment(db):
    c1, c2 = st.columns([3, 1])
    c1.subheader("Personal de la Empresa")
    if c2.button("🔄 Actualizar Tabla", key="btn_ref_empl", use_container_width=True):
        with st.spinner("Refrescando..."): # AGREGADO SPINNER
            st.cache_data.clear()
            time.sleep(0.5)

    empleados_df, _, _ = db.load_all_data()
    st.dataframe(empleados_df[["nombre", "email", "rol"]], use_container_width=True, hide_index=True)
    
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
                    if db.save_employee({"nombre": u_nom, "email": u_email, "password": u_pass, "rol": u_rol}):
                        st.success(f"✅ ¡{u_nom} registrado!")
                        st.rerun(scope="fragment")

# --- FRAGMENTO: DASHBOARD EMPLEADO ---
@st.fragment
def render_employee_dashboard(db, user_id_actual):
    st.subheader("📊 Mi Progreso Histórico")
    
    _, okrs_df, tareas_df = db.load_all_data()
    
    if okrs_df.empty:
        st.info("No hay datos de OKRs.")
        return

    okrs_df.columns = okrs_df.columns.str.strip()
    okrs_df['id_empleado'] = okrs_df['id_empleado'].astype(str).str.replace(".0", "", regex=False).str.strip()
    
    if not tareas_df.empty:
        tareas_df['link_okr'] = tareas_df['link_okr'].astype(str).str.replace(".0", "", regex=False).str.strip()
        tareas_df['estado'] = tareas_df['estado'].astype(str).str.strip()

    id_buscado = str(user_id_actual)
    datos_empleado = okrs_df[okrs_df['id_empleado'] == id_buscado]
    
    if datos_empleado.empty:
        st.info("Aún no tienes objetivos personales registrados.")
        return

    mis_anios = sorted(datos_empleado['año'].unique(), reverse=True)
    col_anio, _,col_act = st.columns([2, 5, 2])
    with col_anio:
        anio_sel = st.selectbox("Selecciona el año", options=mis_anios)
    with col_act:
        if st.button("🔄 Actualizar Datos", key="btn_ref_dash_emp"):
            with st.spinner("Cargando..."): # AGREGADO SPINNER
                st.cache_data.clear()
                time.sleep(0.5)
            st.rerun(scope="fragment")

    okrs_filtrados = datos_empleado[(datos_empleado['año'].astype(str) == str(anio_sel)) & (datos_empleado['tipo'].str.strip() == "Empleado")]

    for _, okr in okrs_filtrados.iterrows():
        tareas_okr = tareas_df[tareas_df['link_okr'] == str(okr['id'])] if not tareas_df.empty else []
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            if not tareas_okr.empty:
                puntos = tareas_okr['estado'].map({"Hecho": 1.0, "Haciendo": 0.5, "Pendiente": 0.0}).sum()
                porcentaje = (puntos / len(tareas_okr))
            else: porcentaje = 0.0

            c1.markdown(f"### {okr['nombre']}")
            c1.progress(float(porcentaje))
            c2.metric("Progreso", f"{int(porcentaje * 100)}%")

# --- VISTAS PRINCIPALES ---
def render_manager_view(data_manager, empleados_df, okrs_df):
    st.title("🛡️ Panel de Dirección")
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard Equipo", "🎯 OKRs Corporativos", "👥 Empleados"])
    
    with tab1:
        render_manager_dashboard(data_manager) # LLAMADA AL NUEVO DASHBOARD
    with tab2:
        render_okrs_corporativos(data_manager)
    with tab3:
        render_gestion_empleados_fragment(data_manager)

def render_employee_view(user_data, okrs_df, tareas_df):
    st.title(f"🚀 Panel de: {user_data['nombre']}")
    tabs = ["📊 Dashboard", "📉 Mis Objetivos", "🏢 OKRs Empresa"]
    tab_list = st.tabs(tabs)
    
    with tab_list[0]:
        render_employee_dashboard(db, int(user_data.get('id')))
    with tab_list[1]:
        render_mis_okrs_empleado(db, int(user_data.get('id')))
    with tab_list[2]:
        st.subheader("🏢 Objetivos Globales")
        _, okrs_df_f, _ = db.load_all_data()
        for _, row in okrs_df_f[okrs_df_f["tipo"].str.strip() == "Organizacion"].iterrows():
            with st.container(border=True):
                st.subheader(row['nombre'])
                st.write(row['descripcion'])