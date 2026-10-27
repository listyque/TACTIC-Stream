import { B as useId, D as nextTick, I as resolveComponent, L as resolveDirective, N as openBlock, _ as createElementBlock, b as createVNode, c as withKeys, f as Teleport, g as createCommentVNode, h as createBlock, it as toDisplayString, l as withModifiers, m as createBaseVNode, q as withDirectives, rt as normalizeStyle, s as vShow, u as Fragment } from "./vue.js";
import { A as t, c as _sfc_main$2, f as _sfc_main$3, j as appearance, ot as _plugin_vue_export_helper_default } from "./index.js";
import { Jt as node, Kt as label, Yt as rect, ct as rpc, i as _sfc_main$4, r as observeFrameSizes, y as translate } from "./CodeBlock.js";
import "./App.js";
import SearchTypes_default from "./SearchTypes.js";
import { n as pending, t as graphFrame_default } from "./graphFrame.js";
//#region ../src/tactic_stream/shared_ui/features/administration/schema/schema_delete.ui.mjs
function allowed(model) {
	return model.canWrite && (!model.metadata || !model.metadata.schemaRevision || model.metadata.schemaRevision === model.schemaRevision);
}
function transition(model, event) {
	if (event.type === "close") return !model.deleting ? [{ type: "close" }] : [];
	if (event.type === "reload") return !model.busy && !model.uncertain ? [{ type: "reload" }] : [];
	if (event.type === "confirmation") return allowed(model) && !model.busy && !model.uncertain ? [{
		type: "confirmation",
		value: event.value
	}] : [];
	if (event.type === "delete") return allowed(model) && !model.busy && !model.uncertain && model.confirmation === model.identity ? [{ type: "delete" }] : [];
	return [];
}
function describe(model, width, height, language) {
	if (width <= 0 || height <= 0) return { nodes: [] };
	if (model.metadata && model.metadata.schemaRevision && model.metadata.schemaRevision !== model.schemaRevision) model = Object.assign({}, model, {
		canWrite: false,
		error: "Schema changed on the server. Reload before deleting a Search Type."
	});
	const tr = (text) => translate(text, language), nodes = [], children = [], w = width - 16, details = model.metadata || {};
	let y = 0;
	function message(id, text, error) {
		const h = Math.max(72, Math.ceil(String(text).length * 7 / Math.max(80, w)) * 16 + 16);
		children.push(node("Area", id, rect(0, y, w, h), {
			label: tr(error ? "Server error" : "Status"),
			text,
			readOnly: true,
			notice: true,
			color: error ? "error" : "secondaryText"
		}));
		y += h + 8;
	}
	if (model.error || model.busy || model.uncertain) message("adminDeleteSearchTypeStatus", tr(model.uncertain ? "The deletion result is unknown. Close this review and reload the schema before trying again." : model.error || (model.deleting ? "Deleting Search Type…" : "Checking objects and dependencies…")), !!model.error || model.uncertain);
	if (details.table) {
		const summary = [
			details.title || model.identity,
			model.identity,
			tr("Project") + ": " + (details.project || ""),
			tr("Table") + ": " + details.table,
			tr("Objects (including retired)") + ": " + (details.objects || 0),
			tr("Pipelines") + ": " + ((details.pipelines || []).join(", ") || "0")
		].join("\n");
		children.push(node("Area", "adminDeleteSearchTypeSummary", rect(0, y, w, 156), {
			label: tr("Search Type"),
			text: summary,
			readOnly: true,
			notice: true
		}));
		y += 164;
		if (!model.canWrite && !model.error && !model.uncertain) {
			message("adminDeleteSearchTypeBlocked", tr("This Search Type is in use. Remove its objects and dependencies before deleting it."), true);
			const blocks = [];
			for (const part of [
				["aliases", "Other registrations for this table"],
				["usedPipelines", "Pipelines with processes"],
				["otherSchemas", "Other schemas using this type"]
			]) if ((details[part[0]] || []).length) blocks.push(tr(part[1]) + ": " + details[part[0]].join(", "));
			for (const reference of details.references || []) blocks.push(reference.type + ": " + reference.count);
			if (blocks.length) message("adminDeleteSearchTypeBlocks", blocks.join("\n"), true);
		}
		if (model.canWrite) {
			message("adminDeleteSearchTypeWarning", tr("This deletes the empty table, empty pipelines and the node with its connections in this project. This editor cannot undo the deletion. Check scripts, naming rules and saved searches that refer to this type."), false);
			if (details.sharedRegistration) message("adminDeleteSharedRegistration", tr("The shared Search Type registration is retained for other projects."), false);
			children.push(label("adminDeleteSearchTypeLabel", rect(0, y, w, 44), tr("Enter the Search Type identifier to confirm") + "\n" + model.identity, { wrap: true }), node("Field", "adminDeleteSearchTypeName", rect(0, y + 52, w, 38), {
				text: model.confirmation,
				label: tr("Search Type identifier"),
				enabled: !model.busy && !model.uncertain,
				action: { type: "confirmation" }
			}));
			y += 98;
		}
	}
	nodes.push(node("Scroll", "adminDeleteSearchTypeViewport", rect(0, 0, width, Math.max(1, height - 96)), {
		contentHeight: y,
		scrollbarId: "adminDeleteSearchTypeScrollBar",
		children
	}));
	const narrow = width < 520;
	nodes.push(node("Button", "adminDeleteSearchTypeCancel", rect(0, height - 84, narrow ? (width - 8) / 2 : 110, 36), {
		text: tr("Cancel"),
		enabled: !model.deleting,
		action: { type: "close" }
	}));
	if (!model.uncertain) nodes.push(node("Button", "adminDeleteSearchTypeReview", rect(narrow ? (width + 8) / 2 : 118, height - 84, narrow ? (width - 8) / 2 : 150, 36), {
		text: tr("Review again"),
		icon: "refresh",
		enabled: !model.busy,
		action: { type: "reload" }
	}));
	nodes.push(node("Button", "adminDeleteSearchTypeApply", rect(0, height - 40, width, 38), {
		text: tr("Delete from project"),
		icon: "delete",
		destructive: true,
		enabled: model.canWrite && !model.busy && !model.uncertain && model.confirmation === model.identity,
		action: { type: "delete" }
	}));
	return { nodes };
}
//#endregion
//#region src/features/administration/SchemaTypeDeletion.vue
var _sfc_main$1 = {
	components: {
		AppButton: _sfc_main$2,
		FrameView: _sfc_main$4
	},
	props: {
		ticket: String,
		project: String
	},
	emits: [
		"deleted",
		"uncertain",
		"active"
	],
	data() {
		return {
			viewport: {
				width: 1,
				height: 1
			},
			observer: null,
			active: false,
			context: null,
			identity: "",
			schemaRevision: "",
			revision: "",
			metadata: null,
			confirmation: "",
			canWrite: false,
			busy: false,
			deleting: false,
			uncertain: false,
			error: "",
			request: 0
		};
	},
	computed: {
		frameModel() {
			return {
				identity: this.identity,
				schemaRevision: this.schemaRevision,
				metadata: this.metadata,
				canWrite: this.canWrite,
				busy: this.busy,
				deleting: this.deleting,
				uncertain: this.uncertain,
				error: this.error,
				confirmation: this.confirmation
			};
		},
		frameScene() {
			return describe(this.frameModel, this.viewport.width, this.viewport.height, appearance.language);
		},
		enabled() {
			return this.canWrite && !this.busy && !this.uncertain && this.confirmation === this.identity;
		}
	},
	mounted() {
		this.observer = observeFrameSizes((entries) => {
			for (const entry of entries) this.viewport = {
				width: Math.max(1, entry.contentRect.width),
				height: Math.max(1, entry.contentRect.height)
			};
		});
		this.observer.observe(this.$refs.body);
	},
	beforeUnmount() {
		this.observer?.disconnect();
		this.request++;
	},
	watch: {
		ticket() {
			this.reset();
		},
		project() {
			this.reset();
		}
	},
	methods: {
		t,
		async dispatch(event) {
			for (const command of transition(this.frameModel, event)) if (command.type === "confirmation") this.confirmation = command.value;
			else if (command.type === "delete") await this.remove();
			else if (command.type === "reload") await this.load();
			else if (command.type === "close") this.close();
		},
		reset() {
			this.request++;
			this.active = false;
			this.$refs.dialog?.close();
			this.$emit("active", false);
		},
		async call(action, values = {}) {
			return (await rpc("execute_cmd", [
				{
					ticket: this.context.ticket,
					project: this.context.project,
					language: "python"
				},
				"tactic.ui.panel.schema_delete_cmd.SchemaDeleteCmd",
				{
					action,
					project_code: this.context.project,
					identity: this.identity,
					...values
				}
			])).info;
		},
		async open(identity, schemaRevision) {
			this.context = {
				ticket: this.ticket,
				project: this.project
			};
			this.identity = identity;
			this.schemaRevision = schemaRevision;
			this.metadata = null;
			this.confirmation = "";
			this.uncertain = false;
			this.active = true;
			this.$emit("active", true);
			await nextTick();
			this.$refs.dialog.showModal();
			this.$refs.frame.focusControl("adminDeleteSearchTypeCancel");
			await this.load();
		},
		async load() {
			const id = ++this.request;
			this.busy = true;
			this.error = "";
			this.canWrite = false;
			this.confirmation = "";
			try {
				const result = await this.call("load");
				if (id !== this.request) return;
				this.metadata = result.metadata;
				this.revision = result.revision;
				if (this.metadata.schemaRevision !== this.schemaRevision) throw Error("Schema changed on the server. Reload before deleting a Search Type.");
				this.canWrite = result.canWrite;
			} catch (error) {
				if (id === this.request) this.error = error.message;
			} finally {
				if (id === this.request) this.busy = false;
			}
		},
		close() {
			if (!this.deleting) this.reset();
		},
		async remove() {
			if (!this.enabled) return;
			const id = this.request;
			this.busy = this.deleting = true;
			this.error = "";
			try {
				const result = await this.call("save", {
					document: { confirmation: this.confirmation },
					expected_revision: this.revision
				});
				if (id === this.request) {
					this.$emit("deleted", result);
					this.reset();
				}
			} catch (error) {
				if (id === this.request) {
					this.canWrite = false;
					this.uncertain = !error.status || error.status >= 500;
					this.error = this.uncertain ? "The deletion result is unknown. Close this review and reload the schema before trying again." : error.message;
					if (this.uncertain) this.$emit("uncertain");
				}
			} finally {
				if (id === this.request || !this.active) this.busy = this.deleting = false;
			}
		}
	}
};
var _hoisted_1$1 = ["aria-label"];
var _hoisted_2$1 = { class: "configuration-header" };
var _hoisted_3$1 = {
	ref: "body",
	class: "frame-host-body"
};
function _sfc_render$1(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_FrameView = resolveComponent("FrameView");
	const _directive_window = resolveDirective("window");
	return withDirectives((openBlock(), createElementBlock("dialog", {
		ref: "dialog",
		class: "record-dialog schema-deletion-dialog frame-schema-delete",
		"aria-label": $options.t("Delete Search Type from project"),
		onCancel: _cache[0] || (_cache[0] = withModifiers(($event) => $options.dispatch({ type: "close" }), ["prevent", "stop"])),
		onKeydown: _cache[1] || (_cache[1] = withKeys(withModifiers(() => {}, ["stop"]), ["esc"]))
	}, [createBaseVNode("header", _hoisted_2$1, [createBaseVNode("h1", null, toDisplayString($options.t("Delete Search Type from project")), 1)]), createBaseVNode("div", _hoisted_3$1, [createVNode(_component_FrameView, {
		ref: "frame",
		scene: $options.frameScene,
		onEvent: $options.dispatch
	}, null, 8, ["scene", "onEvent"])], 512)], 40, _hoisted_1$1)), [[_directive_window]]);
}
var SchemaTypeDeletion_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main$1, [["render", _sfc_render$1], ["__scopeId", "data-v-848c9a0d"]]);
//#endregion
//#region src/features/administration/SchemaEditor.vue
function schemaXml(text) {
	if (/<!DOCTYPE|<!ENTITY/i.test(text)) throw Error("Document types and XML entities are not supported");
	const xml = new DOMParser().parseFromString(text, "application/xml");
	if (xml.querySelector("parsererror") || xml.documentElement.tagName !== "schema") throw Error("The document must have a schema root");
	const names = /* @__PURE__ */ new Set();
	for (const node of [...xml.documentElement.children].filter((node) => node.tagName === "search_type")) {
		const name = node.getAttribute("name")?.trim();
		if (!name || names.has(name)) throw Error("Schema nodes must have unique Search Type identities");
		names.add(name);
		if (["xpos", "ypos"].some((key) => !Number.isFinite(Number(node.getAttribute(key) || 0)))) throw Error("Node positions must be finite");
	}
	for (const edge of [...xml.documentElement.children].filter((node) => node.tagName === "connect")) if (!edge.getAttribute("from") || !edge.getAttribute("to")) throw Error("Every relationship needs a source and a target");
	return xml;
}
var attributes = (node) => Object.fromEntries([...node.attributes].map((attr) => [attr.name, attr.value]));
var edgeKey = (edge) => Object.fromEntries([
	"from",
	"to",
	"path"
].map((key) => [key, edge[key] || ""]));
function schemaText(text) {
	const xml = schemaXml(text);
	function indent(node, depth) {
		if (![...node.childNodes].some((child) => child.nodeType === 1) || [...node.childNodes].some((child) => [3, 4].includes(child.nodeType) && child.textContent.trim())) return;
		for (const child of [...node.childNodes]) if (child.nodeType === 3 && !child.textContent.trim()) child.remove();
		for (const child of [...node.childNodes]) {
			if (child.nodeType === 1) indent(child, depth + 1);
			node.insertBefore(xml.createTextNode("\n" + "  ".repeat(depth + 1)), child);
		}
		node.append(xml.createTextNode("\n" + "  ".repeat(depth)));
	}
	indent(xml.documentElement, 0);
	return new XMLSerializer().serializeToString(xml);
}
var _sfc_main = {
	mixins: [graphFrame_default],
	setup() {
		return { uid: useId() };
	},
	components: {
		FrameView: _sfc_main$4,
		AppButton: _sfc_main$2,
		AppIcon: _sfc_main$3,
		SearchTypes: SearchTypes_default,
		SchemaTypeDeletion: SchemaTypeDeletion_default
	},
	props: {
		ticket: String,
		project: String,
		toolbarTarget: String,
		presentationVisible: {
			type: Boolean,
			default: true
		},
		queuePreview: Function,
		checkins: Array
	},
	emits: [
		"saved",
		"open-commit-queue",
		"node-workflows",
		"type-workflow"
	],
	data() {
		return {
			frameMode: "schema",
			context: null,
			request: 0,
			busy: false,
			error: "",
			uncertain: false,
			document: null,
			identity: "",
			revision: "",
			baseline: "",
			metadata: {},
			canWrite: false,
			selected: [],
			primaryNode: "",
			selectedEdge: -1,
			propertiesWidth: 340,
			propertiesCollapsed: false,
			inspectorPage: "selection",
			page: "canvas",
			typeToAdd: "",
			typeQuery: "",
			source: "",
			target: "",
			xmlDraft: "",
			xmlPending: false,
			attributesDraft: "",
			attributesPending: false,
			columnCatalog: {},
			columnsBusy: false,
			columnsError: "",
			columnRequest: 0,
			creating: false,
			creationPosition: null,
			deletionActive: false
		};
	},
	computed: {
		dirty() {
			return !!this.document && (JSON.stringify(this.document) !== this.baseline || this.xmlPending || this.attributesPending || pending(this.ui));
		},
		editable() {
			return this.canWrite && !this.busy && !this.uncertain && !this.creating && !this.deletionActive;
		},
		xml() {
			try {
				return this.document && schemaXml(this.document.xml);
			} catch {
				return null;
			}
		},
		nodes() {
			if (!this.xml) return [];
			const types = Object.fromEntries((this.metadata.searchTypes || []).map((row) => [row.identity, row]));
			const nodes = [...this.xml.documentElement.children].filter((node) => node.tagName === "search_type").map((node, index) => {
				const identity = node.getAttribute("name"), type = types[identity] || {};
				return {
					identity,
					attributes: attributes(node),
					label: type.label || node.getAttribute("label") || identity,
					nodeX: Number(node.getAttribute("xpos") ?? 40 + index % 3 * 240),
					nodeY: Number(node.getAttribute("ypos") ?? 40 + Math.floor(index / 3) * 130),
					color: node.getAttribute("color") || type.color,
					kind: node.getAttribute("type") || "search_type",
					referenceOnly: false
				};
			});
			const coincident = nodes.length > 1 && new Set(nodes.map((node) => JSON.stringify([node.nodeX, node.nodeY]))).size === 1;
			const unset = nodes.filter((node) => node.nodeX === 0 && node.nodeY === 0).length > 1;
			if (coincident || unset) nodes.forEach((node, index) => {
				if (coincident || node.nodeX === 0 && node.nodeY === 0) {
					node.nodeX = 40 + index % 3 * 240;
					node.nodeY = 40 + Math.floor(index / 3) * 130;
				}
			});
			const known = new Set(nodes.map((node) => node.identity));
			for (const edge of this.edges) for (const identity of [edge.from, edge.to]) if (!known.has(identity)) {
				const index = nodes.length;
				nodes.push({
					identity,
					label: types[identity]?.label || identity,
					attributes: { name: identity },
					kind: "reference",
					referenceOnly: true,
					nodeX: 40 + index % 3 * 240,
					nodeY: 40 + Math.floor(index / 3) * 130
				});
				known.add(identity);
			}
			return nodes;
		},
		edges() {
			return this.xml ? [...this.xml.documentElement.children].filter((node) => node.tagName === "connect").map((node, edgeIndex) => ({
				...attributes(node),
				attributes: attributes(node),
				edgeIndex,
				label: node.getAttribute("relationship") || "code"
			})) : [];
		},
		graph() {
			return {
				center: this.identity,
				nodes: this.nodes,
				edges: this.edges
			};
		},
		node() {
			return this.nodes.find((node) => node.identity === (this.selected.includes(this.primaryNode) ? this.primaryNode : this.selected[0]));
		},
		edge() {
			return this.edges[this.selectedEdge];
		},
		connection() {
			if (!this.edge) return null;
			const table = this.metadata.searchTypes?.find((row) => row.identity === this.edge.to)?.table || this.edge.to.split("/").pop();
			const key = this.edge.relationship || "code";
			return {
				...this.edge,
				from_col: this.edge.from_col || table + "_" + key,
				to_col: this.edge.to_col || key
			};
		},
		instance() {
			return [this.node?.identity, this.edge?.from].find((name) => name && this.document?.newTypes?.[name]) || "";
		},
		instanceLinks() {
			return this.edges.filter((edge) => edge.from === this.instance);
		},
		createColumns() {
			return !!this.edge && (this.document.createColumns || []).some((row) => JSON.stringify(row) === JSON.stringify(edgeKey(this.edge)));
		},
		options() {
			return this.nodes.filter((node) => !node.referenceOnly).map((node) => ({
				value: node.identity,
				label: node.label
			}));
		},
		typeOptions() {
			return (this.metadata.searchTypes || []).filter((type) => !this.nodes.some((node) => node.identity === type.identity && !node.referenceOnly)).map((type) => ({
				value: type.identity,
				label: type.label
			}));
		},
		availableTypes() {
			const query = this.typeQuery.trim().toLocaleLowerCase();
			return (this.metadata.searchTypes || []).filter((type) => `${type.label} ${type.identity}`.toLocaleLowerCase().includes(query));
		},
		typeOnCanvas() {
			return this.nodes.some((node) => node.identity === this.typeToAdd && !node.referenceOnly);
		}
	},
	created() {
		this.load();
	},
	mounted() {
		window.addEventListener("beforeunload", this.beforeUnload);
	},
	beforeUnmount() {
		this.request++;
		this.columnRequest++;
		window.removeEventListener("beforeunload", this.beforeUnload);
	},
	watch: {
		project() {
			this.load();
		},
		ticket() {
			this.load();
		},
		selectedEdge() {
			this.loadColumns();
		},
		node: {
			deep: true,
			handler(value) {
				if (!this.attributesPending) this.attributesDraft = JSON.stringify(value?.attributes || this.edge?.attributes || {}, null, 2);
			}
		},
		edge: {
			deep: true,
			handler(value) {
				if (!this.attributesPending && !this.node) this.attributesDraft = JSON.stringify(value?.attributes || {}, null, 2);
			}
		}
	},
	methods: {
		t,
		beforeUnload(event) {
			if (this.dirty || this.busy || this.uncertain || this.creating || this.deletionActive) {
				event.preventDefault();
				event.returnValue = "";
			}
		},
		canLeave() {
			return !this.creating && !this.deletionActive && !this.busy && (!(this.dirty || this.uncertain) || window.confirm(t("Discard unsaved changes?")));
		},
		openDeletion() {
			if (!this.editable || !this.node || this.node.referenceOnly || this.instance) return;
			if (this.dirty) {
				this.error = "Save or discard the schema draft before deleting a Search Type";
				return;
			}
			this.$refs.deletion.open(this.node.identity, this.revision);
		},
		acceptDeleted(result) {
			this.document = { xml: result.metadata.schema.xml };
			this.baseline = JSON.stringify(this.document);
			this.revision = result.metadata.schema.revision;
			this.xmlDraft = schemaText(this.document.xml);
			if (!result.metadata.sharedRegistration) this.metadata.searchTypes = this.metadata.searchTypes.filter((row) => row.identity !== result.identity);
			this.selectNode("");
			this.columnCatalog = {};
			this.columnRequest++;
			this.error = "";
			this.$emit("saved");
		},
		async call(action, values = {}) {
			return (await rpc("execute_cmd", [
				{
					ticket: this.context.ticket,
					project: this.context.project,
					language: "python"
				},
				"tactic.ui.panel.schema_cmd.SchemaCmd",
				{
					action,
					project_code: this.context.project,
					...values
				}
			])).info;
		},
		accept(result) {
			this.ui = {
				...this.ui,
				text: {},
				confirmation: "",
				pending: null,
				error: ""
			};
			this.document = result.document;
			this.identity = result.identity;
			this.revision = result.revision;
			this.metadata = result.metadata;
			this.canWrite = result.canWrite;
			this.baseline = JSON.stringify(this.document);
			this.xmlDraft = schemaText(this.document.xml);
			this.xmlPending = this.attributesPending = this.uncertain = false;
			this.selected = [];
			this.primaryNode = "";
			this.selectedEdge = -1;
			this.attributesDraft = "";
			this.columnCatalog = {};
			this.columnRequest++;
		},
		async load() {
			const id = ++this.request;
			this.context = {
				ticket: this.ticket,
				project: this.project
			};
			this.busy = true;
			this.error = "";
			try {
				const result = await this.call("load");
				if (id === this.request) this.accept(result);
			} catch (error) {
				if (id === this.request) this.error = error.message;
			} finally {
				if (id === this.request) this.busy = false;
			}
		},
		async reload() {
			if (this.canLeave()) await this.load();
		},
		async save(confirmed = false) {
			if (!this.editable || !this.dirty) return;
			this.error = "";
			if (this.xmlPending) this.applyXml();
			if (this.attributesPending) this.applyAttributes();
			if (this.error || this.xmlPending || this.attributesPending || pending(this.ui)) return;
			if (!confirmed && (Object.keys(this.document.newTypes || {}).length || this.document.createColumns?.length) && !window.confirm(t("Save the schema and create its new instance tables and missing key columns? Existing columns and values will be kept."))) return;
			const id = this.request;
			this.busy = true;
			this.error = "";
			try {
				const result = await this.call("save", {
					identity: this.identity,
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
		discardBuffers() {
			if (!this.attributesPending) return true;
			if (!window.confirm(t("Discard unapplied JSON changes?"))) return false;
			this.attributesPending = false;
			return true;
		},
		selectMany(identities, primary) {
			if (this.discardBuffers()) {
				this.inspectorPage = "selection";
				this.selected = identities;
				this.primaryNode = primary || identities[identities.length - 1] || "";
				this.selectedEdge = -1;
				this.attributesDraft = JSON.stringify(this.node?.attributes || {}, null, 2);
			}
		},
		selectNode(identity, multiple = false) {
			if (!this.discardBuffers()) return;
			this.inspectorPage = "selection";
			this.selected = multiple ? this.selected.includes(identity) ? this.selected.filter((name) => name !== identity) : [...this.selected, identity] : identity ? [identity] : [];
			this.primaryNode = this.selected.includes(identity) ? identity : this.selected[this.selected.length - 1] || "";
			this.selectedEdge = -1;
			this.attributesDraft = JSON.stringify(this.node?.attributes || {}, null, 2);
		},
		selectEdge(index) {
			if (!this.discardBuffers()) return;
			this.inspectorPage = "selection";
			this.selected = [];
			this.selectedEdge = index;
			this.attributesDraft = JSON.stringify(this.edge?.attributes || {}, null, 2);
		},
		changed(xml) {
			const text = new XMLSerializer().serializeToString(xml);
			schemaXml(text);
			this.document.xml = text;
			this.xmlDraft = schemaText(text);
			this.error = "";
			const names = new Set([...xml.documentElement.children].filter((node) => node.tagName === "search_type").map((node) => node.getAttribute("name")));
			for (const name of Object.keys(this.document.newTypes || {})) if (!names.has(name)) delete this.document.newTypes[name];
			const keys = [...xml.documentElement.children].filter((node) => node.tagName === "connect").map((node) => JSON.stringify(edgeKey(attributes(node))));
			if (this.document.createColumns) this.document.createColumns = this.document.createColumns.filter((key) => keys.includes(JSON.stringify(key)));
			for (const key of ["newTypes", "createColumns"]) if (!Object.keys(this.document[key] || {}).length) delete this.document[key];
		},
		editXml(operation) {
			if (!this.editable) return;
			try {
				const xml = schemaXml(this.document.xml);
				operation(xml.documentElement, xml);
				this.changed(xml);
			} catch (error) {
				this.error = error.message;
			}
		},
		addNode(position) {
			if (!this.editable || !this.discardBuffers()) return;
			const name = this.typeToAdd;
			if (this.typeOnCanvas) {
				this.selectNode(name);
				nextTick(() => this.graphCommand({ type: "reveal" }));
				this.typeToAdd = "";
				return;
			}
			if (!this.typeOptions.some((row) => row.value === name)) return;
			this.editXml((root, xml) => {
				const node = xml.createElement("search_type"), index = this.nodes.length;
				for (const [key, value] of Object.entries({
					name,
					xpos: position?.x ?? 40 + index % 3 * 240,
					ypos: position?.y ?? 40 + Math.floor(index / 3) * 130
				})) node.setAttribute(key, String(value));
				root.append(node);
			});
			if (!this.error) {
				this.selectNode(name);
				this.typeToAdd = "";
			}
		},
		moveNodes(positions) {
			this.editXml((root) => {
				for (const position of positions) {
					if (![position.nodeX, position.nodeY].every(Number.isFinite)) throw Error("Node positions must be finite");
					const node = [...root.children].find((node) => node.tagName === "search_type" && node.getAttribute("name") === position.identity);
					if (node) {
						node.setAttribute("xpos", String(Math.round(position.nodeX * 10) / 10));
						node.setAttribute("ypos", String(Math.round(position.nodeY * 10) / 10));
					}
				}
			});
		},
		connect(source = this.source, target = this.target) {
			if (!this.options.some((row) => row.value === source) || !this.options.some((row) => row.value === target) || source === target) {
				this.error = "Choose two different nodes";
				return;
			}
			if (this.edges.some((edge) => edge.from === source && edge.to === target)) {
				this.error = "This connection already exists";
				return;
			}
			this.editXml((root, xml) => {
				const edge = xml.createElement("connect");
				for (const [key, value] of Object.entries({
					from: source,
					to: target,
					relationship: "code",
					type: "hierarchy"
				})) edge.setAttribute(key, value);
				root.append(edge);
			});
			if (!this.error) this.selectEdge(this.edges.length - 1);
		},
		remove(confirmed = false) {
			if (!this.editable || !this.selected.length && !this.edge || !confirmed && !window.confirm(t("Remove the selection from the schema draft? Search Types, tables and data will be kept."))) return;
			const names = this.selected.filter((name) => !this.nodes.find((node) => node.identity === name)?.referenceOnly);
			this.editXml((root) => {
				if (this.edge) [...root.children].filter((node) => node.tagName === "connect")[this.selectedEdge].remove();
				else for (const node of [...root.children]) if (node.tagName === "search_type" && names.includes(node.getAttribute("name")) || node.tagName === "connect" && [node.getAttribute("from"), node.getAttribute("to")].some((name) => names.includes(name))) node.remove();
			});
			if (!this.error) this.selectNode("");
		},
		setAttribute(key, value) {
			if (this.node?.referenceOnly) return;
			this.editXml((root) => {
				(this.node ? [...root.children].find((node) => node.tagName === "search_type" && node.getAttribute("name") === this.node.identity) : [...root.children].filter((node) => node.tagName === "connect")[this.selectedEdge])?.setAttribute(key, String(value));
			});
		},
		setColumn(key, value) {
			const edge = this.connection;
			this.editXml((root) => {
				const node = [...root.children].filter((node) => node.tagName === "connect")[this.selectedEdge];
				node.setAttribute("from_col", edge.from_col);
				node.setAttribute("to_col", edge.to_col);
				node.setAttribute(key, value.trim());
			});
		},
		setCreateColumns(value) {
			const key = edgeKey(this.edge);
			this.document.createColumns = (this.document.createColumns || []).filter((row) => JSON.stringify(row) !== JSON.stringify(key));
			if (value) this.document.createColumns.push(key);
		},
		async loadColumns(refresh = false) {
			const id = ++this.columnRequest;
			this.columnsError = "";
			this.columnsBusy = false;
			const endpoints = [...new Set([this.edge?.from, this.edge?.to].filter((name) => name && name !== "*" && !this.document.newTypes?.[name]))];
			if (refresh) this.columnCatalog = {};
			const missing = endpoints.filter((name) => !this.columnCatalog[name]);
			if (!missing.length) return;
			this.columnsBusy = true;
			try {
				const result = await this.call("columns", { search_types: missing });
				if (id === this.columnRequest) Object.assign(this.columnCatalog, result);
			} catch (error) {
				if (id === this.columnRequest) this.columnsError = error.message;
			} finally {
				if (id === this.columnRequest) this.columnsBusy = false;
			}
		},
		reverse() {
			const edge = this.connection, allowed = this.createColumns;
			if (this.instance) return;
			this.editXml((root) => {
				const node = [...root.children].filter((node) => node.tagName === "connect")[this.selectedEdge];
				for (const [key, value] of Object.entries({
					from: edge.to,
					to: edge.from,
					from_col: edge.to_col,
					to_col: edge.from_col
				})) node.setAttribute(key, value);
			});
			if (!this.error) {
				if (allowed) this.setCreateColumns(true);
				this.loadColumns();
			}
		},
		makeInstance() {
			const edge = this.connection;
			if (!edge || this.instance || [edge.from, edge.to].includes("*")) return;
			const types = Object.fromEntries((this.metadata.searchTypes || []).map((row) => [row.identity, row]));
			const endpoints = [edge.from, edge.to], tables = endpoints.map((name) => types[name]?.table || name.split("/").pop());
			const base = tables.join("_in_");
			let name = this.context.project + "/" + base, suffix = 2;
			while (this.nodes.some((row) => row.identity === name) || types[name]) name = this.context.project + "/" + base + "_" + suffix++;
			const positions = this.nodes.filter((row) => endpoints.includes(row.identity)), allowed = this.createColumns;
			this.editXml((root, xml) => {
				[...root.children].filter((node) => node.tagName === "connect")[this.selectedEdge].remove();
				const node = xml.createElement("search_type");
				for (const [key, value] of Object.entries({
					name,
					type: "instance",
					xpos: positions.reduce((sum, row) => sum + row.nodeX, 0) / positions.length,
					ypos: positions.reduce((sum, row) => sum + row.nodeY, 0) / positions.length + 110
				})) node.setAttribute(key, String(value));
				root.append(node);
				for (const [index, endpoint] of endpoints.entries()) {
					const key = endpoint === edge.to ? edge.to_col || "code" : "code";
					const foreignKey = tables[index] + (tables[0] === tables[1] ? index === 0 ? "_from_" : "_to_" : "_") + key;
					const link = xml.createElement("connect");
					for (const [attr, value] of Object.entries({
						from: name,
						to: endpoint,
						relationship: "code",
						type: "hierarchy",
						from_col: foreignKey,
						to_col: key
					})) link.setAttribute(attr, value);
					root.append(link);
				}
			});
			if (!this.error) {
				(this.document.newTypes ||= {})[name] = {
					original: {
						...edge.attributes,
						from_col: edge.from_col,
						to_col: edge.to_col
					},
					createColumns: allowed
				};
				this.selectNode(name);
			}
		},
		renameInstance(table) {
			if (!/^[a-z][a-z0-9_]*$/.test(table)) {
				this.error = "Use a lowercase table name with letters, digits and underscores";
				return;
			}
			const old = this.instance, name = this.context.project + "/" + table;
			if (name === old) return;
			if (this.nodes.some((row) => row.identity === name) || this.metadata.searchTypes.some((row) => row.identity === name)) {
				this.error = "A Search Type with this name already exists";
				return;
			}
			const draft = this.document.newTypes[old];
			this.editXml((root) => {
				for (const node of [...root.children]) for (const key of node.tagName === "search_type" ? ["name"] : node.tagName === "connect" ? ["from", "to"] : []) if (node.getAttribute(key) === old) node.setAttribute(key, name);
			});
			if (!this.error) {
				(this.document.newTypes ||= {})[name] = draft;
				delete this.document.newTypes[old];
				this.selectNode(name);
			}
		},
		restoreDirect() {
			const name = this.instance, draft = this.document.newTypes[name];
			this.editXml((root, xml) => {
				for (const node of [...root.children]) if (node.tagName === "search_type" && node.getAttribute("name") === name || node.tagName === "connect" && [node.getAttribute("from"), node.getAttribute("to")].includes(name)) node.remove();
				const edge = xml.createElement("connect");
				for (const [key, value] of Object.entries(draft.original)) edge.setAttribute(key, value);
				root.append(edge);
			});
			if (!this.error) {
				this.selectEdge(this.edges.length - 1);
				if (draft.createColumns) this.setCreateColumns(true);
			}
		},
		applyAttributes() {
			if (!this.editable || this.node?.referenceOnly) return;
			try {
				const value = JSON.parse(this.attributesDraft);
				if (!value || typeof value !== "object" || Array.isArray(value) || Object.values(value).some((value) => typeof value !== "string")) throw Error("Attributes must be a JSON object with string values");
				if (this.node && value.name !== this.node.identity) throw Error("Search Type identities cannot be renamed here. Use the instance table name field for a new instance.");
				this.editXml((root) => {
					const node = this.node ? [...root.children].find((node) => node.tagName === "search_type" && node.getAttribute("name") === this.node.identity) : [...root.children].filter((node) => node.tagName === "connect")[this.selectedEdge];
					for (const attr of [...node.attributes]) node.removeAttribute(attr.name);
					for (const [key, text] of Object.entries(value)) node.setAttribute(key, text);
				});
				if (!this.error) {
					this.attributesPending = false;
					this.loadColumns();
				}
			} catch (error) {
				this.error = error.message;
			}
		},
		applyXml() {
			if (!this.editable) return;
			try {
				const xml = schemaXml(this.xmlDraft);
				this.changed(xml);
				this.xmlPending = false;
				this.selectNode("");
			} catch (error) {
				this.error = error.message;
			}
		},
		async arrange(style) {
			if (!this.editable) return;
			const id = this.request;
			this.busy = true;
			try {
				const result = await this.call("layout", {
					document: { xml: this.document.xml },
					style
				});
				if (id === this.request) {
					this.document.xml = result.xml;
					this.xmlDraft = schemaText(result.xml);
					await nextTick();
					this.graphCommand({ type: "reset" });
				}
			} catch (error) {
				if (id === this.request) this.error = error.message;
			} finally {
				if (id === this.request) this.busy = false;
			}
		},
		async createType(position) {
			if (!this.editable || this.xmlPending || this.attributesPending || pending(this.ui)) {
				this.error = "Apply the XML and JSON buffers before creating a Search Type";
				return;
			}
			const index = this.nodes.length;
			this.creationPosition = position || {
				x: 40 + index % 3 * 240,
				y: 40 + Math.floor(index / 3) * 130
			};
			this.creating = true;
			await nextTick();
			this.$refs.creationDialog.showModal();
		},
		closeCreator() {
			if (this.$refs.typeCreator?.busy || this.$refs.typeCreator?.previewValidating) return;
			this.$refs.creationDialog.close();
			this.creating = false;
		},
		async acceptCreated(result) {
			const schema = result.metadata.schema, serverXml = schemaXml(schema.xml), xml = schemaXml(this.document.xml);
			const node = [...serverXml.documentElement.children].find((node) => node.tagName === "search_type" && node.getAttribute("name") === result.identity);
			if (!node) {
				this.error = "The server did not return the created schema node";
				return;
			}
			if (![...xml.documentElement.children].some((node) => node.tagName === "search_type" && node.getAttribute("name") === result.identity)) {
				const copy = xml.importNode(node, true);
				copy.setAttribute("xpos", String(this.creationPosition.x));
				copy.setAttribute("ypos", String(this.creationPosition.y));
				xml.documentElement.append(copy);
			}
			this.baseline = JSON.stringify({ xml: schema.xml });
			this.revision = schema.revision;
			const types = new Map(this.metadata.searchTypes.map((row) => [row.identity, row]));
			for (const row of result.catalog) types.set(row.identity, row);
			this.metadata.searchTypes = [...types.values()];
			this.changed(xml);
			this.selectNode(result.identity);
			this.$emit("saved");
		},
		async creatorSaved() {
			await nextTick();
			if (!this.$refs.typeCreator.dirty) {
				this.$refs.creationDialog.close();
				this.creating = false;
			}
		}
	}
};
var _hoisted_1 = ["aria-busy"];
var _hoisted_2 = {
	ref: "body",
	class: "frame-host-body"
};
var _hoisted_3 = ["aria-label"];
var _hoisted_4 = { class: "configuration-header" };
var _hoisted_5 = { class: "configuration-heading" };
var _hoisted_6 = { class: "muted" };
var _hoisted_7 = ["id"];
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_FrameView = resolveComponent("FrameView");
	const _component_SchemaTypeDeletion = resolveComponent("SchemaTypeDeletion");
	const _component_AppButton = resolveComponent("AppButton");
	const _component_SearchTypes = resolveComponent("SearchTypes");
	const _directive_window = resolveDirective("window");
	return openBlock(), createElementBlock("section", {
		class: "schema-editor frame-host",
		"aria-busy": $data.busy
	}, [
		(openBlock(), createBlock(Teleport, {
			to: $props.toolbarTarget || "body",
			disabled: !$props.toolbarTarget
		}, [withDirectives(createBaseVNode("div", {
			class: "frame-toolbar-host",
			style: normalizeStyle({ width: _ctx.toolbarSize + "px" })
		}, [createVNode(_component_FrameView, {
			scene: _ctx.toolbarScene,
			onEvent: _ctx.dispatch
		}, null, 8, ["scene", "onEvent"])], 4), [[vShow, $props.presentationVisible]])], 8, ["to", "disabled"])),
		createBaseVNode("div", _hoisted_2, [createVNode(_component_FrameView, {
			ref: "frame",
			scene: _ctx.frameScene,
			models: _ctx.frameModels,
			"describe-row": _ctx.rowScene,
			onEvent: _ctx.dispatch
		}, null, 8, [
			"scene",
			"models",
			"describe-row",
			"onEvent"
		])], 512),
		createVNode(_component_SchemaTypeDeletion, {
			ref: "deletion",
			ticket: $props.ticket,
			project: $props.project,
			onActive: _cache[0] || (_cache[0] = ($event) => $data.deletionActive = $event),
			onDeleted: $options.acceptDeleted,
			onUncertain: _cache[1] || (_cache[1] = ($event) => $data.uncertain = true)
		}, null, 8, [
			"ticket",
			"project",
			"onDeleted"
		]),
		withDirectives((openBlock(), createElementBlock("dialog", {
			ref: "creationDialog",
			class: "configuration-dialog schema-creation-dialog",
			"aria-label": $options.t("New Search Type"),
			onCancel: _cache[4] || (_cache[4] = withModifiers((...args) => $options.closeCreator && $options.closeCreator(...args), ["prevent", "stop"])),
			onKeydown: _cache[5] || (_cache[5] = withKeys(withModifiers(() => {}, ["stop"]), ["esc"]))
		}, [$data.creating ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [createBaseVNode("header", _hoisted_4, [
			createBaseVNode("div", _hoisted_5, [createBaseVNode("h1", null, toDisplayString($options.t("New Search Type")), 1), createBaseVNode("p", _hoisted_6, toDisplayString($options.t("Create a table and add its node to the project schema. Your current connections and canvas edits will be kept.")), 1)]),
			createBaseVNode("div", {
				id: $setup.uid + "-schema-creation-actions",
				class: "configuration-actions"
			}, null, 8, _hoisted_7),
			createVNode(_component_AppButton, {
				label: "Close Search Type creator",
				icon: "close",
				"icon-only": "",
				onClick: $options.closeCreator
			}, null, 8, ["onClick"])
		]), createVNode(_component_SearchTypes, {
			ref: "typeCreator",
			ticket: $props.ticket,
			project: $data.context.project,
			"creation-only": "",
			"schema-revision": $data.revision,
			"toolbar-target": "#" + $setup.uid + "-schema-creation-actions",
			"queue-preview": $props.queuePreview,
			checkins: $props.checkins,
			onOpenWorkflow: _cache[2] || (_cache[2] = ($event) => _ctx.$emit("type-workflow", $event)),
			onCreated: $options.acceptCreated,
			onSaved: $options.creatorSaved,
			onOpenCommitQueue: _cache[3] || (_cache[3] = ($event) => _ctx.$emit("open-commit-queue"))
		}, null, 8, [
			"ticket",
			"project",
			"schema-revision",
			"toolbar-target",
			"queue-preview",
			"checkins",
			"onCreated",
			"onSaved"
		])], 64)) : createCommentVNode("", true)], 40, _hoisted_3)), [[_directive_window, { kind: "schema_search_type" }]])
	], 8, _hoisted_1);
}
var SchemaEditor_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { SchemaEditor_default as default };

//# sourceMappingURL=SchemaEditor.js.map