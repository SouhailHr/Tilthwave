/**
 * Tilthwave animated field background (brand handoff, login/field-background.js), typed.
 *
 *   const stop = mountFieldBackground(canvas); // in an effect, on mount
 *   stop();                                    // on unmount: no animation frame or listener survives
 *
 * The canvas should be position:fixed; inset:0; width:100%; height:100%. Under
 * prefers-reduced-motion it draws one still frame (and redraws it on resize), never a blank
 * canvas. Only touches `window` when called, so importing it during server rendering is safe.
 *
 * Differences from the handoff file: the deviceorientation listener is removed on cleanup too
 * (the original left it attached), and the pointer/orientation handlers are guarded until the
 * first build() has sized the field.
 */

type Furrow = {
  y: number;
  amp: number;
  wl: number;
  speed: number;
  width: number;
  alpha: number;
  phase: number;
  depth: number;
  hue: number;
};
type SensorNode = { f: Furrow; u: number; next: number; r: number; pulse?: number };
type Signal = { f: Furrow; u: number; dir: number; born: number; life: number };

const LOAM = [30, 42, 28] as const;
const DEEP = [17, 26, 16] as const;
const HUES = ["140,203,94", "79,154,74", "47,107,58"] as const;
const col = (rgb: readonly number[], a: number) => `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${a})`;

