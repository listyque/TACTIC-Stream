import { taskGroup } from '../../../../src/tactic_stream/shared_ui/features/search/organization.mjs';
export {
  views as resultViews,
  groups as resultGroups
} from '../../../../src/tactic_stream/shared_ui/features/search/menus.ui.mjs';

// Original Handler view_state / results_organization names are persisted as-is.
export const defaultResultView = 'continious';

export function groupRecords(records, mode, nodes = [], organization = {}) {
  if (mode === 'none') return [{ key: '', label: '', records }];
  const groups = new Map(),
    byKey = new Map(nodes.map((node) => [node.record.__search_key__, node])),
    process = mode.startsWith('task_status:') ? mode.slice(12) : '',
    collator = new Intl.Collator(undefined, {
      numeric: true,
      sensitivity: 'base'
    });
  for (const record of records) {
    const node = byKey.get(record.__search_key__),
      task = process
        ? taskGroup(
            node?.tasks || [],
            process,
            organization.statuses?.[process] || [],
            node?.accent,
            collator.compare
          )
        : null,
      key = task
        ? task.key
        : mode === 'pipeline'
          ? record.pipeline_code || ''
          : record.status || record.state || '';
    if (!groups.has(key))
      groups.set(key, {
        key,
        label: task
          ? task.label
          : mode === 'pipeline'
            ? key || 'No pipeline'
            : key || 'No status',
        translate: task?.translate,
        rank: task?.rank || 0,
        accent: task?.accent,
        records: []
      });
    groups.get(key).records.push(record);
  }
  return [...groups.values()].sort(
    (left, right) =>
      left.rank - right.rank ||
      (!left.key
        ? 1
        : !right.key
          ? -1
          : collator.compare(left.label, right.label))
  );
}
