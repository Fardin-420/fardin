/**
 * map.js — real country borders (world-atlas countries-50m) projected with d3-geo.
 *
 * Projection: geoConicConformal, rotate [-15, 0], center [0, 52] (from the brief), standard
 * parallels 40°/62° for a good fit of Europe + western USSR. Geometry is projected ONCE into
 * "base" pixel space (projection centered on 0,0); a per-frame Camera then translates/zooms that
 * space onto the 1080x1920 frame, so camera moves are cheap affine transforms.
 *
 * Borders are modern (that is what the dataset provides); historical context is carried by color:
 *   - Kaliningrad oblast is split off Russia and treated as East Prussia (German until 1945).
 */
'use strict';

const topojson = require('topojson-client');
const d3 = require('d3-geo');
const { clamp, rgba, mix } = require('./easing');

const BASE_SCALE = 1700;
const projection = d3.geoConicConformal()
  .rotate([-15, 0]).center([0, 52]).parallels([40, 62])
  .scale(BASE_SCALE).translate([0, 0])
  .clipExtent([[-2600, -1900], [3200, 1700]]);

// ---- load & project ---------------------------------------------------------------------------
const topo = require('world-atlas/countries-50m.json');
const features = topojson.feature(topo, topo.objects.countries).features;

/** Recording "context" for d3.geoPath: collects rings as flat Float32Arrays of base coordinates. */
function recordRings(geo) {
  const rings = [];
  let cur = null;
  const ctx = {
    moveTo(x, y) { cur = [x, y]; rings.push(cur); },
    lineTo(x, y) { cur.push(x, y); },
    closePath() {},
    arc() {}, // points are never drawn
  };
  d3.geoPath(projection, ctx)(geo);
  return rings.filter((r) => r.length >= 6).map((r) => Float32Array.from(r));
}

function bboxOf(rings) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const r of rings) for (let i = 0; i < r.length; i += 2) {
    if (r[i] < x0) x0 = r[i]; if (r[i] > x1) x1 = r[i];
    if (r[i + 1] < y0) y0 = r[i + 1]; if (r[i + 1] > y1) y1 = r[i + 1];
  }
  return [x0, y0, x1, y1];
}

const COUNTRIES = new Map(); // name -> { name, rings, bbox }
for (const f of features) {
  const name = f.properties.name;
  const [cx, cy] = d3.geoCentroid(f);
  if (cy < 15 || cx < -40 || cx > 120) { if (name !== 'Russia' && name !== 'France') continue; }
  let geo = f;
  if (name === 'Russia' && f.geometry.type === 'MultiPolygon') {
    // split Kaliningrad (East Prussia) off the Russian multipolygon
    const isKal = (poly) => { const [x, y] = d3.geoCentroid({ type: 'Polygon', coordinates: poly }); return x > 19 && x < 23 && y > 54 && y < 56; };
    const kal = f.geometry.coordinates.filter(isKal);
    geo = { type: 'Feature', properties: f.properties, geometry: { type: 'MultiPolygon', coordinates: f.geometry.coordinates.filter((p) => !isKal(p)) } };
    const kr = recordRings({ type: 'MultiPolygon', coordinates: kal });
    COUNTRIES.set('East Prussia', { name: 'East Prussia', rings: kr, bbox: bboxOf(kr) });
  }
  const rings = recordRings(geo);
  if (rings.length) COUNTRIES.set(name, { name, rings, bbox: bboxOf(rings) });
}
const ALL = [...COUNTRIES.values()];

// Historical groupings (colour only; no symbols anywhere).
const GROUPS = {
  germany1939: ['Germany', 'Austria', 'Czechia', 'East Prussia'],
  poland: ['Poland'],
  lowCountries: ['Netherlands', 'Belgium', 'Luxembourg'],
  france: ['France'],
  britain: ['United Kingdom'],
  ussr: ['Russia', 'Ukraine', 'Belarus', 'Lithuania', 'Latvia', 'Estonia', 'Moldova', 'Georgia', 'Armenia',
    'Azerbaijan', 'Kazakhstan', 'Uzbekistan', 'Turkmenistan', 'Kyrgyzstan', 'Tajikistan'],
};

/** Project lon/lat -> base coordinates. */
const project = (lonlat) => projection(lonlat);

