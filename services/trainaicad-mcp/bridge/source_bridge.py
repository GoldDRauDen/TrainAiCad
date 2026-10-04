"""Render real source bytes. Metadata is not proof of vision interpretation."""
import hashlib
import json
import sys
from pathlib import Path
import fitz

source, output, raw = sys.argv[1:]
options = json.loads(raw)
out = Path(output); out.mkdir(parents=True, exist_ok=True)
source_sha = hashlib.sha256(Path(source).read_bytes()).hexdigest()
doc = fitz.open(source)
if not doc.is_pdf:
    doc = fitz.open("pdf", doc.convert_to_pdf())
pages = options.get('pages') or list(range(1, len(doc)+1))
dpi = options.get('dpi', 110)
result = {'sourceSha256':source_sha,'pageCount':len(doc),'pages':[],'images':[]}
for i,page in enumerate(doc):
    result['pages'].append({'page':i+1,'widthPt':page.rect.width,'heightPt':page.rect.height,'rotation':page.rotation,'text':page.get_text(),'embeddedImages':len(page.get_images())})
requests = [{'page':p,'roi':[0,0,1,1]} for p in pages]+options.get('crops',[])
for request in requests:
    p, roi = request['page'], request['roi']
    if not 1<=p<=len(doc):raise ValueError('SOURCE_PAGE_OUT_OF_RANGE')
    if len(roi)!=4 or not (0<=roi[0]<roi[2]<=1 and 0<=roi[1]<roi[3]<=1):raise ValueError('INVALID_SOURCE_ROI')
    page = doc[p-1]
    key = hashlib.sha256(json.dumps([source_sha,p,roi,dpi,page.rotation,fitz.VersionBind]).encode()).hexdigest()
    image_path = out/f'{key}.png'
    if not image_path.exists():
        r = page.rect
        clip = fitz.Rect(roi[0]*r.width,roi[1]*r.height,roi[2]*r.width,roi[3]*r.height)
        page.get_pixmap(matrix=fitz.Matrix(dpi/72,dpi/72),clip=clip,alpha=False).save(image_path)
    result['images'].append({'imageId':key,'page':p,'roi':roi,'dpi':dpi,'sha256':hashlib.sha256(image_path.read_bytes()).hexdigest()})
manifest = out/'manifest.json'
previous = json.loads(manifest.read_text()) if manifest.exists() else {'images':[]}
result['images'] = list({im['imageId']:im for im in previous['images']+result['images']}.values())
temp = manifest.with_suffix('.tmp');temp.write_text(json.dumps(result,ensure_ascii=False));temp.replace(manifest)
print(json.dumps(result,ensure_ascii=False))
