import { I as resolveComponent, N as openBlock, _ as createCommentVNode, g as createBlock, nt as normalizeStyle, rt as toDisplayString, tt as normalizeClass, v as createElementBlock } from "./vue.js";
import { D as t, F as blend, L as cssColor, R as cssRoles, U as readableText, et as BusyIndicator_default, j as frameColors, tt as _plugin_vue_export_helper_default, u as _sfc_main$1 } from "./index.js";
//#region src/controls/ItemPreview.vue
var colorProbe;
var variableRoles = Object.fromEntries(Object.entries(cssRoles).map(([role, variable]) => ["var(" + variable + ")", role]));
var _sfc_main = {
	components: {
		AppIcon: _sfc_main$1,
		BusyIndicator: BusyIndicator_default
	},
	props: {
		source: String,
		file: File,
		fallbackText: String,
		fallbackIcon: String,
		accent: String,
		round: Boolean,
		outlined: Boolean,
		selected: Boolean,
		loading: Boolean,
		previewSize: Number,
		fillMode: {
			type: String,
			default: "cover"
		}
	},
	emits: ["ready", "failed"],
	data() {
		return {
			localUrl: "",
			broken: false,
			request: 0
		};
	},
	computed: {
		pending() {
			return this.loading || this.url.startsWith("pending-preview:");
		},
		url() {
			return this.localUrl || this.source || "";
		},
		fallbackPaint() {
			const role = variableRoles[this.accent] || this.accent;
			let accent = frameColors.value[role] || frameColors.value.contentAccent || frameColors.value.action;
			let cssAccent = cssColor(accent);
			if (this.accent && !frameColors.value[role]) {
				colorProbe ||= document.createElement("canvas").getContext("2d");
				colorProbe.clearRect(0, 0, 1, 1);
				colorProbe.fillStyle = "#000000";
				colorProbe.fillStyle = this.accent;
				colorProbe.fillRect(0, 0, 1, 1);
				accent = [...colorProbe.getImageData(0, 0, 1, 1).data].slice(0, 3);
				cssAccent = this.accent;
			}
			const shade = blend(accent, [
				0,
				0,
				0
			], 1 - 1 / (this.round ? 1.35 : 1.65));
			return {
				"--preview-accent": cssAccent,
				color: cssColor(readableText(shade))
			};
		}
	},
	watch: {
		file: {
			immediate: true,
			handler(file) {
				const request = ++this.request;
				this.localUrl = "";
				if (!file) return;
				const reader = new FileReader();
				reader.onload = () => {
					if (request === this.request) this.localUrl = reader.result;
				};
				reader.readAsDataURL(file);
			}
		},
		url() {
			this.broken = false;
		}
	},
	beforeUnmount() {
		this.request++;
	},
	methods: { t }
};
var _hoisted_1 = ["aria-busy"];
var _hoisted_2 = ["src", "alt"];
var _hoisted_3 = {
	key: 2,
	"aria-hidden": "true"
};
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_BusyIndicator = resolveComponent("BusyIndicator");
	const _component_AppIcon = resolveComponent("AppIcon");
	return openBlock(), createElementBlock("div", {
		class: normalizeClass(["image-picker-preview item-preview", {
			"round-preview": $props.round,
			"outlined-preview": $props.outlined,
			"selected-preview": $props.selected
		}]),
		"aria-busy": $options.pending || void 0,
		style: normalizeStyle({
			...$options.fallbackPaint,
			"--preview-icon-size": $props.previewSize == null ? void 0 : ($props.previewSize > 40 ? 22 : 16) + "px",
			"--preview-text-size": $props.previewSize == null ? void 0 : ($props.previewSize > 40 ? 10 : 8) + "px"
		})
	}, [$options.url && !$options.pending && !$data.broken ? (openBlock(), createElementBlock("img", {
		key: 0,
		src: $options.url,
		style: normalizeStyle({ objectFit: $props.fillMode }),
		alt: $options.t("Preview image"),
		loading: "lazy",
		decoding: "async",
		onLoad: _cache[0] || (_cache[0] = ($event) => _ctx.$emit("ready", $event.target)),
		onError: _cache[1] || (_cache[1] = ($event) => {
			$data.broken = true;
			_ctx.$emit("failed");
		})
	}, null, 44, _hoisted_2)) : $options.pending ? (openBlock(), createBlock(_component_BusyIndicator, {
		key: 1,
		running: "",
		style: {
			width: "min(24px,45%)",
			height: "min(24px,45%)"
		}
	})) : $props.fallbackText ? (openBlock(), createElementBlock("span", _hoisted_3, toDisplayString($props.fallbackText), 1)) : $props.fallbackIcon ? (openBlock(), createBlock(_component_AppIcon, {
		key: 3,
		name: $props.fallbackIcon
	}, null, 8, ["name"])) : createCommentVNode("", true)], 14, _hoisted_1);
}
var ItemPreview_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { ItemPreview_default as t };

//# sourceMappingURL=ItemPreview.js.map