import { r as __exportAll } from "./ObjectFieldFrame.js";
import { A as onMounted, E as nextTick, F as resolveComponent, I as resolveDirective, K as withDirectives, M as openBlock, N as renderList, O as onBeforeUnmount, X as ref, _ as createElementBlock, b as createVNode, et as unref, f as Teleport, g as createCommentVNode, h as createBlock, l as withModifiers, m as createBaseVNode, nt as normalizeStyle, p as computed, rt as toDisplayString, u as Fragment } from "./vue.js";
import { R as _plugin_vue_export_helper_default, T as metrics, o as t, s as appearance, t as _sfc_main$4 } from "./AppButton.js";
import { k as rpc } from "./index.js";
import { A as monthLabel, H as rect, L as button, R as label, V as node, j as parse, n as observeFrameSizes, r as _sfc_main$5, v as translate } from "./resize.js";
//#region ../src/tactic_stream/shared_ui/features/tasks/milestones.ui.mjs
function layout(width, height, controlHeight = 36) {
	const margin = 12, gap = 10, inner = Math.max(0, width - 24), searchY = 98, listY = searchY + controlHeight + gap;
	return {
		margin,
		gap,
		inner,
		searchY,
		listY,
		listHeight: Math.max(0, height - listY - margin)
	};
}
function header(model, width, language) {
	const tr = (text) => translate(text, language), compact = width < 600, createWidth = compact ? 36 : 146;
	const createX = width - 12 - createWidth, refreshX = createX - 39, countWidth = width >= 700 ? 86 : 0;
	const textRight = refreshX - (countWidth ? countWidth + 11 : 8), radius = model.radius || 8;
	const nodes = [
		node("Box", "milestoneHeaderSurface", rect(0, 0, width, 76), {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			borderWidth: 1,
			radius
		}),
		node("Box", "milestoneHeaderIconSurface", rect(12, 15, 46, 46), {
			background: "secondaryContainer",
			radius
		}),
		node("Icon", "milestoneHeaderIcon", rect(24, 27, 22, 22), {
			icon: "milestone",
			color: "action"
		}),
		label("milestoneHeaderTitle", rect(69, 21, textRight - 77, 20), tr("Project milestones"), {
			fontRole: "section",
			weight: 600
		}),
		label("milestoneHeaderProject", rect(69, 43, textRight - 77, 16), translate("Schedule reusable task deadlines for {project}", language, { project: model.project || tr("current project") }), {
			fontRole: "secondary",
			color: "secondaryText"
		}),
		button("milestoneRefresh", rect(refreshX, 24, 28, 28), "", "refresh", { type: "refresh" }, !model.busy, {
			label: tr("Refresh milestones"),
			iconOnly: true,
			iconAction: true,
			iconSize: 16
		}),
		button("milestoneCreate", rect(createX, 22, createWidth, 32), compact ? "" : tr("New milestone"), "add", { type: "create" }, !model.busy && model.canCreate !== false, {
			label: tr("New milestone"),
			iconOnly: compact,
			highlighted: true,
			filledAction: true,
			fontRole: "secondary"
		})
	];
	if (countWidth) nodes.push(label("milestoneHeaderCount", rect(refreshX - countWidth - 11, 30, countWidth, 16), String(model.count || 0) + " " + tr("milestones"), {
		fontRole: "secondary",
		color: "secondaryText",
		align: "right"
	}));
	return {
		nodes,
		height: 76
	};
}
function search(model, width, language) {
	const height = model.controlHeight || 36;
	return {
		height,
		nodes: [node("Field", "milestoneSearch", rect(0, 0, width, height), {
			text: model.query || "",
			inputType: "search",
			paddingLeft: 39,
			label: translate("Search milestones", language),
			placeholder: translate("Search milestones", language),
			enabled: !model.busy,
			action: { type: "query" }
		}), node("Icon", "milestoneSearchIcon", rect(12, (height - 16) / 2, 16, 16), {
			icon: "search",
			color: "secondaryText",
			pointerTransparent: true
		})]
	};
}
function empty(model, width, language) {
	const tr = (text) => translate(text, language), nodes = [];
	nodes.push(node("Icon", "milestoneEmptyIcon", rect(width / 2 - 18, 0, 36, 36), {
		icon: "milestone",
		color: "disabledText"
	}));
	nodes.push(label("milestoneEmptyTitle", rect(0, 44, width, 18), tr(model.query ? "No matching milestones" : "No milestones yet"), {
		fontRole: "body",
		weight: 600,
		align: "center"
	}));
	nodes.push(label("milestoneEmptyHint", rect(0, 70, width, 32), tr(model.query ? "Try another search" : "Create a reusable deadline for project tasks"), {
		fontRole: "secondary",
		color: "secondaryText",
		align: "center",
		wrap: true
	}));
	if (!model.query) nodes.push(button("milestoneEmptyCreate", rect(width / 2 - 80, 110, 160, 32), tr("New milestone"), "add", { type: "create" }, !model.busy && model.canCreate !== false, {
		filledAction: true,
		highlighted: true
	}));
	return {
		nodes,
		height: model.query ? 102 : 150
	};
}
function row(model, width, language) {
	const tr = (text) => translate(text, language), nodes = [], compact = width < 640;
	const radius = model.radius || 8, control = model.controlHeight || 36, blocked = model.busy || model.saving || !!model.uncertain;
	const discard = !!(model.dirty || model.uncertain), actionCount = discard ? 3 : 2, actionsWidth = actionCount * 28 + (actionCount - 1) * 4;
	const nameX = 68, actionsX = width - 9 - actionsWidth;
	const available = Math.max(0, actionsX - nameX - 18), nameWidth = compact ? Math.max(0, width - nameX - 9) : available * .41;
	const dueX = compact ? nameX : nameX + nameWidth + 9, dueWidth = compact ? nameWidth : available - nameWidth;
	const dueTitleY = compact ? 82 : 14, planY = compact ? 148 : 76, planHeight = compact ? 86 : 43;
	const errorY = planY + planHeight + 7, height = errorY + (model.error ? model.canReview ? 72 : 36 : 0);
	nodes.push(node("Box", "milestoneRowSurface", rect(0, 0, width, height), {
		background: model.dirty ? "surfaceContainerHigh" : "surfaceContainerLow",
		radius,
		border: model.error ? "error" : model.selected || model.dirty ? "action" : void 0,
		borderWidth: model.dirty || model.selected || model.error ? 1 : 0
	}));
	nodes.push(node("Box", "milestoneDateSurface", rect(9, 17, 50, 50), {
		background: model.isNew ? "secondaryContainer" : "surfaceContainerHighest",
		radius
	}));
	const parsed = parse(model.dueDate, false);
	nodes.push(label("milestoneDateDay", rect(9, 24, 50, 22), parsed ? String(parsed.getDate()) : "—", {
		fontRole: "title",
		weight: 600,
		align: "center"
	}));
	nodes.push(label("milestoneDateMonth", rect(9, 48, 50, 15), parsed ? monthLabel(parsed, language).split(" ")[0].slice(0, 3).toUpperCase() : "", {
		fontRole: "caption",
		weight: 700,
		align: "center",
		color: "action"
	}));
	nodes.push(label("milestoneRowState", rect(nameX, 14, compact ? Math.max(0, actionsX - nameX - 8) : nameWidth, 12), tr(model.isNew ? "New milestone" : "Milestone").toUpperCase() + (model.dirty ? " · " + tr(model.saving ? "Saving…" : "Unsaved changes") : ""), {
		fontRole: "caption",
		weight: 700,
		color: model.dirty ? "yellow" : "secondaryText"
	}));
	const actions = discard ? [[
		"milestoneDiscard",
		"Discard changes",
		"undo",
		"discard",
		true
	]] : [];
	actions.push([
		"milestoneSave",
		"Save milestone",
		"save",
		"save",
		model.dirty && !model.uncertain
	]);
	actions.push([
		"milestoneDelete",
		"Delete milestone",
		"delete",
		"delete",
		model.canDelete !== false && !model.uncertain
	]);
	actions.forEach(([id, title, icon, type, enabled], index) => nodes.push(button(id, rect(actionsX + index * 32, compact ? 2 : 31, 28, 28), "", icon, {
		type,
		code: model.code
	}, !model.busy && !model.saving && !!enabled, {
		label: tr(title),
		iconOnly: true,
		iconAction: true,
		iconSize: 16,
		iconColor: type === "delete" ? "error" : type === "save" && model.dirty ? "action" : "secondaryText"
	})));
	nodes.push(node("Field", "milestoneName", rect(nameX, 28, nameWidth, control), {
		text: model.description || "",
		label: tr("Milestone name"),
		maxLength: 4096,
		enabled: !blocked && model.nameEditable !== false,
		action: {
			type: "change",
			code: model.code,
			field: "description"
		}
	}));
	nodes.push(label("milestoneDueTitle", rect(dueX, dueTitleY, dueWidth, 12), tr("Due date").toUpperCase(), {
		fontRole: "caption",
		weight: 700,
		color: "secondaryText"
	}));
	nodes.push(node("DateChoice", "milestoneDueDate", rect(dueX, dueTitleY + 14, dueWidth, control), {
		text: model.dueDate || "",
		label: tr("Due date"),
		includeTime: false,
		allowClear: false,
		enabled: !blocked && model.dateEditable !== false,
		action: {
			type: "change",
			code: model.code,
			field: "dueDate"
		}
	}));
	nodes.push(node("Box", "milestonePlanSurface", rect(69, planY, width - 79, planHeight), {
		background: "surfaceContainerHighest",
		radius: 6
	}));
	nodes.push(node("Box", "milestonePlanIconSurface", rect(78, planY + 7.5, 28, 28), {
		background: "secondaryContainer",
		radius: 6
	}));
	nodes.push(node("Icon", "milestonePlanIcon", rect(84.5, planY + 14, 15, 15), {
		icon: "milestone",
		color: "action"
	}));
	const overdueWidth = model.overdueCount ? 68 : 0, progressWidth = compact ? Math.max(0, width - 100 - overdueWidth) : Math.min(226, width * .28);
	const progressX = compact ? 78 : width - 19 - overdueWidth - progressWidth - (overdueWidth ? 9 : 0);
	const titleWidth = compact ? width - 127 : Math.max(0, progressX - 124);
	nodes.push(label("milestonePlanTitle", rect(115, planY + 6, titleWidth, 16), tr("Linked task plan").toUpperCase() + " · " + (model.taskCount ? String(model.completedCount == null ? "—" : model.completedCount) + " / " + model.taskCount + " " + tr("tasks") : tr("No tasks")), {
		fontRole: "secondary",
		weight: 600
	}));
	nodes.push(label("milestonePlanSummary", rect(compact ? 78 : 115, planY + (compact ? 34 : 25), compact ? width - 98 : titleWidth, 15), model.taskCount ? (model.planStartDate || tr("Start not set")) + " → " + (model.dueDate || "—") + (model.processSummary ? " · " + model.processSummary : "") + (model.plannedHours > 0 ? " · " + model.plannedHours + " h" : "") : tr("Assign tasks to build the milestone plan"), {
		fontRole: "caption",
		color: "secondaryText"
	}));
	const completion = Math.max(0, Math.min(100, Number(model.completion) || 0)), progressY = planY + (compact ? 58 : 11);
	nodes.push(label("milestoneCompletionTitle", rect(progressX, progressY, Math.max(0, progressWidth - 40), 15), tr("Completion").toUpperCase(), {
		fontRole: "caption",
		weight: 700,
		color: "secondaryText"
	}));
	nodes.push(label("milestoneCompletion", rect(progressX + Math.max(0, progressWidth - 40), progressY, 40, 15), model.taskCount ? completion + "%" : "—", {
		fontRole: "caption",
		weight: 600,
		align: "right"
	}));
	nodes.push(node("Box", "milestoneCompletionTrack", rect(progressX, progressY + 18, progressWidth, 5), {
		background: "surfaceContainerLow",
		radius: 2.5
	}));
	nodes.push(node("Box", "milestoneCompletionValue", rect(progressX, progressY + 18, progressWidth * completion / 100, 5), {
		background: "action",
		radius: 2.5
	}));
	if (model.overdueCount) nodes.push(label("milestoneOverdue", rect(width - 19 - overdueWidth, progressY + 4, overdueWidth, 15), String(model.overdueCount) + " " + tr("overdue"), {
		fontRole: "caption",
		weight: 600,
		color: "error",
		align: "right"
	}));
	if (model.error) {
		nodes.push(label("milestoneRowError", rect(12, errorY, width - 24, 30), tr(model.error), {
			fontRole: "caption",
			color: "error",
			wrap: true
		}));
		if (model.canReview) nodes.push(button("milestoneReview", rect(12, errorY + 36, width - 24, 28), tr("Review current milestone revision"), "refresh", {
			type: "review",
			code: model.code
		}, !model.busy));
	}
	return {
		nodes,
		height
	};
}
//#endregion
//#region src/features/tasks/MilestoneRow.vue
var _hoisted_1$2 = ["aria-label", "data-milestone"];
var _sfc_main$3 = {
	__name: "MilestoneRow",
	props: { model: Object },
	emits: ["event"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const root = ref(null), width = ref(800);
		let observer;
		const scene = computed(() => row({
			...props.model,
			radius: metrics(appearance.theme).itemRadius,
			controlHeight: metrics(appearance.theme).controlHeight
		}, width.value, appearance.language));
		onMounted(() => {
			observer = observeFrameSizes((entries) => width.value = entries[0].contentRect.width);
			observer.observe(root.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("article", {
				ref_key: "root",
				ref: root,
				class: "milestone-frame-row",
				role: "group",
				"aria-label": __props.model.description || unref(t)("New milestone"),
				"data-milestone": __props.model.code,
				style: normalizeStyle({ height: scene.value.height + "px" })
			}, [createVNode(_sfc_main$5, {
				scene: scene.value,
				onEvent: _cache[0] || (_cache[0] = (event) => emit("event", event))
			}, null, 8, ["scene"])], 12, _hoisted_1$2);
		};
	}
};
//#endregion
//#region src/features/tasks/MilestoneContent.vue
var _hoisted_1$1 = ["aria-busy"];
var _sfc_main$2 = {
	__name: "MilestoneContent",
	props: {
		project: String,
		result: Object,
		rows: {
			type: Array,
			default: () => []
		},
		query: String,
		busy: Boolean,
		uncertain: String,
		focused: String
	},
	emits: ["event"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const root = ref(null), width = ref(800), height = ref(500);
		let observer;
		const metrics$1 = computed(() => metrics(appearance.theme));
		const geometry = computed(() => layout(width.value, height.value, metrics$1.value.controlHeight));
		const headerModel = computed(() => ({
			project: props.project,
			count: props.result?.records?.length ?? props.rows.length,
			radius: metrics$1.value.itemRadius,
			busy: props.busy,
			canCreate: !!(props.result?.canCreate && !props.uncertain)
		}));
		const bounds = (x, y, w, h) => ({
			left: x + "px",
			top: y + "px",
			width: w + "px",
			height: h + "px"
		});
		const editable = (name) => props.result?.fields?.some((field) => field.name === name && field.editable);
		onMounted(() => {
			observer = observeFrameSizes((entries) => {
				width.value = entries[0].contentRect.width;
				height.value = entries[0].contentRect.height;
			});
			observer.observe(root.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "root",
				ref: root,
				class: "milestone-content-frame"
			}, [
				createVNode(_sfc_main$5, {
					class: "milestone-common-header",
					style: normalizeStyle(bounds(geometry.value.margin, geometry.value.margin, geometry.value.inner, 76)),
					scene: header(headerModel.value, geometry.value.inner, unref(appearance).language),
					onEvent: _cache[0] || (_cache[0] = (action) => emit("event", action))
				}, null, 8, ["style", "scene"]),
				createVNode(_sfc_main$5, {
					class: "milestone-frame-search",
					style: normalizeStyle(bounds(geometry.value.margin, geometry.value.searchY, geometry.value.inner, metrics$1.value.controlHeight)),
					scene: search({
						query: __props.query,
						busy: __props.busy,
						controlHeight: metrics$1.value.controlHeight
					}, geometry.value.inner, unref(appearance).language),
					onEvent: _cache[1] || (_cache[1] = (action) => emit("event", action))
				}, null, 8, ["style", "scene"]),
				createBaseVNode("div", {
					class: "milestone-results milestone-frame-results",
					style: normalizeStyle(bounds(geometry.value.margin, geometry.value.listY, geometry.value.inner, geometry.value.listHeight)),
					"aria-busy": __props.busy
				}, [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.rows, (row) => {
					return openBlock(), createBlock(_sfc_main$3, {
						key: row.code,
						model: {
							...row,
							busy: __props.busy,
							uncertain: __props.uncertain,
							selected: __props.focused === row.code,
							canDelete: __props.result?.canDelete,
							canReview: !!row.revision && !__props.uncertain,
							nameEditable: editable("description"),
							dateEditable: editable("due_date")
						},
						onEvent: _cache[2] || (_cache[2] = (action) => emit("event", action))
					}, null, 8, ["model"]);
				}), 128))], 12, _hoisted_1$1),
				!__props.rows.length ? (openBlock(), createElementBlock("div", {
					key: 0,
					class: "milestone-frame-empty",
					style: normalizeStyle(bounds(geometry.value.margin, geometry.value.listY, geometry.value.inner, geometry.value.listHeight))
				}, [createVNode(_sfc_main$5, {
					style: normalizeStyle({
						width: Math.min(360, geometry.value.inner) + "px",
						height: empty({ query: __props.query }, Math.min(360, geometry.value.inner), unref(appearance).language).height + "px"
					}),
					scene: empty({
						query: __props.query,
						busy: __props.busy,
						canCreate: !!__props.result?.canCreate
					}, Math.min(360, geometry.value.inner), unref(appearance).language),
					onEvent: _cache[3] || (_cache[3] = (action) => emit("event", action))
				}, null, 8, ["style", "scene"])], 4)) : createCommentVNode("", true)
			], 512);
		};
	}
};
//#endregion
//#region src/features/tasks/MilestonePanel.vue
var _hoisted_1 = ["aria-label"];
var _hoisted_2 = { class: "task-manager-heading" };
var _hoisted_3 = { class: "muted" };
var _hoisted_4 = { class: "configuration-actions" };
var _hoisted_5 = {
	key: 0,
	class: "notice"
};
var _hoisted_6 = {
	key: 1,
	class: "error",
	role: "alert"
};
var _hoisted_7 = {
	key: 2,
	class: "notice",
	role: "alert"
};
var _hoisted_8 = {
	key: 3,
	class: "milestone-server-data"
};
var _hoisted_9 = {
	key: 4,
	class: "notice milestone-delete",
	role: "alert"
};
var _sfc_main$1 = {
	__name: "MilestonePanel",
	props: {
		project: String,
		pageContext: Function,
		result: Object,
		rows: Array,
		query: String,
		busy: Boolean,
		error: String,
		uncertain: String,
		confirmation: String,
		deleting: String,
		focused: String
	},
	emits: [
		"query",
		"create",
		"change",
		"save",
		"discard",
		"delete",
		"review",
		"refresh",
		"inspect-server",
		"close",
		"keep-editing",
		"confirm",
		"cancel-delete",
		"confirm-delete"
	],
	setup(__props, { expose: __expose, emit: __emit }) {
		const emit = __emit;
		const dialog = ref(null);
		function action(event) {
			if (event.type === "change") emit("change", event.code, event.field, event.value);
			else if (event.type === "query") emit("query", event.value);
			else emit(event.type, event.code);
		}
		function focusRow(code, input = false) {
			const row = [...dialog.value?.querySelectorAll("[data-milestone]") || []].find((row) => row.dataset.milestone === code);
			row?.scrollIntoView({ block: "nearest" });
			if (input) row?.querySelector("input")?.focus();
		}
		__expose({
			open: () => {
				if (!dialog.value.open) dialog.value.show();
			},
			close: () => dialog.value?.close(),
			focusRow
		});
		return (_ctx, _cache) => {
			const _directive_window = resolveDirective("window");
			return openBlock(), createBlock(Teleport, { to: "body" }, [withDirectives((openBlock(), createElementBlock("dialog", {
				ref_key: "dialog",
				ref: dialog,
				class: "configuration-dialog milestone-manager",
				"aria-label": unref(t)("Project milestones"),
				onCancel: _cache[7] || (_cache[7] = withModifiers(($event) => emit("close"), ["prevent"]))
			}, [
				createBaseVNode("header", _hoisted_2, [createBaseVNode("div", null, [createBaseVNode("h2", null, toDisplayString(unref(t)("Project milestones")), 1), createBaseVNode("small", _hoisted_3, toDisplayString(__props.project) + " · " + toDisplayString(unref(t)("Reusable deadlines and the plan of linked tasks.")), 1)]), createBaseVNode("div", _hoisted_4, [createVNode(_sfc_main$4, {
					label: "Close",
					icon: "close",
					"icon-only": "",
					disabled: __props.busy,
					onClick: _cache[0] || (_cache[0] = ($event) => emit("close"))
				}, null, 8, ["disabled"])])]),
				__props.confirmation ? (openBlock(), createElementBlock("aside", _hoisted_5, [
					createBaseVNode("p", null, toDisplayString(unref(t)(__props.confirmation === "close" ? "Discard unsaved milestone changes?" : "Refreshing will discard every unsaved milestone change.")), 1),
					createVNode(_sfc_main$4, {
						label: "Keep editing",
						onClick: _cache[1] || (_cache[1] = ($event) => emit("keep-editing"))
					}),
					createVNode(_sfc_main$4, {
						label: "Discard changes",
						destructive: "",
						onClick: _cache[2] || (_cache[2] = ($event) => emit("confirm"))
					})
				])) : createCommentVNode("", true),
				__props.error ? (openBlock(), createElementBlock("p", _hoisted_6, toDisplayString(unref(t)(__props.error)), 1)) : createCommentVNode("", true),
				__props.uncertain ? (openBlock(), createElementBlock("aside", _hoisted_7, [
					createBaseVNode("p", null, toDisplayString(unref(t)("The server may have saved this milestone. Inspect the server data before discarding the draft; saving is blocked.")), 1),
					createVNode(_sfc_main$4, {
						label: "Inspect current server data",
						icon: "refresh",
						disabled: __props.busy,
						onClick: _cache[3] || (_cache[3] = ($event) => emit("inspect-server"))
					}, null, 8, ["disabled"]),
					createVNode(_sfc_main$4, {
						label: "Discard changes",
						disabled: __props.busy,
						onClick: _cache[4] || (_cache[4] = ($event) => emit("discard", __props.uncertain))
					}, null, 8, ["disabled"])
				])) : createCommentVNode("", true),
				__props.uncertain && __props.result ? (openBlock(), createElementBlock("div", _hoisted_8, [createBaseVNode("strong", null, toDisplayString(unref(t)("Current server data")), 1), (openBlock(true), createElementBlock(Fragment, null, renderList(__props.result.records, (row) => {
					return openBlock(), createElementBlock("p", { key: row.code }, toDisplayString(row.code) + " · " + toDisplayString(row.description) + " · " + toDisplayString(row.dueDate), 1);
				}), 128))])) : createCommentVNode("", true),
				createVNode(_sfc_main$2, {
					class: "milestone-manager-content",
					project: __props.project,
					result: __props.result,
					rows: __props.rows,
					query: __props.query,
					busy: __props.busy,
					uncertain: __props.uncertain,
					focused: __props.focused,
					onEvent: action
				}, null, 8, [
					"project",
					"result",
					"rows",
					"query",
					"busy",
					"uncertain",
					"focused"
				]),
				__props.deleting ? (openBlock(), createElementBlock("aside", _hoisted_9, [
					createBaseVNode("p", null, toDisplayString(unref(t)("Delete this milestone? It can only be deleted when no tasks use it.")), 1),
					createVNode(_sfc_main$4, {
						label: "Cancel",
						disabled: __props.busy,
						onClick: _cache[5] || (_cache[5] = ($event) => emit("cancel-delete"))
					}, null, 8, ["disabled"]),
					createVNode(_sfc_main$4, {
						label: "Delete milestone",
						icon: "delete",
						destructive: "",
						disabled: __props.busy || !!__props.uncertain,
						onClick: _cache[6] || (_cache[6] = ($event) => emit("confirm-delete"))
					}, null, 8, ["disabled"])
				])) : createCommentVNode("", true)
			], 40, _hoisted_1)), [[_directive_window, {
				kind: "milestone_manager",
				type: "window",
				page: __props.pageContext
			}]])]);
		};
	}
};
//#endregion
//#region src/features/tasks/MilestoneManager.vue
var MilestoneManager_exports = /* @__PURE__ */ __exportAll({ default: () => MilestoneManager_default });
function today() {
	const date = /* @__PURE__ */ new Date();
	return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
var _sfc_main = {
	components: { MilestonePanel: _sfc_main$1 },
	props: {
		ticket: String,
		project: String
	},
	emits: ["markers", "saved"],
	data() {
		return {
			context: null,
			result: null,
			drafts: {},
			query: "",
			busy: false,
			saving: "",
			uncertain: "",
			error: "",
			request: 0,
			alive: true,
			confirmation: "",
			deleting: "",
			focused: ""
		};
	},
	computed: {
		validContext() {
			return this.alive && this.context?.ticket === this.ticket && this.context?.project === this.project;
		},
		dirty() {
			return Object.keys(this.drafts).length > 0;
		},
		rows() {
			const rows = [...this.result?.records || []];
			for (const [code, draft] of Object.entries(this.drafts)) if (!rows.some((row) => row.code === code)) rows.unshift({
				code,
				...draft.original
			});
			return rows.map((row) => ({
				...row,
				...this.drafts[row.code]?.data,
				dirty: !!this.drafts[row.code],
				isNew: !!this.drafts[row.code]?.isNew,
				saving: this.saving === row.code,
				error: this.drafts[row.code]?.error || "",
				uncertain: this.uncertain === row.code
			}));
		},
		visibleRows() {
			const query = this.query.toLocaleLowerCase();
			return this.rows.filter((row) => `${row.description} ${row.dueDate}`.toLocaleLowerCase().includes(query));
		},
		markers() {
			return this.rows.filter((row) => !row.isNew && row.dueDate).map((row) => ({
				value: row.code,
				label: row.description || row.code,
				dueDate: row.dueDate,
				completion: row.completion,
				taskCount: row.taskCount
			}));
		}
	},
	watch: {
		ticket() {
			this.reset();
		},
		project() {
			this.reset();
		},
		markers: {
			deep: true,
			handler(value) {
				this.$emit("markers", value);
			}
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
			if (this.busy || this.saving || this.dirty || this.uncertain) throw Error("Apply or discard unsaved changes first");
			return {
				project: this.project,
				route: { args: [this.focused] }
			};
		},
		beforeUnload(event) {
			if (this.dirty || this.busy || this.uncertain) {
				event.preventDefault();
				event.returnValue = "";
			}
		},
		reset() {
			this.request++;
			this.$refs.panel?.close();
			this.context = null;
			this.result = null;
			this.drafts = {};
			this.busy = false;
			this.uncertain = "";
			this.confirmation = "";
			this.$emit("markers", []);
		},
		canLeave() {
			if (this.busy || (this.dirty || this.uncertain) && !window.confirm(t("Discard unsaved milestone changes?"))) return false;
			if (this.dirty || this.uncertain) this.reset();
			return true;
		},
		close(force = false) {
			if (this.busy) return;
			if (!force && (this.dirty || this.uncertain)) {
				this.confirmation = "close";
				return;
			}
			if (force) {
				this.drafts = {};
				this.uncertain = "";
			}
			this.confirmation = "";
			this.$refs.panel.close();
		},
		async ensureLoaded() {
			if (!this.validContext) {
				this.reset();
				this.context = {
					ticket: this.ticket,
					project: this.project
				};
			}
			if (!this.busy && !this.dirty && !this.uncertain) await this.command();
		},
		async open(code = "") {
			if (!this.validContext) {
				this.reset();
				this.context = {
					ticket: this.ticket,
					project: this.project
				};
			}
			this.query = "";
			this.focused = code;
			this.$refs.panel.open();
			if (!this.dirty && !this.uncertain) await this.command();
			await nextTick();
			this.$refs.panel.focusRow(code);
		},
		async create() {
			if (this.busy || this.uncertain || !this.result?.canCreate) return;
			const code = "new:" + Array.from(crypto.getRandomValues(/* @__PURE__ */ new Uint32Array(4)), (value) => value.toString(16)).join("-");
			const original = {
				description: "",
				dueDate: today(),
				completion: 0,
				taskCount: 0,
				completedCount: 0,
				overdueCount: 0,
				planStartDate: "",
				processSummary: "",
				plannedHours: 0
			};
			this.drafts[code] = {
				isNew: true,
				original,
				data: {
					description: "",
					dueDate: original.dueDate
				},
				revision: this.result.revision,
				error: ""
			};
			this.query = "";
			await nextTick();
			this.$refs.panel.focusRow(code, true);
		},
		stage(code, name, value) {
			if (this.busy || this.uncertain || !["description", "dueDate"].includes(name)) return;
			const row = this.result.records.find((row) => row.code === code);
			let draft = this.drafts[code];
			if (!draft) draft = this.drafts[code] = {
				original: { ...row },
				revision: row.revision,
				data: {
					description: row.description,
					dueDate: row.dueDate
				},
				error: ""
			};
			draft.data[name] = value;
			draft.error = "";
			if (!draft.isNew && draft.data.description === draft.original.description && draft.data.dueDate === draft.original.dueDate) delete this.drafts[code];
		},
		discard(code) {
			if (this.busy) return;
			if (this.uncertain === code && !window.confirm(t("Inspect the current server data before discarding this uncertain change. Discard the draft?"))) return;
			delete this.drafts[code];
			if (this.uncertain === code) this.uncertain = "";
		},
		refresh() {
			if (this.busy) return;
			if (this.dirty || this.uncertain) this.confirmation = "refresh";
			else this.command();
		},
		confirm() {
			const action = this.confirmation;
			this.confirmation = "";
			this.drafts = {};
			this.uncertain = "";
			if (action === "close") this.close(true);
			else this.command();
		},
		remove(code) {
			if (this.busy || this.uncertain || !this.result?.canDelete) return;
			if (this.drafts[code]?.isNew) this.discard(code);
			else this.deleting = code;
		},
		async review(code) {
			if (this.busy || this.uncertain) return;
			if (!await this.command()) return;
			const draft = this.drafts[code];
			if (!draft || !this.validContext) return;
			const current = this.result.records.find((row) => row.code === code);
			if (!draft.isNew && !current) {
				draft.error = "Milestone no longer exists. Discard this draft.";
				return;
			}
			const comparison = draft.isNew ? t("The project milestone list changed.") : `${t("Original")}: ${draft.original.description} · ${draft.original.dueDate}\n${t("Current server data")}: ${current.description} · ${current.dueDate}`;
			if (!window.confirm(comparison + "\n" + t("Keep your edits on this revision?"))) return;
			draft.revision = current?.revision || "";
			draft.error = "";
			if (current) draft.original = { ...current };
		},
		async save(code) {
			const draft = this.drafts[code];
			if (!draft || this.busy || this.uncertain) return;
			if (!draft.data.description.trim()) {
				draft.error = "A milestone name is required";
				return;
			}
			if (!/^\d{4}-\d{2}-\d{2}$/.test(draft.data.dueDate)) {
				draft.error = "Choose a valid milestone due date";
				return;
			}
			await this.command(draft.isNew ? "create" : "update", code);
		},
		async command(action = "read", code = "") {
			if (!this.validContext || this.busy || this.uncertain && action !== "read") return false;
			const context = this.context, id = ++this.request, draft = this.drafts[code];
			this.busy = true;
			this.saving = action === "read" ? "" : code;
			this.error = "";
			try {
				const response = await rpc("execute_cmd", [
					context,
					"tactic.ui.table.milestones.MilestoneCmd",
					{
						action,
						code: draft?.isNew ? "" : code,
						expected_revision: draft?.revision || this.result?.records.find((row) => row.code === code)?.revision,
						...draft ? { data: {
							description: draft.data.description,
							due_date: draft.data.dueDate
						} } : {}
					}
				]);
				if (id !== this.request || !this.validContext || context !== this.context) return false;
				const result = response.info;
				if (action !== "read") {
					delete this.drafts[code];
					this.deleting = "";
					this.focused = result.selected;
					this.$emit("saved");
				}
				this.result = result;
				return true;
			} catch (error) {
				if (id === this.request && this.validContext) {
					if (draft) draft.error = error.message;
					else this.error = error.message;
					if (action !== "read" && (!error.status || error.status >= 500)) this.uncertain = code;
				}
				return false;
			} finally {
				if (id === this.request) {
					this.busy = false;
					this.saving = "";
					if (action !== "read" && !this.uncertain && !this.drafts[code] && !this.error) await this.command();
				}
			}
		}
	}
};
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_MilestonePanel = resolveComponent("MilestonePanel");
	return openBlock(), createBlock(_component_MilestonePanel, {
		"page-context": $options.windowContext,
		ref: "panel",
		project: $props.project,
		result: $data.result,
		rows: $options.visibleRows,
		query: $data.query,
		busy: $data.busy,
		error: $data.error,
		uncertain: $data.uncertain,
		confirmation: $data.confirmation,
		deleting: $data.deleting,
		focused: $data.focused,
		onQuery: _cache[0] || (_cache[0] = ($event) => $data.query = $event),
		onCreate: $options.create,
		onChange: $options.stage,
		onSave: $options.save,
		onDiscard: $options.discard,
		onDelete: $options.remove,
		onReview: $options.review,
		onRefresh: $options.refresh,
		onInspectServer: _cache[1] || (_cache[1] = ($event) => $options.command()),
		onClose: _cache[2] || (_cache[2] = ($event) => $options.close()),
		onKeepEditing: _cache[3] || (_cache[3] = ($event) => $data.confirmation = ""),
		onConfirm: $options.confirm,
		onCancelDelete: _cache[4] || (_cache[4] = ($event) => $data.deleting = ""),
		onConfirmDelete: _cache[5] || (_cache[5] = ($event) => $options.command("delete", $data.deleting))
	}, null, 8, [
		"page-context",
		"project",
		"result",
		"rows",
		"query",
		"busy",
		"error",
		"uncertain",
		"confirmation",
		"deleting",
		"focused",
		"onCreate",
		"onChange",
		"onSave",
		"onDiscard",
		"onDelete",
		"onReview",
		"onRefresh",
		"onConfirm"
	]);
}
var MilestoneManager_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { MilestoneManager_exports as n, MilestoneManager_default as t };

//# sourceMappingURL=MilestoneManager.js.map