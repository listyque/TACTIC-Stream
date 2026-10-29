<script>
import {
  rpc,
  resultItems,
  interfaceDefinition,
  navigationLink
} from '../../api.js';
import { fileBlob } from '../objects/previewFiles.js';
import { nextTick, toRaw } from 'vue';
import { t } from '../../i18n.js';
import { mobile } from '../../mobile.js';
import { groupRecords } from './resultViews.js';
import ResultItem from './ResultItem.vue';
import VirtualCollection from '../../controls/lists/VirtualCollection.vue';
import * as Card from '../../../../src/tactic_stream/shared_ui/features/search/card.ui.mjs';
import * as Composition from '../../../../src/tactic_stream/shared_ui/features/administration/layouts/layout.preview.mjs';
import ProcessVisibility from './ProcessVisibility.vue';
import * as Visibility from '../../../../src/tactic_stream/shared_ui/features/search/visibility.ui.mjs';
import ConfiguredResultItem from '../interface/ConfiguredResultItem.vue';
import ItemLayoutTable from '../interface/ItemLayoutTable.vue';
import MobileResults from './MobileResults.vue';
import AppButton from '../../controls/AppButton.vue';
import BusyIndicator from '../../controls/BusyIndicator.vue';
import AppSelect from '../../controls/AppSelect.vue';
import AppSplitter from '../../controls/AppSplitter.vue';
import AppMenu from '../../controls/AppMenu.vue';
import AppMenuItem from '../../controls/AppMenuItem.vue';
import FilePreview from '../objects/FilePreview.vue';
import NotesPanel from '../objects/NotesPanel.vue';
import ObjectOperations from '../objects/ObjectOperations.vue';
import RecordForm from '../objects/RecordForm.vue';
import ObjectAction from '../objects/ObjectAction.vue';
import ObjectReport from '../objects/ObjectReport.vue';
import RelatedObjects from '../objects/RelatedObjects.vue';
import RelatedObjectsMenu from '../objects/RelatedObjectsMenu.vue';

