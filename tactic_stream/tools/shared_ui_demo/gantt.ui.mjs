// Tactic Frame: shared Gantt UI. Coordinates are relative to their layer.
import { DAY, clamp, date, geometry } from "./gantt.state.mjs";

function blend(first, second, amount) {
  const channels = [1, 3, 5].map((offset) => {
    const a = parseInt(first.slice(offset, offset + 2), 16);
    const b = parseInt(second.slice(offset, offset + 2), 16);
    return Math.round(a * (1 - amount) + b * amount).toString(16).padStart(2, "0");
  });
  return "#" + channels.join("");
}

export function scene(spec, fixture, state, width, height, palette, language) {
  const layout = geometry(spec, fixture, state, width, height);
  const metrics = spec.metrics;
  const translate = (text) => language === "ru" ? spec.strings[text] || text : text;
  const layers = [];
  const colors = palette;
  function layer(id, rect) {
    const result = Object.assign({
      id,
      nodes: []
    }, rect);
    layers.push(result);
    return result.nodes;
  }
  function add(nodes, kind, id, properties) {
    if (["Label", "Rectangle", "Button", "CheckBox"].indexOf(kind) < 0) {
      throw Error("Unknown primitive");
    }
    const node = Object.assign({
      kind,
      id,
      text: "",
      color: colors.primaryText,
      background: "transparent",
      border: "transparent",
      radius: 0,
      fontSize: metrics.font,
      bold: false,
      align: "left",
      enabled: true,
      checked: false,
      highlighted: false,
      action: null,
      drag: null,
      keyAction: null,
      a11yLabel: ""
    }, properties);
    nodes.push(node);
    return node;
  }
  const toolbar = layer("toolbar", {
    x: 0,
    y: 0,
    width,
    height: metrics.toolbar
  });
  add(toolbar, "Rectangle", "toolbar-bg", {
    x: 0,
    y: 0,
    width,
    height: metrics.toolbar,
    background: colors.surfaceContainerHigh
  });
  add(toolbar, "Label", "title", {
    x: 12,
    y: 0,
    width: 210,
    height: metrics.toolbar,
    text: translate("Task schedule"),
    bold: true,
    fontSize: 16
  });
  const buttons = [
    { id: "undo", text: "Undo", action: { type: "undo" }, enabled: !!state.undo.length },
    { id: "redo", text: "Redo", action: { type: "redo" }, enabled: !!state.redo.length },
    { id: "today", text: "Today", action: { type: "today" }, enabled: true },
    { id: "auto", text: "Auto", action: { type: "scale", value: "auto" }, enabled: true },
    { id: "days", text: "Days", action: { type: "scale", value: "days" }, enabled: true },
    { id: "weeks", text: "Weeks", action: { type: "scale", value: "weeks" }, enabled: true },
    { id: "zoom-out", text: "−", action: { type: "zoom", factor: .8 }, enabled: state.zoom > .2 },
    { id: "zoom-in", text: "+", action: { type: "zoom", factor: 1.25 }, enabled: state.zoom < 5 }
  ];
  let buttonX = 228;
  for (const button of buttons) {
    const buttonWidth = button.id.indexOf("zoom") === 0 ? 36 : 76;
    add(toolbar, "Button", button.id, {
      x: buttonX,
      y: 6,
      width: buttonWidth,
      height: 36,
      text: translate(button.text),
      action: button.action,
      enabled: button.enabled
    });
    buttonX += buttonWidth + 6;
  }
  const header = layer("header", {
    x: 0,
    y: metrics.toolbar,
    width: layout.labels,
    height: metrics.header
  });
  add(header, "Rectangle", "header-bg", {
    x: 0,
    y: 0,
    width: layout.labels,
    height: metrics.header,
    background: colors.surfaceContainerHigh
  });
  add(header, "CheckBox", "select-all", {
    x: 10,
    y: 8,
    width: 27,
    height: 38,
    checked: state.selected.length === state.tasks.length,
    action: { type: "select-all" },
    text: translate("Tasks")
  });
  add(header, "Label", "task-heading", {
    x: 49,
    y: 0,
    width: layout.labels - 58,
    height: metrics.header,
    text: translate("Tasks") + " · " + state.tasks.length,
    bold: true
  });
  const timeHeader = layer("ticks", {
    x: layout.labels,
    y: metrics.toolbar,
    width: layout.viewport,
    height: metrics.header
  });
  add(timeHeader, "Rectangle", "ticks-bg", {
    x: 0,
    y: 0,
    width: layout.timeline,
    height: metrics.header,
    background: colors.surfaceContainerHigh
  });
  const timeline = layer("timeline", {
    x: layout.labels,
    y: layout.bodyTop,
    width: layout.viewport,
    height: layout.body
  });
  const taskLabels = layer("labels", {
    x: 0,
    y: layout.bodyTop,
    width: layout.labels,
    height: layout.body
  });
  const monthsEN = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec"
  ];
  const monthsRU = [
    "янв",
    "фев",
    "мар",
    "апр",
    "май",
    "июн",
    "июл",
    "авг",
    "сен",
    "окт",
    "ноя",
    "дек"
  ];
  for (let i = 0; i < layout.days; i++) {
    const dayDate = new Date(date(fixture.gantt.rangeStart) + i * DAY);
    const weekend = dayDate.getUTCDay() === 0 || dayDate.getUTCDay() === 6;
    const x = i * layout.day - layout.x;
    add(timeline, "Rectangle", "day-" + i, {
      x,
      y: 0,
      width: layout.day,
      height: layout.body,
      background: weekend ? blend(colors.workspace, colors.surfaceContainerHigh, .35) : "transparent"
    });
    add(timeline, "Rectangle", "grid-" + i, {
      x,
      y: 0,
      width: dayDate.getUTCDate() === 1 ? 2 : 1,
      height: layout.body,
      background: layout.day >= 16 || dayDate.getUTCDay() === 1 || dayDate.getUTCDate() === 1 ? colors.outlineVariant : "transparent"
    });
    if (layout.day >= 22 || (layout.day >= 7 ? dayDate.getUTCDay() === 1 : dayDate.getUTCDate() === 1)) {
      add(timeHeader, "Label", "tick-" + i, {
        x: x + 4,
        y: 22,
        width: layout.day >= 22 ? layout.day - 4 : Math.max(40, layout.day * 7 - 8),
        height: 30,
        text: String(dayDate.getUTCDate()) + (layout.day >= 22 ? "" : " " + (language === "ru" ? monthsRU : monthsEN)[dayDate.getUTCMonth()]),
        fontSize: metrics.micro,
        color: colors.secondaryText
      });
    }
    if (i === 0 || dayDate.getUTCDate() === 1) add(timeHeader, "Label", "month-" + i, {
      x: x + 4,
      y: 0,
      width: Math.max(100, layout.day * 25),
      height: 24,
      text: (language === "ru" ? monthsRU : monthsEN)[dayDate.getUTCMonth()] + " " + dayDate.getUTCFullYear(),
      bold: true
    });
  }
  for (const row of layout.rows) {
    const y = row.top - layout.y;
    const key = row.id;
    if (row.group) {
      add(taskLabels, "Rectangle", key, {
        x: 0,
        y,
        width: layout.labels,
        height: row.height,
        background: colors.surfaceContainerHigh,
        action: {
          type: "collapse",
          key: row.key
        }
      });
      add(taskLabels, "Label", key + "-label", {
        x: 12,
        y,
        width: layout.labels - 24,
        height: row.height,
        text: (state.collapsed.indexOf(row.key) < 0 ? "− " : "+ ") + row.text + " (" + row.tasks.length + ")",
        fontSize: metrics.micro,
        bold: true,
        action: {
          type: "collapse",
          key: row.key
        }
      });
      add(timeline, "Rectangle", key + "-bg", {
        x: 0,
        y,
        width: layout.timeline,
        height: row.height,
        background: colors.surfaceContainerHigh
      });
      const scheduled = row.tasks.filter((task) => task.start && task.end);
      if (scheduled.length) {
        const startMillis = Math.min.apply(null, scheduled.map((task) => date(task.start)));
        const endMillis = Math.max.apply(null, scheduled.map((task) => date(task.end)));
        add(timeline, "Rectangle", key + "-summary", {
          x: (startMillis - date(fixture.gantt.rangeStart)) / DAY * layout.day - layout.x,
          y: y + 9,
          width: (endMillis - startMillis) / DAY * layout.day + layout.day,
          height: 9,
          background: colors.secondaryText,
          radius: 3
        });
      }
      continue;
    }
    const task = row.task;
    const selected = state.selected.indexOf(key) >= 0;
    const color = task.statusColor || colors.action;
    add(taskLabels, "Rectangle", key + "-bg", {
      x: 0,
      y,
      width: layout.labels,
      height: row.height,
      background: selected ? colors.rowHover : colors.workspace,
      action: {
        type: "select",
        key
      }
    });
    add(timeline, "Rectangle", key + "-row", {
      x: 0,
      y,
      width: layout.timeline,
      height: row.height,
      background: selected ? colors.rowHover : "transparent"
    });
    add(taskLabels, "Rectangle", key + "-accent", {
      x: 0,
      y: y + 5,
      width: 3,
      height: row.height - 10,
      background: color,
      radius: 1
    });
    add(taskLabels, "CheckBox", key + "-check", {
      x: 10,
      y: y + 7,
      width: 27,
      height: 36,
      checked: selected,
      text: task.parentTitle,
      action: {
        type: "select",
        key
      }
    });
    add(taskLabels, "Label", key + "-title", {
      x: 46,
      y: y + 4,
      width: layout.labels - 54,
      height: 23,
      text: task.parentTitle,
      action: {
        type: "select",
        key
      }
    });
    add(taskLabels, "Label", key + "-detail", {
      x: 46,
      y: y + 27,
      width: layout.labels - 54,
      height: 18,
      text: task.processLabel + " · " + translate(task.assignedLabel),
      fontSize: metrics.micro,
      color: colors.secondaryText
    });
    add(taskLabels, "Rectangle", key + "-divider", {
      x: 0,
      y: y + row.height - 1,
      width: layout.labels,
      height: 1,
      background: colors.outlineVariant
    });
    add(timeline, "Rectangle", key + "-divider-time", {
      x: 0,
      y: y + row.height - 1,
      width: layout.timeline,
      height: 1,
      background: colors.outlineVariant
    });
    if (!task.start || !task.end) {
      add(timeline, "Button", key + "-schedule", {
        x: 12,
        y: y + 8,
        width: 150,
        height: 34,
        text: translate("Set dates"),
        action: {
          type: "schedule",
          key
        }
      });
      continue;
    }
    const start = (date(task.start) - date(fixture.gantt.rangeStart)) / DAY;
    const duration = (date(task.end) - date(task.start)) / DAY + 1;
    const left = start * layout.day - layout.x;
    const w = Math.max(7, duration * layout.day - 4);
    const barY = y + 11;
    add(timeline, "Rectangle", key + "-bar", {
      x: left,
      y: barY,
      width: w,
      height: metrics.bar,
      background: colors.workspace,
      border: color,
      radius: 6,
      drag: {
        mode: "move",
        key
      }
    });
    add(timeline, "Rectangle", key + "-fill", {
      x: left + 1,
      y: barY + 1,
      width: Math.max(0, (w - 2) * task.progress / 100),
      height: metrics.bar - 2,
      background: color,
      radius: 5,
      drag: {
        mode: "move",
        key
      }
    });
    add(timeline, "Label", key + "-bar-label", {
      x: left + 12,
      y: barY,
      width: Math.max(0, w - 24),
      height: metrics.bar,
      text: task.progress + "% · " + translate(task.status),
      fontSize: metrics.micro,
      align: "center",
      drag: {
        mode: "move",
        key
      }
    });
    add(timeline, "Rectangle", key + "-start", {
      x: left,
      y: barY,
      width: metrics.handle,
      height: metrics.bar,
      background: color,
      radius: 3,
      drag: {
        mode: "start",
        key
      }
    });
    add(timeline, "Rectangle", key + "-end", {
      x: left + w - metrics.handle,
      y: barY,
      width: metrics.handle,
      height: metrics.bar,
      background: color,
      radius: 3,
      drag: {
        mode: "end",
        key
      }
    });
    add(timeline, "Rectangle", key + "-progress", {
      x: left + clamp(w * task.progress / 100, 7, w - 7) - 4,
      y: barY + metrics.bar - 6,
      width: 8,
      height: 10,
      background: colors.primaryText,
      border: colors.workspace,
      radius: 3,
      drag: {
        mode: "progress",
        key
      },
      keyAction: {
        type: "progress-key",
        key
      },
      a11yLabel: task.parentTitle + " · " + task.progress + "%"
    });
  }
  const todayX = fixture.gantt.todayDay * layout.day - layout.x;
  add(timeline, "Rectangle", "today-line", {
    x: todayX,
    y: 0,
    width: 2,
    height: layout.body,
    background: colors.action
  });
  add(timeHeader, "Rectangle", "today-header", {
    x: todayX,
    y: 0,
    width: 2,
    height: metrics.header,
    background: colors.action
  });
  const overview = layer("overview", {
    x: layout.labels,
    y: layout.bodyTop + layout.body,
    width: layout.viewport,
    height: metrics.overview
  });
  add(overview, "Rectangle", "overview-bg", {
    x: 0,
    y: 0,
    width: layout.viewport,
    height: metrics.overview,
    background: colors.surfaceContainerHigh
  });
  for (const task of state.tasks) if (task.start && task.end) add(overview, "Rectangle", task.taskCode + "-overview", {
    x: (date(task.start) - date(fixture.gantt.rangeStart)) / DAY / layout.days * layout.viewport,
    y: 10,
    width: Math.max(2, ((date(task.end) - date(task.start)) / DAY + 1) / layout.days * layout.viewport),
    height: 8,
    background: task.statusColor || colors.action,
    radius: 2
  });
  add(overview, "Rectangle", "overview-thumb", {
    x: layout.x / layout.timeline * layout.viewport,
    y: 3,
    width: layout.viewport / layout.timeline * layout.viewport,
    height: 24,
    background: "transparent",
    border: colors.action,
    radius: 6,
    drag: { mode: "overview" }
  });
  const vertical = layer("vertical", {
    x: width - 12,
    y: layout.bodyTop,
    width: 12,
    height: layout.body
  });
  add(vertical, "Rectangle", "vtrack", {
    x: 0,
    y: 0,
    width: 12,
    height: layout.body,
    background: colors.workspace
  });
  add(vertical, "Rectangle", "vthumb", {
    x: 3,
    y: layout.contentHeight > layout.body ? layout.y / layout.contentHeight * layout.body : 0,
    width: 6,
    height: Math.min(layout.body, layout.body / Math.max(1, layout.contentHeight) * layout.body),
    background: colors.outline,
    radius: 3,
    drag: { mode: "vertical" }
  });
  const footer = layer("footer", {
    x: 0,
    y: height - metrics.footer,
    width,
    height: metrics.footer
  });
  add(footer, "Rectangle", "footer-bg", {
    x: 0,
    y: 0,
    width,
    height: metrics.footer,
    background: colors.surfaceContainerHigh
  });
  add(footer, "Label", "selected-count", {
    x: 12,
    y: 0,
    width: 126,
    height: metrics.footer,
    text: translate("Selected") + ": " + state.selected.length,
    fontSize: metrics.micro
  });
  add(footer, "CheckBox", "working-days", {
    x: 140,
    y: 4,
    width: 168,
    height: 36,
    text: translate("Working days"),
    checked: state.workingDays,
    action: { type: "working" },
    showLabel: true
  });
  buttonX = 314;
  const batchActions = [
    { id: "shift-left", text: "Shift −1", mode: "shift", amount: -1 },
    { id: "shift-right", text: "Shift +1", mode: "shift", amount: 1 },
    { id: "shorten", text: "Shorten", mode: "duration", amount: -1 },
    { id: "extend", text: "Extend", mode: "duration", amount: 1 }
  ];
  for (const button of batchActions) {
    add(footer, "Button", button.id, {
      x: buttonX,
      y: 5,
      width: 100,
      height: 34,
      text: translate(button.text),
      action: {
        type: "batch",
        mode: button.mode,
        amount: button.amount
      },
      enabled: !!state.selected.length
    });
    buttonX += 106;
  }
  add(footer, "Label", "changes", {
    x: buttonX + 4,
    y: 0,
    width: Math.max(0, width - buttonX - 16),
    height: metrics.footer,
    text: translate("Changes") + ": " + state.undo.length,
    fontSize: metrics.micro,
    color: colors.secondaryText
  });
  return {
    layers,
    geometry: layout
  };
}
