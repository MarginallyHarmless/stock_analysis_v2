(() => {
  'use strict';
  const toolbar = document.querySelector('.toolbar');
  const search = document.querySelector('#company-search');
  const category = document.querySelector('#category-filter');
  const sort = document.querySelector('#sort-order');
  const groups = [...document.querySelectorAll('.cluster')];
  const counter = document.querySelector('#result-count');
  const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase();
  const update = () => {
    const query = normalize(search.value.trim());
    let count = 0;
    for (const group of groups) {
      const cards = [...group.querySelectorAll('.company-card')];
      cards.sort((a, b) => sort.value === 'updated'
        ? Date.parse(b.dataset.date) - Date.parse(a.dataset.date) || a.dataset.company.localeCompare(b.dataset.company)
        : a.dataset.company.localeCompare(b.dataset.company));
      let visible = 0;
      for (const card of cards) {
        card.hidden = !(normalize(card.dataset.name).includes(query) && (!category.value || category.value === group.dataset.category));
        if (!card.hidden) visible++;
        group.querySelector('.cluster-cards').appendChild(card);
      }
      group.hidden = visible === 0;
      group.querySelector('.cluster-count').textContent = visible;
      count += visible;
    }
    counter.textContent = `${count} ${counter.dataset.label}`;
    document.querySelector('#no-results').hidden = count !== 0 || groups.length === 0;
  };
  search.addEventListener('input', update);
  category.addEventListener('change', update);
  sort.addEventListener('change', update);
  document.querySelector('#reset-filters').addEventListener('click', () => {
    search.value = ''; category.value = ''; sort.value = 'name'; update(); search.focus();
  });
  toolbar.hidden = groups.length === 0;
})();
