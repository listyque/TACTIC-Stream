<script>
import { nextTick, markRaw } from 'vue';
import { rpc } from '../../api.js';
import { t } from '../../i18n.js';
import AppButton from '../../controls/AppButton.vue';
import AppDialog from '../../controls/AppDialog.vue';
import FrameView from '../../frame/FrameView.vue';
import IngestFileList from './IngestFileList.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { randomId } from '../../controls/identity.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/files/ingest.ui.mjs';
import * as Confirmation from '../../../../src/tactic_stream/shared_ui/controls/feedback/confirmation.ui.mjs';

export default {
  components: { AppButton, AppDialog, FrameView },
  inject: {
    queueCheckin: { default: null },
    openScriptEditor: { default: null }
  },
  props: { ticket: String, project: String },
  data() {
    return {
      parent: null,
      branch: null,
      scope: null,
      rules: [],
      selectedRule: '',
      options: {},
      extraJson: '{}',
      files: [],
      advanced: false,
      busy: false,
      ready: false,
      error: '',
      discard: false,
      conflicts: null,
      request: 0,
      viewport: { width: 920, height: 650 },
      conflictWidth: 540,
      confirmationWidth: 400
    };
  },
  computed: {
    frameModel() {
      return {
        parentTitle:
          this.parent?.name || this.parent?.title || this.parent?.code,
        targetTitle: this.branch?.title,
        searchType: this.branch?.search_type,
        count: this.files.length,
        ruleCount: this.rules.length,
        ready: this.ready,
        busy: this.busy,
        rulesBusy: !this.ready && this.busy,
        canDeleteRule: !!this.rule?.key,
        canStart: !!this.queueCheckin && !this.conflicts,
        canOpenScript: !!this.openScriptEditor,
        advanced: this.advanced,
        options: { ...this.options, extraDataJson: this.extraJson },
        error: t(this.error)
      };
    },
    scene() {
      return UI.describe(
        this.frameModel,
        this.viewport.width,
        this.viewport.height,
        appearance.language
      );
    },
    presentedRules() {
      return this.rules.map((rule) => ({
        ruleId: rule.code,
        title: rule.title,
        subtitle: rule.subtitle || '',
        selected: rule.code === this.selectedRule,
        builtIn: !rule.key,
        applicable: rule.applicable
      }));
    },
    presentedFiles() {
      return this.files.map((row) => ({
        key: row.key,
        title: row.file.name,
        extension: row.file.name.includes('.')
          ? row.file.name.split('.').at(-1)
          : '',
        status: row.status,
        size: row.file.size,
        error: row.reason
      }));
    },
    views() {
      return {
        files: {
          component: markRaw(IngestFileList),
          nodeProps: true,
          props: {
            records: this.presentedFiles,
            busy: this.busy,
            onRemove: this.removeFile
          }
        }
      };
    },
    conflictScene() {
      const files = this.conflicts?.files.filter((item) => item.conflict) || [];
      return UI.conflict(
        {
          conflictCount: files.length,
          conflictNames: [...new Set(files.map((item) => item.name))],
          canUpdateConflicts: this.canUpdate
        },
        this.conflictWidth,
        appearance.language
      );
    },
    confirmationScene() {
      return Confirmation.describe(
        {
          message: t('The rule will be removed from this TACTIC project.'),
          accept: 'Delete rule',
          destructive: true,
          busy: this.busy
        },
        this.confirmationWidth,
        170,
        appearance.language
      );
    },
    discardScene() {
      return Confirmation.describe(
        {
          message: t('Discard unsaved changes?'),
          reject: 'Continue editing',
          accept: 'Discard',
          destructive: true
        },
        this.confirmationWidth,
        170,
        appearance.language
      );
    },
    canUpdate() {
      return this.conflicts?.files
        .filter((item) => item.conflict)
        .every((item) => item.matches.length === 1);
    },
    rule() {
      return this.rules.find((rule) => rule.code === this.selectedRule);
    }
  },
  watch: {
    async conflicts() {
      await nextTick();
      if (!this.$refs.conflictDialog) return;
      const pending = this.conflicts?.files.some((item) => item.conflict);
      if (pending && !this.$refs.conflictDialog.open)
        this.$refs.conflictDialog.show(this.$refs.workspace);
      else if (!pending) this.$refs.conflictDialog.close();
    },
    ticket() {
      this.reset();
    },
    project() {
      if (!this.$refs.dialog?.open) this.reset();
    },
    options: {
      deep: true,
      handler() {
        this.conflicts = null;
      }
    },
    extraJson() {
      this.conflicts = null;
    }
  },
  mounted() {
    window.addEventListener('beforeunload', this.beforeUnload);
    this.frameObserver = observeFrameSizes((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width <= 0) continue;
        if (entry.target === this.$refs.workspace)
          this.viewport = {
            width: entry.contentRect.width,
            height: entry.contentRect.height
          };
        else if (entry.target === this.$refs.conflictContent)
          this.conflictWidth = entry.contentRect.width;
        else this.confirmationWidth = entry.contentRect.width;
      }
    });
    for (const name of [
      'workspace',
      'conflictContent',
      'deleteContent',
      'discardContent'
    ])
      this.frameObserver.observe(this.$refs[name]);
  },
  beforeUnmount() {
    this.request++;
    this.frameObserver?.disconnect();
    window.removeEventListener('beforeunload', this.beforeUnload);
  },
  methods: {
    t,
    describeRow(list, record) {
      return UI.ruleRow(
        this.frameModel,
        record,
        list.width - 16,
        appearance.language
      );
    },
    removeFile(index) {
      if (this.busy) return;
      this.files.splice(index, 1);
      this.conflicts = null;
    },
    dispatch(action) {
      if (action.type === 'option') {
        if (this.busy) return;
        const value = UI.optionValue(action.field, action.value);
        if (action.field === 'extraDataJson') this.extraJson = value;
        else this.options[action.field] = value;
      } else if (action.type === 'rule')
        this.selectRule(this.rules.find((rule) => rule.code === action.key));
      else if (action.type === 'advanced') this.advanced = !this.advanced;
      else if (action.type === 'clear') {
        this.files = [];
        this.conflicts = null;
      } else if (action.type === 'add') this.$refs.picker.click();
      else if (action.type === 'start') this.start();
      else if (action.type === 'close') this.close();
      else if (action.type === 'saveRule') this.saveRule();
      else if (action.type === 'deleteRule')
        this.$refs.deleteDialog.show(this.$refs.workspace);
      else if (action.type === 'script')
        this.openScriptEditor?.(this.options[action.field]);
      else if (action.type === 'conflict') {
        if (action.decision === 'cancel') this.conflicts = null;
        else this.enqueue(action.decision);
      }
    },
    beforeUnload(event) {
      if (this.files.length) {
        event.preventDefault();
        event.returnValue = '';
      }
    },
    reset() {
      this.request++;
      this.files = [];
      this.conflicts = null;
      this.$refs.discardDialog?.close();
      this.$refs.deleteDialog?.close();
      this.$refs.dialog?.close();
    },
    close(force = false) {
      if (this.busy) return;
      if (!force && this.files.length) {
        this.discard = true;
        this.$refs.discardDialog.show(this.$refs.workspace);
        return;
      }
      this.reset();
    },
    windowContext() {
      if (this.busy || this.files.length || this.conflicts)
        throw Error('Apply or discard unsaved changes first');
      return {
        project: this.project,
        route: {
          searchType: this.parent.__search_key__.split('?')[0],
          args: [this.parent, this.branch]
        }
      };
    },
    async open(parent, branch) {
      if (this.$refs.dialog.open) {
        this.$refs.dialog.show();
        return;
      }
      this.parent = parent;
      this.branch = branch;
      this.scope = { ticket: this.ticket, project: this.project };
      this.files = [];
      this.rules = [];
      this.ready = false;
      this.error = '';
      this.discard = false;
      this.conflicts = null;
      this.advanced = false;
      await nextTick();
      this.$refs.dialog.show();
      await this.loadRules();
    },
    async call(action, values = {}) {
      return (
        await rpc('execute_cmd', [
          { ...this.scope, language: 'python' },
          'tactic.command.related_ingest_cmd.RelatedIngestCmd',
          {
            action,
            parent_key: this.parent.__search_key__,
            search_type: this.branch.search_type,
            path: this.branch.path || '',
            ...values
          }
        ])
      ).info;
    },
    async loadRules() {
      const request = ++this.request;
      this.busy = true;
      try {
        const result = await this.call('rules');
        if (request !== this.request) return;
        this.rules = result.rules;
        this.selectRule(this.rules[0]);
        this.ready = true;
      } catch (error) {
        if (request === this.request) this.error = error.message;
      } finally {
        if (request === this.request) this.busy = false;
      }
    },
    selectRule(rule) {
      if (!rule?.applicable) return;
      this.selectedRule = rule.code;
      this.options = { ...rule.options };
      this.extraJson = JSON.stringify(rule.options.extraData, null, 2);
      this.conflicts = null;
    },
    values() {
      const extraData = JSON.parse(this.extraJson);
      if (
        !extraData ||
        Array.isArray(extraData) ||
        typeof extraData !== 'object'
      )
        throw new Error('Extra values must be a JSON object');
      return { ...this.options, extraData };
    },
    addFiles(files) {
      if (this.busy) return;
      this.files.push(
        ...[...files].map((file) => ({
          key: randomId(),
          file,
          status: 'Ready',
          reason: ''
        }))
      );
      this.conflicts = null;
      this.error = '';
    },
    async start() {
      if (!this.ready || this.busy || !this.files.length) return;
      const request = ++this.request;
      this.error = '';
      this.busy = true;
      this.conflicts = null;
      try {
        const options = this.values();
        const result = await this.call('scan', {
          options,
          filenames: this.files.map((row) => row.file.name)
        });
        if (request !== this.request) return;
        this.files.forEach((row, index) => {
          row.status = result.files[index].accepted
            ? result.files[index].conflict
              ? 'Conflict'
              : 'Ready'
            : 'Skipped';
          row.reason = result.files[index].reason || '';
        });
        this.conflicts = { ...result, options };
        const conflicts = result.files.filter((item) => item.conflict);
        if (!conflicts.length) this.enqueue('new');
        else if (options.updateMode === 'update' && this.canUpdate)
          this.enqueue('update');
      } catch (error) {
        if (request === this.request) this.error = error.message;
      } finally {
        if (request === this.request) this.busy = false;
      }
    },
    enqueue(decision) {
      if (!this.conflicts || !this.queueCheckin) return;
      const prepared = this.conflicts;
      const remaining = [];
      try {
        for (const [index, item] of prepared.files.entries()) {
          const row = this.files[index];
          if (!item.accepted || (item.conflict && decision === 'skip')) {
            row.status = 'Skipped';
            row.reason ||= 'Matching item already exists';
            remaining.push(row);
            continue;
          }
          this.queueCheckin({
            ...this.scope,
            searchKey: this.parent.__search_key__,
            title: item.name,
            name: row.file.name,
            files: [row.file],
            file: row.file,
            context: item.context,
            process: prepared.options.process,
            description: '',
            ingest: {
              parent_key: this.parent.__search_key__,
              search_type: this.branch.search_type,
              path: this.branch.path || '',
              options: prepared.options,
              decision: item.conflict ? decision : 'new',
              search_key: decision === 'update' ? item.matches[0] || '' : ''
            }
          });
          row.queued = true;
        }
        this.files = remaining;
        this.conflicts = null;
        if (!remaining.length) this.reset();
      } catch (error) {
        this.files = this.files.filter((row) => !row.queued);
        this.conflicts = null;
        this.error = error.message;
      }
    },
    async saveRule() {
      if (this.busy) return;
      const request = ++this.request;
      this.busy = true;
      this.error = '';
      try {
        const options = this.values(),
          title = options.title.trim();
        if (!title) throw new Error('Enter a rule title');
        await this.call('scan', {
          options,
          filenames: ['rule-validation.txt']
        });
        if (request !== this.request) return;
        const data = {
          scan_type: 'list',
          action_type: 'checkin',
          action: 'file',
          search_type: this.branch.search_type,
          rule: options.pattern,
          filter: options.filter,
          ignore: options.ignore,
          column: options.column,
          ignore_ext: options.ignoreExtension,
          update_mode: options.updateMode === 'update',
          process: options.process,
          context: options.context,
          context_mode: options.contextMode,
          keywords: options.keywords,
          keyword_mode: options.keywordMode,
          extra_data: options.extraData,
          validation_script: options.validationScript,
          process_script: options.processScript,
          create_icon: options.createIcon
        };
        const payload = {
          title,
          base_dir: '',
          rule: options.pattern,
          data: JSON.stringify(data)
        };
        await rpc(this.rule?.key ? 'update' : 'insert', [
          { ...this.scope, language: 'python' },
          this.rule?.key || 'config/ingest_rule',
          payload
        ]);
        if (request === this.request) await this.loadRules();
      } catch (error) {
        if (request === this.request) this.error = error.message;
      } finally {
        if (request === this.request) this.busy = false;
      }
    },
    async deleteRule() {
      if (this.busy || !this.rule?.key) return;
      const request = ++this.request;
      this.busy = true;
      try {
        await rpc('delete_sobject', [
          { ...this.scope, language: 'python' },
          this.rule.key
        ]);
        if (request === this.request) {
          this.$refs.deleteDialog.close();
          await this.loadRules();
        }
      } catch (error) {
        if (request === this.request) this.error = error.message;
      } finally {
        if (request === this.request) this.busy = false;
      }
    }
  }
};
</script>

