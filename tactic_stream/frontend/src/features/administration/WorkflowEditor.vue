<script>
import { nextTick, useId } from 'vue';
import { rpc } from '../../api.js';
import { t } from '../../i18n.js';
import AppButton from '../../controls/AppButton.vue';
import AppIcon from '../../controls/AppIcon.vue';
import ProcessRules from './ProcessRules.vue';

function pipelineXml(text) {
  if (/<!DOCTYPE|<!ENTITY/i.test(text))
    throw Error('Document types and XML entities are not supported');
  const xml = new DOMParser().parseFromString(text, 'application/xml');
  if (
    xml.querySelector('parsererror') ||
    xml.documentElement.tagName !== 'pipeline'
  )
    throw Error('The document must have a pipeline root');
  const names = new Set();
  for (const node of [...xml.documentElement.children].filter(
    (node) => node.tagName === 'process'
  )) {
    const name = node.getAttribute('name')?.trim();
    if (!name || names.has(name))
      throw Error('Process names must be non-empty and unique');
    names.add(name);
    if (
      ['xpos', 'ypos'].some(
        (key) => !Number.isFinite(Number(node.getAttribute(key) || 0))
      )
    )
      throw Error('Node positions must be finite');
  }
  return xml;
}

import FrameView from '../../frame/FrameView.vue';
import graphFrame from './graphFrame.js';
import * as FrameState from '../../../../src/tactic_stream/shared_ui/features/administration/workflow/graph_editor.state.mjs';

