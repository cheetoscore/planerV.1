import numpy as np
import networkx as nx

def generar_matriz_adyacencia(df_actividades):
    num_actividades = df_actividades.shape[0]
    matriz_adyacencia = np.zeros((num_actividades, num_actividades), dtype=int)
    for idx, row in df_actividades.iterrows():
        predecesores = str(row['Predecesoras']).strip()
        if predecesores and predecesores != 'nan':
            for predecesor in predecesores.split(','):
                if predecesor.isdigit():
                    matriz_adyacencia[int(predecesor)-1, idx] = 1
    return matriz_adyacencia

def calcular_orden_topologico(matriz_adyacencia, df_actividades):
    G = nx.DiGraph()
    num_actividades = len(df_actividades)

    for i in range(num_actividades):
        for j in range(num_actividades):
            if matriz_adyacencia[i, j] == 1:  # Agregar dependencia
                G.add_edge(i, j)

    try:
        ciclo = list(nx.find_cycle(G, orientation="original"))
        if ciclo:
            ciclo_str = " -> ".join([f"A{n[0]+1}" for n in ciclo]) + f" -> A{ciclo[0][0]+1}"
            raise nx.NetworkXUnfeasible(f"Se detectó un ciclo: {ciclo_str}")
    except nx.NetworkXNoCycle:
        # Devuelve solo los índices válidos
        orden = [idx for idx in list(nx.topological_sort(G)) if idx < len(df_actividades)]
        return orden, G

    return [], None