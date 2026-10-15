// Tactic Frame: state transitions and shared Gantt layout calculations.
// Executed unchanged by Qt's JS engine and Vue. Dates retain their original time.
export const DAY = 24 * 60 * 60 * 1000;
const copy = (value) => JSON.parse(JSON.stringify(value));
export const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));
export const date = (value) => Date.parse(value.slice(0, 10) + "T00:00:00Z");
const iso = (millis) => new Date(millis).toISOString().slice(0, 10);
const timed = (day, original) => day + (original ? original.slice(10) : " 09:00:00");
export function stable(value) {
  if (Array.isArray(value)) return "[" + value.map(stable).join(",") + "]";
  if (value && typeof value === "object") return "{" + Object.keys(value).sort().map((key) => JSON.stringify(key) + ":" + stable(value[key])).join(",") + "}";
  return JSON.stringify(value);
}

export function initial(fixture) {
  // Repeated fixture rows exercise vertical scrolling without production data.
  const tasks = [];
  for (let block = 0; block < 3; block++) for (const record of fixture.records) {
    const task = copy(record);
    if (block) {
      task.taskCode += "-demo-" + block;
      task.parentTitle += " · " + (block + 1);
      if (task.start) {
        task.start = timed(iso(date(task.start) + block * 7 * DAY), task.start);
        task.end = timed(iso(date(task.end) + block * 7 * DAY), task.end);
      }
    }
    tasks.push(task);
  }
  return {
    tasks,
    selected: [],
    collapsed: [],
    zoom: 1,
    x: 0,
    y: 0,
    workingDays: false,
    undo: [],
    redo: [],
    drag: null
  };
}

export function rows(spec, state) {
  const groups = [];
  const result = [];
  let top = 0;
  for (const task of state.tasks) if (groups.indexOf(task.groupKey) < 0) groups.push(task.groupKey);
  for (const key of groups) {
    const tasks = state.tasks.filter((task) => task.groupKey === key);
    result.push({
      id: "group-" + key,
      group: true,
      key,
      text: tasks[0].group,
      top,
      height: spec.metrics.group,
      tasks
    });
    top += spec.metrics.group;
    if (state.collapsed.indexOf(key) < 0) for (const task of tasks) {
      result.push({
        id: task.taskCode,
        task,
        top,
        height: spec.metrics.row
      });
      top += spec.metrics.row;
    }
  }
  return {
    items: result,
    height: top
  };
}

export function geometry(spec, fixture, state, width, height) {
  const metrics = spec.metrics;
  const labels = Math.min(310, Math.max(220, width * .3));
  const viewport = Math.max(1, width - labels - 12);
  const days = fixture.gantt.days;
  const day = clamp(clamp(viewport / days, 10, 28) * state.zoom, 2, 80);
  const timeline = Math.max(viewport, days * day);
  const body = Math.max(1, height - metrics.toolbar - metrics.header - metrics.overview - metrics.footer);
  const list = rows(spec, state);
  const maxX = Math.max(0, timeline - viewport);
  const maxY = Math.max(0, list.height - body);
  return {
    labels,
    viewport,
    days,
    day,
    timeline,
    body,
    maxX,
    maxY,
    x: clamp(state.x, 0, maxX),
    y: clamp(state.y, 0, maxY),
    rows: list.items,
    contentHeight: list.height,
    bodyTop: metrics.toolbar + metrics.header
  };
}

function snapshot(state) {
  return copy(state.tasks);
}

function commit(state, tasks) {
  if (JSON.stringify(tasks) === JSON.stringify(state.tasks)) return state;
  return Object.assign({}, state, {
    tasks,
    undo: state.undo.concat([snapshot(state)]).slice(-30),
    redo: [],
    drag: null
  });
}

function shift(value, amount, working) {
  let day = date(value);
  let remaining = Math.abs(amount);
  let direction = amount < 0 ? -1 : 1;
  while (remaining) {
    day += direction * DAY;
    const weekday = new Date(day).getUTCDay();
    if (!working || weekday !== 0 && weekday !== 6) remaining--;
  }
  return timed(iso(day), value);
}

function altered(tasks, key, change) {
  return tasks.map((task) => task.taskCode === key ? Object.assign({}, task, change) : task);
}

