<script setup>
// ActivityFeedView.qml / ActivityFeedController; the screen owns requests and read state.
import {
  inject,
  ref,
  computed,
  watch,
  nextTick,
  onMounted,
  onBeforeUnmount
} from 'vue';
import AppButton from '../../controls/AppButton.vue';
import AppIcon from '../../controls/AppIcon.vue';
import ActivityUsers from './ActivityUsers.vue';
import AppMenu from '../../controls/AppMenu.vue';
import { usePagination } from '../../controls/pagination.js';
import ActivityToolbar from './ActivityToolbar.vue';
import FrameView from '../../frame/FrameView.vue';
import { appearance } from '../../appearance.js';
import { observeFrameSizes } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/activity/feed.ui.mjs';
import ActivityEventCard from './ActivityEventCard.vue';
import ActivityCalendar from './ActivityCalendar.vue';
import { serverClock, serverTimestamp } from '../../serverClock.js';
import { activityFeed } from '../../api.js';
import { t } from '../../i18n.js';
import { mobile } from '../../mobile.js';
import {
  feedFilters,
  matchesSearch,
  uniqueRecords,
  dateLabel,
  dayLabel,
  dateKey
} from './activity.js';
import './activityFeed.css';

const usersAnchor = ref(null),
  calendarAnchor = ref(null);
const openHelp = inject('openHelp');
const props = defineProps({
  ticket: String,
  project: String,
  login: String,
  updates: Object,
  updatesError: String
});
const emit = defineEmits([
  'visibility',
  'notification',
  'unread',
  'open-object',
  'open-link',
  'closed',
  'retry',
  'session-expired'
]);
const dialog = ref(null),
  viewport = ref(null),
  content = ref(null),
  usersMenu = ref(null),
  calendarMenu = ref(null),
  calendar = ref(null);
const feedWidth = ref(500);
let feedObserver;
onMounted(() => {
  feedObserver = observeFrameSizes((entries) => {
    if (entries[0].contentRect.width > 0)
      feedWidth.value = entries[0].contentRect.width;
  });
  feedObserver.observe(viewport.value);
});
onBeforeUnmount(() => feedObserver?.disconnect());
const visible = ref(false),
  busy = ref(false),
  error = ref(''),
  calendarError = ref(''),
  pollError = ref('');
watch(visible, (value) => emit('visibility', value));
const optionsVisible = ref(false);
const filter = ref('all'),
  selectedUsers = ref([]),
  pendingUsers = ref([]),
  userQuery = ref(''),
  excludeOwn = ref(false),
  search = ref(''),
  day = ref('');
const records = ref([]),
  users = ref([]),
  counts = ref({}),
  countsReady = ref(false),
  calendarBusy = ref(false),
  offset = ref(0),
  hasMore = ref(false);
const notifications = ref(true),
  unread = ref(new Set());
const clockTick = ref(0);
const now = computed(() => {
  clockTick.value;
  return serverClock.now();
});
let requestId = 0,
  calendarId = 0,
  calendarVersion = 0,
  contextId = 0,
  latest = '',
  cursor = '',
  baseline = true,
  stopped = false,
  polling = false,
  pendingPoll = false,
  pendingRefresh = 0;
