import { A as onMounted, B as useModel, G as withCtx, M as openBlock, N as renderList, O as onBeforeUnmount, P as renderSlot, X as ref, _ as createElementBlock, b as createVNode, et as unref, g as createCommentVNode, h as createBlock, m as createBaseVNode, nt as normalizeStyle, p as computed, rt as toDisplayString, tt as normalizeClass, u as Fragment, w as mergeModels } from "./vue.js";
import { F as accentPresets, I as iconSets, L as themes, a as _sfc_main$5, c as colorModes, f as languages, l as effectiveColorMode, m as readableText, o as t, s as appearance, t as _sfc_main$4 } from "./AppButton.js";
import { B as frameContentWidth, H as _sfc_main$6, U as _sfc_main$7, V as observeFrameSizes } from "./FrameView.js";
//#region src/controls/SettingRow.vue
var _hoisted_1$3 = { class: "setting-description" };
var _hoisted_2$2 = ["for"];
var _hoisted_3$2 = { key: 0 };
var _hoisted_4$2 = ["id"];
var _sfc_main$3 = {
	__name: "SettingRow",
	props: {
		controlId: String,
		title: String,
		description: String,
		path: String,
		showDivider: {
			type: Boolean,
			default: true
		}
	},
	setup(__props) {
		const root = ref(null), accessory = ref(null), stacked = ref(false);
		let observer;
		onMounted(() => {
			observer = observeFrameSizes(() => {
				stacked.value = frameContentWidth(root.value) - parseFloat(getComputedStyle(root.value).columnGap) - accessory.value.scrollWidth < 210;
			});
			observer.observe(root.value);
			observer.observe(accessory.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "root",
				ref: root,
				class: normalizeClass(["settings-row configuration-setting", {
					stacked: stacked.value,
					"no-divider": !__props.showDivider
				}])
			}, [createBaseVNode("div", _hoisted_1$3, [
				createBaseVNode("label", { for: __props.controlId }, [createBaseVNode("strong", null, toDisplayString(unref(t)(__props.title)), 1)], 8, _hoisted_2$2),
				__props.path ? (openBlock(), createElementBlock("code", _hoisted_3$2, toDisplayString(__props.path), 1)) : createCommentVNode("", true),
				__props.description ? (openBlock(), createElementBlock("p", {
					key: 1,
					id: __props.controlId + "-help",
					class: "muted"
				}, toDisplayString(unref(t)(__props.description)), 9, _hoisted_4$2)) : createCommentVNode("", true),
				renderSlot(_ctx.$slots, "description")
			]), createBaseVNode("div", {
				ref_key: "accessory",
				ref: accessory,
				class: "setting-control"
			}, [renderSlot(_ctx.$slots, "default")], 512)], 2);
		};
	}
};
//#endregion
//#region src/controls/AccentPresetPicker.vue
var _hoisted_1$2 = ["aria-label"];
var _sfc_main$2 = {
	__name: "AccentPresetPicker",
	props: /*@__PURE__*/ mergeModels({
		options: Array,
		mode: String,
		label: String,
		disabled: Boolean
	}, {
		"modelValue": {},
		"modelModifiers": {}
	}),
	emits: ["update:modelValue"],
	setup(__props) {
		const model = useModel(__props, "modelValue");
		function foreground(hex) {
			return readableText([
				1,
				3,
				5
			].map((index) => parseInt(hex.slice(index, index + 2), 16)));
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				class: "accent-preset-picker",
				role: "group",
				"aria-label": unref(t)(__props.label)
			}, [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.options, (preset) => {
				return openBlock(), createBlock(_sfc_main$4, {
					key: preset.value,
					label: preset.label,
					title: preset.label,
					disabled: __props.disabled,
					"aria-pressed": model.value === preset.value,
					style: normalizeStyle({
						"--preset-base": preset[__props.mode + "Base"],
						"--preset-accent": preset[__props.mode],
						"--preset-text": foreground(preset[__props.mode])
					}),
					onClick: ($event) => model.value = preset.value
				}, {
					default: withCtx(() => [createBaseVNode("span", null, [model.value === preset.value ? (openBlock(), createBlock(_sfc_main$5, {
						key: 0,
						name: "fontawesome-solid:check"
					})) : createCommentVNode("", true)])]),
					_: 2
				}, 1032, [
					"label",
					"title",
					"disabled",
					"aria-pressed",
					"style",
					"onClick"
				]);
			}), 128))], 8, _hoisted_1$2);
		};
	}
};
//#endregion
//#region src/features/configuration/AppearanceSettings.vue
var _hoisted_1$1 = { key: 0 };
var _hoisted_2$1 = { class: "muted" };
var _hoisted_3$1 = {
	key: 0,
	class: "settings-section"
};
var _hoisted_4$1 = { class: "muted" };
var _hoisted_5 = { class: "configuration-group" };
var _hoisted_6 = {
	key: 1,
	class: "settings-section"
};
var _hoisted_7 = { class: "muted" };
var _hoisted_8 = { class: "configuration-group" };
var _hoisted_9 = ["aria-label"];
var _hoisted_10 = { class: "muted" };
var _sfc_main$1 = {
	__name: "AppearanceSettings",
	props: { compact: Boolean },
	setup(__props) {
		const prefix = __props.compact ? "quick-" : "settings-";
		const darkMode = computed({
			get: () => effectiveColorMode.value === "dark",
			set: (value) => {
				appearance.mode = value ? "dark" : "light";
			}
		});
		const animations = [
			{
				key: "clickAnimations",
				label: "Click animations",
				description: "Animate press feedback, ripples, switches, and disclosure controls."
			},
			{
				key: "hoverAnimations",
				label: "Hover animations",
				description: "Animate pointer hover feedback. When disabled, hover states change instantly."
			},
			{
				key: "fadeAnimations",
				label: "Fades and transitions",
				description: "Animate appearing content, view transitions, expansion, and other interface fades."
			},
			{
				key: "popupAnimations",
				label: "Menu and popup animations",
				description: "Animate opening and closing menus, dropdowns, and popups."
			}
		];
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", { class: normalizeClass(["appearance-settings", { "compact-settings": __props.compact }]) }, [
				createBaseVNode("section", { class: normalizeClass({ "settings-section": !__props.compact }) }, [!__props.compact ? (openBlock(), createElementBlock("header", _hoisted_1$1, [createBaseVNode("h2", null, toDisplayString(unref(t)("Appearance")), 1), createBaseVNode("p", _hoisted_2$1, toDisplayString(unref(t)("Choose the interface style, color mode, palettes, and semantic icon set.")), 1)])) : createCommentVNode("", true), createBaseVNode("div", { class: normalizeClass({ "configuration-group": !__props.compact }) }, [
					__props.compact ? (openBlock(), createBlock(_sfc_main$3, {
						key: 0,
						"control-id": unref(prefix) + "language",
						title: "Interface language",
						description: "Changes application labels and help text while project-defined names remain unchanged."
					}, {
						default: withCtx(() => [createVNode(_sfc_main$6, {
							id: unref(prefix) + "language",
							modelValue: unref(appearance).language,
							"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => unref(appearance).language = $event),
							options: unref(languages),
							label: "Interface language",
							"aria-describedby": unref(prefix) + "language-help"
						}, null, 8, [
							"id",
							"modelValue",
							"options",
							"aria-describedby"
						])]),
						_: 1
					}, 8, ["control-id"])) : createCommentVNode("", true),
					!__props.compact ? (openBlock(), createBlock(_sfc_main$3, {
						key: 1,
						"control-id": unref(prefix) + "dark",
						title: "Dark color mode",
						description: "Use dark surfaces and the dark palette assigned to the selected interface style."
					}, {
						default: withCtx(() => [createVNode(_sfc_main$7, {
							id: unref(prefix) + "dark",
							modelValue: darkMode.value,
							"onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => darkMode.value = $event),
							label: "Dark color mode",
							"aria-describedby": unref(prefix) + "dark-help"
						}, null, 8, [
							"id",
							"modelValue",
							"aria-describedby"
						])]),
						_: 1
					}, 8, ["control-id"])) : createCommentVNode("", true),
					createVNode(_sfc_main$3, {
						"control-id": unref(prefix) + "theme",
						title: "Interface style",
						description: unref(themes).find((item) => item.value === unref(appearance).theme).description
					}, {
						default: withCtx(() => [createVNode(_sfc_main$6, {
							id: unref(prefix) + "theme",
							modelValue: unref(appearance).theme,
							"onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => unref(appearance).theme = $event),
							options: unref(themes),
							label: "Interface style",
							"aria-describedby": unref(prefix) + "theme-help"
						}, null, 8, [
							"id",
							"modelValue",
							"options",
							"aria-describedby"
						])]),
						_: 1
					}, 8, ["control-id", "description"]),
					__props.compact ? (openBlock(), createBlock(_sfc_main$3, {
						key: 2,
						"control-id": unref(prefix) + "mode",
						title: "Color mode",
						description: "Choose light or dark surfaces, or follow the system preference."
					}, {
						default: withCtx(() => [createVNode(_sfc_main$6, {
							id: unref(prefix) + "mode",
							modelValue: unref(appearance).mode,
							"onUpdate:modelValue": _cache[3] || (_cache[3] = ($event) => unref(appearance).mode = $event),
							options: unref(colorModes),
							label: "Color mode",
							"aria-describedby": unref(prefix) + "mode-help"
						}, null, 8, [
							"id",
							"modelValue",
							"options",
							"aria-describedby"
						])]),
						_: 1
					}, 8, ["control-id"])) : createCommentVNode("", true),
					!__props.compact ? (openBlock(), createElementBlock(Fragment, { key: 3 }, renderList(["light", "dark"], (mode) => {
						return createVNode(_sfc_main$3, {
							key: mode,
							class: "appearance-palette-row",
							"control-id": unref(prefix) + mode + "-palette",
							title: mode === "light" ? "Light mode palette" : "Dark mode palette",
							description: mode === "light" ? "Base surface and accent used when the application is in light mode." : "Base surface and accent used when the application is in dark mode."
						}, {
							default: withCtx(() => [createVNode(_sfc_main$2, {
								id: unref(prefix) + mode + "-palette",
								modelValue: unref(appearance).themeAccents[unref(appearance).theme][mode],
								"onUpdate:modelValue": ($event) => unref(appearance).themeAccents[unref(appearance).theme][mode] = $event,
								options: unref(accentPresets),
								mode,
								label: unref(t)(mode === "light" ? "Light mode palette" : "Dark mode palette"),
								"aria-describedby": unref(prefix) + mode + "-palette-help"
							}, null, 8, [
								"id",
								"modelValue",
								"onUpdate:modelValue",
								"options",
								"mode",
								"label",
								"aria-describedby"
							])]),
							_: 2
						}, 1032, [
							"control-id",
							"title",
							"description"
						]);
					}), 64)) : createCommentVNode("", true),
					createVNode(_sfc_main$3, {
						"control-id": unref(prefix) + "icons",
						title: "Icon set",
						description: unref(iconSets).find((item) => item.value === unref(appearance).iconSet).description
					}, {
						default: withCtx(() => [createVNode(_sfc_main$6, {
							id: unref(prefix) + "icons",
							modelValue: unref(appearance).iconSet,
							"onUpdate:modelValue": _cache[4] || (_cache[4] = ($event) => unref(appearance).iconSet = $event),
							options: unref(iconSets),
							label: "Icon set",
							"aria-describedby": unref(prefix) + "icons-help"
						}, null, 8, [
							"id",
							"modelValue",
							"options",
							"aria-describedby"
						])]),
						_: 1
					}, 8, ["control-id", "description"]),
					!__props.compact ? (openBlock(), createElementBlock(Fragment, { key: 4 }, renderList(animations, (animation) => {
						return createVNode(_sfc_main$3, {
							key: animation.key,
							"control-id": unref(prefix) + animation.key,
							title: animation.label,
							description: animation.description
						}, {
							default: withCtx(() => [createVNode(_sfc_main$7, {
								id: unref(prefix) + animation.key,
								modelValue: unref(appearance)[animation.key],
								"onUpdate:modelValue": ($event) => unref(appearance)[animation.key] = $event,
								label: animation.label,
								"aria-describedby": unref(prefix) + animation.key + "-help"
							}, null, 8, [
								"id",
								"modelValue",
								"onUpdate:modelValue",
								"label",
								"aria-describedby"
							])]),
							_: 2
						}, 1032, [
							"control-id",
							"title",
							"description"
						]);
					}), 64)) : createCommentVNode("", true)
				], 2)], 2),
				!__props.compact ? (openBlock(), createElementBlock("section", _hoisted_3$1, [createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)("Language")), 1), createBaseVNode("p", _hoisted_4$1, toDisplayString(unref(t)("Choose the language used by the application interface.")), 1)]), createBaseVNode("div", _hoisted_5, [createVNode(_sfc_main$3, {
					"control-id": unref(prefix) + "language",
					title: "Interface language",
					description: "Changes application labels and help text while project-defined names remain unchanged."
				}, {
					default: withCtx(() => [createVNode(_sfc_main$6, {
						id: unref(prefix) + "language",
						modelValue: unref(appearance).language,
						"onUpdate:modelValue": _cache[5] || (_cache[5] = ($event) => unref(appearance).language = $event),
						options: unref(languages),
						label: "Interface language",
						"aria-describedby": unref(prefix) + "language-help"
					}, null, 8, [
						"id",
						"modelValue",
						"options",
						"aria-describedby"
					])]),
					_: 1
				}, 8, ["control-id"])])])) : createCommentVNode("", true),
				!__props.compact ? (openBlock(), createElementBlock("section", _hoisted_6, [
					createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)("Browser preferences")), 1), createBaseVNode("p", _hoisted_7, toDisplayString(unref(t)("Additional browser features remain available alongside the Handler layout.")), 1)]),
					createBaseVNode("div", _hoisted_8, [
						createVNode(_sfc_main$3, {
							"control-id": unref(prefix) + "mode",
							title: "Color mode",
							description: "Choose light or dark surfaces, or follow the system preference."
						}, {
							default: withCtx(() => [createVNode(_sfc_main$6, {
								id: unref(prefix) + "mode",
								modelValue: unref(appearance).mode,
								"onUpdate:modelValue": _cache[6] || (_cache[6] = ($event) => unref(appearance).mode = $event),
								options: unref(colorModes),
								label: "Color mode",
								"aria-describedby": unref(prefix) + "mode-help"
							}, null, 8, [
								"id",
								"modelValue",
								"options",
								"aria-describedby"
							])]),
							_: 1
						}, 8, ["control-id"]),
						createVNode(_sfc_main$3, {
							"control-id": unref(prefix) + "discussion",
							title: "Object notes",
							description: "Open object and process notes in the Task Inspector, or use a separate notes-only window."
						}, {
							default: withCtx(() => [createVNode(_sfc_main$6, {
								id: unref(prefix) + "discussion",
								modelValue: unref(appearance).discussionView,
								"onUpdate:modelValue": _cache[7] || (_cache[7] = ($event) => unref(appearance).discussionView = $event),
								options: [{
									value: "inspector",
									label: "Task Inspector"
								}, {
									value: "notes",
									label: "Standalone notes"
								}],
								label: "Object notes",
								"aria-describedby": unref(prefix) + "discussion-help"
							}, null, 8, [
								"id",
								"modelValue",
								"aria-describedby"
							])]),
							_: 1
						}, 8, ["control-id"]),
						createBaseVNode("div", {
							class: "icon-preview",
							"aria-label": unref(t)("Icon preview")
						}, [(openBlock(), createElementBlock(Fragment, null, renderList([
							"menu",
							"edit",
							"link",
							"activity",
							"connection",
							"queue",
							"history",
							"appearance",
							"settings",
							"search",
							"add"
						], (name) => {
							return createVNode(_sfc_main$5, {
								key: name,
								name
							}, null, 8, ["name"]);
						}), 64))], 8, _hoisted_9)
					]),
					createBaseVNode("p", _hoisted_10, toDisplayString(unref(t)("The system reduced-motion preference takes priority over animation settings.")) + " " + toDisplayString(unref(t)("Graphics backend selection belongs to Qt. The browser controls web rendering.")), 1)
				])) : createCommentVNode("", true)
			], 2);
		};
	}
};
//#endregion
//#region src/features/configuration/AppearanceControls.vue
var _hoisted_1 = { class: "appearance-controls" };
var _hoisted_2 = ["aria-label", "title"];
var _hoisted_3 = {
	key: 0,
	class: "appearance-title"
};
var _hoisted_4 = { class: "appearance-options" };
var _sfc_main = {
	__name: "AppearanceControls",
	props: { compact: Boolean },
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("details", _hoisted_1, [createBaseVNode("summary", {
				class: normalizeClass({ "icon-button": __props.compact }),
				"aria-label": unref(t)("Appearance"),
				title: unref(t)("Appearance")
			}, [createVNode(_sfc_main$5, { name: "appearance" }), !__props.compact ? (openBlock(), createElementBlock("span", _hoisted_3, toDisplayString(unref(t)("Appearance")), 1)) : createCommentVNode("", true)], 10, _hoisted_2), createBaseVNode("div", _hoisted_4, [createVNode(_sfc_main$1, { compact: "" })])]);
		};
	}
};
//#endregion
export { _sfc_main$2 as n, _sfc_main$3 as r, _sfc_main as t };

//# sourceMappingURL=AppearanceControls.js.map