"""Draw actual 2025 Census county polygons; requires numpy and matplotlib."""
from pathlib import Path
import argparse,hashlib,json,zipfile,xml.etree.ElementTree as ET
import numpy as np
import os
ROOT=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.mplconfig'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch,Patch
import matplotlib.patheffects as pe

SOURCE='https://www2.census.gov/geo/tiger/GENZ2025/kml/cb_2025_us_county_500k.zip'
STUDY={'Baldwin','Clay','DeKalb','Etowah','Jefferson','Mobile','Montgomery','Morgan','Sumter','Tuscaloosa'}
NS={'k':'http://www.opengis.net/kml/2.2'}


def load_counties(archive):
    with zipfile.ZipFile(archive) as z:
        name=next(n for n in z.namelist() if n.endswith('.kml'))
        root=ET.fromstring(z.read(name))
    counties=[]
    for place in root.findall('.//k:Placemark',NS):
        props={s.attrib['name']:s.text for s in place.findall('.//k:SimpleData',NS)}
        polygons=[]
        for polygon in place.findall('.//k:Polygon',NS):
            rings=[]
            for node in polygon.findall('.//k:LinearRing/k:coordinates',NS):
                rings.append(np.array([[float(v) for v in token.split(',')[:2]] for token in node.text.split()]))
            polygons.append(rings)
        counties.append((props,polygons))
    return counties


def transform(ring):
    # Spherical equirectangular projection, central meridian -86.8 degrees,
    # standard parallel 32.5 degrees. Coordinates are kilometers.
    return np.column_stack([(ring[:,0]+86.8)*111.195*np.cos(np.deg2rad(32.5)),
                            (ring[:,1]-32.5)*111.195])


def draw(ax,polygons,color,edge,lw):
    for rings in polygons:
        vertices=[];codes=[]
        for ring in rings:
            xy=transform(ring)
            vertices.extend(xy);codes.extend([MPath.MOVETO]+[MPath.LINETO]*(len(xy)-2)+[MPath.CLOSEPOLY])
        ax.add_patch(PathPatch(MPath(vertices,codes),facecolor=color,edgecolor=edge,lw=lw))


