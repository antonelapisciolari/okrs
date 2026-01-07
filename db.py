import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
class DataManager:
    def __init__(self):
        self.conn = st.connection("gsheets", type=GSheetsConnection)

    def load_all_data(self):
        # Cacheamos para optimizar velocidad
        empleados = self.conn.read(worksheet="empleados")
        okrs = self.conn.read(worksheet="okrs")
        tareas = self.conn.read(worksheet="tareas")
        if not okrs.empty:
            # Forzamos conversión a numérico y luego a Int64 (soporta nulos)
            cols_enteras = ["id", "id_empleado", "año"]
            for col in cols_enteras:
                if col in okrs.columns:
                    okrs[col] = pd.to_numeric(okrs[col], errors='coerce').astype("Int64")
        return empleados, okrs, tareas

    def get_next_user_id(self):
        """Calcula el siguiente ID incremental basado en la tabla de empleados."""
        df = self.conn.read(worksheet="empleados")
        if df.empty or "id" not in df.columns or df["id"].isnull().all():
            return 1
        
        try:
            # Convertimos a numérico por si acaso hay strings, y tomamos el máximo
            ultimo_id = pd.to_numeric(df["id"]).max()
            return int(ultimo_id) + 1
        except Exception:
            # Fallback en caso de datos corruptos en la columna
            return len(df) + 1
        
    def save_employee(self, new_user_dict):
        """
        Recibe un diccionario con los datos del empleado 
        y los persiste en Google Sheets.
        """
        try:
            # Convertimos el diccionario a un DataFrame de una sola fila
            new_user_dict["id"] = self.get_next_user_id()
            
            df_actual = self.conn.read(worksheet="empleados")
            df_new_row = pd.DataFrame([new_user_dict])
            df_updated = pd.concat([df_actual, df_new_row], ignore_index=True)
            
            # Actualizamos la pestaña completa
            self.conn.update(worksheet="empleados", data=df_updated)
            
            # Limpiamos el caché para que la app vea los cambios inmediatamente
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Error al guardar en la base de datos: {e}")
            return False

    def get_next_okr_id(self):
        """Calcula el siguiente ID numérico para la tabla de OKRs."""
        df = self.conn.read(worksheet="okrs")
        
        # Si la tabla está vacía o no tiene la columna id, empezamos en 1
        if df.empty or "id" not in df.columns or df["id"].isnull().all():
            return 1
        
        try:
            # Convertimos a numérico por seguridad y tomamos el máximo
            ultimo_id = pd.to_numeric(df["id"], errors='coerce').max()
            if pd.isna(ultimo_id): return 1
            return int(ultimo_id) + 1
        except:
            return len(df) + 1

    def save_okr(self, nuevo_okr_dict):
        """
        Guarda un nuevo OKR (Organización o Empleado) en el Google Sheet.
        """
        try:
            # 1. Asignamos el ID incremental automáticamente
            nuevo_okr_dict["id"] = self.get_next_okr_id()
            
            # 2. Leemos los datos actuales
            df_actual = self.conn.read(worksheet="okrs")
            
            # 3. Creamos el nuevo registro y lo concatenamos
            df_nuevo = pd.DataFrame([nuevo_okr_dict])
            df_final = pd.concat([df_actual, df_nuevo], ignore_index=True)
            
            # 4. Subimos a Google Sheets
            self.conn.update(worksheet="okrs", data=df_final)
            
            # 5. Limpiamos el caché para que el cambio sea visible inmediatamente
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Error al guardar el OKR: {e}")
            return False
        # src/database.py
    def delete_okr(self, id_okr):
        df = self.conn.read(worksheet="okrs")
        df = df[df["id"] != id_okr]
        self.conn.update(worksheet="okrs", data=df)
        st.cache_data.clear()

    def update_okr(self, id_okr, nuevos_datos):
        df = self.conn.read(worksheet="okrs")
        for key, value in nuevos_datos.items():
            df.loc[df["id"] == id_okr, key] = value
        self.conn.update(worksheet="okrs", data=df)
        st.cache_data.clear()