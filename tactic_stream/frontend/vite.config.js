import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  base: '/ui/',
  plugins: [vue()],
  build: {
    minify: false, cssMinify: true, sourcemap: true,
    outDir: '../src/tactic_stream/web', emptyOutDir: true, manifest: true,
    // shortcut: stable JS requires a page reload after deployment; use versioned directories for rolling releases.
    rolldownOptions: { output: { entryFileNames:'assets/[name].js', chunkFileNames:'assets/[name].js',
      assetFileNames: asset => asset.names.some(name => name.endsWith('.css')) ? 'assets/[name][extname]' : 'assets/[name]-[hash][extname]',
      codeSplitting: { groups: [
      { name:'vue', test:/node_modules[\\/](?:@vue|vue)[\\/]/ },
      { name:'icons', test:/src[\\/](?:icons\.js|assets[\\/]fonts[\\/].+\.json)$/ },
      { name:'locales', test:/src[\\/]locales[\\/]/ },
    ] } } },
  },
  server: { proxy: { '/api/documentation': 'http://127.0.0.1:8081', '/admin/raw-database': 'http://127.0.0.1:8081', '/admin/rpc': 'http://127.0.0.1:8081', '/admin/form': 'http://127.0.0.1:8081', '/admin/interface': 'http://127.0.0.1:8081', '/admin/widget-configuration': 'http://127.0.0.1:8081', '/admin/session': 'http://127.0.0.1:8081', '/admin/configuration': 'http://127.0.0.1:8081', '/admin/security-groups': 'http://127.0.0.1:8081', '/admin/security-rules': 'http://127.0.0.1:8081', '/health': 'http://127.0.0.1:8081' } },
})
