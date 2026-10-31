import { A as onMounted, E as nextTick, G as withCtx, H as watch, M as openBlock, N as renderList, O as onBeforeUnmount, P as renderSlot, X as ref, _ as createElementBlock, b as createVNode, et as unref, g as createCommentVNode, h as createBlock, l as withModifiers, m as createBaseVNode, nt as normalizeStyle, p as computed, rt as toDisplayString, tt as normalizeClass, u as Fragment } from "./vue.js";
import { D as spacing, O as textStyles, R as BusyIndicator_default, _ as controls, a as _sfc_main$15, o as t, s as appearance, t as _sfc_main$14, w as lineHeights, z as _plugin_vue_export_helper_default } from "./AppButton.js";
import { A as _sfc_main$26, C as translate, E as _sfc_main$22, G as label, J as node, N as _sfc_main$16, O as AppSearchField_default, R as _sfc_main$25, T as AppProgress_default, U as _sfc_main$28, V as observeFrameSizes, W as button, Y as rect, _ as describe$5, a as _sfc_main$17, i as _sfc_main$18, n as _sfc_main$24, r as _sfc_main$19, t as _sfc_main$29, v as _sfc_main$20, w as _sfc_main$27, x as _sfc_main$23, z as _sfc_main$21 } from "./FrameView.js";
import { n as _sfc_main$30, r as _sfc_main$31 } from "./AppearanceControls.js";
import { r as ImagePicker_default, t as _sfc_main$32 } from "./RecordForm.js";
import { u as _sfc_main$33 } from "./admin.document.js";
import { $ as _sfc_main$40, A as _sfc_main$34, D as _sfc_main$39, Q as _sfc_main$37, U as _sfc_main$35, et as _sfc_main$36, ut as _sfc_main$38 } from "./ConfiguredView.js";
import { t as _sfc_main$41 } from "./ActionRow.js";
import { t as _sfc_main$42 } from "./AppDialog.js";
import { t as _sfc_main$43 } from "./ContentLoadingOverlay.js";
import { a as visibleRows, i as row$3, n as navigate, t as listAction } from "./tree.ui.js";
import { E as surfaces, T as filterGeometry, d as _sfc_main$44, u as QuickFilterOptions_default, w as QuickFilterChip_default } from "./App.js";
//#region src/features/administration/ShowcaseMenu.vue
var _sfc_main$13 = {
	__name: "ShowcaseMenu",
	props: { frameNode: {
		type: Object,
		required: true
	} },
	emits: ["event"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const menu = ref(null);
		const trigger = ref(null);
		function open(event, below) {
			if (!props.frameNode.enabled) return;
			const bounds = trigger.value.$el.getBoundingClientRect();
			menu.value?.openAt(below ? {
				clientX: bounds.left,
				clientY: bounds.bottom,
				target: trigger.value.$el
			} : event);
		}
		function choose(command) {
			menu.value?.close(true);
			emit("event", {
				...props.frameNode.action,
				value: command
			});
		}
		watch(() => props.frameNode.enabled, (enabled) => {
			if (!enabled) menu.value?.close(true);
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", null, [createVNode(_sfc_main$14, {
				ref_key: "trigger",
				ref: trigger,
				label: __props.frameNode.text,
				"translate-label": false,
				disabled: !__props.frameNode.enabled,
				style: {
					"width": "100%",
					"height": "100%"
				},
				onClick: _cache[0] || (_cache[0] = ($event) => open($event, true)),
				onContextmenu: _cache[1] || (_cache[1] = withModifiers(($event) => open($event, false), ["prevent"]))
			}, null, 8, ["label", "disabled"]), createVNode(_sfc_main$16, {
				ref_key: "menu",
				ref: menu,
				label: __props.frameNode.text,
				"external-trigger": "",
				anchor: trigger.value?.$el,
				overlay: "",
				"frame-composition": "",
				disabled: !__props.frameNode.enabled
			}, {
				default: withCtx(() => [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.frameNode.actions, (record, index) => {
					return openBlock(), createElementBlock(Fragment, { key: index }, [record.children ? (openBlock(), createBlock(_sfc_main$16, {
						key: 0,
						label: record.title,
						"show-label": "",
						submenu: "",
						overlay: "",
						"frame-composition": ""
					}, {
						default: withCtx(() => [(openBlock(true), createElementBlock(Fragment, null, renderList(record.children, (child) => {
							return openBlock(), createBlock(_sfc_main$41, {
								key: child.command,
								record: child,
								onTriggered: ($event) => choose(child.command)
							}, null, 8, ["record", "onTriggered"]);
						}), 128))]),
						_: 2
					}, 1032, ["label"])) : (openBlock(), createBlock(_sfc_main$41, {
						key: 1,
						record,
						onTriggered: ($event) => choose(record.command)
					}, null, 8, ["record", "onTriggered"]))], 64);
				}), 128))]),
				_: 1
			}, 8, [
				"label",
				"anchor",
				"disabled"
			])]);
		};
	}
};
//#endregion
//#region src/features/administration/ShowcaseDialog.vue
var _hoisted_1$8 = ["role"];
var _hoisted_2$4 = { class: "window-actions" };
var _sfc_main$12 = {
	__name: "ShowcaseDialog",
	props: { frameNode: {
		type: Object,
		required: true
	} },
	emits: ["event"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const dialog = ref(null);
		let outcome = "";
		watch(() => props.frameNode.open, async (opened) => {
			await nextTick();
			if (opened) {
				outcome = "";
				dialog.value?.show();
			} else if (dialog.value?.open) dialog.value.close();
		}, { immediate: true });
		function finish(value) {
			outcome = value;
			dialog.value.close();
		}
		function closed() {
			if (props.frameNode.open) emit("event", {
				...props.frameNode.action,
				value: outcome || "cancel"
			});
		}
		onBeforeUnmount(() => {
			if (dialog.value?.open) dialog.value.close();
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", null, [createVNode(_sfc_main$42, {
				ref_key: "dialog",
				ref: dialog,
				title: __props.frameNode.text,
				"translate-title": false,
				style: normalizeStyle({ width: (__props.frameNode.popupWidth || 440) + "px" }),
				onClosed: closed
			}, {
				default: withCtx(() => [createBaseVNode("p", { role: __props.frameNode.error ? "alert" : void 0 }, toDisplayString(__props.frameNode.message), 9, _hoisted_1$8), createBaseVNode("footer", _hoisted_2$4, [createVNode(_sfc_main$14, {
					label: __props.frameNode.cancelText || unref(t)("Cancel"),
					onClick: _cache[0] || (_cache[0] = ($event) => finish("cancel"))
				}, null, 8, ["label"]), createVNode(_sfc_main$14, {
					label: __props.frameNode.acceptText || unref(t)("Apply"),
					highlighted: "",
					disabled: !__props.frameNode.enabled,
					onClick: _cache[1] || (_cache[1] = ($event) => finish("accept"))
				}, null, 8, ["label", "disabled"])])]),
				_: 1
			}, 8, ["title", "style"])]);
		};
	}
};
//#endregion
//#region src/controls/actions/PreviewNavigationButton.vue
var _sfc_main$11 = {
	__name: "PreviewNavigationButton",
	props: {
		icon: {
			type: String,
			default: "chevron-right"
		},
		label: String
	},
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createBlock(_sfc_main$14, {
				class: "preview-navigation-button",
				"icon-only": "",
				icon: __props.icon,
				label: __props.label
			}, null, 8, ["icon", "label"]);
		};
	}
};
//#endregion
//#region src/controls/display/ReactionChip.vue
var _hoisted_1$7 = { class: "reaction-emoji" };
var _hoisted_2$3 = { key: 0 };
var _sfc_main$10 = {
	__name: "ReactionChip",
	props: {
		emoji: String,
		count: {
			type: Number,
			default: 0
		},
		checked: Boolean,
		label: String
	},
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createBlock(_sfc_main$14, {
				class: normalizeClass(["reaction-chip", { checked: __props.checked }]),
				"aria-pressed": __props.checked,
				label: __props.label || __props.emoji
			}, {
				default: withCtx(() => [createBaseVNode("span", _hoisted_1$7, toDisplayString(__props.emoji), 1), __props.count > 1 ? (openBlock(), createElementBlock("span", _hoisted_2$3, toDisplayString(__props.count), 1)) : createCommentVNode("", true)]),
				_: 1
			}, 8, [
				"class",
				"aria-pressed",
				"label"
			]);
		};
	}
};
//#endregion
//#region src/controls/layout/EditorPanel.vue
var _hoisted_1$6 = { key: 0 };
var _hoisted_2$2 = { key: 0 };
var _hoisted_3$1 = {
	key: 1,
	class: "editor-panel-actions"
};
var _sfc_main$9 = {
	__name: "EditorPanel",
	props: {
		title: String,
		description: String,
		icon: String,
		padding: {
			type: Number,
			default: controls.editorPanel.padding
		},
		fillContentHeight: {
			type: Boolean,
			default: true
		}
	},
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				class: "editor-panel",
				style: normalizeStyle({ padding: Math.max(0, __props.padding - 1) + "px" })
			}, [__props.title || _ctx.$slots.actions ? (openBlock(), createElementBlock("header", _hoisted_1$6, [
				__props.icon ? (openBlock(), createBlock(_sfc_main$15, {
					key: 0,
					name: __props.icon
				}, null, 8, ["name"])) : createCommentVNode("", true),
				createBaseVNode("div", null, [createBaseVNode("strong", null, toDisplayString(unref(t)(__props.title)), 1), __props.description ? (openBlock(), createElementBlock("p", _hoisted_2$2, toDisplayString(unref(t)(__props.description)), 1)) : createCommentVNode("", true)]),
				_ctx.$slots.actions ? (openBlock(), createElementBlock("div", _hoisted_3$1, [renderSlot(_ctx.$slots, "actions")])) : createCommentVNode("", true)
			])) : createCommentVNode("", true), createBaseVNode("div", { class: normalizeClass(["editor-panel-body", { "fill-content": __props.fillContentHeight }]) }, [renderSlot(_ctx.$slots, "default")], 2)], 4);
		};
	}
};
//#endregion
//#region src/controls/layout/ConfigurationSection.vue
var _hoisted_1$5 = { key: 0 };
var _sfc_main$8 = {
	__name: "ConfigurationSection",
	props: {
		title: String,
		description: String,
		fillContentHeight: Boolean
	},
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", { class: normalizeClass(["configuration-section", { "fill-content": __props.fillContentHeight }]) }, [
				createBaseVNode("strong", null, toDisplayString(unref(t)(__props.title)), 1),
				__props.description ? (openBlock(), createElementBlock("p", _hoisted_1$5, toDisplayString(unref(t)(__props.description)), 1)) : createCommentVNode("", true),
				createBaseVNode("div", null, [renderSlot(_ctx.$slots, "default")])
			], 2);
		};
	}
};
//#endregion
//#region src/controls/layout/SectionLabel.vue
var _hoisted_1$4 = { class: "section-label" };
var _sfc_main$7 = {
	__name: "SectionLabel",
	props: { text: String },
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("span", _hoisted_1$4, toDisplayString(unref(t)(__props.text)), 1);
		};
	}
};
//#endregion
//#region src/controls/forms/FormFieldFrame.vue
var _hoisted_1$3 = { class: "form-field-icon" };
var _hoisted_2$1 = { class: "field-title-text" };
var _hoisted_3 = {
	key: 0,
	class: "field-required"
};
var _hoisted_4 = { key: 0 };
var _hoisted_5 = {
	key: 0,
	role: "alert"
};
var _sfc_main$6 = {
	__name: "FormFieldFrame",
	props: {
		title: String,
		fieldName: String,
		description: String,
		icon: String,
		error: String,
		required: Boolean,
		readonly: Boolean
	},
	setup(__props) {
		const heading = ref(null), editor = ref(null), weights = ref({
			heading: 1,
			editor: 1
		});
		let observer;
		onMounted(() => {
			observer = new ResizeObserver(() => {
				weights.value = {
					heading: Math.max(1, heading.value.offsetHeight),
					editor: Math.max(1, editor.value.offsetHeight)
				};
			});
			observer.observe(heading.value);
			observer.observe(editor.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", { class: normalizeClass(["form-field-frame", { "has-error": !!__props.error }]) }, [createBaseVNode("div", {
				class: "form-field-layout",
				style: normalizeStyle({
					"--field-heading-weight": weights.value.heading + "fr",
					"--field-editor-weight": weights.value.editor + "fr"
				})
			}, [createBaseVNode("header", {
				ref_key: "heading",
				ref: heading
			}, [createBaseVNode("span", _hoisted_1$3, [createVNode(_sfc_main$15, { name: __props.icon }, null, 8, ["name"])]), createBaseVNode("div", null, [
				createBaseVNode("strong", null, [createBaseVNode("span", _hoisted_2$1, toDisplayString(unref(t)(__props.title)), 1), __props.required ? (openBlock(), createElementBlock("span", _hoisted_3, " *")) : createCommentVNode("", true)]),
				createBaseVNode("p", null, toDisplayString(__props.description ? unref(t)(__props.description) : __props.fieldName), 1),
				__props.readonly ? (openBlock(), createElementBlock("small", _hoisted_4, toDisplayString(unref(t)("Read only")), 1)) : createCommentVNode("", true)
			])], 512), createBaseVNode("div", {
				ref_key: "editor",
				ref: editor,
				class: "form-field-editor"
			}, [renderSlot(_ctx.$slots, "default"), __props.error ? (openBlock(), createElementBlock("p", _hoisted_5, toDisplayString(unref(t)(__props.error)), 1)) : createCommentVNode("", true)], 512)], 4)], 2);
		};
	}
};
//#endregion
//#region src/controls/lists/EditorListItem.vue
var _hoisted_1$2 = { class: "editor-list-item-text" };
var _hoisted_2 = { key: 0 };
var _sfc_main$5 = {
	__name: "EditorListItem",
	props: {
		text: String,
		description: String,
		icon: String,
		badgeText: String,
		selected: Boolean,
		wrapTitle: Boolean,
		accent: String,
		disabled: Boolean
	},
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createBlock(_sfc_main$17, {
				class: "editor-list-item-surface",
				selected: __props.selected,
				accent: __props.accent,
				"selected-color": "var(--selected)",
				"normal-color": "transparent",
				"rail-visible": !!__props.selected,
				"separator-visible": false,
				inset: 0
			}, {
				default: withCtx(() => [createVNode(_sfc_main$14, {
					class: normalizeClass(["editor-list-item", {
						selected: __props.selected,
						"wrap-title": __props.wrapTitle
					}]),
					label: __props.text,
					"translate-label": false,
					"aria-description": __props.description,
					disabled: __props.disabled
				}, {
					default: withCtx(() => [
						__props.icon ? (openBlock(), createBlock(_sfc_main$15, {
							key: 0,
							name: __props.icon,
							style: normalizeStyle({ color: __props.accent || "var(--primary)" })
						}, null, 8, ["name", "style"])) : createCommentVNode("", true),
						createBaseVNode("span", _hoisted_1$2, [createBaseVNode("strong", null, toDisplayString(__props.text), 1), __props.description ? (openBlock(), createElementBlock("span", _hoisted_2, toDisplayString(__props.description), 1)) : createCommentVNode("", true)]),
						__props.badgeText ? (openBlock(), createBlock(_sfc_main$18, {
							key: 1,
							label: __props.badgeText,
							"show-dot": false,
							"show-count": false
						}, null, 8, ["label"])) : createCommentVNode("", true)
					]),
					_: 1
				}, 8, [
					"class",
					"label",
					"aria-description",
					"disabled"
				])]),
				_: 1
			}, 8, [
				"selected",
				"accent",
				"rail-visible"
			]);
		};
	}
};
//#endregion
//#region src/controls/ProfileInfoRow.vue
var _hoisted_1$1 = {
	key: 0,
	class: "profile-info-row"
};
var _sfc_main$4 = {
	__name: "ProfileInfoRow",
	props: {
		icon: String,
		label: String,
		value: String
	},
	setup(__props) {
		return (_ctx, _cache) => {
			return __props.value ? (openBlock(), createElementBlock("div", _hoisted_1$1, [createVNode(_sfc_main$15, { name: __props.icon }, null, 8, ["name"]), createBaseVNode("span", null, [createBaseVNode("small", null, toDisplayString(unref(t)(__props.label)), 1), createVNode(_sfc_main$19, { text: __props.value }, null, 8, ["text"])])])) : createCommentVNode("", true);
		};
	}
};
//#endregion
//#region src/controls/display/DropTargetOverlay.vue
var _sfc_main$3 = {
	__name: "DropTargetOverlay",
	props: {
		prompt: String,
		accepted: {
			type: Boolean,
			default: true
		}
	},
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				class: normalizeClass(["drop-target-overlay", { rejected: !__props.accepted }]),
				role: "status"
			}, [createVNode(_sfc_main$15, { name: __props.accepted ? "move-to-inbox" : "cancel" }, null, 8, ["name"]), createBaseVNode("strong", null, toDisplayString(unref(t)(__props.prompt)), 1)], 2);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/controls/display/surfaces.ui.mjs
