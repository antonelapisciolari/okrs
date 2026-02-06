import streamlit as st
from db import  preguntar_gemini_personalizado,load_okrs, update_okr, update_tarea, delete_okr, delete_tarea,load_tareas, save_area,load_empleados, save_employee, save_okr, save_tarea,load_areas
from datetime import datetime
import pandas as pd
import time

anio_actual = datetime.now().year

def calcular_progreso_empleado(okrs_emp, tareas_df):
    progresos = []
    if okrs_emp.empty:
        return 0.0
    for _, okr in okrs_emp.iterrows():
        t_okr = tareas_df[tareas_df['link_okr'] == str(okr['id'])] if not tareas_df.empty else pd.DataFrame()
        if not t_okr.empty:
            puntos = t_okr['estado'].map({"Hecho": 1.0, "Haciendo": 0.5, "Pendiente": 0.0}).sum()
            progresos.append(puntos / len(t_okr))
        else:
            progresos.append(0.0)
    return sum(progresos) / len(progresos) if progresos else 0.0

@st.fragment
def render_asistente_ia(okrs_df, user_data):
    st.subheader("🤖 Consultor Estratégico AI (v1 SDK)")
    
    if okrs_df.empty:
        st.info("No hay datos de OKRs registrados para analizar.")
        return

    mis_datos_okr = okrs_df[okrs_df['id_empleado'].astype(str) == str(user_data['id'])].to_dict('records')

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": f"Hola {user_data['nombre']}, ¿en qué puedo ayudarte hoy?"}
        ]

    chat_placeholder = st.container(height=450)
    with chat_placeholder:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt := st.chat_input("Escribe tu consulta..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_placeholder:
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Consultando con Gemini..."):
                    try:
                        respuesta = preguntar_gemini_personalizado(
                            prompt, 
                            mis_datos_okr, 
                            user_data['rol']
                        )
                        st.markdown(respuesta)
                        st.session_state.messages.append({"role": "assistant", "content": respuesta})
                    except Exception as e:
                        st.error(f"Error con el nuevo SDK: {e}")
        st.rerun(scope="fragment")

@st.fragment
def render_manager_dashboard(empleados_df, okrs_df, tareas_df, areas_df):
    if "vista_detalle" not in st.session_state:
        st.session_state.vista_detalle = None

    if st.session_state.vista_detalle:
        if st.button("⬅️ Volver al Equipo"):
            st.session_state.vista_detalle = None
            st.rerun()
    
    if empleados_df.empty:
        st.info("No hay empleados registrados aún.")
        return
    else:
        empleados_df['id'] = empleados_df['id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        
    if not okrs_df.empty:
        okrs_df['id'] = okrs_df['id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        okrs_df['id_empleado'] = okrs_df['id_empleado'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    if not tareas_df.empty:
        tareas_df['link_okr'] = tareas_df['link_okr'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    for df, col in [(okrs_df, 'id_empleado'), (tareas_df, 'link_okr'), (empleados_df, 'id')]:
        if not df.empty:
            df[col] = df[col].astype(str).str.replace(".0", "", regex=False).str.strip()

    if not st.session_state.vista_detalle:
        st.subheader(f"📊 Progreso del Equipo - {anio_actual}")
        
        areas_disponibles = ["Todas"] + (areas_df['nombre'].tolist() if not areas_df.empty else [])
        col1, col2 = st.columns([1, 4])
        with col1:
            area_sel = st.selectbox("Filtrar por Área/Departamento", areas_disponibles)

        solo_empleados = empleados_df
        if area_sel != "Todas":
            solo_empleados = solo_empleados[solo_empleados['area'] == area_sel]

        if solo_empleados.empty:
            st.warning(f"No hay empleados registrados en el área: {area_sel}")
            return

        for _, emp in solo_empleados.iterrows():
            okrs_emp = okrs_df[
                (okrs_df['id_empleado'] == emp['id']) & 
                (okrs_df['anio'].astype(str) == str(anio_actual))
            ] if not okrs_df.empty else pd.DataFrame()
            
            with st.container(border=True):
                c_info, c_prog, c_btn = st.columns([2, 3, 1])
                
                with c_info:
                    st.markdown(f"**{emp['nombre']}**")
                    st.caption(f"{emp['rol']}")
                    area_display = emp['area'] if pd.notna(emp['area']) and emp['area'] != "" else "Sin Área"
                    st.caption(f"📍 {area_display} | {len(okrs_emp)} OKRs")
                
                with c_prog:
                    if not okrs_emp.empty:
                        promedio = calcular_progreso_empleado(okrs_emp, tareas_df)
                        st.progress(float(promedio))
                        st.caption(f"Cumplimiento: {int(promedio*100)}%")
                    else:
                        st.caption("Sin objetivos")

                with c_btn:
                    if st.button("Ver detalle", key=f"btn_{emp['id']}", use_container_width=True):
                        st.session_state.vista_detalle = emp['id']
                        st.rerun()

    else:
        emp_id = st.session_state.vista_detalle
        empleado = empleados_df[empleados_df['id'] == emp_id].iloc[0]

        okrs_del_empleado = okrs_df[okrs_df['id_empleado'] == emp_id] if not okrs_df.empty else pd.DataFrame()
        
        if okrs_del_empleado.empty:
            st.info(f"{empleado['nombre']} aún no tiene OKRs registrados.")
            return

        años_disponibles = sorted(okrs_del_empleado['anio'].unique().tolist(), reverse=True)
        
        col1, col2 = st.columns([4, 1])
        with col1:
            st.subheader(f"Gestión de OKRs: {empleado['nombre']}")
        with col2:
            anio_sel = st.selectbox("📅 Filtrar por Año", años_disponibles)
        
        okrs_emp = okrs_del_empleado[okrs_del_empleado['anio'] == anio_sel]

        if okrs_emp.empty:
            st.warning(f"No hay OKRs para el año {anio_sel}.")
        else:
            for _, okr in okrs_emp.iterrows():
                with st.expander(f"🎯 OKR: {okr['nombre']}", expanded=True):
                    with st.container(border=True):
                        c_tit, c_anio, c_est = st.columns([3, 1, 2.5])
                        with c_tit:
                            st.write(f"**OKR: {okr['nombre']}**")
                            if 'descripcion' in okr and okr['descripcion']:
                                st.caption(f"{okr['descripcion']}")
                        with c_anio:
                            st.write(f"Año: {okr['anio']}")
                        with c_est:
                            lista_est_okr = ["Nuevo", "Incompleto", "Completo"]
                            idx_okr = lista_est_okr.index(okr['estado']) if okr['estado'] in lista_est_okr else 0
                            nuevo_estado_okr = st.selectbox("Estado OKR", lista_est_okr, index=idx_okr, key=f"mngr_upd_okr_{okr['id']}", label_visibility="collapsed")
                            id_actual = str(okr['id']).strip().replace(".0", "")
                            if nuevo_estado_okr != okr['estado']:
                                with st.spinner("Actualizando..."):
                                    if update_okr(id_actual, {"estado": nuevo_estado_okr}):
                                        st.cache_data.clear()
                                        st.toast("✅ OKR actualizado")
                                        st.rerun()

                        st.markdown("<hr style='margin: 0.5em 0px; border-top: 1px solid #ccc; opacity: 0.3;'>", unsafe_allow_html=True)
                        mis_tareas = tareas_df[tareas_df["link_okr"] == str(okr['id'])] if not tareas_df.empty else pd.DataFrame()
                        if not mis_tareas.empty:
                            for _, t in mis_tareas.iterrows():
                                t_col1, t_col2 = st.columns([4, 2])
                                t_col1.write(f" {t['nombre'].upper()}")
                                lista_estados_t = ["Pendiente", "Haciendo", "Hecho"]
                                idx_t = lista_estados_t.index(t['estado']) if t['estado'] in lista_estados_t else 0
                                nuevo_e_t = t_col2.selectbox("Estado Tarea", lista_estados_t, index=idx_t, key=f"mngr_upd_t_{t['id']}", label_visibility="collapsed")
                                if nuevo_e_t != t['estado']:
                                    if update_tarea(t['id'], {"estado": nuevo_e_t}):
                                        st.cache_data.clear()
                                        st.toast("✅ Tarea actualizada")
                                        st.rerun(scope="fragment")
                        else:
                            st.caption("No hay tareas registradas.")

@st.fragment
def render_mis_okrs_empleado(okrs_df, tareas_df, user_id_actual):
    st.subheader(f"🎯 Mis Objetivos Personales - {anio_actual}")
    
    # 1. Initialize Session State for OKRs and Tasks
    if "okrs_runtime" not in st.session_state:
        st.session_state.okrs_runtime = okrs_df
    if "tareas_runtime" not in st.session_state:
        st.session_state.tareas_runtime = tareas_df

    # 2. Use the runtime state as the source of truth
    working_okrs = st.session_state.okrs_runtime
    working_tareas = st.session_state.tareas_runtime
    
    # Filter corporate OKRs for the dropdown
    okrs_org = working_okrs[working_okrs["tipo"] == "Organizacion"] if not working_okrs.empty else pd.DataFrame()
    
    # --- FORM: NEW PERSONAL OKR ---
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
                            "anio": anio_actual, "estado": estado
                        }
                        if save_okr(nuevo_okr):
                            # Update state from DB
                            st.session_state.okrs_runtime = load_okrs()
                            st.toast(f"✅ OKR '{nombre}' creado.")
                            time.sleep(1)
                            st.rerun(scope="fragment")

    st.divider()

    # --- LIST: PERSONAL OKRS ---
    # Filter my personal OKRs from the runtime state
    if not working_okrs.empty:
        mis_okrs = working_okrs[
            (working_okrs["tipo"] == "Empleado") & 
            (working_okrs["id_empleado"].astype(str) == str(user_id_actual)) & 
            (working_okrs["anio"].astype(str) == str(anio_actual))
        ]
    else:
        mis_okrs = pd.DataFrame()

    if mis_okrs.empty:
        st.info("Aún no tienes objetivos personales registrados.")
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
                        if delete_okr(row['id']):
                            st.session_state.okrs_runtime = load_okrs()
                            st.toast("✅ OKR eliminado.")
                            time.sleep(1)
                            st.rerun(scope="fragment")

                # --- TASKS SECTION ---
                with st.expander(f"📝 Tareas de este objetivo"):
                    # Filter tasks from the runtime state
                    current_okr_id = str(row["id"])
                    mis_tareas = working_tareas[working_tareas["link_okr"] == current_okr_id] if not working_tareas.empty else pd.DataFrame()
                    
                    with st.form(key=f"form_tarea_{row['id']}", clear_on_submit=True):
                        tc1, tc2, tc3 = st.columns([3, 2, 1])
                        t_nombre = tc1.text_input("Nueva tarea")
                        t_estado = tc2.selectbox("Estado", ["Pendiente", "Haciendo", "Hecho"], key=f"st_{row['id']}")
                        if tc3.form_submit_button("➕"):
                            if t_nombre:
                                if save_tarea({"nombre": t_nombre, "estado": t_estado, "link_okr": current_okr_id, "id_empleado": user_id_actual}):
                                    st.session_state.tareas_runtime = load_tareas()
                                    st.toast("✅ Tarea agregada.")
                                    time.sleep(0.5)
                                    st.rerun(scope="fragment")

                    if not mis_tareas.empty:
                        for _, t in mis_tareas.iterrows():
                            t_col1, t_col2, t_col3 = st.columns([4, 2, 1])
                            t_col1.write(f"• {t['nombre']}")
                            
                            # Status update logic
                            nuevo_e = t_col2.selectbox("E", ["Pendiente", "Haciendo", "Hecho"], 
                                                      index=["Pendiente", "Haciendo", "Hecho"].index(t['estado']),
                                                      key=f"upd_t_{t['id']}", label_visibility="collapsed")
                            if nuevo_e != t['estado']:
                                if update_tarea(t['id'], {"estado": nuevo_e}):
                                    st.session_state.tareas_runtime = load_tareas()
                                    st.toast("✅ Estado actualizado.")
                                    time.sleep(0.5)
                                    st.rerun(scope="fragment")
                            
                            # Delete task logic
                            if t_col3.button("❌", key=f"del_t_{t['id']}"):
                                if delete_tarea(t['id']):
                                    st.session_state.tareas_runtime = load_tareas()
                                    st.toast("🗑️ Tarea eliminada.")
                                    time.sleep(0.5)
                                    st.rerun(scope="fragment")


@st.fragment
def render_okrs_corporativos(okrs_df):
    c1, c2 = st.columns([3, 1])
    c1.subheader("Gestión de OKRs Corporativos")
    
    if "okrs_runtime" not in st.session_state:
        st.session_state.okrs_runtime = okrs_df

    okrs_working_df = st.session_state.okrs_runtime

    if okrs_working_df is None or (isinstance(okrs_working_df, pd.DataFrame) and okrs_working_df.empty):
        okrs_org = pd.DataFrame(columns=["id", "nombre", "descripcion", "tipo", "anio", "estado"])
    else:
        # Filter safely: check if 'tipo' exists before filtering
        if "tipo" in okrs_working_df.columns:
            okrs_org = okrs_working_df[okrs_working_df["tipo"] == "Organizacion"]
        else:
            okrs_org = pd.DataFrame()
    with st.expander("➕ Definir Nuevo OKR Corporativo"):
        with st.form("nuevo_okr_org", clear_on_submit=True):
            nombre = st.text_input("Nombre del Objetivo")
            descripcion = st.text_area("Descripción")
            if st.form_submit_button("Crear OKR Corporativo", use_container_width=True):
                exito = save_okr({"nombre": nombre, "descripcion": descripcion, "tipo": "Organizacion", "id_empleado": None, "anio": anio_actual, "estado": "Nuevo"})
                if exito:    
                    st.session_state.okrs_runtime = load_okrs()
                    st.toast(f"✅ ¡{nombre} registrado con éxito!")
                    time.sleep(1.5)
                    st.rerun(scope="fragment")
                else:
                    st.error("Por favor, contacta a soporte: antopiscio@gmail.com")
                        

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
                    if st.button("🗑️ Borrar", key=f"del_corp_{row['id']}"):
                        exito = delete_okr(row['id'])
                        if exito:
                            if "okrs_runtime" in st.session_state:
                                st.session_state.okrs_runtime = load_okrs()

                            st.toast("✅ OKR Borrado exitosamente")
                            time.sleep(1)
                            st.rerun(scope="fragment")

@st.fragment
def render_gestion_empleados_fragment(empleados_df, areas_df):
    st.subheader("Personal de la Empresa")

    if "empleados_runtime" not in st.session_state:
        st.session_state.empleados_runtime = empleados_df
    
    if "areas_runtime" not in st.session_state:
        st.session_state.areas_runtime = areas_df

    # 2. Reference the working data from State
    working_empl = st.session_state.empleados_runtime
    working_areas = st.session_state.areas_runtime

    # Display Employee Table
    if not working_empl.empty:
        # We work on a copy to avoid modifying the original state directly during formatting
        df_display = working_empl.copy()
        df_display['nombre'] = df_display['nombre'].str.upper()
        st.dataframe(
            df_display[["nombre", "email", "rol", "area"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "nombre": st.column_config.TextColumn("NOMBRE COMPLETO"),
                "email": st.column_config.TextColumn("EMAIL"),
                "rol": st.column_config.TextColumn("ROL"),
                "area": "ÁREA/DEP"
            }
        )
    else:
        st.info("No hay empleados registrados aún.")
    
    st.divider()

    # --- FORM: NEW EMPLOYEE ---
    with st.expander("➕ Dar de alta nuevo empleado"):
        with st.form("form_registro_empleado", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                u_nom = st.text_input("Nombre Completo")
                u_email = st.text_input("Email Corporativo")
            with col2:
                u_rol = st.selectbox("Rol en el sistema", ["empleado", "manager"])
                # Use areas from the runtime state
                lista_areas = working_areas['nombre'].tolist() if not working_areas.empty else ["Sin áreas definidas"]
                u_area = st.selectbox("Area/Depto", lista_areas)
                u_pass = st.text_input("Contraseña Temporal", type="password")
            
            if st.form_submit_button("Guardar Empleado", use_container_width=True):
                if u_nom and u_email and u_pass:
                    with st.spinner("Guardando..."):
                        exito = save_employee({
                            "nombre": u_nom, 
                            "email": u_email, 
                            "password": u_pass, 
                            "rol": u_rol, 
                            "area": u_area
                        })
                        if exito:
                            # OPTIMIZATION: Update state immediately
                            # Assuming you have a load_employees() helper, otherwise use your main load method
                            st.session_state.empleados_runtime = load_empleados() 
                            st.toast(f"✅ ¡{u_nom} registrado con éxito!")
                            time.sleep(1)
                            st.rerun(scope="fragment")
                        else:
                            st.error("Error al guardar. Contacta a soporte.")

    # --- FORM: NEW AREA ---
    with st.expander("➕ Nueva Area"):
        with st.form("form_area", clear_on_submit=True):
            area_nom = st.text_input("Nombre del Área")
            if st.form_submit_button("Guardar Área"):
                if area_nom:
                    if save_area({"nombre": area_nom}):
                        # OPTIMIZATION: Update areas state immediately
                        st.session_state.areas_runtime = load_areas() 
                        st.toast(f"✅ Área '{area_nom}' registrada.")
                        time.sleep(1)
                        st.rerun(scope="fragment")
@st.fragment
def render_employee_dashboard(okrs_df, tareas_df, user_id_actual):
    st.subheader("📊 Mi Progreso Histórico")

    # 1. Inicializar Session State para que el dashboard sea "vivo"
    if "okrs_runtime" not in st.session_state:
        st.session_state.okrs_runtime = okrs_df
    if "tareas_runtime" not in st.session_state:
        st.session_state.tareas_runtime = tareas_df
    if st.button("🔄 Actualizar Datos"):
                # Update the session state from DB
                st.session_state.okrs_runtime = load_okrs()
                st.session_state.tareas_runtime = load_tareas()
                st.toast("✅ Datos sincronizados")
                time.sleep(1)
                st.rerun(scope="fragment")
    # 3. Usar el runtime state
    working_okrs = st.session_state.okrs_runtime
    working_tareas = st.session_state.tareas_runtime

    if working_okrs.empty:
        st.info("No hay datos de OKRs disponibles.")
        return

    # 4. Filtrado del empleado actual
    id_buscado = str(user_id_actual)
    # Limpieza de IDs para evitar errores de comparación
    datos_empleado = working_okrs[working_okrs['id_empleado'].astype(str).str.replace(".0","",regex=False) == id_buscado]

    if datos_empleado.empty:
        st.info("Aún no tienes objetivos registrados para mostrar en el gráfico de progreso.")
        return

    # 5. Selector de año
    mis_anios = sorted(datos_empleado['anio'].unique(), reverse=True)
    col_anio, _, col_act = st.columns([2, 5, 2])
    with col_anio:
        anio_sel = st.selectbox("Selecciona el año", options=mis_anios)
    

    okrs_filtrados = datos_empleado[datos_empleado['anio'].astype(str) == str(anio_sel)]

    # 6. Renderizado de barras de progreso
    for _, okr in okrs_filtrados.iterrows():
        # Filtramos tareas del OKR específico desde el runtime
        tareas_okr = working_tareas[working_tareas['link_okr'] == str(okr['id'])] if not working_tareas.empty else pd.DataFrame()
        
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            
            if not tareas_okr.empty:
                # Cálculo de puntos basado en estado
                puntos = tareas_okr['estado'].map({"Hecho": 1.0, "Haciendo": 0.5, "Pendiente": 0.0}).sum()
                porcentaje = (puntos / len(tareas_okr))
            else: 
                porcentaje = 0.0
            
            c1.markdown(f"**{okr['nombre']}**")
            # Limitamos el progreso entre 0.0 y 1.0 para evitar errores de st.progress
            progreso_final = max(0.0, min(float(porcentaje), 1.0))
            c1.progress(progreso_final)
            
            c2.metric("Avance", f"{int(progreso_final * 100)}%")

def render_manager_view(empleados_df, okrs_df, tareas_df, areas_df):
    st.title("🛡️ Panel de Dirección")
    tabs = st.tabs(["📊 Dashboard Equipo", "🎯 OKRs Corporativos", "👥 Empleados", "🤖 Asistente IA"])
    with tabs[0]: render_manager_dashboard(empleados_df, okrs_df, tareas_df, areas_df)
    with tabs[1]: render_okrs_corporativos(okrs_df)
    with tabs[2]: render_gestion_empleados_fragment(empleados_df, areas_df)
    with tabs[3]: render_asistente_ia(empleados_df, okrs_df, tareas_df, areas_df, st.session_state.user)

def render_employee_view(user_data, okrs_df, tareas_df):
    st.title(f"🚀 Panel de: {user_data['nombre']}")
    tabs = st.tabs(["📊 Dashboard", "📉 Mis Objetivos", "🏢 OKRs Empresa", "🤖 Asistente IA"])
    with tabs[0]: render_employee_dashboard(okrs_df, tareas_df, user_data['id'])
    with tabs[1]: render_mis_okrs_empleado(okrs_df, tareas_df, user_data['id'])
    with tabs[2]:
        st.subheader("🏢 Objetivos Globales")

        okrs_corp = okrs_df[okrs_df["tipo"] == "Organizacion"] if not okrs_df.empty else pd.DataFrame()
        if okrs_corp.empty:
            st.info("No hay objetivos corporativos.")
        else:
            for _, r in okrs_corp.iterrows():
                with st.container(border=True):
                    st.write(f"**{r['nombre']}**")
                    st.caption(r['descripcion'])
    with tabs[3]: render_asistente_ia(okrs_df, user_data)