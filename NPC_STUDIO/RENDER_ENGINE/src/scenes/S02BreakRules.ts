import * as THREE from 'three';
import type { SceneFactory } from '../engine/Engine';
import { Particles, shell } from '../engine/particles';
import { fit, samplePoints, textMesh } from '../engine/chrome';
import {
  clamp, easeInCubic, easeInOutCubic, easeOutCubic, easeOutExpo, impulse, lerp, noise1, range, shake, spring,
} from '../engine/util';
import { camera, chromeLights, dust, floorGrid, glow } from './common';

// SCENE 02 — BREAK THE RULES
// Three software names, set in NPC chrome type (no logos), each destroyed by a
// different procedural effect. The camera whips laterally between stations.

const STATION_GAP = 9;

export const S02: SceneFactory = (a, tl) => {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#020202');
  scene.fog = new THREE.Fog('#020202', 12, 40);
  const cam = camera(38);
  const S = tl.scenes.find((s) => s.id === 'S02')!;
  const c = tl.cues;

  const grid = floorGrid('#ff2b1c', 120, 60, -2.2);
  scene.add(grid);
  const d = dust(2200, [60, 30, 40], 77);
  scene.add(d.points);
  const lights = chromeLights(scene);
  const mats = [a.chrome.face, a.chrome.side];

  type Station = {
    group: THREE.Group; word: THREE.Group; parts: Particles; slash: THREE.Mesh; halo: THREE.Mesh; x: number;
  };
  const make = (text: string, i: number, w: number, seed: number, n: number): Station => {
    const word = textMesh(a.black, text, mats, { size: 1, tracking: 0.01, lineHeight: 1.0 });
    fit(word, w, 2.4);
    const target = samplePoints(word, n, seed);
    const holder = new THREE.Group().add(word); // animated transform; keeps the fit scale on `word`
    const parts = new Particles(shell(n, 3, 9, seed + 1, [1.4, 1, 1]), target, seed + 2);
    parts.u.uSize.value = 0.026;
    parts.u.uRedRatio.value = 0.05;
    const slash = new THREE.Mesh(
      new THREE.PlaneGeometry(w * 1.25, 0.018),
      new THREE.MeshBasicMaterial({ color: new THREE.Color('#ff2b1c').multiplyScalar(5), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }),
    );
    slash.position.z = 0.4;
    slash.rotation.z = -0.08;
    const halo = glow('#ff2b1c', 7, 0);
    halo.position.z = -2;
    const group = new THREE.Group();
    group.add(holder, parts.points, slash, halo);
    group.position.x = i * STATION_GAP;
    scene.add(group);
    return { group, word: holder, parts, slash, halo, x: i * STATION_GAP };
  };
  const premiere = make('PREMIERE', 0, 3.0, 101, 14000);
  const capcut = make('CAPCUT', 1, 2.8, 201, 12000);
  const ae = make('AFTER\nEFFECTS', 2, 2.7, 301, 18000);

  // Camera rail: hold on a station, whip to the next between break and next "in".
  const whips = [
    { t0: c.premiere_break + 0.05, t1: c.capcut_in - 0.08, from: 0, to: 1 },
    { t0: c.capcut_break + 0.08, t1: c.ae_in - 0.05, from: 1, to: 2 },
  ];
  const camX = (t: number) => {
    let x = lerp(-STATION_GAP * 0.9, 0, easeOutExpo(range(t, S.start, S.start + 0.45)));
    for (const w of whips) x += (w.to - w.from) * STATION_GAP * easeInOutCubic(range(t, w.t0, w.t1));
    return x;
  };

  return {
    id: 'S02',
    scene,
    camera: cam,
    update: ({ t }) => {
      const cx = camX(t);
      const vx = (camX(t + 1 / 120) - camX(t - 1 / 120)) * 60; // world units / s
      const [sx, sy] = shake(t - c.ae_break, 0.08, 4);
      const [sx2, sy2] = shake(t - c.premiere_break, 0.04, 6, 8);
      cam.position.set(cx + sx + sx2 + noise1(t * 0.5, 3) * 0.04, 0.25 + sy + sy2 + noise1(t * 0.4, 4) * 0.04, 9.2 - 0.6 * range(t, S.start, S.end));
      cam.lookAt(cx, 0.05, 0);
      cam.rotation.z += clamp(vx * -0.0025, -0.06, 0.06); // bank into the whip

      d.u.uTime.value = t;
      grid.material.uniforms.uScroll.value = t * 1.5;
      grid.material.uniforms.uOpacity.value = 0.22;

      const all = [premiere, capcut, ae];
      for (const s of all) s.parts.u.uTime.value = t;

      // ── PREMIERE: assembles from particles, solidifies, then velocity-displaced.
      {
        const s = premiere;
        const assemble = range(t, S.start + 0.3, c.premiere_in);
        const solid = t >= c.premiere_in && t < c.premiere_break;
        const brk = range(t, c.premiere_break, c.premiere_break + 0.55);
        s.word.visible = solid;
        // Anticipation: the word leans back just before it is ripped away.
        const ant = easeOutCubic(range(t, c.premiere_break - 0.14, c.premiere_break)) * (t < c.premiere_break ? 1 : 0);
        s.word.position.x = -0.12 * ant;
        s.word.scale.setScalar(1 + 0.03 * impulse(t - c.premiere_in, 6) - 0.02 * ant);
        s.parts.points.visible = !solid && t < c.premiere_break + 0.6;
        s.parts.u.uMix.value = t < c.premiere_break ? assemble : 1;
        s.parts.u.uSwirl.value = 2.2;
        s.parts.u.uStagger.value = 0.5;
        s.parts.u.uOpacity.value = (t < c.premiere_in ? 0.4 + 0.6 * assemble : 1) * (1 - brk);
        s.parts.u.uDispVel.value.set(16, 0.6, -2);
        s.parts.u.uDisp.value = easeInCubic(brk);
        s.parts.u.uNoiseAmp.value = 0.05 + brk * 0.3;
        slashAnim(s, t, c.premiere_break);
      }

      // ── CAPCUT: flips in on Y (3D rotation), then digitally fragments.
      {
        const s = capcut;
        const sp = spring(t - c.capcut_in, 2.0, 0.45);
        const brk = range(t, c.capcut_break, c.capcut_break + 0.45);
        const solid = t >= c.capcut_in - 0.05 && t < c.capcut_break;
        s.word.visible = solid;
        s.word.rotation.y = (1 - sp) * -Math.PI * 0.55;
        s.word.position.z = (1 - sp) * -1.5;
        s.parts.points.visible = t >= c.capcut_break && brk < 1;
        s.parts.u.uMix.value = 1;
        s.parts.u.uGlitch.value = easeOutCubic(brk) * 0.9;
        s.parts.u.uBlocks.value = 7;
        s.parts.u.uDispVel.value.set(0, 0, 6);
        s.parts.u.uDisp.value = easeInCubic(brk) * 0.6;
        s.parts.u.uOpacity.value = 1 - easeInCubic(brk);
        s.parts.u.uRedRatio.value = 0.05 + brk * 0.3;
        slashAnim(s, t, c.capcut_break);
      }

      // ── AFTER EFFECTS: rises with X rotation, then disintegrates into embers + shockwave.
      {
        const s = ae;
        const sp = spring(t - c.ae_in, 1.8, 0.5);
        const dis = range(t, c.ae_break, c.ae_break + 1.0);
        const solid = t >= c.ae_in - 0.05 && t < c.ae_break;
        s.word.visible = solid;
        s.word.rotation.x = (1 - sp) * 1.1;
        s.word.position.y = (1 - sp) * -1.2;
        s.group.rotation.y = lerp(0.18, -0.12, range(t, c.ae_in, c.ae_break + 0.6));
        s.parts.points.visible = t >= c.ae_break && dis < 1;
        s.parts.u.uMix.value = 1;
        s.parts.u.uDisint.value = dis;
        s.parts.u.uDisintDist.value = 4.5;
        s.parts.u.uExplode.value = easeOutExpo(dis) * 0.8;
        s.parts.u.uExplodeCenter.value.set(0, 0, -0.5);
        s.parts.u.uNoiseAmp.value = 0.08;
        s.parts.u.uOpacity.value = 0.8;
        slashAnim(s, t, c.ae_break);
      }

      lights.rim.position.set(cx + 4, -1, -2);
      lights.key.position.set(cx - 3, 5, 6);
      lights.rim.intensity = 25 + 60 * impulse(t - c.ae_break, 5);

      const glitch = impulse(t - c.capcut_break, 4) * 0.85 * (t < c.capcut_break + 0.5 ? 1 : 0);
      return {
        bloom: 0.3 + impulse(t - c.ae_break, 4) * 0.6 + impulse(t - c.premiere_in, 8) * 0.2,
        dirBlur: [clamp(vx * 0.0045, -0.12, 0.12) + easeInCubic(range(t, c.premiere_break, c.premiere_break + 0.3)) * (1 - range(t, c.premiere_break + 0.3, c.premiere_break + 0.5)) * 0.05, 0],
        glitch,
        aberration: 1.5 + glitch * 10 + impulse(t - c.ae_break, 6) * 8 + Math.abs(vx) * 0.08,
        shockRadius: t > c.ae_break ? easeOutExpo(range(t, c.ae_break, c.ae_break + 0.8)) * 1.3 : -1,
        shockStrength: 0.9 * (1 - range(t, c.ae_break, c.ae_break + 0.8)),
        flash: impulse(t - c.ae_break, 18) * 0.12 + impulse(t - c.premiere_in, 18) * 0.06,
        vignette: 0.65,
      };
    },
  };

  // A red laser cut slices each word just before it is destroyed.
  function slashAnim(s: Station, t: number, brk: number) {
    const k = range(t, brk - 0.16, brk - 0.02);
    const out = range(t, brk, brk + 0.25);
    s.slash.visible = k > 0 && out < 1;
    s.slash.scale.x = easeOutExpo(k);
    (s.slash.material as THREE.MeshBasicMaterial).opacity = 1 - out;
    (s.halo.material as THREE.ShaderMaterial).uniforms.uOpacity.value = 0.18 * impulse(t - brk, 3) * (t > brk - 0.02 ? 1 : 0);
  }
};