const seen = new Set();
const storageKey = computed(
  () => 'tactic_stream.activity.' + props.login + '.' + props.project
);
const userTitle = computed(() =>
  !selectedUsers.value.length
    ? t('All users')
    : selectedUsers.value.length > 1
      ? t('{count} users', { count: selectedUsers.value.length })
      : users.value.find((row) => row.login === selectedUsers.value[0])
          ?.displayName || selectedUsers.value[0]
);
const shown = computed(() =>
  records.value.filter((row) => matchesSearch(row, search.value))
);
const grouped = computed(() => [
  ...Map.groupBy(shown.value, (row) =>
    row.timestamp ? dateKey(serverTimestamp(row.timestamp)) : ''
  ).entries()
]);
const options = () => ({
  filter: filter.value,
  users: selectedUsers.value,
  exclude_own: excludeOwn.value,
  day: day.value
});
const pagination = usePagination(
  viewport,
  content,
  () => visible.value && !busy.value && !error.value && hasMore.value,
  () => load(false)
);
watch([visible, busy, error, hasMore, shown], pagination.check, {
  flush: 'post'
});
function toolbarEvent(event, source) {
  if (event.type === 'options') optionsVisible.value = !optionsVisible.value;
  else if (event.type === 'notifications') notifications.value = event.value;
  else if (event.type === 'exclude') {
    excludeOwn.value = event.value;
    changeFilter();
  } else if (event.type === 'search') search.value = event.value;
  else if (event.type === 'filter') {
    filter.value = event.value;
    changeFilter();
  } else if (event.type === 'refresh') refresh();
  else if (event.type === 'users') {
    usersAnchor.value = source;
    if (usersMenu.value.open) usersMenu.value.close(true);
    else usersMenu.value.openAt({ target: source });
  } else if (event.type === 'calendar') {
    calendarAnchor.value = source;
    if (calendarMenu.value.open) calendarMenu.value.close(true);
    else calendarMenu.value.openAt({ target: source });
  }
}
function store(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* Reading and notifications continue in memory. */
  }
}
function restore(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key)) ?? fallback;
  } catch {
    return fallback;
  }
}
function markRead() {
  if (latest) {
    cursor = latest;
    store(storageKey.value, cursor);
  }
  unread.value = new Set();
  emit('unread', 0);
}
function track(rows, initial = false) {
  if (rows.length)
    latest = [latest, ...rows.map((row) => row.timestamp || '')].sort().at(-1);
  const incoming = [];
  for (const row of rows) {
    const own =
      String(row.actor || '').toLocaleLowerCase() ===
      props.login.toLocaleLowerCase();
    const first = !seen.has(row.eventId);
    seen.add(row.eventId);
    if (row.timestamp > cursor && !own && !(initial && !cursor)) {
      unread.value.add(row.eventId);
      if (!initial && first && notifications.value) incoming.push(row);
    }
  }
  while (seen.size > 500) seen.delete(seen.values().next().value);
  if ((initial && !cursor) || visible.value) markRead();
  else emit('unread', unread.value.size);
  for (const row of incoming) emit('notification', row);
  return incoming.length;
}
async function poll() {
  if (polling) {
    pendingPoll = true;
    return;
  }
  if (stopped || !props.ticket) return;
  const context = contextId,
    previousCursor = cursor,
    rows = [];
  clockTick.value++;
  polling = true;
  try {
    let start = 0,
      result;
    do {
      result = await activityFeed(
        props.ticket,
        props.project,
        { offset: start },
        true
      );
      if (context !== contextId || stopped) return;
      rows.push(...result.records);
      start = result.nextOffset;
    } while (
      result.hasMore &&
      previousCursor &&
      result.records.at(-1)?.timestamp > previousCursor &&
      start <= 100000
    );
    const changed = rows.some((row) => !seen.has(row.eventId)) && !baseline;
    track(rows, baseline);
    baseline = false;
    pollError.value = '';
    if (changed) {
      calendarVersion++;
      countsReady.value = false;
      if (calendarMenu.value?.open) loadCounts();
      if (visible.value) {
        if (busy.value) pendingRefresh = Math.max(pendingRefresh, rows.length);
        else await load(true, true, rows.length);
      }
    }
  } catch (failure) {
    if (context === contextId && !stopped) {
      pollError.value = failure.message;
      if (failure.code === 'authentication_failed') {
        stopped = true;
        pendingPoll = false;
        emit('session-expired');
      }
    }
  } finally {
    polling = false;
    if (!stopped && (pendingPoll || context !== contextId)) {
      pendingPoll = false;
      poll();
    }
  }
}
watch(
  () => props.updates,
  (batch) => {
    if (
      batch &&
      (baseline ||
        batch.reconnected ||
        batch.activity?.length ||
        [...(batch.cacheChanges || []), ...(batch.cacheRetired || [])].some(
          (row) => row.projectCode === props.project
        ))
    )
      poll();
  }
);
watch(
  () => props.updatesError,
  (value) => {
    pollError.value = value || '';
  }
);
async function load(reset = true, background = false, newRecords = 0) {
  if (stopped || !props.ticket) return;
  if (!reset && (busy.value || !hasMore.value)) return;
  const request = ++requestId,
    context = contextId,
    start = reset ? 0 : offset.value;
  busy.value = true;
  error.value = '';
  pagination.reset();
  const top = viewport.value?.scrollTop || 0;
  const anchor =
    background && top > 0
      ? [...viewport.value.querySelectorAll('[data-event-id]')].find(
          (element) =>
            element.getBoundingClientRect().bottom >
            viewport.value.getBoundingClientRect().top + 34
        )
      : null;
  const anchorId = anchor?.dataset.eventId,
    anchorTop = anchor?.getBoundingClientRect().top;
  const oldest = records.value.at(-1),
    limit = Math.min(100000, offset.value + newRecords);
  try {
    let result,
      next = start;
    const rows = [];
    do {
      result = await activityFeed(
        props.ticket,
        props.project,
        { ...options(), offset: next },
        background
      );
      if (request !== requestId || context !== contextId || stopped) return;
      rows.push(...result.records);
      next = result.nextOffset;
      // Reload through the old tail so a burst larger than one page cannot leave a gap.
    } while (
      background &&
      oldest &&
      result.hasMore &&
      next < limit &&
      !result.records.some(
        (row) =>
          row.eventId === oldest.eventId || row.timestamp < oldest.timestamp
      )
    );
    records.value = uniqueRecords((reset ? [] : records.value).concat(rows));
    offset.value = next;
    hasMore.value = result.hasMore;
    users.value = result.users;
    pollError.value = '';
    track(rows, true);
    await nextTick();
    if (viewport.value && reset) {
      const restored =
        anchorId &&
        [...viewport.value.querySelectorAll('[data-event-id]')].find(
          (element) => element.dataset.eventId === anchorId
        );
      viewport.value.scrollTop = background
        ? restored
          ? viewport.value.scrollTop +
            restored.getBoundingClientRect().top -
            anchorTop
          : top
        : 0;
    }
  } catch (failure) {
    if (request === requestId && context === contextId) {
      error.value = failure.message;
      if (failure.code === 'authentication_failed') {
        stopped = true;
        pendingPoll = false;
        emit('session-expired');
      }
    }
  } finally {
    if (request === requestId && context === contextId) {
      busy.value = false;
      if (pendingRefresh && visible.value && !error.value) {
        const count = pendingRefresh;
        pendingRefresh = 0;
        load(true, true, count);
      }
    }
  }
}
async function loadCounts() {
  if (stopped || !props.ticket || calendarBusy.value || countsReady.value)
    return;
  const request = ++calendarId,
    context = contextId,
    revision = calendarVersion;
  calendarBusy.value = true;
  calendarError.value = '';
  try {
    const result = await activityFeed(props.ticket, props.project, {
      ...options(),
      day: '',
      counts_only: true
    });
    if (request !== calendarId || context !== contextId || stopped) return;
    counts.value = Object.fromEntries(
      result.dayCounts.map((row) => [row.dateKey, row.count])
    );
    countsReady.value = revision === calendarVersion;
  } catch (failure) {
    if (request === calendarId && context === contextId) {
      calendarError.value = failure.message;
      if (failure.code === 'authentication_failed') {
        stopped = true;
        pendingPoll = false;
        emit('session-expired');
      }
    }
  } finally {
    if (request === calendarId && context === contextId) {
      calendarBusy.value = false;
      if (
        !countsReady.value &&
        !calendarError.value &&
        calendarMenu.value?.open
      )
        loadCounts();
    }
  }
}
function invalidateCounts() {
  calendarId++;
  calendarBusy.value = false;
  countsReady.value = false;
  counts.value = {};
  day.value = '';
}
function changeFilter() {
  invalidateCounts();
  load();
}
function refresh() {
  emit('retry');
  calendarVersion++;
  countsReady.value = false;
  load();
  if (calendarMenu.value?.open) loadCounts();
}
function prepareUsers() {
  pendingUsers.value = [...selectedUsers.value];
  userQuery.value = '';
}
function applyUsers() {
  selectedUsers.value = [...pendingUsers.value];
  if (
    selectedUsers.value.length &&
    ['my_tasks', 'my_objects'].includes(filter.value)
  )
    filter.value = 'all';
  usersMenu.value.open = false;
  changeFilter();
}
function chooseDay(value) {
  day.value = value;
  calendarMenu.value.open = false;
  load();
}
async function open(login = '') {
  if (login) {
    selectedUsers.value = [login];
    filter.value = 'all';
    day.value = '';
    search.value = '';
    records.value = [];
    excludeOwn.value = false;
  }
  visible.value = true;
  dialog.value.show();
  markRead();
  if (!records.value.length) await load();
}
function close() {
  usersMenu.value.open = false;
  calendarMenu.value.open = false;
  dialog.value.close();
  visible.value = false;
  pendingRefresh = 0;
}
function openObject(record, target = false) {
  close();
  emit('open-object', { record, target });
}
function openLink(value) {
  if (visible.value) close();
  emit('open-link', value);
}
watch(notifications, (value) =>
  store('tactic_stream.activity.notifications.' + props.login, value)
);
watch(
  () => [props.ticket, props.login, props.project],
  () => {
    contextId++;
    requestId++;
    calendarId++;
    stopped = !props.ticket || !props.project;
    if (visible.value) close();
    records.value = [];
    users.value = [];
    busy.value = false;
    calendarBusy.value = false;
    counts.value = {};
    countsReady.value = false;
    filter.value = 'all';
    selectedUsers.value = [];
    pendingUsers.value = [];
    search.value = '';
    day.value = '';
    offset.value = 0;
    hasMore.value = false;
    error.value = '';
    pollError.value = '';
    calendarError.value = '';
    latest = '';
    baseline = true;
    seen.clear();
    unread.value = new Set();
    pendingRefresh = 0;
    pendingPoll = false;
    cursor = restore(storageKey.value, '');
    if (typeof cursor !== 'string') cursor = '';
    notifications.value =
      restore('tactic_stream.activity.notifications.' + props.login, true) ===
      true;
    emit('unread', 0);
  },
  { immediate: true }
);
onBeforeUnmount(() => {
  stopped = true;
  contextId++;
  requestId++;
  calendarId++;
});
defineExpose({
  open,
  windowContext: () => ({
    route: {
      args: [selectedUsers.value.length === 1 ? selectedUsers.value[0] : '']
    }
  })
});
</script>
<template>
  <Teleport to="body">
    <dialog
      v-window="{ kind: 'activity_feed', type: 'window' }"
      ref="dialog"
      class="activity-dialog activity-feed-dialog"
      :aria-label="t('Activity Feed')"
      :aria-busy="busy"
      @cancel.prevent="close"
      @close="
        visible = false;
        emit('closed');
      "
    >
      <header class="activity-feed-heading">
        <AppIcon name="activity-feed" /><strong>{{ t('Activity Feed') }}</strong
        ><AppButton
          v-if="!mobile"
          icon-only
          icon="help"
          label="Activity Feed help"
          @click="openHelp('activity_feed')"
        /><AppButton
          icon-only
          icon="close"
          label="Close Activity Feed"
          @click="close"
        />
      </header>
      <section class="activity-feed-panel">
        <ActivityToolbar
          :model="{
            phone: mobile,
            optionsVisible,
            notifications,
            excludeOwn,
            search,
            filter,
            userTitle,
            userCount: selectedUsers.length,
            day,
            dayLabel: dateLabel(day),
            busy
          }"
          @event="toolbarEvent"
        >
          <AppMenu
            ref="usersMenu"
            class="activity-user-menu"
            external-trigger
            :anchor="usersAnchor"
            label="Filter by users"
            icon="MDI_ACCOUNT_MULTIPLE"
            overlay
            :close-on-select="false"
            @toggle="usersMenu?.open && prepareUsers()"
          >
            <template v-if="mobile" #trigger
              ><AppIcon name="MDI_ACCOUNT_MULTIPLE" />{{
                t('Filter by users')
              }}</template
            >
            <ActivityUsers
              v-model="pendingUsers"
              :users="users"
              :login="login"
              @clear="pendingUsers = []"
              @cancel="usersMenu.open = false"
              @apply="applyUsers"
            />
          </AppMenu>
          <AppMenu
            ref="calendarMenu"
            class="activity-calendar-menu"
            external-trigger
            :anchor="calendarAnchor"
            :label="dateLabel(day)"
            icon="MDI_CALENDAR_MONTH"
            overlay
            modal
            :close-on-select="false"
            @toggle="calendarMenu?.open && (calendar?.reset(), loadCounts())"
          >
            <template v-if="mobile" #trigger
              ><AppIcon name="MDI_CALENDAR_MONTH" />{{
                dateLabel(day)
              }}</template
            >
            <ActivityCalendar
              ref="calendar"
              :counts="counts"
              :selected="day"
              :busy="calendarBusy"
              @accepted="chooseDay"
              @closed="calendarMenu.open = false"
            />
            <p v-if="calendarError" class="error" role="alert">
              {{ t(calendarError) }}
            </p>
            <AppButton v-if="calendarError" label="Retry" @click="loadCounts" />
          </AppMenu>
        </ActivityToolbar>
        <p v-if="error || pollError" class="error" role="alert">
          {{ t(error || pollError) }}
          <AppButton label="Retry" @click="refresh" />
        </p>
        <div
          ref="viewport"
          class="activity-feed-events"
          :aria-label="t('Activity events')"
          tabindex="0"
        >
          <div ref="content">
            <section v-for="[key, rows] in grouped" :key="key">
              <FrameView
                class="activity-day-label"
                :scene="UI.day(dayLabel(key), feedWidth)"
              /><ActivityEventCard
                v-for="row in rows"
                :key="row.eventId"
                :record="row"
                :now="now"
                @activity="openObject(row)"
                @target="openObject(row, true)"
                @open-link="openLink"
              />
            </section>
            <p v-if="!shown.length && !busy" class="activity-feed-empty">
              {{
                t(
                  search
                    ? 'No matching activity'
                    : day
                      ? 'No activity for this day'
                      : 'No activity for this filter'
                )
              }}
            </p>
            <p v-if="busy" class="activity-feed-loading" role="status">
              {{ t('Loading activity…') }}
            </p>
          </div>
        </div>
      </section>
    </dialog>
  </Teleport>
</template>
