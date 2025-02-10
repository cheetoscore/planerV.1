import sympy as sp
import matplotlib.pyplot as plt
import networkx as nx
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import plotly.graph_objects as go

def mostrar_matriz_latex(nombre, matriz):
    """Muestra una matriz en formato LaTeX."""
    matriz_sym = sp.Matrix(matriz)
    st.latex(f"{nombre} = {sp.latex(matriz_sym)}")

def generar_grafo_ruta_critica(G, duraciones):
    """Genera un grafo mostrando la ruta crítica con pesos (días de duración) de izquierda a derecha."""
    
    # Calcular niveles jerárquicos basados en la distancia desde el nodo inicial (posición izquierda)
    niveles = nx.single_source_shortest_path_length(G, min(G.nodes))
    pos = {nodo: (nivel, -i) for i, (nodo, nivel) in enumerate(niveles.items())}  # Organiza de izquierda a derecha

    plt.figure(figsize=(10, 7))

    # Dibujar todos los nodos y aristas
    nx.draw(G, pos, with_labels=True, node_color='lightblue', node_size=2000, font_size=12, edge_color='black', arrows=True)

    # Agregar pesos a las aristas
    etiquetas = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=etiquetas, font_size=10)

    # Obtener la ruta crítica y resaltarla
    ruta_critica = nx.dag_longest_path(G, weight='weight')
    edges_criticos = [(ruta_critica[i], ruta_critica[i+1]) for i in range(len(ruta_critica)-1)]
    
    # Dibujar la ruta crítica en rojo
    nx.draw_networkx_edges(G, pos, edgelist=edges_criticos, edge_color='red', width=3)

    # Ajustar título y mostrar gráfico
    plt.title("Grafo de Dependencias con Ruta Crítica (Pesos en Días)")
    st.pyplot(plt)

def generar_gantt_plotly(df_actividades, orden_topologico, tiempos_inicio, ruta_critica, matriz_adyacencia, fecha_inicio_proyecto):
    """Genera un diagrama de Gantt interactivo con ruta crítica y flechas de dependencias."""

    # Convertir fecha a datetime.datetime para operaciones con timedelta
    fecha_inicio_proyecto = datetime.combine(fecha_inicio_proyecto, datetime.min.time())

    # Crear datos del Gantt
    data_gantt = []
    for idx in orden_topologico:
        if idx >= len(df_actividades):  # Validar índice
            continue
        
        actividad = df_actividades.iloc[idx]
        inicio_dias = tiempos_inicio[idx]
        duracion = int(actividad['Duración'])
        tipo_actividad = "Ruta Crítica" if idx in ruta_critica else "Normal"

        fecha_inicio = fecha_inicio_proyecto + timedelta(days=inicio_dias)
        fecha_fin = fecha_inicio + timedelta(days=duracion)

        data_gantt.append({
            "ID": actividad['ID Actividad'],
            "Actividad": actividad['Nombre de Actividad'],
            "Inicio": fecha_inicio,
            "Fin": fecha_fin,
            "Tipo": tipo_actividad
        })

    # Crear DataFrame de Gantt ordenado por ID
    df_gantt = pd.DataFrame(data_gantt).sort_values(by="ID")

    # Crear gráfico de Gantt con colores
    fig = px.timeline(
        df_gantt,
        x_start="Inicio", 
        x_end="Fin", 
        y="Actividad", 
        color="Tipo",
        title="Diagrama de Gantt Interactivo con Ruta Crítica",
        labels={"Tipo": "Tipo de Actividad"},
        color_discrete_map={"Ruta Crítica": "red", "Normal": "blue"}
    )

    # Personalizar el gráfico
    fig.update_traces(marker=dict(line=dict(color="black", width=0.5)))
    fig.update_layout(
        xaxis=dict(showgrid=True, gridcolor="LightGrey", tickformat="%d-%b-%Y"),
        yaxis=dict(categoryorder="total ascending")
    )

    # Añadir flechas para dependencias
    for i, j in zip(*matriz_adyacencia.nonzero()):
        if i >= len(df_actividades) or j >= len(df_actividades):
            continue

        inicio_x = fecha_inicio_proyecto + timedelta(days=tiempos_inicio[i] + int(df_actividades.loc[i, 'Duración']))
        fin_x = fecha_inicio_proyecto + timedelta(days=tiempos_inicio[j])
        actividad_i = df_actividades.loc[i, 'Nombre de Actividad']
        actividad_j = df_actividades.loc[j, 'Nombre de Actividad']

        fig.add_trace(go.Scatter(
            x=[inicio_x, fin_x],
            y=[actividad_i, actividad_j],
            mode="lines+markers",
            line=dict(color="black", width=1, dash="dot"),
            showlegend=False
        ))

    # Mostrar gráfico en Streamlit
    st.plotly_chart(fig, use_container_width=True)

    # Mostrar gráfico en Streamlit
    st.plotly_chart(fig, use_container_width=True)
