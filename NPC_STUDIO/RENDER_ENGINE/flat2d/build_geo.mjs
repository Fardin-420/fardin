// Projects Iran, Afghanistan and Turkey from Natural Earth (world-atlas, 50m)
// into one shared SVG coordinate space and writes geo.json for the scenes.
//
//   (cd RENDER_ENGINE && npm i --no-save world-atlas@2 topojson-client@3 && node flat2d/build_geo.mjs)
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { feature } = require('topojson-client');
const world = require('world-atlas/countries-50m.json');

// Equirectangular, scaled by cos(36°) so the region keeps its real proportions.
const LON0 = 25, LAT1 = 43, K = 40, COS = Math.cos((36 * Math.PI) / 180);
const proj = ([lon, lat]) => [+((lon - LON0) * K * COS).toFixed(1), +((LAT1 - lat) * K).toFixed(1)];

const ids = { iran: '364', afghanistan: '004', turkey: '792' };
const out = { projection: { LON0, LAT1, K, COS }, countries: {}, places: {} };
for (const [name, id] of Object.entries(ids)) {
  const f = feature(world, world.objects.countries.geometries.find((g) => g.id === id));
  const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
  const d = polys
    .filter((p) => p[0].length > 12) // drop tiny islands
    .map((p) => 'M' + p[0].map(proj).map((q) => q.join(',')).join('L') + 'Z')
    .join('');
  const pts = polys.flatMap((p) => p[0].map(proj));
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  out.countries[name] = { d, bbox: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)] };
}
for (const [name, ll] of Object.entries({ balkh: [66.9, 36.76], konya: [32.48, 37.87] })) out.places[name] = proj(ll);

const dest = path.join(path.dirname(fileURLToPath(import.meta.url)), 'geo.json');
fs.writeFileSync(dest, JSON.stringify(out));
console.log(Object.fromEntries(Object.entries(out.countries).map(([k, v]) => [k, v.bbox])), out.places);
