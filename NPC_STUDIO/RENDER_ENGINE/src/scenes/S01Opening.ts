import * as THREE from 'three';
import type { SceneFactory } from '../engine/Engine';
import { Particles, shell } from '../engine/particles';
import { fit, textMesh } from '../engine/chrome';
import { easeInCubic, easeOutCubic, easeOutExpo, impulse, lerp, noise1, range, shake, spring } from '../engine/util';
import { camera, chromeLights, dust, glow } from './common';

// SCENE 01 — IMPOSSIBLE OPENING
// Darkness → a single terminal cursor → "Look closer." → energy pulse →
// "THIS WASN'T EDITED." slams in from depth.

export const S01: SceneFactory = (a, tl) => {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#000000');
  const cam = camera(38);
  const end = tl.scenes.find((s) => s.id === 'S01')!.end;

  const cursor = new THREE.Mesh(
    new THREE.PlaneGeometry(0.09, 0.17),
    new THREE.MeshBasicMaterial({ color: new THREE.Color('#f3eee3').multiplyScalar(4) }),
  );
  scene.add(cursor);
  const cursorGlow = glow('#f3eee3', 0.7, 0.0);
  scene.add(cursorGlow);

  const ring = new THREE.Mesh(
    new THREE.RingGeometry(0.96, 1.0, 128),
    new THREE.MeshBasicMaterial({ color: new THREE.Color('#ff2b1c').multiplyScalar(1.6), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }),
  );
  const ring2 = new THREE.Mesh(
    new THREE.RingGeometry(0.985, 1.0, 128),
    new THREE.MeshBasicMaterial({ color: new THREE.Color('#f3eee3').multiplyScalar(3), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }),
  );
  scene.add(ring, ring2);

  const sparksStart = shell(1800, 0, 0.05, 21);
  const sparksDir = shell(1800, 1.5, 9, 22, [1, 1.1, 0.4]);
  const sparks = new Particles(sparksStart, sparksDir, 23);
  sparks.u.uSize.value = 0.022;
  sparks.u.uRedRatio.value = 0.25;
  sparks.u.uStagger.value = 0.2;
  scene.add(sparks.points);

  const d = dust();
  scene.add(d.points);

  const mats = [a.chrome.face, a.chrome.side];
  const line1 = textMesh(a.black, "THIS WASN'T", mats, { size: 0.5, tracking: 0.04 });
  const line2 = textMesh(a.black, 'EDITED.', mats, { size: 0.9, tracking: -0.01, depth: 0.3 });
  fit(line1, 2.6);
  fit(line2, 3.0);
  const title = new THREE.Group();
  const l1 = new THREE.Group().add(line1);
  const l2 = new THREE.Group().add(line2);
  l1.position.y = 0.5;
  l2.position.y = -0.22;
  title.add(l1, l2);
  scene.add(title);
  const behind = glow('#ff2b1c', 6, 0);
  behind.position.z = -3;
  scene.add(behind);
  const lights = chromeLights(scene);

  return {
    id: 'S01',
    scene,
    camera: cam,
    update: ({ t, cue }) => {
      const on = cue('cursor_on');
      const whisper = cue('whisper');
      const pulse = cue('pulse');
      const slam = cue('title_slam');

      // Camera: slow, nervous push-in toward the cursor ("look closer").
      const push = easeOutCubic(range(t, 0, pulse));
      const [sx, sy] = shake(t - slam, 0.09, 3);
      const [px, py] = shake(t - pulse, 0.035, 7, 7);
      cam.position.set(
        noise1(t * 0.4, 1) * 0.05 + sx + px,
        noise1(t * 0.35, 2) * 0.05 + sy + py,
        lerp(11.5, 8.0, push) + lerp(0.8, 1.8, easeOutCubic(range(t, slam - 0.2, end))) * (t > pulse ? 1 : 0),
      );
      cam.lookAt(0, 0, 0);
      cam.rotation.z = noise1(t * 0.3, 5) * 0.01;

      // Cursor: blink (terminal rhythm) until the pulse, then charge and collapse.
      const visible = t > on;
      const blink = t < whisper ? (Math.floor((t - on) / 0.53) % 2 === 0 ? 1 : 0.08) : 1;
      const charge = easeInCubic(range(t, pulse - 0.35, pulse));
      const gone = t > pulse;
      cursor.visible = visible && !gone;
      cursor.scale.set(1 + charge * 0.6, 1 + charge * 1.2, 1);
      cursor.position.x = (Math.sin(t * 90) * 0.004) * charge;
      (cursor.material as THREE.MeshBasicMaterial).color.setScalar(1).multiply(new THREE.Color('#f3eee3')).multiplyScalar(lerp(1.6, 5, charge) * blink);
      (cursorGlow.material as THREE.ShaderMaterial).uniforms.uOpacity.value = visible && !gone ? (0.05 + charge * 0.3) * blink : 0;

      // Energy pulse ring travelling outward through the darkness.
      const pr = range(t, pulse, pulse + 0.9);
      const rs = lerp(0.05, 9, easeOutExpo(pr));
      ring.scale.setScalar(rs);
      ring2.scale.setScalar(rs * 0.82);
      ring.visible = ring2.visible = t > pulse && pr < 1;
      (ring.material as THREE.MeshBasicMaterial).opacity = 1 - pr;
      (ring2.material as THREE.MeshBasicMaterial).opacity = (1 - pr) * 0.8;

      // Sparks thrown off by the pulse.
      sparks.points.visible = t > pulse && t < pulse + 1.2;
      sparks.u.uTime.value = t;
      sparks.u.uMix.value = easeOutExpo(range(t, pulse, pulse + 1.2));
      sparks.u.uOpacity.value = 0.8 * (1 - range(t, pulse + 0.1, pulse + 1.2));
      sparks.u.uNoiseAmp.value = 0.15 * range(t, pulse, pulse + 1.2);

      d.u.uTime.value = t;
      d.u.uOpacity.value = 0.05 + 0.2 * range(t, pulse - 0.2, pulse + 0.4);

      // Title: flies in from depth, lands with spring follow-through.
      const arrive = (delay: number) => {
        const k = range(t, slam - 0.2 + delay, slam + delay);
        return { z: lerp(-38, 0, easeOutExpo(k) * 0.85 + k * 0.15), s: spring(t - slam - delay, 2.4, 0.38) };
      };
      const A = arrive(0);
      const B = arrive(0.07);
      title.visible = t > slam - 0.2;
      l1.position.z = A.z;
      l2.position.z = B.z;
      l1.scale.set(1 + (1 - A.s) * 0.25, 1 - (1 - A.s) * 0.12, 1);
      l2.scale.set(1 + (1 - B.s) * 0.25, 1 - (1 - B.s) * 0.12, 1);
      title.rotation.y = lerp(-0.18, 0.08, easeOutCubic(range(t, slam, end))) + noise1(t * 0.5, 9) * 0.02;
      title.rotation.x = lerp(0.12, -0.03, easeOutCubic(range(t, slam, end)));
      // Exit: whip out to the left, handing the motion to Scene 02.
      const exit = easeInCubic(range(t, end - 0.28, end));
      title.position.x = -exit * 7;

      lights.rim.position.x = lerp(-6, 6, range(t, slam, end));
      lights.rim.intensity = 25 + impulse(t - slam, 6) * 40;
      lights.key.intensity = 2.2 + impulse(t - slam, 8) * 1.2;
      (behind.material as THREE.ShaderMaterial).uniforms.uOpacity.value = 0.05 * range(t, slam, slam + 0.3) + impulse(t - slam, 6) * 0.12;

      const flyV = t > slam - 0.2 && t < slam + 0.07 ? 1 : 0;
      return {
        bloom: 0.35 + impulse(t - pulse, 7) * 0.6 + impulse(t - slam, 10) * 0.3,
        flash: impulse(t - pulse, 18) * 0.18 + impulse(t - slam, 20) * 0.14,
        redFlash: impulse(t - pulse, 10) * 0.05,
        shockRadius: t > pulse ? easeOutExpo(range(t, pulse, pulse + 1.0)) * 1.4 : -1,
        shockStrength: 1 - range(t, pulse, pulse + 1.0),
        zoomBlur: flyV * 0.12 + impulse(t - slam, 12) * 0.08,
        dirBlur: [exit * 0.22, 0],
        aberration: 1.2 + impulse(t - slam, 8) * 10 + impulse(t - pulse, 8) * 6,
        vignette: 0.7,
        fade: 1 - easeOutCubic(range(t, 0, 0.3)),
      };
    },
  };
};
