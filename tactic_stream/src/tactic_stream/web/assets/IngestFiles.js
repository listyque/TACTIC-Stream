import { E as nextTick, F as resolveComponent, G as withCtx, I as resolveDirective, K as withDirectives, M as openBlock, N as renderList, _ as createElementBlock, b as createVNode, f as Teleport, g as createCommentVNode, h as createBlock, l as withModifiers, m as createBaseVNode, o as vModelText, rt as toDisplayString, tt as normalizeClass, u as Fragment, y as createTextVNode, z as useId } from "./vue.js";
import { D as t, o as _sfc_main$1, rt as _plugin_vue_export_helper_default, u as _sfc_main$2 } from "./index.js";
import { F as rpc, d as _sfc_main$5, f as _sfc_main$3, p as _sfc_main$4 } from "./CodeBlock.js";
import { t as _sfc_main$6 } from "./AppCheckbox.js";
//#region src/features/checkin/IngestFiles.vue
var _sfc_main = {
	setup() {
		return { formId: useId() };
	},
	components: {
		AppButton: _sfc_main$1,
		AppSelect: _sfc_main$3,
		AppSwitch: _sfc_main$4,
		AppCheckbox: _sfc_main$6,
		AppIcon: _sfc_main$2,
		SettingRow: _sfc_main$5
	},
	inject: {
		queueCheckin: { default: null },
		openScriptEditor: { default: null }
	},
	props: {
		ticket: String,
		project: String
	},
	data() {
		return {
			parent: null,
			branch: null,
			scope: null,
			rules: [],
			selectedRule: "",
			options: {},
			extraJson: "{}",
			files: [],
			advanced: false,
			busy: false,
			ready: false,
			error: "",
			discard: false,
			conflicts: null,
			request: 0
		};
	},
	computed: {
		canUpdate() {
			return this.conflicts?.files.filter((item) => item.conflict).every((item) => item.matches.length === 1);
		},
		rule() {
			return this.rules.find((rule) => rule.code === this.selectedRule);
		}
	},
	watch: {
		ticket() {
			this.reset();
		},
		project() {
			if (!this.$refs.dialog?.open) this.reset();
		},
		options: {
			deep: true,
			handler() {
				this.conflicts = null;
			}
		},
		extraJson() {
			this.conflicts = null;
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
		beforeUnload(event) {
			if (this.files.length) {
				event.preventDefault();
				event.returnValue = "";
			}
		},
		reset() {
			this.request++;
			this.files = [];
			this.conflicts = null;
			this.$refs.deleteDialog?.close();
			this.$refs.dialog?.close();
		},
		close(force = false) {
			if (this.busy) return;
			if (!force && this.files.length) {
				this.discard = true;
				return;
			}
			this.reset();
		},
		async open(parent, branch) {
			if (this.$refs.dialog.open) {
				this.$refs.dialog.show();
				return;
			}
			this.parent = parent;
			this.branch = branch;
			this.scope = {
				ticket: this.ticket,
				project: this.project
			};
			this.files = [];
			this.rules = [];
			this.ready = false;
			this.error = "";
			this.discard = false;
			this.conflicts = null;
			this.advanced = false;
			await nextTick();
			this.$refs.dialog.show();
			await this.loadRules();
		},
		async call(action, values = {}) {
			return (await rpc("execute_cmd", [
				{
					...this.scope,
					language: "python"
				},
				"tactic.command.related_ingest_cmd.RelatedIngestCmd",
				{
					action,
					parent_key: this.parent.__search_key__,
					search_type: this.branch.search_type,
					path: this.branch.path || "",
					...values
				}
			])).info;
		},
		async loadRules() {
			const request = ++this.request;
			this.busy = true;
			try {
				const result = await this.call("rules");
				if (request !== this.request) return;
				this.rules = result.rules;
				this.selectRule(this.rules[0]);
				this.ready = true;
			} catch (error) {
				if (request === this.request) this.error = error.message;
			} finally {
				if (request === this.request) this.busy = false;
			}
		},
		selectRule(rule) {
			if (!rule.applicable) return;
			this.selectedRule = rule.code;
			this.options = { ...rule.options };
			this.extraJson = JSON.stringify(rule.options.extraData, null, 2);
			this.conflicts = null;
		},
		values() {
			const extraData = JSON.parse(this.extraJson);
			if (!extraData || Array.isArray(extraData) || typeof extraData !== "object") throw new Error("Extra values must be a JSON object");
			return {
				...this.options,
				extraData
			};
		},
		addFiles(files) {
			if (this.busy) return;
			this.files.push(...[...files].map((file) => ({
				file,
				status: "Ready",
				reason: ""
			})));
			this.conflicts = null;
			this.error = "";
		},
		async start() {
			if (!this.ready || this.busy || !this.files.length) return;
			const request = ++this.request;
			this.error = "";
			this.busy = true;
			this.conflicts = null;
			try {
				const options = this.values();
				const result = await this.call("scan", {
					options,
					filenames: this.files.map((row) => row.file.name)
				});
				if (request !== this.request) return;
				this.files.forEach((row, index) => {
					row.status = result.files[index].accepted ? result.files[index].conflict ? "Conflict" : "Ready" : "Skipped";
					row.reason = result.files[index].reason || "";
				});
				this.conflicts = {
					...result,
					options
				};
				if (!result.files.filter((item) => item.conflict).length) this.enqueue("new");
				else if (options.updateMode === "update" && this.canUpdate) this.enqueue("update");
			} catch (error) {
				if (request === this.request) this.error = error.message;
			} finally {
				if (request === this.request) this.busy = false;
			}
		},
		enqueue(decision) {
			if (!this.conflicts || !this.queueCheckin) return;
			const prepared = this.conflicts;
			const remaining = [];
			try {
				for (const [index, item] of prepared.files.entries()) {
					const row = this.files[index];
					if (!item.accepted || item.conflict && decision === "skip") {
						row.status = "Skipped";
						row.reason ||= "Matching item already exists";
						remaining.push(row);
						continue;
					}
					this.queueCheckin({
						...this.scope,
						searchKey: this.parent.__search_key__,
						title: item.name,
						name: row.file.name,
						files: [row.file],
						file: row.file,
						context: item.context,
						process: prepared.options.process,
						description: "",
						ingest: {
							parent_key: this.parent.__search_key__,
							search_type: this.branch.search_type,
							path: this.branch.path || "",
							options: prepared.options,
							decision: item.conflict ? decision : "new",
							search_key: decision === "update" ? item.matches[0] || "" : ""
						}
					});
					row.queued = true;
				}
				this.files = remaining;
				this.conflicts = null;
				if (!remaining.length) this.reset();
			} catch (error) {
				this.files = this.files.filter((row) => !row.queued);
				this.conflicts = null;
				this.error = error.message;
			}
		},
		async saveRule() {
			if (this.busy) return;
			const request = ++this.request;
			this.busy = true;
			this.error = "";
			try {
				const options = this.values(), title = options.title.trim();
				if (!title) throw new Error("Enter a rule title");
				await this.call("scan", {
					options,
					filenames: ["rule-validation.txt"]
				});
				const data = {
					scan_type: "list",
					action_type: "checkin",
					action: "file",
					search_type: this.branch.search_type,
					rule: options.pattern,
					filter: options.filter,
					ignore: options.ignore,
					column: options.column,
					ignore_ext: options.ignoreExtension,
					update_mode: options.updateMode === "update",
					process: options.process,
					context: options.context,
					context_mode: options.contextMode,
					keywords: options.keywords,
					keyword_mode: options.keywordMode,
					extra_data: options.extraData,
					validation_script: options.validationScript,
					process_script: options.processScript,
					create_icon: options.createIcon
				};
				const payload = {
					title,
					base_dir: "",
					rule: options.pattern,
					data: JSON.stringify(data)
				};
				await rpc(this.rule?.key ? "update" : "insert", [
					{
						...this.scope,
						language: "python"
					},
					this.rule?.key || "config/ingest_rule",
					payload
				]);
				if (request === this.request) await this.loadRules();
			} catch (error) {
				if (request === this.request) this.error = error.message;
			} finally {
				if (request === this.request) this.busy = false;
			}
		},
		async deleteRule() {
			if (this.busy || !this.rule?.key) return;
			const request = ++this.request;
			this.busy = true;
			try {
				await rpc("delete_sobject", [{
					...this.scope,
					language: "python"
				}, this.rule.key]);
				if (request === this.request) {
					this.$refs.deleteDialog.close();
					await this.loadRules();
				}
			} catch (error) {
				if (request === this.request) this.error = error.message;
			} finally {
				if (request === this.request) this.busy = false;
			}
		}
	}
};
var _hoisted_1 = ["aria-label"];
var _hoisted_2 = {
	key: 0,
	role: "alert",
	class: "error"
};
var _hoisted_3 = {
	key: 1,
	role: "status"
};
var _hoisted_4 = {
	key: 2,
	class: "ingest-files-grid"
};
var _hoisted_5 = { class: "ingest-file-list" };
var _hoisted_6 = {
	key: 0,
	class: "muted"
};
var _hoisted_7 = { class: "ingest-file-rows" };
var _hoisted_8 = { key: 0 };
var _hoisted_9 = { class: "ingest-rule-panel" };
var _hoisted_10 = { class: "ingest-rules" };
var _hoisted_11 = { class: "ingest-rule-toggle" };
var _hoisted_12 = ["disabled"];
var _hoisted_13 = ["disabled"];
var _hoisted_14 = { class: "muted" };
var _hoisted_15 = { class: "configuration-actions" };
var _hoisted_16 = {
	key: 3,
	class: "notice",
	role: "alert"
};
var _hoisted_17 = { key: 0 };
var _hoisted_18 = { class: "configuration-actions" };
var _hoisted_19 = {
	key: 4,
	class: "notice",
	role: "alert"
};
var _hoisted_20 = ["aria-label"];
var _hoisted_21 = {
	key: 0,
	class: "error",
	role: "alert"
};
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_AppButton = resolveComponent("AppButton");
	const _component_AppIcon = resolveComponent("AppIcon");
	const _component_AppCheckbox = resolveComponent("AppCheckbox");
	const _component_AppSwitch = resolveComponent("AppSwitch");
	const _component_SettingRow = resolveComponent("SettingRow");
	const _component_AppSelect = resolveComponent("AppSelect");
	const _directive_window = resolveDirective("window");
	return openBlock(), createBlock(Teleport, { to: "body" }, [withDirectives((openBlock(), createElementBlock("dialog", {
		ref: "dialog",
		class: "record-dialog ingest-files",
		"aria-label": $options.t("Add files"),
		onCancel: _cache[31] || (_cache[31] = withModifiers(($event) => $options.close(), ["prevent"])),
		onDragover: _cache[32] || (_cache[32] = withModifiers(() => {}, ["prevent"])),
		onDrop: _cache[33] || (_cache[33] = withModifiers(($event) => $options.addFiles($event.dataTransfer.files), ["prevent"]))
	}, [
		createBaseVNode("header", null, [createBaseVNode("div", null, [createBaseVNode("h2", null, toDisplayString($data.parent?.name || $data.parent?.title || $data.parent?.code) + " → " + toDisplayString($data.branch?.title), 1), createBaseVNode("small", null, toDisplayString($options.t("One Search Object per file · snapshot in publish")) + " · " + toDisplayString($data.branch?.search_type), 1)]), createVNode(_component_AppButton, {
			label: "Close",
			icon: "close",
			disabled: $data.busy,
			onClick: _cache[0] || (_cache[0] = ($event) => $options.close())
		}, null, 8, ["disabled"])]),
		$data.error ? (openBlock(), createElementBlock("p", _hoisted_2, toDisplayString($options.t($data.error)), 1)) : createCommentVNode("", true),
		$data.busy ? (openBlock(), createElementBlock("p", _hoisted_3, toDisplayString($options.t("Loading data…")), 1)) : createCommentVNode("", true),
		$data.ready ? (openBlock(), createElementBlock("div", _hoisted_4, [createBaseVNode("section", _hoisted_5, [
			createBaseVNode("header", null, [
				createBaseVNode("strong", null, toDisplayString($options.t("Files")) + " · " + toDisplayString($data.files.length), 1),
				createVNode(_component_AppButton, {
					label: "Clear",
					icon: "delete-sweep",
					"icon-only": "",
					disabled: $data.busy || !$data.files.length,
					onClick: _cache[1] || (_cache[1] = ($event) => {
						$data.files = [];
						$data.conflicts = null;
					})
				}, null, 8, ["disabled"]),
				createVNode(_component_AppButton, {
					label: "Add files",
					icon: "add",
					"icon-only": "",
					disabled: $data.busy,
					onClick: _cache[2] || (_cache[2] = ($event) => _ctx.$refs.picker.click())
				}, null, 8, ["disabled"])
			]),
			createBaseVNode("input", {
				ref: "picker",
				type: "file",
				multiple: "",
				hidden: "",
				onChange: _cache[3] || (_cache[3] = ($event) => {
					$options.addFiles($event.target.files);
					$event.target.value = "";
				})
			}, null, 544),
			!$data.files.length ? (openBlock(), createElementBlock("p", _hoisted_6, [
				createTextVNode(toDisplayString($options.t("Drop files here")), 1),
				_cache[36] || (_cache[36] = createBaseVNode("br", null, null, -1)),
				createTextVNode(toDisplayString($options.t("Each file creates a child item named without its extension.")), 1)
			])) : createCommentVNode("", true),
			createBaseVNode("ul", _hoisted_7, [(openBlock(true), createElementBlock(Fragment, null, renderList($data.files, (row, index) => {
				return openBlock(), createElementBlock("li", { key: index }, [
					createVNode(_component_AppIcon, {
						name: row.status === "Conflict" ? "warning" : row.status === "Skipped" ? "cancel" : "file",
						class: normalizeClass({ "ingest-conflict": ["Conflict", "Skipped"].includes(row.status) })
					}, null, 8, ["name", "class"]),
					createBaseVNode("div", null, [
						createBaseVNode("span", null, toDisplayString(row.file.name), 1),
						createBaseVNode("small", null, toDisplayString($options.t(row.status)) + " · " + toDisplayString(row.file.size) + " " + toDisplayString($options.t("bytes")), 1),
						row.reason ? (openBlock(), createElementBlock("small", _hoisted_8, toDisplayString($options.t(row.reason)), 1)) : createCommentVNode("", true)
					]),
					createBaseVNode("small", null, toDisplayString(row.file.name.split(".").at(-1).toUpperCase()), 1),
					createVNode(_component_AppButton, {
						label: "Remove file",
						icon: "close",
						"icon-only": "",
						disabled: $data.busy,
						onClick: ($event) => {
							$data.files.splice(index, 1);
							$data.conflicts = null;
						}
					}, null, 8, ["disabled", "onClick"])
				]);
			}), 128))])
		]), createBaseVNode("section", _hoisted_9, [
			createBaseVNode("strong", null, toDisplayString($options.t("Ingest rule")), 1),
			createBaseVNode("div", _hoisted_10, [(openBlock(true), createElementBlock(Fragment, null, renderList($data.rules, (rule) => {
				return openBlock(), createBlock(_component_AppButton, {
					key: rule.code,
					label: rule.title,
					"aria-pressed": $data.selectedRule === rule.code,
					disabled: $data.busy || !rule.applicable,
					icon: rule.code ? "script" : "upload",
					onClick: ($event) => $options.selectRule(rule)
				}, {
					default: withCtx(() => [createBaseVNode("span", null, [createBaseVNode("strong", null, toDisplayString(rule.code ? rule.title : $options.t(rule.title)), 1), createBaseVNode("small", null, toDisplayString($options.t(!rule.applicable ? "For another Search Type" : rule.code ? "Saved server ingest rule" : "Create one child item per file and publish immediately")), 1)])]),
					_: 2
				}, 1032, [
					"label",
					"aria-pressed",
					"disabled",
					"icon",
					"onClick"
				]);
			}), 128))]),
			createBaseVNode("div", _hoisted_11, [createVNode(_component_AppCheckbox, {
				"control-id": $setup.formId + "-extension",
				modelValue: $data.options.ignoreExtension,
				"onUpdate:modelValue": _cache[4] || (_cache[4] = ($event) => $data.options.ignoreExtension = $event),
				label: "Remove extension from item name",
				disabled: $data.busy
			}, null, 8, [
				"control-id",
				"modelValue",
				"disabled"
			]), createVNode(_component_AppButton, {
				label: $data.advanced ? "Hide rule details" : "Edit rule details",
				icon: "settings",
				onClick: _cache[5] || (_cache[5] = ($event) => $data.advanced = !$data.advanced)
			}, null, 8, ["label"])]),
			$data.advanced ? (openBlock(), createElementBlock("fieldset", {
				key: 0,
				disabled: $data.busy,
				class: "ingest-rule-details"
			}, [
				createBaseVNode("label", null, [createTextVNode(toDisplayString($options.t("Include: .mov, /regex/")), 1), withDirectives(createBaseVNode("input", { "onUpdate:modelValue": _cache[6] || (_cache[6] = ($event) => $data.options.filter = $event) }, null, 512), [[vModelText, $data.options.filter]])]),
				createBaseVNode("label", null, [createTextVNode(toDisplayString($options.t("Ignore: .tmp, .db")), 1), withDirectives(createBaseVNode("input", { "onUpdate:modelValue": _cache[7] || (_cache[7] = ($event) => $data.options.ignore = $event) }, null, 512), [[vModelText, $data.options.ignore]])]),
				createVNode(_component_SettingRow, {
					title: "Parse values from a path pattern",
					"control-id": $setup.formId + "-pattern"
				}, {
					default: withCtx(() => [createVNode(_component_AppSwitch, {
						id: $setup.formId + "-pattern",
						modelValue: $data.options.usePattern,
						"onUpdate:modelValue": _cache[8] || (_cache[8] = ($event) => $data.options.usePattern = $event),
						label: "Parse values from a path pattern"
					}, null, 8, ["id", "modelValue"])]),
					_: 1
				}, 8, ["control-id"]),
				createBaseVNode("label", null, [createTextVNode(toDisplayString($options.t("Path pattern")), 1), withDirectives(createBaseVNode("input", {
					"onUpdate:modelValue": _cache[9] || (_cache[9] = ($event) => $data.options.pattern = $event),
					disabled: !$data.options.usePattern,
					placeholder: "{sobject.name}_{snapshot.context}.mov"
				}, null, 8, _hoisted_13), [[vModelText, $data.options.pattern]])]),
				createBaseVNode("label", null, [createTextVNode(toDisplayString($options.t("Process")), 1), withDirectives(createBaseVNode("input", { "onUpdate:modelValue": _cache[10] || (_cache[10] = ($event) => $data.options.process = $event) }, null, 512), [[vModelText, $data.options.process]])]),
				createBaseVNode("label", null, [createTextVNode(toDisplayString($options.t("Context")), 1), withDirectives(createBaseVNode("input", { "onUpdate:modelValue": _cache[11] || (_cache[11] = ($event) => $data.options.context = $event) }, null, 512), [[vModelText, $data.options.context]])]),
				createVNode(_component_SettingRow, {
					title: "Update matching item",
					"control-id": $setup.formId + "-update"
				}, {
					default: withCtx(() => [createVNode(_component_AppSwitch, {
						id: $setup.formId + "-update",
						"model-value": $data.options.updateMode === "update",
						label: "Update matching item",
						"onUpdate:modelValue": _cache[12] || (_cache[12] = ($event) => $data.options.updateMode = $event ? "update" : "insert")
					}, null, 8, ["id", "model-value"])]),
					_: 1
				}, 8, ["control-id"]),
				createVNode(_component_SettingRow, {
					title: "Create preview when supported",
					"control-id": $setup.formId + "-preview"
				}, {
					default: withCtx(() => [createVNode(_component_AppSwitch, {
						id: $setup.formId + "-preview",
						modelValue: $data.options.createIcon,
						"onUpdate:modelValue": _cache[13] || (_cache[13] = ($event) => $data.options.createIcon = $event),
						label: "Create preview when supported"
					}, null, 8, ["id", "modelValue"])]),
					_: 1
				}, 8, ["control-id"]),
				createBaseVNode("label", null, [createTextVNode(toDisplayString($options.t("Extra Search Object values (JSON)")), 1), withDirectives(createBaseVNode("textarea", {
					"onUpdate:modelValue": _cache[14] || (_cache[14] = ($event) => $data.extraJson = $event),
					rows: "4"
				}, null, 512), [[vModelText, $data.extraJson]])]),
				createBaseVNode("label", null, [createTextVNode(toDisplayString($options.t("Keywords")), 1), withDirectives(createBaseVNode("input", { "onUpdate:modelValue": _cache[15] || (_cache[15] = ($event) => $data.options.keywords = $event) }, null, 512), [[vModelText, $data.options.keywords]])]),
				createBaseVNode("label", null, [createTextVNode(toDisplayString($options.t("Keyword mode")), 1), createVNode(_component_AppSelect, {
					modelValue: $data.options.keywordMode,
					"onUpdate:modelValue": _cache[16] || (_cache[16] = ($event) => $data.options.keywordMode = $event),
					label: "Keyword mode",
					options: [
						{
							value: "default",
							label: "Default"
						},
						{
							value: "simplified",
							label: "Simplified"
						},
						{
							value: "none",
							label: "None"
						}
					]
				}, null, 8, ["modelValue"])]),
				createBaseVNode("label", null, [createTextVNode(toDisplayString($options.t("Context case")), 1), createVNode(_component_AppSelect, {
					modelValue: $data.options.contextMode,
					"onUpdate:modelValue": _cache[17] || (_cache[17] = ($event) => $data.options.contextMode = $event),
					label: "Context case",
					options: [{
						value: "case_sensitive",
						label: "Case sensitive"
					}, {
						value: "case_insensitive",
						label: "Lowercase"
					}]
				}, null, 8, ["modelValue"])]),
				createBaseVNode("p", _hoisted_14, toDisplayString($options.t("Scripts receive path, sobject, parent and snapshot. Return a truthy value to accept the file.")), 1),
				createBaseVNode("label", null, [createTextVNode(toDisplayString($options.t("Validation script path")), 1), withDirectives(createBaseVNode("input", { "onUpdate:modelValue": _cache[18] || (_cache[18] = ($event) => $data.options.validationScript = $event) }, null, 512), [[vModelText, $data.options.validationScript]])]),
				createVNode(_component_AppButton, {
					label: "Open validation script",
					icon: "code",
					disabled: !$options.openScriptEditor,
					onClick: _cache[19] || (_cache[19] = ($event) => $options.openScriptEditor($data.options.validationScript))
				}, null, 8, ["disabled"]),
				createBaseVNode("label", null, [createTextVNode(toDisplayString($options.t("Process script path")), 1), withDirectives(createBaseVNode("input", { "onUpdate:modelValue": _cache[20] || (_cache[20] = ($event) => $data.options.processScript = $event) }, null, 512), [[vModelText, $data.options.processScript]])]),
				createVNode(_component_AppButton, {
					label: "Open process script",
					icon: "code",
					disabled: !$options.openScriptEditor,
					onClick: _cache[21] || (_cache[21] = ($event) => $options.openScriptEditor($data.options.processScript))
				}, null, 8, ["disabled"]),
				createBaseVNode("label", null, [createTextVNode(toDisplayString($options.t("Rule title")), 1), withDirectives(createBaseVNode("input", { "onUpdate:modelValue": _cache[22] || (_cache[22] = ($event) => $data.options.title = $event) }, null, 512), [[vModelText, $data.options.title]])]),
				createBaseVNode("div", _hoisted_15, [createVNode(_component_AppButton, {
					label: "Save rule",
					icon: "save",
					onClick: $options.saveRule
				}, null, 8, ["onClick"]), createVNode(_component_AppButton, {
					label: "Delete rule",
					icon: "delete",
					destructive: "",
					disabled: !$options.rule?.key,
					onClick: _cache[23] || (_cache[23] = ($event) => _ctx.$refs.deleteDialog.showModal())
				}, null, 8, ["disabled"])])
			], 8, _hoisted_12)) : createCommentVNode("", true)
		])])) : createCommentVNode("", true),
		$data.conflicts?.files.some((item) => item.conflict) ? (openBlock(), createElementBlock("section", _hoisted_16, [
			createBaseVNode("strong", null, toDisplayString($options.t("Resolve matching names")), 1),
			createBaseVNode("p", null, toDisplayString($data.conflicts.files.filter((item) => item.conflict).map((item) => item.name).join(", ")), 1),
			!$options.canUpdate ? (openBlock(), createElementBlock("p", _hoisted_17, toDisplayString($options.t("Update is unavailable because at least one name does not identify exactly one existing item.")), 1)) : createCommentVNode("", true),
			createBaseVNode("div", _hoisted_18, [
				createVNode(_component_AppButton, {
					label: "Cancel",
					onClick: _cache[24] || (_cache[24] = ($event) => $data.conflicts = null)
				}),
				createVNode(_component_AppButton, {
					label: "Create duplicates",
					icon: "copy",
					onClick: _cache[25] || (_cache[25] = ($event) => $options.enqueue("duplicates"))
				}),
				createVNode(_component_AppButton, {
					label: "Skip existing",
					onClick: _cache[26] || (_cache[26] = ($event) => $options.enqueue("skip"))
				}),
				createVNode(_component_AppButton, {
					label: "Update existing",
					icon: "refresh",
					disabled: !$options.canUpdate,
					onClick: _cache[27] || (_cache[27] = ($event) => $options.enqueue("update"))
				}, null, 8, ["disabled"])
			])
		])) : createCommentVNode("", true),
		createBaseVNode("footer", null, [createVNode(_component_AppButton, {
			label: "Close",
			disabled: $data.busy,
			onClick: _cache[28] || (_cache[28] = ($event) => $options.close())
		}, null, 8, ["disabled"]), createVNode(_component_AppButton, {
			label: "Ingest files",
			icon: "upload",
			highlighted: "",
			disabled: !$data.ready || $data.busy || !$data.files.length || !$options.queueCheckin || !!$data.conflicts,
			onClick: $options.start
		}, {
			default: withCtx(() => [createTextVNode(toDisplayString($options.t("Ingest {count}", { count: $data.files.length })), 1)]),
			_: 1
		}, 8, ["disabled", "onClick"])]),
		$data.discard ? (openBlock(), createElementBlock("div", _hoisted_19, [
			createBaseVNode("p", null, toDisplayString($options.t("Discard unsaved changes?")), 1),
			createVNode(_component_AppButton, {
				label: "Continue editing",
				onClick: _cache[29] || (_cache[29] = ($event) => $data.discard = false)
			}),
			createVNode(_component_AppButton, {
				label: "Discard",
				destructive: "",
				onClick: _cache[30] || (_cache[30] = ($event) => $options.close(true))
			})
		])) : createCommentVNode("", true)
	], 40, _hoisted_1)), [[_directive_window, {
		kind: "ingest_files",
		type: "window"
	}]]), createBaseVNode("dialog", {
		ref: "deleteDialog",
		class: "record-dialog",
		"aria-label": $options.t("Delete ingest rule?"),
		onCancel: _cache[35] || (_cache[35] = withModifiers(($event) => !$data.busy && _ctx.$refs.deleteDialog.close(), ["prevent"]))
	}, [
		createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString($options.t("Delete ingest rule?")), 1)]),
		createBaseVNode("p", null, toDisplayString($options.t("The rule will be removed from this TACTIC project.")), 1),
		$data.error ? (openBlock(), createElementBlock("p", _hoisted_21, toDisplayString($options.t($data.error)), 1)) : createCommentVNode("", true),
		createBaseVNode("footer", null, [createVNode(_component_AppButton, {
			label: "Cancel",
			disabled: $data.busy,
			onClick: _cache[34] || (_cache[34] = ($event) => _ctx.$refs.deleteDialog.close())
		}, null, 8, ["disabled"]), createVNode(_component_AppButton, {
			label: "Delete rule",
			destructive: "",
			disabled: $data.busy,
			onClick: $options.deleteRule
		}, null, 8, ["disabled", "onClick"])])
	], 40, _hoisted_20)]);
}
var IngestFiles_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { IngestFiles_default as default };

//# sourceMappingURL=IngestFiles.js.map