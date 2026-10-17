<script>
// Handler FilterEditorController / SearchPresetBar / AdvancedSearchView.
import { searchConfiguration } from '../../api.js';
import { toRaw } from 'vue';
import SearchEditorPart from './SearchEditorPart.vue';
import SearchPresetBar from './SearchPresetBar.vue';
import ConditionCards from './ConditionCards.vue';
import { t } from '../../i18n.js';
import AppButton from '../../controls/AppButton.vue';
import AppSelect from '../../controls/AppSelect.vue';
import AppSwitch from '../../controls/AppSwitch.vue';
import AppIcon from '../../controls/AppIcon.vue';
import { copyText } from '../../controls/clipboard.js';
import { savedSearchLink, browserLink } from './links.js';
import { normalizeRecords } from '../../../../src/tactic_stream/shared_ui/features/search/conditions.ui.mjs';

export default {
  components: {
    SearchEditorPart,
    AppButton,
    AppSelect,
    AppSwitch,
    AppIcon,
    SearchPresetBar,
    ConditionCards
  },
  props: {
    ticket: String,
    project: String,
    searchType: String,
    scope: String,
    tabId: String,
    tabTitle: String,
    records: Array,
    preset: String,
    canManage: Boolean,
    keyword: String,
    orderBys: Array,
    selections: Object,
    active: { type: Boolean, default: true }
  },
  emits: ['apply', 'changed', 'rename', 'closed'],
  data() {
    return {
      catalog: null,
      docked: false,
      opened: false,
      drafts: new Map(),
      pendingMutation: false,
      applyingOwner: false,
      filtersExpanded: true,
      needsGeneratedRefresh: false,
      conditionSuggestions: { index: -1, records: [] },
      conditionRequest: 0,
      selected: '',
      rows: [],
      baseline: '',
      busy: false,
      error: '',
      confirmation: '',
      title: '',
      draftTabTitle: '',
      action: '',
      uncertain: false,
      link: '',
      searchKeyword: '',
      orders: [],
      request: 0
    };
  },
  computed: {
    contextKey() {
      return JSON.stringify([
        this.ticket,
        this.project,
        this.searchType,
        this.scope,
        this.tabId
      ]);
    },
    dirty() {
      return this.snapshot() !== this.baseline;
    },
    current() {
      return this.catalog?.presets.find((row) => row.view === this.selected);
    },
    columns() {
      return [
        ...Object.keys(this.catalog?.columns || {}).map((value) => ({
          value,
          label: value
        })),
        { value: '_expression', label: t('Expression') }
      ];
    },
    presetOptions() {
      return [
        { value: '', label: t('Select a saved search') },
        ...(this.catalog?.presets || []).map((row) => ({
          value: row.view,
          label: row.title
        }))
      ];
    }
  },
  watch: {
    contextKey() {
      this.retainDraft();
      this.$refs.nameDialog?.close();
      this.confirmation = '';
      this.clearConditionSuggestions();
      this.request++;
      this.busy = false;
      this.catalog = null;
      if (!this.ticket) {
        this.drafts.clear();
        this.finishClose();
      } else if (this.opened && this.docked && this.active)
        this.open(true, true);
      else if (this.opened)
        this.error = 'Search context changed. Reopen the editor.';
    },
    active(value) {
      if (!value) this.clearConditionSuggestions();
      else if (
        this.opened &&
        this.docked &&
        this.context?.key !== this.contextKey
      )
        this.open(true, true);
    },
    selections() {
      if (!this.opened || !this.docked || this.applyingOwner) return;
      this.needsGeneratedRefresh = true;
      if (this.active) this.load(false, true);
    }
  },
  beforeUnmount() {
    this.clearConditionSuggestions();
    this.request++;
  },
  methods: {
    t,
    retainDraft() {
      if (!this.opened || !this.context?.key) return;
      this.drafts.set(this.context.key, {
        rows: structuredClone(toRaw(this.rows)),
        selected: this.selected,
        baseline: this.baseline,
        searchKeyword: this.searchKeyword,
        orders: [...this.orders],
        draftTabTitle: this.draftTabTitle,
        uncertain: this.uncertain || this.pendingMutation,
        catalog: this.catalog
      });
    },
    clearConditionSuggestions() {
      clearTimeout(this.conditionTimer);
      this.conditionRequest++;
      this.conditionSuggestions = { index: -1, records: [] };
    },
    requestConditionSuggestions(action) {
      this.clearConditionSuggestions();
      if (
        this.busy ||
        this.uncertain ||
        !action.value.trim() ||
        action.column === '_expression'
      )
        return;
      const generation = this.conditionRequest,
        context = this.context;
      this.conditionTimer = setTimeout(async () => {
        try {
          const result = await searchConfiguration(
            'suggestions',
            context.ticket,
            context.project,
            context.type,
            { keyword: action.value, column: action.column },
            true
          );
          if (
            generation === this.conditionRequest &&
            this.rows[action.index]?.column === action.column
          )
            this.conditionSuggestions = {
              index: action.index,
              records: result.records
            };
        } catch (error) {
          if (generation === this.conditionRequest) this.error = error.message;
        }
      }, 180);
    },
    async ensureCatalog(force = false) {
      if (this.busy || this.opened || (this.catalog && !force)) return;
      this.context = {
        ticket: this.ticket,
        project: this.project,
        type: this.searchType,
        scope: this.scope
      };
      await this.load();
    },
    presetValue(view) {
      const row = this.catalog?.presets.find((preset) => preset.view === view);
      if (!row || row.error || this.busy) return null;
      return {
        records: structuredClone(toRaw(row.records || [])),
        preset: row.view,
        keyword: row.keyword || '',
        order_bys: [...(row.order_bys || [])]
      };
    },
    snapshot() {
      return JSON.stringify({
        rows: this.rows,
        keyword: this.searchKeyword,
        orders: this.orders
      });
    },
    conditionEvent(action) {
      if (action.type === 'expand') {
        this.filtersExpanded = !this.filtersExpanded;
        return;
      }
      if (action.type === 'suggest') {
        this.requestConditionSuggestions(action);
        return;
      }
      if (action.type === 'dismiss') {
        this.clearConditionSuggestions();
        return;
      }
      if (action.type !== 'condition' || action.field !== 'value')
        this.clearConditionSuggestions();
      const row = this.rows[action.index];
      if (action.type === 'condition' && row) {
        row[action.field] = action.value;
        if (action.field === 'column')
          row.relation = action.value === '_expression' ? 'in' : '=';
      } else if (action.type === 'operator' && row)
        row.operator = row.operator === 'or' ? 'and' : 'or';
      else if (action.type === 'move') this.move(action.index, action.delta);
      else if (action.type === 'remove') this.remove(action.index);
      else if (action.type === 'detach' && row) {
        delete row.generatedFilterKind;
        delete row.generatedFilterState;
      } else if (action.type === 'add') this.add();
      else if (action.type === 'reset') {
        this.rows = [];
        this.normalize();
      } else if (action.type === 'apply') this.apply();
    },
    presetEvent(action) {
      if (action.type === 'selectPreset') this.select(action.value);
      else if (action.type === 'update') this.save();
      else if (action.type === 'new') this.prompt('new');
      else if (['rename', 'duplicate'].includes(action.type))
        this.prompt(action.type);
      else if (action.type === 'delete') this.confirmation = 'delete';
      else if (action.type === 'refresh') this.refresh();
      else if (action.type === 'copy_link') this.copyLink();
    },
    async open(docked = false, contextChanged = false) {
      if (
        this.opened &&
        !contextChanged &&
        this.docked === docked &&
        this.context?.key === this.contextKey
      ) {
        if (this.needsGeneratedRefresh) await this.load(false, true);
        return;
      }
      if (this.opened) this.retainDraft();
      this.docked = docked;
      this.opened = true;
      this.clearConditionSuggestions();
      this.context = {
        ticket: this.ticket,
        project: this.project,
        type: this.searchType,
        scope: this.scope,
        key: this.contextKey
      };
      this.rows = structuredClone(toRaw(this.records || []));
      this.draftTabTitle = this.tabTitle || '';
      this.searchKeyword = this.keyword || '';
      this.orders = [...(this.orderBys || [])];
      this.baseline = this.snapshot();
      this.selected = this.preset || '';
      this.catalog = null;
      this.error = '';
      this.link = '';
      this.confirmation = '';
      this.action = '';
      this.uncertain = false;
      const retained = this.drafts.get(this.context.key);
      if (retained) Object.assign(this, retained);
      this.pendingMutation = false;
      await this.$nextTick();
      if (!docked) this.$refs.dialog.showModal();
      await this.load();
    },
    async load(reconcile = false, regenerate = false) {
      const request = ++this.request,
        context = this.context;
      this.busy = true;
      this.error = '';
      try {
        const catalog = await searchConfiguration(
          'settings',
          context.ticket,
          context.project,
          context.type,
          { scope: context.scope, selections: this.selections || {} }
        );
        if (request !== this.request) return;
        this.catalog = catalog;
        const dirty = this.dirty;
        if (!dirty || regenerate)
          this.rows = this.rows
            .filter((row) => !row.generatedFilterKind)
            .concat(catalog.generatedRecords || []);
        this.normalize();
        if (!dirty) this.baseline = this.snapshot();
        this.needsGeneratedRefresh = false;
        if (reconcile) this.uncertain = false;
      } catch (error) {
        if (request === this.request) this.error = error.message;
      } finally {
        if (request === this.request) this.busy = false;
      }
    },
    async refresh() {
      if (this.dirty) {
        this.confirmation = 'refresh';
        return;
      }
      await this.load(true);
      if (!this.error) this.selectNow(this.selected);
    },
    select(value) {
      if (this.dirty) {
        this.confirmation = 'select';
        this.pending = value;
        return;
      }
      this.selectNow(value);
    },
    selectNow(value) {
      this.clearConditionSuggestions();
      if (!this.catalog || this.busy || this.uncertain) return;
      const preset = this.catalog.presets.find((row) => row.view === value);
      if (preset?.error) {
        this.error = preset.error;
        return;
      }
      this.selected = value;
      this.rows = structuredClone(toRaw(preset?.records || []));
      this.confirmation = '';
      this.searchKeyword = preset?.keyword || '';
      this.orders = [...(preset?.order_bys || [])];
      this.normalize();
      this.baseline = this.snapshot();
    },
    add() {
      const column =
        'name' in this.catalog.columns
          ? 'name'
          : Object.keys(this.catalog.columns)[0];
      this.rows.push({
        column,
        relation: '=',
        value: '',
        rowEnabled: true,
        operator: this.rows.length ? 'and' : 'begin'
      });
    },
    move(index, delta) {
      const target = index + delta;
      if (
        this.busy ||
        ![-1, 1].includes(delta) ||
        target < 0 ||
        target >= this.rows.length ||
        this.rows[index]?.generatedFilterKind ||
        this.rows[target]?.generatedFilterKind
      )
        return;
      this.rows.splice(index + delta, 0, this.rows.splice(index, 1)[0]);
      this.normalize();
    },
    normalize() {
      this.rows = normalizeRecords(
        this.rows,
        this.columns.filter((column) => column.value !== '_expression')
      );
    },
    remove(index) {
      this.rows.splice(index, 1);
      this.normalize();
    },
    relations(row) {
      return row.column === '_expression'
        ? [
            { value: 'in', label: 'Have' },
            { value: 'not in', label: 'Do not have' },
            { value: 'match', label: 'Match (slow)' },
            { value: 'do not match', label: 'Do not match (slow)' }
          ]
        : this.catalog.relations;
    },
    prompt(action) {
      this.action = action;
      this.title =
        action === 'rename'
          ? this.current.title
          : action === 'duplicate'
            ? this.current.title + ' copy'
            : '';
      this.$refs.nameDialog.showModal();
      this.$nextTick(() => this.$refs.namePart.focusControl('presetNameField'));
    },
    async save(action = 'update') {
      if (
        !this.catalog ||
        this.busy ||
        this.uncertain ||
        !this.canManage ||
        (['update', 'rename', 'duplicate'].includes(action) && !this.current)
      )
        return;
      const request = this.request;
      this.busy = true;
      this.pendingMutation = true;
      this.error = '';
      const title = action === 'update' ? this.current.title : this.title;
      const code = ['update', 'rename'].includes(action)
        ? this.current.code
        : undefined;
      try {
        const result = await searchConfiguration(
          'save',
          this.context.ticket,
          this.context.project,
          this.context.type,
          {
            scope:
              action === 'new' || action === 'duplicate'
                ? this.context.scope
                : this.context.type,
            revision: this.catalog.revision,
            code,
            title,
            records: this.executableRows(),
            keyword: this.searchKeyword,
            order_bys: this.orders
          }
        );
        if (request !== this.request) return;
        this.catalog = result;
        this.baseline = this.snapshot();
        this.selected = code
          ? result.presets.find((row) => row.code === code)?.view || ''
          : result.presets.find((row) => row.title === title)?.view || '';
        this.$refs.nameDialog.close();
        this.$emit('changed', result);
      } catch (error) {
        if (request === this.request) {
          this.error = error.message;
          this.uncertain = !error.status || error.status >= 500;
        }
      } finally {
        if (request === this.request) {
          this.busy = false;
          this.pendingMutation = false;
        }
      }
    },
    async removePreset() {
      if (!this.current || this.busy || this.uncertain || !this.canManage)
        return;
      const request = this.request;
      this.busy = true;
      this.pendingMutation = true;
      this.error = '';
      this.confirmation = '';
      try {
        const catalog = await searchConfiguration(
          'delete',
          this.context.ticket,
          this.context.project,
          this.context.type,
          {
            scope: this.context.scope,
            code: this.current.code,
            revision: this.catalog.revision
          }
        );
        if (request !== this.request) return;
        this.catalog = catalog;
        this.selected = '';
        this.$emit('changed', this.catalog);
      } catch (error) {
        if (request === this.request) {
          this.error = error.message;
          this.uncertain = !error.status || error.status >= 500;
        }
      } finally {
        if (request === this.request) {
          this.busy = false;
          this.pendingMutation = false;
        }
      }
    },
    async copyLink() {
      const link = new URL(
        browserLink(
          savedSearchLink(
            this.context.project,
            this.context.type,
            this.selected
          )
        ),
        location.origin
      ).href;
      try {
        await copyText(link);
        this.link = '';
      } catch {
        this.link = link;
      }
    },
    apply() {
      this.clearConditionSuggestions();
      if (!this.catalog || this.busy || this.uncertain) return;
      this.normalize();
      const selections = Object.assign(
        {},
        ...this.rows
          .filter((row) => row.generatedFilterKind)
          .map((row) => row.generatedFilterState?.selections || {})
      );
      this.applyingOwner = true;
      this.$emit('apply', {
        records: this.executableRows(false),
        selections,
        preset: this.selected,
        keyword: this.searchKeyword,
        order_bys: this.orders
      });
      this.baseline = this.snapshot();
      this.$nextTick(() => {
        this.applyingOwner = false;
      });
      this.retainDraft();
      if (!this.docked) this.finishClose();
    },
    executableRows(includeGenerated = true) {
      return this.rows
        .filter((row) => includeGenerated || !row.generatedFilterKind)
        .map((row) => {
          const { generatedFilterKind, generatedFilterState, ...record } =
            toRaw(row);
          return { ...record };
        });
    },
    finishClose() {
      if (!this.docked) this.$refs.dialog?.close();
      this.opened = false;
      this.$emit('closed', this.docked);
    },
    close() {
      if (this.busy) return;
      if (this.dirty || this.uncertain) this.confirmation = 'close';
      else this.finishClose();
    },
    async confirm() {
      if (this.confirmation === 'delete') this.removePreset();
      else if (this.confirmation === 'select') this.selectNow(this.pending);
      else if (this.confirmation === 'refresh') {
        this.confirmation = '';
        await this.load(true);
        if (!this.error) this.selectNow(this.selected);
      } else {
        this.drafts.delete(this.context?.key);
        this.finishClose();
        this.confirmation = '';
      }
    }
  }
};
</script>

