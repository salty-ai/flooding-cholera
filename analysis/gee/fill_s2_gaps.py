"""Fill S2 gaps for the two cloudy coastal LGAs (Calabar Municipal, Bakassi).
Relax cloud filter to 80% and widen to full-year 2021 to guarantee scenes,
using a per-pixel cloud mask (SCL) so NDWI/NDVI stay valid."""
import ee, json, csv, datetime
PROJECT='project-bf60cdc9-e913-4f05-942'
ee.Initialize(project=PROJECT)
BOUND='/root/flooding-cholera-gee/backend/data/boundaries/nigeria_lgas_774.geojson'
TARGETS={'NG009010':'Calabar Municipal','NG009005':'Bakassi'}
WET=('2021-06-01','2021-10-31')
g=json.load(open(BOUND)); geoms={}
for f in g['features']:
    pc=f['properties']['adm2_pcode']
    if pc in TARGETS: geoms[pc]=ee.Geometry(f['geometry'])

def masked_indices(aoi,start,end,cloud=80):
    s2=(ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(aoi).filterDate(start,end)
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',cloud)))
    n=s2.size().getInfo()
    if n==0: return {'n':0}
    def prep(img):
        scl=img.select('SCL')
        # keep vegetation(4),bare(5),water(6),unclassified(7); drop clouds/shadow/snow
        good=scl.remap([4,5,6,7],[1,1,1,1],0)
        ndwi=img.normalizedDifference(['B3','B8']).rename('NDWI')
        ndvi=img.normalizedDifference(['B8','B4']).rename('NDVI')
        return img.addBands([ndwi,ndvi]).updateMask(good)
    coll=s2.map(prep)
    ndwi=coll.select('NDWI').mean(); ndvi=coll.select('NDVI').mean()
    st=ndwi.addBands(ndvi).reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.max(),sharedInputs=True),
        geometry=aoi,scale=20,maxPixels=1e10,bestEffort=True).getInfo()
    water=ndwi.gt(0.3).reduceRegion(reducer=ee.Reducer.mean(),geometry=aoi,
        scale=20,maxPixels=1e10,bestEffort=True).getInfo()
    return {'n':n,'ndwi_mean':st.get('NDWI_mean'),'ndwi_max':st.get('NDWI_max'),
            'ndvi_mean':st.get('NDVI_mean'),'water_pct':(water.get('NDWI') or 0)*100}

res={}
for pc,name in TARGETS.items():
    print(f'[{name}] masked S2 (cloud<80%, SCL mask)...',flush=True)
    r=masked_indices(geoms[pc],*WET)
    res[name]=r; print('  ->',r,flush=True)

# merge into existing CSV
path='/root/cholera_paper_data/gee_pilot_covariates_2021.csv'
rows=list(csv.DictReader(open(path)))
for row in rows:
    if row['LGA'] in res and res[row['LGA']].get('n',0)>0:
        r=res[row['LGA']]
        row['wet_ndwi_mean']=r['ndwi_mean']; row['wet_ndwi_max']=r['ndwi_max']
        row['wet_ndvi_mean']=r['ndvi_mean']; row['wet_water_pct']=r['water_pct']
        row['wet_s2_images']=r['n']
        if row['wet_ndwi_mean'] and row['dry_ndwi_mean']:
            row['ndwi_anomaly']=float(row['wet_ndwi_mean'])-float(row['dry_ndwi_mean'])
        row['provenance']=row['provenance']+' | coastal S2 gap-filled: cloud<80% + SCL per-pixel mask'
with open(path,'w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
print('\nUPDATED',path)
for row in rows:
    print(row['LGA'],'| NDWI',row['wet_ndwi_mean'],'| NDVI',row['wet_ndvi_mean'],
          '| precip_mm',row['wet_precip_total_mm'],'| imgs',row['wet_s2_images'])
