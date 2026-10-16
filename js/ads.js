/*
 * Google Ads helpers for the marketing site.
 *
 * Demo request (AW-18012658601/jZp7CNWB954dEKm3jY1D) fires once per successful
 * submit, and only then:
 *   - contact.html when /api/contact returns success
 *   - booking.html when Calendly reports calendly.event_scheduled
 * It does not fire on page view or on a click.
 *
 * The sign-up conversion is completed in the app at /onboard and is not sent
 * from this site.
 *
 * click_to_call and click_to_email are separate events so matching Google Ads
 * conversions can be created later. They are not the demo-request conversion.
 *
 * gclid and UTM parameters already on the landing URL are copied onto
 * same-site links and onto "Get started for free" links to the app, so
 * auto-tagging survives the hop to app.homecareos.co.uk. Nothing is written
 * to a cookie or to storage.
 */
(function () {
  'use strict';

  var DEMO_SEND_TO = 'AW-18012658601/jZp7CNWB954dEKm3jY1D';
  var ATTR_KEYS = ['gclid', 'gbraid', 'wbraid', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'utm_id'];
  var lastDemoAt = 0;

  function trackDemoRequest() {
    var now = Date.now();
    if (now - lastDemoAt < 3000) return;
    lastDemoAt = now;
    if (typeof window.__loadGTM === 'function') window.__loadGTM();
    if (typeof window.gtag !== 'function') return;
    window.gtag('event', 'conversion', { 'send_to': DEMO_SEND_TO });
  }
  window.hcosTrackDemoRequest = trackDemoRequest;

  function pagePath() {
    return (window.location.pathname || '/').replace(/\/+$/, '') || '/';
  }

  function onCalendlyMessage(event) {
    if (!/\/booking(?:\.html)?$/.test(pagePath())) return;
    if (event.origin !== 'https://calendly.com') return;
    var data = event.data || {};
    if (data.event !== 'calendly.event_scheduled') return;
    trackDemoRequest();
  }
  window.addEventListener('message', onCalendlyMessage);

  function currentAttribution() {
    var qs = new URLSearchParams(window.location.search);
    var found = {};
    ATTR_KEYS.forEach(function (key) {
      var value = qs.get(key);
      if (value) found[key] = value;
    });
    return found;
  }

  function linkText(anchor) {
    return (anchor.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
  }

  function shouldCarry(anchor, url, params) {
    if (!params || !Object.keys(params).length) return false;
    if (url.protocol !== 'http:' && url.protocol !== 'https:') return false;
    if (url.origin === window.location.origin) {
      if (/\.(pdf|zip|png|jpe?g|gif|webp|svg|css|js|xml|txt|ico|woff2?)$/i.test(url.pathname)) return false;
      return true;
    }
    return url.hostname === 'app.homecareos.co.uk' && linkText(anchor) === 'get started for free';
  }

  function withAttribution(raw, params) {
    var hash = '';
    var base = raw;
    var hashAt = base.indexOf('#');
    if (hashAt >= 0) {
      hash = base.slice(hashAt);
      base = base.slice(0, hashAt);
    }
    var queryAt = base.indexOf('?');
    var path = queryAt >= 0 ? base.slice(0, queryAt) : base;
    var qs = new URLSearchParams(queryAt >= 0 ? base.slice(queryAt + 1) : '');
    var changed = false;
    ATTR_KEYS.forEach(function (key) {
      if (params[key] && !qs.has(key)) {
        qs.set(key, params[key]);
        changed = true;
      }
    });
    if (!changed) return raw;
    var query = qs.toString();
    return path + (query ? '?' + query : '') + hash;
  }

  function decorateAnchor(anchor, params) {
    var raw = anchor.getAttribute('href');
    if (!raw || raw.charAt(0) === '#' || /^(mailto:|tel:|javascript:)/i.test(raw)) return;
    var url;
    try { url = new URL(raw, window.location.href); } catch (err) { return; }
    if (!shouldCarry(anchor, url, params)) return;
    var next = withAttribution(raw, params);
    if (next !== raw) anchor.setAttribute('href', next);
  }

  function decorateAll() {
    var params = currentAttribution();
    if (!Object.keys(params).length) return;
    var links = document.querySelectorAll('a[href]');
    for (var i = 0; i < links.length; i++) decorateAnchor(links[i], params);
  }

  document.addEventListener('click', function (event) {
    var anchor = event.target && event.target.closest ? event.target.closest('a[href]') : null;
    if (!anchor) return;
    var href = anchor.getAttribute('href') || '';
    if (/^tel:/i.test(href)) {
      if (typeof window.__loadGTM === 'function') window.__loadGTM();
      if (typeof window.gtag === 'function') {
        window.gtag('event', 'click_to_call', {
          'link_url': anchor.href,
          'page_path': pagePath()
        });
      }
    } else if (/^mailto:/i.test(href)) {
      if (typeof window.__loadGTM === 'function') window.__loadGTM();
      if (typeof window.gtag === 'function') {
        window.gtag('event', 'click_to_email', {
          'link_url': anchor.href.split('?')[0],
          'page_path': pagePath()
        });
      }
    }
    decorateAnchor(anchor, currentAttribution());
  }, true);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', decorateAll);
  } else {
    decorateAll();
  }
})();
