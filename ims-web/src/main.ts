import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles/prototype.css'
import App from './App.vue'
import router from './router'
import { useUserStore } from './stores/user'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.directive('perm', {
  mounted(el, binding) {
    const code = String(binding.value || '')
    if (!code) return
    const user = useUserStore()
    if (user.profile?.username === 'admin' || user.hasPerm(code)) return
    el.remove()
  },
})
app.use(router).use(ElementPlus).mount('#app')
