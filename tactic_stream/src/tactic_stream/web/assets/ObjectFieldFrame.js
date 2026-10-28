import { F as renderSlot, N as openBlock, Z as ref, _ as createElementBlock, b as createVNode, g as createCommentVNode, it as toDisplayString, j as onMounted, k as onBeforeUnmount, m as createBaseVNode, p as computed, rt as normalizeStyle } from "./vue.js";
import { j as appearance, q as metrics } from "./index.js";
import { i as _sfc_main$1, r as observeFrameSizes } from "./CodeBlock.js";
import { n as field } from "./fields.ui.js";
//#region src/features/objects/ObjectFieldFrame.vue
var _hoisted_1 = ["for"];
var _sfc_main = {
	__name: "ObjectFieldFrame",
	props: {
		model: Object,
		inputId: String,
		minimumEditorHeight: Number
	},
	setup(__props) {
		const props = __props;
		const host = ref(null), editor = ref(null), width = ref(0), editorHeight = ref(0);
		const scene = computed(() => field({
			...props.model,
			minimumHeight: Math.max(props.model.minimumHeight || 0, metrics(appearance.theme).controlHeight)
		}, width.value, Math.max(props.minimumEditorHeight || 0, editorHeight.value), appearance.language));
		let observer;
		onMounted(() => {
			const measure = () => {
				width.value = host.value.clientWidth;
				editorHeight.value = editor.value.scrollHeight;
			};
			measure();
			observer = observeFrameSizes(measure);
			observer.observe(host.value);
			observer.observe(editor.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "object-field-frame",
				style: normalizeStyle({
					height: scene.value.height + "px",
					"--object-input-height": __props.minimumEditorHeight ? __props.minimumEditorHeight + "px" : void 0
				})
			}, [
				createVNode(_sfc_main$1, { scene: scene.value }, null, 8, ["scene"]),
				__props.inputId ? (openBlock(), createElementBlock("label", {
					key: 0,
					for: __props.inputId,
					class: "visually-hidden"
				}, toDisplayString(__props.model.title), 9, _hoisted_1)) : createCommentVNode("", true),
				createBaseVNode("div", {
					class: "object-field-editor",
					style: normalizeStyle({
						left: scene.value.editor.x + "px",
						top: scene.value.editor.y + "px",
						width: scene.value.editor.width + "px",
						minHeight: scene.value.editor.height + "px"
					})
				}, [createBaseVNode("div", {
					ref_key: "editor",
					ref: editor,
					class: "object-field-content"
				}, [renderSlot(_ctx.$slots, "default")], 512)], 4)
			], 4);
		};
	}
};
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=ObjectFieldFrame.js.map