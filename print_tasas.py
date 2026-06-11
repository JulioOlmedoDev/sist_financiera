# print_tasas.py
from database import get_session
from models import Tasa

with get_session() as session:
    for tasa in session.query(Tasa).all():
        print(f"Plan: {tasa.plan} → TEM={tasa.tem}, TNA={tasa.tna}, TEA={tasa.tea}")
