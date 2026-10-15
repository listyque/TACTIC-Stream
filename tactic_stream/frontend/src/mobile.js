import { ref } from 'vue'

// Phone presentation changes together; desktop drafts and panel state stay mounted.
export const mobileLayout = window.matchMedia('(max-width: 700px)')
export const mobile = ref(mobileLayout.matches)
mobileLayout.addEventListener('change', event => { mobile.value = event.matches })

// The keyboard can shrink only the visual viewport; browser zoom keeps its own scale.
function viewportChanged() {
  const viewport = window.visualViewport
  const keyboardViewport = mobile.value && viewport?.scale === 1
  document.documentElement.style.setProperty('--phone-height', (keyboardViewport ? viewport.height : innerHeight) + 'px')
  document.documentElement.style.setProperty('--phone-top', (keyboardViewport ? viewport.offsetTop : 0) + 'px')
}
window.visualViewport?.addEventListener('resize', viewportChanged)
window.visualViewport?.addEventListener('scroll', viewportChanged)
window.addEventListener('resize', viewportChanged)
mobileLayout.addEventListener('change', viewportChanged)
viewportChanged()