function header(model, width, height = 60) {
	const actions = model.actions || [];
	const leading = model.back ? 48 : model.icon ? 42 : 12;
	const right = width - 12 - actions.length * 36;
	const nodes = [node("Box", "headerSurface", rect(0, 0, width, height), {
		radius: model.radius || 0,
		background: "surfaceContainerHigh"
	})];
	if (model.back) nodes.push(button("headerBack", rect(8, (height - 32) / 2, 32, 32), model.backLabel || "Back", "chevron-left", { type: "back" }, model.enabled !== false, { iconOnly: true }));
	else if (model.icon) nodes.push(node("Icon", "headerIcon", rect(12, (height - 18) / 2, 18, 18), {
		icon: model.icon,
		color: "action"
	}));
	nodes.push(label("headerTitle", rect(leading, model.subtitle ? 10 : (height - 22) / 2, Math.max(0, right - leading - 8), 22), model.title || "", {
		fontRole: "bodyLarge",
		weight: 600
	}));
	if (model.subtitle) nodes.push(label("headerSubtitle", rect(leading, 34, Math.max(0, right - leading - 8), 16), model.subtitle, {
		fontRole: "secondary",
		color: "secondaryText"
	}));
	actions.forEach((action, index) => nodes.push(button("headerAction_" + index, rect(right + index * 36, (height - 32) / 2, 32, 32), action.label, action.icon, { type: action.command }, action.enabled !== false, { iconOnly: true })));
	return {
		width,
		height,
		nodes
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/controls/catalog.ui.mjs
function initial$3() {
	return {
		text: "Robot Arm",
		description: "Sample asset",
		checked: true,
		mixed: true,
		choice: "model",
		user: "admin",
		date: "2024-02-29T13:14",
		color: "#78a6c4",
		icon: "save",
		treeSelected: "assets",
		split: 50,
		tree: [
			{
				id: "assets",
				title: "Assets",
				depth: 0,
				icon: "folder",
				hasChildren: true,
				expanded: true
			},
			{
				id: "arm",
				title: "Robot Arm",
				depth: 1,
				icon: "box"
			},
			{
				id: "body",
				title: "Robot Body",
				depth: 1,
				icon: "box"
			},
			{
				id: "textures",
				title: "Textures",
				depth: 0,
				icon: "folder",
				hasChildren: true,
				expanded: false
			},
			{
				id: "metal",
				title: "Metal",
				depth: 1,
				icon: "image"
			}
		],
		events: []
	};
}
function transition$3(model, action) {
	const next = Object.assign({}, model, { events: model.events.concat([action]) });
	if (Object.prototype.hasOwnProperty.call(model, action.type) && action.value !== void 0) next[action.type] = action.value;
	if (action.type === "checked") next.mixed = false;
	if (action.type === "treeSelect") next.treeSelected = action.id;
	if (action.type === "treeToggle") next.tree = model.tree.map((record) => record.id === action.id ? Object.assign({}, record, { expanded: !record.expanded }) : record);
	if (action.type === "treeKey") {
		const command = navigate(visibleRows(model.tree), action.id, action.key);
		if (command?.type === "select") next.treeSelected = command.id;
		else if (command) next.tree = model.tree.map((record) => record.id === command.id ? Object.assign({}, record, { expanded: command.type === "expand" }) : record);
	}
	return next;
}
var users = [{
	value: "admin",
	login: "admin",
	label: "Administrator",
	displayName: "Administrator",
	initials: "A",
	groups: ["Artists"],
	primaryGroup: "Artists"
}, {
	value: "test",
	login: "test",
	label: "Test Artist",
	displayName: "Test Artist",
	initials: "TA",
	groups: ["Artists"],
	primaryGroup: "Artists"
}];
var choices = [
	{
		value: "model",
		label: "Model"
	},
	{
		value: "rig",
		label: "Rig"
	},
	{
		value: "publish",
		label: "Publish"
	}
];
function treeRows(model) {
	return visibleRows(model.tree);
}
function row$2(list, record, model, language, state) {
	const keys = {};
	for (const key of [
		"ArrowUp",
		"ArrowDown",
		"ArrowLeft",
		"ArrowRight",
		"Home",
		"End"
	]) keys[key] = {
		type: "treeKey",
		id: record.id,
		key
	};
	return row$3("tree_" + record.id, list.width - 16, record, {
		selected: record.id === model.treeSelected,
		enabled: !["disabled", "loading"].includes(state),
		select: {
			type: "treeSelect",
			id: record.id
		},
		toggle: {
			type: "treeToggle",
			id: record.id
		},
		toggleLabel: translate(record.expanded ? "Collapse section" : "Expand section", language),
		keys
	});
}
//#endregion
//#region ../src/tactic_stream/shared_ui/controls/catalog/variants.mjs
var exampleImage = "data:image/svg+xml," + encodeURIComponent("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"120\" height=\"60\"><path fill=\"#cc6655\" d=\"M0 0h60v60H0z\"/><path fill=\"#5588aa\" d=\"M60 0h60v60H60z\"/><path fill=\"#55aa66\" d=\"M0 0h12v60H0z\"/></svg>");
function sample$1(id, family, kind, properties = {}, height = 36) {
	return {
		id,
		family,
		kind,
		properties,
		height
	};
}
var directKinds = [
	"previewCard",
	"Icon",
	"Grid",
	"Graph",
	"Code",
	"tree",
	"Button",
	"CheckBox",
	"Switch",
	"Field",
	"Area",
	"Choice",
	"DateChoice",
	"UserChoice",
	"Preview",
	"ColorChoice",
	"IconChoice",
	"header",
	"Scroll",
	"Splitter"
];
var examples$1 = [
	sample$1("icon-material", "icons", "Icon", {
		icon: "material-design:account",
		color: "action"
	}, 24),
	sample$1("icon-solid", "icons", "Icon", {
		icon: "fontawesome-solid:user",
		color: "action"
	}, 24),
	sample$1("icon-outline", "icons", "Icon", {
		icon: "fontawesome-outline:user",
		color: "action"
	}, 24),
	sample$1("icon-fluent", "icons", "Icon", {
		icon: "fluent-regular:person",
		color: "action"
	}, 24),
	sample$1("icon-fluent-filled", "icons", "Icon", {
		icon: "fluent-filled:person",
		color: "action"
	}, 24),
	sample$1("icon-small", "icons", "Icon", {
		icon: "save",
		color: "secondaryText"
	}, 16),
	sample$1("icon-large", "icons", "Icon", {
		icon: "save",
		color: "action"
	}, 40),
	sample$1("tree", "lists", "tree", {}, 280),
	sample$1("table", "tables", "Grid", {}, 280),
	sample$1("table-readonly", "tables", "Grid", { readOnly: true }, 280),
	sample$1("graph", "graphs", "Graph", {}, 320),
	sample$1("graph-readonly", "graphs", "Graph", { readOnly: true }, 320),
	sample$1("code", "editors", "Code", { value: "def example():\n    return 42\n" }, 300),
	sample$1("code-readonly", "editors", "Code", {
		value: "def example():\n    return 42\n",
		readOnly: true
	}, 300),
	sample$1("button", "buttons", "Button", {
		text: "Save",
		icon: "save"
	}),
	sample$1("button-primary", "buttons", "Button", {
		text: "Create",
		icon: "add",
		highlighted: true
	}),
	sample$1("button-tonal", "buttons", "Button", {
		text: "Apply",
		tonal: true
	}),
	sample$1("button-danger", "buttons", "Button", {
		text: "Delete",
		icon: "delete",
		destructive: true
	}),
	sample$1("button-filled-danger", "buttons", "Button", {
		text: "Delete",
		icon: "delete",
		destructive: true,
		highlighted: true
	}),
	sample$1("button-icon", "buttons", "Button", {
		text: "Refresh",
		icon: "refresh",
		iconOnly: true
	}),
	sample$1("button-badge-zero", "buttons", "counter", { value: 0 }),
	sample$1("button-badge", "buttons", "counter", { value: 4 }),
	sample$1("button-badge-overflow", "buttons", "counter", { value: 132 }),
	sample$1("button-disclosure", "buttons", "disclosure", { value: false }),
	sample$1("button-preview", "buttons", "previewNavigation", { value: 0 }),
	sample$1("button-send", "buttons", "send", { value: false }),
	sample$1("checkbox", "toggles", "CheckBox", {
		text: "Enabled",
		value: false
	}),
	sample$1("checkbox-checked", "toggles", "CheckBox", {
		text: "Enabled",
		value: true
	}),
	sample$1("checkbox-wrapped", "toggles", "CheckBox", {
		text: "Very long example item title that wraps in a narrow viewport",
		wrapText: true,
		value: true
	}, 64),
	sample$1("checkbox-mixed", "toggles", "CheckBox", {
		text: "Enabled",
		value: true,
		mixed: true
	}),
	sample$1("checkbox-compact", "toggles", "CheckBox", {
		text: "Enabled",
		value: true,
		compact: true
	}),
	sample$1("checkbox-prominent", "toggles", "CheckBox", {
		text: "Enabled",
		value: false,
		prominent: true
	}),
	sample$1("switch-off", "toggles", "Switch", {
		text: "Enabled",
		value: false
	}),
	sample$1("switch-on", "toggles", "Switch", {
		text: "Enabled",
		value: true
	}),
	sample$1("segments", "toggles", "segments", { value: "model" }),
	sample$1("segments-icons", "toggles", "segments", {
		value: "model",
		iconOnly: true
	}),
	sample$1("segments-outline", "toggles", "segments", {
		value: "model",
		outlined: true
	}),
	sample$1("segments-disabled-option", "toggles", "segments", {
		value: "model",
		disabledOption: true,
		dataLabels: true
	}),
	sample$1("field", "text-fields", "Field", {
		value: "Robot Arm",
		label: "Name"
	}),
	sample$1("field-empty", "text-fields", "Field", {
		value: "",
		label: "Name",
		placeholder: "Name"
	}),
	sample$1("field-password", "text-fields", "Field", {
		value: "private example",
		label: "Password",
		password: true
	}),
	sample$1("field-readonly", "text-fields", "Field", {
		value: "Read only",
		label: "Name",
		readOnly: true
	}),
	sample$1("field-error", "text-fields", "Field", {
		value: "Invalid value",
		label: "Name",
		error: true
	}),
	sample$1("field-inline", "text-fields", "Field", {
		value: "Robot Arm",
		label: "Name",
		tableCell: true
	}),
	sample$1("text-area", "text-fields", "Area", {
		value: "First line\nSecond line",
		label: "Description"
	}, 100),
	sample$1("search", "search", "search", { value: "Robot" }),
	sample$1("search-empty", "search", "search", { value: "" }),
	sample$1("search-suggestions", "search", "search", {
		value: "Robot",
		suggestions: true
	}),
	sample$1("choice", "choices", "Choice", { value: "model" }),
	sample$1("choice-empty", "choices", "Choice", { value: "" }),
	sample$1("choice-editable", "choices", "Choice", {
		value: "custom_process",
		editable: true
	}),
	sample$1("choice-disabled-option", "choices", "Choice", {
		value: "model",
		disabledOption: true
	}),
	sample$1("choice-icons", "choices", "Choice", {
		value: "model",
		choiceIcons: true
	}),
	sample$1("choice-status", "choices", "status", { value: "model" }, 28),
	sample$1("packed-choices", "choices", "packedChoices", { value: "" }, 280),
	sample$1("integer", "numbers", "spin", {
		value: 5,
		min: 0,
		max: 10,
		step: 1,
		decimals: 0
	}),
	sample$1("decimal", "numbers", "spin", {
		value: 1.25,
		min: -2,
		max: 3,
		step: .25,
		decimals: 2
	}),
	sample$1("integer-min", "numbers", "spin", {
		value: 0,
		min: 0,
		max: 10,
		step: 1,
		decimals: 0
	}),
	sample$1("integer-max", "numbers", "spin", {
		value: 10,
		min: 0,
		max: 10,
		step: 1,
		decimals: 0
	}),
	sample$1("slider", "numbers", "slider", {
		value: 50,
		min: 0,
		max: 100,
		step: 1
	}, 26),
	sample$1("slider-step", "numbers", "slider", {
		value: 50,
		min: 0,
		max: 100,
		step: 5
	}, 26),
	sample$1("slider-fixed", "numbers", "slider", {
		value: 5,
		min: 5,
		max: 5,
		step: 1
	}, 26),
	sample$1("date", "dates", "DateChoice", {
		value: "2024-02-29",
		includeTime: false
	}),
	sample$1("datetime", "dates", "DateChoice", {
		value: "2024-02-29T13:14",
		includeTime: true
	}),
	sample$1("date-early-year", "dates", "DateChoice", {
		value: "0099-01-01",
		includeTime: false
	}),
	sample$1("date-invalid", "dates", "DateChoice", {
		value: "2023-02-29",
		includeTime: false
	}),
	sample$1("date-empty", "dates", "DateChoice", {
		value: "",
		includeTime: false
	}),
	sample$1("user", "user-choice", "UserChoice", { value: "admin" }),
	sample$1("user-empty", "user-choice", "UserChoice", { value: "" }),
	sample$1("users-multiple", "user-choice", "users", { value: ["admin"] }, 300),
	sample$1("avatar-initials", "identity", "Preview", {
		initials: "A",
		round: true,
		outlined: true,
		accent: "#557f75"
	}, 40),
	sample$1("avatar-two-initials", "identity", "Preview", {
		initials: "TA",
		round: true,
		outlined: true,
		accent: "#557f75"
	}, 40),
	sample$1("avatar-fallback", "identity", "Preview", {
		icon: "person",
		round: true,
		outlined: true,
		accent: "#557f75"
	}, 40),
	sample$1("identity", "identity", "identity", { value: "admin" }, 40),
	sample$1("identity-retired", "identity", "identity", {
		value: "admin",
		retired: true
	}, 40),
	sample$1("identity-emphasized", "identity", "identity", {
		value: "admin",
		emphasized: true,
		avatarSize: 56
	}, 56),
	sample$1("user-group", "identity", "userGroup", { value: "Artists" }, 34),
	sample$1("user-group-compact", "identity", "userGroup", {
		value: "Artists",
		compact: true
	}, 28),
	sample$1("user-group-empty", "identity", "userGroup", { value: "Ungrouped" }, 34),
	sample$1("profile-info", "identity", "profileInfo", { value: "Administrator" }, 40),
	sample$1("color", "pickers", "ColorChoice", { value: "#78a6c4" }),
	sample$1("icon-choice", "pickers", "IconChoice", { value: "save" }),
	sample$1("emoji", "pickers", "emoji", { value: "" }),
	sample$1("image-picker", "pickers", "image", { value: "" }, 220),
	sample$1("accent-presets", "pickers", "presets", { value: "blue" }, 48),
	sample$1("preview-square", "previews", "Preview", {
		initials: "RA",
		accent: "#557f75",
		round: false,
		outlined: false
	}, 96),
	sample$1("preview-round", "previews", "Preview", {
		source: exampleImage,
		round: true
	}, 96),
	sample$1("preview-icon", "previews", "Preview", {
		icon: "image",
		round: false
	}, 96),
	sample$1("preview-card", "previews", "previewCard", { source: exampleImage }, 220),
	sample$1("attachment-image", "previews", "attachment", {
		source: exampleImage,
		extension: "svg"
	}, 220),
	sample$1("attachment-file", "previews", "attachment", {
		extension: "pdf",
		compact: true
	}, 64),
	sample$1("preview-outline", "previews", "Preview", {
		initials: "RA",
		accent: "#557f75",
		round: false,
		outlined: true
	}, 96),
	sample$1("preview-broken", "previews", "Preview", {
		initials: "RA",
		source: "missing-example.png",
		accent: "#557f75",
		round: false
	}, 96),
	sample$1("preview-loading", "previews", "Preview", {
		loading: true,
		source: "pending-preview:example",
		round: false
	}, 96),
	sample$1("preview-photo", "previews", "Preview", {
		source: exampleImage,
		round: false
	}, 96),
	sample$1("preview-contain", "previews", "Preview", {
		source: exampleImage,
		round: false,
		fit: "contain"
	}, 96),
	sample$1("preview-selected", "previews", "Preview", {
		source: exampleImage,
		round: false,
		selected: true
	}, 96),
	sample$1("avatar-photo", "identity", "Preview", {
		source: exampleImage,
		round: true
	}, 40),
	sample$1("chip", "badges", "chip", { value: 4 }, 30),
	sample$1("chip-clickable", "badges", "chip", {
		value: 4,
		clickable: true
	}, 30),
	sample$1("chip-compact", "badges", "chip", {
		value: 4,
		compact: true
	}, 24),
	sample$1("status-chip", "badges", "statusChip", { value: "Ready" }, 24),
	sample$1("status-chip-dense", "badges", "statusChip", {
		value: "Ready",
		dense: true
	}, 20),
	sample$1("status-chip-action", "badges", "statusChip", {
		value: "Ready",
		interactive: true
	}, 24),
	sample$1("reaction", "badges", "reaction", {
		value: false,
		count: 1
	}, 28),
	sample$1("reaction-count", "badges", "reaction", {
		value: false,
		count: 4
	}, 28),
	sample$1("reaction-checked", "badges", "reaction", {
		value: true,
		count: 4
	}, 28),
	sample$1("filter-chip", "badges", "filterChip", { value: false }, 32),
	sample$1("filter-chip-checked", "badges", "filterChip", { value: true }, 32),
	sample$1("filter-chip-subtle", "badges", "filterChip", {
		value: true,
		subtle: true
	}, 32),
	sample$1("filter-chip-marker", "badges", "filterChip", {
		value: true,
		marker: true
	}, 32),
	sample$1("filter-chip-emphasis", "badges", "filterChip", {
		value: true,
		emphasis: 1
	}, filterGeometry(1).height),
	sample$1("tab", "tabs", "tab", { value: false }),
	sample$1("tab-current", "tabs", "tab", { value: true }),
	sample$1("header", "headers", "header", { subtitle: "Description" }, 60),
	sample$1("header-back", "headers", "header", {
		back: true,
		subtitle: "Description"
	}, 60),
	sample$1("header-actions", "headers", "header", { actions: [{
		label: "Refresh",
		icon: "refresh",
		command: "refresh"
	}, {
		label: "Actions",
		icon: "more",
		command: "menu"
	}] }, 60),
	sample$1("editor-panel", "headers", "editorPanel", {}, 160),
	sample$1("configuration-section", "headers", "configurationSection", {}, 160),
	sample$1("section-label", "headers", "sectionLabel", {}, 24),
	sample$1("info-values", "headers", "infoValues", { items: [{
		label: "Type",
		value: "Asset"
	}, {
		label: "Version",
		value: "v003"
	}] }, 16),
	sample$1("field-frame", "headers", "fieldFrame", { value: "Robot Arm" }, 150),
	sample$1("field-frame-required", "headers", "fieldFrame", {
		value: "Robot Arm",
		required: true
	}, 150),
	sample$1("field-frame-error", "headers", "fieldFrame", {
		value: "",
		error: true
	}, 180),
	sample$1("field-frame-readonly", "headers", "fieldFrame", {
		value: "Robot Arm",
		readOnly: true
	}, 180),
	sample$1("list-item", "lists", "listItem", { value: "Example item" }, 72),
	sample$1("list-item-selected", "lists", "listItem", {
		value: "Example item",
		selected: true
	}, 72),
	sample$1("list-item-badge", "lists", "listItem", {
		value: "Example item",
		badge: true
	}, 72),
	sample$1("list-item-long", "lists", "listItem", {
		value: "Very long example item title that wraps in a narrow viewport",
		wrapTitle: true
	}, 100),
	sample$1("menu", "menus", "menu", { value: "" }),
	sample$1("menu-checks", "menus", "menu", {
		value: "",
		checkable: true
	}),
	sample$1("busy", "feedback", "busy", { value: true }, 24),
	sample$1("progress", "feedback", "progress", { value: .5 }, 4),
	sample$1("progress-empty", "feedback", "progress", { value: 0 }, 4),
	sample$1("progress-complete", "feedback", "progress", { value: 1 }, 4),
	sample$1("progress-indeterminate", "feedback", "progress", { value: null }, 4),
	sample$1("loading-overlay", "feedback", "loadingOverlay", {}, 220),
	sample$1("loading-cancellable", "feedback", "loadingOverlay", { cancellable: true }, 220),
	sample$1("empty", "feedback", "empty", { value: "" }, 180),
	sample$1("error-retry", "feedback", "empty", {
		value: "",
		error: true
	}, 220),
	sample$1("drop-target", "drag-files", "drop", {
		value: "",
		accepted: true
	}, 180),
	sample$1("drop-rejected", "drag-files", "drop", {
		value: "",
		accepted: false
	}, 180),
	sample$1("markdown", "typography", "markdown", { value: "# Example\n\n**Bold** and a [link](https://example.org).\n\n- First item\n- Second item" }, 200),
	sample$1("middle-elide", "typography", "elide", { value: "D:/very/long/project/path/to/production/scene-file.ext" }),
	sample$1("setting-row", "scroll-layout", "setting", { value: true }, 100),
	sample$1("flow", "scroll-layout", "flow", { value: "" }, 150),
	sample$1("scroll-vertical", "scroll-layout", "Scroll", {}, 280),
	sample$1("scroll-horizontal", "scroll-layout", "Scroll", { horizontal: true }, 120),
	sample$1("scroll-both", "scroll-layout", "Scroll", { both: true }, 280),
	sample$1("splitter-vertical", "scroll-layout", "Splitter", { value: 50 }, 160),
	sample$1("splitter-horizontal", "scroll-layout", "Splitter", {
		value: 50,
		horizontal: true
	}, 10)
];
function find(id) {
	const result = examples$1.find((example) => example.id === id);
	if (!result) throw Error("Unknown control example: " + id);
	return result;
}
function initial$2(id) {
	const example = find(id);
	return Object.assign(initial$3(), {
		id,
		value: example.properties.value === void 0 ? "" : example.properties.value,
		cells: {},
		graphPositions: [],
		graphSelected: [],
		events: []
	});
}
function transition$2(model, action) {
	const result = transition$3(model, action);
	if (action.type === "cell") result.cells = Object.assign({}, model.cells, { [action.row + ":" + action.column]: action.value });
	if (action.value !== void 0) result.value = action.value;
	if (action.type === "graph" && action.value) {
		if (action.value.type === "selectNodes") result.graphSelected = action.value.identities;
		if (action.value.type === "moveNodes") result.graphPositions = action.value.positions;
	}
	return result;
}
function options(example) {
	return choices.map((choice, index) => Object.assign({}, choice, {
		label: example.properties.dataLabels && index === 0 ? "Enabled" : choice.label,
		translate: !example.properties.dataLabels,
		enabled: !(example.properties.disabledOption && index === 1),
		disabled: !!(example.properties.disabledOption && index === 1),
		icon: example.properties.choiceIcons || example.kind === "segments" ? [
			"view-list",
			"edit",
			"publish"
		][index] : "",
		color: [
			"#ce6868",
			"#7b85ca",
			"#55a9ad"
		][index]
	}));
}
function describe$4(model, width, height, language = "en", state = "idle") {
	const example = find(model.id);
	const tr = (text) => translate(text, language);
	const bounds = rect(20, 64, Math.max(0, width - 40), example.height);
	if (example.kind === "Preview" || example.kind === "Icon") bounds.width = bounds.height;
	if (example.kind === "attachment") {
		bounds.width = Math.min(bounds.width, 320);
		bounds.height = example.properties.compact ? 64 : (bounds.width - 16) / 2 + 65;
	}
	if (example.kind === "chip") bounds.width = 140;
	if (["statusChip", "reaction"].indexOf(example.kind) >= 0) bounds.width = 140;
	if (example.kind === "filterChip") bounds.width = 220;
	if (example.kind === "Splitter" && !example.properties.horizontal) bounds.width = 10;
	if (example.kind === "busy") bounds.width = bounds.height;
	if ([
		"counter",
		"disclosure",
		"emoji",
		"menu",
		"send"
	].indexOf(example.kind) >= 0) bounds.width = 36;
	if (example.kind === "previewNavigation") {
		bounds.width = 40;
		bounds.height = 84;
	}
	if (example.properties.iconOnly && example.kind === "Button") bounds.width = 36;
	const values = Object.assign({}, example.properties, {
		enabled: state !== "disabled" && state !== "loading",
		readOnly: !!example.properties.readOnly || state === "readonly",
		action: { type: "change" },
		value: model.value,
		text: [
			"Field",
			"Area",
			"DateChoice"
		].indexOf(example.kind) >= 0 ? String(model.value) : tr(example.properties.text || ""),
		label: tr(example.properties.label || "Name"),
		placeholder: tr(example.properties.placeholder || ""),
		checked: !!model.value,
		mixed: !!example.properties.mixed && !model.events.length,
		options: example.kind === "UserChoice" ? users : options(example),
		users,
		error: example.properties.error || state === "error",
		selected: example.properties.selected || state === "selected",
		loading: example.properties.loading || state === "loading",
		language
	});
	if (["Preview", "previewCard"].includes(example.kind) && ["empty", "error"].includes(state)) {
		values.source = "";
		if (state === "error") {
			values.initials = "";
			values.icon = "alert";
		}
	}
	if (example.kind === "CheckBox") {
		const indicator = values.prominent ? controls.checkBox.prominentIndicator : values.compact ? controls.checkBox.compactIndicator : controls.checkBox.indicator;
		const spacing = values.compact ? controls.checkBox.compactSpacing : controls.checkBox.spacing;
		values.children = [label("checkLabel", rect(indicator + spacing, 0, Math.max(0, bounds.width - indicator - spacing), bounds.height), values.text, {
			fontRole: values.compact ? "secondary" : "body",
			wrap: !!values.wrapText,
			color: values.enabled ? "primaryText" : "disabledText"
		})];
	}
	let content;
	if (example.kind === "previewCard") content = [node("Box", "sample", bounds, {
		radius: 10,
		clip: true,
		children: [
			node("Preview", "sampleCardImage", rect(0, 0, bounds.width, bounds.height), {
				source: values.source,
				round: false,
				fit: "cover",
				loading: values.loading,
				selected: values.selected
			}),
			node("Box", "sampleCardShade", rect(0, 0, bounds.width, bounds.height), {
				background: "#000000",
				opacity: .68,
				radius: 10
			}),
			label("sampleCardTitle", rect(16, 24, Math.max(0, bounds.width - 32), 36), "Robot Arm", {
				fontRole: "title",
				weight: 600,
				color: "#ffffff"
			}),
			label("sampleCardDescription", rect(16, 68, Math.max(0, bounds.width - 32), 48), tr("Image preview"), {
				wrap: true,
				color: "#ffffff"
			}),
			node("StatusChip", "sampleCardStatus", rect(16, bounds.height - 44, Math.min(140, bounds.width - 32), 28), {
				text: tr("Ready"),
				accent: "action"
			})
		]
	})];
	else if (example.kind === "Scroll") {
		const contentWidth = example.properties.horizontal || example.properties.both ? 900 : bounds.width;
		const scroll = {
			contentHeight: example.properties.horizontal ? 80 : 900,
			children: Array.from({ length: example.properties.horizontal ? 7 : 20 }, (_, index) => label("scrollRow_" + index, rect(example.properties.horizontal ? 8 + index * 120 : index % 2 && example.properties.both ? 500 : 8, example.properties.horizontal ? 8 : index * 40, example.properties.horizontal ? 100 : 280, 32), "Example " + String(index + 1), { fontRole: "body" }))
		};
		if (example.properties.horizontal || example.properties.both) scroll.contentWidth = contentWidth;
		content = [node("Scroll", "sample", bounds, scroll)];
	} else if (example.kind === "Splitter") content = [node("Splitter", "sample", bounds, Object.assign({}, values, {
		text: tr("Size"),
		min: 0,
		max: 100,
		horizontal: !!example.properties.horizontal
	}))];
	else if (example.kind === "tree") content = [node("List", "sample", bounds, {
		source: "treeRows",
		keyField: "id",
		rowHeight: 36
	})];
	else if (example.kind === "Grid") content = [node("Grid", "sample", bounds, Object.assign({}, values, {
		source: "cells",
		text: tr("Table"),
		rowHeaders: Array.from({ length: 50 }, (_, index) => ({ label: String(index + 1) })),
		columnHeaders: choices.map((option) => option.label),
		cellWidth: 160,
		rowHeight: 38,
		labelWidth: 40,
		headerHeight: 32,
		revision: model.events.length
	}))];
	else if (example.kind === "Graph") content = [node("Graph", "sample", bounds, Object.assign({}, values, {
		label: tr("Graph"),
		language,
		nodes: [{
			identity: "a",
			label: "First",
			nodeX: 20,
			nodeY: 20,
			color: "action"
		}, {
			identity: "b",
			label: "Second",
			nodeX: 280,
			nodeY: 140,
			color: "action"
		}].map((record) => Object.assign({}, record, model.graphPositions.find((position) => position.identity === record.identity) || {})),
		selectedNodes: model.graphSelected,
		edges: [{
			from: "a",
			to: "b"
		}],
		action: { type: "graph" },
		selectAction: { type: "graphSelect" },
		moveAction: { type: "graphMove" }
	}))];
	else if (example.kind === "Code") content = [node("Code", "sample", bounds, Object.assign({}, values, {
		text: String(model.value),
		service: "sourceEditor",
		bufferKey: model.id,
		language
	}))];
	else if (example.kind === "header") {
		content = header(Object.assign({}, example.properties, {
			title: tr("Name"),
			subtitle: tr(example.properties.subtitle || ""),
			backLabel: tr("Back"),
			enabled: values.enabled,
			actions: (example.properties.actions || []).map((action) => Object.assign({}, action, {
				label: tr(action.label),
				enabled: values.enabled && action.enabled !== false
			}))
		}), bounds.width, bounds.height);
		content = [node("Box", "sample", bounds, { children: content.nodes })];
	} else content = [directKinds.indexOf(example.kind) >= 0 ? node(example.kind, "sample", bounds, values) : node("View", "sample", bounds, { view: "example" })];
	return {
		width,
		height,
		nodes: [
			label("exampleTitle", rect(20, 16, width - 40, 28), example.id, {
				fontRole: "bodyLarge",
				weight: 600
			}),
			...content,
			label("exampleEvents", rect(20, height - 36, width - 40, 24), String(model.events.length), { fontRole: "secondary" })
		]
	};
}
function row$1(list, record, model, language, state) {
	return row$2(list, record, model, language, state);
}
function cell$1(grid, record, row, column, model, state) {
	const key = row + ":" + column;
	return { nodes: [node("Field", "cell_" + row + "_" + column, rect(0, 0, grid.cellWidth, grid.rowHeight), {
		text: model.cells[key] === void 0 ? String(row + 1) + " / " + String(column + 1) : model.cells[key],
		label: "Name",
		tableCell: true,
		readOnly: grid.readOnly || state === "readonly",
		enabled: state !== "disabled",
		action: {
			type: "cell",
			row,
			column
		}
	})] };
}
function packedOptions(value) {
	return Array.from({ length: 1e3 }, (_, index) => ({
		key: String(index),
		title: "Option " + String(index).padStart(4, "0"),
		icon: index % 3 === 0 ? "folder" : "",
		marker: index % 5 === 0,
		accent: "#55a9ad",
		selected: String(index) === value
	}));
}
//#endregion
//#region src/features/administration/ShowcaseControl.vue
var _hoisted_1 = ["data-example"];
var _sfc_main$2 = {
	__name: "ShowcaseControl",
	props: {
		example: Object,
		value: [
			String,
			Number,
			Boolean,
			Array
		],
		disabled: Boolean,
		readonly: Boolean
	},
	emits: ["event"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const data = computed(() => props.example.properties);
		const choices = computed(() => options(props.example));
		const suggestions = computed(() => data.value.suggestions ? [{
			title: "Robot Arm",
			description: "Example",
			code: "arm"
		}, {
			title: "Robot Body",
			description: "Example",
			code: "body"
		}] : []);
		const image = ref(null);
		const optionsViewport = ref(null), optionTop = ref(0);
		const packed = computed(() => packedOptions(props.value));
		const presets = [{
			value: "blue",
			label: "Blue",
			dark: "#78a6c4",
			light: "#3d7599",
			darkBase: "#292d30",
			lightBase: "#d4dce1"
		}, {
			value: "green",
			label: "Green",
			dark: "#77b398",
			light: "#3d8062",
			darkBase: "#26342e",
			lightBase: "#d9e9df"
		}];
		if (![
			"attachment",
			"segments",
			"spin",
			"slider",
			"search",
			"status",
			"users",
			"identity",
			"emoji",
			"image",
			"presets",
			"chip",
			"tab",
			"menu",
			"progress",
			"busy",
			"empty",
			"drop",
			"markdown",
			"elide",
			"setting",
			"flow",
			"counter",
			"disclosure",
			"previewNavigation",
			"send",
			"packedChoices",
			"statusChip",
			"reaction",
			"filterChip",
			"loadingOverlay",
			"editorPanel",
			"configurationSection",
			"sectionLabel",
			"infoValues",
			"fieldFrame",
			"listItem",
			"userGroup",
			"profileInfo"
		].includes(props.example.kind)) throw Error("Missing catalog brick: " + props.example.kind);
		function change(value) {
			if (!props.disabled && !props.readonly) emit("event", {
				type: "change",
				value
			});
		}
		function activate(type = "activate") {
			if (!props.disabled) emit("event", { type });
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				class: "control-example",
				"data-example": __props.example.id
			}, [__props.example.kind === "attachment" ? (openBlock(), createBlock(_sfc_main$33, {
				key: 0,
				title: "Robot Arm",
				extension: data.value.extension,
				"preview-url": data.value.source || "",
				"size-text": "128 KB",
				compact: !!data.value.compact,
				"web-preview": false,
				disabled: __props.disabled || __props.readonly,
				style: {
					width: "100%",
					height: "100%"
				},
				onActivated: _cache[0] || (_cache[0] = ($event) => activate())
			}, null, 8, [
				"extension",
				"preview-url",
				"compact",
				"disabled"
			])) : __props.example.kind === "segments" ? (openBlock(), createBlock(_sfc_main$20, {
				key: 1,
				"model-value": __props.value,
				options: choices.value,
				label: "Display",
				"icon-only": data.value.iconOnly,
				outlined: data.value.outlined,
				disabled: __props.disabled,
				"onUpdate:modelValue": change
			}, null, 8, [
				"model-value",
				"options",
				"icon-only",
				"outlined",
				"disabled"
			])) : __props.example.kind === "spin" ? (openBlock(), createBlock(_sfc_main$32, {
				key: 2,
				"model-value": __props.value,
				min: data.value.min,
				max: data.value.max,
				step: data.value.step,
				decimals: data.value.decimals,
				label: "Size",
				disabled: __props.disabled,
				readonly: __props.readonly,
				"onUpdate:modelValue": change
			}, null, 8, [
				"model-value",
				"min",
				"max",
				"step",
				"decimals",
				"disabled",
				"readonly"
			])) : __props.example.kind === "slider" ? (openBlock(), createBlock(_sfc_main$21, {
				key: 3,
				"model-value": __props.value,
				min: data.value.min,
				max: data.value.max,
				step: data.value.step,
				label: "Size",
				disabled: __props.disabled || __props.readonly,
				"onUpdate:modelValue": change
			}, null, 8, [
				"model-value",
				"min",
				"max",
				"step",
				"disabled"
			])) : __props.example.kind === "search" ? (openBlock(), createBlock(AppSearchField_default, {
				key: 4,
				"model-value": __props.value,
				label: "Search",
				placeholder: unref(t)("Search"),
				suggestions: suggestions.value,
				disabled: __props.disabled,
				readonly: __props.readonly,
				"onUpdate:modelValue": change,
				onSearch: _cache[1] || (_cache[1] = ($event) => activate("search")),
				onDismiss: _cache[2] || (_cache[2] = ($event) => activate("dismiss")),
				onOpen: _cache[3] || (_cache[3] = ($event) => activate("open")),
				onAccept: _cache[4] || (_cache[4] = ($event) => change($event.title))
			}, null, 8, [
				"model-value",
				"placeholder",
				"suggestions",
				"disabled",
				"readonly"
			])) : __props.example.kind === "packedChoices" ? (openBlock(), createElementBlock("div", {
				key: 5,
				ref_key: "optionsViewport",
				ref: optionsViewport,
				class: "example-options-viewport",
				onScrollPassive: _cache[5] || (_cache[5] = ($event) => optionTop.value = $event.target.scrollTop)
			}, [optionsViewport.value ? (openBlock(), createBlock(QuickFilterOptions_default, {
				key: 0,
				options: packed.value,
				viewport: optionsViewport.value,
				top: optionTop.value,
				height: 280,
				active: "",
				disabled: __props.disabled,
				onActivate: change
			}, null, 8, [
				"options",
				"viewport",
				"top",
				"disabled"
			])) : createCommentVNode("", true)], 544)) : __props.example.kind === "status" ? (openBlock(), createBlock(_sfc_main$34, {
				key: 6,
				value: __props.value,
				options: choices.value,
				disabled: __props.disabled,
				onChange: change
			}, null, 8, [
				"value",
				"options",
				"disabled"
			])) : __props.example.kind === "users" ? (openBlock(), createBlock(_sfc_main$44, {
				key: 7,
				"model-value": __props.value,
				users: unref(users),
				disabled: __props.disabled,
				"onUpdate:modelValue": change
			}, null, 8, [
				"model-value",
				"users",
				"disabled"
			])) : __props.example.kind === "identity" ? (openBlock(), createBlock(_sfc_main$22, {
				key: 8,
				login: "admin",
				"display-name": "Administrator",
				initials: "A",
				"avatar-color": "#557f75",
				retired: data.value.retired,
				emphasized: data.value.emphasized,
				"avatar-size": data.value.avatarSize || 40
			}, null, 8, [
				"retired",
				"emphasized",
				"avatar-size"
			])) : __props.example.kind === "userGroup" ? (openBlock(), createBlock(_sfc_main$23, {
				key: 9,
				title: __props.value,
				compact: data.value.compact
			}, null, 8, ["title", "compact"])) : __props.example.kind === "profileInfo" ? (openBlock(), createBlock(_sfc_main$4, {
				key: 10,
				icon: "person",
				label: "Name",
				value: __props.value
			}, null, 8, ["value"])) : __props.example.kind === "emoji" ? (openBlock(), createBlock(_sfc_main$35, {
				key: 11,
				disabled: __props.disabled,
				onSelected: change
			}, null, 8, ["disabled"])) : __props.example.kind === "image" ? (openBlock(), createBlock(ImagePicker_default, {
				key: 12,
				"model-value": image.value,
				disabled: __props.disabled,
				"fallback-text": "RA",
				"onUpdate:modelValue": _cache[6] || (_cache[6] = ($event) => {
					image.value = $event;
					change($event?.name || "");
				})
			}, null, 8, ["model-value", "disabled"])) : __props.example.kind === "presets" ? (openBlock(), createBlock(_sfc_main$30, {
				key: 13,
				"model-value": __props.value,
				options: presets,
				mode: unref(appearance).mode,
				label: "Colors",
				disabled: __props.disabled,
				"onUpdate:modelValue": change
			}, null, 8, [
				"model-value",
				"mode",
				"disabled"
			])) : __props.example.kind === "chip" ? (openBlock(), createBlock(_sfc_main$18, {
				key: 14,
				label: unref(t)("Status"),
				count: __props.value,
				compact: data.value.compact,
				clickable: data.value.clickable,
				disabled: data.value.clickable ? __props.disabled : void 0,
				onClick: _cache[7] || (_cache[7] = ($event) => activate())
			}, null, 8, [
				"label",
				"count",
				"compact",
				"clickable",
				"disabled"
			])) : __props.example.kind === "statusChip" ? (openBlock(), createBlock(_sfc_main$24, {
				key: 15,
				text: __props.value,
				icon: "check",
				accent: "#55a9ad",
				dense: data.value.dense,
				interactive: data.value.interactive,
				disabled: __props.disabled,
				onClick: _cache[8] || (_cache[8] = ($event) => activate())
			}, null, 8, [
				"text",
				"dense",
				"interactive",
				"disabled"
			])) : __props.example.kind === "reaction" ? (openBlock(), createBlock(_sfc_main$10, {
				key: 16,
				emoji: "👍",
				count: data.value.count,
				checked: __props.value,
				disabled: __props.disabled,
				onClick: _cache[9] || (_cache[9] = ($event) => change(!__props.value))
			}, null, 8, [
				"count",
				"checked",
				"disabled"
			])) : __props.example.kind === "filterChip" ? (openBlock(), createBlock(QuickFilterChip_default, {
				key: 17,
				style: {
					"width": "100%",
					"height": "100%"
				},
				text: "Example",
				icon: "filter",
				checked: __props.value,
				subtle: data.value.subtle,
				"show-accent-marker": data.value.marker,
				emphasis: data.value.emphasis,
				disabled: __props.disabled,
				onClick: _cache[10] || (_cache[10] = ($event) => change(!__props.value))
			}, null, 8, [
				"checked",
				"subtle",
				"show-accent-marker",
				"emphasis",
				"disabled"
			])) : __props.example.kind === "loadingOverlay" ? (openBlock(), createBlock(_sfc_main$43, {
				key: 18,
				message: "Loading…",
				cancellable: data.value.cancellable,
				disabled: __props.disabled,
				onCancel: _cache[11] || (_cache[11] = ($event) => activate("cancel"))
			}, null, 8, ["cancellable", "disabled"])) : __props.example.kind === "editorPanel" ? (openBlock(), createBlock(_sfc_main$9, {
				key: 19,
				title: "Name",
				description: "Description",
				icon: "settings"
			}, {
				default: withCtx(() => [..._cache[21] || (_cache[21] = [createBaseVNode("div", { class: "example-body" }, "Example", -1)])]),
				_: 1
			})) : __props.example.kind === "configurationSection" ? (openBlock(), createBlock(_sfc_main$8, {
				key: 20,
				title: "Name",
				description: "Description",
				"fill-content-height": ""
			}, {
				default: withCtx(() => [..._cache[22] || (_cache[22] = [createBaseVNode("div", { class: "example-body" }, "Example", -1)])]),
				_: 1
			})) : __props.example.kind === "sectionLabel" ? (openBlock(), createBlock(_sfc_main$7, {
				key: 21,
				text: "Display"
			})) : __props.example.kind === "infoValues" ? (openBlock(), createBlock(_sfc_main$36, {
				key: 22,
				items: data.value.items
			}, null, 8, ["items"])) : __props.example.kind === "fieldFrame" ? (openBlock(), createBlock(_sfc_main$6, {
				key: 23,
				title: "Name",
				"field-name": "name",
				description: "Description",
				icon: "edit",
				required: data.value.required,
				readonly: __props.readonly || data.value.readOnly,
				error: data.value.error ? "Invalid value" : ""
			}, {
				default: withCtx(() => [createVNode(_sfc_main$25, {
					"model-value": __props.value,
					label: "Name",
					disabled: __props.disabled,
					readonly: __props.readonly || data.value.readOnly,
					"error-state": data.value.error,
					"onUpdate:modelValue": change
				}, null, 8, [
					"model-value",
					"disabled",
					"readonly",
					"error-state"
				])]),
				_: 1
			}, 8, [
				"required",
				"readonly",
				"error"
			])) : __props.example.kind === "listItem" ? (openBlock(), createBlock(_sfc_main$5, {
				key: 24,
				text: __props.value,
				description: "Description",
				icon: "folder",
				selected: data.value.selected,
				"wrap-title": data.value.wrapTitle,
				"badge-text": data.value.badge ? "4" : "",
				disabled: __props.disabled,
				onClick: _cache[12] || (_cache[12] = ($event) => activate())
			}, null, 8, [
				"text",
				"selected",
				"wrap-title",
				"badge-text",
				"disabled"
			])) : __props.example.kind === "tab" ? (openBlock(), createBlock(_sfc_main$26, {
				key: 25,
				label: "Display",
				checked: __props.value,
				disabled: __props.disabled,
				onClick: _cache[13] || (_cache[13] = ($event) => change(!__props.value))
			}, null, 8, ["checked", "disabled"])) : __props.example.kind === "menu" ? (openBlock(), createBlock(_sfc_main$16, {
				key: 26,
				label: "Actions",
				disabled: __props.disabled,
				overlay: ""
			}, {
				default: withCtx(() => [
					createVNode(_sfc_main$37, {
						label: "Refresh",
						icon: "refresh",
						onClick: _cache[14] || (_cache[14] = ($event) => activate("refresh"))
					}),
					createVNode(_sfc_main$37, {
						label: "Enabled",
						checked: data.value.checkable ? !!__props.value : void 0,
						onClick: _cache[15] || (_cache[15] = ($event) => change(!__props.value))
					}, null, 8, ["checked"]),
					createVNode(_sfc_main$37, {
						label: "Delete",
						icon: "delete",
						disabled: ""
					})
				]),
				_: 1
			}, 8, ["disabled"])) : __props.example.kind === "progress" ? (openBlock(), createBlock(AppProgress_default, {
				key: 27,
				label: "Progress",
				value: __props.value === null ? void 0 : __props.value
			}, null, 8, ["value"])) : __props.example.kind === "busy" ? (openBlock(), createBlock(BusyIndicator_default, {
				key: 28,
				running: __props.value && !__props.disabled
			}, null, 8, ["running"])) : __props.example.kind === "empty" ? (openBlock(), createBlock(_sfc_main$27, {
				key: 29,
				error: data.value.error,
				icon: data.value.error ? "warning" : "info",
				title: data.value.error ? "Error" : "No records yet",
				message: "Description",
				action: data.value.error ? {
					label: "Retry",
					icon: "refresh",
					command: "retry",
					disabled: __props.disabled
				} : null,
				onAction: activate
			}, null, 8, [
				"error",
				"icon",
				"title",
				"action"
			])) : __props.example.kind === "drop" ? (openBlock(), createBlock(_sfc_main$3, {
				key: 30,
				accepted: data.value.accepted,
				prompt: data.value.accepted ? "Drop files here" : "Unsupported file type"
			}, null, 8, ["accepted", "prompt"])) : __props.example.kind === "markdown" ? (openBlock(), createBlock(_sfc_main$38, {
				key: 31,
				"document-key": "example",
				text: __props.value,
				onLink: _cache[16] || (_cache[16] = ($event) => activate("link"))
			}, null, 8, ["text"])) : __props.example.kind === "elide" ? (openBlock(), createBlock(_sfc_main$19, {
				key: 32,
				text: __props.value
			}, null, 8, ["text"])) : __props.example.kind === "setting" ? (openBlock(), createBlock(_sfc_main$31, {
				key: 33,
				"control-id": "exampleSetting",
				title: "Enabled",
				description: "Description"
			}, {
				default: withCtx(() => [createVNode(_sfc_main$28, {
					id: "exampleSetting",
					"model-value": __props.value,
					label: "Enabled",
					disabled: __props.disabled,
					"onUpdate:modelValue": change
				}, null, 8, ["model-value", "disabled"])]),
				_: 1
			})) : __props.example.kind === "flow" ? (openBlock(), createBlock(_sfc_main$39, {
				key: 34,
				"minimum-cell-width": 120
			}, {
				default: withCtx(() => [(openBlock(true), createElementBlock(Fragment, null, renderList(choices.value, (option) => {
					return openBlock(), createBlock(_sfc_main$14, {
						key: option.value,
						label: option.label,
						disabled: __props.disabled,
						onClick: ($event) => change(option.value)
					}, null, 8, [
						"label",
						"disabled",
						"onClick"
					]);
				}), 128))]),
				_: 1
			})) : __props.example.kind === "counter" ? (openBlock(), createBlock(_sfc_main$14, {
				key: 35,
				icon: "comment",
				"icon-only": "",
				label: "Notes",
				"badge-count": __props.value,
				"badge-color": "var(--primary)",
				style: normalizeStyle({ color: __props.value > 0 ? "var(--primary)" : "var(--muted)" }),
				disabled: __props.disabled,
				onClick: _cache[17] || (_cache[17] = ($event) => activate())
			}, null, 8, [
				"badge-count",
				"style",
				"disabled"
			])) : __props.example.kind === "disclosure" ? (openBlock(), createBlock(_sfc_main$40, {
				key: 36,
				expanded: __props.value,
				identity: "sample",
				"has-children": "",
				disabled: __props.disabled,
				onClick: _cache[18] || (_cache[18] = ($event) => change(!__props.value))
			}, null, 8, ["expanded", "disabled"])) : __props.example.kind === "previewNavigation" ? (openBlock(), createBlock(_sfc_main$11, {
				key: 37,
				label: "Next",
				disabled: __props.disabled,
				onClick: _cache[19] || (_cache[19] = ($event) => activate())
			}, null, 8, ["disabled"])) : __props.example.kind === "send" ? (openBlock(), createBlock(_sfc_main$14, {
				key: 38,
				label: __props.value ? "Sending" : "Send",
				icon: "send",
				compact: "",
				highlighted: "",
				disabled: __props.disabled || __props.value,
				onClick: _cache[20] || (_cache[20] = ($event) => change(true))
			}, null, 8, ["label", "disabled"])) : createCommentVNode("", true)], 8, _hoisted_1);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/showcase.variants.mjs
var examples = examples$1;
var initial$1 = initial$2;
var transition$1 = transition$2;
function available(family) {
	return examples.filter((example) => example.family === family);
}
function title(id, language) {
	return {
		"preview-round": ["Round photo", "Круглое фото"],
		"preview-square": ["Square initials", "Квадратное с инициалами"],
		"preview-outline": ["Outlined preview", "Превью с обводкой"],
		"preview-photo": ["Square photo · crop", "Квадратное фото · обрезка"],
		"preview-contain": ["Fit whole image", "Изображение целиком"],
		"preview-icon": ["Fallback icon", "Иконка без изображения"],
		"preview-loading": ["Loading image", "Загрузка изображения"],
		"preview-selected": ["Selected image", "Выбранное изображение"],
		"preview-broken": ["Failed image", "Ошибка изображения"],
		"preview-card": ["Image behind card content", "Изображение на фоне карточки"],
		"attachment-image": ["Image attachment", "Вложение с изображением"],
		"attachment-file": ["File attachment", "Файловое вложение"]
	}[id]?.[language === "ru" ? 1 : 0] || id.replace(/-/g, " ");
}
function describe$3(model, width, language, state) {
	const example = find(model.id);
	const scene = describe$4(model, width + 40, example.height + 116, language, state);
	scene.nodes = scene.nodes.filter((item) => !["exampleTitle", "exampleEvents"].includes(item.id)).map((item) => Object.assign({}, item, {
		x: item.x - 20,
		y: item.y - 64
	}));
	return scene;
}
function sample(model, width, language) {
	const example = find(model.variant);
	const height = example.height;
	const scene = describe$3(model.variantModel, width, language, model.state);
	return {
		height,
		nodes: [node("View", "showcaseVariantPreview", rect(0, 0, width, height), {
			view: "showcaseVariant",
			model: model.variantModel,
			state: model.state,
			language
		})],
		code: "import * as Variants from './controls/catalog/variants.mjs';\n\n// Native/Vue named port: ShowcaseControl; local events: Variants.transition.\n// Port example: " + JSON.stringify(example) + "\n(" + JSON.stringify(scene, null, 2) + ")"
	};
}
//#endregion
//#region src/features/administration/ShowcaseVariant.vue
var _sfc_main$1 = {
	__name: "ShowcaseVariant",
	props: { frameNode: Object },
	emits: ["event"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const model = computed(() => props.frameNode.model);
		const state = computed(() => props.frameNode.state);
		const language = computed(() => props.frameNode.language);
		const emit = __emit;
		const models = computed(() => ({
			cells: model.value.id.startsWith("table") ? Array.from({ length: 50 }, () => [
				{},
				{},
				{}
			]) : [],
			treeRows: treeRows(model.value)
		}));
		const scene = computed(() => describe$3(model.value, props.frameNode.width, language.value, state.value));
		function dispatch(action) {
			emit("event", {
				type: props.frameNode.gallery ? "galleryEvent" : "variantEvent",
				id: props.frameNode.gallery,
				value: action
			});
		}
		const views = computed(() => ({ example: {
			component: _sfc_main$2,
			props: {
				example: find(model.value.id),
				value: model.value.value,
				disabled: ["disabled", "loading"].includes(state.value),
				readonly: state.value === "readonly",
				onEvent: dispatch
			}
		} }));
		return (_ctx, _cache) => {
			return openBlock(), createBlock(_sfc_main$29, {
				scene: scene.value,
				models: models.value,
				views: views.value,
				"describe-row": (list, record) => row$1(list, record, model.value, language.value, state.value),
				"describe-cell": (grid, record, row, column) => cell$1(grid, record, row, column, model.value, state.value),
				onEvent: dispatch
			}, null, 8, [
				"scene",
				"models",
				"views",
				"describe-row",
				"describe-cell"
			]);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/controls/showcase.examples.mjs
function describe$2(model, family, width, language) {
	const tr = (text) => translate(text, language), nodes = [];
	const enabled = !["disabled", "readonly"].includes(model.state);
	const text = model.state === "long" ? "A much longer component label / Длинное название компонента" : model.text;
	const flags = {
		enabled: model.state !== "disabled",
		readOnly: model.state === "readonly",
		error: model.state === "error"
	};
	let y = 0, example = null;
	function add(item) {
		nodes.push(item);
		if (!example && !["Label", "Box"].includes(item.kind)) example = item;
	}
	function caption(title) {
		add(label("sampleCaption_" + y, rect(0, y, width, 24), tr(title), {
			fontRole: "section",
			weight: 600,
			role: "heading",
			level: 3
		}));
		y += 32;
	}
	function field(kind, id, properties, height = 36) {
		add(node(kind, id, rect(0, y, Math.min(width, 440), height), properties));
		y += height + 16;
	}
	if (family === "typography") {
		const roles = [
			"headline",
			"hero",
			"heading",
			"title",
			"bodyLarge",
			"body",
			"secondary",
			"caption"
		];
		for (const role of roles) {
			const h = Math.max(32, lineHeights[role] + 12);
			add(label("type_" + role, rect(0, y, width, h), role === "caption" ? "Caption · 0123456789" : text, {
				fontRole: role,
				weight: [
					"headline",
					"hero",
					"title"
				].includes(role) ? 600 : 400,
				role: family === "headers" ? "heading" : void 0,
				level: roles.indexOf(role) + 1
			}));
			y += h;
			add(label("typeToken_" + role, rect(0, y, width, 18), role + " · " + textStyles[role] + " px / " + lineHeights[role] + " px", {
				fontRole: "caption",
				color: "secondaryText"
			}));
			y += 32;
		}
		example = nodes[0];
	} else if (family === "headers") {
		caption("Section heading");
		add(label("sampleHeading", rect(0, y, width, 36), text, {
			fontRole: "hero",
			weight: 600,
			role: "heading",
			level: 2
		}));
		y += 44;
		add(label("sampleSubtitle", rect(0, y, width, 28), tr("Description"), { color: "secondaryText" }));
		y += 64;
		caption("Panel heading");
		add(node("Box", "samplePanelHeader", rect(0, y, width, 72), {
			background: "surfaceContainerLow",
			radius: 0,
			children: [
				node("Icon", "sampleHeadingIcon", rect(12, 18, 24, 24), {
					icon: "folder",
					color: "contentAccent"
				}),
				label("samplePanelTitle", rect(48, 8, Math.max(0, width - 100), 28), text, {
					fontRole: "title",
					weight: 600,
					role: "heading",
					level: 3
				}),
				label("samplePanelSubtitle", rect(48, 38, Math.max(0, width - 100), 20), tr("Description"), {
					fontRole: "secondary",
					color: "secondaryText"
				}),
				button("sampleHeadingAction", rect(Math.max(0, width - 44), 16, 36, 36), tr("Refresh"), "refresh", { type: "demo-header" }, enabled, { iconOnly: true })
			]
		}));
		y += 92;
		example = nodes.find((n) => n.id === "sampleHeading");
	} else if (family === "colors") {
		const roles = [
			"workspace",
			"panel",
			"surfaceContainerLowest",
			"surfaceContainerLow",
			"surfaceContainerHigh",
			"tableHeader",
			"contentSelection",
			"action",
			"green",
			"yellow",
			"error",
			"secondaryText"
		];
		const columns = Math.max(1, Math.floor(width / 220)), cell = width / columns;
		roles.forEach((role, i) => {
			const x = i % columns * cell, top = Math.floor(i / columns) * 64;
			add(node("Box", "color_" + role, rect(x, top, 40, 40), {
				background: role,
				radius: 6,
				border: "outlineVariant"
			}));
			add(label("colorName_" + role, rect(x + 52, top, cell - 60, 40), role, {
				fontRole: "secondary",
				wrap: true
			}));
		});
		y = Math.ceil(roles.length / columns) * 64;
		example = nodes[0];
	} else if (family === "buttons") {
		const w = Math.min(200, (width - 12) / 2);
		[
			[
				"Save",
				"save",
				{ highlighted: true }
			],
			[
				"Cancel",
				"close",
				{}
			],
			[
				"Delete",
				"delete",
				{ destructive: true }
			],
			[
				"Help",
				"help",
				{}
			]
		].forEach(([title, icon, options], i) => {
			add(button("sampleButton_" + i, rect(i % 2 * (w + 12), Math.floor(i / 2) * 52, w, 36), tr(title), icon, { type: "demo-" + title }, enabled, options));
		});
		y = 112;
		add(button("sampleIconButton", rect(0, y, 36, 36), tr("Refresh"), "refresh", { type: "demo-refresh" }, enabled, { iconOnly: true }));
		y += 52;
	} else if (family === "toggles") {
		field("CheckBox", "sampleCheckbox", {
			text: tr("Enabled"),
			checked: model.checked,
			enabled,
			action: { type: "checked" }
		});
		field("CheckBox", "sampleMixed", {
			text: tr("Selection"),
			checked: true,
			mixed: true,
			enabled,
			action: { type: "checked" }
		});
		field("Switch", "sampleSwitch", {
			text: tr("Notifications"),
			checked: model.checked,
			enabled,
			action: { type: "checked" }
		});
	} else if (family === "text-fields" || family === "numbers") {
		caption(family === "numbers" ? "Number" : "Name");
		field("Field", "sampleField", Object.assign({}, flags, {
			text: family === "numbers" ? model.number : text,
			label: tr("Name"),
			inputMode: family === "numbers" ? "decimal" : "text",
			action: { type: family === "numbers" ? "number" : "text" }
		}));
		if (family === "text-fields") {
			caption("Description");
			field("Area", "sampleArea", Object.assign({}, flags, {
				text: model.area,
				label: tr("Description"),
				action: { type: "area" }
			}), 100);
		}
	} else if (family === "choices") {
		caption("Process");
		field("Choice", "sampleChoice", {
			value: model.choice,
			options: choices,
			label: tr("Process"),
			enabled,
			action: { type: "choice" }
		});
	} else if (family === "dates") {
		caption("Start date");
		field("DateChoice", "sampleDate", Object.assign({}, flags, {
			text: model.date,
			language,
			label: tr("Start date"),
			action: { type: "date" },
			commitAction: { type: "date" }
		}));
	} else if (family === "user-choice") {
		caption("Assigned to");
		field("UserChoice", "sampleUser", {
			value: model.user,
			options: users,
			label: tr("Assigned to"),
			enabled,
			action: { type: "user" }
		});
	} else if (family === "pickers") {
		caption("Color");
		field("ColorChoice", "sampleColor", {
			value: model.color,
			text: tr("Color"),
			enabled,
			action: { type: "color" }
		});
		caption("Icon");
		field("IconChoice", "sampleIcon", {
			value: model.icon,
			enabled,
			action: { type: "icon" }
		});
	} else if (family === "icons") {
		const icons = [
			"save",
			"refresh",
			"search",
			"help",
			"person",
			"groups",
			"calendar",
			"folder",
			"table",
			"note",
			"workflow",
			"extension"
		];
		const columns = Math.max(1, Math.floor(width / 116)), cell = width / columns;
		icons.forEach((icon, i) => {
			const x = i % columns * cell, top = Math.floor(i / columns) * 92;
			add(node("Icon", "sampleIcon_" + i, rect(x + 10, top, 28, 28), {
				icon,
				color: "contentAccent"
			}));
			add(label("sampleIconName_" + i, rect(x, top + 36, cell - 8, 28), icon, { fontRole: "caption" }));
		});
		y = Math.ceil(icons.length / columns) * 92;
	} else if (family === "badges") {
		caption("Semantic colors");
		const colors = [
			"action",
			"cyan",
			"green",
			"yellow",
			"error",
			"secondaryText"
		];
		const columns = Math.max(1, Math.min(4, Math.floor((width + 12) / 148))), w = Math.min(140, (width - (columns - 1) * 12) / columns);
		colors.forEach((accent, i) => add(node("StatusChip", "sampleBadge_" + i, rect(i % columns * (w + 12), y + Math.floor(i / columns) * 40, w, 24), {
			text: model.state === "long" ? text : accent,
			accent,
			enabled,
			icon: i === 0 ? "clipboard-check" : ""
		})));
		y += Math.ceil(colors.length / columns) * 40 + 16;
		caption("Sizes and icons");
		add(node("StatusChip", "sampleBadgeNormal", rect(0, y, Math.min(width, 140), 24), {
			text: tr("Ready"),
			accent: "green",
			enabled
		}));
		y += 40;
		add(node("StatusChip", "sampleBadgeDense", rect(0, y, Math.min(width, 140), 20), {
			text: tr("Ready"),
			accent: "green",
			dense: true,
			icon: "clipboard-check",
			enabled
		}));
		y += 48;
		caption("Counters");
		for (const [i, count] of [
			0,
			1,
			125
		].entries()) add(node("SummaryChip", "sampleCounter_" + i, rect(i % columns * (w + 12), y + Math.floor(i / columns) * 44, w, 32), {
			text: tr("Notes"),
			count,
			icon: "note",
			accent: "action",
			enabled,
			action: { type: "demo-counter-" + count }
		}));
		y += Math.ceil(3 / columns) * 44 + 16;
	} else if (family === "tabs") {
		field("Segmented", "sampleTabs", {
			label: tr("Display"),
			value: model.tab,
			enabled,
			options: [
				{
					value: "overview",
					label: tr("Overview")
				},
				{
					value: "details",
					label: tr("Details")
				},
				{
					value: "activity",
					label: tr("Activity")
				}
			],
			action: { type: "tab" }
		});
		add(label("sampleTabValue", rect(0, y, width, 28), model.tab, { color: "secondaryText" }));
		y += 40;
	} else if (family === "lists") {
		caption("List");
		for (const [i, key] of [
			"assets",
			"shots",
			"tasks"
		].entries()) {
			const row = listAction("sampleList_" + key, rect(0, y, width, 56), key[0].toUpperCase() + key.slice(1), [
				"box",
				"film",
				"clipboard-check"
			][i], {
				type: "row",
				value: key
			}, enabled, {
				selected: model.row === key,
				endInset: 64
			});
			row.children.push(node("StatusChip", "sampleListCount_" + key, rect(Math.max(0, width - 60), 16, 48, 24), {
				text: String([
					12,
					8,
					24
				][i]),
				accent: "secondaryText",
				enabled: true
			}));
			add(row);
			y += 60;
		}
		y += 20;
		caption("Two-line list");
		for (const [i, title] of [
			"Model",
			"Rig",
			"Publish"
		].entries()) {
			const row = listAction("sampleDetailRow_" + i, rect(0, y, width, 60), title, "clipboard-check", {
				type: "row",
				value: title
			}, enabled, { selected: model.row === title });
			row.children.find((n) => n.kind === "Label").height = 28;
			row.children.push(label("sampleDetailSubtitle_" + i, rect(34, 30, Math.max(0, width - 46), 22), tr("Description"), {
				fontRole: "secondary",
				color: "secondaryText"
			}));
			add(row);
			y += 64;
		}
	} else if (family === "charts") for (const type of [
		"line",
		"bar",
		"donut"
	]) {
		caption(type === "line" ? "Line chart" : type === "bar" ? "Bar chart" : "Donut chart");
		const scene = describe$5({
			type,
			labels: [
				"Mon",
				"Tue",
				"Wed",
				"Thu",
				"Fri"
			],
			values: [
				4,
				8,
				5,
				12,
				9
			]
		}, "sampleChart_" + type, width, 220, language);
		add(node("Box", "sampleChartBox_" + type, rect(0, y, width, 220), {
			background: "transparent",
			clip: false,
			children: scene.nodes
		}));
		y += 244;
	}
	const properties = {};
	if (example) {
		for (const key of Object.keys(example)) if (![
			"kind",
			"id",
			"x",
			"y",
			"width",
			"height",
			"fontSize"
		].includes(key)) {
			if (key !== "children" || example.children.length) properties[key] = example[key];
		}
	}
	const code = family === "charts" ? "import { describe } from './controls/charts/chart.ui.mjs';\n\ndescribe({ type: 'line', labels: ['Mon', 'Tue', 'Wed'], values: [4, 8, 5] },\n  'chart', 600, 220, 'en');" : example ? `import { node, rect } from './core/frame.mjs';\n\nnode(${JSON.stringify(example.kind)}, 'example',\n  rect(0, 0, ${Math.round(example.width)}, ${Math.round(example.height)}),\n  ${JSON.stringify(properties, null, 2)}\n);` : "";
	return {
		nodes,
		height: y,
		code
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/showcase.examples.mjs
var families$1 = [
	"search",
	"identity",
	"menus",
	"popups",
	"feedback",
	"tables",
	"scroll-layout",
	"previews",
	"drag-files",
	"editors",
	"graphs",
	"input-runtime",
	"domain-fragments"
];
examples$1.find((row) => row.kind === "Preview" && String(row.properties.source).startsWith("data:"))?.properties.source;
var tableRows = Array.from({ length: 100 }, (_, i) => ({
	selected: false,
	name: "Object " + (i + 1),
	value: String(i * 10)
}));
function models(model) {
	return { sampleCells: model.family !== "tables" || model.state === "empty" ? [] : tableRows };
}
function cell(grid, record, row, column, model, language = "en") {
	const key = row + ":" + column;
	return { nodes: [node(column === 0 ? "CheckBox" : "Field", "sampleCell_" + key, rect(0, 0, grid.cellWidth, grid.rowHeight), {
		text: column === 0 ? "" : model.cells[key] === void 0 ? column === 1 ? "Object " + (row + 1) : String(row * 10) : String(model.cells[key]),
		checked: model.cells[key] === void 0 ? model.state === "selected" && row === 0 : !!model.cells[key],
		label: translate(column === 0 ? "Selected" : "Value", language),
		tableCell: true,
		enabled: grid.enabled && !grid.readOnly,
		readOnly: grid.readOnly,
		action: {
			type: "sampleCell",
			row,
			column
		}
	})] };
}
function describe$1(model, family, width, language) {
	const tr = (text) => translate(text, language), nodes = [], enabled = ![
		"disabled",
		"readonly",
		"loading"
	].includes(model.state), flags = {
		enabled: !["disabled", "loading"].includes(model.state),
		readOnly: model.state === "readonly",
		error: model.state === "error"
	}, h = model.state === "long" ? 64 : 36;
	let y = 0;
	function add(kind, id, height, props, w = width) {
		nodes.push(node(kind, id, rect(0, y, w, height), props));
		y += height + 16;
	}
	function title$1(text) {
		add("Label", "sampleTitle_" + y, 28, {
			text: tr(text),
			fontRole: "section",
			weight: 600
		});
	}
	function action(id, text, type, value) {
		nodes.push(button(id, rect(0, y, Math.min(width, 240), 36), tr(text), "", {
			type,
			value
		}, enabled));
		y += 52;
	}
	if (model.state === "loading" && !["search", "feedback"].includes(family)) add("Progress", "sampleLoading", 4, {
		text: tr("Loading"),
		indeterminate: true
	});
	if (model.state === "error" && family !== "feedback") add("Label", "sampleError", 40, {
		text: tr("Something went wrong"),
		color: "error",
		role: "alert",
		wrap: true
	});
	if (family === "search") {
		title$1("Search suggestions");
		const rows = model.state === "empty" || model.state === "loading" ? [] : [
			"Robot Arm",
			"Robot Body",
			"Workshop"
		].filter((text) => text.toLowerCase().includes(model.search.toLowerCase())).map((text, i) => ({
			title: text,
			description: tr("Example"),
			code: String(i)
		}));
		add("Search", "sampleSearch", 44, Object.assign({}, flags, {
			text: model.search,
			placeholder: tr("Search objects"),
			label: tr("Search objects"),
			suggestions: rows,
			errorText: model.state === "error" ? tr("Search failed") : "",
			action: { type: "search" },
			acceptAction: { type: "searchAccept" },
			commitAction: { type: "searchSubmit" }
		}));
		if (model.state === "loading") add("Progress", "sampleSearchPending", 4, {
			text: tr("Loading"),
			indeterminate: true
		});
		add("Label", "sampleSearchCount", 28, {
			text: String(rows.length) + " · " + tr("Search suggestions"),
			color: "secondaryText"
		});
	} else if (family === "identity") {
		for (const [login, name, initials, retired, emphasized] of [
			[
				"admin",
				"Administrator",
				"A",
				false,
				true
			],
			[
				"vfx_anna",
				model.state === "long" ? model.text.repeat(4) : "Anna",
				"VA",
				false,
				false
			],
			[
				"archived",
				"Retired",
				"AR",
				true,
				false
			]
		]) add("Identity", "sampleIdentity_" + login, 52, {
			text: tr(name),
			login,
			initials,
			accent: "action",
			retired,
			emphasized,
			opacity: model.state === "disabled" ? .5 : 1
		});
		add("UserChoice", "sampleIdentityChoice", 36, {
			value: model.user,
			options: [{
				value: "admin",
				label: "Administrator",
				login: "admin"
			}, {
				value: "vfx_anna",
				label: "Anna",
				login: "vfx_anna"
			}],
			enabled,
			action: { type: "user" },
			label: tr("User")
		});
	} else if (family === "menus") {
		title$1("Context menu");
		add("View", "sampleMenu", 36, {
			view: "showcaseMenu",
			text: tr("Open menu"),
			enabled,
			checked: model.menuChecked,
			language,
			action: { type: "sampleMenu" },
			actions: [
				{
					title: tr("Actions"),
					header: true,
					translate: false
				},
				{
					title: tr("Edit"),
					command: "edit",
					icon: "edit",
					translate: false
				},
				{
					title: tr("Selected"),
					command: "toggle",
					checked: model.menuChecked,
					translate: false
				},
				{ separator: true },
				{
					title: tr("More"),
					children: [{
						title: tr("Refresh"),
						command: "refresh",
						icon: "refresh",
						translate: false
					}],
					translate: false
				},
				{
					title: tr("Delete"),
					command: "delete",
					icon: "delete",
					enabled: false,
					translate: false
				}
			].filter((row) => model.state !== "empty").concat(model.state === "empty" ? [{
				title: tr("No results"),
				enabled: false,
				translate: false
			}] : [])
		}, Math.min(width, 240));
		add("Label", "sampleMenuResult", 40, {
			text: model.last || tr("Choose an action"),
			wrap: true
		});
	} else if (family === "popups") {
		title$1("Confirmation");
		action("sampleOpenDialog", "Open dialog", "sampleDialogOpen");
		add("View", "sampleDialog", 0, {
			view: "showcaseDialog",
			text: tr("Confirmation"),
			message: model.state === "empty" ? "" : model.state === "long" ? model.text.repeat(8) : tr("Changes stay in this example."),
			open: model.dialogOpen,
			popupWidth: 440,
			cancelText: tr("Cancel"),
			acceptText: tr("Apply"),
			enabled,
			language,
			error: flags.error,
			action: { type: "sampleDialog" }
		});
		add("Label", "sampleDialogResult", 36, {
			text: model.last || tr("No changes"),
			wrap: true
		});
	} else if (family === "feedback") {
		title$1("Progress");
		add("Progress", "sampleProgress", 4, {
			text: tr("Progress"),
			value: model.progress / 100,
			indeterminate: model.state === "loading"
		});
		add("Label", "sampleProgressValue", 28, { text: String(model.progress) + "%" });
		action("sampleAdvance", "Continue", "sampleAdvance");
		add("Empty", "sampleEmpty", 220, {
			text: tr(model.state === "error" ? "Something went wrong" : "No results"),
			message: tr("Changes stay in this example."),
			error: flags.error,
			icon: flags.error ? "alert" : "search",
			actionText: tr("Retry"),
			actionIcon: "refresh",
			action: { type: "sampleRetry" },
			enabled
		});
	} else if (family === "tables") {
		title$1("Table");
		add("Grid", "sampleGrid", 330, {
			text: tr("Table"),
			source: "sampleCells",
			cellWidth: 160,
			rowHeight: 38,
			labelWidth: 40,
			headerHeight: 32,
			rowHeaders: models(model).sampleCells.map((_, i) => ({ label: String(i + 1) })),
			columnHeaders: [
				tr("Selected"),
				tr("Name"),
				tr("Value")
			],
			revision: model.revision,
			enabled,
			readOnly: flags.readOnly
		});
		if (model.state === "empty") add("Empty", "sampleGridEmpty", 180, {
			text: tr("No results"),
			icon: "table"
		});
	} else if (family === "scroll-layout") {
		title$1("Resizable panels");
		const split = Math.max(0, Math.min(width - 60, model.split * width));
		const pane = (id, x, w) => node("Scroll", id, rect(x, y, w, 240), {
			contentWidth: 420,
			contentHeight: 700,
			children: Array.from({ length: 14 }, (_, i) => label(id + "_" + i, rect(12, i * 48, 380, 36), tr("Row") + " " + (i + 1)))
		});
		nodes.push(pane("sampleLeftPane", 0, split), pane("sampleRightPane", split + 12, Math.max(0, width - split - 12)), node("Splitter", "sampleSplitter", rect(split, y, 12, 240), {
			min: 0,
			max: Math.max(48, width - 60),
			value: split,
			enabled,
			text: tr("Resize panels"),
			action: {
				type: "sampleSplit",
				width
			},
			commitAction: {
				type: "sampleSplit",
				width
			}
		}));
		y += 256;
		action("sampleCollapsePane", model.split < .2 ? "Expand" : "Collapse", "sampleCollapse");
	} else if (family === "previews") {
		const thumbnails = [
			"preview-round",
			"preview-square",
			"preview-outline",
			"preview-photo",
			"preview-contain",
			"preview-icon",
			"preview-loading",
			"preview-selected"
		];
		const columns = width >= 560 ? 4 : width >= 280 ? 2 : 1;
		const cellWidth = (width - (columns - 1) * 16) / columns;
		for (let index = 0; index < thumbnails.length; index++) {
			const id = thumbnails[index], example = examples$1.find((row) => row.id === id);
			const x = index % columns * (cellWidth + 16), top = y + Math.floor(index / columns) * 144;
			nodes.push(node("Preview", "sample_" + id, rect(x, top, 96, 96), Object.assign({}, example.properties, {
				round: example.properties.round === true,
				source: model.state === "empty" || model.state === "error" ? "" : example.properties.source,
				loading: model.state === "loading" || example.properties.loading,
				selected: model.state === "selected" || example.properties.selected,
				fit: id === "preview-contain" ? "contain" : "cover"
			})));
			nodes.push(label("caption_" + id, rect(x, top + 104, cellWidth, 32), title(id, language), {
				fontRole: "caption",
				wrap: true
			}));
		}
		y += Math.ceil(thumbnails.length / columns) * 144;
		for (const id of [
			"preview-card",
			"attachment-image",
			"attachment-file"
		]) {
			const example = examples$1.find((row) => row.id === id);
			title$1(title(id, language));
			add("View", "sample_" + id, example.height, {
				view: "showcaseVariant",
				model: initial$2(id),
				state: model.state,
				language,
				gallery: id
			});
		}
	} else if (family === "drag-files") {
		title$1("Files");
		add("FileField", "sampleFile", 44, Object.assign({}, flags, {
			text: model.files.map((file) => file.name).join(", "),
			label: tr("Choose file"),
			action: { type: "sampleFiles" }
		}));
		add("Box", "sampleDrop", 144, {
			enabled,
			background: "surfaceContainerLow",
			border: flags.error ? "error" : "outlineVariant",
			radius: 8,
			dropAction: {
				type: "sampleFiles",
				name: "file-ingest"
			},
			children: [label("sampleDropText", rect(16, 16, Math.max(0, width - 32), 110), tr("Drop files here or choose a file above."), {
				wrap: true,
				align: "center"
			})]
		});
		for (const file of model.files) add("Label", "sampleFile_" + y, 36, {
			text: file.name,
			elideMiddle: true
		});
		action("sampleFilesClear", "Clear", "sampleFilesClear");
	} else if (family === "editors") {
		title$1("Source code");
		add("Code", "sampleEditor", 320, Object.assign({}, flags, {
			text: model.state === "empty" ? "" : model.editorText,
			service: "sourceEditor",
			bufferKey: "showcaseEditable",
			language,
			syntax: "python",
			action: { type: "sampleEditor" }
		}));
	} else if (family === "graphs") {
		title$1("Graph");
		const records = model.state === "empty" ? [] : [{
			identity: "a",
			label: "Model",
			nodeX: 24,
			nodeY: 24,
			color: "action"
		}, {
			identity: "b",
			label: "Review",
			nodeX: Math.min(width - 180, 300),
			nodeY: 160,
			color: "action"
		}];
		add("Graph", "sampleGraph", 360, Object.assign({}, flags, {
			enabled,
			nodes: records.map((row) => Object.assign({}, row, model.graphPositions.find((p) => p.identity === row.identity) || {})),
			edges: records.length ? [{
				from: "a",
				to: "b"
			}] : [],
			selectedNodes: model.state === "selected" ? ["a"] : model.graphSelected,
			resetKey: "showcaseGraph_" + model.resetRevision,
			action: { type: "sampleGraph" },
			selectAction: { type: "sampleGraphSelect" },
			moveAction: { type: "sampleGraphMove" }
		}));
		action("sampleGraphReset", "Reset", "sampleGraphReset");
	} else if (family === "input-runtime") {
		title$1("Mouse, keyboard and touch");
		add("Button", "sampleActivation", h, {
			text: model.state === "long" ? model.text.repeat(3) : tr("Activate"),
			enabled,
			action: { type: "sampleActivate" },
			pressAction: { type: "samplePress" },
			cancelAction: { type: "sampleCancel" },
			toolTip: tr("Mouse, keyboard and touch")
		});
		add("Field", "sampleIME", 36, Object.assign({}, flags, {
			text: model.ime,
			label: tr("Text"),
			placeholder: "IME · Кириллица · 日本語",
			action: { type: "sampleIME" }
		}));
		add("Label", "sampleInputCounts", 44, {
			text: tr("Activated") + ": " + model.activations + " · " + tr("Pressed") + ": " + model.presses + " · " + tr("Cancelled") + ": " + model.cancels,
			wrap: true
		});
	} else if (family === "domain-fragments") {
		title$1("Task workspace surface");
		const part = surfaces({
			value: model.surface,
			disabled: !enabled,
			controlHeight: 36
		}, width, language);
		add("Box", "sampleTaskSurfaces", part.height, {
			background: "transparent",
			children: part.nodes
		});
		add("Identity", "sampleTaskAssignee", 48, {
			text: "Anna",
			login: "vfx_anna",
			initials: "VA",
			accent: "action"
		});
		add("StatusChip", "sampleTaskStatus", 32, {
			text: tr("In progress"),
			accent: "action"
		});
		add("Area", "sampleTaskDraft", 100, Object.assign({}, flags, {
			text: model.taskDraft,
			label: tr("Description"),
			action: { type: "sampleTaskDraft" }
		}));
		action("sampleTaskSave", "Save", "sampleTaskSave");
		if (model.last === "sampleTaskSave") add("Label", "sampleTaskSaved", 28, {
			text: tr("Saved"),
			color: "green",
			role: "status"
		});
	}
	const scene = {
		nodes,
		models: models(model)
	};
	const code = "import * as Showcase from './features/administration/showcase.ui.mjs';\n\n// FrameView: models = example.models; local model = Showcase.initial();\n// describeCell = (grid, record, row, column) => Showcase.cell(grid, record, row, column, model);\n// Menu/dialog ports: ComponentShowcase hosts. Events: Showcase.transition.\n(" + JSON.stringify(scene, null, 2) + ")";
	return {
		nodes,
		height: y,
		code
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/controls/catalog.data.mjs
var catalogue = {
	levels: {
		primitive: "Базовый визуальный элемент или одно действие/значение; без проекта, бизнес-объекта и серверной операции.",
		composite: "Базовый составной контрол: собирает примитивы, имеет нейтральные данные и события, подходит разным формам.",
		infrastructure: "Механика ввода, позиционирования, окон, рендеринга или жизненного цикла; не отдельный визуальный контрол.",
		feature: "Форма, экран или предметный фрагмент: знает конкретный сценарий, предметную модель или операцию.",
		review: "Исходник учтён; его ответственность требует отдельного разбора. Это не подтверждённый базовый контрол."
	},
	families: [
		{
			id: "buttons",
			title: "Кнопки и действия",
			level: "primitive",
			native: [
				"Button",
				"CompactIconButton",
				"FilledActionButton",
				"DisclosureButton",
				"ItemCountActionButton",
				"PreviewNavigationButton",
				"RefreshIconButton",
				"MessageSendButton"
			],
			vue: [
				"AppButton",
				"DisclosureButton",
				"PreviewNavigationButton"
			],
			tokens: [
				"button",
				"action-count",
				"disclosure",
				"reveal"
			],
			variants: [
				"Обычная",
				"Primary / заполненная",
				"Tonal",
				"Destructive",
				"Текстовая / плоская",
				"Круглая иконка",
				"Прямоугольная toolbar action",
				"Счётчик поверх кнопки",
				"Раскрытие ветки",
				"Навигация превью",
				"Отправка / sending"
			],
			coverage: "contract",
			example: "button",
			gaps: ["Команда формы и доступность операции остаются у владельца. Native PopupAction не активируется повторно от autorepeat-release."],
			rule: "Общий Button + именованные варианты. Геометрия hit target, поверхности, иконки и бейджа задаётся отдельно; предметная команда остаётся у формы.",
			examples: [
				"button",
				"button-primary",
				"button-tonal",
				"button-danger",
				"button-filled-danger",
				"button-icon",
				"button-badge-zero",
				"button-badge",
				"button-badge-overflow",
				"button-disclosure",
				"button-preview",
				"button-send"
			],
			label: "Buttons and actions",
			category: "controls"
		},
		{
			id: "toggles",
			title: "Чекбоксы, radio, переключатели",
			level: "primitive",
			native: [
				"CheckBox",
				"Switch",
				"SegmentedButton"
			],
			vue: [
				"AppCheckbox",
				"AppSwitch",
				"AppSegmentedButton"
			],
			tokens: [
				"checkbox",
				"switch",
				"radio",
				"toggle",
				"segment"
			],
			variants: [
				"Checkbox обычный / compact / prominent",
				"Unchecked / checked / mixed",
				"Switch",
				"Radio",
				"Сегменты с текстом",
				"Сегменты с иконками",
				"Outlined segments",
				"Недоступный отдельный вариант"
			],
			coverage: "contract",
			example: "checkbox",
			gaps: ["Radio — именованный вариант выбора SegmentedButton, а не отдельный предметный редактор. Disabled-опции пропускаются клавиатурой."],
			rule: "Один смысл выбора и клавиатурной навигации; явные варианты плотности и вида, а не локальные CSS-копии.",
			examples: [
				"checkbox",
				"checkbox-checked",
				"checkbox-mixed",
				"checkbox-compact",
				"checkbox-prominent",
				"switch-off",
				"switch-on",
				"segments",
				"segments-icons",
				"segments-outline",
				"segments-disabled-option"
			],
			label: "Checkboxes and switches",
			category: "controls"
		},
		{
			id: "text-fields",
			title: "Текстовые поля",
			level: "primitive",
			native: ["TextField", "TextArea"],
			vue: ["AppTextField", "AppTextArea"],
			tokens: [
				"text-field",
				"textarea",
				"textinput",
				"textedit",
				"input",
				"field"
			],
			variants: [
				"Однострочное",
				"Многострочное",
				"Placeholder",
				"Password / reveal",
				"Readonly",
				"Ошибка и helper text",
				"Prefix / suffix / trailing action",
				"Табличный inline editor"
			],
			coverage: "contract",
			example: "field",
			gaps: ["IME, selection, undo и потеря focus проверяются настоящими вводами платформенного стенда. Предметная валидация не является частью базового поля.", "У оригинального TextField нет общего prefix/suffix API: такие подписи и кнопки собираются формой из базовых контролов. Это не отдельный недописанный контрол для переноса."],
			rule: "Общий ввод/selection/IME/validation presentation. Значение и предметная валидация принадлежат владельцу формы.",
			examples: [
				"field",
				"field-empty",
				"field-password",
				"field-readonly",
				"field-error",
				"field-inline",
				"text-area"
			],
			label: "Text fields",
			category: "controls"
		},
		{
			id: "search",
			title: "Поиск и подсказки",
			level: "composite",
			native: ["SearchField", "SearchSuggestionsPopup"],
			vue: ["AppSearchField"],
			tokens: [
				"search",
				"suggest",
				"completer",
				"autocomplete"
			],
			variants: [
				"Поиск с иконкой",
				"Очистка",
				"Загрузка",
				"Подсказки",
				"Поиск в меню / picker",
				"Компактный",
				"Поиск с trailing actions"
			],
			coverage: "contract",
			gaps: ["Подсказки получают нейтральные записи; TacticSearchField оставляет запрос, debounce и открытие результата своему controller."],
			rule: "SearchField не знает TSQL, проект или HTTP. Поисковая форма собирает его с фильтрами и владеет запросом.",
			examples: [
				"search",
				"search-empty",
				"search-suggestions"
			],
			example: "search",
			label: "Search and suggestions",
			category: "controls"
		},
		{
			id: "choices",
			title: "Комбобоксы и выбор из списка",
			level: "composite",
			native: ["ComboBox", "QuickFilterOptions"],
			vue: [
				"AppSelect",
				"StatusSelect",
				"QuickFilterOptions",
				"AppEditableSelect"
			],
			tokens: [
				"combo",
				"select",
				"choice",
				"dropdown"
			],
			variants: [
				"Обычный",
				"Пустой / not assigned",
				"Иконки",
				"Цветовые swatches",
				"Группы",
				"Поиск",
				"Multi-select + chips",
				"Статус с цветом",
				"Action field",
				"Длинные названия"
			],
			coverage: "contract",
			example: "choice",
			gaps: ["1000 локальных записей проверяют packing/виртуализацию. Системный fallback select в браузерах без base-select сохраняет нативное оформление ОС."],
			rule: "Нейтральная модель options/value и одинаковые события. Загрузка проектов/процессов/статусов не входит в контрол.",
			examples: [
				"choice",
				"choice-empty",
				"choice-disabled-option",
				"choice-icons",
				"choice-status",
				"packed-choices"
			],
			label: "Selection controls",
			category: "controls"
		},
		{
			id: "numbers",
			title: "Числа, spinbox, sliders",
			level: "composite",
			native: ["SpinBox", "Slider"],
			vue: ["AppSlider", "AppSpinBox"],
			tokens: [
				"spin",
				"slider",
				"range",
				"number"
			],
			variants: [
				"Integer / decimal",
				"Min / max / step",
				"Ввод и стрелки",
				"Slider horizontal / vertical",
				"Текущее значение",
				"Клавиатура и колесо"
			],
			coverage: "contract",
			example: "integer",
			gaps: ["Публичный QML SpinBox сохраняет scaled-int API Qt (32-bit); JS number не расширяет его диапазон. EN/RU grouping, decimal, clamp и external-model binding проверяются отдельно."],
			rule: "Общие range/step/clamp/commit правила. Не считать центральное положение thumb проверкой поведения.",
			examples: [
				"integer",
				"decimal",
				"integer-min",
				"integer-max",
				"slider",
				"slider-step",
				"slider-fixed"
			],
			label: "Numeric controls",
			category: "controls"
		},
		{
			id: "dates",
			title: "Дата, время, календари",
			level: "composite",
			native: ["DateField", "ActivityCalendarPopup"],
			vue: ["AppDateField", "ActivityCalendar"],
			tokens: [
				"date",
				"time",
				"calendar",
				"month",
				"day"
			],
			variants: [
				"Date only",
				"Date + time",
				"Time only",
				"Месяц и дни",
				"Сегодня / очистить",
				"Високосный год",
				"Год до 100",
				"Неверная дата",
				"Readonly / disabled",
				"Диапазон дат"
			],
			coverage: "contract",
			example: "date",
			gaps: ["ActivityCalendarPopup — фильтр истории активности, а не базовый календарь DateField; его полный экран относится к B11."],
			rule: "Календарь выбора даты — базовый составной контрол. Планировщик задач с загрузкой/сохранением — форма/панель.",
			examples: [
				"date",
				"datetime",
				"date-early-year",
				"date-invalid",
				"date-empty"
			],
			label: "Date and time",
			category: "controls"
		},
		{
			id: "identity",
			title: "Аватары, имя пользователя, группы",
			level: "composite",
			native: [
				"UserAvatar",
				"UserIdentity",
				"UserGroupSection",
				"ProfileInfoRow"
			],
			vue: [
				"UserIdentity",
				"UserGroupSection",
				"ProfileInfoRow"
			],
			tokens: [
				"avatar",
				"identity",
				"user-badge",
				"profile-row",
				"presence"
			],
			variants: [
				"Фото",
				"Один / два инициала",
				"Fallback person",
				"Круг / квадрат",
				"Имя + login",
				"Retired",
				"Presence dot",
				"Размеры строки / шапки / профиля",
				"Группа пользователей"
			],
			coverage: "contract",
			gaps: ["UserAvatar обращается к profile/userModel и является адаптером предметных данных; нейтральный avatar — ItemPreview. Отдельного готового presence-dot контрола в оригинале нет."],
			rule: "Identity принимает нейтральные данные профиля; редактор пользователя и операции членства — отдельные формы.",
			examples: [
				"avatar-initials",
				"avatar-two-initials",
				"avatar-fallback",
				"identity",
				"identity-retired",
				"identity-emphasized",
				"user-group",
				"user-group-compact",
				"user-group-empty",
				"profile-info",
				"avatar-photo"
			],
			example: "avatar-initials",
			label: "Avatars and identity",
			category: "display"
		},
		{
			id: "user-choice",
			title: "Выбор пользователя",
			level: "composite",
			native: [
				"UserComboBox",
				"UserPicker",
				"UserFilter"
			],
			vue: ["UserComboBox", "UserPicker"],
			tokens: [
				"user-combo",
				"user-picker",
				"assignee",
				"member-picker"
			],
			variants: [
				"Single select",
				"Not assigned",
				"Поиск по имени/login/group",
				"Multi-select",
				"Selected chips",
				"Группировка",
				"Клавиатурный выбор"
			],
			coverage: "contract",
			example: "user",
			gaps: ["Поиск/выбор сохраняют скрытые выбранные записи. Данные пользователя, ACL и сохранение назначения не принадлежат пикеру."],
			rule: "Контрол получает готовую модель пользователей и возвращает identity; он не меняет ACL и не выполняет серверный поиск самостоятельно.",
			examples: [
				"user",
				"user-empty",
				"users-multiple"
			],
			label: "User selection",
			category: "controls"
		},
		{
			id: "pickers",
			title: "Цвет, иконка, emoji, изображение",
			level: "composite",
			native: [
				"ColorField",
				"ColorPickerDialog",
				"IconPickerButton",
				"EmojiPicker",
				"ImagePicker",
				"AccentPresetPicker"
			],
			vue: [
				"AppColorInput",
				"ColorPicker",
				"IconPicker",
				"EmojiPicker",
				"ImagePicker",
				"AccentPresetPicker"
			],
			tokens: [
				"picker",
				"swatch",
				"palette",
				"emoji",
				"icon-library"
			],
			variants: [
				"Color swatch",
				"Plane / hue / hex / alpha",
				"Icon search / set / virtual grid",
				"Emoji categories / recent / search",
				"Image choose / clear / preview",
				"Accent presets"
			],
			coverage: "contract",
			example: "color",
			gaps: ["Выбор локального файла остаётся системной возможностью хоста. Browser File и native URL/path не подменяются одним фиктивным API."],
			rule: "Picker выбирает значение; загрузка/сохранение файла или изменение настройки выполняется владельцем сценария.",
			examples: [
				"color",
				"icon-choice",
				"emoji",
				"image-picker",
				"accent-presets"
			],
			label: "Color, icon and emoji pickers",
			category: "controls"
		},
		{
			id: "icons",
			title: "Иконки и служебные глифы",
			level: "primitive",
			native: ["IconFontData", "MaterialIcon"],
			vue: ["AppIcon"],
			tokens: ["icon", "glyph"],
			variants: [
				"Пять наборов",
				"Semantic alias",
				"Точный set:name",
				"Force solid",
				"Оптический размер",
				"Цвет роли",
				"Иконка внутри контрола"
			],
			coverage: "contract",
			example: "icon-material",
			gaps: ["Проверяются реальные Unicode-глифы и шрифтовые наборы. Разная растеризация шрифта ОС не означает разные имена иконок."],
			rule: "Один семантический словарь и fallback. Разница выбора глифа — дефект; сглаживание растеризаторов учитывается отдельно.",
			examples: [
				"icon-material",
				"icon-solid",
				"icon-outline",
				"icon-fluent",
				"icon-fluent-filled",
				"icon-small",
				"icon-large"
			],
			label: "Icons",
			category: "foundations"
		},
		{
			id: "tabs",
			title: "Табы и полосы вкладок",
			level: "composite",
			native: [
				"TabButton",
				"WorkspaceTabVisual",
				"SectionTabRail"
			],
			vue: [
				"AppTabButton",
				"WorkspaceTabs",
				"SectionTabRail",
				"WorkspaceTabVisual",
				"SectionTabVisual"
			],
			tokens: [
				"tab",
				"tabbar",
				"tab-rail",
				"workspace-tab"
			],
			variants: [
				"Section tabs",
				"Workspace tabs",
				"Dock tabs",
				"Closable",
				"Dirty / count",
				"Overflow",
				"Reorder / drag",
				"Контекстное меню",
				"Текущая / disabled / mobile"
			],
			coverage: "contract",
			gaps: ["Поиск/section tabs имеют отдельные свежие B01 сценарии drag, close, reopen и сохранения; standalone tab показывает нейтральную поверхность."],
			rule: "Разделить выбор вкладки, её содержимое и host docking. Общая вкладка не должна знать задачи/проекты.",
			examples: ["tab", "tab-current"],
			example: "tab",
			label: "Tabs",
			category: "navigation"
		},
		{
			id: "badges",
			title: "Бейджи, chips, счётчики и точки",
			level: "composite",
			native: [
				"SummaryChip",
				"StatusChip",
				"CompletionStrip",
				"QuickFilterChip",
				"MessageReactionChip"
			],
			vue: [
				"SummaryChip",
				"StatusChip",
				"ReactionChip",
				"QuickFilterChip"
			],
			tokens: [
				"badge",
				"chip",
				"count",
				"unread",
				"status-dot",
				"completion"
			],
			variants: [
				"Badge count 0 / 1 / 99+",
				"Unread",
				"Notification/error",
				"Status dot",
				"Status chip",
				"Filter chip + remove",
				"Clickable / passive",
				"Selected",
				"Compact",
				"Completion strip"
			],
			coverage: "contract",
			gaps: ["CompletionStrip/TacticCompletionCell знают задачи/снимки и переходы: предметные фрагменты B07/B08. Базовые StatusChip и счётчики не сохраняют данные."],
			rule: "Badge (наложение), Chip (элемент потока) и status indicator (состояние) — разные роли. У каждой один контракт и именованные варианты.",
			examples: [
				"chip",
				"chip-clickable",
				"chip-compact",
				"status-chip",
				"status-chip-dense",
				"status-chip-action",
				"reaction",
				"reaction-count",
				"reaction-checked",
				"filter-chip",
				"filter-chip-checked",
				"filter-chip-subtle",
				"filter-chip-marker",
				"filter-chip-emphasis"
			],
			example: "chip",
			label: "Badges, chips and counters",
			category: "display"
		},
		{
			id: "headers",
			title: "Заголовки, toolbar, переключатели вида",
			level: "composite",
			native: [
				"ColumnHeaderGrip",
				"EditorPanel",
				"SectionLabel",
				"InfoValueStrip",
				"ConfigurationSection",
				"SObjectFieldFrame"
			],
			vue: [
				"EditorPanel",
				"SectionLabel",
				"InfoValueStrip",
				"ConfigurationSection",
				"FormFieldFrame"
			],
			tokens: [
				"header",
				"heading",
				"titlebar",
				"toolbar",
				"view-switch",
				"mode-switch",
				"surface-switch"
			],
			variants: [
				"Заголовок раздела",
				"Панель: icon + title + subtitle + actions",
				"Toolbar",
				"Title + count",
				"Header с tabs",
				"List / cards / table switcher",
				"Back / collapse",
				"Sticky"
			],
			coverage: "contract",
			gaps: ["EditorPanel, section, strip и FormFieldFrame — нейтральные компоновки. Поля, операции и серверная валидация задаются формой."],
			rule: "Нейтральная шапка/toolbar — базовая композиция. TaskInspectorHeader и управление конкретной рабочей областью — фрагмент формы.",
			examples: [
				"header",
				"header-back",
				"header-actions",
				"editor-panel",
				"configuration-section",
				"section-label",
				"info-values",
				"field-frame",
				"field-frame-required",
				"field-frame-error",
				"field-frame-readonly"
			],
			example: "header",
			label: "Headings and toolbars",
			category: "foundations"
		},
		{
			id: "menus",
			title: "Меню, popover и списки действий",
			level: "composite",
			native: [
				"Menu",
				"ScrollablePopup",
				"TextContextMenu",
				"ActionMenu",
				"ActionMenuRow"
			],
			vue: [
				"AppMenu",
				"AppMenuItem",
				"ActionRow",
				"ActionRows"
			],
			tokens: [
				"menu",
				"popover",
				"context",
				"submenu",
				"account-panel"
			],
			variants: [
				"Anchored",
				"Context menu",
				"Submenu",
				"Checkable item",
				"Icon + label + shortcut",
				"Separator / heading",
				"Scrollable",
				"Searchable",
				"Disabled",
				"Escape / outside click / restore focus"
			],
			coverage: "contract",
			example: "menu",
			gaps: ["Меню, check/radio rows, separators, submenus, tooltips и закрытие/focus проверяются каталогом и существующими menu/platform сценариями."],
			rule: "Меню — базовый составной контрол. Его команды передаются снаружи; ObjectActionsMenu с ACL и запросами — предметная композиция.",
			examples: ["menu", "menu-checks"],
			label: "Menus and popovers",
			category: "navigation"
		},
		{
			id: "popups",
			title: "Popup, dialog и оконная механика",
			level: "infrastructure",
			native: [
				"Popup",
				"Dialog",
				"DialogActions",
				"PopupBackground",
				"PopupScrim",
				"PopupCoordinator",
				"HoverReleaseCoordinator"
			],
			vue: [
				"WindowControls",
				"MobilePage",
				"AppDialog"
			],
			tokens: [
				"popup",
				"dialog",
				"modal",
				"window",
				"scrim",
				"backdrop"
			],
			variants: [
				"Non-modal",
				"Modal",
				"Anchored",
				"Floating",
				"Docked",
				"Close/minimize/maximize",
				"Drag / resize",
				"Stacking / focus / owner"
			],
			coverage: "contract",
			gaps: ["Позиционирование, scrim, ownership и native Popup.Window — инфраструктура. Полная предметная форма внутри окна проверяется в своём batch."],
			rule: "Host решает ownership/lifecycle, форма — свой сценарий, DialogActions — нейтральная строка действий.",
			examples: [],
			label: "Dialogs and windows",
			category: "navigation"
		},
		{
			id: "feedback",
			title: "Tooltip, loading, progress, empty/error",
			level: "composite",
			native: [
				"ToolTip",
				"BusyIndicator",
				"EmptyState",
				"InitialBatchPresentation",
				"ContentLoadingOverlay",
				"TacticCompletionCell",
				"ErrorDialog",
				"ProgressBar"
			],
			vue: [
				"BusyIndicator",
				"AppProgress",
				"CompletionCell",
				"EmptyState",
				"ContentLoadingOverlay"
			],
			tokens: [
				"tooltip",
				"progress",
				"busy",
				"spinner",
				"empty",
				"skeleton",
				"error",
				"notice",
				"warning",
				"alert"
			],
			variants: [
				"Tooltip",
				"Busy inline / block",
				"Determinate / indeterminate",
				"Progress + cancel",
				"Empty state",
				"Error + retry",
				"Skeleton",
				"Inline validation"
			],
			coverage: "contract",
			example: "busy",
			gaps: ["Нет готового отдельного skeleton-контрола в оригинале: InitialBatchPresentation управляет появлением делегатов, а не рисует skeleton."],
			rule: "Сообщение об ошибке и retry action поступают снаружи; контрол не перезапускает серверную операцию сам.",
			examples: [
				"busy",
				"progress",
				"progress-empty",
				"progress-complete",
				"progress-indeterminate",
				"loading-overlay",
				"loading-cancellable",
				"empty",
				"error-retry"
			],
			label: "Feedback and progress",
			category: "feedback"
		},
		{
			id: "lists",
			title: "Списки, дерево, строки",
			level: "composite",
			native: [
				"SmoothListView",
				"EditorListItem",
				"HierarchyGuide",
				"HierarchyReveal",
				"TreeExpansionMotion",
				"NavigationRow"
			],
			vue: [
				"ItemSurface",
				"NavigationRow",
				"EditorListItem",
				"VirtualCollection"
			],
			tokens: [
				"list",
				"tree",
				"hierarchy",
				"row",
				"selection"
			],
			variants: [
				"Обычная / selected / hover строка",
				"Одно / двухстрочная",
				"Tree indent / guide / disclosure",
				"Checkbox row",
				"Virtualized",
				"Variable-height collections and tiles; retained offscreen focus (tools/frame_search)",
				"Loading / empty",
				"Keyboard selection",
				"Navigation drawer: mouse/touch, off-screen keys, focus and reserved scrollbar gutter"
			],
			coverage: "contract",
			example: "tree",
			gaps: ["Нейтральный list/tree контракт покрывает virtual rows, selection, раскрытие и keyboard. ProcessSelectionTree остаётся предметной формой."],
			rule: "Tree row и navigation — базовый контрол; загрузка и смысл веток принадлежат форме.",
			examples: [
				"tree",
				"list-item",
				"list-item-selected",
				"list-item-badge",
				"list-item-long"
			],
			label: "Lists and trees",
			category: "display"
		},
		{
			id: "tables",
			title: "Табличная база и ячейки",
			level: "composite",
			native: ["FrameGrid", "FrameGridBranch"],
			vue: ["FrameGrid"],
			tokens: [
				"grid",
				"table",
				"cell",
				"column",
				"sort"
			],
			variants: [
				"Header / row header",
				"Sort / resize / reorder columns",
				"Selection",
				"Text / checkbox / icon cell",
				"Inline edit",
				"Frozen / scroll",
				"Virtualized"
			],
			coverage: "contract",
			example: "table",
			gaps: ["Это контракт Grid (virtual cells, selection/focus, resize, drafts, readonly). Production Table View и его виджеты остаются B07."],
			rule: "Grid нейтрален к Search Type; widget-config renderer и сохранение SObject — отдельный уровень.",
			examples: ["table", "table-readonly"],
			label: "Tables and cells",
			category: "display"
		},
		{
			id: "scroll-layout",
			title: "Прокрутка, splitters, layout",
			level: "composite",
			native: [
				"ScrollBar",
				"SplitterHandle",
				"ResizeGripVisual",
				"ResponsiveFlow",
				"DockDragGrip",
				"DockWorkspaceFooter",
				"SettingsRow",
				"SettingsNavigationItem",
				"AdminSaveBar"
			],
			vue: [
				"AppSplitter",
				"ResponsiveFlow",
				"DockGrip",
				"SettingRow",
				"AdminSaveBar",
				"DockWorkspaceFooter"
			],
			tokens: [
				"scroll",
				"splitter",
				"resize",
				"grip",
				"flow",
				"settings-row",
				"footer"
			],
			variants: [
				"Vertical / horizontal scrollbar",
				"Rest / hover / pressed / disabled",
				"Splitter",
				"Keyboard resize",
				"Grip",
				"Responsive flow",
				"Label-help-control row",
				"Footer actions"
			],
			coverage: "contract",
			example: "setting-row",
			gaps: ["Оба направления overflow, keyboard splitter и drag проверяются реальным вводом. Физический touch/OS compositor не заменяются synthetic input."],
			rule: "Layout-кирпичики знают размеры/слоты, а не сохранение настроек проекта.",
			examples: [
				"setting-row",
				"flow",
				"scroll-vertical",
				"scroll-horizontal",
				"scroll-both",
				"splitter-vertical",
				"splitter-horizontal"
			],
			label: "Scroll, splitters and layout",
			category: "navigation"
		},
		{
			id: "typography",
			title: "Текст, elide, markdown, кодовые блоки",
			level: "primitive",
			native: [
				"Typography",
				"SelectableText",
				"DocumentPane",
				"MessageBodyText"
			],
			vue: [
				"MiddleElide",
				"MarkdownText",
				"DocumentPane",
				"CodeBlock"
			],
			tokens: [
				"label",
				"text",
				"elide",
				"markdown",
				"code-block",
				"typography"
			],
			variants: [
				"Именованные text roles",
				"Single / wrap / elide",
				"Middle elide",
				"Selectable",
				"Links",
				"Markdown",
				"Monospace / code block",
				"Пустой / длинный / mixed script"
			],
			coverage: "contract",
			gaps: ["DocumentPane использует реальные Qt Markdown и browser Markdown renderer; сложный rich text и растеризация имеют явные платформенные границы. Сохранение/ссылки принадлежат владельцу."],
			rule: "Текстовые роли не заменяют контракты wrapping/selection/links. Rich renderer не должен владеть предметными запросами.",
			examples: ["markdown", "middle-elide"],
			example: "markdown",
			label: "Typography",
			category: "foundations"
		},
		{
			id: "previews",
			title: "Preview, thumbnail, карточки файлов",
			level: "composite",
			native: [
				"ItemPreview",
				"ItemSurface",
				"AttachmentCard",
				"MessageTimelineFrame",
				"MessageForwardPreview",
				"MessageReplyPreview",
				"SnapshotPreviewLayers"
			],
			vue: [
				"ItemPreview",
				"ItemSurface",
				"AttachmentCard"
			],
			tokens: [
				"preview",
				"thumbnail",
				"attachment",
				"image",
				"surface",
				"card"
			],
			variants: [
				"Photo / initials / icon",
				"Round / square",
				"Outlined",
				"Fit / crop",
				"Loading / failure / retry",
				"File card",
				"Image card",
				"Selected surface / accent rail"
			],
			coverage: "contract",
			gaps: ["Фото, contain/crop, broken/loading и selected border показаны отдельно. Rounded mask проверяется Windows/OpenGL; Qt software не подтверждает маску. AttachmentCard/forward/reply/snapshot layers — предметные компоненты."],
			rule: "Карточка нейтральных данных — составной контрол; ObjectCard с командами/ACL — предметный фрагмент.",
			examples: [
				"preview-square",
				"preview-round",
				"preview-icon",
				"preview-card",
				"attachment-image",
				"attachment-file",
				"preview-outline",
				"preview-broken",
				"preview-loading",
				"preview-photo",
				"preview-contain",
				"preview-selected"
			],
			example: "preview-square",
			label: "Image and file previews",
			category: "display"
		},
		{
			id: "drag-files",
			title: "Drop zones, файлы, clipboard",
			level: "infrastructure",
			native: [
				"AttachmentDropArea",
				"DropTargetOverlay",
				"ImageFileDialog",
				"FileInput"
			],
			vue: ["DropTargetOverlay", "AppFileInput"],
			tokens: [
				"drop",
				"upload",
				"file-dialog",
				"clipboard",
				"drag"
			],
			variants: [
				"Drag enter / valid / invalid / busy",
				"File choose",
				"Clipboard image/text",
				"Paste",
				"Native filesystem capability",
				"Browser file input"
			],
			coverage: "contract",
			gaps: ["DropTargetOverlay — нейтральное состояние drop target. AttachmentDropArea исполняет attachmentController.add_files; фактический перенос/загрузка относится к B11/B12."],
			rule: "Обратиться к файловой системе — адаптер платформы; политика check-in/upload — предметный сценарий.",
			examples: ["drop-target", "drop-rejected"],
			example: "drop-target",
			label: "Files, clipboard and drop zones",
			category: "specialized"
		},
		{
			id: "editors",
			title: "Редакторы текста/кода",
			level: "composite",
			native: [
				"ScriptCodeEditor",
				"FrameCode",
				"FrameCodeBranch",
				"ScriptOutline",
				"KnowledgeTableOfContents",
				"TableTextEditor"
			],
			vue: ["CodeEditor", "FrameCode"],
			tokens: [
				"code-editor",
				"source-editor",
				"completion",
				"syntax",
				"document"
			],
			variants: [
				"Plain code",
				"Highlight",
				"Line numbers",
				"Search / replace",
				"Undo / redo",
				"IME",
				"Completion",
				"Readonly / error / dirty"
			],
			coverage: "contract",
			gaps: ["Контракт FrameCode: текст, readonly, undo, search/replace, selection и clipboard. ScriptCodeEditor/ScriptOutline и выполнение скриптов остаются B13."],
			rule: "CodeEditor не знает Script Editor, Batch Manager и выполнение Python. Эти формы используют редактор.",
			examples: ["code", "code-readonly"],
			example: "code",
			label: "Text and code editors",
			category: "specialized"
		},
		{
			id: "graphs",
			title: "Графы и соединения",
			level: "composite",
			native: [
				"NodeGraph",
				"NodeGraphSelectionArea",
				"GraphPort",
				"FrameGraph",
				"FrameGraphBranch"
			],
			vue: ["FrameGraph"],
			tokens: [
				"graph",
				"edge",
				"port",
				"connection",
				"node"
			],
			variants: [
				"Node / port / edge",
				"Single / multi select",
				"Drag",
				"Connect",
				"Zoom / pan",
				"Readonly",
				"Keyboard delete",
				"Marquee"
			],
			coverage: "contract",
			gaps: ["FrameGraph — нейтральные nodes/edges/selection/move. NodeGraph и XML pipeline controller — отдельный существующий предметный редактор B03/B10."],
			rule: "Нейтральный graph control не владеет XML schema/pipeline, ACL или сохранением.",
			examples: ["graph", "graph-readonly"],
			example: "graph",
			label: "Graphs and connections",
			category: "specialized"
		},
		{
			id: "input-runtime",
			title: "Ввод, focus, ripple, координация",
			level: "infrastructure",
			native: [
				"ActivationHandler",
				"PopupAction",
				"MaterialRipple"
			],
			vue: [],
			tokens: [
				"activation",
				"ripple",
				"pointer",
				"focus",
				"gesture"
			],
			variants: [
				"Mouse / touch / pen",
				"Press / release / cancel",
				"Dedup synthesized click",
				"Keyboard activation",
				"IME",
				"Focus return",
				"Destroy while open"
			],
			coverage: "contract",
			gaps: ["Настоящие мышь/touch/keyboard, отмена, одна активация и три DPI выполняются platform gate. OS IME composition и физический pen требуют аппаратной проверки."],
			rule: "Одна активация на один пользовательский жест; событийная механика не исполняет бизнес-команды сама.",
			examples: [],
			label: "Input and focus infrastructure",
			category: "specialized"
		},
		{
			id: "domain-fragments",
			title: "Предметные формы и фрагменты — отдельно от базы",
			level: "feature",
			native: [
				"ProjectCard",
				"ProjectFilterToggles",
				"ProcessSelectionTree",
				"TaskWorkspaceModeSwitcher",
				"TaskWorkspaceSurfaceSwitcher",
				"ScriptSavedHistoryButton",
				"TacticSearchField",
				"MessageComposerField",
				"UserGroupMembershipEditor"
			],
			vue: ["TaskInspectorHeader", "TaskWorkspaceSurfaceSwitcher"],
			tokens: [],
			variants: [
				"Project selection/filter",
				"Process selector",
				"Task header/view switcher",
				"Script history",
				"Tactic search",
				"Message composer",
				"Membership editor"
			],
			coverage: "not-base",
			gaps: ["Расположение в controls/ не делает ProjectFilterToggles или ProjectCard базовым контролом.", "Существующие forms/fragments входят в полный индекс исходников, но не завышают число базовых контролов."],
			rule: "Если компонент знает Search Type, задачи, script token, членство/ACL или вызывает предметный controller, это композиция сценария. Вынести из неё можно нейтральную часть.",
			label: "Domain components",
			category: "specialized"
		},
		{
			id: "colors",
			title: "Цвета и поверхности",
			label: "Colors and surfaces",
			category: "foundations",
			level: "primitive",
			native: [],
			vue: [],
			tokens: [
				"palette",
				"surface",
				"semantic"
			],
			variants: [
				"Semantic roles",
				"Light and dark surfaces",
				"Contrast pairs"
			]
		},
		{
			id: "charts",
			title: "Диаграммы",
			label: "Charts",
			category: "display",
			level: "primitive",
			native: ["FrameChart"],
			vue: ["FrameChart"],
			tokens: ["chart"],
			variants: [
				"Bar",
				"Line",
				"Donut"
			]
		}
	],
	reviewedFeatureRoots: {
		native: [
			"ActivityEventCard",
			"ActivityFeedView",
			"AdvancedSearchView",
			"AttachmentComposerControls",
			"AttachmentStagingPanel",
			"CheckinDialogs",
			"CheckinOptionsPage",
			"CollaborationInitializationState",
			"CommitQueueView",
			"CommitWorkspaceView",
			"CommunicationView",
			"ConfigurationAppearancePage",
			"ConfigurationCachePage",
			"ConfigurationDccPage",
			"ConfigurationGlobalPreferencesPage",
			"ConfigurationPage",
			"ConfigurationProjectPage",
			"ConfigurationRepositoryPage",
			"ConfigurationServerPage",
			"ConfigurationTaskPreferencesPage",
			"ConfigurationView",
			"CostReportsView",
			"DatabaseBatchEditorView",
			"DatabaseEditorView",
			"DccOptionsView",
			"DebugLogView",
			"DeleteSObjectView",
			"DemoThinClientWindow",
			"DescriptionEditor",
			"DropPlateView",
			"DuplicateSObjectView",
			"FileWorkspaceCatalog",
			"FileWorkspaceChangelistFiles",
			"FileWorkspaceChangelistView",
			"FileWorkspaceComparisonDialog",
			"FileWorkspaceDepots",
			"FileWorkspaceFileRow",
			"FileWorkspaceGetRevisionDialog",
			"FileWorkspaceHistory",
			"FileWorkspaceInspector",
			"FileWorkspaceLog",
			"FileWorkspaceMappings",
			"FileWorkspaceNavigation",
			"FileWorkspaceRevertDialog",
			"FileWorkspaceReviewDialog",
			"FileWorkspaceShelfDialog",
			"FileWorkspaceStorage",
			"FileWorkspaceStreamEditor",
			"FileWorkspaceStreamGraph",
			"FileWorkspaceStreams",
			"FileWorkspaceSubmitDialog",
			"FileWorkspaceTargetDialog",
			"FileWorkspaceTreeRow",
			"FileWorkspaceView",
			"HandlerServerView",
			"HelpView",
			"IngestConflictDialog",
			"IngestFileList",
			"IngestFilesView",
			"IngestRuleEditor",
			"ItemCheckinDialogs",
			"ItemQuickActions",
			"KnowledgeArticleAttachments",
			"KnowledgeArticleContent",
			"KnowledgeArticleEditor",
			"KnowledgeArticleViewer",
			"KnowledgeAttachmentLibrary",
			"KnowledgeBaseView",
			"KnowledgeEditorImageOverlay",
			"KnowledgeImageSelectionOverlay",
			"KnowledgeLinkedObjectHeader",
			"KnowledgeNavigation",
			"KnowledgeRevisionHistoryPopup",
			"KnowledgeRichTextBlockDecorations",
			"KnowledgeRichTextToolbar",
			"LinkList",
			"LinkSObjectsView",
			"LoginDialog",
			"MatchingTemplatesView",
			"MessageReactionPicker",
			"MessagesConversationList",
			"MessagesTimeline",
			"MessagesView",
			"MilestoneManagerView",
			"NotesTimelinePosition",
			"NotificationStack",
			"NotificationsView",
			"ProcessFilterEditorView",
			"ProjectChooser",
			"ProjectEditorView",
			"ProjectTemplatesView",
			"ProjectWizardView",
			"QueueView",
			"QuickFilterEditorView",
			"RepositoryEditorView",
			"RepositorySetupPrompt",
			"RepositorySyncEditorView",
			"RepositorySyncView",
			"RevisionHistoryPopup",
			"SKeyPreviewCard",
			"SObjectFieldDelegate",
			"SObjectFieldEditor",
			"SObjectFieldGrid",
			"SObjectInfoView",
			"SObjectSnapshotTree",
			"SObjectValueEditor",
			"ScreenshotMakerView",
			"ScreenshotView",
			"ScriptEditorView",
			"ScriptShelfBar",
			"ScriptShelfEditorView",
			"ScriptTree",
			"ScriptTreePicker",
			"ScriptTriggerEditorView",
			"SearchAssigneeFilterPopup",
			"SearchPresetBar",
			"SearchQuickFilterPopup",
			"SearchResultMenus",
			"SearchResultSurface",
			"SearchResultTable",
			"SearchResultTableHeader",
			"SearchResultsPane",
			"SearchWorkspaceView",
			"ServerPresetsView",
			"SidebarSearchPreview",
			"SnapshotBrowser",
			"SnapshotBrowserOptionsMenu",
			"SnapshotBrowserToolbar",
			"SnapshotSummary",
			"SyncEditorView",
			"SyncQueueView",
			"TableViewPresetMenu",
			"TacticStructuredTableCell",
			"TacticTableActionCell",
			"TacticTableCellDisplay",
			"TacticTableInlineEditor",
			"TacticTaskCards",
			"TacticTaskCell",
			"TagCloudPopup",
			"TaskBrowserTable",
			"TaskBulkBar",
			"TaskCalendarView",
			"TaskDockView",
			"TaskGanttProgressHandle",
			"TaskGanttView",
			"TaskHiddenDetails",
			"TaskInspector",
			"TaskPendingChangesBar",
			"TaskProcessPanel",
			"TaskQuickFilterPopup",
			"TaskTableEditorCell",
			"TaskWorkspaceSummary",
			"TasksWorkspaceView",
			"TimesheetView",
			"UiPerformanceView",
			"UpdatePrompt",
			"UpdateView",
			"UserProfileEditorDialog",
			"UserProfileView",
			"UserWorkSummary",
			"WatchFolderDeleteDialog",
			"WatchFolderEditorView",
			"WatchFoldersView",
			"WorkHourEditorDialog",
			"WorkHoursSummary",
			"WorkReportsView",
			"WorkspaceCard",
			"WorkspaceChangeBranch",
			"WorkspaceChangeFile",
			"WorkspaceDetails",
			"WorkspaceDialogs",
			"WorkspaceFileDropTarget",
			"WorkspaceFilters",
			"WorkspaceFooter",
			"WorkspaceLayoutPresetMenuSection",
			"WorkspaceResultItem",
			"WorkspaceToolbar",
			"WorkspaceTreePane",
			"WorkspaceView"
		],
		vue: [
			"QueueDialogs",
			"QueuePreview",
			"QueueWorkspace",
			"StreamGraph",
			"StreamGraphEdges",
			"WorkspaceCatalog",
			"WorkspaceInspectorView",
			"WorkspaceLogEntries",
			"WorkspaceLogMessage",
			"WorkspaceTable",
			"WorkspaceToolbar",
			"WorkspaceTreePaint",
			"WorkspaceTreePane"
		]
	},
	levelOverrides: {
		IconFontData: "infrastructure",
		ColumnHeaderGrip: "primitive",
		SegmentedButton: "composite",
		AppSegmentedButton: "composite",
		TabButton: "primitive",
		AppTabButton: "primitive",
		UserAvatar: "feature",
		BusyIndicator: "primitive",
		AppProgress: "primitive",
		ScrollBar: "primitive",
		SplitterHandle: "primitive",
		HierarchyGuide: "primitive",
		HierarchyReveal: "primitive",
		AppMenuItem: "primitive",
		ActionMenuRow: "primitive",
		DialogActions: "composite",
		CodeBlock: "composite",
		MarkdownText: "composite",
		DocumentPane: "composite",
		Typography: "infrastructure",
		NavigationRow: "composite",
		SidebarTreeRow: "composite",
		ActionRow: "primitive",
		ActivityCalendarPopup: "feature",
		ActivityCalendar: "feature",
		CompletionStrip: "feature",
		TacticCompletionCell: "feature",
		CompletionCell: "feature",
		InitialBatchPresentation: "infrastructure",
		AttachmentDropArea: "feature",
		ImageFileDialog: "infrastructure",
		AttachmentCard: "feature",
		MessageTimelineFrame: "feature",
		MessageForwardPreview: "feature",
		MessageReplyPreview: "feature",
		SnapshotPreviewLayers: "feature",
		NodeGraph: "feature",
		NodeGraphSelectionArea: "feature",
		GraphPort: "feature",
		ScriptOutline: "feature",
		KnowledgeTableOfContents: "feature",
		TableTextEditor: "feature",
		ComponentShowcase: "feature",
		ComponentShowcaseView: "feature"
	},
	excludedVariants: [
		{
			name: "Standalone presence indicator",
			reason: "No completed standalone control in the original; avatar/status in domain cards stay domain-owned."
		},
		{
			name: "Skeleton loader",
			reason: "Original InitialBatchPresentation is delegate lifecycle infrastructure, not a finished skeleton control."
		},
		{
			name: "Emoji recents/favorites",
			reason: "Not implemented as a finished house control in the original."
		},
		{
			name: "Generic range date / multi combo / vertical slider",
			reason: "No completed corresponding original neutral variant; do not invent a port from wishlist names."
		}
	],
	categories: [
		{
			id: "foundations",
			title: {
				en: "Foundations",
				ru: "Основа"
			}
		},
		{
			id: "controls",
			title: {
				en: "Controls",
				ru: "Управление"
			}
		},
		{
			id: "display",
			title: {
				en: "Data display",
				ru: "Отображение данных"
			}
		},
		{
			id: "navigation",
			title: {
				en: "Navigation and layout",
				ru: "Навигация и компоновка"
			}
		},
		{
			id: "feedback",
			title: {
				en: "Feedback",
				ru: "Обратная связь"
			}
		},
		{
			id: "specialized",
			title: {
				en: "Specialized components",
				ru: "Специальные компоненты"
			}
		}
	]
};
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/showcase.ui.mjs
var live = [
	"typography",
	"headers",
	"colors",
	"icons",
	"buttons",
	"toggles",
	"text-fields",
	"choices",
	"numbers",
	"dates",
	"user-choice",
	"pickers",
	"tabs",
	"badges",
	"lists",
	"charts"
].concat(families$1);
var states = [
	"default",
	"disabled",
	"readonly",
	"error",
	"long",
	"loading",
	"empty",
	"selected"
];
var stateLabels = [
	"Default",
	"Disabled",
	"Read only",
	"Error",
	"Long text",
	"Loading",
	"Empty",
	"Selected"
];
function initial() {
	return {
		family: "typography",
		query: "",
		category: "",
		state: "default",
		code: false,
		variant: "",
		variantModel: null,
		text: "Robot Arm",
		area: "A local example",
		checked: true,
		choice: "model",
		user: "admin",
		date: "2026-11-02",
		color: "#78a6c4",
		icon: "save",
		number: "42",
		row: "assets",
		tab: "overview",
		search: "",
		menuChecked: true,
		dialogOpen: false,
		progress: 42,
		cells: {},
		revision: 0,
		split: .5,
		files: [],
		fit: "contain",
		previewSelected: false,
		editorText: "def example():\n    return 42\n",
		graphPositions: [],
		graphSelected: [],
		resetRevision: 0,
		presses: 0,
		activations: 0,
		cancels: 0,
		ime: "",
		surface: "cards",
		taskDraft: "Review the model",
		savedTaskDraft: "",
		last: ""
	};
}
function transition(model, event, catalog) {
	const next = Object.assign({}, model);
	if (event.type === "family" && catalog.families.some((f) => f.id === event.value)) Object.assign(next, {
		family: event.value,
		dialogOpen: false,
		variant: "",
		variantModel: null
	});
	else if (event.type === "variant" && (event.value === "" || available(model.family).some((row) => row.id === event.value))) Object.assign(next, {
		variant: event.value,
		variantModel: event.value ? initial$1(event.value) : null
	});
	else if (event.type === "galleryEvent") next.last = event.id + ": " + event.value.type;
	else if (event.type === "variantEvent" && model.variantModel && ![
		"disabled",
		"readonly",
		"loading"
	].includes(model.state)) {
		next.variantModel = transition$1(model.variantModel, event.value);
		next.last = event.value.type;
	} else if (event.type === "category" && (event.value === "" || catalog.categories.some((c) => c.id === event.value))) next.category = event.value;
	else if (event.type === "state" && states.includes(event.value)) Object.assign(next, {
		state: event.value,
		dialogOpen: false
	});
	else if (event.type === "query") next.query = String(event.value || "").slice(0, 200);
	else if (event.type === "code") next.code = !model.code;
	else if (event.type === "reset") return Object.assign(initial(), {
		resetRevision: model.resetRevision + 1,
		family: model.family,
		variant: model.variant,
		variantModel: model.variant ? initial$1(model.variant) : null,
		query: model.query,
		category: model.category
	});
	else if (event.type.startsWith("sample") || [
		"search",
		"searchAccept",
		"searchSubmit",
		"surface"
	].includes(event.type)) {
		if ([
			"disabled",
			"readonly",
			"loading"
		].includes(model.state) && event.type !== "sampleDialog") return model;
		next.last = event.type;
		if (event.type === "search") next.search = String(event.value || "").slice(0, 200);
		else if (event.type === "searchAccept") next.search = String(event.value.title || "");
		else if (event.type === "sampleMenu") {
			next.last = String(event.value);
			if (event.value === "toggle") next.menuChecked = !model.menuChecked;
		} else if (event.type === "sampleDialogOpen") next.dialogOpen = true;
		else if (event.type === "sampleDialog") {
			next.dialogOpen = false;
			next.last = String(event.value);
		} else if (event.type === "sampleAdvance") next.progress = Math.min(100, model.progress + 10);
		else if (event.type === "sampleRetry") {
			next.progress = 0;
			next.state = "default";
		} else if (event.type === "sampleCell") {
			next.cells = Object.assign({}, model.cells);
			next.cells[event.row + ":" + event.column] = event.value;
			next.revision++;
		} else if (event.type === "sampleSplit" && event.width > 0) next.split = Math.max(0, Math.min(1, Number(event.value) / event.width));
		else if (event.type === "sampleCollapse") next.split = model.split < .2 ? .5 : 0;
		else if (event.type === "sampleFit") next.fit = event.value === "cover" ? "cover" : "contain";
		else if (event.type === "samplePreviewSelect") next.previewSelected = !model.previewSelected;
		else if (event.type === "sampleFiles") next.files = fileLabels(event.value);
		else if (event.type === "sampleFilesClear") next.files = [];
		else if (event.type === "sampleEditor") next.editorText = String(event.value);
		else if (event.type === "sampleGraphSelect") next.graphSelected = Array.isArray(event.value) ? event.value : [];
		else if (event.type === "sampleGraphMove") next.graphPositions = Array.isArray(event.value) ? event.value : [];
		else if (event.type === "sampleGraphReset") {
			next.resetRevision++;
			next.graphSelected = [];
			next.graphPositions = [];
		} else if (event.type === "sampleGraph" && event.value) {
			if (event.value.type === "clear") next.graphSelected = [];
			if (event.value.type === "selectNodes") next.graphSelected = event.value.identities || [];
			else if (event.value.type === "moveNodes") {
				const positions = event.value.positions || [];
				next.graphPositions = model.graphPositions.filter((old) => !positions.some((row) => row.identity === old.identity)).concat(positions);
			}
		} else if (event.type === "sampleActivate") next.activations++;
		else if (event.type === "samplePress") next.presses++;
		else if (event.type === "sampleCancel") next.cancels++;
		else if (event.type === "sampleIME") next.ime = String(event.value);
		else if (event.type === "surface" && [
			"cards",
			"compact",
			"workspace"
		].includes(event.value)) next.surface = event.value;
		else if (event.type === "sampleTaskDraft") next.taskDraft = String(event.value);
		else if (event.type === "sampleTaskSave") next.savedTaskDraft = model.taskDraft;
	} else if ([
		"text",
		"area",
		"checked",
		"choice",
		"user",
		"date",
		"color",
		"icon",
		"number",
		"row",
		"tab"
	].includes(event.type)) next[event.type] = event.value;
	else next.last = event.type;
	return next;
}
function fileLabels(values) {
	if (!Array.isArray(values)) return [];
	return values.slice(0, 100).map((value) => {
		const raw = typeof value === "string" ? value : value && value.name;
		if (!raw || typeof value === "string" && !raw.startsWith("file:")) return null;
		let name = String(raw).split(/[\\/]/).pop();
		try {
			name = decodeURIComponent(name);
		} catch (_) {}
		return { name: name.slice(0, 240) };
	}).filter(Boolean);
}
function families(catalog, model, language) {
	const query = model.query.trim().toLocaleLowerCase();
	const groups = catalog.categories.map((c) => c.id);
	const foundations = [
		"typography",
		"colors",
		"headers",
		"icons"
	];
	return catalog.families.filter((f) => (!model.category || f.category === model.category) && (!query || [
		f.id,
		f.title,
		f.label,
		...f.native,
		...f.vue,
		...f.tokens,
		...available(f.id).map((row) => row.id)
	].join(" ").toLocaleLowerCase().includes(query))).sort((a, b) => groups.indexOf(a.category) - groups.indexOf(b.category) || (a.category === "foundations" ? foundations.indexOf(a.id) - foundations.indexOf(b.id) : catalog.families.indexOf(a) - catalog.families.indexOf(b))).map((f) => ({
		id: f.id,
		title: language === "ru" ? f.title : f.label,
		level: f.level,
		available: live.includes(f.id),
		count: available(f.id).length + 1
	}));
}
function row(list, record, model, language) {
	const tr = (text) => translate(text, language);
	const result = listAction("showcaseFamily_" + record.id, rect(0, 0, list.width, 48), record.title, "", {
		type: "family",
		value: record.id
	}, true, { selected: model.family === record.id });
	result.children[0].height = 27;
	result.children.push(label("showcaseFamilyState_" + record.id, rect(12, 27, list.width - 24, 16), tr(record.available ? "Live example" : "Catalogue entry") + " · " + record.count, {
		fontRole: "caption",
		color: "secondaryText"
	}));
	return {
		nodes: [result],
		width: list.width,
		height: 48
	};
}
function describe(model, catalog, width, height, language = "en") {
	const tr = (text) => translate(text, language), narrow = width < 740, nav = narrow ? 0 : 228;
	const x = nav + (narrow ? spacing.none : spacing.content), w = Math.max(0, width - x), top = narrow ? 96 : 48;
	const visible = families(catalog, model, language), family = catalog.families.find((f) => f.id === model.family) || catalog.families[0];
	const nodes = [];
	nodes.push(node("Field", "showcaseSearch", rect(0, 0, narrow ? width : nav, 36), {
		text: model.query,
		label: tr("Search components"),
		placeholder: tr("Search components"),
		enabled: true,
		action: { type: "query" }
	}));
	const groupOptions = [{
		value: "",
		label: tr("All component groups")
	}, ...catalog.categories.map((c) => ({
		value: c.id,
		label: c.title[language === "ru" ? "ru" : "en"]
	}))];
	if (!narrow) {
		nodes.push(node("Choice", "showcaseCategory", rect(0, 44, nav, 36), {
			value: model.category,
			options: groupOptions,
			enabled: true,
			label: tr("Category"),
			action: { type: "category" }
		}));
		nodes.push(node("List", "showcaseFamilies", rect(0, 88, nav, Math.max(0, height - 88)), {
			source: "families",
			fields: [
				"id",
				"title",
				"available",
				"count",
				"level"
			],
			rowHeight: 52,
			selectedKey: model.family,
			keyField: "id",
			resetKey: model.query + "|" + model.category
		}));
	} else nodes.push(node("Choice", "showcaseFamilyChoice", rect(0, 44, Math.max(0, width - 168), 36), {
		value: model.family,
		options: visible.map((f) => ({
			value: f.id,
			label: f.title
		})),
		enabled: true,
		label: tr("Component showcase"),
		action: { type: "family" }
	}));
	const controlsX = narrow ? Math.max(0, width - 160) : x;
	nodes.push(node("Choice", "showcaseState", rect(controlsX, narrow ? 44 : 0, narrow ? 120 : 160, 36), {
		value: model.state,
		options: states.map((value, i) => ({
			value,
			label: tr(stateLabels[i])
		})),
		label: tr("Component state"),
		enabled: true,
		action: { type: "state" }
	}));
	nodes.push(button("showcaseReset", rect(narrow ? width - 36 : x + 168, narrow ? 44 : 0, 36, 36), tr("Reset"), "refresh", { type: "reset" }, true, { iconOnly: true }));
	if (!narrow) nodes.push(button("showcaseCode", rect(Math.max(x + 212, width - 136), 0, 136, 36), tr(model.code ? "Preview" : "Code example"), "code", { type: "code" }, true, {
		selected: model.code,
		radio: true
	}));
	const content = [], inner = Math.max(0, w - 32), titleHeight = narrow ? lineHeights.hero * 2 : 46;
	content.push(label("showcaseTitle", rect(16, 12, inner, titleHeight), language === "ru" ? family.title : family.label, {
		fontRole: "hero",
		weight: 600,
		wrap: true,
		maxLines: 2,
		verticalAlign: "top",
		role: "heading",
		level: 2
	}));
	content.push(label("showcaseScope", rect(16, titleHeight + 16, inner, 32), tr(live.includes(family.id) ? "Local demo; project data stays unchanged" : "Standalone example not added yet"), {
		fontRole: "secondary",
		color: "secondaryText",
		wrap: true
	}));
	let y = titleHeight + 64;
	if (!visible.length) {
		content.push(label("showcaseNoResults", rect(16, y, inner, 48), tr("No matching components"), { wrap: true }));
		y += 64;
	} else if (live.includes(family.id)) {
		const variants = available(family.id);
		if (variants.length) {
			content.push(node("Choice", "showcaseVariant", rect(16, y, inner, 36), {
				value: model.variant,
				label: language === "ru" ? "Вариант контрола" : "Control variant",
				options: [{
					value: "",
					label: language === "ru" ? "Обзор примеров" : "Example overview"
				}, ...variants.map((row) => ({
					value: row.id,
					label: title(row.id, language)
				}))],
				enabled: true,
				action: { type: "variant" }
			}));
			y += 48;
		}
		const p = model.variant && model.variantModel ? sample(model, inner, language) : families$1.includes(family.id) ? describe$1(model, family.id, inner, language) : describe$2(model, family.id, inner, language);
		if (p.code) {
			if (narrow) content.push(button("showcaseCode", rect(16, y, Math.min(inner, 160), 36), tr(model.code ? "Preview" : "Code example"), "code", { type: "code" }, true, {
				selected: model.code,
				radio: true
			}));
			if (narrow) y += 48;
			if (model.code) {
				content.push(node("Code", "showcaseCodeSource", rect(16, y, inner, 260), {
					text: p.code,
					language: "javascript",
					readOnly: true,
					enabled: true
				}));
				y += 276;
			}
		}
		if (!model.code || !p.code) {
			content.push(node("Box", "showcasePreview", rect(16, y, inner, p.height), {
				background: "transparent",
				children: p.nodes,
				clip: false
			}));
			y += p.height + 12;
		}
	}
	for (const [title, values] of [["Native controls", family.native], ["Vue controls", family.vue]]) {
		content.push(label("showcaseOwner_" + title, rect(16, y, inner, 22), tr(title), {
			fontRole: "secondary",
			weight: 600
		}));
		y += 26;
		const text = values.join(" · ") || "—", h = Math.max(24, Math.ceil(text.length / Math.max(12, inner / 7)) * 18);
		content.push(label("showcaseNames_" + title, rect(16, y, inner, h), text, {
			wrap: true,
			fontRole: "secondary",
			color: "secondaryText"
		}));
		y += h + 20;
	}
	if (model.last) {
		content.push(label("showcaseEvent", rect(16, y, inner, 28), tr("Action") + ": " + model.last, {
			fontRole: "caption",
			color: "secondaryText"
		}));
		y += 40;
	}
	nodes.push(node("Box", "showcaseSurface", rect(x, top, w, Math.max(0, height - top)), {
		background: "surfaceContainerLowest",
		radius: 8
	}));
	nodes.push(node("Scroll", "showcaseContent", rect(x, top, Math.max(0, w - (y + 8 > height - top ? 12 : 0)), Math.max(0, height - top)), {
		contentHeight: y + 8,
		resetKey: model.family,
		children: content
	}));
	return { nodes };
}
var ComponentShowcase_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "ComponentShowcase",
	setup(__props, { expose: __expose }) {
		const host = ref(null), view = ref(null), size = ref({
			width: 1,
			height: 1
		}), model = ref(initial());
		const scene = computed(() => describe(model.value, catalogue, size.value.width, size.value.height, appearance.language));
		const models$1 = computed(() => ({
			...models(model.value),
			families: families(catalogue, model.value, appearance.language)
		}));
		const views = {
			showcaseVariant: {
				component: _sfc_main$1,
				nodeProps: true,
				props: { onEvent: dispatch }
			},
			showcaseMenu: {
				component: _sfc_main$13,
				nodeProps: true,
				props: { onEvent: dispatch }
			},
			showcaseDialog: {
				component: _sfc_main$12,
				nodeProps: true,
				props: { onEvent: dispatch }
			}
		};
		function dispatch(event) {
			model.value = transition(model.value, event, catalogue);
		}
		__expose({
			dispatch,
			model,
			scene
		});
		let observer;
		onMounted(() => {
			observer = observeFrameSizes(([entry]) => size.value = {
				width: Math.max(1, entry.contentRect.width),
				height: Math.max(1, entry.contentRect.height)
			});
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				ref_key: "host",
				ref: host,
				class: "component-showcase"
			}, [createVNode(_sfc_main$29, {
				ref_key: "view",
				ref: view,
				scene: scene.value,
				models: models$1.value,
				views,
				"describe-cell": (grid, record, row, column) => cell(grid, record, row, column, model.value, unref(appearance).language),
				"describe-row": (list, record) => row(list, record, model.value, unref(appearance).language),
				onEvent: dispatch
			}, null, 8, [
				"scene",
				"models",
				"describe-cell",
				"describe-row"
			])], 512);
		};
	}
}, [["__scopeId", "data-v-f21543c2"]]);
//#endregion
export { ComponentShowcase_default as default };

//# sourceMappingURL=ComponentShowcase.js.map