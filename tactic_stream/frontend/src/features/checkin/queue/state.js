import { t } from '../../../i18n.js';
import { sourcePath } from '../files.js';
import {
  fileName,
  extension
} from '../../../../../src/tactic_stream/shared_ui/features/files/file_values.mjs';

export const editable = (job) =>
  !!job &&
  ![
    'Uploading',
    'Checking in',
    'Complete',
    'Skipped',
    'Result unknown'
  ].includes(job.status);

export function record(job, owner) {
  if (!job) return {};
  const canEdit =
      !owner.running && editable(job) && !!job.file && !job.submission,
    canOptions = canEdit && !job.ingest && !job.preview,
    status =
      job.status === 'Complete'
        ? 'Completed'
        : ['Uploading', 'Checking in'].includes(job.status)
          ? 'Running'
          : job.status === 'Queued'
            ? job.validating
              ? 'Validating'
              : job.planError
                ? 'Invalid'
                : 'Prepared'
            : job.status,
    canCommit =
      !owner.running &&
      editable(job) &&
      !!job.file &&
      !job.validating &&
      !job.planError &&
      job.status !== 'Cancelled';
  return {
    operationId: String(job.id),
    title: job.name,
    objectTitle: job.title,
    fileCount: job.files.length || job.sourceFiles?.length || 0,
    context: job.context,
    contextBranch: job.context.split('/').slice(1).join('/'),
    process: job.process,
    description: job.description,
    repository: job.repositoryAlias,
    version: job.version,
    mode: 'upload',
    explicitFilename: job.explicitFilename,
    contextAsFilename: job.contextAsFilename,
    updateVersionless: job.updateVersionless,
    onlyVersionless: job.onlyVersionless,
    keepFileName: job.keepFileName,
    generatePreviews: job.generatePreviews,
    versionlessAllowed: canOptions && !job.isRevision,
    selected: job.id === owner.selectedId,
    checked: job.checked,
    status,
    canEdit,
    canCheck: !owner.running && editable(job),
    canOptions,
    canDescription: canEdit && !job.ingest,
    canRepository: canOptions && !job.isRevision,
    canVersion: canOptions,
    canContext: canOptions && !job.isRevision,
    canPreview: canOptions,
    canNaming:
      !!owner.canAdminister && !owner.running && !job.ingest && !job.preview,
    canCommit,
    canRetry: !!job.file && ['Failed', 'Cancelled'].includes(job.status),
    canCancel:
      canEdit ||
      (!!job.submission &&
        !['Complete', 'Skipped', 'Result unknown'].includes(job.status)),
    canRemove:
      !job.submission ||
      ['Complete', 'Skipped', 'Result unknown'].includes(job.status),
    canInspect: !!job.snapshot || job.status === 'Result unknown',
    needsFiles: job.status === 'Missing files',
    previewCount: job.previews.length,
    previewExtension: extension(job.files[0]?.name || job.name),
    futureFileName: fileName(
      job.plan?.files[0]?.versioned?.[0] || job.explicitFilename || job.name
    ),
    progress: job.progress,
    stage: ['Uploading', 'Checking in'].includes(job.status)
      ? t(job.status)
      : '',
    error: t(job.error),
    validationError: t(job.planError),
    naming: (job.plan?.files || []).map((file, index) => ({
      key: String(index),
      title: file.title,
      versioned: file.versioned,
      versionless: file.versionless
    }))
  };
}

export function sourceFiles(job, canRemove) {
  if (!job) return [];
  const sources = job.files.length
      ? job.files.map((file) => ({ path: sourcePath(file), size: file.size }))
      : job.sourceFiles || [],
    previews = job.previews.length
      ? job.previews.map((file) => ({
          path: sourcePath(file),
          size: file.size
        }))
      : job.previewFiles || [],
    targets = new Map();
  for (const group of job.plan?.files || []) {
    group.indices.forEach((index, member) =>
      targets.set(index, group.versioned[member] || '')
    );
  }
  return [
    ...sources.map((file, index) => ({
      key: 'main_' + index,
      index,
      path: file.path,
      target: targets.get(index) || '',
      preview: false,
      canRemove
    })),
    ...previews.map((file, index) => ({
      key: 'preview_' + index,
      index,
      path: file.path,
      target: targets.get(sources.length + index) || '',
      preview: true,
      canRemove
    }))
  ];
}

export function previewFiles(jobs) {
  const result = Object.create(null);
  for (const job of jobs) {
    result[String(job.id)] =
      job.previews[0] ||
      (job.files[0]?.type.startsWith('image/') ? job.files[0] : undefined);
    job.previews.forEach((file, index) => {
      result[job.id + ':preview:' + index] = file;
    });
  }
  return result;
}

export function model(owner, rows, files) {
  const selected = owner.jobs.find((job) => job.id === owner.selectedId),
    current =
      rows.find((row) => row.operationId === String(owner.selectedId)) || {};
  return {
    record: current,
    count: rows.length,
    selected: owner.jobs.indexOf(selected),
    busy: owner.running,
    autoClean: owner.preferences.checkin.commitQueueAutoClean,
    applyChecked: owner.applyChecked,
    advanced: owner.advanced,
    details: owner.mobileDetails,
    namingExpanded: owner.namingExpanded,
    paneWidth: owner.width,
    filesHeight: owner.filesHeight,
    contextEditing: owner.contextEditing,
    contextDraft: owner.contextBranch,
    versionDraft: owner.versionDraft,
    versionError: owner.versionError,
    filenameDraft: owner.filenameDraft,
    descriptionDraft: owner.descriptionDraft,
    localMethods: false,
    serverQueueAvailable: false,
    clipboardKnown: false,
    cancelPrepared: true,
    hasReady: !owner.versionError && rows.some((row) => row.canCommit),
    hasCheckedReady: rows.some((row) => row.checked && row.canCommit),
    hasCompleted: rows.some((row) => row.status === 'Completed'),
    canCancel: true,
    fileCount: files.length,
    sourceTargets: files.some((file) => !!file.target),
    repositories: owner.repositoryOptions,
    duplicate: !!owner.duplicate,
    canReplace: !owner.jobs.some(
      (job) =>
        job.id === owner.duplicate?.oldId &&
        (job.submission ||
          ['Uploading', 'Checking in', 'Result unknown'].includes(job.status))
    ),
    error: t(owner.error)
  };
}
