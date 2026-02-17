// Patches pretty-format@30.x ESM wrapper which has a broken default re-export
// that crashes Metro's HMR client on web with:
// "Cannot read properties of undefined (reading 'default')"
const fs = require('fs');
const path = require('path');

const target = path.join(__dirname, '..', 'node_modules', 'pretty-format', 'build', 'index.mjs');

if (fs.existsSync(target)) {
  const fixed = `import * as cjsModule from './index.js';
const _cjs = cjsModule.default || cjsModule;
export const DEFAULT_OPTIONS = _cjs.DEFAULT_OPTIONS;
export const format = _cjs.format;
export const plugins = _cjs.plugins;
export default _cjs.format || _cjs.default || _cjs;
`;
  fs.writeFileSync(target, fixed);
  console.log('Patched pretty-format/build/index.mjs');
}
