<script setup>
import {
  computed,
  ref,
  watchPostEffect,
  h,
  onMounted,
  onBeforeUnmount
} from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/activity/event.ui.mjs';
import { t } from '../../i18n.js';
import { appearance } from '../../appearance.js';
import {
  eventSentence,
  eventIcon,
  changeValue,
  compactText,
  needsExpansion,
  timestampLabel,
  timestampFullLabel,
  safeColor
} from './activity.js';
import {
  escapeHtml,
  linkifyPlainText,
  activateRichLink
} from '../../controls/richText.js';
import { browserLink } from '../workspace/links.js';
const props = defineProps({ record: Object, now: Number });
const emit = defineEmits(['activity', 'target', 'open-link']);
const expanded = ref(false);
const sentence = ref(null),
  root = ref(null),
  width = ref(500),
  heights = ref({}),
  hovered = ref(false);
let observer;
const html = computed(() => eventSentence(props.record, expanded.value));
// CSSOM assignments preserve the site's CSP; injected style attributes are blocked.
watchPostEffect(() => {
  html.value;
  sentence.value?.querySelectorAll('[data-color]').forEach((element) => {
    element.style.color = safeColor(element.dataset.color);
  });
});
const changes = computed(() =>
  !props.record.relationAction &&
  ['create', 'change', 'delete'].includes(props.record.kind)
    ? props.record.changes || []
    : []
);
const expandable = computed(() =>
  [
    props.record.detail,
    props.record.title,
    ...changes.value.map((change) => changeValue(props.record, change))
  ].some(needsExpansion)
);
const time = computed(() => {
  appearance.language;
  return timestampLabel(
    props.record.timestamp,
    props.now ? new Date(props.now) : undefined
  );
});
function activate(event) {
  if (activateRichLink(event, (value) => emit('open-link', value))) return;
  const action = event.target.closest('[data-action]')?.dataset.action;
  if (action) {
    event.preventDefault();
    emit(action);
  }
}

const fieldLabel = (value) =>
  t(
    {
      name: 'Name',
      title: 'Title',
      description: 'Description',
      assigned: 'Assignee',
      status: 'Status',
      priority: 'Priority',
      'bid start date': 'Start date',
      'bid end date': 'Deadline'
    }[String(value).toLowerCase()] || value
  );
const model = computed(() => ({
  ...props.record,
  time: time.value,
  fullTime: timestampFullLabel(props.record.timestamp),
  expanded: expanded.value,
  expandable: expandable.value,
  hovered: hovered.value,
  changes: changes.value.map((row) => ({
    ...row,
    label: fieldLabel(row.field)
  }))
}));
const scene = computed(() =>
  UI.card(
    model.value,
    width.value,
    heights.value,
    appearance.language,
    appearance.theme
  )
);
const port = {
  props: { frameNode: Object },
  setup(port, { attrs }) {
    const element = ref(null);
    let resize;
    onMounted(() => {
      resize = observeFrameSizes(() => {
        const key =
            port.frameNode.view === 'sentence'
              ? 'sentence'
              : 'change_' + port.frameNode.index,
          height = element.value.getBoundingClientRect().height;
        if (height > 0 && heights.value[key] !== height)
          heights.value = { ...heights.value, [key]: height };
      });
      resize.observe(element.value);
    });
    onBeforeUnmount(() => resize?.disconnect());
    return () => {
      const body = port.frameNode.view === 'sentence',
        change = changes.value[port.frameNode.index],
        value = body
          ? html.value
          : expanded.value
            ? linkifyPlainText(changeValue(props.record, change), browserLink)
            : escapeHtml(compactText(changeValue(props.record, change)));
      return h('div', attrs, [
        h('div', {
          ref: (node) => {
            element.value = node;
            if (body) sentence.value = node;
          },
          class: body ? 'activity-sentence-port' : 'activity-change-port',
          style: {
            overflowWrap: 'anywhere',
            fontSize: body ? '13px' : '12px',
            lineHeight: body ? '18px' : '16px',
            userSelect: 'text'
          },
          innerHTML: value,
          onClick: activate
        })
      ]);
    };
  }
};
const views = {
  sentence: { component: port, nodeProps: true },
  change: { component: port, nodeProps: true }
};
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    if (entries[0].contentRect.width > 0)
      width.value = entries[0].contentRect.width;
  });
  observer.observe(root.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <article
    ref="root"
    class="activity-event-card"
    :data-event-id="record.eventId"
    :style="{ height: scene.height + 'px' }"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
  >
    <FrameView
      :scene="scene"
      :views="views"
      @event="
        (event) => {
          if (event.type === 'expand') expanded = !expanded;
        }
      "
    />
  </article>
</template>
<style>
.activity-event-card {
  display: block !important;
  position: relative;
  padding: 0 !important;
  min-width: 0;
}
.activity-event-card > .frame-view {
  height: 100%;
}
.activity-event-card .activity-sentence-port,
.activity-event-card .activity-change-port {
  white-space: normal;
}
</style>
