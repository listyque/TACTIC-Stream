<script setup>
import { computed, ref } from 'vue'
import MobilePage from '../../controls/MobilePage.vue'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import ResultItem from './ResultItem.vue'
import ConfiguredResultItem from '../interface/ConfiguredResultItem.vue'
import FilePreviewContent from '../objects/FilePreviewContent.vue'
import { prettySize } from '../checkin/files.js'
import { timestampFullLabel } from '../activity/activity.js'

const props = defineProps({ itemLayout: Object, readOnly: Boolean, groups: Array, parent: Object, path: Array, direction: String, scroll: Object,
  busy: Boolean, error: String, active: Boolean, closedGroups: Object, selectedKeys: Array })
const emit = defineEmits(['enter', 'back', 'scrolled', 'refresh', 'retry', 'more', 'preview', 'preview-retry', 'upload', 'inspect', 'operate', 'notes', 'tasks', 'select', 'group', 'create', 'link', 'completion', 'root-scroll'])
const key = computed(() => props.parent?.id || 'root')
const title = computed(() => props.parent?.snapshot_display?.title || props.parent?.title || props.parent?.record?.name || props.parent?.record?.code || t('All items'))
const groups = computed(() => props.parent ? [{ key: '', label: '', nodes: props.parent.children || [] }] : props.groups)
const snapshot = computed(() => ['snapshot', 'file'].includes(props.parent?.kind))
const busy = computed(() => props.busy || props.parent?.busy)
const error = computed(() => props.error || props.parent?.error)
const snapshotFooter = ref(null)
</script>

<template>
  <MobilePage :aria-label="t('Mobile item browser')" :screen-key="key" :title="title" :back="!!parent" :direction="direction" :scroll="scroll" :busy="busy" :active="active"
    @enter="id => emit('enter', groups.flatMap(group => group.nodes).find(node => node.id === id))" @back="emit('back')" @scrolled="(id, top) => emit('scrolled', id, top)" @root-scroll="emit('root-scroll', $event)">
    <template #header>
      <component :is="itemLayout ? ConfiguredResultItem : ResultItem" :layout="itemLayout" :read-only="readOnly" :node="parent" back :navigable="false" @back="emit('back')" @inspect="emit('inspect', parent)"
        @tasks="(node, event) => emit('tasks', node, event)" @notes="(node, event) => emit('notes', node, event)" @upload="emit('upload', parent)" @preview="emit('preview', parent)"
        @operate="(node, event) => emit('operate', node, event)" @completion="(owner, item) => emit('completion', owner, item)"
        @create="emit('create', parent)" @link="emit('link', parent)" />
    </template>
    <template v-if="snapshot">
        <div class="mobile-snapshot-view file-preview">
          <p v-if="parent.previewBusy" role="status">{{ t('Loading file…') }}</p>
          <p v-if="parent.previewError" role="alert" class="error">{{ t(parent.previewError) }} <AppButton label="Retry" @click="emit('preview-retry', parent)" /></p>
          <FilePreviewContent v-if="parent.previewCell" :cell="parent.previewCell" :record="parent.record" :description="parent.record.description || t('No description')" :actions-target="snapshotFooter" embedded />
        </div>
        <AppButton v-if="parent.children?.length" class="mobile-snapshot-versions" label="View versions" icon="MDI_CHEVRON_RIGHT" @click="emit('enter', parent.children[0])"><span>{{ t('View versions') }} · {{ parent.children[0].children.length }}<template v-if="parent.children[0].hasNext">+</template></span></AppButton>
        <dl class="mobile-snapshot-metadata">
          <dt>{{ t('Process') }}</dt><dd>{{ parent.record.context }}</dd>
          <dt>{{ t('Version') }}</dt><dd>{{ parent.snapshot_display?.version || parent.record.version }}</dd>
          <template v-if="parent.snapshot_display?.author"><dt>{{ t('Author') }}</dt><dd>{{ parent.snapshot_display.author }}</dd></template>
          <template v-if="parent.snapshot_display?.size != null"><dt>{{ t('Size') }}</dt><dd>{{ prettySize(parent.snapshot_display.size) }}</dd></template>
          <template v-if="parent.record.timestamp"><dt>{{ t('Date') }}</dt><dd>{{ timestampFullLabel(parent.record.timestamp) }}</dd></template>
        </dl>
    </template>
    <p v-if="busy" class="table-message" role="status">{{ t('Loading data…') }}</p>
    <p v-if="error" class="error table-message" role="alert">{{ t(error) }} <AppButton label="Retry" icon="refresh" @click="emit(parent ? 'retry' : 'refresh')" /></p>
    <section v-for="group in snapshot ? [] : groups" :key="group.key">
      <AppButton v-if="group.label" class="result-group-heading" :aria-expanded="!closedGroups[group.key]" @click="emit('group', group.key)">{{ group.key ? group.label : t(group.label) }} <small>{{ group.nodes.length }}</small></AppButton>
      <div v-show="parent || !closedGroups[group.key]" class="mobile-result-list">
        <component :is="itemLayout ? ConfiguredResultItem : ResultItem" :layout="itemLayout" :read-only="readOnly" v-for="node in group.nodes" :key="node.id" :node="node" :data-mobile-item="node.id" @activate="emit('enter', node)" @inspect="emit('inspect', node)"
          :selectable="!readOnly && !parent && node.kind === 'object'" :checked="selectedKeys?.includes(node.record?.__search_key__)" @select="(owner, selected) => emit('select', owner, selected)"
          @create="emit('create', node)" @link="emit('link', node)" @completion="(owner, item) => emit('completion', owner, item)"
          @upload="emit('upload', node)"
          @operate="(node, event) => emit('operate', node, event)" @preview="emit('preview', node)" @notes="(node, event) => emit('notes', node, event)" @tasks="(node, event) => emit('tasks', node, event)" />
      </div>
    </section>
    <p v-if="!busy && !error && !snapshot && !groups.some(group => group.nodes.length)" class="table-message">{{ t(parent?.branch?.kind === 'versions' ? 'No versions' : 'No records yet') }}</p>
    <AppButton v-if="parent?.hasNext" label="Load more" icon="next" :disabled="busy" @click="emit('more')" />
    <template v-if="snapshot" #footer><div ref="snapshotFooter" class="mobile-snapshot-footer"></div></template>
  </MobilePage>
