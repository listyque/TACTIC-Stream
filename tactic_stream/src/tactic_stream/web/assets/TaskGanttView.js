import { A as onMounted, D as onActivated, E as nextTick, G as withCtx, H as watch, M as openBlock, N as renderList, O as onBeforeUnmount, P as renderSlot, X as ref, _ as createElementBlock, b as createVNode, c as withKeys, et as unref, g as createCommentVNode, h as createBlock, k as onDeactivated, l as withModifiers, m as createBaseVNode, nt as normalizeStyle, p as computed, rt as toDisplayString, tt as normalizeClass, u as Fragment } from "./vue.js";
import { C as layout$1, T as metrics$1, o as t, s as appearance, t as _sfc_main$1 } from "./AppButton.js";
import { C as translate, G as label, J as node, N as _sfc_main$3, W as button, Y as rect, t as _sfc_main$2 } from "./FrameView.js";
//#region ../src/tactic_stream/shared_ui/features/tasks/gantt.state.mjs
var clamp = (value, minimum, maximum) => Math.max(minimum, Math.min(maximum, value));
var metrics = {
	heading: 54,
	headingGap: 3,
	overview: 30,
	footer: layout$1.dockWorkspaceFooterHeight,
	section: 28,
	group: 27,
	row: 50,
	bar: 27,
	barInset: 4,
	minBar: 7,
	gripWidth: 12,
	gripHeight: 22,
	gripOutside: 8,
	progressWidth: 18,
	progressHeight: 22,
	overscan: 100,
	autoScrollEdge: 28,
	autoScrollStep: 10,
	autoScrollInterval: 20,
	dragThreshold: 3
};
function layout(width, height, days, zoom = 1, gutter = 0) {
	const labels = Math.min(310, Math.max(220, width * .3));
	const viewport = Math.max(1, width - labels - gutter);
	const count = Math.max(1, days || 1);
	const baseDay = clamp(viewport / count, 10, 28);
	const day = clamp(baseDay * zoom, 2, 80);
	const bodyTop = metrics.heading + metrics.headingGap;
	const bodyHeight = Math.max(0, height - bodyTop - metrics.overview - metrics.footer);
	return {
		labels,
		viewport,
		baseDay,
		day,
		timeline: Math.max(viewport, count * day),
		heading: {
			x: 0,
			y: 0,
			width,
			height: metrics.heading
		},
		body: {
			x: 0,
			y: bodyTop,
			width,
			height: bodyHeight
		},
		overview: {
			x: 0,
			y: bodyTop + bodyHeight,
			width,
			height: metrics.overview
		},
		footer: {
			x: 0,
			y: Math.max(0, height - metrics.footer),
			width,
			height: metrics.footer
		}
	};
}
function rows(records, collapsed = []) {
	const result = [];
	let top = 0;
	function add(kind, key, record, height) {
		result.push({
			kind,
			key,
			record,
			height,
			top
		});
		top += height;
	}
	for (const record of records) {
		if (record.ganttSectionFirst) add("section", "section:" + record.ganttSection, record, metrics.section);
		if (record.groupFirst && record.groupKey) add("group", record.ganttSection + ":" + record.groupKey, record, metrics.group);
		if (collapsed.indexOf(record.groupKey) < 0) add("task", record.taskCode, record, metrics.row);
	}
	return {
		items: result,
		height: top
	};
}
function dateForDay(rangeStart, offset) {
	const value = /* @__PURE__ */ new Date((rangeStart || "2000-01-01").slice(0, 10) + "T12:00:00Z");
	value.setUTCDate(value.getUTCDate() + Number(offset || 0));
	return value.toISOString().slice(0, 10);
}
function boundary(rangeStart, offset) {
	const date = /* @__PURE__ */ new Date(dateForDay(rangeStart, offset) + "T12:00:00Z");
	return date.getUTCDate() === 1 ? 2 : date.getUTCDay() === 1 ? 1 : 0;
}
function tickMode(day) {
	return day >= 22 ? "days" : day >= 7 ? "weeks" : day >= 2.8 ? "months" : "quarters";
}
function ticks(range, day, x, width) {
	return ((range.tickSets || {})[tickMode(day)] || []).filter((tick) => tick.offsetDay * day >= x - metrics.overscan && tick.offsetDay * day <= x + width + metrics.overscan);
}
function bar(start, duration, day, x = 0) {
	return {
		x: start * day - x,
		y: (metrics.row - metrics.bar) / 2,
		width: Math.max(metrics.minBar, duration * day - metrics.barInset),
		height: metrics.bar
	};
}
function progressAt(pointer, width) {
	return clamp(Math.round(pointer / Math.max(1, width) * 100), 0, 100);
}
function progressKey(progress, key) {
	if (key === "Home") return 0;
	if (key === "End") return 100;
	if (key === "ArrowLeft") return clamp(progress - 1, 0, 100);
	if (key === "ArrowRight") return clamp(progress + 1, 0, 100);
	return null;
}
function progressLeft(width, progress) {
	return clamp(width * progress / 100, 18, width - 18) - metrics.progressWidth / 2;
}
function begin(record, mode, contentX, day, fromIssue = false) {
	const start = mode === "create" ? Math.round(contentX / day) : record.ganttStartDay;
	const duration = mode === "create" ? 1 : Math.max(1, record.ganttDurationDays);
	return {
		key: record.taskCode,
		mode,
		fromIssue,
		distance: 0,
		press: contentX,
		baseStart: start,
		baseDuration: duration,
		start,
		duration,
		baseProgress: record.progress,
		progress: record.progress
	};
}
function pointer(drag, contentX, day) {
	const next = Object.assign({}, drag);
	next.distance = Math.max(drag.distance || 0, Math.abs(contentX - drag.press));
	if (drag.mode === "progress") {
		next.progress = progressAt(contentX - drag.baseStart * day, bar(drag.baseStart, drag.baseDuration, day).width);
		return next;
	}
	const delta = Math.round((contentX - drag.press) / day);
	if (drag.mode === "move") next.start = clamp(drag.baseStart + delta, -3650, 36600);
	else if (drag.mode === "start" || drag.mode === "resize-start") {
		next.start = clamp(drag.baseStart + delta, -3650, drag.baseStart + drag.baseDuration - 1);
		next.duration = Math.min(3650, drag.baseDuration + drag.baseStart - next.start);
	} else if (drag.mode === "create") {
		next.start = drag.baseStart + Math.min(0, delta);
		next.duration = Math.min(3650, Math.abs(delta) + 1);
	} else if (drag.mode === "end" || drag.mode === "resize-end") next.duration = clamp(drag.baseDuration + delta, 1, 3650);
	else throw Error("Unknown schedule gesture: " + drag.mode);
	return next;
}
function moved(drag) {
	return drag.distance >= metrics.dragThreshold;
}
function changed(drag) {
	return drag.mode === "create" && (!drag.fromIssue || moved(drag)) || drag.start !== drag.baseStart || drag.duration !== drag.baseDuration || drag.progress !== drag.baseProgress;
}
function zoomAt(geometry, x, value, anchor) {
	const zoom = clamp(value, 2 / geometry.baseDay, 5);
	const day = clamp(geometry.baseDay * zoom, 2, 80);
	return {
		zoom,
		day,
		x: (x + clamp(anchor, 0, geometry.viewport)) / geometry.day * day - clamp(anchor, 0, geometry.viewport)
	};
}
function scaleZoom(mode, baseDay) {
	const widths = {
		days: 28,
		weeks: 12,
		months: 5,
		quarters: 2,
		auto: baseDay
	};
	if (!(mode in widths)) throw Error("Unknown timeline scale: " + mode);
	return widths[mode] / baseDay;
}
function overviewPosition(position, viewport, timeline, offset) {
	const thumb = Math.min(viewport, Math.max(28, viewport * viewport / timeline));
	const travel = Math.max(0, viewport - thumb);
	return travel ? clamp(position - (offset === void 0 ? thumb / 2 : offset), 0, travel) / travel * Math.max(0, timeline - viewport) : 0;
}
function autoScroll(x, width, scroll, maximum) {
	return clamp(scroll + (x < metrics.autoScrollEdge ? -metrics.autoScrollStep : x > width - metrics.autoScrollEdge ? metrics.autoScrollStep : 0), 0, maximum);
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/tasks/gantt.ui.mjs
var batchActions = [
	{
		title: "Shift one day earlier",
		action: "shift",
		amount: -1
	},
	{
		title: "Shift one day later",
		action: "shift",
		amount: 1
	},
	{
		title: "Align start dates",
		action: "align-start",
		amount: 1
	},
	{
		title: "Align deadlines",
		action: "align-end",
		amount: 1
	},
	{
		title: "Schedule sequentially",
		action: "sequence",
		amount: 1
	},
	{
		title: "Extend by one day",
		action: "extend",
		amount: 1
	},
	{
		title: "Shorten by one day",
		action: "shorten",
		amount: 1
	}
];
var scales = [
	{
		label: "Fit range",
		value: "auto"
	},
	{
		label: "Days",
		value: "days"
	},
	{
		label: "Weeks",
		value: "weeks"
	},
	{
		label: "Months",
		value: "months"
	},
	{
		label: "Quarters",
		value: "quarters"
	}
];
var box = (id, bounds, background, extra = {}) => node("Box", id, bounds, Object.assign({
	background,
	radius: 0
}, extra));
function heading(model, width, language) {
	const t = (text) => translate(text, language);
	return { nodes: [
		node("Icon", "ganttHeadingIcon", rect(10, 19, 16, 16), {
			icon: "gantt",
			color: "action"
		}),
		label("ganttHeadingTitle", rect(34, 10, width - 42, 17), t("Task schedule").toUpperCase(), {
			fontRole: "secondary",
			weight: 600
		}),
		label("ganttHeadingCount", rect(34, 29, width - 42, 15), translate("{scheduled} scheduled · {unscheduled} unscheduled", language, {
			scheduled: model.scheduled || 0,
			unscheduled: model.unscheduled || 0
		}), {
			fontRole: "caption",
			color: "secondaryText"
		})
	] };
}
function section(record, width, language) {
	const scheduled = record.ganttSection === "scheduled";
	return { nodes: [
		box("ganttSectionSurface", rect(0, 0, width, metrics.section), "workspace"),
		node("Icon", "ganttSectionIcon", rect(9, 7, 14, 14), {
			icon: scheduled ? "schedule" : "warning",
			color: scheduled ? "action" : "yellow"
		}),
		label("ganttSectionText", rect(30, 6, width - 38, 16), translate(scheduled ? "Scheduled tasks" : "Unscheduled tasks", language).toUpperCase(), {
			fontRole: "caption",
			weight: 600,
			color: "secondaryText"
		})
	] };
}
function group(record, width, collapsed) {
	return { nodes: [
		box("ganttGroupSurface", rect(0, 0, width, metrics.group), "surfaceContainerLow"),
		node("Icon", "ganttGroupChevron", rect(8, 7, 13, 13), {
			icon: collapsed ? "chevron-right" : "expand-more",
			color: "secondaryText"
		}),
		box("ganttGroupDot", rect(27, 10, 7, 7), record.groupColor || "action", { radius: 3.5 }),
		label("ganttGroupLabel", rect(40, 5.5, width - 80, 16), String(record.group || "").toUpperCase(), {
			fontRole: "caption",
			weight: 600
		}),
		label("ganttGroupCount", rect(width - 35, 5.5, 27, 16), String(record.groupCount || 0), {
			fontRole: "caption",
			color: "secondaryText",
			align: "right"
		})
	] };
}
function taskLabel(record, width, language) {
	const blocked = !!record.busy;
	const trailing = record.ganttWarning ? 42 : 24;
	return { nodes: [
		box("ganttLabelSurface", rect(0, 0, width, metrics.row), "surfaceContainerLow", { opacity: .94 }),
		...record.selected || record.dirty ? [box("ganttActiveMark", rect(0, 6, 2, 38), "action", { radius: 1 })] : [],
		node("CheckBox", "ganttTaskCheck", rect(5, 11.5, 27, 27), {
			label: translate("Select task", language) + " " + record.parentTitle + " " + record.processLabel,
			checked: !!record.checked,
			enabled: !blocked,
			hideLabel: true,
			action: {
				type: "select",
				key: record.taskCode
			}
		}),
		node("Preview", "ganttTaskPreview", rect(39, 10, 30, 30), {
			source: record.parentPreviewUrl || "",
			initials: String(record.parentTitle || "").slice(0, 2).toUpperCase(),
			icon: "sobject",
			accent: record.processColor || "action",
			round: false,
			outlined: false
		}),
		label("ganttTaskTitle", rect(76, 9, width - 84 - trailing, 17), record.parentTitle || "", {
			fontRole: "secondary",
			weight: 600
		}),
		label("ganttTaskSubtitle", rect(76, 27, width - 84 - trailing, 15), (record.processLabel || "") + (record.assignedLabel ? "  ·  " + record.assignedLabel : ""), {
			fontRole: "caption",
			color: "secondaryText"
		}),
		node("Action", "ganttTaskActivate", rect(72, 0, width - 80 - trailing, 50), {
			text: record.parentTitle || "",
			enabled: !blocked,
			action: {
				type: "activate",
				key: record.taskCode
			},
			doubleAction: {
				type: "object",
				key: record.taskCode
			}
		}),
		button("ganttTaskEdit", rect(width - trailing, 14, 22, 22), "", "edit", {
			type: "edit",
			key: record.taskCode
		}, !blocked, {
			label: translate("Edit schedule", language),
			iconOnly: true,
			iconAction: true,
			iconSize: 14,
			opacity: 1
		}),
		...record.ganttWarning ? [node("Icon", "ganttTaskWarning", rect(width - 17, 18.5, 13, 13), {
			icon: "warning",
			color: "yellow",
			toolTip: record.warningText || record.ganttWarning
		})] : []
	] };
}
function scheduleBar(record, width, language) {
	const progress = Math.max(0, Math.min(100, record.progress || 0));
	const color = record.ganttColor || "action";
	const h = metrics.bar;
	return { nodes: [
		box("ganttBarBackground", rect(0, 0, width, h), color, {
			opacity: record.editing ? .42 : .3,
			radius: record.radius || 8
		}),
		box("ganttBarProgress", rect(0, 0, width * progress / 100, h), color, {
			opacity: .88,
			radius: record.radius || 8
		}),
		label("ganttBarLabel", rect(record.progressSupported ? 30 : 7, 6, width - (record.progressSupported ? 37 : 14), 15), record.editing ? record.startLabel + " — " + record.endLabel : (record.processLabel || "") + "  " + progress + "%", {
			fontRole: "caption",
			weight: 600
		}),
		...[-8, width - 4].map((x, index) => box(index ? "ganttEndGrip" : "ganttStartGrip", rect(x, 2.5, 12, 22), "surfaceContainerHighest", {
			radius: 5,
			border: "primaryText",
			borderWidth: 1,
			children: [box("ganttGripLine" + index, rect(5, 6, 2, 10), "primaryText", { radius: 1 })]
		}))
	] };
}
function grid(range, day, x, width, height) {
	if (!range.rangeStart) return { nodes: [] };
	const nodes = [];
	for (const span of range.weekends || []) {
		const left = span.offsetDay * day - x, size = span.durationDays * day;
		if (left + size >= 0 && left <= width) nodes.push(box("ganttWeekend" + span.offsetDay, rect(left, 0, size, height), "surfaceContainerHigh", { opacity: .22 }));
	}
	if (day >= 16) {
		const first = Math.max(0, Math.floor(x / day) - 1);
		const last = Math.min(range.days || 1, Math.ceil((x + width) / day) + 1);
		for (let offset = first; offset <= last; offset++) {
			const level = boundary(range.rangeStart, offset);
			nodes.push(box("ganttBoundary" + offset, rect(offset * day - x, 0, level === 2 ? 2 : 1, height), level ? "outline" : "separator", { opacity: level === 2 ? .52 : level === 1 ? .38 : .24 }));
		}
	} else for (const tick of ticks(range, day, x, width)) nodes.push(box("ganttBoundary" + tick.offsetDay, rect(tick.offsetDay * day - x, 0, tick.major ? 2 : 1, height), tick.major ? "outline" : "separator", { opacity: tick.major ? .28 : .38 }));
	for (const marker of range.milestones || []) nodes.push(box("ganttMilestoneLine" + marker.code, rect(marker.offsetDay * day - x, 0, 3, height), "tertiary", { opacity: .72 }));
	if (range.todayDay >= 0) nodes.push(box("ganttTodayLine", rect(range.todayDay * day - x, 0, 2, height), "error", { opacity: .52 }));
	return { nodes };
}
function footer(model, width, language) {
	const t = (text) => translate(text, language), nodes = [];
	let x = width - (model.hostWidth || 0) - 8;
	function action(id, text, icon, type, enabled = true, extra = {}) {
		x -= 28;
		nodes.push(button(id, rect(x, 15, 28, 28), "", icon, { type }, enabled, Object.assign({
			label: t(text),
			iconOnly: true,
			iconAction: true,
			iconSize: 16
		}, extra)));
		x -= 5;
	}
	action("ganttToday", "Center today", "schedule", "today", model.todayDay >= 0);
	if (width >= 700) {
		action("ganttZoomIn", "Zoom in", "zoom-in", "zoom-in", model.zoom < 5);
		x -= 58;
		nodes.push(button("ganttScale", rect(x, 15, 58, 28), Math.round(model.zoom * 100) + "%", "", { type: "scale" }, true, {
			label: t("Timeline scale"),
			compact: true
		}));
		x -= 5;
		action("ganttZoomOut", "Zoom out", "zoom-out", "zoom-out", model.zoom > (model.minZoom || .15));
	}
	if (width >= 520) {
		action("ganttResource", "Group workload by assignee", "group", "resource", !model.busy, { highlighted: !!model.resourceMode });
		action("ganttWorking", "Working days only", "calendar-today", "working", !model.busy, { highlighted: !!model.workingDays });
	}
	action("ganttRedo", "Redo schedule change", "redo", "redo", !model.busy && model.canRedo);
	action("ganttUndo", "Undo schedule change", "undo", "undo", !model.busy && model.canUndo);
	action("ganttOptions", "Schedule options", "more", "options", !model.busy);
	nodes.unshift(box("ganttFooterSurface", rect(0, 0, width, metrics.footer), "surfaceContainer"));
	nodes.push(box("ganttFooterDivider", rect(0, 0, width, 1), "outlineVariant"));
	if (x > 50) nodes.push(label("ganttRange", rect(10, 21, x - 18, 16), (model.rangeStart || "") + "  —  " + (model.rangeEnd || ""), {
		fontRole: "caption",
		color: "secondaryText"
	}));
	return {
		nodes,
		height: metrics.footer
	};
}
function dependencies(records, collapsed, day, x = 0, y = 0) {
	const rows$2 = rows(records, collapsed).items.filter((row) => row.kind === "task");
	const byId = {};
	for (const row of rows$2) if (row.record.taskId) byId[row.record.taskId] = row;
	const nodes = [];
	for (const target of rows$2) {
		const source = byId[target.record.dependencyId];
		if (!source || source === target || !source.record.ganttScheduled || !target.record.ganttScheduled) continue;
		const from = bar(source.record.ganttStartDay, source.record.ganttDurationDays, day, x);
		const to = bar(target.record.ganttStartDay, target.record.ganttDurationDays, day, x);
		const startX = from.x + from.width, endX = to.x - 8;
		const startY = source.top + metrics.row / 2 - y;
		const endY = target.top + metrics.row / 2 - y;
		const bend = Math.max(startX + 12, endX - 12), id = target.key;
		nodes.push(box("ganttDependencyOut" + id, rect(startX, startY, bend - startX, 1), "outline"));
		nodes.push(box("ganttDependencyVertical" + id, rect(bend, Math.min(startY, endY), 1, Math.abs(endY - startY)), "outline"));
		nodes.push(box("ganttDependencyIn" + id, rect(Math.min(bend, endX), endY, Math.abs(endX - bend), 1), "outline"));
		nodes.push(node("Icon", "ganttDependencyArrow" + id, rect(endX - 5, endY - 6, 12, 12), {
			icon: "arrow-right",
			color: "outline"
		}));
	}
	return { nodes };
}
function dateLabel(value, language, mode = "compact") {
	if (!value) return "—";
	const year = value.slice(0, 4), month = Number(value.slice(5, 7)), day = Number(value.slice(8, 10));
	const names = language === "ru" ? [
		"янв.",
		"февр.",
		"мар.",
		"апр.",
		"мая",
		"июн.",
		"июл.",
		"авг.",
		"сент.",
		"окт.",
		"нояб.",
		"дек."
	] : [
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
	if (mode === "days") return String(day);
	if (mode === "months") return names[month - 1] + " " + year;
	if (mode === "quarters") return translate("Q{quarter} {year}", language, {
		quarter: Math.ceil(month / 3),
		year
	});
	return language === "ru" ? day + " " + names[month - 1] : names[month - 1] + " " + day;
}
function timelineHeading(range, day, x, width, language) {
	const nodes = [];
	for (const tick of ticks(range, day, x, width)) {
		const left = tick.offsetDay * day - x;
		const size = Math.max(48, (tick.spanDays || 1) * day);
		nodes.push(box("ganttTickLine" + tick.date, rect(left, 0, tick.major ? 2 : 1, 54), tick.major ? "outline" : "separator", { opacity: tick.major ? .55 : .7 }));
		const text = label("ganttTick" + tick.date, rect(left + 6, 21, size - 8, 12), dateLabel(tick.date, language, tickMode(day)), {
			fontRole: tick.major ? "timelineMajorTick" : "timelineTick",
			color: tick.major ? "primaryText" : "secondaryText",
			weight: tick.major ? 600 : 400
		});
		nodes.push(text);
	}
	for (const marker of range.milestones || []) {
		const left = marker.offsetDay * day - x;
		const size = Math.min(150, Math.max(76, marker.label.length * 6 + 43));
		if (left + size < 0 || left > width) continue;
		nodes.push(box("ganttMarkerSurface" + marker.code, rect(left, 2, size, 22), "tertiaryContainer", {
			radius: 6,
			border: "tertiary",
			borderWidth: 1
		}));
		nodes.push(node("Icon", "ganttMarkerIcon" + marker.code, rect(left + 6, 6.5, 13, 13), {
			icon: "milestone",
			color: "tertiary"
		}));
		nodes.push(label("ganttMarkerLabel" + marker.code, rect(left + 23, 5.5, size - 57, 15), marker.label, {
			fontRole: "caption",
			weight: 600
		}));
		nodes.push(label("ganttMarkerCompletion" + marker.code, rect(left + size - 30, 5.5, 26, 15), String(clamp(Number(marker.completion) || 0, 0, 100)) + "%", {
			fontRole: "caption",
			color: "tertiary",
			align: "right"
		}));
		nodes.push(box("ganttMarkerLine" + marker.code, rect(left, 24, 3, 30), "tertiary", { opacity: .94 }));
		nodes.push(node("Action", "ganttMarkerOpen" + marker.code, rect(left, 2, size, 22), {
			text: marker.label + " · " + marker.dueDate,
			action: {
				type: "milestone",
				value: marker.code
			}
		}));
	}
	if (range.todayDay >= 0) {
		const left = range.todayDay * day - x;
		nodes.push(box("ganttHeaderToday", rect(left, 0, 3, 54), "error", { opacity: .82 }));
		nodes.push(label("ganttTodayLabel", rect(left - 64, 37, 60, 15), translate("TODAY", language), {
			fontRole: "caption",
			color: "error",
			weight: 600,
			align: "right"
		}));
	}
	return { nodes };
}
function overviewGeometry(viewport, timeline, x) {
	const width = Math.min(viewport, Math.max(28, viewport * viewport / timeline));
	return {
		width,
		x: timeline > viewport ? x / (timeline - viewport) * Math.max(0, viewport - width) : 0
	};
}
function overview(range, labels, width, timeline, x, language) {
	const viewport = Math.max(1, width - labels), nodes = [];
	nodes.push(box("ganttOverviewSurface", rect(0, 0, width, 30), "surfaceContainerLow"));
	nodes.push(node("Icon", "ganttOverviewIcon", rect(10, 9, 12, 12), {
		icon: "visibility",
		color: "secondaryText"
	}));
	nodes.push(label("ganttOverviewLabel", rect(28, 7.5, labels - 36, 15), range.warnings ? translate("{count} schedule warnings", language, { count: range.warnings }) : translate("Project overview", language), {
		fontRole: "caption",
		color: range.warnings ? "yellow" : "secondaryText"
	}));
	nodes.push(box("ganttOverviewTrack", rect(labels, 10, viewport, 10), "surfaceContainerHigh", {
		radius: 5,
		border: "outlineVariant",
		borderWidth: 1
	}));
	for (const [index, span] of (range.overview || []).entries()) nodes.push(box("ganttOverviewSpan" + index, rect(labels + span.startDay / Math.max(1, range.days) * viewport, 13.5, Math.max(2, span.durationDays / Math.max(1, range.days) * viewport), 3), span.warning ? "yellow" : span.color || "action", {
		opacity: .62,
		radius: 1.5
	}));
	for (const marker of range.milestones || []) nodes.push(box("ganttOverviewMarker" + marker.code, rect(labels + marker.offsetDay / Math.max(1, range.days) * viewport, 10, 2, 10), "tertiary", { opacity: .82 }));
	if (range.todayDay >= 0) nodes.push(box("ganttOverviewToday", rect(labels + range.todayDay / Math.max(1, range.days) * viewport, 10, 2, 10), "error", { opacity: .68 }));
	const thumb = overviewGeometry(viewport, timeline, x);
	nodes.push(box("ganttOverviewThumb", rect(labels + thumb.x, 6, thumb.width, 18), "secondaryContainer", {
		radius: 6,
		border: "action",
		borderWidth: 1
	}));
	return { nodes };
}
function rowSurface(model, width) {
	return { nodes: [box("ganttRowBackground", rect(0, 0, width, metrics.row), model.checked ? "secondaryContainer" : model.selected ? "contentSelection" : model.hovered ? "rowHover" : "transparent", { opacity: model.checked ? .55 : 1 }), box("ganttRowSeparator", rect(0, metrics.row - 1, width, 1), "separator")] };
}
function band(kind, width, record = {}, collapsed = false) {
	return { nodes: [box("gantt" + kind + "Band", rect(0, 0, width, kind === "section" ? metrics.section : metrics.group), kind === "section" ? "workspace" : "surfaceContainerLow"), ...kind === "group" ? [node("Action", "ganttGroupToggle", rect(0, 0, width, metrics.group), {
		text: record.group || "",
		role: "button",
		expanded: !collapsed,
		action: {
			type: "collapse",
			value: record.groupKey
		}
	})] : []] };
}
function groupTimeline(record, day, collapsed, x = 0) {
	if (!record.ganttGroupDurationDays) return { nodes: [] };
	const width = Math.max(5, record.ganttGroupDurationDays * day - 2), height = collapsed ? 11 : 5;
	return { nodes: [box("ganttGroupSummary", rect(record.ganttGroupStartDay * day - x, (metrics.group - height) / 2, width, height), record.groupColor || "action", {
		radius: height / 2,
		opacity: collapsed ? .55 : .34,
		children: [box("ganttGroupSummaryProgress", rect(0, 0, width * record.ganttGroupProgress / 100, height), record.groupColor || "action", {
			radius: height / 2,
			opacity: .95
		})]
	})] };
}
function issue(record, width, language) {
	const text = translate(record.ganttIssue || "", language);
	const size = Math.max(0, Math.min(width - 20, text.length * 6 + 34));
	return {
		width: size,
		height: 30,
		nodes: [
			box("ganttIssueSurface", rect(0, 0, size, 30), "surfaceContainerHigh", { radius: record.radius || 8 }),
			node("Icon", "ganttIssueIcon", rect(7, 8.5, 13, 13), {
				icon: "warning",
				color: "yellow"
			}),
			label("ganttUnscheduledIssueLabel", rect(25, 7, size - 32, 16), text, {
				fontRole: "secondary",
				color: "secondaryText"
			})
		]
	};
}
function empty(width, height, loading, language) {
	return { nodes: [label("ganttEmptyLabel", rect(10, Math.max(0, (height - 20) / 2), width - 20, 20), translate(loading ? "Loading data…" : "No tasks match the current scope and filters", language), {
		fontRole: "secondary",
		color: "secondaryText",
		align: "center"
	})] };
}
function options(model, width, language) {
	const tr = (text) => translate(text, language), nodes = [];
	for (const [index, title, type, checked] of [[
		0,
		"Working days only",
		"working",
		model.workingDays
	], [
		1,
		"Group workload by assignee",
		"resource",
		model.resourceMode
	]]) nodes.push(node("CheckBox", "ganttOption" + type, rect(4, index * 32, width - 8, 28), {
		text: tr(title),
		checked: !!checked,
		enabled: !model.busy,
		action: { type }
	}));
	nodes.push(node("Choice", "ganttOptionScale", rect(4, 68, width - 8, 32), {
		label: tr("Timeline scale"),
		value: model.scale,
		options: scales.map((option) => ({
			value: option.value,
			label: tr(option.label)
		})),
		action: { type: "scale-value" }
	}));
	let y = 108;
	for (const option of batchActions) {
		nodes.push(button("ganttBatch" + option.action + option.amount, rect(0, y, width, 30), tr(option.title), "", {
			type: "batch",
			operation: option.action,
			amount: option.amount
		}, !model.busy && model.checked > 0, { align: "left" }));
		y += 32;
	}
	nodes.push(button("ganttDeleteSelectedTasksButton", rect(0, y + 4, width, 32), tr("Delete selected tasks"), "delete", { type: "delete" }, !model.busy && model.checked > 0 && !model.dirty, {
		destructive: true,
		align: "left"
	}));
	return {
		nodes,
		height: y + 40
	};
}
function scaleOptions(mode, width, language) {
	return {
		height: scales.length * 34,
		nodes: scales.map((option, index) => button("ganttScale" + option.value, rect(0, index * 34, width, 32), translate(option.label, language), "", {
			type: "scale-value",
			value: option.value
		}, true, {
			highlighted: mode === option.value,
			align: "left"
		}))
	};
}
//#endregion
//#region src/features/tasks/TaskGanttView.vue
var _hoisted_1 = ["aria-label", "aria-busy"];
var _hoisted_2 = { class: "gantt-heading" };
var _hoisted_3 = ["aria-label"];
var _hoisted_4 = ["data-task-key"];
var _hoisted_5 = ["onDblclick"];
var _hoisted_6 = ["title"];
var _hoisted_7 = { class: "gantt-date-chip start" };
var _hoisted_8 = { class: "gantt-date-chip end" };
var _hoisted_9 = { class: "gantt-overview" };
var _hoisted_10 = [
	"aria-label",
	"aria-valuemax",
	"aria-valuenow"
];
var _hoisted_11 = { class: "gantt-footer" };
var _hoisted_12 = {
	key: 0,
	class: "gantt-footer-host"
};
var _sfc_main = {
	__name: "TaskGanttView",
	props: {
		projection: Object,
		tasks: {
			type: Array,
			default: () => []
		},
		selected: {
			type: Array,
			default: () => []
		},
		collapsed: {
			type: Array,
			default: () => []
		},
		busy: Boolean,
		projecting: Boolean,
		workingDays: Boolean,
		resourceMode: Boolean,
		canUndo: Boolean,
		canRedo: Boolean,
		active: String,
		hasMore: Boolean
	},
	emits: [
		"select",
		"select-all",
		"activate",
		"object",
		"collapse",
		"edit",
		"inspect",
		"working-days",
		"resource-mode",
		"undo",
		"redo",
		"batch",
		"schedule",
		"milestone",
		"progress",
		"delete",
		"load-more"
	],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const root = ref(null), body = ref(null), viewport = ref(800), gutter = ref(0), scrollX = ref(0), scrollY = ref(0), bodyHeight = ref(400), zoom = ref(1), scale = ref("auto"), drag = ref(null);
		let observer, resizeFrame, autoScroll$1, ignoreClickUntil = 0;
		const range = computed(() => props.projection?.gantt);
		const dayCount = computed(() => Math.max(1, range.value?.days || 1));
		const layout$2 = computed(() => layout(viewport.value, 0, dayCount.value, zoom.value, gutter.value));
		const labelWidth = computed(() => layout$2.value.labels);
		const timelineViewport = computed(() => layout$2.value.viewport);
		const baseDayWidth = computed(() => layout$2.value.baseDay);
		const dayWidth = computed(() => layout$2.value.day);
		const timelineWidth = computed(() => layout$2.value.timeline);
		const tasksByKey = computed(() => new Map(props.tasks.map((task) => [task.key, task])));
		const rowLayout = computed(() => rows(range.value?.records || [], props.collapsed));
		const rows$1 = computed(() => rowLayout.value.items);
		const totalHeight = computed(() => rowLayout.value.height);
		const visibleRows = computed(() => rows$1.value.filter((row) => row.top + row.height >= scrollY.value - metrics.overscan && row.top < scrollY.value + bodyHeight.value + metrics.overscan));
		const headingScene = computed(() => heading(range.value || {}, labelWidth.value, appearance.language));
		const gridScene = computed(() => grid(range.value || {}, dayWidth.value, scrollX.value, timelineViewport.value, bodyHeight.value));
		const dependencyScene = computed(() => dependencies(range.value?.records || [], props.collapsed, dayWidth.value));
		const footerScene = computed(() => footer({
			...range.value,
			zoom: zoom.value,
			busy: props.busy,
			workingDays: props.workingDays,
			resourceMode: props.resourceMode,
			canUndo: props.canUndo,
			canRedo: props.canRedo,
			minZoom: 2 / baseDayWidth.value,
			hostWidth: viewport.value >= 380 ? 112 : 0
		}, viewport.value, appearance.language));
		const optionsTrigger = ref(null), scaleTrigger = ref(null), optionsAnchor = ref(null), scaleAnchor = ref(null);
		function footerAction(action, source) {
			if (action.type === "today") setScroll(range.value.todayDay * dayWidth.value - timelineViewport.value * .42);
			else if (action.type === "zoom-in") setZoom(zoom.value * 1.25);
			else if (action.type === "zoom-out") setZoom(zoom.value / 1.25);
			else if (action.type === "working") emit("working-days", !props.workingDays);
			else if (action.type === "resource") emit("resource-mode", !props.resourceMode);
			else if (action.type === "options" && optionsTrigger.value.open) optionsTrigger.value.close(true);
			else if (action.type === "options") {
				optionsAnchor.value = source;
				optionsTrigger.value.openAt({ target: source });
			} else if (action.type === "scale" && scaleTrigger.value.open) scaleTrigger.value.close(true);
			else if (action.type === "scale") {
				scaleAnchor.value = source;
				scaleTrigger.value.openAt({ target: source });
			} else emit(action.type);
		}
		const optionsScene = computed(() => options({
			workingDays: props.workingDays,
			resourceMode: props.resourceMode,
			scale: scale.value,
			busy: props.busy,
			checked: props.selected.length,
			dirty: props.tasks.some((task) => task.pending)
		}, 268, appearance.language));
		function optionAction(action) {
			if (action.type === "working") emit("working-days", action.value);
			else if (action.type === "resource") emit("resource-mode", action.value);
			else if (action.type === "scale-value") {
				setScale(action.value);
				scaleTrigger.value.close(true);
			} else if (action.type === "batch") {
				emit("batch", action.operation, action.amount);
				optionsTrigger.value.close(true);
			} else if (action.type === "delete") {
				emit("delete");
				optionsTrigger.value.close(true);
			}
		}
		function rowModel(record) {
			const task = tasksByKey.value.get(record.taskCode) || {};
			return {
				...record,
				selected: props.active === record.taskCode,
				checked: props.selected.includes(record.taskCode),
				dirty: task.pending,
				busy: props.busy,
				parentPreviewUrl: task.parent?.__preview_url__ || "",
				processColor: task.__process__?.color || record.processColor,
				warningText: warningText(record),
				touch: matchMedia("(hover:none)").matches
			};
		}
		function labelAction(action) {
			if (action.type === "select") emit("select", action.key, !props.selected.includes(action.key));
			else if (action.type === "edit") edit(action.key);
			else emit(action.type, action.key);
		}
		function barScene(record) {
			const pending = drag.value?.key === record.taskCode ? drag.value : null;
			return scheduleBar({
				...record,
				progress: progress(record),
				ganttColor: color(record),
				radius: metrics$1(appearance.theme).itemRadius,
				editing: pending && pending.mode !== "progress",
				startLabel: pending ? dateForDay$1(pending.start) : "",
				endLabel: pending ? dateForDay$1(pending.start + pending.duration - 1) : "",
				progressSupported: progressSupported(record)
			}, parseFloat(geometry(record).width), appearance.language);
		}
		function progressSupported(record) {
			const task = tasksByKey.value.get(record.taskCode) || {};
			return Object.hasOwn(task, "progress") || Object.hasOwn(task, "completion");
		}
		function dateForDay$1(day) {
			return dateForDay(range.value?.rangeStart, day);
		}
		function dateLabel$1(value) {
			return dateLabel(value, appearance.language);
		}
		function warningText(record) {
			return (record.ganttWarning || record.ganttIssue || "").split("\n").map((value) => t(value)).join("\n");
		}
		function color(record) {
			return tasksByKey.value.get(record.taskCode)?.__status__?.color || record.ganttColor || "var(--primary)";
		}
		function progress(record) {
			return drag.value?.key === record.taskCode && drag.value.mode === "progress" ? drag.value.progress : record.progress;
		}
		function geometry(record) {
			const pending = drag.value?.key === record.taskCode && drag.value.mode !== "progress" ? drag.value : null;
			const value = bar(pending?.start ?? record.ganttStartDay, pending?.duration ?? record.ganttDurationDays, dayWidth.value);
			return {
				left: value.x + "px",
				top: value.y + "px",
				transform: "none",
				width: value.width + "px",
				"--bar-color": color(record)
			};
		}
		function synchronize() {
			scrollX.value = body.value.scrollLeft;
			scrollY.value = body.value.scrollTop;
		}
		function setScroll(value) {
			body.value.scrollLeft = Math.max(0, Math.min(timelineWidth.value - timelineViewport.value, value));
			synchronize();
		}
		async function setZoom(value, anchor = timelineViewport.value / 2, mode = "custom") {
			const next = zoomAt(layout$2.value, scrollX.value, value, anchor);
			scale.value = mode;
			zoom.value = next.zoom;
			await nextTick();
			setScroll(next.x);
		}
		function setScale(mode) {
			setZoom(scaleZoom(mode, baseDayWidth.value), timelineViewport.value / 2, mode);
		}
		function wheel(event, offset = 0) {
			event.preventDefault();
			if (event.shiftKey || Math.abs(event.deltaX) > Math.abs(event.deltaY)) setScroll(scrollX.value + (event.deltaX || event.deltaY) * 1.65);
			else setZoom(zoom.value * Math.pow(1.16, -event.deltaY / (event.deltaMode === 1 ? 3 : 100)), Math.max(0, event.clientX - event.currentTarget.getBoundingClientRect().left - offset));
		}
		function timelineWheel(event) {
			if (event.clientX - event.currentTarget.getBoundingClientRect().left >= labelWidth.value) wheel(event, labelWidth.value);
		}
		function edit(key) {
			if (performance.now() >= ignoreClickUntil && !props.busy) emit("edit", key);
		}
		function activate(key, event) {
			if (performance.now() >= ignoreClickUntil && !props.busy) emit("activate", key, event);
		}
		function begin$1(record, mode, event, fromIssue = false) {
			if (props.busy || event.pointerType !== "mouse" || event.button !== 0) return;
			if (mode === "progress") event.currentTarget.focus({ preventScroll: true });
			else body.value.focus({ preventScroll: true });
			event.preventDefault();
			event.stopPropagation();
			event.currentTarget.setPointerCapture(event.pointerId);
			const box = event.currentTarget.closest(".task-gantt-timeline").getBoundingClientRect();
			drag.value = {
				...begin(record, mode, event.clientX - box.left, dayWidth.value, fromIssue),
				originLeft: box.left + scrollX.value,
				clientX: event.clientX
			};
			autoScroll$1 = setInterval(() => {
				if (!drag.value || drag.value.mode === "progress") return;
				const rect = body.value.getBoundingClientRect(), x = drag.value.clientX;
				setScroll(autoScroll(x - rect.left - labelWidth.value, timelineViewport.value, scrollX.value, timelineWidth.value - timelineViewport.value));
				updateDrag(x);
			}, metrics.autoScrollInterval);
		}
		function updateDrag(x) {
			const value = drag.value;
			if (!value) return;
			drag.value = {
				...pointer(value, x - value.originLeft + scrollX.value, dayWidth.value),
				clientX: x
			};
		}
		function finish(cancel = false) {
			clearInterval(autoScroll$1);
			const value = drag.value;
			drag.value = null;
			if (!value) return;
			const changed$1 = changed(value);
			if (changed$1 || moved(value)) ignoreClickUntil = performance.now() + 150;
			if (cancel || !changed$1) return;
			if (value.mode === "progress") emit("progress", value.key, value.progress);
			else if (value.mode === "create" || value.start !== value.baseStart || value.duration !== value.baseDuration) emit("schedule", value.key, value.start, value.duration, value.mode);
		}
		function keyboard(event) {
			if (event.key === "Escape" && drag.value) {
				event.preventDefault();
				event.stopPropagation();
				finish(true);
			}
		}
		function progressKey$1(event, record) {
			const value = progressKey(record.progress, event.key);
			if (value === null) return;
			event.preventDefault();
			event.stopPropagation();
			emit("progress", record.taskCode, value);
		}
		let overviewOffset;
		function overview$1(event) {
			const box = event.currentTarget.getBoundingClientRect();
			if (event.type === "pointerdown") {
				event.preventDefault();
				event.currentTarget.setPointerCapture(event.pointerId);
				const thumb = overviewGeometry(timelineViewport.value, timelineWidth.value, scrollX.value), x = event.clientX - box.left;
				overviewOffset = x >= thumb.x && x <= thumb.x + thumb.width ? x - thumb.x : thumb.width / 2;
			}
			if (event.type === "pointermove" && !event.buttons) return;
			setScroll(overviewPosition(event.clientX - box.left, timelineViewport.value, timelineWidth.value, overviewOffset));
		}
		function pan(event) {
			if (event.pointerType !== "mouse" || ![0, 1].includes(event.button) || event.target.closest("button,input,label,summary")) return;
			event.preventDefault();
			event.currentTarget.setPointerCapture(event.pointerId);
			event.currentTarget.dataset.panX = event.clientX;
			event.currentTarget.dataset.panScroll = scrollX.value;
		}
		function move(event) {
			if (drag.value) updateDrag(event.clientX);
			else if ([1, 4].includes(event.buttons) && event.currentTarget.dataset.panX) setScroll(Number(event.currentTarget.dataset.panScroll) + Number(event.currentTarget.dataset.panX) - event.clientX);
		}
		watch(visibleRows, (value) => {
			if (drag.value && !value.some((row) => row.key === drag.value.key)) finish(true);
		});
		onMounted(() => {
			const measured = {
				width: 800,
				bodyWidth: 800,
				bodyHeight: 400
			};
			observer = new ResizeObserver((entries) => {
				for (const { target, contentRect } of entries) if (target === root.value) measured.width = contentRect.width;
				else {
					measured.bodyWidth = contentRect.width;
					measured.bodyHeight = contentRect.height;
				}
				cancelAnimationFrame(resizeFrame);
				resizeFrame = requestAnimationFrame(() => {
					viewport.value = measured.width;
					gutter.value = Math.max(0, measured.width - measured.bodyWidth);
					bodyHeight.value = measured.bodyHeight;
				});
			});
			observer.observe(root.value);
			observer.observe(body.value);
			document.addEventListener("keydown", keyboard, true);
			window.addEventListener("blur", cancel);
		});
		function cancel() {
			finish(true);
		}
		let resumeFrame, activation = 0;
		onDeactivated(() => {
			activation++;
			cancelAnimationFrame(resizeFrame);
			observer?.disconnect();
			finish(true);
			optionsTrigger.value?.close();
			scaleTrigger.value?.close();
			document.removeEventListener("keydown", keyboard, true);
			window.removeEventListener("blur", cancel);
			cancelAnimationFrame(resumeFrame);
		});
		onActivated(async () => {
			const generation = ++activation;
			const x = scrollX.value, y = scrollY.value;
			observer?.observe(root.value);
			observer?.observe(body.value);
			document.addEventListener("keydown", keyboard, true);
			window.addEventListener("blur", cancel);
			await nextTick();
			if (generation !== activation) return;
			resumeFrame = requestAnimationFrame(() => {
				resumeFrame = requestAnimationFrame(() => {
					body.value.scrollLeft = x;
					body.value.scrollTop = y;
					synchronize();
				});
			});
		});
		onBeforeUnmount(() => {
			activation++;
			observer?.disconnect();
			cancelAnimationFrame(resumeFrame);
			cancelAnimationFrame(resizeFrame);
			clearInterval(autoScroll$1);
			document.removeEventListener("keydown", keyboard, true);
			window.removeEventListener("blur", cancel);
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				ref_key: "root",
				ref: root,
				class: "task-schedule-view task-gantt-view",
				"aria-label": unref(t)("Task Gantt"),
				"aria-busy": __props.projecting,
				style: normalizeStyle({
					"--gantt-label-width": labelWidth.value + "px",
					"--gantt-width": timelineWidth.value + "px",
					"--gantt-scroll-gutter": gutter.value + "px",
					"--gantt-heading-height": metrics.heading + "px",
					"--gantt-heading-gap": metrics.headingGap + "px",
					"--gantt-overview-height": metrics.overview + "px",
					"--gantt-footer-height": metrics.footer + "px",
					"--gantt-bar-height": metrics.bar + "px"
				})
			}, [
				createBaseVNode("header", _hoisted_2, [createVNode(_sfc_main$2, {
					class: "gantt-heading-label",
					scene: headingScene.value
				}, null, 8, ["scene"]), createBaseVNode("div", {
					class: "gantt-heading-viewport",
					onWheel: wheel
				}, [createVNode(_sfc_main$2, {
					scene: timelineHeading(range.value || {}, dayWidth.value, scrollX.value, timelineViewport.value, unref(appearance).language),
					onEvent: _cache[0] || (_cache[0] = (action) => emit("milestone", action.value))
				}, null, 8, ["scene"])], 32)]),
				createBaseVNode("div", {
					ref_key: "body",
					ref: body,
					class: "gantt-body",
					onWheel: timelineWheel,
					tabindex: "0",
					"aria-label": unref(t)("Task schedule"),
					onScroll: synchronize,
					onPointerdown: pan,
					onPointermove: move,
					onPointerup: _cache[12] || (_cache[12] = ($event) => finish()),
					onPointercancel: _cache[13] || (_cache[13] = ($event) => finish(true))
				}, [createBaseVNode("div", {
					class: "gantt-canvas",
					style: normalizeStyle({
						height: Math.max(bodyHeight.value, totalHeight.value) + "px",
						width: labelWidth.value + timelineWidth.value + "px"
					})
				}, [
					createVNode(_sfc_main$2, {
						class: "gantt-grid",
						scene: gridScene.value,
						interactive: false,
						style: normalizeStyle({
							left: labelWidth.value + scrollX.value + "px",
							top: scrollY.value + "px",
							width: timelineViewport.value + "px",
							height: bodyHeight.value + "px"
						})
					}, null, 8, ["scene", "style"]),
					createVNode(_sfc_main$2, {
						class: "gantt-dependencies",
						scene: dependencyScene.value,
						interactive: false,
						style: normalizeStyle({
							left: labelWidth.value + "px",
							width: timelineWidth.value + "px",
							height: totalHeight.value + "px"
						})
					}, null, 8, ["scene", "style"]),
					(openBlock(true), createElementBlock(Fragment, null, renderList(visibleRows.value, (row) => {
						return openBlock(), createElementBlock("div", {
							key: row.key,
							class: normalizeClass(["task-gantt-row", ["gantt-" + row.kind, {
								"task-selected": __props.selected.includes(row.key),
								"task-active": __props.active === row.key,
								pending: tasksByKey.value.get(row.key)?.pending
							}]]),
							"data-task-key": row.kind === "task" ? row.key : void 0,
							style: normalizeStyle({
								top: row.top + "px",
								height: row.height + "px"
							})
						}, [row.kind === "section" ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [
							createVNode(_sfc_main$2, {
								class: "gantt-band",
								scene: band(row.kind, labelWidth.value + timelineWidth.value),
								interactive: false
							}, null, 8, ["scene"]),
							createVNode(_sfc_main$2, {
								class: "task-gantt-label task-gantt-section",
								scene: section(row.record, labelWidth.value, unref(appearance).language)
							}, null, 8, ["scene"]),
							_cache[16] || (_cache[16] = createBaseVNode("div", { class: "task-gantt-timeline" }, null, -1))
						], 64)) : row.kind === "group" ? (openBlock(), createElementBlock(Fragment, { key: 1 }, [
							createVNode(_sfc_main$2, {
								class: "gantt-band gantt-group-band",
								scene: band(row.kind, labelWidth.value + timelineWidth.value, row.record, __props.collapsed.includes(row.record.groupKey)),
								onEvent: _cache[1] || (_cache[1] = (action) => emit("collapse", action.value))
							}, null, 8, ["scene"]),
							createVNode(_sfc_main$2, {
								class: "task-gantt-label gantt-group-label",
								scene: group(row.record, labelWidth.value, __props.collapsed.includes(row.record.groupKey)),
								interactive: false
							}, null, 8, ["scene"]),
							createVNode(_sfc_main$2, {
								class: "task-gantt-timeline",
								scene: groupTimeline(row.record, dayWidth.value, __props.collapsed.includes(row.record.groupKey)),
								interactive: false
							}, null, 8, ["scene"])
						], 64)) : (openBlock(), createElementBlock(Fragment, { key: 2 }, [
							createVNode(_sfc_main$2, {
								class: "gantt-row-surface",
								scene: rowSurface(rowModel(row.record), labelWidth.value + timelineWidth.value),
								interactive: false
							}, null, 8, ["scene"]),
							createVNode(_sfc_main$2, {
								class: "task-gantt-label",
								scene: taskLabel(rowModel(row.record), labelWidth.value, unref(appearance).language),
								onEvent: labelAction
							}, null, 8, ["scene"]),
							createBaseVNode("div", {
								class: "task-gantt-timeline",
								onDblclick: ($event) => edit(row.key)
							}, [row.record.ganttScheduled || drag.value?.key === row.key ? (openBlock(), createElementBlock("div", {
								key: 0,
								class: "task-gantt-bar",
								style: normalizeStyle(geometry(row.record)),
								title: row.record.parentTitle + " · " + row.record.status + "\n" + row.record.start + " — " + row.record.end + "\n" + warningText(row.record)
							}, [
								createVNode(_sfc_main$2, {
									class: "gantt-bar-paint",
									scene: barScene(row.record),
									interactive: false
								}, null, 8, ["scene"]),
								createVNode(_sfc_main$1, {
									class: "task-gantt-move",
									"aria-label": unref(t)("Edit schedule") + " " + row.record.parentTitle,
									disabled: __props.busy,
									onClick: ($event) => activate(row.key, $event),
									onDblclick: ($event) => emit("object", row.key),
									onPointerdown: ($event) => begin$1(row.record, "move", $event),
									onPointermove: move,
									onPointerup: _cache[2] || (_cache[2] = withModifiers(($event) => finish(), ["stop"])),
									onPointercancel: _cache[3] || (_cache[3] = ($event) => finish(true))
								}, null, 8, [
									"aria-label",
									"disabled",
									"onClick",
									"onDblclick",
									"onPointerdown"
								]),
								createBaseVNode("small", _hoisted_7, toDisplayString(dateLabel$1(row.record.start)), 1),
								createBaseVNode("small", _hoisted_8, toDisplayString(dateLabel$1(row.record.end)), 1),
								createVNode(_sfc_main$1, {
									label: "Resize start date",
									"icon-only": "",
									class: "task-gantt-resize start",
									disabled: __props.busy,
									onClick: ($event) => edit(row.key),
									onPointerdown: ($event) => begin$1(row.record, "start", $event),
									onPointermove: move,
									onPointerup: _cache[4] || (_cache[4] = withModifiers(($event) => finish(), ["stop"])),
									onPointercancel: _cache[5] || (_cache[5] = ($event) => finish(true))
								}, null, 8, [
									"disabled",
									"onClick",
									"onPointerdown"
								]),
								createVNode(_sfc_main$1, {
									label: "Resize deadline",
									"icon-only": "",
									class: "task-gantt-resize end",
									disabled: __props.busy,
									onClick: ($event) => edit(row.key),
									onPointerdown: ($event) => begin$1(row.record, "end", $event),
									onPointermove: move,
									onPointerup: _cache[6] || (_cache[6] = withModifiers(($event) => finish(), ["stop"])),
									onPointercancel: _cache[7] || (_cache[7] = ($event) => finish(true))
								}, null, 8, [
									"disabled",
									"onClick",
									"onPointerdown"
								]),
								row.record.ganttScheduled && parseFloat(geometry(row.record).width) >= 36 && (Object.hasOwn(tasksByKey.value.get(row.key) || {}, "progress") || Object.hasOwn(tasksByKey.value.get(row.key) || {}, "completion")) ? (openBlock(), createBlock(_sfc_main$1, {
									key: 0,
									class: "gantt-progress-handle",
									label: "Progress",
									role: "slider",
									"aria-valuenow": progress(row.record),
									"aria-valuemin": "0",
									"aria-valuemax": "100",
									style: normalizeStyle({ left: progressLeft(parseFloat(geometry(row.record).width), progress(row.record)) + "px" }),
									disabled: __props.busy,
									onKeydown: ($event) => progressKey$1($event, row.record),
									onPointerdown: ($event) => begin$1(row.record, "progress", $event),
									onPointermove: move,
									onPointerup: _cache[8] || (_cache[8] = withModifiers(($event) => finish(), ["stop"])),
									onPointercancel: _cache[9] || (_cache[9] = ($event) => finish(true))
								}, {
									default: withCtx(() => [..._cache[17] || (_cache[17] = [createBaseVNode("span", null, null, -1)])]),
									_: 1
								}, 8, [
									"aria-valuenow",
									"style",
									"disabled",
									"onKeydown",
									"onPointerdown"
								])) : createCommentVNode("", true)
							], 12, _hoisted_6)) : createCommentVNode("", true), !row.record.ganttScheduled ? (openBlock(), createElementBlock("div", {
								key: 1,
								class: "gantt-issue",
								style: normalizeStyle({
									opacity: drag.value?.key === row.key ? 0 : 1,
									width: issue(row.record, timelineViewport.value, unref(appearance).language).width + "px"
								})
							}, [createVNode(_sfc_main$2, {
								scene: issue({
									...row.record,
									radius: unref(metrics$1)(unref(appearance).theme).itemRadius
								}, timelineViewport.value, unref(appearance).language),
								interactive: false
							}, null, 8, ["scene"]), createVNode(_sfc_main$1, {
								label: "Set task schedule",
								"icon-only": "",
								disabled: __props.busy,
								onClick: ($event) => edit(row.key),
								onPointerdown: ($event) => begin$1(row.record, "create", $event, true),
								onPointermove: move,
								onPointerup: _cache[10] || (_cache[10] = withModifiers(($event) => finish(), ["stop"])),
								onPointercancel: _cache[11] || (_cache[11] = ($event) => finish(true))
							}, null, 8, [
								"disabled",
								"onClick",
								"onPointerdown"
							])], 4)) : createCommentVNode("", true)], 40, _hoisted_5)
						], 64))], 14, _hoisted_4);
					}), 128))
				], 4), !range.value?.records.length ? (openBlock(), createBlock(_sfc_main$2, {
					key: 0,
					class: "gantt-empty",
					scene: empty(viewport.value - gutter.value, bodyHeight.value, __props.projecting, unref(appearance).language),
					interactive: false
				}, null, 8, ["scene"])) : createCommentVNode("", true)], 40, _hoisted_3),
				createBaseVNode("div", _hoisted_9, [createVNode(_sfc_main$2, {
					scene: overview(range.value || {}, labelWidth.value, viewport.value - gutter.value, timelineWidth.value, scrollX.value, unref(appearance).language),
					interactive: false
				}, null, 8, ["scene"]), createBaseVNode("div", {
					class: "task-gantt-overview",
					style: normalizeStyle({
						left: labelWidth.value + "px",
						width: timelineViewport.value + "px"
					}),
					role: "slider",
					tabindex: "0",
					"aria-label": unref(t)("Timeline overview"),
					"aria-valuemin": "0",
					"aria-valuemax": dayCount.value,
					"aria-valuenow": Math.round(scrollX.value / dayWidth.value),
					onPointerdown: overview$1,
					onPointermove: overview$1,
					onKeydown: [_cache[14] || (_cache[14] = withKeys(withModifiers(($event) => setScroll(scrollX.value - 100), ["prevent"]), ["left"])), _cache[15] || (_cache[15] = withKeys(withModifiers(($event) => setScroll(scrollX.value + 100), ["prevent"]), ["right"]))]
				}, null, 44, _hoisted_10)]),
				createBaseVNode("footer", _hoisted_11, [
					createVNode(_sfc_main$2, {
						class: "gantt-footer-frame",
						scene: footerScene.value,
						onEvent: footerAction
					}, null, 8, ["scene"]),
					createVNode(_sfc_main$3, {
						ref_key: "optionsTrigger",
						ref: optionsTrigger,
						anchor: optionsAnchor.value,
						label: "Schedule options",
						overlay: "",
						"external-trigger": "",
						width: 284,
						"close-on-select": false
					}, {
						default: withCtx(() => [createVNode(_sfc_main$2, {
							style: normalizeStyle({
								width: "268px",
								height: optionsScene.value.height + "px"
							}),
							scene: optionsScene.value,
							onEvent: optionAction
						}, null, 8, ["style", "scene"])]),
						_: 1
					}, 8, ["anchor"]),
					createVNode(_sfc_main$3, {
						ref_key: "scaleTrigger",
						ref: scaleTrigger,
						anchor: scaleAnchor.value,
						label: "Timeline scale",
						overlay: "",
						"external-trigger": "",
						width: 170
					}, {
						default: withCtx(() => [createVNode(_sfc_main$2, {
							style: {
								"width": "154px",
								"height": "170px"
							},
							scene: scaleOptions(scale.value, 154, unref(appearance).language),
							onEvent: optionAction
						}, null, 8, ["scene"])]),
						_: 1
					}, 8, ["anchor"]),
					viewport.value >= 380 ? (openBlock(), createElementBlock("div", _hoisted_12, [renderSlot(_ctx.$slots, "footer")])) : createCommentVNode("", true)
				])
			], 12, _hoisted_1);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=TaskGanttView.js.map