<script>
import { observeFrameSizes } from '../../frame/resize.js';
import { inject } from 'vue';
import { widgetConfiguration, rpc, resultItems } from '../../api.js';
import { t } from '../../i18n.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/administration/layouts/layout.ui.mjs';
import * as State from '../../../../src/tactic_stream/shared_ui/features/administration/layouts/layout.state.mjs';
import * as Document from '../../../../src/tactic_stream/shared_ui/features/administration/layouts/layout.document.mjs';
import { layoutTree } from '../interface/layoutXml.js';
import FrameView from '../../frame/FrameView.vue';
import LayoutPreview from './LayoutPreview.vue';
import { workspaceAddress } from '../workspace/links.js';

export default {
  components: { FrameView },
  props: {
    ticket: String,
    project: String,
    initialFocus: Object,
    toolbarTarget: String,
    presentationVisible: { type: Boolean, default: true }
  },
  emits: ['saved'],
  setup() {
    return { openHelp: inject('openHelp', null) };
  },
  data() {
    return {
      ui: State.initial(),
      viewport: { width: 1, height: 1 },
      toolbarSize: 620,
      observer: null,
      searchType: '',
      catalog: [],
      view: 'continuous_example',
      configuration: null,
      knownViews: [],
      context: null,
      source: '',
      xml: '',
      baseline: '',
      sampleItems: [],
      preview: null,
      liveInterface: null,
      checked: '',
      diff: '',
      error: '',
      sampleError: '',
      message: '',
      busy: false,
      uncertain: false,
      request: 0,
      previewRequest: 0,
      previewTimer: null,
      previewBusy: false,
      previewError: ''
    };
  },
  computed: {
    navigationParent() {
      return State.navigationParent(this.ui);
    },
    dirty() {
      return (
        this.xml !== this.baseline || State.pending(this.ui) || this.uncertain
      );
    },
    editable() {
      return (
        !!this.configuration &&
        !this.busy &&
        !this.uncertain &&
        this.context?.ticket === this.ticket &&
        this.context?.project === this.project &&
        this.context?.searchType === this.searchType &&
        this.context?.view === this.view
      );
    },
    typeOptions() {
      return this.catalog
        .filter((row) => row.__record_read__?.available !== false)
        .map((row) => ({
          value: row.code,
          label: row.title || row.code
        }));
    },
    parsed() {
      try {
        return { tree: layoutTree(this.xml), error: '' };
      } catch (error) {
        return { tree: null, error: error.message };
      }
    },
    templates() {
      return (this.configuration?.layout_templates || []).map((row) => ({
        ...row,
        tree: layoutTree(row.xml)
      }));
    },
    rawModel() {
      return {
        project: this.project,
        searchTypes: this.typeOptions,
        searchType: this.searchType,
        view: this.view,
        configuration: this.configuration,
        knownViews: this.knownViews,
        source: this.source,
        xml: this.xml,
        tree: this.parsed.tree,
        parseError: this.parsed.error,
        templates: this.templates,
        sampleItems: this.sampleItems,
        sampleError: this.sampleError,
        liveInterface: this.liveInterface,
        preview: this.preview,
        checked: this.checked,
        diff: this.diff,
        error: this.error || this.previewError,
        message: this.message,
        busy: this.busy,
        dirty: this.xml !== this.baseline || this.uncertain,
        uncertain: this.uncertain,
        canWrite:
          !!this.configuration &&
          this.context?.ticket === this.ticket &&
          this.context?.project === this.project &&
          this.context?.searchType === this.searchType &&
          this.context?.view === this.view,
        canLoad: !!this.ticket && !!this.searchType,
        assetBase: location.origin
      };
    },
    frameModel() {
      return UI.model(
        this.rawModel,
        this.ui,
        appearance.language,
        this.viewport.width > 0 ? window.innerWidth : 1000
      );
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
        appearance.language,
        !!this.toolbarTarget
      );
    },
    models() {
      return UI.models(this.frameModel, appearance.language);
    },
    previewRows() {
      return this.sampleItems.map((item) => item.record);
    },
    previewViews() {
      return {
        itemResults: {
          component: LayoutPreview,
          nodeProps: true,
          props: {
            sample: this.frameModel.samplePreview,
            rows: this.previewRows,
            ticket: this.ticket,
            project: this.project,
            searchType: this.searchType,
            layout: this.liveInterface?.table?.item_layout,
            error: this.error || this.previewError || this.sampleError,
            editing: this.ui.page !== 'resolved',
            selectedElement:
              this.ui.page === 'resolved' ? '' : this.ui.selected,
            onGeometry: (value) => this.dispatch({ type: 'geometry', value }),
            onElement: (name) => this.dispatch({ type: 'select', name })
          }
        }
      };
    }
  },
  mounted() {
    this.searchType =
      this.initialFocus?.searchType || this.typeOptions[0]?.value || '';
    this.view = this.initialFocus?.view || 'continuous_example';
    this.loadCatalog();
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
        ? document.querySelector(this.toolbarTarget) || this.$el
        : this.$el
    );
  },
  beforeUnmount() {
    this.observer?.disconnect();
    this.request++;
    clearTimeout(this.previewTimer);
    this.previewRequest++;
    window.removeEventListener('beforeunload', this.beforeUnload);
  },
  watch: {
    rawModel: {
      deep: false,
      handler() {
        const next = State.synchronize(this.ui, this.frameModel);
        if (next !== this.ui) {
          this.ui = next;
          this.revealSelection();
        }
      }
    },
    xml() {
      this.checked = '';
      this.preview = null;
      this.diff = '';
      if (this.xml !== this.baseline) this.message = '';
      this.schedulePreview();
    },
    project() {
      this.contextChanged();
    },
    ticket() {
      this.contextChanged();
    },
    initialFocus: {
      deep: true,
      handler(value) {
        if (!value || !this.canLeave()) return;
        this.searchType = value.searchType || this.searchType;
        this.view = value.view || this.view;
        this.reload();
      }
    }
  },
  methods: {
    t,
    async revealSelection() {
      await this.$nextTick();
      const index = this.models.layoutElements.findIndex(
        (row) => row.name === this.ui.selected
      );
      this.$refs.frame?.focusListRow('layoutElementsList', index, '');
    },
    schedulePreview() {
      clearTimeout(this.previewTimer);
      const generation = ++this.previewRequest;
      this.previewError = '';
      this.previewTimer = setTimeout(async () => {
        if (
          !this.configuration ||
          !this.xml ||
          this.parsed.error ||
          this.uncertain
        )
          return;
        const request = this.request,
          xml = this.xml;
        this.previewBusy = true;
        try {
          const result = await this.call('preview', {
            source_id: this.source === '' ? null : this.source,
            xml,
            revision: this.configuration.revision
          });
          if (generation === this.previewRequest && request === this.request)
            this.preview = this.liveInterface = result.interface;
        } catch (error) {
          if (generation === this.previewRequest && request === this.request)
            this.previewError = error.message;
        } finally {
          if (generation === this.previewRequest) this.previewBusy = false;
        }
      }, 250);
    },
    rowScene(list, record) {
      return UI.row(
        list,
        record,
        this.frameModel,
        this.ui,
        appearance.language
      );
    },
    beforeUnload(event) {
      if (this.dirty || this.busy) {
        event.preventDefault();
        event.returnValue = '';
      }
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
    contextChanged() {
      this.request++;
      this.previewRequest++;
      clearTimeout(this.previewTimer);
      this.busy = false;
      this.catalog = [];
      this.configuration = null;
      this.knownViews = [];
      this.liveInterface = null;
      this.xml = this.baseline = '';
      this.ui = State.initial();
      this.uncertain = false;
      this.loadCatalog();
    },
    async loadCatalog() {
      if (!this.ticket || !this.project) return;
      const request = ++this.request;
      this.catalog = [];
      this.busy = true;
      this.error = '';
      try {
        const result = await widgetConfiguration(
          'catalog',
          this.ticket,
          this.project,
          '',
          ''
        );
        if (request !== this.request) return;
        if (
          !Array.isArray(result.stypes) ||
          result.stypes.some(
            (row) => !row || typeof row.code !== 'string' || !row.code
          )
        )
          throw Error('Invalid Search Type catalog response');
        this.catalog = result.stypes;
        if (!this.typeOptions.some((row) => row.value === this.searchType))
          this.searchType = this.typeOptions[0]?.value || '';
      } catch (error) {
        if (request === this.request) this.error = error.message;
      } finally {
        if (request === this.request) this.busy = false;
      }
      if (request === this.request && !this.error) await this.reload();
    },
    call(action, values = {}) {
      const context = this.context;
      return widgetConfiguration(
        action,
        context.ticket,
        context.project,
        context.searchType,
        context.view,
        values
      );
    },
    async dispatch(event) {
      const result = State.transition(this.ui, this.frameModel, event);
      this.ui = result.ui;
      if (event.type === 'select') {
        await this.revealSelection();
      }
      for (const command of result.commands) {
        switch (command.type) {
          case 'reference':
            this.searchType = command.searchType;
            this.view = command.view;
            await this.reload(undefined, command);
            break;
          case 'xml':
            if (this.editable) this.xml = command.value;
            break;
          case 'context':
            this[command.field] = command.value;
            await this.reload();
            break;
          case 'source':
            this.source = command.value;
            this.selectSource();
            break;
          case 'newView':
            this.view = command.view;
            await this.reload(command.xml);
            break;
          case 'check':
            await this.check();
            break;
          case 'save':
            await this.save();
            break;
          case 'reload':
            await this.reload();
            break;
          case 'discard':
            await this.discard();
            break;
          case 'openView':
            if (this.canLeave())
              window.open(
                workspaceAddress(this.project, this.searchType, this.view),
                '_blank',
                'noopener'
              );
            break;
          case 'help':
            this.openHelp?.();
            break;
          default:
            throw Error('Unsupported layout command: ' + command.type);
        }
        if (!this.error) this.ui = State.completed(this.ui, command);
      }
    },
    async reload(newXml, reference = null) {
      if (!this.ticket || !this.searchType || this.busy) return;
      if (!/^[A-Za-z_][\w.@-]{0,127}$/.test(this.view))
        this.view = 'continuous_example';
      const request = ++this.request;
      if (
        this.context?.project !== this.project ||
        this.context?.searchType !== this.searchType
      )
        this.knownViews = [];
      this.context = {
        ticket: this.ticket,
        project: this.project,
        searchType: this.searchType,
        view: this.view
      };
      this.busy = true;
      this.configuration = null;
      this.liveInterface = null;
      this.error = this.sampleError = '';
      this.sampleItems = [];
      try {
        const result = await this.call('read');
        if (request !== this.request) return;
        if (reference && !(result.layout_views || []).includes(this.view))
          throw Error('Referenced item layout is unavailable');
        if (
          reference?.source != null &&
          reference.source !== '' &&
          !result.sources.some((row) => row.id === reference.source)
        )
          throw Error('The original configuration source is unavailable');
        this.configuration = result;
        this.knownViews = result.layout_views || [];
        this.uncertain = false;
        this.source = reference?.source ?? result.sources[0]?.id ?? '';
        this.selectSource();
        if (typeof newXml === 'string') {
          this.source = '';
          this.baseline = '';
          this.xml = newXml;
        }
        try {
          const context = this.context,
            rows = await rpc(
              'query',
              [
                {
                  ticket: context.ticket,
                  project: context.project,
                  language: 'python'
                },
                context.searchType
              ],
              { limit: 3 }
            );
          if (request !== this.request) return;
          if (rows.length) {
            const items = await resultItems(
              context.ticket,
              context.project,
              context.searchType,
              rows.map((row) => row.__search_key__)
            );
            if (request === this.request) this.sampleItems = items.items;
          }
        } catch (error) {
          if (request === this.request) this.sampleError = error.message;
        }
      } catch (error) {
        if (request === this.request) this.error = error.message;
      } finally {
        if (request === this.request) this.busy = false;
      }
    },
    selectSource() {
      const source = this.configuration?.sources.find(
          (row) => row.id === this.source
        ),
        inherited = this.configuration?.layers.find(
          (row) => row.view === this.view && row.xml.includes('sobject-layout')
        );
      const blank = this.templates.find((row) => row.name === 'blank');
      this.xml = this.baseline =
        source?.xml ||
        inherited?.xml ||
        (blank
          ? Document.serialize(Document.template(blank.tree, this.view))
          : '');
      this.error = '';
      this.checked = '';
      this.preview = null;
      this.diff = '';
      this.message = '';
      this.schedulePreview();
    },
    async check() {
      if (!this.editable) return;
      const request = this.request;
      this.busy = true;
      this.error = '';
      try {
        const result = await this.call('preview', {
          source_id: this.source === '' ? null : this.source,
          xml: this.xml,
          revision: this.configuration.revision
        });
        if (request === this.request) {
          this.preview = this.liveInterface = result.interface;
          this.checked = this.xml;
          this.diff = result.diff;
        }
      } catch (error) {
        if (request === this.request) this.error = error.message;
      } finally {
        if (request === this.request) this.busy = false;
      }
    },
    async save() {
      if (
        !this.editable ||
        !this.dirty ||
        this.checked !== this.xml ||
        State.pending(this.ui)
      )
        return;
      const request = this.request;
      this.busy = true;
      this.error = '';
      try {
        const result = await this.call('save', {
          source_id: this.source === '' ? null : this.source,
          xml: this.xml,
          revision: this.configuration.revision
        });
        if (request !== this.request) return;
        this.configuration = result;
        this.source = result.sources[0]?.id ?? '';
        this.selectSource();
        this.message = 'Layout saved';
        this.$emit('saved', result);
      } catch (error) {
        if (request === this.request) {
          this.uncertain = !error.status || error.status >= 500;
          this.error = this.uncertain
            ? 'The save result is unknown. Refresh before trying again.'
            : error.message;
        }
      } finally {
        if (request === this.request) this.busy = false;
      }
    },
    async discard() {
      if (this.uncertain) await this.reload();
      else if (this.configuration) this.selectSource();
      else this.xml = this.baseline;
    }
  }
};
</script>
<template>
  <section
    class="layout-editor frame-host"
    :aria-label="t('Layout Editor')"
    :aria-busy="busy"
  >
    <Teleport :to="toolbarTarget || 'body'" :disabled="!toolbarTarget"
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
        :views="previewViews"
        @event="dispatch"
      />
      <p v-if="previewError" class="error" role="alert">{{ previewError }}</p>
    </div>
  </section>
</template>
