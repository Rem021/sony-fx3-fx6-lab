
const token="test";let displayed=0,shown=0,shownSHA='',busy=false,ending=false,finished=false,lastURL=null,renderFault=null;
const image=document.querySelector('#frame'),statusEl=document.querySelector('#status'),err=document.querySelector('#error');
const keys=[...document.querySelectorAll('.key')];
async function post(path,body){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Trial-Token':token},body:JSON.stringify(body)});const j=await r.json();if(!r.ok)throw Error(j.error||'操作未完成');return j;}
function enableKeys(s){const visual=!!s.frame&&displayed>0&&shownSHA===s.frame.PNG_sha256&&s.render_valid&&!renderFault;keys.forEach(b=>b.disabled=!s.ready||busy||ending||!visual);}
async function showFrame(s){
 if(!s.frame)return;
 if(s.frame.PNG_sha256===shownSHA){displayed=shown=s.frame.sequence;return;}
 const response=await fetch('/frame.png',{cache:'no-store'});if(!response.ok)throw Error('画面请求失败：HTTP '+response.status);
 const seq=Number(response.headers.get('X-Frame-Sequence')),sha=response.headers.get('X-Frame-PNG-SHA256');
 if(!Number.isSafeInteger(seq)||seq<=0||!sha)throw Error('画面身份缺失');
 const u=URL.createObjectURL(await response.blob());
 try{await new Promise((resolve,reject)=>{let done=false;const timer=setTimeout(()=>{if(!done){done=true;reject(Error('画面加载超时，请刷新页面或结束试用'));}},8000);
   image.onload=()=>{if(!done){done=true;clearTimeout(timer);resolve();}};
   image.onerror=()=>{if(!done){done=true;clearTimeout(timer);reject(Error('画面解码失败，请刷新页面或结束试用'));}};
   image.src=u;});
 }catch(e){URL.revokeObjectURL(u);throw e;}
 document.querySelector('#placeholder').hidden=true;
 displayed=shown=seq;shownSHA=sha;if(lastURL)URL.revokeObjectURL(lastURL);lastURL=u;
}
async function tick(){if(finished)return;let s=null;try{
 const response=await fetch('/api/status',{cache:'no-store'});if(!response.ok)throw Error('状态请求失败：HTTP '+response.status);s=await response.json();
 statusEl.textContent=s.message;err.textContent=s.error||'';
 document.querySelector('#meta').textContent=`按键 ${s.steps}/${s.max_steps} · 剩余 ${Math.ceil(s.remaining_seconds/60)} 分钟 · 提交帧 ${s.frame?s.frame.sequence:'等待中'}${s.frame?' · 像素源 '+s.frame.pixel_source_sequence:''}`;
 document.querySelector('#events').replaceChildren(...s.events.map(e=>{const li=document.createElement('li');li.textContent=e;return li;}));
 if(s.frame&&s.frame.sequence!==shown)await showFrame(s);
 renderFault=null;enableKeys(s);
 if(s.phase==='finished'){finished=true;keys.forEach(b=>b.disabled=true);document.querySelector('#end').disabled=true;}
 }catch(e){renderFault=e.message;err.textContent=renderFault;keys.forEach(b=>b.disabled=true);if(ending){statusEl.textContent='试用已结束，窗口可以关闭。';finished=true;}}
 finally{if(!finished)setTimeout(tick,400);}}
keys.forEach(b=>b.onclick=async()=>{if(busy||ending||renderFault)return;busy=true;keys.forEach(k=>k.disabled=true);try{await post('/api/key',{key:Number(b.dataset.key),observed_sequence:displayed});err.textContent='';}catch(e){err.textContent=e.message;}finally{busy=false;}});
document.querySelector('#end').onclick=async()=>{ending=true;keys.forEach(b=>b.disabled=true);document.querySelector('#end').disabled=true;statusEl.textContent='正在结束试用并回收资源…';try{await post('/api/stop',{});}catch(e){err.textContent=e.message;}};tick();
