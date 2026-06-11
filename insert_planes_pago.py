from database import get_session
from models import PlanPago

planes = ["Diario", "Semanal", "Mensual"]

with get_session() as session:
    for nombre in planes:
        existe = session.query(PlanPago).filter_by(nombre=nombre).first()
        if not existe:
            nuevo_plan = PlanPago(nombre=nombre)
            session.add(nuevo_plan)
    session.commit()
print("Planes de pago cargados correctamente.")
