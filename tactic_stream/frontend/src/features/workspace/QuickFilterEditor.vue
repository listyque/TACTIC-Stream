<script>
// Handler QuickFilterEditorController and QuickFilterEditorView.
import { searchConfiguration, userProfile } from '../../api.js';
import SearchEditorPart from './SearchEditorPart.vue';
import QuickFilterChip from '../../controls/display/QuickFilterChip.vue';
import { nextTick, toRaw } from 'vue';
import { t } from '../../i18n.js';
import AppButton from '../../controls/AppButton.vue';
import AppMenu from '../../controls/AppMenu.vue';
import AppSwitch from '../../controls/AppSwitch.vue';
import UserPicker from '../../controls/UserPicker.vue';
import { editor } from '../../../../src/tactic_stream/shared_ui/features/search/editors.ui.mjs';

export default {
  components: {
    AppButton,
    AppMenu,
    AppSwitch,
    SearchEditorPart,
    QuickFilterChip,
    UserPicker
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
    canManage: Boolean
  },
  emits: ['apply', 'changed'],
  data() {
    return {
      editor,
      chipHeight: 0,
      catalog: null,
      groups: [],
      selected: {},
      original: {},
      baseline: '',
      busy: false,
      error: '',
      message: '',
      showHidden: false,
      confirmation: false,
      uncertain: false,
      request: 0,
      users: null,
      usersBusy: false,
      usersError: '',
      usersRequest: 0,
      assigneeAnchor: null
    };
  },
  computed: {
    contextKey() {
      return [
        this.ticket,
        this.project,
        this.searchType,
        this.tabId,
        this.scope
      ];
    },
    dirty() {
      return JSON.stringify(this.configuration()) !== this.baseline;
    },
    selectedUsers() {
      return (this.selected.assigned || []).filter(
        (value) => value !== '__current_login__'
      );
    },
    chips() {
      return Object.entries(this.selected).flatMap(([key, values]) => {
        const group = this.groups.find((row) => row.key === key);
        const groupTitle = group
          ? ['process', 'status', 'assigned'].includes(key)
            ? t(group.title)
            : group.title
          : key;
        return values.map((value) => ({
          key,
          value,
          title:
            groupTitle +
            ': ' +
            (value === '__current_login__'
              ? t('MY TASKS')
              : (key === 'assigned' &&
                  this.users?.find((user) => user.login === value)
                    ?.displayName) ||
                group?.options.find((option) => option.key === value)?.title ||
                value)
        }));
      });
    }
  },
  watch: {
    contextKey() {
      this.request++;
      this.usersRequest++;
      this.busy = this.usersBusy = false;
      this.catalog = null;
      this.users = null;
      this.usersError = '';
      this.$refs.assignees?.close();
      this.error = 'Search context changed. Reopen the editor.';
    }
  },
  beforeUnmount() {
    this.request++;
    this.usersRequest++;
    this.chipObserver?.disconnect();
  },
  methods: {
    t,
    toRaw,
    measureChips() {
      this.chipObserver?.disconnect();
      if (!this.$refs.chips) return;
      this.chipHeight = this.$refs.chips.getBoundingClientRect().height;
      this.chipObserver = new ResizeObserver((entries) => {
        this.chipHeight = entries.at(-1).contentRect.height;
      });
      this.chipObserver.observe(this.$refs.chips);
    },
    command(action) {
      if (action.type === 'copy') {
        this.selected = structuredClone(toRaw(this.selections || {}));
        this.sanitize();
      } else if (action.type === 'clear') this.selected = {};
      else if (action.type === 'showHidden') this.showHidden = action.value;
      else if (action.type === 'move') this.move(action.index, action.delta);
      else if (action.type === 'icon' || action.type === 'iconReset')
        this.groups[action.index].icon =
          action.type === 'icon' ? action.value : '';
      else if (action.type === 'group') {
        this.groups[action.index].enabled = action.value;
        this.sanitize();
      } else if (action.type === 'save') this.apply();
      else if (action.type === 'defaults') this.saveDefaults();
      else if (action.type === 'close') this.close();
    },
    async open(catalog = null) {
      const request = ++this.request;
      this.context = {
        ticket: this.ticket,
        project: this.project,
        type: this.searchType,
        scope: this.scope
      };
      this.error = '';
      this.message = '';
      this.catalog = null;
      this.confirmation = false;
      this.uncertain = false;
      this.$refs.dialog.showModal();
      this.busy = true;
      try {
        const result =
          catalog ||
          (await searchConfiguration(
            'read',
            this.context.ticket,
            this.context.project,
            this.context.type,
            { scope: this.context.scope }
          ));
        if (request !== this.request) return;
        this.catalog = result;
        this.original = structuredClone(
          toRaw(this.layout || this.catalog.configuration)
        );
        this.selected = structuredClone(
          toRaw(this.selections || this.original.defaultSelections || {})
        );
        const settings = new Map(
          this.original.groups.map((row) => [row.key, row])
        );
        const standard = new Map(
          this.catalog.configuration.groups.map((row) => [row.key, row])
        );
        const order = [
          ...settings.keys(),
          ...this.catalog.groups
            .map((row) => row.key)
            .filter((key) => !settings.has(key))
        ];
        this.groups = order
          .map((key) => {
            const group = this.catalog.groups.find((row) => row.key === key);
            if (
              !group ||
              (!this.canManage && standard.get(key)?.enabled === false)
            )
              return null;
            const config = settings.get(key) || standard.get(key) || {};
            return {
              ...group,
              ...(Object.hasOwn(config, 'icon') ? { icon: config.icon } : {}),
              enabled: config.enabled !== false,
              options: group.options
                .filter(
                  (option) =>
                    this.canManage ||
                    !standard.get(key)?.options ||
                    standard.get(key).options.includes(option.key)
                )
                .map((option) => ({
                  ...option,
                  enabled:
                    !config.options || config.options.includes(option.key)
                }))
            };
          })
          .filter(Boolean);
        this.sanitize();
        this.baseline = JSON.stringify(this.configuration());
        await nextTick();
        this.measureChips();
      } catch (error) {
        if (request === this.request) this.error = error.message;
      } finally {
        if (request === this.request) this.busy = false;
      }
    },
    configuration() {
      const known = new Set(this.groups.map((row) => row.key));
      const groups = this.groups
        .map((row) => {
          const previous =
            this.original.groups?.find((group) => group.key === row.key) || {};
          return {
            ...previous,
            key: row.key,
            enabled: row.enabled,
            ...(Object.hasOwn(row, 'icon') ? { icon: row.icon } : {})
          };
        })
        .concat(
          (this.original.groups || []).filter((row) => !known.has(row.key))
        );
      return {
        groups,
        defaultSelections: structuredClone(toRaw(this.selected))
      };
    },
    sanitize() {
      for (const [key, values] of Object.entries(this.selected)) {
        const group = this.groups.find((row) => row.key === key);
        if (!group) continue; // Preserve selections absent from the current catalog.
        if (key === 'assigned') {
          this.selected[key] = group.enabled
            ? [...new Set(values.filter(Boolean))].sort()
            : [];
          if (!this.selected[key].length) delete this.selected[key];
          continue;
        }
        const allowed = new Set(
          group.options
            .filter((option) => option.enabled)
            .map((option) => option.key)
        );
        this.selected[key] = group.enabled
          ? values.filter((value) => allowed.has(value))
          : [];
        if (!this.selected[key].length) delete this.selected[key];
      }
    },
    async openUsers(event) {
      if (event?.currentTarget) this.assigneeAnchor = event.currentTarget;
      this.$refs.assignees.open = true;
      if (this.users || this.usersBusy) return;
      const request = ++this.usersRequest;
      this.usersBusy = true;
      this.usersError = '';
      try {
        const result = await userProfile(
          'read',
          this.context?.ticket || this.ticket,
          this.context?.project || this.project,
          { login: this.login }
        );
        if (request === this.usersRequest) this.users = result.users;
      } catch (error) {
        if (request === this.usersRequest) this.usersError = error.message;
      } finally {
        if (request === this.usersRequest) this.usersBusy = false;
      }
    },
    setUsers(values) {
      const selected = [...values];
      if ((this.selected.assigned || []).includes('__current_login__'))
        selected.push('__current_login__');
      if (selected.length) this.selected.assigned = selected.sort();
      else delete this.selected.assigned;
    },
    toggle(group, value) {
      const values = new Set(this.selected[group.key] || []);
      if (values.has(value)) values.delete(value);
      else values.add(value);
      if (values.size) this.selected[group.key] = [...values].sort();
      else delete this.selected[group.key];
    },
    remove(key, value) {
      this.selected[key] = this.selected[key].filter((item) => item !== value);
      if (!this.selected[key].length) delete this.selected[key];
    },
    move(index, delta) {
      this.groups.splice(index + delta, 0, this.groups.splice(index, 1)[0]);
    },
    apply() {
      if (!this.catalog || this.busy || this.uncertain) return;
      this.sanitize();
      this.$emit('apply', this.configuration());
      this.baseline = JSON.stringify(this.configuration());
      this.message = 'Quick filters saved for this tab';
    },
    async saveDefaults() {
      if (!this.canManage || !this.catalog || this.busy || this.uncertain)
        return;
      const request = this.request;
      this.busy = true;
      this.error = '';
      this.message = '';
      this.sanitize();
      try {
        const catalog = await searchConfiguration(
          'quick-save',
          this.context.ticket,
          this.context.project,
          this.context.type,
          {
            scope: this.context.scope,
            revision: this.catalog.revision,
            configuration: this.configuration()
          }
        );
        if (request !== this.request) return;
        this.catalog = catalog;
        this.original = structuredClone(toRaw(this.catalog.configuration));
        this.baseline = JSON.stringify(this.configuration());
        this.$emit('changed', this.catalog);
        this.message = 'Quick-filter defaults saved on server';
      } catch (error) {
        if (request === this.request) {
          this.error = error.message;
          this.uncertain = !error.status || error.status >= 500;
        }
      } finally {
        if (request === this.request) this.busy = false;
      }
    },
    close() {
      if (this.busy) return;
      if (this.dirty || this.uncertain) this.confirmation = true;
      else this.$refs.dialog.close();
    }
  }
};
</script>

