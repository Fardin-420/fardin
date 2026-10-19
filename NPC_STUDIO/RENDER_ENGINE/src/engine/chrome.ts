import * as THREE from 'three';
import { Font } from 'three/examples/jsm/loaders/FontLoader.js';
import { TextGeometry } from 'three/examples/jsm/geometries/TextGeometry.js';
import { MeshSurfaceSampler } from 'three/examples/jsm/math/MeshSurfaceSampler.js';
import { prng } from './util';

/**
 * Procedural photo-studio environment for chrome: a black void lit by long
 * softbox strips and a single thin red strip. Its reflections give the metal
 * its cinematic contrast without any image assets.
 */
export function buildStudioEnv(renderer: THREE.WebGLRenderer): THREE.Texture {
  const env = new THREE.Scene();
  env.background = new THREE.Color('#000000');
  const strip = (w: number, h: number, color: string, intensity: number, pos: number[], rot: number[]) => {
    const m = new THREE.Mesh(
      new THREE.PlaneGeometry(w, h),
      new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(intensity), side: THREE.DoubleSide }),
    );
    m.position.set(pos[0], pos[1], pos[2]);
    m.rotation.set(rot[0], rot[1], rot[2]);
    env.add(m);
  };
  strip(14, 1.2, '#ffffff', 5, [0, 7, -2], [Math.PI / 2, 0, 0]); // overhead key
  strip(1.0, 9, '#fff6ea', 3.2, [-8, 0, 2], [0, Math.PI / 2, 0]); // left rim
  strip(1.6, 9, '#e8eeff', 2.4, [8, 1, -1], [0, -Math.PI / 2, 0]); // right fill
  strip(10, 0.25, '#ff2b1c', 6, [0, -2.4, -7], [0, 0, 0]); // red accent strip
  strip(10, 0.5, '#ffffff', 1.4, [0, -6, 3], [-Math.PI / 2, 0, 0]); // floor bounce
  // Banded softboxes behind the camera: front faces reflect these, so flat
  // type reads as polished chrome with horizon-like highlight bands.
  strip(18, 1.6, '#fff8ef', 1.15, [0, 1.6, 9], [0, Math.PI, 0]);
  strip(18, 0.35, '#ffffff', 2.2, [0, -0.2, 9], [0, Math.PI, 0]);
  strip(18, 2.4, '#d8dce6', 0.3, [0, -2.6, 9], [0, Math.PI, 0]);
  strip(0.6, 8, '#ffffff', 2.5, [-3.5, 0, 8.5], [0, Math.PI, 0]); // vertical kicker for travelling highlights
  const pmrem = new THREE.PMREMGenerator(renderer);
  const tex = pmrem.fromScene(env, 0.035).texture;
  pmrem.dispose();
  return tex;
}

export function chromeMaterials(env: THREE.Texture) {
  const face = new THREE.MeshStandardMaterial({
    color: '#e9ebf0', metalness: 1, roughness: 0.1, envMap: env, envMapIntensity: 1.7,
  });
  const side = new THREE.MeshStandardMaterial({
    color: '#9a9ea8', metalness: 1, roughness: 0.32, envMap: env, envMapIntensity: 0.9,
  });
  return { face, side };
}

export type TextOpts = {
  size: number;
  depth?: number;
  bevel?: number;
  lineHeight?: number;
  tracking?: number; // extra advance per glyph, in units of size
  align?: 'center' | 'left';
};

