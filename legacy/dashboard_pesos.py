import streamlit as st
import json
import os

# -----------------------------
# 1. Cargar archivo de pesos
# -----------------------------
PESOS_FILE = "pesos.json"

if not os.path.exists(PESOS_FILE):
    st.error("No se encontró pesos.json. Crea el archivo antes de usar el dashboard.")
    st.stop()

with open(PESOS_FILE, "r", encoding="utf-8") as f:
    pesos = json.load(f)

st.title("Editor de Pesos por Estado y Municipio")
st.write("Modifica los pesos sin tocar Excel ni código.")

# -----------------------------
# 2. Selección de Estado
# -----------------------------
estados = list(pesos.keys())
estado = st.selectbox("Estado", estados)

# -----------------------------
# 3. Selección de Municipio
# -----------------------------
municipios = list(pesos[estado].keys())
municipio = st.selectbox("Municipio", municipios)

# -----------------------------
# 4. Mostrar peso actual
# -----------------------------
peso_actual = pesos[estado][municipio]
st.write(f"**Peso actual:** {peso_actual}")

# -----------------------------
# 5. Campo para nuevo peso
# -----------------------------
nuevo_peso = st.text_input("Nuevo peso", value=str(peso_actual))

# -----------------------------
# 6. Guardar cambios
# -----------------------------
if st.button("Guardar cambios"):
    try:
        valor = float(nuevo_peso)
        pesos[estado][municipio] = valor

        with open(PESOS_FILE, "w", encoding="utf-8") as f:
            json.dump(pesos, f, indent=4, ensure_ascii=False)

        st.success("Peso actualizado correctamente.")
    except ValueError:
        st.error("El valor ingresado no es un número válido.")
