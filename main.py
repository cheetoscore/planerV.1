import streamlit as st
from datetime import datetime
import pandas as pd
import networkx as nx
from db_manager import (
    inicializar_bd, insertar_actividades_desde_tabla, obtener_actividades, limpiar_actividades,
    insertar_restricciones_desde_tabla, obtener_restricciones, limpiar_restricciones
)
from adyacencia import generar_matriz_adyacencia, calcular_orden_topologico
from calculos import (
    calcular_tiempos_inicio, generar_matriz_contractual, convertir_a_excel, 
    generar_matriz_restricciones, generar_matriz_contractual_ajustada, 
    calcular_tiempos_inicio_ajustados, generar_matriz_adyacencia_ajustada, calcular_ruta_critica_ajustada
)
from visualizacion import mostrar_matriz_latex, generar_grafo_ruta_critica, generar_gantt_plotly

# Inicializar la base de datos
inicializar_bd()

def cargar_restricciones_bd():
    """Carga las restricciones desde la base de datos y las convierte en DataFrame."""
    restricciones = obtener_restricciones()  # 🔹 Aquí realmente consultamos la BD
    if restricciones:
        return pd.DataFrame([{
            'ID Restricción': res.id,
            'Nombre de Actividad': res.nombre_actividad,
            'Restricción Tipo': res.tipo_restriccion,
            'Fecha de Inicio': res.fecha_inicio,
            'Fecha de Fin': res.fecha_fin,
            '%Parcial': res.porcentaje_parcial,
            'Estado': res.estado
        } for res in restricciones])
    return pd.DataFrame(columns=['ID Restricción', 'Nombre de Actividad', 'Restricción Tipo',
                                 'Fecha de Inicio', 'Fecha de Fin', '%Parcial', 'Estado'])

def cargar_datos_bd():
    """Carga los datos desde la base de datos y los convierte en DataFrame."""
    actividades = obtener_actividades()  # Se usa aquí
    if actividades:
        return pd.DataFrame([{
            'ID Actividad': act.id,
            'Nombre de Actividad': act.nombre,
            'Unidades a Producir': act.unidades,
            'Duración': act.duracion,
            'Predecesoras': act.predecesoras,
            'Avance Necesario': act.avance_necesario
        } for act in actividades])
    return pd.DataFrame(columns=['ID Actividad', 'Nombre de Actividad', 'Unidades a Producir',
                                 'Duración', 'Predecesoras', 'Avance Necesario'])

# Agregar selector de fecha en la interfaz
fecha_inicio_proyecto = st.date_input("Selecciona la fecha de inicio del proyecto:", value=datetime.today())
fecha_inicio_proyecto = datetime.combine(fecha_inicio_proyecto, datetime.min.time())

