import { descriptors } from '../files.js';

export default {
  changed() {
    this.$emit('changed', this.jobs);
    try {
      localStorage.setItem(
        'tactic_stream.commit_queue.' + this.login,
        JSON.stringify(
          this.jobs.map(
            ({ ticket, files, file, previews, validating, plan, ...job }) => ({
              ...job,
              sourceFiles: files?.length
                ? descriptors(files)
                : job.sourceFiles || [],
              previewFiles: previews?.length
                ? descriptors(previews)
                : job.previewFiles || []
            })
          )
        )
      );
    } catch {
      this.error =
        'Queue recovery could not be saved. Keep this page open until pending work is complete.';
    }
  },
  restore() {
    if (this.pending || this.running) return;
    let saved = [];
    try {
      saved = JSON.parse(
        localStorage.getItem('tactic_stream.commit_queue.' + this.login) || '[]'
      );
    } catch {
      /* Empty queue. */
    }
    this.jobs = Array.isArray(saved)
      ? saved
          .filter(
            (job) =>
              job &&
              typeof job.searchKey === 'string' &&
              typeof job.project === 'string'
          )
          .map((job) => ({
            ...job,
            id: ++this.sequence,
            ticket: this.ticket,
            files: [],
            previews: [],
            file: null,
            plan: null,
            validating: false,
            status:
              job.status === 'Checking in'
                ? 'Result unknown'
                : ['Complete', 'Skipped', 'Result unknown'].includes(job.status)
                  ? job.status
                  : 'Missing files',
            error: ['Uploading', 'Checking in'].includes(job.status)
              ? 'The page closed during check-in. Inspect Snapshot Browser before repeating it.'
              : job.error || ''
          }))
      : [];
    this.selectedId = this.jobs[0]?.id || '';
    this.$emit('changed', this.jobs);
  }
};
