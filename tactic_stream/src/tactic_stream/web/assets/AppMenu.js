import { D as nextTick, F as renderSlot, G as withCtx, K as withDirectives, M as onUpdated, N as openBlock, R as resolveDynamicComponent, X as ref, _ as createCommentVNode, et as unref, g as createBlock, k as onBeforeUnmount, nt as normalizeStyle, q as isRef, rt as toDisplayString, tt as normalizeClass, u as withModifiers, v as createElementBlock, x as createVNode } from "./vue.js";
import { D as t, c as capturePress, l as ripple, s as tooltipDirective, u as _sfc_main$1 } from "./index.js";
//#region src/controls/AppMenu.vue
var _hoisted_1 = [
	"aria-label",
	"aria-expanded",
	"aria-disabled",
	"tabindex"
];
var _hoisted_2 = { key: 0 };
var _hoisted_3 = {
	key: 0,
	class: "app-button-badge",
	"aria-hidden": "true"
};
var _sfc_main = {
	__name: "AppMenu",
	props: {
		label: String,
		frameComposition: Boolean,
		showLabel: Boolean,
		compactTrigger: Boolean,
		icon: {
			type: String,
			default: "more"
		},
		badgeCount: {
			type: Number,
			default: 0
		},
		closeOnSelect: {
			type: Boolean,
			default: true
		},
		boundary: Object,
		anchor: Object,
		alignStart: Boolean,
		centered: Boolean,
		disabled: Boolean,
		inline: Boolean,
		overlay: Boolean,
		modal: Boolean,
		submenu: Boolean,
		width: Number,
		maxHeight: Number
	},
	emits: ["before-open"],
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const menu = ref(null);
		const trigger = ref(null);
		const expanded = ref(false);
		const panelElement = ref(null);
		let point = null;
		let returnTarget = null;
		let hoverTimer = null;
		let focusEdge = null;
		function cancelHover() {
			clearTimeout(hoverTimer);
		}
		function hoverSubmenu() {
			if (!props.submenu || props.disabled) return;
			clearTimeout(hoverTimer);
			hoverTimer = setTimeout(() => {
				if (menu.value.parentElement.closest("details")?.open) menu.value.open = true;
			}, parseFloat(getComputedStyle(menu.value).getPropertyValue("--motion-medium")) || 0);
		}
		function activate(event) {
			if (props.disabled) {
				event.preventDefault();
				return;
			}
			if (!props.submenu) return;
			event.preventDefault();
			clearTimeout(hoverTimer);
			menu.value.open = true;
		}
		function close(focus = false) {
			clearTimeout(hoverTimer);
			if (props.inline || !menu.value) return;
			menu.value.open = false;
			expanded.value = false;
			if (props.modal && panelElement.value.open) panelElement.value.close();
			if (props.overlay && !props.modal && panelElement.value?.matches(":popover-open")) panelElement.value.hidePopover();
			if (focus) (returnTarget?.isConnected ? returnTarget : props.anchor?.isConnected ? props.anchor : trigger.value)?.focus();
		}
		function outside(event) {
			if (menu.value && !menu.value.contains(event.target) && !props.anchor?.contains(event.target)) close();
		}
		function escape(event) {
			if (event.key !== "Escape" || event.defaultPrevented || !menu.value.open || props.inline || menu.value.querySelector("details[open]")) return;
			const dialog = event.target.closest("dialog");
			if (dialog && dialog !== panelElement.value && !dialog.contains(menu.value)) return;
			event.preventDefault();
			event.stopPropagation();
			close(true);
		}
		function position() {
			const panel = menu.value?.querySelector(".account-panel");
			if (!panel || !menu.value.open) return;
			const boundary = props.boundary?.getBoundingClientRect();
			const viewport = window.visualViewport, keyboardViewport = innerWidth <= 700 && viewport?.scale === 1;
			const viewportTop = keyboardViewport ? viewport.offsetTop : 0, viewportBottom = keyboardViewport ? viewportTop + viewport.height : innerHeight;
			const top = Math.max(viewportTop, boundary?.top || 0), bottom = Math.min(viewportBottom, boundary?.bottom ?? viewportBottom);
			if (props.centered) {
				const left = Math.max(0, boundary?.left || 0), right = Math.min(innerWidth, boundary?.right ?? innerWidth);
				panel.style.maxHeight = Math.max(0, Math.min(props.maxHeight ?? Infinity, bottom - top - 8)) + "px";
				panel.style.left = left + (right - left - panel.offsetWidth) / 2 + "px";
				panel.style.top = top + (bottom - top - panel.offsetHeight) / 2 + "px";
			} else if (props.overlay || props.modal) {
				const triggerBox = (props.anchor || trigger.value).getBoundingClientRect();
				panel.style.left = Math.max(4, props.submenu ? triggerBox.right + 6 : point?.x ?? (props.alignStart ? triggerBox.left : triggerBox.right - panel.offsetWidth)) + "px";
				const anchorTop = point?.y ?? triggerBox.top, anchorBottom = point?.y ?? triggerBox.bottom;
				const below = bottom - anchorBottom - 8, above = anchorTop - top - 8;
				const up = !props.modal && panel.scrollHeight > below && above > below;
				panel.style.maxHeight = Math.max(0, Math.min(props.maxHeight ?? Infinity, props.modal ? bottom - top - 8 : up ? above : below)) + "px";
				if (props.overlay && !props.modal) panel.style.overflowY = "auto";
				panel.style.top = (props.submenu ? triggerBox.top - 6 : up ? anchorTop - panel.offsetHeight - 4 : anchorBottom + 4) + "px";
				if (props.submenu) {
					panel.style.maxHeight = Math.max(0, Math.min(props.maxHeight ?? Infinity, bottom - top - 8)) + "px";
					if (triggerBox.right + 6 + panel.offsetWidth > (boundary?.right ?? innerWidth)) panel.style.left = Math.max(4, triggerBox.left - panel.offsetWidth - 6) + "px";
				}
			}
			panel.style.translate = "";
			const left = Math.max(0, boundary?.left || 0), right = Math.min(innerWidth, boundary?.right ?? innerWidth);
			if (boundary) panel.style.maxWidth = Math.max(0, right - left - 8) + "px";
			const box = panel.getBoundingClientRect(), style = getComputedStyle(panel);
			const scale = parseFloat(style.scale) || 1;
			const [originX, originY] = style.transformOrigin.split(" ").map(parseFloat);
			const x = box.left - originX * (1 - scale), y0 = box.top - originY * (1 - scale);
			const bounds = {
				left: x,
				top: y0,
				right: x + parseFloat(style.width),
				bottom: y0 + parseFloat(style.height)
			};
			const y = Math.max(top + 4 - bounds.top, Math.min(0, bottom - 4 - bounds.bottom));
			panel.style.translate = Math.max(left + 4 - bounds.left, Math.min(0, right - 4 - bounds.right)) + "px " + y + "px";
		}
		function items() {
			return [...panelElement.value.querySelectorAll("button:not(:disabled):not([data-menu-secondary]), a[href], .workspace-menu > summary")].filter((item) => item.getClientRects().length && item.getAttribute("aria-disabled") !== "true" && (item.tagName === "SUMMARY" ? item.parentElement.parentElement.closest(".workspace-menu") : item.closest(".workspace-menu")) === menu.value);
		}
		function move(event) {
			if (props.disabled) {
				event.preventDefault();
				return;
			}
			if (props.inline) return;
			if (event.key === "Escape" && menu.value.open && !menu.value.querySelector("details[open]")) {
				event.preventDefault();
				event.stopPropagation();
				close(true);
				return;
			}
			if (event.key === "ArrowLeft" && props.submenu && menu.value.open) {
				event.preventDefault();
				event.stopPropagation();
				close(true);
				return;
			}
			if (event.key === "ArrowRight" && event.target.tagName === "SUMMARY" && event.target.parentElement !== menu.value) {
				event.preventDefault();
				event.stopPropagation();
				const child = event.target.parentElement;
				child.open = true;
				nextTick(() => child.querySelector(".account-panel button:not(:disabled)")?.focus());
				return;
			}
			if (event.target.closest("input, select, textarea, [role=\"combobox\"]")) return;
			if (![
				"ArrowDown",
				"ArrowUp",
				"Home",
				"End"
			].includes(event.key)) return;
			event.preventDefault();
			const backwards = event.key === "ArrowUp" || event.key === "End";
			if (!menu.value.open) {
				focusEdge = backwards ? "last" : "first";
				menu.value.open = true;
				toggled();
				return;
			}
			const buttons = items();
			const active = document.activeElement;
			const index = buttons.indexOf(active?.matches("[data-menu-secondary]") ? active.parentElement.querySelector("[data-menu-primary]") : active);
			buttons[event.key === "Home" ? 0 : event.key === "End" ? buttons.length - 1 : index < 0 ? backwards ? buttons.length - 1 : 0 : (index + (backwards ? -1 : 1) + buttons.length) % buttons.length]?.focus();
		}
		function toggled() {
			if (!menu.value) return;
			if (menu.value.open && !expanded.value) emit("before-open");
			expanded.value = menu.value.open;
			if (!menu.value.open) {
				point = null;
				for (const child of menu.value.querySelectorAll("details[open]")) child.open = false;
			}
			document.removeEventListener("pointerdown", outside);
			document.removeEventListener("keydown", escape, true);
			document.removeEventListener("scroll", position, true);
			window.removeEventListener("resize", position);
			window.visualViewport?.removeEventListener("resize", position);
			window.visualViewport?.removeEventListener("scroll", position);
			window.removeEventListener("windowgeometrychange", position);
			if (menu.value.open) {
				if (props.submenu) {
					for (const sibling of menu.value.parentElement.querySelectorAll(":scope > details[open]")) if (sibling !== menu.value) sibling.open = false;
				}
				if (props.modal && !panelElement.value.open) panelElement.value.showModal();
				else if (props.overlay && !props.modal && !panelElement.value.matches(":popover-open")) panelElement.value.showPopover();
				document.addEventListener("pointerdown", outside);
				document.addEventListener("keydown", escape, true);
				window.addEventListener("resize", position);
				window.visualViewport?.addEventListener("resize", position);
				window.visualViewport?.addEventListener("scroll", position);
				position();
				if (focusEdge) {
					const buttons = items();
					(focusEdge === "last" ? buttons.at(-1) : buttons[0])?.focus();
					focusEdge = null;
				} else if (props.frameComposition) nextTick(() => items()[0]?.focus());
				if (props.submenu && document.activeElement === trigger.value) nextTick(() => items()[0]?.focus());
				if (!trigger.value.getClientRects().length) nextTick(() => (panelElement.value.querySelector("input:not([type=\"hidden\"]):not(:disabled), textarea:not(:disabled)") || items()[0])?.focus());
				window.addEventListener("windowgeometrychange", position);
				if (props.overlay) document.addEventListener("scroll", position, true);
			} else if (props.modal && panelElement.value.open) panelElement.value.close();
			else if (props.overlay && !props.modal && panelElement.value.matches(":popover-open")) panelElement.value.hidePopover();
		}
		function backdrop(event) {
			if (!props.modal || event.target !== panelElement.value) return;
			const box = panelElement.value.getBoundingClientRect();
			if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) close(true);
		}
		function selected(event) {
			if (!menu.value) return;
			const action = event.target.closest("button, a[href]");
			if (action && !props.closeOnSelect) event.stopPropagation();
			if (props.closeOnSelect && action && !action.closest("[role=\"combobox\"]")) close(menu.value.contains(document.activeElement));
		}
		onUpdated(() => {
			if (props.disabled && menu.value?.open) close();
			else position();
		});
		__expose({
			close,
			openAt(event) {
				point = {
					x: event.clientX,
					y: event.clientY
				};
				returnTarget = event.target?.closest("[tabindex],button,a");
				menu.value.open = true;
				nextTick(() => {
					position();
					if (trigger.value?.getClientRects().length) trigger.value.focus();
				});
			},
			focusTrigger() {
				trigger.value?.focus();
			},
			get open() {
				return menu.value?.open;
			},
			set open(value) {
				if (menu.value) menu.value.open = value;
			}
		});
		onBeforeUnmount(() => {
			clearTimeout(hoverTimer);
			document.removeEventListener("pointerdown", outside);
			document.removeEventListener("keydown", escape, true);
			document.removeEventListener("scroll", position, true);
			window.removeEventListener("resize", position);
			window.visualViewport?.removeEventListener("resize", position);
			window.visualViewport?.removeEventListener("scroll", position);
			window.removeEventListener("windowgeometrychange", position);
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("details", {
				ref_key: "menu",
				ref: menu,
				class: normalizeClass(["workspace-menu", {
					"inline-menu": __props.inline,
					"frame-menu": __props.frameComposition,
					"labelled-menu": __props.showLabel,
					"compact-trigger": __props.compactTrigger
				}]),
				onKeydown: move,
				onToggle: toggled
			}, [withDirectives((openBlock(), createElementBlock("summary", {
				ref_key: "trigger",
				ref: trigger,
				class: "icon-button",
				"aria-label": unref(t)(__props.label),
				"aria-expanded": expanded.value,
				"aria-disabled": __props.disabled || void 0,
				tabindex: __props.disabled ? -1 : 0,
				onClick: activate,
				onPointerenter: hoverSubmenu,
				onPointerleave: cancelHover,
				onPointerdown: _cache[0] || (_cache[0] = ($event) => {
					cancelHover();
					isRef(point) ? point.value = null : point = null;
					unref(capturePress)($event);
					!__props.disabled && unref(ripple)($event);
				})
			}, [renderSlot(_ctx.$slots, "trigger", {}, () => [createVNode(_sfc_main$1, { name: __props.icon }, null, 8, ["name"]), __props.showLabel ? (openBlock(), createElementBlock("span", _hoisted_2, toDisplayString(unref(t)(__props.label)), 1)) : createCommentVNode("", true)]), __props.badgeCount > 0 ? (openBlock(), createElementBlock("span", _hoisted_3, toDisplayString(__props.badgeCount > 99 ? "99+" : __props.badgeCount), 1)) : createCommentVNode("", true)], 40, _hoisted_1)), [[unref(tooltipDirective), unref(t)(__props.label)]]), (openBlock(), createBlock(resolveDynamicComponent(__props.modal ? "dialog" : "div"), {
				ref_key: "panelElement",
				ref: panelElement,
				class: "account-panel",
				style: normalizeStyle(__props.width ? { width: "min(" + __props.width + "px, calc(100dvw - " + (__props.frameComposition ? 8 : 16) + "px))" } : void 0),
				"aria-label": __props.modal ? unref(t)(__props.label) : void 0,
				popover: __props.overlay && !__props.modal ? "manual" : void 0,
				onCancel: _cache[1] || (_cache[1] = withModifiers(($event) => close(true), ["prevent", "stop"])),
				onPointerdown: backdrop,
				onClick: selected,
				onTransitionend: withModifiers(position, ["self"])
			}, {
				default: withCtx(() => [renderSlot(_ctx.$slots, "default")]),
				_: 3
			}, 40, [
				"style",
				"aria-label",
				"popover"
			]))], 34);
		};
	}
};
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=AppMenu.js.map