export default {
  components: {
    RelatedObjectsMenu,
    ObjectReport,
    ProcessVisibility,
    VirtualCollection,
    ConfiguredResultItem,
    ItemLayoutTable,
    MobileResults,
    ResultItem,
    AppButton,
    BusyIndicator,
    AppSelect,
    AppSplitter,
    AppMenu,
    AppMenuItem,
    FilePreview,
    NotesPanel,
    ObjectOperations,
    RecordForm,
    ObjectAction,
    RelatedObjects
  },
  props: {
    itemLayout: Object,
    editing: Boolean,
    selectedElement: String,
    readOnly: Boolean,
    rows: Array,
    ticket: String,
    project: String,
    searchType: String,
    workspaceId: String,
    mode: String,
    groupMode: String,
    selectedKeys: Array,
    state: Object,
    active: Boolean
  },
  inject: {
    openObjectTab: { default: null },
    openTaskManager: { default: null }
  },
  emits: [
    'geometry',
    'element',
    'select',
    'inspect',
    'operate',
    'state',
    'focus',
    'root-scroll',
    'organization'
  ],
  data() {
    return {
      processIgnore: structuredClone(toRaw(this.state?.processIgnore || {})),
      organization: { processes: [], statuses: {} },
      nodes: [],
      busy: false,
      error: '',
      request: 0,
      selectedId: '',
      selectedIds: [...(this.state?.selectedIds || [])],
      selectionAnchor: '',
      cardPath: [],
      closedGroups: { ...this.state?.closedGroups },
      childFilters: { ...this.state?.childFilters },
      versions: [],
      versionBusy: false,
      versionError: '',
      versionHasNext: false,
      versionRequest: 0,
      versionProcess: '',
      moving: false,
      operationNode: null,
      formType: '',
      relatedType: '',
      operations: {},
      detail: null,
      choiceNode: null,
      choiceTasks: false,
      choices: [],
      relationNode: null,
      splitRatio: Math.max(
        20,
        Math.min(80, Number(this.state?.splitRatio) || 55)
      ),
      operationRequest: 0,
      mobilePath: [],
      mobileScroll: { ...this.state?.mobileScroll },
      mobileDirection: 'forward'
    };
  },
  computed: {
    mobile() {
      return mobile.value;
    },
    context() {
      return [this.rows, this.ticket, this.project, this.searchType];
    },
    split() {
      return !this.mobile && this.mode.startsWith('splitted_');
    },
    mobileParent() {
      return this.find(this.mobilePath.at(-1));
    },
    mobileHistoryKey() {
      return this.workspaceId
        ? this.project + ':' + this.workspaceId + ':' + this.searchType
        : '';
    },
    compact() {
      return this.mode === 'compact';
    },
    selectedNode() {
      return this.find(this.selectedId);
    },
    selectedObject() {
      return this.selectedNode?.kind === 'branch'
        ? this.find(this.selectedNode.ownerId)
        : this.selectedNode;
    },
    cardParent() {
      return this.find(this.cardPath.at(-1));
    },
    cardNodes() {
      return this.cardParent?.children || this.nodes;
    },
    groups() {
      const nodes = (
        this.mode === 'tiles' ? this.cardNodes : this.nodes
      ).filter(this.nodeVisible);
      if (this.cardPath.length && this.mode === 'tiles')
        return [{ key: '', label: '', nodes }];
      const byRecord = new Map(nodes.map((node) => [node.record, node]));
      return groupRecords(
        nodes.map((node) => node.record),
        this.groupMode,
        this.nodes,
        this.organization
      ).map((group) => ({
        ...group,
        nodes: group.records.map((record) => byRecord.get(record))
      }));
    },
    versionProcesses() {
      return [
        { value: '', label: 'All processes' },
        ...(this.selectedObject?.branches || [])
          .filter((branch) => branch.kind === 'process')
          .map((branch) => ({ value: branch.process, label: branch.title }))
      ];
    }
  },
  watch: {
    'state.processIgnore': {
      deep: true,
      handler(value) {
        if (JSON.stringify(value || {}) !== JSON.stringify(this.processIgnore))
          this.processIgnore = structuredClone(toRaw(value || {}));
      }
    },
    'state.splitRatio'(value) {
      this.splitRatio = Math.max(20, Math.min(80, Number(value) || 55));
    },
    'state.closedGroups': {
      deep: true,
      handler(value) {
        if (JSON.stringify(value || {}) !== JSON.stringify(this.closedGroups))
          this.closedGroups = { ...value };
      }
    },
    context: {
      immediate: true,
      handler(value, previous) {
        this.request++;
        this.versionRequest++;
        this.operationRequest++;
        if (
          !this.active ||
          !previous ||
          value.slice(1).some((part, index) => part !== previous[index + 1])
        ) {
          this.nodes = [];
          this.organization = { processes: [], statuses: {} };
        }
        this.busy = false;
        this.load();
      }
    },
    active(value) {
      if (value && !this.nodes.length && !this.busy) this.load();
    },
    mobile() {
      this.load();
    },
    splitRatio() {
      this.saveState();
    },
    cardPath: {
      deep: true,
      handler() {
        this.saveState();
      }
    },
    closedGroups: {
      deep: true,
      handler() {
        this.saveState();
      }
    },
    mode(value, old) {
      if (value !== 'tiles' && !mobile.value) this.cardPath = [];
      if (
        value.startsWith('splitted_') &&
        !old?.startsWith('splitted_') &&
        this.selectedNode
      )
        this.loadVersions();
    },
    groupMode(value) {
      if (value !== 'none') this.cardPath = [];
      if (value.startsWith('task_status:')) this.ensureOrganization();
    }
  },
  mounted() {
    this.scrollHost = this.$el.closest('.table-container');
    this.scrollHost?.addEventListener('scroll', this.scrolling, {
      passive: true
    });
    window.addEventListener('popstate', this.mobilePopstate, true);
  },
  beforeUnmount() {
    this.request++;
    this.versionRequest++;
    this.operationRequest++;
    clearTimeout(this.scrollTimer);
    this.scrollHost?.removeEventListener('scroll', this.scrolling);
    window.removeEventListener('popstate', this.mobilePopstate, true);
  },
  methods: {
    ensureOrganization() {
      if (!this.nodes.length && !this.busy) this.load(true);
    },
    openProcessVisibility() {
      this.$refs.processVisibility.open();
    },
    nodeVisible(node) {
      if (node.kind === 'branch')
        return Visibility.branchVisible(
          node.branch,
          this.find(node.ownerId)?.record || {},
          this.processIgnore
        );
      if (
        node.kind === 'snapshot' &&
        node.ownerId &&
        this.find(node.ownerId)?.kind === 'object'
      )
        return Visibility.branchVisible(
          {
            kind: 'process',
            process: (node.record.context || '').split('/')[0]
          },
          this.find(node.ownerId).record,
          this.processIgnore
        );
      return true;
    },
    applyProcessVisibility(ignore) {
      this.processIgnore = ignore;
      this.saveState();
    },
    layoutAction(action, node, event) {
      if (this.readOnly) return;
      if (action === 'tasks' || action === 'notes')
        this.notes(node, action === 'tasks', event);
      else if (action === 'upload') this.quickAction(node, 'save');
      else if (action === 'create') this.createRelated(node);
      else if (action === 'link') this.showRelated(node, node.branch);
      else if (action === 'relations') this.relations(node, event);
      else if (action === 'quickaction') this.quickAction(node, event);
      else if (['inspect', 'operate', 'preview'].includes(action))
        this[action](node, event);
    },
    t,
    scrolling() {
      this.moving = true;
      clearTimeout(this.scrollTimer);
      this.scrollTimer = setTimeout(() => {
        this.moving = false;
      }, 120);
    },
    collectionItems(nodes) {
      return (this.mode === 'tiles' ? nodes : this.visible(nodes)).map(
        (node) => ({
          key: node.id,
          data: node,
          height: Card.layout(
            {
              kind:
                node.kind === 'branch'
                  ? node.branch?.kind === 'relation'
                    ? 'relation'
                    : 'process'
                  : node.kind,
              compact: this.compact,
              tile: this.mode === 'tiles'
            },
            212
          ).height
        })
      );
    },
    configured(node) {
      return Composition.supports(this.itemLayout, node, window.innerWidth);
    },
    async load(force = false) {
      if (!this.active && !force && !this.groupMode.startsWith('task_status:'))
        return;
      const request = ++this.request;
      this.busy = true;
      this.error = '';
      if (!this.rows?.length) {
        this.organization = { processes: [], statuses: {} };
        this.nodes = [];
        this.busy = false;
        return;
      }
      try {
        const result = {
          items: [],
          organization: { processes: [], statuses: Object.create(null) }
        };
        for (let offset = 0; offset < this.rows.length; offset += 500) {
          const batch = await resultItems(
            this.ticket,
            this.project,
            this.searchType,
            this.rows
              .slice(offset, offset + 500)
              .map((row) => row.__search_key__)
          );
          if (request !== this.request) return;
          result.items.push(...batch.items);
          for (const process of batch.organization?.processes || [])
            if (
              !result.organization.processes.some(
                (row) => row.key === process.key
              )
            )
              result.organization.processes.push(process);
          for (const [process, statuses] of Object.entries(
            batch.organization?.statuses || {}
          )) {
            const catalog =
              result.organization.statuses[process] ||
              (result.organization.statuses[process] = []);
            for (const status of statuses)
              if (!catalog.some((row) => row.key === status.key))
                catalog.push(status);
          }
        }
        if (request !== this.request) return;
        const previous = new Map(this.nodes.map((node) => [node.id, node]));
        this.organization = result.organization;
        this.$emit('organization', this.organization);
        this.nodes = result.items.map((item) =>
          this.makeNode(item, null, previous)
        );
        this.busy = false;
        this.selectedId = this.selectedId || this.state?.selectedId || '';
        if (this.mobile) {
          const saved = history.state?.mobileResult;
          await this.restoreMobilePath(
            saved?.key === this.mobileHistoryKey
              ? saved.path
              : this.mobilePath.length
                ? this.mobilePath
                : this.state?.mobilePath || [],
            request
          );
          this.mobileHistory(true);
        } else
          for (const node of this.nodes) {
            await this.restoreExpansion(node);
            if (request !== this.request) return;
          }
        if (!this.cardPath.length && Array.isArray(this.state?.cardPath))
          this.cardPath = this.state.cardPath.filter((id) => this.find(id));
        if (!this.find(this.selectedId)) {
          this.selectedId = '';
          this.versions = [];
          this.versionRequest++;
        }
        if (this.active && this.selectedNode)
          this.$emit('focus', this.selectedNode);
        if (this.split && this.selectedNode) this.loadVersions();
      } catch (error) {
        if (request === this.request) this.error = error.message;
      } finally {
        if (request === this.request) this.busy = false;
      }
    },
    makeNode(item, parent, previous = new Map()) {
      const searchType = item.record.__search_key__.split('?')[0];
      const navigation = this.itemLayout?.navigation?.[searchType];
      const id = (parent?.id || '') + '/' + item.record.__search_key__;
      const old = previous.get(id);
      const ancestors = parent
        ? [
            ...(parent.ancestors || []),
            parent.ownerKey || parent.record?.__search_key__
          ].filter(Boolean)
        : [];
      return {
        ...item,
        accent:
          item.accent ||
          (searchType === 'sthpw/snapshot' ? parent?.accent : ''),
        id,
        searchType,
        ownerId: parent?.id,
        relationship: parent?.branch?.relationship,
        relationParent: parent?.ownerKey,
        relationPath: parent?.branch?.path,
        kind:
          searchType === 'sthpw/snapshot'
            ? 'snapshot'
            : searchType === 'sthpw/file'
              ? 'file'
              : 'object',
        subtitle:
          parent?.branch?.kind === 'relation'
            ? item.record.description || ''
            : item.subtitle,
        info_items:
          parent?.branch?.kind === 'relation'
            ? item.info_items.map((chip) =>
                chip.column === 'category' ||
                chip.column.endsWith('_category_code')
                  ? {
                      ...chip,
                      text: String(item.record[chip.column]),
                      tooltip: String(item.record[chip.column])
                    }
                  : chip
              )
            : item.info_items,
        depth: parent ? parent.depth + 1 : 0,
        ancestors,
        hasChildren:
          (navigation === undefined
            ? item.branches.length > 0
            : item.branches.some(
                (branch) =>
                  branch.kind === 'relation' &&
                  navigation.includes(branch.search_type)
              )) && !ancestors.includes(item.record.__search_key__),
        expanded: old?.expanded || false,
        children: [],
        loaded: false,
        busy: false,
        error: ''
      };
    },
    find(id, nodes = this.nodes) {
      for (const node of nodes) {
        if (node.id === id) return node;
        const child = this.find(id, node.children);
        if (child) return child;
      }
      return null;
    },
    saveState() {
      const collect = (nodes) =>
        nodes.flatMap((node) => [
          ...(node.expanded ? [node.id] : []),
          ...collect(node.children)
        ]);
      const expanded = this.mobile
        ? this.state?.expanded || []
        : collect(this.nodes);
      this.$emit('state', {
        ...this.state,
        processIgnore: structuredClone(toRaw(this.processIgnore)),
        expanded,
        selectedId: this.selectedId,
        selectedIds: [...this.selectedIds],
        splitRatio: Number(this.splitRatio),
        cardPath: [...this.cardPath],
        closedGroups: { ...this.closedGroups },
        childFilters: { ...this.childFilters },
        mobilePath: [...this.mobilePath],
        mobileScroll: { ...this.mobileScroll }
      });
    },
    async restoreExpansion(node) {
      if (!node.expanded && !(this.state?.expanded || []).includes(node.id))
        return;
      await this.expand(node, true, false);
      for (const child of node.children) await this.restoreExpansion(child);
    },
    visible(nodes) {
      return nodes
        .filter(this.nodeVisible)
        .flatMap((node) => [
          node,
          ...(node.expanded ? this.visible(node.children) : [])
        ]);
    },
    async expand(node, value = !node.expanded, save = true) {
      if (!node.hasChildren || node.busy) return;
      node.expanded = value;
      if (!value || node.loaded) {
        if (save) this.saveState();
        return;
      }
      await this.loadChildren(node);
      if (save) this.saveState();
    },
    async loadChildren(node) {
      if (!node || node.loaded || node.busy) return;
      node.error = '';
      if (node.kind === 'file') {
        node.loaded = true;
        return;
      }
      if (node.kind !== 'branch') {
        if (
          node.kind === 'snapshot' &&
          !this.mobile &&
          this.mode === 'continious'
        ) {
          if (!node.branches.length) {
            node.loaded = true;
            return;
          }
          await this.loadBranch(node);
          return;
        }
        if (node.kind === 'object') {
          node.busy = true;
          const request = this.request;
          try {
            const result = await resultItems(
              this.ticket,
              this.project,
              node.searchType,
              [node.record.__search_key__],
              { branch: { kind: 'children' } }
            );
            if (request !== this.request) return;
            Object.assign(node, result.items[0]);
            if (node.relationParent) {
              const item = this.makeNode(
                result.items[0],
                this.find(node.ownerId)
              );
              node.subtitle = item.subtitle;
              node.info_items = item.info_items;
            }
          } catch (error) {
            node.error = error.message;
            node.expanded = false;
            return;
          } finally {
            node.busy = false;
          }
        }
        const ancestorTypes = node.ancestors.map((key) => key.split('?')[0]);
        const navigation = this.itemLayout?.navigation?.[node.searchType];
        const branches = node.branches.filter(
          (branch) =>
            (navigation === undefined ||
              (branch.kind === 'relation' &&
                navigation.includes(branch.search_type))) &&
            (branch.kind !== 'relation' ||
              !ancestorTypes.includes(branch.search_type))
        );
        node.children = branches.map((branch) => ({
          kind: 'branch',
          id: node.id + '/' + branch.key,
          title: branch.title,
          branch,
          depth: node.depth + 1,
          ownerId: node.id,
          ownerKey: node.record.__search_key__,
          searchType: node.searchType,
          accent: branch.accent || node.accent,
          task_count: branch.task_count,
          note_count: branch.note_count,
          ancestors: node.ancestors,
          hasChildren:
            branch.kind === 'relation'
              ? branch.count > 0
              : branch.has_children !== false,
          filterText: this.childFilters[node.id + '/' + branch.key] || '',
          children: [],
          expanded: false,
          busy: false,
          error: '',
          loaded: false
        }));
        if (
          navigation === undefined &&
          (this.mobile || this.mode === 'continious')
        ) {
          const publishAccent =
            node.branches.find((branch) => branch.process === 'publish')
              ?.accent || node.accent;
          node.children.unshift(
            ...(node.direct_snapshots || []).map((item) =>
              this.makeNode({ ...item, accent: publishAccent }, node)
            )
          );
        }
        node.loaded = true;
        if (this.mobile && node.kind === 'snapshot')
          for (const versions of node.children) {
            await this.loadBranch(versions);
            versions.branch.count = versions.children.length;
          }
      } else await this.loadBranch(node);
    },
    async restoreMobilePath(path, request = this.request) {
      const valid = [];
      for (const id of path.slice(0, 64)) {
        if (request !== this.request) return;
        const siblings = valid.length
          ? this.find(valid.at(-1))?.children || []
          : this.nodes;
        const node = siblings.find((node) => node.id === id);
        if (!node || request !== this.request) break;
        valid.push(id);
        await this.loadChildren(node);
      }
      if (request === this.request) {
        this.mobilePath = valid;
        if (this.mobileParent?.kind === 'snapshot')
          await this.loadSnapshotContent(this.mobileParent);
      }
    },
    async loadSnapshotContent(node) {
      if (!node || node.previewCell || node.previewBusy) return;
      const request = this.request;
      node.previewBusy = true;
      node.previewError = '';
      try {
        const target = await navigationLink(
          this.ticket,
          this.project,
          'skey://' + node.record.__search_key__
        );
        if (!target.preview) throw new Error('No preview available');
        if (request === this.request)
          node.previewCell = { ...target.preview, loadFile: fileBlob };
      } catch (error) {
        if (request === this.request) node.previewError = error.message;
      } finally {
        node.previewBusy = false;
      }
    },
    mobileHistory(replace = false, preview = false) {
      if (
        !this.mobile ||
        !this.active ||
        !this.mobileHistoryKey ||
        !this.$el?.getClientRects().length
      )
        return;
      const previous = history.state?.mobileResult;
      history[replace ? 'replaceState' : 'pushState'](
        {
          ...history.state,
          mobileResult: {
            key: this.mobileHistoryKey,
            path: [...this.mobilePath],
            preview,
            depth:
              (previous?.key === this.mobileHistoryKey
                ? previous.depth || 0
                : 0) + (replace ? 0 : 1)
          }
        },
        ''
      );
    },
    async mobileEnter(node) {
      if (this.mobilePath.at(-1) === node.id) return;
      this.mobileHistory(true);
      this.mobileDirection = 'forward';
      this.mobilePath.push(node.id);
      this.selectedId = node.id;
      this.$emit('focus', node);
      this.mobileHistory();
      this.saveState();
      await Promise.all([
        this.loadChildren(node),
        node.kind === 'snapshot'
          ? this.loadSnapshotContent(node)
          : Promise.resolve()
      ]);
      this.saveState();
    },
    mobilePreviewOpened() {
      if (
        history.state?.mobileResult?.key === this.mobileHistoryKey &&
        history.state.mobileResult.preview
      )
        return;
      this.mobileHistory(true);
      this.mobileHistory(false, true);
    },
    mobilePreviewClosed() {
      if (
        this.mobile &&
        history.state?.mobileResult?.key === this.mobileHistoryKey &&
        history.state.mobileResult.preview
      )
        history.back();
    },
    mobileBack() {
      if (!this.mobilePath.length) return;
      if (
        this.mobileHistoryKey &&
        history.state?.mobileResult?.key === this.mobileHistoryKey &&
        history.state.mobileResult.depth > 0
      )
        history.back();
      else {
        this.mobileDirection = 'back';
        this.mobilePath.pop();
        this.mobileHistory(true);
        this.saveState();
      }
    },
    async mobilePopstate(event) {
      if (
        !this.mobile ||
        !this.active ||
        !this.$el?.getClientRects().length ||
        !this.mobileHistoryKey ||
        event.state?.mobileResult?.key !== this.mobileHistoryKey
      )
        return;
      event.stopImmediatePropagation();
      const path = event.state.mobileResult.path;
      if (!event.state.mobileResult.preview)
        for (const preview of [
          this.$refs.preview,
          this.$refs.operations?.$refs.preview
        ]) {
          if (preview?.$refs.dialog?.open) preview.close();
        }
      if (JSON.stringify(path) === JSON.stringify(this.mobilePath)) return;
      if (document.querySelector('dialog:modal')) {
        if (path.length < this.mobilePath.length) history.forward();
        else history.back();
        return;
      }
      this.mobileDirection =
        path.length < this.mobilePath.length ? 'back' : 'forward';
      await this.restoreMobilePath(path);
      if (this.mobileParent) this.$emit('focus', this.mobileParent);
      this.saveState();
    },
    mobileScrolled(key, top) {
      this.mobileScroll[key] = top;
      this.saveState();
    },
    async disclose(node, value = !node.expanded, event = {}) {
      const request = this.request;
      await this.expand(node, value);
      if (event.shiftKey && request === this.request) {
        for (const child of node.children) {
          if (request !== this.request) return;
          await this.disclose(child, value, event);
        }
      }
    },
    async openCard(node, event = {}) {
      if (this.readOnly) return;
      if (node.kind === 'snapshot' || node.kind === 'file')
        await this.quickAction(node, 'open');
      else if (node.hasChildren && !node.busy) {
        await this.expand(node, true);
        this.cardPath.push(node.id);
        this.saveState();
      }
    },
    async doubleClick(node, event) {
      if (this.mobile) return;
      if (this.mode === 'tiles') {
        await this.openCard(node, event);
        return;
      }
      if (this.mode !== 'continious') return;
      if (node.kind === 'snapshot' || node.kind === 'file')
        await this.quickAction(node, 'open');
      else await this.disclose(node, !node.expanded, event);
    },
    newTab(node) {
      if (this.readOnly) return;
      const owner = node.kind === 'branch' ? this.find(node.ownerId) : node;
      this.openObjectTab?.(
        'skey://' + owner.record.__search_key__,
        this.project
      );
    },
    filterChildren(node, text) {
      node.filterText = text;
      this.childFilters[node.id] = text;
      node.hasNext = false;
      this.saveState();
      this.loadBranch(node);
    },
    async loadBranch(node, append = false) {
      const request = this.request;
      const branchRequest = (node.branchRequest =
        (node.branchRequest || 0) + 1);
      node.busy = true;
      node.error = '';
      try {
        const { kind, search_type, path, process } =
          node.branch || node.branches[0];
        const branch = ['process', 'versions'].includes(kind)
          ? { kind, process }
          : { kind, search_type, path };
        const offset = append ? node.nextOffset : 0;
        const result = await resultItems(
          this.ticket,
          this.project,
          node.searchType,
          [node.ownerKey || node.record.__search_key__],
          { branch, offset, query: node.filterText || '' }
        );
        if (request !== this.request || branchRequest !== node.branchRequest)
          return;
        const retained = (node.retainedChildren ||= new Map());
        for (const child of node.children) retained.set(child.id, child);
        const children = result.items
          .filter(
            (item) =>
              !node.ancestors.includes(item.record.__search_key__) &&
              item.record.__search_key__ !== node.ownerKey
          )
          .map((item) => {
            const child = this.makeNode(item, node);
            if (!retained.has(child.id)) retained.set(child.id, child);
            return retained.get(child.id);
          });
        node.children = append ? [...node.children, ...children] : children;
        node.nextOffset = offset + result.items.length;
        node.hasNext = result.has_next;
        node.loaded = true;
      } catch (error) {
        if (request === this.request && branchRequest === node.branchRequest)
          node.error = error.message;
      } finally {
        if (branchRequest === node.branchRequest) node.busy = false;
      }
    },
    async activate(node, event = {}) {
      if (this.mobile && event.type !== 'contextmenu') {
        await this.mobileEnter(node);
        return;
      }
      this.$emit('focus', node);
      const all = this.visible(this.nodes);
      const compatible = (candidate) =>
        candidate.kind === node.kind &&
        candidate.ownerId === node.ownerId &&
        candidate.depth === node.depth &&
        candidate.kind !== 'branch';
      if (node.kind === 'branch') {
        this.selectedIds = [node.id];
        this.selectionAnchor = node.id;
      } else if (
        event.shiftKey &&
        all.some((item) => item.id === this.selectionAnchor && compatible(item))
      ) {
        const bounds = [
          all.findIndex((item) => item.id === this.selectionAnchor),
          all.indexOf(node)
        ].sort((a, b) => a - b);
        const ranged = all
          .slice(Math.max(0, bounds[0]), bounds[1] + 1)
          .filter(compatible)
          .map((item) => item.id);
        this.selectedIds =
          event.ctrlKey || event.metaKey
            ? [...new Set([...this.selectedIds, ...ranged])]
            : ranged.length
              ? ranged
              : [node.id];
      } else if (event.ctrlKey || event.metaKey) {
        const previous = this.selectedIds
          .map((id) => this.find(id))
          .filter(Boolean);
        this.selectedIds = previous.every(compatible)
          ? this.selectedIds.filter((id) => id !== node.id)
          : [];
        if (!previous.some((item) => item.id === node.id))
          this.selectedIds.push(node.id);
        this.selectionAnchor = node.id;
      } else {
        this.selectedIds = [node.id];
        this.selectionAnchor = node.id;
      }
      if (!this.readOnly) {
        this.$emit('select', this.rows, false);
        this.$emit(
          'select',
          this.nodes
            .filter((item) => this.selectedIds.includes(item.id))
            .map((item) => item.record),
          true
        );
      }
      if (node.kind === 'branch') {
        this.selectedId = node.id;
        this.saveState();
        if (this.split) {
          this.versionProcess = node.branch.process || '';
          this.loadVersions();
        }
        if (mobile.value) await this.expand(node, true);
        return;
      }
      this.selectedId = node.id;
      this.saveState();
      if (this.split) {
        this.versionProcess = '';
        this.loadVersions();
      }
    },
    async loadVersions(append = false) {
      const node = this.selectedObject;
      const request = ++this.versionRequest;
      this.versionError = '';
      this.versionBusy = true;
      if (!append) this.versions = [];
      if (!node) {
        this.versionBusy = false;
        return;
      }
      try {
        const branch = this.versionProcess
          ? { kind: 'process', process: this.versionProcess }
          : { kind: 'versions' };
        const result = await resultItems(
          this.ticket,
          this.project,
          node.searchType,
          [node.record.__search_key__],
          { branch, offset: append ? this.versions.length : 0 }
        );
        if (request !== this.versionRequest) return;
        const versions = result.items.map((item) => ({
          ...this.makeNode(item, null),
          hasChildren: false
        }));
        this.versions = append ? [...this.versions, ...versions] : versions;
        this.versionHasNext = result.has_next;
      } catch (error) {
        if (request === this.versionRequest) this.versionError = error.message;
      } finally {
        if (request === this.versionRequest) this.versionBusy = false;
      }
    },
    preview(node) {
      this.$emit('focus', node);
      this.$refs.preview.open(node.record, node.preview);
    },
    async quickAction(node, command) {
      if (this.readOnly) return;
      const request = ++this.operationRequest;
      const owner = node.kind === 'branch' ? this.find(node.ownerId) : node;
      this.formType = owner.searchType;
      try {
        const definition = await interfaceDefinition(
          this.ticket,
          this.project,
          this.formType
        );
        if (request !== this.operationRequest) return;
        this.operations = definition.operations;
        await nextTick();
        if (request === this.operationRequest)
          await this.$refs.operations.quick(owner.record, node, command);
      } catch (error) {
        if (request === this.operationRequest) this.error = error.message;
      }
    },
    async relations(node, event) {
      this.relationNode = node;
      await nextTick();
      this.$refs.relationMenu.openAt(event);
    },
    async notes(node, tasks = false, event = null, choice = null) {
      const owner = node.kind === 'branch' ? this.find(node.ownerId) : node;
      const process = choice?.process || node.branch?.process || 'publish';
      if (this.mode === 'continious' && event && !choice) {
        const processBranches = owner.branches.filter(
          (branch) => branch.kind === 'process'
        );
        const names = [
          ...new Set([
            'publish',
            ...processBranches.map((branch) => branch.process),
            ...owner.tasks.map((task) => task.process),
            ...Object.keys(owner.note_counts || {})
          ])
        ].filter(Boolean);
        const processes =
          node.kind === 'branch'
            ? [node.branch]
            : names.map(
                (process) =>
                  processBranches.find(
                    (branch) => branch.process === process
                  ) || { process, title: process, accent: owner.accent }
              );
        this.choices = processes.flatMap((branch) => {
          const matching = owner.tasks.filter(
            (task) => task.process === branch.process
          );
          const count = tasks
            ? matching.length
            : owner.note_counts?.[branch.process] || 0;
          if (node.kind !== 'branch' && branch.process !== 'publish' && !count)
            return [];
          if (node.kind === 'branch' && matching.length > 1)
            return matching.map((task) => ({
              ...task,
              title: task.context || task.process,
              count: tasks ? 1 : count,
              accent: branch.accent
            }));
          return [
            {
              process: branch.process,
              title: branch.title || branch.process,
              count,
              accent: branch.accent,
              taskSearchKey:
                matching.length === 1 ? matching[0].taskSearchKey : '',
              multipleTasks: matching.length > 1
            }
          ];
        });
        if (this.choices.length > 1) {
          this.choiceNode = node;
          this.choiceTasks = tasks;
          await nextTick();
          this.$refs.processMenu.openAt(event);
          return;
        }
        choice = this.choices[0];
      }
      const chosenProcess = choice?.process || process;
      const ownTasks = owner.tasks.filter(
        (task) => task.process === chosenProcess
      );
      const task =
        owner.tasks.find(
          (task) => task.taskSearchKey === choice?.taskSearchKey
        ) || (ownTasks.length === 1 ? ownTasks[0] : { process: chosenProcess });
      if (tasks && this.mobile)
        this.openTaskManager?.(owner.record, chosenProcess);
      else if (tasks)
        this.$refs.notes.openTask(
          owner.record,
          { process: chosenProcess, tasks: ownTasks },
          task
        );
      else
        this.$refs.notes.open(
          owner.record,
          { process: chosenProcess },
          chosenProcess,
          undefined,
          task.taskSearchKey || ''
        );
    },
    chooseTask(choice, event) {
      event.stopPropagation();
      const owner =
        this.choiceNode.kind === 'branch'
          ? this.find(this.choiceNode.ownerId)
          : this.choiceNode;
      this.choices = owner.tasks
        .filter((task) => task.process === choice.process)
        .map((task) => ({
          ...task,
          title: task.context || task.process,
          count: 1,
          accent: choice.accent
        }));
    },
    async createRelated(node) {
      const request = ++this.operationRequest;
      this.formType = node.branch.search_type;
      try {
        const definition = await interfaceDefinition(
          this.ticket,
          this.project,
          this.formType
        );
        if (request !== this.operationRequest) return;
        this.operations = definition.operations;
        if (!definition.operations?.create)
          throw new Error(
            'This operation or object type is not available yet.'
          );
        this.$nextTick(() =>
          this.$refs.form.open(
            null,
            null,
            node.branch.relationship === 'instance'
              ? {
                  instance: {
                    parent_key: node.ownerKey,
                    path: node.branch.path
                  }
                }
              : { parent_key: node.ownerKey }
          )
        );
      } catch (error) {
        this.error = error.message;
      }
    },
    showRelated(node, branch = null, target = '') {
      const owner = node.kind === 'branch' ? this.find(node.ownerId) : node;
      this.relatedType = owner.searchType;
      this.$nextTick(() =>
        this.$refs.related.open(
          owner.record,
          branch?.search_type || target,
          branch?.kind === 'parent' ? null : branch,
          branch?.kind === 'parent' ? branch : null
        )
      );
    },
    async operate(node, event) {
      if (this.readOnly) return;
      if (
        node.kind === 'branch' &&
        !['process', 'relation'].includes(node.branch.kind)
      )
        return;
      if (
        node.kind !== 'branch' &&
        node.searchType === this.searchType &&
        node.relationship !== 'instance'
      ) {
        this.$emit('operate', node.record, event, node);
        return;
      }
      const request = ++this.operationRequest;
      this.operationNode = node;
      this.formType =
        node.kind === 'branch' && node.branch.kind === 'relation'
          ? node.branch.search_type
          : node.searchType;
      try {
        const definition = await interfaceDefinition(
          this.ticket,
          this.project,
          this.formType
        );
        if (request !== this.operationRequest) return;
        this.operations = definition.operations;
        this.$nextTick(() =>
          this.$refs.operations.open(
            node.record || this.find(node.ownerId).record,
            event,
            node
          )
        );
      } catch (error) {
        this.error = error.message;
      }
    },
    async unlink() {
      const node = this.operationNode;
      if (
        node.relationship !== 'instance' ||
        !node.relationParent ||
        !window.confirm(
          t('Unlink this object? The object itself will be kept.')
        )
      )
        return;
      try {
        await rpc('execute_cmd', [
          { ticket: this.ticket, project: this.project },
          'tactic.command.sobject_link_cmd.SObjectLinkCmd',
          {
            parent_key: node.relationParent,
            search_type: node.searchType,
            path: node.relationPath || '',
            exclude_search_keys: [node.record.__search_key__]
          }
        ]);
        this.load();
      } catch (error) {
        this.error = error.message;
      }
    },
    edit(record) {
      this.$refs.details.close();
      this.$refs.form.open(record.__search_key__);
    },
    inspect(node) {
      this.$emit('focus', node);
      if (node.searchType === this.searchType)
        this.$emit('inspect', node.record);
      else {
        this.detail = node.record;
        this.$nextTick(() => this.$refs.details.show());
      }
    }
  }
};
</script>

