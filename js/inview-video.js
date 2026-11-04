/*
 * HomecareOS — play silent product animations only while they are on screen
 *
 * Usage:
 *   <figure class="rota-video">
 *     <video data-inview-video muted loop playsinline preload="none" poster="...">
 *       <source src="....webm" type="video/webm">
 *       <source src="....mp4" type="video/mp4">
 *     </video>
 *     <button type="button" class="rota-video-toggle" hidden>Pause animation</button>
 *   </figure>
 *
 * The video downloads nothing until it is near the viewport (preload="none"),
 * then plays muted and loops. It pauses when scrolled away. Visitors who ask
 * for reduced motion only ever see the poster. The toggle gives everyone a way
 * to stop it (WCAG 2.2.2).
 */
(function () {
  'use strict';

  var vids = document.querySelectorAll('video[data-inview-video]');
  if (!vids.length) return;

  var mq = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  function reduced() { return !!(mq && mq.matches); }

  function setLabel(btn, playing) {
    if (!btn) return;
    btn.textContent = playing ? 'Pause animation' : 'Play animation';
    btn.setAttribute('aria-pressed', playing ? 'false' : 'true');
  }

  function tryPlay(v) {
    if (reduced() || v._hcosPaused) return;
    v.muted = true;
    var p = v.play();
    if (p && p.catch) p.catch(function () {});
  }

  for (var i = 0; i < vids.length; i++) {
    (function (v) {
      v.muted = true;
      var btn = v.parentNode && v.parentNode.querySelector('.rota-video-toggle');
      if (btn && !reduced()) {
        btn.hidden = false;
        setLabel(btn, true);
        btn.addEventListener('click', function () {
          v._hcosPaused = !v._hcosPaused;
          if (v._hcosPaused) { v.pause(); setLabel(btn, false); }
          else { tryPlay(v); setLabel(btn, true); }
        });
      }
    })(vids[i]);
  }

  if (!('IntersectionObserver' in window)) {
    for (var j = 0; j < vids.length; j++) tryPlay(vids[j]);
    return;
  }

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) tryPlay(e.target);
      else e.target.pause();
    });
  }, { rootMargin: '150px 0px', threshold: 0.2 });

  for (var k = 0; k < vids.length; k++) io.observe(vids[k]);

  if (mq && mq.addEventListener) {
    mq.addEventListener('change', function () {
      if (!reduced()) return;
      for (var m = 0; m < vids.length; m++) { vids[m].pause(); vids[m].currentTime = 0; }
    });
  }
})();
