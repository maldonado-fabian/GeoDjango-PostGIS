export default {
  server: {
    // El puerto debe coincidir con CORS_ALLOWED_ORIGINS de Django
    // (geodjango/settings.py). strictPort evita que Vite se mueva solo a 5174
    // si 5173 está ocupado: en ese caso el navegador quedaría en un origen no
    // autorizado y todas las llamadas a la API fallarían con "No se pudo
    // conectar al servidor". Con strictPort, Vite avisa en vez de derivar.
    port: 5173,
    strictPort: true,
  },
  build: {
    sourcemap: true,
  },
}
