/**
 * load-more.js — кнопка «Подгрузить ещё»
 * Загружает следующую страницу постов через fetch и добавляет карточки в контейнер.
 * При отсутствии JS работает стандартная серверная пагинация (ссылки ?page=N).
 */
(function () {
  'use strict';

  var container = document.getElementById('posts-container');
  var loadMoreWrap = document.querySelector('.pagination__load-more');

  if (!container || !loadMoreWrap) return;

  var btn = loadMoreWrap.querySelector('.js-load-more');
  if (!btn) return;

  btn.addEventListener('click', function () {
    var url = btn.getAttribute('data-url');
    if (!url) return;

    btn.disabled = true;
    btn.textContent = '...';

    fetch(url, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
      .then(function (resp) { return resp.text(); })
      .then(function (html) {
        // Парсим HTML ответа
        var parser = new DOMParser();
        var doc = parser.parseFromString(html, 'text/html');
        var newCards = doc.querySelectorAll('.post-card');
        var newLoadMore = doc.querySelector('.pagination__load-more');

        // Добавляем карточки
        newCards.forEach(function (card) {
          container.appendChild(card);
        });

        // Обновляем кнопку или удаляем блок
        if (newLoadMore) {
          var newBtn = newLoadMore.querySelector('.js-load-more');
          if (newBtn) {
            btn.setAttribute('data-url', newBtn.getAttribute('data-url'));
            btn.disabled = false;
            btn.textContent = btn.getAttribute('data-label') || 'Load more';
          }
        } else {
          loadMoreWrap.remove();
        }
      })
      .catch(function () {
        btn.disabled = false;
        btn.textContent = 'Error. Try again.';
      });
  });
})();