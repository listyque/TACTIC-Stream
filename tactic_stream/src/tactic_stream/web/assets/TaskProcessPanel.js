import { G as withCtx, N as openBlock, P as renderList, X as ref, _ as createCommentVNode, b as createTextVNode, d as Fragment, et as unref, g as createBlock, h as createBaseVNode, j as onMounted, k as onBeforeUnmount, nt as normalizeStyle, rt as toDisplayString, tt as normalizeClass, v as createElementBlock, x as createVNode } from "./vue.js";
import { D as t, o as _sfc_main$1 } from "./index.js";
import { t as _sfc_main$2 } from "./AppMenu.js";
import { t as _sfc_main$3 } from "./UserComboBox.js";
import { t as _sfc_main$4 } from "./ItemSurface.js";
import { A as _sfc_main$5 } from "./App.js";
//#region src/features/tasks/TaskProcessPanel.vue
var _hoisted_1 = ["aria-label"];
var _hoisted_2 = { class: "task-process-title" };
var _hoisted_3 = { class: "task-process-actions" };
var _hoisted_4 = {
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
	setup(__props) {
		const editable = (record, name) => record.plan.fields.some((field) => field.name === name && field.editable) && !record.deleting;
		const panel = ref(null), columns = ref(1);
		let observer;
		onMounted(() => {
			observer = new ResizeObserver((entries) => {
				columns.value = Math.max(1, Math.floor(entries[0].contentRect.width / 224));
			});
			observer.observe(panel.value);
		});
		onBeforeUnmount(() => observer.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock(Fragment, null, [createBaseVNode("div", {
				ref_key: "panel",
				ref: panel,
				class: normalizeClass(["task-process-panel", __props.mode]),
				"aria-label": unref(t)("Task processes"),
				style: normalizeStyle({ "--process-columns": columns.value })
			}, [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.target ? __props.records : [], (record) => {
				return openBlock(), createBlock(_sfc_main$4, {
					key: record.value,
					accent: record.color,
					inset: 0,
					class: normalizeClass(["task-process-item", {
						dirty: record.dirty,
						missing: !record.plan.task_key
					}]),
					"data-process": record.value,
					"data-task-key": record.key
				}, {
					default: withCtx(() => [
						createBaseVNode("div", _hoisted_2, [createBaseVNode("span", {
							class: "task-process-dot",
							style: normalizeStyle({ backgroundColor: record.color })
						}, null, 4), createBaseVNode("strong", null, [createTextVNode(toDisplayString(record.label), 1), record.choices.length > 1 ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [createTextVNode(" | " + toDisplayString(record.choices.length), 1)], 64)) : createCommentVNode("", true)])]),
						createVNode(_sfc_main$5, {
							value: record.values.status || "",
							options: record.statuses,
							disabled: __props.blocked || !editable(record, "status"),
							onChange: ($event) => _ctx.$emit("change", record, "status", $event)
						}, null, 8, [
							"value",
							"options",
							"disabled",
							"onChange"
						]),
						createVNode(_sfc_main$3, {
							value: record.values.assigned || "",
							options: record.users,
							disabled: __props.blocked || !editable(record, "assigned"),
							onChange: ($event) => _ctx.$emit("change", record, "assigned", $event)
						}, null, 8, [
							"value",
							"options",
							"disabled",
							"onChange"
						]),
						createBaseVNode("div", _hoisted_3, [
							record.dirty ? (openBlock(), createBlock(_sfc_main$1, {
								key: 0,
								label: "Reset task changes",
								icon: "undo",
								"icon-only": "",
								disabled: __props.blocked,
								onClick: ($event) => _ctx.$emit("discard", record)
							}, null, 8, ["disabled", "onClick"])) : createCommentVNode("", true),
							record.dirty ? (openBlock(), createBlock(_sfc_main$1, {
								key: 1,
								label: record.plan.task_key ? "Save task changes" : "Create task",
								icon: "save",
								"icon-only": "",
								disabled: __props.blocked,
								onClick: ($event) => _ctx.$emit("save", record)
							}, null, 8, [
								"label",
								"disabled",
								"onClick"
							])) : createCommentVNode("", true),
							createVNode(_sfc_main$1, {
								label: "Task notes",
								icon: "comment",
								"icon-only": "",
								"badge-count": record.notes,
								disabled: __props.blocked || record.deleting,
								onClick: ($event) => _ctx.$emit("inspect", record)
							}, null, 8, [
								"badge-count",
								"disabled",
								"onClick"
							]),
							createVNode(_sfc_main$2, {
								label: "Task actions",
								overlay: "",
								disabled: __props.blocked
							}, {
								default: withCtx(() => [
									createVNode(_sfc_main$1, {
										label: "Add task",
										icon: "add",
										disabled: __props.blocked,
										onClick: ($event) => _ctx.$emit("add", record)
									}, null, 8, ["disabled", "onClick"]),
									record.plan.task_key ? (openBlock(), createBlock(_sfc_main$1, {
										key: 0,
										label: "Edit task",
										icon: "edit",
										disabled: __props.blocked || record.deleting,
										onClick: ($event) => _ctx.$emit("edit", record)
									}, null, 8, ["disabled", "onClick"])) : createCommentVNode("", true),
									record.plan.task_key ? (openBlock(), createBlock(_sfc_main$1, {
										key: 1,
										label: "Delete task",
										icon: "delete",
										destructive: "",
										disabled: __props.blocked || record.dirty,
										onClick: ($event) => _ctx.$emit("delete", record)
									}, null, 8, ["disabled", "onClick"])) : createCommentVNode("", true),
									record.choices.length > 1 ? (openBlock(), createElementBlock(Fragment, { key: 2 }, [
										_cache[0] || (_cache[0] = createBaseVNode("hr", null, null, -1)),
										createBaseVNode("strong", null, toDisplayString(unref(t)("Tasks")), 1),
										(openBlock(true), createElementBlock(Fragment, null, renderList(record.choices, (choice) => {
											return openBlock(), createBlock(_sfc_main$1, {
												key: choice.key,
												label: choice.label,
												"aria-label": choice.label,
												"aria-pressed": record.key === choice.key,
												icon: record.key === choice.key ? "check" : void 0,
												onClick: ($event) => _ctx.$emit("select", record.value, choice.key)
											}, {
												default: withCtx(() => [createTextVNode(toDisplayString(choice.label), 1)]),
												_: 2
											}, 1032, [
												"label",
												"aria-label",
												"aria-pressed",
												"icon",
												"onClick"
											]);
										}), 128))
									], 64)) : createCommentVNode("", true)
								]),
								_: 2
							}, 1032, ["disabled"])
						])
					]),
					_: 2
				}, 1032, [
					"accent",
					"class",
					"data-process",
					"data-task-key"
				]);
			}), 128))], 14, _hoisted_1), !__props.target ? (openBlock(), createElementBlock("div", _hoisted_4, toDisplayString(unref(t)("Select an sObject to view its task processes")), 1)) : createCommentVNode("", true)], 64);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=TaskProcessPanel.js.map