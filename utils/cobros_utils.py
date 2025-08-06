from models import Venta, Cuota, Cobro, session

def actualizar_estado_venta(venta_id):
    venta = session.query(Venta).get(venta_id)
    if not venta:
        return

    cuotas = session.query(Cuota).filter_by(venta_id=venta.id).all()
    pagadas = all(c.pagada for c in cuotas)

    total_cobrado = sum(c.monto for c in session.query(Cobro).filter_by(venta_id=venta.id).all())

    if pagadas or total_cobrado >= venta.ptf:
        venta.finalizada = True
    else:
        venta.finalizada = False

    session.commit()
