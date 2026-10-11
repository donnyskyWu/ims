import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles/prototype.css'
import App from './App.vue'
import router from './router'
import { bindSessionCleaner } from './auth/session'
import { useUserStore } from './stores/user'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
bindSessionCleaner(() => useUserStore(pinia).clearLocalSession())
app.use(router).use(ElementPlus).mount('#app')
