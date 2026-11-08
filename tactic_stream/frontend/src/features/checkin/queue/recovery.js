import { descriptors } from '../files.js';

export function queueId() {
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), (byte) =>
    byte.toString(16).padStart(2, '0')
  ).join('');
}

const storageKey = (login) => 'tactic_stream.commit_queue.' + login;
const prefix = (login) =>
  'tactic_stream.commit_queue_jobs.' + encodeURIComponent(login) + '.';
const recoveryError =
  'Queue recovery could not be saved. Keep this page open until pending work is complete.';

function record({
  ticket,
  id,
  files,
  file,
  previews,
  validating,
  plan,
  request,
  ...job
}) {
  return {
    ...job,
    sourceFiles: files?.length ? descriptors(files) : job.sourceFiles || [],
    previewFiles: previews?.length
      ? descriptors(previews)
      : job.previewFiles || []
  };
}

function restoreJob(job, ticket) {
  const active = ['Uploading', 'Checking in'].includes(job.status);
  const terminal = ['Complete', 'Skipped', 'Result unknown'].includes(
    job.status
  );
  return {
    ...job,
    ticket,
    files: [],
    previews: [],
    file: null,
    plan: null,
    validating: false,
    request: 0,
    status: terminal
      ? job.status
      : job.submission
        ? 'Checking in'
        : job.status === 'Checking in'
          ? 'Result unknown'
          : 'Missing files',
    error:
      active && !job.submission
        ? 'The page closed during check-in. Inspect Snapshot Browser before repeating it.'
        : job.error || ''
  };
}

export default {
  changed() {
    this.$emit('changed', this.jobs);
    if (!this.login) return false;
    try {
      for (const job of this.jobs) {
        const key = prefix(this.login) + job.recoveryId;
        const saved = JSON.stringify(record(job));
        if (this.persisted.get(key) !== saved) {
          localStorage.setItem(key, saved);
          this.persisted.set(key, saved);
        }
      }
      return true;
    } catch {
      this.error = recoveryError;
      return false;
    }
  },
  forgetJob(job) {
    const key = prefix(this.login) + job.recoveryId;
    try {
      localStorage.removeItem(key);
      this.persisted.delete(key);
    } catch {
      this.error = recoveryError;
    }
  },
  restore() {
    if (!this.login || !this.ticket) return;
    const oldKey = storageKey(this.login);
    const base = prefix(this.login);
    try {
      const legacy = JSON.parse(localStorage.getItem(oldKey) || '[]');
      if (Array.isArray(legacy) && legacy.length) {
        legacy.forEach((job, index) => {
          if (!job || typeof job.searchKey !== 'string') return;
          const id = 'legacy-' + index;
          if (localStorage.getItem(base + id) == null)
            localStorage.setItem(
              base + id,
              JSON.stringify({ ...job, recoveryId: id, queueOrder: index })
            );
        });
        localStorage.removeItem(oldKey);
      }
      for (const key of Object.keys(localStorage)) {
        if (key.startsWith(base))
          this.queueStorage({ key, newValue: localStorage.getItem(key) });
      }
    } catch {
      this.error = recoveryError;
    }
    this.selectedId ||= this.jobs[0]?.id || '';
    this.$emit('changed', this.jobs);
  },
  queueStorage({ key, newValue }) {
    const base = prefix(this.login);
    if (
      !this.login ||
      !this.ticket ||
      !key?.startsWith(base) ||
      this.persisted.get(key) === newValue
    )
      return;
    const id = key.slice(base.length);
    const index = this.jobs.findIndex((job) => job.recoveryId === id);
    const previous = this.jobs[index];
    if (
      this.running &&
      previous &&
      ['Uploading', 'Checking in'].includes(previous.status)
    )
      return;
    if (!newValue) {
      this.persisted.delete(key);
      if (index >= 0) this.jobs.splice(index, 1);
    } else {
      let saved;
      try {
        saved = JSON.parse(newValue);
      } catch {
        return;
      }
      if (
        !saved ||
        saved.recoveryId !== id ||
        typeof saved.searchKey !== 'string' ||
        typeof saved.project !== 'string'
      )
        return;
      const job = restoreJob(saved, this.ticket);
      job.id = previous?.id ?? ++this.sequence;
      if (
        previous?.file &&
        !['Complete', 'Skipped'].includes(job.status) &&
        JSON.stringify(descriptors(previous.files)) ===
          JSON.stringify(saved.sourceFiles) &&
        JSON.stringify(descriptors(previous.previews)) ===
          JSON.stringify(saved.previewFiles)
      ) {
        Object.assign(job, {
          files: previous.files,
          previews: previous.previews,
          file: previous.file
        });
        if (job.status === 'Missing files') job.status = saved.status;
      }
      this.persisted.set(key, JSON.stringify(record(job)));
      if (index >= 0) this.jobs.splice(index, 1, job);
      else this.jobs.push(job);
      this.jobs.sort(
        (left, right) =>
          (left.queueOrder || 0) - (right.queueOrder || 0) ||
          left.recoveryId.localeCompare(right.recoveryId)
      );
    }
    if (!this.selected) this.selectedId = this.jobs[0]?.id || '';
    this.$emit('changed', this.jobs);
  }
};
