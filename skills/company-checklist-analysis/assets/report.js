(() => {
  'use strict';
  const dialog = document.getElementById('evidence-dialog');
  const body = document.getElementById('dialog-body');
  const tooltip = document.getElementById('evidence-tooltip');
  let activeRef = null;
  const hideTip = () => {
    tooltip.hidden = true;
    if (activeRef) activeRef.removeAttribute('aria-describedby');
    activeRef = null;
  };
  const showTip = (ref) => {
    if (dialog.open) return;
    hideTip();
    activeRef = ref;
    tooltip.textContent = ref.dataset.preview;
    tooltip.hidden = false;
    ref.setAttribute('aria-describedby', 'evidence-tooltip');
    const rect = ref.getBoundingClientRect();
    const box = tooltip.getBoundingClientRect();
    tooltip.style.left = `${Math.max(12, Math.min(rect.left, innerWidth - box.width - 12))}px`;
    tooltip.style.top = `${Math.max(12, Math.min(rect.bottom + 8, innerHeight - box.height - 12))}px`;
  };
  document.addEventListener('pointerover', event => {
    const ref = event.target.closest?.('[data-evidence]');
    if (ref && event.pointerType !== 'touch') showTip(ref);
  });
  document.addEventListener('pointerout', event => {
    if (event.target.closest?.('[data-evidence]')) hideTip();
  });
  document.addEventListener('focusin', event => {
    const ref = event.target.closest?.('[data-evidence]');
    if (ref) showTip(ref);
  });
  document.addEventListener('focusout', hideTip);
  document.addEventListener('click', event => {
    const ref = event.target.closest?.('[data-evidence]');
    if (!ref || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const original = document.getElementById(`ev-${ref.dataset.evidence}`);
    if (!original || typeof dialog.showModal !== 'function') return;
    event.preventDefault();
    hideTip();
    const copy = (original.querySelector('.evidence-entry') || original).cloneNode(true);
    copy.removeAttribute('id');
    body.replaceChildren(copy);
    body.scrollTop = 0;
    if (!dialog.open) dialog.showModal();
    document.getElementById('close-evidence').focus();
  });
  document.getElementById('close-evidence').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    const link = event.target.closest('a[href^="#source-"]');
    if (link) dialog.close();
    if (event.target === dialog) {
      const r = dialog.getBoundingClientRect();
      if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close();
    }
  });
  document.addEventListener('keydown', event => { if (event.key === 'Escape') hideTip(); });
  window.addEventListener('resize', hideTip);
  const reasoning = Array.from(document.querySelectorAll('.analysis-detail, .scenario-detail'));
  const expandButton = document.querySelector('.reasoning-toggle');
  if (expandButton) {
    expandButton.hidden = false;
    const syncButton = () => {
      const allOpen = reasoning.every(section => section.open);
      expandButton.textContent = allOpen ? expandButton.dataset.closeLabel : expandButton.dataset.openLabel;
      expandButton.setAttribute('aria-expanded', String(allOpen));
    };
    expandButton.addEventListener('click', () => {
      const open = !reasoning.every(section => section.open);
      reasoning.forEach(section => { section.open = open; });
      syncButton();
    });
    reasoning.forEach(section => section.addEventListener('toggle', syncButton));
    document.addEventListener('reportlanguagechange',syncButton);
    syncButton();
  }
  const evidenceRows = Array.from(document.querySelectorAll('.evidence-record'));
  const search = document.getElementById('evidence-search');
  const type = document.getElementById('evidence-type');
  const count = document.getElementById('evidence-count');
  const supporting = document.getElementById('evidence-supporting');
  const inScope = row => !supporting || supporting.checked || search.value.trim() || row.dataset.supporting !== 'true';
  const previous = document.getElementById('evidence-previous');
  const next = document.getElementById('evidence-next');
  const pageSize = 12;
  let evidencePage = 0;
  const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const searchable = new Map(evidenceRows.map(row => [row, normalize(row.id + ' ' + row.textContent)]));
  const originalSearchable = new Map(searchable);
  let matching = evidenceRows.filter(inScope);
  const drawEvidence = () => {
    const start = evidencePage * pageSize;
    const visible = new Set(matching.slice(start, start + pageSize));
    evidenceRows.forEach(row => {
      row.hidden = !visible.has(row);
      if (row.hidden) row.open = false;
    });
    const ro = document.documentElement.lang === 'ro';
    count.textContent = `${matching.length ? start + 1 : 0}–${Math.min(start + pageSize, matching.length)} ${ro ? 'din' : 'of'} ${matching.length}` + (matching.length !== evidenceRows.length ? ` · ${evidenceRows.length} ${ro ? 'în total' : 'total'}` : '');
    previous.disabled = evidencePage === 0;
    next.disabled = start + pageSize >= matching.length;
    document.getElementById('evidence-empty').hidden = matching.length !== 0;
  };
  const filterEvidence = () => {
    const words = normalize(search.value).trim().split(/\s+/).filter(Boolean);
    matching = evidenceRows.filter(row => inScope(row) && (!type.value || row.dataset.kind === type.value) && words.every(word => searchable.get(row).includes(word)));
    evidencePage = 0;
    drawEvidence();
  };
  if (evidenceRows.length && search) {
    document.querySelector('.evidence-controls').hidden = false;
    document.querySelector('.evidence-pager').hidden = false;
    search.addEventListener('input', filterEvidence);
    type.addEventListener('change', filterEvidence);
    if (supporting) { supporting.parentElement.hidden = false; supporting.addEventListener('change', filterEvidence); }
    document.getElementById('evidence-reset').addEventListener('click', () => {
      search.value = ''; type.value = ''; if (supporting) supporting.checked = false; filterEvidence(); search.focus();
    });
    const changePage = delta => {
      evidencePage += delta;
      drawEvidence();
      document.getElementById('evidence-list').scrollIntoView({block:'start'});
      matching[evidencePage * pageSize]?.querySelector('summary').focus({preventScroll:true});
    };
    previous.addEventListener('click', () => changePage(-1));
    next.addEventListener('click', () => changePage(1));
    evidenceRows.forEach(row => row.addEventListener('toggle', () => {
      if (row.open) evidenceRows.forEach(other => { if (other !== row && other.open) other.open = false; });
    }));
    drawEvidence();
    document.addEventListener('reportlanguagechange', () => {
      evidenceRows.forEach(row => searchable.set(row,originalSearchable.get(row)+' '+normalize(row.textContent)));
      const currentPage=evidencePage;
        const words=normalize(search.value).trim().split(/\s+/).filter(Boolean);
        matching=evidenceRows.filter(row=>inScope(row) && (!type.value || row.dataset.kind===type.value) && words.every(word=>searchable.get(row).includes(word)));
      evidencePage=Math.min(currentPage,Math.max(0,Math.ceil(matching.length/pageSize)-1));
      drawEvidence();
    });
  }
  // Deep links reveal their record even when it is on another page or filtered out.
  const revealTarget = hash => {
    const target = document.getElementById(hash.slice(1));
    const row = target?.closest('.evidence-record');
    if (row && search) {
      search.value = ''; type.value = ''; if (supporting) supporting.checked = true; matching = evidenceRows;
      evidencePage = Math.floor(evidenceRows.indexOf(row) / pageSize);
      drawEvidence();
    }
    for (let parent = target; parent; parent = parent.parentElement) {
      if (parent.tagName === 'DETAILS') parent.open = true;
    }
    if (target) requestAnimationFrame(() => target.scrollIntoView({block:'start'}));
  };
  window.addEventListener('hashchange', () => revealTarget(location.hash));
  document.addEventListener('click', event => {
    const link = event.target.closest?.('a[href^="#"]:not([data-evidence])');
    if (link && link.hash === location.hash) revealTarget(link.hash);
  });
  if (location.hash) revealTarget(location.hash);
  if ('IntersectionObserver' in window) {
    const links = Array.from(document.querySelectorAll('nav a[href^="#"]'));
    const sections = links.map(link => document.querySelector(link.getAttribute('href'))).filter(Boolean);
    const observer = new IntersectionObserver(entries => {
      const entering = entries.filter(entry => entry.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (!entering) return;
      links.forEach(link => {
        if (link.hash === `#${entering.target.id}`) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
      });
    }, {rootMargin: '-8% 0px -60% 0px', threshold: 0});
    sections.forEach(section => observer.observe(section));
  }
})();
