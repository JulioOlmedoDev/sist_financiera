# print_tasas.py
from database import session
from models import Tasa

for tasa in session.query(Tasa).all():
    print(f"Plan: {tasa.plan} → TEM={tasa.tem}, TNA={tasa.tna}, TEA={tasa.tea}")