<template>
  <Teleport defer :to="docked ? '#dock-advanced_search' : 'body'">
    <component
      :is="docked ? 'section' : 'dialog'"
      v-window="docked ? false : undefined"
      ref="dialog"
      class="record-dialog search-library-dialog"
      :class="{ 'search-library-docked': docked }"
      :role="docked ? 'region' : undefined"
      :aria-label="t(docked ? 'Advanced Search' : 'Saved searches')"
      @cancel.prevent="close"
    >
      <section class="search-library-shell" :aria-busy="busy">
        <header v-if="!docked">
          <div>
            <h2>{{ t('Saved searches') }}</h2>
            <p class="muted">{{ project }} · {{ searchType }}</p>
          </div>
          <AppButton
            icon-only
            label="Refresh saved searches"
            icon="refresh"
            :disabled="busy"
            @click="refresh"
          /><AppButton
            label="Close"
            icon="close"
            :disabled="busy"
            @click="close"
          />
        </header>
        <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
        <p v-if="uncertain" class="notice">
          {{ t('The save result is unknown. Reload before trying again.') }}
        </p>
        <div v-if="confirmation" class="notice" role="alert">
          <p>
            {{
              t(
                confirmation === 'delete'
                  ? 'Delete the selected saved search?'
                  : 'Discard unsaved filter changes?'
              )
            }}
          </p>
          <AppButton
            label="Keep editing"
            @click="confirmation = ''"
          /><AppButton
            :label="
              confirmation === 'delete' ? 'Delete preset' : 'Discard changes'
            "
            destructive
            @click="confirm"
          />
        </div>
        <template v-if="catalog">
          <SearchPresetBar
            :model="{
              presets: catalog.presets,
              selected,
              busy,
              uncertain,
              canManage
            }"
            @event="presetEvent"
          />
          <input
            v-if="link"
            :value="link"
            readonly
            :aria-label="t('Saved search link')"
          />
          <ConditionCards
            :model="{
              rows: rows.map((row) => ({
                ...row,
                generatedTitle: row.generatedFilterState?.translatable
                  ? t(row.generatedFilterState.title)
                  : row.generatedFilterState?.title,
                relations: relations(row)
              })),
              columns,
              suggestions: conditionSuggestions,
              busy: busy || uncertain,
              expanded: filtersExpanded,
              active: !docked || active,
              reorder: true
            }"
            @event="conditionEvent"
          />
          <SearchEditorPart
            v-if="tabId"
            part="tabName"
            :model="{ title: draftTabTitle, busy: busy || !catalog }"
            @event="
              (action) => {
                if (action.type === 'tabName') draftTabTitle = action.value;
                else if (action.type === 'rename' && catalog)
                  $emit('rename', action.value);
              }
            "
          />
          <footer v-if="!docked">
            <AppButton
              label="Apply filters"
              icon="search"
              highlighted
              :disabled="busy || uncertain"
              @click="apply"
            /><AppButton label="Cancel" :disabled="busy" @click="close" />
          </footer>
        </template>
      </section>
    </component>
  </Teleport>
  <dialog
    ref="nameDialog"
    class="record-dialog search-preset-name-dialog"
    :aria-label="
      t(
        action === 'rename'
          ? 'Rename preset'
          : action === 'duplicate'
            ? 'Duplicate preset'
            : 'Save filter preset'
      )
    "
    @cancel.prevent="!busy && $refs.nameDialog.close()"
  >
    <h2>
      {{
        t(
          action === 'rename'
            ? 'Rename preset'
            : action === 'duplicate'
              ? 'Duplicate preset'
              : 'Save filter preset'
        )
      }}
    </h2>
    <SearchEditorPart
      ref="namePart"
      part="presetName"
      :model="{ title, busy, uncertain }"
      @event="
        (event) => {
          if (event.type === 'title') title = event.value;
          else if (event.type === 'save') save(action);
          else if (event.type === 'close') $refs.nameDialog.close();
        }
      "
    />
    <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
  </dialog>
</template>

<style>
.search-preset-name-dialog {
  width: min(390px, calc(100dvw - 32px));
}
.search-library-docked.record-dialog {
  width: 100%;
  max-width: none;
  height: 100%;
  max-height: none;
  margin: 0;
  border: 0;
  border-radius: 0;
  background: var(--surface);
}
.search-library-docked > .search-library-shell {
  padding: 10px;
  gap: 10px;
  overflow: auto;
  scrollbar-gutter: stable;
}
.search-library-docked .search-library-conditions {
  flex: none;
  overflow: visible;
}
</style>
