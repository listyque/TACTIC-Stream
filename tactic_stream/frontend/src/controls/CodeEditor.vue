<script setup>
// Handler ScriptCodeEditor.qml (EPL-1.0): shared code buffer, commands and source toolbar.
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import AppButton from './AppButton.vue';
import AppIcon from './AppIcon.vue';
import AppMenu from './AppMenu.vue';
import AppSwitch from './AppSwitch.vue';
import { copyText as writeClipboard, readClipboard } from './clipboard.js';
import { t } from '../i18n.js';
import { syntaxTokens, detectLanguage } from './pythonSyntax.js';
import { editCommand, findMatches, documentSymbols, completions } from './codeEditing.js';
import './codeEditor.css';

const props = defineProps({
  bufferKey: String,
  language: String,
  readOnly: Boolean,
  disabled: Boolean,
  analysis: Object,
  ariaLabel: String,
  sourceToolbar: { type: Boolean, default: true }
});
const model = defineModel({ default: '' });
const emit = defineEmits(['run', 'help', 'outline', 'analyse', 'blur']);
const input = ref(null),
  scroll = ref({ x: 0, y: 0 }),
  selection = ref({ start: 0, end: 0 });
const findOpen = ref(false),
  replaceOpen = ref(false),
  query = ref(''),
  replacement = ref(''),
  caseSensitive = ref(false),
  wholeWord = ref(false),
  regex = ref(false);
const findInput = ref(null),
  suggestions = ref([]),
  suggestionIndex = ref(0),
  clipboardError = ref('');
const completionStyle = ref({});
const fontSize = defineModel('fontSize', { default: 9.25 });
const buffers = new Map(),
  history = ref({ steps: [], index: -1 });
let completionTimer,
  analysisRequest = 0,
  completionSuppressed = false;
