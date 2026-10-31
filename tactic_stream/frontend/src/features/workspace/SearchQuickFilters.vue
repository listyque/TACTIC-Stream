<script>
// SearchQuickFilterPopup.qml / SearchAssigneeFilterPopup.qml; the tab owns selection.
import { nextTick, toRaw } from 'vue';
import { searchConfiguration, userProfile } from '../../api.js';
import FrameView from '../../frame/FrameView.vue';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/search/popups.ui.mjs';
import * as Header from '../../../../src/tactic_stream/shared_ui/features/search/header.ui.mjs';
import {
  fontFamily,
  textStyles
} from '../../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import { qtLabelTextWidth } from '../../controls/typography/textMetrics.js';
import { t } from '../../i18n.js';
import AppButton from '../../controls/AppButton.vue';
import QuickFilterChip from '../../controls/display/QuickFilterChip.vue';
import AppIcon from '../../controls/AppIcon.vue';
import AppMenu from '../../controls/AppMenu.vue';
import UserPicker from '../../controls/UserPicker.vue';
import QuickFilterOptions from './QuickFilterOptions.vue';

const mine = '__current_login__';
export default {
  components: {
    FrameView,
    AppButton,
    AppIcon,
    AppMenu,
    UserPicker,
    QuickFilterOptions,
    QuickFilterChip
  },
  props: {
    ticket: String,
    project: String,
    searchType: String,
    tabId: String,
    scope: String,
    login: String,
    selections: Object,
    layout: Object,
    disabled: Boolean,
    boundary: Object,
    overlay: Boolean,
    budget: { type: Number, default: 0 }
  },
  emits: ['apply', 'reset', 'edit', 'toggle', 'resize'],
  data() {
    return {
      headerWidth: 400,
      catalog: null,
      busy: false,
      error: '',
      request: 0,
      visible: false,
      top: 0,
      height: 0,
      flows: {},
      menuBoundary: null,
      users: null,
      usersBusy: false,
      usersError: '',
      usersRequest: 0,
      groupKey: '',
      groupAnchor: null
    };
  },
  computed: {
    strip() {
      if (this.budget <= 0)
        return Header.quickStrip([], 0, appearance.language);
      const groups = this.groups.slice(0, 3).map((group) => {
        const item = {
          ...group,
          count: group.values.length,
          disabled: this.disabled || this.busy
        };
        item.textWidth = qtLabelTextWidth(
          Header.quickLabel(item, appearance.language),
          `400 ${textStyles.body}px "${fontFamily}"`
        );
        return item;
      });
      return Header.quickStrip(groups, this.budget, appearance.language);
    },
    shownGroups() {
      return this.groupKey
        ? this.groups.filter((group) => group.key === this.groupKey)
        : this.groups;
    },
    headerScene() {
      return UI.quickHeader(
        {
          busy: this.busy,
          loaded: !!this.catalog,
          count: this.count,
          personalized: this.personalized,
          disabled: this.disabled
        },
        this.headerWidth,
        appearance.language
      );
    },
    context() {
      return [
        this.ticket,
        this.project,
        this.searchType,
        this.tabId,
        this.scope
      ];
    },
    count() {
      return Object.values(this.selections || {}).reduce(
        (count, values) => count + values.length,
        0
      );
    },
    groups() {
      if (!this.catalog) return [];
      const standard = new Map(
        this.catalog.configuration.groups.map((group) => [group.key, group])
      );
      const personal = new Map(
        (this.layout?.groups || []).map((group) => [group.key, group])
      );
      const catalog = [...this.catalog.groups];
      for (const key of Object.keys(this.selections || {}))
        if (
          key.startsWith('column:') &&
          !catalog.some((group) => group.key === key)
        )
          catalog.push({
            key,
            title: key.slice(7).replaceAll('_', ' '),
            source: 'column',
            options: []
          });
      const order = [
        ...personal.keys(),
        ...standard.keys(),
        ...catalog.map((group) => group.key)
      ];
      return [...new Set(order)].flatMap((key) => {
        const group = catalog.find((group) => group.key === key),
          base = standard.get(key) || {},
          local = personal.get(key) || {};
        if (!group || base.enabled === false || local.enabled === false)
          return [];
        const values = this.selections?.[key] || [];
        const allowed = (value) =>
          (!base.options || base.options.includes(value)) &&
          (!local.options || local.options.includes(value));
        const options = [
          ...group.options,
          ...values
            .filter(
              (value) => !group.options.some((option) => option.key === value)
            )
            .map((value) => ({ key: value, title: value }))
        ].filter((option) => allowed(option.key));
        return [
          {
            ...group,
            ...(Object.hasOwn(base, 'icon') ? { icon: base.icon } : {}),
            ...(Object.hasOwn(local, 'icon') ? { icon: local.icon } : {}),
            options,
            values
          }
        ];
      });
    },
    selectedUsers() {
      return (this.selections?.assigned || []).filter(
        (value) => value !== mine
      );
    },
    personalized() {
      return this.layout !== null && this.layout !== undefined;
    }
  },
  watch: {
    'strip.width': {
      immediate: true,
      handler(width) {
        this.$emit('resize', width);
      }
    },
    budget(value) {
      this.close();
      if (value > 0 && this.ticket && this.searchType) this.load();
    },
    context() {
      this.request++;
      this.usersRequest++;
      this.busy = this.usersBusy = false;
      this.catalog = null;
      this.users = null;
      this.error = this.usersError = '';
      this.$refs.menu.close();
      this.$refs.assignees.close();
      this.groupKey = '';
      this.groupAnchor = null;
      if (this.budget > 0 && this.ticket && this.searchType) this.load();
    }
  },
  mounted() {
    this.menuBoundary = this.boundary || this.$el.closest('.workspace-browser');
    this.resize = new ResizeObserver(this.scrolled);
    this.resize.observe(this.$refs.viewport);
    if (this.budget > 0 && this.ticket && this.searchType) this.load();
  },
  beforeUnmount() {
    this.request++;
    this.usersRequest++;
    this.resize.disconnect();
  },
  methods: {
    t,
    async openGroup(action, source) {
      this.groupKey = action.key;
      this.groupAnchor = source;
      await nextTick();
      this.$refs.menu.open = true;
    },
    fullMenu(event) {
      if (
        event.target.closest('summary')?.parentElement === this.$refs.menu?.$el
      ) {
        this.groupKey = '';
        this.groupAnchor = null;
      }
    },
    groupHeader(group) {
      return UI.groupHeader(
        group.source === 'task' ? t(group.title) : group.title,
        this.headerWidth
      );
    },
    headerEvent(action) {
      if (action.type === 'edit') this.edit();
      else if (action.type === 'reset') this.reset();
      else if (action.type === 'clear') this.clear();
      else if (action.type === 'lastGroup')
        this.focusGroup(this.shownGroups.length - 1, -1);
    },
    open() {
      this.$refs.menu.open = true;
    },
    close() {
      this.$refs.menu.close(true);
    },
    async toggled(event) {
      this.$emit('toggle', event);
      this.visible = event.target.open;
      if (!this.visible) return;
      this.$refs.viewport.scrollTop = 0;
      await this.load();
      await nextTick();
      this.scrolled();
    },
    async load(force = false) {
      if (this.busy || (this.catalog && !force)) return;
      const request = ++this.request;
      this.busy = true;
      this.error = '';
      try {
        const catalog = await searchConfiguration(
          'read',
          this.ticket,
          this.project,
          this.searchType,
          { scope: this.scope || this.searchType.split('?')[0] }
        );
        if (request === this.request) this.catalog = catalog;
      } catch (error) {
        if (request === this.request) this.error = error.message;
      } finally {
        if (request === this.request) this.busy = false;
      }
    },
    scrolled() {
      if (this.$refs.viewport)
        this.headerWidth = this.$refs.viewport.clientWidth - 24;
      this.top = this.$refs.viewport.scrollTop;
      this.height = this.$refs.viewport.clientHeight;
    },
    optionsFor(group) {
      const all = {
        key: '',
        title: t('ALL'),
        selected: !group.values.length,
        accent: group.accent
      };
      if (group.key === 'assigned' && group.source === 'task')
        return [
          all,
          {
            key: mine,
            title: t('MY TASKS'),
            icon: 'user',
            accent: group.accent,
            selected: group.values.includes(mine)
          },
          {
            key: '__users__',
            title:
              t(this.selectedUsers.length ? 'USERS' : 'SELECT USERS') +
              (this.selectedUsers.length
                ? ' / ' + this.selectedUsers.length
                : ''),
            icon: 'groups',
            accent: group.accent,
            selected: !!this.selectedUsers.length
          }
        ];
      return [
        all,
        ...group.options.map((option) => ({
          ...option,
          accent: option.accent || group.accent,
          marker: option.showAccentMarker ?? !!option.accent,
          selected: group.values.includes(option.key)
        }))
      ];
    },
    apply(selections) {
      this.$emit('apply', {
        groups: structuredClone(
          toRaw((this.layout || this.catalog.configuration).groups)
        ),
        defaultSelections: selections
      });
    },
    select(group, key) {
      if (this.disabled) return;
      if (key === '__users__') {
        this.openUsers();
        return;
      }
      const selections = structuredClone(toRaw(this.selections || {})),
        values = new Set(selections[group] || []);
      if (!key) values.clear();
      else if (values.has(key)) values.delete(key);
      else values.add(key);
      if (values.size) selections[group] = [...values];
      else delete selections[group];
      this.apply(selections);
    },
    clear() {
      if (!this.disabled) this.apply({});
    },
    reset() {
      if (!this.disabled)
        this.$emit(
          'reset',
          structuredClone(toRaw(this.catalog.configuration.defaultSelections))
        );
    },
    edit() {
      this.close();
      this.$emit('edit', this.catalog);
    },
    focusGroup(index, direction) {
      const group = this.shownGroups[index],
        flow = group && this.flows[group.key];
      if (!flow) {
        this.$refs.viewport.scrollTop = 0;
        this.scrolled();
        this.$refs.header.focusControl('editQuickFiltersButton');
        return;
      }
      flow.focusOption(direction > 0 ? 0 : flow.options.length - 1);
    },
    async openUsers() {
      this.$refs.menu.close();
      this.$refs.assignees.open = true;
      if (this.users || this.usersBusy) return;
      const request = ++this.usersRequest;
      this.usersBusy = true;
      this.usersError = '';
      try {
        const result = await userProfile('read', this.ticket, this.project, {
          login: this.login
        });
        if (request === this.usersRequest) this.users = result.users;
      } catch (error) {
        if (request === this.usersRequest) this.usersError = error.message;
      } finally {
        if (request === this.usersRequest) this.usersBusy = false;
      }
    },
    setUsers(values) {
      const selections = structuredClone(toRaw(this.selections || {})),
        selected = [...values];
      if ((selections.assigned || []).includes(mine)) selected.push(mine);
      if (selected.length) selections.assigned = selected;
      else delete selections.assigned;
      this.apply(selections);
    }
  }
};
</script>
<template>
  <div
    class="search-quick-filter-host"
    @pointerdown.capture="fullMenu"
    @keydown.capture="fullMenu"
  >
    <FrameView
      v-if="strip.nodes.length"
      :scene="strip"
      :style="{ width: strip.width - 38 + 'px', height: '38px', flex: 'none' }"
      @event="openGroup"
    />
    <AppMenu
      ref="menu"
      class="search-quick-filters"
      :class="{ 'has-selection': count > 0 }"
      label="Quick filters"
      icon="filter"
      :max-height="400"
      :show-label="overlay"
      :overlay="overlay || !!groupKey"
      :close-on-select="false"
      :boundary="boundary || menuBoundary"
      :anchor="groupAnchor"
      :align-start="!!groupKey"
      @toggle="toggled"
    >
      <template #trigger
        ><AppIcon name="filter" /><span v-if="overlay">{{
          t('Quick filters')
        }}</span
        ><small v-if="count" class="action-count">{{ count }}</small></template
      >
      <div
        ref="viewport"
        class="quick-filter-viewport"
        :aria-busy="busy"
        @scroll.passive="scrolled"
      >
        <FrameView
          ref="header"
          :scene="headerScene"
          :style="{ height: headerScene.contentHeight + 'px', flex: 'none' }"
          @event="headerEvent"
        />
        <p v-if="busy || error" :class="{ error }" role="status">
          <span>{{ t(busy ? 'Loading filters…' : error) }}</span
          ><AppButton v-if="error" label="Retry" @click="load(true)" />
        </p>
        <section
          v-for="(group, index) in shownGroups"
          :key="group.key"
          class="quick-filter-group"
          :aria-label="group.source === 'task' ? t(group.title) : group.title"
        >
          <FrameView
            :scene="groupHeader(group)"
            :style="{ height: '24px', marginBottom: '9px', flex: 'none' }"
          />
          <QuickFilterOptions
            :ref="(flow) => (flows[group.key] = flow)"
            :options="optionsFor(group)"
            :viewport="$refs.viewport"
            :top="top"
            :height="height"
            :active="visible"
            :disabled="disabled"
            @activate="select(group.key, $event)"
            @scroll="scrolled"
            @adjacent="focusGroup(index + $event, $event)"
          />
        </section>
        <p v-if="catalog && !groups.length && !busy && !error" class="muted">
          {{ t('No filters available') }}
        </p>
        <slot v-if="!groupKey" :close="close" />
      </div>
    </AppMenu>
    <AppMenu
      ref="assignees"
      class="quick-filter-assignees"
      label="ASSIGNED TO"
      icon="groups"
      :overlay="overlay || !!groupAnchor"
      :anchor="groupAnchor || $refs.menu?.$el.querySelector('summary')"
      :close-on-select="false"
      :boundary="boundary || menuBoundary"
      @toggle="$emit('toggle', $event)"
    >
      <div class="quick-assignee-body">
        <header>
          <strong>{{ t('ASSIGNED TO') }}</strong
          ><QuickFilterChip
            :checked="!(selections?.assigned || []).length"
            :text="t('ALL')"
            :disabled="disabled"
            @click="select('assigned', '')"
          />
        </header>
        <QuickFilterChip
          icon="user"
          :text="t('MY TASKS')"
          :checked="(selections?.assigned || []).includes('__current_login__')"
          :disabled="disabled"
          @click="select('assigned', '__current_login__')"
        />
        <hr />
        <p v-if="usersBusy || usersError" role="status">
          <span>{{ t(usersBusy ? 'Loading data…' : usersError) }}</span
          ><AppButton v-if="usersError" label="Retry" @click="openUsers" />
        </p>
        <UserPicker
          v-if="users"
          :users="users"
          :current-login="login"
          :model-value="selectedUsers"
          :disabled="disabled"
          @update:model-value="setUsers"
        />
      </div>
    </AppMenu>
  </div>
