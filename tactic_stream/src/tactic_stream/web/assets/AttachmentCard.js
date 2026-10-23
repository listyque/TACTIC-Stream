import { K as withCtx, N as openBlock, U as watch, Z as ref, b as createVNode, g as createCommentVNode, h as createBlock, it as toDisplayString, j as onMounted, k as onBeforeUnmount, m as createBaseVNode, nt as normalizeClass, p as computed, rt as normalizeStyle } from "./vue.js";
import { c as _sfc_main$1, f as _sfc_main$2 } from "./index.js";
import { w as ItemPreview_default } from "./CodeBlock.js";
//#region src/controls/AttachmentCard.vue
var _hoisted_1 = { class: "attachment-info" };
var _sfc_main = {
	__name: "AttachmentCard",
	props: {
		title: String,
		extension: String,
		previewUrl: String,
		sizeText: String,
		compact: Boolean,
		disabled: Boolean,
		local: Boolean,
		webPreview: {
			type: Boolean,
			default: true
		},
		activationIcon: String,
		activationLabel: String
	},
	emits: ["activated"],
	setup(__props) {
		const props = __props;
		const card = ref(null), width = ref(240), pixels = ref(null);
		const extensionLabel = computed(() => (props.extension || "FILE").slice(0, 5).toUpperCase());
		const imageAttachment = computed(() => [
			"JPG",
			"JPEG",
			"PNG",
			"WEBP",
			"GIF",
			"BMP",
			"TIF",
			"TIFF",
			"TGA",
			"EXR",
			"HDR",
			"SVG",
			"HEIC",
			"AVIF"
		].includes((props.extension || "").toUpperCase()));
		const imageWidth = computed(() => Math.round(props.webPreview ? Math.min(Math.max(0, width.value - 16), pixels.value?.width || Infinity) : Math.max(0, width.value - 16)));
		const imageHeight = computed(() => Math.round(Math.min(360, imageWidth.value * (pixels.value ? pixels.value.height / pixels.value.width : .56))));
		let observer, resizeFrame;
		watch(() => props.previewUrl, () => {
			pixels.value = null;
		});
		function loaded(event) {
			if (!props.compact && event.target.tagName === "IMG") pixels.value = {
				width: event.target.naturalWidth,
				height: event.target.naturalHeight
			};
		}
		onMounted(() => {
			observer = new ResizeObserver((entries) => {
				const next = Math.round(entries[0].contentRect.width);
				if (next > 0 && Math.abs(next - width.value) > 1) {
					cancelAnimationFrame(resizeFrame);
					resizeFrame = requestAnimationFrame(() => {
						width.value = next;
					});
				}
			});
			observer.observe(card.value.$el);
		});
		onBeforeUnmount(() => {
			observer?.disconnect();
			cancelAnimationFrame(resizeFrame);
		});
		return (_ctx, _cache) => {
			return openBlock(), createBlock(_sfc_main$1, {
				ref_key: "card",
				ref: card,
				class: normalizeClass(["attachment-card", {
					compact: __props.compact,
					"image-attachment": imageAttachment.value && !__props.compact
				}]),
				label: __props.activationLabel,
				disabled: __props.disabled,
				onLoadCapture: loaded,
				onClick: _cache[0] || (_cache[0] = ($event) => _ctx.$emit("activated"))
			}, {
				default: withCtx(() => [imageAttachment.value && !__props.compact ? (openBlock(), createBlock(ItemPreview_default, {
					key: 0,
					class: "attachment-image",
					style: normalizeStyle({
						width: imageWidth.value + "px",
						height: imageHeight.value + "px"
					}),
					source: __props.previewUrl,
					"fallback-icon": "image",
					outlined: ""
				}, null, 8, ["style", "source"])) : createCommentVNode("", true), createBaseVNode("span", _hoisted_1, [
					__props.compact || !imageAttachment.value ? (openBlock(), createBlock(ItemPreview_default, {
						key: 0,
						class: "attachment-badge",
						style: normalizeStyle({
							background: imageAttachment.value && __props.previewUrl ? "var(--surface-highest)" : "var(--primary)",
							color: "var(--on-selected)",
							"--preview-text-size": (extensionLabel.value.length > 4 ? 8 : 9) + "px"
						}),
						source: imageAttachment.value ? __props.previewUrl : "",
						"fallback-text": extensionLabel.value,
						round: !imageAttachment.value
					}, null, 8, [
						"style",
						"source",
						"fallback-text",
						"round"
					])) : createCommentVNode("", true),
					createBaseVNode("span", null, [createBaseVNode("strong", null, toDisplayString(__props.title), 1), createBaseVNode("small", null, toDisplayString(imageAttachment.value && !__props.compact ? [extensionLabel.value, __props.sizeText].filter(Boolean).join(" · ") : __props.sizeText), 1)]),
					createVNode(_sfc_main$2, { name: __props.activationIcon || (__props.local ? "MDI_OPEN_IN_NEW" : "download") }, null, 8, ["name"])
				])]),
				_: 1
			}, 8, [
				"class",
				"label",
				"disabled"
			]);
		};
	}
};
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=AttachmentCard.js.map