// Copies the Bootstrap 3 stylesheet and the icon font into the app's static
// dir (only the CSS is used - no jQuery or Bootstrap JS).
// Usage: npm run vendor
import { cpSync, mkdirSync } from 'node:fs';

const SRC = 'node_modules/bootstrap/dist';
const DEST = 'myworld/line/static/line/vendor/bootstrap';

mkdirSync(`${DEST}/css`, { recursive: true });
mkdirSync(`${DEST}/fonts`, { recursive: true });
cpSync(`${SRC}/css/bootstrap.min.css`, `${DEST}/css/bootstrap.min.css`);
for (const font of ['glyphicons-halflings-regular.woff2', 'glyphicons-halflings-regular.woff']) {
  cpSync(`${SRC}/fonts/${font}`, `${DEST}/fonts/${font}`);
}
cpSync('node_modules/bootstrap/LICENSE', `${DEST}/LICENSE`);
console.log('Bootstrap 3.4.1 copied to', DEST);
