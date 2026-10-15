<script setup>
import { randomId } from '../../controls/identity.js'
// Handler KnowledgeArticleEditor / KnowledgeRichTextToolbar (EPL-1.0).
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import AppMenu from '../../controls/AppMenu.vue'
import AppMenuItem from '../../controls/AppMenuItem.vue'
import AppTextField from '../../controls/AppTextField.vue'
import AppTextArea from '../../controls/AppTextArea.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppSlider from '../../controls/AppSlider.vue'
import AppSegmentedButton from '../../controls/AppSegmentedButton.vue'
import { escapeHtml } from '../../controls/richText.js'
import { articleHtml, htmlMarkdown, safeUrl, sanitize } from './markdown.js'

const props=defineProps({ modelValue:String, project:String, disabled:Boolean, attachments:Array })
const emit=defineEmits(['update:modelValue','attachments','upload'])
const host=ref(null), body=ref(null), source=ref(null), mode=ref('visual'), width=ref(0), insertion=ref(null)
const panel=ref(''), label=ref(''), address=ref(''), content=ref(''), language=ref('python'), failure=ref('')
const image=ref(null), imageWidth=ref(320), imageNatural=ref(''), formats=reactive({})
const scroll=ref(null), hoveredLink=ref(null), linkPosition=ref({}), imagePosition=ref({})
let range=null, editingAnchor=null, emitted='', observer, resizeStart=null
const actions=[['bold','bold','Bold · Ctrl+B',0],['italic','italic','Italic · Ctrl+I',640],['underline','underline','Underline',650],['strikeThrough','strikethrough','Strikethrough',690],['small','small-text','Small text',730],['link','link','Insert link · Ctrl+K',0],['attachments','attachments-editor','Show attached files',640],['quote','format-quote','Insert quote',770],['code','code-block','Insert code block',810],['checklist','checkbox-multiple-marked-outline','Checklist',850]]
const hidden=computed(()=>actions.filter(action=>width.value<action[3]))
function previews(){for(const node of body.value?.querySelectorAll('img')||[]){const file=props.attachments?.find(file=>file.webUrl===(node.dataset.original||node.getAttribute('src')));if(file&&file.previewUrl!==file.webUrl){node.dataset.original=file.webUrl;node.dataset.preview=file.previewUrl}}}
function load() { if (body.value) body.value.innerHTML=articleHtml(props.modelValue,props.project);previews();image.value=null }
watch(()=>props.attachments,previews)
function imageError(event){const node=event.target;if(node.tagName==='IMG'&&node.dataset.preview&&node.src!==new URL(node.dataset.preview,location.href).href)node.src=node.dataset.preview}
watch(()=>props.modelValue,value=>{ if (value!==emitted && mode.value==='visual') load() })
watch(mode,()=>nextTick(load))
function sync() { if(mode.value!=='visual')return;const value=htmlMarkdown(body.value); emitted=value; emit('update:modelValue',value) }
function remember() {
  const selection=window.getSelection()
  if (selection?.rangeCount && body.value?.contains(selection.anchorNode) && body.value.contains(selection.focusNode)) range=selection.getRangeAt(0).cloneRange()
  for (const name of ['bold','italic','underline','strikeThrough']) formats[name]=!!body.value?.contains(selection?.anchorNode) && document.queryCommandState(name)
}
function restore() {
  body.value.focus(); const selection=window.getSelection(); selection.removeAllRanges()
  if (range && body.value.contains(range.commonAncestorContainer)) selection.addRange(range)
  else { const last=document.createRange(); last.selectNodeContents(body.value); last.collapse(false); selection.addRange(last) }
}
function insert(html) { restore(); document.execCommand('insertHTML',false,html);previews();sync(); remember() }
function wrapSource(before,after='') {
  const field=source.value, start=field.selectionStart, end=field.selectionEnd
  const value=props.modelValue.slice(0,start)+before+props.modelValue.slice(start,end)+after+props.modelValue.slice(end)
  emitted=value; emit('update:modelValue',value); nextTick(()=>{ field.focus(); field.setSelectionRange(start+before.length,end+before.length) })
}
function action(name,value='') {
  if (props.disabled) return
  if (name==='attachments') { mode.value='visual'; emit('attachments'); return }
  if (['link','image','quote','pull-quote','code','table'].includes(name)) { open(name); return }
  if (mode.value==='markdown') {
    const syntax={bold:['**','**'],italic:['*','*'],underline:['<u>','</u>'],strikeThrough:['~~','~~'],small:['<small>','</small>'],insertUnorderedList:['- '],insertOrderedList:['1. '],checklist:['- [ ] '],divider:['\n\n---\n\n'],formatBlock:[value==='p'?'': '#'.repeat(Number(value.slice(1)))+' ']}
    if (syntax[name]) wrapSource(...syntax[name]); else if (name==='undo'||name==='redo') { source.value.focus(); document.execCommand(name) }
    return
  }
  restore()
  if (name==='divider') document.execCommand('insertHTML',false,'<hr><p><br></p>')
  else if (name==='checklist') document.execCommand('insertHTML',false,'<ul><li><input type="checkbox" disabled> </li></ul>')
  else if (name==='small') document.execCommand('insertHTML',false,`<small>${escapeHtml(window.getSelection().toString()||' ')}</small>`)
  else document.execCommand(name,false,value)
  sync(); remember()
}
function open(kind,anchor=null) {
  remember(); panel.value=kind; editingAnchor=anchor; failure.value=''
  label.value=anchor?.textContent||window.getSelection()?.toString()||''
  address.value=anchor?.dataset.link||anchor?.getAttribute('href')||''
  content.value=label.value; insertion.value.showModal()
}
function applyInsertion() {
  if (['link','image'].includes(panel.value) && (!safeUrl(address.value) || panel.value==='image'&&!/^(https?:\/\/|\/assets\/)/i.test(address.value))) { failure.value=t('Enter a valid web or skey link.'); return }
  let html, markdown
  const text=escapeHtml(label.value), url=escapeHtml(address.value)
  if (panel.value==='link') { html=`<a href="${url}" data-link="${url}">${text||url}</a>`; markdown=`[${label.value||address.value}](${address.value})` }
  else if (panel.value==='image') { html=`<img src="${url}" alt="${text}" width="560">`; markdown=`![${label.value}](${address.value}){width=560}` }
  else if (panel.value==='code') { html=`<pre data-language="${escapeHtml(language.value)}"><code>${escapeHtml(content.value)}</code></pre><p><br></p>`; markdown='\n\n```'+language.value+'\n'+content.value+'\n```\n\n' }
  else if (panel.value==='table') { html='<table><thead><tr><th> </th><th> </th></tr></thead><tbody><tr><td> </td><td> </td></tr></tbody></table><p><br></p>'; markdown='\n\n| | |\n| --- | --- |\n| | |\n\n' }
  else { const align=panel.value==='pull-quote'?' align="center"':''; html=`<blockquote><p${align}>${escapeHtml(content.value).replace(/\n/g,'<br>')}</p></blockquote><p><br></p>`; markdown='\n\n'+content.value.split('\n').map(line=>'> '+line).join('\n')+(align?' {align=center}':'')+'\n\n' }
  insertion.value.close()
  if (mode.value==='markdown') wrapSource(markdown)
  else {
    if (editingAnchor?.isConnected) { range=document.createRange(); range.selectNode(editingAnchor) }
    insert(html)
  }
}
function insertAttachment(file) {
  const url=file.webUrl, title=file.title.replace(/[\[\]]/g,'')
  if (mode.value==='markdown') wrapSource((file.isImage?'!':'')+`[${title}](${url})`+(file.isImage?'{width=560}':''))
  else insert(file.isImage ? `<img src="${escapeHtml(url)}" alt="${escapeHtml(file.title)}" width="560">` : `<a href="${escapeHtml(url)}" data-link="${escapeHtml(url)}">${escapeHtml(file.title)}</a>`)
}
function paste(event) {
  event.preventDefault()
  const files=[...event.clipboardData.files]
  if (files.length) { emit('upload',files); return }
  const html=event.clipboardData.getData('text/html'), text=event.clipboardData.getData('text/plain')
  insert(html ? sanitize(html,props.project).innerHTML : escapeHtml(text).replace(/\n/g,'<br>'))
}
function selectImage(event) {
  const target=event.target.closest('img')
  image.value=target||null
  if (target) { imageWidth.value=Math.round(target.width); imageNatural.value=`${target.naturalWidth} × ${target.naturalHeight}`; range=document.createRange(); range.selectNode(target);positionImage() }
  else if (event.target.closest('a')) event.preventDefault()
}
function hoverLink(event){const anchor=event.target.closest('a');if(anchor===hoveredLink.value)return;hoveredLink.value=anchor;if(anchor){const box=anchor.getBoundingClientRect(),host=scroll.value.getBoundingClientRect();linkPosition.value={left:Math.max(0,Math.min(host.width-30,box.right-host.left))+'px',top:Math.max(0,box.top-host.top+scroll.value.scrollTop-24)+'px'}}}
function positionImage(){if(!image.value?.isConnected)return;const box=image.value.getBoundingClientRect(),host=scroll.value.getBoundingClientRect();imagePosition.value={left:Math.max(0,box.right-host.left-20)+'px',top:box.bottom-host.top+scroll.value.scrollTop-20+'px'}}
function setWidth(value,fit=false) {
  const selected=image.value
  if (!selected?.isConnected) return
  const width=Math.max(24,Math.round(value)), height=Math.round(width*(selected.naturalHeight||selected.height)/(selected.naturalWidth||selected.width))
  const marker=randomId()
  const html=`<img data-editor-image="${marker}" src="${escapeHtml(selected.getAttribute('src'))}"${selected.dataset.original?' data-original="'+escapeHtml(selected.dataset.original)+'"':''} alt="${escapeHtml(selected.alt)}" width="${width}" height="${height}"${fit?' data-fit="content"':''}>`
  range=document.createRange(); range.selectNode(selected); insert(html)
  image.value=body.value.querySelector('img[data-editor-image="'+marker+'"]');if(image.value)delete image.value.dataset.editorImage;imageWidth.value=width
  positionImage()
}
function resizeDown(event) { event.preventDefault(); event.currentTarget.setPointerCapture(event.pointerId); resizeStart={ x:event.clientX,width:image.value.width }; }
function resizeMove(event) { if (resizeStart) { imageWidth.value=Math.max(24,Math.round(resizeStart.width+event.clientX-resizeStart.x)); image.value.style.width=imageWidth.value+'px'; image.value.style.height='auto';positionImage() } }
function resizeEnd(event) { if (!resizeStart) return; const value=event.type==='pointercancel'?resizeStart.width:imageWidth.value; image.value.style.width=''; image.value.style.height=''; resizeStart=null; setWidth(value) }
function drop(event) {
  if (event.dataTransfer.files.length) { event.preventDefault(); emit('upload',[...event.dataTransfer.files]); return }
  if (image.value && event.dataTransfer.types.includes('text/html')) {
    // The browser moves a native editor image as one undo operation.
    image.value=null;return
  }
  if(event.dataTransfer.getData('text/html')){event.preventDefault();insert(sanitize(event.dataTransfer.getData('text/html'),props.project).innerHTML)}
}
function keys(event) {
  if (!(event.ctrlKey||event.metaKey)) return
  const name={b:'bold',i:'italic',u:'underline',k:'link'}[event.key.toLowerCase()]
  if (name) { event.preventDefault(); action(name) }
}
onMounted(()=>{ load(); observer=new ResizeObserver(entries=>{width.value=entries[0].contentRect.width}); observer.observe(host.value); document.addEventListener('selectionchange',remember) })
onBeforeUnmount(()=>{ observer?.disconnect(); document.removeEventListener('selectionchange',remember) })
defineExpose({ insertAttachment, focus(){ (mode.value==='visual'?body.value:source.value)?.focus() }, synchronize:sync })
</script>
<template>
  <div ref="host" class="knowledge-editor" @keydown="keys">
    <div class="knowledge-formatting" :class="{minimal:width<640}">
      <AppButton icon-only icon="undo" label="Undo" :disabled="disabled" @mousedown.prevent @click="action('undo')" /><AppButton icon-only icon="redo" label="Redo" :disabled="disabled" @mousedown.prevent @click="action('redo')" />
      <span class="knowledge-format-divider" />
      <AppMenu label="Text style" icon="format-size" overlay :width="190"><template #trigger><span>{{ 'Aa' }}</span></template><AppMenuItem label="Normal text" @click="action('formatBlock','p')" /><AppMenuItem v-for="level in 6" :key="level" :label="t('Heading {level}',{level})" @click="action('formatBlock','h'+level)" /></AppMenu>
      <template v-for="item in actions" :key="item[0]"><AppButton v-if="width>=item[3]" :icon="item[1]" :label="item[2]" icon-only :tonal="formats[item[0]]" :disabled="disabled" @mousedown.prevent @click="action(item[0])" /></template>
      <span class="knowledge-format-divider" />
      <AppMenu label="Lists" icon="list-ul" overlay :width="210"><AppMenuItem label="Bulleted list" icon="list-ul" @click="action('insertUnorderedList')" /><AppMenuItem label="Numbered list" icon="list-ol" @click="action('insertOrderedList')" /><AppMenuItem label="Checklist" icon="checkbox-multiple-marked-outline" @click="action('checklist')" /></AppMenu>
      <AppMenu label="More formatting" overlay :width="240"><AppMenuItem v-for="item in hidden" :key="item[0]" :label="item[2]" :icon="item[1]" @click="action(item[0])" /><AppMenuItem label="Insert image URL" icon="image" @click="action('image')" /><AppMenuItem label="Insert pull quote" icon="format-quote" @click="action('pull-quote')" /><AppMenuItem label="Insert divider" icon="minus" @click="action('divider')" /><AppMenuItem label="Insert table" icon="table" @click="action('table')" /><AppMenuItem v-for="align in ['left','center','right','justify']" :key="align" :label="'Align '+align" :icon="'align-'+align" @click="action('justify'+align[0].toUpperCase()+align.slice(1))" /></AppMenu>
      <AppSegmentedButton v-model="mode" class="knowledge-editor-mode" :icon-only="width<640" :options="[{value:'visual',label:'Visual',icon:'edit'},{value:'markdown',label:'Markdown',icon:'code'}]" :label="t('Editor mode')" />
    </div>
    <slot v-if="mode==='visual'" name="attachments" />
    <div v-show="mode==='visual'" ref="scroll" class="knowledge-visual-scroll" @pointerleave="hoveredLink=null" @scroll="hoveredLink=null;positionImage()">
      <div ref="body" class="knowledge-document knowledge-visual" :contenteditable="!disabled" role="textbox" aria-multiline="true" :aria-label="t('Article content')" spellcheck="true" @error.capture="imageError" @input="sync" @paste="paste" @click="selectImage" @pointerover="hoverLink" @dragover.prevent @drop="drop" />
      <AppButton v-if="hoveredLink" icon-only icon="edit" label="Edit link" class="knowledge-link-edit" :style="linkPosition" @mousedown.prevent @click="open('link',hoveredLink)" /><AppButton v-if="image" icon-only icon="MDI_RESIZE_BOTTOM_RIGHT" label="Resize image" class="knowledge-image-handle" :style="imagePosition" @pointerdown="resizeDown" @pointermove="resizeMove" @pointerup="resizeEnd" @pointercancel="resizeEnd" />
      <div v-if="image" class="knowledge-image-settings"><small>{{ t('Image size') }}: {{ imageWidth }} px · {{ t('Original') }}: {{ imageNatural }}</small><AppSlider :model-value="imageWidth" :min="24" :max="Math.max(560,body?.clientWidth||560)" :step="1" label="Fixed image width" @update:model-value="setWidth" /><AppButton label="Stretch to content width" @click="setWidth(body.clientWidth,true)" /></div>
    </div>
    <textarea v-show="mode==='markdown'" ref="source" class="knowledge-source app-text-area" :value="modelValue" :aria-label="t('Markdown source')" :disabled="disabled" @input="emitted=$event.target.value;emit('update:modelValue',emitted)" @paste="event=>{if(event.clipboardData.files.length){event.preventDefault();emit('upload',[...event.clipboardData.files])}}" />
    <dialog ref="insertion" class="record-dialog knowledge-insertion" :aria-label="t('Insert content')"><header><h2>{{ t(panel==='link'?'Insert link':panel==='image'?'Insert image URL':panel==='code'?'Insert code block':panel==='table'?'Insert table':'Insert quote') }}</h2><AppButton icon-only icon="close" label="Close" @click="insertion.close()" /></header><p v-if="failure" class="error">{{ failure }}</p>
      <template v-if="panel==='link'||panel==='image'"><label>{{ t('Label') }}<AppTextField v-model="label" label="Label" /></label><label>{{ t('Address') }}<AppTextField v-model="address" label="Address" /></label></template>
      <template v-else-if="panel!=='table'"><label v-if="panel==='code'">{{ t('Language') }}<AppSelect v-model="language" :options="['python','javascript','xml','text'].map(value=>({value,label:value}))" label="Language" /></label><AppTextArea v-model="content" label="Content" /></template>
      <footer><AppButton label="Cancel" @click="insertion.close()" /><AppButton label="Insert" icon="plus" highlighted @click="applyInsertion" /></footer>
    </dialog>
  </div>