const options = computed(() => ({
  caseSensitive: caseSensitive.value,
  wholeWord: wholeWord.value,
  regex: regex.value
}));
const matches = computed(() =>
  findMatches(model.value, query.value, options.value)
);
const selectedText = computed(() =>
  model.value.slice(selection.value.start, selection.value.end)
);
const effectiveLanguage = computed(() =>
  detectLanguage(model.value, props.language)
);
const highlighted = computed(() => {
  const tokens = syntaxTokens(
    model.value,
    props.language,
    props.analysis?.source === model.value ? props.analysis.moduleNames : []
  );
  const word = /^[\w$]+$/.test(selectedText.value) ? selectedText.value : '';
  const overlays = [
    ...matches.value.map((row) => ({ ...row, role: 'search' })),
    ...findMatches(model.value, word, {
      wholeWord: true,
      caseSensitive: true
    }).map((row) => ({ ...row, role: 'occurrence' }))
  ];
  const parts = [];
  let offset = 0;
  for (const token of tokens) {
    const end = offset + token.text.length,
      cuts = [
        ...new Set([
          offset,
          end,
          ...overlays
            .flatMap((row) => [row.start, row.end])
            .filter((point) => point > offset && point < end)
        ])
      ].sort((a, b) => a - b);
    for (let i = 1; i < cuts.length; i++)
      parts.push({
        text: model.value.slice(cuts[i - 1], cuts[i]),
        role: token.role,
        overlay: overlays.find(
          (row) => row.start <= cuts[i - 1] && row.end >= cuts[i]
        )?.role
      });
    offset = end;
  }
  return parts;
});
function snapshot() {
  return { text: model.value, ...selection.value };
}
function record() {
  if (history.value.steps[history.value.index]?.text === model.value) return;
  history.value.steps.splice(history.value.index + 1);
  history.value.steps.push(snapshot());
  if (history.value.steps.length > 120) history.value.steps.shift();
  history.value.index = history.value.steps.length - 1;
}
watch(
  () => props.bufferKey,
  async (key) => {
    suggestions.value = [];
    selection.value = { start: 0, end: 0 };
    scroll.value = { x: 0, y: 0 };
    if (!buffers.has(key)) buffers.set(key, { steps: [snapshot()], index: 0 });
    history.value = buffers.get(key);
    await nextTick();
    if (input.value) {
      input.value.scrollTop = 0;
      input.value.scrollLeft = 0;
    }
  },
  { immediate: true }
);
watch([model, () => props.bufferKey, () => props.language], () => {
  record();
  dismissCompletions();
  completionSuppressed = false;
  clearTimeout(completionTimer);
  completionTimer = setTimeout(() => complete(false), 140);
});
onBeforeUnmount(() => clearTimeout(completionTimer));
watch(
  () => props.analysis,
  (result) => {
    if (
      !result ||
      result.requestId !== analysisRequest ||
      result.bufferKey !== props.bufferKey ||
      result.source !== model.value ||
      result.cursor !== input.value?.selectionEnd
    )
      return;
    suggestions.value =
      !completionSuppressed && document.activeElement === input.value
        ? result.completions
        : [];
    suggestionIndex.value = 0;
    nextTick(positionCompletions);
  }
);
function dismissCompletions() {
  analysisRequest++;
  completionSuppressed = true;
  suggestions.value = [];
}
function positionCompletions() {
  if (!suggestions.value.length || !input.value) return;
  const area = input.value.closest('.code-buffer'),
    popup = area.querySelector('.code-completions'),
    style = getComputedStyle(input.value);
  if (!popup) return;
  const before = model.value.slice(0, input.value.selectionEnd),
    line = before.slice(before.lastIndexOf('\n') + 1),
    canvas = document.createElement('canvas').getContext('2d');
  canvas.font = style.font;
  const x = 34 + 12 + canvas.measureText(line).width - input.value.scrollLeft,
    y =
      12 +
      before.split('\n').length * parseFloat(style.lineHeight) -
      input.value.scrollTop;
  completionStyle.value = {
    left:
      Math.max(4, Math.min(x, area.clientWidth - popup.offsetWidth - 4)) + 'px',
    top:
      Math.max(4, Math.min(y, area.clientHeight - popup.offsetHeight - 4)) +
      'px'
  };
}
function blur(event) {
  if (!event.relatedTarget?.closest('.code-completions')) dismissCompletions();
}
function select(start, end = start) {
  if (!input.value) return;
  selection.value = { start, end };
  input.value.focus();
  input.value.setSelectionRange(start, end);
  input.value.scrollTop =
    Math.max(0, model.value.slice(0, start).split('\n').length - 3) *
    parseFloat(getComputedStyle(input.value).lineHeight);
  syncScroll();
}
async function apply(value) {
  model.value = value.text;
  await nextTick();
  select(value.start, value.end);
  record();
}
async function restore(index) {
  const step = history.value.steps[index];
  if (!step || props.readOnly) return;
  history.value.index = index;
  model.value = step.text;
  await nextTick();
  select(step.start, step.end);
}
function command(action) {
  if (!props.readOnly)
    apply(
      editCommand(
        action,
        model.value,
        selection.value.start,
        selection.value.end,
        effectiveLanguage.value
      )
    );
}
function syncSelection() {
  if (!input.value) return;
  selection.value = {
    start: input.value.selectionStart,
    end: input.value.selectionEnd
  };
  const step = history.value.steps[history.value.index];
  if (step?.text === model.value) Object.assign(step, selection.value);
}
function syncScroll() {
  if (input.value)
    scroll.value = { x: input.value.scrollLeft, y: input.value.scrollTop };
}
function showFind(replace = false) {
  dismissCompletions();
  if (findOpen.value && replaceOpen.value === replace) {
    findOpen.value = false;
    query.value = '';
    input.value.focus();
    return;
  }
  findOpen.value = true;
  replaceOpen.value = replace && !props.readOnly;
  nextTick(() => {
    findInput.value?.focus();
    findInput.value?.select();
  });
}
function nextMatch(backwards = false) {
  const rows = matches.value;
  if (!rows.length) return;
  const row = backwards
    ? [...rows].reverse().find((row) => row.end < selection.value.start) ||
      rows.at(-1)
    : rows.find((row) => row.start > selection.value.start) || rows[0];
  select(row.start, row.end);
}
function replace(all = false) {
  if (props.readOnly) return;
  const rows = all
    ? matches.value
    : matches.value.filter(
        (row) =>
          row.start === selection.value.start && row.end === selection.value.end
      );
  if (!rows.length) return nextMatch();
  let text = model.value;
  for (const row of [...rows].reverse())
    text = text.slice(0, row.start) + replacement.value + text.slice(row.end);
  apply({
    text,
    start: rows[0].start,
    end: rows[0].start + replacement.value.length
  });
}
async function clipboard(action) {
  try {
    clipboardError.value = '';
    if (action === 'paste') {
      if (props.readOnly) return;
      const value = await readClipboard();
      apply({
        text:
          model.value.slice(0, selection.value.start) +
          value +
          model.value.slice(selection.value.end),
        start: selection.value.start + value.length,
        end: selection.value.start + value.length
      });
    } else {
      await writeClipboard(selectedText.value);
      if (action === 'cut' && !props.readOnly)
        apply({
          text:
            model.value.slice(0, selection.value.start) +
            model.value.slice(selection.value.end),
          start: selection.value.start,
          end: selection.value.start
        });
    }
  } catch (error) {
    clipboardError.value = error.message;
  }
}
function complete(manual = true) {
  clearTimeout(completionTimer);
  if (manual) completionSuppressed = false;
  const cursor = input.value?.selectionEnd || 0;
  emit('analyse', {
    bufferKey: props.bufferKey,
    source: model.value,
    cursor,
    manual,
    requestId: ++analysisRequest
  });
  if (!props.analysis && !props.readOnly && document.activeElement === input.value) {
    const prefix = /[\w$:-]*$/.exec(model.value.slice(0, cursor))[0];
    suggestions.value =
      !completionSuppressed && (manual || prefix.length >= 2)
        ? completions(model.value, cursor, effectiveLanguage.value)
        : [];
    suggestionIndex.value = 0;
    nextTick(positionCompletions);
  }
}
function acceptSuggestion(row, suffix = '') {
  dismissCompletions();
  if (props.readOnly) return;
  const text = row.insertText || row.name,
    cursor = row.start + text.length + (row.cursorOffset || 0);
  const source =
    model.value.slice(0, row.start) + text + model.value.slice(row.end);
  apply({
    text: source.slice(0, cursor) + suffix + source.slice(cursor),
    start: cursor + suffix.length,
    end: cursor + suffix.length
  });
}
function goToLine(line) {
  const position = model.value
    .split('\n')
    .slice(0, line - 1)
    .reduce((sum, value) => sum + value.length + 1, 0);
  select(position);
}
function navigateSymbol(delta) {
  const symbols =
      props.analysis?.symbols ||
      documentSymbols(model.value, effectiveLanguage.value),
    line = model.value.slice(0, selection.value.end).split('\n').length;
  const row =
    delta > 0
      ? symbols.find((row) => row.line > line) || symbols[0]
      : [...symbols].reverse().find((row) => row.line < line) || symbols.at(-1);
  if (row) goToLine(row.line);
}
function definition() {
  const cursor = selection.value.end,
    before = /[\w$]*$/.exec(model.value.slice(0, cursor))[0],
    after = /^[\w$]*/.exec(model.value.slice(cursor))[0];
  const symbols =
    props.analysis?.symbols ||
    documentSymbols(model.value, effectiveLanguage.value);
  const row = symbols.find((row) => row.name === before + after);
  if (row) goToLine(row.line);
}
function key(event) {
  const ctrl = event.ctrlKey || event.metaKey;
  if (event.key === 'Tab' && event.target !== input.value) return;
  if (
    event.target.tagName === 'INPUT' &&
    !['Escape', 'F3'].includes(event.key) &&
    !(ctrl && ['f', 'h'].includes(event.key.toLowerCase()))
  )
    return;
  if (ctrl && event.key === 'Enter') {
    event.preventDefault();
    dismissCompletions();
    emit('run', selectedText.value || model.value);
    return;
  }
  if (
    suggestions.value.length &&
    !ctrl &&
    ['ArrowDown', 'ArrowUp', 'Enter', 'Tab', ' '].includes(event.key)
  ) {
    if (event.key === 'Enter') {
      dismissCompletions();
      return;
    }
    event.preventDefault();
    if (['Tab', ' '].includes(event.key))
      acceptSuggestion(
        suggestions.value[suggestionIndex.value],
        event.key === ' ' ? ' ' : ''
      );
    else {
      suggestionIndex.value =
        (suggestionIndex.value +
          (event.key === 'ArrowDown' ? 1 : suggestions.value.length - 1)) %
        suggestions.value.length;
      nextTick(() =>
        input.value.parentElement.parentElement
          .querySelector('[aria-selected="true"]')
          ?.scrollIntoView({ block: 'nearest' })
      );
    }
    return;
  }
  if (event.key === 'Escape' && (suggestions.value.length || findOpen.value)) {
    event.preventDefault();
    event.stopPropagation();
    const searching = !suggestions.value.length;
    dismissCompletions();
    if (searching) {
      findOpen.value = false;
      query.value = '';
      input.value.focus();
    }
    return;
  }
  let handled = true;
  if (ctrl && event.key.toLowerCase() === 'z')
    restore(history.value.index + (event.shiftKey ? 1 : -1));
  else if (ctrl && event.key.toLowerCase() === 'y')
    restore(history.value.index + 1);
  else if (ctrl && ['f', 'h'].includes(event.key.toLowerCase()))
    showFind(event.key.toLowerCase() === 'h');
  else if (event.key === 'F3') nextMatch(event.shiftKey);
  else if (ctrl && event.code === 'Space') complete();
  else if (ctrl && event.shiftKey && event.key.toLowerCase() === 'o')
    emit('outline');
  else if (event.altKey && ['ArrowUp', 'ArrowDown'].includes(event.key))
    navigateSymbol(event.key === 'ArrowUp' ? -1 : 1);
  else if (event.key === 'F12') definition();
  else if (ctrl && event.shiftKey && event.key.toLowerCase() === 'k')
    command('delete_line');
  else if (ctrl && event.key === '/') command('toggle_comment');
  else if (ctrl && event.key.toLowerCase() === 'd') command('duplicate');
  else if (event.key === 'Tab') {
    if (event.shiftKey || selectedText.value)
      command(event.shiftKey ? 'unindent' : 'indent');
    else if (!props.readOnly) {
      const cursor = selection.value.end,
        count =
          4 - ((cursor - model.value.lastIndexOf('\n', cursor - 1) - 1) % 4);
      apply({
        text:
          model.value.slice(0, cursor) +
          ' '.repeat(count) +
          model.value.slice(cursor),
        start: cursor + count,
        end: cursor + count
      });
    }
  } else handled = false;
  if (handled) event.preventDefault();
  else suggestions.value = [];
}
defineExpose({
  select,
  goToLine,
  selectedText,
  showFind,
  clipboard,
  historyTo: restore,
  undo() {
    return restore(history.value.index - 1);
  },
  redo() {
    return restore(history.value.index + 1);
  },
  frameState: computed(() => ({
    historyCount: history.value.steps.length,
    historyIndex: history.value.index,
    canUndo: history.value.index > 0,
    canRedo: history.value.index < history.value.steps.length - 1,
    canCopy: !!selectedText.value
  })),
  focus() {
    input.value?.focus();
  }
});
</script>
<template>
  <section
    class="code-editor"
    :style="{ '--code-size': fontSize + 'pt' }"
    @keydown="key"
  >
    <div v-if="sourceToolbar" class="code-source-toolbar">
      <AppIcon name="MDI_FILE_EDIT" /><span>{{ t('Source') }}</span>
      <AppButton
        icon-only
        icon="undo"
        label="Undo"
        :disabled="readOnly || history.index <= 0"
        @click="restore(history.index - 1)"
      />
      <AppButton
        icon-only
        icon="redo"
        label="Redo"
        :disabled="readOnly || history.index >= history.steps.length - 1"
        @click="restore(history.index + 1)"
      />
      <AppMenu overlay label="Edit history" icon="history"
        ><AppButton
          v-for="(step, index) in [...history.steps].reverse()"
          :key="index"
          :label="
            String(history.steps.length - index) +
            ' · ' +
            step.text.split('\n')[0].slice(0, 80)
          "
          :disabled="readOnly"
          @click="restore(history.steps.length - index - 1)"
      /></AppMenu>
      <slot name="actions" />
      <AppButton
        icon-only
        icon="FAS_CUT"
        label="Cut"
        :disabled="readOnly || !selectedText"
        @click="clipboard('cut')"
      />
      <AppButton
        icon-only
        icon="copy"
        label="Copy"
        :disabled="!selectedText"
        @click="clipboard('copy')"
      />
      <AppButton
        icon-only
        icon="MDI_CONTENT_PASTE"
        label="Paste"
        :disabled="readOnly"
        @click="clipboard('paste')"
      />
      <AppMenu overlay label="Text size" icon="MDI_FORMAT_SIZE"
        ><AppButton
          v-for="(size, index) in [8, 9.25, 11, 13, 15]"
          :key="size"
          :label="['Small', 'Normal', 'Medium', 'Large', 'Extra large'][index]"
          :aria-pressed="size === fontSize"
          @click="fontSize = size"
      /></AppMenu>
      <AppButton icon-only icon="search" label="Find" @click="showFind()" />
      <AppButton
        icon-only
        icon="MDI_PLAY_BOX_OUTLINE"
        label="Run selection"
        :disabled="readOnly || disabled || !selectedText"
        @click="emit('run', selectedText)"
      />
      <AppButton
        icon-only
        icon="help"
        label="Code editor help"
        @click="emit('help')"
      />
    </div>
    <div v-if="findOpen" class="code-search">
      <input
        ref="findInput"
        v-model="query"
        :aria-label="t('Find in source')"
        :placeholder="t('Find')"
        @keydown.enter.prevent="nextMatch($event.shiftKey)"
      />
      <span>{{ matches.length }}</span
      ><AppButton
        icon-only
        icon="previous"
        label="Previous match"
        @click="nextMatch(true)"
      /><AppButton
        icon-only
        icon="next"
        label="Next match"
        @click="nextMatch()"
      />
      <label
        >{{ t('Match case')
        }}<AppSwitch v-model="caseSensitive" label="Match case" /></label
      ><label
        >{{ t('Whole word')
        }}<AppSwitch v-model="wholeWord" label="Whole word" /></label
      ><label
        >{{ t('Regular expression')
        }}<AppSwitch v-model="regex" label="Regular expression"
      /></label>
      <AppButton
        v-if="!readOnly"
        icon-only
        icon="edit"
        label="Replace"
        @click="replaceOpen = !replaceOpen"
      /><AppButton
        icon-only
        icon="close"
        label="Close search"
        @click="
          findOpen = false;
          query = '';
        "
      />
      <template v-if="replaceOpen"
        ><input
          v-model="replacement"
          :aria-label="t('Replacement')"
          :placeholder="t('Replacement')" /><AppButton
          label="Replace"
          @click="replace()" /><AppButton
          label="Replace all"
          @click="replace(true)"
      /></template>
    </div>
    <p v-if="clipboardError" class="error" role="alert">
      {{ t(clipboardError) }}
    </p>
    <div class="code-buffer">
      <div class="code-line-numbers" aria-hidden="true">
        <pre :style="{ transform: `translateY(${-scroll.y}px)` }">{{
          Array.from(
            { length: model.split('\n').length },
            (_, i) => i + 1
          ).join('\n')
        }}</pre>
      </div>
      <div class="code-input-area">
        <pre
          class="code-highlight"
          aria-hidden="true"
          :style="{ transform: `translate(${-scroll.x}px, ${-scroll.y}px)` }"
        ><span v-for="(part, index) in highlighted" :key="index" :class="[part.role && 'syntax-' + part.role, part.overlay && 'syntax-' + part.overlay]">{{ part.text }}</span>{{ '\n' }}</pre>
        <textarea
          ref="input"
          v-model="model"
          wrap="off"
          spellcheck="false"
          autocapitalize="off"
          autocomplete="off"
          :readonly="readOnly"
          :aria-label="ariaLabel || t('Script source')"
          @select="syncSelection"
          @keyup="syncSelection"
          @click="syncSelection"
          @input="
            syncSelection();
            record();
          "
          @scroll="syncScroll"
          @blur="
            blur();
            emit('blur', model);
          "
        />
      </div>
      <div
        v-if="suggestions.length"
        class="code-completions"
        :style="completionStyle"
        role="listbox"
        :aria-label="t('Code completions')"
      >
        <AppButton
          v-for="(row, index) in suggestions"
          :key="row.label || row.name"
          role="option"
          :aria-selected="index === suggestionIndex"
          :label="row.label || row.name"
          :class="{ detailed: row.detail }"
          @click="acceptSuggestion(row)"
          ><AppIcon
            :name="
              row.kind === 'class'
                ? 'MDI_FORMAT_SIZE'
                : row.kind === 'module'
                  ? 'MDI_API'
                  : 'code'
            "
          /><span
            ><strong>{{ row.label || row.name }}</strong
            ><small v-if="row.detail">{{ t(row.detail) }}</small></span
          ><small class="code-completion-kind">{{
            t(row.kind || 'variable')
          }}</small></AppButton
        >
      </div>
    </div>
  </section>
</template>
