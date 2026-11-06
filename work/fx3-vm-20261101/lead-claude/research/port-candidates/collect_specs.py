import concurrent.futures, datetime, hashlib, html.parser, json, pathlib, re, subprocess
ROOT=pathlib.Path(__file__).resolve().parent
URLS={
 'FX3-spec':'https://www.sony.jp/pro-cam/products/ILME-FX3/spec.html',
 'FX3A-spec':'https://www.sony.jp/pro-cam/products/ILME-FX3A/spec/',
 'FX30-spec':'https://www.sony.jp/pro-cam/products/ILME-FX30/spec.html',
 'FX2-spec':'https://www.sony.jp/pro-cam/products/ILME-FX2B/spec.html',
 'FX6-spec':'https://www.sony.jp/pro-cam/products/ILME-FX6V/spec.html',
 'FX5-spec':'https://www.sony.jp/pro-cam/products/ILME-FX5/spec.html',
 'A7SIII-spec':'https://www.sony.jp/ichigan/products/ILCE-7SM3/spec.html',
 'A7IV-spec':'https://www.sony.jp/ichigan/products/ILCE-7M4/spec.html',
 'A1-spec':'https://www.sony.jp/ichigan/products/ILCE-1/spec.html',
 'FX3-release':'https://www.sony.jp/CorporateCruise/Press/202102/21-0224/',
 'FX3A-product':'https://www.sony.jp/pro-cam/products/ILME-FX3A/',
 'FX30-release':'https://www.sony.jp/CorporateCruise/Press/202209/22-0928/',
 'FX2-release':'https://www.sony.jp/CorporateCruise/Press/202505/25-0528/',
 'FX6-release':'https://www.sony.jp/CorporateCruise/Press/202011/20-1118/',
 'FX5-release':'https://www.sony.jp/CorporateCruise/Press/202607/26-0722B/',
 'A7SIII-release':'https://www.sony.jp/CorporateCruise/Press/202007/20-0729/',
 'A7IV-release':'https://www.sony.jp/CorporateCruise/Press/202112/21-1202/',
 'A1-release':'https://www.sony.jp/CorporateCruise/Press/202101/21-0127/',
 'oss-notice':'https://oss.sony.net/Products/Linux/notice.html',
 'oss-B2B-index':'https://oss.sony.net/Products/Linux/B2B/category01.html',
 'oss-DI-index':'https://oss.sony.net/Products/Linux/DI/category01.html'}
class Text(html.parser.HTMLParser):
 def __init__(self):super().__init__();self.a=[];self.skip=0
 def handle_starttag(self,t,a):
  if t in ('script','style'):self.skip+=1
  if t in ('tr','p','br','li','h1','h2','h3'):self.a.append('\n')
  if t in ('th','td'):self.a.append(' | ')
 def handle_endtag(self,t):
  if t in ('script','style'):self.skip=max(0,self.skip-1)
  if t in ('tr','p','li'):self.a.append('\n')
 def handle_data(self,s):
  if not self.skip:self.a.append(s.strip()+' ')
def fetch(k,u):
 b=subprocess.check_output(['curl','-fsSL','--connect-timeout','15','--max-time','80','--retry','1',u])
 p=ROOT/'pages'/f'{k}.html';p.parent.mkdir(exist_ok=True);p.write_bytes(b)
 codec='cp932' if re.search(br'charset=["\']?(?:shift_jis|sjis)',b,re.I) else 'utf-8'
 parser=Text();parser.feed(b.decode(codec,errors='replace'));txt='\n'.join(re.sub(r'\s+',' ',x).strip() for x in ''.join(parser.a).splitlines() if x.strip())
 t=p.with_suffix('.txt');t.write_text(txt+'\n')
 return {'id':k,'url':u,'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'text_path':str(t.relative_to(ROOT))}
if __name__=='__main__':
 rs=[];errs=[]
 with concurrent.futures.ThreadPoolExecutor(5) as pool:
  fs={pool.submit(fetch,k,u):k for k,u in URLS.items()}
  for f in concurrent.futures.as_completed(fs):
   try:rs.append(f.result())
   except Exception as e:errs.append({'id':fs[f],'error':str(e)})
 (ROOT/'spec-page-receipts.json').write_text(json.dumps({'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pages':rs,'errors':errs},indent=2)+'\n')
 print(json.dumps({'pages':len(rs),'errors':errs}),flush=True)
