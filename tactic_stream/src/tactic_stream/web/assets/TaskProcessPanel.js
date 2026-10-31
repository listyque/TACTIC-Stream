import { A as onMounted, G as withCtx, J as markRaw, M as openBlock, N as renderList, O as onBeforeUnmount, S as h, X as ref, _ as createElementBlock, b as createVNode, et as unref, g as createCommentVNode, h as createBlock, m as createBaseVNode, nt as normalizeStyle, p as computed, rt as toDisplayString, tt as normalizeClass, u as Fragment } from "./vue.js";
import { o as t, s as appearance, t as _sfc_main$2 } from "./AppButton.js";
import { B as frameContentWidth, C as translate, G as label, J as node, N as _sfc_main$5, V as observeFrameSizes, W as button, Y as rect, t as _sfc_main$4, y as _sfc_main$3 } from "./FrameView.js";
import { A as _sfc_main$6 } from "./ConfiguredView.js";
//#region ../src/tactic_stream/shared_ui/features/tasks/process.ui.mjs
var metrics = {
	cardHeight: 119,
	cardPitch: 126,
	columnMinimum: 224,
	compactHeight: 44,
	gap: 7,
	compactGap: 5,
	inset: 6
};
function columns(width) {
	return Math.max(1, Math.floor(width / metrics.columnMinimum));
}
function minimumWidth(model) {
	return 442 + (model.dirty ? 70 : 0);
}
function describe(model, width, mode, language) {
	const tr = (text) => translate(text, language);
	const compact = mode === "compact";
	const height = compact ? metrics.compactHeight : metrics.cardHeight;
	const nodes = [
		node("Box", "taskProcessSurface", rect(0, 0, width, height), {
			background: compact || model.hasTask ? "surfaceContainer" : "surfaceContainerLow",
			radiusRole: compact ? "itemRadius" : "surfaceRadius",
			border: model.dirty ? "action" : void 0
		}),
		node("Box", "taskProcessRail", rect(0, compact ? 6 : 0, 3, compact ? height - 12 : height), {
			background: model.color || "action",
			radius: 1.5
		}),
		node("Box", "taskProcessDot", rect(compact ? 11 : 10, compact ? 16.5 : 18, compact ? 11 : 12, compact ? 11 : 12), {
			background: model.color || "action",
			radius: 6
		})
	];
	const actions = [];
	if (model.dirty) actions.push([
		"discard",
		"Reset task changes",
		"undo",
		28
	], [
		"save",
		model.hasTask ? "Save task changes" : "Create task",
		"save",
		28
	]);
	actions.push([
		"notes",
		"Task notes",
		"comment",
		30
	], [
		"menu",
		"Task actions",
		"more",
		28
	]);
	const gap = compact ? 7 : 5;
	const actionsWidth = actions.reduce((sum, action) => sum + action[3], 0) + (actions.length - 1) * gap;
	const actionLeft = width - (compact ? 7 : 8) - actionsWidth;
	let x = actionLeft;
	for (const [type, title, icon, extent] of actions) {
		nodes.push(button("taskProcess_" + type, rect(x, compact ? (height - extent) / 2 : 8, extent, extent), tr(title), icon, { type }, !model.blocked && (type !== "notes" || model.hasTarget !== false && !model.deleting), {
			iconOnly: true,
			iconAction: true,
			iconSize: 17,
			badgeCount: type === "notes" ? model.notes || 0 : 0,
			iconColor: type === "save" || type === "notes" && model.notes ? "action" : "primaryText"
		}));
		x += extent + gap;
	}
	nodes.push(label("taskProcessTitle", rect(compact ? 29 : 27, compact ? 12 : 14, compact ? 100 : Math.max(0, actionLeft - 32), 20), model.label + (model.count > 1 ? " | " + model.count : ""), {
		fontRole: compact ? "body" : "bodyLarge",
		weight: 600
	}));
	const statusX = compact ? 136 : 10, userX = compact ? 255 : 10;
	nodes.push(node("View", "taskProcessStatus", rect(statusX, compact ? 7.5 : 47, compact ? 112 : width - 18, compact ? 29 : 28), { view: "status" }), node("View", "taskProcessAssignee", rect(userX, compact ? 7.5 : 82, compact ? Math.max(0, actionLeft - 7 - userX) : width - 18, compact ? 29 : 28), { view: "assigned" }));
	return {
		nodes,
		height
	};
}
//#endregion
//#region src/features/tasks/TaskProcessItem.vue
var _hoisted_1$1 = ["data-process", "data-task-key"];
var _sfc_main$1 = {
	__name: "TaskProcessItem",
	props: {
		record: Object,
		mode: String,
		blocked: Boolean
	},
	emits: [
		"change",
		"save",
		"discard",
		"inspect",
		"add",
		"edit",
		"delete",
		"select"
	],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const host = ref(null), width = ref(0), menu = ref(null), anchor = ref(null);
		const scene = computed(() => describe({
			label: props.record.label,
			count: props.record.choices.length,
			color: props.record.color,
			hasTask: !!props.record.plan.task_key,
			dirty: props.record.dirty,
			notes: props.record.notes,
			blocked: props.blocked,
			deleting: props.record.deleting,
			hasTarget: true
		}, width.value, props.mode, appearance.language));
		const editable = (name) => !props.blocked && !props.record.deleting && props.record.plan.fields.some((field) => field.name === name && field.editable);
		const statusPort = markRaw({ setup(_, { attrs }) {
			return () => h(_sfc_main$6, {
				...attrs,
				value: props.record.values.status || "",
				options: props.record.statuses,
				disabled: !editable("status"),
				onChange: (value) => emit("change", "status", value)
			});
		} });
		const userPort = markRaw({ setup(_, { attrs }) {
			return () => h(_sfc_main$3, {
				...attrs,
				value: props.record.values.assigned || "",
				options: props.record.users,
				disabled: !editable("assigned"),
				onChange: (value) => emit("change", "assigned", value)
			});
		} });
		const views = {
			status: { component: statusPort },
			assigned: { component: userPort }
		};
		function event(action, source) {
			if (action.type === "menu") {
				anchor.value = source;
				if (menu.value.open) menu.value.close();
				else {
					const box = source.getBoundingClientRect();
					menu.value.openAt({
						clientX: box.left,
						clientY: box.bottom + 6,
						target: source
					});
				}
			} else emit(action.type === "notes" ? "inspect" : action.type);
		}
		let observer;
		onMounted(() => {
			const measure = () => {
				width.value = frameContentWidth(host.value);
			};
			measure();
			observer = observeFrameSizes(measure);
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: normalizeClass(["task-process-item", {
					dirty: __props.record.dirty,
					missing: !__props.record.plan.task_key
				}]),
				"data-process": __props.record.value,
				"data-task-key": __props.record.key,
				style: normalizeStyle({
					height: scene.value.height + "px",
					minWidth: __props.mode === "compact" ? minimumWidth(__props.record) + "px" : void 0
				})
			}, [createVNode(_sfc_main$4, {
				scene: scene.value,
				views,
				onEvent: event
			}, null, 8, ["scene"]), createVNode(_sfc_main$5, {
				ref_key: "menu",
				ref: menu,
				anchor: anchor.value,
				"external-trigger": "",
				label: "Task actions",
				overlay: "",
				disabled: __props.blocked
			}, {
				default: withCtx(() => [
					createVNode(_sfc_main$2, {
						label: "Add task",
						icon: "add",
						disabled: __props.blocked,
						onClick: _cache[0] || (_cache[0] = ($event) => emit("add"))
					}, null, 8, ["disabled"]),
					__props.record.plan.task_key ? (openBlock(), createBlock(_sfc_main$2, {
						key: 0,
						label: "Edit task",
						icon: "edit",
						disabled: __props.blocked || __props.record.deleting,
						onClick: _cache[1] || (_cache[1] = ($event) => emit("edit"))
					}, null, 8, ["disabled"])) : createCommentVNode("", true),
					__props.record.plan.task_key ? (openBlock(), createBlock(_sfc_main$2, {
						key: 1,
						label: "Delete task",
						icon: "delete",
						destructive: "",
						disabled: __props.blocked || __props.record.dirty,
						onClick: _cache[2] || (_cache[2] = ($event) => emit("delete"))
					}, null, 8, ["disabled"])) : createCommentVNode("", true),
					__props.record.choices.length > 1 ? (openBlock(), createElementBlock(Fragment, { key: 2 }, [
						_cache[3] || (_cache[3] = createBaseVNode("hr", null, null, -1)),
						createBaseVNode("strong", null, toDisplayString(unref(t)("Tasks")), 1),
						(openBlock(true), createElementBlock(Fragment, null, renderList(__props.record.choices, (choice) => {
							return openBlock(), createBlock(_sfc_main$2, {
								key: choice.key,
								label: choice.label,
								"translate-label": false,
								"aria-pressed": __props.record.key === choice.key,
								icon: __props.record.key === choice.key ? "check" : void 0,
								onClick: ($event) => emit("select", choice.key)
							}, null, 8, [
								"label",
								"aria-pressed",
								"icon",
								"onClick"
							]);
						}), 128))
					], 64)) : createCommentVNode("", true)
				]),
				_: 1
			}, 8, ["anchor", "disabled"])], 14, _hoisted_1$1);
		};
	}
};
//#endregion
//#region src/features/tasks/TaskProcessPanel.vue
var _hoisted_1 = ["aria-label"];
var _hoisted_2 = {
	key: 0,
	class: "task-manager-empty",
	role: "status"
};
var _sfc_main = {
	__name: "TaskProcessPanel",
	props: {
		records: Array,
		mode: String,
		blocked: Boolean,
		target: Object
	},
	emits: [
		"change",
		"save",
		"discard",
		"inspect",
		"add",
		"edit",
		"delete",
		"select"
	],
	setup(__props, { emit: __emit }) {
		const emit = __emit;
		const panel = ref(null), width = ref(0);
		const columns$1 = computed(() => columns(width.value));
		let observer;
		onMounted(() => {
			observer = observeFrameSizes((entries) => {
				width.value = entries[0].contentRect.width;
			});
			observer.observe(panel.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock(Fragment, null, [createBaseVNode("div", {
				ref_key: "panel",
				ref: panel,
				class: normalizeClass(["task-process-panel", __props.mode]),
				"aria-label": unref(t)("Task processes"),
				style: normalizeStyle({
					"--process-columns": columns$1.value,
					"--process-card-width": Math.max(0, width.value / columns$1.value - metrics.gap) + "px",
					padding: metrics.inset + "px",
					gap: (__props.mode === "cards" ? metrics.gap : metrics.compactGap) + "px"
				})
			}, [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.target ? __props.records : [], (record) => {
				return openBlock(), createBlock(_sfc_main$1, {
					key: record.value,
					record,
					mode: __props.mode,
					blocked: __props.blocked,
					onChange: (name, value) => emit("change", record, name, value),
					onSave: ($event) => emit("save", record),
					onDiscard: ($event) => emit("discard", record),
					onInspect: ($event) => emit("inspect", record),
					onAdd: ($event) => emit("add", record),
					onEdit: ($event) => emit("edit", record),
					onDelete: ($event) => emit("delete", record),
					onSelect: ($event) => emit("select", record.value, $event)
				}, null, 8, [
					"record",
					"mode",
					"blocked",
					"onChange",
					"onSave",
					"onDiscard",
					"onInspect",
					"onAdd",
					"onEdit",
					"onDelete",
					"onSelect"
				]);
			}), 128))], 14, _hoisted_1), !__props.target ? (openBlock(), createElementBlock("div", _hoisted_2, toDisplayString(unref(t)("Select an sObject to view its task processes")), 1)) : createCommentVNode("", true)], 64);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=TaskProcessPanel.js.map