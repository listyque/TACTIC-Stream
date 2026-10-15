<script>
import { observeFrameSizes } from '../../frame/resize.js';
import FrameView from '../../frame/FrameView.vue';
import { sidebarRequest } from '../../api.js';
import { t } from '../../i18n.js';
import { nextTick } from 'vue';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/administration/sidebar/sidebar.ui.mjs';
import * as State from '../../../../src/tactic_stream/shared_ui/features/administration/sidebar/sidebar.state.mjs';

export default {
  inheritAttrs: false,
  inject: ['openHelp'],
  components: { FrameView },
  props: {
    ticket: String,
    project: String,
    toolbarTarget: String,
    presentationVisible: { type: Boolean, default: true }
  },
  emits: ['saved', 'configure-search', 'manage-groups'],
  data() {
    return {
      ui: State.initial(),
      viewport: { width: 1, height: 1 },
      toolbarSize: 620,
      observer: null,
      dispatching: false,
      draft: null,
      projectTitle: '',
      context: null,
      baseline: '',
      revision: '',
      library: [],
      searchTypes: [],
      busy: false,
      error: '',
      uncertain: false,
      page: 'item',
      mode: 'simple',
      xml: '',
      xmlBaseline: '',
      request: 0,
      confirmation: '',
      textChanges: {}
    };
  },
  computed: {
    frameModel() {
      return {
        ready: !!this.draft,
        projectTitle: this.projectTitle || this.project,
        canWrite: this.validContext,
        canLoad: !!this.ticket,
        busy: this.busy || this.dispatching,
        dirty: !!this.dirty,
        uncertain: this.uncertain,
        error: this.error,
        selected: this.draft?.selected ?? -1,
        entry: this.entry,
        source: this.draft?.source || 'handler',
        previewGroup: this.draft?.previewGroup || '',
        xml: this.xmlBaseline,
        entries: (this.draft?.entries || [])
          .map((row, index) => ({
            ...row,
            index,
            accent:
              this.searchTypes.find((type) => type.value === row.searchType)
                ?.color ||
              row.accent ||
              ''
          }))
          .filter((row) => row.entryVisible),
        groups: this.draft?.groups || [],
        previewOptions: [
          { value: '', label: t('All groups') },
          ...(this.draft?.groups || []).map((row) => ({
            value: row.code,
            label: row.label
          }))
        ],
        typeOptions: this.typeOptions,
        presetOptions: this.presets,
        resultOptions: this.resultViews.map((row) => ({
          ...row,
          label: t(row.label)
        })),
        widgetOptions: this.widgetTypes.map((row) => ({
          ...row,
          label: t(row.label)
        })),
        layoutOptions: this.layouts,
        shelfOptions: this.shelves
      };
    },
    frameScene() {
      return UI.describe(
        this.frameModel,
        this.ui,
        this.viewport.width,
        this.viewport.height,
        appearance.language
      );
    },
    toolbarScene() {
      return UI.toolbar(
        this.frameModel,
        this.ui,
        this.toolbarSize,
        appearance.language
      );
    },
    models() {
      return {
        entries: this.frameModel.entries,
        groups: this.frameModel.groups.map((row, index) => ({ ...row, index }))
      };
    },
    state() {
      return this.draft
        ? Object.fromEntries(
            [
              'documents',
              'selected',
              'source',
              'collapsed',
              'updates',
              'previewGroup'
            ].map((key) => [key, this.draft[key]])
          )
        : null;
    },
    dirty() {
      return (
        this.uncertain ||
        (this.draft &&
          (State.pending(this.ui) ||
            Object.keys(this.textChanges).length ||
            JSON.stringify([this.draft.documents, this.draft.updates]) !==
              this.baseline ||
            this.xml !== this.xmlBaseline))
      );
    },
    entry() {
      return this.draft?.entries[this.draft.selected] || {};
    },
    validContext() {
      return (
        this.context?.ticket === this.ticket &&
        this.context?.project === this.project
      );
    },
    editable() {
      return !!this.draft && this.validContext && !this.busy && !this.uncertain;
    },
    typeOptions() {
      return [
        { value: '', label: t('Select Search Type') },
        ...this.searchTypes
      ];
    },
    presets() {
      const type = this.entry.searchType?.split('?')[0] || '';
      const options = this.library
        .filter(
          (row) =>
            row.search_type === type &&
            row.view.startsWith('link_search:') &&
            (row.view.split(':')[2] === type ||
              row.view.split(':')[2]?.startsWith(type + '@'))
        )
        .map((row) => ({ value: row.view, label: row.title || row.view }));
      return this.options(
        options,
        this.entry.searchView,
        'No predefined search'
      );
    },
    layouts() {
      return this.options(
        this.library
          .filter((row) => row.category === 'workspace_layout')
          .map((row) => ({ value: row.view, label: row.title || row.view })),
        this.entry.layoutPreset,
        'Do not change workspace layout'
      );
    },
    shelves() {
      return this.options(
        this.library
          .filter((row) => row.category === 'script_shelf')
          .map((row) => ({ value: row.view, label: row.title || row.view })),
        this.entry.scriptShelf,
        'Project default shelf'
      );
    },
    resultViews() {
      return [
        ['continious', 'Continuous tree'],
        ['tiles', 'Cards'],
        ['table', 'Table'],
        ['compact', 'Compact rows'],
        ['splitted_vertical', 'Versions on the right'],
        ['splitted_horizontal', 'Versions at the bottom']
      ].map(([value, label]) => ({ value, label }));
    },
    widgetTypes() {
      return [
        ['view_panel', 'Layout with Search'],
        ['custom_layout', 'Custom Layout'],
        ['edit_layout', 'Edit Layout'],
        ['tile_layout', 'Tile Layout'],
        ['fast_layout', 'Fast Table Layout'],
        ['__class__', 'Class Path']
      ].map(([value, label]) => ({ value, label }));
    }
  },
  watch: {
    project() {
      this.reload();
    },
    ticket() {
      this.request++;
      this.draft = null;
    }
  },
  mounted() {
    this.reload();
    window.addEventListener('beforeunload', this.beforeUnload);
    this.observer = observeFrameSizes((entries) => {
      for (const entry of entries) {
        if (entry.target === this.$refs.body)
          this.viewport = {
            width: Math.max(1, entry.contentRect.width),
            height: Math.max(1, entry.contentRect.height)
          };
        else this.toolbarSize = entry.contentRect.width;
      }
    });
    this.observer.observe(this.$refs.body);
    this.observer.observe(
      this.toolbarTarget
        ? this.$el.closest('dialog') || this.$refs.body.parentElement
        : this.$refs.body.parentElement
    );
  },
  beforeUnmount() {
    this.request++;
    this.observer?.disconnect();
    window.removeEventListener('beforeunload', this.beforeUnload);
  },
  methods: {
    rowScene(node, record) {
      return UI.row(
        node,
        record,
        this.frameModel,
        this.ui,
        appearance.language
      );
    },
    async applyFrameText() {
      this.textChanges = { ...this.ui.text };
      this.xml = this.ui.xml === null ? this.xmlBaseline : this.ui.xml;
      if (!(await this.applyXml())) return false;
      this.ui = State.transition(this.ui, this.frameModel, {
        type: 'applied'
      }).ui;
      return true;
    },
    async dispatch(event) {
      if (this.dispatching) return;
      const result = State.transition(this.ui, this.frameModel, event);
      this.dispatching = true;
      try {
        for (const command of result.commands) {
          if (
            !['reload', 'discard', 'help'].includes(command.type) &&
            !(await this.applyFrameText())
          )
            return;
          switch (command.type) {
            case 'apply':
              break;
            case 'select':
              await this.select(command.index);
              break;
            case 'toggle':
              await this.select(command.index, true);
              break;
            case 'source':
              await this.source(command.value);
              break;
            case 'preview':
              await this.previewGroup(command.value);
              break;
            case 'mode':
              await this.setMode(command.value);
              break;
            case 'back':
              break;
            case 'field':
              await this.field(command.field, command.value);
              break;
            case 'group':
              await this.edit('group', {
                field: command.code,
                value: command.value
              });
              break;
            case 'add':
              await this.add(command.value);
              break;
            case 'move':
              await this.operate('move', { value: command.value });
              break;
            case 'delete':
              await this.operate('delete');
              break;
            case 'search':
              this.$emit('configure-search', this.entry);
              break;
            case 'groups':
              this.$emit('manage-groups');
              break;
            case 'help':
              this.openHelp('sidebar_editor');
              break;
            case 'save':
              await this.save();
              break;
            case 'discard':
            case 'reload':
              await this.reload(true);
              break;
            default:
              throw Error('Unsupported Sidebar command: ' + command.type);
          }
          if (this.error && !['reload', 'discard'].includes(command.type))
            return;
          result.ui = State.completed(result.ui, command);
        }
        this.ui = result.ui;
      } finally {
        this.dispatching = false;
      }
    },
    t,
    options(rows, value, empty) {
      return [
        { value: '', label: t(empty) },
        ...rows,
        ...(value && !rows.some((row) => row.value === value)
          ? [{ value, label: value }]
          : [])
      ];
    },
    beforeUnload(event) {
      if (this.dirty || this.busy || this.uncertain) {
        event.preventDefault();
        event.returnValue = '';
      }
    },
    canLeave() {
      if (this.dirty || this.busy || this.uncertain) {
        this.error = 'Save or discard sidebar changes before leaving.';
        return false;
      }
      return true;
    },
    accept(result, loaded = false) {
      this.draft = result;
      this.xml = this.xmlBaseline = result.xml;
      if (loaded) {
        this.projectTitle = result.projectTitle || this.project;
        this.revision = result.revision;
        this.library = result.library;
        this.searchTypes = result.searchTypes;
        this.baseline = JSON.stringify([result.documents, result.updates]);
      }
    },
    async reload(force = false) {
      if (this.busy) return;
      if (!force && (this.dirty || this.uncertain)) {
        this.confirmation = 'reload';
        return;
      }
      const request = ++this.request;
      this.context = { ticket: this.ticket, project: this.project };
      this.busy = true;
      this.error = '';
      this.confirmation = '';
      try {
        const result = await sidebarRequest(
          'read',
          this.context.ticket,
          this.context.project
        );
        if (request !== this.request) return;
        this.accept(result, true);
        this.uncertain = false;
        this.mode = 'simple';
        this.textChanges = {};
        this.ui = State.initial();
      } catch (error) {
        this.error = error.message;
      } finally {
        if (request === this.request) this.busy = false;
      }
    },
    async edit(operation, values = {}, state = this.state) {
      if (!this.editable) return false;
      this.busy = true;
      this.error = '';
      const request = this.request;
      try {
        const result = await sidebarRequest(
          'edit',
          this.context.ticket,
          this.context.project,
          { state, operation, ...values }
        );
        if (request !== this.request) return false;
        this.accept(result);
        return true;
      } catch (error) {
        this.error = error.message;
        return false;
      } finally {
        if (request === this.request) this.busy = false;
      }
    },
    async flushText() {
      for (const [field, value] of Object.entries(this.textChanges)) {
        if (!(await this.edit('field', { field, value }))) return false;
        delete this.textChanges[field];
      }
      return true;
    },
    async applyXml() {
      return (
        (await this.flushText()) &&
        (this.xml === this.xmlBaseline ||
          (await this.edit('xml', { xml: this.xml })))
      );
    },
    async select(index, toggle = false) {
      if (await this.applyXml())
        await this.edit(
          toggle ? 'toggle' : 'select',
          {},
          { ...this.state, selected: index }
        );
    },
    async source(value) {
      if (await this.applyXml())
        await this.edit(
          'select',
          {},
          { ...this.state, source: value, selected: -1 }
        );
    },
    async previewGroup(value) {
      if (await this.applyXml())
        await this.edit('select', {}, { ...this.state, previewGroup: value });
    },
    async setMode(value) {
      if (await this.applyXml()) this.mode = value;
    },
    async field(field, value) {
      if (await this.applyXml()) return this.edit('field', { field, value });
    },
    async operate(operation, values = {}) {
      if (await this.applyXml()) await this.edit(operation, values);
    },
    async add(value) {
      if (await this.applyXml()) await this.edit('add', { value });
    },
    discard() {
      this.confirmation = 'discard';
    },
    async refreshLibrary() {
      const context = this.context,
        request = this.request;
      try {
        const result = await sidebarRequest(
          'read',
          context.ticket,
          context.project
        );
        if (request !== this.request || context !== this.context) return;
        this.library = result.library;
        if (
          !this.dirty &&
          JSON.stringify(result.documents) ===
            JSON.stringify(this.draft.documents)
        )
          this.revision = result.revision;
      } catch (error) {
        this.error = error.message;
      }
    },
    async save() {
      if (!this.editable || !this.dirty || !(await this.applyXml())) return;
      this.busy = true;
      this.error = '';
      const request = this.request;
      try {
        const result = await sidebarRequest(
          'save',
          this.context.ticket,
          this.context.project,
          { state: this.state, revision: this.revision }
        );
        if (request !== this.request) return;
        this.accept(result, true);
        this.$emit('saved', result);
      } catch (error) {
        this.uncertain = !error.status || error.status >= 500;
        this.error = this.uncertain
          ? 'The save result is unknown. Reload sidebar before trying again.'
          : error.message;
      } finally {
        if (request === this.request) this.busy = false;
      }
    }
  }
};
</script>

<template>
  <section v-bind="$attrs" class="sidebar-editor frame-host" :aria-busy="busy">
    <Teleport defer :to="toolbarTarget || 'body'" :disabled="!toolbarTarget"
      ><div
        v-show="presentationVisible"
        class="frame-toolbar-host"
        :style="{ width: toolbarSize + 'px' }"
      >
        <FrameView :scene="toolbarScene" @event="dispatch" /></div
    ></Teleport>
    <div ref="body" class="frame-host-body">
      <FrameView
        ref="frame"
        :scene="frameScene"
        :models="models"
        :describe-row="rowScene"
        @event="dispatch"
      />
    </div>
  </section>
</template>
