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
 *
 * While playing, the video gets .is-on and its host gets .is-playing (and
 * loses .is-paused), so a poster can fade out or a caption can run.
 */
(function () {
  'use strict';

  var vids = document.querySelectorAll('video[data-inview-video]');
  if (!vids.length) return;

  var mq = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  function reduced() { return !!(mq && mq.matches); }

  function host(v) {
    return v.closest('.rota-video, .hero-video, .shot-video') || v.parentNode;
  }

  function setPlaying(v, playing) {
    if (playing) {
      v.classList.add('is-on');
      var h = host(v);
      if (h) {
        h.classList.add('is-playing');
        h.classList.remove('is-paused');
      }
    } else {
      v.classList.remove('is-on');
      var h2 = host(v);
      if (h2) {
        h2.classList.remove('is-playing');
        h2.classList.add('is-paused');
      }
    }
  }

  function setLabel(btn, playing) {
    if (!btn) return;
    btn.textContent = playing ? 'Pause animation' : 'Play animation';
    btn.setAttribute('aria-pressed', playing ? 'false' : 'true');
  }

  function attachSources(v) {
    if (v._hcosSources) return;
    var webm = v.getAttribute('data-src-webm');
    var mp4 = v.getAttribute('data-src-mp4');
    if (!webm && !mp4) return;
    v._hcosSources = true;
    if (webm) {
      var s1 = document.createElement('source');
      s1.src = webm;
      s1.type = 'video/webm';
      v.appendChild(s1);
    }
    if (mp4) {
      var s2 = document.createElement('source');
      s2.src = mp4;
      s2.type = 'video/mp4';
      v.appendChild(s2);
    }
    v.load();
  }

  function attachPoster(v) {
    var src = v.getAttribute('data-poster');
    if (src && !v.getAttribute('poster')) v.setAttribute('poster', src);
  }

  function tryPlay(v) {
    if (reduced() || v._hcosPaused || v._hcosInView === false) return;
    attachPoster(v);
    attachSources(v);
    v.muted = true;
    var p = v.play();
    if (p && p.catch) p.catch(function () {});
  }

  function whenReady(v, fn) {
    var defer = v.getAttribute('data-inview-defer');
    if (!defer) { fn(); return; }
    function go() {
      // Hero loops should not compete with fonts or LCP. Wait until the
      // window has loaded, then give the main thread a short idle gap.
      var delay = 1200;
      if (window.requestIdleCallback) {
        requestIdleCallback(function () { setTimeout(fn, delay); }, { timeout: delay + 800 });
      } else {
        setTimeout(fn, delay);
      }
    }
    if (document.readyState === 'complete') go();
    else window.addEventListener('load', go, { once: true });
  }

  for (var i = 0; i < vids.length; i++) {
    (function (v) {
      v.muted = true;
      v.addEventListener('play', function () { setPlaying(v, true); });
      v.addEventListener('pause', function () { setPlaying(v, false); });
      var btn = v.parentNode && v.parentNode.querySelector('.rota-video-toggle');
      if (btn && !reduced()) {
        btn.hidden = false;
        setLabel(btn, true);
        btn.addEventListener('click', function (e) {
          e.preventDefault();
          e.stopPropagation();
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
      var v = e.target;
      if (e.isIntersecting) {
        v._hcosInView = true;
        whenReady(v, function () { tryPlay(v); });
      } else {
        v._hcosInView = false;
        v.pause();
      }
    });
  }, { rootMargin: '150px 0px', threshold: 0.2 });

  for (var k = 0; k < vids.length; k++) io.observe(vids[k]);

  if (mq && mq.addEventListener) {
    mq.addEventListener('change', function () {
      if (!reduced()) return;
      for (var m = 0; m < vids.length; m++) {
        vids[m].pause();
        vids[m].currentTime = 0;
        setPlaying(vids[m], false);
      }
    });
  }
})();
