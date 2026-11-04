<script>
import { rpc } from '../../api.js';
import { appearance } from '../../appearance.js';
import { observeFrameSizes } from '../../frame/resize.js';
import { randomUuid } from '../../controls/identity.js';
import { projectPath } from '../workspace/links.js';
import FrameView from '../../frame/FrameView.vue';
import CustomLayoutView from '../interface/CustomLayoutView.vue';
import PageEditorTools from './PageEditorTools.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/administration/layouts/page.ui.mjs';
import * as State from '../../../../src/tactic_stream/shared_ui/features/administration/layouts/page.state.mjs';
import * as Reports from '../../../../src/tactic_stream/shared_ui/features/administration/layouts/page.reports.mjs';
import * as Links from '../../../../src/tactic_stream/shared_ui/features/administration/layouts/page.links.mjs';
export default {
  components: { FrameView },
  props: {
    ticket: String,
    project: String,
    searchTypes: Array,
    initialFocus: String,
    toolbarTarget: String,
    presentationVisible: { type: Boolean, default: true }
  },
  emits: ['saved', 'card', 'columns', 'linkedPage'],
  data() {
    return {
      ui: State.initial(),
      contexts: Object.create(null),
      catalog: [],
      document: null,
      baseline: '',
      revision: '',
      compiled: null,
      sourceXml: '',
      canvasBoxes: [],
      checkedDocument: '',
      error: '',
      message: '',
      busy: false,
      uncertain: false,
      canWrite: false,
      sourceTypes: [],
      dataSource: {},
      dataBusy: false,
      dataError: '',
      dataSerial: 0,
      dataEpoch: 0,
      dataInFlight: false,
      pendingData: null,
      viewport: { width: 1, height: 1 },
      toolbarSize: 620,
      observer: null,
      generation: 0,
      previewSerial: 0,
      previewTimer: null,
      previewInFlight: false,
      previewAgain: false,
      pendingSave: null,
      previewKey: '',
      closed: false
    };
  },
  computed: {
    dataScope() {
      return Reports.scope(this.document, this.ui);
    },
    dataKey() {
      return JSON.stringify([
        this.project,
        this.ticket,
        this.dataEpoch,
        this.dataScope
      ]);
    },
    dirty() {
      return (
        (!!this.document && JSON.stringify(this.document) !== this.baseline) ||
        Object.keys(this.ui.text).length > 0 ||
        this.uncertain
      );
    },
    frameModel() {
      return UI.model(
        {
          document: this.document || {},
          project: this.project,
          origin: location.origin,
          catalog: this.catalog,
          dirty: this.dirty,
          busy: this.busy,
          uncertain: this.uncertain,
          canWrite: this.canWrite,
          canLoad: !!this.ticket,
          checked:
            !!this.document &&
            JSON.stringify(this.document) === this.checkedDocument,
          sourceXml: this.sourceXml,
          error: this.error,
          message: this.message,
          dataSource: this.dataSource,
          dataBusy: this.dataBusy,
          dataError: this.dataError,
          searchTypes: this.sourceTypes.length
            ? this.sourceTypes
            : (this.searchTypes || []).map((row) => ({
                value: row.search_type,
                label: row.title || row.search_type
              }))
        },
        this.ui
      );
    },
    scene() {
      return UI.describe(
        this.frameModel,
        this.ui,
        this.viewport.width,
        this.viewport.height,
        appearance.language
      );
    },
    toolbar() {
      return UI.toolbar(
        this.frameModel,
        this.ui,
        this.toolbarSize,
        appearance.language
      );
    },
    models() {
      return UI.models(this.frameModel, this.ui);
    },
    views() {
      return {
        pageTools: {
          component: PageEditorTools,
          nodeProps: true,
          props: {
            onCommand: (command) => this.dispatch(UI.toolEvent(command))
          }
        },
        pagePreview: {
          component: CustomLayoutView,
          nodeProps: true,
          props: {
            model: this.compiled || { layoutNodes: [] },
            ticket: this.ticket,
            project: this.project,
            editing: true,
            guides: !this.ui.preview,
            selectedBlock: this.ui.preview ? '' : this.ui.selected,
            canvasViewport: this.ui.canvas,
            selectedBlocks: this.ui.selection,
            multiSelect: this.ui.multiSelect,
            snap: this.ui.snap,
            onSelection: (keys) => this.dispatch({ type: 'selection', keys }),
            onCanvasBoxes: (boxes) => {
              this.canvasBoxes = boxes;
            },
            onLoaded: (value) => this.sampleLoaded(value),
            onBlock: (key) => this.dispatch({ type: 'select', key }),
            onGeometry: (value, boxes) =>
              this.dispatch({ type: 'geometry', value, boxes })
          }
        }
      };
    }
  },
  mounted() {
    this.observe();
    this.reload();
  },
  beforeUnmount() {
    this.closed = true;
    this.dataSerial++;
    this.pendingData = null;
    this.observer?.disconnect();
    this.generation++;
    this.previewSerial++;
    clearTimeout(this.previewTimer);
  },
  watch: {
    dataKey() {
      this.loadSource();
    },
    project() {
      this.reset();
    },
    ticket() {
      this.reset();
    },
    initialFocus(value) {
      if (value && !this.dirty && !this.busy) this.load(value);
    }
  },
  methods: {
    retainContext() {
      if (!this.document?.name) return;
      this.contexts[this.document.name] = Links.context(this.ui);
      const names = Object.keys(this.contexts);
      if (names.length > 32) delete this.contexts[names[0]];
    },
    async revealSelection() {
      if (this.ui.layersHidden || this.ui.preview || this.ui.source) return;
      await this.$nextTick();
      const index = this.models.pageBlocks.findIndex(
        (row) => row.key === (this.ui.selected || 'page')
      );
      this.$refs.frame?.focusListRow('pageBlocks', index, '');
    },
    keydown(event) {
      if (
        event.isComposing ||
        event.repeat ||
        event.defaultPrevented ||
        event.target.closest('input, textarea, [contenteditable="true"]')
      )
        return;
      const action = State.shortcut(
        event.code?.replace('Key', '') || event.key,
        event.ctrlKey || event.metaKey,
        event.shiftKey,
        event.altKey
      );
      if (action) {
        event.preventDefault();
        this.dispatch(action);
      }
    },
    async loadSource(source = null) {
      const request = ++this.dataSerial;
      const values = source || this.dataScope;
      this.dataError = '';
      if (!values.searchType || this.closed) {
        this.pendingData = null;
        this.dataSource = {};
        this.dataBusy = false;
        return;
      }
      this.dataBusy = true;
      this.pendingData = {
        serial: request,
        generation: this.generation,
        scope: { ticket: this.ticket, project: this.project },
        values
      };
      if (this.dataInFlight) return;
      this.dataInFlight = true;
      try {
        while (this.pendingData && !this.closed) {
          const pending = this.pendingData;
          this.pendingData = null;
          try {
            const result = await this.call(
              'sources',
              {
                search_type: pending.values.searchType,
                record_key: pending.values.recordKey || '',
                edit_view: pending.values.editView || 'edit',
                query: pending.values.query ?? null
              },
              pending.scope
            );
            if (
              !this.closed &&
              pending.serial === this.dataSerial &&
              pending.generation === this.generation
            )
              this.dataSource = result;
          } catch (error) {
            if (
              !this.closed &&
              pending.serial === this.dataSerial &&
              pending.generation === this.generation
            )
              this.dataError = error.message;
          }
        }
      } finally {
        this.dataInFlight = false;
        this.dataBusy = false;
      }
    },
    rowScene(list, row) {
      return UI.row(list, row, this.frameModel, this.ui, appearance.language);
    },
    sampleLoaded(value) {
      if (!this.compiled?.layoutHasDetails) return;
      const key = value.records?.[0]?.__search_key__;
      if (key && (key !== this.previewKey || !this.compiled.layoutDetail)) {
        this.previewKey = key;
        this.schedule();
      }
    },
    observe() {
      this.observer = observeFrameSizes((entries) => {
        for (const entry of entries) {
          if (entry.target === this.$refs.body)
            this.viewport = {
              width: entry.contentRect.width,
              height: entry.contentRect.height
            };
          else this.toolbarSize = entry.contentRect.width;
        }
      });
      this.observer.observe(this.$refs.body);
      this.observer.observe(
        this.toolbarTarget
          ? document.querySelector(this.toolbarTarget)
          : this.$el
      );
    },
    call(
      action,
      values = {},
      scope = { ticket: this.ticket, project: this.project }
    ) {
      return rpc('execute_cmd', [
        { ticket: scope.ticket, project: scope.project },
        'tactic.ui.panel.dashboard_cmd.DashboardCmd',
        { action, project_code: scope.project, ...values }
      ]).then((result) => result.info);
    },
    reset() {
      this.generation++;
      this.previewSerial++;
      clearTimeout(this.previewTimer);
      this.document = null;
      this.compiled = null;
      this.baseline = '';
      this.checkedDocument = '';
      this.catalog = [];
      this.revision = this.error = this.message = '';
      this.ui = State.initial();
      this.contexts = Object.create(null);
      this.pendingSave = null;
      this.previewKey = '';
      this.canWrite = false;
      this.busy = this.uncertain = false;
      if (this.ticket) this.reload();
    },
    canLeave() {
      if (this.busy) return false;
      if (this.dirty || this.uncertain) {
        this.error = '';
        this.dispatch({ type: 'discard' });
        return false;
      }
      return true;
    },
    async reload(force = false) {
      if (this.busy || (this.dirty && !force)) return;
      if (this.uncertain && this.pendingSave) {
        await this.recover();
        return;
      }
      const generation = ++this.generation,
        scope = { ticket: this.ticket, project: this.project };
      this.busy = true;
      this.error = '';
      try {
        const requested = this.document?.name || this.initialFocus || '';
        let state;
        try {
          state = await this.call(
            'read',
            {
              name: requested,
              default_first: !requested,
              include_preview: true
            },
            scope
          );
        } catch (err) {
          if (!requested) throw err;
          state = await this.call(
            'read',
            { default_first: true, include_preview: true },
            scope
          );
        }
        if (generation !== this.generation) return;
        this.catalog = state.dashboards.map((row) => ({
          identity: row.view.slice(10),
          label: row.view.slice(10)
        }));
        this.revision = state.revision;
        this.canWrite = true;
        this.sourceTypes = state.sourceTypes || [];
        this.document = null;
        this.baseline = '';
        this.compiled = null;
        if (state.document) {
          this.document = state.document;
          this.baseline = JSON.stringify(state.document);
          this.compiled = state.model || null;
          this.sourceXml = state.xml || '';
          this.checkedDocument = state.model ? this.baseline : '';
          this.ui = State.initial();
          this.dataEpoch++;
        }
      } catch (e) {
        if (generation === this.generation) this.error = e.message;
      } finally {
        if (generation === this.generation) {
          this.busy = false;
          if (this.document && !this.compiled) this.schedule();
        }
      }
    },
    async load(name) {
      if (this.busy || this.dirty) return;
      this.retainContext();
      const generation = ++this.generation;
      this.busy = true;
      this.error = '';
      try {
        const value = await this.call('read', { name, include_preview: true });
        if (generation !== this.generation) return;
        this.document = value.document;
        this.revision = value.revision;
        this.baseline = JSON.stringify(value.document);
        this.compiled = value.model || null;
        this.sourceXml = value.xml || '';
        this.checkedDocument = value.model ? this.baseline : '';
        this.ui = { ...State.initial(), ...this.contexts[name] };
        this.revealSelection();
        this.sourceTypes = value.sourceTypes || this.sourceTypes;
        this.dataEpoch++;
      } catch (e) {
        if (generation === this.generation) this.error = e.message;
      } finally {
        if (generation === this.generation) {
          this.busy = false;
          if (this.document && !this.compiled) this.schedule();
        }
      }
    },
    schedule() {
      if (this.closed) return;
      clearTimeout(this.previewTimer);
      this.previewSerial++;
      this.previewTimer = setTimeout(() => this.preview(), 250);
    },
    async preview() {
      if (this.closed || !this.document || this.busy || this.uncertain) return;
      if (this.previewInFlight) {
        this.previewAgain = true;
        return;
      }
      const generation = this.generation,
        serial = this.previewSerial,
        document = JSON.stringify(this.document),
        scope = { ticket: this.ticket, project: this.project };
      this.previewInFlight = true;
      try {
        const value = await this.call(
          'preview',
          {
            document: JSON.parse(document),
            expected_revision: this.revision,
            detail_key: this.previewKey
          },
          scope
        );
        if (generation === this.generation && serial === this.previewSerial) {
          this.compiled = value.model;
          this.sourceXml = value.xml;
          this.checkedDocument = document;
          this.error = '';
        }
      } catch (e) {
        if (generation === this.generation && serial === this.previewSerial)
          this.error = e.message;
      } finally {
        this.previewInFlight = false;
        if (this.previewAgain || serial !== this.previewSerial) {
          this.previewAgain = false;
          this.schedule();
        }
      }
    },
    async save() {
      if (
        this.busy ||
        this.uncertain ||
        !this.frameModel.saveAllowed ||
        !this.dirty
      )
        return;
      const payload = {
        document: JSON.parse(JSON.stringify(this.document)),
        expected_revision: this.revision
      };
      if (
        !this.pendingSave ||
        JSON.stringify(this.pendingSave.payload) !== JSON.stringify(payload)
      )
        this.pendingSave = { payload, operation_id: randomUuid() };
      const generation = ++this.generation,
        pending = this.pendingSave;
      this.busy = true;
      this.error = '';
      try {
        const saved = await this.call('apply', {
          ...pending.payload,
          operation_id: pending.operation_id
        });
        if (generation !== this.generation) return;
        if (
          saved.status !== 'applied' ||
          saved.operation_id !== pending.operation_id
        )
          throw Error('Invalid save acknowledgement');
        const state = await this.call('read', { name: this.document.name });
        if (generation !== this.generation) return;
        this.document = state.document;
        this.baseline = this.checkedDocument = JSON.stringify(state.document);
        this.revision = state.revision;
        this.compiled = saved.model;
        this.pendingSave = null;
        this.message = 'Layout saved';
        this.$emit('saved', saved);
      } catch (e) {
        if (generation === this.generation) {
          this.uncertain = !e.status || e.status >= 500;
          this.error = this.uncertain
            ? 'The save result is unknown. Refresh before trying again.'
            : e.message;
        }
      } finally {
        if (generation === this.generation) this.busy = false;
      }
    },
    async recover() {
      const generation = this.generation,
        pending = this.pendingSave,
        scope = { ticket: this.ticket, project: this.project };
      this.busy = true;
      try {
        const result = await this.call(
          'operation',
          {
            operation_id: pending.operation_id
          },
          scope
        );
        if (generation !== this.generation) return;
        if (result.status === 'applied') {
          this.uncertain = false;
          this.busy = false;
          await this.reload(true);
        } else {
          this.uncertain = false;
          this.error =
            'No saved result was found. Save again to retry the same operation.';
        }
      } catch (e) {
        if (generation === this.generation) this.error = e.message;
      } finally {
        if (generation === this.generation) this.busy = false;
      }
    },
    async dispatch(event) {
      if (event.type === 'align') event = { ...event, boxes: this.canvasBoxes };
      const result = State.transition(this.ui, this.frameModel, event);
      this.ui = result.ui;
      if (['selection', 'select', 'togglePanel'].includes(event.type))
        this.revealSelection();
      for (const command of result.commands) {
        switch (command.type) {
          case 'source':
            await this.loadSource(command);
            break;
          case 'document':
            this.document = command.document;
            this.error = this.message = '';
            this.schedule();
            break;
          case 'load':
            await this.load(command.name);
            break;
          case 'create':
            this.document = {
              name: command.name,
              title: command.title,
              blocks: []
            };
            this.baseline = '';
            this.compiled = null;
            this.checkedDocument = '';
            this.schedule();
            break;
          case 'discard':
            this.document = this.baseline ? JSON.parse(this.baseline) : null;
            this.ui.text = {};
            this.error = '';
            this.schedule();
            break;
          case 'save':
            await this.save();
            break;
          case 'reload':
            await this.reload(command.force);
            break;
          case 'check':
            await this.preview();
            break;
          case 'card':
          case 'columns':
          case 'linkedPage':
            this.$emit(command.type, command);
            break;
          case 'open':
            window.open(
              projectPath(this.project) + 'dashboard/' + this.document.name,
              '_blank',
              'noopener'
            );
            break;
          default:
            throw Error('Unsupported page command: ' + command.type);
        }
      }
    }
  }
};
</script>
<template>
  <section
    class="page-layout-editor frame-host"
    :aria-busy="busy"
    @keydown="keydown"
  >
    <Teleport :to="toolbarTarget || 'body'" :disabled="!toolbarTarget"
      ><div
        v-show="presentationVisible"
        class="frame-toolbar-host"
        :style="{ width: toolbarSize + 'px' }"
      >
        <FrameView :scene="toolbar" @event="dispatch" /></div
    ></Teleport>
    <div ref="body" class="frame-host-body">
      <FrameView
        ref="frame"
        :scene="scene"
        :models="models"
        :describe-row="rowScene"
        :views="views"
        @event="dispatch"
      />
    </div>
  </section>
</template>
