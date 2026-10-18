import { nextTick } from 'vue';
import { editable } from './state.js';
import * as UI from '../../../../../src/tactic_stream/shared_ui/features/files/queue/queue.ui.mjs';

export default {
  dispatch(action) {
    const job =
      action.key != null
        ? this.jobs.find((job) => String(job.id) === action.key)
        : action.index == null
          ? this.selected
          : this.jobs[action.index];
    if (action.type === 'select') {
      if (!job) return;
      this.select(job, !action.focus);
      if (action.focus)
        nextTick(() =>
          this.$refs.workspace?.focusOperation(action.index, String(job.id))
        );
    } else if (action.type === 'navigate')
      this.mobileDetails = action.value === 'details';
    else if (action.type === 'check') {
      if (job && !this.running && editable(job)) {
        job.checked = action.value;
        this.changed();
      }
    } else if (action.type === 'remove') {
      if (job) this.remove(job);
    } else if (action.type === 'up') this.move(-1);
    else if (action.type === 'down') this.move(1);
    else if (action.type === 'completed') this.clear(true);
    else if (action.type === 'clear') this.$refs.auxiliary.clear();
    else if (action.type === 'help') this.$emit('help', 'commit_queue');
    else if (action.type === 'autoClean') this.autoClean(action.value);
    else if (
      ['paneWidth', 'paneWidthDraft', 'paneWidthCancel'].includes(action.type)
    )
      this.width = action.value;
    else if (
      ['filesHeight', 'filesHeightDraft', 'filesHeightCancel'].includes(
        action.type
      )
    )
      this.filesHeight = action.value;
    else if (action.type === 'advanced') this.advanced = !this.advanced;
    else if (action.type === 'applyChecked') this.applyChecked = action.value;
    else if (action.type === 'namingToggle')
      this.namingExpanded = !this.namingExpanded;
    else if (action.type === 'namingEditor') this.naming();
    else if (action.type === 'contextEdit') this.beginContext();
    else if (action.type === 'contextDraft') this.contextBranch = action.value;
    else if (action.type === 'contextCommit') this.finishContext();
    else if (action.type === 'contextCancel') this.contextEditing = false;
    else if (action.type === 'versionDraft') {
      this.versionDraft = action.value;
      this.versionError = '';
    } else if (action.type === 'versionCommit') {
      if (this.versionDraft == null) return;
      const version = UI.versionValue(this.versionDraft);
      if (version == null)
        this.versionError = 'Version must be a whole number from 0 to 9999';
      else {
        this.update('version', version);
        this.versionDraft = null;
        this.versionError = '';
      }
    } else if (action.type === 'filenameDraft')
      this.filenameDraft = action.value;
    else if (action.type === 'filenameCommit') {
      if (this.filenameDraft != null) {
        this.update('explicitFilename', this.filenameDraft);
        this.filenameDraft = null;
      }
    } else if (action.type === 'descriptionDraft')
      this.descriptionDraft = action.value;
    else if (action.type === 'descriptionCommit') {
      if (this.descriptionDraft != null) {
        this.update('description', this.descriptionDraft);
        this.descriptionDraft = null;
      }
    } else if (action.type === 'field')
      this.update(
        action.field === 'repository' ? 'repositoryAlias' : action.field,
        action.value
      );
    else if (action.type === 'removeFile') {
      if (action.operationId !== String(this.selectedId)) return;
      const file = action.preview
        ? this.selected?.previews[action.index]
        : this.selected?.files[action.index];
      if (file) this.removeFile(file);
    } else if (action.type === 'removePreview') {
      if (action.operationId !== String(this.selectedId)) return;
      const file = this.selected?.previews[action.index];
      if (file) this.removeFile(file);
    } else if (action.type === 'reselect') this.chooseSources(false);
    else if (action.type === 'reselectDirectory') this.chooseSources(true);
    else if (action.type === 'preview') this.previewAction(action.command);
    else if (action.type === 'menuCommand') {
      if (action.menu === 'preview') {
        if (job?.id === this.selectedId) this.previewAction(action.command);
      } else
        this.sendAction(
          action.command,
          action.menu === 'operation' ? job : this.selected
        );
    } else if (action.type === 'duplicate')
      this.resolveDuplicate(action.decision);
    else if (action.type === 'snapshot') this.snapshot();
    else if (['all', 'retry', 'cancel'].includes(action.type))
      this.sendAction(action.type, this.selected);
  },
  previewAction(command) {
    if (command === 'capture') this.capture();
    else if (command === 'choose') {
      this.previewPickerId = this.selectedId;
      this.$refs.previewsInput.click();
    } else if (command === 'paste') this.pasteImage();
    else if (command === 'manage') this.$refs.auxiliary.previews();
    else if (command === 'clearPreviews') this.clearPreviews();
  },
  sendAction(command, job) {
    if (
      this.versionError &&
      ['all', 'selected', 'current', 'retry'].includes(command)
    )
      return;
    if (command === 'all') this.run(this.jobs);
    else if (command === 'selected')
      this.run(this.jobs.filter((job) => job.checked));
    else if (command === 'current' && job) this.run([job]);
    else if (command === 'retry' && job) this.retry(job);
    else if (command === 'cancel' && this.running) {
      this.cancelRequested = true;
      const active = this.jobs.find((job) =>
        ['Uploading', 'Checking in'].includes(job.status)
      );
      if (active) this.cancel(active);
    } else if (command === 'cancel' || (command === 'cancelOperation' && job))
      this.cancel(job);
    else if (command === 'remove' && job) this.remove(job);
  }
};
