import { B as useId, D as nextTick, G as withCtx, I as resolveComponent, N as openBlock, P as renderList, _ as createCommentVNode, d as Fragment, g as createBlock, h as createBaseVNode, rt as toDisplayString, tt as normalizeClass, u as withModifiers, v as createElementBlock, x as createVNode } from "./vue.js";
import { D as t, et as _plugin_vue_export_helper_default, o as _sfc_main$1, u as _sfc_main$2 } from "./index.js";
//#region src/controls/AppSearchField.vue
var _sfc_main = {
	components: {
		AppButton: _sfc_main$1,
		AppIcon: _sfc_main$2
	},
	props: {
		modelValue: String,
		placeholder: String,
		label: String,
		disabled: Boolean,
		suggestions: {
			type: Array,
			default: () => []
		},
		error: String,
		boundary: Object
	},
	emits: [
		"update:modelValue",
		"search",
		"accept",
		"open",
		"dismiss"
	],
	setup() {
		return { listId: useId() };
	},
	data() {
		return {
			opened: false,
			selected: -1
		};
	},
	watch: {
		suggestions() {
			this.selected = -1;
			this.show();
		},
		error() {
			this.show();
		},
		disabled(value) {
			if (value) this.close();
		}
	},
	mounted() {
		this.resize = new ResizeObserver(this.position);
		this.resize.observe(this.$el);
		document.addEventListener("pointerdown", this.outside);
		window.addEventListener("resize", this.position);
	},
	beforeUnmount() {
		clearTimeout(this.blurTimer);
		this.resize.disconnect();
		document.removeEventListener("pointerdown", this.outside);
		window.removeEventListener("resize", this.position);
	},
	methods: {
		t,
		focus() {
			this.$refs.input.focus();
		},
		close() {
			if (this.$refs.popup?.isConnected) this.$refs.popup.hidePopover();
			this.opened = false;
			this.selected = -1;
		},
		outside(event) {
			if (!this.$el.contains(event.target)) this.close();
		},
		blurred() {
			clearTimeout(this.blurTimer);
			this.blurTimer = setTimeout(() => {
				if (!this.$el.contains(document.activeElement)) this.close();
			}, 120);
		},
		edit(value) {
			this.close();
			this.$emit("update:modelValue", value);
		},
		async show() {
			await nextTick();
			if (!this.$refs.popup?.isConnected) return;
			if (this.disabled || !this.suggestions.length && !this.error) {
				this.close();
				return;
			}
			if (document.activeElement !== this.$refs.input) return;
			this.$refs.popup.showPopover();
			this.opened = true;
			this.position();
		},
		position() {
			if (!this.opened) return;
			const field = this.$el.getBoundingClientRect(), area = this.boundary?.getBoundingClientRect();
			const left = Math.max(0, area?.left || 0), right = Math.min(innerWidth, area?.right ?? innerWidth);
			const top = Math.max(0, area?.top || 0), bottom = Math.min(innerHeight, area?.bottom ?? innerHeight);
			const width = Math.min(Math.max(240, field.width), right - left - 8);
			const desired = this.error ? 50 : this.suggestions.length * 34 + 8;
			const below = bottom - field.bottom - 10, above = field.top - top - 10;
			const up = below < Math.min(desired, 180) && above > below;
			const height = Math.min(desired, Math.max(0, up ? above : below));
			Object.assign(this.$refs.popup.style, {
				width: width + "px",
				maxHeight: height + "px",
				left: Math.max(left + 4, Math.min(field.left, right - width - 4)) + "px",
				top: (up ? field.top - height - 6 : field.bottom + 6) + "px"
			});
		},
		async key(event) {
			if (event.isComposing) return;
			if (event.key === "Escape") {
				event.preventDefault();
				event.stopPropagation();
				this.close();
				this.$emit("dismiss");
				return;
			}
			if (event.key === "Enter") {
				event.preventDefault();
				if (this.opened && this.selected >= 0) this.choose(this.selected, event.altKey);
				else {
					this.close();
					this.$emit("search");
				}
			} else if (this.opened && this.suggestions.length && ["ArrowDown", "ArrowUp"].includes(event.key)) {
				event.preventDefault();
				this.selected = event.key === "ArrowDown" ? Math.min(this.suggestions.length - 1, this.selected + 1) : this.selected <= 0 ? this.suggestions.length - 1 : this.selected - 1;
				await nextTick();
				this.$refs.popup.querySelector("#" + CSS.escape(this.listId + "-" + this.selected))?.scrollIntoView({ block: "nearest" });
			}
		},
		choose(index, newTab = false) {
			const record = this.suggestions[index];
			this.close();
			this.focus();
			this.$emit(newTab ? "open" : "accept", record);
		}
	}
};
var _hoisted_1 = [
	"value",
	"placeholder",
	"aria-label",
	"aria-controls",
	"aria-expanded",
	"aria-activedescendant",
	"disabled"
];
var _hoisted_2 = {
	ref: "popup",
	popover: "manual",
	class: "search-suggestions"
};
var _hoisted_3 = {
	key: 0,
	role: "status"
};
var _hoisted_4 = ["id", "aria-label"];
var _hoisted_5 = [
	"id",
	"aria-selected",
	"onPointerenter"
];
var _hoisted_6 = {
	role: "gridcell",
	class: "search-suggestion-content"
};
var _hoisted_7 = { key: 0 };
var _hoisted_8 = { role: "gridcell" };
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_AppIcon = resolveComponent("AppIcon");
	const _component_AppButton = resolveComponent("AppButton");
	return openBlock(), createElementBlock("div", {
		class: "workspace-search app-search-field",
		role: "search",
		onFocusout: _cache[7] || (_cache[7] = (...args) => $options.blurred && $options.blurred(...args))
	}, [
		createVNode(_component_AppIcon, {
			name: "search",
			onClick: _cache[0] || (_cache[0] = ($event) => {
				$options.focus();
				_ctx.$refs.input.select();
			})
		}),
		createBaseVNode("input", {
			ref: "input",
			type: "search",
			role: "combobox",
			enterkeyhint: "search",
			autocomplete: "off",
			value: $props.modelValue,
			placeholder: $props.placeholder,
			"aria-label": $options.t($props.label),
			"aria-autocomplete": "list",
			"aria-haspopup": "grid",
			"aria-controls": $setup.listId,
			"aria-expanded": $data.opened,
			"aria-activedescendant": $data.opened && $data.selected >= 0 ? $setup.listId + "-" + $data.selected : void 0,
			disabled: $props.disabled,
			onInput: _cache[1] || (_cache[1] = ($event) => $options.edit($event.target.value)),
			onFocus: _cache[2] || (_cache[2] = (...args) => $options.show && $options.show(...args)),
			onKeydown: _cache[3] || (_cache[3] = (...args) => $options.key && $options.key(...args))
		}, null, 40, _hoisted_1),
		$props.modelValue ? (openBlock(), createBlock(_component_AppButton, {
			key: 0,
			"icon-only": "",
			label: "Clear search",
			icon: "close",
			disabled: $props.disabled,
			onClick: _cache[4] || (_cache[4] = ($event) => {
				$options.edit("");
				$options.focus();
			})
		}, null, 8, ["disabled"])) : createCommentVNode("", true),
		createBaseVNode("div", _hoisted_2, [$props.error ? (openBlock(), createElementBlock("p", _hoisted_3, toDisplayString($options.t($props.error)), 1)) : (openBlock(), createElementBlock("div", {
			key: 1,
			id: $setup.listId,
			role: "grid",
			"aria-label": $options.t("Search suggestions")
		}, [(openBlock(true), createElementBlock(Fragment, null, renderList($props.suggestions, (record, index) => {
			return openBlock(), createElementBlock("div", {
				id: $setup.listId + "-" + index,
				key: index,
				role: "row",
				class: normalizeClass(["search-suggestion-row", { selected: $data.selected === index }]),
				"aria-selected": $data.selected === index,
				onPointerenter: ($event) => $data.selected = index
			}, [createBaseVNode("div", _hoisted_6, [createVNode(_component_AppButton, {
				"aria-label": record.title,
				title: record.title + (record.description ? " — " + record.description : ""),
				onPointerdown: _cache[5] || (_cache[5] = withModifiers(() => {}, ["prevent"])),
				onClick: ($event) => $options.choose(index),
				onAuxclick: withModifiers(($event) => $event.button === 1 && $options.choose(index, true), ["prevent"])
			}, {
				default: withCtx(() => [
					createVNode(_component_AppIcon, { name: "search" }),
					createBaseVNode("strong", null, toDisplayString(record.title), 1),
					createBaseVNode("span", null, toDisplayString(record.description ? "– " + record.description : ""), 1),
					record.keyword ? (openBlock(), createElementBlock("small", _hoisted_7, "#" + toDisplayString(record.keyword), 1)) : createCommentVNode("", true)
				]),
				_: 2
			}, 1032, [
				"aria-label",
				"title",
				"onClick",
				"onAuxclick"
			])]), createBaseVNode("div", _hoisted_8, [createVNode(_component_AppButton, {
				"icon-only": "",
				icon: "MDI_OPEN_IN_NEW",
				label: "Open result in new tab",
				"aria-label": $options.t("Open {title} in new tab", { title: record.title }),
				disabled: !record.code && record.id == null,
				onPointerdown: _cache[6] || (_cache[6] = withModifiers(() => {}, ["prevent"])),
				onClick: ($event) => $options.choose(index, true)
			}, null, 8, [
				"aria-label",
				"disabled",
				"onClick"
			])])], 42, _hoisted_5);
		}), 128))], 8, _hoisted_4))], 512)
	], 32);
}
var AppSearchField_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { AppSearchField_default as t };

//# sourceMappingURL=AppSearchField.js.map