<script>
// DuplicateSObjectView.qml and SObjectDuplicateController: the same five steps.
import { appearance } from '../../appearance.js';
import {
  choices,
  busyState
} from '../../../../src/tactic_stream/shared_ui/features/objects/duplicate.ui.mjs';
import ContentLoadingOverlay from '../../controls/display/ContentLoadingOverlay.vue';
import { nextTick } from 'vue';
import { rpc } from '../../api.js';
import { t } from '../../i18n.js';
import { notify } from '../activity/notifications.js';
import AppButton from '../../controls/AppButton.vue';
import AppCheckbox from '../../controls/AppCheckbox.vue';
import AppSelect from '../../controls/AppSelect.vue';
import AppDateField from '../../controls/AppDateField.vue';
import AppTextField from '../../controls/AppTextField.vue';
import AppColorInput from '../../controls/AppColorInput.vue';
import ObjectDuplicateSurface from './ObjectDuplicateSurface.vue';
import ObjectFieldFrame from './ObjectFieldFrame.vue';
import AppTextArea from '../../controls/AppTextArea.vue';
import {
  contentChoices,
  duplicateProfile,
  saveDuplicateProfile,
  applyDuplicateProfile,
  changeContent
} from './duplicateProfiles.js';

export default {
  components: {
    ContentLoadingOverlay,
    ObjectDuplicateSurface,
    ObjectFieldFrame,
    AppTextArea,
    AppDateField,
    AppButton,
    AppCheckbox,
    AppSelect,
    AppTextField,
    AppColorInput
  },
  inject: { openHelp: {}, currentLogin: { default: () => () => '' } },
  props: { ticket: String, project: String },
  emits: ['completed'],
  data() {
    return {
      analysis: null,
      draft: {},
      baseline: '',
      scope: null,
      sourceKey: '',
      sourceType: '',
      owner: '',
      revision: '',
      step: 0,
      remember: true,
      busy: false,
      saving: false,
      uncertain: false,
      error: '',
      discard: false,
      request: 0,
      quick: false
    };
  },
  computed: {
    presentation() {
      return {
        title: this.analysis?.title,
        searchType: this.analysis?.searchType || this.sourceType,
        step: this.step,
        ready: !!this.analysis,
        busy: this.busy,
        saving: this.saving,
        uncertain: this.uncertain,
        valid: this.valid,
        error: this.error,
        remember: this.remember,
        relations: this.analysis?.relations || [],
        processes: this.analysis?.processes || [],
        totals: this.totals
      };
    },
    busyPresentation() {
      return busyState(this.presentation, appearance.language);
    },
    dirty() {
      return (
        !!this.analysis && JSON.stringify(this.options()) !== this.baseline
      );
    },
    valid() {
      return (
        this.scope?.ticket === this.ticket &&
        this.scope?.project === this.project
      );
    },
    totals() {
      const result = { related: 0, snapshots: 0, tasks: 0, messages: 0 };
      for (const relation of this.analysis?.relations || [])
        if (relation.mode !== 'none') result.related += relation.count;
      for (const process of this.analysis?.processes || []) {
        if (process.copySnapshots) result.snapshots += process.snapshotCount;
        if (process.copyTasks) result.tasks += process.taskCount;
        if (process.copyProcessMessages)
          result.messages += process.processMessageCount;
        if (process.copyTaskMessages)
          result.messages += process.taskMessageCount;
        if (process.copyProcessAttachments)
          result.messages += process.processAttachmentCount;
        if (process.copyTaskAttachments)
          result.messages += process.taskAttachmentCount;
      }
      return result;
    }
  },
  watch: {
    ticket() {
      this.invalidate();
    },
    project() {
      this.invalidate();
    }
  },
  mounted() {
    window.addEventListener('beforeunload', this.beforeUnload);
  },
  beforeUnmount() {
    this.request++;
    window.removeEventListener('beforeunload', this.beforeUnload);
  },
  methods: {
    t,
    action(event) {
      if (event.type === 'step') this.step = event.value;
      else if (event.type === 'remember') this.remember = event.value;
      else if (event.type === 'relation')
        this.analysis.relations[event.index].mode = event.value;
      else if (event.type === 'choice')
        this.changeContent(
          this.analysis.processes[event.index],
          event.name,
          event.value
        );
      else if (event.type === 'back') this.step--;
      else if (event.type === 'next') this.step++;
      else if (event.type === 'duplicate') this.duplicate();
      else if (event.type === 'retry') this.analyze();
      else if (event.type === 'cancel') this.close();
      else if (event.type === 'help') this.openHelp('duplicating_objects');
    },
    changeContent,
    beforeUnload(event) {
      if (
        this.$refs.dialog?.open &&
        (this.dirty || this.saving || this.uncertain)
      ) {
        event.preventDefault();
        event.returnValue = '';
      }
    },
    invalidate() {
      this.request++;
      this.busy = this.saving = false;
      if (this.$refs.dialog?.open)
        this.error =
          'Connection context changed. Close this form and reopen it before saving.';
    },
    async open(record, quick = false) {
      if (this.$refs.dialog.open) {
        this.$refs.dialog.show();
        return;
      }
      this.scope = {
        ticket: this.ticket,
        project: this.project,
        language: 'python'
      };
      this.sourceKey = record.__search_key__;
      this.sourceType = record.__search_key__.split('?')[0];
      this.owner = this.currentLogin();
      this.analysis = null;
      this.draft = {};
      this.revision = '';
      this.step = 0;
      this.quick = quick;
      this.error = '';
      this.uncertain = this.discard = false;
      await nextTick();
      this.$refs.dialog.show();
      await this.analyze();
      if (quick && this.analysis && !this.error && this.valid)
        await this.duplicate();
    },
    async call(action, values = {}) {
      return (
        await rpc('execute_cmd', [
          this.scope,
          'tactic.command.sobject_duplicate_cmd.SObjectDuplicateCmd',
          { action, search_key: this.sourceKey, ...values }
        ])
      ).info;
    },
    async analyze() {
      if (!this.valid || this.saving || this.uncertain) return;
      const request = ++this.request,
        previous = this.analysis ? this.options() : null;
      this.busy = true;
      this.error = '';
      try {
        const result = await this.call('analyze');
        if (request !== this.request) return;
        const profile = duplicateProfile(
          this.owner,
          this.scope.project,
          this.sourceType
        );
        if (this.quick && !profile)
          throw new Error(
            'Open Duplicate… once to save choices for this Search Type.'
          );
        applyDuplicateProfile(result.analysis, previous || profile);
        this.analysis = result.analysis;
        this.revision = result.revision;
        this.draft = Object.fromEntries(
          this.analysis.fields.map((field) => [
            field.name,
            previous?.fields?.[field.name] ??
              (this.fieldKind(field) === 'checkbox'
                ? ['True', 'true', '1', 'on'].includes(field.value)
                : String(field.widget?.input?.value ?? field.value))
          ])
        );
        if (!previous) this.baseline = JSON.stringify(this.options());
      } catch (error) {
        if (request === this.request) this.error = error.message;
      } finally {
        if (request === this.request) this.busy = false;
      }
    },
    readOnly(field) {
      return (
        field.widget?.input?.read_only ||
        [true, 'true'].includes(field.widget?.options?.read_only)
      );
    },
    fieldKind(field) {
      const widget = field.widget;
      if (
        widget?.input?.type === 'hidden' ||
        widget?.class_name?.endsWith('.HiddenWdg')
      )
        return 'hidden';
      if (widget?.input?.type === 'color') return 'color';
      if (widget?.choices && widget.input?.type !== 'multiselect')
        return 'select';
      if (
        widget?.class_name?.endsWith('.CheckboxWdg') ||
        /bool/i.test(field.dataType)
      )
        return 'checkbox';
      if (field.multiline || widget?.class_name?.endsWith('.TextAreaWdg'))
        return 'textarea';
      if (widget?.input?.type === 'time') return 'time';
      if (widget?.class_name?.includes('CalendarInput'))
        return 'datetime-local';
      return /int|float|double|numeric|decimal/i.test(field.dataType)
        ? 'number'
        : 'text';
    },
    fieldChoices(field) {
      const widget = field.widget;
      return [
        ...(widget.input?.empty_label
          ? [{ value: '', label: widget.input.empty_label }]
          : []),
        ...widget.choices.map((value, index) => ({
          value,
          label: widget.labels[index]
        }))
      ];
    },
    pageChoices(process) {
      return choices.filter(
        (choice) => choice.page === this.step && process[choice.count]
      );
    },
    options() {
      return {
        fields: Object.fromEntries(
          (this.analysis?.fields || [])
            .filter((field) => !this.readOnly(field))
            .map((field) => [field.name, this.draft[field.name]])
        ),
        relations: Object.fromEntries(
          (this.analysis?.relations || []).map((row) => [row.key, row.mode])
        ),
        processes: Object.fromEntries(
          (this.analysis?.processes || []).map((row) => [
            row.name,
            Object.fromEntries(
              contentChoices.map((name) => [name, row[name] === true])
            )
          ])
        )
      };
    },
    async duplicate() {
      if (
        !this.analysis ||
        this.busy ||
        this.saving ||
        this.uncertain ||
        !this.valid
      )
        return;
      if (!this.$refs.fields?.checkValidity()) {
        this.step = 0;
        await nextTick();
        this.$refs.fields.reportValidity();
        return;
      }
      const request = ++this.request;
      this.saving = true;
      this.error = '';
      try {
        const options = this.options();
        if (this.remember) {
          try {
            saveDuplicateProfile(
              this.owner,
              this.scope.project,
              this.sourceType,
              { relations: options.relations, processes: options.processes }
            );
          } catch {
            const error = new Error(
              'Unable to save choices in this browser. Turn off Remember choices to continue.'
            );
            error.status = 400;
            throw error;
          }
        }
        const result = await this.call('duplicate', {
          options,
          revision: this.revision
        });
        if (request !== this.request) return;
        this.baseline = JSON.stringify(options);
        this.$refs.dialog.close();
        this.analysis = null;
        notify('info', 'Object duplicated');
        this.$emit('completed', result.result);
      } catch (error) {
        if (request !== this.request) return;
        this.uncertain = !error.status || error.status >= 500;
        this.error = this.uncertain
          ? 'The result is unknown. Refresh the objects before trying again.'
          : error.message;
      } finally {
        if (request === this.request) this.saving = false;
      }
    },
    close(force = false) {
      if (this.saving) return;
      if (!force && (this.dirty || this.uncertain)) {
        this.discard = true;
        return;
      }
      this.request++;
      this.$refs.dialog.close();
      this.analysis = null;
      this.busy = this.uncertain = this.discard = false;
    }
  }
};
</script>

