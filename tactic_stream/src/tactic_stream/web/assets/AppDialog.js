import { A as onMounted, E as nextTick, K as withDirectives, M as openBlock, O as onBeforeUnmount, P as renderSlot, X as ref, _ as createElementBlock, et as unref, g as createCommentVNode, h as createBlock, l as withModifiers, m as createBaseVNode, rt as toDisplayString, tt as normalizeClass } from "./vue.js";
import { o as t, t as _sfc_main$1 } from "./AppButton.js";
import { t as windowDirective, yt as fit } from "./index.js";
import { H as observeFrameSizes } from "./FrameView.js";
//#region src/controls/AppDialog.vue
var _hoisted_1 = ["aria-label"];
var _hoisted_2 = {
	key: 0,
	class: "app-dialog-titlebar"
};
var _hoisted_3 = { class: "app-dialog-content" };
var _sfc_main = {
	__name: "AppDialog",
	props: {
		title: {
			type: String,
			default: ""
		},
		translateTitle: {
			type: Boolean,
			default: true
		},
		windowKind: String,
		modal: {
			type: Boolean,
			default: true
		},
		closeOnEscape: {
			type: Boolean,
			default: true
		},
		closeOnOutside: {
			type: Boolean,
			default: true
		},
		ownerMargin: {
			type: Number,
			default: 24
		}
	},
	emits: ["closed", "rejected"],
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const dialog = ref(null);
		let ownerElement, observer;
		function position() {
			const element = dialog.value;
			if (!element?.open) return;
			const owner = ownerElement?.isConnected ? ownerElement.getBoundingClientRect() : {
				x: 0,
				y: 0,
				width: innerWidth,
				height: innerHeight
			};
			element.style.setProperty("--dialog-owner-width", Math.max(1, owner.width - props.ownerMargin) + "px");
			element.style.setProperty("--dialog-owner-height", Math.max(1, owner.height - props.ownerMargin) + "px");
			const box = element.getBoundingClientRect();
			const fitted = fit({
				x: owner.x + (owner.width - box.width) / 2,
				y: owner.y + (owner.height - box.height) / 2,
				width: box.width,
				height: box.height
			}, {
				x: 0,
				y: 0,
				width: innerWidth,
				height: innerHeight
			});
			Object.assign(element.style, {
				left: fitted.x + "px",
				top: fitted.y + "px",
				right: "auto",
				bottom: "auto",
				margin: "0"
			});
		}
		function reject() {
			emit("rejected");
			dialog.value.close();
		}
		function outside(event) {
			const element = dialog.value;
			if (!element?.open || !props.closeOnOutside) return;
			const box = element.getBoundingClientRect();
			if (event.target === element && (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) || !props.modal && !element.contains(event.target)) reject();
		}
		onMounted(() => {
			document.addEventListener("pointerdown", outside, true);
			window.addEventListener("resize", position);
			window.addEventListener("windowgeometrychange", position);
			observer = observeFrameSizes(position);
			observer.observe(dialog.value);
		});
		onBeforeUnmount(() => {
			observer?.disconnect();
			document.removeEventListener("pointerdown", outside, true);
			window.removeEventListener("resize", position);
			window.removeEventListener("windowgeometrychange", position);
		});
		__expose({
			get open() {
				return !!dialog.value?.open;
			},
			show(owner) {
				if (dialog.value.open) return;
				if (ownerElement) observer?.unobserve(ownerElement);
				ownerElement = owner || document.activeElement?.closest("dialog[open]");
				if (ownerElement) observer?.observe(ownerElement);
				if (props.modal) dialog.value.showModal();
				else dialog.value.show();
				position();
				nextTick(position);
			},
			close: () => dialog.value.close(),
			element: () => dialog.value
		});
		return (_ctx, _cache) => {
			return withDirectives((openBlock(), createElementBlock("dialog", {
				ref_key: "dialog",
				ref: dialog,
				class: normalizeClass(["app-dialog", { "app-dialog-untitled": !__props.title }]),
				"aria-label": __props.translateTitle ? unref(t)(__props.title) : __props.title,
				onCancel: _cache[0] || (_cache[0] = withModifiers(($event) => __props.closeOnEscape && reject(), ["prevent"])),
				onClose: _cache[1] || (_cache[1] = ($event) => emit("closed"))
			}, [__props.title ? (openBlock(), createElementBlock("header", _hoisted_2, [createBaseVNode("h2", null, toDisplayString(__props.translateTitle ? unref(t)(__props.title) : __props.title), 1), __props.windowKind ? (openBlock(), createBlock(_sfc_main$1, {
				key: 0,
				label: "Close",
				icon: "close",
				"icon-only": "",
				onClick: reject
			})) : createCommentVNode("", true)])) : createCommentVNode("", true), createBaseVNode("div", _hoisted_3, [renderSlot(_ctx.$slots, "default")])], 42, _hoisted_1)), [[unref(windowDirective), __props.modal ? __props.windowKind ? {
				type: "dialog",
				kind: __props.windowKind
			} : false : {
				type: __props.windowKind ? "window" : "popup",
				kind: __props.windowKind || ""
			}]]);
		};
	}
};
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=AppDialog.js.map