# -*- coding: utf-8 -*-
"""Hand-authored SVG diagrams -> PNG. Flat grayscale journal style. Three DISTINCT layouts."""
import cairosvg, os
OUT="/root/paper_figures_gen"; os.makedirs(OUT, exist_ok=True)

FONT="Helvetica, Arial, sans-serif"
def esc(s):
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def box(x,y,w,h,label,sub="",fill="#f3f3f3",stroke="#222",fs=13,r=6):
    t=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>'
    if sub:
        t+=f'<text x="{x+w/2}" y="{y+h/2-4}" font-family="{FONT}" font-size="{fs}" font-weight="600" text-anchor="middle" fill="#111">{esc(label)}</text>'
        t+=f'<text x="{x+w/2}" y="{y+h/2+14}" font-family="{FONT}" font-size="10" text-anchor="middle" fill="#555">{esc(sub)}</text>'
    else:
        t+=f'<text x="{x+w/2}" y="{y+h/2+5}" font-family="{FONT}" font-size="{fs}" font-weight="600" text-anchor="middle" fill="#111">{esc(label)}</text>'
    return t
def arrow(x1,y1,x2,y2,dash=False):
    d=' stroke-dasharray="5 4"' if dash else ''
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#333" stroke-width="1.6" marker-end="url(#ah)"{d}/>'
def band(x,y,w,h,label):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="none" stroke="#999" stroke-width="1.2" stroke-dasharray="2 3"/>'
            f'<text x="{x+12}" y="{y+20}" font-family="{FONT}" font-size="12" font-weight="700" fill="#666" letter-spacing="1">{label}</text>')
DEFS='<defs><marker id="ah" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L8,3 L0,6 Z" fill="#333"/></marker></defs>'

def render(name, w, h, body):
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{DEFS}<rect width="{w}" height="{h}" fill="white"/>{body}</svg>'
    open(f"{OUT}/{name}.svg","w").write(svg)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{OUT}/{name}.png", output_width=w*2, output_height=h*2)
    print("saved",name)

# ============ DIAGRAM 1: 3-TIER SYSTEM ARCHITECTURE (horizontal bands) ============
W,H=1180,720
b=band(20,20,1140,150,"DATA SOURCES (TIER 1)")
b+=band(20,200,1140,180,"BACKEND MICROSERVICES (TIER 2)")
b+=band(20,410,1140,150,"DELIVERY LAYER (TIER 3)")
b+=band(20,590,1140,110,"ACTIONABLE OUTPUTS")
# tier1 sources
srcs=[("GPM-IMERG","Precipitation"),("Sentinel-2","NDWI water"),("Landsat 8/9","NDVI veg."),
      ("Sentinel-1 SAR","Flood extent"),("NCDC SitReps","Case/death"),("GRID3 / FMOH","Boundaries·facilities")]
for i,(a,c) in enumerate(srcs):
    b+=box(45+i*185,55,165,90,a,c,fill="#eee")
# tier2 services
svcs=[("GEE Ingestion","zonal stats"),("Risk Engine","heuristic MCDA"),("Correlation","exploratory lag"),
      ("Alert Engine","threshold rules"),("PostGIS DB","spatial store")]
for i,(a,c) in enumerate(svcs):
    b+=box(60+i*222,235,190,100,a,c,fill="#e6e6e6")
# tier3
deliv=[("MapLibre Choropleth","774-LGA map"),("Dashboards & Reports","KPIs · SitReps"),("Surveillance Copilot","assisted analytics")]
for i,(a,c) in enumerate(deliv):
    b+=box(80+i*360,445,320,90,a,c,fill="#ededed")
# outputs
outs=["Risk prioritization","Prepositioning of ORS/vaccines","Multi-agency awareness","WASH targeting"]
for i,o in enumerate(outs):
    b+=box(45+i*285,610,265,70,o,fill="#f6f6f6",fs=11)