</template>
<style>
.knowledge-editor { display:flex; flex-direction:column; min-width:0; min-height:0; flex:1; gap:8px; container-type:inline-size; }.knowledge-formatting { display:flex; align-items:center; gap:3px; padding:6px; border:1px solid var(--outline-variant); border-radius:var(--item-radius); background:var(--surface); flex:none; }.knowledge-formatting .icon-button,.knowledge-formatting > details > summary { width:30px; height:30px; min-width:30px; min-height:30px; }.knowledge-formatting .app-icon { width:16px; height:16px; font-size:16px; }.knowledge-format-divider { width:1px; height:22px; background:var(--outline-variant); margin-inline:3px; flex:none; }.knowledge-editor-mode { margin-left:auto; }.knowledge-formatting.minimal .knowledge-editor-mode .segment-label { display:none; }.knowledge-visual-scroll { position:relative; flex:1; overflow:auto; min-height:0; }.knowledge-visual { min-height:100%; outline:none; padding:0; }.knowledge-source { min-height:0; flex:1; width:100%; resize:none; background:var(--page); border:1px solid var(--outline-variant); font-family:var(--font-mono); white-space:pre-wrap; }.knowledge-image-settings { position:sticky; bottom:0; display:flex; align-items:center; gap:6px; padding:8px; flex-wrap:wrap; background:var(--surface-high); border:1px solid var(--outline-variant); border-radius:var(--item-radius); }.knowledge-image-settings .app-slider { flex:1; min-width:100px; }.knowledge-insertion { width:min(520px,calc(100vw - 24px)); }.knowledge-insertion > label { display:flex; flex-direction:column; gap:7px; margin:12px 0; }.knowledge-insertion textarea { width:100%; min-height:140px; }
.knowledge-editor-mode .app-button { height:28px; min-height:28px; font-size:var(--text-body); font-weight:400; }.knowledge-editor-mode .app-button span { font-size:var(--text-body); }.knowledge-formatting { border:0; }.knowledge-formatting .app-button.icon-button,.knowledge-formatting > details > summary { border:0; border-radius:var(--item-radius); }
.knowledge-link-edit,.knowledge-image-handle { position:absolute; width:24px; height:24px; min-width:24px; min-height:24px; background:var(--surface-high); z-index:2; }.knowledge-image-handle { cursor:nwse-resize; border-radius:4px; }.knowledge-visual img { user-select:all; }.knowledge-visual img[data-fit="content"] { width:100%; height:auto; }
</style>
