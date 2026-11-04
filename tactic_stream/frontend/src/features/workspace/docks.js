// Handler workspace_models/docks_tree.py, docks_records.py, EPL-1.0.
import * as DockLayout from '../../../../src/tactic_stream/shared_ui/shell/dock.layout.mjs';
export const dockPanels = [
  { id: 'results', title: 'Results', icon: 'search', closable: false },
  {
    id: 'advanced_search',
    title: 'Advanced Search',
    icon: 'advanced-search',
    closable: true
  },
  {
    id: 'task_calendar',
    title: 'Task Calendar',
    icon: 'MDI_CALENDAR_MONTH',
    closable: true
  },
  {
    id: 'tasks',
    title: 'Task Manager',
    icon: 'MDI_CLIPBOARD_TEXT_OUTLINE',
    closable: true
  },
  { id: 'notes', title: 'Task Inspector', icon: 'comment', closable: true },
  {
    id: 'timesheet',
    title: 'Timesheet',
    icon: 'MDI_CLOCK_OUTLINE',
    closable: true
  },
  {
    id: 'work_reports',
    title: 'Work reports',
    icon: 'MDI_CHART_BAR',
    closable: true
  },
  {
    id: 'cost_reports',
    title: 'Cost Reports',
    icon: 'MDI_CHART_BAR',
    closable: true
  },
  { id: 'commit_queue', title: 'Commit Queue', icon: 'queue', closable: true },
  {
    id: 'description',
    title: 'Description',
    icon: 'description',
    closable: true
  },
  {
    id: 'snapshot',
    title: 'Snapshot Browser',
    icon: 'snapshot',
    closable: true
  },
  {
    id: 'knowledge',
    title: 'Knowledge Base',
    icon: 'book-open',
    closable: true
  },
  { id: 'drop_plate', title: 'Drop Plate', icon: 'upload', closable: true }
];
export const defaultStackTargets = {
  snapshot: 'notes',
  description: 'notes',
  task_calendar: 'notes',
  timesheet: 'notes',
  work_reports: 'notes',
  cost_reports: 'notes',
  knowledge: 'notes',
  drop_plate: 'tasks',
  commit_queue: 'results'
};
export const stack = (id) => ({ type: 'stack', panels: [id], active: id });
// Handler capture_layout document: shared presets keep its native panel records.
export function captureLayout(state) {
  return {
    layout: JSON.parse(JSON.stringify(state.layout || stack('results'))),
    panels: dockPanels.map((panel) => {
      const value = state.panels[panel.id],
        [x, y, width, height] = value.rect;
      return {
        panel_id: panel.id,
        title: panel.id === 'tasks' ? 'Tasks' : panel.title,
        kind: panel.id,
        x,
        y,
        width,
        height,
        visible: value.visible,
        closable: panel.closable,
        z: value.z,
        dock_area: value.slide
          ? 'slide_' + value.slide
          : value.floating
            ? 'floating'
            : 'docked',
        detached: false
      };
    })
  };
}
export function decodeLayout(value) {
  if (!value || !Array.isArray(value.panels) || !value.layout)
    throw new Error('Invalid layout preset');
  const state = defaults(),
    known = dockPanels.map((panel) => panel.id);
  for (const panel of value.panels) {
    if (!known.includes(panel.panel_id)) {
      if (panel.visible)
        throw new Error(
          'This layout requires panels that have not been migrated yet.'
        );
      continue;
    }
    const rect = [panel.x, panel.y, panel.width, panel.height];
    if (
      !rect.every(Number.isFinite) ||
      rect[2] <= 0 ||
      rect[3] <= 0 ||
      !Number.isFinite(panel.z) ||
      typeof panel.visible !== 'boolean'
    )
      throw new Error('Invalid layout preset');
    if (panel.detached)
      throw new Error(
        'Detached workspace windows are not supported in this browser.'
      );
    const slide =
      panel.panel_id !== 'results' && panel.dock_area === 'slide_left'
        ? 'left'
        : panel.panel_id !== 'results' && panel.dock_area === 'slide_right'
          ? 'right'
          : '';
    state.panels[panel.panel_id] = {
      visible: panel.panel_id === 'results' || panel.visible,
      floating: panel.dock_area === 'floating',
      slide,
      rect,
      z: panel.z
    };
  }
  state.layout = readTree(value.layout);
  if (!state.layout) throw new Error('Invalid layout preset');
  for (const panel of dockPanels)
    if (
      state.panels[panel.id].visible &&
      !state.panels[panel.id].floating &&
      !state.panels[panel.id].slide &&
      !ids(state.layout).includes(panel.id)
    )
      state.layout = place(
        state.layout,
        panel.id,
        panel.id === 'results' ? 'left' : 'right'
      );
  restorePresentation(state, value.presentation);
  return state;
}
function restorePresentation(state, value) {
  const available = (id) =>
    dockPanels.some((panel) => panel.id === id) && state.panels[id].visible;
  state.maximized = available(value?.maximized) ? value.maximized : '';
  state.compactActive = dockPanels.some(
    (panel) => panel.id === value?.compactActive
  )
    ? value.compactActive
    : 'results';
}
export const ids = (node) =>
  !node
    ? []
    : node.type === 'stack'
      ? node.panels
      : [...ids(node.first), ...ids(node.second)];
