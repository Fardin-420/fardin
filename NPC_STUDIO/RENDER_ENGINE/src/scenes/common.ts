import * as THREE from 'three';
import { Particles, box } from '../engine/particles';

export function camera(fov = 38, aspect = 1080 / 1920) {
  const c = new THREE.PerspectiveCamera(fov, aspect, 0.05, 400);
  c.position.set(0, 0, 10);
  return c;
}

/** Faint deep-space dust: gives every shot parallax and scale. */
export function dust(n = 2600, size: [number, number, number] = [30, 50, 60], seed = 99) {
  const pts = box(n, size, [0, 0, -size[2] / 2 + 8], seed);
  const p = new Particles(pts, pts, seed);
  p.u.uSize.value = 0.035;
  p.u.uOpacity.value = 0.22;
  p.u.uNoiseAmp.value = 0.25;
  p.u.uNoiseFreq.value = 0.35;
  p.u.uRedRatio.value = 0.03;
  return p;
}

/** Large soft volumetric glow behind subjects (additive gradient billboard). */
export function glow(color = '#ff2b1c', size = 12, opacity = 0.35) {
  const mat = new THREE.ShaderMaterial({
    uniforms: { uColor: { value: new THREE.Color(color) }, uOpacity: { value: opacity } },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
    fragmentShader: `uniform vec3 uColor; uniform float uOpacity; varying vec2 vUv;
      void main(){ float d = length(vUv - 0.5) * 2.0; float a = exp(-d * d * 4.0) * uOpacity; gl_FragColor = vec4(uColor * a, 1.0); }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  });
  const m = new THREE.Mesh(new THREE.PlaneGeometry(size, size), mat);
  return m;
}

/** Fullscreen-ish light rays fanning from a point (screen-facing plane). */
export function rays(color = '#f3eee3', size = 30) {
  const mat = new THREE.ShaderMaterial({
    uniforms: { uColor: { value: new THREE.Color(color) }, uOpacity: { value: 0 }, uTime: { value: 0 } },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
    fragmentShader: `uniform vec3 uColor; uniform float uOpacity, uTime; varying vec2 vUv;
      float h(float n){ return fract(sin(n)*43758.5453); }
      void main(){
        vec2 p = vUv - 0.5; float a = atan(p.y, p.x); float r = length(p) * 2.0;
        float k = a * 18.0 / 3.14159;
        float i = floor(k); float f = fract(k);
        float beam = smoothstep(0.5, 0.0, abs(f - 0.5) - 0.12 * h(i)) * (0.35 + 0.65 * h(i + 3.0));
        beam *= 0.6 + 0.4 * sin(uTime * (0.6 + h(i) * 1.5) + i);
        float fall = exp(-r * 2.6) * smoothstep(0.0, 0.08, r);
        gl_FragColor = vec4(uColor * beam * fall * uOpacity, 1.0);
      }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  });
  return new THREE.Mesh(new THREE.PlaneGeometry(size, size), mat);
}

/** Perspective floor grid that fades into the distance. */
export function floorGrid(color = '#ff2b1c', size = 80, div = 40, y = -6) {
  const mat = new THREE.ShaderMaterial({
    uniforms: { uColor: { value: new THREE.Color(color) }, uOpacity: { value: 0.35 }, uScroll: { value: 0 } },
    vertexShader: `varying vec3 vW; void main(){ vec4 w = modelMatrix * vec4(position,1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: `uniform vec3 uColor; uniform float uOpacity, uScroll; varying vec3 vW;
      void main(){
        vec2 g = vec2(vW.x, vW.z + uScroll) / ${(size / div).toFixed(3)};
        vec2 l = abs(fract(g - 0.5) - 0.5) / fwidth(g);
        float line = 1.0 - min(min(l.x, l.y), 1.0);
        float fade = exp(-abs(vW.z + 10.0) * 0.045) * smoothstep(${(size / 2).toFixed(1)}, 10.0, abs(vW.x));
        gl_FragColor = vec4(uColor * line * fade * uOpacity, 1.0);
      }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    extensions: { derivatives: true } as never,
  });
  const m = new THREE.Mesh(new THREE.PlaneGeometry(size, size, 1, 1), mat);
  m.rotation.x = -Math.PI / 2;
  m.position.y = y;
  return m;
}

/** Key + red rim lights shared by chrome shots. */
export function chromeLights(scene: THREE.Scene) {
  const key = new THREE.DirectionalLight('#fff4e6', 2.2);
  key.position.set(-3, 5, 6);
  const rim = new THREE.PointLight('#ff2b1c', 30, 30, 1.6);
  rim.position.set(4, -1, -2);
  const fill = new THREE.PointLight('#cfd8ff', 8, 30, 1.6);
  fill.position.set(-5, -3, 4);
  scene.add(key, rim, fill, new THREE.AmbientLight('#ffffff', 0.05));
  return { key, rim, fill };
}
