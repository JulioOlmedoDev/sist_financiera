from database import session
from models import PlanPago

# Planes por defecto
planes = ["Diario", "Semanal", "Mensual"]

for nombre in planes:
    existe = session.query(PlanPago).filter_by(nombre=nombre).first()
    if not existe:
        nuevo_plan = PlanPago(nombre=nombre)
        session.add(nuevo_plan)

session.commit()
print("Planes de pago cargados correctamente.")
