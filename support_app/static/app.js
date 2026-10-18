const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const paths = {
  chat: '<path d="M21 11.5a8.4 8.4 0 0 1-9 8.5 10 10 0 0 1-4-.8L3 21l1.8-5A8.5 8.5 0 1 1 21 11.5Z"/><path d="M8 10h8M8 14h5"/>',
  box: '<path d="m12 3 9 5-9 5-9-5 9-5Zm-9 5v10l9 5 9-5V8M12 13v10M7 5.8l9 5"/>',
  book: '<path d="M12 5v15M3 4c4-1 6 0 9 2 3-2 5-3 9-2v15c-4-1-6 0-9 2-3-2-5-3-9-2V4Z"/>',
  ticket: '<path d="M3 7V4h18v3a3 3 0 0 0 0 6v3H3v-3a3 3 0 0 0 0-6Z"/><path d="M15 5v2m0 3v2m0 3v1"/>',
  truck: '<path d="M1 4h13v12H1V4Zm13 5h4l4 4v3h-8"/><circle cx="5" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>',
  return: '<path d="m8 4-5 5 5 5M3 9h11a6 6 0 0 1 0 12h-3"/>',
  headphones: '<path d="M4 14v-3a8 8 0 0 1 16 0v3"/><rect x="3" y="12" width="4" height="8" rx="2"/><rect x="17" y="12" width="4" height="8" rx="2"/>',
  shield: '<path d="m12 3 8 3v6c0 5-8 10-8 10S4 17 4 12V6l8-3Z"/><path d="m8 12 3 3 5-6"/>',
  refresh: '<path d="M20 7V2m0 5h-5M20 7a8 8 0 1 0 1 9"/>',
  mic: '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3m-4 0h8"/>',
  arrowUp: '<path d="M12 20V4m-6 6 6-6 6 6"/>',
  search: '<circle cx="10" cy="10" r="7"/><path d="m15 15 6 6"/>',
};
for (const el of $$('[data-icon]')) el.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true">${paths[el.dataset.icon] || ''}</svg>`;

