import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 6173,
    proxy: {
      '/admin-api': process.env.IMS_API || 'http://127.0.0.1:18080',
    },
  },
})