</template>

<style>
@media(max-width:700px) {
  .configured-view:has(.mobile-results), .result-presentation:has(> .mobile-results) { height:100%; min-height:0; }
  .workspace-results:has(.mobile-results) { overflow:clip; margin:0; }
  .workspace-browser:has(.configured-view[data-workspace-current="true"] .mobile-result-header) > :is(.search-header,.workspace-tabs,.workspace-footer,.selection-actions,#workspace-script-shelf) { display:none; }
  .workspace-browser:has(.configured-view[data-workspace-current="true"] .mobile-results[data-chrome-hidden="true"]) > :is(.search-header,.workspace-tabs,#workspace-script-shelf) { display:none; }
}
.mobile-snapshot-view { padding:8px 12px; }
.mobile-snapshot-view .file-preview-content { max-height:none; min-height:100px; overflow:visible; }
.mobile-snapshot-footer { flex:none; min-height:44px; background:var(--surface-high); }
.mobile-snapshot-view .file-preview-content .image-picker-preview { max-height:48dvh; height:auto; min-height:100px; }
.mobile-snapshot-view .file-preview-text { min-height:100px; padding:8px; background:var(--surface); border-radius:var(--item-radius); }
.mobile-snapshot-view .file-preview-download { margin-block:8px; }
.mobile-snapshot-versions { margin:8px 12px; }
.mobile-snapshot-metadata { display:grid; grid-template-columns:auto 1fr; gap:6px 16px; padding:4px 12px; font-size:var(--text-caption); }
.mobile-snapshot-metadata dt { color:var(--muted); }
.mobile-snapshot-metadata dd { margin:0; overflow-wrap:anywhere; }
.mobile-result-screen .result-item { --result-depth:0 !important; padding:10px 70px 10px 66px; min-height:72px; height:auto; }
.mobile-result-list { display:grid; gap:6px; padding:6px 4px; }
.mobile-result-screen .result-item > .result-surface { border:0; border-radius:var(--surface-radius); box-shadow:none; }
.mobile-result-screen .result-item-object > .result-surface { border:1px solid var(--outline-variant); box-shadow:0 2px 3px var(--shadow-color); }
.mobile-result-screen .result-item-object > .result-surface::before { inset:-1px; width:auto; border:0; border-left:2px solid var(--result-accent); border-radius:inherit; background:transparent; box-sizing:border-box; }
.mobile-result-screen .result-item-snapshot > .result-surface { background:var(--surface-high); border-radius:var(--item-radius); }
.mobile-result-screen .result-item-branch { min-height:52px; padding-left:44px; }
.mobile-result-screen .result-preview { left:12px; }
.mobile-result-screen .result-preview .image-picker-preview { width:42px; height:42px; flex-basis:42px; font-size:12px; }
.mobile-result-screen .result-branch-icon { left:18px; }
.mobile-result-screen .result-item-actions { right:30px; }
.mobile-result-screen .result-item-actions .workspace-menu > summary { width:36px; height:36px; }
.result-mobile-next { position:absolute; right:10px; top:50%; transform:translateY(-50%); width:16px; height:16px; color:var(--muted); pointer-events:none; }
.mobile-result-screen .result-description { overflow:hidden; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; white-space:normal; }
.mobile-result-screen .result-metadata { max-height:36px; overflow:hidden; }
.mobile-results .result-item { --mobile-leading:42px; display:grid; grid-template-columns:var(--mobile-leading) minmax(0,1fr) auto; gap:4px 6px; padding:8px 24px 8px 8px; min-height:64px; height:auto; align-content:start; }
.mobile-results .result-item-branch { --mobile-leading:14px; min-height:52px; padding-block:8px; align-content:center; }
.mobile-results .result-item-branch > .result-mobile-next { top:50%; }
.mobile-results .result-item > .result-surface { inset:0; }
.mobile-results .result-preview { position:static; grid-column:1; grid-row:1; justify-self:end; align-self:start; }
.mobile-results .result-preview .image-picker-preview { width:42px; height:42px; flex-basis:42px; }
.mobile-results .result-branch-icon { position:static; grid-column:1; grid-row:1; align-self:center; justify-self:end; }
.mobile-results .result-item-copy { grid-column:2; grid-row:1; grid-template-columns:minmax(0,1fr); min-height:42px; align-content:center; }
.mobile-results .result-item-branch .result-item-copy { min-height:32px; }
.mobile-results .result-title-line { height:auto; width:100%; overflow:hidden; }
.mobile-results .result-title-line > :is(strong,h2) { min-width:0; max-width:100%; white-space:normal; overflow-wrap:anywhere; }
.mobile-results .result-item-actions { position:static; grid-column:3; grid-row:1; height:auto; display:flex; gap:4px; justify-self:end; align-self:center; }
.mobile-results .result-item-actions .workspace-menu > summary { width:32px; height:32px; }
.mobile-results .result-mobile-next { top:29px; right:6px; }
.mobile-results .result-mobile-actions { display:flex; gap:4px; }
.mobile-results .result-mobile-actions > .icon-button { width:28px; height:28px; min-width:28px; min-height:28px; flex:none; padding:0; font-size:16px; }
.mobile-results .result-item-object { grid-template-columns:var(--mobile-leading) minmax(0,1fr) 28px; }
.mobile-results .result-item-object > .result-item-actions { display:contents; }
.mobile-results .result-item-object .result-mobile-actions { grid-column:2/-1; grid-row:2; justify-self:end; }
.mobile-results .result-item-object .result-item-actions > .workspace-menu { grid-column:3; grid-row:1; align-self:start; }
.mobile-results .result-item-object .result-item-actions .workspace-menu > summary { width:28px; height:28px; }
.mobile-results .result-item-object:not(.result-mobile-header) { grid-template-columns:42px minmax(0,1fr) 28px 16px; gap:8px; padding:12px; }
.mobile-results .result-item-object:not(.result-mobile-header) .result-mobile-actions { grid-column:2; justify-self:start; }
.mobile-results .result-item-object:not(.result-mobile-header) .result-item-actions > .workspace-menu { grid-row:1 / 3; align-self:center; }
.mobile-results .result-item-object:not(.result-mobile-header) > .result-mobile-next { position:static; grid-column:4; grid-row:1 / 3; align-self:center; transform:none; }
.mobile-results .result-metadata:empty { display:none; }
.mobile-results .result-mobile-header { --mobile-leading:74px; padding-inline:4px; }
.mobile-results .result-mobile-header.result-item-branch { --mobile-leading:54px; }
.mobile-results .result-mobile-back { position:absolute; left:4px; top:15px; width:28px; height:28px; min-width:28px; }
.mobile-result-header .result-surface { border:0; border-radius:0; background:var(--surface-high); box-shadow:none; }
.mobile-result-header .result-surface::before { display:none; }
.mobile-result-header .result-preview .image-picker-preview { font-size:12px; }
.mobile-result-header .result-description { display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; white-space:normal; font-size:var(--text-caption); }
.mobile-results .result-item-object > .result-preview { --mobile-preview-center:calc(12px + 42px / 2 - 3px); position:absolute; inset:0 auto auto 3px; width:min(55%,180px); height:100%; grid-area:auto; justify-self:start; align-self:stretch; z-index:-1; pointer-events:none; overflow:hidden; border-radius:var(--surface-radius) 0 0 var(--surface-radius); }
.mobile-results .result-item-object > .result-preview .image-picker-preview { position:relative; width:100%; height:100%; flex-basis:auto; border-radius:0; background:transparent; }
.mobile-results .result-item-object .image-picker-preview img { position:absolute; left:var(--mobile-preview-center); top:0; transform:translateX(-50%); }
.mobile-results .result-item-object .image-picker-preview:has(img) { mask-image:linear-gradient(to right,black 0%,rgb(0 0 0 / .6) var(--mobile-preview-center),transparent calc(50% + var(--mobile-preview-center))); }
.mobile-results .result-item-object .image-picker-preview:has(img)::after { content:''; position:absolute; inset:0; backdrop-filter:blur(8px); mask-image:linear-gradient(to right,transparent,black 75%); }
.mobile-results .result-item-object > .result-preview .image-picker-preview:not(:has(img)) { background:linear-gradient(to right,color-mix(in srgb,var(--preview-accent,var(--primary)),var(--surface) 65%),transparent 90%); }
.mobile-results .result-item-object .image-picker-preview > span:not(.app-icon) { position:absolute; left:calc(var(--mobile-preview-center) - 42px / 2); top:50%; transform:translateY(-50%); width:42px; text-align:center; color:var(--on-surface); font-size:var(--text-body-large); font-weight:600; letter-spacing:.06em; }
.mobile-result-header .result-item-object > .result-preview { --mobile-preview-center:calc(4px + var(--mobile-leading) - 42px / 2); inset:0 auto auto 0; height:100%; border-radius:0; }
@media(max-width:700px) {
  .workspace-browser > .search-header.mobile-search-header { overflow:hidden; opacity:1; transition:height var(--motion-popup-fast),opacity var(--motion-popup-fast),padding var(--motion-popup-fast); }
  .workspace-browser > .search-header.mobile-search-collapsed { height:0; min-height:0; padding-block:0; opacity:0; }
  .workspace-tabs.mobile-tabs { height:40px; min-height:40px; padding:4px 8px; gap:4px; }
  .workspace-tabs.mobile-tabs > .workspace-tab-menu { flex:1; min-width:0; }
  .workspace-tabs.mobile-tabs > .workspace-tab-menu > summary { width:100%; height:32px; padding:0 4px; border-radius:var(--item-radius); justify-content:flex-start; gap:6px; }
  .mobile-tab-title { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; text-align:left; font-size:var(--text-body-large); }
  .mobile-tab-count { flex:none; color:var(--muted); font-size:var(--text-caption); }
  .workspace-tabs.mobile-tabs > .icon-button,.workspace-tabs.mobile-tabs > .compact-result-actions > summary { width:32px; height:32px; min-width:32px; min-height:32px; }
  .workspace-tabs.mobile-tabs > .icon-button { padding:0; border-radius:50%; }
  .mobile-tabs #workspace-mobile-view-actions .inline-menu > .account-panel { display:grid; }
}
</style>