const en = Object.fromEntries($$('[data-i18n]').map(el => [el.dataset.i18n, el.textContent]));
en.voiceTitle = 'A familiar voice.\nA helping hand.';
const ar = {
  workspace:'مساحة الدعم الخاصة بك',support:'مركز الدعم',orders:'طلباتي',knowledge:'دليل المساعدة',tickets:'طلبات الدعم',humanTitle:'بعض الأمور تحتاج لمسة بشرية.',humanBody:'اكتب التفاصيل في طلب دعم. سنحتفظ بكل شيء في مكان واحد.',createRequest:'إنشاء طلب',demoCustomer:'عميل تجريبي',fictionalStore:'متجر خيالي · عرض محلي',helpCenter:'مركز المساعدة',hereToHelp:'قليل من المساعدة، كثير من الاهتمام.',welcome:'أهلاً بك في نورا كير',hero:'خلّنا نلقى الحل.',heroBody:'من أول فتح للعلبة إلى أسئلتك اليومية. نحن هنا لمساعدتك.',meetNoor:'تعرّف على نور',assistantLabel:'مساعدك لخدمة عملاء نورا',chatGreeting:'سعداء بوجودك هنا.',chatIntro:'اسأل عن طلبك، أو احصل على مساعدة للمنتج، أو تعرّف على سياساتنا. من أين نبدأ؟',quickDelivery:'وين طلبي؟',quickReturn:'إرجاع منتج',quickProduct:'مساعدة مع سماعاتي',quickWarranty:'ماذا يشمل الضمان؟',thinking:'أراجع دليل المساعدة…',messageLabel:'رسالتك',grounded:'إجابات مستندة إلى دليل المساعدة',aiReplies:'ردود الذكاء الاصطناعي',ratherTalk:'تفضّل نتكلم؟',voiceTitle:'صوت مألوف.\nومساعدة قريبة.',voiceBody:'تحدّث مع نور بالعربية أو الإنجليزية، على راحتك.',startVoice:'بدء محادثة صوتية',voiceCost:'يستخدم رصيد منصت الصوتي · حد 5 دقائق',mute:'كتم الميكروفون',onItsWay:'شيء جميل في طريقه لك.',shipped:'تم الشحن',viewOrder:'عرض طلبك',usefulReads:'مقالات قد تفيدك',allArticles:'تصفّح المقالات العشر',bottomNote:'منتجات مدروسة تستحق دعماً مدروساً.',demoTag:'تجربة توضيحية',yourNoura:'كل ما يخص نورا، في مكان واحد',ordersIntro:'طلبان خياليان لتجربة التتبع ودعم المنتجات.',goodToKnow:'معلومات مفيدة',knowledgeIntro:'نفس الدليل الذي يستخدمه نور. إجابات واضحة دون تخمين.',everyDetail:'كل التفاصيل في مكان واحد',ticketsIntro:'تُحفظ على هذا الجهاز. لا يُرسل بريد ولا يُخطر موظف.',footer:'تجربة خيالية لخدمة العملاء، صُنعت باهتمام.',letsHelp:'دعنا نساعدك',ticketDisclaimer:'يحفظ هذا العرض طلبك محلياً. لن يُرسل بريد إلكتروني أو يُتواصل مع فريق دعم حقيقي.',subject:'الموضوع',category:'الفئة',details:'ماذا حدث؟',attach:'إرفاق آخر 12 رسالة من المحادثة',saveRequest:'حفظ الطلب',newConversation:'بدء محادثة جديدة؟',clearDescription:'ستُحذف رسائل هذه الجلسة من المتصفح. تبقى طلبات الدعم المحفوظة متاحة.',keepChat:'متابعة المحادثة',startFresh:'بدء من جديد',
};
const state = {language: localStorage.getItem('noura-language') === 'ar' ? 'ar' : 'en', view:'support', data:null, busy:false, room:null, connecting:false, voiceSources:[], muted:false, ticketId:null, voiceTimer:null, agentTimer:null};
const t = (key) => (state.language === 'ar' ? ar[key] : en[key]) || en[key] || key;
const local = (english, arabic) => state.language === 'ar' ? arabic : english;
const categoryTitle = category => state.language === 'ar' ? ({'Orders & delivery':'الطلبات والتوصيل','Returns & refunds':'الإرجاع والاسترداد','Product care':'العناية بالمنتج','Shopping with Noura':'التسوق مع نورا'}[category] || category) : category;
const node = (tag, className, text) => {const el=document.createElement(tag); if(className)el.className=className; if(text!==undefined)el.textContent=text; return el;};
let toastTimer;
function toast(message){$('#toast').textContent=message;$('#toast').classList.remove('hidden');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').classList.add('hidden'),6500);}
async function api(path, body){
  const response=await fetch(path,body===undefined?{credentials:'same-origin'}:{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':state.data?.csrf||''},body:JSON.stringify(body)});
  const result=await response.json();
  if(!response.ok)throw new Error(result.error||local('Something went wrong. Please try again.','حدث خطأ. حاول مرة أخرى.'));
  return result;
}
function applyLanguage(){
  document.documentElement.lang=state.language;document.documentElement.dir=state.language==='ar'?'rtl':'ltr';
  for(const el of $$('[data-i18n]'))el.textContent=t(el.dataset.i18n);
  for(const el of $$('nav [data-view]'))el.setAttribute('aria-label',t(el.dataset.view));
  $('.voice-card h2').style.whiteSpace='pre-line';
  $('#language').textContent=state.language==='ar'?'English ↔':'عربي ↔';
  $('#language').setAttribute('aria-label',state.language==='ar'?'Switch to English':'التبديل إلى العربية');
  $('#message').placeholder=local('Tell us what’s on your mind…','كيف نقدر نساعدك؟');
  $('#article-search').placeholder=local('Search delivery, returns, product care…','ابحث عن التوصيل والإرجاع والعناية بالمنتج…');
  $('#ticket-subject').placeholder=local('A short summary of the issue','ملخص قصير للمشكلة');
  $('#ticket-description').placeholder=local('Include your demo order number if relevant. No payment details, please.','اذكر رقم الطلب التجريبي إن كان مناسباً. لا تكتب بيانات الدفع.');
  $('#breadcrumb-current').textContent=t(state.view==='support'?'support':state.view);
  $('#new-chat').title=t('newConversation');$('#new-chat').setAttribute('aria-label',t('newConversation'));
  if(state.data){renderOrders();renderArticles();renderTickets();renderSources(state.voiceSources.length?state.voiceSources:null);}
  updateVoice();
}
function switchView(view){
  state.view=view;
  for(const el of $$('.view'))el.classList.toggle('hidden',el.id!==`view-${view}`);
  for(const el of $$('nav [data-view]')){el.classList.toggle('active',el.dataset.view===view);if(el.dataset.view===view)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');}
  $('#breadcrumb-current').textContent=t(view==='support'?'support':view);
  window.scrollTo({top:0,behavior:'smooth'});
}
function renderSources(sources){
  const items=sources||state.data.articles.filter(a=>['returns','pairing','delivery'].includes(a.id));
  $('#source-list').replaceChildren();
  for(const article of items){
    const full=state.data.articles.find(a=>a.id===article.id)||article;
    const button=node('button','source-link');button.append(node('span','',state.language==='ar'?(full.title_ar||full.title):full.title),node('span','','↗'));
    button.addEventListener('click',()=>openArticle(full.id));$('#source-list').append(button);
  }
}
function openArticle(id){
  const article=state.data?.articles.find(a=>a.id===id);if(!article)return;
  const content=$('#article-content');content.replaceChildren();
  content.append(node('div','eyebrow',categoryTitle(article.category)),node('h2','',state.language==='ar'?article.title_ar:article.title),node('p','article-body',state.language==='ar'?article.body_ar:article.body));
  content.append(node('p','article-disclaimer',local('Noura demo knowledge base · Fictional store policies and products.','دليل نورا التجريبي · سياسات ومنتجات متجر خيالي.')));
  const ask=node('button','primary-button',local('Ask Noor about this','اسأل نور عن هذا'));ask.onclick=()=>{$('#article-dialog').close();switchView('support');sendMessage(local(`Tell me about ${article.title}`,`أخبرني عن ${article.title_ar}`));};content.append(ask);$('#article-dialog').showModal();
}
function renderArticles(){
  const query=$('#article-search').value.trim().toLocaleLowerCase();
  const articles=state.data.articles.filter(a=>`${a.title} ${a.title_ar} ${a.body} ${a.body_ar} ${a.keywords.join(' ')}`.toLocaleLowerCase().includes(query));
  $('#articles-list').replaceChildren();
  for(const article of articles){
    const button=node('button','article-card');const body=state.language==='ar'?article.body_ar:article.body;
    button.append(node('small','',categoryTitle(article.category)),node('h2','',state.language==='ar'?article.title_ar:article.title),node('p','',body.slice(0,110)+'…'),node('span','',local('Read the guide ↗','اقرأ الدليل ↖')));button.onclick=()=>openArticle(article.id);$('#articles-list').append(button);
  }
  if(!articles.length)$('#articles-list').append(node('p','muted',local('No matching articles. Try another word.','لا توجد مقالات مطابقة. جرّب كلمة أخرى.')));
}
function art(kind){
  const el=node('div',`product-art ${kind==='headphones'?'headphones-art':'speaker-art'}`);el.setAttribute('aria-hidden','true');
  if(kind==='headphones')el.append(node('div','headband'),node('div','ear left'),node('div','ear right'));return el;
}
function renderOrders(){
  $('#orders-list').replaceChildren();
  for(const order of state.data.orders){
    const card=node('article','order-card');const top=node('div','order-card-top');top.append(node('strong','',`#${order.id}`),node('span',`pill ${order.status==='Shipped'?'shipping':'delivered'}`,state.language==='ar'?order.status_ar:order.status));
    const product=node('div','order-card-product');const details=node('div');details.append(node('h2','',order.product),node('p','',order.detail),node('p','price',`${order.price} ${local('AED','درهم')}`));product.append(art(order.art),details);
    const timeline=node('ol','timeline');order.milestones.forEach((step,i)=>timeline.append(node('li',i<=order.progress?'done':'',state.language==='ar'?['تأكيد الطلب','تغليف بعناية','تسليم لشركة الشحن','تم التوصيل'][i]:step)));
    const button=node('button','secondary-button',local('Ask Noor about this order ↗','اسأل نور عن هذا الطلب ↖'));button.onclick=()=>{switchView('support');sendMessage(local(`What is the status of order ${order.id}?`,`ما حالة الطلب ${order.id}؟`));};
    card.append(top,product,timeline,node('p','',state.language==='ar'?order.estimate_ar:order.estimate),button);$('#orders-list').append(card);
  }
}
function renderTickets(){
  const tickets=state.data.tickets;$('#ticket-count').textContent=tickets.length;$('#tickets-list').replaceChildren();
  if(!tickets.length){const empty=node('div','empty-state');empty.append(node('div','tiny-spark','✳'),node('h2','',local('A clean slate.','بداية جديدة.')),node('p','',local('No requests yet. If you need a little extra help, start here.','لا توجد طلبات بعد. إذا احتجت مساعدة إضافية، ابدأ هنا.')));const button=node('button','primary-button',t('createRequest'));button.onclick=openTicket;empty.append(button);$('#tickets-list').append(empty);return;}
  for(const ticket of tickets){const row=node('article','ticket-row');const info=node('div');info.append(node('small','',`${ticket.id} · ${ticket.category}`),node('h3','',ticket.subject),node('p','',ticket.description),node('small','',new Date(ticket.created*1000).toLocaleString(state.language==='ar'?'ar-AE':'en-AE')));row.append(info,node('span','pill delivered',local('Saved locally','محفوظ محلياً')));$('#tickets-list').append(row);}
}
function appendMessage(message){
  $('#chat-welcome').classList.add('hidden');const row=node('div',`message ${message.role||'assistant'}`);
  const label=node('div','message-label',message.role==='user'?local('YOU','أنت'):local('NOOR','نور'));
  if(message.mode==='knowledge')label.append(node('span','',local('· SUPPORT GUIDE','· دليل المساعدة')));
  if(message.mode==='voice')label.append(node('span','',local('· VOICE','· صوت')));
  const bubble=node('div','bubble',message.text);bubble.dir='auto';row.append(label,bubble);
  if(message.notice)row.append(node('div','message-notice',message.notice));
  if(message.sources?.length){const sources=node('div','message-sources');for(const source of message.sources){const button=node('button','citation',`↗ ${source.title}`);button.onclick=()=>openArticle(source.id);sources.append(button);}row.append(sources);renderSources(message.sources);}
  if(message.needs_support){const actions=node('div','message-actions');const button=node('button','',t('createRequest'));button.onclick=openTicket;actions.append(button);row.append(actions);}
  $('#messages').append(row);$('#chat-scroll').scrollTop=$('#chat-scroll').scrollHeight;
}
function setBusy(busy){state.busy=busy;$('#send').disabled=busy||!!state.room;$('#new-chat').disabled=busy||!!state.room;$('#message').disabled=busy||!!state.room;$('#thinking').classList.toggle('hidden',!busy);for(const button of $$('.quick-prompts button'))button.disabled=busy||!!state.room;$('#ai-mode').disabled=busy||!state.data?.ai_available;updateVoice();}
async function sendMessage(text){
  if(!state.data)return toast(local('Still connecting. Please try again in a moment.','جارٍ الاتصال. حاول بعد لحظة.'));
  if(state.busy||state.room||state.connecting)return toast(local('Finish the current reply or voice call first.','انتظر الرد الحالي أو أنهِ المكالمة أولاً.'));
  text=text.trim();if(!text)return;
  appendMessage({role:'user',text});$('#message').value='';$('#message').style.height='auto';setBusy(true);
  try{const result=await api('/api/chat',{message:text,language:state.language,mode:$('#ai-mode').checked?'ai':'knowledge'});appendMessage({role:'assistant',...result});}
  catch(error){appendMessage({role:'assistant',text:local('I couldn’t complete that request. Please try again.','تعذّر إكمال الطلب. حاول مرة أخرى.'),notice:error.message});}
  finally{setBusy(false);$('#message').focus();}
}
function openTicket(){if(!state.data)return;$('#ticket-form').reset();$('#ticket-error').textContent='';state.ticketId=crypto.randomUUID();$('#ticket-dialog').showModal();}
async function submitTicket(event){
  event.preventDefault();const form=new FormData(event.currentTarget);$('#save-ticket').disabled=true;$('#ticket-error').textContent='';
  try{const response=await api('/api/tickets',{subject:form.get('subject'),category:form.get('category'),description:form.get('description'),attach:form.get('attach')==='on',request_id:state.ticketId});state.data.tickets=response.tickets;renderTickets();$('#ticket-dialog').close();switchView('tickets');toast(local(`Request ${response.id} saved locally.`, `تم حفظ الطلب ${response.id} محلياً.`));}
  catch(error){$('#ticket-error').textContent=error.message;}
  finally{$('#save-ticket').disabled=false;}
}
function updateVoice(){
  $('#voice-label').textContent=state.connecting?local('Connecting…','جارٍ الاتصال…'):state.room?local('End voice chat','إنهاء المحادثة'):t('startVoice');
  $('#voice-button').disabled=state.connecting||state.busy;
  $('#mute-button').classList.toggle('hidden',!state.room);$('#mute-button').textContent=state.muted?local('Unmute microphone','تشغيل الميكروفون'):t('mute');
  $('.voice-wave').classList.toggle('live',!!state.room&&!state.muted);
}
async function endVoice(){
  clearTimeout(state.voiceTimer);clearTimeout(state.agentTimer);
  const room=state.room;state.room=null;state.connecting=false;
  if(room)await room.disconnect();$('#audio-output').replaceChildren();$('#audio-resume').classList.add('hidden');
  updateVoice();setBusy(false);$('#voice-status').textContent=t('voiceCost');
  try{await api('/api/voice/end',{});const messages=await api('/api/messages');$('#messages').replaceChildren();for(const message of messages.items)appendMessage(message);$('#chat-welcome').classList.toggle('hidden',messages.items.length>0);}
  catch(error){toast(error.message);}
}
async function startVoice(){
  if(state.room)return endVoice();
  if(state.busy||state.connecting)return;
  let issued=false;
  state.connecting=true;updateVoice();$('#voice-status').textContent=local('Connecting your microphone…','جارٍ توصيل الميكروفون…');
  try{
    const status=await api('/api/voice/status');state.data.voice=status;
    if(!status.ready)throw new Error(local('Stop the old server, then run: python -m support_app.launch','أوقف الخادم السابق ثم شغّل: python -m support_app.launch'));
    const {Room,RoomEvent,Track}=await import('https://cdn.jsdelivr.net/npm/livekit-client@2.22.4/+esm');
    const access=await api('/api/voice/token',{language:state.language});issued=true;
    const room=new Room();state.room=room;
    room.on(RoomEvent.TrackSubscribed,track=>{if(track.kind===Track.Kind.Audio){const audio=track.attach();$('#audio-output').append(audio);}});
    room.on(RoomEvent.TrackUnsubscribed,track=>track.detach().forEach(el=>el.remove()));
    room.on(RoomEvent.AudioPlaybackStatusChanged,()=>$('#audio-resume').classList.toggle('hidden',room.canPlaybackAudio));
    room.on(RoomEvent.ParticipantConnected,()=>{clearTimeout(state.agentTimer);$('#voice-status').textContent=local('Connected. Go ahead, Noor is listening.','تم الاتصال. تفضّل، نور يستمع.');});
    room.on(RoomEvent.Disconnected,()=>{if(state.room===room){state.room=null;clearTimeout(state.voiceTimer);clearTimeout(state.agentTimer);updateVoice();setBusy(false);$('#voice-status').textContent=local('Call ended.','انتهت المكالمة.');$('#audio-output').replaceChildren();}});
    room.registerTextStreamHandler('lk.transcription',async(reader,participant)=>{try{const text=await reader.readAll();if(text)appendMessage({role:participant.identity===room.localParticipant.identity?'user':'assistant',text,mode:'voice',sources:participant.identity===room.localParticipant.identity?[]:state.voiceSources});}catch{toast(local('A caption was interrupted.','انقطع أحد النصوص المصاحبة.'));}});
    room.registerTextStreamHandler('noura.sources',async(reader)=>{try{const sources=JSON.parse(await reader.readAll());state.voiceSources=Array.isArray(sources)?sources.filter(s=>state.data.articles.some(a=>a.id===s.id)):[];renderSources(state.voiceSources);}catch{/* Ignore incomplete source messages. */}});
    await room.connect(access.url,access.token);await room.startAudio();await room.localParticipant.setMicrophoneEnabled(true);
    state.connecting=false;state.muted=false;updateVoice();setBusy(false);
    $('#voice-status').textContent=local('Waiting for Noor to join…','بانتظار انضمام نور…');
    if(room.remoteParticipants.size){$('#voice-status').textContent=local('Connected. Go ahead, Noor is listening.','تم الاتصال. تفضّل، نور يستمع.');}
    else state.agentTimer=setTimeout(()=>{toast(local('The voice agent did not join. Check the agent terminal and try again.','لم ينضم المساعد الصوتي. تحقق من تشغيله وحاول مجدداً.'));endVoice();},25000);
    state.voiceTimer=setTimeout(()=>{toast(local('The five-minute demo call has ended.','انتهت مدة المكالمة التجريبية: خمس دقائق.'));endVoice();},300000);
  }catch(error){if(state.room){const room=state.room;state.room=null;await room.disconnect();}state.connecting=false;updateVoice();setBusy(false);const reason=error.name==='NotAllowedError'?local('Microphone permission was denied. Allow it in your browser and try again.','تم رفض إذن الميكروفون. اسمح به من المتصفح وحاول مجدداً.'):error.message;$('#voice-status').textContent=reason;toast(reason);if(issued){try{await api('/api/voice/end',{});}catch{/* No active local media remains. */}}}
}

for(const el of $$('[data-view]'))el.addEventListener('click',()=>switchView(el.dataset.view));
for(const el of $$('[data-action="ticket"]'))el.addEventListener('click',openTicket);
for(const el of $$('[data-close]'))el.addEventListener('click',()=>document.getElementById(el.dataset.close).close());
for(const dialog of $$('dialog'))dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});
$('#language').onclick=()=>{state.language=state.language==='en'?'ar':'en';localStorage.setItem('noura-language',state.language);applyLanguage();};
$('#article-search').oninput=()=>state.data&&renderArticles();
$('#track-order').onclick=()=>switchView('orders');
$('#chat-form').onsubmit=e=>{e.preventDefault();sendMessage($('#message').value);};
$('#message').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();sendMessage(e.target.value);}};
$('#message').oninput=e=>{e.target.style.height='auto';e.target.style.height=Math.min(e.target.scrollHeight,120)+'px';};
const prompts={delivery:['Where is my order NR-1042?','وين طلبي NR-1042؟'],returns:['What is your return policy?','ما سياسة الإرجاع؟'],pairing:['How do I pair my Noura Air headphones?','كيف أقوم بإقران سماعات Noura Air؟'],warranty:['What does the warranty cover?','ماذا يشمل الضمان؟']};
for(const el of $$('[data-prompt]'))el.onclick=()=>sendMessage(prompts[el.dataset.prompt][state.language==='ar'?1:0]);
$('#ticket-form').onsubmit=submitTicket;
$('#new-chat').onclick=()=>!state.busy&&!state.room&&$('#confirm-dialog').showModal();
$('#confirm-clear').onclick=async()=>{try{await api('/api/conversation/clear',{});$('#messages').replaceChildren();$('#chat-welcome').classList.remove('hidden');state.voiceSources=[];renderSources();$('#confirm-dialog').close();}catch(error){toast(error.message);}};
$('#voice-button').onclick=startVoice;
$('#mute-button').onclick=async()=>{if(state.room){try{await state.room.localParticipant.setMicrophoneEnabled(state.muted);state.muted=!state.muted;updateVoice();}catch{toast(local('Microphone could not be changed.','تعذّر تغيير حالة الميكروفون.'));}}};
const audioResume=node('button','mute-button hidden',local('Enable audio playback','تشغيل الصوت'));audioResume.id='audio-resume';audioResume.onclick=()=>state.room?.startAudio();$('.voice-card').append(audioResume);
applyLanguage();setBusy(false);
try{state.data=await api('/api/bootstrap');$('#ai-mode').checked=state.data.ai_available;setBusy(false);applyLanguage();for(const message of state.data.messages)appendMessage(message);if(!state.data.voice.ready)$('#voice-status').textContent=local('Start both services: python -m support_app.launch','شغّل الخدمتين: python -m support_app.launch');}
catch(error){toast(local('The support server is unavailable. Refresh after starting it.','خادم الدعم غير متاح. حدّث الصفحة بعد تشغيله.'));$('#voice-status').textContent=error.message;}
