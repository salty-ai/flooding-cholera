import os, sys
sys.path.insert(0,'.')
os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS','/home/debian/cholera-app/backend/adc.json')
from app.database import SessionLocal
from app.models import LGA
from app.services.earth_engine import EarthEngineService
db=SessionLocal()
lga=db.query(LGA).filter(LGA.name=='Yakurr').first()
print('LGA:', lga.name if lga else None, '| has geom:', lga is not None)
svc=EarthEngineService()
print('auth:', svc.authenticate())
# get geometry as geojson
from app.services import earth_engine as ee_mod
import json
# fetch flood index for 2021 window
from datetime import date
try:
    geom=None
    # try common accessors
    if hasattr(lga,'geometry_geojson') and lga.geometry_geojson:
        geom=lga.geometry_geojson
    else:
        # pull via PostGIS
        from sqlalchemy import text
        row=db.execute(text("SELECT ST_AsGeoJSON(geometry) FROM lgas WHERE id=:i"),{'i':lga.id}).first()
        geom=json.loads(row[0]) if row and row[0] else None
    print('geom type:', geom.get('type') if geom else None)
    res=svc.get_flood_index(geom, date(2021,8,1), date(2021,9,30))
    print('FLOOD INDEX RESULT:', res)
except Exception as e:
    import traceback; traceback.print_exc()
