"""Jグランツ公開API収集・検証用。Python 3.10+ / pip install requests"""
import argparse, datetime as dt, json, logging, sqlite3, time
from pathlib import Path
import requests
BASE='https://api.jgrants-portal.go.jp/exp'
KEYWORDS=['事業','補助','支援','促進','設備','創業','デジタル','省エネ','販路','地域','雇用','研究','開発','観光','農業','商業','経営','投資','人材','環境']
SCHEMA='''CREATE TABLE IF NOT EXISTS subsidies(id TEXT PRIMARY KEY,title TEXT,area TEXT,max_amount REAL,agency TEXT,raw_json TEXT,first_seen TEXT,last_seen TEXT);
CREATE TABLE IF NOT EXISTS rounds(id TEXT PRIMARY KEY,subsidy_id TEXT,start_at TEXT,end_at TEXT,area TEXT,raw_json TEXT,last_seen TEXT);
CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY AUTOINCREMENT,started_at TEXT,finished_at TEXT,keywords INTEGER,list_records INTEGER,unique_records INTEGER,details_ok INTEGER,details_failed INTEGER,error TEXT);'''
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def get(session,url,params=None):
 for attempt in range(5):
  try:
   r=session.get(url,params=params,timeout=25)
   if r.status_code in (429,500,502,503,504):
    time.sleep(min(2**attempt,20));continue
   r.raise_for_status();return r.json()
  except (requests.RequestException,ValueError):
   if attempt==4:raise
   time.sleep(min(2**attempt,20))
 raise RuntimeError('API retries exhausted')
def results(payload):
 if not isinstance(payload,dict) or not isinstance(payload.get('result'),list):raise ValueError('Unexpected API response structure')
 return payload['result']
def collect(path,keywords,detail_limit,delay):
 db=sqlite3.connect(path);db.executescript(SCHEMA);start=now();items={};ok=failed=0;errors=[]
 s=requests.Session();s.headers.update({'User-Agent':'HojokinCompassResearch/0.2 (public API; low-rate access)','Accept':'application/json'})
 for word in keywords:
  try:
   data=results(get(s,BASE+'/v1/public/subsidies',{'keyword':word,'sort':'acceptance_end_datetime','order':'ASC','acceptance':1}))
   for item in data:
    if isinstance(item,dict) and item.get('id'):items[str(item['id'])]=item
   print(f'{word}: {len(data)} records; unique so far {len(items)}')
  except Exception as exc:errors.append(f'{word}: {exc}');logging.warning('keyword %s failed: %s',word,exc)
  time.sleep(delay)
 for item in items.values():
  db.execute('''INSERT INTO subsidies(id,title,area,max_amount,agency,raw_json,first_seen,last_seen) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,area=excluded.area,max_amount=excluded.max_amount,agency=excluded.agency,raw_json=excluded.raw_json,last_seen=excluded.last_seen''',(str(item['id']),item.get('title'),item.get('target_area_search'),item.get('subsidy_max_limit'),item.get('institution_name'),json.dumps(item,ensure_ascii=False),now(),now()))
 db.commit()
 for sid in list(items)[:detail_limit]:
  try:
   data=results(get(s,BASE+'/v2/public/subsidies/id/'+sid))
   if not data:raise ValueError('empty detail')
   detail=data[0]; rounds=detail.get('workflow') or []
   for index,r in enumerate(rounds):
    rid=str(r.get('id') or f'{sid}:{index}')
    db.execute('''INSERT INTO rounds VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET start_at=excluded.start_at,end_at=excluded.end_at,area=excluded.area,raw_json=excluded.raw_json,last_seen=excluded.last_seen''',(rid,sid,r.get('acceptance_start_datetime'),r.get('acceptance_end_datetime'),r.get('target_area_search'),json.dumps(r,ensure_ascii=False),now()))
   db.execute('UPDATE subsidies SET raw_json=? WHERE id=?',(json.dumps(detail,ensure_ascii=False),sid));db.commit();ok+=1
  except Exception as exc:failed+=1;errors.append(f'detail {sid}: {exc}')
  time.sleep(delay)
 db.execute('INSERT INTO runs(started_at,finished_at,keywords,list_records,unique_records,details_ok,details_failed,error) VALUES(?,?,?,?,?,?,?,?)',(start,now(),len(keywords),len(items),len(items),ok,failed,'\n'.join(errors[:30])))
 db.commit()
 stats={'run_at':now(),'keywords':len(keywords),'unique_subsidies':len(items),'details_ok':ok,'details_failed':failed,'rounds':db.execute('SELECT COUNT(*) FROM rounds').fetchone()[0],'with_max_amount':sum(i.get('subsidy_max_limit') is not None for i in items.values()),'errors':errors[:30]}
 Path(path).with_suffix('.report.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(stats,ensure_ascii=False,indent=2));db.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--db',default='hojokin.sqlite');p.add_argument('--detail-limit',type=int,default=30);p.add_argument('--delay',type=float,default=0.4);p.add_argument('--keywords',nargs='+',default=KEYWORDS);a=p.parse_args();collect(a.db,a.keywords,a.detail_limit,a.delay)