def centroid(polygons):
    # Label anchor: planar area centroid of largest outer polygon.
    candidates=[]
    for rings in polygons:
        xy=transform(rings[0]);x,y=xy[:,0],xy[:,1]
        cross=x[:-1]*y[1:]-x[1:]*y[:-1];area=cross.sum()/2
        center=np.array([((x[:-1]+x[1:])*cross).sum(),((y[:-1]+y[1:])*cross).sum()])/(6*area)
        candidates.append((abs(area),center))
    return max(candidates,key=lambda v:v[0])[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--boundaries',type=Path,default=ROOT/'counties_2025.zip')
    parser.add_argument('--output',type=Path,default=ROOT)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    counties=load_counties(args.boundaries)
    al=[c for c in counties if c[0]['STATEFP']=='01']
    assert len(al)==67
    selected=[c for c in al if c[0]['NAME'] in STUDY]
    assert {c[0]['NAME'] for c in selected}==STUDY and len(selected)==10
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.fonttype':'none'})
    fig=plt.figure(figsize=(10,11),facecolor='white')
    ax=fig.add_axes([.06,.13,.88,.77]);ax.set_facecolor('#eef6f8')
    for props,polygons in counties:
        if props['STATEFP'] in ['28','13','12','47']:
            draw(ax,polygons,'#f3f2ee','#f3f2ee',.1)
    for props,polygons in al:
        chosen=props['NAME'] in STUDY
        draw(ax,polygons,'#237c9b' if chosen else '#e4e9ec','#ffffff' if chosen else '#9caab1',.8 if chosen else .45)
    for props,polygons in selected:
        name=props['NAME'];xy=centroid(polygons)
        ax.text(*xy,name,ha='center',va='center',fontsize=10 if name not in ['Montgomery','Tuscaloosa'] else 9.5,
                color='white',weight='bold',path_effects=[pe.withStroke(linewidth=1,foreground='#12546b')])
    for text,lon,lat,rotation in [('TENNESSEE',-86.7,35.12,0),('MISSISSIPPI',-88.65,33.1,90),
                                 ('GEORGIA',-84.8,33.1,90),('FLORIDA',-85.9,30.75,0),('Gulf of Mexico',-88.0,30.04,0)]:
        xy=transform(np.array([[lon,lat]]))[0]
        ax.text(*xy,text,rotation=rotation,ha='center',va='center',color='#677a82',fontsize=10,
                style='italic' if text=='Gulf of Mexico' else 'normal')
    ax.set_xlim(-205,205);ax.set_ylim(-290,310);ax.set_aspect('equal')
    ax.set_xticks([]);ax.set_yticks([])
    for spine in ax.spines.values():spine.set_visible(False)
    ax.annotate('',xy=(168,268),xytext=(168,225),arrowprops=dict(arrowstyle='-|>',lw=1.3,color='#223843'))
    ax.text(168,278,'N',ha='center',weight='bold',fontsize=13)
    sx,sy=35,-259
    ax.plot([sx,sx+100],[sy,sy],color='#223843',lw=2)
    for dx in [0,50,100]:
        ax.plot([sx+dx,sx+dx],[sy-4,sy+4],color='#223843',lw=1)
        ax.text(sx+dx,sy-9,str(dx),ha='center',va='top',fontsize=8)
    ax.text(sx+110,sy-9,'km',va='top',fontsize=8)
    inset=fig.add_axes([.105,.68,.19,.19]);inset.set_facecolor('#eef6f8')
    for props,polygons in counties:
        if props['STATEFP'] in ['01','28','13','12','47','21','37','45','22','05','51']:
            draw(inset,polygons,'#237c9b' if props['STATEFP']=='01' else '#dbe2e5','#dbe2e5',.1)
    inset.set_xlim(-680,590);inset.set_ylim(-440,800);inset.set_aspect('equal');inset.set_xticks([]);inset.set_yticks([])
    inset.text(0,0,'AL',color='white',weight='bold',ha='center',fontsize=9)
    inset.set_title('Regional location',fontsize=9,pad=4)
    for spine in inset.spines.values():spine.set_color('#aab8bd')
    fig.text(.08,.96,'Alabama PM2.5 study counties',fontsize=23,weight='bold',color='#203a48')
    fig.text(.08,.924,'Ten study counties highlighted within Alabama’s 67 counties',fontsize=12,color='#536a75')
    fig.legend(handles=[Patch(facecolor='#237c9b',label='Study counties (10)'),Patch(facecolor='#e4e9ec',edgecolor='#9caab1',label='Other Alabama counties (57)')],
               loc='lower center',bbox_to_anchor=(.5,.075),ncol=2,frameon=False)
    fig.text(.08,.047,'Source: U.S. Census Bureau, 2025 Cartographic Boundary Files, 1:500,000.',fontsize=9,color='#536a75')
    fig.text(.08,.027,'Generalized geographic boundaries. Highlighting indicates study inclusion, not pollution levels.',fontsize=9,color='#536a75')
    for ext in ['png','svg']:fig.savefig(args.output/f'Alabama_study_counties.{ext}',dpi=240,facecolor='white')
    plt.close(fig)
    selected_features=[]
    for props,polygons in al:
        selected_features.append({'type':'Feature','properties':{**props,'study_county':props['NAME'] in STUDY},
                                 'geometry':{'type':'MultiPolygon','coordinates':[[r.tolist() for r in poly] for poly in polygons]}})
    (args.output/'Alabama_counties_2025.geojson').write_text(json.dumps({'type':'FeatureCollection','features':selected_features}))
    (args.output/'map_metadata.json').write_text(json.dumps({'boundary_source':SOURCE,'vintage':2025,'scale':'1:500,000',
        'download_date':'2026-10-11','boundary_sha256':hashlib.sha256(args.boundaries.read_bytes()).hexdigest(),
        'projection':'Spherical equirectangular, standard parallel 32.5N, central meridian 86.8W',
        'alabama_counties':len(al),'highlighted_counties':sorted(STUDY)},indent=2))
    print('Verified 67 Alabama boundaries and all 10 study counties. Saved PNG, SVG, GeoJSON and metadata.')


if __name__=='__main__':main()
