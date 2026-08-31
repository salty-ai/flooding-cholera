"""
Real GEE covariate extraction for the four Cross River sentinel-pilot LGAs.
Computes per-LGA Sentinel-2 NDWI, Sentinel-2 NDVI, and GPM-IMERG precipitation
for the 2021 cholera-season window, plus a 2021 dry-season baseline for anomaly context.
Outputs a frozen CSV with provenance columns.
"""
import ee, json, csv, datetime

PROJECT = 'project-bf60cdc9-e913-4f05-942'
ee.Initialize(project=PROJECT)

BOUND = '/root/flooding-cholera-gee/backend/data/boundaries/nigeria_lgas_774.geojson'
PILOT_PCODES = {
    'NG009018': 'Yakurr',
    'NG009007': 'Biase',
    'NG009010': 'Calabar Municipal',
    'NG009005': 'Bakassi',
}

# Windows (2021). Wet/outbreak season vs dry baseline for anomaly.
WET = ('2021-06-01', '2021-10-31')   # peak rains -> flood/cholera season
DRY = ('2021-01-01', '2021-03-31')   # dry-season baseline

g = json.load(open(BOUND))
geoms = {}
for f in g['features']:
    pc = f['properties']['adm2_pcode']
    if pc in PILOT_PCODES:
        geoms[pc] = ee.Geometry(f['geometry'])

def s2_indices(aoi, start, end):
    s2 = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
          .filterBounds(aoi).filterDate(start, end)
          .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 40)))
    n = s2.size().getInfo()
    if n == 0:
        return {'n_images': 0, 'ndwi_mean': None, 'ndwi_max': None,
                'water_pct_ndwi_gt_0_3': None, 'ndvi_mean': None}
    def add(img):
        ndwi = img.normalizedDifference(['B3', 'B8']).rename('NDWI')
        ndvi = img.normalizedDifference(['B8', 'B4']).rename('NDVI')
        return img.addBands([ndwi, ndvi])
    coll = s2.map(add)
    ndwi = coll.select('NDWI').mean()
    ndvi = coll.select('NDVI').mean()
    stats = ndwi.addBands(ndvi).reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.max(), sharedInputs=True),
        geometry=aoi, scale=20, maxPixels=1e10, bestEffort=True).getInfo()
    water = ndwi.gt(0.3).reduceRegion(
        reducer=ee.Reducer.mean(), geometry=aoi, scale=20,
        maxPixels=1e10, bestEffort=True).getInfo()
    return {
        'n_images': n,
        'ndwi_mean': stats.get('NDWI_mean'),
        'ndwi_max': stats.get('NDWI_max'),
        'water_pct_ndwi_gt_0_3': (water.get('NDWI') or 0) * 100,
        'ndvi_mean': stats.get('NDVI_mean'),
    }

def imerg_precip(aoi, start, end):
    # GPM IMERG v07 half-hourly precipitationCal (mm/hr). Sum -> total mm over window.
    coll = (ee.ImageCollection('NASA/GPM_L3/IMERG_V07')
            .filterBounds(aoi).filterDate(start, end).select('precipitation'))
    n = coll.size().getInfo()
    if n == 0:
        return {'imerg_slices': 0, 'precip_total_mm': None, 'precip_mean_mm_per_day': None}
    # each slice is mm/hr over 0.5h -> multiply by 0.5 to get mm, then sum
    total_mm = coll.map(lambda i: i.multiply(0.5)).sum()
    val = total_mm.reduceRegion(reducer=ee.Reducer.mean(), geometry=aoi,
                                scale=11132, maxPixels=1e10, bestEffort=True).getInfo()
    tot = val.get('precipitation')
    days = (datetime.date.fromisoformat(end) - datetime.date.fromisoformat(start)).days or 1
    return {'imerg_slices': n, 'precip_total_mm': tot,
            'precip_mean_mm_per_day': (tot/days if tot is not None else None)}

rows = []
for pc, name in PILOT_PCODES.items():
    aoi = geoms[pc]
    print(f'[{name}] wet-season S2...', flush=True)
    wet_s2 = s2_indices(aoi, *WET)
    print(f'[{name}] dry-season S2...', flush=True)
    dry_s2 = s2_indices(aoi, *DRY)
    print(f'[{name}] IMERG precip...', flush=True)
    wet_p = imerg_precip(aoi, *WET)
    dry_p = imerg_precip(aoi, *DRY)
    row = {
        'LGA': name, 'pcode': pc, 'state': 'Cross River',
        'wet_window': f'{WET[0]}..{WET[1]}', 'dry_window': f'{DRY[0]}..{DRY[1]}',
        # wet season
        'wet_ndwi_mean': wet_s2['ndwi_mean'], 'wet_ndwi_max': wet_s2['ndwi_max'],
        'wet_water_pct': wet_s2['water_pct_ndwi_gt_0_3'],
        'wet_ndvi_mean': wet_s2['ndvi_mean'], 'wet_s2_images': wet_s2['n_images'],
        'wet_precip_total_mm': wet_p['precip_total_mm'],
        'wet_precip_mm_per_day': wet_p['precip_mean_mm_per_day'],
        # dry baseline
        'dry_ndwi_mean': dry_s2['ndwi_mean'], 'dry_ndvi_mean': dry_s2['ndvi_mean'],
        'dry_water_pct': dry_s2['water_pct_ndwi_gt_0_3'],
        'dry_precip_total_mm': dry_p['precip_total_mm'],
        'dry_precip_mm_per_day': dry_p['precip_mean_mm_per_day'],
        'provenance': 'GEE: COPERNICUS/S2_SR_HARMONIZED (NDWI B3/B8, NDVI B8/B4, cloud<40%, 20m); NASA/GPM_L3/IMERG_V07 precipitationCal; GRID3 Admin-2 geometry',
        'computed_utc': datetime.datetime.utcnow().isoformat()+'Z',
        'ee_project': PROJECT,
    }
    # anomalies
    def anom(w, d):
        return (w - d) if (w is not None and d is not None) else None
    row['ndwi_anomaly'] = anom(row['wet_ndwi_mean'], row['dry_ndwi_mean'])
    row['precip_anomaly_mm'] = anom(row['wet_precip_total_mm'], row['dry_precip_total_mm'])
    rows.append(row)
    print(f'  -> NDWI(wet)={row["wet_ndwi_mean"]}, NDVI(wet)={row["wet_ndvi_mean"]}, '
          f'precip(wet)={row["wet_precip_total_mm"]} mm, imgs={row["wet_s2_images"]}', flush=True)

out = '/root/cholera_paper_data/gee_pilot_covariates_2021.csv'
cols = list(rows[0].keys())
with open(out, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)
print('\nSAVED', out)
for r in rows:
    print(r['LGA'], '| NDWI', r['wet_ndwi_mean'], '| NDVI', r['wet_ndvi_mean'],
          '| precip_mm', r['wet_precip_total_mm'], '| water%', r['wet_water_pct'])