// ---- camera -----------------------------------------------------------------------------------
/**
 * Camera: looks at (lon, lat) with a zoom factor; `ax, ay` is where that point lands on screen.
 * zoom 1 ≈ Europe from Ireland to the Volga across 1080 px.
 */
class Camera {
  constructor({ lon, lat, zoom, ax = 540, ay = 940 }) {
    this.zoom = zoom; this.ax = ax; this.ay = ay;
    [this.cx, this.cy] = project([lon, lat]);
  }
  /** base -> screen */
  toScreenBase(x, y) { return [(x - this.cx) * this.zoom + this.ax, (y - this.cy) * this.zoom + this.ay]; }
  /** lon/lat -> screen */
  toScreen(lonlat) { const [x, y] = project(lonlat); return this.toScreenBase(x, y); }
  /** Push this camera's transform onto ctx (caller must save/restore). */
  apply(ctx) { ctx.translate(this.ax, this.ay); ctx.scale(this.zoom, this.zoom); ctx.translate(-this.cx, -this.cy); }
  /** visible base-space rectangle (with margin) for culling */
  view(W = 1080, H = 1920, m = 60) {
    return [this.cx + (-this.ax - m) / this.zoom, this.cy + (-this.ay - m) / this.zoom,
      this.cx + (W - this.ax + m) / this.zoom, this.cy + (H - this.ay + m) / this.zoom];
  }
}

/** Interpolate between camera keyframes {lon, lat, zoom} with eased t. */
function lerpCam(a, b, t, extra = {}) {
  // interpolate zoom geometrically so push-ins feel uniform
  const zoom = a.zoom * Math.pow(b.zoom / a.zoom, t);
  return new Camera({ lon: a.lon + (b.lon - a.lon) * t, lat: a.lat + (b.lat - a.lat) * t, zoom, ...extra });
}

// ---- drawing ----------------------------------------------------------------------------------
const visible = (c, v) => !(c.bbox[2] < v[0] || c.bbox[0] > v[2] || c.bbox[3] < v[1] || c.bbox[1] > v[3]);

function tracePath(ctx, country) {
  for (const r of country.rings) {
    ctx.moveTo(r[0], r[1]);
    for (let i = 2; i < r.length; i += 2) ctx.lineTo(r[i], r[i + 1]);
    ctx.closePath();
  }
}

function traceGroup(ctx, names) {
  for (const n of names) { const c = COUNTRIES.get(n); if (c) tracePath(ctx, c); }
}

/**
 * Draw the base map.
 * @param fills  { [countryName]: { color, amount (0..1), glow (0..1) } }
 * @param opts   { colors, alpha, sweeps: [{ names, color, origin:[lon,lat], radius (base px), soft, alpha }] }
 */
function drawMap(ctx, cam, fills = {}, opts = {}) {
  const C = opts.colors;
  const v = cam.view();
  const vis = ALL.filter((c) => visible(c, v));
  const z = cam.zoom;

  // sea
  ctx.fillStyle = C.sea;
  ctx.fillRect(-20, -20, 1120, 1960);
  drawGraticule(ctx, cam, C);

  ctx.save();
  cam.apply(ctx);
  // soft drop shadow for land (offset copy)
  ctx.save();
  ctx.translate(3 / z, 6 / z);
  ctx.fillStyle = 'rgba(0,0,0,0.55)';
  ctx.beginPath();
  for (const c of vis) tracePath(ctx, c);
  ctx.fill();
  ctx.restore();

  // land fills
  for (const c of vis) {
    const f = fills[c.name];
    ctx.beginPath();
    tracePath(ctx, c);
    ctx.fillStyle = f ? mix(C.land, f.color, f.amount) : C.land;
    ctx.fill();
  }

  // progressive "occupation" sweeps, clipped to their countries
  for (const s of opts.sweeps || []) {
    if (s.radius <= 0) continue;
    const [ox, oy] = project(s.origin);
    ctx.save();
    ctx.beginPath();
    traceGroup(ctx, s.names);
    ctx.clip();
    const soft = s.soft || 60;
    const g = ctx.createRadialGradient(ox, oy, Math.max(0, s.radius - soft), ox, oy, s.radius);
    g.addColorStop(0, rgba(s.color, s.alpha ?? 1));
    g.addColorStop(1, rgba(s.color, 0));
    ctx.fillStyle = g;
    ctx.fillRect(ox - s.radius, oy - s.radius, s.radius * 2, s.radius * 2);
    // bright advancing edge
    if (s.edge) {
      ctx.beginPath();
      ctx.arc(ox, oy, Math.max(1, s.radius - soft * 0.5), 0, Math.PI * 2);
      ctx.strokeStyle = rgba('#d8d2c4', 0.25 * s.edge);
      ctx.lineWidth = 3 / z;
      ctx.stroke();
    }
    ctx.restore();
  }

  // borders
  ctx.lineJoin = 'round';
  ctx.strokeStyle = C.border;
  ctx.lineWidth = 1.3 / z;
  ctx.beginPath();
  for (const c of vis) tracePath(ctx, c);
  ctx.stroke();

  // glows (pulsing country outlines), additive
  ctx.globalCompositeOperation = 'lighter';
  for (const c of vis) {
    const f = fills[c.name];
    if (!f || !f.glow) continue;
    ctx.beginPath();
    tracePath(ctx, c);
    ctx.strokeStyle = rgba(f.color, 0.18 * f.glow);
    ctx.lineWidth = 14 / z;
    ctx.stroke();
    ctx.strokeStyle = rgba(f.color, 0.55 * f.glow);
    ctx.lineWidth = 4 / z;
    ctx.stroke();
    ctx.fillStyle = rgba(f.color, 0.18 * f.glow);
    ctx.fill();
  }
  ctx.globalCompositeOperation = 'source-over';
  ctx.restore();
}

