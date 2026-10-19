import * as THREE from 'three';
import { prng } from './util';

// One GPU particle system covers every particle effect in the reel. All motion
// is computed in the vertex shader from uniforms, so any frame renders
// independently (required for parallel, out-of-order frame rendering).

const vertexShader = /* glsl */ `
  attribute vec3 aTarget;
  attribute vec4 aRand;
  uniform float uTime, uMix, uStagger, uNoiseAmp, uNoiseFreq, uSize, uScale;
  uniform vec3 uDispVel; uniform float uDisp;
  uniform vec3 uExplodeCenter; uniform float uExplode;
  uniform float uDisint, uDisintDist, uSweepMin, uSweepRange;
  uniform float uGlitch, uBlocks;
  uniform float uSparkle, uRedRatio, uSwirl;
  varying float vAlpha; varying vec3 vColor; varying float vGlint;
  uniform vec3 uColorA, uColorB;

  float h1(float n) { return fract(sin(n) * 43758.5453123); }

  vec3 flow(vec3 p, float t, vec4 r) {
    return vec3(
      sin(p.y * uNoiseFreq + t * 0.9 + r.x * 6.28),
      sin(p.z * uNoiseFreq + t * 1.1 + r.y * 6.28),
      sin(p.x * uNoiseFreq + t * 0.7 + r.z * 6.28));
  }

  void main() {
    // Staggered morph start -> target with per-particle easing.
    float m = clamp((uMix - aRand.x * uStagger) / max(1.0 - uStagger, 1e-4), 0.0, 1.0);
    m = 1.0 - pow(1.0 - m, 3.0);
    vec3 p = mix(position, aTarget, m);

    // Swirl around Y while travelling (assembly vortex).
    float sw = uSwirl * (1.0 - m) * (0.6 + aRand.y);
    float cs = cos(sw), sn = sin(sw);
    p.xz = mat2(cs, -sn, sn, cs) * p.xz;

    p += flow(p, uTime, aRand) * uNoiseAmp * (0.3 + aRand.z);

    // Velocity-based displacement: faster particles lead, the rest trail.
    p += uDispVel * uDisp * (0.35 + aRand.y * 1.3) * (1.0 + 0.6 * sin(aTarget.y * 3.0));

    // Explosion.
    vec3 dir = normalize(p - uExplodeCenter + (aRand.xyz - 0.5) * 0.8);
    p += dir * uExplode * (0.4 + aRand.w * 1.4);

    // Disintegration sweeps across the shape; embers drift up and away.
    float sweep = (aTarget.x - uSweepMin) / max(uSweepRange, 1e-4);
    float d = clamp((uDisint * 1.7 - sweep * 0.7 - aRand.w * 0.35) / 0.65, 0.0, 1.0);
    p += (vec3(0.25, 1.0, 0.35) * d * d * uDisintDist) + flow(p * 1.7, uTime * 2.0, aRand) * d * 0.6;

    // Digital fragmentation: rows torn sideways in quantized blocks.
    if (uGlitch > 0.0) {
      float row = floor(aTarget.y * uBlocks);
      float k = floor(uTime * 24.0);
      float r = h1(row * 13.1 + k * 7.7);
      p.x += (r - 0.5) * uGlitch * 3.0 * step(0.45, h1(row + k));
      p = floor(p * (40.0 - uGlitch * 30.0)) / (40.0 - uGlitch * 30.0);
    }

    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    gl_Position = projectionMatrix * mv;
    float s = uSize * (0.45 + aRand.z * 0.9);
    gl_PointSize = clamp(s * uScale / -mv.z, 0.0, 64.0);

    vAlpha = (1.0 - smoothstep(0.55, 1.0, d));
    bool red = aRand.y < uRedRatio;
    vColor = red ? uColorB : uColorA;
    vColor = mix(vColor, uColorB * 1.6, smoothstep(0.15, 0.6, d) * (1.0 - smoothstep(0.6, 1.0, d)));
    vGlint = uSparkle * pow(0.5 + 0.5 * sin(uTime * (6.0 + aRand.z * 20.0) + aRand.x * 100.0), 24.0);
  }
`;

const fragmentShader = /* glsl */ `
  uniform float uOpacity;
  varying float vAlpha; varying vec3 vColor; varying float vGlint;
  void main() {
    vec2 c = gl_PointCoord - 0.5;
    float r = length(c);
    if (r > 0.5) discard;
    float soft = smoothstep(0.5, 0.0, r);
    float core = exp(-r * r * 60.0);
    vec3 col = vColor * (soft * 0.22 + core * 0.75) + vec3(1.0) * vGlint * core * 2.5;
    gl_FragColor = vec4(col * uOpacity * vAlpha, 1.0);
  }
`;

