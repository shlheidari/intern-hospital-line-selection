// Bundles every page entry point into a single file under the app's static dir.
// Usage: npm run build   (the bundles are committed so deploys need no Node)
import { build } from 'esbuild';

const OUT_DIR = 'myworld/line/static/line/js';

await build({
  entryPoints: {
    select: 'frontend/src/select/main.jsx',
    capacity: 'frontend/src/capacity/main.jsx',
    realtime: 'frontend/src/realtime/main.js',
    members: 'frontend/src/members/main.js',
    index: 'frontend/src/index/main.js',
    password: 'frontend/src/password/main.js',
  },
  outdir: OUT_DIR,
  bundle: true,
  minify: true,
  format: 'iife',
  target: ['es2019'],
  jsx: 'automatic',
  legalComments: 'eof',
  define: { 'process.env.NODE_ENV': '"production"' },
  logLevel: 'info',
});