<template>
  <Teleport to="body">
    <dialog
      v-window="{ kind: 'ingest_files', type: 'window', page: windowContext }"
      ref="dialog"
      class="record-dialog ingest-files"
      :aria-label="t('Add files')"
      @cancel.prevent="close()"
      @dragover.prevent
      @drop.prevent="addFiles($event.dataTransfer.files)"
    >
      <header>
        <h2>{{ t('Add files') }}</h2>
        <AppButton
          label="Close"
          icon="close"
          :disabled="busy"
          @click="close()"
        />
      </header>
      <div ref="workspace" class="ingest-workspace" :aria-busy="busy">
        <FrameView
          :scene="scene"
          :models="{ rules: presentedRules }"
          :describe-row="describeRow"
          :views="views"
          @event="dispatch"
        />
      </div>
      <input
        ref="picker"
        type="file"
        multiple
        hidden
        @change="
          addFiles($event.target.files);
          $event.target.value = '';
        "
      />
    </dialog>
    <AppDialog
      ref="conflictDialog"
      class="ingest-conflict-dialog"
      title="Resolve matching names"
      :close-on-outside="false"
      @rejected="conflicts = null"
    >
      <div
        ref="conflictContent"
        class="ingest-dialog-content"
        :style="{ height: conflictScene.height + 'px' }"
      >
        <FrameView :scene="conflictScene" @event="dispatch" />
      </div>
    </AppDialog>
    <AppDialog
      ref="deleteDialog"
      class="ingest-confirmation-dialog"
      title="Delete ingest rule?"
      :close-on-escape="!busy"
      :close-on-outside="!busy"
    >
      <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
      <div
        ref="deleteContent"
        class="ingest-dialog-content"
        style="height: 170px"
      >
        <FrameView
          :scene="confirmationScene"
          @event="
            $event.type === 'accept' ? deleteRule() : $refs.deleteDialog.close()
          "
        />
      </div>
    </AppDialog>
    <AppDialog
      ref="discardDialog"
      class="ingest-confirmation-dialog"
      title="Discard unsaved changes?"
      @rejected="discard = false"
    >
      <div
        ref="discardContent"
        class="ingest-dialog-content"
        style="height: 170px"
      >
        <FrameView
          :scene="discardScene"
          @event="
            $event.type === 'accept' ? close(true) : $refs.discardDialog.close()
          "
        />
      </div>
    </AppDialog>
  </Teleport>
</template>
<style>
.ingest-files.record-dialog {
  width: min(1000px, calc(100dvw - 24px));
  height: min(800px, 85dvh);
}
.ingest-files[open] {
  display: flex;
  flex-direction: column;
}
.ingest-files > header {
  flex: none;
}
.ingest-workspace {
  position: relative;
  min-width: 0;
  min-height: 0;
  flex: 1;
}
.ingest-dialog-content {
  position: relative;
}
.ingest-conflict-dialog {
  width: min(620px, calc(100dvw - 24px));
}
.ingest-confirmation-dialog {
  width: min(440px, calc(100dvw - 24px));
}
</style>
