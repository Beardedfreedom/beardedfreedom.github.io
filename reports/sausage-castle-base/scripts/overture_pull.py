import sys, json, time
import pyarrow.dataset as ds, pyarrow.fs as fs, pyarrow.compute as pc, pyarrow as pa
rel, theme, typ, out = sys.argv[1:5]
xmin, ymin, xmax, ymax = map(float, sys.argv[5:9])
t0=time.time()
s3 = fs.S3FileSystem(anonymous=True, region="us-west-2", proxy_options="http://127.0.0.1:39727")
path = f"overturemaps-us-west-2/release/{rel}/theme={theme}/type={typ}/"
d = ds.dataset(path, filesystem=s3, format="parquet")
flt = (pc.field(("bbox","xmin")) < xmax) & (pc.field(("bbox","xmax")) > xmin) & (pc.field(("bbox","ymin")) < ymax) & (pc.field(("bbox","ymax")) > ymin)
tbl = d.to_table(filter=flt)
print(typ, "rows:", tbl.num_rows, f"({time.time()-t0:.0f}s)")
# write GeoJSON via shapely from WKB
from shapely import wkb
feats=[]
cols=[c for c in tbl.column_names if c not in ("geometry","bbox")]
for i in range(tbl.num_rows):
    props={}
    for c in cols:
        v=tbl.column(c)[i].as_py()
        if v is None: continue
        if isinstance(v,(dict,list)): v=json.dumps(v, default=str)
        props[c]=v
    g=wkb.loads(tbl.column("geometry")[i].as_py())
    feats.append({"type":"Feature","properties":props,"geometry":json.loads(json.dumps(g.__geo_interface__))})
json.dump({"type":"FeatureCollection","features":feats}, open(out,"w"))
print("wrote", out)
