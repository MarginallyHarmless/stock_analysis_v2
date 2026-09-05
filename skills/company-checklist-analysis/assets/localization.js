(() => {
  const dictionaries = JSON.parse(document.getElementById('report-translations').textContent);
  const controls = document.querySelector('.language-switch');
  const storageKey = 'company-report-language';
  const translate = language => {
    if (!dictionaries[language]) return;
    const words = dictionaries[language];
    document.documentElement.lang = language;
    document.querySelectorAll('[data-i18n]').forEach(node => { node.textContent = words[node.dataset.i18n]; });
    document.querySelectorAll('[data-i18n-attrs]').forEach(node => {
      for (const [attr,key] of Object.entries(JSON.parse(node.dataset.i18nAttrs))) node.setAttribute(attr,words[key]);
    });
    controls.querySelectorAll('button').forEach(button => button.setAttribute('aria-pressed',String(button.dataset.language === language)));
    document.getElementById('evidence-tooltip').hidden = true;
    document.dispatchEvent(new CustomEvent('reportlanguagechange'));
    try { localStorage.setItem(storageKey,language); } catch (_) { /* Offline restrictions must not block switching. */ }
  };
  controls.hidden = false;
  controls.addEventListener('click',event => {
    const button = event.target.closest('[data-language]');
    if (!button) return;
    // Keep the reader's section and open evidence in place as text reflows.
    const sections = Array.from(document.querySelectorAll('main>.report-section,main>.hero'));
    const anchor = sections.find(section => section.getBoundingClientRect().bottom > 0);
    const top = anchor?.getBoundingClientRect().top;
    translate(button.dataset.language);
    if (anchor && window.scrollY > 0) window.scrollBy(0,anchor.getBoundingClientRect().top-top);
  });
  let language = document.documentElement.lang;
  try { language = localStorage.getItem(storageKey) || language; } catch (_) {}
  translate(language);
})();
