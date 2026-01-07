import streamlit as st

def init_session():
    """Inicializa las variables de estado si no existen."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user = None

def check_credentials(df_empleados, email_input, pass_input):
    """Valida email y password contra el dataframe."""
    # Buscamos el usuario por email
    user_match = df_empleados[df_empleados["email"] == email_input]
    if not user_match.empty:
        # Verificamos la password (case sensitive)
        stored_pass = str(user_match.iloc[0]["password"])
        if str(pass_input) == stored_pass:
            return user_match.iloc[0] # Retorna la fila del usuario
    return None

def login(user_data):
    st.session_state.authenticated = True
    st.session_state.user = user_data
    st.rerun()

def logout():
    st.session_state.authenticated = False
    st.session_state.user = None
    st.rerun()