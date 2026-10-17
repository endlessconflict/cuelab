// node ease_ref.mjs <video-project-dir>
// Prints Remotion's own Easing.bezier curves for the three easings in the project's timeline.json, so the Python easing port can be
// checked against the real thing (python cuelab.py ease-check <video-project-dir>). Needs `npm install` done in the video project.
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const dir = path.resolve(process.argv[2]);
const require = createRequire(path.join(dir, "package.json"));
const { Easing, interpolate } = require("remotion");
const tl = JSON.parse(fs.readFileSync(path.join(dir, "timeline.json"), "utf8"));
const out = { EASE: tl.ease };
for (const [k, [a, b, c, d]] of Object.entries(tl.ease)) {
  out[k] = [];
  for (let f = 0; f <= 100; f += 2.5) out[k].push([f, interpolate(f, [0, 100], [0, 1], { easing: Easing.bezier(a, b, c, d) })]);
}
console.log(JSON.stringify(out));
