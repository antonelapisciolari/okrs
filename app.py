import streamlit as st
from db import DataManager
import auth as auth
import componentes as ui

# 1. Configuración e Inicialización
st.set_page_config(page_title="OKR Enterprise System")
auth.init_session()
db = DataManager()

# 2. Carga de datos (silenciosa para el login)
try:
    empleados, okrs, tareas = db.load_all_data()
except Exception as e:
    st.error("Error al conectar con la base de datos.")
    st.stop()

# 3. Router de Vistas
if not st.session_state.authenticated:
    # --- VISTA DE LOGIN ---
    st.container()
    with st.form("login_form"):
        st.title("OKRs Empresarial")
        st.markdown("Introduce tus credenciales corporativas")
        st.write("Manager: manager@gmail.com - Contraseña: manager123")
        st.write("Empleado: empleado@gmail.com - Contraseña: emp123")
        email = st.text_input("Correo Electrónico")
        password = st.text_input("Contraseña", type="password")
        
        submit = st.form_submit_button("Iniciar Sesión", use_container_width=True)
        
        if submit:
            user_found = auth.check_credentials(empleados, email, password)
            if user_found is not None:
                auth.login(user_found)
            else:
                st.error("Email o contraseña incorrectos")
else:
    # --- VISTA DE APLICACIÓN (POST-LOGIN) ---
    st.set_page_config(layout="wide") # Cambiamos a ancho completo una vez dentro
    user = st.session_state.user
    
    # Sidebar de Navegación
    with st.sidebar:
        st.title("🚀 OKR Tracker")
        st.write(f"Usuario: **{user['nombre']}**")
        st.write(f"Rol: `{user['rol'].upper()}`")
        st.divider()
        if st.button("Cerrar Sesión"):
            auth.logout()

    # Router por Rol
    if user['rol'].lower() == "manager":
        ui.render_manager_view(db, empleados, okrs)
    else:
        ui.render_employee_view(user, okrs, tareas)