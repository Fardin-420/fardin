// Final cinematic pass: shockwave distortion, block glitch, directional + zoom
// motion blur, chromatic aberration, grade, flash, vignette, grain, fade.

export type PostParams = {
  bloom: number; // UnrealBloom strength
  bloomRadius: number;
  bloomThreshold: number;
  exposure: number;
  aberration: number; // pixels at the frame edge
  dirBlur: [number, number]; // blur vector in UV units
  zoomBlur: number; // radial blur amount
  zoomCenter: [number, number];
  shockCenter: [number, number];
  shockRadius: number;
  shockStrength: number;
  glitch: number;
  flash: number; // additive white/ivory
  redFlash: number; // additive red energy
  vignette: number;
  grain: number;
  fade: number; // 1 = black
};

export const defaultPost = (): PostParams => ({
  bloom: 0.9,
  bloomRadius: 0.45,
  bloomThreshold: 0.85,
  exposure: 1,
  aberration: 1.2,
  dirBlur: [0, 0],
  zoomBlur: 0,
  zoomCenter: [0.5, 0.5],
  shockCenter: [0.5, 0.5],
  shockRadius: -1,
  shockStrength: 0,
  glitch: 0,
  flash: 0,
  redFlash: 0,
  vignette: 0.55,
  grain: 0.045,
  fade: 0,
});

export const FinalShader = {
  uniforms: {
    tDiffuse: { value: null },
    uTime: { value: 0 },
    uRes: { value: [1080, 1920] },
    uAberration: { value: 1 },
    uDirBlur: { value: [0, 0] },
    uZoomBlur: { value: 0 },
    uZoomCenter: { value: [0.5, 0.5] },
    uShockCenter: { value: [0.5, 0.5] },
    uShockRadius: { value: -1 },
    uShockStrength: { value: 0 },
    uGlitch: { value: 0 },
    uFlash: { value: 0 },
    uRedFlash: { value: 0 },
    uVignette: { value: 0.5 },
    uGrain: { value: 0.04 },
    uFade: { value: 0 },
    uExposure: { value: 1 },
  },
  vertexShader: /* glsl */ `
    varying vec2 vUv;
    void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
  `,
  fragmentShader: /* glsl */ `
    uniform sampler2D tDiffuse;
    uniform float uTime, uAberration, uZoomBlur, uShockRadius, uShockStrength, uGlitch;
    uniform float uFlash, uRedFlash, uVignette, uGrain, uFade, uExposure;
    uniform vec2 uRes, uDirBlur, uZoomCenter, uShockCenter;
    varying vec2 vUv;

    float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

    vec3 sampleCA(vec2 uv, float ca) {
      vec2 d = (uv - 0.5) * ca / uRes.x;
      return vec3(texture2D(tDiffuse, uv + d).r, texture2D(tDiffuse, uv).g, texture2D(tDiffuse, uv - d).b);
    }

    void main() {
      vec2 uv = vUv;
      float aspect = uRes.x / uRes.y;

      // Shockwave: a refracting ring travelling outwards.
      if (uShockRadius > 0.0) {
        vec2 p = (uv - uShockCenter) * vec2(aspect, 1.0);
        float d = length(p);
        float ring = d - uShockRadius;
        float w = 0.06;
        float m = exp(-ring * ring / (w * w)) * uShockStrength;
        uv -= normalize(p + 1e-5) / vec2(aspect, 1.0) * m * 0.06;
      }

      // Block glitch: horizontal slices torn sideways, re-seeded 30x per second.
      float ga = 0.0;
      if (uGlitch > 0.0) {
        float t = floor(uTime * 30.0);
        float row = floor(uv.y * 48.0);
        float r = hash(vec2(row, t));
        if (r < uGlitch * 0.55) {
          float off = (hash(vec2(t, row + 7.0)) - 0.5) * 0.18 * uGlitch;
          uv.x += off;
          ga = uGlitch;
        }
      }

      float ca = uAberration + ga * 18.0;
      vec3 col = vec3(0.0);
      const int N = 12;
      float bl = length(uDirBlur) + uZoomBlur;
      if (bl > 0.0005) {
        for (int i = 0; i < N; i++) {
          float k = (float(i) / float(N - 1) - 0.5);
          vec2 o = uDirBlur * k + (uv - uZoomCenter) * uZoomBlur * k;
          col += sampleCA(uv + o, ca);
        }
        col /= float(N);
      } else {
        col = sampleCA(uv, ca);
      }

      col *= uExposure;
      // Grade: crush blacks, warm ivory highlights, cool deep shadows.
      col = max(col - 0.004, 0.0) * 1.004;
      float l = dot(col, vec3(0.2126, 0.7152, 0.0722));
      col = mix(col, col * vec3(1.03, 1.0, 0.95), smoothstep(0.4, 1.0, l));
      col = mix(col, col * vec3(0.94, 0.97, 1.05), 1.0 - smoothstep(0.0, 0.25, l));

      col += vec3(1.0, 0.96, 0.9) * uFlash;
      col += vec3(1.0, 0.12, 0.05) * uRedFlash;

      vec2 q = (vUv - 0.5) * vec2(aspect, 1.0) * 1.6;
      col *= mix(1.0, smoothstep(1.25, 0.2, length(q)), uVignette);

      float g = hash(vUv * uRes + fract(uTime * 13.37) * 100.0) - 0.5;
      col += g * uGrain;
      col *= 1.0 - uFade;
      gl_FragColor = vec4(col, 1.0);
    }
  `,
};
