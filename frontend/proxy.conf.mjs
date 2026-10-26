// Proxy del dev server de Angular hacia el backend FastAPI.
// Se usa en la configuración "remote" (ver angular.json y scripts/up.sh):
// el navegador solo habla con el frontend y este reenvía las rutas de la
// API al backend local, que nunca queda expuesto directamente.
const backendPort = process.env.BACKEND_PORT || '8000';
const target = `http://localhost:${backendPort}`;

export default {
  '/api': { target, secure: false, changeOrigin: true },
  '/docs': { target, secure: false, changeOrigin: true },
  '/openapi.json': { target, secure: false, changeOrigin: true },
  '/health': { target, secure: false, changeOrigin: true }
};
