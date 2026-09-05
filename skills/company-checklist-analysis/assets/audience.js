(() => {
 const control=document.querySelector('.audience-switch');
 if(!control)return;
 const storageKey='company-report-audience';
 const setMode=mode=>{
  if(!['beginner','experienced'].includes(mode))mode=control.dataset.default;
  document.documentElement.dataset.audience=mode;
  control.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.audienceChoice===mode)));
  try{localStorage.setItem(storageKey,mode)}catch(_){}
  document.getElementById('evidence-tooltip').hidden=true;
  document.dispatchEvent(new CustomEvent('reportaudiencechange',{detail:{mode}}));
 };
 control.hidden=false;
 control.addEventListener('click',event=>{
  const button=event.target.closest('[data-audience-choice]');if(!button)return;
  const anchor=Array.from(document.querySelectorAll('main>.report-section,main>.hero')).find(s=>s.getBoundingClientRect().bottom>0);
  const top=anchor?.getBoundingClientRect().top;
  setMode(button.dataset.audienceChoice);
  if(anchor&&scrollY>0)scrollBy(0,anchor.getBoundingClientRect().top-top);
 });
 let mode=control.dataset.default;
 try{mode=localStorage.getItem(storageKey)||mode}catch(_){}
 setMode(mode);
})();
