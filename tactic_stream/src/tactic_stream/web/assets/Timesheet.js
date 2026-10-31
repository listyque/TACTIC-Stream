import { r as __exportAll } from "./ObjectFieldFrame.js";
import { A as onMounted, E as nextTick, F as resolveComponent, G as withCtx, I as resolveDirective, K as withDirectives, L as resolveDynamicComponent, M as openBlock, N as renderList, O as onBeforeUnmount, X as ref, _ as createElementBlock, b as createVNode, et as unref, f as Teleport, g as createCommentVNode, h as createBlock, l as withModifiers, m as createBaseVNode, nt as normalizeStyle, p as computed, rt as toDisplayString, s as vShow, tt as normalizeClass, u as Fragment } from "./vue.js";
import { R as _plugin_vue_export_helper_default, o as t, s as appearance, t as _sfc_main$4 } from "./AppButton.js";
import { k as rpc } from "./index.js";
import { C as frameContentWidth, G as node, H as label, K as rect, S as translate, V as button, j as _sfc_main$6, t as _sfc_main$5, w as observeFrameSizes, z as _sfc_main$7 } from "./FrameView.js";
//#region ../src/tactic_stream/shared_ui/features/workhours/reports.ui.mjs
var titles = {
	my_hours: "My Work Hours",
	bid_actual: "Bid vs Actual",
	approval: "Approval",
	team: "Team Hours",
	process: "Process Hours",
	labor_cost: "Labor Cost"
};
var descriptions = {
	my_hours: "Daily logged time",
	bid_actual: "Planned and approved hours",
	approval: "Approved and pending time",
	team: "Hours by user",
	process: "Hours by process",
	labor_cost: "Authorized wage-based cost"
};
function allowed(record, model) {
	return !record.permission || record.permission === "user" || record.permission === "supervisor" && !!model.canManage || record.permission === "finance" && !!model.canViewCosts;
}
function describe(model, width, height, language) {
	const tr = (text) => translate(text, language), compact = width < 640;
	const nav = compact ? 0 : Math.min(230, Math.max(170, width * .28));
	const x = compact ? 8 : nav + 9, y = compact ? 50 : 9, main = Math.max(0, width - x - 9);
	const nodes = [node("Box", "workReportBackground", rect(0, 0, width, height), { background: "workspace" })];
	if (compact) nodes.push(node("Choice", "workReportChoice", rect(8, 8, Math.max(0, width - 16), 34), {
		label: tr("Report"),
		value: model.report,
		options: (model.options || []).filter((record) => allowed(record, model)).map((record) => ({
			value: record.key || record.value,
			label: tr(titles[record.key || record.value] || record.title || record.label)
		})),
		enabled: !model.busy,
		action: { type: "report" }
	}));
	else nodes.push(node("List", "workReportTypes", rect(7, 7, Math.max(0, nav - 14), Math.max(0, height - 14)), {
		source: "reports",
		keyField: "key",
		fields: [
			"key",
			"title",
			"description",
			"icon",
			"permission",
			"selected"
		],
		rowHeight: 54,
		rowGap: 4
	}));
	nodes.push(label("workReportTitle", rect(x, y, Math.max(0, main - 37), 28), tr(titles[model.report] || "Work reports"), {
		fontRole: "title",
		weight: 600,
		role: "heading"
	}));
	nodes.push(button("workReportRefresh", rect(x + Math.max(0, main - 30), y, 30, 30), tr("Refresh report"), "refresh", { type: "refresh" }, !model.busy, { iconOnly: true }));
	nodes.push(label("workReportDates", rect(x, y + 31, main, 22), (model.weekStart || "") + " — " + (model.weekEnd || ""), {
		fontRole: "caption",
		color: "secondaryText"
	}));
	const message = model.error || model.message || "";
	if (message) nodes.push(label("workReportMessage", rect(x, y + 58, main, 38), tr(message), {
		maxLines: 2,
		color: model.error ? "error" : "secondaryText"
	}));
	const top = y + (message ? 103 : 60);
	nodes.push(node("List", "workReportValues", rect(x, top, main, Math.max(0, height - top - 9)), {
		source: "values",
		keyField: "label",
		fields: [
			"label",
			"value",
			"valueLabel",
			"share"
		],
		rowHeight: 52,
		rowGap: 6
	}));
	if (!model.count && !model.busy) nodes.push(label("workReportEmpty", rect(x, top, main, 44), tr("No report data for this week"), {
		color: "secondaryText",
		wrap: true
	}));
	return { nodes };
}
function descriptor(record, model, width, language) {
	const key = record.key || record.value;
	const permitted = allowed(record, model);
	return { nodes: [node("Action", "workReport-" + key, rect(0, 0, width, 54), {
		text: translate(titles[key] || record.title || record.label, language),
		enabled: !!permitted && !model.busy,
		selected: key === model.report,
		normalColor: "transparent",
		selectedColor: "contentSelection",
		action: {
			type: "report",
			value: key
		},
		children: [
			node("Icon", "workReportTypeIcon", rect(8, 18, 18, 18), {
				icon: record.icon || "bar-chart",
				color: key === model.report ? "action" : "secondaryText"
			}),
			label("workReportTypeTitle", rect(34, 5, Math.max(0, width - 42), 22), translate(titles[key] || record.title || record.label, language), { weight: 600 }),
			label("workReportTypeDescription", rect(34, 28, Math.max(0, width - 42), 18), translate(descriptions[key] || record.description || "", language), {
				fontRole: "caption",
				color: "secondaryText"
			})
		]
	})] };
}
function valueRow(record, width, language) {
	const tr = (text) => translate(text, language), name = record.localized ? tr(record.label) : record.label;
	const labelWidth = Math.min(180, width * .34), barX = 20 + labelWidth, barWidth = Math.max(0, width - barX - 90);
	const share = Math.max(0, Math.min(1, Number(record.share) || 0));
	return { nodes: [
		node("Box", "workReportValueSurface", rect(0, 0, width, 52), {
			background: "surfaceContainerLow",
			radius: 8
		}),
		label("workReportValueLabel", rect(10, 12, labelWidth, 28), name || ""),
		node("Box", "workReportValueTrack", rect(barX, 23, barWidth, 6), {
			background: "surfaceContainerHighest",
			radius: 3
		}),
		node("Box", "workReportValueFill", rect(barX, 23, barWidth * share, 6), {
			background: "action",
			radius: 3
		}),
		label("workReportValueNumber", rect(Math.max(0, width - 80), 12, 70, 28), String(record.valueLabel || "").replace(/ h$/, tr(" h")), {
			weight: 600,
			align: "right"
		})
	] };
}
//#endregion
//#region src/features/objects/WorkReportSurface.vue
var _sfc_main$3 = {
	__name: "WorkReportSurface",
	props: {
		data: Object,
		report: String,
		busy: Boolean
	},
	emits: ["report", "refresh"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const host = ref(null), width = ref(600), height = ref(400);
		const options = computed(() => (props.data?.reports || []).map((row) => ({
			...row,
			key: row.value
		})));
		const values = computed(() => (props.data?.rows || []).map((row) => ({
			...row,
			valueLabel: props.data.unit === "cost" ? Number(row.value).toFixed(2) : row.value + " h"
		})));
		const model = computed(() => ({
			report: props.report,
			busy: props.busy,
			count: values.value.length,
			options: options.value,
			weekStart: props.data?.week_start,
			weekEnd: props.data?.week_end,
			message: props.data?.message
		}));
		const scene = computed(() => describe(model.value, width.value, height.value, appearance.language));
		function row(list, record) {
			return list.source === "reports" ? descriptor(record, model.value, Math.max(0, list.width - 16), appearance.language) : valueRow(record, Math.max(0, list.width - 16), appearance.language);
		}
		let observer;
		onMounted(() => {
			observer = observeFrameSizes(() => {
				width.value = host.value.clientWidth;
				height.value = host.value.clientHeight;
			});
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "work-report-surface"
			}, [createVNode(_sfc_main$5, {
				scene: scene.value,
				models: {
					reports: options.value,
					values: values.value
				},
				"describe-row": row,
				onEvent: _cache[0] || (_cache[0] = (action) => action.type === "report" ? emit("report", action.value) : emit("refresh"))
			}, null, 8, ["scene", "models"])], 512);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/features/workhours/sheet.ui.mjs
function toolbar(model, width, language) {
	const tr = (text) => translate(text, language);
	const nodes = [], enabled = !model.busy && !model.locked;
	nodes.push(button("timesheetPrevious", rect(8, 7, 30, 30), tr("Previous week"), "chevron-left", {
		type: "week",
		value: -1
	}, enabled, { iconOnly: true }));
	nodes.push(node("DateChoice", "timesheetWeek", rect(44, 6, 176, 32), {
		text: model.weekStart || "",
		label: tr("Week"),
		includeTime: false,
		allowClear: false,
		enabled,
		action: { type: "date" }
	}));
	nodes.push(button("timesheetNext", rect(226, 7, 30, 30), tr("Next week"), "chevron-right", {
		type: "week",
		value: 1
	}, enabled, { iconOnly: true }));
	let right = width - 7;
	for (const record of [
		[
			"timesheetRefresh",
			"Refresh timesheet",
			"refresh",
			"refresh",
			true
		],
		[
			"timesheetReports",
			"Open work reports",
			"bar-chart",
			"reports",
			true
		],
		[
			"timesheetCreate",
			model.canCreate ? "Log time for the selected task" : "Select a task before logging time",
			"add-alarm",
			"create",
			!!model.canCreate
		]
	]) {
		right -= 30;
		nodes.push(button(record[0], rect(right, width < 384 ? 44 : 7, 30, 30), tr(record[1]), record[2], { type: record[3] }, enabled && record[4], { iconOnly: true }));
		right -= 6;
	}
	let top = width < 384 ? 81 : 44;
	if (model.canManage) {
		nodes.push(node("UserChoice", "timesheetUser", rect(8, top, Math.max(0, Math.min(260, width - 16)), 32), {
			label: tr("Team member"),
			value: model.login || "",
			options: model.users || [],
			enabled,
			action: { type: "user" }
		}));
		top += 39;
	}
	if (model.selectedCount) {
		nodes.push(label("timesheetSelection", rect(8, top, Math.max(0, width - 132), 30), tr("{count} selected").replace("{count}", model.selectedCount), { color: "secondaryText" }));
		let x = width - 116;
		for (const record of [
			[
				"approve",
				"Approve selected entries",
				"approval"
			],
			[
				"reject",
				"Return selected entries to pending",
				"undo"
			],
			[
				"clear",
				"Clear selection",
				"close"
			]
		]) {
			nodes.push(button("timesheetBulk-" + record[0], rect(x, top, 30, 30), tr(record[1]), record[2], { type: record[0] }, enabled, { iconOnly: true }));
			x += 36;
		}
		top += 37;
	}
	return {
		nodes,
		height: top
	};
}
function summary(values, width, language) {
	const tr = (text) => translate(text, language), nodes = [], keys = [
		"logged",
		"approved",
		"pending",
		"overtime"
	];
	const columns = width < 480 ? 2 : 4;
	const size = Math.max(0, (width - 7 * (columns - 1)) / columns);
	for (let index = 0; index < keys.length; index++) {
		const key = keys[index], x = index % columns * (size + 7), y = Math.floor(index / columns) * 59;
		nodes.push(node("Box", "timesheetSummary-" + key, rect(x, y, size, 52), {
			background: "surfaceContainerHigh",
			radius: 8
		}));
		nodes.push(label("timesheetSummaryValue-" + key, rect(x + 4, y + 5, Math.max(0, size - 8), 24), String(values?.[key] || 0) + tr(" h"), {
			fontRole: "bodyLarge",
			weight: 600,
			align: "center"
		}));
		nodes.push(label("timesheetSummaryLabel-" + key, rect(x + 4, y + 30, Math.max(0, size - 8), 18), tr(key[0].toUpperCase() + key.slice(1)), {
			fontRole: "caption",
			color: "secondaryText",
			align: "center"
		}));
	}
	return {
		nodes,
		height: columns === 2 ? 111 : 52
	};
}
function entry(record, width, language) {
	const tr = (text) => translate(text, language), compact = width < 650, height = compact ? 100 : 62, nodes = [];
	const actions = [];
	if (record.canApprove) actions.push([
		"approval",
		record.status === "approved" ? "Return to pending" : "Approve entry",
		record.status === "approved" ? "undo" : "approval"
	]);
	if (record.canEdit) {
		actions.push([
			"edit",
			"Edit entry",
			"edit"
		]);
		actions.push([
			"delete",
			"Delete entry",
			"delete"
		]);
	}
	const actionWidth = actions.length * 36;
	const left = record.selectable ? 44 : 10, detailX = left + 49;
	const end = compact ? width - 10 : width - actionWidth - 10;
	nodes.push(node("Box", "timesheetEntrySurface", rect(0, 0, width, height), {
		background: record.selected ? "surfaceContainerHighest" : "surfaceContainerLow",
		radius: 8
	}));
	if (record.selectable) nodes.push(node("CheckBox", "timesheetEntrySelect", rect(0, 9, 44, 44), {
		text: "",
		indicatorX: 10,
		label: tr("Select time entry") + ": " + [record.taskTitle, record.day].filter(Boolean).join(" · "),
		checked: !!record.selected,
		enabled: !record.disabled,
		action: {
			type: "select",
			id: record.id
		}
	}));
	nodes.push(node("Box", "timesheetEntryDaySurface", rect(left, 11, 40, 40), {
		background: "surfaceContainerHighest",
		radius: 8
	}));
	nodes.push(label("timesheetEntryDay", rect(left, 13, 40, 22), String(record.day || "").slice(8, 10), {
		weight: 600,
		align: "center"
	}));
	nodes.push(label("timesheetEntryMonth", rect(left, 34, 40, 16), String(record.day || "").slice(5, 7), {
		fontRole: "caption",
		color: "secondaryText",
		align: "center"
	}));
	nodes.push(label("timesheetEntryTask", rect(detailX, 8, Math.max(0, end - detailX - 95), 24), [record.taskTitle, record.process].filter(Boolean).join(" · "), { weight: 600 }));
	nodes.push(label("timesheetEntryDescription", rect(detailX, 34, Math.max(0, end - detailX - 95 - (record.overtimeHours > 0 && !compact ? 65 : 0)), 20), [record.loginLabel, record.description].filter(Boolean).join(" · "), {
		fontRole: "caption",
		color: "secondaryText"
	}));
	nodes.push(label("timesheetEntryHours", rect(Math.max(0, end - 88), 8, 88, 24), String(record.hours || 0) + tr(" h"), {
		align: "right",
		weight: 600
	}));
	nodes.push(label("timesheetEntryStatus", rect(Math.max(0, end - 88), 34, 88, 20), tr(record.status === "approved" ? "Approved" : "Pending"), {
		align: "right",
		fontRole: "caption",
		color: record.status === "approved" ? "action" : "secondaryText"
	}));
	if (record.overtimeHours > 0) nodes.push(label("timesheetEntryOvertime", rect(compact ? 10 : Math.max(0, end - 155), compact ? 66 : 34, compact ? Math.max(0, width - actionWidth - 20) : 62, 24), tr("OT ") + record.overtimeHours + tr(" h"), {
		fontRole: "caption",
		color: "tertiary"
	}));
	let x = width - actionWidth;
	for (const [type, text, icon] of actions) {
		nodes.push(button("timesheetEntry-" + type, rect(x, compact ? 65 : 16, 30, 30), tr(text), icon, {
			type,
			id: record.id
		}, !record.disabled, {
			iconOnly: true,
			destructive: type === "delete"
		}));
		x += 36;
	}
	return {
		nodes,
		height
	};
}
function validHours(value) {
	return /^\d+(?:[.,]\d{1,2})?$/.test(String(value)) && Number(String(value).replace(",", ".")) > 0 && Number(String(value).replace(",", ".")) <= 24;
}
function editor(model, width, language) {
	const tr = (text) => translate(text, language), nodes = [], gap = 10, half = Math.max(0, (width - gap) / 2), enabled = !model.busy;
	function field(kind, id, title, text, x, y, w, field, extra) {
		nodes.push(label(id + "Label", rect(x, y, w, 20), tr(title)));
		nodes.push(node(kind, id, rect(x, y + 24, w, kind === "Area" ? 64 : 32), Object.assign({
			text: String(text ?? ""),
			label: tr(title),
			enabled,
			action: {
				type: "change",
				field
			}
		}, extra || {})));
	}
	field("DateChoice", "workHourDay", "Work date", model.day, 0, 0, half, "day", {
		includeTime: false,
		allowClear: false
	});
	field("Field", "workHourDuration", "Duration, hours", model.hours, half + gap, 0, half, "hours", {
		inputMode: "decimal",
		error: model.hours && !validHours(model.hours) ? tr("Enter hours between 0.01 and 24.") : "",
		selectOnFocus: true
	});
	nodes.push(node("Segmented", "workHourCategory", rect(0, 66, width, 32), {
		label: tr("Category"),
		value: model.category || "regular",
		options: [{
			value: "regular",
			label: tr("Regular"),
			icon: "schedule"
		}, {
			value: "overtime",
			label: tr("Overtime"),
			icon: "more-time"
		}],
		enabled,
		action: {
			type: "change",
			field: "category"
		}
	}));
	let y = 108;
	if (model.canManage) {
		nodes.push(node("UserChoice", "workHourUser", rect(0, y, width, 32), {
			label: tr("User"),
			value: model.login || "",
			options: model.users || [],
			enabled,
			action: {
				type: "change",
				field: "login"
			}
		}));
		y += 42;
	}
	field("Area", "workHourDescription", "Description", model.description, 0, y, width, "description");
	y += 102;
	if (model.error) {
		nodes.push(label("workHourError", rect(0, y, width, 40), model.error, {
			color: "error",
			maxLines: 2
		}));
		y += 46;
	}
	const canSave = enabled && validHours(model.hours) && /^\d{4}-\d{2}-\d{2}$/.test(String(model.day || ""));
	const wrapApproval = !!model.canManage && width < 500;
	const approveWidth = model.canManage && !wrapApproval ? 220 : 0;
	nodes.push(button("workHourCancel", rect(0, y, 112, 32), tr("Cancel"), "close", { type: "cancel" }, enabled));
	nodes.push(button("workHourSave", rect(Math.max(0, width - approveWidth - 143), y, 136, 32), tr("Save"), "save", { type: "save" }, canSave));
	if (model.canManage) nodes.push(button("workHourApprove", rect(wrapApproval ? 0 : Math.max(0, width - 220), wrapApproval ? y + 39 : y, wrapApproval ? width : 220, 32), tr("Save & Approve"), "approval", { type: "approve" }, canSave, { highlighted: true }));
	return {
		nodes,
		height: y + 32 + (wrapApproval ? 39 : 0)
	};
}
//#endregion
//#region src/features/objects/WorkHourForm.vue
var _sfc_main$2 = {
	__name: "WorkHourForm",
	props: {
		draft: Object,
		busy: Boolean,
		users: Array,
		error: String
	},
	emits: [
		"change",
		"cancel",
		"save"
	],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const host = ref(null), width = ref(390);
		const scene = computed(() => editor({
			...props.draft,
			busy: props.busy,
			canManage: !!props.users?.length,
			users: props.users,
			error: props.error
		}, width.value, appearance.language));
		let observer;
		onMounted(() => {
			observer = observeFrameSizes(() => width.value = host.value.clientWidth);
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "work-hour-form",
				style: normalizeStyle({ height: scene.value.height + "px" })
			}, [createVNode(_sfc_main$5, {
				scene: scene.value,
				onEvent: _cache[0] || (_cache[0] = (action) => action.type === "change" ? emit("change", action.field, action.value) : action.type === "cancel" ? emit("cancel") : emit("save", action.type === "approve"))
			}, null, 8, ["scene"])], 4);
		};
	}
};
//#endregion
//#region src/features/objects/TimeEntryPanel.vue
var _hoisted_1 = {
	key: 0,
	class: "error",
	role: "alert"
};
var _hoisted_2 = {
	key: 1,
	class: "notice"
};
var _hoisted_3 = {
	key: 2,
	class: "notice",
	role: "alert"
};
var _hoisted_4 = { class: "configuration-actions" };
var _hoisted_5 = {
	key: 5,
	class: "timesheet-filters"
};
var _hoisted_6 = {
	key: 8,
	role: "status"
};
var _hoisted_7 = {
	key: 9,
	class: "muted"
};
var _hoisted_8 = {
	key: 10,
	class: "time-entry-list"
};
var _hoisted_9 = {
	key: 0,
	class: "notice"
};
var _sfc_main$1 = {
	__name: "TimeEntryPanel",
	props: {
		pageContext: Function,
		dockTarget: String,
		dockReport: String,
		data: Object,
		draft: Object,
		editing: Boolean,
		busy: Boolean,
		error: String,
		uncertain: Boolean,
		deleting: String,
		users: Array,
		mode: {
			type: String,
			default: "task"
		},
		week: String,
		login: String,
		selected: Array,
		report: String,
		canCreate: Boolean,
		confirmation: Boolean
	},
	emits: [
		"create",
		"edit",
		"save",
		"action",
		"cancel-edit",
		"delete",
		"close",
		"refresh",
		"change",
		"scope",
		"move-week",
		"select",
		"clear-selection",
		"bulk",
		"keep-editing",
		"discard-close"
	],
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const dialog = ref(null);
		const width = ref(640);
		const language = computed(() => appearance.language);
		const toolbarModel = computed(() => ({
			weekStart: props.week,
			login: props.login,
			busy: props.busy,
			locked: props.uncertain || props.editing,
			canCreate: props.canCreate,
			canManage: !!props.users?.length,
			users: [{
				value: "",
				label: t("All users")
			}, ...props.users || []],
			selectedCount: props.selected?.length || 0
		}));
		const toolbar$1 = computed(() => toolbar(toolbarModel.value, width.value, language.value));
		function scopeAction(action) {
			if (action.type === "week") emit("move-week", action.value);
			else if (action.type === "date") emit("scope", "week", action.value);
			else if (action.type === "user") emit("scope", "login", action.value);
			else if (action.type === "refresh") emit("refresh");
			else if (action.type === "create") emit("create");
			else if (action.type === "reports") emit("scope", "mode", "report");
			else if (action.type === "clear") emit("clear-selection");
			else emit("bulk", action.type);
		}
		function entryScene(entry$1) {
			return entry({
				id: entry$1.search_key,
				day: entry$1.day,
				taskTitle: entry$1.task_title || "",
				process: entry$1.process,
				loginLabel: entry$1.login,
				description: entry$1.description,
				hours: entry$1.hours,
				overtimeHours: entry$1.category === "overtime" ? entry$1.hours : 0,
				status: entry$1.status,
				canEdit: entry$1.can_edit !== false,
				canApprove: true,
				selectable: props.mode === "week",
				selected: props.selected?.includes(entry$1.search_key),
				disabled: props.busy || props.uncertain || props.editing
			}, width.value, language.value);
		}
		function entryAction(entry, action) {
			if (action.type === "select") emit("select", entry.search_key, action.value);
			else if (action.type === "edit") emit("edit", entry);
			else if (action.type === "delete") emit("delete", entry.search_key);
			else emit("action", entry, entry.status === "approved" ? "reject" : "approve");
		}
		let observer;
		onMounted(() => nextTick(() => {
			observer = observeFrameSizes(() => width.value = frameContentWidth(dialog.value));
			observer.observe(dialog.value);
		}));
		onBeforeUnmount(() => observer?.disconnect());
		const opened = ref(false);
		__expose({
			open: () => {
				opened.value = true;
				if (!props.dockTarget) dialog.value.show();
			},
			close: () => {
				opened.value = false;
				if (!props.dockTarget) dialog.value?.close();
			},
			isOpen: () => props.dockTarget ? opened.value : !!dialog.value?.open
		});
		return (_ctx, _cache) => {
			const _directive_window = resolveDirective("window");
			return openBlock(), createBlock(Teleport, {
				defer: "",
				to: __props.dockTarget || "body"
			}, [withDirectives((openBlock(), createBlock(resolveDynamicComponent(__props.dockTarget ? "section" : "dialog"), {
				ref_key: "dialog",
				ref: dialog,
				class: normalizeClass(["time-entry-panel", {
					"record-dialog": !__props.dockTarget,
					"time-entry-panel-docked": !!__props.dockTarget
				}]),
				role: __props.dockTarget ? "region" : "dialog",
				"aria-label": unref(t)(__props.mode === "task" ? "Task timesheet" : __props.mode === "report" ? __props.dockReport === "labor_cost" ? "Cost Reports" : "Work reports" : "Weekly timesheet"),
				"aria-busy": __props.busy,
				onCancel: _cache[16] || (_cache[16] = withModifiers(($event) => emit("close"), ["prevent"]))
			}, {
				default: withCtx(() => [
					createBaseVNode("header", null, [createBaseVNode("div", null, [createBaseVNode("h2", null, toDisplayString(unref(t)(__props.mode === "task" ? "Task timesheet" : __props.mode === "report" ? __props.dockReport === "labor_cost" ? "Cost Reports" : "Work reports" : "Weekly timesheet")), 1), createBaseVNode("small", null, toDisplayString(__props.mode === "task" ? unref(t)("Time entries for the selected task") : `${__props.data?.week_start || __props.week} — ${__props.data?.week_end || ""}`), 1)]), createVNode(_sfc_main$4, {
						label: "Close",
						icon: "close",
						"icon-only": "",
						disabled: __props.busy,
						onClick: _cache[0] || (_cache[0] = ($event) => emit("close"))
					}, null, 8, ["disabled"])]),
					__props.error ? (openBlock(), createElementBlock("p", _hoisted_1, toDisplayString(unref(t)(__props.error)), 1)) : createCommentVNode("", true),
					__props.uncertain ? (openBlock(), createElementBlock("p", _hoisted_2, toDisplayString(unref(t)("Refresh and check the timesheet before retrying. The server may have saved the changes.")), 1)) : createCommentVNode("", true),
					__props.confirmation ? (openBlock(), createElementBlock("aside", _hoisted_3, [
						createBaseVNode("p", null, toDisplayString(unref(t)("Discard unsaved changes?")), 1),
						createVNode(_sfc_main$4, {
							label: "Keep editing",
							onClick: _cache[1] || (_cache[1] = ($event) => emit("keep-editing"))
						}),
						createVNode(_sfc_main$4, {
							label: "Discard changes",
							destructive: "",
							onClick: _cache[2] || (_cache[2] = ($event) => emit("discard-close"))
						})
					])) : createCommentVNode("", true),
					createBaseVNode("div", _hoisted_4, [
						__props.mode === "task" ? (openBlock(), createBlock(_sfc_main$4, {
							key: 0,
							label: "Log time",
							icon: "add",
							disabled: __props.busy || __props.uncertain || __props.editing || !__props.data || !__props.canCreate,
							onClick: _cache[3] || (_cache[3] = ($event) => emit("create"))
						}, null, 8, ["disabled"])) : createCommentVNode("", true),
						__props.mode !== "week" ? (openBlock(), createBlock(_sfc_main$4, {
							key: 1,
							label: "Weekly timesheet",
							icon: "table",
							disabled: __props.busy || __props.uncertain || __props.editing,
							onClick: _cache[4] || (_cache[4] = ($event) => emit("scope", "mode", "week"))
						}, null, 8, ["disabled"])) : createCommentVNode("", true),
						__props.mode !== "task" && __props.canCreate ? (openBlock(), createBlock(_sfc_main$4, {
							key: 2,
							label: "Task timesheet",
							icon: "MDI_CLOCK_OUTLINE",
							disabled: __props.busy || __props.uncertain || __props.editing,
							onClick: _cache[5] || (_cache[5] = ($event) => emit("scope", "mode", "task"))
						}, null, 8, ["disabled"])) : createCommentVNode("", true),
						__props.mode === "task" ? (openBlock(), createBlock(_sfc_main$4, {
							key: 3,
							label: "Open work reports",
							icon: "bar-chart",
							disabled: __props.busy || __props.uncertain || __props.editing,
							onClick: _cache[6] || (_cache[6] = ($event) => emit("scope", "mode", "report"))
						}, null, 8, ["disabled"])) : createCommentVNode("", true),
						__props.mode === "task" ? (openBlock(), createBlock(_sfc_main$4, {
							key: 4,
							label: "Refresh",
							icon: "refresh",
							disabled: __props.busy,
							onClick: _cache[7] || (_cache[7] = ($event) => emit("refresh"))
						}, null, 8, ["disabled"])) : createCommentVNode("", true)
					]),
					__props.mode === "week" ? (openBlock(), createBlock(_sfc_main$5, {
						key: 3,
						class: "time-entry-frame",
						style: normalizeStyle({ height: toolbar$1.value.height + "px" }),
						scene: toolbar$1.value,
						onEvent: scopeAction
					}, null, 8, ["style", "scene"])) : createCommentVNode("", true),
					__props.mode === "week" && __props.data ? (openBlock(), createBlock(_sfc_main$5, {
						key: 4,
						class: "time-entry-frame",
						style: normalizeStyle({ height: summary(__props.data.summary, width.value, language.value).height + "px" }),
						scene: summary(__props.data.summary, width.value, language.value)
					}, null, 8, ["style", "scene"])) : createCommentVNode("", true),
					__props.mode === "report" ? (openBlock(), createElementBlock("div", _hoisted_5, [createVNode(_sfc_main$6, {
						"model-value": __props.week,
						label: "Week",
						"include-time": false,
						"allow-clear": false,
						disabled: __props.busy || __props.uncertain || __props.editing,
						onChange: _cache[8] || (_cache[8] = ($event) => emit("scope", "week", $event))
					}, null, 8, ["model-value", "disabled"]), createVNode(_sfc_main$7, {
						"model-value": __props.login,
						options: [{
							value: "",
							label: unref(t)("All users")
						}, ...__props.users],
						label: "Team member",
						disabled: __props.busy || __props.uncertain || __props.editing,
						"translate-labels": false,
						"onUpdate:modelValue": _cache[9] || (_cache[9] = ($event) => emit("scope", "login", $event))
					}, null, 8, [
						"model-value",
						"options",
						"disabled"
					])])) : createCommentVNode("", true),
					__props.mode === "report" ? (openBlock(), createBlock(_sfc_main$3, {
						key: 6,
						data: __props.data,
						report: __props.report,
						busy: __props.busy || __props.uncertain,
						onReport: _cache[10] || (_cache[10] = ($event) => emit("scope", "report", $event)),
						onRefresh: _cache[11] || (_cache[11] = ($event) => emit("refresh"))
					}, null, 8, [
						"data",
						"report",
						"busy"
					])) : createCommentVNode("", true),
					__props.editing ? (openBlock(), createBlock(_sfc_main$2, {
						key: 7,
						draft: __props.draft,
						users: __props.users,
						busy: __props.busy || __props.uncertain,
						error: __props.error,
						onChange: _cache[12] || (_cache[12] = (field, value) => emit("change", field, value)),
						onCancel: _cache[13] || (_cache[13] = ($event) => emit("cancel-edit")),
						onSave: _cache[14] || (_cache[14] = ($event) => emit("save", $event))
					}, null, 8, [
						"draft",
						"users",
						"busy",
						"error"
					])) : createCommentVNode("", true),
					__props.busy ? (openBlock(), createElementBlock("p", _hoisted_6, toDisplayString(unref(t)("Loading data…")), 1)) : __props.mode !== "report" && __props.data && !__props.data.entries.length ? (openBlock(), createElementBlock("p", _hoisted_7, toDisplayString(unref(t)(__props.mode === "week" ? "No work hours for this week" : "No time entries yet")), 1)) : createCommentVNode("", true),
					__props.mode !== "report" ? (openBlock(), createElementBlock("div", _hoisted_8, [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.data?.entries || [], (entry) => {
						return openBlock(), createElementBlock("article", {
							key: entry.search_key,
							class: "timesheet-entry"
						}, [createVNode(_sfc_main$5, {
							class: "time-entry-frame",
							scene: entryScene(entry),
							style: normalizeStyle({ height: entryScene(entry).height + "px" }),
							onEvent: (action) => entryAction(entry, action)
						}, null, 8, [
							"scene",
							"style",
							"onEvent"
						]), __props.deleting === entry.search_key ? (openBlock(), createElementBlock("div", _hoisted_9, [
							createBaseVNode("p", null, toDisplayString(unref(t)("Delete this time entry?")), 1),
							createVNode(_sfc_main$4, {
								label: "Delete time entry",
								icon: "delete",
								destructive: "",
								disabled: __props.busy || __props.uncertain,
								onClick: ($event) => emit("action", entry, "delete")
							}, null, 8, ["disabled", "onClick"]),
							createVNode(_sfc_main$4, {
								label: "Cancel",
								disabled: __props.busy,
								onClick: _cache[15] || (_cache[15] = ($event) => emit("delete", ""))
							}, null, 8, ["disabled"])
						])) : createCommentVNode("", true)]);
					}), 128))])) : createCommentVNode("", true)
				]),
				_: 1
			}, 40, [
				"class",
				"role",
				"aria-label",
				"aria-busy"
			])), [[vShow, !__props.dockTarget || opened.value], [_directive_window, __props.dockTarget ? false : {
				type: "window",
				kind: "work_hours",
				page: __props.pageContext
			}]])], 8, ["to"]);
		};
	}
};
//#endregion
//#region src/features/objects/Timesheet.vue
var Timesheet_exports = /* @__PURE__ */ __exportAll({ default: () => Timesheet_default });
function today() {
	const date = /* @__PURE__ */ new Date();
	return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
var _sfc_main = {
	components: { TimeEntryPanel: _sfc_main$1 },
	props: {
		ticket: String,
		project: String,
		currentUser: String,
		dockTarget: String,
		dockMode: String,
		dockReport: String
	},
	inject: { openWorkHours: { default: null } },
	emits: [
		"saved",
		"opened",
		"closed",
		"open-dock"
	],
	data() {
		return {
			context: null,
			task: null,
			mode: this.dockMode || "task",
			week: today(),
			login: "",
			report: this.dockReport || "my_hours",
			result: null,
			users: [],
			draft: null,
			revision: "",
			selected: [],
			deleting: "",
			confirmation: false,
			busy: false,
			uncertain: false,
			error: "",
			request: 0,
			alive: true
		};
	},
	computed: { validContext() {
		return this.alive && this.context?.ticket === this.ticket && this.context?.project === this.project;
	} },
	watch: {
		ticket() {
			this.close(true);
		},
		project() {
			this.close(true);
		}
	},
	mounted() {
		window.addEventListener("beforeunload", this.beforeUnload);
	},
	beforeUnmount() {
		this.alive = false;
		this.request++;
		window.removeEventListener("beforeunload", this.beforeUnload);
	},
	methods: {
		windowContext() {
			if (this.busy || this.draft || this.uncertain) throw Error("Apply or discard unsaved changes first");
			return {
				project: this.project,
				route: {
					mode: this.mode,
					args: [
						this.task ? { scope: {
							task_key: this.task.scope?.task_key,
							search_key: this.task.scope?.search_key,
							process: this.task.scope?.process
						} } : null,
						false,
						this.mode === "week",
						this.week
					]
				}
			};
		},
		beforeUnload(event) {
			if (this.draft || this.busy || this.uncertain) {
				event.preventDefault();
				event.returnValue = "";
			}
		},
		async open(task = null, log = false, weekly = false, day = "") {
			if (this.busy || this.draft || this.uncertain) {
				this.error = "Save or discard time-entry changes before switching tasks.";
				return;
			}
			if (this.$refs.panel.isOpen() && this.task?.scope.task_key === task?.scope.task_key && (!day || day === this.week)) return;
			this.context = {
				ticket: this.ticket,
				project: this.project
			};
			this.task = task;
			if (day) this.week = String(day).slice(0, 10);
			this.users = task?.users || [];
			this.mode = this.dockMode || (weekly ? "week" : "task");
			this.login = this.currentUser || "";
			this.result = null;
			this.draft = null;
			this.confirmation = false;
			this.selected = [];
			this.deleting = "";
			this.uncertain = false;
			this.$refs.panel.open();
			this.$emit("opened");
			await this.command();
			if (log && this.result && this.validContext) this.edit();
		},
		openWeekly() {
			return this.open(null, false, true);
		},
		edit(entry = null) {
			if (this.busy || this.uncertain || !this.result) return;
			this.draft = entry ? { ...entry } : {
				day: today(),
				hours: 1,
				category: "regular",
				login: this.login || this.currentUser,
				description: ""
			};
			this.revision = this.result.revision;
			this.deleting = "";
			this.error = "";
		},
		close(force = false) {
			if (force !== true && (this.busy || this.draft || this.uncertain)) {
				if (!this.busy) this.confirmation = true;
				return;
			}
			this.request++;
			this.$refs.panel?.close();
			this.draft = null;
			this.confirmation = false;
			this.$emit("closed");
			if (force === true) this.busy = false;
		},
		scope(name, value) {
			if (this.busy || this.draft || this.uncertain) return;
			if (name === "report" && value === "labor_cost" && this.dockReport !== "labor_cost") {
				if (this.dockTarget) {
					this.$emit("open-dock", "cost");
					return;
				}
				if (this.openWorkHours) {
					this.openWorkHours("cost", this.task, this.project);
					return;
				}
			}
			if (name === "mode" && ["week", "report"].includes(value) && value !== this.dockMode) {
				if (this.dockTarget) {
					this.$emit("open-dock", value);
					return;
				}
				if (this.openWorkHours) {
					this.openWorkHours(value, this.task, this.project);
					return;
				}
			}
			this[name] = value;
			this.selected = [];
			this.deleting = "";
			this.result = null;
			this.command();
		},
		moveWeek(offset) {
			const date = /* @__PURE__ */ new Date(this.week + "T12:00:00Z");
			date.setUTCDate(date.getUTCDate() + offset * 7);
			this.scope("week", date.toISOString().slice(0, 10));
		},
		toggle(key, value) {
			this.selected = value ? [.../* @__PURE__ */ new Set([...this.selected, key])] : this.selected.filter((item) => item !== key);
		},
		async command(action = "read", entry = null, approve = false, keys = null) {
			if (!this.validContext || this.busy || this.uncertain && action !== "read") return;
			const context = this.context, id = ++this.request;
			this.busy = true;
			this.error = "";
			try {
				const data = this.draft ? Object.fromEntries([
					"day",
					"hours",
					"category",
					"login",
					"description"
				].map((name) => [name, name === "hours" ? String(this.draft[name]).replace(",", ".") : this.draft[name]])) : null;
				const response = await rpc("execute_cmd", [
					context,
					"tactic.ui.table.work_hours.WorkHoursCmd",
					{
						...this.task?.scope,
						mode: this.mode,
						week: this.week,
						login: this.login,
						report: this.report,
						action,
						entry_key: entry?.search_key || "",
						...keys ? { entry_keys: keys } : {},
						expected_revision: ["create", "update"].includes(action) ? this.revision : this.result?.revision,
						...data ? { data: {
							...data,
							approve
						} } : {}
					}
				]);
				if (id !== this.request || !this.validContext || this.context !== context) return;
				this.result = response.info;
				this.uncertain = false;
				this.deleting = "";
				if (this.result.users) this.users = this.result.users;
				if (this.mode !== "task") this.week = this.result.week_start || this.week;
				this.selected = [];
				if (action !== "read") {
					this.draft = null;
					this.$emit("saved");
				}
			} catch (error) {
				if (id === this.request && this.validContext) {
					this.error = error.message;
					this.uncertain = action !== "read" && (!error.status || error.status >= 500);
				}
			} finally {
				if (id === this.request) this.busy = false;
			}
		}
	}
};
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_TimeEntryPanel = resolveComponent("TimeEntryPanel");
	return openBlock(), createBlock(_component_TimeEntryPanel, {
		"page-context": $options.windowContext,
		ref: "panel",
		"dock-target": $props.dockTarget,
		"dock-report": $props.dockReport,
		data: $data.result,
		draft: $data.draft,
		editing: !!$data.draft,
		busy: $data.busy,
		error: $data.error,
		uncertain: $data.uncertain,
		deleting: $data.deleting,
		users: $data.users,
		mode: $data.mode,
		week: $data.week,
		login: $data.login,
		selected: $data.selected,
		report: $data.report,
		"can-create": !!$data.task?.scope.task_key,
		confirmation: $data.confirmation,
		onCreate: _cache[0] || (_cache[0] = ($event) => $options.edit()),
		onEdit: $options.edit,
		onChange: _cache[1] || (_cache[1] = (name, value) => $data.draft[name] = value),
		onCancelEdit: _cache[2] || (_cache[2] = ($event) => $data.draft = null),
		onDelete: _cache[3] || (_cache[3] = ($event) => $data.deleting = $event),
		onClose: _cache[4] || (_cache[4] = ($event) => $options.close()),
		onRefresh: _cache[5] || (_cache[5] = ($event) => $options.command()),
		onSave: _cache[6] || (_cache[6] = (approve) => $options.command($data.draft.search_key ? "update" : "create", $data.draft, approve)),
		onAction: _cache[7] || (_cache[7] = (entry, action) => $options.command(action, entry)),
		onScope: $options.scope,
		onMoveWeek: $options.moveWeek,
		onSelect: $options.toggle,
		onClearSelection: _cache[8] || (_cache[8] = ($event) => $data.selected = []),
		onBulk: _cache[9] || (_cache[9] = (action) => $options.command(action, null, false, $data.selected)),
		onKeepEditing: _cache[10] || (_cache[10] = ($event) => $data.confirmation = false),
		onDiscardClose: _cache[11] || (_cache[11] = ($event) => $options.close(true))
	}, null, 8, [
		"page-context",
		"dock-target",
		"dock-report",
		"data",
		"draft",
		"editing",
		"busy",
		"error",
		"uncertain",
		"deleting",
		"users",
		"mode",
		"week",
		"login",
		"selected",
		"report",
		"can-create",
		"confirmation",
		"onEdit",
		"onScope",
		"onMoveWeek",
		"onSelect"
	]);
}
var Timesheet_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { Timesheet_exports as n, Timesheet_default as t };

//# sourceMappingURL=Timesheet.js.map