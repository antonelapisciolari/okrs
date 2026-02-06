import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import os
from supabase import create_client, Client
from google import genai
from google.genai import types
from variables import *
load_dotenv()
# --- CONFIGURACIÓN SEGÚN TU ESTRUCTURA ---
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
env = os.getenv("SUPABASE_ENV")

supabase: Client = create_client(url, key)

# --- MÉTODO CORE PARA DATA_EDITOR ---
def update_database_from_editor(table_name, df_changes, pk_col="id"):
    """Procesa los cambios del st.data_editor y los sube a Supabase"""
    # 1. Filas editadas
    for index, row in df_changes.get("edited_rows", {}).items():
        # Obtenemos el ID real desde el dataframe original guardado en session_state
        real_id = st.session_state[f"original_{table_name}"].iloc[index][pk_col]
        supabase.table(table_name).update(row).eq(pk_col, real_id).execute()
    
    # 2. Filas eliminadas
    for index in df_changes.get("deleted_rows", []):
        real_id = st.session_state[f"original_{table_name}"].iloc[index][pk_col]
        supabase.table(table_name).delete().eq(pk_col, real_id).execute()

    # 3. Filas añadidas
    added_rows = df_changes.get("added_rows", [])
    if added_rows:
        supabase.table(table_name).insert(added_rows).execute()
    
    st.cache_data.clear()

# --- LECTURA DE DATOS ---
def load_all_data():
    emp = pd.DataFrame(supabase.table(tablaEmpleados).select("*").execute().data)
    okr = pd.DataFrame(supabase.table(tablaOkrs).select("*").execute().data)
    tar = pd.DataFrame(supabase.table(tablaTareas).select("*").execute().data)
    are = pd.DataFrame(supabase.table(tablaAreas).select("*").execute().data)
    return emp, okr, tar, are

def load_okrs():
    okr = pd.DataFrame(supabase.table(tablaOkrs).select("*").execute().data)
    return okr
def load_areas():
    areas = pd.DataFrame(supabase.table(tablaAreas).select("*").execute().data)
    return areas
def load_empleados():
    emp = pd.DataFrame(supabase.table(tablaEmpleados).select("*").execute().data)
    return emp
def load_tareas():
    tareas = pd.DataFrame(supabase.table(tablaTareas).select("*").execute().data)
    return tareas
# --- GUARDADO INDIVIDUAL (FORMULARIOS) ---
def save_area( new_area_dict):
    try:
        supabase.table(tablaAreas).insert(new_area_dict).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error Supabase: {e}")
        return False

def save_employee(new_user_dict):
    try:
        # Supabase genera el ID automáticamente si usas UUID o Serial
        supabase.table("empleados").insert(new_user_dict).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error Supabase: {e}")
        return False

def save_okr(nuevo_okr_dict):
    try:
        supabase.table(tablaOkrs).insert(nuevo_okr_dict).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error Supabase: {e}")
        return False

def save_tarea(nueva_tarea_dict):
    try:
        supabase.table(tablaTareas).insert(nueva_tarea_dict).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error Supabase: {e}")
        return False

# --- ACTUALIZACIONES Y BORRADOS PUNTUALES ---
def update_okr(id_okr, nuevos_datos):
    try:
        supabase.table(tablaOkrs).update(nuevos_datos).eq("id", id_okr).execute()
        st.cache_data.clear()
        return True
    except Exception:
        return False

def delete_okr(id_okr):
    try:
        supabase.table(tablaOkrs).delete().eq("id", id_okr).execute()
        st.cache_data.clear()
        return True
    except Exception:
        return False

def update_tarea(tarea_id, nuevos_datos):
    try:
        supabase.table(tablaTareas).update(nuevos_datos).eq("id", tarea_id).execute()
        st.cache_data.clear()
        return True
    except Exception:
        return False

def delete_tarea(tarea_id):
    try:
        supabase.table(tablaTareas).delete().eq("id", tarea_id).execute()
        st.cache_data.clear()
        return True
    except Exception:
        return False

# --- FUNCIÓN IA (SE MANTIENE IGUAL PERO USANDO SECRETS) ---
def preguntar_gemini_personalizado(prompt, contexto_okrs, rol_usuario):
    try:
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        instrucciones_sistema = f"""
        Eres un consultor experto en OKRs. Usuario: {rol_usuario}.
        Contexto: {contexto_okrs}.
        Ayuda al usuario a mejorar sus objetivos y tareas de forma estratégica.
        Responde en español con tono profesional.
        """
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=instrucciones_sistema,
                temperature=0.7
            )
        )
        return response.text
    except Exception as e:
        return f"Error técnico en la IA: {str(e)}"