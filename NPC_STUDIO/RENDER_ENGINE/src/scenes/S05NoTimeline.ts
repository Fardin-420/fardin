import * as THREE from 'three';
import type { SceneFactory } from '../engine/Engine';
import { Particles } from '../engine/particles';
import { fit, textMesh } from '../engine/chrome';
import {
  easeInCubic, easeInOutCubic, easeInExpo, easeOutCubic, easeOutExpo, impulse, lerp, noise1, prng, range, shake, spring,
} from '../engine/util';
import { camera, chromeLights, dust, glow, rays } from './common';

// SCENE 05 — NO TIMELINE
// Beat 1: hundreds of layers move in perfect sync.
// Beat 2: everything collapses into one luminous horizontal line.
// Beat 3: the line explodes outward into "JUST CODE."

const LAYERS = 340;

export const S05: SceneFactory = (a, tl) => {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#010101');
  const cam = camera(40);
  const S = tl.scenes.find((s) => s.id === 'S05')!;
  const c = tl.cues;
  const r = prng(505);

  // Layer slabs.
  const geo = new THREE.BoxGeometry(1, 1, 0.02);
  const mat = new THREE.MeshBasicMaterial({ color: '#ffffff', transparent: true });
  const slabs = new THREE.InstancedMesh(geo, mat, LAYERS);
  slabs.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(LAYERS * 3), 3);
  scene.add(slabs);
  type L = { row: number; depth: number; x: number; w: number; phase: number; color: THREE.Color; delay: number };
  const layers: L[] = [];
  for (let i = 0; i < LAYERS; i++) {
    const row = i % 34;
    const depth = Math.floor(i / 34);
    const red = r() < 0.07;
    const v = 0.12 + r() * 0.5;
    layers.push({
      row, depth, x: (r() - 0.5) * 9, w: 0.3 + r() * 1.6, phase: row * 0.35 + depth * 0.6,
      color: red ? new THREE.Color('#ff2b1c').multiplyScalar(2.2) : new THREE.Color('#f3eee3').multiplyScalar(v),
      delay: r() * 0.5,
    });
  }

  // The luminous line.
  const line = new THREE.Mesh(
    new THREE.PlaneGeometry(1, 1),
    new THREE.MeshBasicMaterial({ color: new THREE.Color('#fff4e8').multiplyScalar(6), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }),
  );
  scene.add(line);
  const lineGlow = glow('#ff2b1c', 6, 0);
  lineGlow.scale.set(1.6, 0.25, 1);
  scene.add(lineGlow);

  // Explosion particles seeded along the line.
  const N = 9000;
  const st = new Float32Array(N * 3);
  const tg = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) {
    const x = (r() - 0.5) * 7;
    st[i * 3] = x;
    st[i * 3 + 1] = (r() - 0.5) * 0.02;
    st[i * 3 + 2] = 0;
    const th = r() * Math.PI * 2;
    const sp = 2 + r() * 9;
    tg[i * 3] = x * 1.4 + Math.cos(th) * sp * 0.5;
    tg[i * 3 + 1] = Math.sin(th) * sp;
    tg[i * 3 + 2] = (r() - 0.3) * sp * 0.8;
  }
  const blast = new Particles(st, tg, 506);
  blast.u.uSize.value = 0.03;
  blast.u.uStagger.value = 0.1;
  blast.u.uRedRatio.value = 0.3;
  scene.add(blast.points);

  // JUST CODE.
  const mats = [a.chrome.face, a.chrome.side];
  const just = textMesh(a.black, 'JUST', mats, { size: 1, tracking: 0.02 });
  const codeW = textMesh(a.black, 'CODE.', mats, { size: 1, tracking: -0.01, depth: 0.32 });
  fit(just, 2.2);
  fit(codeW, 3.1);
  const title = new THREE.Group();
  const gJust = new THREE.Group().add(just);
  const gCode = new THREE.Group().add(codeW);
  gJust.position.y = 0.6;
  gCode.position.y = -0.45;
  title.add(gJust, gCode);
  scene.add(title);
  const lights = chromeLights(scene);
  const ray = rays('#f3eee3', 22);
  ray.position.z = -4;
  scene.add(ray);
  const d = dust(2000, [30, 40, 40], 555);
  scene.add(d.points);

  const dummy = new THREE.Object3D();

  return {
    id: 'S05',
    scene,
    camera: cam,
    update: ({ t }) => {
      const pop = (l: L) => easeOutExpo(range(t, c.layers + l.delay * 0.6 - 0.1, c.layers + l.delay * 0.6 + 0.35));
      const col = easeInOutCubic(range(t, c.collapse - 0.05, c.collapse + 0.45));
      const ex = c.explode;
      const exploded = t >= ex;

      // Camera: tilted 3D view of the layer stack, straightens for the collapse, then punches in.
      const tilt = 1 - col;
      const [sx, sy] = shake(t - ex, 0.16, 2, 4.5);
      cam.position.set(
        lerp(0, 3.2, tilt) + sx + noise1(t * 0.5, 1) * 0.05,
        lerp(0, 2.4, tilt) + sy,
        lerp(9.5, 12, tilt) - 1.2 * easeOutCubic(range(t, ex, S.end)),
      );
      cam.lookAt(0, 0, 0);
      cam.rotation.z += lerp(0, -0.12, tilt);

      // Layers: synchronized timeline motion, then collapse into the line.
      for (let i = 0; i < LAYERS; i++) {
        const l = layers[i];
        const p = pop(l);
        const sync = Math.sin(t * 3.2 + l.phase) * 0.35;
        const scroll = ((l.x + t * 1.6 + 4.5) % 9 + 9) % 9 - 4.5;
        const x0 = scroll + sync * 0.2;
        const y0 = (l.row - 16.5) * 0.17 + Math.sin(t * 2.4 + l.depth * 0.8) * 0.06;
        const z0 = -l.depth * 0.55 + sync * 0.3;
        dummy.position.set(lerp(x0, x0 * 0.85, col), lerp(y0, 0, col), lerp(z0, 0, col));
        dummy.scale.set(l.w * lerp(1, 1.6, col), lerp(0.065, 0.004, col) * p, 1);
        dummy.updateMatrix();
        slabs.setMatrixAt(i, dummy.matrix);
        slabs.setColorAt(i, l.color);
      }
      slabs.instanceMatrix.needsUpdate = true;
      slabs.instanceColor!.needsUpdate = true;
      slabs.visible = t < c.collapse + 0.5;
      mat.opacity = 0.9 * (1 - range(t, c.collapse + 0.3, c.collapse + 0.5));

      // Line: forms out of the collapse, hums with rising charge, then detonates.
      const charge = easeInExpo(range(t, c.collapse + 0.6, ex));
      const lw = easeOutExpo(range(t, c.collapse + 0.15, c.collapse + 0.6)) * 7.2;
      line.visible = t > c.collapse + 0.15 && t < ex + 0.12;
      line.scale.set(lw, 0.012 + charge * 0.02 + (exploded ? easeOutExpo(range(t, ex, ex + 0.1)) * 2 : 0), 1);
      line.position.y = Math.sin(t * 90) * 0.004 * charge;
      (line.material as THREE.MeshBasicMaterial).opacity = exploded ? 1 - range(t, ex, ex + 0.12) : 1;
      (lineGlow.material as THREE.ShaderMaterial).uniforms.uOpacity.value = line.visible ? 0.12 + charge * 0.5 : 0;

      blast.points.visible = exploded && t < ex + 1.5;
      blast.u.uTime.value = t;
      blast.u.uMix.value = easeOutExpo(range(t, ex, ex + 1.3));
      blast.u.uOpacity.value = 1 - range(t, ex + 0.3, ex + 1.5);
      blast.u.uNoiseAmp.value = 0.2 * range(t, ex, ex + 1.3);

      // Title punches out of the line: vertical spring from zero height + z punch.
      const s1 = spring(t - ex, 2.1, 0.4);
      const s2 = spring(t - ex - 0.06, 2.1, 0.4);
      title.visible = exploded;
      gJust.scale.set(1 + (1 - s1) * 0.4, Math.max(0.001, s1), 1);
      gCode.scale.set(1 + (1 - s2) * 0.4, Math.max(0.001, s2), 1);
      title.position.z = lerp(3, 0, easeOutExpo(range(t, ex, ex + 0.35)));
      title.rotation.y = Math.sin(t * 0.8) * 0.06 + lerp(0.12, 0, easeOutCubic(range(t, ex, ex + 1.2)));
      title.rotation.x = -0.05;
      lights.rim.intensity = 25 + 80 * impulse(t - ex, 4);
      lights.rim.position.x = lerp(4, -4, range(t, ex, S.end));

      const rm = ray.material as THREE.ShaderMaterial;
      rm.uniforms.uOpacity.value = exploded ? 0.1 * impulse(t - ex, 2.5) + 0.02 : 0;
      rm.uniforms.uTime.value = t;
      d.u.uTime.value = t;

      return {
        bloom: 0.35 + charge * 0.6 + impulse(t - ex, 5) * 0.5,
        flash: impulse(t - ex, 12) * 0.22 + impulse(t - c.collapse, 12) * 0.05,
        redFlash: impulse(t - ex, 6) * 0.06,
        shockRadius: exploded ? easeOutExpo(range(t, ex, ex + 0.9)) * 1.4 : -1,
        shockStrength: 1.2 * (1 - range(t, ex, ex + 0.9)),
        shockCenter: [0.5, 0.5],
        zoomBlur: impulse(t - ex, 7) * 0.2 + easeInCubic(range(t, S.end - 0.25, S.end)) * 0.25,
        dirBlur: [0, impulse(t - c.collapse, 6) * 0.04],
        aberration: 1.5 + charge * 4 + impulse(t - ex, 5) * 12,
        glitch: impulse(t - c.layers, 9) * 0.2,
        vignette: 0.7,
        exposure: 1 - 0.35 * range(t, c.collapse + 0.4, c.collapse + 0.8) * (exploded ? 0 : 1),
      };
    },
  };
};
