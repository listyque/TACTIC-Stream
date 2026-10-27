import { t as __exportAll } from "./rolldown-runtime.js";
import { I as resolveComponent, N as openBlock, _ as createElementBlock, b as createVNode, f as Teleport, h as createBlock, m as createBaseVNode, q as withDirectives, rt as normalizeStyle, s as vShow } from "./vue.js";
import { A as t, j as appearance, ot as _plugin_vue_export_helper_default } from "./index.js";
import { Gt as button, Jt as node, Kt as label, Yt as rect, ct as rpc, i as _sfc_main$1, qt as muted, r as observeFrameSizes, y as translate } from "./CodeBlock.js";
import { n as sections } from "./sections.ui.js";
import { $ as sectionSelector, Q as policy, X as documentEvent, Z as notices, tt as toolbar$1 } from "./App.js";
//#region ../src/tactic_stream/shared_ui/features/administration/naming/naming.ui.mjs
function toolbar(model, ui, width, language) {
	const tr = (text) => translate(text, language), actions = toolbar$1(model, ui, width, language), edit = !model.busy && !model.uncertain && model.canWrite && !ui.confirmation;
	actions.nodes = actions.nodes.filter((row) => row.id !== "adminDocumentStatus");
	actions.nodes.push(button("namingCreate", rect(46, 0, 38, 38), tr("Create naming rule"), "add", { type: "create" }, edit, { iconOnly: true }), button("namingDuplicate", rect(90, 0, 38, 38), tr("Duplicate selected rule"), "copy", { type: "duplicate" }, edit && model.ready, { iconOnly: true }));
	return actions;
}
function title(row, language) {
	const record = row.document || {}, match = /snapshot\.context\)\s*==\s*['"]?([\w/.-]+)/.exec(record.condition || "");
	return record.context || match && match[1] || record.script_path || translate(record.latest_versionless || record.current_versionless ? "Versionless" : "Default", language);
}
function describe(model, ui, width, height, language) {
	if (width <= 0 || height <= 0) return { nodes: [] };
	const tr = (text) => translate(text, language), local = model.previewMode === "local", noticeModel = Object.assign({}, model, { error: model.error || ui.error });
	if (ui.confirmation === "execute") noticeModel.confirmationText = "Run custom naming code? This uses the normal server environment, not an isolated sandbox. Scripts and classes can change data or files.";
	if (ui.confirmation === "save") noticeModel.confirmationText = "Update project naming rule? This changes future check-ins in the current project. Existing files are kept.";
	const notice = notices(noticeModel, ui, width, language, "Discard unsaved naming changes?", ui.confirmation === "execute" ? "Evaluate with custom code" : void 0), nodes = notice.nodes;
	const y = notice.top, h = height - y, split = width >= 800, left = split ? Math.min(ui.catalogWidth, width * .4) : width, editing = split || ui.editing;
	if (h < 220) return { nodes: [node("Scroll", "namingPageScroll", rect(0, 0, width, height), {
		contentHeight: 400 + y,
		children: describe(model, ui, width - 16, 400 + y, language).nodes
	})] };
	if (split || !ui.editing) nodes.push(node("Box", "namingCatalogPanel", rect(0, y, left, h), {
		background: "surfaceContainerLow",
		border: "outlineVariant",
		children: [label("namingCatalogTitle", rect(12, 8, left - 24, 28), tr("Naming rules"), {
			fontRole: "section",
			weight: 600
		}), node("List", "namingRules", rect(12, 44, left - 24, h - 56), {
			source: "namingRules",
			keyField: "identity",
			rowHeight: 86,
			scrollbarId: "namingRulesScrollBar"
		})].concat(model.rules.length ? [] : [label("namingRulesEmpty", rect(12, 52, left - 24, 100), tr("No rules for this search type"), Object.assign({ wrap: true }, muted))])
	}));
	if (split) nodes.push(node("Splitter", "namingSplitHandle", rect(left, y, 10, h), {
		text: tr("Naming rules panel width"),
		value: left,
		min: 180,
		max: width * .4,
		action: { type: "split" }
	}));
	if (!editing) return { nodes };
	const bounds = rect(split ? left + 10 : 0, y, split ? width - left - 10 : width, h), w = bounds.width - 40, children = [];
	let top = 12;
	if (!split) {
		children.push(button("namingBack", rect(12, top, 110, 36), tr("Back"), "chevron-left", { type: "back" }, !model.busy && !!model.identity));
		top += 44;
	}
	children.push(label("namingTargetTitle", rect(12, top, w, 26), model.targetTitle || model.searchType || tr("Naming editor"), {
		fontRole: "section",
		weight: 600
	}), label("namingTargetType", rect(12, top + 30, w, 22), model.project + " / " + model.searchType, muted));
	top += 60;
	if (!model.ready) children.push(label("namingSelectHelp", rect(12, top, w, 80), tr("Select a rule or create a new one."), Object.assign({ wrap: true }, muted)));
	else {
		children.push(sectionSelector("namingPages", [
			{
				value: "rule",
				label: tr("Naming rule"),
				icon: "edit"
			},
			{
				value: "preview",
				label: tr("Naming preview"),
				icon: "search"
			},
			{
				value: "advanced",
				label: tr("Advanced fields"),
				icon: "tune"
			}
		], ui.page, rect(12, top, bounds.width - 24, 38), !model.busy, "page", tr("Naming sections")));
		top += 46;
		const fields = [], text = (key) => Object.prototype.hasOwnProperty.call(ui.text, key) ? ui.text[key] : String(model.document[key] || "");
		const field = (key, title, description, area) => ({
			id: "naming_" + key,
			title,
			description,
			kind: area ? "Area" : "Field",
			height: area ? 82 : 38,
			field: key,
			props: {
				text: text(key),
				action: {
					type: "text",
					field: key
				},
				commitAction: { type: "commit" }
			}
		});
		if (ui.page === "rule") {
			fields.push({
				kind: "Heading",
				id: "namingRuleHeading",
				title: model.identity || "New naming rule"
			}, {
				id: "namingSearchType",
				title: "Search Type",
				props: {
					text: model.searchType,
					readOnly: true
				}
			}, field("context", "Rule context (empty means any)", "Use a context or a native wildcard such as publish/*.", false), {
				kind: "Choice",
				id: "namingCheckin",
				title: "Check-in type",
				field: "checkin_type",
				options: [
					{
						value: "auto",
						label: tr("Auto")
					},
					{
						value: "strict",
						label: tr("Strict")
					},
					{
						value: "",
						label: tr("Unspecified")
					}
				],
				props: { value: model.document.checkin_type || "" }
			}, field("dir_naming", "Directory naming", "", true), field("file_naming", "File naming", "", true));
			for (const flag of [
				["latest_versionless", "Latest versionless"],
				["current_versionless", "Current versionless"],
				["manual_version", "Manual version"]
			]) fields.push({
				kind: "Switch",
				id: "naming_" + flag[0],
				title: flag[1],
				field: flag[0],
				props: { checked: !!model.document[flag[0]] }
			});
		} else if (ui.page === "advanced") {
			fields.push({
				kind: "Heading",
				id: "namingAdvancedHeading",
				title: "Advanced fields"
			});
			for (const row of [
				[
					"snapshot_type",
					"Snapshot type",
					"Empty matches any snapshot type."
				],
				[
					"base_dir_alias",
					"Base directory alias",
					"Repository alias used by native check-in."
				],
				[
					"sandbox_dir_naming",
					"Sandbox directory naming",
					"The sandbox path expression; empty uses Directory naming."
				],
				[
					"sandbox_dir_alias",
					"Sandbox directory alias",
					"Sandbox repository alias used by native check-in."
				],
				[
					"ingest_rule_code",
					"Ingest rule code",
					"Optional ingest rule associated with this naming rule."
				],
				[
					"condition",
					"Condition",
					"A native TACTIC expression evaluated on the object and snapshot."
				],
				[
					"script_path",
					"Script path",
					"Existing server script overriding directory and file naming."
				],
				[
					"class_name",
					"Class name",
					"Installed naming class implementing get_dir and get_file."
				]
			]) fields.push(field(row[0], row[1], row[2], ["condition", "sandbox_dir_naming"].indexOf(row[0]) >= 0));
		} else {
			fields.push({
				kind: "Heading",
				id: "namingPreviewHeading",
				title: "Naming preview",
				description: local ? "Local rule simulation" : "Evaluate the draft on a real object with the native TACTIC engine. Preview does not check in a file."
			});
			if (!local) fields.push({
				kind: "Choice",
				id: "namingSampleObject",
				title: "Search Object",
				options: model.items.map((row) => ({
					value: row.key,
					label: row.label
				})),
				props: {
					value: model.sample.key,
					action: {
						type: "sample",
						field: "key"
					}
				}
			});
			for (const row of [
				["file", "Example file"],
				["process", "Process"],
				["context", "Preview context"],
				["snapshotType", "Snapshot type"],
				["version", "Version"],
				["fileType", "File type"]
			]) {
				if (local && ["process", "snapshotType"].indexOf(row[0]) >= 0 && model.typeMode) continue;
				const version = row[0] === "version";
				fields.push({
					id: "namingSample_" + row[0],
					title: row[1],
					props: {
						text: version && ui.sampleVersion !== null ? ui.sampleVersion : String(model.sample[row[0]] === void 0 ? "" : model.sample[row[0]]),
						inputMode: version ? "numeric" : "text",
						action: version ? { type: "version" } : {
							type: "sample",
							field: row[0]
						},
						commitAction: version ? { type: "commitVersion" } : null
					}
				});
			}
		}
		const body = sections(fields, w, language, policy(model).editable && !ui.confirmation);
		let bottom = body.height;
		if (ui.page === "preview") {
			if (!local) {
				if (model.itemCount > 50) {
					body.nodes.push(button("namingObjectsPrevious", rect(0, bottom, 100, 36), tr("Previous"), "chevron-left", {
						type: "items",
						offset: model.itemOffset - 50
					}, !model.busy && model.itemOffset > 0), label("namingObjectsPage", rect(108, bottom, Math.max(0, w - 216), 36), String(model.itemOffset + 1) + "–" + (model.itemOffset + model.items.length) + " / " + model.itemCount, { align: "center" }), button("namingObjectsNext", rect(w - 100, bottom, 100, 36), tr("Next"), "chevron-right", {
						type: "items",
						offset: model.itemOffset + 50
					}, !model.busy && model.itemOffset + model.items.length < model.itemCount));
					bottom += 44;
				}
				body.nodes.push(button("namingEvaluate", rect(0, bottom, w, 38), tr("Evaluate naming"), "search", { type: "evaluate" }, policy(model).editable && !!model.sample.key), button("namingEvaluateCustom", rect(0, bottom + 46, w, 38), tr("Evaluate with custom code"), "code", {
					type: "evaluate",
					execute: true
				}, policy(model).editable && !!model.sample.key));
				bottom += 96;
			}
			for (const result of model.previewResults || []) {
				body.nodes.push(label("namingResult_" + result.mode, rect(0, bottom, w, 26), tr({
					version: "Version",
					latest: "Latest versionless",
					current: "Current versionless",
					local: "Local rule simulation"
				}[result.mode] || result.mode), { weight: 600 }), node("Area", "namingPath_" + result.mode, rect(0, bottom + 32, w, 100), {
					text: result.path || "",
					label: tr("Naming result"),
					readOnly: true,
					monospace: true
				}));
				bottom += 140;
				const detail = [
					result.status || "",
					result.directory ? tr("Directory naming") + ": " + result.directory : "",
					result.file ? tr("File naming") + ": " + result.file : "",
					result.sandbox ? tr("Sandbox directory naming") + ": " + result.sandbox : "",
					result.matches === false ? tr("This draft is not selected for these parameters by native naming lookup.") + " " + (result.selectedRule || "") : ""
				].filter(Boolean).join("\n");
				if (detail) {
					body.nodes.push(node("Area", "namingResultDetails_" + result.mode, rect(0, bottom, w, 112), {
						text: detail,
						label: tr("Naming result"),
						readOnly: true,
						notice: true
					}));
					bottom += 120;
				}
				if (result.collisions && result.collisions.length) {
					body.nodes.push(node("Area", "namingCollisions_" + result.mode, rect(0, bottom, w, 120), {
						text: tr("Existing files already use this path:") + "\n" + result.collisions.map((row) => row.key + " · " + row.snapshot).join("\n"),
						label: tr("Existing files"),
						readOnly: true,
						color: "error"
					}));
					bottom += 128;
				}
			}
		}
		children.push(node("Scroll", "namingFieldsScroll", rect(12, top, bounds.width - 24, Math.max(1, h - top - 12)), {
			contentHeight: bottom,
			resetKey: ui.page + ":" + model.identity,
			scrollbarId: "namingFieldsScrollBar",
			children: body.nodes
		}));
	}
	nodes.push(node("Box", "namingEditorPanel", bounds, {
		background: "surfaceContainerLow",
		border: "outlineVariant",
		children
	}));
	return { nodes };
}
function row(listNode, record, model, language) {
	const width = listNode.width - 16, doc = record.document || {}, tr = (text) => translate(text, language);
	return { nodes: [node("Action", "namingRule_" + record.identity, rect(0, 0, width, 82), {
		text: title(record, language),
		selected: model.identity === record.identity,
		enabled: !model.busy && (!model.uncertain || model.identity === record.identity),
		normalColor: "transparent",
		selectedColor: "contentSelection",
		children: [
			label("namingRuleTitle_" + record.identity, rect(12, 6, width - 24, 24), title(record, language), { weight: 600 }),
			label("namingRuleSummary_" + record.identity, rect(12, 32, width - 24, 20), doc.file_naming || doc.script_path || doc.dir_naming || "", muted),
			label("namingRuleIdentity_" + record.identity, rect(12, 56, width - 24, 20), record.identity + " · " + (doc.checkin_type || tr("Unspecified")), muted)
		],
		action: {
			type: "select",
			identity: record.identity
		}
	})] };
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/naming/naming.state.mjs
var fields$1 = [
	"search_type",
	"dir_naming",
	"file_naming",
	"sandbox_dir_naming",
	"snapshot_type",
	"context",
	"latest_versionless",
	"current_versionless",
	"manual_version",
	"ingest_rule_code",
	"condition",
	"class_name",
	"script_path",
	"checkin_type",
	"base_dir_alias",
	"sandbox_dir_alias"
];
var flags$1 = [
	"latest_versionless",
	"current_versionless",
	"manual_version"
];
function initial() {
	return {
		editing: true,
		catalogWidth: 270,
		page: "rule",
		confirmation: "",
		pending: null,
		text: {},
		sampleVersion: null,
		error: ""
	};
}
function pending(ui) {
	return Object.keys(ui.text).length > 0;
}
function transition(ui, model, event) {
	const next = Object.assign({}, ui), commands = [], edit = policy(model).editable;
	const document = documentEvent(ui, model, event);
	if (document && [
		"save",
		"reload",
		"discard"
	].indexOf(event.type) >= 0) return document;
	switch (event.type) {
		case "keep":
			next.confirmation = "";
			next.pending = null;
			break;
		case "confirm":
			if (model.busy || !next.confirmation) break;
			if (next.pending) {
				commands.push({ type: "discard" }, next.pending);
				next.pending = null;
				next.confirmation = "";
			} else if (next.confirmation === "execute") {
				if (edit) commands.push({
					type: "evaluate",
					execute: true
				});
				next.confirmation = "";
			} else return documentEvent(ui, model, event);
			break;
		case "text":
			if (edit && !next.confirmation) next.text = Object.assign({}, next.text, { [event.field]: event.value });
			break;
		case "applied":
			next.text = {};
			break;
		case "commit":
			if (edit && pending(next)) commands.push({ type: "apply" });
			break;
		case "field":
			if (edit && !next.confirmation) commands.push({
				type: "field",
				field: event.field,
				value: event.value
			});
			break;
		case "sample":
			if (edit && !next.confirmation) commands.push({
				type: "sample",
				field: event.field,
				value: event.value
			});
			break;
		case "version":
			if (edit) next.sampleVersion = event.value;
			break;
		case "commitVersion":
			if (next.sampleVersion !== null) {
				const version = Number(next.sampleVersion);
				if (!/^\d+$/.test(next.sampleVersion) || version < 1 || version > 9999) next.error = "Version must be between 1 and 9999";
				else {
					commands.push({
						type: "sample",
						field: "version",
						value: version
					});
					next.sampleVersion = null;
					next.error = "";
				}
			}
			break;
		case "page":
			next.page = event.value;
			break;
		case "split":
			next.catalogWidth = Math.max(180, Math.min(420, Number(event.value)));
			break;
		case "back":
			if (model.identity) next.editing = false;
			break;
		case "evaluate":
			if (edit && model.sample.key && !next.confirmation) {
				if (event.execute) next.confirmation = "execute";
				else commands.push({
					type: "evaluate",
					execute: false
				});
			}
			break;
		case "items":
			if (!model.busy && !next.confirmation) commands.push({
				type: "items",
				offset: event.offset
			});
			break;
		case "select":
		case "create":
		case "duplicate":
			if (event.type === "select" && event.identity === model.identity && !model.busy && !next.confirmation) {
				next.editing = true;
				break;
			}
			if (model.busy || model.uncertain || next.confirmation || !model.canWrite && event.type !== "select") break;
			if (model.dirty) {
				next.confirmation = "navigate";
				next.pending = event;
			} else commands.push(event);
	}
	return {
		ui: next,
		commands
	};
}
function completed(ui, command) {
	if ([
		"select",
		"create",
		"duplicate"
	].indexOf(command.type) >= 0) return Object.assign({}, ui, {
		editing: true,
		text: {}
	});
	if (["reload", "discard"].indexOf(command.type) >= 0) return Object.assign({}, ui, {
		text: {},
		confirmation: "",
		pending: null
	});
	return ui;
}
//#endregion
//#region src/features/administration/NamingEditor.vue
var NamingEditor_exports = /* @__PURE__ */ __exportAll({ default: () => NamingEditor_default });
var fields = fields$1;
var flags = flags$1;
var sessionFields = [
	"rules",
	"items",
	"itemCount",
	"itemOffset",
	"identity",
	"document",
	"baseline",
	"revision",
	"uncertain",
	"error",
	"message",
	"context",
	"preview",
	"sample"
];
var _sfc_main = {
	components: { FrameView: _sfc_main$1 },
	props: {
		ticket: String,
		project: String,
		searchType: String,
		targetTitle: String,
		session: Object,
		toolbarTarget: String,
		presentationVisible: {
			type: Boolean,
			default: true
		}
	},
	emits: ["saved"],
	data() {
		const state = {
			restored: false,
			rules: [],
			items: [],
			itemCount: 0,
			itemOffset: 0,
			identity: "",
			document: null,
			baseline: "",
			revision: "",
			busy: false,
			uncertain: false,
			error: "",
			message: "",
			context: null,
			request: 0,
			preview: null,
			ui: initial(),
			viewport: {
				width: 1,
				height: 1
			},
			toolbarSize: 620,
			observer: null,
			sample: {
				key: "",
				file: "example.ma",
				version: 1,
				process: "publish",
				context: "publish",
				fileType: "main",
				snapshotType: "file"
			}
		};
		const saved = this.session?.snapshot;
		if (saved?.context?.ticket === this.ticket && saved.context.project === this.project && saved.context.searchType === this.searchType) Object.assign(state, saved, { restored: true });
		return state;
	},
	computed: {
		dirty() {
			return this.uncertain || this.document !== null && (JSON.stringify(this.document) !== this.baseline || pending(this.ui));
		},
		editable() {
			return !this.busy && !this.uncertain;
		},
		frameModel() {
			return {
				ready: !!this.document,
				canWrite: !!this.searchType,
				canLoad: !!this.ticket,
				busy: this.busy,
				dirty: this.dirty,
				uncertain: this.uncertain,
				error: this.error,
				message: this.message,
				identity: this.identity,
				document: this.document || {},
				rules: this.rules,
				items: this.items,
				itemCount: this.itemCount,
				itemOffset: this.itemOffset,
				sample: this.sample,
				previewMode: "server",
				previewResults: this.preview?.results || [],
				project: this.project,
				searchType: this.searchType,
				targetTitle: this.targetTitle || this.searchType
			};
		},
		frameScene() {
			return describe(this.frameModel, this.ui, this.viewport.width, this.viewport.height, appearance.language);
		},
		toolbarScene() {
			return toolbar(this.frameModel, this.ui, this.toolbarSize, appearance.language);
		},
		models() {
			return { namingRules: this.rules };
		}
	},
	mounted() {
		window.addEventListener("beforeunload", this.beforeUnload);
		if (!this.restored) this.reload();
		this.observer = observeFrameSizes((entries) => {
			for (const entry of entries) if (entry.target === this.$refs.body) this.viewport = {
				width: Math.max(1, entry.contentRect.width),
				height: Math.max(1, entry.contentRect.height)
			};
			else this.toolbarSize = entry.contentRect.width;
		});
		this.observer.observe(this.$refs.body);
		this.observer.observe(this.toolbarTarget ? document.querySelector(this.toolbarTarget) || this.$el : this.$el);
	},
	beforeUnmount() {
		this.applyText();
		if (this.session) this.session.snapshot = Object.fromEntries(sessionFields.map((key) => [key, this[key]]));
		this.observer?.disconnect();
		this.request++;
		window.removeEventListener("beforeunload", this.beforeUnload);
	},
	watch: {
		ticket() {
			this.contextChanged();
		},
		project() {
			this.contextChanged();
		},
		searchType() {
			this.contextChanged();
		},
		document: {
			deep: true,
			handler(value, previous) {
				this.preview = null;
				if (this.dirty && value === previous) this.message = "";
			}
		},
		sample: {
			deep: true,
			handler() {
				this.preview = null;
			}
		}
	},
	methods: {
		t,
		rowScene(node, record) {
			return row(node, record, this.frameModel, appearance.language);
		},
		applyText() {
			for (const [field, value] of Object.entries(this.ui.text)) this.document[field] = value;
			this.ui = transition(this.ui, this.frameModel, { type: "applied" }).ui;
		},
		async dispatch(event) {
			const result = transition(this.ui, this.frameModel, event);
			this.ui = result.ui;
			for (const command of result.commands) {
				if (!["reload", "discard"].includes(command.type)) this.applyText();
				switch (command.type) {
					case "apply": break;
					case "field":
						this.document[command.field] = command.value;
						break;
					case "sample":
						this.sample[command.field] = command.value;
						break;
					case "select":
						this.select(this.rules.find((row) => row.identity === command.identity), true);
						break;
					case "create":
						this.create(false, true);
						break;
					case "duplicate":
						this.create(true, true);
						break;
					case "reload":
						await this.reload(0, false, true);
						break;
					case "discard":
						this.document = this.identity ? { ...this.rules.find((row) => row.identity === this.identity)?.document } : null;
						this.baseline = JSON.stringify(this.document);
						this.preview = null;
						this.ui = {
							...this.ui,
							text: {}
						};
						if (this.uncertain) await this.reload(0, false, true);
						break;
					case "save":
						await this.save(true);
						break;
					case "evaluate":
						await this.evaluate(command.execute, true);
						break;
					case "items":
						await this.reload(command.offset, true, true);
						break;
					default: throw Error("Unsupported Naming command: " + command.type);
				}
				this.ui = completed(this.ui, command);
			}
		},
		beforeUnload(event) {
			if (this.dirty || this.busy || this.uncertain) {
				event.preventDefault();
				event.returnValue = "";
			}
		},
		canLeave() {
			return !this.busy && (!(this.dirty || this.uncertain) || window.confirm(t("Discard unsaved naming changes?")));
		},
		title(row) {
			return row.document.context || row.document.script_path || (row.document.latest_versionless || row.document.current_versionless ? t("Versionless") : t("Default"));
		},
		async call(action, values = {}) {
			return (await rpc("execute_cmd", [
				{
					ticket: this.context.ticket,
					project: this.context.project,
					language: "python"
				},
				"tactic.ui.panel.naming_cmd.NamingCmd",
				{
					action,
					project_code: this.context.project,
					search_type: this.context.searchType,
					...values
				}
			])).info;
		},
		contextChanged() {
			this.request++;
			this.busy = false;
			this.document = null;
			this.baseline = "null";
			this.identity = "";
			this.sample.key = "";
			this.uncertain = false;
			this.ui = initial();
			this.reload();
		},
		select(row, confirmed = false) {
			if (row?.identity === this.identity || !confirmed && !this.canLeave()) return;
			this.identity = row?.identity || "";
			this.document = row ? { ...row.document } : null;
			this.baseline = JSON.stringify(this.document);
			this.preview = null;
			this.error = "";
			this.message = "";
		},
		accept(result, preserve = false) {
			this.rules = result.rules;
			this.items = result.items;
			this.itemCount = result.itemCount;
			this.itemOffset = result.itemOffset;
			this.revision = result.revision;
			this.uncertain = false;
			if (!preserve) {
				const row = this.rules.find((item) => item.identity === result.identity) || this.rules[0];
				this.identity = row?.identity || "";
				this.document = row ? { ...row.document } : null;
				this.baseline = JSON.stringify(this.document);
			}
			if (!this.sample.key && this.items.length) this.sample.key = this.items[0].key;
			this.preview = null;
		},
		async reload(offset = 0, preserve = false, confirmed = false) {
			if (this.busy || !preserve && !confirmed && !this.canLeave()) return;
			const id = ++this.request;
			this.context = {
				ticket: this.ticket,
				project: this.project,
				searchType: this.searchType
			};
			this.busy = true;
			this.error = "";
			try {
				const result = await this.call("load", { object_offset: offset });
				if (id === this.request) this.accept(result, preserve);
			} catch (error) {
				if (id === this.request) this.error = error.message;
			} finally {
				if (id === this.request) this.busy = false;
			}
		},
		create(duplicate = false, confirmed = false) {
			if (!this.editable || !confirmed && !this.canLeave()) return;
			const copy = duplicate && this.document ? { ...this.document } : Object.fromEntries(fields.map((key) => [key, flags.includes(key) ? false : ""]));
			if (!duplicate) Object.assign(copy, {
				search_type: this.searchType,
				context: this.sample.context,
				checkin_type: "strict",
				dir_naming: "{project.code}/{search_type.table_name}/{sobject.code}/{snapshot.context}/versions",
				file_naming: "{sobject.name}_v{version}.{ext}"
			});
			this.identity = "";
			this.document = copy;
			this.baseline = "";
			this.preview = null;
			this.error = "";
			this.message = duplicate ? "Duplicated rule is local until Save is pressed." : "New rule is local until Save is pressed.";
		},
		async save(confirmed = false) {
			if (!this.editable || !this.dirty || !this.document) return;
			if (!confirmed && this.identity && !window.confirm(t("Update project naming rule? This changes future check-ins in the current project. Existing files are kept."))) return;
			const id = this.request;
			this.busy = true;
			this.error = "";
			try {
				const result = await this.call("save", {
					identity: this.identity,
					document: this.document,
					expected_revision: this.revision,
					object_offset: this.itemOffset
				});
				if (id === this.request) {
					this.accept(result);
					this.message = "Naming rule saved.";
					this.$emit("saved");
				}
			} catch (error) {
				if (id === this.request) {
					this.uncertain = !error.status || error.status >= 500;
					this.error = this.uncertain ? "The save result is unknown. Refresh before trying again." : error.message;
				}
			} finally {
				if (id === this.request) this.busy = false;
			}
		},
		async evaluate(allowExecution = false, confirmed = false) {
			if (!this.editable || !this.document || !this.sample.key) return;
			if (!confirmed && allowExecution && !window.confirm(t("Run custom naming code? This uses the normal server environment, not an isolated sandbox. Scripts and classes can change data or files."))) return;
			const id = this.request;
			this.busy = true;
			this.error = "";
			this.preview = null;
			try {
				const result = await this.call("preview", {
					identity: this.identity,
					document: this.document,
					sample: this.sample,
					allow_execution: allowExecution
				});
				if (id === this.request) this.preview = result;
			} catch (error) {
				if (id === this.request) this.error = error.message;
			} finally {
				if (id === this.request) this.busy = false;
			}
		}
	}
};
var _hoisted_1 = ["aria-label", "aria-busy"];
var _hoisted_2 = {
	ref: "body",
	class: "frame-host-body"
};
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_FrameView = resolveComponent("FrameView");
	return openBlock(), createElementBlock("section", {
		class: "naming-editor frame-host",
		"aria-label": $options.t("Naming editor"),
		"aria-busy": _ctx.busy
	}, [(openBlock(), createBlock(Teleport, {
		to: $props.toolbarTarget || "body",
		disabled: !$props.toolbarTarget
	}, [withDirectives(createBaseVNode("div", {
		class: "frame-toolbar-host",
		style: normalizeStyle({ width: _ctx.toolbarSize + "px" })
	}, [createVNode(_component_FrameView, {
		scene: $options.toolbarScene,
		onEvent: $options.dispatch
	}, null, 8, ["scene", "onEvent"])], 4), [[vShow, $props.presentationVisible]])], 8, ["to", "disabled"])), createBaseVNode("div", _hoisted_2, [createVNode(_component_FrameView, {
		scene: $options.frameScene,
		models: $options.models,
		"describe-row": $options.rowScene,
		onEvent: $options.dispatch
	}, null, 8, [
		"scene",
		"models",
		"describe-row",
		"onEvent"
	])], 512)], 8, _hoisted_1);
}
var NamingEditor_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { NamingEditor_exports as n, NamingEditor_default as t };

//# sourceMappingURL=NamingEditor.js.map