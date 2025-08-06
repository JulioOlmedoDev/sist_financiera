from sqlalchemy import create_engine, Column, Integer, String, Date, Text, ForeignKey, Enum, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from dotenv import load_dotenv

import os

load_dotenv()

Base = declarative_base()

# Conexion a la base de datos
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine)
session = Session()

# --- MODELOS ---

class Rol(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), unique=True, nullable=False)

class Permiso(Base):
    __tablename__ = 'permisos'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), unique=True, nullable=False)

class UsuarioPermiso(Base):
    __tablename__ = 'usuario_permisos'
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'))
    permiso_id = Column(Integer, ForeignKey('permisos.id'))

class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    rol_id = Column(Integer, ForeignKey('roles.id'))
    personal_id = Column(Integer, ForeignKey('personal.id'))
    activo = Column(Boolean, default=True)  # ✅ NUEVO

    rol = relationship("Rol")
    permisos = relationship("Permiso", secondary="usuario_permisos")
    personal = relationship("Personal", uselist=False)


class Cliente(Base):
    __tablename__ = 'clientes'
    id = Column(Integer, primary_key=True)
    apellidos = Column(String(100))
    nombres = Column(String(100))
    dni = Column(String(20), unique=True)
    fecha_nacimiento = Column(Date)
    ocupacion = Column(String(100))
    domicilio_personal = Column(String(255))
    localidad = Column(String(100))
    provincia = Column(String(100))
    lugar_trabajo_nombre = Column(String(100))
    domicilio_laboral = Column(String(255))
    sexo = Column(String(20))
    estado_civil = Column(String(50))
    celular_personal = Column(String(50))
    celular_trabajo = Column(String(50))
    email = Column(String(100))
    calificacion = Column(String(20))
    descripcion = Column(Text)

class Garante(Base):
    __tablename__ = 'garantes'
    id = Column(Integer, primary_key=True)
    apellidos = Column(String(100))
    nombres = Column(String(100))
    dni = Column(String(20), unique=True)
    fecha_nacimiento = Column(Date)
    ocupacion = Column(String(100))
    domicilio_personal = Column(String(255))
    localidad = Column(String(100))
    provincia = Column(String(100))
    lugar_trabajo_nombre = Column(String(100))
    domicilio_laboral = Column(String(255))
    sexo = Column(String(20))
    estado_civil = Column(String(50))
    celular_personal = Column(String(50))
    celular_trabajo = Column(String(50))
    email = Column(String(100))
    calificacion = Column(Integer)
    descripcion = Column(Text)

class Categoria(Base):
    __tablename__ = 'categorias'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)

class Producto(Base):
    __tablename__ = 'productos'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    categoria_id = Column(Integer, ForeignKey('categorias.id'))
    categoria = relationship("Categoria")

class Personal(Base):
    __tablename__ = 'personal'
    id = Column(Integer, primary_key=True)
    apellidos = Column(String(100))
    nombres = Column(String(100))
    dni = Column(String(20), unique=True)
    fecha_nacimiento = Column(Date)
    domicilio_personal = Column(String(255))
    localidad = Column(String(100))
    provincia = Column(String(100))
    sexo = Column(String(20))
    estado_civil = Column(String(50))
    celular_personal = Column(String(50))
    celular_alternativo = Column(String(50))
    email = Column(String(100))
    cuil = Column(String(20))
    fecha_ingreso = Column(Date)
    tipo = Column(String(50))  # Coordinador, Vendedor, Cobrador

class Venta(Base):
    __tablename__ = 'ventas'
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey('clientes.id'))
    garante_id = Column(Integer, ForeignKey('garantes.id'))
    producto_id = Column(Integer, ForeignKey('productos.id'))
    coordinador_id = Column(Integer, ForeignKey('personal.id'))
    vendedor_id = Column(Integer, ForeignKey('personal.id'))
    cobrador_id = Column(Integer, ForeignKey('personal.id'))
    fecha = Column(Date)
    fecha_inicio_pago = Column(Date)
    monto = Column(Float)
    num_cuotas = Column(Integer)
    valor_cuota = Column(Float)
    ptf = Column(Float)
    interes = Column(Float)
    tem = Column(Float)
    tna = Column(Float)
    tea = Column(Float)
    descripcion = Column(Text)
    domicilio_cobro_preferido = Column(String(20))
    anulada = Column(Boolean, default=False)
    finalizada = Column(Boolean, default=False)

    plan_pago = Column(
        Enum('diaria','semanal','mensual', name='plan_pago_enum'),
        nullable=False,
        default='mensual'
    )

    cliente = relationship("Cliente")
    garante = relationship("Garante")
    producto = relationship("Producto")
    coordinador = relationship("Personal", foreign_keys=[coordinador_id])
    vendedor = relationship("Personal", foreign_keys=[vendedor_id])
    cobrador = relationship("Personal", foreign_keys=[cobrador_id])
    cuotas = relationship("Cuota", back_populates="venta", cascade="all, delete-orphan")
    cobros = relationship("Cobro", back_populates="venta", cascade="all, delete-orphan")

class Cuota(Base):
    __tablename__ = 'cuotas'
    id = Column(Integer, primary_key=True)
    venta_id = Column(Integer, ForeignKey('ventas.id'))
    numero = Column(Integer)
    fecha_vencimiento = Column(Date)
    monto_original = Column(Float)
    monto_pagado = Column(Float, default=0.0)
    pagada = Column(Boolean, default=False)
    vencida = Column(Boolean, default=False)
    interes_mora = Column(Float, default=0.0)
    refinanciada = Column(Boolean, default=False)
    
    fecha_pago = Column(Date, nullable=True)  # ✅ NUEVO
    concepto = Column(String(50), default="CUOTA")  # ✅ NUEVO

    venta = relationship("Venta", back_populates="cuotas")


class Cobro(Base):
    __tablename__ = 'cobros'
    id = Column(Integer, primary_key=True)
    venta_id = Column(Integer, ForeignKey('ventas.id'))
    fecha = Column(Date)
    monto = Column(Float)
    tipo = Column(String(20))
    observaciones = Column(Text)
    cuota_id = Column(Integer, ForeignKey('cuotas.id'), nullable=True)

    venta = relationship("Venta", back_populates="cobros")
    cuota = relationship("Cuota", backref="cobros_aplicados", lazy="joined")

class Tasa(Base):
    __tablename__ = "tasas"
    id  = Column(Integer, primary_key=True)
    plan = Column(String(20), unique=True, nullable=False)  # "mensual", "semanal", "diaria"
    tem  = Column(Float, nullable=False)
    tna  = Column(Float, nullable=False)
    tea  = Column(Float, nullable=False)

# Crear todas las tablas
if __name__ == "__main__":
    Base.metadata.create_all(engine)
    print("Base de datos y tablas creadas correctamente.")