export function readTree(value, allowed = dockPanels.map((panel) => panel.id)) {
  const seen = new Set();
  function read(node, depth = 0) {
    if (!node || typeof node !== 'object' || depth > 64) return null;
    if (node.type === 'stack') {
      const panels = (Array.isArray(node.panels) ? node.panels : []).filter(
        (id) => {
          if (!allowed.includes(id) || seen.has(id)) return false;
          seen.add(id);
          return true;
        }
      );
      return panels.length
        ? {
            type: 'stack',
            panels,
            active: panels.includes(node.active) ? node.active : panels[0]
          }
        : null;
    }
    if (
      node.type !== 'split' ||
      !['horizontal', 'vertical'].includes(node.orientation)
    )
      return null;
    const first = read(node.first, depth + 1),
      second = read(node.second, depth + 1);
    if (!first || !second) return first || second;
    const ratio = Number(node.ratio);
    return {
      type: 'split',
      orientation: node.orientation,
      ratio: Number.isFinite(ratio)
        ? Math.max(0.02, Math.min(0.98, ratio))
        : 0.5,
      first,
      second
    };
  }
  return read(value);
}
export function remove(node, id) {
  if (!node) return null;
  if (node.type === 'stack') {
    const panels = node.panels.filter((value) => value !== id);
    return panels.length
      ? {
          ...node,
          panels,
          active: panels.includes(node.active) ? node.active : panels[0]
        }
      : null;
  }
  const first = remove(node.first, id),
    second = remove(node.second, id);
  return first && second ? { ...node, first, second } : first || second;
}
export function activate(node, id) {
  if (!node) return null;
  if (node.type === 'stack')
    return node.panels.includes(id) ? { ...node, active: id } : node;
  return {
    ...node,
    first: activate(node.first, id),
    second: activate(node.second, id)
  };
}
export function place(node, id, side, target = '') {
  if (id === target) return node;
  if (side === 'swap' && ids(node).includes(id) && ids(node).includes(target)) {
    function swap(current) {
      const replace = (value) =>
        value === id ? target : value === target ? id : value;
      return current.type === 'stack'
        ? {
            ...current,
            panels: current.panels.map(replace),
            active: replace(current.active)
          }
        : {
            ...current,
            first: swap(current.first),
            second: swap(current.second)
          };
    }
    return swap(node);
  }
  if (side === 'swap') side = 'right';
  node = remove(node, id);
  if (!node) return stack(id);
  const split = (current, ratio) => ({
    type: 'split',
    orientation: ['top', 'bottom'].includes(side) ? 'vertical' : 'horizontal',
    ratio,
    first: ['left', 'top'].includes(side) ? stack(id) : current,
    second: ['left', 'top'].includes(side) ? current : stack(id)
  });
  if (target && ids(node).includes(target)) {
    function insert(current) {
      if (current.type === 'stack')
        return !current.panels.includes(target)
          ? current
          : side === 'center'
            ? { ...current, panels: [...current.panels, id], active: id }
            : split(current, 0.5);
      return {
        ...current,
        first: insert(current.first),
        second: insert(current.second)
      };
    }
    return insert(node);
  }
  return split(
    node,
    { left: 0.28, right: 0.66, top: 0.28, bottom: 0.7 }[side] || 0.5
  );
}
export const panelKinds = Object.fromEntries(
  dockPanels.map((panel) => [panel.id, panel.id])
);
export function projectTree(node, available, width, height) {
  return DockLayout.project(
    node,
    available,
    DockLayout.normalizedSizes(panelKinds, width, height)
  );
}
export function resizeTree(node, available, width, height, path, ratio) {
  return DockLayout.resize(
    node,
    path,
    ratio,
    available,
    DockLayout.normalizedSizes(panelKinds, width, height)
  );
}
export function defaults() {
  return {
    maximized: '',
    compactActive: 'results',
    layout: stack('results'),
    panels: Object.fromEntries(
      dockPanels.map((panel) => [
        panel.id,
        {
          visible: panel.id === 'results',
          floating: false,
          slide: '',
          rect: [0.16, 0.12, 0.68, 0.72],
          z: 1
        }
      ])
    )
  };
}
export function readDocks(login) {
  const state = defaults();
  try {
    const saved = JSON.parse(
      localStorage.getItem('tactic_stream.docks.' + login)
    );
    state.layout = readTree(saved?.layout) || state.layout;
    for (const panel of dockPanels) {
      const value = saved?.panels?.[panel.id];
      if (!value || typeof value !== 'object') continue;
      const rect = value.rect;
      const slide =
        panel.id !== 'results' && ['left', 'right'].includes(value.slide)
          ? value.slide
          : '';
      state.panels[panel.id] = {
        visible: panel.closable ? value.visible === true : true,
        floating: !slide && value.floating === true,
        slide,
        z: Number.isFinite(value.z)
          ? Math.max(1, Math.min(1000000, value.z))
          : 1,
        rect:
          Array.isArray(rect) &&
          rect.length === 4 &&
          rect.every(Number.isFinite)
            ? [
                Math.max(0, Math.min(0.8, rect[0])),
                Math.max(0, Math.min(0.8, rect[1])),
                Math.max(0.2, Math.min(1, rect[2])),
                Math.max(0.16, Math.min(1, rect[3]))
              ]
            : [0.16, 0.12, 0.68, 0.72]
      };
      if (
        !state.panels[panel.id].floating &&
        !state.panels[panel.id].slide &&
        !ids(state.layout).includes(panel.id) &&
        state.panels[panel.id].visible
      )
        state.layout = place(
          state.layout,
          panel.id,
          panel.id === 'tasks' ? 'center' : 'right'
        );
    }
    if (
      !state.panels.results.floating &&
      !ids(state.layout).includes('results')
    )
      state.layout = place(state.layout, 'results', 'left');
    restorePresentation(state, saved);
  } catch {
    /* Invalid preferences never prevent opening the workspace. */
  }
  return state;
}
