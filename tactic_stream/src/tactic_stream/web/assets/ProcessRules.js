import { E as nextTick, F as resolveComponent, I as resolveDirective, K as withDirectives, M as openBlock, _ as createElementBlock, b as createVNode, c as withKeys, g as createCommentVNode, h as createBlock, l as withModifiers, m as createBaseVNode, nt as normalizeStyle, rt as toDisplayString } from "./vue.js";
import { R as _plugin_vue_export_helper_default, a as _sfc_main$2, o as t, s as appearance, t as _sfc_main$1 } from "./AppButton.js";
import { k as rpc } from "./index.js";
import { B as node, L as button, R as label, V as rect, n as observeFrameSizes, r as _sfc_main$3, v as translate, z as muted } from "./resize.js";
import { n as sections } from "./sections.ui.js";
import { i as sectionSelector, n as notices, o as toolbar$1, r as policy, s as _sfc_main$4, t as documentEvent } from "./admin.document.js";
//#region ../src/tactic_stream/shared_ui/features/administration/workflow/process_rules.ui.mjs
function toolbar(model, ui, width, language) {
	const result = toolbar$1(model, ui, width, language), tr = (text) => translate(text, language);
	result.nodes = result.nodes.filter((row) => row.id !== "adminDocumentStatus");
	result.nodes.push(button("adminAddProcessRule", rect(46, 0, 38, 38), tr("Add rule"), "add", { type: "add" }, model.canWrite && !model.busy && !model.uncertain && ["trigger", "notification"].indexOf(ui.page) >= 0, { iconOnly: true }));
	return result;
}
function models(model, ui) {
	return {
		processRules: model.document.rules.map((rule, index) => ({
			identity: String(index),
			index,
			rule
		})).filter((row) => row.rule.kind === ui.page),
		processNaming: (model.metadata.naming || []).map((row, index) => Object.assign({ identity: String(index) }, row)),
		processObjects: (model.metadata.items || []).map((row) => Object.assign({ identity: row.key }, row))
	};
}
function row(list, record, model, language) {
	const tr = (text) => translate(text, language), w = list.width - 16;
	const rule = record.rule, heading = rule ? rule.title || (rule.key ? rule.event : tr("New rule")) : list.source === "processNaming" ? record.context || "" : record.label || record.key;
	const description = rule ? tr(rule.managed ? "Managed by node parameters" : rule.scope === "global" ? "All matching processes" : "This pipeline") : list.source === "processNaming" ? (record.directory || "") + " / " + (record.file || "") : record.key;
	return { nodes: [node("Action", "processRuleRow_" + list.source + "_" + record.identity, rect(0, 0, w, 78), {
		text: heading,
		enabled: !model.busy,
		selected: !!rule && model.selected === record.index,
		normalColor: "transparent",
		selectedColor: "contentSelection",
		children: [label("processRuleTitle_" + list.source + "_" + record.identity, rect(12, 4, w - 24, 28), heading, { weight: 600 }), label("processRuleDetail_" + list.source + "_" + record.identity, rect(12, 36, w - 24, 34), description, muted)],
		action: rule ? {
			type: "select",
			index: record.index
		} : list.source === "processObjects" ? {
			type: "object",
			key: record.key
		} : null
	})] };
}
function fields(model, language) {
	const tr = (text) => translate(text, language), rule = model.rule, metadata = model.metadata, fields = [];
	const text = (key, title, description, area) => ({
		id: "adminRule_" + key,
		title,
		description,
		kind: area ? "Area" : "Field",
		height: area ? 120 : 38,
		field: key,
		props: { text: rule[key] || "" }
	});
	const choices = (key, title, options, description, value) => ({
		id: "adminRule_" + key,
		title,
		description,
		kind: "Choice",
		field: key,
		options: options.map((row) => ({
			value: row.value,
			label: row.data ? row.label : tr(row.label)
		})),
		props: { value: value === void 0 ? rule[key] || "" : value }
	});
	const toggle = (key, title, description) => ({
		id: "adminRule_" + key,
		title,
		description,
		kind: "Switch",
		field: key,
		props: { checked: rule[key] === true }
	});
	fields.push(text("title", "Name", "The readable name of this rule."), text("description", "Description", "Explain why this rule is needed.", true), choices("scope", "Scope", [{
		value: "local",
		label: "This pipeline"
	}, {
		value: "global",
		label: "All matching processes"
	}], rule.scope === "global" ? "Applies to every process with this name in the project, including other pipelines." : "Applies only to this process in this pipeline."));
	const events = [
		{
			value: "change|sthpw/task|status",
			label: "Task status changed"
		},
		{
			value: "change|sthpw/task|assigned",
			label: "Task assignee changed"
		},
		{
			value: "insert|sthpw/note",
			label: "Note created"
		},
		{
			value: "change|sthpw/note",
			label: "Note created or modified"
		},
		{
			value: "checkin|" + (metadata.searchType || ""),
			label: "File checked in"
		}
	], known = events.some((row) => row.value === rule.event);
	fields.push(choices("event", "Event", events.concat([{
		value: "",
		label: "Custom event"
	}]), "The native event that starts this rule.", known ? rule.event : ""));
	if (!known) {
		const custom = text("event", "Native event identifier");
		custom.id = "adminRuleCustomEvent";
		fields.push(custom);
	}
	if (rule.event === "change|sthpw/task|status" && rule.action !== "parent_status") fields.push(choices("srcStatus", "Source status", [{
		value: "",
		label: "Any status"
	}].concat((metadata.sourceStatuses || []).map((value) => ({
		value,
		label: value,
		data: true
	}))), "Filter the source task status, or listen to any status."));
	if (rule.kind !== "notification") fields.push(choices("action", "Action", [
		{
			value: "task_status",
			label: "Change task statuses"
		},
		{
			value: "parent_status",
			label: "Change parent status"
		},
		{
			value: "task_create",
			label: "Create output tasks"
		},
		{
			value: "task_date",
			label: "Set actual task date"
		},
		{
			value: "custom_script",
			label: "Server script"
		},
		{
			value: "python_class",
			label: "Server command class"
		}
	], "Saving configures the trigger. It does not run the action."));
	if (rule.action === "task_status") {
		fields.push({
			kind: "Heading",
			id: "ruleTargetsHeading",
			title: "Destination tasks",
			description: "Each process uses its own task status workflow."
		});
		for (const process of metadata.processes || []) {
			const target = (rule.targets || []).find((row) => row.process === process.identity), status = target ? target.status : (process.statuses || [])[0] || "";
			fields.push({
				id: "adminRuleTarget_" + process.identity,
				title: process.label || process.identity,
				dataLabel: true,
				kind: "Switch",
				props: {
					checked: !!target,
					action: {
						type: "target",
						process: process.identity,
						status
					}
				}
			}, {
				id: "adminRuleTargetStatus_" + process.identity,
				title: "Destination status",
				kind: "Choice",
				options: (process.statuses || []).map((value) => ({
					value,
					label: value
				})),
				props: {
					value: status,
					enabled: policy(model).editable && !rule.managed && !!target,
					action: {
						type: "target",
						process: process.identity,
						enabled: true
					}
				}
			});
		}
	}
	if (rule.action === "task_create") {
		fields.push({
			kind: "Heading",
			id: "ruleOutputsHeading",
			title: "Output processes",
			description: "Only connected output processes are available. Add connections on the canvas first."
		});
		for (const process of metadata.outputs || []) fields.push({
			id: "adminRuleOutput_" + process,
			title: process,
			dataLabel: true,
			kind: "Switch",
			props: {
				checked: (rule.outputs || []).indexOf(process) >= 0,
				action: {
					type: "output",
					process
				}
			}
		});
	}
	if (rule.action === "task_date") fields.push(choices("column", "Actual date", [{
		value: "actual_start_date",
		label: "Start"
	}, {
		value: "actual_end_date",
		label: "End"
	}], "Choose which actual task date to set."));
	if (rule.action === "custom_script") fields.push(choices("scriptPath", "Server script", (metadata.scriptPaths || []).map((value) => ({
		value,
		label: value,
		data: true
	})), "Select an existing server script. Its source remains in the Script Editor."));
	for (const field of [
		{
			key: "targetStatus",
			title: "Destination status",
			action: "parent_status"
		},
		{
			key: "classPath",
			title: "Installed Python class",
			action: "python_class"
		},
		{
			key: "subject",
			title: "Subject",
			action: "notification"
		},
		{
			key: "mailTo",
			title: "Recipients",
			action: "notification"
		},
		{
			key: "mailCc",
			title: "Copy recipients",
			action: "notification"
		}
	]) if (rule.action === field.action) fields.push(text(field.key, field.title, "Native action parameters. TACTIC expressions are supported by notifications."));
	if (rule.kind === "notification") {
		fields.push({
			kind: "Heading",
			id: "ruleNotificationHeading",
			title: "Notification content",
			description: "TACTIC expressions are supported in recipients, subject and body. Saving does not send a notification."
		}, toggle("useTemplate", "Use the native event template on save", "The native event template replaces the subject and body when saved."));
		const body = text("body", "Body", "Notification message with optional TACTIC expressions.", true);
		body.props.enabled = policy(model).editable && !rule.managed && !rule.useTemplate;
		fields.push(body, toggle("loginTicket", "Generate a temporary login ticket", "The native notification handler may include a login ticket."), text("rules", "Additional conditions (native rules XML)", "Conditions are checked as XML before saving.", true));
	} else fields.push(choices("mode", "Execution mode", [
		{
			value: "same process,same transaction",
			label: "Same transaction"
		},
		{
			value: "separate process,blocking",
			label: "Separate process, wait"
		},
		{
			value: "separate process,non-blocking",
			label: "Separate process, background"
		},
		{
			value: "separate process,queued",
			label: "Queued"
		}
	], "Use the execution mode supported by the installed server handler."));
	return fields;
}
function describe(model, ui, width, height, language) {
	if (width <= 0 || height <= 0) return { nodes: [] };
	const tr = (text) => translate(text, language), noticeModel = Object.assign({}, model, { error: model.error || ui.error });
	if (ui.confirmation === "save") noticeModel.confirmationText = "Save process rules? Global rules affect matching processes in other pipelines. Removed rules are deleted; their scripts are kept. Actions are not executed by Save.";
	if (ui.confirmation === "remove") noticeModel.confirmationText = "The rule will be removed from the server when you save. The script itself is not deleted.";
	const notice = notices(noticeModel, ui, width, language, void 0, ui.confirmation === "remove" ? "Remove rule" : void 0), nodes = notice.nodes;
	let y = notice.top;
	nodes.push(sectionSelector("adminDependencyPages", [
		{
			value: "trigger",
			label: tr("Triggers") + " · " + model.document.rules.filter((row) => row.kind === "trigger").length
		},
		{
			value: "notification",
			label: tr("Notifications") + " · " + model.document.rules.filter((row) => row.kind === "notification").length
		},
		{
			value: "naming",
			label: tr("Naming conventions") + " · " + (model.metadata.naming || []).length
		},
		{
			value: "objects",
			label: tr("Search Objects") + " · " + (model.metadata.itemCount || 0)
		}
	], ui.page, rect(0, y, width, 38), !model.busy, "page"));
	y += 46;
	const h = Math.max(1, height - y), rulePage = ["trigger", "notification"].indexOf(ui.page) >= 0, split = width >= 800, left = split ? Math.min(ui.catalogWidth, width * .34) : width;
	if (rulePage) {
		if (split || !ui.editing) nodes.push(node("Box", "processRulesCatalogPanel", rect(0, y, left, h), {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			children: [node("List", "adminProcessRulesList", rect(12, 12, left - 24, h - 24), {
				source: "processRules",
				keyField: "identity",
				rowHeight: 82,
				scrollbarId: "adminProcessRulesScrollBar"
			})]
		}));
		if (split) nodes.push(node("Splitter", "processRulesSplit", rect(left, y, 10, h), {
			text: tr("Rule list width"),
			value: left,
			min: 180,
			max: Math.min(420, width * .34),
			action: { type: "split" }
		}));
		if (split || ui.editing) {
			const x = split ? left + 10 : 0, w = width - x, children = [];
			let top = 12;
			if (!split) {
				children.push(button("processRulesBack", rect(12, top, w - 24, 36), tr("Back"), "chevron-left", { type: "back" }, !model.busy));
				top += 44;
			}
			if (model.rule.kind) {
				if (model.rule.managed) {
					children.push(label("processManagedHelp", rect(12, top, w - 24, 100), tr("This trigger is generated by the workflow engine. Edit its action or progress listener in the node parameters, not in a second copy here."), Object.assign({ wrap: true }, muted)));
					top += 108;
				}
				const body = sections(fields(Object.assign({}, model, { busy: model.busy || !!ui.confirmation }), language), w - 40, language, policy(model).editable && !model.rule.managed && !ui.confirmation);
				body.nodes.push(button("adminRemoveProcessRule", rect(0, body.height, w - 40, 38), tr("Remove rule"), "delete", { type: "remove" }, policy(model).editable && !model.rule.managed && !ui.confirmation));
				children.push(node("Scroll", "adminRuleViewport", rect(12, top, w - 24, h - top - 12), {
					contentHeight: body.height + 46,
					resetKey: String(model.selected),
					scrollbarId: "adminRuleScrollBar",
					children: body.nodes
				}));
			} else children.push(label("processNoRule", rect(12, top, w - 24, 120), tr("No rules configured. Use Add rule to create one."), Object.assign({ wrap: true }, muted)));
			nodes.push(node("Box", "processRuleEditorPanel", rect(x, y, w, h), {
				background: "surfaceContainerLow",
				border: "outlineVariant",
				children
			}));
		}
	} else {
		const objects = ui.page === "objects", rows = objects ? model.metadata.items || [] : model.metadata.naming || [], offset = model.metadata.itemOffset || 0, count = model.metadata.itemCount || 0;
		nodes.push(label("processRelatedHelp", rect(12, y, width - 24, 84), tr(objects ? "This count is for the pipeline, not the number of tasks in this process." : "Rules whose context starts with this process. Edit naming in the Search Type's existing Naming Editor."), Object.assign({ wrap: true }, muted)), node("List", "adminRelatedObjects", rect(12, y + 92, width - 24, h - (objects ? 146 : 104)), {
			source: objects ? "processObjects" : "processNaming",
			keyField: "identity",
			rowHeight: 82,
			scrollbarId: "adminRelatedObjectsScrollBar"
		}));
		if (!rows.length) nodes.push(label("processRelatedEmpty", rect(24, y + 100, width - 48, 80), tr(objects ? "No Search Objects" : "No naming conventions for this process."), Object.assign({ wrap: true }, muted)));
		if (objects) nodes.push(button("adminObjectsPrevious", rect(12, height - 42, 100, 36), tr("Previous"), "chevron-left", {
			type: "items",
			offset: offset - 50
		}, !model.busy && !model.dirty && offset > 0), label("processObjectsPage", rect(120, height - 42, width - 240, 36), String(offset + (rows.length ? 1 : 0)) + "–" + (offset + rows.length) + " / " + count, { align: "center" }), button("adminObjectsNext", rect(width - 112, height - 42, 100, 36), tr("Next"), "chevron-right", {
			type: "items",
			offset: offset + 50
		}, !model.busy && !model.dirty && offset + rows.length < count));
	}
	return { nodes };
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/workflow/process_rules.state.mjs
function initial() {
	return {
		page: "trigger",
		editing: false,
		catalogWidth: 250,
		confirmation: "",
		error: ""
	};
}
function transition(ui, model, event) {
	const next = Object.assign({}, ui), commands = [], edit = policy(model).editable && !model.rule.managed;
	if (event.type === "confirm" && ui.confirmation === "remove") {
		if (edit) commands.push({ type: "remove" });
		next.confirmation = "";
		return {
			ui: next,
			commands
		};
	}
	if (event.type === "confirm" && ui.confirmation === "close") {
		if (!model.busy) commands.push({ type: "discard" }, { type: "close" });
		next.confirmation = "";
		return {
			ui: next,
			commands
		};
	}
	const document = documentEvent(ui, model, event);
	if (document) return document;
	if (model.busy || ui.confirmation) return {
		ui: next,
		commands
	};
	switch (event.type) {
		case "page":
			next.page = event.value;
			next.editing = false;
			commands.push({
				type: "select",
				index: model.document.rules.findIndex((row) => row.kind === event.value)
			});
			break;
		case "select":
			next.editing = true;
			commands.push(event);
			break;
		case "back":
			next.editing = false;
			break;
		case "split":
			next.catalogWidth = Math.max(180, Math.min(420, Number(event.value)));
			break;
		case "add":
			if (model.canWrite && !model.uncertain && ["trigger", "notification"].indexOf(next.page) >= 0) {
				commands.push({
					type: "add",
					kind: next.page
				});
				next.editing = true;
			}
			break;
		case "field":
			if (edit && ownField(model.rule, event.field)) commands.push(event);
			break;
		case "target":
			if (edit) commands.push(event);
			break;
		case "output":
			if (edit) commands.push(event);
			break;
		case "remove":
			if (edit && model.rule.kind) next.confirmation = "remove";
			break;
		case "items":
			if (!model.dirty) commands.push(event);
			break;
		case "object":
			if ((model.metadata.items || []).some((row) => row.key === event.key)) commands.push(event);
			break;
		case "close": if (model.dirty || model.uncertain) next.confirmation = "close";
		else commands.push(event);
	}
	return {
		ui: next,
		commands
	};
}
function ownField(rule, key) {
	return Object.prototype.hasOwnProperty.call(rule, key) && [
		"key",
		"kind",
		"managed",
		"targets",
		"outputs"
	].indexOf(key) < 0;
}
//#endregion
//#region src/features/administration/ProcessRules.vue
var _sfc_main = {
	components: {
		ObjectReport: _sfc_main$4,
		FrameView: _sfc_main$3,
		AppButton: _sfc_main$1,
		AppIcon: _sfc_main$2
	},
	props: {
		ticket: String,
		project: String
	},
	emits: ["saved"],
	data() {
		return {
			ui: initial(),
			viewport: {
				width: 1,
				height: 1
			},
			toolbarSize: 620,
			observer: null,
			active: false,
			context: null,
			identity: "",
			revision: "",
			metadata: {},
			document: { rules: [] },
			baseline: "",
			selected: -1,
			busy: false,
			error: "",
			uncertain: false,
			request: 0,
			canWrite: false,
			page: "trigger",
			object: null
		};
	},
	computed: {
		dirty() {
			return JSON.stringify(this.document) !== this.baseline;
		},
		rule() {
			return this.document.rules[this.selected];
		},
		editable() {
			return this.canWrite && !this.busy && !this.uncertain && !this.rule?.managed;
		},
		frameModel() {
			return {
				ready: Array.isArray(this.document.rules),
				canWrite: this.canWrite,
				canLoad: !!this.identity,
				busy: this.busy,
				dirty: this.dirty,
				uncertain: this.uncertain,
				error: this.error,
				message: "",
				identity: this.identity,
				document: this.document,
				metadata: this.metadata,
				selected: this.selected,
				rule: this.rule || {}
			};
		},
		frameScene() {
			return describe(this.frameModel, this.ui, this.viewport.width, this.viewport.height, appearance.language);
		},
		toolbarScene() {
			return toolbar(this.frameModel, this.ui, this.toolbarSize, appearance.language);
		},
		models() {
			return models(this.frameModel, this.ui);
		}
	},
	mounted() {
		window.addEventListener("beforeunload", this.beforeUnload);
		this.observer = observeFrameSizes((entries) => {
			for (const entry of entries) if (entry.target === this.$refs.body) this.viewport = {
				width: Math.max(1, entry.contentRect.width),
				height: Math.max(1, entry.contentRect.height)
			};
			else this.toolbarSize = entry.contentRect.width;
		});
		this.observer.observe(this.$refs.body);
		this.observer.observe(this.$refs.frameRoot);
	},
	beforeUnmount() {
		this.observer?.disconnect();
		this.request++;
		window.removeEventListener("beforeunload", this.beforeUnload);
	},
	watch: {
		ticket() {
			this.request++;
			this.active = false;
			this.$refs.dialog?.close();
		},
		project() {
			this.request++;
			this.active = false;
			this.$refs.dialog?.close();
		}
	},
	methods: {
		t,
		rowScene(list, record) {
			return row(list, record, this.frameModel, appearance.language);
		},
		async dispatch(event) {
			const result = transition(this.ui, this.frameModel, event);
			this.ui = result.ui;
			for (const command of result.commands) switch (command.type) {
				case "select":
					this.page = this.ui.page;
					this.selected = command.index;
					break;
				case "add":
					this.page = command.kind;
					this.add();
					break;
				case "field":
					this.rule[command.field] = command.value;
					if (command.field === "event" && command.value !== "change|sthpw/task|status") this.rule.srcStatus = "";
					break;
				case "target":
					this.setTarget(command.process, command.enabled === true ? String(command.value) : command.status, command.enabled === true || command.value === true);
					break;
				case "output":
					this.setOutput(command.process, command.value);
					break;
				case "remove":
					this.remove(true);
					break;
				case "items":
					await this.load(command.offset);
					break;
				case "object":
					await this.inspect(command.key);
					break;
				case "save":
					await this.save(true);
					break;
				case "reload":
					await this.load();
					break;
				case "discard":
					this.document = JSON.parse(this.baseline);
					this.selected = this.document.rules.findIndex((rule) => rule.kind === this.ui.page);
					this.error = "";
					break;
				case "close":
					this.close(true);
					break;
				default: throw Error("Unsupported process dependencies command: " + command.type);
			}
		},
		beforeUnload(event) {
			if (this.active && (this.dirty || this.busy || this.uncertain)) {
				event.preventDefault();
				event.returnValue = "";
			}
		},
		accept(result) {
			this.identity = result.identity;
			this.document = result.document;
			this.metadata = result.metadata;
			this.revision = result.revision;
			this.canWrite = result.canWrite;
			this.baseline = JSON.stringify(this.document);
			this.selected = this.document.rules.findIndex((rule) => rule.kind === this.page);
			this.uncertain = false;
		},
		async call(action, values = {}) {
			return (await rpc("execute_cmd", [
				{
					ticket: this.context.ticket,
					project: this.context.project,
					language: "python"
				},
				"tactic.ui.panel.process_rules_cmd.ProcessRulesCmd",
				{
					action,
					project_code: this.context.project,
					identity: this.identity,
					...values
				}
			])).info;
		},
		windowContext() {
			if (this.busy || this.uncertain || this.dirty) throw Error("Apply or discard unsaved changes first");
			return {
				project: this.project,
				route: { args: [this.identity] }
			};
		},
		async open(identity) {
			this.context = {
				ticket: this.ticket,
				project: this.project
			};
			this.identity = identity;
			this.active = true;
			this.page = "trigger";
			this.ui = initial();
			await nextTick();
			this.$refs.dialog.showModal();
			await this.load();
		},
		async load(offset = this.metadata.itemOffset || 0) {
			const id = ++this.request;
			this.busy = true;
			this.error = "";
			try {
				const result = await this.call("load", { item_offset: offset });
				if (id === this.request) this.accept(result);
			} catch (error) {
				if (id === this.request) this.error = error.message;
			} finally {
				if (id === this.request) this.busy = false;
			}
		},
		close(confirmed = false) {
			if (this.busy || !confirmed && (this.dirty || this.uncertain) && !window.confirm(t("Discard unsaved changes?"))) return;
			this.request++;
			this.active = false;
			this.$refs.dialog.close();
		},
		reload() {
			if (!this.busy && (!(this.dirty || this.uncertain) || window.confirm(t("Discard unsaved changes?")))) this.load();
		},
		selectPage(page) {
			this.page = page;
			this.selected = this.document.rules.findIndex((rule) => rule.kind === page);
		},
		add() {
			if (!this.canWrite || this.busy || this.uncertain) return;
			const kind = this.page === "notification" ? "notification" : "trigger";
			this.document.rules.push({
				key: "",
				kind,
				title: "",
				description: "",
				event: "change|sthpw/task|status",
				scope: "local",
				action: kind === "notification" ? "notification" : "task_status",
				managed: false,
				srcStatus: "",
				targets: [],
				outputs: [],
				column: "",
				targetStatus: "",
				scriptPath: "",
				classPath: "",
				subject: "",
				body: "",
				mailTo: "",
				mailCc: "",
				loginTicket: false,
				useTemplate: false,
				mode: "same process,same transaction",
				rules: ""
			});
			this.selected = this.document.rules.length - 1;
			this.page = kind;
		},
		remove(confirmed = false) {
			if (this.editable && this.rule && (confirmed || window.confirm(t("Remove this rule from the draft?")))) {
				this.document.rules.splice(this.selected, 1);
				this.selected = this.document.rules.findIndex((rule) => rule.kind === this.page);
			}
		},
		setTarget(process, status, enabled) {
			this.rule.targets = this.rule.targets.filter((row) => row.process !== process);
			if (enabled) this.rule.targets.push({
				process,
				status
			});
		},
		setOutput(process, enabled) {
			this.rule.outputs = this.rule.outputs.filter((name) => name !== process);
			if (enabled) this.rule.outputs.push(process);
		},
		async save(confirmed = false) {
			if (!this.canWrite || this.busy || this.uncertain || !this.dirty) return;
			if (!confirmed && !window.confirm(t("Save process rules? Global rules affect matching processes in other pipelines. Removed rules are deleted; their scripts are kept. Actions are not executed by Save."))) return;
			const id = this.request;
			this.busy = true;
			this.error = "";
			try {
				const result = await this.call("save", {
					document: this.document,
					expected_revision: this.revision
				});
				if (id === this.request) {
					this.accept(result);
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
		async inspect(key) {
			const id = this.request;
			try {
				const result = await rpc("get_by_search_key", [{
					ticket: this.context.ticket,
					project: this.context.project,
					language: "python"
				}, key]);
				if (id !== this.request || !this.active) return;
				this.object = result;
				await nextTick();
				this.$refs.object.show();
			} catch (error) {
				if (id === this.request) this.error = error.message;
			}
		}
	}
};
var _hoisted_1 = ["aria-label", "aria-busy"];
var _hoisted_2 = { class: "configuration-header" };
var _hoisted_3 = { class: "configuration-heading" };
var _hoisted_4 = { class: "muted" };
var _hoisted_5 = {
	ref: "frameRoot",
	class: "frame-host process-dependencies-body"
};
var _hoisted_6 = {
	ref: "body",
	class: "frame-host-body"
};
var _hoisted_7 = ["aria-label"];
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_AppButton = resolveComponent("AppButton");
	const _component_FrameView = resolveComponent("FrameView");
	const _component_ObjectReport = resolveComponent("ObjectReport");
	const _directive_window = resolveDirective("window");
	return withDirectives((openBlock(), createElementBlock("dialog", {
		ref: "dialog",
		class: "configuration-dialog process-rules-editor frame-process-dialog",
		"aria-label": $options.t("Process dependencies"),
		"aria-busy": $data.busy,
		onCancel: _cache[2] || (_cache[2] = withModifiers(($event) => $options.dispatch({ type: "close" }), ["prevent", "stop"])),
		onKeydown: _cache[3] || (_cache[3] = withKeys(withModifiers(() => {}, ["stop"]), ["esc"]))
	}, [
		createBaseVNode("header", _hoisted_2, [createBaseVNode("div", _hoisted_3, [createBaseVNode("h1", null, toDisplayString($options.t("Process dependencies")), 1), createBaseVNode("p", _hoisted_4, toDisplayString($data.metadata.process) + " · " + toDisplayString($data.metadata.pipeline), 1)]), createVNode(_component_AppButton, {
			label: "Close process dependencies",
			icon: "close",
			"icon-only": "",
			onClick: _cache[0] || (_cache[0] = ($event) => $options.dispatch({ type: "close" }))
		})]),
		createBaseVNode("section", _hoisted_5, [createBaseVNode("div", {
			class: "frame-toolbar-host",
			style: normalizeStyle({ width: $data.toolbarSize + "px" })
		}, [createVNode(_component_FrameView, {
			scene: $options.toolbarScene,
			onEvent: $options.dispatch
		}, null, 8, ["scene", "onEvent"])], 4), createBaseVNode("div", _hoisted_6, [createVNode(_component_FrameView, {
			scene: $options.frameScene,
			models: $options.models,
			"describe-row": $options.rowScene,
			onEvent: $options.dispatch
		}, null, 8, [
			"scene",
			"models",
			"describe-row",
			"onEvent"
		])], 512)], 512),
		withDirectives((openBlock(), createElementBlock("dialog", {
			ref: "object",
			class: "record-dialog process-object-details",
			"aria-label": $options.t("Object details")
		}, [createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString($data.object?.name || $data.object?.title || $data.object?.code || $data.object?.id || $options.t("Object details")), 1), createVNode(_component_AppButton, {
			icon: "close",
			"icon-only": "",
			label: "Close",
			onClick: _cache[1] || (_cache[1] = ($event) => _ctx.$refs.object.close())
		})]), $data.object ? (openBlock(), createBlock(_component_ObjectReport, {
			key: 0,
			ticket: $props.ticket,
			project: $props.project,
			record: $data.object
		}, null, 8, [
			"ticket",
			"project",
			"record"
		])) : createCommentVNode("", true)], 8, _hoisted_7)), [[_directive_window, { type: "window" }]])
	], 40, _hoisted_1)), [[_directive_window, {
		kind: "process_dependencies",
		page: $options.windowContext
	}]]);
}
var ProcessRules_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render], ["__scopeId", "data-v-a3045eda"]]);
//#endregion
export { ProcessRules_default as default };

//# sourceMappingURL=ProcessRules.js.map