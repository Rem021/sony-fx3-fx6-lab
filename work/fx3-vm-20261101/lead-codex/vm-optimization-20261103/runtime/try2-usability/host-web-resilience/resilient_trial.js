const token=__TOKEN__;
let displayed=0,shown=0,shownSHA='',busy=false,ending=false,finished=false;
let lastURL=null,renderFault=null,lastStatus=null,awaitingStep=null,deliveryUnknown=false;
const image=document.querySelector('#frame'),statusEl=document.querySelector('#status');
const err=document.querySelector('#error'),endButton=document.querySelector('#end');
const keys=[...document.querySelectorAll('.key')];

// Bound fetch AND body consumption. A lost mutation response is never retried.
async function request(path,options={},bodyKind='json'){
 const controller=new AbortController();let timer;
 const deadline=new Promise((_,reject)=>{timer=setTimeout(()=>{
   const error=new Error('连接超时；操作结果需要重新确认。');
   error.deliveryUnknown=true;reject(error);controller.abort();
 },8000);});
 try{return await Promise.race([deadline,(async()=>{
   const response=await fetch(path,{cache:'no-store',...options,signal:controller.signal});
   if(!response.ok){
     // Only explicit server rejections prove a mutation was rejected.
     const body=await response.json();const error=new Error(body.error||'操作未完成');
     error.deliveryUnknown=response.status>=500;throw error;
   }
   const body=await response[bodyKind]();return {response,body};
 })()]);}finally{clearTimeout(timer);}
}
async function post(path,body){return (await request(path,{method:'POST',
 headers:{'Content-Type':'application/json','X-Trial-Token':token},body:JSON.stringify(body)})).body;}
function disableKeys(){keys.forEach(b=>b.disabled=true);}
function enableKeys(s){
 const visual=!!s.frame&&displayed>0&&shownSHA===s.frame.PNG_sha256&&s.render_valid&&!renderFault;
 keys.forEach(b=>b.disabled=!s.ready||busy||ending||awaitingStep!==null||!visual);
}
async function showFrame(s){
 if(!s.frame)return;
 if(s.frame.PNG_sha256===shownSHA){displayed=shown=s.frame.sequence;return;}
 const {response,body}=await request('/frame.png',{},'blob');
 const seq=Number(response.headers.get('X-Frame-Sequence')),sha=response.headers.get('X-Frame-PNG-SHA256');
 if(!Number.isSafeInteger(seq)||seq<=0||!sha)throw Error('画面身份缺失');
 const u=URL.createObjectURL(body);
 try{await new Promise((resolve,reject)=>{
   const timer=setTimeout(()=>settle(Error('画面加载超时，请结束试用或重新连接。')),8000);
   let done=false;
   function settle(error){if(done)return;done=true;clearTimeout(timer);image.onload=image.onerror=null;
     if(error)reject(error);else resolve();}
   image.onload=()=>settle();image.onerror=()=>settle(Error('画面解码失败。'));
   image.src=u;
 });}catch(e){URL.revokeObjectURL(u);throw e;}
 document.querySelector('#placeholder').hidden=true;
 displayed=shown=seq;shownSHA=sha;
 if(lastURL)URL.revokeObjectURL(lastURL);lastURL=u;
}
async function tick(){
 if(finished)return;
 try{
   const s=(await request('/api/status')).body;lastStatus=s;
   statusEl.textContent=s.message;err.textContent=s.error||'';
   document.querySelector('#meta').textContent=`按键 ${s.steps}/${s.max_steps} · 剩余 ${Math.ceil(s.remaining_seconds/60)} 分钟 · 提交帧 ${s.frame?s.frame.sequence:'等待中'}`;
   document.querySelector('#events').replaceChildren(...s.events.map(e=>{
     const li=document.createElement('li');li.textContent=e;return li;
   }));
   // A final server receipt remains authoritative even if its last image is unavailable.
   if(s.phase==='finished'){
     finished=true;disableKeys();endButton.disabled=true;return;
   }
   if(s.phase==='stopping'){ending=true;disableKeys();}
   if(awaitingStep!==null&&!busy&&!deliveryUnknown&&s.steps>=awaitingStep&&!s.busy){
     awaitingStep=null;deliveryUnknown=false;
   }
   if(deliveryUnknown)err.textContent='按键是否送达尚未确认，已暂停新按键；请结束本轮后重新启动。';
   if(s.frame&&s.frame.sequence!==shown)await showFrame(s);
   renderFault=null;enableKeys(s);
 }catch(e){
   renderFault=e.message;disableKeys();err.textContent=renderFault;
   if(ending){
     statusEl.textContent='结束状态尚未确认，请查看启动终端；必要时在终端按 Ctrl-C。';
     endButton.disabled=false;
   }
 }finally{if(!finished)setTimeout(tick,400);}
}
keys.forEach(b=>b.onclick=async()=>{
 if(b.disabled||busy||ending||renderFault||awaitingStep!==null||!lastStatus)return;
 busy=true;awaitingStep=lastStatus.steps+1;disableKeys();
 try{
   const ack=await post('/api/key',{key:Number(b.dataset.key),observed_sequence:displayed});
   if(ack.accepted!==true||ack.next_step!==awaitingStep)throw Error('按键回执不完整，请等待状态确认。');
   err.textContent='';
 }catch(e){
   if(e.deliveryUnknown===false){awaitingStep=null;deliveryUnknown=false;}
   else{deliveryUnknown=true;}
   err.textContent=e.message;
 }finally{busy=false;}
});
endButton.onclick=async()=>{
 if(finished||endButton.disabled)return;
 ending=true;disableKeys();endButton.disabled=true;
 statusEl.textContent='正在结束试用并等待资源回收确认…';
 try{await post('/api/stop',{});}
 catch(e){err.textContent=e.message;endButton.disabled=false;
   statusEl.textContent='结束请求未确认，请查看启动终端；必要时在终端按 Ctrl-C。';}
};
tick();
