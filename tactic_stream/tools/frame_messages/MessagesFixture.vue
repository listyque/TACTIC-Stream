<script setup>
import { ref, nextTick } from 'vue';
import {
  appearance,
  hostedPalette,
  initializeAppearance
} from '../../frontend/src/appearance.js';
import MessagesView from '../../frontend/src/features/messages/MessagesView.vue';
import MessageForm from '../../frontend/src/features/messages/MessageForm.vue';
import MessageReference from '../../frontend/src/features/messages/MessageReference.vue';
import ActivityCalendar from '../../frontend/src/features/activity/ActivityCalendar.vue';
import ActivityFeed from '../../frontend/src/features/activity/ActivityFeed.vue';
import ActivityEventCard from '../../frontend/src/features/activity/ActivityEventCard.vue';
import SystemActivity from '../../frontend/src/features/activity/SystemActivity.vue';
import { notificationHistory } from '../../frontend/src/features/activity/notifications.js';
import NotificationToast from '../../frontend/src/features/activity/NotificationToast.vue';
const fixture = ref(null),
  messages = ref(null),
  calendar = ref(null),
  activity = ref(null),
  notifications = ref(null),
  text = ref(''),
  recipients = ref(['artist']);
hostedPalette.value = {
  dark: '#78a6c4',
  darkBase: '#292d30',
  light: '#3d7599',
  lightBase: '#d4dce1'
};
initializeAppearance();
window.messagesFixture = {
  async show(value) {
    messages.value?.close();
    fixture.value = null;
    await nextTick();
    Object.assign(appearance, {
      theme: value.style,
      mode: value.dark ? 'dark' : 'light',
      language: value.language,
      clickAnimations: false,
      hoverAnimations: false,
      fadeAnimations: false,
      popupAnimations: false
    });
    fixture.value = value;
    text.value = value.screen === 'search' ? 'lighting' : 'Lighting review';
    recipients.value = ['artist'];
    await nextTick();
    if (
      [
        'messages',
        'forwarding',
        'view-members',
        'history',
        'pin-history',
        'files'
      ].includes(value.screen)
    ) {
      await messages.value.open(
        ['view-members', 'history', 'pin-history', 'files'].includes(
          value.screen
        )
          ? 'review'
          : 'favorites'
      );
      const dialog = document.querySelector('.messages-dialog');
      Object.assign(dialog.style, {
        width: (value.screen !== 'messages' ? 1000 : value.width) + 2 + 'px',
        height: (value.screen !== 'messages' ? 620 : value.height) + 42 + 'px',
        left: '0px',
        top: '0px',
        margin: '0px',
        maxWidth: 'none',
        maxHeight: 'none'
      });
    }
    if (value.screen === 'calendar') calendar.value.reset();
    if (['activity', 'notifications'].includes(value.screen)) {
      if (value.screen === 'activity') await activity.value.open();
      else {
        notificationHistory.records = value.model.history;
        notifications.value.open();
      }
      const dialog = document.querySelector(
        value.screen === 'activity'
          ? '.activity-dialog:not(.system-activity-dialog)'
          : '.system-activity-dialog'
      );
      Object.assign(dialog.style, {
        width: value.width + 2 + 'px',
        height: value.height + 42 + 'px',
        left: '0px',
        top: '0px',
        margin: '0px',
        maxWidth: 'none',
        maxHeight: 'none'
      });
    }
    await document.fonts.ready;
    for (let i = 0; i < 8; i++) await new Promise(requestAnimationFrame);
  }
};
</script>
<template>
  <section
    v-if="fixture"
    id="messages-fixture"
    :style="{
      width:
        ([
          'forwarding',
          'view-members',
          'history',
          'pin-history',
          'files'
        ].includes(fixture.screen)
          ? 1000
          : fixture.width) + 'px',
      height:
        ([
          'forwarding',
          'view-members',
          'history',
          'pin-history',
          'files'
        ].includes(fixture.screen)
          ? 620
          : fixture.height) + 'px'
    }"
  >
    <MessagesView
      v-if="
        [
          'messages',
          'forwarding',
          'view-members',
          'history',
          'pin-history',
          'files'
        ].includes(fixture.screen)
      "
      ref="messages"
      ticket="fixture"
      project="cg"
      login="admin"
    />
    <MessageForm
      v-else-if="
        [
          'create',
          'members',
          'search',
          'edit',
          'clear',
          'delete',
          'delete-message'
        ].includes(fixture.screen)
      "
      :mode="fixture.screen"
      v-model:text="text"
      v-model:recipients="recipients"
      :users="fixture.model.users"
      login="admin"
      valid
      can-create-group
      style="width: 100%; height: 100%"
    />
    <MessageReference
      v-else-if="['reference', 'forward'].includes(fixture.screen)"
      :reference="fixture.model.reference"
      :users="fixture.model.users"
      :forwarded="fixture.screen === 'forward'"
      :dismissible="fixture.screen === 'reference'"
    />
    <ActivityCalendar
      v-else-if="fixture.screen === 'calendar'"
      ref="calendar"
      :counts="fixture.model.calendar.counts"
      :selected="fixture.model.calendar.selected"
    />
    <ActivityFeed
      v-else-if="fixture.screen === 'activity'"
      ref="activity"
      ticket="fixture"
      project="cg"
      login="admin"
    />
    <SystemActivity
      v-else-if="fixture.screen === 'notifications'"
      ref="notifications"
    />
    <ActivityEventCard
      v-else-if="fixture.screen === 'event'"
      :record="fixture.model.activity[0]"
      :now="Date.now()"
    />
    <NotificationToast
      v-else-if="fixture.screen === 'toast'"
      :row="fixture.model.toast"
    />
  </section>
</template>
<style>
html,
body {
  margin: 0;
  background: var(--surface-high);
}
#messages-fixture {
  position: relative;
  overflow: hidden;
}
</style>
