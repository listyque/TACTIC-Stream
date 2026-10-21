import { N as openBlock, P as renderList, Z as ref, _ as createElementBlock, b as createVNode, g as createCommentVNode, h as createBlock, it as toDisplayString, j as onMounted, k as onBeforeUnmount, m as createBaseVNode, nt as normalizeClass, p as computed, q as withDirectives, rt as normalizeStyle, s as vShow, tt as unref, u as Fragment } from "./vue.js";
import { A as appearance, K as metrics, k as t } from "./index.js";
import { Kt as node, Ut as button, Wt as label, i as _sfc_main$1, qt as rect, r as observeFrameSizes, y as translate } from "./CodeBlock.js";
//#region ../src/tactic_stream/shared_ui/features/tasks/calendar.ui.mjs
function layout(width, height) {
	const compact = width < 500 || height < 430;
	const margin = compact ? 6 : 10, gap = compact ? 5 : 8, cellGap = compact ? 2 : 4;
	const inner = Math.max(0, width - 2 * margin);
	const gridY = margin + 34 + gap + 22 + gap;
	const gridHeight = Math.max(0, height - gridY - gap - 28 - margin);
	return {
		compact,
		margin,
		gap,
		cellGap,
		inner,
		gridY,
		gridHeight,
		cellWidth: Math.max(0, (inner - 6 * cellGap) / 7),
		cellHeight: Math.max(0, (gridHeight - 5 * cellGap) / 6),
		footerY: height - margin - 28
	};
}
function navigation(model, width, language) {
	const tr = (text) => translate(text, language), nodes = [];
	const icon = (id, x, text, name, type) => nodes.push(button(id, rect(x, 3, 28, 28), "", name, { type }, !model.busy, {
		label: tr(text),
		iconOnly: true,
		iconAction: true,
		iconSize: 16
	}));
	icon("calendarPrevious", 0, "Previous month", "chevron_left", "previous");
	const trailing = model.selectedDay ? 128 : 96;
	nodes.push(node("DateChoice", "calendarMonth", rect(32, 1, Math.max(0, width - 36 - trailing), 32), {
		label: tr("Calendar month"),
		text: model.monthDate,
		includeTime: false,
		monthOnly: true,
		allowClear: false,
		enabled: !model.busy,
		action: { type: "month-value" }
	}));
	let x = width - trailing;
	icon("calendarNext", x, "Next month", "chevron_right", "next");
	x += 32;
	icon("calendarToday", x, "Today", "calendar_today", "today");
	x += 32;
	if (model.selectedDay) {
		icon("calendarClearDay", x, "Clear selected day", "filter_alt_off", "clear");
		x += 32;
	}
	icon("calendarAgenda", x, "Agenda", "format-list-bulleted", "agenda");
	return { nodes };
}
function weekday(index, width, language) {
	return { nodes: [label("calendarWeekday" + index, rect(0, 3, width, 16), (language === "ru" ? [
		"ПН",
		"ВТ",
		"СР",
		"ЧТ",
		"ПТ",
		"СБ",
		"ВС"
	] : [
		"MON",
		"TUE",
		"WED",
		"THU",
		"FRI",
		"SAT",
		"SUN"
	])[index], {
		fontRole: "caption",
		color: "secondaryText",
		weight: 600,
		align: "center"
	})] };
}
function taskLimit(height, compact, milestones) {
	return compact ? 0 : Math.max(1, Math.min(3, Math.floor((height - (milestones ? 54 : 30)) / 22)));
}
function day(model, width, height, language) {
	const nodes = [], today = !!model.today, weekend = model.index % 7 >= 5;
	const limit = taskLimit(height, model.compact, (model.milestones || []).length);
	const radius = model.radius || 8;
	const color = model.selected ? "secondaryContainer" : model.hovered ? "surfaceContainerHighest" : weekend ? "surfaceContainerLow" : "surfaceContainer";
	nodes.push(node("Box", "calendarDaySurface", rect(0, 0, width, height), {
		background: color,
		radius
	}));
	nodes.push(node("Action", "calendarDayAction", rect(0, 0, width, height), {
		text: model.date,
		selected: !!model.selected,
		enabled: !model.busy,
		action: {
			type: "day",
			value: model.date
		},
		radius
	}));
	if (today) nodes.push(node("Box", "calendarTodayCircle", rect(5, 5, 23, 23), {
		background: "action",
		radius: 11.5
	}));
	nodes.push(label("calendarDayNumber", rect(5, 8.5, 23, 16), String(model.day), {
		fontRole: "secondary",
		align: "center",
		color: today ? "selectedText" : "primaryText",
		weight: today ? 600 : 400
	}));
	if (model.taskCount) nodes.push(label("calendarTaskCount", rect(width - 34, 7, 27, 15), String(model.taskCount), {
		fontRole: "caption",
		align: "right",
		weight: 600,
		color: model.overdueCount ? "error" : "secondaryText"
	}));
	const milestone = (model.milestones || [])[0];
	if (milestone) {
		const bandHeight = model.compact ? 8 : 20;
		nodes.push(node("Box", "calendarMilestoneBand", rect(5, 31, width - 10, bandHeight), {
			background: "tertiaryContainer",
			border: "tertiary",
			borderWidth: 1,
			radius: 6
		}));
		if (!model.compact) {
			nodes.push(node("Icon", "calendarMilestoneIcon", rect(10, 35.5, 11, 11), {
				icon: "milestone",
				color: "tertiary"
			}));
			nodes.push(label("calendarMilestoneLabel", rect(25, 33.5, width - 32, 15), milestone.label, {
				fontRole: "caption",
				weight: 600
			}));
		}
		nodes.push(node("Action", "calendarMilestoneAction", rect(5, 31, width - 10, bandHeight), {
			text: milestone.label,
			enabled: !model.busy,
			action: {
				type: "milestone",
				value: milestone.code
			}
		}));
	}
	let y = milestone ? 55 : 31;
	for (const task of (model.tasks || []).slice(0, limit)) {
		nodes.push(node("Box", "calendarTaskSurface" + task.taskCode, rect(5, y, width - 10, 19), {
			background: task.selected ? "secondaryContainer" : "row",
			radius: 6
		}));
		nodes.push(node("Box", "calendarTaskDot" + task.taskCode, rect(10, y + 6.5, 6, 6), {
			background: task.statusColor || "action",
			radius: 3
		}));
		nodes.push(label("calendarTaskText" + task.taskCode, rect(20, y + 2, width - 30, 15), task.parentTitle + " · " + task.processLabel, { fontRole: "caption" }));
		nodes.push(node("Action", "calendarTaskOpen" + task.taskCode, rect(5, y, width - 10, 19), {
			text: task.parentTitle + " · " + task.processLabel,
			enabled: !model.busy,
			action: {
				type: "inspect",
				value: task.taskCode,
				parentKey: task.parentKey,
				process: task.process
			}
		}));
		y += 22;
	}
	if (limit && model.taskCount > limit) nodes.push(label("calendarMoreTasks", rect(5, y, width - 10, 14), translate("{count} more tasks", language, { count: model.taskCount - limit }), {
		fontRole: "caption",
		color: "secondaryText",
		align: "right"
	}));
	if (!limit) (model.tasks || []).slice(0, 5).forEach((task, index) => nodes.push(node("Box", "calendarStatusDot" + index, rect(6 + index * 9, height - 12, 6, 6), {
		background: task.statusColor || "action",
		radius: 3
	})));
	return { nodes };
}
function footer(model, width, language) {
	const tr = (text) => translate(text, language), nodes = [];
	nodes.push(node("Icon", "calendarFooterIcon", rect(0, 7.5, 13, 13), {
		icon: "calendar_month",
		color: "secondaryText"
	}));
	nodes.push(label("calendarFooterText", rect(19, 6, width - 54 - (model.hasMore ? 32 : 0), 16), model.selectedDay ? translate("Task Browser filtered by {date}", language, { date: model.selectedDay }) : tr("Select a day to filter Task Browser"), {
		fontRole: "caption",
		color: "secondaryText"
	}));
	if (model.hasMore) nodes.push(button("calendarLoadMore", rect(width - 60, 0, 28, 28), "", "add", { type: "load-more" }, !model.busy, {
		label: tr("Load more tasks"),
		iconOnly: true,
		iconAction: true,
		iconSize: 16
	}));
	nodes.push(button("calendarTasks", rect(width - 28, 0, 28, 28), "", "tasks", { type: "tasks" }, true, {
		label: tr("Task Manager"),
		iconOnly: true,
		iconAction: true,
		iconSize: 16
	}));
	return { nodes };
}
function agendaRows(days, selected) {
	const rows = [];
	for (const day of days) {
		if (selected ? day.date !== selected : !day.inMonth) continue;
		if (!(day.tasks || []).length && !(day.milestones || []).length) continue;
		rows.push({
			kind: "date",
			key: day.date,
			text: day.date
		});
		for (const marker of day.milestones || []) rows.push({
			kind: "milestone",
			key: day.date + marker.code,
			text: marker.label,
			action: {
				type: "milestone",
				value: marker.code
			}
		});
		for (const task of day.tasks || []) rows.push({
			kind: "task",
			key: day.date + task.taskCode,
			text: task.parentTitle + " · " + task.processLabel + " · " + task.status,
			action: {
				type: "inspect",
				value: task.taskCode,
				parentKey: task.parentKey,
				process: task.process
			}
		});
	}
	return rows;
}
function agendaRow(row, width) {
	return { nodes: row.kind === "date" ? [label("calendarAgendaDate", rect(0, 8, width, 18), row.text, {
		fontRole: "body",
		weight: 600
	})] : [button("calendarAgendaAction", rect(0, 2, width, 30), row.text, row.kind === "milestone" ? "milestone" : "", row.action, true, { align: "left" })] };
}
//#endregion
//#region src/features/tasks/TaskCalendarView.vue
var _hoisted_1 = ["aria-label", "aria-busy"];
var _hoisted_2 = {
	key: 0,
	role: "alert",
	class: "calendar-error"
};
var _hoisted_3 = {
	key: 0,
	class: "muted"
};
var _sfc_main = {
	__name: "TaskCalendarView",
	props: {
		projection: Object,
		year: Number,
		month: Number,
		selectedDay: String,
		busy: Boolean,
		projecting: Boolean,
		error: String,
		hasMore: Boolean
	},
	emits: [
		"month",
		"month-value",
		"today",
		"day",
		"inspect",
		"milestone",
		"load-more",
		"tasks"
	],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const root = ref(null), width = ref(600), height = ref(500), agenda = ref(false), hovered = ref("");
		let observer;
		const layout$1 = computed(() => layout(width.value, height.value));
		const days = computed(() => props.projection?.calendar || []);
		const model = computed(() => ({
			...props,
			monthDate: props.year + "-" + String(props.month).padStart(2, "0") + "-01"
		}));
		const rows = computed(() => agendaRows(days.value, props.selectedDay));
		const bounds = (x, y, w, h) => ({
			left: x + "px",
			top: y + "px",
			width: w + "px",
			height: h + "px"
		});
		function action(event) {
			if (event.type === "previous") emit("month", -1);
			else if (event.type === "next") emit("month", 1);
			else if (event.type === "agenda") agenda.value = !agenda.value;
			else if (event.type === "clear") emit("day", "");
			else emit(event.type, event.type === "month-value" ? event.value.slice(0, 7) : event.value);
		}
		function dayModel(day, index) {
			return {
				...day,
				index,
				compact: layout$1.value.compact,
				selected: day.date === props.selectedDay,
				hovered: hovered.value === day.date,
				busy: props.busy,
				radius: metrics(appearance.theme).itemRadius
			};
		}
		onMounted(() => {
			observer = observeFrameSizes((entries) => {
				width.value = entries[0].contentRect.width;
				height.value = entries[0].contentRect.height;
			});
			observer.observe(root.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				ref_key: "root",
				ref: root,
				class: normalizeClass(["task-calendar-view", { compact: layout$1.value.compact }]),
				"aria-label": unref(t)("Task calendar"),
				"aria-busy": __props.projecting
			}, [
				createVNode(_sfc_main$1, {
					class: "calendar-navigation",
					style: normalizeStyle(bounds(layout$1.value.margin, layout$1.value.margin, layout$1.value.inner, 34)),
					scene: navigation(model.value, layout$1.value.inner, unref(appearance).language),
					onEvent: action
				}, null, 8, ["style", "scene"]),
				__props.error ? (openBlock(), createElementBlock("p", _hoisted_2, toDisplayString(unref(t)(__props.error)), 1)) : createCommentVNode("", true),
				withDirectives(createBaseVNode("div", {
					class: "calendar-weekdays",
					style: normalizeStyle(bounds(layout$1.value.margin, layout$1.value.margin + 34 + layout$1.value.gap, layout$1.value.inner, 22))
				}, [(openBlock(), createElementBlock(Fragment, null, renderList(7, (index) => {
					return createVNode(_sfc_main$1, {
						key: index,
						style: normalizeStyle(bounds((index - 1) * (layout$1.value.cellWidth + layout$1.value.cellGap), 0, layout$1.value.cellWidth, 22)),
						scene: weekday(index - 1, layout$1.value.cellWidth, unref(appearance).language)
					}, null, 8, ["style", "scene"]);
				}), 64))], 4), [[vShow, !agenda.value]]),
				withDirectives(createBaseVNode("div", {
					class: "task-calendar-grid",
					style: normalizeStyle(bounds(layout$1.value.margin, layout$1.value.gridY, layout$1.value.inner, layout$1.value.gridHeight))
				}, [(openBlock(true), createElementBlock(Fragment, null, renderList(days.value, (day$1, index) => {
					return openBlock(), createBlock(_sfc_main$1, {
						key: day$1.date,
						class: "task-calendar-day",
						"data-date": day$1.date,
						style: normalizeStyle({
							...bounds(index % 7 * (layout$1.value.cellWidth + layout$1.value.cellGap), Math.floor(index / 7) * (layout$1.value.cellHeight + layout$1.value.cellGap), layout$1.value.cellWidth, layout$1.value.cellHeight),
							opacity: day$1.inMonth ? 1 : .55
						}),
						scene: day(dayModel(day$1, index), layout$1.value.cellWidth, layout$1.value.cellHeight, unref(appearance).language),
						onPointerenter: ($event) => hovered.value = day$1.date,
						onPointerleave: _cache[0] || (_cache[0] = ($event) => hovered.value = ""),
						onEvent: action
					}, null, 8, [
						"data-date",
						"style",
						"scene",
						"onPointerenter"
					]);
				}), 128))], 4), [[vShow, !agenda.value]]),
				agenda.value ? (openBlock(), createElementBlock("div", {
					key: 1,
					class: "task-calendar-agenda",
					style: normalizeStyle(bounds(layout$1.value.margin, layout$1.value.margin + 34 + layout$1.value.gap, layout$1.value.inner, layout$1.value.footerY - layout$1.value.margin - 34 - layout$1.value.gap * 2))
				}, [(openBlock(true), createElementBlock(Fragment, null, renderList(rows.value, (row) => {
					return openBlock(), createBlock(_sfc_main$1, {
						key: row.key,
						style: { "height": "34px" },
						scene: agendaRow(row, layout$1.value.inner - 14),
						onEvent: action
					}, null, 8, ["scene"]);
				}), 128)), !rows.value.length ? (openBlock(), createElementBlock("p", _hoisted_3, toDisplayString(unref(t)("No loaded tasks on these dates.")), 1)) : createCommentVNode("", true)], 4)) : createCommentVNode("", true),
				createVNode(_sfc_main$1, {
					class: "calendar-footer",
					style: normalizeStyle(bounds(layout$1.value.margin, layout$1.value.footerY, layout$1.value.inner, 28)),
					scene: footer(model.value, layout$1.value.inner, unref(appearance).language),
					onEvent: action
				}, null, 8, ["style", "scene"])
			], 10, _hoisted_1);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=TaskCalendarView.js.map