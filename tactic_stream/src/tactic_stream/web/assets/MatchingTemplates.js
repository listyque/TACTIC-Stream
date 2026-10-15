import { F as renderSlot, G as withCtx, N as openBlock, P as renderList, T as mergeModels, V as useModel, X as ref, _ as createCommentVNode, b as createTextVNode, d as Fragment, et as unref, g as createBlock, h as createBaseVNode, j as onMounted, l as withKeys, m as computed, nt as normalizeStyle, rt as toDisplayString, tt as normalizeClass, u as withModifiers, v as createElementBlock, x as createVNode } from "./vue.js";
import { T as t, c as _sfc_main$2, i as _sfc_main$3 } from "./index.js";
import { M as rpc } from "./clipboard.js";
import { t as _sfc_main$4 } from "./AppTextField.js";
import { t as _sfc_main$5 } from "./AppMenu.js";
import { S as _sfc_main$6 } from "./App.js";
//#region src/controls/AppCheckBox.vue
var _hoisted_1$1 = { class: "app-checkbox-indicator" };
var _hoisted_2$1 = [
	"id",
	"checked",
	"disabled",
	"indeterminate",
	"aria-label"
];
var _sfc_main$1 = {
	__name: "AppCheckBox",
	props: /*@__PURE__*/ mergeModels({
		label: String,
		controlId: String,
		disabled: Boolean,
		indeterminate: Boolean,
		compact: Boolean,
		hideLabel: Boolean,
		translateLabel: {
			type: Boolean,
			default: true
		}
	}, {
		"modelValue": {
			type: Boolean,
			default: false
		},
		"modelModifiers": {}
	}),
	emits: /*@__PURE__*/ mergeModels(["update:modelValue"], ["update:modelValue"]),
	setup(__props, { emit: __emit }) {
		const props = __props;
		const model = useModel(__props, "modelValue");
		const emit = __emit;
		function changed(event) {
			if (props.indeterminate) emit("update:modelValue", true);
			else model.value = event.target.checked;
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("label", { class: normalizeClass(["app-checkbox", {
				disabled: __props.disabled,
				compact: __props.compact
			}]) }, [createBaseVNode("span", _hoisted_1$1, [createBaseVNode("input", {
				id: __props.controlId,
				type: "checkbox",
				checked: !__props.indeterminate && model.value,
				onChange: changed,
				disabled: __props.disabled,
				indeterminate: __props.indeterminate,
				"aria-label": __props.label ? __props.translateLabel ? unref(t)(__props.label) : __props.label : void 0
			}, null, 40, _hoisted_2$1), model.value || __props.indeterminate ? (openBlock(), createBlock(_sfc_main$2, {
				key: 0,
				name: __props.indeterminate ? "minus" : "check"
			}, null, 8, ["name"])) : createCommentVNode("", true)]), !__props.hideLabel ? renderSlot(_ctx.$slots, "default", {}, () => [createTextVNode(toDisplayString(__props.label ? __props.translateLabel ? unref(t)(__props.label) : __props.label : ""), 1)], void 0, 0) : createCommentVNode("", true)], 2);
		};
	}
};
//#endregion
//#region src/features/checkin/MatchingTemplates.vue
var _hoisted_1 = { class: "matching-template-actions" };
var _hoisted_2 = { class: "matching-template-rows" };
var _hoisted_3 = { class: "matching-template-editor" };
var _hoisted_4 = { class: "muted" };
var _hoisted_5 = { class: "matching-template-mapping" };
var _hoisted_6 = { class: "matching-template-test" };
var _hoisted_7 = {
	key: 1,
	class: "error",
	role: "alert"
};
var _hoisted_8 = { class: "muted" };
var _hoisted_9 = { id: "matching-process-options" };
var _hoisted_10 = ["value"];
var _hoisted_11 = { id: "matching-context-options" };
var _hoisted_12 = ["value"];
var _sfc_main = {
	__name: "MatchingTemplates",
	props: {
		scope: Object,
		items: Array,
		padding: Number,
		processes: Array,
		context: String
	},
	emits: ["save", "close"],
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const rows = ref(props.items.map((row) => ({ ...row }))), selectedIndex = ref(0), width = ref(440), example = ref(""), result = ref(""), matchedType = ref(""), error = ref(""), busy = ref(false);
		const selected = computed(() => rows.value[selectedIndex.value]);
		const workspace = ref(null);
		onMounted(() => {
			width.value = Math.max(300, workspace.value.clientWidth * .48);
		});
		const initialPadding = props.padding;
		const dirty = computed(() => props.padding !== initialPadding || JSON.stringify(rows.value.map(({ preview, matchingType, validationError, ...row }) => row)) !== JSON.stringify(props.items.map(({ preview, matchingType, validationError, ...row }) => row)));
		let request = 0;
		async function inspect(test = false) {
			const id = ++request;
			error.value = "";
			result.value = "";
			busy.value = true;
			try {
				const patterns = test ? [selected.value.pattern] : rows.value.map((row) => row.pattern);
				const response = (await rpc("execute_cmd", [
					props.scope,
					"tactic.command.browser_checkin_cmd.BrowserCheckinCmd",
					{
						action: "templates",
						templates: patterns,
						padding: props.padding,
						example: test ? example.value.trim() : ""
					}
				], {}, true)).info.templates;
				if (id !== request) return false;
				for (const row of rows.value) {
					const value = response.find((item) => item.pattern === row.pattern);
					if (value) {
						row.preview = value.preview;
						row.matchingType = value.matchingType;
						row.validationError = value.validationError;
					}
				}
				error.value = test ? response[0].validationError : rows.value.find((row) => row.enabled && row.validationError)?.validationError || "";
				if (test) {
					matchedType.value = response[0].matched;
					result.value = !example.value.trim() ? "Enter a filename to test" : matchedType.value ? "Matched as {type}" : "No match";
				}
				return !error.value;
			} catch (failure) {
				if (id === request) error.value = failure.message;
				return false;
			} finally {
				if (id === request) busy.value = false;
			}
		}
		function select(index) {
			selectedIndex.value = index;
			result.value = "";
			error.value = "";
		}
		function create(duplicate = false) {
			const item = duplicate ? {
				...selected.value,
				locked: false
			} : {
				enabled: true,
				pattern: "$FILENAME.$EXT",
				process: "",
				context: "",
				locked: false
			};
			const index = duplicate ? selectedIndex.value + 1 : rows.value.length;
			rows.value.splice(index, 0, item);
			select(index);
			inspect();
		}
		function move(offset) {
			const index = selectedIndex.value, target = index + offset;
			if (target < 0 || target >= rows.value.length) return;
			rows.value.splice(target, 0, ...rows.value.splice(index, 1));
			select(target);
		}
		function remove() {
			if (selected.value.locked) return;
			rows.value.splice(selectedIndex.value, 1);
			select(Math.min(selectedIndex.value, rows.value.length - 1));
		}
		async function save() {
			if (await inspect()) emit("save", rows.value.map(({ preview, matchingType, matched, validationError, ...row }) => row));
		}
		function close() {
			if (!dirty.value || window.confirm(t("Discard unsaved changes?"))) emit("close");
		}
		__expose({ close });
		inspect();
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "workspace",
				ref: workspace,
				class: "matching-templates-workspace"
			}, [
				createBaseVNode("section", {
					class: "matching-template-list",
					style: normalizeStyle({ "--template-width": width.value + "px" })
				}, [createBaseVNode("header", null, [
					createBaseVNode("strong", null, toDisplayString(unref(t)("Matching templates")), 1),
					createVNode(_sfc_main$3, {
						"icon-only": "",
						label: "Add",
						icon: "add",
						disabled: rows.value.length >= 32,
						onClick: _cache[0] || (_cache[0] = ($event) => create())
					}, null, 8, ["disabled"]),
					createBaseVNode("div", _hoisted_1, [
						createVNode(_sfc_main$3, {
							"icon-only": "",
							label: "Duplicate",
							icon: "copy",
							disabled: rows.value.length >= 32,
							onClick: _cache[1] || (_cache[1] = ($event) => create(true))
						}, null, 8, ["disabled"]),
						createVNode(_sfc_main$3, {
							"icon-only": "",
							label: "Move up",
							icon: "MDI_ARROW_UP",
							disabled: selectedIndex.value === 0,
							onClick: _cache[2] || (_cache[2] = ($event) => move(-1))
						}, null, 8, ["disabled"]),
						createVNode(_sfc_main$3, {
							"icon-only": "",
							label: "Move down",
							icon: "MDI_ARROW_DOWN",
							disabled: selectedIndex.value === rows.value.length - 1,
							onClick: _cache[3] || (_cache[3] = ($event) => move(1))
						}, null, 8, ["disabled"]),
						createVNode(_sfc_main$3, {
							"icon-only": "",
							label: "Delete",
							icon: "delete",
							disabled: selected.value?.locked,
							onClick: remove
						}, null, 8, ["disabled"])
					]),
					createVNode(_sfc_main$5, {
						class: "matching-template-overflow",
						label: "Template actions"
					}, {
						default: withCtx(() => [
							createVNode(_sfc_main$3, {
								label: "Duplicate",
								icon: "copy",
								onClick: _cache[4] || (_cache[4] = ($event) => create(true)),
								disabled: rows.value.length >= 32
							}, null, 8, ["disabled"]),
							createVNode(_sfc_main$3, {
								label: "Move up",
								icon: "MDI_ARROW_UP",
								disabled: selectedIndex.value === 0,
								onClick: _cache[5] || (_cache[5] = ($event) => move(-1))
							}, null, 8, ["disabled"]),
							createVNode(_sfc_main$3, {
								label: "Move down",
								icon: "MDI_ARROW_DOWN",
								disabled: selectedIndex.value === rows.value.length - 1,
								onClick: _cache[6] || (_cache[6] = ($event) => move(1))
							}, null, 8, ["disabled"]),
							createVNode(_sfc_main$3, {
								label: "Delete",
								icon: "delete",
								disabled: selected.value?.locked,
								onClick: remove
							}, null, 8, ["disabled"])
						]),
						_: 1
					})
				]), createBaseVNode("div", _hoisted_2, [(openBlock(true), createElementBlock(Fragment, null, renderList(rows.value, (row, index) => {
					return openBlock(), createElementBlock("article", {
						key: index,
						class: normalizeClass({ selected: index === selectedIndex.value })
					}, [
						createVNode(_sfc_main$1, {
							compact: "",
							"hide-label": "",
							label: "Enable template",
							modelValue: row.enabled,
							"onUpdate:modelValue": [($event) => row.enabled = $event, inspect],
							disabled: row.locked
						}, null, 8, [
							"modelValue",
							"onUpdate:modelValue",
							"disabled"
						]),
						createBaseVNode("small", null, toDisplayString(index + 1), 1),
						createVNode(_sfc_main$3, {
							label: row.pattern,
							onClick: ($event) => select(index)
						}, {
							default: withCtx(() => [
								createBaseVNode("strong", null, toDisplayString(row.pattern), 1),
								createBaseVNode("small", null, toDisplayString(row.validationError || row.preview || row.pattern), 1),
								createBaseVNode("small", null, [
									createTextVNode(toDisplayString(row.matchingType), 1),
									row.process ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [createTextVNode(" · " + toDisplayString(row.process), 1)], 64)) : createCommentVNode("", true),
									row.context ? (openBlock(), createElementBlock(Fragment, { key: 1 }, [createTextVNode(" · " + toDisplayString(row.context), 1)], 64)) : createCommentVNode("", true)
								])
							]),
							_: 2
						}, 1032, ["label", "onClick"])
					], 2);
				}), 128))])], 4),
				createVNode(_sfc_main$6, {
					modelValue: width.value,
					"onUpdate:modelValue": _cache[7] || (_cache[7] = ($event) => width.value = $event),
					min: 260,
					max: 650,
					label: "Templates pane width"
				}, null, 8, ["modelValue"]),
				createBaseVNode("section", _hoisted_3, [
					createBaseVNode("strong", null, toDisplayString(unref(t)("Template properties")), 1),
					createBaseVNode("label", null, [createTextVNode(toDisplayString(unref(t)("Pattern")), 1), createVNode(_sfc_main$4, {
						modelValue: selected.value.pattern,
						"onUpdate:modelValue": _cache[8] || (_cache[8] = ($event) => selected.value.pattern = $event),
						label: "Pattern",
						disabled: selected.value.locked,
						onChange: inspect
					}, null, 8, ["modelValue", "disabled"])]),
					createBaseVNode("small", _hoisted_4, toDisplayString(unref(t)("Preview: {preview} · Type: {type}", {
						preview: selected.value.preview || selected.value.pattern,
						type: selected.value.matchingType || "—"
					})), 1),
					createBaseVNode("div", _hoisted_5, [createBaseVNode("label", null, [createTextVNode(toDisplayString(unref(t)("Process mapping")), 1), createVNode(_sfc_main$4, {
						modelValue: selected.value.process,
						"onUpdate:modelValue": _cache[9] || (_cache[9] = ($event) => selected.value.process = $event),
						label: "Process mapping",
						list: "matching-process-options",
						placeholder: "All processes",
						disabled: selected.value.locked
					}, null, 8, ["modelValue", "disabled"])]), createBaseVNode("label", null, [createTextVNode(toDisplayString(unref(t)("Context mapping")), 1), createVNode(_sfc_main$4, {
						modelValue: selected.value.context,
						"onUpdate:modelValue": _cache[10] || (_cache[10] = ($event) => selected.value.context = $event),
						label: "Context mapping",
						list: "matching-context-options",
						placeholder: "All contexts",
						disabled: selected.value.locked
					}, null, 8, ["modelValue", "disabled"])])]),
					createBaseVNode("label", null, [createTextVNode(toDisplayString(unref(t)("Test on filename")), 1), createBaseVNode("div", _hoisted_6, [createVNode(_sfc_main$4, {
						modelValue: example.value,
						"onUpdate:modelValue": _cache[11] || (_cache[11] = ($event) => example.value = $event),
						label: "Test on filename",
						placeholder: "shot.001.exr",
						onKeydown: _cache[12] || (_cache[12] = withKeys(withModifiers(($event) => inspect(true), ["prevent"]), ["enter"]))
					}, null, 8, ["modelValue"]), createVNode(_sfc_main$3, {
						label: "Test",
						icon: "search",
						disabled: busy.value,
						onClick: _cache[13] || (_cache[13] = ($event) => inspect(true))
					}, null, 8, ["disabled"])])]),
					result.value ? (openBlock(), createElementBlock("p", {
						key: 0,
						class: normalizeClass({ error: result.value === "No match" }),
						role: "status"
					}, toDisplayString(unref(t)(result.value, { type: matchedType.value })), 3)) : createCommentVNode("", true),
					error.value ? (openBlock(), createElementBlock("p", _hoisted_7, toDisplayString(unref(t)(error.value)), 1)) : createCommentVNode("", true),
					createBaseVNode("footer", null, [
						createBaseVNode("span", _hoisted_8, toDisplayString(dirty.value ? unref(t)("Unsaved changes") : ""), 1),
						createVNode(_sfc_main$3, {
							label: "Cancel",
							onClick: close
						}),
						createVNode(_sfc_main$3, {
							label: "Save",
							icon: "save",
							highlighted: "",
							disabled: !dirty.value || busy.value,
							onClick: save
						}, null, 8, ["disabled"])
					])
				]),
				createBaseVNode("datalist", _hoisted_9, [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.processes || [], (process) => {
					return openBlock(), createElementBlock("option", {
						key: process.value,
						value: process.value
					}, null, 8, _hoisted_10);
				}), 128))]),
				createBaseVNode("datalist", _hoisted_11, [createBaseVNode("option", { value: __props.context }, null, 8, _hoisted_12)])
			], 512);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=MatchingTemplates.js.map