export function mountFieldBackground(canvas: HTMLCanvasElement): () => void {
  const ctx = canvas.getContext("2d");
  if (!ctx) return () => {};
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let W = 0;
  let H = 0;
  let furrows: Furrow[] = [];
  let nodes: SensorNode[] = [];
  let signals: Signal[] = [];
  let t = 0;
  const px = { x: 0, y: 0 };
  const target = { x: 0, y: 0 };

  function build() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth;
    H = window.innerHeight;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
    furrows = [];
    nodes = [];
    signals = [];
    const n = Math.max(9, Math.round(H / 62));
    for (let i = 0; i < n; i++) {
      const d = i / (n - 1); // 0 = horizon (far), 1 = foreground
      furrows.push({
        y: H * (0.3 + 0.74 * d * d), // perspective: rows bunch near the horizon
        amp: 6 + 34 * d,
        wl: 260 + 520 * d,
        speed: (0.12 + 0.55 * d) * (i % 2 ? 1 : -1),
        width: 1 + 5.5 * d,
        alpha: 0.1 + 0.55 * d,
        phase: Math.random() * 1000,
        depth: d,
        hue: i % 3,
      });
    }
    // sensor nodes sit on the mid/foreground furrows
    furrows.forEach((f, i) => {
      if (f.depth < 0.25 || i % 2) return;
      const count = 1 + Math.floor(Math.random() * 2);
      for (let k = 0; k < count; k++) {
        nodes.push({ f, u: 0.12 + Math.random() * 0.76, next: t + Math.random() * 6, r: 2 + 3 * f.depth });
      }
    });
  }

  function furrowY(f: Furrow, x: number, time: number) {
    const k = ((x + f.phase + time * f.speed * 40) / f.wl) * Math.PI * 2;
    return f.y + Math.sin(k) * f.amp + Math.sin(k * 0.37 + 1.3) * f.amp * 0.35;
  }

  function drawSky() {
    const c = ctx!;
    const g = c.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, col(DEEP, 1));
    g.addColorStop(0.55, col(LOAM, 1));
    g.addColorStop(1, "#213e26");
    c.fillStyle = g;
    c.fillRect(0, 0, W, H);
    // amber dawn glow, breathing
    const b = 0.22 + 0.06 * Math.sin(t * 0.35);
    const r = c.createRadialGradient(
      W * 0.72 + px.x * 30,
      H * 0.3 + px.y * 20,
      0,
      W * 0.72,
      H * 0.3,
      Math.max(W, H) * 0.55,
    );
    r.addColorStop(0, `rgba(227,163,59,${b})`);
    r.addColorStop(0.5, "rgba(227,163,59,0.05)");
    r.addColorStop(1, "rgba(227,163,59,0)");
    c.fillStyle = r;
    c.fillRect(0, 0, W, H);
    // horizon haze
    const hz = c.createLinearGradient(0, H * 0.22, 0, H * 0.42);
    hz.addColorStop(0, "rgba(140,203,94,0)");
    hz.addColorStop(1, "rgba(140,203,94,0.07)");
    c.fillStyle = hz;
    c.fillRect(0, H * 0.22, W, H * 0.2);
  }

  function drawFurrows() {
    const c = ctx!;
    c.lineCap = "round";
    for (const f of furrows) {
      const ox = px.x * 40 * f.depth;
      const oy = px.y * 24 * f.depth;
      c.beginPath();
      for (let x = -40; x <= W + 40; x += 6) c.lineTo(x + ox, furrowY(f, x, t) + oy);
      // soft glow under the brighter foreground rows
      if (f.depth > 0.6) {
        c.strokeStyle = `rgba(${HUES[f.hue]},${f.alpha * 0.25})`;
        c.lineWidth = f.width * 3.2;
        c.stroke();
      }
      c.strokeStyle = `rgba(${HUES[f.hue]},${f.alpha})`;
      c.lineWidth = f.width;
      c.stroke();
    }
  }

  function drawNodes() {
    const c = ctx!;
    for (const n of nodes) {
      const f = n.f;
      const x = n.u * W;
      const y = furrowY(f, x, t) + px.y * 24 * f.depth;
      const ox = px.x * 40 * f.depth;
      if (!reduce && t > n.next) {
        n.next = t + 3.5 + Math.random() * 6;
        n.pulse = t;
        signals.push({ f, u: n.u, dir: Math.random() < 0.5 ? -1 : 1, born: t, life: 2.6 + Math.random() * 1.6 });
      }
      const age = n.pulse === undefined ? 99 : t - n.pulse;
      if (age < 2.4) {
        const p = age / 2.4;
        c.beginPath();
        c.arc(x + ox, y, n.r + p * 60 * f.depth, 0, Math.PI * 2);
        c.strokeStyle = `rgba(227,163,59,${(1 - p) * 0.7})`;
        c.lineWidth = 1.5;
        c.stroke();
      }
      const glow = c.createRadialGradient(x + ox, y, 0, x + ox, y, n.r * 5);
      glow.addColorStop(0, "rgba(227,163,59,.55)");
      glow.addColorStop(1, "rgba(227,163,59,0)");
      c.fillStyle = glow;
      c.beginPath();
      c.arc(x + ox, y, n.r * 5, 0, Math.PI * 2);
      c.fill();
      c.fillStyle = "#E3A33B";
      c.beginPath();
      c.arc(x + ox, y, n.r, 0, Math.PI * 2);
      c.fill();
    }
  }

  function drawSignals() {
    const c = ctx!;
    signals = signals.filter((s) => t - s.born < s.life);
    for (const s of signals) {
      const p = (t - s.born) / s.life;
      const f = s.f;
      const ox = px.x * 40 * f.depth;
      const oy = px.y * 24 * f.depth;
      const head = s.u * W + s.dir * p * W * 0.55;
      const tail = 90 * f.depth;
      c.beginPath();
      for (let i = 0; i <= 18; i++) {
        const x = head - s.dir * (i / 18) * tail;
        c.lineTo(x + ox, furrowY(f, x, t) + oy);
      }
      const g = c.createLinearGradient(head + ox, 0, head - s.dir * tail + ox, 0);
      const a = Math.sin(p * Math.PI) * 0.9;
      g.addColorStop(0, `rgba(238,242,228,${a})`);
      g.addColorStop(0.35, `rgba(227,163,59,${a * 0.7})`);
      g.addColorStop(1, "rgba(227,163,59,0)");
      c.strokeStyle = g;
      c.lineWidth = f.width + 1;
      c.lineCap = "round";
      c.stroke();
      c.fillStyle = `rgba(255,236,200,${a})`;
      c.beginPath();
      c.arc(head + ox, furrowY(f, head, t) + oy, f.width * 0.7 + 1, 0, Math.PI * 2);
      c.fill();
    }
  }

  let last = performance.now();
  function frame(now: number) {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    if (!reduce) t += dt;
    px.x += (target.x - px.x) * 0.04;
    px.y += (target.y - px.y) * 0.04;
    drawSky();
    drawFurrows();
    drawSignals();
    drawNodes();
  }

  const onResize = () => {
    build();
    if (reduce) frame(performance.now());
  };
  const onMove = (e: PointerEvent) => {
    if (!W || !H) return;
    target.x = e.clientX / W - 0.5;
    target.y = e.clientY / H - 0.5;
  };
  const onTilt = (e: DeviceOrientationEvent) => {
    if (e.gamma == null || e.beta == null) return;
    target.x = Math.max(-0.5, Math.min(0.5, e.gamma / 60));
    target.y = Math.max(-0.5, Math.min(0.5, (e.beta - 45) / 90));
  };
  window.addEventListener("resize", onResize);
  window.addEventListener("pointermove", onMove, { passive: true });
  window.addEventListener("deviceorientation", onTilt);

  let raf = 0;
  const loop = (now: number) => {
    frame(now);
    if (!reduce) raf = window.requestAnimationFrame(loop);
  };
  build();
  raf = window.requestAnimationFrame(loop);

  return () => {
    window.cancelAnimationFrame(raf);
    window.removeEventListener("resize", onResize);
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("deviceorientation", onTilt);
  };
}
