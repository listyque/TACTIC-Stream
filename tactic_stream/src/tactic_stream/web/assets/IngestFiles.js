import { E as nextTick, F as resolveComponent, G as withCtx, I as resolveDirective, J as markRaw, K as withDirectives, M as openBlock, _ as createElementBlock, b as createVNode, et as unref, f as Teleport, g as createCommentVNode, h as createBlock, l as withModifiers, m as createBaseVNode, nt as normalizeStyle, p as computed, rt as toDisplayString } from "./vue.js";
import { o as t, s as appearance, t as _sfc_main$2, z as _plugin_vue_export_helper_default } from "./AppButton.js";
import { It as randomId, j as rpc } from "./index.js";
import { G as button, H as observeFrameSizes, J as muted, K as label, X as rect, Y as node, t as _sfc_main$3, w as translate } from "./FrameView.js";
import { t as captionHeight } from "./sections.ui.js";
import { t as describe$1 } from "./confirmation.ui.js";
import { t as _sfc_main$4 } from "./AppDialog.js";
import { t as _sfc_main$5 } from "./VirtualCollection.js";
//#region ../src/tactic_stream/shared_ui/features/files/ingest.ui.mjs
function optionValue(field, value) {
	return field === "updateMode" ? value ? "update" : "insert" : value;
}
function status(status) {
	if (status === "Completed") return {
		icon: "check-circle",
		color: "green"
	};
	if (status === "Failed") return {
		icon: "error",
		color: "error"
	};
	if (status === "Conflict") return {
		icon: "warning",
		color: "yellow"
	};
	if (["Skipped", "Cancelled"].includes(status)) return {
		icon: "cancel",
		color: "yellow"
	};
	if ([
		"Queued",
		"Running",
		"Checking"
	].includes(status)) return {
		icon: "sync",
		color: "action"
	};
	return {
		icon: "file",
		color: "secondaryText"
	};
}
function fileHeight(record) {
	return record.error ? 62 : 46;
}
function fileRow(model, record, index, width, language) {
	const tr = (text) => translate(text, language), height = fileHeight(record), state = status(record.status), key = String(index), textWidth = Math.max(0, width - 138);
	return { nodes: [node("Box", "ingestFile_" + key, rect(0, 0, width, height), {
		background: "row",
		border: "outlineVariant",
		radius: 12,
		children: [
			node("Icon", "ingestFileStatus_" + key, rect(10, (height - 17) / 2, 17, 17), state),
			label("ingestFileTitle_" + key, rect(35, record.error ? 8 : 0, textWidth, record.error ? 22 : height), record.title, {
				elideMiddle: true,
				toolTip: record.title + "\n" + tr(record.status) + (record.size == null ? "" : " · " + record.size + " " + tr("bytes"))
			}),
			...record.error ? [label("ingestFileError_" + key, rect(35, 32, textWidth, 20), tr(record.error), {
				fontRole: "caption",
				color: "error"
			})] : [],
			label("ingestFileExtension_" + key, rect(width - 96, 0, 48, height), (record.extension || "FILE").toUpperCase(), {
				fontRole: "caption",
				color: "secondaryText",
				align: "right"
			}),
			button("ingestFileRemove_" + key, rect(width - 40, (height - 28) / 2, 28, 28), tr("Remove file"), "close", {
				type: "remove",
				index
			}, !model.busy, {
				iconOnly: true,
				iconAction: true
			})
		]
	})] };
}
function ruleRow(model, record, width, language) {
	const tr = (text) => translate(text, language);
	return { nodes: [node("Action", "ingestRule_" + record.ruleId, rect(0, 0, width, 50), {
		text: record.title,
		selected: record.selected,
		enabled: record.applicable && !model.busy,
		opacity: record.applicable ? 1 : .5,
		normalColor: "row",
		selectedColor: "selected",
		radius: 12,
		action: {
			type: "rule",
			key: record.ruleId
		},
		children: [
			node("Icon", "ingestRuleIcon_" + record.ruleId, rect(10, 16, 17, 17), {
				icon: record.builtIn ? "upload" : "script-python",
				color: record.selected ? "action" : "secondaryText"
			}),
			label("ingestRuleTitle_" + record.ruleId, rect(35, 5, width - 45, 22), record.builtIn ? tr("Quick ingest") : record.title, { weight: 600 }),
			label("ingestRuleSubtitle_" + record.ruleId, rect(35, 27, width - 45, 18), !record.applicable ? tr("For another Search Type") : record.builtIn ? tr("Create one child item per file and publish immediately") : record.subtitle, {
				fontRole: "caption",
				color: "secondaryText"
			})
		]
	})] };
}
function ruleEditor(model, width, language) {
	const tr = (text) => translate(text, language), options = model.options || {}, nodes = [], enabled = !model.busy, stacked = width < 430;
	let y = 0;
	function heading(id, title) {
		nodes.push(label(id, rect(0, y, width, 24), tr(title), Object.assign({}, muted, { weight: 600 })));
		y += 32;
	}
	function field(name, title, x, fieldWidth, top = y, active = enabled) {
		nodes.push(node("Field", "ingestOption_" + name, rect(x, top, fieldWidth, 36), {
			label: tr(title),
			placeholder: tr(title),
			text: options[name] || "",
			enabled: active,
			action: {
				type: "option",
				field: name
			}
		}));
	}
	function pair(left, right) {
		const w = stacked ? width : (width - 8) / 2;
		field(left[0], left[1], 0, w);
		field(right[0], right[1], stacked ? 0 : w + 8, w, y + (stacked ? 44 : 0));
		y += stacked ? 88 : 44;
	}
	function check(name, title, checked) {
		const h = Math.max(32, captionHeight(tr(title), width - 40));
		nodes.push(node("CheckBox", "ingestOption_" + name, rect(0, y, width, h), {
			text: tr(title),
			checked: checked === void 0 ? !!options[name] : checked,
			enabled,
			action: {
				type: "option",
				field: name
			}
		}));
		y += h + 8;
	}
	function choice(name, title, values) {
		nodes.push(label("ingestLabel_" + name, rect(0, y, width, 20), tr(title), muted));
		y += 26;
		nodes.push(node("Choice", "ingestOption_" + name, rect(0, y, width, 36), {
			label: tr(title),
			value: options[name],
			options: values.map(([value, title]) => ({
				value,
				label: tr(title)
			})),
			enabled,
			action: {
				type: "option",
				field: name
			}
		}));
		y += 46;
	}
	heading("ingestSelectionHeading", "File selection");
	pair(["filter", "Include: .mov, /regex/"], ["ignore", "Ignore: .tmp, .db"]);
	check("usePattern", "Parse values from a path pattern");
	field("pattern", "{sobject.name}_{snapshot.context}.mov", 0, width, y, enabled && !!options.usePattern);
	y += 46;
	heading("ingestPublishHeading", "Publish target");
	pair(["process", "Process"], ["context", "Context"]);
	check("updateMode", "Update matching item", options.updateMode === "update");
	check("createIcon", "Create preview when supported");
	nodes.push(label("ingestExtraLabel", rect(0, y, width, 20), tr("Extra Search Object values (JSON)"), muted));
	y += 26;
	nodes.push(node("Area", "ingestOption_extraDataJson", rect(0, y, width, 82), {
		label: tr("Extra Search Object values (JSON)"),
		text: options.extraDataJson || "{}",
		enabled,
		action: {
			type: "option",
			field: "extraDataJson"
		}
	}));
	y += 92;
	field("keywords", "Keywords", 0, width);
	y += 46;
	choice("keywordMode", "Keyword mode", [
		["default", "Default"],
		["simplified", "Simplified"],
		["none", "None"]
	]);
	choice("contextMode", "Context case", [["case_sensitive", "Case sensitive"], ["case_insensitive", "Lowercase"]]);
	heading("ingestScriptsHeading", "TACTIC server scripts");
	const help = tr("Scripts receive path, sobject, parent and snapshot. Return a truthy value to accept the file."), helpHeight = captionHeight(help, width);
	nodes.push(label("ingestScriptsHelp", rect(0, y, width, helpHeight), help, Object.assign({}, muted, { wrap: true })));
	y += helpHeight + 10;
	for (const [name, title] of [["validationScript", "Validation script path"], ["processScript", "Process script path"]]) {
		field(name, title, 0, Math.max(0, width - 44));
		nodes.push(button("ingestOpen_" + name, rect(width - 36, y, 36, 36), tr("Open Script Editor"), "script-python", {
			type: "script",
			field: name
		}, enabled && model.canOpenScript !== false, {
			iconOnly: true,
			iconAction: true
		}));
		y += 46;
	}
	field("title", "Rule title", 0, width);
	y += 46;
	nodes.push(button("ingestSaveRule", rect(0, y, (width - 8) / 2, 38), tr("Save rule"), "save", { type: "saveRule" }, enabled));
	nodes.push(button("ingestDeleteRule", rect((width + 8) / 2, y, (width - 8) / 2, 38), tr("Delete rule"), "delete", { type: "deleteRule" }, enabled && !!model.canDeleteRule, { destructive: true }));
	return {
		nodes,
		height: y + 46
	};
}
function describe(model, width, height, language) {
	const tr = (text, values) => translate(text, language, values), narrow = width < 720, footerHeight = 58, headerHeight = width < 480 ? 76 : 62, inner = Math.max(0, width - 20), bodyHeight = Math.max(0, height - headerHeight - footerHeight - 20), filesWidth = narrow ? inner : Math.min(380, Math.max(280, inner * .4)), filesHeight = narrow ? Math.min(220, bodyHeight * .42) : bodyHeight, rulesWidth = narrow ? inner : inner - filesWidth - 10, rulesHeight = narrow ? Math.max(0, bodyHeight - filesHeight - 10) : bodyHeight, nodes = [node("Box", "ingestBackground", rect(0, 0, width, height), {
		background: "workspace",
		radius: 0
	})];
	nodes.push(node("Box", "ingestContext", rect(0, 0, width, headerHeight), {
		background: "surfaceContainer",
		children: [
			node("Icon", "ingestContextIcon", rect(14, 17, 22, 22), {
				icon: "upload",
				color: "action"
			}),
			label("ingestTarget", rect(46, 9, width - 60, 25), (model.parentTitle || tr("Parent")) + " → " + (model.targetTitle || tr("Child items")), {
				fontRole: "bodyLarge",
				weight: 600
			}),
			label("ingestSubtitle", rect(46, 35, width - 60, headerHeight - 40), tr("One Search Object per file · snapshot in publish") + " · " + (model.searchType || ""), {
				fontRole: "caption",
				color: "secondaryText",
				wrap: narrow
			})
		]
	}));
	const fileChildren = [
		label("ingestFilesHeading", rect(10, 8, filesWidth - 90, 28), tr("Files") + " · " + model.count, { weight: 600 }),
		button("ingestClearFiles", rect(filesWidth - 76, 8, 28, 28), tr("Clear"), "delete-sweep", { type: "clear" }, !model.busy && model.count > 0, {
			iconOnly: true,
			iconAction: true
		}),
		button("ingestAddFiles", rect(filesWidth - 38, 8, 28, 28), tr("Add files"), "add", { type: "add" }, !model.busy, {
			iconOnly: true,
			iconAction: true
		}),
		node("Box", "ingestFilesDivider", rect(0, 44, filesWidth, 1), { background: "outlineVariant" })
	];
	if (model.count) fileChildren.push(node("View", "ingestFileList", rect(0, 45, filesWidth, Math.max(0, filesHeight - 45)), { view: "files" }));
	else {
		const top = Math.max(48, (filesHeight - 72) / 2);
		fileChildren.push(label("ingestEmptyTitle", rect(12, top, filesWidth - 24, 26), tr("Drop files here"), {
			weight: 600,
			align: "center"
		}));
		fileChildren.push(label("ingestEmptyHelp", rect(12, top + 30, filesWidth - 24, 42), tr("Each file creates a child item named without its extension."), Object.assign({}, muted, {
			wrap: true,
			align: "center"
		})));
	}
	nodes.push(node("Box", "ingestFilesPanel", rect(10, headerHeight + 10, filesWidth, filesHeight), {
		background: "panelDeep",
		border: "outlineVariant",
		radius: 16,
		clip: true,
		children: fileChildren
	}));
	const rw = Math.max(0, rulesWidth - 32), listHeight = Math.min(174, Math.max(52, model.ruleCount * 54)), children = [label("ingestRuleHeading", rect(0, 0, rw, 24), tr("Ingest rule"), { weight: 600 }), node("List", "ingestRules", rect(0, 32, rw, listHeight), {
		source: "rules",
		keyField: "ruleId",
		rowHeight: 54,
		rowGap: 4,
		label: tr("Ingest rule"),
		fields: [
			"ruleId",
			"title",
			"subtitle",
			"selected",
			"builtIn",
			"applicable"
		]
	})];
	let y = 42 + listHeight;
	const checkboxHeight = Math.max(32, captionHeight(tr("Remove extension from item name"), rw - 40));
	children.push(node("CheckBox", "ingestOption_ignoreExtension", rect(0, y, rw, checkboxHeight), {
		text: tr("Remove extension from item name"),
		checked: !!model.options?.ignoreExtension,
		enabled: !model.busy,
		action: {
			type: "option",
			field: "ignoreExtension"
		}
	}));
	y += checkboxHeight + 8;
	children.push(button("ingestAdvanced", rect(0, y, rw, 36), tr(model.advanced ? "Hide rule details" : "Edit rule details"), model.advanced ? "expand-less" : "settings", { type: "advanced" }, !model.busy));
	y += 46;
	if (model.advanced) {
		const form = ruleEditor(model, rw, language);
		children.push(node("Box", "ingestRuleEditor", rect(0, y, rw, form.height), { children: form.nodes }));
		y += form.height;
	}
	if (model.rulesBusy) children.push(label("ingestRulesLoading", rect(0, y, rw, 28), tr("Loading ingest rules…"), Object.assign({}, muted, { role: "status" })));
	nodes.push(node("Box", "ingestRulePanel", rect(narrow ? 10 : filesWidth + 20, headerHeight + 10 + (narrow ? filesHeight + 10 : 0), rulesWidth, rulesHeight), {
		background: "panelDeep",
		border: "outlineVariant",
		radius: 16,
		children: [node("Scroll", "ingestOptionsViewport", rect(8, 8, rulesWidth - 16, rulesHeight - 16), {
			contentHeight: y + (model.rulesBusy ? 38 : 0),
			children
		})]
	}));
	const footerY = Math.max(0, height - footerHeight), actionWidth = width < 480 ? 126 : 150, closeWidth = 90, actionX = width - actionWidth - 12;
	nodes.push(node("Box", "ingestFooter", rect(0, footerY, width, footerHeight), {
		background: "surfaceContainer",
		children: [
			label("ingestMessage", rect(12, 6, Math.max(0, actionX - closeWidth - 40), 46), model.error || model.message || (model.busy ? tr("Loading data…") : ""), {
				fontRole: "caption",
				wrap: true,
				color: model.error ? "error" : "secondaryText",
				role: model.error ? "alert" : "status"
			}),
			button("ingestClose", rect(actionX - closeWidth - 8, 10, closeWidth, 38), tr(model.busy && model.canStop ? "Stop" : "Close"), "", { type: model.busy && model.canStop ? "stop" : "close" }, !model.busy || !!model.canStop),
			button("ingestStart", rect(actionX, 10, actionWidth, 38), tr("Ingest {count}", { count: model.count }), "upload", { type: "start" }, !model.busy && !model.rulesBusy && model.ready !== false && model.count > 0 && model.canStart !== false, { highlighted: true })
		]
	}));
	return { nodes };
}
function conflict(model, width, language) {
	const tr = (text, values) => translate(text, language, values), nodes = [], inner = Math.max(0, width - 32), compact = width < 480, message = tr("{count} file(s) match existing child items or repeat a name in this batch. What should ingest do?", { count: model.conflictCount }), messageHeight = Math.max(40, captionHeight(message, inner));
	nodes.push(label("ingestConflictMessage", rect(16, 12, inner, messageHeight), message, { wrap: true }));
	let y = 22 + messageHeight;
	if (model.conflictNames?.length) {
		nodes.push(label("ingestConflictNames", rect(16, y, inner, 22), tr("Conflicts: {names}", { names: model.conflictNames.slice(0, 5).join(", ") }), muted));
		y += 32;
	}
	if (!model.canUpdateConflicts) {
		const text = tr("Update is unavailable because at least one name does not identify exactly one existing item."), h = captionHeight(text, inner);
		nodes.push(label("ingestConflictUnavailable", rect(16, y, inner, h), text, Object.assign({}, muted, { wrap: true })));
		y += h + 10;
	}
	const columns = compact ? 1 : 2, w = (inner - (columns - 1) * 8) / columns;
	for (const [index, [decision, text, icon]] of [
		[
			"cancel",
			"Cancel",
			""
		],
		[
			"duplicates",
			"Create duplicates",
			"copy"
		],
		[
			"skip",
			"Skip existing",
			"cancel"
		],
		[
			"update",
			"Update existing",
			"refresh"
		]
	].entries()) nodes.push(button("ingestConflict_" + decision, rect(16 + index % columns * (w + 8), y + Math.floor(index / columns) * 46, w, 38), tr(text), icon, {
		type: "conflict",
		decision
	}, decision !== "update" || !!model.canUpdateConflicts, { highlighted: model.canUpdateConflicts ? decision === "update" : decision === "skip" }));
	return {
		nodes,
		height: y + 4 / columns * 46 + 8
	};
}
//#endregion
//#region src/features/checkin/IngestFileList.vue
var _hoisted_1$1 = { class: "ingest-file-viewport" };
var _sfc_main$1 = {
	__name: "IngestFileList",
	props: {
		records: Array,
		busy: Boolean,
		frameNode: Object
	},
	emits: ["remove"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const items = computed(() => props.records.map((record, index) => ({
			key: record.key,
			height: fileHeight(record),
			data: {
				record,
				index
			}
		})));
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", _hoisted_1$1, [createVNode(_sfc_main$5, {
				items: items.value,
				"row-gap": 4
			}, {
				default: withCtx(({ item }) => [createVNode(_sfc_main$3, {
					style: normalizeStyle({ height: fileHeight(item.record) + "px" }),
					scene: fileRow({ busy: __props.busy }, item.record, item.index, Math.max(0, __props.frameNode.width - 28), unref(appearance).language),
					onEvent: _cache[0] || (_cache[0] = ($event) => emit("remove", $event.index))
				}, null, 8, ["style", "scene"])]),
				_: 1
			}, 8, ["items"])]);
		};
	}
};
//#endregion
//#region src/features/checkin/IngestFiles.vue
var _sfc_main = {
	components: {
		AppButton: _sfc_main$2,
		AppDialog: _sfc_main$4,
		FrameView: _sfc_main$3
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
			request: 0,
			viewport: {
				width: 920,
				height: 650
			},
			conflictWidth: 540,
			confirmationWidth: 400
		};
	},
	computed: {
		frameModel() {
			return {
				parentTitle: this.parent?.name || this.parent?.title || this.parent?.code,
				targetTitle: this.branch?.title,
				searchType: this.branch?.search_type,
				count: this.files.length,
				ruleCount: this.rules.length,
				ready: this.ready,
				busy: this.busy,
				rulesBusy: !this.ready && this.busy,
				canDeleteRule: !!this.rule?.key,
				canStart: !!this.queueCheckin && !this.conflicts,
				canOpenScript: !!this.openScriptEditor,
				advanced: this.advanced,
				options: {
					...this.options,
					extraDataJson: this.extraJson
				},
				error: t(this.error)
			};
		},
		scene() {
			return describe(this.frameModel, this.viewport.width, this.viewport.height, appearance.language);
		},
		presentedRules() {
			return this.rules.map((rule) => ({
				ruleId: rule.code,
				title: rule.title,
				subtitle: rule.subtitle || "",
				selected: rule.code === this.selectedRule,
				builtIn: !rule.key,
				applicable: rule.applicable
			}));
		},
		presentedFiles() {
			return this.files.map((row) => ({
				key: row.key,
				title: row.file.name,
				extension: row.file.name.includes(".") ? row.file.name.split(".").at(-1) : "",
				status: row.status,
				size: row.file.size,
				error: row.reason
			}));
		},
		views() {
			return { files: {
				component: markRaw(_sfc_main$1),
				nodeProps: true,
				props: {
					records: this.presentedFiles,
					busy: this.busy,
					onRemove: this.removeFile
				}
			} };
		},
		conflictScene() {
			const files = this.conflicts?.files.filter((item) => item.conflict) || [];
			return conflict({
				conflictCount: files.length,
				conflictNames: [...new Set(files.map((item) => item.name))],
				canUpdateConflicts: this.canUpdate
			}, this.conflictWidth, appearance.language);
		},
		confirmationScene() {
			return describe$1({
				message: t("The rule will be removed from this TACTIC project."),
				accept: "Delete rule",
				destructive: true,
				busy: this.busy
			}, this.confirmationWidth, 170, appearance.language);
		},
		discardScene() {
			return describe$1({
				message: t("Discard unsaved changes?"),
				reject: "Continue editing",
				accept: "Discard",
				destructive: true
			}, this.confirmationWidth, 170, appearance.language);
		},
		canUpdate() {
			return this.conflicts?.files.filter((item) => item.conflict).every((item) => item.matches.length === 1);
		},
		rule() {
			return this.rules.find((rule) => rule.code === this.selectedRule);
		}
	},
	watch: {
		async conflicts() {
			await nextTick();
			if (!this.$refs.conflictDialog) return;
			const pending = this.conflicts?.files.some((item) => item.conflict);
			if (pending && !this.$refs.conflictDialog.open) this.$refs.conflictDialog.show(this.$refs.workspace);
			else if (!pending) this.$refs.conflictDialog.close();
		},
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
		this.frameObserver = observeFrameSizes((entries) => {
			for (const entry of entries) {
				if (entry.contentRect.width <= 0) continue;
				if (entry.target === this.$refs.workspace) this.viewport = {
					width: entry.contentRect.width,
					height: entry.contentRect.height
				};
				else if (entry.target === this.$refs.conflictContent) this.conflictWidth = entry.contentRect.width;
				else this.confirmationWidth = entry.contentRect.width;
			}
		});
		for (const name of [
			"workspace",
			"conflictContent",
			"deleteContent",
			"discardContent"
		]) this.frameObserver.observe(this.$refs[name]);
	},
	beforeUnmount() {
		this.request++;
		this.frameObserver?.disconnect();
		window.removeEventListener("beforeunload", this.beforeUnload);
	},
	methods: {
		t,
		describeRow(list, record) {
			return ruleRow(this.frameModel, record, list.width - 16, appearance.language);
		},
		removeFile(index) {
			if (this.busy) return;
			this.files.splice(index, 1);
			this.conflicts = null;
		},
		dispatch(action) {
			if (action.type === "option") {
				if (this.busy) return;
				const value = optionValue(action.field, action.value);
				if (action.field === "extraDataJson") this.extraJson = value;
				else this.options[action.field] = value;
			} else if (action.type === "rule") this.selectRule(this.rules.find((rule) => rule.code === action.key));
			else if (action.type === "advanced") this.advanced = !this.advanced;
			else if (action.type === "clear") {
				this.files = [];
				this.conflicts = null;
			} else if (action.type === "add") this.$refs.picker.click();
			else if (action.type === "start") this.start();
			else if (action.type === "close") this.close();
			else if (action.type === "saveRule") this.saveRule();
			else if (action.type === "deleteRule") this.$refs.deleteDialog.show(this.$refs.workspace);
			else if (action.type === "script") this.openScriptEditor?.(this.options[action.field]);
			else if (action.type === "conflict") {
				if (action.decision === "cancel") this.conflicts = null;
				else this.enqueue(action.decision);
			}
		},
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
			this.$refs.discardDialog?.close();
			this.$refs.deleteDialog?.close();
			this.$refs.dialog?.close();
		},
		close(force = false) {
			if (this.busy) return;
			if (!force && this.files.length) {
				this.discard = true;
				this.$refs.discardDialog.show(this.$refs.workspace);
				return;
			}
			this.reset();
		},
		windowContext() {
			if (this.busy || this.files.length || this.conflicts) throw Error("Apply or discard unsaved changes first");
			return {
				project: this.project,
				route: {
					searchType: this.parent.__search_key__.split("?")[0],
					args: [this.parent, this.branch]
				}
			};
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
			if (!rule?.applicable) return;
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
				key: randomId(),
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
				if (request !== this.request) return;
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
var _hoisted_2 = ["aria-busy"];
var _hoisted_3 = {
	key: 0,
	class: "error",
	role: "alert"
};
var _hoisted_4 = {
	ref: "deleteContent",
	class: "ingest-dialog-content",
	style: { "height": "170px" }
};
var _hoisted_5 = {
	ref: "discardContent",
	class: "ingest-dialog-content",
	style: { "height": "170px" }
};
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_AppButton = resolveComponent("AppButton");
	const _component_FrameView = resolveComponent("FrameView");
	const _component_AppDialog = resolveComponent("AppDialog");
	const _directive_window = resolveDirective("window");
	return openBlock(), createBlock(Teleport, { to: "body" }, [
		withDirectives((openBlock(), createElementBlock("dialog", {
			ref: "dialog",
			class: "record-dialog ingest-files",
			"aria-label": $options.t("Add files"),
			onCancel: _cache[2] || (_cache[2] = withModifiers(($event) => $options.close(), ["prevent"])),
			onDragover: _cache[3] || (_cache[3] = withModifiers(() => {}, ["prevent"])),
			onDrop: _cache[4] || (_cache[4] = withModifiers(($event) => $options.addFiles($event.dataTransfer.files), ["prevent"]))
		}, [
			createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString($options.t("Add files")), 1), createVNode(_component_AppButton, {
				label: "Close",
				icon: "close",
				disabled: $data.busy,
				onClick: _cache[0] || (_cache[0] = ($event) => $options.close())
			}, null, 8, ["disabled"])]),
			createBaseVNode("div", {
				ref: "workspace",
				class: "ingest-workspace",
				"aria-busy": $data.busy
			}, [createVNode(_component_FrameView, {
				scene: $options.scene,
				models: { rules: $options.presentedRules },
				"describe-row": $options.describeRow,
				views: $options.views,
				onEvent: $options.dispatch
			}, null, 8, [
				"scene",
				"models",
				"describe-row",
				"views",
				"onEvent"
			])], 8, _hoisted_2),
			createBaseVNode("input", {
				ref: "picker",
				type: "file",
				multiple: "",
				hidden: "",
				onChange: _cache[1] || (_cache[1] = ($event) => {
					$options.addFiles($event.target.files);
					$event.target.value = "";
				})
			}, null, 544)
		], 40, _hoisted_1)), [[_directive_window, {
			kind: "ingest_files",
			type: "window",
			page: $options.windowContext
		}]]),
		createVNode(_component_AppDialog, {
			ref: "conflictDialog",
			class: "ingest-conflict-dialog",
			title: "Resolve matching names",
			"close-on-outside": false,
			onRejected: _cache[5] || (_cache[5] = ($event) => $data.conflicts = null)
		}, {
			default: withCtx(() => [createBaseVNode("div", {
				ref: "conflictContent",
				class: "ingest-dialog-content",
				style: normalizeStyle({ height: $options.conflictScene.height + "px" })
			}, [createVNode(_component_FrameView, {
				scene: $options.conflictScene,
				onEvent: $options.dispatch
			}, null, 8, ["scene", "onEvent"])], 4)]),
			_: 1
		}, 512),
		createVNode(_component_AppDialog, {
			ref: "deleteDialog",
			class: "ingest-confirmation-dialog",
			title: "Delete ingest rule?",
			"close-on-escape": !$data.busy,
			"close-on-outside": !$data.busy
		}, {
			default: withCtx(() => [$data.error ? (openBlock(), createElementBlock("p", _hoisted_3, toDisplayString($options.t($data.error)), 1)) : createCommentVNode("", true), createBaseVNode("div", _hoisted_4, [createVNode(_component_FrameView, {
				scene: $options.confirmationScene,
				onEvent: _cache[6] || (_cache[6] = ($event) => $event.type === "accept" ? $options.deleteRule() : _ctx.$refs.deleteDialog.close())
			}, null, 8, ["scene"])], 512)]),
			_: 1
		}, 8, ["close-on-escape", "close-on-outside"]),
		createVNode(_component_AppDialog, {
			ref: "discardDialog",
			class: "ingest-confirmation-dialog",
			title: "Discard unsaved changes?",
			onRejected: _cache[8] || (_cache[8] = ($event) => $data.discard = false)
		}, {
			default: withCtx(() => [createBaseVNode("div", _hoisted_5, [createVNode(_component_FrameView, {
				scene: $options.discardScene,
				onEvent: _cache[7] || (_cache[7] = ($event) => $event.type === "accept" ? $options.close(true) : _ctx.$refs.discardDialog.close())
			}, null, 8, ["scene"])], 512)]),
			_: 1
		}, 512)
	]);
}
var IngestFiles_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { IngestFiles_default as default };

//# sourceMappingURL=IngestFiles.js.map