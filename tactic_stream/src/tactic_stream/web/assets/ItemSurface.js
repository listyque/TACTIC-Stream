import { E as nextTick, F as resolveComponent, G as withCtx, M as openBlock, N as renderList, P as renderSlot, X as ref, _ as createElementBlock, b as createVNode, et as unref, g as createCommentVNode, h as createBlock, l as withModifiers, m as createBaseVNode, nt as normalizeStyle, p as computed, rt as toDisplayString, tt as normalizeClass, u as Fragment, z as useId } from "./vue.js";
import { D as t, I as controls, o as _sfc_main$4, tt as _plugin_vue_export_helper_default, u as _sfc_main$5 } from "./index.js";
import { t as _sfc_main$6 } from "./AppMenu.js";
import { t as ItemPreview_default } from "./ItemPreview.js";
//#region src/controls/AppSearchField.vue
var _sfc_main$3 = {
	components: {
		AppButton: _sfc_main$4,
		AppIcon: _sfc_main$5
	},
	props: {
		modelValue: String,
		placeholder: String,
		label: String,
		disabled: Boolean,
		readonly: Boolean,
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
		},
		readonly(value) {
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
			if (this.disabled || this.readonly) return;
			this.close();
			this.$emit("update:modelValue", value);
		},
		async show() {
			await nextTick();
			if (!this.$refs.popup?.isConnected) return;
			if (this.disabled || this.readonly || !this.suggestions.length && !this.error) {
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
var _hoisted_1$2 = [
	"value",
	"placeholder",
	"aria-label",
	"aria-controls",
	"aria-expanded",
	"aria-activedescendant",
	"disabled",
	"readonly"
];
var _hoisted_2$1 = {
	ref: "popup",
	popover: "manual",
	class: "search-suggestions"
};
var _hoisted_3$1 = {
	key: 0,
	role: "status"
};
var _hoisted_4$1 = ["id", "aria-label"];
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
			readonly: $props.readonly,
			onInput: _cache[1] || (_cache[1] = ($event) => $options.edit($event.target.value)),
			onFocus: _cache[2] || (_cache[2] = (...args) => $options.show && $options.show(...args)),
			onKeydown: _cache[3] || (_cache[3] = (...args) => $options.key && $options.key(...args))
		}, null, 40, _hoisted_1$2),
		$props.modelValue ? (openBlock(), createBlock(_component_AppButton, {
			key: 0,
			"icon-only": "",
			label: "Clear search",
			icon: "close",
			disabled: $props.disabled || $props.readonly,
			onClick: _cache[4] || (_cache[4] = ($event) => {
				$options.edit("");
				$options.focus();
			})
		}, null, 8, ["disabled"])) : createCommentVNode("", true),
		createBaseVNode("div", _hoisted_2$1, [$props.error ? (openBlock(), createElementBlock("p", _hoisted_3$1, toDisplayString($options.t($props.error)), 1)) : (openBlock(), createElementBlock("div", {
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
		}), 128))], 8, _hoisted_4$1))], 512)
	], 32);
}
var AppSearchField_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main$3, [["render", _sfc_render]]);
//#endregion
//#region src/controls/UserGroupSection.vue
var _sfc_main$2 = {
	__name: "UserGroupSection",
	props: {
		title: String,
		compact: Boolean
	},
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", { class: normalizeClass(["user-group-section", { compact: __props.compact }]) }, [
				createVNode(_sfc_main$5, { name: "MDI_ACCOUNT_GROUP" }),
				createBaseVNode("span", null, toDisplayString(__props.title === "Ungrouped" ? unref(t)("UNGROUPED") : __props.title?.toUpperCase()), 1),
				_cache[0] || (_cache[0] = createBaseVNode("hr", null, null, -1))
			], 2);
		};
	}
};
//#endregion
//#region src/controls/userSearch.js
function matchesUser(user, query) {
	query = String(query || "").trim().toLowerCase();
	return !query || `${user.login} ${user.displayName || ""} ${user.email || ""} ${(user.groups || []).join(" ")}`.toLowerCase().includes(query);
}
//#endregion
//#region src/controls/UserComboBox.vue
var _hoisted_1$1 = { class: "user-combo-label" };
var _hoisted_2 = { class: "user-combo-list" };
var _hoisted_3 = { class: "user-combo-copy" };
var _hoisted_4 = { key: 0 };
var _sfc_main$1 = {
	__name: "UserComboBox",
	props: {
		value: String,
		options: {
			type: Array,
			default: () => []
		},
		disabled: Boolean,
		actionField: {
			type: Boolean,
			default: true
		},
		label: {
			type: String,
			default: "Assigned to"
		}
	},
	emits: ["change"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const menu = ref(null), query = ref(""), popupWidth = ref(controls.userPicker.popupWidth), expanded = ref(false);
		const users = computed(() => [{
			value: "",
			login: "",
			displayName: t("Not assigned"),
			primaryGroup: "Ungrouped"
		}, ...props.options.filter((option) => option.value).map((option) => ({
			...option,
			login: option.value,
			displayName: option.label || option.displayName || option.value,
			initials: option.initials || (option.label || option.displayName || option.value).trim().split(/\s+/).map((word) => word[0]).filter(Boolean).filter((_, index, parts) => index === 0 || index === parts.length - 1).join("").toUpperCase(),
			primaryGroup: option.primaryGroup || "Ungrouped"
		}))]);
		const current = computed(() => users.value.find((user) => user.login === props.value) || {
			login: props.value,
			displayName: props.value
		});
		const groups = computed(() => {
			const rows = users.value.filter((user) => matchesUser(user, query.value)).sort((a, b) => (a.login ? 1 : 0) - (b.login ? 1 : 0) || a.primaryGroup.toLowerCase().localeCompare(b.primaryGroup.toLowerCase()) || a.displayName.toLowerCase().localeCompare(b.displayName.toLowerCase()));
			return [...new Set(rows.map((user) => user.primaryGroup))].map((title) => ({
				title,
				users: rows.filter((user) => user.primaryGroup === title)
			}));
		});
		function choose(user) {
			if (props.disabled) return;
			emit("change", user.value);
			menu.value.close(true);
		}
		function prepare() {
			query.value = "";
			const font = getComputedStyle(menu.value.$el), context = document.createElement("canvas").getContext("2d");
			context.font = `600 ${font.fontSize} ${font.fontFamily}`;
			popupWidth.value = Math.max(250, menu.value.$el.getBoundingClientRect().width, ...users.value.map((user) => context.measureText(user.displayName).width + 116));
		}
		function opened(event) {
			if (event.target !== menu.value?.$el) return;
			expanded.value = event.newState === "open";
			if (!expanded.value) return;
			nextTick(() => {
				if (menu.value?.open) menu.value.$el.querySelector("input")?.focus();
			});
		}
		function searchKey(event) {
			if (event.key === "ArrowDown") {
				event.preventDefault();
				(menu.value.$el.querySelector(".user-combo-option[aria-checked=\"true\"]") || menu.value.$el.querySelector(".user-combo-option"))?.focus();
			}
		}
		function optionKey(event) {
			if (![
				"ArrowUp",
				"ArrowDown",
				"Home",
				"End"
			].includes(event.key)) return;
			event.preventDefault();
			event.stopPropagation();
			const rows = [...menu.value.$el.querySelectorAll(".user-combo-option")], index = rows.indexOf(event.currentTarget);
			rows[event.key === "Home" ? 0 : event.key === "End" ? rows.length - 1 : (index + (event.key === "ArrowUp" ? -1 : 1) + rows.length) % rows.length]?.focus();
		}
		return (_ctx, _cache) => {
			return openBlock(), createBlock(_sfc_main$6, {
				ref_key: "menu",
				ref: menu,
				class: normalizeClass(["user-combo-box", {
					"user-combo-field": !__props.actionField,
					disabled: __props.disabled
				}]),
				label: __props.label,
				disabled: __props.disabled,
				overlay: "",
				"align-start": "",
				width: popupWidth.value,
				"close-on-select": false,
				onBeforeOpen: prepare,
				onToggle: opened
			}, {
				trigger: withCtx(() => [
					createVNode(ItemPreview_default, {
						source: current.value.avatarUrl,
						"fallback-text": current.value.initials,
						"fallback-icon": "user",
						accent: current.value.avatarColor,
						"preview-size": 22,
						round: "",
						outlined: ""
					}, null, 8, [
						"source",
						"fallback-text",
						"accent"
					]),
					createBaseVNode("span", _hoisted_1$1, toDisplayString(current.value.displayName), 1),
					!__props.actionField ? (openBlock(), createBlock(_sfc_main$5, {
						key: 0,
						class: "user-combo-indicator",
						name: expanded.value ? "MDI_CHEVRON_UP" : "MDI_CHEVRON_DOWN"
					}, null, 8, ["name"])) : createCommentVNode("", true)
				]),
				default: withCtx(() => [createVNode(AppSearchField_default, {
					modelValue: query.value,
					"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => query.value = $event),
					label: "Search users",
					placeholder: unref(t)("Search users"),
					disabled: __props.disabled,
					onKeydown: searchKey,
					onSearch: _cache[1] || (_cache[1] = ($event) => groups.value[0]?.users[0] && choose(groups.value[0].users[0]))
				}, null, 8, [
					"modelValue",
					"placeholder",
					"disabled"
				]), createBaseVNode("div", _hoisted_2, [(openBlock(true), createElementBlock(Fragment, null, renderList(groups.value, (group) => {
					return openBlock(), createElementBlock(Fragment, { key: group.title }, [createVNode(_sfc_main$2, {
						title: group.title,
						compact: ""
					}, null, 8, ["title"]), (openBlock(true), createElementBlock(Fragment, null, renderList(group.users, (user) => {
						return openBlock(), createBlock(_sfc_main$4, {
							key: user.login,
							class: "user-combo-option",
							label: user.displayName,
							role: "radio",
							"aria-checked": __props.value === user.login,
							disabled: __props.disabled,
							onKeydown: optionKey,
							onClick: ($event) => choose(user)
						}, {
							default: withCtx(() => [
								createVNode(ItemPreview_default, {
									source: user.avatarUrl,
									"fallback-text": user.initials,
									"fallback-icon": "user",
									accent: user.avatarColor,
									"preview-size": 32,
									round: "",
									outlined: ""
								}, null, 8, [
									"source",
									"fallback-text",
									"accent"
								]),
								createBaseVNode("span", _hoisted_3, [createBaseVNode("strong", null, toDisplayString(user.displayName), 1), user.login ? (openBlock(), createElementBlock("small", _hoisted_4, toDisplayString(user.login), 1)) : createCommentVNode("", true)]),
								__props.value === user.login ? (openBlock(), createBlock(_sfc_main$5, {
									key: 0,
									class: "user-combo-check",
									name: "MDI_CHECK_CIRCLE"
								})) : createCommentVNode("", true)
							]),
							_: 2
						}, 1032, [
							"label",
							"aria-checked",
							"disabled",
							"onClick"
						]);
					}), 128))], 64);
				}), 128))])]),
				_: 1
			}, 8, [
				"class",
				"label",
				"disabled",
				"width"
			]);
		};
	}
};
//#endregion
//#region src/controls/ItemSurface.vue
var _hoisted_1 = {
	key: 0,
	class: "item-surface-rail",
	"aria-hidden": "true"
};
var _sfc_main = {
	__name: "ItemSurface",
	props: {
		accent: String,
		selected: Boolean,
		cornerRadius: {
			type: Number,
			default: 10
		},
		inset: {
			type: Number,
			default: 1
		},
		normalColor: String,
		selectedColor: String,
		railVisible: {
			type: Boolean,
			default: true
		},
		separatorVisible: {
			type: Boolean,
			default: true
		}
	},
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				class: normalizeClass(["item-surface", {
					selected: __props.selected,
					"without-separator": !__props.separatorVisible
				}]),
				style: normalizeStyle({
					"--item-base": (__props.selected ? __props.selectedColor : __props.normalColor) || void 0,
					"--item-accent": __props.accent || "var(--primary)",
					"--item-corner": __props.cornerRadius + "px",
					"--item-inset": __props.inset + "px"
				})
			}, [__props.railVisible ? (openBlock(), createElementBlock("span", _hoisted_1)) : createCommentVNode("", true), renderSlot(_ctx.$slots, "default")], 6);
		};
	}
};
//#endregion
export { AppSearchField_default as a, _sfc_main$2 as i, _sfc_main$1 as n, matchesUser as r, _sfc_main as t };

//# sourceMappingURL=ItemSurface.js.map