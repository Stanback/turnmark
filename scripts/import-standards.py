#!/usr/bin/env python3
"""Extract factual individual-event times from the official USA Swimming PDF.
Requires Poppler's pdftotext. PDF stays in a temporary directory, not the repo.
Run with --pdf PATH to reproduce from a downloaded source.
"""
import argparse, datetime, hashlib, json, pathlib, re, subprocess, tempfile, urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
URL='https://www.usaswimming.org/docs/default-source/timesdocuments/time-standards/2025/2028-motivational-standards-age-group.pdf'
parser=argparse.ArgumentParser();parser.add_argument('--pdf',type=pathlib.Path);args=parser.parse_args()
def seconds(value):
 parts=value.split(':');return round(float(parts[-1])+(int(parts[-2])*60 if len(parts)>1 else 0),2)
with tempfile.TemporaryDirectory() as temp:
 pdf=args.pdf or pathlib.Path(temp)/'standards.pdf'
 if not args.pdf:
  req=urllib.request.Request(URL,headers={'User-Agent':'Turnmark data importer/4.0'})
  pdf.write_bytes(urllib.request.urlopen(req).read())
 raw=pdf.read_bytes();text=subprocess.check_output(['pdftotext','-layout',str(pdf),'-'],text=True)
 assert '10/10/2025' in text, 'Source revision changed: review before updating parser and manifest.'
 records=[];age=None;seen=set()
 for line in text.splitlines():
  group=re.search(r'(10 & under|11-12|13-14|15-16|17-18) Girls',line)
  if group:age=group[1].replace('10 & under','10u')
  event=re.search(r'\b(50|100|200|400|500|800|1000|1500|1650)\s+(FR|BK|BR|FL|IM)\s+(SCY|SCM|LCM)\b',line)
  if not event:continue
  assert age
  left=re.findall(r'\d+(?::\d{2})?\.\d{2}',line[:event.start()])
  right=re.findall(r'\d+(?::\d{2})?\.\d{2}',line[event.end():])
  assert len(left)==len(right)==6,(age,line)
  distance,stroke,course=event.groups()
  for category,values in [('women',left),('men',right[::-1])]:
   key=(age,category,course,int(distance),stroke);assert key not in seen,key;seen.add(key)
   times=[seconds(x) for x in values];assert all(a>b for a,b in zip(times,times[1:])),key
   records.append({'age':age,'category':category,'course':course,'distance':int(distance),'stroke':stroke,'times':times})
 assert len(records)==482,len(records)
 result={'source':{'title':'USA Swimming 2024–2028 Motivational Standards','url':URL,'revision':'2025-10-10','retrieved':str(datetime.date.today()),'sha256':hashlib.sha256(raw).hexdigest(),'levels':['B','BB','A','AA','AAA','AAAA'],'scope':'Individual events; relays excluded. Categories follow the published girls/boys tables.'},'records':records}
 (ROOT/'packages/sdk/src/data/standards.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
 print(f'Imported {len(records)} event/category rows ({len(records)*6} published times).')