<template>
  <div
    class="result-presentation"
    :class="{
      'result-split-right': mode === 'splitted_vertical',
      'result-split-bottom': mode === 'splitted_horizontal',
      'result-moving': moving
    }"
    :style="{ '--result-split': splitRatio + '%' }"
    :data-result-view="mode"
    :aria-busy="busy"
  >
    <MobileResults
      :visible-node="nodeVisible"
      :item-layout="itemLayout"
      :read-only="readOnly"
      v-if="mobile"
      :groups="groups"
      :parent="mobileParent"
      :path="mobilePath"
      :direction="mobileDirection"
      :scroll="mobileScroll"
      :selected-keys="selectedKeys"
      :busy="busy"
      :error="error"
      :active="active"
      @enter="mobileEnter"
      @back="mobileBack"
      @scrolled="mobileScrolled"
      @refresh="load"
      @retry="loadChildren(mobileParent)"
      @more="loadBranch(mobileParent, true)"
      @preview="quickAction($event, 'open')"
      @inspect="inspect"
      @operate="operate"
      @notes="(node, event) => notes(node, false, event)"
      @tasks="(node, event) => notes(node, true, event)"
      @upload="
        (node) =>
          quickAction(node, node.kind === 'snapshot' ? 'append' : 'save')
      "
      @preview-retry="loadSnapshotContent"
      @root-scroll="$emit('root-scroll', $event)"
      @create="createRelated"
      @link="(node) => showRelated(node, node.branch)"
      @completion="(node, item) => showRelated(node, null, item.search_type)"
      @select="(node, selected) => $emit('select', [node.record], selected)"
      @group="(key) => (closedGroups[key] = !closedGroups[key])"
      :closed-groups="closedGroups"
    />
    <section v-else class="result-main">
      <p v-if="error" class="error" role="alert">
        {{ t(error) }} <AppButton label="Retry" icon="refresh" @click="load" />
      </p>
      <p
        v-if="busy && !nodes.length"
        role="status"
        :aria-label="t('Loading data…')"
      >
        <BusyIndicator running />
      </p>
      <nav
        v-if="mode === 'tiles' && cardPath.length"
        class="result-card-navigation"
        :aria-label="t('Card navigation')"
      >
        <AppButton
          label="Back"
          icon="MDI_ARROW_LEFT"
          @click="cardPath.pop()"
        /><AppButton
          label="All items"
          icon="home"
          @click="cardPath = []"
        /><strong>{{
          cardParent?.title ||
          cardParent?.record?.name ||
          cardParent?.record?.code
        }}</strong>
      </nav>
      <section v-for="group in groups" :key="group.key" class="result-group">
        <AppButton
          v-if="group.label"
          class="result-group-heading"
          :icon="
            closedGroups[group.key] ? 'MDI_CHEVRON_RIGHT' : 'MDI_CHEVRON_DOWN'
          "
          :aria-expanded="!closedGroups[group.key]"
          @click="closedGroups[group.key] = !closedGroups[group.key]"
          >{{ group.translate || !group.key ? t(group.label) : group.label }}
          <small>{{ group.nodes.length }}</small></AppButton
        >
        <ItemLayoutTable
          v-if="mode === 'layout_table'"
          v-show="!closedGroups[group.key]"
          :layout="itemLayout"
          :nodes="group.nodes"
          :read-only="readOnly"
          @activate="activate"
          @context="(node, event) => !readOnly && operate(node, event)"
          @action="layoutAction"
          @completion="
            (owner, item) => showRelated(owner, null, item.search_type)
          "
        >
          <template v-if="!readOnly" #actions="{ node }"
            ><AppButton
              label="Object actions"
              icon="more"
              icon-only
              @click.stop="operate(node, $event)"
          /></template>
        </ItemLayoutTable>
        <VirtualCollection
          v-else
          v-show="!closedGroups[group.key]"
          class="result-item-list"
          :items="collectionItems(group.nodes)"
          :cell-width="
            mode === 'tiles' ? itemLayout?.card_width || 212 : undefined
          "
          :column-gap="mode === 'tiles' ? 18 : 0"
          :row-gap="mode === 'tiles' ? 14 : 3"
        >
          <template #default="{ item: node, index }">
            <div class="result-tree-row" :data-sequence="index">
              <component
                :is="configured(node) ? 'ConfiguredResultItem' : 'ResultItem'"
                :layout="itemLayout"
                :read-only="readOnly"
                :editing="editing"
                :selected-element="selectedElement"
                @geometry="$emit('geometry', $event)"
                @element="$emit('element', $event)"
                :node="node"
                :compact="compact"
                :card="mode === 'tiles'"
                :tree="mode === 'continious' && !mobile"
                :selected="
                  node.depth
                    ? selectedIds.includes(node.id)
                    : selectedKeys.includes(node.record?.__search_key__)
                "
                :checked="selectedKeys.includes(node.record?.__search_key__)"
                :selectable="!readOnly && !node.depth && node.kind !== 'branch'"
                @activate="activate"
                @opencard="openCard"
                @expand="disclose"
                @doubleclick="doubleClick"
                @newtab="newTab"
                @quickaction="quickAction"
                @relations="relations"
                @inspect="inspect"
                @operate="operate"
                @select="
                  (node, selected) => $emit('select', [node.record], selected)
                "
                @preview="preview"
                @notes="(node, event) => notes(node, false, event)"
                @tasks="(node, event) => notes(node, true, event)"
                @create="createRelated"
                @link="(node) => showRelated(node, node.branch)"
                @filter="filterChildren"
                @completion="
                  (node, item) => showRelated(node, null, item.search_type)
                "
              />
              <p
                v-if="node.error"
                class="error result-branch-message"
                role="alert"
              >
                {{ t(node.error) }}
                <AppButton
                  label="Retry"
                  icon="refresh"
                  @click="loadBranch(node)"
                />
              </p>
              <p
                v-if="node.expanded && node.loaded && !node.children.length"
                class="result-branch-message"
              >
                {{ t(node.filterText ? 'No results found' : 'No records yet') }}
              </p>
              <AppButton
                v-if="node.expanded && node.hasNext"
                class="result-branch-message"
                label="Load more"
                icon="next"
                :disabled="node.busy"
                @click="loadBranch(node, true)"
              />
            </div>
          </template>
        </VirtualCollection>
      </section>
      <p v-if="!busy && !nodes.length && !error" class="table-message">
        {{ t('No records yet') }}
      </p>
    </section>
    <template v-if="split">
      <AppSplitter
        v-model="splitRatio"
        class="result-split-divider"
        label="Resize versions panel"
        proportional
        :horizontal="mode !== 'splitted_vertical'"
        :min="20"
        :max="80"
      />
      <section
        class="result-versions"
        :aria-label="t('Versions')"
        :aria-busy="versionBusy"
      >
        <header>
          <strong>{{ t('Versions') }}</strong
          ><AppSelect
            :model-value="versionProcess"
            :options="versionProcesses"
            label="Process"
            :disabled="versionBusy || !selectedNode"
            @update:model-value="
              versionProcess = $event;
              loadVersions();
            "
          /><AppButton
            label="Refresh"
            icon="refresh"
            icon-only
            :disabled="versionBusy || !selectedNode"
            @click="loadVersions()"
          />
        </header>
        <p v-if="!selectedNode" class="table-message">
          {{ t('Select an item to see its versions.') }}
        </p>
        <p
          v-else-if="!versionBusy && !versions.length && !versionError"
          class="table-message"
        >
          {{ t('No versions') }}
        </p>
        <p v-if="versionError" class="error" role="alert">
          {{ t(versionError) }}
          <AppButton label="Retry" @click="loadVersions()" />
        </p>
        <p v-if="versionBusy" role="status">{{ t('Loading data…') }}</p>
        <component
          :is="itemLayout ? 'ConfiguredResultItem' : 'ResultItem'"
          :layout="itemLayout"
          :read-only="readOnly"
          v-for="node in versions"
          :key="node.id"
          :node="node"
          compact
          @activate="preview"
          @preview="preview"
          @inspect="inspect"
          @operate="operate"
          @notes="notes($event)"
          @tasks="notes($event, true)"
        />
        <AppButton
          v-if="versionHasNext"
          label="Load more"
          :disabled="versionBusy"
          @click="loadVersions(true)"
        />
      </section>
    </template>
    <AppMenu
      ref="processMenu"
      class="result-process-menu"
      label="Choose process"
      modal
      overlay
      :width="260"
      @toggle="choiceNode && (choiceNode.menuVisible = $event.target.open)"
    >
      <AppMenuItem
        v-for="choice in choices"
        :key="choice.taskSearchKey || choice.process"
        :label="choice.title"
        :translate="false"
        icon="FAS_CIRCLE"
        :badge-count="choice.count"
        :show-zero-badge="choice.process === 'publish'"
        :secondary-label="choice.multipleTasks ? 'Choose task' : undefined"
        secondary-icon="MDI_CHEVRON_RIGHT"
        :style="{
          '--process-accent': choice.accent || 'var(--content-accent)'
        }"
        @click="notes(choiceNode, choiceTasks, null, choice)"
        @secondary="chooseTask(choice, $event)"
      />
    </AppMenu>
    <RelatedObjectsMenu
      ref="relationMenu"
      :node="relationNode"
      @choose="
        (branch) =>
          showRelated(
            relationNode,
            branch?.kind === 'parent' ? branch : null,
            branch?.kind === 'relation' ? branch.search_type : ''
          )
      "
    />
    <ProcessVisibility
      ref="processVisibility"
      :ticket="ticket"
      :project="project"
      :search-type="searchType"
      :workspace-id="workspaceId"
      :ignore="processIgnore"
      @apply="applyProcessVisibility"
    />
    <FilePreview
      ref="preview"
      :ticket="ticket"
      :project="project"
      :search-type="searchType"
      @opened="mobilePreviewOpened"
      @closed="mobilePreviewClosed"
    />
    <NotesPanel
      ref="notes"
      :ticket="ticket"
      :project="project"
      :search-type="searchType"
      @saved="load"
    />
    <ObjectOperations
      ref="operations"
      :ticket="ticket"
      :project="project"
      :search-type="formType"
      :operations="operations"
      @files-attached="load"
      @preview-opened="mobilePreviewOpened"
      @preview-closed="mobilePreviewClosed"
      @inspect="
        inspect(
          operationNode.kind === 'branch'
            ? find(operationNode.ownerId)
            : operationNode
        )
      "
      @edit="edit"
      @create="$refs.form.open()"
      @duplicate="(record) => $refs.form.open(null, record.__search_key__)"
      @duplicated="load"
      @related="showRelated(operationNode)"
      @create-related="createRelated(operationNode)"
      @link-related="showRelated(operationNode, operationNode.branch)"
      @unlink="unlink"
      @retire="(record) => $refs.action.open(record, 'retire')"
      @reactivate="(record) => $refs.action.open(record, 'reactivate')"
      @delete="(record) => $refs.action.open(record, 'delete')"
    />
    <RecordForm
      ref="form"
      :ticket="ticket"
      :project="project"
      :search-type="formType"
      @saved="load"
    />
    <ObjectAction
      ref="action"
      :ticket="ticket"
      :project="project"
      :search-type="formType"
      view="table"
      @saved="load"
    />
    <RelatedObjects
      ref="related"
      :ticket="ticket"
      :project="project"
      :search-type="relatedType || formType"
      @saved="load"
    />
    <dialog
      v-window="{ type: 'window', kind: 'sobject_info' }"
      ref="details"
      class="app-dialog object-details"
      :aria-label="t('Object details')"
    >
      <header class="app-dialog-titlebar">
        <h2>
          {{ detail?.name || detail?.title || detail?.code || detail?.id }}
        </h2>
        <AppButton
          label="Close details"
          icon="close"
          icon-only
          @click="$refs.details.close()"
        />
      </header>
      <ObjectReport
        v-if="detail"
        :ticket="ticket"
        :project="project"
        :record="detail"
      />
    </dialog>
  </div>
</template>

<style></style>
