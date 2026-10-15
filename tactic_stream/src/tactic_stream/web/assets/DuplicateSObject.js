import { D as nextTick, G as withCtx, I as resolveComponent, K as withDirectives, L as resolveDirective, N as openBlock, P as renderList, _ as createCommentVNode, b as createTextVNode, c as vShow, d as Fragment, g as createBlock, h as createBaseVNode, p as Teleport, rt as toDisplayString, s as vModelText, u as withModifiers, v as createElementBlock, x as createVNode } from "./vue.js";
import { D as t, Y as _plugin_vue_export_helper_default, o as _sfc_main$1, u as _sfc_main$2 } from "./index.js";
import { M as rpc, ct as notify } from "./clipboard.js";
import { t as _sfc_main$3 } from "./AppSelect.js";
import { t as _sfc_main$4 } from "./AppTextField.js";
import { n as _sfc_main$6, t as _sfc_main$5 } from "./AppDateField.js";
import { t as _sfc_main$7 } from "./AppCheckbox.js";
import { F as contentChoices, I as duplicateProfile, L as saveDuplicateProfile, N as applyDuplicateProfile, P as changeContent, h as _sfc_main$8, k as _sfc_main$9 } from "./App.js";
//#region src/features/objects/DuplicateSObject.vue
var steps = [
	"Fields",
	"Relations",
	"Snapshots",
	"Tasks and messages",
	"Review duplicate"
];
var icons = [
	"edit",
	"account-tree",
	"inventory-2",
	"task",
	"fact-check"
];
var choices = [
	{
		name: "copySnapshots",
		label: "Snapshots",
		count: "snapshotCount",
		page: 2
	},
	{
		name: "copyTasks",
		label: "Tasks",
		count: "taskCount",
		page: 3
	},
	{
		name: "copyProcessMessages",
		label: "Process messages",
		count: "processMessageCount",
		page: 3
	},
	{
		name: "copyProcessAttachments",
		label: "Process attachments",
		count: "processAttachmentCount",
		page: 3
	},
	{
		name: "copyTaskMessages",
		label: "Task messages",
		count: "taskMessageCount",
		page: 3
	},
	{
		name: "copyTaskAttachments",
		label: "Task attachments",
		count: "taskAttachmentCount",
		page: 3
	}
];
var _sfc_main = {
	components: {
		AppDateField: _sfc_main$5,
		AppButton: _sfc_main$1,
		AppIcon: _sfc_main$2,
		AppCheckbox: _sfc_main$7,
		AppSelect: _sfc_main$3,
		AppTextField: _sfc_main$4,
		AppColorInput: _sfc_main$6,
		AppSegmentedButton: _sfc_main$8,
		SummaryChip: _sfc_main$9
	},
	inject: {
		openHelp: {},
		currentLogin: { default: () => () => "" }
	},
	props: {
		ticket: String,
		project: String
	},
	emits: ["completed"],
	data() {
		return {
			analysis: null,
			draft: {},
			baseline: "",
			scope: null,
			sourceKey: "",
			sourceType: "",
			owner: "",
			revision: "",
			step: 0,
			remember: true,
			busy: false,
			saving: false,
			uncertain: false,
			error: "",
			discard: false,
			request: 0,
			quick: false
		};
	},
	computed: {
		steps() {
			return steps.map((label, value) => ({
				value,
				label,
				icon: icons[value]
			}));
		},
		processes() {
			return this.analysis?.processes.filter((process) => choices.some((choice) => choice.page === this.step && process[choice.count])) || [];
		},
		dirty() {
			return !!this.analysis && JSON.stringify(this.options()) !== this.baseline;
		},
		valid() {
			return this.scope?.ticket === this.ticket && this.scope?.project === this.project;
		},
		totals() {
			const result = {
				related: 0,
				snapshots: 0,
				tasks: 0,
				messages: 0
			};
			for (const relation of this.analysis?.relations || []) if (relation.mode !== "none") result.related += relation.count;
			for (const process of this.analysis?.processes || []) {
				if (process.copySnapshots) result.snapshots += process.snapshotCount;
				if (process.copyTasks) result.tasks += process.taskCount;
				if (process.copyProcessMessages) result.messages += process.processMessageCount;
				if (process.copyTaskMessages) result.messages += process.taskMessageCount;
				if (process.copyProcessAttachments) result.messages += process.processAttachmentCount;
				if (process.copyTaskAttachments) result.messages += process.taskAttachmentCount;
			}
			return result;
		}
	},
	watch: {
		ticket() {
			this.invalidate();
		},
		project() {
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
		changeContent,
		beforeUnload(event) {
			if (this.$refs.dialog?.open && (this.dirty || this.saving || this.uncertain)) {
				event.preventDefault();
				event.returnValue = "";
			}
		},
		invalidate() {
			this.request++;
			this.busy = this.saving = false;
			if (this.$refs.dialog?.open) this.error = "Connection context changed. Close this form and reopen it before saving.";
		},
		async open(record, quick = false) {
			if (this.$refs.dialog.open) {
				this.$refs.dialog.show();
				return;
			}
			this.scope = {
				ticket: this.ticket,
				project: this.project,
				language: "python"
			};
			this.sourceKey = record.__search_key__;
			this.sourceType = record.__search_key__.split("?")[0];
			this.owner = this.currentLogin();
			this.analysis = null;
			this.draft = {};
			this.revision = "";
			this.step = 0;
			this.quick = quick;
			this.error = "";
			this.uncertain = this.discard = false;
			await nextTick();
			this.$refs.dialog.show();
			await this.analyze();
			if (quick && this.analysis && !this.error && this.valid) await this.duplicate();
		},
		async call(action, values = {}) {
			return (await rpc("execute_cmd", [
				this.scope,
				"tactic.command.sobject_duplicate_cmd.SObjectDuplicateCmd",
				{
					action,
					search_key: this.sourceKey,
					...values
				}
			])).info;
		},
		async analyze() {
			if (!this.valid || this.saving || this.uncertain) return;
			const request = ++this.request, previous = this.analysis ? this.options() : null;
			this.busy = true;
			this.error = "";
			try {
				const result = await this.call("analyze");
				if (request !== this.request) return;
				const profile = duplicateProfile(this.owner, this.scope.project, this.sourceType);
				if (this.quick && !profile) throw new Error("Open Duplicate… once to save choices for this Search Type.");
				applyDuplicateProfile(result.analysis, previous || profile);
				this.analysis = result.analysis;
				this.revision = result.revision;
				this.draft = Object.fromEntries(this.analysis.fields.map((field) => [field.name, previous?.fields?.[field.name] ?? (this.fieldKind(field) === "checkbox" ? [
					"True",
					"true",
					"1",
					"on"
				].includes(field.value) : String(field.widget?.input?.value ?? field.value))]));
				if (!previous) this.baseline = JSON.stringify(this.options());
			} catch (error) {
				if (request === this.request) this.error = error.message;
			} finally {
				if (request === this.request) this.busy = false;
			}
		},
		readOnly(field) {
			return field.widget?.input?.read_only || [true, "true"].includes(field.widget?.options?.read_only);
		},
		fieldKind(field) {
			const widget = field.widget;
			if (widget?.input?.type === "hidden" || widget?.class_name?.endsWith(".HiddenWdg")) return "hidden";
			if (widget?.input?.type === "color") return "color";
			if (widget?.choices && widget.input?.type !== "multiselect") return "select";
			if (widget?.class_name?.endsWith(".CheckboxWdg") || /bool/i.test(field.dataType)) return "checkbox";
			if (field.multiline || widget?.class_name?.endsWith(".TextAreaWdg")) return "textarea";
			if (widget?.input?.type === "time") return "time";
			if (widget?.class_name?.includes("CalendarInput")) return "datetime-local";
			return /int|float|double|numeric|decimal/i.test(field.dataType) ? "number" : "text";
		},
		fieldChoices(field) {
			const widget = field.widget;
			return [...widget.input?.empty_label ? [{
				value: "",
				label: widget.input.empty_label
			}] : [], ...widget.choices.map((value, index) => ({
				value,
				label: widget.labels[index]
			}))];
		},
		pageChoices(process) {
			return choices.filter((choice) => choice.page === this.step && process[choice.count]);
		},
		options() {
			return {
				fields: Object.fromEntries((this.analysis?.fields || []).filter((field) => !this.readOnly(field)).map((field) => [field.name, this.draft[field.name]])),
				relations: Object.fromEntries((this.analysis?.relations || []).map((row) => [row.key, row.mode])),
				processes: Object.fromEntries((this.analysis?.processes || []).map((row) => [row.name, Object.fromEntries(contentChoices.map((name) => [name, row[name] === true]))]))
			};
		},
		async duplicate() {
			if (!this.analysis || this.busy || this.saving || this.uncertain || !this.valid) return;
			if (!this.$refs.fields?.checkValidity()) {
				this.step = 0;
				await nextTick();
				this.$refs.fields.reportValidity();
				return;
			}
			const request = ++this.request;
			this.saving = true;
			this.error = "";
			try {
				const options = this.options();
				if (this.remember) try {
					saveDuplicateProfile(this.owner, this.scope.project, this.sourceType, {
						relations: options.relations,
						processes: options.processes
					});
				} catch {
					const error = /* @__PURE__ */ new Error("Unable to save choices in this browser. Turn off Remember choices to continue.");
					error.status = 400;
					throw error;
				}
				const result = await this.call("duplicate", {
					options,
					revision: this.revision
				});
				if (request !== this.request) return;
				this.baseline = JSON.stringify(options);
				this.$refs.dialog.close();
				this.analysis = null;
				notify("info", "Object duplicated");
				this.$emit("completed", result.result);
			} catch (error) {
				if (request !== this.request) return;
				this.uncertain = !error.status || error.status >= 500;
				this.error = this.uncertain ? "The result is unknown. Refresh the objects before trying again." : error.message;
			} finally {
				if (request === this.request) this.saving = false;
			}
		},
		close(force = false) {
			if (this.saving) return;
			if (!force && (this.dirty || this.uncertain)) {
				this.discard = true;
				return;
			}
			this.request++;
			this.$refs.dialog.close();
			this.analysis = null;
			this.busy = this.uncertain = this.discard = false;
		}
	}
};
var _hoisted_1 = ["aria-label"];
var _hoisted_2 = { class: "duplicate-header" };
var _hoisted_3 = { class: "duplicate-symbol" };
var _hoisted_4 = { class: "duplicate-step" };
var _hoisted_5 = {
	key: 0,
	role: "alert",
	class: "error"
};
var _hoisted_6 = {
	key: 1,
	role: "status"
};
var _hoisted_7 = { class: "duplicate-page" };
var _hoisted_8 = { class: "muted duplicate-intro" };
var _hoisted_9 = { class: "duplicate-fields" };
var _hoisted_10 = { class: "duplicate-field-heading" };
var _hoisted_11 = { class: "duplicate-symbol small" };
var _hoisted_12 = [
	"onUpdate:modelValue",
	"aria-label",
	"disabled"
];
var _hoisted_13 = {
	key: 6,
	class: "muted"
};
var _hoisted_14 = {
	key: 0,
	class: "duplicate-page"
};
var _hoisted_15 = { class: "muted" };
var _hoisted_16 = {
	key: 0,
	class: "muted"
};
var _hoisted_17 = { class: "duplicate-card-heading" };
var _hoisted_18 = { class: "duplicate-symbol small" };
var _hoisted_19 = { class: "muted" };
var _hoisted_20 = {
	key: 1,
	class: "duplicate-page"
};
var _hoisted_21 = { class: "muted" };
var _hoisted_22 = {
	key: 0,
	class: "muted"
};
var _hoisted_23 = { class: "duplicate-card-heading" };
var _hoisted_24 = { class: "duplicate-symbol small" };
var _hoisted_25 = { key: 0 };
var _hoisted_26 = { class: "duplicate-content-choices" };
var _hoisted_27 = {
	key: 2,
	class: "duplicate-page"
};
var _hoisted_28 = { class: "duplicate-review" };
var _hoisted_29 = { class: "muted" };
var _hoisted_30 = { class: "duplicate-totals" };
var _hoisted_31 = { class: "duplicate-intro muted" };
var _hoisted_32 = { class: "configuration-actions" };
var _hoisted_33 = {
	key: 3,
	class: "notice",
	role: "alert"
};
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_AppIcon = resolveComponent("AppIcon");
	const _component_AppButton = resolveComponent("AppButton");
	const _component_AppSegmentedButton = resolveComponent("AppSegmentedButton");
	const _component_AppCheckbox = resolveComponent("AppCheckbox");
	const _component_AppSelect = resolveComponent("AppSelect");
	const _component_AppColorInput = resolveComponent("AppColorInput");
	const _component_AppDateField = resolveComponent("AppDateField");
	const _component_AppTextField = resolveComponent("AppTextField");
	const _component_SummaryChip = resolveComponent("SummaryChip");
	const _directive_window = resolveDirective("window");
	return openBlock(), createBlock(Teleport, { to: "body" }, [withDirectives((openBlock(), createElementBlock("dialog", {
		ref: "dialog",
		class: "record-dialog duplicate-sobject",
		"aria-label": $options.t("Duplicate object"),
		onCancel: _cache[10] || (_cache[10] = withModifiers(($event) => $options.close(), ["prevent"]))
	}, [
		createBaseVNode("header", _hoisted_2, [
			createBaseVNode("span", _hoisted_3, [createVNode(_component_AppIcon, { name: "control-point-duplicate" })]),
			createBaseVNode("div", null, [createBaseVNode("h2", null, toDisplayString($options.t("Duplicate")) + " " + toDisplayString($data.analysis?.title), 1), createBaseVNode("small", null, toDisplayString($data.analysis?.searchType || $data.sourceType), 1)]),
			createBaseVNode("span", _hoisted_4, toDisplayString($options.t("Step {step} of 5", { step: $data.step + 1 })), 1),
			createVNode(_component_AppButton, {
				label: "Help",
				icon: "help",
				"icon-only": "",
				onClick: _cache[0] || (_cache[0] = ($event) => $options.openHelp("duplicating_objects"))
			}),
			createVNode(_component_AppButton, {
				label: "Close",
				icon: "close",
				"icon-only": "",
				disabled: $data.saving,
				onClick: _cache[1] || (_cache[1] = ($event) => $options.close())
			}, null, 8, ["disabled"])
		]),
		$data.error ? (openBlock(), createElementBlock("p", _hoisted_5, [createTextVNode(toDisplayString($options.t($data.error)) + " ", 1), !$data.uncertain && $options.valid ? (openBlock(), createBlock(_component_AppButton, {
			key: 0,
			label: "Analyze again",
			disabled: $data.busy || $data.saving,
			onClick: $options.analyze
		}, null, 8, ["disabled", "onClick"])) : createCommentVNode("", true)])) : createCommentVNode("", true),
		$data.busy || $data.saving ? (openBlock(), createElementBlock("p", _hoisted_6, toDisplayString($options.t($data.saving ? "Creating duplicate on server…" : "Analyzing object…")), 1)) : createCommentVNode("", true),
		$data.analysis ? (openBlock(), createElementBlock(Fragment, { key: 2 }, [createVNode(_component_AppSegmentedButton, {
			modelValue: $data.step,
			"onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => $data.step = $event),
			options: $options.steps,
			label: "Duplicate steps",
			disabled: $data.saving || $data.busy,
			class: "duplicate-steps"
		}, null, 8, [
			"modelValue",
			"options",
			"disabled"
		]), createBaseVNode("form", {
			ref: "fields",
			class: "duplicate-pages",
			onSubmit: _cache[3] || (_cache[3] = withModifiers((...args) => $options.duplicate && $options.duplicate(...args), ["prevent"]))
		}, [
			withDirectives(createBaseVNode("section", _hoisted_7, [createBaseVNode("p", _hoisted_8, [createVNode(_component_AppIcon, { name: "edit" }), createTextVNode(toDisplayString($options.t("Edit values for the new object. Identity, project and relationship fields are managed automatically.")), 1)]), createBaseVNode("div", _hoisted_9, [(openBlock(true), createElementBlock(Fragment, null, renderList($data.analysis.fields.filter((field) => $options.fieldKind(field) !== "hidden"), (field) => {
				return openBlock(), createElementBlock("div", {
					key: field.name,
					class: "duplicate-field"
				}, [
					createBaseVNode("span", _hoisted_10, [createBaseVNode("span", _hoisted_11, [createVNode(_component_AppIcon, { name: $options.fieldKind(field) === "textarea" ? "description" : "text-fields" }, null, 8, ["name"])]), createBaseVNode("span", null, [createBaseVNode("strong", null, toDisplayString($options.t(field.widget?.title || field.label)), 1), createBaseVNode("small", null, toDisplayString(field.name), 1)])]),
					$options.fieldKind(field) === "checkbox" ? (openBlock(), createBlock(_component_AppCheckbox, {
						key: 0,
						modelValue: $data.draft[field.name],
						"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event,
						label: field.widget?.title || field.label,
						disabled: $data.saving || $options.readOnly(field)
					}, null, 8, [
						"modelValue",
						"onUpdate:modelValue",
						"label",
						"disabled"
					])) : $options.fieldKind(field) === "select" ? (openBlock(), createBlock(_component_AppSelect, {
						key: 1,
						modelValue: $data.draft[field.name],
						"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event,
						options: $options.fieldChoices(field),
						label: field.widget?.title || field.label,
						"translate-labels": false,
						disabled: $data.saving || $options.readOnly(field)
					}, null, 8, [
						"modelValue",
						"onUpdate:modelValue",
						"options",
						"label",
						"disabled"
					])) : $options.fieldKind(field) === "color" ? (openBlock(), createBlock(_component_AppColorInput, {
						key: 2,
						modelValue: $data.draft[field.name],
						"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event,
						label: field.label,
						disabled: $data.saving || $options.readOnly(field)
					}, null, 8, [
						"modelValue",
						"onUpdate:modelValue",
						"label",
						"disabled"
					])) : $options.fieldKind(field) === "textarea" ? withDirectives((openBlock(), createElementBlock("textarea", {
						key: 3,
						"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event,
						"aria-label": $options.t(field.widget?.title || field.label),
						rows: "4",
						disabled: $data.saving || $options.readOnly(field)
					}, null, 8, _hoisted_12)), [[vModelText, $data.draft[field.name]]]) : $options.fieldKind(field) === "datetime-local" ? (openBlock(), createBlock(_component_AppDateField, {
						key: 4,
						modelValue: $data.draft[field.name],
						"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event,
						label: field.widget?.title || field.label,
						required: [true, "true"].includes(field.widget?.options?.required),
						disabled: $data.saving || $options.readOnly(field)
					}, null, 8, [
						"modelValue",
						"onUpdate:modelValue",
						"label",
						"required",
						"disabled"
					])) : (openBlock(), createBlock(_component_AppTextField, {
						key: 5,
						modelValue: $data.draft[field.name],
						"onUpdate:modelValue": ($event) => $data.draft[field.name] = $event,
						label: field.widget?.title || field.label,
						type: $options.fieldKind(field),
						required: [true, "true"].includes(field.widget?.options?.required),
						disabled: $data.saving || $options.readOnly(field),
						step: "any"
					}, null, 8, [
						"modelValue",
						"onUpdate:modelValue",
						"label",
						"type",
						"required",
						"disabled"
					])),
					field.widget?.options?.hint || field.widget?.options?.hint_text ? (openBlock(), createElementBlock("small", _hoisted_13, toDisplayString($options.t(field.widget.options.hint || field.widget.options.hint_text)), 1)) : createCommentVNode("", true)
				]);
			}), 128))])], 512), [[vShow, $data.step === 0]]),
			$data.step === 1 ? (openBlock(), createElementBlock("section", _hoisted_14, [
				createBaseVNode("p", _hoisted_15, toDisplayString($options.t("Keep parent and instance links, or duplicate direct children. Linked targets are not cloned.")), 1),
				!$data.analysis.relations.length ? (openBlock(), createElementBlock("p", _hoisted_16, toDisplayString($options.t("No linked objects")), 1)) : createCommentVNode("", true),
				(openBlock(true), createElementBlock(Fragment, null, renderList($data.analysis.relations, (relation) => {
					return openBlock(), createElementBlock("article", {
						key: relation.key,
						class: "duplicate-card"
					}, [
						createBaseVNode("div", _hoisted_17, [createBaseVNode("span", _hoisted_18, [createVNode(_component_AppIcon, { name: relation.kind === "instance" ? "link" : "account-tree" }, null, 8, ["name"])]), createBaseVNode("div", null, [createBaseVNode("strong", null, toDisplayString(relation.title), 1), createBaseVNode("small", null, [createTextVNode(toDisplayString($options.t(relation.kind === "parent" ? "Parent" : relation.kind === "instance" ? "Instance links" : "Children")) + " · " + toDisplayString(relation.count), 1), relation.path ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [createTextVNode(" · " + toDisplayString(relation.path), 1)], 64)) : createCommentVNode("", true)])])]),
						createVNode(_component_AppSegmentedButton, {
							modelValue: relation.mode,
							"onUpdate:modelValue": ($event) => relation.mode = $event,
							options: relation.options.map((option) => ({
								value: option.value,
								label: option.label
							})),
							label: relation.title,
							disabled: $data.saving
						}, null, 8, [
							"modelValue",
							"onUpdate:modelValue",
							"options",
							"label",
							"disabled"
						]),
						createBaseVNode("p", _hoisted_19, toDisplayString(relation.items.map((item) => item.title).join(" · ")), 1)
					]);
				}), 128))
			])) : createCommentVNode("", true),
			$data.step === 2 || $data.step === 3 ? (openBlock(), createElementBlock("section", _hoisted_20, [
				createBaseVNode("p", _hoisted_21, toDisplayString($options.t($data.step === 2 ? "Copy current snapshots and their files by process. Message attachments are selected separately." : "Choose tasks, message threads and attachments to duplicate. Attachment choices include their messages and tasks.")), 1),
				!$options.processes.length ? (openBlock(), createElementBlock("p", _hoisted_22, toDisplayString($options.t($data.step === 2 ? "No current snapshots" : "No tasks or messages")), 1)) : createCommentVNode("", true),
				(openBlock(true), createElementBlock(Fragment, null, renderList($options.processes, (process) => {
					return openBlock(), createElementBlock("article", {
						key: process.name,
						class: "duplicate-card"
					}, [createBaseVNode("div", _hoisted_23, [
						createBaseVNode("span", _hoisted_24, [createVNode(_component_AppIcon, { name: "account-tree" })]),
						createBaseVNode("div", null, [createBaseVNode("strong", null, toDisplayString(process.name), 1), $data.step === 2 ? (openBlock(), createElementBlock("small", _hoisted_25, toDisplayString($options.t("Snapshots")) + " " + toDisplayString(process.snapshotCount) + " · " + toDisplayString($options.t("Files")) + " " + toDisplayString(process.fileCount), 1)) : createCommentVNode("", true)]),
						createVNode(_component_SummaryChip, {
							label: $options.t("Items"),
							count: $data.step === 2 ? process.snapshotCount : process.taskCount + process.processMessageCount + process.taskMessageCount,
							"show-dot": false
						}, null, 8, ["label", "count"])
					]), createBaseVNode("div", _hoisted_26, [(openBlock(true), createElementBlock(Fragment, null, renderList($options.pageChoices(process), (choice) => {
						return openBlock(), createBlock(_component_AppCheckbox, {
							key: choice.name,
							"model-value": process[choice.name],
							label: choice.label,
							compact: "",
							disabled: $data.saving,
							"onUpdate:modelValue": ($event) => $options.changeContent(process, choice.name, $event)
						}, {
							default: withCtx(() => [createTextVNode(toDisplayString($options.t(choice.label)) + " " + toDisplayString(process[choice.count]), 1), choice.name === "copySnapshots" ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [createTextVNode(" · " + toDisplayString($options.t("Files")) + " " + toDisplayString(process.fileCount), 1)], 64)) : createCommentVNode("", true)]),
							_: 2
						}, 1032, [
							"model-value",
							"label",
							"disabled",
							"onUpdate:modelValue"
						]);
					}), 128))])]);
				}), 128))
			])) : createCommentVNode("", true),
			$data.step === 4 ? (openBlock(), createElementBlock("section", _hoisted_27, [createBaseVNode("div", _hoisted_28, [
				createVNode(_component_AppIcon, { name: "control-point-duplicate" }),
				createBaseVNode("h3", null, toDisplayString($options.t("Ready to duplicate")), 1),
				createBaseVNode("p", _hoisted_29, toDisplayString($options.t("The new object will have its own identity. Instance links refer to the same objects; selected children and content are copied.")), 1),
				createBaseVNode("div", _hoisted_30, [
					createVNode(_component_SummaryChip, {
						label: $options.t("Related objects"),
						count: $options.totals.related
					}, null, 8, ["label", "count"]),
					createVNode(_component_SummaryChip, {
						label: $options.t("Snapshots"),
						count: $options.totals.snapshots
					}, null, 8, ["label", "count"]),
					createVNode(_component_SummaryChip, {
						label: $options.t("Tasks"),
						count: $options.totals.tasks
					}, null, 8, ["label", "count"]),
					createVNode(_component_SummaryChip, {
						label: $options.t("Messages and files"),
						count: $options.totals.messages
					}, null, 8, ["label", "count"])
				])
			]), createBaseVNode("p", _hoisted_31, [createVNode(_component_AppIcon, { name: "MDI_LIGHTNING_BOLT" }), createTextVNode(toDisplayString($options.t($data.remember ? "These choices will be available for Quick Duplicate." : "These choices apply only to this duplicate.")), 1)])])) : createCommentVNode("", true)
		], 544)], 64)) : createCommentVNode("", true),
		createBaseVNode("footer", null, [createVNode(_component_AppCheckbox, {
			modelValue: $data.remember,
			"onUpdate:modelValue": _cache[4] || (_cache[4] = ($event) => $data.remember = $event),
			label: "Remember choices",
			compact: "",
			disabled: $data.saving || !$data.analysis
		}, null, 8, ["modelValue", "disabled"]), createBaseVNode("div", _hoisted_32, [
			createVNode(_component_AppButton, {
				label: "Cancel",
				disabled: $data.saving,
				onClick: _cache[5] || (_cache[5] = ($event) => $options.close())
			}, null, 8, ["disabled"]),
			$data.step > 0 ? (openBlock(), createBlock(_component_AppButton, {
				key: 0,
				label: "Back",
				icon: "chevron-left",
				"icon-only": "",
				disabled: $data.busy || $data.saving,
				onClick: _cache[6] || (_cache[6] = ($event) => $data.step--)
			}, null, 8, ["disabled"])) : createCommentVNode("", true),
			$data.step < 4 ? (openBlock(), createBlock(_component_AppButton, {
				key: 1,
				label: "Next",
				icon: "chevron-right",
				"icon-only": "",
				disabled: !$data.analysis || $data.busy || $data.saving,
				onClick: _cache[7] || (_cache[7] = ($event) => $data.step++)
			}, null, 8, ["disabled"])) : createCommentVNode("", true),
			createVNode(_component_AppButton, {
				label: "Duplicate",
				icon: "copy",
				highlighted: "",
				disabled: !$data.analysis || $data.busy || $data.saving || $data.uncertain || !$options.valid,
				onClick: $options.duplicate
			}, null, 8, ["disabled", "onClick"])
		])]),
		$data.discard ? (openBlock(), createElementBlock("div", _hoisted_33, [
			createBaseVNode("p", null, toDisplayString($options.t("Discard unsaved changes?")), 1),
			createVNode(_component_AppButton, {
				label: "Continue editing",
				onClick: _cache[8] || (_cache[8] = ($event) => $data.discard = false)
			}),
			createVNode(_component_AppButton, {
				label: "Discard",
				destructive: "",
				onClick: _cache[9] || (_cache[9] = ($event) => $options.close(true))
			})
		])) : createCommentVNode("", true)
	], 40, _hoisted_1)), [[_directive_window, {
		kind: "duplicate_sobject",
		type: "window"
	}]])]);
}
var DuplicateSObject_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { DuplicateSObject_default as default };

//# sourceMappingURL=DuplicateSObject.js.map