// Shim: supervisor calls `yarn expo start --tunnel --port 3000`
// This redirects to Vite dev server
import { createServer } from 'vite';

const server = await createServer({
  configFile: './vite.config.js',
  server: { port: 3000, host: '0.0.0.0' }
});
await server.listen();
server.printUrls();