/** Faint lat/lon graticule with slight parallax (drawn with a slower camera). */
function drawGraticule(ctx, cam, C) {
  ctx.save();
  ctx.strokeStyle = 'rgba(216,210,196,0.045)';
  ctx.lineWidth = 1;
  const par = new Camera({ lon: 15, lat: 52, zoom: cam.zoom * 0.92, ax: cam.ax, ay: cam.ay });
  // shift parallax camera so it tracks the main camera at 92% speed
  par.cx = cam.cx * 0.92 + 0; par.cy = cam.cy * 0.92;
  ctx.beginPath();
  for (let lon = -30; lon <= 70; lon += 5) {
    for (let lat = 30; lat <= 72; lat += 1) {
      const [x, y] = par.toScreenBase(...project([lon, lat]));
      if (lat === 30) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
  }
  for (let lat = 30; lat <= 70; lat += 5) {
    for (let lon = -30; lon <= 70; lon += 1) {
      const [x, y] = par.toScreenBase(...project([lon, lat]));
      if (lon === -30) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
  }
  ctx.stroke();
  ctx.restore();
}

/**
 * Fill a lon/lat polygon (densified, so edges follow the projection) clipped to a group of
 * countries — used for front lines that don't follow national borders.
 */
function fillRegion(ctx, cam, names, polygon, color, alpha = 1, edgeAlpha = 0) {
  ctx.save();
  cam.apply(ctx);
  ctx.beginPath();
  traceGroup(ctx, names);
  ctx.clip();
  ctx.beginPath();
  for (let i = 0; i < polygon.length; i++) {
    const a = polygon[i], b = polygon[(i + 1) % polygon.length];
    for (let k = 0; k < 8; k++) {
      const [x, y] = project([a[0] + ((b[0] - a[0]) * k) / 8, a[1] + ((b[1] - a[1]) * k) / 8]);
      if (i === 0 && k === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
  }
  ctx.closePath();
  ctx.fillStyle = rgba(color, alpha);
  ctx.fill();
  if (edgeAlpha > 0) {
    ctx.strokeStyle = rgba('#d8d2c4', edgeAlpha);
    ctx.lineWidth = 2.5 / cam.zoom;
    ctx.stroke();
  }
  ctx.restore();
}

/** Fill helper: set many countries to the same {color, amount, glow}. */
function fillGroup(fills, names, color, amount = 1, glow = 0) {
  if (amount <= 0 && glow <= 0) return fills;
  for (const n of names) fills[n] = { color, amount: clamp(amount), glow };
  return fills;
}

module.exports = { projection, project, COUNTRIES, GROUPS, Camera, lerpCam, drawMap, fillGroup, fillRegion, traceGroup, BASE_SCALE };
