/* OPHANIM mark: concentric wheels covered in eyes (the Ophanim / "Thrones"), centre eye.
   Usage: <span data-ophanim-mark data-size="40" data-spin="slow"></span>
   Rings counter-rotate via anime.js (if loaded); pupils can follow the pointer (data-follow).
   Reduced motion: static. Hidden tab: paused.  window.OphanimMark.setAlert(true) turns pupils red + speeds up. */
(function () {
  const NS = 'http://www.w3.org/2000/svg';
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const el = (tag, attrs, parent) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; };

  // almond eye centred on (0,0), w = half width
  function eye(g, x, y, angle, w, pupils) {
    const e = el('g', { transform: `translate(${x.toFixed(2)} ${y.toFixed(2)}) rotate(${angle.toFixed(1)})`, class: 'eye' }, g);
    const h = w * 0.55;
    el('path', { d: `M${-w} 0 Q0 ${-h * 1.6} ${w} 0 Q0 ${h * 1.6} ${-w} 0Z`, fill: 'var(--paper,#F8F8F8)', stroke: 'var(--ink,#060606)', 'stroke-width': Math.max(0.9, w * 0.16) }, e);
    const p = el('circle', { r: (h * 0.75).toFixed(2), fill: 'var(--violet-text,#7A3FE0)', class: 'pupil' }, e);
    pupils.push({ p, max: w * 0.35 });
    return e;
  }

  function build(host) {
    const size = +host.dataset.size || 40, detailed = size >= 64;
    const svg = el('svg', { viewBox: '-50 -50 100 100', width: size, height: size, class: 'ophanim-mark', role: 'img', 'aria-label': 'Ophanim logo: wheels of eyes' });
    const pupils = [], rings = [];
    // [radius, eyes, eye half-width, stroke]
    const spec = detailed ? [[45, 10, 4.2, 2.2], [32, 7, 4.0, 2.2], [19, 5, 3.6, 2.2]] : [[44, 6, 6.5, 3.2], [28, 4, 6, 3.2]];
    spec.forEach(([r, n, w, sw], i) => {
      const g = el('g', { class: 'ring' }, svg);
      el('circle', { r, fill: 'none', stroke: 'var(--ink,#060606)', 'stroke-width': sw }, g);
      if (detailed) el('circle', { r: r - 3.2, fill: 'none', stroke: 'var(--ink,#060606)', 'stroke-width': 0.6, 'stroke-dasharray': '1 2.2' }, g);
      for (let k = 0; k < n; k++) {
        const a = (k / n) * Math.PI * 2 + i * 0.4;
        eye(g, Math.cos(a) * r, Math.sin(a) * r, (a * 180) / Math.PI + 90, w, pupils);
      }
      rings.push(g);
    });
    // gimbal: one tilted ring crossing the wheels ("a wheel within a wheel")
    if (detailed) el('ellipse', { rx: 45, ry: 14, fill: 'none', stroke: 'var(--violet-text,#7A3FE0)', 'stroke-width': 1.2, transform: 'rotate(-28)', opacity: .9 }, svg);
    const centre = eye(svg, 0, 0, 0, detailed ? 9 : 12, pupils);
    host.textContent = '';
    host.appendChild(svg);

    const ctl = { svg, pupils, rings, anims: [], speed: host.dataset.spin || 'slow' };
    const A = window.anime;
    if (A && !reduce && ctl.speed !== 'none') {
      const base = ctl.speed === 'fast' ? 14000 : 40000;
      rings.forEach((g, i) => {
        ctl.anims.push(A.animate(g, { rotate: i % 2 ? -360 : 360, duration: base * (1 - i * 0.22), ease: 'linear', loop: true }));
      });
      // occasional blink of the centre eye (not a fast loop: one blink every ~6 s)
      ctl.anims.push(A.animate(centre.firstChild, { scaleY: [1, .08, 1], duration: 260, ease: 'inOutQuad', loop: true, loopDelay: 6000, delay: 2500 }));
      centre.firstChild.style.transformBox = 'fill-box'; centre.firstChild.style.transformOrigin = 'center';
      document.addEventListener('visibilitychange', () => ctl.anims.forEach(a => document.hidden ? a.pause() : a.play()));
    }
    if (host.dataset.follow !== undefined && !reduce) {
      addEventListener('pointermove', ev => {
        const b = svg.getBoundingClientRect(), cx = b.left + b.width / 2, cy = b.top + b.height / 2;
        const dx = ev.clientX - cx, dy = ev.clientY - cy, d = Math.hypot(dx, dy) || 1;
        pupils.forEach(({ p, max }) => {
          // convert the screen direction into each eye's rotated frame
          const m = p.parentNode.getCTM(), inv = m && m.inverse();
          let ux = dx / d, uy = dy / d;
          if (inv) { const tx = inv.a * ux + inv.c * uy, ty = inv.b * ux + inv.d * uy, l = Math.hypot(tx, ty) || 1; ux = tx / l; uy = ty / l; }
          p.setAttribute('cx', (ux * max).toFixed(2)); p.setAttribute('cy', (uy * max * 0.6).toFixed(2));
        });
      }, { passive: true });
    }
    ctl.setAlert = on => {
      pupils.forEach(({ p }) => p.setAttribute('fill', on ? 'var(--red,#D92D20)' : 'var(--violet-text,#7A3FE0)'));
      ctl.anims.forEach(a => { if (a.speed !== undefined) a.speed = on ? 4 : 1; });
    };
    host._ophanim = ctl;
    return ctl;
  }

  function init() { document.querySelectorAll('[data-ophanim-mark]').forEach(h => { if (!h._ophanim) build(h); }); }
  window.OphanimMark = { build, init, setAlert(on) { document.querySelectorAll('[data-ophanim-mark]').forEach(h => h._ophanim && h._ophanim.setAlert(on)); } };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
