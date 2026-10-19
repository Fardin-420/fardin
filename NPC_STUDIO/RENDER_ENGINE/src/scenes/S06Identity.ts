import * as THREE from 'three';
import type { SceneFactory } from '../engine/Engine';
import { Particles, shell } from '../engine/particles';
import { fit, samplePoints, textMesh } from '../engine/chrome';
import { easeInOutCubic, easeOutCubic, easeOutExpo, impulse, lerp, noise1, range, spring } from '../engine/util';
import { camera, dust, glow, rays } from './common';

// SCENE 06 — THE NPC IDENTITY
// Procedural monogram (no official logo file exists in BRAND/logos): a thin
// chrome ring around extruded NPC letters, with the red terminal cursor from
// the opening shot as its single accent. Metallic particles assemble it.

export const S06: SceneFactory = (a, tl) => {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#010101');
  const cam = camera(38);
  const S = tl.scenes.find((s) => s.id === 'S06')!;
  const c = tl.cues;

  const emblem = new THREE.Group();
  emblem.position.y = 0.55;
  scene.add(emblem);

  const ring = new THREE.Mesh(new THREE.TorusGeometry(1.0, 0.035, 32, 256), a.chrome.face);
  const ringInner = new THREE.Mesh(new THREE.TorusGeometry(0.9, 0.008, 16, 256), a.chrome.side);
  const letters = textMesh(a.black, 'NPC', [a.chrome.face, a.chrome.side], { size: 1, tracking: 0.03, depth: 0.3 });
  fit(letters, 1.32);
  const cursor = new THREE.Mesh(
    new THREE.BoxGeometry(0.07, 0.13, 0.05),
    new THREE.MeshBasicMaterial({ color: new THREE.Color('#ff2b1c').multiplyScalar(3) }),
  );
  cursor.position.set(0, 1.0, 0.02);
  const solid = new THREE.Group();
  solid.add(ring, ringInner, letters, cursor);
  emblem.add(solid);

  // Particles land on the emblem surface.
  const N = 30000;
  const target = samplePoints(new THREE.Group().add(ring.clone(), letters.clone()), N, 606);
  const start = shell(N, 1.8, 4.6, 607, [1, 1.5, 0.6]);
  const parts = new Particles(start, target, 608);
  parts.u.uSize.value = 0.026;
  parts.u.uStagger.value = 0.55;
  parts.u.uRedRatio.value = 0.04;
  parts.u.uColorA.value = new THREE.Color('#dfe2ea');
  emblem.add(parts.points);

  const back = glow('#ff2b1c', 5.5, 0);
  back.position.z = -1.2;
  emblem.add(back);
  const ray = rays('#f3eee3', 16);
  ray.position.z = -2;
  emblem.add(ray);

  const key = new THREE.DirectionalLight('#fff4e6', 2.2);
  key.position.set(-3, 4, 6);
  const sweep = new THREE.PointLight('#ffffff', 0, 12, 1.4);
  const rim = new THREE.PointLight('#ff2b1c', 18, 20, 1.6);
  rim.position.set(3, -1, -2);
  scene.add(key, sweep, rim);
  const d = dust(1800, [20, 30, 30], 666);
  scene.add(d.points);

  return {
    id: 'S06',
    scene,
    camera: cam,
    update: ({ t }) => {
      const lock = c.emblem_lock;
      const assemble = range(t, S.start, lock);
      const locked = t >= lock;

      // Smooth orbit that settles to a frontal brand frame.
      const settle = easeInOutCubic(range(t, lock, c.final_hit + 0.4));
      const ang = lerp(-0.85, -0.35, easeOutCubic(assemble)) * (1 - settle);
      const rad = lerp(9.2, 7.6, easeOutCubic(range(t, S.start, c.tagline))) - 0.5 * range(t, c.tagline, S.end); // never fully static
      cam.position.set(Math.sin(ang) * rad, 0.4 + Math.sin(ang) * -0.3 + noise1(t * 0.3, 2) * 0.03, Math.cos(ang) * rad);
      cam.lookAt(0, 0.3, 0);

      parts.u.uTime.value = t;
      parts.u.uMix.value = easeInOutCubic(assemble);
      parts.u.uSwirl.value = 5.5;
      parts.u.uNoiseAmp.value = 0.05 * (1 - assemble);
      parts.u.uSparkle.value = 1.2;
      parts.u.uOpacity.value = locked ? 1 - easeOutCubic(range(t, lock, lock + 0.7)) : 0.85 + 0.15 * assemble;
      parts.points.visible = t < lock + 0.7;

      // Solid emblem materialises under a flash the instant the particles land.
      const s = spring(t - lock, 1.6, 0.55);
      solid.visible = locked;
      solid.scale.setScalar(lerp(0.94, 1, s));
      solid.rotation.y = (1 - s) * 0.25 + Math.sin(t * 0.5) * 0.03 * (1 - settle);
      ring.rotation.z = t * 0.05;
      const blink = Math.floor((t - c.final_hit) / 0.53) % 2 === 0 || t < c.final_hit ? 1 : 0.15;
      (cursor.material as THREE.MeshBasicMaterial).color.set('#ff2b1c').multiplyScalar(2.6 * blink);

      // Light sweep across the chrome on the final hit.
      const sw = range(t, c.final_hit - 0.1, c.final_hit + 1.1);
      sweep.position.set(lerp(-3, 3, easeInOutCubic(sw)), 1.2, 2.2);
      sweep.intensity = Math.sin(sw * Math.PI) * 40;

      (back.material as THREE.ShaderMaterial).uniforms.uOpacity.value = locked ? 0.035 + impulse(t - lock, 3) * 0.1 : 0.02 * assemble;
      const rm = ray.material as THREE.ShaderMaterial;
      rm.uniforms.uOpacity.value = locked ? 0.07 * easeOutExpo(range(t, lock, lock + 0.8)) + impulse(t - c.final_hit, 2) * 0.08 : 0;
      rm.uniforms.uTime.value = t;
      d.u.uTime.value = t;

      return {
        bloom: 0.35 + impulse(t - lock, 4) * 0.5 + impulse(t - c.final_hit, 4) * 0.2,
        flash: impulse(t - lock, 14) * 0.15,
        zoomBlur: (1 - easeOutCubic(range(t, S.start, S.start + 0.4))) * 0.2 + impulse(t - lock, 10) * 0.05,
        aberration: 1 + impulse(t - lock, 6) * 6,
        vignette: 0.75,
        grain: 0.04,
        fade: (1 - easeOutCubic(range(t, S.start, S.start + 0.15))) * 0.3,
      };
    },
  };
};
