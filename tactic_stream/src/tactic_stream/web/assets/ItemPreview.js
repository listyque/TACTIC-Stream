import { I as resolveComponent, N as openBlock, _ as createCommentVNode, g as createBlock, nt as normalizeStyle, rt as toDisplayString, tt as normalizeClass, v as createElementBlock } from "./vue.js";
import { K as _plugin_vue_export_helper_default, T as t, c as _sfc_main$1 } from "./index.js";
//#region src/controls/ItemPreview.vue
var _sfc_main = {
	components: { AppIcon: _sfc_main$1 },
	props: {
		source: String,
		file: File,
		fallbackText: String,
		fallbackIcon: String,
		accent: String,
		round: Boolean,
		outlined: Boolean,
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
	computed: { url() {
		return this.localUrl || this.source || "";
	} },
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
var _hoisted_1 = ["src", "alt"];
var _hoisted_2 = {
	key: 1,
	"aria-hidden": "true"
};
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_AppIcon = resolveComponent("AppIcon");
	return openBlock(), createElementBlock("div", {
		class: normalizeClass(["image-picker-preview item-preview", {
			"round-preview": $props.round,
			"outlined-preview": $props.outlined
		}]),
		style: normalizeStyle({
			"--preview-accent": $props.accent || void 0,
			"--preview-icon-size": $props.previewSize == null ? void 0 : ($props.previewSize > 40 ? 22 : 16) + "px",
			"--preview-text-size": $props.previewSize == null ? void 0 : ($props.previewSize > 40 ? 10 : 8) + "px"
		})
	}, [$options.url && !$data.broken ? (openBlock(), createElementBlock("img", {
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
	}, null, 44, _hoisted_1)) : $props.fallbackText ? (openBlock(), createElementBlock("span", _hoisted_2, toDisplayString($props.fallbackText), 1)) : $props.fallbackIcon ? (openBlock(), createBlock(_component_AppIcon, {
		key: 2,
		name: $props.fallbackIcon
	}, null, 8, ["name"])) : createCommentVNode("", true)], 6);
}
var ItemPreview_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { ItemPreview_default as t };

//# sourceMappingURL=ItemPreview.js.map