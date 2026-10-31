import { A as onMounted, G as withCtx, H as watch, M as openBlock, O as onBeforeUnmount, X as ref, _ as createElementBlock, b as createVNode, g as createCommentVNode, h as createBlock, m as createBaseVNode, nt as normalizeStyle, p as computed } from "./vue.js";
import { T as metrics, b as fontFamily, o as t, s as appearance, t as _sfc_main$1 } from "./AppButton.js";
import { G as node, K as rect, t as _sfc_main$2, w as observeFrameSizes } from "./FrameView.js";
//#region ../src/tactic_stream/shared_ui/controls/menus/action.ui.mjs
function height(record, extent) {
	return record.separator ? 5 : record.header ? 28 : record.status ? 48 : extent;
}
function row(record, width, options) {
	const h = height(record, options.extent), nodes = [];
	if (record.separator) return {
		width,
		height: h,
		nodes: [node("Box", "menuSeparator", rect(0, 2, width, 1), { background: "separator" })]
	};
	const enabled = record.enabled !== false && !record.header;
	const foreground = enabled ? record.checked && record.accent ? record.accent : "primaryText" : "secondaryText";
	nodes.push(node("Box", "menuRowSurface", rect(0, 0, width, h), {
		background: record.checked && record.accent ? record.accent : "primaryText",
		opacity: record.header ? 0 : record.checked && record.accent ? .14 : !enabled ? 0 : options.pressed ? .12 : options.hovered ? .08 : options.focused ? .1 : 0,
		radius: options.radius
	}));
	let left = 10, right = width - 8;
	if (record.secondaryCommand) {
		right -= 15;
		nodes.push(node("Icon", "menuSecondary", rect(right, (h - 15) / 2, 15, 15), {
			icon: record.secondaryIcon || "update",
			color: "secondaryText"
		}));
		right -= 9;
	}
	if (record.children || record.submenuPopup) {
		right -= 16;
		nodes.push(node("Icon", "menuChildren", rect(right, (h - 16) / 2, 16, 16), {
			icon: "chevron-right",
			color: "secondaryText"
		}));
		right -= 9;
	}
	if (record.checked) {
		right -= 18;
		nodes.push(node("Icon", "menuChecked", rect(right, (h - 18) / 2, 18, 18), {
			icon: "check-circle",
			color: record.accent || "action"
		}));
		right -= 9;
	}
	if (Number(record.badgeCount) > 0 || record.showZeroBadge) {
		const count = Number(record.badgeCount || 0), text = count > 99 ? "99+" : String(count), badge = Math.max(18, (options.badgeTextWidth === void 0 ? text.length * 7 : options.badgeTextWidth) + 8);
		right -= badge;
		nodes.push(node("Box", "menuBadge", rect(right, (h - 18) / 2, badge, 18), {
			background: record.badgeUpdated === false ? "secondaryText" : "error",
			radius: 9
		}));
		nodes.push(node("Label", "menuBadgeText", rect(right, (h - 18) / 2, badge, 18), {
			text,
			fontRole: "caption",
			weight: 700,
			align: "center",
			color: "selectedText",
			translate: false
		}));
		right -= 9;
	}
	if (!record.header && record.accent && !record.accentIcon) {
		const extent = record.compactAccent ? 12 : 24;
		if (!record.compactAccent) nodes.push(node("Box", "menuAccentSurface", rect(left, (h - extent) / 2, extent, extent), {
			background: record.accent,
			opacity: .16,
			radius: extent / 2
		}));
		const dot = record.compactAccent ? 8 : 10;
		nodes.push(node("Box", "menuAccent", rect(left + (extent - dot) / 2, (h - dot) / 2, dot, dot), {
			background: record.accent,
			radius: dot / 2
		}));
		left += extent + 9;
	}
	if (!record.header && (record.avatarUrl || record.initials)) {
		nodes.push(node("Preview", "menuAvatar", rect(left, (h - 26) / 2, 26, 26), {
			source: record.avatarUrl || "",
			initials: record.initials || "",
			accent: record.avatarColor || record.accent || "action",
			round: true
		}));
		left += 35;
	} else if (!record.header && record.icon) {
		nodes.push(node("Icon", "menuIcon", rect(left, (h - 16) / 2, 16, 16), {
			icon: record.icon,
			color: record.accentIcon ? record.accent || "action" : "secondaryText"
		}));
		left += 25;
	}
	nodes.push(node("Label", "menuTitle", rect(left, record.status ? 8 : 0, Math.max(0, right - left), record.status ? 16 : h), {
		text: record.title || "",
		translate: false,
		color: foreground,
		fontRole: record.header ? "menuHeading" : "secondary",
		weight: record.header ? 600 : 400
	}));
	if (record.status) nodes.push(node("Label", "menuStatus", rect(left, 24, Math.max(0, right - left), 16), {
		text: record.status,
		translate: false,
		color: record.status === "Experimental" ? "action" : "secondaryText",
		fontRole: "secondary"
	}));
	return {
		width,
		height: h,
		nodes
	};
}
//#endregion
//#region src/controls/ActionRow.vue
var _hoisted_1 = ["data-menu-command"];
var _sfc_main = {
	__name: "ActionRow",
	props: {
		record: {
			type: Object,
			required: true
		},
		suppressFocus: Boolean
	},
	emits: ["triggered"],
	setup(__props) {
		const props = __props;
		const root = ref(null), width = ref(230), hovered = ref(false), pressed = ref(false), focused = ref(false), badgeTextWidth = ref(0);
		const title = computed(() => props.record.translate === false ? props.record.title : t(props.record.title || "", props.record.titleArgs));
		const scene = computed(() => row({
			...props.record,
			title: title.value,
			status: props.record.statusTranslate === false ? props.record.status : t(props.record.status || "")
		}, width.value, {
			extent: metrics(appearance.theme).compactControlHeight,
			radius: metrics(appearance.theme).itemRadius,
			badgeTextWidth: badgeTextWidth.value,
			hovered: hovered.value,
			pressed: pressed.value,
			focused: focused.value && !props.suppressFocus
		}));
		let observer;
		const measureBadge = () => {
			if (props.record.badgeCount === void 0 && !props.record.showZeroBadge) return;
			const context = document.createElement("canvas").getContext("2d");
			context.font = `700 11px "${fontFamily}"`;
			const count = Number(props.record.badgeCount || 0);
			badgeTextWidth.value = context.measureText(count > 99 ? "99+" : String(count)).width;
		};
		watch(() => props.record.badgeCount, measureBadge);
		onMounted(() => {
			measureBadge();
			document.fonts.addEventListener("loadingdone", measureBadge);
			observer = observeFrameSizes((entries) => {
				width.value = entries.at(-1).contentRect.width;
			});
			observer.observe(root.value);
		});
		onBeforeUnmount(() => {
			observer?.disconnect();
			document.fonts.removeEventListener("loadingdone", measureBadge);
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "root",
				ref: root,
				class: "action-row",
				"data-menu-command": __props.record.command,
				style: normalizeStyle({ height: scene.value.height + "px" })
			}, [createVNode(_sfc_main$2, {
				scene: scene.value,
				interactive: false
			}, null, 8, ["scene"]), !__props.record.separator && !__props.record.header ? (openBlock(), createBlock(_sfc_main$1, {
				key: 0,
				class: "action-row-hit frame-hit-target",
				label: title.value,
				"translate-label": false,
				href: __props.record.href,
				target: __props.record.href ? "_blank" : void 0,
				rel: __props.record.href ? "noopener" : void 0,
				disabled: __props.record.enabled === false,
				role: __props.record.role || (__props.record.checked === void 0 ? void 0 : "menuitemradio"),
				"aria-checked": __props.record.checked,
				onPointerenter: _cache[0] || (_cache[0] = ($event) => hovered.value = true),
				onPointerleave: _cache[1] || (_cache[1] = ($event) => hovered.value = pressed.value = false),
				onPointerdown: _cache[2] || (_cache[2] = ($event) => pressed.value = true),
				onPointerup: _cache[3] || (_cache[3] = ($event) => pressed.value = false),
				onPointercancel: _cache[4] || (_cache[4] = ($event) => pressed.value = false),
				onFocus: _cache[5] || (_cache[5] = ($event) => focused.value = true),
				onBlur: _cache[6] || (_cache[6] = ($event) => focused.value = pressed.value = false),
				onClick: _cache[7] || (_cache[7] = ($event) => _ctx.$emit("triggered"))
			}, {
				default: withCtx(() => [..._cache[8] || (_cache[8] = [createBaseVNode("span", {
					hidden: "",
					"aria-hidden": "true"
				}, null, -1)])]),
				_: 1
			}, 8, [
				"label",
				"href",
				"target",
				"rel",
				"disabled",
				"role",
				"aria-checked"
			])) : createCommentVNode("", true)], 12, _hoisted_1);
		};
	}
};
//#endregion
export { row as n, _sfc_main as t };

//# sourceMappingURL=ActionRow.js.map