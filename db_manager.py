from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL
from models import Base, Actividad

# Configuración de la base de datos
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Crear tablas si no existen
def inicializar_bd():
    Base.metadata.create_all(engine)

# Insertar datos desde una tabla de pandas
def insertar_actividades_desde_tabla(df_actividades):
    for _, row in df_actividades.iterrows():
        nueva_actividad = Actividad(
            nombre=row['Nombre de Actividad'], 
            unidades=row['Unidades a Producir'], 
            duracion=row['Duración'], 
            predecesoras=row['Predecesoras'], 
            avance_necesario=row['Avance Necesario']
        )
        session.add(nueva_actividad)
    session.commit()

def obtener_actividades():
    return session.query(Actividad).all()

def limpiar_actividades():
    session.query(Actividad).delete()
    session.commit()
