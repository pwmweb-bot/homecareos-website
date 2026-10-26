// Help centre: search filter on /help.html, and "Was this helpful?" on articles.
// No backend. A click is sent to Google Analytics only if the visitor has
// accepted cookies (Consent Mode holds it otherwise).
(function () {
  var input = document.getElementById('help-search-input');
  if (input) {
    var cards = Array.prototype.slice.call(document.querySelectorAll('.help-role .help-card'));
    var sections = Array.prototype.slice.call(document.querySelectorAll('.help-role'));
    var start = document.getElementById('getting-started');
    var empty = document.getElementById('help-empty');
    var count = document.getElementById('help-search-count');
    var run = function () {
      var words = input.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
      var shown = 0;
      cards.forEach(function (c) {
        var hay = c.getAttribute('data-search') || '';
        var ok = words.every(function (w) { return hay.indexOf(w) !== -1; });
        c.hidden = !ok;
        if (ok) shown++;
      });
      sections.forEach(function (s) {
        s.hidden = !s.querySelector('.help-card:not([hidden])');
      });
      if (start) start.hidden = words.length > 0;
      if (empty) empty.hidden = shown > 0;
      if (count) count.textContent = words.length ? (shown === 1 ? '1 guide found' : shown + ' guides found') : '';
    };
    input.addEventListener('input', run);
    var q = new URLSearchParams(window.location.search).get('q');
    if (q) { input.value = q; run(); }
  }

  document.querySelectorAll('.help-feedback').forEach(function (box) {
    box.querySelectorAll('[data-helpful]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var answer = btn.getAttribute('data-helpful');
        box.querySelectorAll('[data-helpful]').forEach(function (b) { b.disabled = true; });
        box.querySelectorAll('.help-feedback-thanks').forEach(function (p) {
          p.hidden = p.getAttribute('data-for') !== answer;
        });
        if (typeof window.gtag === 'function') {
          window.gtag('event', 'help_feedback', { article: box.getAttribute('data-article'), helpful: answer });
        }
      });
    });
  });
})();
