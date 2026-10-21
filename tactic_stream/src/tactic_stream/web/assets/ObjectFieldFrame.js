import { F as renderSlot, N as openBlock, Z as ref, _ as createElementBlock, b as createVNode, g as createCommentVNode, it as toDisplayString, j as onMounted, k as onBeforeUnmount, m as createBaseVNode, p as computed, rt as normalizeStyle } from "./vue.js";
import { A as appearance, K as metrics, R as controls } from "./index.js";
import { Gt as label, Jt as rect, i as _sfc_main$1, qt as node, r as observeFrameSizes, y as translate } from "./CodeBlock.js";
//#region ../src/tactic_stream/shared_ui/features/objects/fields.ui.mjs
function columnCount(width, count, minimum = 430, maximum = 3, gap = 10) {
	return Math.max(1, Math.min(maximum, Math.max(1, count), Math.floor((width + gap) / (minimum + gap))));
}
function arrange(width, heights, minimum = 430, maximum = 3, gap = 10) {
	const columns = columnCount(width, heights.length, minimum, maximum, gap);
	const cellWidth = Math.max(0, (width - gap * (columns - 1)) / columns);
	const bottoms = Array(columns).fill(0);
	return {
		columns,
		cells: heights.map((height, index) => {
			const column = index % columns, top = bottoms[column];
			bottoms[column] += Math.max(0, height) + gap;
			return rect(column * (cellWidth + gap), top, cellWidth, height);
		}),
		cellWidth,
		height: Math.max(0, Math.max(...bottoms) - gap)
	};
}
function lines(text, width, maximum = Infinity) {
	return Math.min(maximum, Math.max(1, Math.ceil(String(text || "").length * 6 / Math.max(1, width))));
}
function columns(model, width) {
	const m = controls.formField, compact = width < m.compactBreakpoint;
	const labelWidth = compact ? Math.max(0, width - m.padding * 2) : m.labelWidth;
	const textWidth = Math.max(0, labelWidth - m.iconExtent - m.labelSpacing);
	const caption = model.description || model.name || "";
	const captionHeight = lines(caption, textWidth, 2) * 15;
	const labelHeight = Math.max(m.iconExtent, 19 + m.textSpacing + captionHeight + (model.readOnly ? 17 : 0));
	const inputX = compact ? m.padding : m.padding + m.labelWidth + m.columnSpacing;
	return {
		compact,
		labelWidth,
		textWidth,
		caption,
		captionHeight,
		labelHeight,
		inputX,
		inputWidth: Math.max(0, width - inputX - m.padding),
		inputY: m.padding + (compact ? labelHeight + m.rowSpacing : 0)
	};
}
function field(model, width, editorHeight, language) {
	const m = controls.formField;
	const { compact, labelWidth, textWidth, caption, captionHeight, labelHeight, inputX, inputWidth, inputY } = columns(model, width);
	const inputHeight = Math.max(model.minimumHeight || 36, editorHeight || 0);
	const errorHeight = model.error ? lines(model.error, inputWidth) * 15 + m.editorSpacing : 0;
	const height = compact ? inputY + inputHeight + errorHeight + m.padding : Math.max(labelHeight, inputHeight + errorHeight) + m.padding * 2;
	const prefix = "objectField_" + model.name + "_";
	const nodes = [
		node("Box", "sobjectFieldSurface_" + model.name, rect(0, 0, width, height), {
			background: "surfaceContainerLow",
			border: model.error ? "error" : "outlineVariant"
		}),
		node("Box", prefix + "iconSurface", rect(m.padding, m.padding, m.iconExtent, m.iconExtent), {
			background: model.error ? "errorContainer" : "secondaryContainer",
			radius: 10
		}),
		node("Icon", prefix + "icon", rect(m.padding + (m.iconExtent - m.iconSize) / 2, m.padding + (m.iconExtent - m.iconSize) / 2, m.iconSize, m.iconSize), {
			icon: model.icon || "type",
			color: model.error ? "error" : "action"
		}),
		label(prefix + "title", rect(m.padding + m.iconExtent + m.labelSpacing, m.padding, textWidth - (model.required ? 14 : 0), 19), model.title || model.name, {
			fontRole: "bodyLarge",
			weight: 600,
			color: model.error ? "error" : "primaryText"
		}),
		label(prefix + "caption", rect(m.padding + m.iconExtent + m.labelSpacing, m.padding + 19 + m.textSpacing, textWidth, captionHeight), caption, {
			fontRole: "caption",
			color: "secondaryText",
			wrap: true,
			maxLines: 2
		})
	];
	if (model.required) nodes.push(label(prefix + "required", rect(m.padding + labelWidth - 12, m.padding, 12, 19), "*", {
		fontRole: "bodyLarge",
		color: "error",
		weight: 700
	}));
	if (model.readOnly) nodes.push(label(prefix + "readOnly", rect(m.padding + m.iconExtent + m.labelSpacing, m.padding + labelHeight - 15, textWidth, 15), translate("Read only", language), {
		fontRole: "caption",
		color: "secondaryText",
		weight: 600
	}));
	if (model.error) nodes.push(label(prefix + "error", rect(inputX, inputY + inputHeight + m.editorSpacing, inputWidth, errorHeight - m.editorSpacing), model.error, {
		fontRole: "caption",
		color: "error",
		wrap: true,
		role: "alert"
	}));
	return {
		nodes,
		height,
		editor: rect(inputX, inputY, inputWidth, inputHeight),
		compact
	};
}
//#endregion
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
export { arrange as n, _sfc_main as t };

//# sourceMappingURL=ObjectFieldFrame.js.map