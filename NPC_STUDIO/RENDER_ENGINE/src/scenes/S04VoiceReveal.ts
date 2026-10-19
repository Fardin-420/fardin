import * as THREE from 'three';
import type { SceneFactory } from '../engine/Engine';
import { Particles, shell } from '../engine/particles';
import { fit, samplePoints, textMesh } from '../engine/chrome';
import { clamp, easeInOutCubic, easeOutCubic, easeOutExpo, impulse, lerp, noise1, prng, range } from '../engine/util';
import { camera, dust, glow } from './common';

// SCENE 04 — THE VOICE REVEAL
// Every element is driven by the measured narration (envelope.json):
// per-frame RMS and a 24-band spectrum. Without NPC_VOICE_V1 narration the
// engine falls back to the soundtrack signal and labels it as such.

const BARS = 120;
const WAVES = 5;
const WAVE_PTS = 420;

export const S04: SceneFactory = (a, tl) => {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#010101');
  const cam = camera(36);
  const S = tl.scenes.find((s) => s.id === 'S04')!;
  const c = tl.cues;
  const r = prng(404);

  const root = new THREE.Group();
  scene.add(root);

  // Radial spectrum: instanced bars around a circle.
  const barGeo = new THREE.BoxGeometry(0.022, 1, 0.022);
  barGeo.translate(0, 0.5, 0);
  const barMat = new THREE.MeshBasicMaterial({ color: '#ffffff', transparent: true, blending: THREE.AdditiveBlending, depthWrite: false });
  const bars = new THREE.InstancedMesh(barGeo, barMat, BARS);
  bars.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(BARS * 3), 3);
  root.add(bars);

  // Concentric rings.
  const rings = [1.0, 1.32, 1.75, 2.3].map((rad, i) => {
    const m = new THREE.Mesh(
      new THREE.TorusGeometry(rad, i === 1 ? 0.006 : 0.003, 8, 256),
      new THREE.MeshBasicMaterial({ color: new THREE.Color(i === 1 ? '#ff2b1c' : '#f3eee3').multiplyScalar(2), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }),
    );
    root.add(m);
    return m;
  });

  // Layered horizontal waveforms across the frame.
  const waves = Array.from({ length: WAVES }, (_, i) => {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(WAVE_PTS * 3), 3));
    const col = new THREE.Color(i === 2 ? '#f3eee3' : i % 2 ? '#ff2b1c' : '#a9a49a').multiplyScalar(i === 2 ? 2.2 : 1.2);
    const line = new THREE.Line(g, new THREE.LineBasicMaterial({ color: col, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    line.position.z = -0.3 * Math.abs(i - 2);
    scene.add(line);
    return line;
  });

  // Orbiting particle halo -> NPC symbol.
  const word = textMesh(a.black, 'NPC', [a.chrome.face, a.chrome.side], { size: 1, tracking: 0.04 });
  fit(word, 2.3);
  const N = 14000;
  const symbol = samplePoints(word, N, 405);
  const halo = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) {
    const th = r() * Math.PI * 2;
    const rad = 1.9 + (r() - 0.5) * 0.5;
    halo[i * 3] = Math.cos(th) * rad;
    halo[i * 3 + 1] = Math.sin(th) * rad;
    halo[i * 3 + 2] = (r() - 0.5) * 0.3;
  }
  const parts = new Particles(halo, symbol, 406);
  parts.u.uSize.value = 0.018;
  parts.u.uStagger.value = 0.5;
  parts.u.uRedRatio.value = 0.08;
  root.add(parts.points);

  const core = glow('#ff2b1c', 5, 0.1);
  core.position.z = -1;
  root.add(core);
  const d = dust(1500, [20, 30, 30], 444);
  scene.add(d.points);
  void shell;

  const dummy = new THREE.Object3D();
  const col = new THREE.Color();
  const ivory = new THREE.Color('#f3eee3');
  const red = new THREE.Color('#ff2b1c');

  return {
    id: 'S04',
    scene,
    camera: cam,
    update: ({ t, frame, env }) => {
      const rms = env.signalRms(frame);
      const spec = env.signalSpec(frame);
      // Smoothed level (short look-back) so motion has weight but stays in sync.
      let lvl = 0;
      for (let k = 0; k < 6; k++) lvl = Math.max(lvl, env.signalRms(frame - k) * (1 - k * 0.12));
      const intro = easeOutExpo(range(t, S.start, S.start + 0.9));
      const morph = range(t, c.symbol_morph - 0.35, c.symbol_morph + 0.6);
      const outK = range(t, S.end - 0.3, S.end);

      cam.position.set(noise1(t * 0.4, 1) * 0.25 + Math.sin(t * 0.3) * 0.6, noise1(t * 0.35, 2) * 0.2, lerp(11, 8.3, easeOutCubic(range(t, S.start, S.end))));
      cam.lookAt(0, 0, 0);
      root.rotation.set(Math.sin(t * 0.4) * 0.25, Math.sin(t * 0.3) * 0.35, 0);

      // Spectrum bars: mirrored 24-band spectrum around the ring.
      for (let i = 0; i < BARS; i++) {
        const u = i / BARS;
        const mirrored = u < 0.5 ? u * 2 : (1 - u) * 2;
        const fb = mirrored * (spec.length - 1);
        const b0 = Math.floor(fb);
        const v = lerp(spec[b0], spec[Math.min(spec.length - 1, b0 + 1)], fb - b0);
        const h = (0.04 + v * 0.75 * (0.35 + lvl)) * intro * (1 - morph);
        const ang = u * Math.PI * 2 + t * 0.15;
        dummy.position.set(Math.cos(ang) * 1.08, Math.sin(ang) * 1.08, 0);
        dummy.rotation.set(0, 0, ang - Math.PI / 2);
        dummy.scale.set(1, Math.max(h, 0.001), 1);
        dummy.updateMatrix();
        bars.setMatrixAt(i, dummy.matrix);
        col.copy(ivory).lerp(red, clamp(v * 1.4 - 0.3)).multiplyScalar(1.2 + v * 2);
        bars.setColorAt(i, col);
      }
      bars.instanceMatrix.needsUpdate = true;
      bars.instanceColor!.needsUpdate = true;

      rings.forEach((m, i) => {
        const s = (1 + lvl * (0.06 + i * 0.05)) * lerp(0.6, 1, intro) * (1 - morph * 0.3);
        m.scale.setScalar(s);
        m.rotation.set(t * (0.2 + i * 0.07), t * (0.13 - i * 0.05), 0);
        (m.material as THREE.MeshBasicMaterial).opacity = (0.35 + lvl * 0.6) * intro * (1 - morph * 0.85);
      });

      // Waveforms: band-weighted harmonics; amplitude follows real speech energy.
      waves.forEach((w, wi) => {
        const pos = (w.geometry.attributes.position as THREE.BufferAttribute).array as Float32Array;
        const amp = (0.06 + lvl * 0.9) * intro * (1 - easeInOutCubic(morph));
        for (let i = 0; i < WAVE_PTS; i++) {
          const x = (i / (WAVE_PTS - 1) - 0.5) * 4.4;
          const win = Math.exp(-x * x * 0.35);
          let y = 0;
          for (let b = 0; b < spec.length; b += 2) {
            y += spec[b] * Math.sin(x * (2 + b * 0.9) + t * (3 + b * 0.4) + wi * 0.9 + b) / (1 + b * 0.15);
          }
          pos[i * 3] = x;
          pos[i * 3 + 1] = y * amp * 0.35 * win * (1 - Math.abs(wi - 2) * 0.18) + (wi - 2) * 0.05;
          pos[i * 3 + 2] = 0;
        }
        w.geometry.attributes.position.needsUpdate = true;
        (w.material as THREE.LineBasicMaterial).opacity = (wi === 2 ? 1 : 0.45) * intro * (1 - morph);
      });

      parts.u.uTime.value = t;
      parts.u.uMix.value = easeInOutCubic(morph);
      parts.u.uSwirl.value = 4;
      parts.u.uNoiseAmp.value = 0.02 + lvl * 0.12 * (1 - morph);
      parts.u.uOpacity.value = intro * (0.7 + lvl * 0.6) * (1 - outK * 0.5);
      parts.u.uSparkle.value = 0.6;
      parts.points.rotation.z = (1 - easeOutCubic(morph)) * t * 0.6;
      (core.material as THREE.ShaderMaterial).uniforms.uOpacity.value = 0.05 + lvl * 0.25 + impulse(t - c.mine, 3) * 0.15;
      d.u.uTime.value = t;

      return {
        bloom: 0.45 + lvl * 0.4 + impulse(t - c.symbol_morph, 5) * 0.4,
        aberration: 1.2 + lvl * 3,
        flash: impulse(t - c.mine, 12) * 0.05,
        zoomBlur: easeInOutCubic(outK) * 0.15 + (1 - easeOutCubic(range(t, S.start, S.start + 0.3))) * 0.1,
        vignette: 0.75,
      };
    },
  };
};
