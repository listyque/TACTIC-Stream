import { computed, reactive, ref, watchEffect } from 'vue'
import { themes, iconSets, accentPresets, defaultThemeAccents } from './appearanceCatalog.js'
import { configurationPreview } from './features/configuration/preferences.js'
import { cssVariables, palette as sharedPalette, readableText as sharedReadableText } from '../../src/tactic_stream/shared_ui/core/foundation.mjs'
export { themes, iconSets, accentPresets } from './appearanceCatalog.js'

export const languages = [
  { value: 'en', label: 'English' },
  { value: 'ru', label: 'Russian' },
]

export const colorModes = [
  { value: 'system', label: 'System' },
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
]

const storageKey = 'tactic_stream.appearance'

// Move existing browser state once after the product namespace rename.
for (const [area, suffix] of [['localStorage', 'appearance'], ['sessionStorage', 'session']]) {
  try {
    const storage = window[area]
    const previousKey = `tactic_flow.${suffix}`
    const nextKey = `tactic_stream.${suffix}`
    const previous = storage.getItem(previousKey)
    if (previous && storage.getItem(nextKey) === null) storage.setItem(nextKey, previous)
    storage.removeItem(previousKey)
  } catch { /* Existing defaults work when browser storage is unavailable. */ }
}

function readAppearance() {
  let saved
  try { saved = JSON.parse(localStorage.getItem(storageKey) || 'null') } catch { /* Use defaults. */ }
  const language = typeof saved?.language === 'string' ? saved.language.toLowerCase().replace('_', '-').split('-')[0] : 'en'
  const themeAccents = {}
  for (const theme of themes) {
    themeAccents[theme.value] = {}
    for (const mode of ['light', 'dark']) {
      const preset = saved?.themeAccents?.[theme.value]?.[mode]
      themeAccents[theme.value][mode] = accentPresets.some(item => item.value === preset) ? preset : defaultThemeAccents[theme.value][mode]
    }
  }
  return {
    language: languages.some(item => item.value === language) ? language : 'en',
    theme: themes.some(item => item.value === saved?.theme) ? saved.theme : 'md3',
    mode: colorModes.some(item => item.value === saved?.mode) ? saved.mode : 'system',
    iconSet: iconSets.some(item => item.value === saved?.iconSet) ? saved.iconSet : 'material-design',
    discussionView: saved?.discussionView === 'notes' ? 'notes' : 'inspector',
    themeAccents,
    clickAnimations: saved?.clickAnimations !== false,
    hoverAnimations: saved?.hoverAnimations !== false,
    fadeAnimations: saved?.fadeAnimations !== false,
    popupAnimations: saved?.popupAnimations !== false,
  }
}

export const appearance = reactive(readAppearance())
export const hostedPalette = ref(null)
export const projectPalette = ref(null)

export function readableText(color) {
  return '#' + sharedReadableText(color).map(channel => channel.toString(16).padStart(2, '0')).join('')
}

export function saveAppearance() { localStorage.setItem(storageKey, JSON.stringify(appearance)) }
const systemDark = ref(typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches)
export const effectiveColorMode = computed(() => appearance.mode === 'system' ? (systemDark.value ? 'dark' : 'light') : appearance.mode)

const projectPreset = computed(() => projectPalette.value ? {
  light: projectPalette.value.light.accent, lightBase: projectPalette.value.light.base,
  dark: projectPalette.value.dark.accent, darkBase: projectPalette.value.dark.base,
} : null)
const colorPreset = computed(() => hostedPalette.value || projectPreset.value || accentPresets.find(item => item.value === appearance.themeAccents[appearance.theme][effectiveColorMode.value]))
const effectiveStyle = computed(() => hostedPalette.value ? appearance.theme : projectPalette.value?.style || appearance.theme)
const channels = hex => hex.match(/[a-f\d]{2}/gi).map(value => parseInt(value, 16))
export const frameColors = computed(() => {
  const mode = effectiveColorMode.value, preset = colorPreset.value
  return sharedPalette(effectiveStyle.value, mode === 'dark', channels(preset[mode + 'Base']), channels(preset[mode]))
})

export function initializeAppearance() {
  const media = window.matchMedia('(prefers-color-scheme: dark)')
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)')
  const reducedMotion = ref(motion.matches)
  systemDark.value = media.matches
  media.addEventListener('change', event => { systemDark.value = event.matches })
  motion.addEventListener('change', event => { reducedMotion.value = event.matches })
  watchEffect(() => {
    const root = document.documentElement
    root.lang = appearance.language
    root.dataset.theme = effectiveStyle.value
    const mode = effectiveColorMode.value
    root.dataset.mode = mode
    root.dataset.iconSet = appearance.iconSet
    const palette = colorPreset.value
    root.style.setProperty('--base', palette[mode + 'Base'])
    root.style.setProperty('--primary', palette[mode])
    const accent = palette[mode].match(/[a-f\d]{2}/gi).map(value => parseInt(value, 16))
    const base = palette[mode + 'Base'].match(/[a-f\d]{2}/gi).map(value => parseInt(value, 16))
    const dark = mode === 'dark'
    const variables = cssVariables(effectiveStyle.value, dark, base, accent, {
      click:appearance.clickAnimations, hover:appearance.hoverAnimations,
      fade:appearance.fadeAnimations, popup:appearance.popupAnimations, reduced:reducedMotion.value,
    })
    for (const [name, value] of Object.entries(variables)) root.style.setProperty(name, value)
    for (const motion of ['click', 'hover', 'fade', 'popup']) root.dataset[motion + 'Animations'] = String(appearance[motion + 'Animations'])
    try { if (!configurationPreview.value) saveAppearance() }
    catch { /* The current choices still work when browser storage is unavailable. */ }
  })
}