<template>
  <dialog
    v-window="{ kind: 'quick_filter_editor' }"
    ref="dialog"
    class="record-dialog quick-filter-editor-dialog"
    :aria-label="t('Quick filters')"
    @cancel.prevent="close"
  >
    <section
      class="search-library-shell"
      :aria-busy="busy"
      :style="{
        '--search-editor-inset': editor.inset + 'px',
        '--search-editor-gap': editor.gap + 'px',
        '--search-group-gap': editor.groupGap + 'px'
      }"
    >
      <header>
        <div>
          <h2>{{ t('Quick filters') }}</h2>
          <p class="muted">{{ project }} · {{ searchType }}</p>
        </div>
        <AppButton label="Close" icon="close" :disabled="busy" @click="close" />
      </header>
      <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
      <p v-if="message" class="notice" role="status">{{ t(message) }}</p>
      <p v-if="uncertain" class="notice">
        {{ t('The save result is unknown. Reload before trying again.') }}
      </p>
      <div v-if="confirmation" class="notice" role="alert">
        <p>{{ t('Discard unsaved filter changes?') }}</p>
        <AppButton
          label="Keep editing"
          @click="confirmation = false"
        /><AppButton
          label="Discard changes"
          destructive
          @click="
            $refs.dialog.close();
            confirmation = false;
          "
        />
      </div>
      <div v-if="catalog" class="search-library-conditions">
        <section class="configuration-group quick-filter-selection-group">
          <SearchEditorPart
            part="selection"
            :model="{
              count: chips.length,
              chipHeight,
              busy,
              canEdit: !uncertain
            }"
            @event="command"
          >
            <template #chips
              ><div
                ref="chips"
                class="quick-filter-chips"
                @vue:mounted="measureChips"
              >
                <QuickFilterChip
                  v-for="chip in chips"
                  :key="chip.key + ':' + chip.value"
                  :text="chip.title"
                  icon="close"
                  checked
                  subtle
                  :disabled="busy || uncertain"
                  @click="remove(chip.key, chip.value)"
                /></div
            ></template>
          </SearchEditorPart>
        </section>
        <div class="quick-filter-available-header">
          <SearchEditorPart
            part="available"
            :model="{ showHidden }"
            @event="command"
          />
        </div>
        <article
          v-for="(group, index) in groups"
          v-show="group.enabled || showHidden"
          :key="group.key"
          class="configuration-group"
        >
          <SearchEditorPart
            part="group"
            :model="{
              ...group,
              title: ['process', 'status', 'assigned'].includes(group.key)
                ? t(group.title)
                : group.title,
              index,
              total: groups.length,
              busy,
              canEdit: !uncertain
            }"
            @event="command"
          />
          <div v-if="group.enabled" class="quick-filter-chips">
            <template v-if="group.key === 'assigned'">
              <QuickFilterChip
                icon="user"
                :text="t('MY TASKS')"
                :checked="(selected.assigned || []).includes('__current_login__')"
                :accent="group.accent"
                subtle
                :disabled="busy || uncertain"
                @click="toggle(group, '__current_login__')"
              />
              <QuickFilterChip
                icon="groups"
                :text="
                  t(selectedUsers.length ? 'USERS' : 'SELECT USERS') +
                  (selectedUsers.length ? ' / ' + selectedUsers.length : '')
                "
                :checked="selectedUsers.length > 0"
                :accent="group.accent"
                subtle
                :disabled="busy || uncertain"
                @click="openUsers($event)"
              />
            </template>
            <template v-else>
              <QuickFilterChip
                v-for="option in group.options"
                :key="option.key"
                :text="
                  option.key === '__current_login__'
                    ? t('MY TASKS')
                    : option.title
                "
                :checked="(selected[group.key] || []).includes(option.key)"
                :accent="option.accent"
                :show-accent-marker="!!option.showAccentMarker"
                subtle
                :disabled="busy || uncertain || !option.enabled"
                @click="toggle(group, option.key)"
              />
            </template>
          </div>
        </article>
        <p v-if="!groups.length" class="muted">
          {{ t('No filters available') }}
        </p>
      </div>
      <div class="quick-filter-editor-footer">
        <SearchEditorPart
          part="footer"
          :model="{
            busy,
            loaded: !!catalog,
            uncertain,
            canSaveDefaults: canManage
          }"
          @event="command"
        />
      </div>
    </section>
    <AppMenu
      ref="assignees"
      class="quick-filter-assignees"
      label="ASSIGNED TO"
      icon="groups"
      external-trigger
      overlay
      :anchor="assigneeAnchor"
      :close-on-select="false"
      :boundary="$refs.dialog"
    >
      <div class="quick-assignee-body">
        <header>
          <strong>{{ t('ASSIGNED TO') }}</strong
          ><QuickFilterChip
            :checked="!(selected.assigned || []).length"
            :text="t('ALL')"
            :disabled="busy || uncertain"
            @click="delete selected.assigned"
          />
        </header>
        <QuickFilterChip
          icon="user"
          :text="t('MY TASKS')"
          :checked="(selected.assigned || []).includes('__current_login__')"
          :disabled="busy || uncertain"
          @click="toggle({ key: 'assigned' }, '__current_login__')"
        />
        <hr />
        <p v-if="usersBusy || usersError" role="status">
          <span>{{ t(usersBusy ? 'Loading data…' : usersError) }}</span
          ><AppButton v-if="usersError" label="Retry" @click="openUsers()" />
        </p>
        <UserPicker
          v-if="users"
          :users="users"
          :current-login="login"
          :model-value="selectedUsers"
          :disabled="busy || uncertain"
          @update:model-value="setUsers"
        />
      </div>
    </AppMenu>
  </dialog>
</template>
<style>
.quick-filter-editor-dialog {
  width: min(860px, calc(100dvw - 32px));
  height: min(720px, calc(100dvh - 32px));
  max-width: none;
  max-height: none;
  padding: 0;
  overflow: hidden;
}
.quick-filter-editor-dialog > .search-library-shell {
  padding: var(--search-editor-inset);
  gap: var(--search-editor-gap);
}
.quick-filter-editor-dialog .search-library-conditions {
  gap: var(--search-editor-gap);
  padding-right: 4px;
  scrollbar-gutter: stable;
}
.quick-filter-editor-dialog .configuration-group {
  display: grid;
  gap: var(--search-group-gap);
  padding: var(--space-md);
  border: 1px solid var(--outline-variant);
  border-radius: var(--section-radius);
  background: var(--surface);
}
.quick-filter-editor-dialog .configuration-group > .quick-filter-chips {
  padding-top: var(--search-group-gap);
  border-top: 1px solid var(--outline-variant);
}
.quick-filter-available-header {
  padding-top: var(--space-xs);
  border-top: 1px solid var(--outline-variant);
}
.quick-filter-editor-footer {
  flex: none;
  padding-top: var(--space-sm);
  border-top: 1px solid var(--outline-variant);
}
</style>
