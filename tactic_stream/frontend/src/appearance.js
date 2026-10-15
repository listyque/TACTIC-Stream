import { computed, reactive, ref, watchEffect } from 'vue'
import { themes, iconSets, accentPresets, defaultThemeAccents } from './appearanceCatalog.js'
import { configurationPreview } from './features/configuration/preferences.js'
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

function blend(first, second, weight) {
  return first.map((value, index) => value * (1 - weight) + second[index] * weight)
}

// Theme.qml readableText uses sRGB channels and the same threshold.
export function readableText([red, green, blue]) {
  return (red * .2126 + green * .7152 + blue * .0722) / 255 > .56 ? '#172027' : '#f6f8fa'
}

export function saveAppearance() { localStorage.setItem(storageKey, JSON.stringify(appearance)) }
const systemDark = ref(typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches)
export const effectiveColorMode = computed(() => appearance.mode === 'system' ? (systemDark.value ? 'dark' : 'light') : appearance.mode)

export function initializeAppearance() {
  const media = window.matchMedia('(prefers-color-scheme: dark)')
  systemDark.value = media.matches
  media.addEventListener('change', event => { systemDark.value = event.matches })
  watchEffect(() => {
    const root = document.documentElement
    root.lang = appearance.language
    root.dataset.theme = appearance.theme
    const mode = effectiveColorMode.value
    root.dataset.mode = mode
    root.dataset.iconSet = appearance.iconSet
    const palette = hostedPalette.value || accentPresets.find(item => item.value === appearance.themeAccents[appearance.theme][mode])
    root.style.setProperty('--base', palette[mode + 'Base'])
    root.style.setProperty('--primary', palette[mode])
    const accent = palette[mode].match(/[a-f\d]{2}/gi).map(value => parseInt(value, 16))
    let base = palette[mode + 'Base'].match(/[a-f\d]{2}/gi).map(value => parseInt(value, 16))
    const dark = mode === 'dark'
    if (appearance.theme === 'material5') base = blend(base, accent, dark ? .07 : .05)
    const raised = blend(base, [255, 255, 255], dark ? .08 : .38)
    const workspace = blend(base, dark ? [0, 0, 0] : [255, 255, 255],
      dark ? (appearance.theme === 'fluent' ? .23 : .34) : (appearance.theme === 'fluent' ? .12 : .08))
    root.style.setProperty('--on-surface', readableText(workspace))
    root.style.setProperty('--on-primary', readableText(accent))
    root.style.setProperty('--on-selected', readableText(blend(accent, raised, dark ? .28 : .30)))
    for (const motion of ['click', 'hover', 'fade', 'popup']) root.dataset[motion + 'Animations'] = String(appearance[motion + 'Animations'])
    try { if (!configurationPreview.value) saveAppearance() }
    catch { /* The current choices still work when browser storage is unavailable. */ }
  })
}
