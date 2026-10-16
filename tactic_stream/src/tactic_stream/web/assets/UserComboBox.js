import { D as nextTick, G as withCtx, N as openBlock, P as renderList, X as ref, _ as createCommentVNode, d as Fragment, et as unref, g as createBlock, h as createBaseVNode, m as computed, rt as toDisplayString, tt as normalizeClass, v as createElementBlock, x as createVNode } from "./vue.js";
import { D as t, I as controls, o as _sfc_main$3, u as _sfc_main$2 } from "./index.js";
import { t as _sfc_main$4 } from "./AppMenu.js";
import { t as ItemPreview_default } from "./ItemPreview.js";
import { t as AppSearchField_default } from "./AppSearchField.js";
//#region src/controls/UserGroupSection.vue
var _sfc_main$1 = {
	__name: "UserGroupSection",
	props: {
		title: String,
		compact: Boolean
	},
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", { class: normalizeClass(["user-group-section", { compact: __props.compact }]) }, [
				createVNode(_sfc_main$2, { name: "MDI_ACCOUNT_GROUP" }),
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
var _hoisted_1 = { class: "user-combo-label" };
var _hoisted_2 = { class: "user-combo-list" };
var _hoisted_3 = { class: "user-combo-copy" };
var _hoisted_4 = { key: 0 };
var _sfc_main = {
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
			return openBlock(), createBlock(_sfc_main$4, {
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
					createBaseVNode("span", _hoisted_1, toDisplayString(current.value.displayName), 1),
					!__props.actionField ? (openBlock(), createBlock(_sfc_main$2, {
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
					return openBlock(), createElementBlock(Fragment, { key: group.title }, [createVNode(_sfc_main$1, {
						title: group.title,
						compact: ""
					}, null, 8, ["title"]), (openBlock(true), createElementBlock(Fragment, null, renderList(group.users, (user) => {
						return openBlock(), createBlock(_sfc_main$3, {
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
								__props.value === user.login ? (openBlock(), createBlock(_sfc_main$2, {
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
export { matchesUser as n, _sfc_main$1 as r, _sfc_main as t };

//# sourceMappingURL=UserComboBox.js.map