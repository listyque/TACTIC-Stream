import { editable } from './state.js';
import { sourcePath, descriptors } from '../files.js';

export default {
  chooseSources(directory) {
    this.sourcePickerId = this.selectedId;
    this.$refs[directory ? 'reselectDirectory' : 'reselectInput'].click();
  },
  previewsPicked(files) {
    if (this.previewPickerId === this.selectedId) this.addPreviews(files);
  },
  sourcesPicked(files) {
    if (this.sourcePickerId === this.selectedId) this.reselect(files);
  },
  removeFile(file) {
    if (!this.canEdit) return;
    const job = this.selected;
    job.files = job.files.filter((item) => item !== file);
    job.previews = job.previews.filter((item) => item !== file);
    job.sourceFiles = descriptors(job.files);
    job.previewFiles = descriptors(job.previews);
    job.file = job.files[0];
    this.changed();
    if (job.file) this.validateAll();
    else {
      job.plan = null;
      job.planError = 'Choose source files before check-in';
    }
  },
  reselect(files) {
    const job = this.selected,
      expected = [...(job.sourceFiles || []), ...(job.previewFiles || [])],
      incoming = [...files];
    if (
      incoming.every((file) => !file.webkitRelativePath) &&
      new Set(expected.map((source) => source.path.split('/').pop())).size ===
        expected.length
    ) {
      for (const file of incoming) {
        const source = expected.find(
          (source) => source.path.split('/').pop() === file.name
        );
        if (source)
          Object.defineProperty(file, 'webkitRelativePath', {
            value: source.path
          });
      }
    }
    if (
      expected.length !== incoming.length ||
      expected.some(
        (source) =>
          !incoming.some(
            (file) =>
              sourcePath(file) === source.path && file.size === source.size
          )
      )
    ) {
      this.error = 'Choose the same source files shown in this operation.';
      return;
    }
    const resolve = (source) =>
      incoming.find((file) => sourcePath(file) === source.path);
    job.files = job.sourceFiles.map(resolve);
    job.previews = (job.previewFiles || []).map(resolve);
    job.file = job.files[0];
    job.status = 'Queued';
    job.error = '';
    this.changed();
    this.validateAll();
  },
  addPreviews(files) {
    if (!this.canEdit) return;
    const incoming = [...files];
    if (incoming.some((file) => !file.type.startsWith('image/'))) {
      this.error = 'Choose an image for the preview';
      return;
    }
    this.selected.previews.push(...incoming);
    this.changed();
    this.validateAll();
  },
  clearPreviews() {
    if (!this.canEdit) return;
    this.selected.previews = [];
    this.selected.previewFiles = [];
    this.changed();
    this.validateAll();
  },
  snapshot() {
    if (!this.docked) this.$refs.dialog.close();
    this.$emit('snapshot', this.selected);
  },
  paste(event) {
    if (this.canEdit && event.clipboardData?.files.length) {
      event.preventDefault();
      this.addPreviews(event.clipboardData.files);
    }
  },
  async pasteImage() {
    const job = this.selected,
      epoch = this.sessionEpoch;
    try {
      if (!navigator.clipboard?.read)
        throw new Error('Paste an image with Ctrl+V or choose a file on HTTP.');
      const files = [];
      for (const item of await navigator.clipboard.read()) {
        const type = item.types.find((type) => type.startsWith('image/'));
        if (type)
          files.push(
            new File(
              [await item.getType(type)],
              'clipboard-' + (files.length + 1) + '.' + type.split('/')[1],
              { type }
            )
          );
      }
      if (!files.length) throw new Error('No image in clipboard');
      if (this.ownsJob(job, epoch) && this.selected === job && editable(job))
        this.addPreviews(files);
    } catch (error) {
      if (this.ownsJob(job, epoch)) this.error = error.message;
    }
  },
  async capture() {
    const job = this.selected,
      epoch = this.sessionEpoch;
    let stream;
    try {
      if (!navigator.mediaDevices?.getDisplayMedia)
        throw new Error(
          'Screen capture requires HTTPS or localhost. Choose or paste an image instead.'
        );
      stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      if (!this.ownsJob(job, epoch)) return;
      const video = document.createElement('video');
      video.srcObject = stream;
      await video.play();
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext('2d').drawImage(video, 0, 0);
      const blob = await new Promise((resolve) =>
        canvas.toBlob(resolve, 'image/png')
      );
      if (
        this.ownsJob(job, epoch) &&
        this.selected === job &&
        editable(job) &&
        blob
      )
        this.addPreviews([
          new File([blob], 'screenshot.png', { type: 'image/png' })
        ]);
    } catch (error) {
      if (this.ownsJob(job, epoch)) this.error = error.message;
    } finally {
      stream?.getTracks().forEach((track) => track.stop());
    }
  }
};
