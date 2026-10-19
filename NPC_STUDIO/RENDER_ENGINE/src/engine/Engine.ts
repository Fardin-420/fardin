import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import { Font } from 'three/examples/jsm/loaders/FontLoader.js';
import { FinalShader, PostParams, defaultPost } from './post';
import { buildStudioEnv, chromeMaterials } from './chrome';
import { setPointScale } from './particles';
import type { Envelope, Timeline } from '../data';

export type Assets = {
  renderer: THREE.WebGLRenderer;
  black: Font;
  xbold: Font;
  env: THREE.Texture;
  chrome: { face: THREE.MeshStandardMaterial; side: THREE.MeshStandardMaterial };
  codeText: string;
  width: number;
  height: number;
};

export type Ctx = {
  t: number; // global seconds
  local: number; // seconds since scene start
  frame: number;
  tl: Timeline;
  cue: (k: string) => number;
  env: Envelope;
};

export interface SceneModule {
  id: string;
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  update(ctx: Ctx): Partial<PostParams>;
}

export type SceneFactory = (a: Assets, tl: Timeline) => SceneModule;

export class Engine {
  renderer: THREE.WebGLRenderer;
  composer: EffectComposer;
  renderPass: RenderPass;
  bloom: UnrealBloomPass;
  final: ShaderPass;
  scenes: SceneModule[] = [];

  constructor(
    public canvas: HTMLCanvasElement,
    public width: number,
    public height: number,
    public tl: Timeline,
    public env: Envelope,
  ) {
    this.renderer = new THREE.WebGLRenderer({
      canvas, antialias: true, preserveDrawingBuffer: true, powerPreference: 'high-performance',
    });
    this.renderer.setPixelRatio(1);
    this.renderer.setSize(width, height, false);
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.0;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;

    const rt = new THREE.WebGLRenderTarget(width, height, { type: THREE.HalfFloatType, samples: 4 });
    this.composer = new EffectComposer(this.renderer, rt);
    this.composer.setPixelRatio(1);
    this.composer.setSize(width, height);
    this.renderPass = new RenderPass(new THREE.Scene(), new THREE.PerspectiveCamera());
    this.bloom = new UnrealBloomPass(new THREE.Vector2(width / 2, height / 2), 0.9, 0.55, 0.12);
    this.final = new ShaderPass(FinalShader);
    this.final.uniforms.uRes.value = [width, height];
    this.composer.addPass(this.renderPass);
    this.composer.addPass(this.bloom);
    this.composer.addPass(new OutputPass());
    this.composer.addPass(this.final);
  }

  async load(staticUrl: (p: string) => string, factories: SceneFactory[]) {
    const json = (p: string) => fetch(staticUrl(p)).then((r) => r.json());
    // Canvas-drawn code textures need the mono face registered before drawing.
    for (const [w, f] of [['500', 'JetBrainsMono-Medium.ttf'], ['400', 'JetBrainsMono-Regular.ttf']]) {
      const face = new FontFace('NPC Mono', `url(${staticUrl(`fonts/${f}`)})`, { weight: w });
      document.fonts.add(await face.load());
    }
    const [black, xbold, codeText] = await Promise.all([
      json('fonts/InterDisplay-Black.typeface.json'),
      json('fonts/InterDisplay-ExtraBold.typeface.json'),
      fetch(staticUrl('code/engine_source.txt')).then((r) => r.text()),
    ]);
    setPointScale(this.height);
    const env = buildStudioEnv(this.renderer);
    const assets: Assets = {
      renderer: this.renderer,
      black: new Font(black),
      xbold: new Font(xbold),
      env,
      chrome: chromeMaterials(env),
      codeText,
      width: this.width,
      height: this.height,
    };
    this.scenes = factories.map((f) => f(assets, this.tl));
    // Compile every shader up front so frame timing is stable.
    for (const s of this.scenes) this.renderer.compile(s.scene, s.camera);
  }

  render(t: number, frame: number) {
    const tl = this.tl;
    const bounds = tl.scenes.find((s) => t >= s.start && t < s.end) ?? tl.scenes[tl.scenes.length - 1];
    const mod = this.scenes.find((s) => s.id === bounds.id)!;
    const cue = (k: string) => {
      const v = tl.cues[k];
      if (v === undefined) throw new Error(`unknown cue ${k}`);
      return v;
    };
    const p: PostParams = { ...defaultPost(), ...mod.update({ t, local: t - bounds.start, frame, tl, cue, env: this.env }) };

    this.renderPass.scene = mod.scene;
    this.renderPass.camera = mod.camera;
    this.bloom.strength = p.bloom;
    this.bloom.radius = p.bloomRadius;
    this.bloom.threshold = p.bloomThreshold;
    const u = this.final.uniforms;
    u.uTime.value = t;
    u.uAberration.value = p.aberration;
    u.uDirBlur.value = p.dirBlur;
    u.uZoomBlur.value = p.zoomBlur;
    u.uZoomCenter.value = p.zoomCenter;
    u.uShockCenter.value = p.shockCenter;
    u.uShockRadius.value = p.shockRadius;
    u.uShockStrength.value = p.shockStrength;
    u.uGlitch.value = p.glitch;
    u.uFlash.value = p.flash;
    u.uRedFlash.value = p.redFlash;
    u.uVignette.value = p.vignette;
    u.uGrain.value = p.grain;
    u.uFade.value = p.fade;
    u.uExposure.value = p.exposure;
    this.composer.render();
  }
}
