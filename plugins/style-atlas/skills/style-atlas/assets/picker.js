let picked=null,saving=false,ready=false,connectionFailed=false,targetName='',intent='browse',preset=null,receiver={status:'disconnected'},lastSnapshot='',errorMessage='';
document.body.classList.add('live-picker');
const contextBar=text('section','','context-bar');contextBar.setAttribute('aria-label','当前任务');document.querySelector('.catalog').before(contextBar);
const taskMessage=text('p','','task-message');taskMessage.setAttribute('aria-live','polite');document.querySelector('.catalog-caption').after(taskMessage);
const applyButton=$('apply');applyButton.disabled=true;
const isPreset=()=>intent==='preset';
const submitted=()=>['submitted','received'].includes(receiver.status);
const connected=()=>ready&&(isPreset()||(intent==='apply'&&targetName))&&receiver.status==='waiting'&&Date.now()/1000<receiver.expiresAt;
const canChoose=()=>ready&&!saving&&(isPreset()||connected());
const activeId=()=>isPreset()?preset?.id:submitted()?picked?.id:null;
const actionLabel=()=>isPreset()?'设为默认风格':'应用此风格';
async function post(path,data){
 const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data),signal:AbortSignal.timeout(8000)});
 const result=await r.json();if(!r.ok){if(result.error==='source_changed')receiver.status='source_changed';throw new Error(result.error||'request_failed')}return result;
}
async function editPreset(clear=false){
 if(saving||!ready||!isPreset())return;saving=true;errorMessage='';showState();
 try{
  const data=await post(clear?'clear-preset':'arm',clear?{}:{presetEdit:true});
  receiver=clear?data.receiver:data;if(clear){preset=null;picked=null}else{$('search').value='';render()}
  lastSnapshot='';
 }catch{errorMessage=clear?'暂未确认取消结果，请检查连接后重试。':'暂时无法更换，请检查连接后重试。'}
 finally{saving=false;showState();if(!clear&&!errorMessage){$('search').focus({preventScroll:true});$('catalog').scrollIntoView({block:'start',behavior:'smooth'})}}
}
function action(container,label,id,fn){const button=text('button',label,'secondary');button.id=id;button.disabled=saving;button.onclick=fn;container.append(button)}
function showState(){
 document.body.classList.toggle('is-connected',canChoose());
 contextBar.replaceChildren();
 const style=styles.find(s=>s.id===activeId());
 if(style){const thumb=document.createElement('img');thumb.className='context-thumb';thumb.src=style.embedded;thumb.alt='';contextBar.append(thumb)}
 const copy=text('div','','context-copy');contextBar.append(copy);
 let label='当前任务',name='正在连接…',note='';
 if(ready&&isPreset()){label=preset?'当前默认':'默认风格';name=preset?preset.name:'尚未设置';}
 else if(ready&&targetName){label='当前 HTML';name=targetName;}
 else if(ready){label='开始使用';name='请先在 Codex 对话中上传 HTML';note='上传后让 Codex 连接文件，即可应用风格；也可以先在对话中设置默认风格。';}
 else{name=connectionFailed?'连接已断开':'正在连接…';note=connectionFailed?'请在 Codex 对话中重新打开 Style Pearlyn。':'';}
 copy.append(text('p',label,'context-label'),text('div',name,'context-name'));if(note)copy.append(text('p',note,'context-note'));
 const actions=text('div','','context-actions');
 if(ready&&isPreset()){
  action(actions,preset?'更换':'选择风格','change-preset',()=>editPreset());
  if(preset)action(actions,'取消默认','clear-preset',()=>editPreset(true));
 }else if(connected())action(actions,'取消等待','cancel-wait',async()=>{try{receiver=await post('cancel',{roundId:receiver.roundId});errorMessage=''}catch{errorMessage='取消未确认，请在 Codex 中停止任务。'}showState()});
 if(actions.children.length)contextBar.append(actions);
 const caption=isPreset()?'选一种喜欢的风格，用于本任务后续网页。':targetName?'选择风格后直接应用，修改后的 HTML 会在对话中返回。':'浏览风格参考，连接任务后即可使用。';
 document.querySelector('.catalog-caption').textContent=caption;
 let message='';
 if(ready&&!isPreset()&&submitted())message=receiver.status==='received'?'已选择「'+picked?.name+'」。Codex 正在处理，请在对话中查看结果。':'选择已提交，等待 Codex 接收，无需重复点击。';
 if(ready&&!isPreset()&&targetName&&!connected()&&!submitted())message=receiver.status==='source_changed'?'原 HTML 已发生变化，请回到 Codex 连接最新文件。':'本轮连接已结束，请回到 Codex 重新打开面板。';
 taskMessage.textContent=errorMessage||message;taskMessage.classList.toggle('save-error',Boolean(errorMessage));
 document.querySelectorAll('.card').forEach(card=>{
  const active=activeId()===card.dataset.styleId;card.classList.toggle('is-picked',active);
  const button=card.querySelector('.choose');button.textContent=active?(isPreset()?'当前默认':'已选用'):saving?'提交中…':canChoose()?'选用':submitted()?'选用':'连接后选用';
  button.classList.toggle('is-current',Boolean(active));button.disabled=!canChoose()||active;
  button.setAttribute('aria-label',(isPreset()?'设为默认风格':'应用此风格')+' · '+styles.find(s=>s.id===card.dataset.styleId).name);
  let mark=card.querySelector('.selected-mark');if(active&&!mark){mark=document.createElement('input');mark.type='checkbox';mark.checked=true;mark.tabIndex=-1;mark.setAttribute('aria-hidden','true');mark.className='selected-mark';card.append(mark)}else if(!active&&mark)mark.remove();
 });
 applyButton.textContent=current?.id===activeId()?(isPreset()?'当前默认风格':'已选用'):saving?'正在提交…':canChoose()?actionLabel():'连接任务后选用';
 applyButton.disabled=!canChoose()||current?.id===activeId();
}
async function useStyle(s){
 if(!canChoose()||s.id===activeId())return;saving=true;errorMessage='';showState();
 try{
  if(isPreset()&&!connected())receiver=await post('arm',{presetEdit:true});
  const data=await post('selection',{id:s.id,mode:'style',action:'continue',roundId:receiver.roundId});
  picked=data.selection;receiver=data.receiver;preset=data.preset||null;lastSnapshot='';
  if($('dialog').open)$('dialog').close();
 }catch{errorMessage='暂未确认提交结果，请检查连接。已提交的选择会自动更新。'}
 finally{saving=false;showState()}
}
applyButton.onclick=()=>current&&useStyle(current);
const originalOpenStyle=openStyle;openStyle=function(s,from){originalOpenStyle(s,from);showState()};
const originalRender=render;render=function(){originalRender();document.querySelectorAll('.card').forEach(card=>{card.querySelector('.choose').onclick=()=>useStyle(styles.find(s=>s.id===card.dataset.styleId))});showState()};
$('search').oninput=render;render();
async function sync(){
 try{
  const r=await fetch('selection',{signal:AbortSignal.timeout(8000)});if(!r.ok)throw new Error();const data=await r.json(),snapshot=JSON.stringify(data);
  if(!saving&&(!ready||snapshot!==lastSnapshot)){lastSnapshot=snapshot;picked=data.selection;targetName=data.targetName||'';intent=data.intent||'browse';preset=data.preset||null;receiver=data.receiver||{status:'disconnected'};ready=true;connectionFailed=false;showState()}
 }catch{ready=false;connectionFailed=true;receiver={status:'disconnected'};showState()}
 finally{setTimeout(sync,document.hidden?5000:1500)}
}
sync();