# arrows between bands
b+=arrow(590,170,590,200); b+=arrow(590,380,590,410); b+=arrow(590,560,590,590)
render("diag_architecture",W,H,b)

# ============ DIAGRAM 2: DATA PROCESSING PIPELINE (left-to-right flow) ============
W,H=1200,460
b=f'<text x="600" y="34" font-family="{FONT}" font-size="16" font-weight="700" text-anchor="middle" fill="#111">End-to-End Data Processing Pipeline</text>'
# top row: EO branch, bottom row: epi branch, converge to risk
b+=box(40,90,190,80,"EO Satellite Grids","GEE retrieval",fill="#eee")
b+=box(40,300,190,80,"NCDC / Line-list","case · death",fill="#eee")
b+=box(280,90,190,80,"Preprocess","cloud/speckle mask",fill="#e8e8e8")
b+=box(280,300,190,80,"Normalize","LGA join · CFR",fill="#e8e8e8")
b+=box(520,195,190,80,"Spatial Join","LGA polygons",fill="#dedede")
b+=box(760,195,200,80,"Risk Scoring v2.0","weighted MCDA",fill="#d3d3d3")
b+=box(1000,90,170,80,"Alerts","rule engine",fill="#ededed")
b+=box(1000,300,170,80,"Decision Support","map · SitRep",fill="#ededed")
b+=arrow(230,130,280,130); b+=arrow(230,340,280,340)
b+=arrow(470,130,540,215); b+=arrow(470,340,540,255)
b+=arrow(710,235,760,235)
b+=arrow(960,225,1000,150); b+=arrow(960,245,1000,330)
b+=f'<text x="600" y="430" font-family="{FONT}" font-size="10" text-anchor="middle" fill="#777">Where a satellite product is unavailable, the platform returns an explicit "unavailable" status rather than substituting synthetic values.</text>'
render("diag_pipeline",W,H,b)

# ============ DIAGRAM 3: FUTURE ROADMAP (hub-and-spoke, distinct shape) ============
W,H=900,640
cx,cy=450,330
b=f'<text x="450" y="34" font-family="{FONT}" font-size="16" font-weight="700" text-anchor="middle" fill="#111">Advanced Integration &amp; Automation Roadmap</text>'
# central gateway (ellipse to differ from rects)
b+=f'<ellipse cx="{cx}" cy="{cy}" rx="120" ry="66" fill="#d0d0d0" stroke="#111" stroke-width="1.6"/>'
b+=f'<text x="{cx}" y="{cy-4}" font-family="{FONT}" font-size="14" font-weight="700" text-anchor="middle">Unified Integration</text>'
b+=f'<text x="{cx}" y="{cy+16}" font-family="{FONT}" font-size="14" font-weight="700" text-anchor="middle">Gateway</text>'
spokes=[("NCDC/SORMAS API","live case sync",cx,90),
        ("NASRDA Constellation","3 optical + 1 SAR",755,190),
        ("DHS Microdata","WASH · vulnerability",755,470),
        ("AI Field Parser","sitreps · SMS",cx,560),
        ("Calibration Engine","PCA · temporal holdout",145,470),
        ("ML Predictive Layer","validated forecasts (future)",145,190)]
import math
for a,c,bx,by in spokes:
    # connector line first (behind box)
    ang=math.atan2(by-cy,bx-cx)
    ex=cx+120*math.cos(ang)*0.92; ey=cy+66*math.sin(ang)*0.92
    b+=f'<line x1="{ex:.0f}" y1="{ey:.0f}" x2="{bx}" y2="{by}" stroke="#333" stroke-width="1.5" stroke-dasharray="5 4"/>'
for a,c,bx,by in spokes:
    b+=box(bx-115,by-38,230,76,a,c,fill="#eee",fs=12)
render("diag_roadmap",W,H,b)
print("ALL DIAGRAMS DONE")
