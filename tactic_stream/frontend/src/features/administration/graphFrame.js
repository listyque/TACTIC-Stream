import { nextTick } from 'vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/administration/workflow/graph_editor.ui.mjs';
import * as State from '../../../../src/tactic_stream/shared_ui/features/administration/workflow/graph_editor.state.mjs';
import { graphXmlText } from './graphXml.js';

// Engine adapter: server requests and native XML remain owned by each editor.
export default {
  data() {
    return {
      ui: State.initial(),
      viewport: { width: 1, height: 1 },
      toolbarSize: 620,
      frameObserver: null
    };
  },
  computed: {
    frameModel() {
      const workflow = this.frameMode === 'workflow',
        document = this.document || {},
        settings = workflow ? this.processSettings || {} : {},
        kind =
          document.searchType === 'sthpw/task'
            ? 'status'
            : this.node?.kind || 'manual',
        columnCatalog = workflow ? {} : { ...this.columnCatalog };
      if (!workflow)
        for (const identity of Object.keys(document.newTypes || {}))
          columnCatalog[identity] = {
            columns: this.edges
              .filter((row) => row.from === identity && row.from_col)
              .map((row) => ({ name: row.from_col, type: '', pending: true }))
          };
      return {
        mode: this.frameMode,
        style: appearance.theme,
        ready: !!document.xml,
        canWrite: this.canWrite,
        canLoad: !!this.ticket,
        busy:
          this.busy || (!workflow && (this.creating || this.deletionActive)),
        dirty: this.dirty,
        uncertain: this.uncertain,
        pendingText: State.pending(this.ui),
        saveAllowed: !workflow || !!document.name?.trim(),
        error: this.error,
        message: '',
        identity: this.identity,
        document,
        catalog: workflow ? this.catalog : [],
        metadata: this.metadata,
        creationSearchType: workflow ? this.creationType : '',
        nodes: this.nodes,
        edges: this.edges,
        selectedNode: this.node?.identity || '',
        selectedNodes: this.selected,
        selectedEdge: this.selectedEdge,
        xml: graphXmlText(this.xml),
        attributes: JSON.stringify(
          this.node?.attributes || this.edge?.attributes || {},
          null,
          2
        ),
        settings: JSON.stringify(settings, null, 2),
        processSettings: settings,
        processKind: kind,
        processProperties: workflow ? this.processProperties || {} : {},
        processDescription:
          document.processDescriptions?.[this.node?.identity] || '',
        processCatalog: this.metadata,
        connection: workflow ? {} : this.connection || {},
        instance: workflow ? '' : this.instance || '',
        instanceLinks: workflow ? [] : this.instanceLinks,
        createColumns: workflow ? false : this.createColumns,
        columnCatalog,
        columnsBusy: !workflow && this.columnsBusy,
        columnsError: workflow ? '' : this.columnsError
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
    frameModels() {
      return UI.models(this.frameModel, this.ui, appearance.language);
    }
  },
  mounted() {
    const toolbar = this.toolbarTarget
      ? document.querySelector(this.toolbarTarget) || this.$el
      : this.$el;
    this.frameObserver = observeFrameSizes((entries) => {
      for (const { target, contentRect: box } of entries) {
        const size = {
          width: Math.max(1, box.width),
          height: Math.max(1, box.height)
        };
        if (target === this.$refs.body) this.viewport = size;
        else if (target === toolbar) this.toolbarSize = size.width;
      }
    });
    this.frameObserver.observe(this.$refs.body);
    this.frameObserver.observe(toolbar);
  },
  beforeUnmount() {
    this.frameObserver?.disconnect();
  },
  methods: {
    rowScene(list, record) {
      return UI.row(
        list,
        record,
        this.frameModel,
        this.ui,
        appearance.language
      );
    },
    graphCommand(command) {
      return this.$refs.frame?.graphCommand('adminGraphCanvas', command);
    },
    insertionPoint() {
      return this.graphCommand({ type: 'point' }) || { x: 40, y: 40 };
    },
    async dispatch(event) {
      const result = State.transition(this.ui, this.frameModel, event);
      this.ui = result.ui;
      for (const command of result.commands) {
        switch (command.type) {
          case 'field':
            this.document[command.field] = command.value;
            break;
          case 'attribute':
            this.setAttribute(command.key, String(command.value));
            break;
          case 'setting':
            this.setSetting(command.section, command.key, command.value);
            break;
          case 'description':
            this.document.processDescriptions[this.node.identity] =
              command.value;
            break;
          case 'selectNodes':
            this.selectMany(command.identities, command.primary);
            break;
          case 'selectEdge':
            this.selectEdge(command.index);
            break;
          case 'clear':
            this.selectNode('');
            break;
          case 'moveNodes':
            this.moveNodes(command.positions);
            break;
          case 'connect':
            this.connect(command.from, command.to);
            break;
          case 'remove':
            this.remove(true);
            break;
          case 'addNode':
            this.nodeName = command.identity;
            this.typeToAdd = command.identity;
            this.nodeKind = command.kind;
            this.addNode(this.insertionPoint());
            if (!this.error) {
              await nextTick();
              this.graphCommand({ type: 'reveal' });
            }
            break;
          case 'layout':
            await this.arrange(command.style);
            await nextTick();
            this.graphCommand({ type: 'reset' });
            break;
          case 'createType':
            await this.createType(this.insertionPoint());
            break;
          case 'deleteType':
            this.openDeletion();
            break;
          case 'nodeWorkflows':
            this.$emit('node-workflows', this.node.identity);
            break;
          case 'createWorkflow':
            await this.open(
              '',
              command.searchType ||
                this.creationType ||
                this.document?.searchType
            );
            break;
          case 'selectPipeline':
            if (command.identity) await this.open(command.identity);
            break;
          case 'taskWorkflow':
            await this.open(this.processProperties.task_pipeline);
            break;
          case 'dependencies':
            this.dependencies();
            break;
          case 'column':
            if (command.value) this.setColumn(command.key, command.value);
            break;
          case 'renameInstance':
            this.renameInstance(command.value);
            break;
          case 'relationship':
            if (command.value === 'many_to_many') this.makeInstance();
            else this.setAttribute('relationship', command.value);
            break;
          case 'createColumns':
            this.setCreateColumns(command.value);
            break;
          case 'reverse':
            this.reverse();
            break;
          case 'restoreDirect':
            this.restoreDirect();
            break;
          case 'refreshColumns':
            await this.loadColumns(true);
            break;
          case 'apply':
            if (command.key === 'xml') {
              this.xmlDraft = command.value;
              this.xmlPending = true;
              this.applyXml();
            } else if (command.key === 'attributes') {
              this.attributesDraft = command.value;
              this.attributesPending = true;
              this.applyAttributes();
            } else if (command.key === 'settings') {
              this.settingsDraft = command.value;
              this.settingsPending = true;
              this.applySettings();
            } else if (command.key === 'script')
              this.setSetting('default', 'script', command.value);
            if (!this.error) this.ui = State.applied(this.ui, command.key);
            break;
          case 'save':
            await this.save(true);
            break;
          case 'reload':
            if (this.frameMode === 'workflow')
              await this.open(
                this.identity,
                this.identity
                  ? ''
                  : this.creationType || this.document?.searchType
              );
            else await this.load();
            break;
          case 'discard':
            this.ui = { ...this.ui, text: {} };
            this.xmlPending =
              this.attributesPending =
              this.settingsPending =
                false;
            if (this.uncertain) {
              if (this.frameMode === 'workflow') await this.open(this.identity);
              else await this.load();
            } else {
              this.document = this.baseline ? JSON.parse(this.baseline) : null;
              this.xmlDraft = this.document?.xml || '';
              this.selectNode('');
              this.error = '';
            }
            break;
          default:
            throw Error('Unsupported graph command: ' + command.type);
        }
        if (!this.error) this.ui = State.completed(this.ui, command);
      }
    }
  }
};