/** Extruded chrome type; multi-line, centered, with optional tracking. */
export function textMesh(font: Font, text: string, mats: THREE.Material[], o: TextOpts) {
  const group = new THREE.Group();
  const lines = text.split('\n');
  const lh = (o.lineHeight ?? 1.05) * o.size;
  lines.forEach((line, li) => {
    const lineGroup = new THREE.Group();
    let x = 0;
    for (const ch of line) {
      if (ch === ' ') {
        x += o.size * 0.28 + (o.tracking ?? 0) * o.size;
        continue;
      }
      const g = new TextGeometry(ch, {
        font, size: o.size, depth: o.depth ?? o.size * 0.22, curveSegments: 7,
        bevelEnabled: true, bevelThickness: (o.bevel ?? 0.03) * o.size, bevelSize: (o.bevel ?? 0.03) * o.size * 0.6,
        bevelSegments: 3,
      });
      g.computeBoundingBox();
      const glyph = font.data.glyphs[ch];
      const adv = ((glyph?.ha ?? 600) / font.data.resolution) * o.size;
      const m = new THREE.Mesh(g, mats);
      m.position.x = x;
      lineGroup.add(m);
      x += adv + (o.tracking ?? 0) * o.size;
    }
    const width = x - (o.tracking ?? 0) * o.size;
    lineGroup.children.forEach((c) => (c.position.x -= width / 2));
    lineGroup.position.y = -li * lh + ((lines.length - 1) * lh) / 2 - o.size * 0.36;
    lineGroup.position.z = -(o.depth ?? o.size * 0.22) / 2;
    lineGroup.userData.width = width;
    group.add(lineGroup);
  });
  return group;
}

/** Sample points on the surface of every mesh in a group (world space of the group). */
export function samplePoints(group: THREE.Object3D, n: number, seed = 11): Float32Array {
  group.updateMatrixWorld(true);
  const meshes: THREE.Mesh[] = [];
  group.traverse((o) => {
    if ((o as THREE.Mesh).isMesh) meshes.push(o as THREE.Mesh);
  });
  // Distribute by triangle area so density is even across glyphs.
  const areas = meshes.map((m) => {
    const g = m.geometry as THREE.BufferGeometry;
    const pos = g.attributes.position;
    const idx = g.index;
    let a = 0;
    const t = new THREE.Triangle();
    const cnt = idx ? idx.count : pos.count;
    for (let i = 0; i < cnt; i += 3) {
      const i0 = idx ? idx.getX(i) : i, i1 = idx ? idx.getX(i + 1) : i + 1, i2 = idx ? idx.getX(i + 2) : i + 2;
      t.a.fromBufferAttribute(pos, i0);
      t.b.fromBufferAttribute(pos, i1);
      t.c.fromBufferAttribute(pos, i2);
      a += t.getArea();
    }
    return a;
  });
  const total = areas.reduce((s, a) => s + a, 0);
  const out = new Float32Array(n * 3);
  const r = prng(seed);
  const p = new THREE.Vector3();
  let k = 0;
  const rootInv = new THREE.Matrix4().copy(group.matrixWorld).invert();
  meshes.forEach((m, mi) => {
    const count = mi === meshes.length - 1 ? n - k : Math.round((areas[mi] / total) * n);
    const sampler = (new MeshSurfaceSampler(m) as MeshSurfaceSampler & { setRandomGenerator(f: () => number): MeshSurfaceSampler }).setRandomGenerator(r).build();
    const mat = new THREE.Matrix4().multiplyMatrices(rootInv, m.matrixWorld);
    for (let i = 0; i < count && k < n; i++, k++) {
      sampler.sample(p);
      p.applyMatrix4(mat);
      out[k * 3] = p.x;
      out[k * 3 + 1] = p.y;
      out[k * 3 + 2] = p.z;
    }
  });
  return out;
}

/** Thin emissive line segments, used for grids, frames and rays. */
export function lineMat(color: string, opacity = 1) {
  return new THREE.LineBasicMaterial({
    color, transparent: true, opacity, blending: THREE.AdditiveBlending, depthWrite: false,
  });
}

/** Uniformly scale a group so its bounding box fits the given width/height. */
export function fit(group: THREE.Object3D, maxW: number, maxH = Infinity) {
  group.updateMatrixWorld(true);
  const b = new THREE.Box3().setFromObject(group);
  const s = Math.min(maxW / (b.max.x - b.min.x), maxH / (b.max.y - b.min.y));
  group.scale.multiplyScalar(s);
  return s;
}

/** Visible frustum width at a distance, for layout. */
export const viewWidth = (cam: THREE.PerspectiveCamera, dist: number) =>
  2 * dist * Math.tan(THREE.MathUtils.degToRad(cam.fov / 2)) * cam.aspect;
