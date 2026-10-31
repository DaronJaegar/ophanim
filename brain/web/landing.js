/* Landing: particle brain (three.js Points, scroll-morphed through 4 shapes), step switching,
   anime.js scramble + staggered reveals, live preview numbers. Reduced motion: no morph/rotation, final states shown. */
import * as THREE from './vendor/three.module.min.js';

const A = window.anime;
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const mobile = matchMedia('(max-width: 820px)');

/* ---------------- step switching ---------------- */
const story = document.getElementById('story');
const steps = [...document.querySelectorAll('.step')];
const bars = [...document.querySelectorAll('.progress li')];
const hud = document.getElementById('hud-step');
const NAMES = ['/00 brain', '/01 one brain', '/02 every path', '/03 wheels of eyes'];
let activeStep = 0;

function scramble(el, delay = 0) {
  if (!A || reduce || !A.scrambleText) return;
  A.animate(el, { innerHTML: A.scrambleText({ chars: 'uppercase', cursor: '_' }), duration: 900, delay });
}
function setStep(i) {
  if (i === activeStep) return;
  activeStep = i;
  steps.forEach((s, k) => { s.classList.toggle('is-active', k === i); s.setAttribute('aria-hidden', k === i ? 'false' : 'true'); });
  bars.forEach((b, k) => b.classList.toggle('on', k <= i));
  hud.textContent = NAMES[i];
  steps[i].querySelectorAll('[data-scramble]').forEach((el, k) => scramble(el, k * 120));
}
bars[0].classList.add('on');

function storyProgress() {           // 0..3 across the pinned section
  const r = story.getBoundingClientRect(), span = story.offsetHeight - innerHeight;
  return span > 0 ? Math.min(3, Math.max(0, (-r.top / span) * 3.6)) : 0;
}
addEventListener('scroll', () => { if (!mobile.matches) setStep(Math.min(3, Math.floor(storyProgress() + 0.35))); }, { passive: true });

// hero headline: decode on load (A2 text scramble, ~80-100 ms per character in the inspo)
document.querySelectorAll('.step[data-step="0"] [data-scramble]').forEach((el, k) => scramble(el, 200 + k * 160));

/* ---------------- staggered reveals (A7) ---------------- */
if (A && !reduce && 'IntersectionObserver' in window) {
  const groups = [...document.querySelectorAll('.cards, .timeline')];
  groups.forEach(g => [...g.children].forEach(c => c.classList.add('pre')));
  const io = new IntersectionObserver(entries => entries.forEach(e => {
    if (!e.isIntersecting) return;
    io.unobserve(e.target);
    A.animate([...e.target.children], { opacity: [0, 1], translateY: [24, 0], duration: 700, ease: 'outExpo', delay: A.stagger(90) });
  }), { threshold: 0.12 });
  groups.forEach(g => io.observe(g));
}

/* ---------------- marquee pause button ---------------- */
const mq = document.querySelector('.marquee'), mqb = document.querySelector('.marquee-toggle');
mqb && mqb.addEventListener('click', () => {
  const p = mq.classList.toggle('paused'); mqb.setAttribute('aria-pressed', p); mqb.textContent = p ? '▶' : '❚❚';
  mqb.setAttribute('aria-label', p ? 'Play the moving strip' : 'Pause the moving strip');
});

/* ---------------- live preview numbers ---------------- */
async function live() {
  try {
    const g = await (await fetch('/graph', { cache: 'no-store' })).json();
    document.getElementById('pv-risk').textContent = g.risk;
    document.getElementById('pv-open').textContent = g.open_paths;
    if (g.one_fix) document.getElementById('pv-fix').textContent = g.one_fix.text;
    const a = await (await fetch('/audit/verify', { cache: 'no-store' })).json();
    const chip = document.getElementById('pv-audit');
    chip.textContent = a.ok ? 'Audit verified' : `Audit broken @ ${a.broken_at}`;
    chip.className = 'chip ' + (a.ok ? 'lime' : 'red');
    document.getElementById('pv-live').textContent = 'LIVE · updated ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch { /* brain not reachable: keep the static demo numbers */ }
}
live(); setInterval(() => { if (!document.hidden) live(); }, 5000);

/* ---------------- particle brain (A8) ---------------- */
const canvas = document.getElementById('particles');
let renderer;
try { renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true }); }
catch { document.documentElement.classList.add('no-webgl'); }