<template>
  <Teleport to="body">
    <dialog
      v-window="{ kind: 'duplicate_sobject', type: 'window' }"
      ref="dialog"
      class="record-dialog duplicate-sobject"
      :aria-label="t('Duplicate object')"
      @cancel.prevent="close()"
    >
      <header>
        <h2>{{ t('Duplicate object') }}</h2>
        <AppButton
          label="Close"
          icon="close"
          icon-only
          :disabled="saving"
          @click="close()"
        />
      </header>
      <ObjectDuplicateSurface
        :model="presentation"
        part="header"
        @event="action"
      />
      <ObjectDuplicateSurface
        :model="presentation"
        part="tabs"
        @event="action"
      />
      <div class="duplicate-pages-wrapper">
        <div class="duplicate-pages">
          <ObjectDuplicateSurface :model="presentation" @event="action" />
          <form v-if="analysis" ref="fields" @submit.prevent="duplicate">
            <section v-show="step === 0" class="duplicate-page">
              <div class="duplicate-fields">
                <ObjectFieldFrame
                  v-for="field in analysis.fields.filter(
                    (field) => fieldKind(field) !== 'hidden'
                  )"
                  :key="field.name"
                  :minimum-editor-height="
                    fieldKind(field) === 'textarea' ? 112 : undefined
                  "
                  :model="{
                    name: field.name,
                    title: field.widget?.title || field.label,
                    description:
                      field.widget?.options?.hint ||
                      field.widget?.options?.hint_text ||
                      '',
                    readOnly: readOnly(field),
                    required: [true, 'true'].includes(
                      field.widget?.options?.required
                    ),
                    icon:
                      fieldKind(field) === 'textarea'
                        ? 'description'
                        : 'text-fields'
                  }"
                >
                  <AppCheckbox
                    v-if="fieldKind(field) === 'checkbox'"
                    v-model="draft[field.name]"
                    :label="field.widget?.title || field.label"
                    :disabled="saving || readOnly(field)"
                  />
                  <AppSelect
                    v-else-if="fieldKind(field) === 'select'"
                    v-model="draft[field.name]"
                    :options="fieldChoices(field)"
                    :label="field.widget?.title || field.label"
                    :translate-labels="false"
                    :disabled="saving || readOnly(field)"
                  />
                  <AppColorInput
                    v-else-if="fieldKind(field) === 'color'"
                    v-model="draft[field.name]"
                    :label="field.label"
                    :disabled="saving || readOnly(field)"
                  />
                  <AppTextArea
                    v-else-if="fieldKind(field) === 'textarea'"
                    v-model="draft[field.name]"
                    :label="field.widget?.title || field.label"
                    rows="4"
                    :disabled="saving || readOnly(field)"
                  />
                  <AppDateField
                    include-time
                    v-else-if="fieldKind(field) === 'datetime-local'"
                    v-model="draft[field.name]"
                    :label="field.widget?.title || field.label"
                    :required="
                      [true, 'true'].includes(field.widget?.options?.required)
                    "
                    :disabled="saving || readOnly(field)"
                  />
                  <AppTextField
                    v-else
                    v-model="draft[field.name]"
                    :label="field.widget?.title || field.label"
                    :type="fieldKind(field)"
                    :required="
                      [true, 'true'].includes(field.widget?.options?.required)
                    "
                    :disabled="saving || readOnly(field)"
                    step="any"
                  />
                  <small
                    v-if="
                      field.widget?.options?.hint ||
                      field.widget?.options?.hint_text
                    "
                    class="muted"
                    >{{
                      t(
                        field.widget.options.hint ||
                          field.widget.options.hint_text
                      )
                    }}</small
                  >
                </ObjectFieldFrame>
              </div>
            </section>
          </form>
        </div>
        <ContentLoadingOverlay
          v-if="busyPresentation"
          :message="busyPresentation.message"
          :cancellable="busyPresentation.cancellable"
          @cancel="close()"
        />
      </div>
      <ObjectDuplicateSurface
        :model="presentation"
        part="footer"
        @event="action"
      />
      <div v-if="discard" class="notice" role="alert">
        <p>{{ t('Discard unsaved changes?') }}</p>
        <AppButton
          label="Continue editing"
          @click="discard = false"
        /><AppButton label="Discard" destructive @click="close(true)" />
      </div>
    </dialog>
  </Teleport>
</template>

<style>
.duplicate-sobject {
  width: min(960px, calc(100vw - 32px));
  height: min(620px, calc(100dvh - 32px));
  padding: 14px;
  background: var(--workspace);
}
.duplicate-sobject[open] {
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow: hidden;
}
.app-window.duplicate-sobject > header {
  flex: none;
  min-height: 40px;
  margin: 0;
  padding: 0 6px;
}
.duplicate-pages-wrapper {
  position: relative;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}
.duplicate-pages {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 6px 10px 10px 6px;
  scrollbar-gutter: stable;
}
.duplicate-pages > form {
  margin-top: 10px;
}
.duplicate-fields {
  display: grid;
  align-items: start;
  grid-template-columns: repeat(auto-fit, minmax(min(430px, 100%), 1fr));
  gap: 10px;
}
.duplicate-fields .app-text-area {
  height: 112px;
}
</style>
