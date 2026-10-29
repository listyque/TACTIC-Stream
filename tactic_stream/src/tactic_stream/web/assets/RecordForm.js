import { n as arrange, r as __exportAll, t as _sfc_main$6 } from "./ObjectFieldFrame.js";
import { B as useId, C as h, D as nextTick, F as renderSlot, I as resolveComponent, K as withCtx, L as resolveDirective, M as onUpdated, N as openBlock, P as renderList, U as watch, Z as ref, _ as createElementBlock, a as vModelSelect, b as createVNode, g as createCommentVNode, h as createBlock, i as vModelCheckbox, it as toDisplayString, j as onMounted, k as onBeforeUnmount, l as withModifiers, m as createBaseVNode, nt as normalizeClass, o as vModelText, p as computed, q as withDirectives, rt as normalizeStyle, s as vShow, u as Fragment, y as createTextVNode } from "./vue.js";
import { E as textStyles, L as _plugin_vue_export_helper_default, g as controls, o as t, s as appearance, t as _sfc_main$7 } from "./AppButton.js";
import { K as uploadFormFile, _t as mobile, d as formDefinition, k as rpc } from "./index.js";
import { B as node, C as ItemPreview_default, D as _sfc_main$10, E as _sfc_main$13, F as _sfc_main$14, I as _sfc_main$11, L as button, M as _sfc_main$12, N as _sfc_main$9, R as label, V as rect, n as observeFrameSizes, r as _sfc_main$8, v as translate } from "./resize.js";
import { n as qtLabelTextWidth } from "./textMetrics.js";
import { t as captionHeight } from "./sections.ui.js";
//#region src/features/objects/recordFields.js
function fieldKind(field) {
	if (field.class_name === "tactic.ui.input.text_input_wdg.TextInputWdg") return "TextWdg";
	if (field.class_name === "tactic.ui.input.color_input_wdg.ColorInputWdg") return "ColorInputWdg";
	if (field.class_name === "tactic.ui.input.task_input_wdg.TaskSObjectInputWdg") return "ParentInput";
	if (field.class_name === "tactic.ui.widget.upload_wdg.SimpleUploadWdg") return "FileInput";
	if (field.class_name === "pyasm.widget.input_wdg.UploadWdg") return "MultiUpload";
	if (field.class_name === "tactic.ui.widget.upload_wdg.UploadWdg") return "MultiUpload";
	if (field.class_name === "tactic.ui.widget.calendar_wdg.CalendarInputWdg") return "CalendarInputWdg";
	if (field.class_name === "tactic.ui.widget.calendar_wdg.TimeInputWdg") return "TimeInputWdg";
	if ([
		"tactic.ui.input.pipeline_input_wdg.PipelineInputWdg",
		"tactic.ui.input.project_user_select_wdg.ProjectSelectWdg",
		"tactic.ui.input.process_context_wdg.ProcessInputWdg",
		"tactic.ui.input.process_context_wdg.ReviewProcessInputWdg",
		"tactic.ui.input.search_type_input_wdg.SearchTypeInputWdg",
		"tactic.ui.input.search_type_input_wdg.SearchTypeWithPipelineInputWdg",
		"tactic.ui.input.process_group_select_wdg.ProcessGroupSelectWdg",
		"tactic.ui.widget.misc_input_wdg.TaskStatusSelectWdg"
	].includes(field.class_name)) return field.input?.type === "select" ? "SelectWdg" : field.input?.type === "text" ? "TextWdg" : null;
	if (field.class_name === "tactic.ui.input.process_context_wdg.SubContextInputWdg") return "TextWdg";
	return [
		"TextWdg",
		"TextAreaWdg",
		"CheckboxWdg",
		"SelectWdg",
		"MultiSelectWdg",
		"HiddenWdg",
		"ThumbInputWdg"
	].find((name) => field.class_name === `pyasm.widget.input_wdg.${name}`);
}
function unsupportedField(field) {
	const options = field.options;
	const allowed = [
		"hint",
		"hint_text",
		"default",
		"value",
		"column",
		"read_only",
		"required",
		"size",
		"rows",
		"cols",
		"parent_key",
		"values",
		"labels",
		"query",
		"query_filter",
		"query_limit",
		"values_expr",
		"labels_expr",
		"mode_expr",
		"setting",
		"extra_values",
		"extra_labels",
		"empty",
		"empty_label",
		"persist"
	];
	if (fieldKind(field) === "CalendarInputWdg") allowed.push("show_time", "show_activator", "display_mode");
	if (fieldKind(field) === "TimeInputWdg") allowed.push("time");
	if (fieldKind(field) === "ColorInputWdg") allowed.push("start_color", "css_background");
	if (field.class_name === "tactic.ui.input.pipeline_input_wdg.PipelineInputWdg") allowed.push("use_code");
	if (field.class_name === "tactic.ui.input.process_context_wdg.ProcessInputWdg") allowed.push("context");
	if (field.class_name === "tactic.ui.input.process_context_wdg.ReviewProcessInputWdg") allowed.push("context", "pipeline_code");
	if (field.class_name === "tactic.ui.input.process_group_select_wdg.ProcessGroupSelectWdg") allowed.push("label_attr");
	if (fieldKind(field) === "FileInput") allowed.push("context", "client_action", "icon_size");
	if (fieldKind(field) === "MultiUpload") allowed.push("names", "upload_type", "context", "pipeline", "context_option", "subcontext");
	if (field.class_name === "tactic.ui.widget.upload_wdg.UploadWdg") allowed.push("context_expr", "client_action");
	const multiActions = [
		"MultiUploadAction",
		"pyasm.command.MultiUploadAction",
		"pyasm.command.edit_wdg_action.MultiUploadAction",
		"MultiZipUploadAction",
		"pyasm.command.MultiZipUploadAction",
		"pyasm.command.edit_wdg_action.MultiZipUploadAction"
	];
	const uploadActions = [
		"UploadAction",
		"pyasm.command.UploadAction",
		"pyasm.command.edit_wdg_action.UploadAction"
	];
	const nullActions = [
		"",
		"NullAction",
		"pyasm.command.NullAction",
		"pyasm.command.edit_wdg_action.NullAction"
	];
	return !fieldKind(field) || field.values.length > 1 && fieldKind(field) !== "MultiSelectWdg" || field.values.some((value) => value !== null && typeof value === "object") || Object.keys(options).some((key) => !allowed.includes(key)) || fieldKind(field) === "CheckboxWdg" && options.value || fieldKind(field) === "ColorInputWdg" && options.css_background && options.css_background !== "{$VALUE}" || fieldKind(field) === "CalendarInputWdg" && field.input?.display_mode !== "browser" || fieldKind(field) === "ThumbInputWdg" && !nullActions.includes(field.action.handler || "") || [
		"TimeAction",
		"pyasm.command.TimeAction",
		"pyasm.command.edit_wdg_action.TimeAction"
	].includes(field.action.handler) && fieldKind(field) !== "TimeInputWdg" || fieldKind(field) === "FileInput" && (!uploadActions.includes(field.action.handler || "") || options.client_action) || fieldKind(field) === "MultiUpload" && (field.class_name === "tactic.ui.widget.upload_wdg.UploadWdg" ? ![
		...uploadActions,
		...multiActions,
		...nullActions
	].includes(field.action.handler || "") || options.client_action || options.upload_type || options.names && ![...multiActions, ...nullActions].includes(field.action.handler || "") || field.input.fields.map((item) => item.name).join("|") !== (field.action.options.names || options.names || field.name) : ![...multiActions, ...nullActions].includes(field.action.handler || "") || field.input.arbitrary !== (field.action.options.upload_type === "arbitrary") || field.input.arbitrary && field.input.fields.length !== 1 || !field.input.arbitrary && field.input.fields.map((item) => item.name).join("|") !== (field.action.options.names || field.name)) || fieldKind(field) === "MultiSelectWdg" && ![
		"MultiDatabaseAction",
		"pyasm.command.MultiDatabaseAction",
		"pyasm.command.edit_wdg_action.MultiDatabaseAction"
	].includes(field.action.handler) || fieldKind(field) === "TimeInputWdg" && ![
		"TimeDatabaseAction",
		"tactic.ui.widget.TimeDatabaseAction",
		"tactic.ui.widget.calendar_wdg.TimeDatabaseAction",
		"TimeAction",
		"pyasm.command.TimeAction",
		"pyasm.command.edit_wdg_action.TimeAction"
	].includes(field.action.handler);
}
//#endregion
//#region src/features/objects/ObjectFieldGrid.vue
var _sfc_main$5 = {
	__name: "ObjectFieldGrid",
	setup(__props) {
		const host = ref(null), height = ref(0);
		let observer, frame = 0;
		const observed = /* @__PURE__ */ new Set();
		function schedule() {
			if (!frame) frame = requestAnimationFrame(layout);
		}
		function layout() {
			frame = 0;
			const children = [...host.value.children].filter((child) => child.style.display !== "none");
			const scene = arrange(host.value.clientWidth, children.map((child) => child.offsetHeight));
			children.forEach((child, index) => {
				const box = scene.cells[index];
				Object.assign(child.style, {
					position: "absolute",
					left: box.x + "px",
					top: box.y + "px",
					width: box.width + "px"
				});
			});
			height.value = scene.height;
			for (const child of observed) if (!children.includes(child)) {
				observer.unobserve(child);
				observed.delete(child);
			}
			for (const child of children) if (!observed.has(child)) {
				observer.observe(child);
				observed.add(child);
			}
		}
		onMounted(() => {
			observer = observeFrameSizes(schedule);
			observer.observe(host.value);
			schedule();
		});
		onUpdated(schedule);
		onBeforeUnmount(() => {
			observer?.disconnect();
			cancelAnimationFrame(frame);
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "object-field-grid",
				style: normalizeStyle({ height: height.value + "px" })
			}, [renderSlot(_ctx.$slots, "default")], 4);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/controls/forms/file.ui.mjs
function describe(value, width, language, enabled = true) {
	const tr = (text) => translate(text, language), name = String(value || "").replace(/\\/g, "/").split("/").pop(), actions = name ? 76 : 40;
	const nodes = [
		node("Box", "fileInputSurface", rect(0, 0, width, 44), { background: "surfaceContainerHigh" }),
		label("fileInputName", rect(12, 10, Math.max(0, width - actions - 20), 24), name || tr("No file selected"), {
			color: name ? "primaryText" : "secondaryText",
			toolTip: name || "",
			elideMiddle: true
		}),
		button("fileInputChoose", rect(Math.max(0, width - actions), 6, 32, 32), tr("Choose file"), "attach-file", { type: "choose" }, enabled, {
			iconOnly: true,
			iconAction: true
		})
	];
	if (name) nodes.push(button("fileInputClear", rect(Math.max(0, width - 36), 6, 32, 32), tr("Clear file"), "close", { type: "clear" }, enabled, {
		iconOnly: true,
		iconAction: true
	}));
	return {
		height: 44,
		nodes
	};
}
//#endregion
//#region src/controls/forms/AppFileInput.vue
var _hoisted_1$2 = [
	"aria-label",
	"disabled",
	"required"
];
var _sfc_main$4 = {
	__name: "AppFileInput",
	props: {
		value: String,
		disabled: Boolean,
		label: String,
		required: Boolean
	},
	emits: ["change"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const input = ref(null);
		const host = ref(null), width = ref(0);
		let observer;
		const scene = computed(() => describe(props.value, width.value, appearance.language, !props.disabled));
		onMounted(() => {
			const measure = () => {
				width.value = host.value.clientWidth;
			};
			measure();
			observer = observeFrameSizes(measure);
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		function action(event) {
			if (props.disabled) return;
			if (event.type === "choose") input.value.click();
			else if (event.type === "clear") {
				input.value.value = "";
				emit("change", { target: { files: [] } });
			}
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "app-file-input",
				style: {
					"position": "relative",
					"height": "44px",
					"width": "100%"
				}
			}, [createVNode(_sfc_main$8, {
				scene: scene.value,
				onEvent: action
			}, null, 8, ["scene"]), createBaseVNode("input", {
				ref_key: "input",
				ref: input,
				type: "file",
				hidden: "",
				"aria-label": __props.label,
				disabled: __props.disabled,
				required: __props.required,
				onChange: _cache[0] || (_cache[0] = ($event) => emit("change", $event))
			}, null, 40, _hoisted_1$2)], 512);
		};
	}
};
//#endregion
//#region src/controls/previewImage.js
async function readPreviewImage(file) {
	const url = await new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onerror = reject;
		reader.onload = () => resolve(reader.result);
		reader.readAsDataURL(file);
	});
	await new Promise((resolve, reject) => {
		const image = new Image();
		image.onload = resolve;
		image.onerror = reject;
		image.src = url;
	});
	return url;
}
//#endregion
//#region src/controls/ImagePicker.vue
var _sfc_main$3 = {
	components: {
		AppButton: _sfc_main$7,
		ItemPreview: ItemPreview_default
	},
	props: {
		modelValue: File,
		displayFile: File,
		previewUrl: String,
		fallbackText: String,
		accent: String,
		previewSize: {
			type: Number,
			default: controls.imagePicker.previewSize
		},
		statusText: String,
		description: String,
		inlineErrors: {
			type: Boolean,
			default: true
		},
		required: Boolean,
		disabled: Boolean
	},
	emits: [
		"update:modelValue",
		"validating",
		"error"
	],
	watch: { error(value) {
		this.$emit("error", value);
	} },
	data() {
		return {
			loading: false,
			error: "",
			selection: 0,
			actionsHeight: 36,
			pickerWidth: 0,
			pickerHeight: 0
		};
	},
	mounted() {
		this.resize = new ResizeObserver((entries) => {
			this.actionsHeight = this.$refs.actions.offsetHeight;
			const root = entries.find((entry) => entry.target === this.$el);
			if (root) {
				this.pickerWidth = root.contentRect.width;
				this.pickerHeight = root.contentRect.height;
			}
		});
		this.resize.observe(this.$refs.actions);
		this.resize.observe(this.$el);
	},
	beforeUnmount() {
		this.selection++;
		this.resize?.disconnect();
	},
	computed: {
		previewRowHeight() {
			if (!this.compact) return this.pickerHeight;
			const room = this.pickerHeight - controls.imagePicker.rowSpacing;
			return Math.max(this.previewSize, Math.round(room * this.previewSize / (this.previewSize + this.actionsHeight)));
		},
		actionsRowHeight() {
			return this.compact ? Math.max(this.actionsHeight, this.pickerHeight - controls.imagePicker.rowSpacing - this.previewRowHeight) : this.pickerHeight;
		},
		columns() {
			if (this.compact) return "minmax(0,1fr)";
			if (this.statusText || this.description || this.$slots.default) return `${this.previewSize}px minmax(0,1fr)`;
			const actions = Math.max(this.actionWidth("Choose image"), this.modelValue ? this.actionWidth("Undo image selection") : 0);
			const room = this.pickerWidth - controls.imagePicker.columnSpacing;
			return `${Math.max(this.previewSize, Math.round(room * this.previewSize / (this.previewSize + actions)))}px minmax(${actions}px,1fr)`;
		},
		rows() {
			if (!this.compact) return "1fr";
			return `${this.previewRowHeight}px minmax(min-content,1fr)`;
		},
		compact() {
			return this.pickerWidth < this.previewSize + controls.imagePicker.minimumActionsWidth;
		}
	},
	methods: {
		t,
		pixelCentre(rowHeight, contentHeight) {
			const offset = (rowHeight - contentHeight) / 2;
			return { transform: `translateY(${Math.round(offset) - offset}px)` };
		},
		actionWidth(label) {
			const sizing = controls.button;
			const family = getComputedStyle(document.documentElement).fontFamily;
			const text = qtLabelTextWidth(t(label), `600 ${textStyles.body}px ${family}`);
			return Math.max(sizing.minimumWidth, Math.ceil(text) + sizing.iconSize + sizing.spacing + sizing.iconPadding + sizing.padding);
		},
		actionStyle(label) {
			return { width: this.actionWidth(label) + "px" };
		},
		async choose(event) {
			const file = event.target.files[0];
			event.target.value = "";
			if (!file) return;
			const selection = ++this.selection;
			this.loading = true;
			this.$emit("validating", true);
			this.error = "";
			try {
				await readPreviewImage(file);
				if (selection === this.selection) {
					this.loading = false;
					this.$emit("validating", false);
					if (!this.disabled) this.$emit("update:modelValue", file);
				}
			} catch {
				if (selection === this.selection) this.error = "The selected preview is not a readable image";
			} finally {
				if (selection === this.selection) {
					this.loading = false;
					this.$emit("validating", false);
				}
			}
		}
	}
};
var _hoisted_1$1 = ["aria-busy"];
var _hoisted_2$1 = {
	key: 0,
	class: "image-picker-status"
};
var _hoisted_3$1 = {
	key: 1,
	class: "image-picker-description"
};
var _hoisted_4$1 = [
	"disabled",
	"required",
	"aria-label"
];
var _hoisted_5$1 = {
	key: 3,
	class: "error",
	role: "alert"
};
function _sfc_render$1(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_ItemPreview = resolveComponent("ItemPreview");
	const _component_AppButton = resolveComponent("AppButton");
	return openBlock(), createElementBlock("div", {
		class: normalizeClass(["image-picker", { "image-picker-compact": $options.compact }]),
		"aria-busy": $data.loading,
		style: normalizeStyle({ "--image-picker-preview-size": $props.previewSize + "px" })
	}, [createBaseVNode("div", {
		class: "image-picker-layout",
		style: normalizeStyle({
			gridTemplateColumns: $options.columns,
			gridTemplateRows: $options.rows
		})
	}, [createVNode(_component_ItemPreview, {
		"data-image-picker-part": "Preview",
		style: normalizeStyle($options.pixelCentre($options.previewRowHeight, $props.previewSize)),
		file: $props.modelValue || $props.displayFile,
		source: $props.previewUrl,
		"fallback-text": $props.fallbackText,
		accent: $props.accent || "var(--primary)",
		"preview-size": $props.previewSize,
		outlined: "",
		"fill-mode": "cover"
	}, null, 8, [
		"style",
		"file",
		"source",
		"fallback-text",
		"accent",
		"preview-size"
	]), createBaseVNode("div", {
		ref: "actions",
		class: "image-picker-actions",
		style: normalizeStyle($options.pixelCentre($options.actionsRowHeight, $data.actionsHeight))
	}, [
		$props.statusText ? (openBlock(), createElementBlock("p", _hoisted_2$1, toDisplayString($options.t($props.statusText)), 1)) : createCommentVNode("", true),
		$props.description ? (openBlock(), createElementBlock("p", _hoisted_3$1, toDisplayString($options.t($props.description)), 1)) : createCommentVNode("", true),
		renderSlot(_ctx.$slots, "default"),
		createBaseVNode("input", {
			ref: "file",
			type: "file",
			accept: "image/png,image/jpeg,image/webp,image/gif,image/bmp",
			hidden: "",
			disabled: $props.disabled || $data.loading,
			required: $props.required && !$props.modelValue,
			"aria-label": $options.t("Choose preview image"),
			onChange: _cache[0] || (_cache[0] = (...args) => $options.choose && $options.choose(...args))
		}, null, 40, _hoisted_4$1),
		createVNode(_component_AppButton, {
			"data-image-picker-part": "ChoosePreview",
			label: "Choose image",
			style: normalizeStyle($options.actionStyle("Choose image")),
			icon: "add-photo-alternate",
			disabled: $props.disabled || $data.loading,
			onClick: _cache[1] || (_cache[1] = ($event) => _ctx.$refs.file.click())
		}, null, 8, ["style", "disabled"]),
		$props.modelValue ? (openBlock(), createBlock(_component_AppButton, {
			key: 2,
			"data-image-picker-part": "CancelPreview",
			label: "Undo image selection",
			style: normalizeStyle($options.actionStyle("Undo image selection")),
			icon: "undo",
			disabled: $props.disabled || $data.loading,
			onClick: _cache[2] || (_cache[2] = ($event) => {
				$data.error = "";
				_ctx.$emit("update:modelValue", null);
			})
		}, null, 8, ["style", "disabled"])) : createCommentVNode("", true),
		$data.error && $props.inlineErrors ? (openBlock(), createElementBlock("p", _hoisted_5$1, toDisplayString($options.t($data.error)), 1)) : createCommentVNode("", true)
	], 4)], 4)], 14, _hoisted_1$1);
}
var ImagePicker_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main$3, [["render", _sfc_render$1]]);
//#endregion
//#region ../src/tactic_stream/shared_ui/controls/forms/number.mjs
function clamp(value, minimum, maximum, decimals = 0) {
	if (typeof value !== "number" || !isFinite(value)) return null;
	const scale = Math.pow(10, Math.floor(Math.max(0, Math.min(8, decimals))));
	const bounded = Math.max(minimum, Math.min(maximum, value));
	const rounded = Math.round(bounded * scale) / scale;
	return isFinite(rounded) ? rounded : bounded;
}
function step(value, direction, minimum, maximum, increment = 1, decimals = 0) {
	return clamp(value + direction * increment, minimum, maximum, decimals);
}
function separator(language) {
	return String(language).split(/[-_]/)[0] === "ru" ? "," : ".";
}
function pattern(decimals = 0, language = "en") {
	const digits = Math.floor(Math.max(0, Math.min(8, decimals)));
	const point = separator(language) === "," ? "," : "\\.";
	const integer = "(?:\\d+|\\d{1,3}(?:" + (separator(language) === "," ? "[\xA0  ]" : ",") + "\\d{3})+)";
	return digits ? "^[+-]?(?:" + integer + "(?:" + point + "\\d{0," + digits + "})?|" + point + "\\d{1," + digits + "})$" : "^[+-]?" + integer + "$";
}
function parse(text, decimals = 0, language = "en") {
	const source = String(text);
	if (!new RegExp(pattern(decimals, language)).test(source)) return null;
	const ungrouped = separator(language) === "," ? source.replace(/[\u00a0\u202f ]/g, "") : source.replace(/,/g, "");
	const value = Number(ungrouped.replace(separator(language), "."));
	return isFinite(value) ? value : null;
}
function format(value, decimals = 0, language = "en") {
	const rounded = clamp(value, -Number.MAX_VALUE, Number.MAX_VALUE, decimals);
	if (rounded === null) return "";
	const digits = Math.floor(Math.max(0, Math.min(8, decimals)));
	const parts = rounded.toFixed(digits).split(".");
	if (parts[1]) parts[1] = parts[1].replace(/0+$/, "");
	if (parts.length > 1 && !parts[1]) parts.pop();
	parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, separator(language) === "," ? "\xA0" : ",");
	return parts.join(separator(language));
}
//#endregion
//#region src/controls/forms/AppSpinBox.vue
var _sfc_main$2 = {
	__name: "AppSpinBox",
	props: {
		modelValue: {
			type: Number,
			default: 0
		},
		min: {
			type: Number,
			default: 0
		},
		max: {
			type: Number,
			default: 100
		},
		step: {
			type: Number,
			default: 1
		},
		decimals: {
			type: Number,
			default: 0
		},
		label: String,
		disabled: Boolean,
		readonly: Boolean
	},
	emits: ["update:modelValue"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const formatted = computed(() => format(props.modelValue, props.decimals, appearance.language));
		const text = ref(formatted.value);
		const parsed = computed(() => parse(text.value, props.decimals, appearance.language));
		const invalid = computed(() => parsed.value === null);
		watch(formatted, (value) => {
			text.value = value;
		});
		function accept(value) {
			if (props.disabled || props.readonly) return;
			const next = clamp(value, props.min, props.max, props.decimals);
			if (next === null) return;
			text.value = format(next, props.decimals, appearance.language);
			if (next !== props.modelValue) emit("update:modelValue", next);
		}
		function commit() {
			if (invalid.value) text.value = formatted.value;
			else accept(parsed.value);
		}
		function increment(direction) {
			accept(step(props.modelValue, direction, props.min, props.max, props.step, props.decimals));
		}
		function key(event) {
			if (event.isComposing || props.disabled || props.readonly) return;
			if (![
				"ArrowUp",
				"ArrowDown",
				"Enter",
				"Escape"
			].includes(event.key)) return;
			event.preventDefault();
			if (event.key === "Escape") text.value = formatted.value;
			else if (event.key === "Enter") commit();
			else increment(event.key === "ArrowUp" ? 1 : -1);
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				class: normalizeClass(["app-spin-box", { disabled: __props.disabled }]),
				onKeydown: key
			}, [
				createVNode(_sfc_main$7, {
					"icon-only": "",
					icon: "chevron-down",
					label: "Decrease value",
					disabled: __props.disabled || __props.readonly || __props.modelValue <= __props.min,
					onClick: _cache[0] || (_cache[0] = ($event) => increment(-1))
				}, null, 8, ["disabled"]),
				createVNode(_sfc_main$9, {
					modelValue: text.value,
					"onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => text.value = $event),
					inputmode: "decimal",
					role: "spinbutton",
					label: __props.label,
					disabled: __props.disabled,
					readonly: __props.readonly,
					min: __props.min,
					max: __props.max,
					step: __props.step,
					"aria-valuemin": __props.min,
					"aria-valuemax": __props.max,
					"aria-valuenow": __props.modelValue,
					"error-state": invalid.value,
					onBlur: commit
				}, null, 8, [
					"modelValue",
					"label",
					"disabled",
					"readonly",
					"min",
					"max",
					"step",
					"aria-valuemin",
					"aria-valuemax",
					"aria-valuenow",
					"error-state"
				]),
				createVNode(_sfc_main$7, {
					"icon-only": "",
					icon: "chevron-up",
					label: "Increase value",
					disabled: __props.disabled || __props.readonly || __props.modelValue >= __props.max,
					onClick: _cache[2] || (_cache[2] = ($event) => increment(1))
				}, null, 8, ["disabled"])
			], 34);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/features/objects/editor.ui.mjs
var editor_ui_exports = /* @__PURE__ */ __exportAll({
	batchDrafts: () => batchDrafts,
	batchExample: () => batchExample,
	footer: () => footer,
	header: () => header,
	numberedValue: () => numberedValue,
	tools: () => tools
});
function header(model, width, language) {
	const tr = (text) => translate(text, language), compact = width < 660, height = compact ? 90 : 98, margin = compact ? 16 : 22;
	const publishing = model.mode === "publish", context = publishing ? model.recordKey || tr("New object") : model.parentTitle;
	const actions = model.mode === "insert" ? Math.min(238, Math.max(80, width - margin * 2 - 142)) : 0;
	const refreshX = width - margin - 28, modeX = refreshX - 8 - actions;
	const textWidth = Math.max(0, (model.mode === "insert" ? modeX : refreshX - (model.mode === "edit" ? 60 : 0)) - margin - 57 - 10);
	const nodes = [
		node("Box", "sobjectEditorHeader", rect(0, 0, width, height), { background: "surfaceContainerLow" }),
		node("Box", "sobjectEditorIconSurface", rect(margin, (height - 44) / 2, 44, 44), {
			background: "secondaryContainer",
			children: [node("Icon", "sobjectEditorIcon", rect(11, 11, 22, 22), {
				icon: model.mode === "publish" ? "publish" : "sobject",
				color: "action"
			})]
		}),
		label("sobjectEditorTitle", rect(margin + 57, context ? 14 : 22, textWidth, 24), (model.mode === "publish" ? tr("Publish") : model.title) || tr(model.mode === "edit" ? "Edit record" : "Create record"), {
			fontRole: "bodyLarge",
			weight: 600
		}),
		label("sobjectEditorType", rect(margin + 57, context ? 40 : 48, Math.max(0, width - margin * 2 - 57), 20), model.searchType || "", {
			elideMiddle: true,
			color: "secondaryText"
		})
	];
	if (context) nodes.push(label("sobjectEditorParent", rect(margin + 57, 63, Math.max(0, width - margin * 2 - 57), 18), tr(publishing ? "Object" : "Parent") + ": " + context, {
		fontRole: "caption",
		color: "secondaryText",
		toolTip: context
	}));
	if (model.mode === "insert") nodes.push(node("Segmented", "sobjectCreateMode", rect(modeX, 18, actions, 36), {
		label: tr("Create mode"),
		options: [{
			value: "single",
			label: tr("One"),
			icon: "sobject"
		}, {
			value: "batch",
			label: tr("Multiple"),
			icon: "control-point-duplicate",
			enabled: model.batchAllowed !== false
		}],
		value: model.batchEnabled ? "batch" : "single",
		iconOnly: compact,
		enabled: !model.busy,
		action: { type: "mode" }
	}));
	if (model.mode === "edit") nodes.push(node("Box", "sobjectEditorModeBadge", rect(refreshX - 63, 24, 50, 25), {
		background: "secondaryContainer",
		radius: 12.5,
		children: [label("sobjectEditorModeLabel", rect(4, 3, 42, 19), tr("Edit"), {
			align: "center",
			fontRole: "caption",
			color: "action"
		})]
	}));
	nodes.push(button("sobjectEditorRefresh", rect(refreshX, 22, 28, 28), tr("Reload schema"), "refresh", { type: "refresh" }, !model.busy && !model.dirty && !model.uncertain, {
		iconOnly: true,
		iconAction: true
	}));
	return {
		height,
		nodes
	};
}
function tools(model, width, language) {
	const tr = (text) => translate(text, language), nodes = [];
	let y = 0;
	if (model.error || model.busy) {
		const text = tr(model.error || "Loading data…"), height = Math.max(40, captionHeight(text, Math.max(1, width - 24)) + 20);
		nodes.push(label("sobjectEditorMessage", rect(12, 10, Math.max(0, width - 24), height - 20), text, {
			wrap: true,
			color: model.error ? "error" : "secondaryText",
			role: model.error ? "alert" : "status"
		}));
		y += height + 10;
	}
	if (model.mode === "insert" && model.batchAllowed === false && model.fieldCount) {
		const text = tr(model.batchReason);
		const height = captionHeight(text, Math.max(1, width - 24)) + 12;
		nodes.push(label("sobjectBatchCapability", rect(12, y, Math.max(0, width - 24), height), text, {
			wrap: true,
			fontRole: "caption",
			color: "secondaryText"
		}));
		y += height + 10;
	}
	if (model.batchEnabled && !model.batchPreview) {
		const narrow = width < 660, caption = tr("Place the caret in a text field and insert a number format. Numbers are substituted during preview.") + (model.batchExample ? "  " + tr("Name preview") + ": " + model.batchExample : "");
		const captionY = narrow ? 96 : 56, height = captionY + captionHeight(caption, Math.max(1, width - 28)) + 18;
		const children = [label("sobjectBatchCountLabel", rect(14, 14, narrow ? width - 154 : 150, 32), tr("Number of objects"), {}), node("View", "sobjectBatchCount", rect(narrow ? width - 126 : 174, 14, 112, 32), { view: "batchCount" })];
		const start = narrow ? 14 : Math.max(300, width - 332), cell = narrow ? Math.max(0, (width - 52) / 4) : 70;
		[
			"{n}",
			"{n:02}",
			"{n:03}",
			"{n:04}"
		].forEach((token, index) => children.push(button("sobjectBatchToken_" + index, rect(start + index * (cell + 8), narrow ? 54 : 14, cell, 32), token, "", {
			type: "token",
			value: token
		}, !model.busy, {
			translate: false,
			retainFocus: true
		})));
		children.push(label("sobjectBatchHint", rect(14, captionY, width - 28, height - captionY - 12), caption, {
			wrap: true,
			color: "secondaryText",
			fontRole: "caption"
		}));
		nodes.push(node("Box", "sobjectBatchSetup", rect(0, y, width, height), {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			children
		}));
		y += height + 10;
	}
	if (model.batchPreview) {
		nodes.push(node("Box", "sobjectBatchNavigator", rect(0, y, width, 58), {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			children: [
				button("sobjectBatchPrevious", rect(9, 13, 32, 32), tr("Previous object"), "chevron-left", {
					type: "item",
					value: model.batchIndex - 1
				}, !model.busy && model.batchIndex > 0, { iconOnly: true }),
				label("sobjectBatchPosition", rect(49, 8, Math.max(0, width - 98), 22), translate("Object {index} of {total}", language, {
					index: model.batchIndex + 1,
					total: model.batchTotal
				}), {
					align: "center",
					weight: 600
				}),
				label("sobjectBatchInstructions", rect(49, 31, Math.max(0, width - 98), 18), tr("Edit any fields for this object, then move to the next one."), {
					align: "center",
					fontRole: "caption",
					color: "secondaryText"
				}),
				button("sobjectBatchNext", rect(width - 41, 13, 32, 32), tr("Next object"), "chevron-right", {
					type: "item",
					value: model.batchIndex + 1
				}, !model.busy && model.batchIndex < model.batchTotal - 1, { iconOnly: true })
			]
		}));
		y += 68;
	} else {
		nodes.push(label("sobjectEditorFieldsTitle", rect(0, y, Math.max(0, width - 48), 26), tr("Object fields"), {
			fontRole: "bodyLarge",
			weight: 600
		}), label("sobjectEditorFieldCount", rect(width - 44, y, 44, 26), String(model.fieldCount || 0), {
			align: "right",
			color: "secondaryText"
		}));
		y += 36;
	}
	return {
		height: y,
		nodes
	};
}
function footer(model, width, language) {
	const tr = (text) => translate(text, language), compact = width < 660, margin = compact ? 16 : 22;
	const submit = model.submitLabel || (model.mode === "publish" ? tr("Publish") : model.mode === "edit" ? tr("Save changes") : model.batchPreview ? translate("Create {count} objects", language, { count: model.batchTotal }) : model.batchEnabled ? translate("Preview {count} objects", language, { count: model.batchCount }) : tr("Create"));
	const submitWidth = Math.min(width * .52, Math.max(72, submit.length * 6 + 32)), backWidth = model.batchPreview ? 86 : 0, checkWidth = model.uncertain ? 148 : 0, closeWidth = 72, submitX = width - margin - submitWidth;
	const nodes = [
		node("Box", "sobjectEditorFooter", rect(0, 0, width, 58), {
			background: "surfaceContainer",
			radius: 0
		}),
		button("sobjectEditorCancel", rect(Math.max(margin, submitX - closeWidth - backWidth - checkWidth - 8), 14, closeWidth, 36), tr("Cancel"), "", { type: "cancel" }, !model.busy),
		button("sobjectEditorSubmit", rect(submitX, 14, submitWidth, 36), model.busy ? tr("Saving…") : submit, "", { type: "submit" }, !model.busy && !model.uncertain && model.valid !== false && model.fieldCount > 0 && model.canSave !== false, { highlighted: true })
	];
	if (model.uncertain) nodes.push(button("sobjectEditorCheck", rect(submitX - backWidth - checkWidth - 4, 14, checkWidth - 4, 36), tr("Check saved changes"), "", { type: "check" }, !model.busy));
	if (model.batchPreview) nodes.push(button("sobjectBatchBack", rect(submitX - backWidth - 4, 14, backWidth - 4, 36), tr("Back"), "", { type: "back" }, !model.busy));
	nodes.push(node("Icon", "sobjectEditorValidityIcon", rect(margin, 22, 16, 16), {
		icon: model.valid === false ? "warning" : "check-circle",
		color: model.valid === false ? "error" : "secondaryText"
	}));
	if (!compact) nodes.push(label("sobjectEditorValidity", rect(margin + 24, 16, Math.max(0, submitX - closeWidth - backWidth - checkWidth - margin - 22), 32), tr(model.valid === false ? "Correct the highlighted fields" : "Ready to save"), { color: model.valid === false ? "error" : "secondaryText" }));
	return {
		height: 58,
		nodes
	};
}
function batchDrafts(draft, fields, count) {
	if (!Number.isInteger(count) || count < 2 || count > 100) throw Error("Choose between 2 and 100 objects");
	return Array.from({ length: count }, (_, index) => {
		const result = JSON.parse(JSON.stringify(draft));
		for (const field of fields) if (!field.readOnly && ["string", "multiline"].includes(field.type) && typeof result[field.name] === "string") result[field.name] = numberedValue(result[field.name], index + 1);
		return result;
	});
}
function numberedValue(value, number) {
	return String(value).replace(/\{n(?::0([1-9]))?\}/g, (_, digits) => String(number).padStart(Number(digits) || 0, "0"));
}
function batchExample(value, count) {
	return /\{n(?::0([1-9]))?\}/.test(value) ? numberedValue(value, 1) + " … " + numberedValue(value, count) : "";
}
//#endregion
//#region src/features/objects/ObjectEditorSurface.vue
var _sfc_main$1 = {
	__name: "ObjectEditorSurface",
	props: {
		model: Object,
		part: String
	},
	emits: ["event"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const host = ref(null), width = ref(0);
		let observer;
		const scene = computed(() => editor_ui_exports[props.part](props.model, width.value, appearance.language));
		const views = { batchCount: { component: (_, context) => h(_sfc_main$2, {
			...context.attrs,
			modelValue: props.model.batchCount,
			min: 2,
			max: 100,
			label: "Number of objects",
			disabled: props.model.busy,
			"onUpdate:modelValue": (value) => emit("event", {
				type: "count",
				value
			})
		}) } };
		onMounted(() => {
			const measure = () => {
				width.value = host.value.clientWidth;
			};
			measure();
			observer = observeFrameSizes(measure);
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				ref_key: "host",
				ref: host,
				class: "object-editor-surface",
				style: normalizeStyle({ height: scene.value.height + "px" })
			}, [createVNode(_sfc_main$8, {
				scene: scene.value,
				views,
				onEvent: _cache[0] || (_cache[0] = ($event) => emit("event", $event))
			}, null, 8, ["scene"])], 4);
		};
	}
};
var fields_default = { icons: {
	"string": "type",
	"integer": "type",
	"float": "type",
	"multiline": "description",
	"bool": "task-alt",
	"enum": "view-list",
	"user": "person",
	"project": "workspaces",
	"process": "process",
	"pipeline": "workflow",
	"status": "status",
	"date": "calendar-month",
	"datetime": "calendar-month",
	"parent": "link",
	"preview": "image-edit",
	"thumbnail": "image",
	"password": "visibility-off",
	"unsupported": "warning"
} };
//#endregion
//#region src/features/objects/RecordForm.vue
var _sfc_main = {
	setup() {
		return { formId: useId() };
	},
	components: {
		AppDateField: _sfc_main$10,
		AppSwitch: _sfc_main$11,
		AppColorInput: _sfc_main$12,
		AppButton: _sfc_main$7,
		AppTextField: _sfc_main$9,
		AppTextArea: _sfc_main$13,
		AppSelect: _sfc_main$14,
		ObjectFieldFrame: _sfc_main$6,
		ObjectFieldGrid: _sfc_main$5,
		AppFileInput: _sfc_main$4,
		ImagePicker: ImagePicker_default,
		ObjectEditorSurface: _sfc_main$1
	},
	props: {
		ticket: String,
		project: String,
		searchType: String,
		modal: Boolean,
		editView: {
			type: String,
			default: "edit"
		},
		insertView: {
			type: String,
			default: "insert"
		},
		ignoreFields: {
			type: Array,
			default: () => []
		}
	},
	emits: ["saved"],
	data() {
		return {
			createBatch: false,
			batchCount: 2,
			batchIndex: -1,
			batchDrafts: [],
			batchSource: {},
			lastTextField: null,
			definition: null,
			context: null,
			draft: {},
			baseline: {},
			loading: false,
			saving: false,
			error: "",
			discard: false,
			uncertain: false,
			request: 0,
			files: {},
			validatingFiles: {},
			selectedFields: [],
			instanceRelation: null,
			operation: "",
			formSearchKey: "",
			windowOpenArgs: []
		};
	},
	computed: {
		batchCreationAllowed() {
			return !!this.definition && this.operation !== "publish" && this.definition.mode === "insert" && !this.instanceRelation && this.definition.fields.every((field) => this.readOnly(field) || ["HiddenWdg", "ParentInput"].includes(this.kind(field)) || [
				"TextWdg",
				"TextAreaWdg",
				"SelectWdg",
				"CheckboxWdg",
				"HiddenWdg",
				"ParentInput",
				"ColorInputWdg"
			].includes(this.kind(field)) && [
				"",
				"DatabaseAction",
				"pyasm.command.DatabaseAction",
				"pyasm.command.edit_wdg_action.DatabaseAction"
			].includes(field.action.handler || ""));
		},
		editorModel() {
			return {
				title: this.t(this.operation === "publish" ? "Publish" : this.batch ? "Edit selected" : this.definition?.mode === "edit" ? "Edit record" : "Create record"),
				searchType: this.searchType,
				mode: this.operation || this.definition?.mode || "insert",
				recordKey: this.formSearchKey,
				parentTitle: this.definition?.parent_key || "",
				fieldCount: this.definition?.fields.filter((field) => this.kind(field) !== "HiddenWdg").length || 0,
				busy: this.loading || this.saving,
				error: "",
				uncertain: this.uncertain,
				valid: !this.blocked && this.contextValid,
				canSave: !this.fileValidating && this.fieldsToSave.length > 0 && (this.definition?.mode !== "edit" || this.dirty),
				dirty: this.dirty,
				batchEnabled: this.createBatch,
				batchAllowed: this.batchCreationAllowed,
				batchReason: "Batch creation is available for database fields. Uploads and custom actions require individual forms.",
				batchCount: this.batchCount,
				batchExample: this.batchNameExample,
				batchPreview: this.batchIndex >= 0,
				batchIndex: this.batchIndex,
				batchTotal: this.batchDrafts.length || this.batchCount
			};
		},
		batchNameExample() {
			if (!this.createBatch || this.batchIndex >= 0) return "";
			for (const name of [
				"name",
				"title",
				"code"
			]) {
				const field = this.editableFields.find((field) => [field.name, field.action?.options?.column].includes(name) && ["TextWdg", "TextAreaWdg"].includes(this.kind(field)));
				if (field) return batchExample(this.draft[field.name] || "", this.batchCount);
			}
			return "";
		},
		mobile() {
			return mobile.value;
		},
		contextValid() {
			return this.context?.ticket === this.ticket && this.context?.project === this.project && (!this.definition || this.definition.search_type === this.searchType);
		},
		batch() {
			return !!this.definition?.search_keys;
		},
		dirty() {
			return this.batch && this.selectedFields.length > 0 || JSON.stringify(this.draft) !== JSON.stringify(this.baseline);
		},
		editableFields() {
			return (this.definition?.fields || []).filter((field) => !this.readOnly(field));
		},
		batchFields() {
			return this.editableFields.filter((field) => !this.unsupported.includes(field) && ![
				"FileInput",
				"MultiUpload",
				"HiddenWdg",
				"ParentInput"
			].includes(this.kind(field)) && ![
				"TimeAction",
				"pyasm.command.TimeAction",
				"pyasm.command.edit_wdg_action.TimeAction"
			].includes(field.action.handler));
		},
		fieldsToSave() {
			return this.batch ? this.batchFields.filter((field) => this.selectedFields.includes(field.name)) : this.editableFields;
		},
		blocked() {
			return !this.batch && this.unsupported.length > 0;
		},
		unsupported() {
			return (this.definition?.fields || []).filter(unsupportedField);
		},
		fileValidating() {
			return Object.values(this.validatingFiles).some(Boolean);
		}
	},
	watch: {
		ticket() {
			this.invalidate();
		},
		project() {
			this.invalidate();
		},
		searchType() {
			this.invalidate();
		}
	},
	mounted() {
		window.addEventListener("beforeunload", this.beforeUnload);
	},
	beforeUnmount() {
		this.request++;
		window.removeEventListener("beforeunload", this.beforeUnload);
	},
	methods: {
		t,
		windowContext() {
			if (this.loading || this.saving || this.uncertain || this.dirty || this.createBatch || Object.keys(this.files).length) throw Error("Apply or discard unsaved changes first");
			return {
				project: this.project,
				route: {
					searchType: this.searchType,
					editView: this.editView,
					insertView: this.insertView,
					args: this.windowOpenArgs
				}
			};
		},
		editorAction(event) {
			if (event.type === "mode") {
				if (event.value === "batch" && !this.batchCreationAllowed) return;
				this.createBatch = event.value === "batch";
				if (this.batchIndex >= 0) {
					this.draft = this.batchSource;
					this.batchIndex = -1;
					this.batchDrafts = [];
				}
			} else if (event.type === "count") this.batchCount = event.value;
			else if (event.type === "item") {
				if (event.value >= 0 && event.value < this.batchDrafts.length) {
					this.batchDrafts[this.batchIndex] = this.draft;
					this.batchIndex = event.value;
					this.draft = this.batchDrafts[event.value];
				}
			} else if (event.type === "back") {
				this.batchDrafts[this.batchIndex] = this.draft;
				this.batchIndex = -1;
				this.draft = this.batchSource;
			} else if (event.type === "refresh") this.openAgain();
			else if (event.type === "cancel") this.cancel();
			else if (event.type === "check") this.save(true);
			else if (event.type === "submit") {
				if (this.createBatch && this.batchIndex < 0) this.previewBatch();
				else this.save();
			} else if (event.type === "token") {
				const element = this.lastTextField;
				if (element?.isConnected) {
					const start = element.selectionStart, end = element.selectionEnd;
					const field = this.definition.fields.find((field) => this.inputName(field) === element.name);
					if (field) {
						const value = String(this.draft[field.name] || "");
						this.draft[field.name] = value.slice(0, start) + event.value + value.slice(end);
						nextTick(() => {
							element.focus();
							element.setSelectionRange(start + event.value.length, start + event.value.length);
						});
					}
				}
			}
		},
		rememberTextField(event) {
			if (event.target.matches("input[type=text],input:not([type]),textarea")) this.lastTextField = event.target;
		},
		async openAgain() {
			if (this.dirty || this.saving || this.uncertain) return;
			const key = this.definition?.mode === "edit" ? this.definition.search_key : null;
			this.$refs.dialog.close();
			await this.open(key, null, { operation: this.operation });
		},
		previewBatch() {
			if (!this.$refs.form.checkValidity()) {
				this.$refs.form.reportValidity();
				return;
			}
			this.batchSource = this.draft;
			this.batchDrafts = batchDrafts(this.draft, this.definition.fields.map((field) => ({
				name: field.name,
				readOnly: this.readOnly(field),
				type: this.kind(field) === "TextAreaWdg" ? "multiline" : this.kind(field) === "TextWdg" ? "string" : "other"
			})), this.batchCount);
			this.batchIndex = 0;
			this.draft = this.batchDrafts[0];
		},
		async saveCreationBatch() {
			if (!this.batchCreationAllowed || this.batchIndex < 0 || !this.contextValid || this.saving || this.uncertain) return;
			this.batchDrafts[this.batchIndex] = this.draft;
			for (let index = 0; index < this.batchDrafts.length; index++) for (const field of this.fieldsToSave) if (this.required(field) && (this.batchDrafts[index][field.name] == null || String(this.batchDrafts[index][field.name]).trim() === "")) {
				this.batchIndex = index;
				this.draft = this.batchDrafts[index];
				await nextTick();
				this.$refs.form.reportValidity();
				return;
			}
			const request = this.request;
			const fields = this.fieldsToSave.filter((field) => !["HiddenWdg", "ParentInput"].includes(this.kind(field)));
			const rows = this.batchDrafts.map((draft) => Object.fromEntries(fields.map((field) => [field.action.options?.column || field.options.column || field.name, draft[field.name] ?? ""])));
			this.saving = true;
			this.error = "";
			try {
				await rpc("insert_multiple", [
					this.context,
					this.searchType,
					rows
				], { parent_key: this.definition.parent_key || null });
				if (request === this.request && this.contextValid) {
					this.definition = null;
					this.draft = this.baseline = {};
					this.$refs.dialog.close();
					this.$emit("saved");
				}
			} catch (error) {
				if (request === this.request) {
					this.uncertain = !error.status || error.status >= 500;
					this.error = this.uncertain ? "The save result is unknown. Close this form and refresh the records before trying again." : error.message;
				}
			} finally {
				if (request === this.request) this.saving = false;
			}
		},
		fieldPresentation(field) {
			let type = {
				TextWdg: "string",
				TextAreaWdg: "multiline",
				CheckboxWdg: "bool",
				SelectWdg: "enum",
				CalendarInputWdg: "date",
				ParentInput: "parent",
				FileInput: "preview",
				ThumbInputWdg: "thumbnail"
			}[fieldKind(field)] || "string";
			if (unsupportedField(field)) type = "unsupported";
			return {
				name: field.name,
				title: field.title,
				description: field.attributes.description || field.options.hint || field.options.hint_text || "",
				required: this.required(field),
				readOnly: this.readOnly(field),
				icon: fields_default.icons[type]
			};
		},
		kind: fieldKind,
		choices(field) {
			return field.choices.map((value, index) => ({
				value,
				label: value === "" && field.labels[index] === field.input?.empty_label ? t(field.labels[index]) : field.labels[index]
			}));
		},
		readOnly(field) {
			return field.input?.read_only || [true, "true"].includes(field.options.read_only);
		},
		disabled(field) {
			return this.readOnly(field) || this.batch && !this.selectedFields.includes(field.name);
		},
		required(field) {
			return [true, "true"].includes(field.options.required);
		},
		checked(value) {
			return [
				true,
				1,
				"1",
				"true",
				"on"
			].includes(value);
		},
		inputName(field) {
			return this.definition.input_prefix ? `${this.definition.input_prefix}|${field.name}` : field.name;
		},
		selectFile(field, event) {
			const file = event.target.files[0];
			if (file) this.files[field.name] = file;
			else delete this.files[field.name];
			this.draft[field.name] = file?.name ?? this.baseline[field.name];
		},
		selectUploads(field, slot, event) {
			const files = Array.from(event.target.files);
			this.files[slot] = files;
			this.draft[field.name].files[slot] = files.map((file) => file.name);
		},
		beforeUnload(event) {
			if (this.dirty || this.saving || this.uncertain) {
				event.preventDefault();
				event.returnValue = "";
			}
		},
		invalidate() {
			this.request++;
			this.loading = false;
			this.error = "Connection context changed. Close this form and reopen it before saving.";
		},
		async open(searchKey = null, sourceKey = null, relation = {}) {
			const uploads = Object.values(this.files).some((value) => Array.isArray(value) ? value.length : !!value);
			if (this.$refs.dialog.open && (this.loading || this.saving || this.dirty || uploads || this.uncertain || this.createBatch)) {
				this.$refs.dialog.show();
				return;
			}
			this.windowOpenArgs = [
				searchKey,
				sourceKey,
				relation
			];
			const { operation = "", ...relations } = relation;
			if (!["", "publish"].includes(operation)) throw new Error("Unsupported form operation");
			this.operation = operation;
			this.formSearchKey = searchKey || "";
			relation = relations;
			const id = ++this.request;
			this.createBatch = false;
			this.batchIndex = -1;
			this.batchDrafts = [];
			this.batchSource = {};
			this.lastTextField = null;
			this.context = {
				ticket: this.ticket,
				project: this.project,
				language: "python"
			};
			this.instanceRelation = relation.instance || null;
			this.definition = null;
			this.draft = this.baseline = {};
			this.files = {};
			this.validatingFiles = {};
			this.selectedFields = [];
			this.error = "";
			this.discard = this.uncertain = false;
			this.loading = true;
			this.$refs.dialog.showModal();
			try {
				const definition = await formDefinition(this.context.ticket, this.context.project, this.searchType, searchKey ? this.editView : this.insertView, searchKey, sourceKey, {
					...this.instanceRelation ? {} : relation,
					...this.ignoreFields.length ? { ignore: this.ignoreFields } : {}
				});
				if (id !== this.request) return;
				this.definition = definition;
				this.draft = Object.fromEntries(definition.fields.map((field) => [field.name, this.kind(field) === "MultiSelectWdg" ? field.input.value : this.kind(field) === "MultiUpload" ? {
					context: field.input.context.value,
					subcontext: "",
					description: "",
					is_revision: false,
					files: {}
				} : ["TimeInputWdg", "ColorInputWdg"].includes(this.kind(field)) ? field.input.value : field.values[0] ?? null]));
				this.baseline = JSON.parse(JSON.stringify(this.draft));
				await nextTick();
				if (!this.mobile) this.$refs.dialog.querySelector("input:not(:disabled), textarea:not(:disabled), select:not(:disabled)")?.focus();
			} catch (error) {
				if (id === this.request) this.error = error instanceof TypeError ? "Unable to reach the server." : error.message;
			} finally {
				if (id === this.request) this.loading = false;
			}
		},
		cancel() {
			if (this.saving) return;
			if (this.dirty || this.uncertain) this.discard = true;
			else this.close();
		},
		close() {
			if (this.saving) return;
			this.request++;
			this.definition = null;
			this.draft = this.baseline = {};
			this.files = {};
			this.validatingFiles = {};
			this.uncertain = false;
			this.$refs.dialog.close();
		},
		async save(checkOnly = false) {
			if (this.createBatch) {
				await this.saveCreationBatch();
				return;
			}
			if (!this.contextValid || this.loading || this.fileValidating || this.saving || this.uncertain && !checkOnly || this.blocked || !this.fieldsToSave.length) return;
			const request = this.request;
			this.saving = true;
			this.error = "";
			const files = Object.values(this.files).flat();
			if (new Set(files.map((file) => file.name.toLowerCase())).size !== files.length) {
				this.error = "Choose different file names for separate upload fields.";
				this.saving = false;
				return;
			}
			const values = {
				search_type: this.definition.search_type,
				search_id: "-1"
			};
			for (const field of this.batch ? this.fieldsToSave : this.definition.fields) {
				let value = this.draft[field.name];
				if (this.kind(field) === "FileInput") value = "";
				if (this.kind(field) === "MultiUpload") value = "";
				if (this.kind(field) === "MultiSelectWdg") value = value.map((item) => String(item));
				if (this.kind(field) === "TimeInputWdg" && [
					"TimeAction",
					"pyasm.command.TimeAction",
					"pyasm.command.edit_wdg_action.TimeAction"
				].includes(field.action.handler)) {
					const [hour, minute] = String(value).split(":");
					values[`${this.inputName(field)}|hour`] = hour;
					values[`${this.inputName(field)}|minute`] = minute;
				} else if (this.kind(field) === "TimeInputWdg" && value === this.baseline[field.name]) value = field.input.unchanged_value;
				if (this.kind(field) === "CalendarInputWdg") value = value === this.baseline[field.name] ? field.input.unchanged_value : value ? value + field.input.value_suffix : "";
				values[this.inputName(field)] = value;
			}
			const args = {
				view: this.definition.view,
				search_key: this.definition.search_key,
				input_prefix: this.definition.input_prefix,
				element_names: this.fieldsToSave.filter((field) => this.kind(field) !== "MultiUpload" || Object.values(this.draft[field.name].files).some((files) => files.length)).map((field) => field.name)
			};
			if (this.definition.expected_revision) args.expected_revision = this.definition.expected_revision;
			if (checkOnly) args.action = "check";
			if (this.definition.parent_key) args.parent_key = this.definition.parent_key;
			if (this.definition.connect_key) args.connect_key = this.definition.connect_key;
			if (this.batch) {
				delete args.search_key;
				delete args.expected_revision;
				args.search_keys = this.definition.search_keys;
				if (this.definition.plans) args.plans = this.definition.plans;
				args.update_data = JSON.stringify(args.search_keys.map(() => Object.fromEntries(this.fieldsToSave.map((field) => [field.name, values[this.inputName(field)]]))));
				args.extra_data = JSON.stringify(args.search_keys.map(() => ({})));
				args.extra_action = JSON.stringify(args.search_keys.map(() => ({})));
			}
			try {
				for (const field of this.fieldsToSave.filter((field) => this.kind(field) === "FileInput")) {
					const file = this.files[field.name];
					const prefix = this.inputName(field);
					values[`${prefix}|context`] = field.input.context;
					values[`${prefix}|column`] = field.input.column;
					if (file) {
						values[`${prefix}|path`] = await uploadFormFile(this.context.ticket, this.context.project, file);
						values[`${prefix}|ticket`] = this.context.ticket;
					}
				}
				for (const field of this.fieldsToSave.filter((field) => this.kind(field) === "MultiUpload")) {
					const prefix = this.inputName(field);
					for (const name of [
						"context",
						"subcontext",
						"description",
						"is_revision"
					]) values[`${prefix}|${name}`] = this.draft[field.name][name];
					if (field.input.column) values[`${prefix}|column`] = field.input.column;
					for (const slot of field.input.fields) {
						const files = this.files[`${field.name}|${slot.name}`] || [];
						for (const [index, file] of files.entries()) {
							const name = field.input.arbitrary ? `${field.name}${index}` : slot.name;
							const input = this.definition.input_prefix ? `${this.definition.input_prefix}|${name}` : name;
							values[`${input}|path`] = await uploadFormFile(this.context.ticket, this.context.project, file);
							values[`${input}|ticket`] = this.context.ticket;
						}
					}
				}
				if (!this.contextValid) {
					const error = /* @__PURE__ */ new Error("Connection context changed. Close this form and reopen it before saving.");
					error.status = 400;
					throw error;
				}
				if (this.instanceRelation) Object.assign(args, {
					create: true,
					search_type: this.searchType,
					instance_parent_key: this.instanceRelation.parent_key,
					path: this.instanceRelation.path
				});
				const response = await rpc("execute_cmd", [
					this.context,
					this.instanceRelation ? "tactic.command.sobject_link_cmd.SObjectLinkCmd" : this.batch ? "tactic.ui.panel.EditMultipleCmd" : "tactic.ui.panel.EditCmd",
					args,
					values
				]);
				if (request !== this.request || !this.contextValid) return;
				if (checkOnly) {
					const state = response?.info?.state;
					if (state === "saved") {
						this.definition = null;
						this.draft = this.baseline = {};
						this.files = {};
						this.uncertain = false;
						this.$refs.dialog.close();
						this.$emit("saved");
					} else if (state === "unchanged") {
						this.uncertain = false;
						this.error = "Changes were not saved. You can save again.";
					} else this.error = "Record changed on the server. Close or refresh before saving.";
					return;
				}
				this.definition = null;
				this.draft = this.baseline = {};
				this.files = {};
				this.$refs.dialog.close();
				this.$emit("saved");
			} catch (error) {
				this.uncertain = !error.status || error.status >= 500;
				this.error = this.uncertain ? "The save result is unknown. Close this form and refresh the records before trying again." : error.message;
			} finally {
				this.saving = false;
			}
		}
	}
};
var _hoisted_1 = ["aria-label"];
var _hoisted_2 = { class: "muted" };
var _hoisted_3 = {
	key: 0,
	role: "status"
};
var _hoisted_4 = {
	key: 1,
	class: "error",
	role: "alert"
};
var _hoisted_5 = {
	key: 0,
	class: "notice"
};
var _hoisted_6 = {
	key: 1,
	class: "notice"
};
var _hoisted_7 = {
	key: 2,
	class: "notice"
};
var _hoisted_8 = {
	key: 3,
	class: "notice"
};
var _hoisted_9 = {
	key: 4,
	class: "notice"
};
var _hoisted_10 = ["disabled"];
var _hoisted_11 = {
	key: 0,
	class: "configuration-toggle batch-field-toggle"
};
var _hoisted_12 = ["value", "disabled"];
var _hoisted_13 = {
	key: 1,
	class: "muted"
};
var _hoisted_14 = {
	key: 2,
	class: "muted"
};
var _hoisted_15 = ["id"];
var _hoisted_16 = ["id"];
var _hoisted_17 = ["name", "value"];
var _hoisted_18 = ["id", "disabled"];
var _hoisted_19 = [
	"multiple",
	"required",
	"onChange"
];
var _hoisted_20 = ["onUpdate:modelValue", "aria-label"];
var _hoisted_21 = ["value"];
var _hoisted_22 = ["onUpdate:modelValue"];
var _hoisted_23 = { key: 0 };
var _hoisted_24 = ["onUpdate:modelValue"];
var _hoisted_25 = ["onUpdate:modelValue"];
var _hoisted_26 = { class: "configuration-toggle" };
var _hoisted_27 = [
	"id",
	"onUpdate:modelValue",
	"name",
	"readonly",
	"disabled",
	"required"
];
var _hoisted_28 = ["id", "disabled"];
var _hoisted_29 = [
	"onUpdate:modelValue",
	"value",
	"name",
	"required"
];
var _hoisted_30 = {
	key: 17,
	class: "muted"
};
var _hoisted_31 = {
	key: 18,
	class: "muted"
};
var _hoisted_32 = {
	key: 19,
	class: "muted"
};
var _hoisted_33 = {
	key: 0,
	class: "notice",
	role: "alert"
};
var _hoisted_34 = { class: "configuration-actions" };
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_AppButton = resolveComponent("AppButton");
	const _component_ObjectEditorSurface = resolveComponent("ObjectEditorSurface");
	const _component_AppColorInput = resolveComponent("AppColorInput");
	const _component_ImagePicker = resolveComponent("ImagePicker");
	const _component_AppFileInput = resolveComponent("AppFileInput");
	const _component_AppSwitch = resolveComponent("AppSwitch");
	const _component_AppDateField = resolveComponent("AppDateField");
	const _component_AppSelect = resolveComponent("AppSelect");
	const _component_AppTextArea = resolveComponent("AppTextArea");
	const _component_AppTextField = resolveComponent("AppTextField");
	const _component_ObjectFieldFrame = resolveComponent("ObjectFieldFrame");
	const _component_ObjectFieldGrid = resolveComponent("ObjectFieldGrid");
	const _directive_window = resolveDirective("window");
	return withDirectives((openBlock(), createElementBlock("dialog", {
		ref: "dialog",
		class: "record-dialog record-form-dialog",
		"aria-label": $options.t("Record form"),
		onCancel: _cache[4] || (_cache[4] = withModifiers((...args) => $options.cancel && $options.cancel(...args), ["prevent"]))
	}, [_ctx.$slots.surface ? renderSlot(_ctx.$slots, "surface", {
		form: { ..._ctx.$data },
		save: $options.save,
		cancel: $options.cancel,
		close: $options.close,
		keep: () => {
			$data.discard = false;
		},
		reportError: (value) => {
			$data.error = value;
		},
		contextValid: $options.contextValid
	}, void 0, void 0, 0) : (openBlock(), createElementBlock(Fragment, { key: 1 }, [
		createBaseVNode("header", null, [createBaseVNode("div", null, [createBaseVNode("h2", null, toDisplayString($options.t($data.operation === "publish" ? "Publish" : $options.batch ? "Edit selected" : $data.definition?.source_key ? "Duplicate record" : $data.definition?.mode === "edit" ? "Edit record" : "Create record")), 1), createBaseVNode("small", _hoisted_2, toDisplayString($options.batch ? $options.t("{count} selected records", { count: $data.definition.search_keys.length }) : $data.definition?.source_key || $data.definition?.search_key || $props.searchType), 1)]), createVNode(_component_AppButton, {
			label: "Close",
			icon: "close",
			"icon-only": $options.mobile,
			disabled: $data.saving,
			onClick: $options.cancel
		}, null, 8, [
			"icon-only",
			"disabled",
			"onClick"
		])]),
		createVNode(_component_ObjectEditorSurface, {
			model: $options.editorModel,
			part: "header",
			onEvent: $options.editorAction
		}, null, 8, ["model", "onEvent"]),
		$data.loading ? (openBlock(), createElementBlock("p", _hoisted_3, toDisplayString($options.t("Loading data…")), 1)) : createCommentVNode("", true),
		$data.error ? (openBlock(), createElementBlock("p", _hoisted_4, toDisplayString($options.t($data.error)), 1)) : createCommentVNode("", true),
		$data.definition ? (openBlock(), createElementBlock(Fragment, { key: 2 }, [
			$data.definition.parent_key ? (openBlock(), createElementBlock("p", _hoisted_5, toDisplayString($options.t("The new record will belong to this parent: {key}", { key: $data.definition.parent_key })), 1)) : createCommentVNode("", true),
			$data.definition.source_key ? (openBlock(), createElementBlock("p", _hoisted_6, toDisplayString($options.t("Copies the editable fields in the creation form. Related objects and repository files are not copied. The new object receives its own code and timestamps.")), 1)) : createCommentVNode("", true),
			$options.batch ? (openBlock(), createElementBlock("p", _hoisted_7, toDisplayString($options.t("Select the fields to apply to every selected record. Values start from the first record; unselected fields keep their own values.")), 1)) : createCommentVNode("", true),
			$options.blocked ? (openBlock(), createElementBlock("p", _hoisted_8, toDisplayString($options.t("This form contains unsupported inputs or options. Saving is unavailable.")) + " " + toDisplayString($options.unsupported.map((field) => field.title).join(", ")), 1)) : !$data.definition.fields.length ? (openBlock(), createElementBlock("p", _hoisted_9, toDisplayString($options.t("This view has no elements.")), 1)) : createCommentVNode("", true),
			$data.definition.fields.length ? (openBlock(), createElementBlock("form", {
				key: 5,
				ref: "form",
				class: "record-form",
				onFocusin: _cache[2] || (_cache[2] = (...args) => $options.rememberTextField && $options.rememberTextField(...args)),
				onSubmit: _cache[3] || (_cache[3] = withModifiers((...args) => $options.save && $options.save(...args), ["prevent"]))
			}, [
				createBaseVNode("fieldset", { disabled: !$options.contextValid || $data.saving || $data.uncertain || $options.blocked }, [createVNode(_component_ObjectEditorSurface, {
					model: $options.editorModel,
					part: "tools",
					onEvent: $options.editorAction
				}, null, 8, ["model", "onEvent"]), createVNode(_component_ObjectFieldGrid, null, {
					default: withCtx(() => [(openBlock(true), createElementBlock(Fragment, null, renderList($data.definition.fields, (field, index) => {
						return withDirectives((openBlock(), createBlock(_component_ObjectFieldFrame, {
							key: index,
							class: "record-field",
							"input-id": `record-field-${$setup.formId}-${index}`,
							"minimum-editor-height": $options.kind(field) === "TextAreaWdg" ? 112 : void 0,
							model: $options.fieldPresentation(field)
						}, {
							default: withCtx(() => [
								$options.batch ? (openBlock(), createElementBlock("label", _hoisted_11, [createTextVNode(toDisplayString($options.t("Apply {field}", { field: field.title })) + " ", 1), withDirectives(createBaseVNode("input", {
									type: "checkbox",
									"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => $data.selectedFields = $event),
									value: field.name,
									disabled: !$options.batchFields.includes(field)
								}, null, 8, _hoisted_12), [[vModelCheckbox, $data.selectedFields]])])) : createCommentVNode("", true),
								$options.batch && field.mixed ? (openBlock(), createElementBlock("small", _hoisted_13, toDisplayString($options.t("The selected records have different values.")), 1)) : createCommentVNode("", true),
								$options.batch && !$options.readOnly(field) && !$options.batchFields.includes(field) ? (openBlock(), createElementBlock("small", _hoisted_14, toDisplayString($options.t("Edit this field on one record at a time.")), 1)) : createCommentVNode("", true),
								$options.kind(field) === "ParentInput" ? (openBlock(), createElementBlock("span", {
									key: 3,
									id: `record-field-${$setup.formId}-${index}`
								}, toDisplayString(field.input.no_parent_type ? $options.t("No parent type") : field.input.project ? $options.t("Project: {project}", { project: field.input.project }) : field.input.label), 9, _hoisted_15)) : $options.kind(field) === "ThumbInputWdg" ? (openBlock(), createElementBlock("span", {
									key: 4,
									id: `record-field-${$setup.formId}-${index}`,
									class: "muted"
								}, toDisplayString($options.t("Thumbnail is managed by the check-in and preview pipeline")), 9, _hoisted_16)) : $options.kind(field) === "HiddenWdg" ? (openBlock(), createElementBlock("input", {
									key: 5,
									type: "hidden",
									name: $options.inputName(field),
									value: $data.draft[field.name]
								}, null, 8, _hoisted_17)) : $options.kind(field) === "ColorInputWdg" ? (openBlock(), createBlock(_component_AppColorInput, {
									key: 6,
									id: `record-field-${$setup.formId}-${index}`,
									modelValue: $data.draft[field.name],
									"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event,
									name: $options.inputName(field),
									label: field.title,
									readonly: $options.readOnly(field),
									disabled: $options.batch && $options.disabled(field),
									required: $options.required(field)
								}, null, 8, [
									"id",
									"modelValue",
									"onUpdate:modelValue",
									"name",
									"label",
									"readonly",
									"disabled",
									"required"
								])) : $options.kind(field) === "FileInput" && field.input.context === "icon" ? (openBlock(), createBlock(_component_ImagePicker, {
									key: 7,
									class: "record-preview-input",
									role: "group",
									"aria-label": field.title,
									"model-value": $data.files[field.name] || null,
									"status-text": $data.files[field.name]?.name || "",
									disabled: $options.disabled(field),
									required: $options.required(field),
									onValidating: ($event) => $data.validatingFiles[field.name] = $event,
									"onUpdate:modelValue": ($event) => $options.selectFile(field, { target: { files: $event ? [$event] : [] } })
								}, null, 8, [
									"aria-label",
									"model-value",
									"status-text",
									"disabled",
									"required",
									"onValidating",
									"onUpdate:modelValue"
								])) : $options.kind(field) === "FileInput" ? (openBlock(), createBlock(_component_AppFileInput, {
									key: 8,
									id: `record-field-${$setup.formId}-${index}`,
									label: field.title,
									value: $data.files[field.name]?.name || "",
									disabled: $options.disabled(field),
									required: $options.required(field),
									onChange: ($event) => $options.selectFile(field, $event)
								}, null, 8, [
									"id",
									"label",
									"value",
									"disabled",
									"required",
									"onChange"
								])) : $options.kind(field) === "MultiUpload" ? (openBlock(), createElementBlock("fieldset", {
									key: 9,
									id: `record-field-${$setup.formId}-${index}`,
									disabled: $options.disabled(field),
									class: "compound-upload"
								}, [
									createBaseVNode("legend", null, toDisplayString(field.title), 1),
									(openBlock(true), createElementBlock(Fragment, null, renderList(field.input.fields, (slot) => {
										return openBlock(), createElementBlock("label", { key: slot.name }, [createTextVNode(toDisplayString(slot.name) + " ", 1), createBaseVNode("input", {
											type: "file",
											multiple: field.input.arbitrary,
											required: slot.required && ($data.definition.mode === "insert" || Object.values($data.draft[field.name].files).some((files) => files.length)),
											onChange: ($event) => $options.selectUploads(field, `${field.name}|${slot.name}`, $event)
										}, null, 40, _hoisted_19)]);
									}), 128)),
									createBaseVNode("label", null, [createTextVNode(toDisplayString($options.t("Context")) + " ", 1), field.input.context.type === "select" ? withDirectives((openBlock(), createElementBlock("select", {
										key: 0,
										"onUpdate:modelValue": ($event) => $data.draft[field.name].context = $event,
										"aria-label": $options.t("Context")
									}, [(openBlock(true), createElementBlock(Fragment, null, renderList(field.input.context.choices, (value, option) => {
										return openBlock(), createElementBlock("option", {
											key: option,
											value
										}, toDisplayString(field.input.context.labels[option]), 9, _hoisted_21);
									}), 128))], 8, _hoisted_20)), [[vModelSelect, $data.draft[field.name].context]]) : withDirectives((openBlock(), createElementBlock("input", {
										key: 1,
										"onUpdate:modelValue": ($event) => $data.draft[field.name].context = $event
									}, null, 8, _hoisted_22)), [[vModelText, $data.draft[field.name].context]])]),
									field.input.subcontext ? (openBlock(), createElementBlock("label", _hoisted_23, [createTextVNode(toDisplayString($options.t("Subcontext")), 1), withDirectives(createBaseVNode("input", { "onUpdate:modelValue": ($event) => $data.draft[field.name].subcontext = $event }, null, 8, _hoisted_24), [[vModelText, $data.draft[field.name].subcontext]])])) : createCommentVNode("", true),
									createBaseVNode("label", null, [createTextVNode(toDisplayString($options.t("Comment")), 1), withDirectives(createBaseVNode("textarea", {
										"onUpdate:modelValue": ($event) => $data.draft[field.name].description = $event,
										rows: "3"
									}, null, 8, _hoisted_25), [[vModelText, $data.draft[field.name].description]])]),
									createBaseVNode("div", _hoisted_26, [createBaseVNode("span", null, toDisplayString($options.t("Is revision")), 1), createVNode(_component_AppSwitch, {
										modelValue: $data.draft[field.name].is_revision,
										"onUpdate:modelValue": ($event) => $data.draft[field.name].is_revision = $event,
										label: "Is revision"
									}, null, 8, ["modelValue", "onUpdate:modelValue"])])
								], 8, _hoisted_18)) : $options.kind(field) === "CheckboxWdg" ? (openBlock(), createBlock(_component_AppSwitch, {
									key: 10,
									id: `record-field-${$setup.formId}-${index}`,
									name: $options.inputName(field),
									"model-value": $options.checked($data.draft[field.name]),
									disabled: $options.disabled(field),
									required: $options.required(field),
									"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event
								}, null, 8, [
									"id",
									"name",
									"model-value",
									"disabled",
									"required",
									"onUpdate:modelValue"
								])) : $options.kind(field) === "TimeInputWdg" ? withDirectives((openBlock(), createElementBlock("input", {
									key: 11,
									id: `record-field-${$setup.formId}-${index}`,
									type: "time",
									step: "60",
									"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event,
									name: $options.inputName(field),
									readonly: $options.readOnly(field),
									disabled: $options.batch && $options.disabled(field),
									required: $options.required(field)
								}, null, 8, _hoisted_27)), [[vModelText, $data.draft[field.name]]]) : $options.kind(field) === "CalendarInputWdg" ? (openBlock(), createBlock(_component_AppDateField, {
									key: 12,
									id: `record-field-${$setup.formId}-${index}`,
									"include-time": field.input.type !== "date",
									label: field.title,
									"model-value": $data.draft[field.name] === $data.baseline[field.name] ? field.input.value : $data.draft[field.name],
									name: $options.inputName(field),
									readonly: $options.readOnly(field),
									disabled: $options.batch && $options.disabled(field),
									required: $options.required(field),
									"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event === field.input.value ? $data.baseline[field.name] : $event
								}, null, 8, [
									"id",
									"include-time",
									"label",
									"model-value",
									"name",
									"readonly",
									"disabled",
									"required",
									"onUpdate:modelValue"
								])) : $options.kind(field) === "SelectWdg" ? (openBlock(), createBlock(_component_AppSelect, {
									key: 13,
									id: `record-field-${$setup.formId}-${index}`,
									modelValue: $data.draft[field.name],
									"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event,
									name: $options.inputName(field),
									disabled: $options.disabled(field),
									required: $options.required(field),
									options: $options.choices(field),
									"translate-labels": false
								}, null, 8, [
									"id",
									"modelValue",
									"onUpdate:modelValue",
									"name",
									"disabled",
									"required",
									"options"
								])) : $options.kind(field) === "MultiSelectWdg" ? (openBlock(), createElementBlock("fieldset", {
									key: 14,
									id: `record-field-${$setup.formId}-${index}`,
									disabled: $options.disabled(field)
								}, [createBaseVNode("legend", null, toDisplayString(field.title), 1), (openBlock(true), createElementBlock(Fragment, null, renderList(field.choices, (value, option) => {
									return openBlock(), createElementBlock("label", {
										key: option,
										class: "configuration-toggle"
									}, [createTextVNode(toDisplayString(field.labels[option]) + " ", 1), withDirectives(createBaseVNode("input", {
										type: "checkbox",
										"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event,
										value,
										name: $options.inputName(field),
										required: $options.required(field) && !$data.draft[field.name].length && option === 0
									}, null, 8, _hoisted_29), [[vModelCheckbox, $data.draft[field.name]]])]);
								}), 128))], 8, _hoisted_28)) : $options.kind(field) === "TextAreaWdg" ? (openBlock(), createBlock(_component_AppTextArea, {
									key: 15,
									label: field.title,
									id: `record-field-${$setup.formId}-${index}`,
									modelValue: $data.draft[field.name],
									"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event,
									name: $options.inputName(field),
									readonly: $options.readOnly(field),
									disabled: $options.batch && $options.disabled(field),
									required: $options.required(field),
									rows: field.options.rows || 3,
									cols: field.options.cols || 50
								}, null, 8, [
									"label",
									"id",
									"modelValue",
									"onUpdate:modelValue",
									"name",
									"readonly",
									"disabled",
									"required",
									"rows",
									"cols"
								])) : $options.kind(field) === "TextWdg" ? (openBlock(), createBlock(_component_AppTextField, {
									key: 16,
									label: field.title,
									id: `record-field-${$setup.formId}-${index}`,
									modelValue: $data.draft[field.name],
									"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event,
									name: $options.inputName(field),
									readonly: $options.readOnly(field),
									disabled: $options.batch && $options.disabled(field),
									required: $options.required(field),
									size: field.options.size || null
								}, null, 8, [
									"label",
									"id",
									"modelValue",
									"onUpdate:modelValue",
									"name",
									"readonly",
									"disabled",
									"required",
									"size"
								])) : (openBlock(), createElementBlock("span", _hoisted_30, toDisplayString($options.t("Widget unavailable")), 1)),
								field.options.hint || field.options.hint_text ? (openBlock(), createElementBlock("small", _hoisted_31, toDisplayString(field.options.hint || field.options.hint_text), 1)) : createCommentVNode("", true),
								field.input?.timezone ? (openBlock(), createElementBlock("small", _hoisted_32, toDisplayString($options.t("Time zone: {timezone}", { timezone: field.input.timezone === "local" ? $options.t("Server local time") : field.input.timezone })), 1)) : createCommentVNode("", true)
							]),
							_: 2
						}, 1032, [
							"input-id",
							"minimum-editor-height",
							"model"
						])), [[vShow, $options.kind(field) !== "HiddenWdg"]]);
					}), 128))]),
					_: 1
				})], 8, _hoisted_10),
				$data.discard ? (openBlock(), createElementBlock("div", _hoisted_33, [createBaseVNode("p", null, toDisplayString($options.t("Discard unsaved changes?")), 1), createBaseVNode("div", _hoisted_34, [createVNode(_component_AppButton, {
					label: "Keep editing",
					onClick: _cache[1] || (_cache[1] = ($event) => $data.discard = false)
				}), createVNode(_component_AppButton, {
					label: "Discard changes",
					onClick: $options.close
				}, null, 8, ["onClick"])])])) : createCommentVNode("", true),
				createBaseVNode("footer", null, [createVNode(_component_ObjectEditorSurface, {
					model: $options.editorModel,
					part: "footer",
					onEvent: $options.editorAction
				}, null, 8, ["model", "onEvent"])])
			], 544)) : createCommentVNode("", true)
		], 64)) : createCommentVNode("", true)
	], 64))], 40, _hoisted_1)), [[_directive_window, {
		kind: $props.searchType === "sthpw/task" ? "task_editor" : "add_sobject",
		type: "dialog",
		page: $options.windowContext
	}]]);
}
var RecordForm_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { fieldKind as a, RecordForm_default as default, readPreviewImage as i, format as n, unsupportedField as o, ImagePicker_default as r, _sfc_main$2 as t };

//# sourceMappingURL=RecordForm.js.map