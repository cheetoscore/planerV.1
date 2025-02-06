import numpy as np

def calcular_tiempos_inicio(df_actividades, orden_topologico, matriz_adyacencia):
    tiempos_inicio = [0] * len(orden_topologico)
    for idx in orden_topologico:
        predecesores = np.where(matriz_adyacencia[:, idx] == 1)[0]
        avances = str(df_actividades.loc[idx, 'Avance Necesario']).split(',')
        max_inicio = 0

        for i, predecesor in enumerate(predecesores):
            avance_parcial = float(avances[i]) if i < len(avances) and avances[i].strip() else 1.0
            duracion_predecesor = int(df_actividades.loc[predecesor, 'Duración'])
            if duracion_predecesor > 0:  # Evita duraciones nulas o incorrectas
                inicio_predecesor = tiempos_inicio[predecesor]
                max_inicio = max(max_inicio, inicio_predecesor + avance_parcial * duracion_predecesor)

        tiempos_inicio[idx] = max_inicio
    return tiempos_inicio

def generar_matriz_contractual(df_actividades, tiempos_inicio, duracion_total):
    num_actividades = df_actividades.shape[0]
    C = np.zeros((num_actividades, duracion_total))
    for idx, row in df_actividades.iterrows():
        duracion = int(row['Duración'])
        unidades = float(row['Unidades a Producir'])
        inicio = int(tiempos_inicio[idx])
        if duracion > 0 and unidades > 0:  # Verificar valores válidos
            produccion_diaria = unidades / duracion
            C[idx, inicio:inicio+duracion] = produccion_diaria
    return C