</template>
<style>
.search-quick-filter-host {
  position: relative;
  display: flex;
  align-items: center;
}
.search-quick-filters:not(.labelled-menu) > summary {
  width: 38px;
  height: 38px;
}
.search-quick-filters.has-selection > summary,
.search-quick-filters[open] > summary {
  color: var(--primary);
}
.search-quick-filters[open] > summary {
  background: var(--content-selection);
}
.workspace-menu.search-quick-filters > .account-panel {
  width: 440px;
  max-height: min(400px, calc(100dvh - 16px));
  padding: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: none;
}
.quick-filter-viewport {
  position: relative;
  min-height: 0;
  overflow: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  padding: 12px;
}
.quick-filter-viewport > header {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: var(--control-height);
}
.quick-filter-viewport > header > strong {
  flex: 1;
  font-size: 12px;
}
.quick-filter-viewport > header > .icon-button {
  width: 28px;
  height: 28px;
}
.quick-filter-viewport > header > .app-button:not(.icon-button) {
  flex: none;
  padding: 0 12px;
  font-size: var(--text-body);
  font-weight: 600;
  color: var(--on-surface);
  border: 1px solid var(--outline-variant);
  background: var(--hover);
  border-radius: var(--button-radius);
  min-height: var(--control-height);
}
.quick-filter-group {
  margin-top: 16px;
}
.quick-filter-group > h3 {
  margin: 0 0 9px;
  font-size: var(--text-body-large);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.quick-filter-options {
  position: relative;
}
.quick-filter-options .quick-filter-chip.app-button {
  gap: 5px;
}
.quick-filter-options .quick-filter-chip .app-icon {
  width: 11px;
  height: 11px;
  font-size: 11px;
  color: var(--muted);
}
.quick-filter-options .primary .app-icon {
  color: var(--on-selected);
}
.quick-filter-accent {
  width: 8px;
  height: 8px;
  flex: none;
  border-radius: 50%;
  background-color: var(--chip-accent);
}
.quick-filter-assignees > summary {
  display: none;
}
.workspace-menu.quick-filter-assignees > .account-panel {
  width: 400px;
  height: 430px;
  max-height: calc(100dvh - 16px);
  padding: 12px;
  overflow: hidden;
}
.quick-assignee-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
}
.quick-assignee-body > header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.quick-assignee-body > header strong {
  flex: 1;
  font-size: var(--text-body-large);
}
.quick-assignee-body > .quick-filter-chip {
  align-self: flex-start;
}
.quick-assignee-body > hr {
  width: 100%;
  margin: 0;
  border: 0;
  border-top: 1px solid var(--outline-variant);
}
.quick-filter-field {
  margin-top: 16px;
  border-top: 1px solid var(--outline-variant);
  padding-top: 12px;
}
.quick-filter-field > summary {
  min-height: 28px;
}
.quick-filter-field .search-filter-panel {
  display: grid;
  gap: 12px;
  padding-top: 12px;
}
.quick-filter-field .search-filter-panel > label {
  display: grid;
  gap: 6px;
  padding: 0;
}
</style>
