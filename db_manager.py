from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from config import DATABASE_URL
from models import Base, Actividad

# Configuración de la base de datos con un pool de conexiones
engine = create_engine(
    DATABASE_URL,
    pool_size=5,            # Máximo de 5 conexiones activas
    max_overflow=10,        # Hasta 10 conexiones adicionales si se requieren
    pool_timeout=30,        # Espera hasta 30 segundos antes de fallar
    pool_recycle=1800       # Recicla conexiones inactivas cada 30 minutos
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def inicializar_bd():
    """Crea las tablas en la base de datos si no existen."""
    Base.metadata.create_all(engine)

def insertar_actividades_desde_tabla(df_actividades):
    """Inserta actividades desde un DataFrame en la base de datos de forma segura."""
    session = SessionLocal()
    try:
        for _, row in df_actividades.iterrows():
            nueva_actividad = Actividad(
                nombre=row['Nombre de Actividad'], 
                unidades=row['Unidades a Producir'], 
                duracion=row['Duración'], 
                predecesoras=row['Predecesoras'], 
                avance_necesario=row['Avance Necesario']
            )
            session.add(nueva_actividad)
        session.commit()  # Confirmar cambios
    except (SQLAlchemyError, OperationalError) as e:
        session.rollback()  # 🔥 Rollback en caso de error
        print(f"Error al insertar actividades: {e}")
    finally:
        session.close()  # ✅ Cerrar sesión al finalizar

def obtener_actividades():
    """Consulta todas las actividades en la base de datos de forma segura."""
    session = SessionLocal()
    try:
        return session.query(Actividad).all()
    except (SQLAlchemyError, OperationalError) as e:
        session.rollback()  # Rollback en caso de error
        print(f"Error en la consulta a la base de datos: {e}")
        return []
    finally:
        session.close()  # ✅ Cerrar sesión después de la consulta

def limpiar_actividades():
    """Elimina todas las actividades en la base de datos."""
    session = SessionLocal()
    try:
        session.query(Actividad).delete()
        session.commit()
    except (SQLAlchemyError, OperationalError) as e:
        session.rollback()  # Rollback en caso de error
        print(f"Error al eliminar actividades: {e}")
    finally:
        session.close()  # ✅ Cerrar sesión
