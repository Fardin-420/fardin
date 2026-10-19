import * as THREE from 'three';
import type { SceneFactory } from '../engine/Engine';
import { Particles, shell } from '../engine/particles';
import { chromeMaterials } from '../engine/chrome';
import {
  easeInCubic, easeInOutCubic, easeInOutSine, easeOutCubic, easeOutExpo, impulse, lerp, noise1, prng, range, shake,
} from '../engine/util';
import { camera, dust, glow } from './common';

// SCENE 03 — EVERY FRAME IS CODE
// The camera flies down a corridor of this engine's real source code. Glyphs
// detach as particles, assemble into geometry, a chrome 9:16 frame slams past
// on "every single frame", and everything resolves into a moving code-built
// structure on "written in code".

const KEYWORDS = /\b(const|let|return|export|import|from|function|new|if|for|type|class|float|vec2|vec3|vec4|uniform|void)\b/;

function codeTexture(code: string[], seed: number) {
  const W = 1024, H = 1280;
  const cv = document.createElement('canvas');
  cv.width = W;
  cv.height = H;
  const g = cv.getContext('2d')!;
  g.clearRect(0, 0, W, H);
  const r = prng(seed);
  const start = Math.floor(r() * Math.max(1, code.length - 60));
  const size = 25;
  g.font = `500 ${size}px 'NPC Mono', 'JetBrains Mono', monospace`;
  g.textBaseline = 'top';
  let y = 24;
  for (let i = start; i < start + 60 && y < H - 30; i++) {
    const line = code[i] ?? '';
    const indent = line.match(/^\s*/)![0].length;
    // Line number gutter.
    g.fillStyle = 'rgba(243,238,227,0.22)';
    g.fillText(String(i + 1).padStart(4, ' '), 16, y);
    let x = 96 + indent * size * 0.3;
    for (const tok of line.trim().split(/(\s+)/)) {
      if (KEYWORDS.test(tok)) g.fillStyle = '#ff3a26';
      else if (/^['"`]/.test(tok)) g.fillStyle = '#d9c9a8';
      else if (/^\/\//.test(tok)) g.fillStyle = 'rgba(243,238,227,0.35)';
      else g.fillStyle = 'rgba(243,238,227,0.92)';
      g.fillText(tok, x, y);
      x += g.measureText(tok).width;
    }
    y += size * 1.45;
  }
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}

/** 9:16 chrome frame (rounded rectangle tube). */
function chromeFrame(mat: THREE.Material) {
  const w = 1.8, h = 3.2, r = 0.18;
  const s = new THREE.Shape();
  s.moveTo(-w / 2 + r, -h / 2);
  s.lineTo(w / 2 - r, -h / 2);
  s.quadraticCurveTo(w / 2, -h / 2, w / 2, -h / 2 + r);
  s.lineTo(w / 2, h / 2 - r);
  s.quadraticCurveTo(w / 2, h / 2, w / 2 - r, h / 2);
  s.lineTo(-w / 2 + r, h / 2);
  s.quadraticCurveTo(-w / 2, h / 2, -w / 2, h / 2 - r);
  s.lineTo(-w / 2, -h / 2 + r);
  s.quadraticCurveTo(-w / 2, -h / 2, -w / 2 + r, -h / 2);
  const hole = new THREE.Path();
  const t = 0.07;
  hole.moveTo(-w / 2 + t, -h / 2 + t);
  hole.lineTo(-w / 2 + t, h / 2 - t);
  hole.lineTo(w / 2 - t, h / 2 - t);
  hole.lineTo(w / 2 - t, -h / 2 + t);
  hole.lineTo(-w / 2 + t, -h / 2 + t);
  s.holes.push(hole);
  const g = new THREE.ExtrudeGeometry(s, { depth: 0.12, bevelEnabled: true, bevelThickness: 0.02, bevelSize: 0.02, bevelSegments: 3, curveSegments: 10 });
  g.center();
  return new THREE.Mesh(g, mat);
}

export const S03: SceneFactory = (a, tl) => {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#010101');
  scene.fog = new THREE.FogExp2('#010101', 0.022);
  const cam = camera(42);
  const S = tl.scenes.find((s) => s.id === 'S03')!;
  const c = tl.cues;
  const code = a.codeText.split('\n');

  // Corridor of code panels.
  const panels: THREE.Mesh[] = [];
  const r = prng(303);
  const panelPts: number[] = [];
  const corridorLen = 70;
  for (let i = 0; i < 30; i++) {
    const z = 6 - i * (corridorLen / 30);
    const side = i % 4; // left, right, top, bottom-ish
    const ang = (side * Math.PI) / 2 + (r() - 0.5) * 0.5 + Math.PI / 4;
    const rad = 3.4 + r() * 1.4;
    const tex = codeTexture(code, 1000 + i);
    const m = new THREE.Mesh(
      new THREE.PlaneGeometry(3.2, 4.0),
      new THREE.MeshBasicMaterial({ map: tex, color: new THREE.Color(1.8, 1.8, 1.8), transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }),
    );
    m.position.set(Math.cos(ang) * rad * 0.75, Math.sin(ang) * rad * 1.25, z);
    m.lookAt(0, 0, z + 2.5);
    scene.add(m);
    panels.push(m);
    for (let k = 0; k < 900; k++) {
      const p = new THREE.Vector3((r() - 0.5) * 3.2, (r() - 0.5) * 4.0, 0).applyMatrix4(m.matrixWorld.compose(m.position, m.quaternion, m.scale));
      panelPts.push(p.x, p.y, p.z);
    }
  }

  // Structures travel with the camera so they stay framed while the world streams past.
  const rig = new THREE.Group();
  scene.add(rig);

  // Glyph particles: panel surfaces -> geodesic shell ("every effect").
  const N = 27000;
  const start = new Float32Array(panelPts.slice(0, N * 3));
  const geo = new THREE.IcosahedronGeometry(0.95, 5);
  const shellPts = new Float32Array(N * 3);
  const gp = geo.attributes.position;
  for (let i = 0; i < N; i++) {
    const j = i % gp.count;
    const jitter = 1 + (r() - 0.5) * 0.06;
    shellPts[i * 3] = gp.getX(j) * jitter;
    shellPts[i * 3 + 1] = gp.getY(j) * jitter;
    shellPts[i * 3 + 2] = gp.getZ(j) * jitter;
  }
  // Panel positions are in world space; the rig moves, so P1 lives in the scene.
  const p1 = new Particles(start, shellPts, 311);
  p1.u.uSize.value = 0.016;
  p1.u.uStagger.value = 0.6;
  p1.u.uRedRatio.value = 0.08;
  scene.add(p1.points);

  // Shell -> torus knot ("written in code").
  const knot = new THREE.TorusKnotGeometry(0.8, 0.22, 400, 40, 2, 3);
  const kp = knot.attributes.position;
  const knotPts = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) {
    const j = Math.floor(r() * kp.count);
    knotPts[i * 3] = kp.getX(j);
    knotPts[i * 3 + 1] = kp.getY(j);
    knotPts[i * 3 + 2] = kp.getZ(j);
  }
  const p2 = new Particles(shellPts.slice(), knotPts, 312);
  p2.u.uSize.value = 0.016;
  p2.u.uStagger.value = 0.45;
  p2.u.uRedRatio.value = 0.1;
  rig.add(p2.points);

  // Wireframe skeleton that fades in under the knot for structure.
  const wire = new THREE.LineSegments(
    new THREE.WireframeGeometry(new THREE.TorusKnotGeometry(0.8, 0.22, 120, 10, 2, 3)),
    new THREE.LineBasicMaterial({ color: '#ff2b1c', transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }),
  );
  rig.add(wire);

  const chrome = chromeMaterials(a.env);
  const frame = chromeFrame(chrome.face);
  scene.add(frame);
  const frameGlow = glow('#ff2b1c', 5, 0);
  scene.add(frameGlow);

  const d = dust(3000, [20, 30, 90], 333);
  scene.add(d.points);
  const key = new THREE.DirectionalLight('#fff4e6', 2);
  key.position.set(-2, 4, 6);
  scene.add(key, new THREE.PointLight('#ff2b1c', 20, 20, 1.5));

  const camZ = (t: number) => {
    const k = range(t, S.start, S.end);
    // Constant cruise with a surge through the frame.
    return lerp(8, -42, easeInOutSine(k) * 0.75 + k * 0.25) - 6 * easeInOutCubic(range(t, c.frame_hit - 0.35, c.frame_hit + 0.25));
  };

  return {
    id: 'S03',
    scene,
    camera: cam,
    update: ({ t }) => {
      const z = camZ(t);
      const vz = (camZ(t + 1 / 120) - camZ(t - 1 / 120)) * 60;
      const [sx, sy] = shake(t - c.frame_hit, 0.07, 9);
      cam.position.set(noise1(t * 0.6, 1) * 0.35 + sx, noise1(t * 0.5, 2) * 0.3 + sy, z);
      cam.lookAt(noise1(t * 0.3, 3) * 0.4, noise1(t * 0.3, 4) * 0.3, z - 10);
      cam.rotation.z += Math.sin(t * 0.7) * 0.05 + easeInOutCubic(range(t, c.frame_hit - 0.3, c.frame_hit + 0.4)) * Math.PI * 0.5;

      // Panels: fade in from the dark, flicker on as the camera approaches.
      for (const [i, m] of panels.entries()) {
        const dz = z - m.position.z;
        const near = 1 - range(dz, 18, 34);
        const on = range(t, S.start + i * 0.02, S.start + 0.25 + i * 0.02);
        const flick = 0.75 + 0.25 * Math.sin(t * 40 + i * 3) * impulse(t - c.transition_word - i * 0.01, 6);
        (m.material as THREE.MeshBasicMaterial).opacity = 1.0 * near * on * flick * (1 - 0.6 * range(t, c.code_word, c.code_resolve));
      }

      rig.position.set(0, 0, z - 6.5);
      rig.rotation.set(t * 0.21, t * 0.33, 0);

      // P1: glyphs detach from panels and assemble a geodesic shell in front of the camera.
      const toShell = range(t, c.transition_word, c.effect_word + 0.6);
      p1.points.visible = t < c.code_word + 0.05;
      p1.u.uTime.value = t;
      p1.u.uMix.value = easeInOutCubic(toShell);
      p1.points.position.set(0, 0, 0);
      // Target shell must follow the rig: offset targets by animating the system's transform.
      p1.points.position.z = (z - 6.5) * easeOutCubic(toShell);
      p1.points.rotation.set(t * 0.21 * toShell, t * 0.33 * toShell, 0);
      p1.u.uNoiseAmp.value = 0.04 + 0.1 * impulse(t - c.effect_word, 3);
      p1.u.uOpacity.value = 0.2 + 0.4 * range(t, c.transition_word, c.transition_word + 0.6);
      p1.u.uSparkle.value = 0.6;

      // P2: shell re-forms into the torus knot.
      const toKnot = range(t, c.code_word, c.code_resolve);
      p2.points.visible = t >= c.code_word;
      p2.u.uTime.value = t;
      p2.u.uMix.value = easeInOutCubic(toKnot);
      p2.u.uSwirl.value = 3.0;
      p2.u.uNoiseAmp.value = 0.03;
      p2.u.uSparkle.value = 0.8;
      p2.u.uOpacity.value = 0.6;
      (wire.material as THREE.LineBasicMaterial).opacity = 0.22 * range(t, c.code_resolve - 0.4, c.code_resolve + 0.3);
      const pulse = 1 + 0.08 * impulse(t - c.code_resolve, 5);
      rig.scale.setScalar(pulse);

      // The 9:16 frame: waits ahead, camera blasts through it on "frame".
      const passZ = camZ(c.frame_hit + 0.15);
      frame.position.set(0, 0, passZ - 0.3);
      frame.rotation.set(0.05, 0, 0);
      frame.visible = t > c.frame_word - 0.2 && t < c.frame_hit + 0.6;
      frame.scale.setScalar(easeOutExpo(range(t, c.frame_word, c.frame_word + 0.5)) * 1.5 + 0.001);
      frameGlow.position.set(0, 0, passZ - 1.5);
      (frameGlow.material as THREE.ShaderMaterial).uniforms.uOpacity.value = frame.visible ? 0.05 + impulse(t - c.frame_hit, 4) * 0.12 : 0;

      d.u.uTime.value = t;
      d.points.position.z = z - 30;

      const speed = Math.abs(vz);
      const inT = range(t, S.start, S.start + 0.35);
      return {
        bloom: 0.4 + impulse(t - c.frame_hit, 4) * 0.5 + impulse(t - c.code_resolve, 5) * 0.25,
        zoomBlur: Math.min(0.11, speed * 0.004) + impulse(t - c.frame_hit, 8) * 0.12 + (1 - easeOutCubic(inT)) * 0.2,
        aberration: 1.5 + speed * 0.15 + impulse(t - c.frame_hit, 6) * 9,
        flash: impulse(t - c.frame_hit, 14) * 0.18 + (1 - easeOutCubic(inT)) * 0.1,
        redFlash: impulse(t - c.frame_hit, 9) * 0.02,
        glitch: impulse(t - c.transition_word, 10) * 0.25 + impulse(t - c.effect_word, 10) * 0.3,
        fade: easeInCubic(range(t, S.end - 0.2, S.end)) * 0.7,
        vignette: 0.7,
      };
    },
  };
};