# 📌 FUNCIÓN PRINCIPAL
def main():
    st.title("Gestión de Proyectos: Matriz Contractual, Ruta Crítica y Gantt")

    # Cargar actividades y restricciones desde la BD
    df_actividades = cargar_datos_bd()
    df_restricciones = cargar_restricciones_bd()

    # 📌 SECCIÓN DE ACTIVIDADES
    st.subheader("Actividades del Proyecto")
    df_actividades = st.data_editor(df_actividades, num_rows="dynamic", key="tabla_actividades")

    if st.button("Guardar Actividades en la Base de Datos"):
        if df_actividades['Nombre de Actividad'].str.strip().eq("").any():
            st.error("Error: Hay actividades sin nombre.")
        elif (df_actividades['Duración'] <= 0).any():
            st.error("Error: Todas las actividades deben tener duración mayor a cero.")
        else:
            limpiar_actividades()
            insertar_actividades_desde_tabla(df_actividades)
            st.success("Actividades guardadas correctamente.")
            st.experimental_rerun()

    # 📌 PROCESAMIENTO DE MATRICES
    if not df_actividades.empty:
        try:
            # Matriz de Adyacencia
            matriz_adyacencia = generar_matriz_adyacencia(df_actividades)
            st.subheader("Matriz de Adyacencia")
            mostrar_matriz_latex("A", matriz_adyacencia)

            # Orden Topológico
            orden_topologico, G = calcular_orden_topologico(matriz_adyacencia, df_actividades)
            st.write(f"Orden de Ejecución: {orden_topologico}")

            # Tiempos de Inicio
            tiempos_inicio = calcular_tiempos_inicio(df_actividades, orden_topologico, matriz_adyacencia)
            mostrar_matriz_latex("T_i", tiempos_inicio)

            # Ruta Crítica
            for u, v in G.edges():
                G[u][v]['weight'] = int(df_actividades.loc[u, 'Duración'])
            ruta_critica = nx.dag_longest_path(G, weight='weight')

            duracion_total = sum(int(df_actividades.loc[act, 'Duración']) for act in ruta_critica)
            st.write(f"Ruta Crítica: {ruta_critica}")
            st.write(f"Duración Total del Proyecto: **{duracion_total} días**")

            # Matriz C
            matriz_C = generar_matriz_contractual(df_actividades, tiempos_inicio, duracion_total)
            mostrar_matriz_latex("C", matriz_C)

            # Matriz R
            matriz_R = generar_matriz_restricciones(df_actividades, df_restricciones, fecha_inicio_proyecto, duracion_total)
            mostrar_matriz_latex("R", matriz_R)

            # Tiempos de Inicio Ajustados
            tiempos_inicio_ajustados = calcular_tiempos_inicio_ajustados(
                df_actividades, orden_topologico, matriz_adyacencia, matriz_R, fecha_inicio_proyecto, duracion_total
            )
            mostrar_matriz_latex("T_i'", tiempos_inicio_ajustados)

            # Matriz A Ajustada
            matriz_A_ajustada = generar_matriz_adyacencia_ajustada(df_actividades, tiempos_inicio_ajustados)
            mostrar_matriz_latex("A'", matriz_A_ajustada)

            # Ruta Crítica Ajustada
            ruta_critica_ajustada, duracion_total_ajustada = calcular_ruta_critica_ajustada(matriz_A_ajustada, df_actividades, tiempos_inicio_ajustados)

            if ruta_critica_ajustada is None or duracion_total_ajustada is None:
                st.warning("⚠️ No se pudo calcular la ruta crítica ajustada. Verifica los datos de entrada.")
            else:
                st.write(f"Ruta Crítica Ajustada: {ruta_critica_ajustada}")
                st.write(f"Duración Total del Proyecto Ajustada: **{duracion_total_ajustada} días**")               

            # Matriz C Ajustada
            matriz_C_ajustada = generar_matriz_contractual_ajustada(
                 df_actividades, matriz_C, matriz_R, matriz_adyacencia, tiempos_inicio_ajustados, duracion_total
            )
            st.subheader("Matriz Contractual Ajustada \( C' \)")
            mostrar_matriz_latex("C'", matriz_C_ajustada)

            # Descarga en Excel
            st.download_button(
                label="📥 Descargar Todas las Matrices en Excel",
                data=convertir_a_excel(pd.DataFrame(matriz_C), pd.DataFrame(matriz_C_ajustada), pd.DataFrame(matriz_R), df_actividades, fecha_inicio_proyecto),
                file_name="matrices_restricciones.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # Visualizaciones
            generar_grafo_ruta_critica(G, duraciones=df_actividades['Duración'].tolist())
            generar_gantt_plotly(df_actividades, orden_topologico, tiempos_inicio, ruta_critica, matriz_adyacencia, fecha_inicio_proyecto)

        except Exception as e:
            st.error(f"Error en los cálculos: {str(e)}")
            
    # 📌 SECCIÓN DE RESTRICCIONES
    st.subheader("Restricciones del Proyecto")
    df_restricciones = st.data_editor(df_restricciones, num_rows="dynamic", key="tabla_restricciones")

    if st.button("Guardar Restricciones en la Base de Datos"):
        limpiar_restricciones()
        insertar_restricciones_desde_tabla(df_restricciones)
        st.success("Restricciones guardadas correctamente.")
        st.experimental_rerun()
        
# 📌 EJECUCIÓN DEL PROGRAMA
if __name__ == "__main__":
    main()
