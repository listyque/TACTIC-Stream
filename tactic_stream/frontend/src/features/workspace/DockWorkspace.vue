<script setup>
// Handler DockHost/DockPanel and workspace_models/docks_*.py, EPL-1.0.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import AppMenu from '../../controls/AppMenu.vue'
import AppMenuItem from '../../controls/AppMenuItem.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppIcon from '../../controls/AppIcon.vue'
import DockGrip from '../../controls/DockGrip.vue'
import WorkspaceTabs from '../../controls/WorkspaceTabs.vue'
import { workspaceLayouts } from '../../api.js'
import { activate, captureLayout, decodeLayout, defaults, defaultStackTargets, dockPanels, ids, place, projectTree, readDocks, remove, stack } from './docks.js'

const props = defineProps({ login: String, ticket: String, project: String, resultsActive: Boolean, canAdminister: Boolean, mobile: Boolean, menuTarget: Object })
const emit = defineEmits(['open', 'changing', 'changed', 'error', 'help'])
const host = ref(null), state = ref(readDocks(props.login)), width = ref(0), height = ref(0)
const dragged = ref(''), drop = ref(null)
const compactActive = computed({ get: () => state.value.compactActive, set: value => { state.value.compactActive = value } })
const maximized = computed({ get: () => state.value.maximized, set: value => { state.value.maximized = value } })
const contextMenu = ref(null), contextPanel = ref('results')
const positionTarget = ref('results')
const catalog = ref(null), presetBusy = ref(false), presetError = ref(''), uncertain = ref(false), activePreset = ref('')
const nameDialog = ref(null), deleteDialog = ref(null), presetTitle = ref(''), deleting = ref(null), presetMenu = ref(null)
let presetRequest = 0
const presets = computed(() => (catalog.value?.presets || []).map(row => {
  if (!row.valid) return row
  try { decodeLayout(row.configuration); return row }
  catch (error) { return { ...row, valid: false, error: error.message } }
}))
let observer, gesture = null, applying = false
const compact = computed(() => props.mobile || width.value < 640 || height.value < 440)
const phonePanels = computed(() => dockPanels.filter(panel => panel.id !== 'drop_plate' && (!['tasks','task_calendar'].includes(panel.id) || props.canAdminister)))
const visible = computed(() => (props.mobile ? phonePanels.value : dockPanels).filter(panel => (state.value.panels[panel.id].visible || props.mobile && compactActive.value === panel.id) && (!['tasks','task_calendar'].includes(panel.id) || props.canAdminister)))
watch(visible, panels => { if (!props.mobile && maximized.value && !panels.some(panel => panel.id === maximized.value)) maximized.value = '' })
const projection = computed(() => {
  const available = visible.value.filter(panel => !state.value.panels[panel.id].floating).map(panel => panel.id)
  if (compact.value) {
    const panels = visible.value.map(panel => panel.id)
    return { stacks: panels.length ? [{ panels, active: panels.includes(compactActive.value) ? compactActive.value : panels[0], rect: [0, 0, 1, 1] }] : [], dividers: [] }
  }
  if (available.includes(maximized.value) || visible.value.some(panel => panel.id === maximized.value)) return { stacks: [{ panels: [maximized.value], active: maximized.value, rect: [0, 0, 1, 1] }], dividers: [] }
  return projectTree(state.value.layout, available, width.value, height.value)
})
function stackFor(id) { return projection.value.stacks.find(item => item.panels.includes(id)) }
function presented(id) {
  if (!visible.value.some(panel => panel.id === id)) return false
  if (!compact.value && !maximized.value && state.value.panels[id].floating) return true
  return stackFor(id)?.active === id
}
watch(() => props.mobile, phone => {
  if (!phone) return
  const panels = phonePanels.value.filter(panel => state.value.panels[panel.id].visible).map(panel => panel.id)
  const active = panels.includes(maximized.value) ? [maximized.value]
    : [...projectTree(state.value.layout, panels.filter(id => !state.value.panels[id].floating), width.value, height.value).stacks.map(item => item.active),
      ...panels.filter(id => state.value.panels[id].floating)]
  // A saved phone choice may refer to a hidden or inactive desktop panel.
  compactActive.value = active.includes(compactActive.value) ? compactActive.value : active.includes('results') ? 'results' : active[0] || 'results'
  changed()
})
// Geometry changes can reveal a restored panel after its lazy screen mounted.
watch(() => visible.value.filter(panel => presented(panel.id)).map(panel => panel.id).join(','), () => emit('changed'), { flush:'post' })
function rectangle(id) {
  let rect = stackFor(id)?.rect || state.value.panels[id].rect
  if (!compact.value && state.value.panels[id].floating && !maximized.value) {
    const [x, y, w, h] = rect
    const fw = Math.min(width.value, Math.max(280, w * width.value)), fh = Math.min(height.value, Math.max(200, h * height.value))
    return { left: Math.max(0, Math.min(x * width.value, width.value - fw)) + 'px', top: Math.max(0, Math.min(y * height.value, height.value - fh)) + 'px', width: fw + 'px', height: fh + 'px', zIndex: state.value.panels[id].z + 10 }
  }
  const [x, y, w, h] = rect
  return { left: Math.round(x * width.value) + 'px', top: Math.round(y * height.value) + 'px', width: Math.round((x + w) * width.value) - Math.round(x * width.value) + 'px', height: Math.round((y + h) * height.value) - Math.round(y * height.value) + 'px' }
}
function header(id) { return id !== 'results' || state.value.panels[id].floating || (stackFor(id)?.panels.length || 0) > 1 }
function save() {
  if (!props.login) return true
  try { localStorage.setItem('tactic_stream.docks.' + props.login, JSON.stringify(state.value)); return true }
  catch { emit('error', 'Unable to save preferences. Browser storage is unavailable or full.'); return false }
}
async function changed() { save(); await nextTick(); emit('changed') }
function raise(id) { state.value.panels[id].z = Math.max(...Object.values(state.value.panels).map(panel => panel.z)) + 1 }
async function select(id) {
  const restoreFocus = document.activeElement?.closest('[data-kind="dock"]')
  emit('changing'); compactActive.value = id
  if (!props.mobile) state.value.layout = activate(state.value.layout, id)
  await changed()
  if (restoreFocus) host.value?.querySelector(`[data-dock="${id}"] [data-tab-id="${id}"]`)?.focus()
}
function selectPhone(id) { select(id); if (id !== 'results') emit('open',id) }
function reorderStack(id, source, target) {
  const order = [...stackFor(id).panels]
  order.splice(target, 0, ...order.splice(source, 1))
  let node = state.value.layout
  function reorder(current) {
    if (!current) return
    if (current.type === 'stack') {
      if (current.panels.includes(id) && order.length && new Set(order).size === order.length && order.every(value => current.panels.includes(value))) {
        let index = 0; current.panels = current.panels.map(value => order.includes(value) ? order[index++] : value)
      }
    } else { reorder(current.first); reorder(current.second) }
  }
  emit('changing'); reorder(node); changed()
}
function panelKey(event, id) {
  if (props.mobile || event.target !== event.currentTarget) return
  if (event.key === 'F10' && event.shiftKey) {
    event.preventDefault(); const box = event.currentTarget.getBoundingClientRect()
    panelMenu({ target:event.currentTarget, clientX:box.left+24, clientY:box.bottom }, id); return
  }
  if (event.altKey && event.key === 'F10') { event.preventDefault(); maximize(id); return }
  if (!event.altKey || !['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key) || !state.value.panels[id].floating || maximized.value) return
  event.preventDefault(); emit('changing')
  const rect = state.value.panels[id].rect, dx = event.key === 'ArrowLeft' ? -10/width.value : event.key === 'ArrowRight' ? 10/width.value : 0
  const dy = event.key === 'ArrowUp' ? -10/height.value : event.key === 'ArrowDown' ? 10/height.value : 0
  if (event.shiftKey) {
    rect[2] = Math.max(Math.min(1,280/width.value), Math.min(1-rect[0],rect[2]+dx))
    rect[3] = Math.max(Math.min(1,200/height.value), Math.min(1-rect[1],rect[3]+dy))
  } else {
    rect[0] = Math.max(0,Math.min(1-rect[2],rect[0]+dx)); rect[1] = Math.max(0,Math.min(1-rect[3],rect[1]+dy))
  }
  changed()
}
function show(id) {
  if (applying) return
  const panel = state.value.panels[id]
  if (!panel) return
  if (props.mobile) { select(id); return }
  emit('changing'); panel.visible = true; compactActive.value = id; maximized.value = ''
  if (!panel.floating && !ids(state.value.layout).includes(id)) {
    const target = defaultStackTargets[id]
    if (target && !state.value.panels[target].floating) {
      if (!ids(state.value.layout).includes(target)) state.value.layout = place(state.value.layout, target, target === 'tasks' ? 'center' : 'right')
      state.value.layout = place(state.value.layout, id, 'center', target)
    } else state.value.layout = place(state.value.layout, id, id === 'tasks' ? 'center' : 'right')
  }
  state.value.layout = activate(state.value.layout, id); raise(id); changed()
}
function hide(id) {
  if (id === 'results') return
  if (props.mobile) { select('results'); return }
  emit('changing'); state.value.panels[id].visible = false; maximized.value = ''; changed()
}
function toggle(id) { if (state.value.panels[id].visible) hide(id); else { show(id); emit('open', id) } }
function move(id, side, target = '') {
  if (target === id || side === 'swap' && state.value.panels[target]?.floating) return
  emit('changing'); maximized.value = ''; state.value.panels[id].floating = false
  state.value.layout = place(state.value.layout, id, side, target); compactActive.value = id; changed()
}
function float(id) {
  emit('changing'); maximized.value = ''
  const bounds = rectangle(id), w = Math.max(.32, Math.min(.68, parseFloat(bounds.width) / width.value)), h = Math.max(.26, Math.min(.72, parseFloat(bounds.height) / height.value))
  state.value.panels[id].rect = [Math.max(.04, (1 - w) / 2), Math.max(.04, (1 - h) / 2), w, h]
  state.value.panels[id].floating = true
  state.value.layout = remove(state.value.layout, id); raise(id); changed()
}
function maximize(id) { emit('changing'); maximized.value = maximized.value === id ? '' : id; changed() }
function reset() { emit('changing'); state.value = defaults(); compactActive.value = 'results'; maximized.value = ''; changed() }
function capture() { return { ...captureLayout(state.value), presentation: { maximized: maximized.value, compactActive: compactActive.value } } }
function apply(configuration) {
  let next
  try { next = decodeLayout(configuration) }
  catch (error) { emit('error', error.message); return false }
  emit('changing'); cancelGesture(); state.value = next
  applying = true
  try { for (const panel of visible.value) if (panel.id !== 'results') emit('open', panel.id, true) }
  finally { applying = false }
  changed(); return true
}
async function refreshLayouts() {
  const request = ++presetRequest, ticket = props.ticket, project = props.project
  catalog.value = null; presetError.value = ''; activePreset.value = ''; presetBusy.value = true
  if (!ticket || !project) { presetBusy.value = false; return }
  try {
    const result = await workspaceLayouts('read', ticket, project)
    if (request === presetRequest) { catalog.value = result; uncertain.value = false }
  } catch (error) { if (request === presetRequest) presetError.value = error.message }
  finally { if (request === presetRequest) presetBusy.value = false }
}
async function applyAssigned(view, stillCurrent = () => true) {
  const ticket = props.ticket, project = props.project
  if (!catalog.value || !catalog.value.presets.some(row => row.view === view)) await refreshLayouts()
  if (ticket !== props.ticket || project !== props.project || !stillCurrent()) return false
  const row = presets.value.find(row => row.view === view)
  if (!row?.valid) { emit('error', row?.error || 'This workspace layout preset is unavailable or invalid'); return false }
  if (!apply(row.configuration)) return false
  activePreset.value = row.view; return true
}
async function mutatePreset(action, values = {}) {
  if (!props.canAdminister || presetBusy.value || !catalog.value || uncertain.value) return
  const request = presetRequest, ticket = props.ticket, project = props.project
  presetBusy.value = true; presetError.value = ''
  try {
    const result = await workspaceLayouts(action, ticket, project, { revision: catalog.value.revision, ...values })
    if (request !== presetRequest) return
    catalog.value = result; nameDialog.value.close(); deleteDialog.value.close()
    if (action === 'save') activePreset.value = result.presets.find(row => row.title === values.title)?.view || ''
    else if (!result.presets.some(row => row.view === activePreset.value)) activePreset.value = ''
  } catch (error) {
    if (request === presetRequest) {
      uncertain.value = !error.status || error.status >= 500
      presetError.value = uncertain.value ? 'The save result is unknown. Refresh layout presets before trying again.' : error.message
    }
  } finally { if (request === presetRequest) presetBusy.value = false }
}
function savePreset(row = null) { mutatePreset('save', { code: row?.code, title: row?.title || presetTitle.value.trim(), configuration: captureLayout(state.value) }) }
function namePreset() { presetTitle.value = ''; presetError.value = ''; nameDialog.value.showModal(); nextTick(() => nameDialog.value.querySelector('input').focus()) }
function deletePreset(row) { deleting.value = row; presetError.value = ''; deleteDialog.value.showModal() }
function panelMenu(event, id) {
  if (props.mobile) return
  contextPanel.value = id; contextMenu.value.openAt(event)
}
function titlePress(event, id) {
  if (!state.value.panels[id].floating || maximized.value || event.target.closest('button, a, input, select, textarea, summary, label, [role="button"], [role="tab"], .dock-move-handle')) return
  start(event, id, 'float-move')
}
function cancelGesture() { if (gesture) stop({ pointerId: gesture.pointer, type: 'pointercancel' }) }
function escapeGesture(event) {
  if (event.key !== 'Escape' || !gesture) return
  event.preventDefault(); event.stopImmediatePropagation(); cancelGesture()
}
function start(event, id, kind, divider = null, edge = 'bottom-right') {
  if (gesture || event.button !== 0 || event.isPrimary === false || compact.value) return
  event.preventDefault(); emit('changing')
  const target = event.currentTarget
  target.setPointerCapture(event.pointerId)
  gesture = { id, kind, divider, edge, x: event.clientX, y: event.clientY, target, pointer: event.pointerId,
    before: JSON.parse(JSON.stringify(state.value)), maximized: maximized.value,
    rect: host.value.querySelector(`[data-dock="${id}"]`)?.getBoundingClientRect(), origin: [...(state.value.panels[id]?.rect || [])] }
  if (kind === 'resize' || kind === 'float-move') {
    const box = host.value.getBoundingClientRect(), rect = gesture.rect
    gesture.origin = [(rect.left-box.left)/box.width, (rect.top-box.top)/box.height, rect.width/box.width, rect.height/box.height]
  }
}
function pointer(event) {
  if (!gesture || gesture.pointer !== event.pointerId) return
  const bounds = host.value.getBoundingClientRect(), dx = event.clientX - gesture.x, dy = event.clientY - gesture.y
  if (gesture.kind === 'split') {
    let node = state.value.layout
    for (const step of gesture.divider.path) node = step === '0' ? node.first : node.second
    const [x, y, w, h] = gesture.divider.rect, horizontal = node.orientation === 'horizontal'
    const value = horizontal ? ((event.clientX - bounds.left) / bounds.width - x) / w : ((event.clientY - bounds.top) / bounds.height - y) / h
    node.ratio = Math.max(gesture.divider.minimum, Math.min(1 - gesture.divider.minimum, value)); return
  }
  const panel = state.value.panels[gesture.id]
  if (gesture.kind === 'float-move') {
    gesture.moved ||= Math.hypot(dx, dy) >= 5
    if (!gesture.moved) return
    const [x, y, w, h] = gesture.origin
    panel.rect = [Math.max(0, Math.min(1 - w, x + dx / bounds.width)), Math.max(0, Math.min(1 - h, y + dy / bounds.height)), w, h]
    return
  }
  if (gesture.kind === 'resize') {
    const [x, y, w, h] = gesture.origin, minimumWidth = Math.min(1, 280 / bounds.width), minimumHeight = Math.min(1, 200 / bounds.height)
    const left = gesture.edge.includes('left') ? Math.max(0, Math.min(x + w - minimumWidth, x + dx / bounds.width)) : x
    const top = gesture.edge.includes('top') ? Math.max(0, Math.min(y + h - minimumHeight, y + dy / bounds.height)) : y
    const right = gesture.edge.includes('right') ? Math.min(1, Math.max(x + minimumWidth, x + w + dx / bounds.width)) : x + w
    const bottom = gesture.edge.includes('bottom') ? Math.min(1, Math.max(y + minimumHeight, y + h + dy / bounds.height)) : y + h
    panel.rect = [left, top, right - left, bottom - top]; return
  }
  if (!dragged.value && Math.hypot(dx, dy) < 5) return
  if (!dragged.value) {
    maximized.value = ''
    dragged.value = gesture.id; panel.floating = true; state.value.layout = remove(state.value.layout, gesture.id); raise(gesture.id)
    panel.rect = [(gesture.rect.left - bounds.left) / bounds.width, (gesture.rect.top - bounds.top) / bounds.height,
      Math.min(.68, gesture.rect.width / bounds.width), Math.min(.72, gesture.rect.height / bounds.height)]
    gesture.origin = [...panel.rect]
  }
  panel.rect[0] = Math.max(0, Math.min(1 - panel.rect[2], gesture.origin[0] + dx / bounds.width))
  panel.rect[1] = Math.max(0, Math.min(1 - panel.rect[3], gesture.origin[1] + dy / bounds.height))
  drop.value = null
  for (const item of projection.value.stacks) {
    const [x, y, w, h] = item.rect, px = (event.clientX - bounds.left) / bounds.width, py = (event.clientY - bounds.top) / bounds.height
    if (px < x || py < y || px > x + w || py > y + h) continue
    const rx = (px - x) / w, ry = (py - y) / h
    drop.value = { target: item.active, side: rx < .25 ? 'left' : rx > .75 ? 'right' : ry < .25 ? 'top' : ry > .75 ? 'bottom' : 'center' }
  }
}
function stop(event) {
  if (!gesture || gesture.pointer !== event.pointerId) return
  const current = gesture; gesture = null
  if (current.target.hasPointerCapture(current.pointer)) current.target.releasePointerCapture(current.pointer)
  if (event.type === 'pointercancel') { state.value = current.before; maximized.value = current.maximized }
  if (event.type !== 'pointercancel' && dragged.value && drop.value) move(dragged.value, drop.value.side, drop.value.target)
  dragged.value = ''; drop.value = null; changed()
}
function dividerStyle(item) {
  const [x, y, w, h] = item.rect
  return item.orientation === 'horizontal' ? { left: `calc(${item.boundary * 100}% - 5px)`, top: y * 100 + '%', height: h * 100 + '%', width: '10px' }
    : { top: `calc(${item.boundary * 100}% - 5px)`, left: x * 100 + '%', width: w * 100 + '%', height: '10px' }
}
function resizeKey(event, item) {
  if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) return
  event.preventDefault(); emit('changing')
  let node = state.value.layout
  for (const step of item.path) node = step === '0' ? node.first : node.second
  node.ratio = event.key === 'Home' ? item.minimum : event.key === 'End' ? 1 - item.minimum
    : Math.max(item.minimum, Math.min(1 - item.minimum, item.ratio + (['ArrowLeft', 'ArrowUp'].includes(event.key) ? -.02 : .02)))
  changed()
}
function floatSize(event, id) {
  if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return
  event.preventDefault(); emit('changing')
  const rect = state.value.panels[id].rect, horizontal = ['ArrowLeft', 'ArrowRight'].includes(event.key)
  const axis = horizontal ? 2 : 3, minimum = horizontal ? .2 : .16, maximum = 1 - rect[horizontal ? 0 : 1]
  rect[axis] = Math.max(minimum, Math.min(maximum, rect[axis] + (['ArrowLeft', 'ArrowUp'].includes(event.key) ? -.02 : .02)))
  changed()
}
watch(() => props.login, () => { cancelGesture(); state.value = readDocks(props.login) })
watch(() => [props.ticket, props.project], () => { uncertain.value = false; nameDialog.value?.close(); deleteDialog.value?.close(); refreshLayouts() }, { immediate: true })
watch(() => props.canAdminister, value => { if (value) for (const id of ['tasks','task_calendar']) if (state.value.panels[id].visible) emit('open', id, true) })
onMounted(async () => {
  window.addEventListener('keydown', escapeGesture, true)
  window.addEventListener('blur', cancelGesture); window.addEventListener('pagehide', cancelGesture)
  observer = new ResizeObserver(entries => { const box = entries[0].contentRect; width.value = box.width; height.value = box.height })
  observer.observe(host.value)
  await nextTick()
  for (const panel of visible.value) if (panel.id !== 'results') emit('open', panel.id, true)
})
onBeforeUnmount(() => {
  presetRequest++; cancelGesture(); observer?.disconnect(); save()
  window.removeEventListener('keydown', escapeGesture, true)
  window.removeEventListener('blur', cancelGesture); window.removeEventListener('pagehide', cancelGesture)
})
defineExpose({ show, hide, move, maximize, reset, save, capture, apply, applyAssigned, refreshLayouts, presented })
</script>

<template>
  <div ref="host" class="dock-workspace" @pointermove="pointer" @pointerup="stop" @pointercancel="stop" @lostpointercapture="gesture?.target === $event.target && cancelGesture()">
    <Teleport v-if="mobile" defer to="#mobile-panel-picker"><AppSelect class="phone-panel-picker" :model-value="projection.stacks[0]?.active || 'results'" label="Active panel" :options="phonePanels.map(item => ({value:item.id,label:item.id === 'results' ? 'Search' : item.title}))" @update:model-value="selectPhone" /></Teleport>
    <section v-for="panel in dockPanels" :key="panel.id" v-show="presented(panel.id)" class="dock-panel" :data-dock="panel.id"
      :class="{ floating: !compact && state.panels[panel.id].floating, dragging: dragged === panel.id }" :style="rectangle(panel.id)" @pointerdown="!mobile && raise(panel.id)">
      <header v-if="mobile && !['results','notes'].includes(panel.id)" class="phone-panel-heading">
        <AppButton label="Back to search" icon="MDI_ARROW_LEFT" icon-only @click="hide(panel.id)" />
        <strong>{{ t(panel.title) }}</strong>
      </header>
      <header v-if="!mobile && header(panel.id)" class="dock-titlebar" tabindex="0" @pointerdown="titlePress($event,panel.id)" @keydown="panelKey($event,panel.id)" @contextmenu.prevent.stop="panelMenu($event, panel.id)" @dblclick="!$event.target.closest('button,summary,.dock-move-handle') && maximize(panel.id)">
        <template v-if="(stackFor(panel.id)?.panels.length || 0) > 1">
          <WorkspaceTabs class="dock-stack-tabs" kind="dock" :reorderable="!compact" :selected="panel.id" :tabs="stackFor(panel.id).panels.map(id => ({ ...dockPanels.find(item => item.id === id), icon:id === 'results' ? 'view-kanban' : dockPanels.find(item => item.id === id).icon, title:t(id === 'results' ? 'Search' : dockPanels.find(item => item.id === id).title) }))" @select="select" @close="hide" @reorder="(source, target) => reorderStack(panel.id, source, target)" />
        </template>
        <template v-else><AppIcon :name="panel.icon" /><strong>{{ t(panel.title) }}</strong></template>
        <span v-if="!mobile" class="dock-move-handle" :title="t('Drag to move or dock')" :aria-label="t('Drag to move or dock')" @pointerdown="start($event, panel.id, 'move')"><DockGrip /></span>
        <AppButton icon-only icon="help" label="Help" @click="emit('help','dock.' + panel.id)" />
        <AppButton v-if="!mobile" icon-only :icon="maximized === panel.id ? 'MDI_FIT_TO_SCREEN_OUTLINE' : 'MDI_FIT_TO_SCREEN'" :label="maximized === panel.id ? 'Restore panel' : 'Maximize panel'" @click="maximize(panel.id)" />
        <AppMenu v-if="!mobile" :label="t('Panel position: {name}', { name: t(panel.title) })" icon="MDI_DOCK_WINDOW">
          <label>{{ t('Place relative to') }}<AppSelect v-model="positionTarget" label="Place relative to" :options="visible.filter(item => item.id !== panel.id && !state.panels[item.id].floating).map(item => ({ value: item.id, label: item.title }))" /></label>
          <AppButton v-for="[side, title] in [['left','Dock left'],['right','Dock right'],['top','Dock top'],['bottom','Dock bottom'],['center','Stack panels'],['swap','Swap panels']]" :key="side" :label="title" :disabled="positionTarget === panel.id || !visible.some(item => item.id === positionTarget && !state.panels[item.id].floating)" @click="move(panel.id, side, positionTarget)" />
          <hr><AppButton :label="state.panels[panel.id].floating ? 'Dock panel' : 'Float panel'" icon="MDI_DOCK_WINDOW" @click="state.panels[panel.id].floating ? move(panel.id, 'right') : float(panel.id)" />
        </AppMenu>
        <AppButton v-if="panel.closable" icon-only icon="close" :label="t('Close panel: {name}', { name: t(panel.title) })" @click="hide(panel.id)" />
      </header>
      <div :id="panel.id === 'results' ? 'workspace-data' : 'dock-' + panel.id" class="dock-content"></div>
      <button v-if="state.panels[panel.id].floating && !compact && !maximized" class="dock-floating-resize" :aria-label="t('Resize panel: {name}', { name: t(panel.title) })" @pointerdown="start($event, panel.id, 'resize')" @keydown="floatSize($event, panel.id)"><AppIcon name="MDI_RESIZE_BOTTOM_RIGHT" /></button>
      <template v-if="state.panels[panel.id].floating && !compact && !maximized"><span v-for="edge in ['left','right','top','bottom','top-left','top-right','bottom-left','bottom-right']" :key="edge" class="dock-resize-edge" :class="[edge, { 'resize-grip': ['left','right','top','bottom'].includes(edge) }]" aria-hidden="true" @pointerdown.stop="start($event, panel.id, 'resize', null, edge)" /></template>
    </section>
    <div v-for="item in projection.dividers" :key="item.path" class="dock-divider resize-grip" :class="item.orientation" :style="dividerStyle(item)" role="separator" tabindex="0"
      :aria-label="t('Resize workspace panels')" :aria-orientation="item.orientation === 'horizontal' ? 'vertical' : 'horizontal'" :aria-valuenow="Math.round(item.ratio * 100)" :aria-valuemin="Math.round(item.minimum * 100)" :aria-valuemax="Math.round((1 - item.minimum) * 100)"
      @pointerdown="start($event, '', 'split', item)" @keydown="resizeKey($event, item)"></div>
    <div v-if="drop" class="dock-drop-guide" role="status">{{ t('Drop to dock') }}: {{ t(drop.side) }}</div>
    <AppMenu ref="contextMenu" class="dock-context-menu" label="Dock actions" overlay>
      <AppMenuItem label="Help for this dock" icon="help" @click="emit('help','dock.' + contextPanel)" />
      <hr><AppMenuItem :label="state.panels[contextPanel].floating ? 'Dock to workspace' : 'Float panel'" icon="MDI_DOCK_WINDOW" @click="state.panels[contextPanel].floating ? move(contextPanel, 'right') : float(contextPanel)" />
      <AppMenuItem :label="maximized === contextPanel ? 'Restore panel' : 'Maximize panel'" icon="MDI_FIT_TO_SCREEN" @click="maximize(contextPanel)" />
      <AppMenuItem v-if="contextPanel !== 'results'" label="Close dock" icon="close" @click="hide(contextPanel)" />
    </AppMenu>
    <Teleport defer :to="resultsActive && menuTarget ? menuTarget : '#workspace-data'">
    <AppMenu v-if="!mobile" v-show="presented('results')" class="dock-menu" :class="{ 'dock-menu-toolbar':resultsActive && menuTarget }" label="Workspace panels" :boundary="host" overlay :width="280">
      <AppMenu class="dock-group-menu" label="Browsing" icon="view-kanban" overlay submenu :boundary="host" :width="280">
        <template #trigger><AppIcon name="view-kanban" /><span>{{ t('Browsing') }}</span><AppIcon name="next" /></template>
        <AppMenuItem label="Results" icon="search" :checked="state.panels.results.visible" disabled />
        <AppMenuItem label="Description" icon="description" :checked="state.panels.description.visible" @click="toggle('description')" />
        <AppMenuItem label="Snapshot Browser" icon="snapshot" :checked="state.panels.snapshot.visible" @click="toggle('snapshot')" />
        <AppMenuItem label="Knowledge Base" icon="book-open" :checked="state.panels.knowledge.visible" @click="toggle('knowledge')" />
      </AppMenu>
      <AppMenu class="dock-group-menu" label="Tasks and reports" icon="task-alt" overlay submenu :boundary="host" :width="280">
        <template #trigger><AppIcon name="task-alt" /><span>{{ t('Tasks and reports') }}</span><AppIcon name="next" /></template>
        <AppMenuItem v-if="canAdminister" label="Task Manager" icon="MDI_CLIPBOARD_TEXT_OUTLINE" :checked="state.panels.tasks.visible" @click="toggle('tasks')" />
        <AppMenuItem label="Task Inspector" icon="comment" :checked="state.panels.notes.visible" @click="toggle('notes')" />
        <AppMenuItem v-if="canAdminister" label="Task Calendar" icon="MDI_CALENDAR_MONTH" :checked="state.panels.task_calendar.visible" @click="toggle('task_calendar')" />
      </AppMenu>
      <AppMenu class="dock-group-menu" label="Tools" icon="settings-suggest" overlay submenu :boundary="host" :width="280">
        <template #trigger><AppIcon name="settings-suggest" /><span>{{ t('Tools') }}</span><AppIcon name="next" /></template>
        <AppMenuItem label="Drop Plate" icon="upload" :checked="state.panels.drop_plate.visible" @click="toggle('drop_plate')" />
        <AppMenuItem label="Commit Queue" icon="queue" :checked="state.panels.commit_queue.visible" @click="toggle('commit_queue')" />
        <hr><AppMenuItem :label="state.panels.results.floating ? 'Dock results' : 'Float results'" icon="MDI_DOCK_WINDOW" @click="state.panels.results.floating ? move('results', 'left') : float('results')" />
        <AppMenuItem :label="maximized === 'results' ? 'Restore panel' : 'Maximize panel'" icon="MDI_FIT_TO_SCREEN" @click="maximize('results')" />
        <hr><slot name="view-actions" />
      </AppMenu>
      <hr><AppMenu ref="presetMenu" class="dock-presets-menu dock-group-menu" label="Layout presets" icon="dashboard-customize" :close-on-select="false" :boundary="host" overlay submenu :width="330">
        <template #trigger><AppIcon name="dashboard-customize" /><span>{{ t('Layout presets') }}</span><AppIcon name="next" /></template>
        <header class="dock-presets-heading"><strong>{{ t('Layout presets') }}</strong><AppButton icon-only label="Refresh layout presets" icon="refresh" :disabled="presetBusy" @click.stop="refreshLayouts" /></header>
        <p v-if="!presets.length" class="muted">{{ t(presetBusy ? 'Loading data…' : 'No saved layouts yet') }}</p>
        <div v-for="row in presets" :key="row.view" class="dock-preset-row">
          <AppButton :label="row.title" :translate-label="false" :aria-pressed="activePreset === row.view" :disabled="!row.valid || presetBusy" :title="row.error" @click="applyAssigned(row.view); presetMenu.open = false"><AppIcon :name="row.valid ? 'MDI_VIEW_DASHBOARD' : 'warning'" /><span><strong>{{ row.title }}</strong><small>{{ row.valid ? t('{panels} panels · {items} sidebar items', { panels: row.panelCount, items: row.assignedCount }) : t('Invalid layout preset') }}</small></span></AppButton>
          <AppButton v-if="canAdminister" icon-only label="Replace with current layout" icon="save" :disabled="presetBusy || uncertain" @click="savePreset(row)" />
          <AppButton v-if="canAdminister" icon-only label="Delete layout preset" icon="delete" destructive :disabled="presetBusy || uncertain || row.assignedCount > 0" :title="row.assignedCount ? t('Remove this preset from sidebar items first') : t('Delete layout preset')" @click="deletePreset(row)" />
        </div>
        <AppButton v-if="canAdminister" label="Save current layout…" icon="add" :disabled="presetBusy || !catalog || uncertain" @click="namePreset" />
        <p v-if="presetError" class="error" role="alert">{{ t(presetError) }}</p>
      </AppMenu>
      <AppButton label="Reset layout" icon="sync" @click="reset" />
    </AppMenu>
    </Teleport>
    <slot v-if="mobile" name="view-actions" />
  </div>
  <Teleport to="body">
    <dialog ref="nameDialog" class="record-dialog" :aria-label="t('Save workspace layout')" @cancel.prevent="!presetBusy && nameDialog.close()">
      <form @submit.prevent="savePreset()"><h2>{{ t('Save workspace layout') }}</h2><label>{{ t('Layout preset name') }}<input v-model="presetTitle" :aria-label="t('Layout preset name')" required maxlength="256" :disabled="presetBusy"></label>
        <p v-if="presetError" class="error" role="alert">{{ t(presetError) }}</p><div class="configuration-actions"><AppButton type="submit" label="Save" icon="save" highlighted :disabled="presetBusy || uncertain || !presetTitle.trim()" /><AppButton label="Cancel" :disabled="presetBusy" @click="nameDialog.close()" /></div></form>
    </dialog>
    <dialog ref="deleteDialog" class="record-dialog" :aria-label="t('Delete layout preset?')" @cancel.prevent="!presetBusy && deleteDialog.close()">
      <h2>{{ t('Delete layout preset?') }}</h2><p>{{ t('The server layout preset “{name}” will be deleted.', { name: deleting?.title || '' }) }}</p><p v-if="presetError" class="error" role="alert">{{ t(presetError) }}</p>
      <div class="configuration-actions"><AppButton label="Delete" icon="delete" destructive :disabled="presetBusy || uncertain" @click="mutatePreset('delete', { code: deleting.code })" /><AppButton label="Cancel" :disabled="presetBusy" @click="deleteDialog.close()" /></div>
    </dialog>
  </Teleport>
</template>
