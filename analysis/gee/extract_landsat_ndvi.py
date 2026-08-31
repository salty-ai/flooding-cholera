"""Compute Landsat-8 NDVI for the four pilot LGAs, 2021 wet season,
so the abstract's 'NDVI from Landsat' is literally true. Adds landsat_ndvi_mean."""
import ee, json, csv
PROJECT='project-bf60cdc9-e913-4f05-942'
ee.Initialize(project=PROJECT)
BOUND='/root/flooding-cholera-gee/backend/data/boundaries/nigeria_lgas_774.geojson'
TARGETS={'NG009018':'Yakurr','NG009007':'Biase','NG009010':'Calabar Municipal','NG009005':'Bakassi'}
WET=('2021-06-01','2021-10-31')
g=json.load(open(BOUND)); geoms={}
for f in g['features']:
    pc=f['properties']['adm2_pcode']
    if pc in TARGETS: geoms[pc]=ee.Geometry(f['geometry'])

def landsat_ndvi(aoi,start,end):
    # Landsat 8 Collection 2 L2 surface reflectance; NDVI=(SR_B5-SR_B4)/(SR_B5+SR_B4)
    col=(ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
         .filterBounds(aoi).filterDate(start,end)
         .filter(ee.Filter.lt('CLOUD_COVER',80)))
    n=col.size().getInfo()
    if n==0: return {'n':0,'ndvi':None}
    def prep(img):
        qa=img.select('QA_PIXEL')
        # bits 3 (cloud) and 4 (cloud shadow) must be 0
        mask=qa.bitwiseAnd(1<<3).eq(0).And(qa.bitwiseAnd(1<<4).eq(0))
        nd=img.normalizedDifference(['SR_B5','SR_B4']).rename('NDVI')
        return nd.updateMask(mask)
    ndvi=col.map(prep).mean()
    v=ndvi.reduceRegion(reducer=ee.Reducer.mean(),geometry=aoi,scale=30,
        maxPixels=1e10,bestEffort=True).getInfo()
    return {'n':n,'ndvi':v.get('NDVI')}

res={}
for pc,name in TARGETS.items():
    print(f'[{name}] Landsat-8 NDVI...',flush=True)
    r=landsat_ndvi(geoms[pc],*WET); res[name]=r; print('  ->',r,flush=True)

path='/root/cholera_paper_data/gee_pilot_covariates_2021.csv'
rows=list(csv.DictReader(open(path)))
# insert new column
for row in rows:
    r=res.get(row['LGA'],{})
    row['wet_landsat_ndvi_mean']=r.get('ndvi')
    row['wet_landsat_scenes']=r.get('n')
cols=list(rows[0].keys())
with open(path,'w',newline='') as fp:
    w=csv.DictWriter(fp,fieldnames=cols); w.writeheader(); w.writerows(rows)
print('\nUPDATED',path)
for row in rows:
    print(row['LGA'],'| S2 NDVI',row['wet_ndvi_mean'],'| Landsat NDVI',row['wet_landsat_ndvi_mean'],'| L8 scenes',row['wet_landsat_scenes'])
