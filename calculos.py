import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import io

from datetime import datetime

# Lista de feriados (convertidos a datetime automáticamente)
FERIADOS = {datetime.strptime(date, "%Y-%m-%d").date() for date in [
    "2025-01-01", "2025-04-18", "2025-05-01", "2025-07-28", "2025-07-29", "2025-12-25"
]}

def obtener_fechas_laborales(fecha_inicio, num_dias):
    """Genera una lista de fechas laborales excluyendo sábados, domingos y feriados."""
    fechas = []
    fecha_actual = fecha_inicio.date()  # Convertir a date para evitar errores de tipo

    while len(fechas) < num_dias:
        if fecha_actual.weekday() < 5 and fecha_actual not in FERIADOS:
            fechas.append(datetime.combine(fecha_actual, datetime.min.time()))  # Convertir de nuevo a datetime
        fecha_actual += timedelta(days=1)

    return fechas

def calcular_tiempos_inicio(df_actividades, orden_topologico, matriz_adyacencia):
    """Calcula los tiempos de inicio de las actividades considerando dependencias y avances parciales."""
    
    tiempos_inicio = np.zeros(len(orden_topologico))  # Usa NumPy para mejor rendimiento
    
    
    
    for idx in orden_topologico:
        predecesores = np.where(matriz_adyacencia[:, idx] == 1)[0]
        avances = str(df_actividades.loc[idx, 'Avance Necesario']).split(',')
        avances = [float(a.strip()) if a.strip() else 1.0 for a in avances]  # Limpia y convierte avances
        max_inicio = 0

        for i, predecesor in enumerate(predecesores):
            if i >= len(avances):  # Evita errores de índice si hay menos avances que predecesores
                avance_parcial = 1.0
            else:
                avance_parcial = avances[i]
            
            duracion_predecesor = df_actividades.loc[predecesor, 'Duración']
            if pd.notna(duracion_predecesor) and duracion_predecesor > 0:  # Evita valores NaN o negativos
                inicio_predecesor = tiempos_inicio[predecesor]
                max_inicio = max(max_inicio, inicio_predecesor + avance_parcial * duracion_predecesor)

        tiempos_inicio[idx] = max_inicio  # Asigna el mayor tiempo calculado

    return tiempos_inicio


def generar_matriz_contractual(df_actividades, tiempos_inicio, duracion_total):
    """Genera la matriz contractual basada en los tiempos de inicio y duración de las actividades."""
    
    num_actividades = len(df_actividades)
    C = np.zeros((num_actividades, duracion_total))

    for idx, row in df_actividades.iterrows():
        duracion = int(row['Duración']) if pd.notna(row['Duración']) else 0
        unidades = float(row['Unidades a Producir']) if pd.notna(row['Unidades a Producir']) else 0
        inicio = int(tiempos_inicio[idx])

        if duracion > 0 and unidades > 0:
            produccion_diaria = unidades / duracion
            fin = min(inicio + duracion, duracion_total)  # Evita desbordamiento de matriz
            C[idx, inicio:fin] = produccion_diaria

    return C

def convertir_a_excel(df, df_actividades, fecha_inicio_proyecto):
    """Convierte la matriz contractual en un archivo Excel con fechas laborales y días de la semana."""
    
    # Convertir fecha de inicio a datetime si es necesario
    if isinstance(fecha_inicio_proyecto, datetime):
        fecha_inicio = fecha_inicio_proyecto
    else:
        fecha_inicio = datetime.combine(fecha_inicio_proyecto, datetime.min.time())

    # Obtener solo días laborales
    fechas = obtener_fechas_laborales(fecha_inicio, len(df.columns))

    # Convertir fechas a string (YYYY-MM-DD) y obtener días de la semana
    etiquetas_fechas = [fecha.strftime("%Y-%m-%d") for fecha in fechas]
    etiquetas_dias = [fecha.strftime("%a").capitalize() for fecha in fechas]  # Lun, Mar, Mié...

    # Agregar nombres de actividades como primera columna
    df.insert(0, "Actividad", df_actividades["Nombre de Actividad"])

    # Crear un DataFrame con la fila adicional para los días de la semana
    df_dias = pd.DataFrame([["Día de la semana"] + etiquetas_dias], columns=df.columns)
    
    # Concatenar la fila de días con la matriz original
    df_final = pd.concat([df_dias, df], ignore_index=True)

    # Asignar etiquetas de columnas con fechas laborales
    df_final.columns = ["Actividad"] + etiquetas_fechas

    # Convertir a Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_final.to_excel(writer, sheet_name="Matriz Contractual", index=False)
    processed_data = output.getvalue()

    return processed_data
