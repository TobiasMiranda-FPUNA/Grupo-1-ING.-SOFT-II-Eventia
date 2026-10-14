// Entorno usado por "ng serve --configuration remote" (scripts/up.sh remote).
// La URL es relativa: el dev server de Angular reenvía /api al backend
// (ver proxy.conf.mjs), así funciona igual desde localhost o desde la URL
// pública del túnel, sin exponer el backend ni tocar el CORS.
export const environment = {
  production: false,
  apiUrl: '/api/v1'
};