export function transition(spec, fixture, state, event, width, height) {
  const layout = geometry(spec, fixture, state, width, height);
  switch (event.type) {
    case "select": return Object.assign({}, state, { selected: state.selected.indexOf(event.key) < 0 ? state.selected.concat([event.key]) : state.selected.filter((key) => key !== event.key) });
    case "select-all": return Object.assign({}, state, { selected: state.selected.length === state.tasks.length ? [] : state.tasks.map((task) => task.taskCode) });
    case "collapse": return Object.assign({}, state, {
      collapsed: state.collapsed.indexOf(event.key) < 0 ? state.collapsed.concat([event.key]) : state.collapsed.filter((key) => key !== event.key),
      y: 0
    });
    case "working": return Object.assign({}, state, { workingDays: !state.workingDays });
    case "scroll": return Object.assign({}, state, {
      x: clamp(layout.x + (event.dx || 0), 0, layout.maxX),
      y: clamp(layout.y + (event.dy || 0), 0, layout.maxY)
    });
    case "zoom":
    case "scale": {
      const zoom = event.type === "zoom" ? clamp(state.zoom * event.factor, .2, 5) : event.value === "days" ? 2.8 : event.value === "weeks" ? 1.2 : 1;
      const next = Object.assign({}, state, { zoom });
      const ng = geometry(spec, fixture, next, width, height);
      const anchor = event.x === undefined ? layout.viewport / 2 : clamp(event.x - layout.labels, 0, layout.viewport);
      next.x = clamp((layout.x + anchor) / layout.day * ng.day - anchor, 0, ng.maxX);
      return next;
    }
    case "today": return Object.assign({}, state, { x: clamp(fixture.gantt.todayDay * layout.day - layout.viewport / 2, 0, layout.maxX) });
    case "undo": return state.undo.length ? Object.assign({}, state, {
      tasks: copy(state.undo[state.undo.length - 1]),
      undo: state.undo.slice(0, -1),
      redo: state.redo.concat([snapshot(state)]),
      drag: null
    }) : state;
    case "redo": return state.redo.length ? Object.assign({}, state, {
      tasks: copy(state.redo[state.redo.length - 1]),
      redo: state.redo.slice(0, -1),
      undo: state.undo.concat([snapshot(state)]),
      drag: null
    }) : state;
    case "batch": {
      const tasks = copy(state.tasks);
      for (const task of tasks) if (state.selected.indexOf(task.taskCode) >= 0 && task.start && task.end) {
        if (event.mode === "shift") {
          task.start = shift(task.start, event.amount, state.workingDays);
          task.end = shift(task.end, event.amount, state.workingDays);
        } else if (event.mode === "duration") task.end = timed(iso(Math.max(date(task.start), date(task.end) + event.amount * DAY)), task.end);
        else throw Error("Unknown batch operation");
      }
      return commit(state, tasks);
    }
    case "schedule": {
      const start = iso(date(fixture.gantt.rangeStart) + fixture.gantt.todayDay * DAY);
      return commit(state, altered(state.tasks, event.key, {
        start: timed(start),
        end: iso(date(start) + 4 * DAY) + " 17:00:00"
      }));
    }
    case "progress-key": {
      const task = state.tasks.filter((task) => task.taskCode === event.key)[0];
      if (!task) throw Error("Invalid progress target");
      const progress = event.code === "Home" ? 0 : event.code === "End" ? 100 : task.progress + (event.code === "ArrowLeft" ? -1 : 1);
      return commit(state, altered(state.tasks, event.key, { progress: clamp(progress, 0, 100) }));
    }
    case "press": {
      if (event.mode === "overview" || event.mode === "vertical") return Object.assign({}, state, { drag: {
        mode: event.mode,
        x: event.x,
        y: event.y,
        scrollX: layout.x,
        scrollY: layout.y
      } });
      const task = state.tasks.filter((task) => task.taskCode === event.key)[0];
      if (!task || !task.start || !task.end || [
        "move",
        "start",
        "end",
        "progress"
      ].indexOf(event.mode) < 0) throw Error("Invalid drag target");
      const start = (date(task.start) - date(fixture.gantt.rangeStart)) / DAY;
      const duration = (date(task.end) - date(task.start)) / DAY + 1;
      return Object.assign({}, state, { drag: {
        mode: event.mode,
        key: event.key,
        x: event.x,
        y: event.y,
        dayWidth: layout.day,
        start,
        duration,
        base: snapshot(state),
        origin: task,
        left: layout.labels + start * layout.day - layout.x,
        width: Math.max(7, duration * layout.day - 4)
      } });
    }
    case "pointer": {
      if (!state.drag) return state;
      const drag = state.drag;
      if (drag.mode === "overview") return Object.assign({}, state, { x: clamp(drag.scrollX + (event.x - drag.x) * layout.timeline / layout.viewport, 0, layout.maxX) });
      if (drag.mode === "vertical") return Object.assign({}, state, { y: clamp(drag.scrollY + (event.y - drag.y) * layout.contentHeight / layout.body, 0, layout.maxY) });
      const delta = Math.round((event.x - drag.x) / drag.dayWidth);
      const change = {};
      if (drag.mode === "progress") change.progress = clamp(Math.round((event.x - drag.left) / drag.width * 100), 0, 100);
      else {
        let start = drag.start;
        let end = start + drag.duration - 1;
        if (drag.mode === "move") {
          start = clamp(start + delta, 0, layout.days - drag.duration);
          end = start + drag.duration - 1;
        }
        if (drag.mode === "start") start = clamp(start + delta, 0, end);
        if (drag.mode === "end") end = clamp(end + delta, start, layout.days - 1);
        change.start = timed(iso(date(fixture.gantt.rangeStart) + start * DAY), drag.origin.start);
        change.end = timed(iso(date(fixture.gantt.rangeStart) + end * DAY), drag.origin.end);
      }
      return Object.assign({}, state, { tasks: altered(drag.base, drag.key, change) });
    }
    case "release": {
      if (!state.drag) return state;
      const drag = state.drag;
      const next = Object.assign({}, state, { drag: null });
      if (!drag.base || JSON.stringify(drag.base) === JSON.stringify(state.tasks)) return next;
      return Object.assign({}, next, {
        undo: state.undo.concat([drag.base]).slice(-30),
        redo: []
      });
    }
    case "cancel": return state.drag ? Object.assign({}, state, {
      tasks: state.drag.base || state.tasks,
      drag: null
    }) : state;
    default: throw Error("Unknown Gantt action: " + event.type);
  }
}