export default {
  mixins: [graphFrame],
  setup() {
    return { uid: useId() };
  },
  components: { FrameView, AppButton, AppIcon, ProcessRules },
  props: {
    ticket: String,
    project: String,
    inline: Boolean,
    deferInitialLoad: Boolean,
    toolbarTarget: String,
    presentationVisible: { type: Boolean, default: true }
  },
  emits: ['saved'],
  data() {
    return {
      frameMode: 'workflow',
      active: false,
      context: null,
      request: 0,
      busy: false,
      error: '',
      uncertain: false,
      identity: '',
      revision: '',
      document: null,
      baseline: '',
      metadata: {},
      catalog: [],
      canWrite: false,
      selected: [],
      primaryNode: '',
      selectedEdge: -1,
      propertiesWidth: 360,
      propertiesCollapsed: false,
      catalogCollapsed: false,
      catalogWidth: 230,
      page: 'canvas',
      inspectorPage: 'selection',
      nodeName: '',
      nodeKind: 'manual',
      source: '',
      target: '',
      xmlDraft: '',
      attributesDraft: '',
      settingsDraft: '',
      search: '',
      creationType: '',
      xmlPending: false,
      attributesPending: false,
      settingsPending: false,
      compact: window.innerWidth <= 700
    };
  },
  computed: {
    dirty() {
      return (
        this.document !== null &&
        (JSON.stringify(this.document) !== this.baseline ||
          this.xmlPending ||
          this.attributesPending ||
          this.settingsPending ||
          FrameState.pending(this.ui))
      );
    },
    editable() {
      return this.canWrite && !this.busy && !this.uncertain;
    },
    xml() {
      try {
        return this.document ? pipelineXml(this.document.xml) : null;
      } catch {
        return null;
      }
    },
    nodes() {
      if (!this.xml) return [];
      const nodes = [...this.xml.documentElement.children]
        .filter((node) => node.tagName === 'process')
        .map((node, index) => ({
          identity: node.getAttribute('name'),
          label: node.getAttribute('label') || node.getAttribute('name'),
          nodeX: Number(node.getAttribute('xpos') ?? 40 + (index % 3) * 240),
          nodeY: Number(
            node.getAttribute('ypos') ?? 40 + Math.floor(index / 3) * 130
          ),
          color: node.getAttribute('color'),
          kind: node.getAttribute('type') || 'manual',
          attributes: Object.fromEntries(
            [...node.attributes].map((attr) => [attr.name, attr.value])
          )
        }));
      const known = new Set(nodes.map((node) => node.identity));
      for (const edge of this.edges)
        for (const identity of [edge.from, edge.to])
          if (identity && !known.has(identity)) {
            const index = nodes.length;
            nodes.push({
              identity,
              label: identity,
              kind: 'missing',
              referenceOnly: true,
              attributes: { name: identity },
              nodeX: 40 + (index % 3) * 240,
              nodeY: 40 + Math.floor(index / 3) * 130
            });
            known.add(identity);
          }
      return nodes;
    },
    edges() {
      return this.xml
        ? [...this.xml.documentElement.children]
            .filter((node) => node.tagName === 'connect')
            .map((node, edgeIndex) => ({
              ...Object.fromEntries(
                [...node.attributes].map((attr) => [attr.name, attr.value])
              ),
              attributes: Object.fromEntries(
                [...node.attributes].map((attr) => [attr.name, attr.value])
              ),
              edgeIndex,
              label: node.getAttribute('from_attr') || ''
            }))
        : [];
    },
    graph() {
      return {
        center: this.identity || 'draft',
        nodes: this.nodes,
        edges: this.edges
      };
    },
    node() {
      return this.nodes.find(
        (node) =>
          node.identity ===
          (this.selected.includes(this.primaryNode)
            ? this.primaryNode
            : this.selected[0])
      );
    },
    edge() {
      return this.edges[this.selectedEdge];
    },
    processSettings() {
      return this.document?.processSettings?.[this.node?.identity] || {};
    },
    processProperties() {
      return { ...this.node?.attributes, ...this.processSettings.properties };
    },
    options() {
      return this.nodes
        .filter((node) => !node.referenceOnly)
        .map((node) => ({ value: node.identity, label: node.label }));
    },
    groups() {
      const groups = {};
      for (const item of this.catalog.filter((item) =>
        `${item.label} ${item.identity}`
          .toLowerCase()
          .includes(this.search.toLowerCase())
      ))
        (groups[item.searchType] ||= []).push(item);
      groups['sthpw/task'] ||= [];
      if (this.document && !this.identity)
        groups[this.document.searchType] ||= [];
      return Object.entries(groups).map(([identity, pipelines]) => ({
        identity,
        pipelines,
        label:
          identity === 'sthpw/task'
            ? t('Task status workflows')
            : this.metadata.searchTypes?.find(
                (row) => row.identity === identity
              )?.label ||
              identity ||
              t('No Search Type')
      }));
    }
  },
  mounted() {
    window.addEventListener('resize', this.resize);
    window.addEventListener('beforeunload', this.beforeUnload);
    if (this.inline && !this.deferInitialLoad) this.open();
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.resize);
    this.request++;
    window.removeEventListener('beforeunload', this.beforeUnload);
  },
  watch: {
    edge: {
      deep: true,
      handler(value) {
        if (!this.attributesPending && !this.node)
          this.attributesDraft = JSON.stringify(
            value?.attributes || {},
            null,
            2
          );
      }
    },
    processSettings: {
      deep: true,
      handler(value) {
        if (!this.settingsPending)
          this.settingsDraft = JSON.stringify(value, null, 2);
      }
    },
    node: {
      deep: true,
      handler(value) {
        if (!this.attributesPending)
          this.attributesDraft = JSON.stringify(
            value?.attributes || this.edge?.attributes || {},
            null,
            2
          );
      }
    },
    project() {
      if (this.inline) this.open();
      else this.close(true);
    },
    ticket() {
      if (this.inline) this.open();
      else this.close(true);
    }
  },
  methods: {
    t,
    resize() {
      this.compact = window.innerWidth <= 700;
    },
    beforeUnload(event) {
      if (this.active && (this.dirty || this.busy || this.uncertain)) {
        event.preventDefault();
        event.returnValue = '';
      }
    },
    canLeave() {
      return (
        !this.busy &&
        !this.$refs.rules?.active &&
        (!(this.dirty || this.uncertain) ||
          window.confirm(t('Discard unsaved changes?')))
      );
    },
    async call(action, values = {}) {
      const result = await rpc('execute_cmd', [
        {
          ticket: this.context.ticket,
          project: this.context.project,
          language: 'python'
        },
        'tactic.ui.panel.workflow_cmd.WorkflowCmd',
        { action, project_code: this.context.project, ...values }
      ]);
      return result.info;
    },
    accept(result) {
      this.ui = {
        ...this.ui,
        text: {},
        confirmation: '',
        pending: null,
        error: ''
      };
      this.catalog = result.catalog;
      this.metadata = result.metadata;
      this.identity = result.identity || '';
      this.revision = result.revision || '';
      this.document = result.document?.xml ? result.document : null;
      this.canWrite = result.canWrite;
      this.baseline = JSON.stringify(this.document);
      this.uncertain = false;
      this.xmlDraft = this.document?.xml || '';
      this.xmlPending = this.attributesPending = this.settingsPending = false;
      this.selectNode('');
    },
    async openSearchType(searchType) {
      if (this.busy || this.dirty || this.uncertain) return;
      const id = ++this.request;
      this.context = { ticket: this.ticket, project: this.project };
      this.busy = true;
      this.error = '';
      try {
        const result = await this.call('new', { identity: searchType });
        if (id !== this.request) return;
        const match = (result.metadata.pipelines || []).find(
          (row) => row.searchType === searchType
        );
        this.accept(
          match ? await this.call('load', { identity: match.identity }) : result
        );
        if (!match) this.startDraft(searchType);
        this.creationType = searchType;
      } catch (error) {
        if (id === this.request) this.error = error.message;
      } finally {
        if (id === this.request) this.busy = false;
      }
    },
    async open(identity = '', searchType = '') {
      const id = ++this.request;
      this.context = { ticket: this.ticket, project: this.project };
      this.active = true;
      this.busy = true;
      this.error = '';
      this.document = null;
      this.page = 'canvas';
      await nextTick();
      if (!this.inline && !this.$refs.dialog.open)
        this.$refs.dialog.showModal();
      try {
        let result = await this.call(
          searchType ? 'new' : identity ? 'load' : 'list',
          { identity: searchType || identity }
        );
        if (id !== this.request) return;
        if (!identity && !searchType && result.catalog.length)
          result = await this.call('load', {
            identity: result.catalog[0].identity
          });
        if (id !== this.request) return;
        this.accept(result);
        if (searchType) this.startDraft(searchType);
        this.creationType =
          searchType ||
          this.document?.searchType ||
          this.metadata.searchTypes?.[0]?.identity ||
          '';
      } catch (error) {
        if (id === this.request) this.error = error.message;
      } finally {
        if (id === this.request) this.busy = false;
      }
    },
    close(force = false) {
      if (!force && !this.canLeave()) return;
      this.request++;
      this.active = false;
      if (!this.inline) this.$refs.dialog?.close();
      this.document = null;
    },
    startDraft(searchType) {
      this.identity = this.revision = this.baseline = '';
      this.document = {
        name: '',
        description: '',
        color: '',
        searchType,
        xml: '<pipeline/>',
        processSettings: {},
        processDescriptions: {}
      };
      this.canWrite = true;
      this.metadata.shared = false;
      this.xmlDraft = this.document.xml;
      this.selectNode('');
    },
    async create(searchType) {
      if (this.canLeave() && searchType) await this.open('', searchType);
    },
    async selectPipeline(identity) {
      if (identity && this.canLeave()) await this.open(identity);
    },
    async reload() {
      if (this.canLeave())
        await this.open(
          this.identity,
          this.identity ? '' : this.document?.searchType
        );
    },
    async save(confirmed = false) {
      if (!this.editable || !this.dirty || !this.document.name.trim()) return;
      this.error = '';
      if (this.xmlPending) this.applyXml();
      if (this.attributesPending) this.applyAttributes();
      if (this.settingsPending) this.applySettings();
      if (
        this.xmlPending ||
        this.attributesPending ||
        this.settingsPending ||
        this.error
      )
        return;
      const id = this.request;
      this.busy = true;
      this.error = '';
      try {
        const result = await this.call('save', {
          identity: this.identity,
          expected_revision: this.revision,
          document: this.document
        });
        if (id !== this.request) return;
        this.accept(result);
        this.$emit('saved');
      } catch (error) {
        if (id !== this.request) return;
        this.uncertain = !error.status || error.status >= 500;
        this.error = this.uncertain
          ? 'The save result is unknown. Refresh before trying again.'
          : error.message;
      } finally {
        if (id === this.request) this.busy = false;
      }
    },
    discardBuffers() {
      if (!(this.attributesPending || this.settingsPending)) return true;
      if (!window.confirm(t('Discard unapplied JSON changes?'))) return false;
      this.attributesPending = this.settingsPending = false;
      return true;
    },
    setPage(page) {
      if (this.xmlPending && page !== 'xml') {
        this.applyXml();
        if (this.xmlPending) return;
      }
      this.page = page;
    },
    selectMany(identities, primary) {
      if (this.discardBuffers()) {
        this.inspectorPage = 'selection';
        this.selected = identities;
        this.primaryNode = primary || identities[identities.length - 1] || '';
        this.selectedEdge = -1;
        this.attributesDraft = JSON.stringify(
          this.node?.attributes || {},
          null,
          2
        );
        this.settingsDraft = JSON.stringify(this.processSettings, null, 2);
      }
    },
    selectNode(identity, multiple = false) {
      if (!this.discardBuffers()) return;
      this.inspectorPage = 'selection';
      this.selected = multiple
        ? this.selected.includes(identity)
          ? this.selected.filter((name) => name !== identity)
          : [...this.selected, identity]
        : identity
          ? [identity]
          : [];
      this.primaryNode = this.selected.includes(identity)
        ? identity
        : this.selected[this.selected.length - 1] || '';
      this.selectedEdge = -1;
      this.attributesDraft = JSON.stringify(
        this.node?.attributes || {},
        null,
        2
      );
      this.settingsDraft = JSON.stringify(this.processSettings, null, 2);
    },
    selectEdge(index) {
      if (!this.discardBuffers()) return;
      this.inspectorPage = 'selection';
      this.selected = [];
      this.selectedEdge = index;
      this.attributesDraft = JSON.stringify(
        this.edge?.attributes || {},
        null,
        2
      );
    },
    editXml(operation) {
      if (!this.editable) return;
      try {
        const xml = pipelineXml(this.document.xml);
        operation(xml.documentElement, xml);
        const value = new XMLSerializer().serializeToString(xml);
        pipelineXml(value);
        this.document.xml = this.xmlDraft = value;
        this.error = '';
      } catch (error) {
        this.error = error.message;
      }
    },
    async openNodeTools() {
      if (!this.discardBuffers()) return;
      this.inspectorPage =
        this.inspectorPage === 'add_node' ? 'selection' : 'add_node';
      await nextTick();
      this.$el.querySelector('.workflow-add-node input')?.focus();
    },
    addNode(position) {
      const name = this.nodeName.trim();
      if (
        !name ||
        this.nodes.some((node) => node.identity === name && !node.referenceOnly)
      ) {
        this.error = 'Enter a unique node name';
        return;
      }
      const kind =
        this.document.searchType === 'sthpw/task' ? 'status' : this.nodeKind;
      this.editXml((root, xml) => {
        const node = xml.createElement('process'),
          index = this.nodes.length;
        for (const [key, value] of Object.entries({
          name,
          type: kind,
          xpos: position?.x ?? 40 + (index % 3) * 240,
          ypos: position?.y ?? 40 + Math.floor(index / 3) * 130
        }))
          node.setAttribute(key, String(value));
        root.append(node);
      });
      if (!this.error) {
        this.document.processSettings[name] = { version: 2, node_type: kind };
        this.selectNode(name);
        this.nodeName = '';
      }
    },
    connect(source = this.source, target = this.target) {
      if (
        !this.options.some((node) => node.value === source) ||
        !this.options.some((node) => node.value === target) ||
        source === target
      ) {
        this.error = 'Choose two different nodes';
        return;
      }
      if (
        this.edges.some((edge) => edge.from === source && edge.to === target)
      ) {
        this.error = 'This connection already exists';
        return;
      }
      this.editXml((root, xml) => {
        const edge = xml.createElement('connect');
        edge.setAttribute('from', source);
        edge.setAttribute('to', target);
        root.append(edge);
      });
      if (!this.error) this.selectEdge(this.edges.length - 1);
    },
    moveNodes(positions) {
      this.editXml((root) => {
        for (const position of positions) {
          if (![position.nodeX, position.nodeY].every(Number.isFinite))
            throw Error('Node positions must be finite');
          const node = [...root.children].find(
            (node) =>
              node.tagName === 'process' &&
              node.getAttribute('name') === position.identity
          );
          if (node) {
            node.setAttribute(
              'xpos',
              String(Math.round(position.nodeX * 10) / 10)
            );
            node.setAttribute(
              'ypos',
              String(Math.round(position.nodeY * 10) / 10)
            );
          }
        }
      });
    },
    remove(confirmed = false) {
      if (
        !this.editable ||
        (!this.selected.length && !this.edge) ||
        (!confirmed &&
          !window.confirm(t('Remove the selection from this workflow draft?')))
      )
        return;
      const names = this.selected.filter(
        (name) =>
          !this.nodes.find((node) => node.identity === name)?.referenceOnly
      );
      this.editXml((root) => {
        if (this.edge)
          [...root.children]
            .filter((node) => node.tagName === 'connect')
            [this.selectedEdge].remove();
        else
          for (const node of [...root.children])
            if (
              (node.tagName === 'process' &&
                names.includes(node.getAttribute('name'))) ||
              (node.tagName === 'connect' &&
                [node.getAttribute('from'), node.getAttribute('to')].some(
                  (name) => names.includes(name)
                ))
            )
              node.remove();
      });
      if (!this.error) {
        for (const name of names) {
          delete this.document.processSettings[name];
          delete this.document.processDescriptions[name];
        }
        this.selectNode('');
      }
    },
    setAttribute(key, value) {
      if (this.node?.referenceOnly) return;
      this.editXml((root) => {
        const node = this.node
          ? [...root.children].find(
              (node) =>
                node.tagName === 'process' &&
                node.getAttribute('name') === this.node.identity
            )
          : [...root.children].filter((node) => node.tagName === 'connect')[
              this.selectedEdge
            ];
        node?.setAttribute(key, String(value));
      });
    },
    setSetting(section, key, value) {
      if (!this.editable || !this.node || this.node.referenceOnly) return;
      const settings = (this.document.processSettings[this.node.identity] ||= {
        version: 2
      });
      if (
        section &&
        settings[section] &&
        (typeof settings[section] !== 'object' ||
          Array.isArray(settings[section]))
      ) {
        this.error = 'Process setting sections must be JSON objects';
        return;
      }
      settings.version ||= 2;
      if (section) (settings[section] ||= {})[key] = value;
      else settings[key] = value;
      if (section === 'hierarchy' && key === 'subpipeline')
        (settings.default ||= {}).subpipeline_code = value;
      if (
        this.node.kind === 'status' &&
        section === 'default' &&
        ['mapping', 'direction', 'status'].includes(key)
      ) {
        settings[key] = value;
        if (value)
          for (const other of key === 'mapping'
            ? ['direction', 'status']
            : ['mapping'])
            settings[other] = settings.default[other] = '';
      }
      if (key === 'related_search_type')
        Object.assign(settings[section], {
          related_pipeline_code: '',
          related_process: ''
        });
      if (key === 'related_pipeline_code')
        settings[section].related_process = '';
      if (section === 'properties') {
        if (this.node.kind === 'status' && key === 'color')
          (settings.default ||= {}).color = value;
        this.setAttribute(key, value);
      }
      this.error = '';
    },
    applySettings() {
      if (!this.editable || !this.node || this.node.referenceOnly) return;
      try {
        const value = JSON.parse(this.settingsDraft);
        if (!value || typeof value !== 'object' || Array.isArray(value))
          throw Error('Process settings must be a JSON object');
        this.document.processSettings[this.node.identity] = value;
        this.settingsPending = false;
        this.error = '';
      } catch (error) {
        this.error = error.message;
      }
    },
    applyAttributes() {
      if (!this.editable || this.node?.referenceOnly) return;
      try {
        const attributes = JSON.parse(this.attributesDraft);
        if (
          !attributes ||
          typeof attributes !== 'object' ||
          Array.isArray(attributes) ||
          Object.values(attributes).some((value) => typeof value !== 'string')
        )
          throw Error('Attributes must be a JSON object with string values');
        const name = this.node?.identity,
          nextName = attributes.name;
        const saved =
          this.identity &&
          [
            ...pipelineXml(JSON.parse(this.baseline).xml).documentElement
              .children
          ].some(
            (node) =>
              node.tagName === 'process' && node.getAttribute('name') === name
          );
        if (name && saved && nextName !== name)
          throw Error(
            'Saved process identifiers cannot be renamed. Change the display label instead.'
          );
        if (
          name &&
          attributes.process_code !== this.node.attributes.process_code
        )
          throw Error(
            'Process codes are generated by TACTIC and cannot be edited'
          );
        this.editXml((root) => {
          const node = name
            ? [...root.children].find(
                (node) =>
                  node.tagName === 'process' &&
                  node.getAttribute('name') === name
              )
            : [...root.children].filter((node) => node.tagName === 'connect')[
                this.selectedEdge
              ];
          for (const attr of [...node.attributes])
            node.removeAttribute(attr.name);
          for (const [key, value] of Object.entries(attributes))
            node.setAttribute(key, value);
          if (name && nextName !== name)
            for (const edge of [...root.children].filter(
              (node) => node.tagName === 'connect'
            ))
              for (const key of ['from', 'to'])
                if (edge.getAttribute(key) === name)
                  edge.setAttribute(key, nextName);
        });
        if (!this.error) this.attributesPending = false;
        if (!this.error && name && nextName !== name) {
          for (const key of ['processSettings', 'processDescriptions']) {
            this.document[key][nextName] = this.document[key][name];
            delete this.document[key][name];
          }
          this.selectNode(nextName);
        }
      } catch (error) {
        this.error = error.message;
      }
    },
    applyXml() {
      if (!this.editable) return;
      try {
        pipelineXml(this.xmlDraft);
        this.document.xml = this.xmlDraft;
        this.xmlPending = false;
        this.error = '';
        this.selectNode('');
      } catch (error) {
        this.error = error.message;
      }
    },
    async arrange(style) {
      if (!this.editable) return;
      const id = this.request;
      this.busy = true;
      try {
        const result = await this.call('layout', {
          document: { xml: this.document.xml },
          style
        });
        if (id === this.request) this.document.xml = this.xmlDraft = result.xml;
      } catch (error) {
        if (id === this.request) this.error = error.message;
      } finally {
        if (id === this.request) this.busy = false;
      }
    },
    dependencies() {
      if (this.dirty) {
        this.error = 'Save the workflow before editing process dependencies';
        return;
      }
      const code = this.metadata.processCodes?.[this.node?.identity];
      if (!code) {
        this.error = 'Save the process before editing its dependencies';
        return;
      }
      this.$refs.rules.open(code);
    },
    async rulesSaved() {
      const id = this.request;
      try {
        const result = await this.call('load', { identity: this.identity });
        if (id === this.request) {
          this.accept(result);
          this.$emit('saved');
        }
      } catch (error) {
        if (id === this.request) this.error = error.message;
      }
    }
  }
};
</script>

<template>
  <component
    v-window
    :is="inline ? 'section' : 'dialog'"
    ref="dialog"
    class="workflow-editor frame-host"
    :class="{ 'configuration-dialog': !inline }"
    :aria-label="t('Workflow editor')"
    :aria-busy="busy"
    @cancel.prevent.stop="close()"
    @keydown.esc.stop
  >
    <header v-if="!inline" class="configuration-header">
      <div class="configuration-heading">
        <h1>{{ t('Workflow') }}</h1>
        <p class="muted">{{ context?.project }} · {{ document?.searchType }}</p>
      </div>
      <div
        :id="uid + '-workflow-dialog-actions'"
        class="configuration-actions"
      ></div>
      <AppButton
        label="Close workflow editor"
        icon="close"
        icon-only
        @click="close()"
      />
    </header>
    <Teleport
      defer
      :to="
        inline
          ? toolbarTarget || 'body'
          : '#' + uid + '-workflow-dialog-actions'
      "
      :disabled="inline && !toolbarTarget"
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
        :models="frameModels"
        :describe-row="rowScene"
        @event="dispatch"
      />
    </div>
    <ProcessRules
      ref="rules"
      :ticket="ticket"
      :project="project"
      @saved="rulesSaved"
    />
  </component>
</template>