if (renderer) {
  const N = mobile.matches ? 1600 : 2600;           // UI UX Pro Max: start 1000-3000 points
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
  camera.position.set(0, 0, 7.2);
  const rnd = (() => { let s = 7; return () => (s = (s * 16807) % 2147483647) / 2147483647; })();  // seeded, same picture every load
  const gauss = () => { let u = 0, v = 0; while (!u) u = rnd(); while (!v) v = rnd(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };
  const unit = () => { const z = rnd() * 2 - 1, t = rnd() * Math.PI * 2, r = Math.sqrt(1 - z * z); return [r * Math.cos(t), z, r * Math.sin(t)]; };

  // shape 0: brain (lateral view; two hemispheres with folds, cerebellum, stem)
  function brain() {
    const p = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) {
      let x, y, z; const k = rnd();
      if (k < 0.82) {
        const [dx, dy, dz] = unit();
        const fold = 1 + 0.07 * Math.sin(9 * dx + 3) * Math.sin(11 * dy) * Math.cos(7 * dz);
        x = dx * 1.62 * fold; y = dy * 1.12 * fold; z = dz * 1.28 * fold;
        if (y < -0.42) y = -0.42 + (y + 0.42) * 0.35;
        z += Math.sign(z || 1) * 0.08;                           // the fissure between hemispheres
        y += 0.15;
      } else if (k < 0.95) {
        const [dx, dy, dz] = unit();
        x = -1.0 + dx * 0.55; y = -0.62 + dy * 0.32; z = dz * 0.78;
        y = Math.round(y * 14) / 14 + gauss() * 0.01;            // striations
      } else {
        const t = rnd(), a = rnd() * Math.PI * 2;
        x = -0.45 - t * 0.2 + Math.cos(a) * 0.14; y = -0.55 - t * 0.85; z = Math.sin(a) * 0.14;
      }
      p.set([x * 1.15, y * 1.15, z * 1.15], i * 3);
    }
    return p;
  }
  // shape 1: globe (latitude/longitude shell: "everything in one place")
  function globe() {
    const p = new Float32Array(N * 3), R = 1.9;
    for (let i = 0; i < N; i++) {
      let lat, lon;
      if (rnd() < 0.5) { lat = (Math.floor(rnd() * 9) - 4) * (Math.PI / 10); lon = rnd() * Math.PI * 2; }
      else { lon = Math.floor(rnd() * 12) * (Math.PI / 6); lat = (rnd() - 0.5) * Math.PI; }
      p.set([R * Math.cos(lat) * Math.cos(lon), R * Math.sin(lat), R * Math.cos(lat) * Math.sin(lon)], i * 3);
    }
    return p;
  }
  // shape 2: the attack graph (same 8 nodes as the console), clusters + edges
  const NODES = { attacker: [-2.3, 0, 0], gmail: [-0.8, 1.1, 0.3], drive: [-0.8, 0, -0.3], pc: [-0.8, -1.1, 0.2],
    bank: [0.7, 1.5, 0], invoices: [0.7, 0.5, 0.3], money: [2.2, 0.9, 0], records: [2.2, -0.8, 0] };
  const EDGES = [['attacker', 'gmail'], ['attacker', 'drive'], ['attacker', 'pc'], ['gmail', 'bank'], ['gmail', 'invoices'],
    ['bank', 'money'], ['invoices', 'money'], ['drive', 'records'], ['pc', 'records'], ['pc', 'drive']];
  const keys = Object.keys(NODES);
  function network() {
    const p = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) {
      let v;
      if (rnd() < 0.55) { const n = NODES[keys[Math.floor(rnd() * keys.length)]], big = /money|records/.test(keys[0]) ? 1 : 1; v = [n[0] + gauss() * 0.13 * big, n[1] + gauss() * 0.13, n[2] + gauss() * 0.13]; }
      else { const [a, b] = EDGES[Math.floor(rnd() * EDGES.length)], t = rnd(), A1 = NODES[a], B1 = NODES[b]; v = [A1[0] + (B1[0] - A1[0]) * t + gauss() * 0.02, A1[1] + (B1[1] - A1[1]) * t + gauss() * 0.02, A1[2] + (B1[2] - A1[2]) * t + gauss() * 0.02]; }
      p.set(v, i * 3);
    }
    return p;
  }
  // shape 3: the Ophanim — three tilted rings with eyes, turning (computed per frame)
  const ringData = new Float32Array(N * 4);   // ring index, angle, eye flag, jitter
  const RINGS = [{ r: 2.0, tilt: [0.35, 0, 0.2], speed: 0.18 }, { r: 1.5, tilt: [-0.9, 0.5, 0], speed: -0.27 }, { r: 1.0, tilt: [0.6, -0.8, 0.4], speed: 0.4 }];
  for (let i = 0; i < N; i++) {
    const ring = i % 3, eyes = [10, 8, 6][ring], isEye = rnd() < 0.42;
    const ang = isEye ? (Math.floor(rnd() * eyes) / eyes) * Math.PI * 2 : rnd() * Math.PI * 2;
    ringData.set([ring, ang, isEye ? 1 : 0, rnd()], i * 4);
  }
  const eul = RINGS.map(R => new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(...R.tilt)));
  const tmp = new THREE.Vector3();
  function rings(out, time) {
    for (let i = 0; i < N; i++) {
      const ring = ringData[i * 4], R = RINGS[ring], ang = ringData[i * 4 + 1] + time * R.speed, eye = ringData[i * 4 + 2], j = ringData[i * 4 + 3];
      let rr = R.r, y = 0;
      if (eye) { const e = j * Math.PI * 2; rr += Math.cos(e) * 0.13; y = Math.sin(e) * 0.07 * (j < 0.15 ? 0.2 : 1); if (j < 0.15) rr = R.r + (j - 0.075) * 0.6; }
      else { rr += (j - 0.5) * 0.04; }
      tmp.set(Math.cos(ang) * rr, y, Math.sin(ang) * rr).applyMatrix4(eul[ring]);
      out[i * 3] = tmp.x; out[i * 3 + 1] = tmp.y; out[i * 3 + 2] = tmp.z;
    }
    return out;
  }

  const shapes = [brain(), globe(), network(), new Float32Array(N * 3)];
  const pos = new Float32Array(shapes[0]);
  const col = new Float32Array(N * 3);
  const graphite = new THREE.Color('#2B2B2B'), violet = new THREE.Color('#7A3FE0');
  const delay = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    (ringData[i * 4 + 2] && rnd() < 0.55 ? violet : rnd() < 0.18 ? violet : graphite).toArray(col, i * 3);
    delay[i] = rnd();
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  // triangle sprite (the inspo's particles are small triangles)
  const tc = document.createElement('canvas'); tc.width = tc.height = 64;
  const g2 = tc.getContext('2d'); g2.fillStyle = '#fff'; g2.beginPath(); g2.moveTo(32, 6); g2.lineTo(60, 56); g2.lineTo(4, 56); g2.closePath(); g2.fill();
  const tex = new THREE.CanvasTexture(tc); tex.colorSpace = THREE.SRGBColorSpace;
  const mat = new THREE.PointsMaterial({ size: 0.075, map: tex, vertexColors: true, transparent: true, alphaTest: 0.4, sizeAttenuation: true, depthWrite: false });
  const points = new THREE.Points(geo, mat);
  const group = new THREE.Group(); group.add(points); scene.add(group);
  group.rotation.set(0.12, -0.5, 0);

  function resize() {
    const r = canvas.getBoundingClientRect();
    renderer.setSize(r.width, r.height, false);
    camera.aspect = r.width / Math.max(1, r.height); camera.updateProjectionMatrix();
    camera.position.z = camera.aspect < 0.9 ? 9 : 7.2;
  }
  new ResizeObserver(resize).observe(canvas); resize();

  let px = 0, py = 0;
  addEventListener('pointermove', e => { px = e.clientX / innerWidth - 0.5; py = e.clientY / innerHeight - 0.5; }, { passive: true });
  const ease = t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

  let visible = true;
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible) loop(); }).observe(canvas);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) loop(); });
  let running = false, smooth = 0;

  function frame(now) {
    const time = now / 1000;
    const target = mobile.matches ? (time / 6) % 4 : storyProgress();     // mobile: no pinning, cycle slowly
    smooth += (target - smooth) * (reduce ? 1 : 0.08);
    const s = Math.min(3, Math.max(0, smooth)), a = Math.min(2, Math.floor(s)), local = s - a;
    rings(shapes[3], reduce ? 0 : time);
    const A0 = shapes[a], B0 = shapes[Math.min(3, a + 1)];
    for (let i = 0; i < N; i++) {
      const t = reduce ? Math.round(local) : ease(Math.min(1, Math.max(0, (local * 1.5) - delay[i] * 0.5)));
      const k = i * 3;
      pos[k] = A0[k] + (B0[k] - A0[k]) * t; pos[k + 1] = A0[k + 1] + (B0[k + 1] - A0[k + 1]) * t; pos[k + 2] = A0[k + 2] + (B0[k + 2] - A0[k + 2]) * t;
    }
    geo.attributes.position.needsUpdate = true;
    if (!reduce) { group.rotation.y += 0.0025; group.rotation.x += ((py * 0.3 + 0.12) - group.rotation.x) * 0.05; points.rotation.y = px * 0.4; }
    renderer.render(scene, camera);
  }
  function loop() {
    if (running) return; running = true;
    const tick = now => { if (!visible || document.hidden) { running = false; return; } frame(now); if (reduce) { running = false; return; } requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  }
  if (reduce) addEventListener('scroll', () => requestAnimationFrame(frame), { passive: true });
  loop();
}
