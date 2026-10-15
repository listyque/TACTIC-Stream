import { B as useId, D as nextTick, I as resolveComponent, K as withDirectives, L as resolveDirective, N as openBlock, P as renderList, _ as createCommentVNode, a as vModelCheckbox, b as createTextVNode, c as vShow, d as Fragment, g as createBlock, h as createBaseVNode, o as vModelSelect, rt as toDisplayString, s as vModelText, tt as normalizeClass, u as withModifiers, v as createElementBlock, x as createVNode } from "./vue.js";
import { H as _plugin_vue_export_helper_default, T as t, i as _sfc_main$1, n as mobile } from "./index.js";
import { K as uploadFormFile, M as rpc, h as formDefinition } from "./clipboard.js";
import { t as _sfc_main$2 } from "./AppSwitch.js";
import { t as _sfc_main$3 } from "./AppColorInput.js";
import { t as _sfc_main$4 } from "./AppDateField.js";
//#region src/features/objects/recordFields.js
function fieldKind(field) {
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
		"HiddenWdg"
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
	if (fieldKind(field) === "FileInput") allowed.push("context", "client_action");
	if (fieldKind(field) === "MultiUpload") allowed.push("names", "upload_type", "context", "pipeline");
	if (field.class_name === "tactic.ui.widget.upload_wdg.UploadWdg") allowed.push("context_expr", "client_action");
	return !fieldKind(field) || field.values.length > 1 && fieldKind(field) !== "MultiSelectWdg" || field.values.some((value) => value !== null && typeof value === "object") || Object.keys(options).some((key) => !allowed.includes(key)) || fieldKind(field) === "CheckboxWdg" && options.value || fieldKind(field) === "ColorInputWdg" && options.css_background && options.css_background !== "{$VALUE}" || fieldKind(field) === "CalendarInputWdg" && field.input?.display_mode !== "browser" || [
		"TimeAction",
		"pyasm.command.TimeAction",
		"pyasm.command.edit_wdg_action.TimeAction"
	].includes(field.action.handler) && fieldKind(field) !== "TimeInputWdg" || fieldKind(field) === "FileInput" && (![
		"UploadAction",
		"pyasm.command.UploadAction",
		"pyasm.command.edit_wdg_action.UploadAction"
	].includes(field.action.handler) || options.client_action) || fieldKind(field) === "MultiUpload" && (field.class_name === "tactic.ui.widget.upload_wdg.UploadWdg" ? ![
		"UploadAction",
		"pyasm.command.UploadAction",
		"pyasm.command.edit_wdg_action.UploadAction"
	].includes(field.action.handler) || options.client_action || options.names || options.upload_type : ![
		"MultiUploadAction",
		"pyasm.command.MultiUploadAction",
		"pyasm.command.edit_wdg_action.MultiUploadAction",
		"MultiZipUploadAction",
		"pyasm.command.MultiZipUploadAction",
		"pyasm.command.edit_wdg_action.MultiZipUploadAction"
	].includes(field.action.handler) || field.input.arbitrary !== (field.action.options.upload_type === "arbitrary") || field.input.arbitrary && field.input.fields.length !== 1 || !field.input.arbitrary && field.input.fields.map((item) => item.name).join("|") !== (field.action.options.names || field.name)) || fieldKind(field) === "MultiSelectWdg" && ![
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
//#region src/features/objects/RecordForm.vue
var _sfc_main = {
	setup() {
		return { formId: useId() };
	},
	components: {
		AppDateField: _sfc_main$4,
		AppSwitch: _sfc_main$2,
		AppColorInput: _sfc_main$3,
		AppButton: _sfc_main$1
	},
	props: {
		ticket: String,
		project: String,
		searchType: String
	},
	emits: ["saved"],
	data() {
		return {
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
			selectedFields: [],
			instanceRelation: null
		};
	},
	computed: {
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
		kind: fieldKind,
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
			this.draft[field.name] = file?.name || "";
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
			if (this.$refs.dialog.open) {
				this.$refs.dialog.show();
				return;
			}
			const id = ++this.request;
			this.context = {
				ticket: this.ticket,
				project: this.project,
				language: "python"
			};
			this.instanceRelation = relation.instance || null;
			this.definition = null;
			this.draft = this.baseline = {};
			this.files = {};
			this.selectedFields = [];
			this.error = "";
			this.discard = this.uncertain = false;
			this.loading = true;
			this.searchType === "sthpw/task" ? this.$refs.dialog.showModal() : this.$refs.dialog.show();
			try {
				const definition = await formDefinition(this.context.ticket, this.context.project, this.searchType, searchKey ? "edit" : "insert", searchKey, sourceKey, this.instanceRelation ? {} : relation);
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
			this.uncertain = false;
			this.$refs.dialog.close();
		},
		async save() {
			if (!this.contextValid || this.loading || this.saving || this.uncertain || this.blocked || !this.fieldsToSave.length) return;
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
			if (this.definition.parent_key) args.parent_key = this.definition.parent_key;
			if (this.definition.connect_key) args.connect_key = this.definition.connect_key;
			if (this.batch) {
				delete args.search_key;
				args.search_keys = this.definition.search_keys;
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
				await rpc("execute_cmd", [
					this.context,
					this.instanceRelation ? "tactic.command.sobject_link_cmd.SObjectLinkCmd" : this.batch ? "tactic.ui.panel.EditMultipleCmd" : "tactic.ui.panel.EditCmd",
					args,
					values
				]);
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
var _hoisted_15 = ["for"];
var _hoisted_16 = ["id"];
var _hoisted_17 = ["name", "value"];
var _hoisted_18 = [
	"id",
	"name",
	"disabled",
	"required",
	"onChange"
];
var _hoisted_19 = ["id", "disabled"];
var _hoisted_20 = [
	"multiple",
	"required",
	"onChange"
];
var _hoisted_21 = ["onUpdate:modelValue", "aria-label"];
var _hoisted_22 = ["value"];
var _hoisted_23 = ["onUpdate:modelValue"];
var _hoisted_24 = { key: 0 };
var _hoisted_25 = ["onUpdate:modelValue"];
var _hoisted_26 = ["onUpdate:modelValue"];
var _hoisted_27 = { class: "configuration-toggle" };
var _hoisted_28 = [
	"id",
	"onUpdate:modelValue",
	"name",
	"readonly",
	"disabled",
	"required"
];
var _hoisted_29 = [
	"id",
	"onUpdate:modelValue",
	"name",
	"disabled",
	"required"
];
var _hoisted_30 = ["value"];
var _hoisted_31 = ["value"];
var _hoisted_32 = ["id", "disabled"];
var _hoisted_33 = [
	"onUpdate:modelValue",
	"value",
	"name",
	"required"
];
var _hoisted_34 = [
	"id",
	"value",
	"name",
	"readonly",
	"disabled",
	"required",
	"rows",
	"cols",
	"onInput"
];
var _hoisted_35 = [
	"id",
	"value",
	"name",
	"readonly",
	"disabled",
	"required",
	"size",
	"onInput"
];
var _hoisted_36 = {
	key: 16,
	class: "muted"
};
var _hoisted_37 = {
	key: 17,
	class: "muted"
};
var _hoisted_38 = {
	key: 18,
	class: "muted"
};
var _hoisted_39 = {
	key: 19,
	class: "muted"
};
var _hoisted_40 = {
	key: 0,
	class: "notice",
	role: "alert"
};
var _hoisted_41 = { class: "configuration-actions" };
var _hoisted_42 = { class: "configuration-actions" };
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_AppButton = resolveComponent("AppButton");
	const _component_AppColorInput = resolveComponent("AppColorInput");
	const _component_AppSwitch = resolveComponent("AppSwitch");
	const _component_AppDateField = resolveComponent("AppDateField");
	const _directive_window = resolveDirective("window");
	return withDirectives((openBlock(), createElementBlock("dialog", {
		ref: "dialog",
		class: "record-dialog record-form-dialog",
		"aria-label": $options.t("Record form"),
		onCancel: _cache[3] || (_cache[3] = withModifiers((...args) => $options.cancel && $options.cancel(...args), ["prevent"]))
	}, [
		createBaseVNode("header", null, [createBaseVNode("div", null, [createBaseVNode("h2", null, toDisplayString($options.t($options.batch ? "Edit selected" : $data.definition?.source_key ? "Duplicate record" : $data.definition?.mode === "edit" ? "Edit record" : "Create record")), 1), createBaseVNode("small", _hoisted_2, toDisplayString($options.batch ? $options.t("{count} selected records", { count: $data.definition.search_keys.length }) : $data.definition?.source_key || $data.definition?.search_key || $props.searchType), 1)]), createVNode(_component_AppButton, {
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
		$data.loading ? (openBlock(), createElementBlock("p", _hoisted_3, toDisplayString($options.t("Loading data…")), 1)) : createCommentVNode("", true),
		$data.error ? (openBlock(), createElementBlock("p", _hoisted_4, toDisplayString($options.t($data.error)), 1)) : createCommentVNode("", true),
		$data.definition ? (openBlock(), createElementBlock(Fragment, { key: 2 }, [
			$data.definition.parent_key ? (openBlock(), createElementBlock("p", _hoisted_5, toDisplayString($options.t("The new record will belong to this parent: {key}", { key: $data.definition.parent_key })), 1)) : createCommentVNode("", true),
			$data.definition.source_key ? (openBlock(), createElementBlock("p", _hoisted_6, toDisplayString($options.t("Copies the editable fields in the creation form. Related objects and repository files are not copied. The new object receives its own code and timestamps.")), 1)) : createCommentVNode("", true),
			$options.batch ? (openBlock(), createElementBlock("p", _hoisted_7, toDisplayString($options.t("Select the fields to apply to every selected record. Values start from the first record; unselected fields keep their own values.")), 1)) : createCommentVNode("", true),
			$options.blocked ? (openBlock(), createElementBlock("p", _hoisted_8, toDisplayString($options.t("This form contains unsupported inputs or options. Saving is unavailable.")) + " " + toDisplayString($options.unsupported.map((field) => field.title).join(", ")), 1)) : !$data.definition.fields.length ? (openBlock(), createElementBlock("p", _hoisted_9, toDisplayString($options.t("This view has no elements.")), 1)) : createCommentVNode("", true),
			$data.definition.fields.length ? (openBlock(), createElementBlock("form", {
				key: 5,
				class: "record-form",
				onSubmit: _cache[2] || (_cache[2] = withModifiers((...args) => $options.save && $options.save(...args), ["prevent"]))
			}, [
				createBaseVNode("fieldset", { disabled: !$options.contextValid || $data.saving || $data.uncertain || $options.blocked }, [(openBlock(true), createElementBlock(Fragment, null, renderList($data.definition.fields, (field, index) => {
					return withDirectives((openBlock(), createElementBlock("div", {
						key: index,
						class: normalizeClass(["record-field", { "configuration-toggle": !$options.batch && $options.kind(field) === "CheckboxWdg" }])
					}, [
						$options.batch ? (openBlock(), createElementBlock("label", _hoisted_11, [createTextVNode(toDisplayString($options.t("Apply {field}", { field: field.title })) + " ", 1), withDirectives(createBaseVNode("input", {
							type: "checkbox",
							"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => $data.selectedFields = $event),
							value: field.name,
							disabled: !$options.batchFields.includes(field)
						}, null, 8, _hoisted_12), [[vModelCheckbox, $data.selectedFields]])])) : createCommentVNode("", true),
						$options.batch && field.mixed ? (openBlock(), createElementBlock("small", _hoisted_13, toDisplayString($options.t("The selected records have different values.")), 1)) : createCommentVNode("", true),
						$options.batch && !$options.readOnly(field) && !$options.batchFields.includes(field) ? (openBlock(), createElementBlock("small", _hoisted_14, toDisplayString($options.t("Edit this field on one record at a time.")), 1)) : createCommentVNode("", true),
						!["MultiUpload", "MultiSelectWdg"].includes($options.kind(field)) ? (openBlock(), createElementBlock("label", {
							key: 3,
							for: `record-field-${$setup.formId}-${index}`
						}, toDisplayString(field.title), 9, _hoisted_15)) : createCommentVNode("", true),
						$options.kind(field) === "ParentInput" ? (openBlock(), createElementBlock("span", {
							key: 4,
							id: `record-field-${$setup.formId}-${index}`
						}, toDisplayString(field.input.no_parent_type ? $options.t("No parent type") : field.input.project ? $options.t("Project: {project}", { project: field.input.project }) : field.input.label), 9, _hoisted_16)) : $options.kind(field) === "HiddenWdg" ? (openBlock(), createElementBlock("input", {
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
						])) : $options.kind(field) === "FileInput" ? (openBlock(), createElementBlock("input", {
							key: 7,
							id: `record-field-${$setup.formId}-${index}`,
							type: "file",
							name: $options.inputName(field),
							disabled: $options.disabled(field),
							required: $options.required(field),
							onChange: ($event) => $options.selectFile(field, $event)
						}, null, 40, _hoisted_18)) : $options.kind(field) === "MultiUpload" ? (openBlock(), createElementBlock("fieldset", {
							key: 8,
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
								}, null, 40, _hoisted_20)]);
							}), 128)),
							createBaseVNode("label", null, [createTextVNode(toDisplayString($options.t("Context")) + " ", 1), field.input.context.type === "select" ? withDirectives((openBlock(), createElementBlock("select", {
								key: 0,
								"onUpdate:modelValue": ($event) => $data.draft[field.name].context = $event,
								"aria-label": $options.t("Context")
							}, [(openBlock(true), createElementBlock(Fragment, null, renderList(field.input.context.choices, (value, option) => {
								return openBlock(), createElementBlock("option", {
									key: option,
									value
								}, toDisplayString(field.input.context.labels[option]), 9, _hoisted_22);
							}), 128))], 8, _hoisted_21)), [[vModelSelect, $data.draft[field.name].context]]) : withDirectives((openBlock(), createElementBlock("input", {
								key: 1,
								"onUpdate:modelValue": ($event) => $data.draft[field.name].context = $event
							}, null, 8, _hoisted_23)), [[vModelText, $data.draft[field.name].context]])]),
							field.input.subcontext ? (openBlock(), createElementBlock("label", _hoisted_24, [createTextVNode(toDisplayString($options.t("Subcontext")), 1), withDirectives(createBaseVNode("input", { "onUpdate:modelValue": ($event) => $data.draft[field.name].subcontext = $event }, null, 8, _hoisted_25), [[vModelText, $data.draft[field.name].subcontext]])])) : createCommentVNode("", true),
							createBaseVNode("label", null, [createTextVNode(toDisplayString($options.t("Comment")), 1), withDirectives(createBaseVNode("textarea", {
								"onUpdate:modelValue": ($event) => $data.draft[field.name].description = $event,
								rows: "3"
							}, null, 8, _hoisted_26), [[vModelText, $data.draft[field.name].description]])]),
							createBaseVNode("div", _hoisted_27, [createBaseVNode("span", null, toDisplayString($options.t("Is revision")), 1), createVNode(_component_AppSwitch, {
								modelValue: $data.draft[field.name].is_revision,
								"onUpdate:modelValue": ($event) => $data.draft[field.name].is_revision = $event,
								label: "Is revision"
							}, null, 8, ["modelValue", "onUpdate:modelValue"])])
						], 8, _hoisted_19)) : $options.kind(field) === "CheckboxWdg" ? (openBlock(), createBlock(_component_AppSwitch, {
							key: 9,
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
							key: 10,
							id: `record-field-${$setup.formId}-${index}`,
							type: "time",
							step: "60",
							"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event,
							name: $options.inputName(field),
							readonly: $options.readOnly(field),
							disabled: $options.batch && $options.disabled(field),
							required: $options.required(field)
						}, null, 8, _hoisted_28)), [[vModelText, $data.draft[field.name]]]) : $options.kind(field) === "CalendarInputWdg" ? (openBlock(), createBlock(_component_AppDateField, {
							key: 11,
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
						])) : $options.kind(field) === "SelectWdg" ? withDirectives((openBlock(), createElementBlock("select", {
							key: 12,
							id: `record-field-${$setup.formId}-${index}`,
							"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event,
							name: $options.inputName(field),
							disabled: $options.disabled(field),
							required: $options.required(field)
						}, [!field.choices.some((value) => String(value) === String($data.draft[field.name])) ? (openBlock(), createElementBlock("option", {
							key: 0,
							value: $data.draft[field.name]
						}, toDisplayString($data.draft[field.name] ?? $options.t("Not set")), 9, _hoisted_30)) : createCommentVNode("", true), (openBlock(true), createElementBlock(Fragment, null, renderList(field.choices, (value, option) => {
							return openBlock(), createElementBlock("option", {
								key: option,
								value
							}, toDisplayString(value === "" && field.labels[option] === field.input?.empty_label ? $options.t(field.labels[option]) : field.labels[option]), 9, _hoisted_31);
						}), 128))], 8, _hoisted_29)), [[vModelSelect, $data.draft[field.name]]]) : $options.kind(field) === "MultiSelectWdg" ? (openBlock(), createElementBlock("fieldset", {
							key: 13,
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
							}, null, 8, _hoisted_33), [[vModelCheckbox, $data.draft[field.name]]])]);
						}), 128))], 8, _hoisted_32)) : $options.kind(field) === "TextAreaWdg" ? (openBlock(), createElementBlock("textarea", {
							key: 14,
							id: `record-field-${$setup.formId}-${index}`,
							value: $data.draft[field.name],
							name: $options.inputName(field),
							readonly: $options.readOnly(field),
							disabled: $options.batch && $options.disabled(field),
							required: $options.required(field),
							rows: field.options.rows || 3,
							cols: field.options.cols || 50,
							onInput: ($event) => $data.draft[field.name] = $event.target.value
						}, null, 40, _hoisted_34)) : $options.kind(field) === "TextWdg" ? (openBlock(), createElementBlock("input", {
							key: 15,
							id: `record-field-${$setup.formId}-${index}`,
							value: $data.draft[field.name],
							name: $options.inputName(field),
							readonly: $options.readOnly(field),
							disabled: $options.batch && $options.disabled(field),
							required: $options.required(field),
							size: field.options.size || null,
							onInput: ($event) => $data.draft[field.name] = $event.target.value
						}, null, 40, _hoisted_35)) : (openBlock(), createElementBlock("span", _hoisted_36, toDisplayString($options.t("Widget unavailable")), 1)),
						field.options.hint || field.options.hint_text ? (openBlock(), createElementBlock("small", _hoisted_37, toDisplayString(field.options.hint || field.options.hint_text), 1)) : createCommentVNode("", true),
						(field.attributes.description || field.attributes.title) && (field.attributes.description || field.attributes.title) !== field.title ? (openBlock(), createElementBlock("small", _hoisted_38, toDisplayString(field.attributes.description || field.attributes.title), 1)) : createCommentVNode("", true),
						field.input?.timezone ? (openBlock(), createElementBlock("small", _hoisted_39, toDisplayString($options.t("Time zone: {timezone}", { timezone: field.input.timezone === "local" ? $options.t("Server local time") : field.input.timezone })), 1)) : createCommentVNode("", true)
					], 2)), [[vShow, $options.kind(field) !== "HiddenWdg"]]);
				}), 128))], 8, _hoisted_10),
				$data.discard ? (openBlock(), createElementBlock("div", _hoisted_40, [createBaseVNode("p", null, toDisplayString($options.t("Discard unsaved changes?")), 1), createBaseVNode("div", _hoisted_41, [createVNode(_component_AppButton, {
					label: "Keep editing",
					onClick: _cache[1] || (_cache[1] = ($event) => $data.discard = false)
				}), createVNode(_component_AppButton, {
					label: "Discard changes",
					onClick: $options.close
				}, null, 8, ["onClick"])])])) : createCommentVNode("", true),
				createBaseVNode("footer", _hoisted_42, [createVNode(_component_AppButton, {
					highlighted: "",
					type: "submit",
					label: $data.saving ? "Saving…" : "Save record",
					icon: "save",
					disabled: !$options.contextValid || $data.saving || $data.uncertain || $options.blocked || !$options.fieldsToSave.length || $data.definition.mode === "edit" && !$options.dirty
				}, null, 8, ["label", "disabled"])])
			], 32)) : createCommentVNode("", true)
		], 64)) : createCommentVNode("", true)
	], 40, _hoisted_1)), [[_directive_window, { type: $props.searchType === "sthpw/task" ? "dialog" : "window" }]]);
}
var RecordForm_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { fieldKind as n, unsupportedField as r, RecordForm_default as t };

//# sourceMappingURL=RecordForm.js.map