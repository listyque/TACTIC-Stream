<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import AppButton from '../../controls/AppButton.vue';
import AppIcon from '../../controls/AppIcon.vue';
import FrameView from '../../frame/FrameView.vue';
import NotificationHistoryRow from './NotificationHistoryRow.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { t } from '../../i18n.js';
import { appearance } from '../../appearance.js';
import {
  notificationHistory,
  clearNotificationHistory
} from './notifications.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/activity/notifications.ui.mjs';
import './activityFeed.css';
const emit = defineEmits(['closed', 'open-link']);
const dialog = ref(null),
  content = ref(null),
  width = ref(0),
  height = ref(0),
  group = ref('all');
const geometry = computed(() => UI.layout(width.value, height.value));
const records = computed(() =>
  notificationHistory.records.filter(
    (row) => group.value === 'all' || row.group === group.value
  )
);
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const size = entries[0].contentRect;
    if (size.width > 0) {
      width.value = size.width;
      height.value = size.height;
    }
  });
  observer.observe(content.value);
});
onBeforeUnmount(() => observer?.disconnect());
const bounds = (rect) => ({
  position: 'absolute',
  left: rect.x + 'px',
  top: rect.y + 'px',
  width: rect.width + 'px',
  height: rect.height + 'px'
});
function action(event) {
  if (event.type === 'clear') clearNotificationHistory();
  else if (event.type === 'group') group.value = event.value;
}
function link(value) {
  dialog.value.close();
  emit('open-link', value);
}
defineExpose({
  open() {
    dialog.value.show();
  }
});
</script>
<template>
  <Teleport to="body"
    ><dialog
      v-window="{ kind: 'notifications', type: 'window' }"
      ref="dialog"
      class="activity-dialog system-activity-dialog"
      :aria-label="t('Notifications')"
      @close="emit('closed')"
    >
      <header class="activity-feed-heading">
        <AppIcon name="system-activity" /><strong>{{
          t('Notifications')
        }}</strong
        ><AppButton
          icon-only
          icon="close"
          label="Close Notifications"
          @click="dialog.close()"
        />
      </header>
      <div ref="content" class="system-activity-content">
        <section
          class="activity-feed-panel"
          :style="bounds(geometry.panel)"
        ></section>
        <FrameView
          class="activity-feed-toolbar"
          :style="bounds(geometry.header)"
          :scene="
            UI.header(
              {
                count: notificationHistory.records.length,
                group,
                repository: false
              },
              geometry.header.width,
              appearance.language
            )
          "
          @event="action"
        />
        <div
          class="system-activity-history"
          :style="bounds(geometry.history)"
          role="log"
          :aria-label="t('Notification history')"
        >
          <NotificationHistoryRow
            v-for="row in records"
            :key="row.notificationId"
            :record="row"
            @open-link="link"
          />
          <FrameView
            v-if="!records.length"
            class="system-activity-empty"
            :scene="
              UI.empty(
                geometry.history.width,
                geometry.history.height,
                appearance.language
              )
            "
          />
        </div>
      </div></dialog
  ></Teleport>
</template>
<style>
.system-activity-dialog {
  width: min(56dvw, calc(100dvw - 16px));
  height: min(64dvh, calc(100dvh - 16px));
}
.system-activity-content {
  position: relative;
  flex: 1;
  min-height: 0;
  background: var(--page);
}
.system-activity-content > .activity-feed-panel {
  margin: 0;
  padding: 0;
  border: 1px solid var(--outline-variant);
  border-radius: var(--surface-radius);
  background: var(--surface);
}
.system-activity-content > .activity-feed-toolbar {
  padding: 0;
  display: block;
  background: transparent;
}
.system-activity-history {
  overflow: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}
.system-activity-empty {
  position: absolute;
  inset: 0;
}
@media (max-width: 760px) {
  .system-activity-dialog {
    width: calc(100dvw - 8px);
    height: calc(100dvh - 8px);
  }
}
</style>
