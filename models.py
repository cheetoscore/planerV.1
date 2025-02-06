from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Actividad(Base):
    __tablename__ = "actividades"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String, nullable=False)
    unidades = Column(Float, nullable=False)
    duracion = Column(Integer, nullable=False)
    predecesoras = Column(String, nullable=True)
    avance_necesario = Column(String, nullable=True)
