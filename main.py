import streamlit as st
import pandas as pd
import networkx as nx
from db_manager import (
    inicializar_bd, insertar_actividades_desde_tabla, obtener_actividades, limpiar_actividades
)
from adyacencia import generar_matriz_adyacencia, calcular_orden_topologico
from calculos import calcular_tiempos_inicio, generar_matriz_contractual
from visualizacion import mostrar_matriz_latex, generar_grafo_ruta_critica, generar_gantt_plotly

# Inicializar la base de datos
inicializar_bd()

def cargar_datos_bd():
    """Carga los datos desde la base de datos y los convierte en DataFrame."""
    actividades = obtener_actividades()
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

def main():
    st.title("Gestión de Proyectos: Matriz Contractual, Ruta Crítica y Gantt")

    # Cargar datos desde la base de datos
    df_actividades = cargar_datos_bd()

    # Configurar la tabla de entrada
    num_actividades = st.number_input("Número de Actividades:", min_value=1, max_value=20, step=1, value=len(df_actividades) or 4)

    # Crear tabla editable si no hay datos cargados
    if df_actividades.empty:
        df_actividades = pd.DataFrame({
            'ID Actividad': list(range(1, num_actividades + 1)),
            'Nombre de Actividad': ["" for _ in range(num_actividades)],
            'Unidades a Producir': [0 for _ in range(num_actividades)],
            'Duración': [0 for _ in range(num_actividades)],
            'Predecesoras': ["" for _ in range(num_actividades)],
            'Avance Necesario': ["" for _ in range(num_actividades)]
        })

    # Mostrar y permitir edición de la tabla
    st.subheader("Actividades del Proyecto")
    df_actividades = st.data_editor(df_actividades, num_rows="dynamic", key="tabla_actividades")

    # Botón para sincronizar los datos con la base de datos
    if st.button("Guardar Actividades en la Base de Datos"):
        if df_actividades['Nombre de Actividad'].str.strip().eq("").any():
            st.error("Error: Hay actividades sin nombre. Completa todas las actividades.")
        elif (df_actividades['Duración'] <= 0).any():
            st.error("Error: Todas las actividades deben tener una duración mayor a cero.")
        else:
            limpiar_actividades()  # Eliminar datos previos
            insertar_actividades_desde_tabla(df_actividades)
            st.success("Datos sincronizados correctamente con la base de datos.")
            st.experimental_rerun()  # Recargar la aplicación para mostrar los datos actualizados

    # Validar y procesar datos si existen
    if not df_actividades.empty:
        try:
            # Generar matriz de adyacencia
            matriz_adyacencia = generar_matriz_adyacencia(df_actividades)
            st.subheader("Matriz de Adyacencia")
            mostrar_matriz_latex("A", matriz_adyacencia)

            # Calcular orden topológico
            orden_topologico, G = calcular_orden_topologico(matriz_adyacencia, df_actividades)
            st.write(f"Orden de Ejecución: {orden_topologico}")

            # Calcular tiempos de inicio
            tiempos_inicio = calcular_tiempos_inicio(df_actividades, orden_topologico, matriz_adyacencia)
            st.subheader("Tiempos de Inicio")
            mostrar_matriz_latex("T_i", tiempos_inicio)

            # Calcular ruta crítica
            for u, v in G.edges():
                G[u][v]['weight'] = int(df_actividades.loc[u, 'Duración'])
            ruta_critica = nx.dag_longest_path(G, weight='weight')

            duracion_total = sum(int(df_actividades.loc[act, 'Duración']) for act in ruta_critica)
            st.write(f"Ruta Crítica: {ruta_critica}")
            st.write(f"Duración Total del Proyecto: **{duracion_total} días**")

            # Generar y mostrar matriz C
            matriz_C = generar_matriz_contractual(df_actividades, tiempos_inicio, duracion_total)
            st.subheader("Matriz Contractual \( C \):")
            mostrar_matriz_latex("C", matriz_C)

            # Visualizaciones
            st.subheader("Grafo de Dependencias con Ruta Crítica:")
            generar_grafo_ruta_critica(G, duraciones=df_actividades['Duración'].tolist())

            st.subheader("Diagrama de Gantt Interactivo con Ruta Crítica:")
            generar_gantt_plotly(df_actividades, orden_topologico, tiempos_inicio, ruta_critica, matriz_adyacencia)

        except Exception as e:
            st.error(f"Error en los cálculos: {str(e)}")

    # Botón para limpiar actividades en la base de datos
    if st.button("Limpiar Actividades"):
        limpiar_actividades()
        st.success("Actividades eliminadas.")
        st.experimental_rerun()

if __name__ == "__main__":
    main()