export type ParticleUniforms = {
  uTime: { value: number };
  uMix: { value: number };
  uStagger: { value: number };
  uNoiseAmp: { value: number };
  uNoiseFreq: { value: number };
  uSize: { value: number };
  uScale: { value: number };
  uOpacity: { value: number };
  uDispVel: { value: THREE.Vector3 };
  uDisp: { value: number };
  uExplodeCenter: { value: THREE.Vector3 };
  uExplode: { value: number };
  uDisint: { value: number };
  uDisintDist: { value: number };
  uSweepMin: { value: number };
  uSweepRange: { value: number };
  uGlitch: { value: number };
  uBlocks: { value: number };
  uSparkle: { value: number };
  uRedRatio: { value: number };
  uSwirl: { value: number };
  uColorA: { value: THREE.Color };
  uColorB: { value: THREE.Color };
};

/** Point sizes are authored for a 1920px-tall frame; the engine sets the real height. */
let pointScale = 1920;
export const setPointScale = (h: number) => (pointScale = h);

export class Particles {
  points: THREE.Points;
  u: ParticleUniforms;

  constructor(start: Float32Array, target: Float32Array, seed = 1, scale = pointScale) {
    const n = start.length / 3;
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(start, 3));
    g.setAttribute('aTarget', new THREE.BufferAttribute(target, 3));
    const r = prng(seed);
    const rand = new Float32Array(n * 4);
    for (let i = 0; i < rand.length; i++) rand[i] = r();
    g.setAttribute('aRand', new THREE.BufferAttribute(rand, 4));
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e4);

    let minX = Infinity, maxX = -Infinity;
    for (let i = 0; i < n; i++) {
      minX = Math.min(minX, target[i * 3]);
      maxX = Math.max(maxX, target[i * 3]);
    }

    this.u = {
      uTime: { value: 0 },
      uMix: { value: 1 },
      uStagger: { value: 0.4 },
      uNoiseAmp: { value: 0 },
      uNoiseFreq: { value: 1.3 },
      uSize: { value: 0.05 },
      uScale: { value: scale },
      uOpacity: { value: 1 },
      uDispVel: { value: new THREE.Vector3() },
      uDisp: { value: 0 },
      uExplodeCenter: { value: new THREE.Vector3() },
      uExplode: { value: 0 },
      uDisint: { value: 0 },
      uDisintDist: { value: 3 },
      uSweepMin: { value: minX },
      uSweepRange: { value: Math.max(maxX - minX, 1e-3) },
      uGlitch: { value: 0 },
      uBlocks: { value: 9 },
      uSparkle: { value: 0 },
      uRedRatio: { value: 0.06 },
      uSwirl: { value: 0 },
      uColorA: { value: new THREE.Color('#f3eee3') },
      uColorB: { value: new THREE.Color('#ff2b1c') },
    };
    const mat = new THREE.ShaderMaterial({
      uniforms: this.u as unknown as Record<string, THREE.IUniform>,
      vertexShader,
      fragmentShader,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    this.points = new THREE.Points(g, mat);
    this.points.frustumCulled = false;
  }
}

/** Uniform random points inside a spherical shell. */
export function shell(n: number, rMin: number, rMax: number, seed = 7, squash = [1, 1, 1]) {
  const r = prng(seed);
  const a = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    const u = r() * 2 - 1;
    const th = r() * Math.PI * 2;
    const s = Math.sqrt(1 - u * u);
    const rad = rMin + (rMax - rMin) * Math.cbrt(r());
    a[i * 3] = s * Math.cos(th) * rad * squash[0];
    a[i * 3 + 1] = u * rad * squash[1];
    a[i * 3 + 2] = s * Math.sin(th) * rad * squash[2];
  }
  return a;
}

/** Random points in an axis-aligned box. */
export function box(n: number, size: [number, number, number], center: [number, number, number] = [0, 0, 0], seed = 3) {
  const r = prng(seed);
  const a = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    a[i * 3] = center[0] + (r() - 0.5) * size[0];
    a[i * 3 + 1] = center[1] + (r() - 0.5) * size[1];
    a[i * 3 + 2] = center[2] + (r() - 0.5) * size[2];
  }
  return a;
}
