import { A as onMounted, D as onActivated, E as nextTick, F as resolveComponent, G as withCtx, H as watch, I as resolveDirective, K as withDirectives, M as openBlock, N as renderList, O as onBeforeUnmount, P as renderSlot, X as ref, Y as reactive, _ as createElementBlock, b as createVNode, et as unref, f as Teleport, g as createCommentVNode, h as createBlock, k as onDeactivated, m as createBaseVNode, nt as normalizeStyle, p as computed, rt as toDisplayString, s as vShow, tt as normalizeClass, u as Fragment, y as createTextVNode } from "./vue.js";
import { $ as accentPresets, A as effectiveColorMode, D as t, I as controls, J as normalizePreferences, M as languages, O as appearance, P as saveAppearance, X as savePreferencePage, Y as preferences, et as iconSets, k as colorModes, o as _sfc_main$8, p as debugSettings, q as configurationPreview, rt as _plugin_vue_export_helper_default, tt as themes, u as _sfc_main$7 } from "./index.js";
import { C as label, E as rect, S as button, T as node, _ as AppSearchField_default, f as translate, n as observeFrameSizes, r as _sfc_main$9, w as muted } from "./resize.js";
import { F as rpc, I as saveServerConfiguration, O as projectCatalog, U as serverConfiguration, f as _sfc_main$11, u as _sfc_main$10 } from "./CodeBlock.js";
import { a as unsupportedField, i as fieldKind, t as RecordForm_default } from "./RecordForm.js";
import { m as timestampFullLabel } from "./textMetrics.js";
import { P as views, _ as editColumn, a as updateIntervals, b as describe$3, d as ProjectCreation_default, f as ImagePicker_default, g as describe$2, h as contentWidth, i as updateBatchDelays, m as change, o as updateModes, r as networkSettings, u as lifecycle, v as fieldsFor, x as pages, y as confirmation } from "./App.js";
//#region src/features/configuration/FrameSettings.vue
var _sfc_main$6 = {
	__name: "FrameSettings",
	props: {
		page: String,
		values: Object,
		options: Object,
		busy: Boolean,
		fields: Array,
		natural: Boolean
	},
	emits: [
		"field",
		"action",
		"columns"
	],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const host = ref(null), viewport = ref({
			width: 800,
			height: 600
		});
		const model = computed(() => ({
			values: props.values,
			options: props.options,
			busy: props.busy,
			style: appearance.theme,
			native: false,
			columns: props.page === "tasks" ? props.values.columns : []
		}));
		const fields = computed(() => props.fields || fieldsFor(props.page, model.value));
		const scene = computed(() => {
			const result = describe$2({
				...model.value,
				fields: fields.value
			}, viewport.value.width, viewport.value.height, appearance.language);
			if (props.natural) result.nodes[0].height = result.nodes[0].contentHeight;
			return result;
		});
		const height = computed(() => props.natural ? scene.value.nodes[0].contentHeight + "px" : "100%");
		const views = computed(() => Object.fromEntries(["light", "dark"].map((mode) => [mode + "Accent", {
			component: _sfc_main$10,
			props: {
				options: accentPresets,
				mode,
				label: mode === "light" ? "Light mode palette" : "Dark mode palette",
				disabled: props.busy,
				modelValue: props.values[mode + "Accent"],
				"onUpdate:modelValue": (value) => emit("field", {
					field: mode + "Accent",
					value
				})
			}
		}])));
		let observer;
		onMounted(() => {
			observer = observeFrameSizes((entries) => {
				const box = entries.at(-1).contentRect;
				viewport.value = {
					width: box.width,
					height: box.height
				};
			});
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		function dispatch(action) {
			if (action.type === "field" || action.type === "step") {
				const next = change(props.values, action, fields.value);
				emit("field", {
					field: action.field,
					value: next[action.field]
				});
			} else if (action.type.startsWith("column")) emit("columns", editColumn(props.values.columns || [], action));
			else emit("action", action);
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: normalizeClass(["frame-settings", { "frame-settings-natural": __props.natural }]),
				style: normalizeStyle({ height: height.value })
			}, [createVNode(_sfc_main$9, {
				scene: scene.value,
				views: views.value,
				onEvent: dispatch
			}, null, 8, ["scene", "views"])], 6);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/features/configuration/server.ui.mjs
function fields$3(model, language) {
	const text = (key) => translate(key, language), result = [];
	for (const [index, group] of (model.groups || []).entries()) {
		result.push({
			kind: "Heading",
			id: "serverGroup" + index,
			title: group.title
		});
		for (const setting of group.settings) {
			const key = setting.path;
			const definition = {
				id: "serverSetting_" + key,
				field: key,
				title: setting.label,
				description: setting.description,
				readOnly: !setting.editable,
				props: {
					maxLength: 4096,
					error: model.errorField === key
				}
			};
			if (setting.restart) definition.description += "\n" + text("Restart required after changes");
			if (setting.input_type === "services") for (const [name, title] of [["queue", "Background jobs"], ["files", "Bulk file transfers"]]) result.push(Object.assign({}, definition, {
				kind: "Switch",
				id: "serverService_" + name,
				field: key + "#" + name,
				title,
				enabled: setting.editable,
				action: {
					type: "service",
					path: key,
					name
				}
			}));
			else if (setting.editable && setting.input_type === "boolean") result.push(Object.assign({}, definition, { kind: "Switch" }));
			else if (setting.editable && setting.choices) result.push(Object.assign({}, definition, {
				kind: "Choice",
				options: setting.choices
			}));
			else result.push(Object.assign({}, definition, {
				kind: "Field",
				props: Object.assign({}, definition.props, {
					password: !!setting.secret,
					placeholder: setting.secret ? text("Leave empty to keep the stored secret") : String(setting.default ?? "")
				})
			}));
			if (setting.editable && setting.input_type === "boolean") result.push({
				kind: "Button",
				id: "serverDefault_" + key,
				title: "Use default",
				props: { icon: "undo" },
				enabled: model.draft[key] !== "",
				action: {
					type: "default",
					path: key
				}
			});
			if (setting.editable && setting.secret && setting.configured) result.push({
				kind: "Button",
				id: "serverClear_" + key,
				title: "Clear stored secret",
				enabled: model.draft[key] !== "",
				props: {
					icon: "delete",
					destructive: true
				},
				action: {
					type: "clear",
					path: key
				}
			});
			if (model.showDetails) {
				result.push({
					kind: "Button",
					id: "serverDetails_" + key,
					title: "Details",
					props: { icon: "info" },
					action: {
						type: "details",
						path: key
					}
				});
				if (model.expanded?.includes(key)) {
					const lines = [key];
					if (setting.editable) lines.push(text("Saved value: {value}").replace("{value}", setting.secret ? text(setting.configured ? "Configured (hidden)" : "Not set") : String(setting.value ?? text("Not set"))));
					if (!setting.configured && setting.default !== null) lines.push(text("Default when empty: {value}").replace("{value}", String(setting.default)));
					if (setting.environment_override) lines.push(text("Environment override: {value}").replace("{value}", String(setting.environment_override)));
					if (setting.note) lines.push(text(setting.note));
					if (setting.services) for (const service of setting.services) lines.push(text(service.name === "tactic" ? "Web and API" : service.name === "files" ? "Bulk file transfers" : "Background jobs") + " · " + text(service.enabled ? "Enabled" : "Disabled"));
					result.push({
						kind: "Area",
						id: "serverDetailsText_" + key,
						field: "details_" + key,
						title: "Details",
						height: Math.max(80, lines.length * 20),
						readOnly: true,
						detailsText: lines.join("\n")
					});
				}
			}
		}
	}
	return result;
}
//#endregion
//#region src/features/configuration/ServerConfiguration.vue
var _sfc_main$5 = {
	components: {
		FrameSettings: _sfc_main$6,
		AppIcon: _sfc_main$7,
		AppButton: _sfc_main$8
	},
	props: {
		ticket: {
			type: String,
			required: true
		},
		showDetails: Boolean,
		groupTitles: Array
	},
	emits: ["session-expired"],
	data() {
		return {
			configuration: null,
			activeGroup: "Services and workers",
			search: "",
			loading: false,
			saving: false,
			clientsLoading: false,
			clientsError: "",
			error: "",
			errorField: null,
			notice: "",
			draft: {},
			baseline: {},
			expanded: [],
			generation: 0
		};
	},
	computed: {
		fields() {
			return fields$3({
				groups: this.groups,
				draft: this.draft,
				expanded: this.expanded,
				showDetails: this.showDetails,
				errorField: this.errorField
			}, appearance.language);
		},
		frameValues() {
			const values = { ...this.draft };
			for (const group of this.groups) for (const setting of group.settings) {
				if (!setting.editable) values[setting.path] = this.value(setting);
				else if (setting.input_type === "boolean") values[setting.path] = this.booleanValue(setting);
				if (setting.services) for (const service of setting.services) values[setting.path + "#" + service.name] = this.serviceEnabled(setting, service);
			}
			for (const field of this.fields) if (field.detailsText) values[field.field] = field.detailsText;
			return values;
		},
		changes() {
			return Object.fromEntries(Object.entries(this.draft).filter(([path, value]) => value !== this.baseline[path]));
		},
		hasChanges() {
			return Object.keys(this.changes).length > 0;
		},
		failedSetting() {
			return this.configuration?.groups.flatMap((group) => group.settings).find((setting) => setting.path === this.errorField)?.label;
		},
		groups() {
			const query = this.search.trim().toLowerCase();
			return (this.configuration?.groups || []).filter((group) => !this.groupTitles || this.groupTitles.includes(group.title)).filter((group) => query || group.title === this.activeGroup).map((group) => ({
				...group,
				settings: group.settings.filter((setting) => [
					setting.path,
					t(setting.label),
					t(setting.description),
					t(group.title)
				].some((value) => value.toLowerCase().includes(query)))
			})).filter((group) => group.settings.length);
		}
	},
	watch: { ticket() {
		this.generation++;
		this.configuration = null;
		this.draft = {};
		this.baseline = {};
		this.expanded = [];
		this.loading = this.saving = this.clientsLoading = false;
		this.error = this.notice = this.clientsError = "";
	} },
	mounted() {
		window.addEventListener("beforeunload", this.beforeUnload);
		this.load();
	},
	beforeUnmount() {
		this.generation++;
		window.removeEventListener("beforeunload", this.beforeUnload);
	},
	methods: {
		t,
		fieldEdited(action) {
			const setting = this.configuration.groups.flatMap((group) => group.settings).find((setting) => setting.path === action.field);
			const value = setting.input_type === "boolean" ? action.value ? "true" : "false" : setting.secret && !action.value ? null : action.value;
			this.editSetting(action.field, value);
		},
		action(action) {
			if (action.type === "details") this.expanded = this.expanded.includes(action.path) ? this.expanded.filter((path) => path !== action.path) : [...this.expanded, action.path];
			else if (action.type === "default" || action.type === "clear") this.editSetting(action.path, "");
			else if (action.type === "service") {
				const setting = this.configuration.groups.flatMap((group) => group.settings).find((setting) => setting.path === action.path);
				this.editService(setting, action.name, action.value);
			}
		},
		groupHeading(title) {
			return {
				"Services and workers": "Processes and monitoring",
				Network: "Connection",
				Database: "Database connection",
				"File repository": "Repository locations",
				"Task scheduling": "Schedule",
				Security: "Account and API security",
				"Directories and logs": "Runtime paths"
			}[title] || title;
		},
		groupChanged(group) {
			return group.settings.some((setting) => Object.hasOwn(this.changes, setting.path));
		},
		beforeUnload(event) {
			if (!this.hasChanges && !this.saving) return;
			event.preventDefault();
			event.returnValue = "";
		},
		async load() {
			if (this.loading || this.saving || this.hasChanges) return;
			const generation = this.generation;
			this.loading = true;
			this.error = "";
			this.notice = "";
			try {
				const configuration = await serverConfiguration(this.ticket);
				if (generation !== this.generation) return;
				this.configuration = configuration;
				this.resetDraft();
			} catch (error) {
				if (generation !== this.generation) return;
				if (error.code === "authentication_failed") this.$emit("session-expired");
				this.error = error instanceof TypeError ? "Unable to reach the server." : error.message;
			} finally {
				if (generation === this.generation) this.loading = false;
			}
		},
		resetDraft(groupTitles) {
			const previous = { ...this.draft };
			this.draft = {};
			for (const group of this.configuration.groups) for (const setting of group.settings) {
				if (!setting.editable) continue;
				this.draft[setting.path] = setting.input_type === "services" ? setting.services.filter((service) => service.enabled).map((service) => service.name).join("|") : setting.secret ? null : setting.value ?? "";
			}
			this.baseline = { ...this.draft };
			if (groupTitles) {
				for (const group of this.configuration.groups) if (!groupTitles.includes(group.title)) {
					for (const setting of group.settings) if (Object.hasOwn(previous, setting.path)) this.draft[setting.path] = previous[setting.path];
				}
			}
			this.error = "";
			this.errorField = null;
		},
		async refreshClients() {
			if (this.clientsLoading || this.loading || this.saving) return;
			const generation = this.generation;
			this.clientsLoading = true;
			this.clientsError = "";
			try {
				const result = await serverConfiguration(this.ticket);
				if (generation !== this.generation) return;
				this.configuration.event_clients = result.event_clients;
			} catch (error) {
				if (generation !== this.generation) return;
				if (error.code === "authentication_failed") this.$emit("session-expired");
				this.clientsError = error instanceof TypeError ? "Unable to reach the server." : error.message;
			} finally {
				if (generation === this.generation) this.clientsLoading = false;
			}
		},
		connectedTime(value) {
			return timestampFullLabel(new Date(value).toISOString());
		},
		async save(groupTitles) {
			if (this.loading || this.saving) return false;
			const generation = this.generation;
			const changes = Object.fromEntries(Object.entries(this.changes).filter(([path]) => !groupTitles || this.configuration.groups.some((group) => groupTitles.includes(group.title) && group.settings.some((setting) => setting.path === path))));
			if (!Object.keys(changes).length) return true;
			const pending = { ...this.changes };
			this.saving = true;
			this.error = "";
			this.errorField = null;
			try {
				const configuration = await saveServerConfiguration(this.ticket, changes, this.configuration.revision);
				if (generation !== this.generation) return false;
				this.configuration = configuration;
				this.resetDraft();
				for (const [path, value] of Object.entries(pending)) if (!Object.hasOwn(changes, path)) this.draft[path] = value;
				this.notice = this.configuration.restart_required ? "Saved to XML. Restart the backend to apply these settings." : this.configuration.saved ? "Saved to XML. New requests use the updated settings." : "No configuration changes were needed.";
				return true;
			} catch (error) {
				if (generation !== this.generation) return false;
				if (error.code === "authentication_failed") this.$emit("session-expired");
				this.error = error instanceof TypeError ? "Unable to reach the server." : error.message;
				this.errorField = error.field;
				const group = this.configuration.groups.find((group) => group.settings.some((setting) => setting.path === error.field));
				if (group) {
					this.activeGroup = group.title;
					this.search = "";
				}
				return false;
			} finally {
				if (generation === this.generation) this.saving = false;
			}
		},
		booleanValue(setting) {
			return (this.draft[setting.path] || setting.default) === "true";
		},
		value(setting) {
			if (setting.secret) return t(setting.configured ? "Configured (hidden)" : "Not set");
			return setting.value ?? t("Not set");
		},
		serviceEnabled(setting, service) {
			return setting.editable ? this.draft[setting.path].split("|").includes(service.name) : service.enabled;
		},
		editService(setting, name, enabled) {
			const services = new Set(this.draft[setting.path].split("|"));
			if (enabled) services.add(name);
			else services.delete(name);
			this.editSetting(setting.path, [
				"tactic",
				"queue",
				"files"
			].filter((service) => services.has(service)).join("|"));
		},
		editSetting(path, value) {
			this.draft[path] = value;
			if (this.errorField === path) {
				this.error = "";
				this.errorField = null;
			}
		}
	}
};
var _hoisted_1$4 = ["aria-busy"];
var _hoisted_2$3 = {
	key: 0,
	class: "error",
	role: "alert"
};
var _hoisted_3$1 = { key: 0 };
var _hoisted_4$1 = {
	key: 1,
	class: "notice",
	role: "status"
};
var _hoisted_5$1 = {
	key: 2,
	class: "muted",
	role: "status"
};
var _hoisted_6$1 = {
	key: 0,
	class: "settings-section event-clients"
};
var _hoisted_7$1 = { class: "muted" };
var _hoisted_8$1 = {
	key: 0,
	class: "error",
	role: "alert"
};
var _hoisted_9$1 = { class: "event-clients-scroll" };
var _hoisted_10 = { key: 0 };
var _hoisted_11 = {
	key: 1,
	class: "muted"
};
var _hoisted_12 = {
	key: 1,
	class: "configuration-source"
};
var _hoisted_13 = ["disabled"];
var _hoisted_14 = { class: "muted" };
var _hoisted_15 = { class: "muted" };
var _hoisted_16 = { class: "muted" };
var _hoisted_17 = {
	key: 0,
	class: "muted"
};
var _hoisted_18 = { class: "configuration-groups" };
var _hoisted_19 = {
	key: 0,
	class: "muted"
};
var _hoisted_20 = {
	key: 1,
	class: "configuration-group"
};
var _hoisted_21 = { class: "muted" };
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_AppButton = resolveComponent("AppButton");
	const _component_AppIcon = resolveComponent("AppIcon");
	const _component_FrameSettings = resolveComponent("FrameSettings");
	return openBlock(), createElementBlock("section", {
		class: "content server-configuration",
		"aria-busy": $data.loading || $data.saving
	}, [
		$data.error ? (openBlock(), createElementBlock("p", _hoisted_2$3, [$options.failedSetting ? (openBlock(), createElementBlock("strong", _hoisted_3$1, toDisplayString($options.t($options.failedSetting)) + ": ", 1)) : createCommentVNode("", true), createTextVNode(toDisplayString($options.t($data.error)), 1)])) : createCommentVNode("", true),
		$data.notice && !$options.hasChanges ? (openBlock(), createElementBlock("p", _hoisted_4$1, toDisplayString($options.t($data.notice)), 1)) : createCommentVNode("", true),
		$data.loading ? (openBlock(), createElementBlock("p", _hoisted_5$1, toDisplayString($options.t("Loading data…")), 1)) : createCommentVNode("", true),
		$data.configuration ? (openBlock(), createElementBlock(Fragment, { key: 3 }, [
			$data.activeGroup === "Services and workers" && !$data.search ? (openBlock(), createElementBlock("section", _hoisted_6$1, [
				createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString($options.t("SSE connections")) + " · " + toDisplayString($data.configuration.event_clients?.length || 0), 1), createVNode(_component_AppButton, {
					icon: "refresh",
					label: "Refresh connections",
					disabled: $data.clientsLoading || $data.loading || $data.saving,
					onClick: $options.refreshClients
				}, null, 8, ["disabled", "onClick"])]),
				createBaseVNode("p", _hoisted_7$1, toDisplayString($options.t("Open SSE connections across all web workers. This is a connection list, not user presence. Refresh to update the snapshot; closed connections disappear within the collection interval, crashed workers within 45 seconds.")), 1),
				$data.clientsError ? (openBlock(), createElementBlock("p", _hoisted_8$1, toDisplayString($options.t($data.clientsError)), 1)) : createCommentVNode("", true),
				createBaseVNode("div", _hoisted_9$1, [$data.configuration.event_clients?.length ? (openBlock(), createElementBlock("table", _hoisted_10, [createBaseVNode("thead", null, [createBaseVNode("tr", null, [
					createBaseVNode("th", null, toDisplayString($options.t("User")), 1),
					createBaseVNode("th", null, toDisplayString($options.t("Project")), 1),
					createBaseVNode("th", null, toDisplayString($options.t("Client")), 1),
					createBaseVNode("th", null, toDisplayString($options.t("Address")), 1),
					createBaseVNode("th", null, toDisplayString($options.t("Connected at")), 1),
					createBaseVNode("th", null, toDisplayString($options.t("Worker")), 1),
					createBaseVNode("th", null, toDisplayString($options.t("Subscriptions")), 1)
				])]), createBaseVNode("tbody", null, [(openBlock(true), createElementBlock(Fragment, null, renderList($data.configuration.event_clients, (client) => {
					return openBlock(), createElementBlock("tr", { key: client.connection }, [
						createBaseVNode("td", null, toDisplayString(client.login), 1),
						createBaseVNode("td", null, toDisplayString(client.project), 1),
						createBaseVNode("td", null, toDisplayString($options.t(client.application)), 1),
						createBaseVNode("td", null, toDisplayString(client.address), 1),
						createBaseVNode("td", null, toDisplayString($options.connectedTime(client.connected_at)), 1),
						createBaseVNode("td", null, toDisplayString(client.worker), 1),
						createBaseVNode("td", null, [createBaseVNode("details", null, [createBaseVNode("summary", null, toDisplayString(client.channels.join(", ")) + " · " + toDisplayString(client.search_types.length), 1), createBaseVNode("code", null, toDisplayString(client.search_types.join("\n")), 1)])])
					]);
				}), 128))])])) : (openBlock(), createElementBlock("p", _hoisted_11, toDisplayString($options.t("No open SSE connections")), 1))])
			])) : createCommentVNode("", true),
			$props.showDetails ? (openBlock(), createElementBlock("details", _hoisted_12, [
				createBaseVNode("summary", null, toDisplayString($options.t("Configuration source")), 1),
				createBaseVNode("button", {
					disabled: $data.loading || $data.saving || $options.hasChanges,
					onClick: _cache[0] || (_cache[0] = (...args) => $options.load && $options.load(...args))
				}, [createVNode(_component_AppIcon, { name: "refresh" }), createTextVNode(toDisplayString($options.t("Refresh")), 1)], 8, _hoisted_13),
				createBaseVNode("span", _hoisted_14, toDisplayString($options.t("Configuration file")), 1),
				createBaseVNode("code", null, toDisplayString($data.configuration.config_path), 1),
				createBaseVNode("span", _hoisted_15, toDisplayString($options.t("Data directory")), 1),
				createBaseVNode("code", null, toDisplayString($data.configuration.data_dir), 1),
				createBaseVNode("p", _hoisted_16, toDisplayString($options.t("Supported settings can be saved to XML. Values come from the configuration file; startup overrides may differ.")), 1),
				!$data.configuration.writable ? (openBlock(), createElementBlock("p", _hoisted_17, toDisplayString($options.t("The configuration file is missing or not writable. Editing is unavailable.")), 1)) : createCommentVNode("", true)
			])) : createCommentVNode("", true),
			createBaseVNode("div", _hoisted_18, [
				createVNode(_component_FrameSettings, {
					fields: $options.fields,
					values: $options.frameValues,
					busy: $data.loading || $data.saving,
					natural: "",
					onField: $options.fieldEdited,
					onAction: $options.action
				}, null, 8, [
					"fields",
					"values",
					"busy",
					"onField",
					"onAction"
				]),
				!$options.groups.length ? (openBlock(), createElementBlock("p", _hoisted_19, toDisplayString($options.t("No settings found")), 1)) : createCommentVNode("", true),
				$data.configuration.undocumented.length ? (openBlock(), createElementBlock("details", _hoisted_20, [
					createBaseVNode("summary", null, toDisplayString($options.t("Other configured options")) + " · " + toDisplayString($data.configuration.undocumented.length), 1),
					createBaseVNode("p", _hoisted_21, toDisplayString($options.t("These options still need documentation and a support check. Their values are not exposed.")), 1),
					createBaseVNode("ul", null, [(openBlock(true), createElementBlock(Fragment, null, renderList($data.configuration.undocumented, (path) => {
						return openBlock(), createElementBlock("li", { key: path }, [createBaseVNode("code", null, toDisplayString(path), 1)]);
					}), 128))])
				])) : createCommentVNode("", true)
			])
		], 64)) : createCommentVNode("", true)
	], 8, _hoisted_1$4);
}
var ServerConfiguration_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main$5, [["render", _sfc_render]]);
//#endregion
//#region ../src/tactic_stream/shared_ui/features/projects/catalog.ui.mjs
var fields$2 = ["projectCode", "projectDetails"];
function row$1(model, record, width, language) {
	const project = record.projectDetails, text = (key) => translate(key, language);
	const content = [
		node("Preview", "configurationProjectPreview", rect(10, 10, 96, 96), {
			source: project.preview || "",
			fallbackText: project.initials || project.code.slice(0, 2).toUpperCase(),
			radius: 10
		}),
		label("configurationProjectTitle", rect(118, 10, width - 132, 26), project.title || project.code, {
			fontRole: "bodyLarge",
			weight: 600
		}),
		label("configurationProjectCode", rect(118, 40, width - 132, 22), project.code, muted),
		label("configurationProjectCategory", rect(118, 66, width - 132, 20), project.category || text("No Category"), muted),
		label("configurationProjectLifecycle", rect(118, 90, width - 132, 18), text(lifecycle(project)), {
			fontRole: "caption",
			color: "secondaryText"
		})
	];
	return { nodes: [node("Action", "configurationProject_" + project.code, rect(0, 0, width, 116), {
		text: project.title || project.code,
		enabled: !model.busy,
		selected: model.selected?.code === project.code,
		normalColor: "surfaceContainerHigh",
		selectedColor: "contentSelection",
		action: {
			type: "select",
			record: project
		},
		doubleAction: {
			type: "activate",
			code: project.code
		},
		children: content
	})] };
}
function describe$1(model, width, height, language) {
	const text = (key) => translate(key, language), compact = width < 900, margin = 20;
	const selected = model.selected || {}, actionsWidth = compact ? width - 40 : 280;
	const catalogWidth = compact ? width - 40 : width - actionsWidth - 40 - 14;
	const nodes = [label("configurationProjectsTitle", rect(margin, 14, width - 40, 24), text("Available projects"), {
		fontRole: "bodyLarge",
		weight: 600,
		role: "heading"
	})];
	let x = margin;
	for (const [key, title] of [
		["retired", "Retired"],
		["templates", "Templates"],
		["builtins", "Built-in"]
	]) {
		const fieldWidth = Math.max(85, Math.min(126, catalogWidth / 3));
		nodes.push(node("CheckBox", "projectFilter_" + key, rect(x, 46, fieldWidth, 32), {
			text: text(title) + (model.counts ? " · " + model.counts[key] : ""),
			checked: !!model.filters?.[key],
			enabled: !model.busy,
			action: {
				type: "filter",
				field: key
			}
		}));
		x += fieldWidth;
	}
	const actionsX = compact ? margin : width - actionsWidth - margin;
	const actionsY = compact ? 104 : 46;
	const controls = [
		[
			"Activate selected project",
			"check",
			"activate",
			!!selected.code && selected.code !== model.currentCode
		],
		[
			"Edit selected project",
			"edit",
			"edit",
			!!selected.code && !selected.isBuiltin && model.canManage
		],
		[
			"Deactivate current project",
			"close",
			"deactivate",
			!!model.currentCode
		],
		[
			"Create template archive",
			"download",
			"archive",
			!!selected.code && !selected.isBuiltin && model.canManage
		],
		[
			"Create new project",
			"add",
			"create",
			model.canManage
		],
		[
			"Refresh projects",
			"refresh",
			"refresh",
			true
		]
	];
	for (const [index, [title, icon, type, enabled]] of controls.entries()) nodes.push(button("configurationProjectAction_" + type, rect(compact ? actionsX + index * 42 : actionsX, compact ? actionsY : actionsY + 112 + index * 44, compact ? 34 : actionsWidth, 36), text(title), icon, {
		type,
		code: selected.code
	}, enabled && !model.busy, { iconOnly: compact }));
	nodes.push(label("configurationCurrentProject", rect(actionsX, compact ? 146 : actionsY, actionsWidth, 28), model.currentTitle || text("No active project"), {
		weight: 600,
		role: "heading"
	}));
	if (!compact) {
		nodes.push(label("configurationSelectedProject", rect(actionsX, actionsY + 42, actionsWidth, 28), selected.title || text("Select a project"), { weight: 600 }));
		nodes.push(label("configurationSelectedCode", rect(actionsX, actionsY + 74, actionsWidth, 22), selected.code || "", muted));
	}
	nodes.push(label("configurationProjectsCount", rect(margin, 80, catalogWidth, 20), translate("{visible} of {total} projects shown", language, {
		visible: model.visibleCount || 0,
		total: model.totalCount || 0
	}), muted));
	const top = compact ? 184 : 110, bottom = model.error ? 70 : 16;
	nodes.push(node("List", "configurationProjects", rect(margin, top, catalogWidth, Math.max(0, height - top - bottom)), {
		source: "projects",
		fields: fields$2,
		keyField: "projectCode",
		rowHeight: 120,
		rowGap: 4
	}));
	if (model.error) nodes.push(label("configurationProjectsError", rect(margin, height - 60, width - 40, 48), model.error, {
		color: "error",
		wrap: true
	}));
	return { nodes };
}
function visibleProjects(projects, filters) {
	return projects.filter((project) => project.isBuiltin ? filters.builtins : project.isTemplate ? filters.templates : filters.retired || !project.isRetired);
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/projects/editor.ui.mjs
function fields$1(model) {
	const fields = [
		{
			kind: "Heading",
			id: "projectEditorImageTitle",
			title: "Project image",
			description: "Choose a large image; the repository web representation is used automatically when available."
		},
		{
			kind: "View",
			id: "projectEditorImage",
			fullWidth: true,
			height: 210,
			props: { view: "image" }
		},
		{
			kind: "Heading",
			id: "projectEditorDetails",
			title: "Project details",
			description: "Category and type describe how the project is organized; the project code is permanent."
		},
		{
			kind: "Field",
			field: "code",
			title: "Project code",
			description: "Permanent TACTIC identifier. It cannot be changed here.",
			readOnly: true
		},
		{
			kind: "Field",
			field: "title",
			title: "Name",
			description: "Human-readable project title shown throughout the application.",
			props: { maxLength: 100 }
		},
		{
			kind: "Field",
			field: "category",
			title: "Category",
			description: "Groups related projects in the chooser."
		},
		{
			kind: model.typeOptions?.length ? "Choice" : "Field",
			field: "type",
			title: "Type",
			description: "Project classification stored by TACTIC.",
			options: model.typeOptions
		},
		{
			kind: "Area",
			field: "description",
			title: "Description",
			description: "Explain the purpose of the project for people browsing the workspace.",
			height: 96
		},
		{
			kind: "Heading",
			id: "projectEditorLifecycle",
			title: "Lifecycle",
			description: "Archived projects stay on the server but are hidden by default. Templates are available for creating new projects."
		},
		{
			kind: "Switch",
			field: "archived",
			title: "Archive project",
			description: "Hide this project from the default active-project list without deleting it."
		},
		{
			kind: "Switch",
			field: "isTemplate",
			title: "Use as template",
			description: "Mark this project as a source template for future projects."
		}
	];
	if (model.extraFields?.length) fields.push({
		kind: "Heading",
		id: "projectEditorAdditional",
		title: "Additional settings"
	}, ...model.extraFields);
	return fields;
}
function describe(model, width, height, language) {
	const text = (key) => translate(key, language), footer = model.discard ? 116 : 62;
	const formFields = fields$1(model);
	const imageWidth = Math.max(1, contentWidth(width) - 32);
	if (imageWidth < 160 + controls.imagePicker.minimumActionsWidth) {
		const description = text("Choose a large image; the repository web representation is used automatically when available.");
		const lines = Math.max(1, Math.ceil(description.length * 7 / imageWidth));
		formFields.find((field) => field.id === "projectEditorImage").height = 190 + lines * 16 + 10 + 36 + (model.stagedImage ? 41 : 0);
	}
	const nodes = [
		node("Box", "projectEditorSurface", rect(0, 0, width, height), { background: "panelDeep" }),
		label("projectEditorTitle", rect(24, 12, width - 200, 28), text("Edit project"), {
			fontRole: "title",
			weight: 600,
			role: "heading"
		}),
		button("projectEditorHelp", rect(width - 86, 12, 32, 32), text("Project help"), "help", { type: "help" }, true, { iconOnly: true }),
		button("projectEditorClose", rect(width - 48, 12, 32, 32), text("Close"), "close", { type: "close" }, !model.busy, { iconOnly: true })
	];
	const body = describe$2({
		fields: formFields,
		values: model.values || {},
		busy: model.busy || model.loading || model.uncertain || model.blocked,
		error: model.error,
		notice: model.loading ? text("Loading data…") : text(model.notice),
		style: model.style
	}, width, Math.max(0, height - 52 - footer), language);
	for (const child of body.nodes) nodes.push(Object.assign({}, child, { y: child.y + 52 }));
	nodes.push(node("Box", "projectEditorFooter", rect(0, height - footer, width, footer), {
		background: "surfaceContainerLow",
		radius: 0
	}));
	if (model.discard) {
		nodes.push(label("projectEditorDiscardText", rect(20, height - footer + 10, width - 40, 38), text("Discard changes?"), { wrap: true }));
		nodes.push(button("projectEditorKeep", rect(20, height - 48, 142, 36), text("Keep editing"), "", { type: "keep" }, !model.busy));
		nodes.push(button("projectEditorDiscard", rect(width - 176, height - 48, 156, 36), text("Discard changes"), "", { type: "discard" }, !model.busy, { destructive: true }));
	} else {
		nodes.push(button("projectEditorCancel", rect(20, height - 48, 110, 36), text("Cancel"), "", { type: "close" }, !model.busy));
		nodes.push(button("projectEditorSave", rect(width - 150, height - 48, 130, 36), text("Save"), "save", { type: "save" }, model.dirty && !model.busy && !model.uncertain && !model.blocked && !model.loading, { highlighted: true }));
	}
	const header = nodes.splice(1, 3);
	nodes.splice(1, 0, node("Box", "projectEditorHeader", rect(0, 0, width, 48), {
		titlebar: true,
		chromeRight: 86,
		background: "surfaceContainerLow",
		radius: 0,
		children: header
	}));
	return { nodes };
}
//#endregion
//#region src/features/projects/ProjectEditorSurface.vue
var _sfc_main$4 = {
	__name: "ProjectEditorSurface",
	props: {
		form: Object,
		contextValid: Boolean,
		previewUrl: String
	},
	emits: [
		"save",
		"cancel",
		"close",
		"keep",
		"help",
		"error"
	],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const imageValidating = ref(false);
		const host = ref(null), viewport = ref({
			width: 800,
			height: 700
		});
		const known = [
			"snapshot",
			"code",
			"title",
			"category",
			"type",
			"description",
			"s_status",
			"is_template"
		];
		const inputFields = computed(() => props.form.definition?.fields || []);
		const imageField = computed(() => inputFields.value.find((field) => fieldKind(field) === "FileInput"));
		const options = (field) => field?.choices?.map((value, index) => ({
			value,
			label: field.labels[index],
			dataLabel: true
		}));
		const unsupported = computed(() => inputFields.value.filter((field) => unsupportedField(field) || !known.includes(field.name) && ![
			"TextWdg",
			"TextAreaWdg",
			"SelectWdg",
			"CheckboxWdg",
			"HiddenWdg"
		].includes(fieldKind(field))));
		const extraFields = computed(() => inputFields.value.filter((field) => !known.includes(field.name) && fieldKind(field) !== "HiddenWdg" && !unsupported.value.includes(field)).map((field) => ({
			kind: fieldKind(field) === "SelectWdg" ? "Choice" : fieldKind(field) === "TextAreaWdg" ? "Area" : fieldKind(field) === "CheckboxWdg" ? "Switch" : "Field",
			field: field.name,
			title: field.title,
			description: field.options.hint || field.options.hint_text || "",
			dataLabel: true,
			options: options(field),
			readOnly: !!field.input?.read_only || field.options.read_only === "true"
		})));
		const model = computed(() => ({
			values: {
				...props.form.draft,
				archived: props.form.draft.s_status === "retired",
				isTemplate: [
					true,
					1,
					"1",
					"true",
					"t"
				].includes(props.form.draft.is_template)
			},
			stagedImage: !!(imageField.value && props.form.files[imageField.value.name]),
			typeOptions: options(inputFields.value.find((field) => field.name === "type")),
			extraFields: extraFields.value,
			busy: props.form.saving || imageValidating.value,
			loading: props.form.loading,
			uncertain: props.form.uncertain,
			dirty: JSON.stringify(props.form.draft) !== JSON.stringify(props.form.baseline),
			blocked: !props.contextValid || unsupported.value.length > 0,
			notice: unsupported.value.length ? "This form contains unsupported inputs or options. Saving is unavailable." : "",
			error: props.form.error,
			discard: props.form.discard,
			style: appearance.theme
		}));
		const scene = computed(() => describe(model.value, viewport.value.width, viewport.value.height, appearance.language));
		const views = computed(() => ({ image: {
			component: ImagePicker_default,
			props: {
				previewSize: 160,
				inlineErrors: false,
				onError: (message) => emit("error", message),
				onValidating: (value) => {
					imageValidating.value = value;
				},
				previewUrl: props.previewUrl,
				statusText: imageField.value && props.form.files[imageField.value.name] ? "A new preview is ready to be queued" : "Current project preview",
				description: "Choose a large image; the repository web representation is used automatically when available.",
				modelValue: imageField.value ? props.form.files[imageField.value.name] : null,
				fallbackText: String(props.form.draft.code || "").slice(0, 2).toUpperCase(),
				disabled: !imageField.value || props.form.saving || model.value.blocked || model.value.uncertain,
				"onUpdate:modelValue": (file) => {
					const key = imageField.value.name;
					if (file) props.form.files[key] = file;
					else delete props.form.files[key];
					props.form.draft[key] = file?.name || "";
				}
			}
		} }));
		let observer;
		onMounted(() => {
			observer = observeFrameSizes((entries) => {
				const box = entries.at(-1).contentRect;
				viewport.value = {
					width: box.width,
					height: box.height
				};
			});
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		function dispatch(action) {
			if (action.type === "field") props.form.draft[{
				archived: "s_status",
				isTemplate: "is_template"
			}[action.field] || action.field] = action.field === "archived" ? action.value ? "retired" : "" : action.value;
			else if (action.type === "keep") emit("keep");
			else if (action.type === "discard") emit("close");
			else if (action.type === "close") emit("cancel");
			else if (action.type === "save" && !imageValidating.value) emit("save");
			else if (action.type === "help") emit("help");
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "project-editor-frame"
			}, [createVNode(_sfc_main$9, {
				scene: scene.value,
				views: views.value,
				onEvent: dispatch
			}, null, 8, ["scene", "views"])], 512);
		};
	}
};
//#endregion
//#region src/features/configuration/ProjectSettings.vue
var _hoisted_1$3 = ["aria-busy"];
var _hoisted_2$2 = {
	key: 1,
	role: "status"
};
var _sfc_main$3 = {
	__name: "ProjectSettings",
	props: {
		ticket: String,
		project: String,
		canAdminister: Boolean,
		openProject: Function
	},
	emits: ["changed", "help"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const projects = ref([]), selected = ref(""), editor = ref(null), creator = ref(null), busy = ref(false), error = ref("");
		const item = computed(() => projects.value.find((item) => item.code === selected.value));
		const editable = computed(() => props.canAdminister && item.value && !item.value.__builtin__ && !busy.value);
		const host = ref(null), viewport = ref({
			width: 900,
			height: 600
		}), filters = ref({
			retired: false,
			templates: false,
			builtins: false
		});
		const records = computed(() => projects.value.map((record) => ({
			...record,
			isBuiltin: !!record.__builtin__,
			isTemplate: [
				true,
				1,
				"true",
				"t",
				"1"
			].includes(record.is_template),
			isRetired: record.s_status === "retired",
			preview: record.preview || record.__preview__ || ""
		})));
		const visible = computed(() => visibleProjects(records.value, filters.value).map((projectDetails) => ({
			projectCode: projectDetails.code,
			projectDetails
		})));
		const model = computed(() => ({
			counts: {
				retired: records.value.filter((item) => item.isRetired).length,
				templates: records.value.filter((item) => item.isTemplate).length,
				builtins: records.value.filter((item) => item.isBuiltin).length
			},
			totalCount: records.value.length,
			visibleCount: visible.value.length,
			selected: records.value.find((record) => record.code === selected.value),
			currentCode: props.project,
			currentTitle: projects.value.find((record) => record.code === props.project)?.title,
			canManage: props.canAdminister,
			busy: busy.value,
			error: error.value,
			filters: filters.value
		}));
		const scene = computed(() => describe$1(model.value, viewport.value.width, viewport.value.height, appearance.language));
		const row = (list, record) => row$1(model.value, record, list.width - 16, appearance.language);
		let observer;
		let generation = 0;
		watch(() => props.ticket, () => {
			generation++;
			projects.value = [];
			selected.value = "";
			busy.value = false;
			error.value = "";
		});
		onMounted(() => {
			observer = observeFrameSizes((entries) => {
				const box = entries.at(-1).contentRect;
				viewport.value = {
					width: box.width,
					height: box.height
				};
			});
			observer.observe(host.value);
		});
		onBeforeUnmount(() => {
			generation++;
			observer?.disconnect();
		});
		function dispatch(action) {
			if (action.type === "select") selected.value = action.record.code;
			else if (action.type === "filter") filters.value[action.field] = action.value;
			else if (action.type === "activate") activate(action.code);
			else if (action.type === "deactivate") activate("");
			else if (action.type === "edit") editor.value.open(item.value.__search_key__);
			else if (action.type === "archive") archive();
			else if (action.type === "create") creator.value.open();
			else if (action.type === "refresh") load();
		}
		async function load() {
			const request = generation;
			busy.value = true;
			error.value = "";
			try {
				const records = await projectCatalog(props.ticket);
				if (request === generation) projects.value = records;
			} catch (failure) {
				if (request !== generation) return;
				error.value = failure.message;
			} finally {
				if (request === generation) busy.value = false;
			}
		}
		async function activate(code) {
			const request = generation;
			if (busy.value) return;
			busy.value = true;
			error.value = "";
			try {
				if (await props.openProject(code) === false) error.value = "The project could not be activated.";
			} catch (failure) {
				if (request !== generation) return;
				error.value = failure.message;
			} finally {
				if (request === generation) busy.value = false;
			}
		}
		async function changed() {
			await load();
			emit("changed");
		}
		async function created(code) {
			if (await props.openProject(code) === false) throw new Error("The project could not be activated.");
			selected.value = code;
			await changed();
		}
		async function archive() {
			const request = generation;
			if (!editable.value) return;
			busy.value = true;
			error.value = "";
			try {
				const result = await rpc("execute_cmd", [
					{
						ticket: props.ticket,
						project: "admin",
						language: "python"
					},
					"tactic.ui.app.ProjectTemplateExportCmd",
					{ project_code: item.value.code }
				]);
				if (request !== generation) return;
				const link = document.createElement("a");
				link.href = "/assets/_cache/" + encodeURIComponent(props.ticket) + "/" + encodeURIComponent(result.info.filename);
				link.download = result.info.filename;
				link.click();
			} catch (failure) {
				if (request !== generation) return;
				error.value = failure.message;
			} finally {
				if (request === generation) busy.value = false;
			}
		}
		onMounted(load);
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				ref_key: "host",
				ref: host,
				class: "configuration-projects-frame",
				"aria-busy": busy.value
			}, [
				createVNode(_sfc_main$9, {
					scene: scene.value,
					models: { projects: visible.value },
					"describe-row": row,
					onEvent: dispatch
				}, null, 8, ["scene", "models"]),
				createVNode(RecordForm_default, {
					ref_key: "editor",
					ref: editor,
					class: "configuration-project-editor",
					ticket: __props.ticket,
					project: "admin",
					"search-type": "sthpw/project",
					"edit-view": "configuration_edit",
					modal: "",
					onSaved: changed
				}, {
					surface: withCtx(({ form, save, cancel, close, keep, reportError, contextValid }) => [form.definition || form.error ? (openBlock(), createBlock(_sfc_main$4, {
						key: 0,
						form,
						"preview-url": typeof item.value?.preview === "string" ? item.value.preview : "",
						"context-valid": contextValid,
						onSave: save,
						onCancel: cancel,
						onClose: close,
						onKeep: keep,
						onError: reportError,
						onHelp: _cache[0] || (_cache[0] = ($event) => _ctx.$emit("help", "project_creation"))
					}, null, 8, [
						"form",
						"preview-url",
						"context-valid",
						"onSave",
						"onCancel",
						"onClose",
						"onKeep",
						"onError"
					])) : (openBlock(), createElementBlock("p", _hoisted_2$2, toDisplayString(unref(t)("Loading data…")), 1))]),
					_: 1
				}, 8, ["ticket"]),
				createVNode(ProjectCreation_default, {
					ref_key: "creator",
					ref: creator,
					ticket: __props.ticket,
					"open-project": created
				}, null, 8, ["ticket"])
			], 8, _hoisted_1$3);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/features/configuration/repository.ui.mjs
var fields = [
	"alias",
	"title",
	"code",
	"active",
	"isDefault",
	"defaultEligible",
	"custom",
	"windowsPath",
	"linuxPath",
	"status",
	"statusText",
	"projectMapping"
];
function row(model, record, width) {
	return { nodes: [node("Action", "repository_" + record.alias, rect(0, 0, width, 54), {
		text: record.title || record.alias,
		enabled: !model.busy,
		selected: model.selected === record.alias,
		normalColor: "transparent",
		selectedColor: "contentSelection",
		action: {
			type: "select",
			alias: record.alias
		},
		children: [
			node("Box", "repositoryActive", rect(10, 23, 8, 8), {
				radius: 4,
				background: record.active ? "action" : "secondaryText"
			}),
			label("repositoryTitle", rect(28, 5, width - 38, 24), record.title || record.alias, { weight: 600 }),
			label("repositoryCode", rect(28, 30, width - 38, 18), record.code || record.alias, muted)
		]
	})] };
}
function editorFields(model) {
	const record = model.record || {};
	const fields = [
		{
			kind: "Heading",
			id: "repositoryIdentity",
			title: record.title || "Repository",
			dataLabel: !!record.title,
			description: model.native ? "Paths are stored in the active server preset" : "Paths are stored in the server configuration"
		},
		{
			kind: "CheckBox",
			field: "active",
			title: "Enabled",
			enabled: model.editable !== false && record.alias !== "plugins"
		},
		{
			kind: "CheckBox",
			field: "isDefault",
			title: "Default",
			enabled: !!record.active && record.defaultEligible !== false
		},
		{
			kind: "Field",
			field: "title",
			title: "Display name",
			props: { maxLength: 100 }
		}
	];
	if (!model.native) fields.push({
		kind: "Field",
		field: "serverPath",
		title: "Server repository path",
		readOnly: record.alias === "plugins"
	}, {
		kind: "Field",
		field: "webPath",
		title: "Repository web URL"
	});
	fields.push({
		kind: "Field",
		field: "windowsPath",
		title: model.native ? "Windows path" : "Windows client path"
	}, {
		kind: "Field",
		field: "linuxPath",
		title: model.native ? "Linux path" : "Linux client path"
	});
	if (model.native) fields.push({
		kind: "Area",
		field: "projectMapping",
		title: "PROJECT MAPPING",
		height: 80,
		readOnly: true
	});
	else fields.push({
		kind: "ColorChoice",
		field: "color",
		title: "Color"
	});
	fields.push({
		kind: "Field",
		field: "statusText",
		title: "Path status",
		readOnly: true
	}, {
		kind: "Button",
		field: "check",
		title: "Check paths",
		props: { icon: "check" },
		action: { type: "check" }
	});
	if (record.custom) fields.push({
		kind: "Button",
		field: "remove",
		title: "Delete",
		description: "Remove custom repository",
		props: {
			destructive: true,
			icon: "delete"
		},
		action: { type: "remove" }
	});
	if (!model.native) fields.push({
		kind: "Button",
		field: "advanced",
		title: "Advanced settings",
		props: { icon: "settings" },
		action: { type: "advanced" }
	});
	return fields.map((field) => Object.assign({}, field, { enabled: field.enabled !== false && (model.editable !== false || field.action?.type === "advanced") }));
}
function editor(model, width, height, language) {
	const text = (key) => translate(key, language), compact = width < 700, footerCompact = width < 560, margin = 16;
	const sidebar = compact ? width - 32 : Math.min(220, width * .34);
	const showCatalog = !compact || !model.editing;
	const showDetails = !compact || model.editing;
	const nodes = [label("repositoryEditorTitle", rect(margin, 12, width - 180, 26), text("Repository Editor"), {
		fontRole: "title",
		weight: 600,
		role: "heading"
	}), button("repositoryEditorClose", rect(width - 48, 10, 32, 32), text("Close"), "close", { type: "close" }, !model.busy, { iconOnly: true })];
	if (showCatalog) {
		nodes.push(node("Box", "repositoryCatalog", rect(margin, 52, sidebar, Math.max(0, height - 120)), {
			background: "surfaceContainerHigh",
			border: "outlineVariant",
			radius: 12
		}));
		nodes.push(label("repositoryCatalogTitle", rect(28, 62, sidebar - 64, 28), text("REPOSITORIES"), muted));
		nodes.push(button("repositoryAdd", rect(margin + sidebar - 44, 60, 32, 32), text("Add custom repository"), "add", { type: "add" }, !model.busy && model.editable !== false, { iconOnly: true }));
		nodes.push(node("List", "repositoryCatalogRows", rect(24, 100, sidebar - 16, Math.max(0, height - 176)), {
			source: "repositories",
			fields,
			keyField: "alias",
			rowHeight: 58,
			rowGap: 4
		}));
	}
	if (showDetails) {
		const left = compact ? 0 : sidebar + margin + 12, top = compact ? 90 : 48;
		if (compact) nodes.push(button("repositoryBack", rect(16, 50, 150, 34), text("Repositories"), "previous", { type: "back" }, true));
		const body = describe$2({
			fields: editorFields(model),
			values: model.record || {},
			busy: model.busy,
			error: model.error,
			notice: model.notice,
			style: model.style
		}, width - left - margin, Math.max(0, height - top - 68), language);
		for (const child of body.nodes) nodes.push(Object.assign({}, child, {
			x: child.x + left,
			y: child.y + top
		}));
	}
	nodes.push(node("Box", "repositoryFooter", rect(0, height - 62, width, 62), { background: "surfaceContainerLow" }));
	nodes.push(button("repositoryReset", rect(16, height - 48, footerCompact ? 36 : 120, 36), text("Reset"), "undo", { type: "reset" }, model.dirty && !model.busy, { iconOnly: footerCompact }));
	if (model.teamLocal && !model.dirty) nodes.push(button("repositorySync", rect(width - (footerCompact ? 192 : 336), height - 48, footerCompact ? 36 : 180, 36), text("Sync"), "refresh", { type: "sync" }, !model.busy, { iconOnly: footerCompact }));
	nodes.push(button("repositorySave", rect(width - 146, height - 48, 130, 36), text("Save"), "save", { type: "save" }, model.dirty && !model.busy, { highlighted: true }));
	const header = nodes.splice(0, 2);
	nodes.unshift(node("Box", "repositoryEditorHeader", rect(0, 0, width, 48), {
		titlebar: true,
		chromeRight: 48,
		background: "surfaceContainerLow",
		radius: 0,
		children: header
	}));
	return { nodes };
}
function summary(model, width, height, language) {
	const text = (key) => translate(key, language), fields = [
		{
			kind: "Heading",
			id: "repositoryStorage",
			title: "Repository storage",
			description: "Snapshots, previews, check-in, check-out and synchronization depend on a valid repository path."
		},
		{
			kind: "Field",
			field: "currentPath",
			title: model.currentTitle || "Repository configuration is loading",
			dataLabel: !!model.currentTitle,
			readOnly: true
		},
		{
			kind: "Button",
			field: "edit",
			title: "Open Repository Editor",
			props: { icon: "database" },
			action: { type: "edit" }
		},
		{
			kind: "Button",
			field: "check",
			title: model.busy ? "Checking…" : "Check paths",
			props: { icon: "check" },
			action: { type: "check" }
		},
		{
			kind: "Heading",
			id: "repositoryActive",
			title: "Active repositories",
			description: "The default repository is used when an operation does not choose another destination explicitly."
		}
	];
	for (const record of model.records || []) fields.push({
		kind: "Field",
		field: "repositoryPath_" + record.alias,
		title: record.title || record.alias,
		dataLabel: true,
		readOnly: true,
		description: [
			record.code || record.alias,
			record.isDefault ? text("Default") : "",
			text(record.active ? "Enabled" : "Disabled"),
			text(record.statusText || "Not checked")
		].filter(Boolean).join(" · ")
	});
	const values = { currentPath: model.currentPath || "" };
	for (const record of model.records || []) values["repositoryPath_" + record.alias] = record.path || record.windowsPath || record.linuxPath || "";
	return describe$2({
		fields,
		values,
		error: model.error,
		notice: model.notice,
		busy: model.busy,
		style: model.style
	}, width, height, language);
}
//#endregion
//#region src/features/configuration/RepositorySettings.vue
var _hoisted_1$2 = ["aria-busy"];
var _sfc_main$2 = {
	__name: "RepositorySettings",
	props: {
		ticket: String,
		busy: Boolean
	},
	emits: ["edit", "session-expired"],
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const records = ref([]), platform = ref(""), checking = ref(false), error = ref("");
		const current = computed(() => records.value.find((item) => item.alias === preferences.repository.defaultAlias) || records.value.find((item) => item.is_default));
		let generation = 0;
		watch(() => props.ticket, () => {
			generation++;
			records.value = [];
			checking.value = false;
			error.value = "";
		});
		async function load(action = "load", paths) {
			if (checking.value) return;
			const request = generation;
			checking.value = true;
			error.value = "";
			try {
				const result = await rpc("execute_cmd", [
					{
						ticket: props.ticket,
						project: "admin"
					},
					"tactic.ui.app.RepositoryPathsCmd",
					{
						action,
						...paths ? { paths } : {}
					}
				], {}, true);
				if (request !== generation) return false;
				records.value = result.info.repositories;
				platform.value = result.info.platform;
				return true;
			} catch (failure) {
				if (request !== generation) return false;
				if (failure.code === "authentication_failed") emit("session-expired");
				error.value = failure.message;
				return false;
			} finally {
				if (request === generation) checking.value = false;
			}
		}
		const host = ref(null), viewport = ref({
			width: 800,
			height: 600
		});
		const model = computed(() => ({
			currentTitle: current.value?.title,
			currentPath: current.value?.path,
			records: records.value.map((record) => ({
				...record,
				code: record.alias,
				active: record.enabled,
				isDefault: record.alias === preferences.repository.defaultAlias,
				statusText: record.status === "available" ? "Available" : record.status === "unchecked" ? "Not checked" : "Folder not found or inaccessible"
			})),
			busy: props.busy || checking.value,
			error: error.value,
			style: appearance.theme
		}));
		const scene = computed(() => summary(model.value, viewport.value.width, viewport.value.height, appearance.language));
		let observer;
		onMounted(() => {
			load();
			observer = observeFrameSizes((entries) => {
				const box = entries.at(-1).contentRect;
				viewport.value = {
					width: box.width,
					height: box.height
				};
			});
			observer.observe(host.value);
		});
		onBeforeUnmount(() => {
			generation++;
			observer?.disconnect();
		});
		function dispatch(action) {
			if (action.type === "edit") emit("edit");
			else if (action.type === "check") load("check");
		}
		__expose({
			load,
			records,
			checking
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				ref_key: "host",
				ref: host,
				class: "repository-settings repository-summary-frame",
				"aria-busy": checking.value
			}, [createVNode(_sfc_main$9, {
				scene: scene.value,
				onEvent: dispatch
			}, null, 8, ["scene"])], 8, _hoisted_1$2);
		};
	}
};
//#endregion
//#region src/features/configuration/RepositoryEditor.vue
var _hoisted_1$1 = { class: "repository-editor-frame-shell" };
var _hoisted_2$1 = { class: "repository-editor-advanced-frame" };
var _sfc_main$1 = {
	__name: "RepositoryEditor",
	props: {
		server: Object,
		repositories: Array,
		draft: Object,
		busy: Boolean,
		dirty: Boolean
	},
	emits: [
		"check",
		"close",
		"save",
		"reset"
	],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const selected = ref("default");
		const entries = computed(() => {
			try {
				return [.../* @__PURE__ */ new Set([
					...Object.keys(mapping("asset_base_dir")),
					...Object.keys(mapping("base_dir_alias")),
					"plugins"
				])].map((alias) => ({
					...props.repositories?.find((item) => item.alias === alias) || {},
					alias,
					path: root(alias)
				}));
			} catch {
				return props.repositories || [];
			}
		});
		const record = computed(() => entries.value.find((item) => item.alias === selected.value) || entries.value[0]);
		function stored(key) {
			return props.server?.draft["checkin/" + key] ?? "";
		}
		function mapping(key) {
			const raw = stored(key);
			return !raw ? {} : raw.startsWith("{") ? JSON.parse(raw) : { default: raw };
		}
		const invalid = computed(() => {
			try {
				for (const key of [
					"asset_base_dir",
					"base_dir_alias",
					"web_base_dir",
					"repository_display",
					"win32_client_repo_dir",
					"linux_client_repo_dir"
				]) mapping(key);
				return false;
			} catch {
				return true;
			}
		});
		function presentation(item) {
			try {
				return mapping("repository_display")[item.alias] || {};
			} catch {
				return {};
			}
		}
		function title(item) {
			return presentation(item).title || item.title;
		}
		function update(key, field, value) {
			if (!record.value || invalid.value) return;
			const entries = Object.assign(Object.create(null), mapping(key)), alias = record.value.alias;
			if (field) entries[alias] = {
				...entries[alias],
				[field]: value
			};
			else if (value.trim() || ["asset_base_dir", "base_dir_alias"].includes(key)) entries[alias] = value;
			else delete entries[alias];
			props.server.editSetting("checkin/" + key, Object.keys(entries).length ? JSON.stringify(entries) : "");
		}
		function path(key) {
			try {
				return mapping(key)[record.value?.alias] || "";
			} catch {
				return "";
			}
		}
		function color() {
			const value = presentation(record.value).color;
			return Array.isArray(value) ? "#" + value.map((channel) => channel.toString(16).padStart(2, "0")).join("") : value ? "#" + value.replace(/^#/, "") : "";
		}
		function root(alias) {
			try {
				return mapping("base_dir_alias")[alias] || mapping("asset_base_dir")[alias] || props.repositories?.find((item) => item.alias === alias)?.path || "";
			} catch {
				return props.repositories?.find((item) => item.alias === alias)?.path || "";
			}
		}
		function enabled(alias) {
			return alias !== "plugins" && (props.draft.enabledAliases === null || props.draft.enabledAliases.includes(alias));
		}
		function enable(alias, value) {
			props.draft.enabledAliases = entries.value.filter((item) => item.alias !== "plugins" && (item.alias === alias ? value : enabled(item.alias))).map((item) => item.alias);
			if (!enabled(props.draft.defaultAlias)) props.draft.defaultAlias = props.draft.enabledAliases[0] || "";
		}
		function add() {
			let index = 0;
			while (entries.value.some((item) => item.alias === "custom_" + index)) index++;
			const alias = "custom_" + index;
			selected.value = alias;
			const roots = Object.assign(Object.create(null), mapping("asset_base_dir"));
			roots[alias] = "";
			props.server.editSetting("checkin/asset_base_dir", JSON.stringify(roots));
			const urls = Object.assign(Object.create(null), mapping("web_base_dir"));
			urls[alias] = "/repository/" + alias;
			props.server.editSetting("checkin/web_base_dir", JSON.stringify(urls));
			props.draft.enabledAliases = entries.value.filter((item) => item.alias !== alias && enabled(item.alias)).map((item) => item.alias);
		}
		function remove() {
			const alias = record.value.alias;
			for (const key of [
				"asset_base_dir",
				"base_dir_alias",
				"web_base_dir",
				"repository_display",
				"win32_client_repo_dir",
				"linux_client_repo_dir"
			]) {
				const values = Object.assign(Object.create(null), mapping(key));
				delete values[alias];
				props.server.editSetting("checkin/" + key, Object.keys(values).length ? JSON.stringify(values) : "");
			}
			if (props.draft.enabledAliases) props.draft.enabledAliases = props.draft.enabledAliases.filter((item) => item !== alias);
			if (props.draft.defaultAlias === alias) props.draft.defaultAlias = entries.value.find((item) => enabled(item.alias))?.alias || "";
		}
		const host = ref(null), viewport = ref({
			width: 1e3,
			height: 700
		}), editing = ref(false), advanced = ref(false);
		const canonical = computed(() => entries.value.map((item) => ({
			...item,
			code: item.alias,
			title: title(item) || item.alias,
			active: enabled(item.alias),
			isDefault: props.draft.defaultAlias === item.alias,
			defaultEligible: item.alias !== "plugins",
			custom: item.alias.startsWith("custom_")
		})));
		const model = computed(() => ({
			selected: record.value?.alias,
			record: record.value ? {
				...canonical.value.find((item) => item.alias === record.value.alias),
				title: presentation(record.value).title || title(record.value) || record.value.alias,
				serverPath: root(record.value.alias),
				webPath: path("web_base_dir"),
				windowsPath: path("win32_client_repo_dir"),
				linuxPath: path("linux_client_repo_dir"),
				color: color(),
				statusText: t(record.value.status === "available" ? "Available" : record.value.status === "inaccessible" ? "Folder not found or inaccessible" : "Not checked")
			} : {},
			dirty: props.dirty,
			busy: props.busy,
			editable: !invalid.value,
			notice: props.server?.notice,
			error: props.server?.error || (invalid.value ? t("Fix the repository JSON in Advanced settings before editing these fields.") : ""),
			editing: editing.value,
			style: appearance.theme
		}));
		const scene = computed(() => editor(model.value, viewport.value.width, viewport.value.height, appearance.language));
		const row$2 = (list, record) => row(model.value, record, list.width - 16);
		let observer;
		onMounted(() => {
			observer = observeFrameSizes((entries) => {
				const box = entries.at(-1).contentRect;
				viewport.value = {
					width: box.width,
					height: box.height
				};
			});
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		function dispatch(action) {
			if (action.type === "select") {
				selected.value = action.alias;
				editing.value = true;
			} else if (action.type === "back") editing.value = false;
			else if (action.type === "add") {
				add();
				editing.value = true;
			} else if (action.type === "remove") remove();
			else if (action.type === "advanced") advanced.value = !advanced.value;
			else if (action.type === "check") emit("check", Object.fromEntries(entries.value.filter((item) => item.alias !== "plugins").map((item) => [item.alias, root(item.alias)])));
			else if (action.type === "field") {
				if (action.field === "active") enable(record.value.alias, action.value);
				else if (action.field === "isDefault") props.draft.defaultAlias = action.value ? record.value.alias : entries.value.find((item) => item.alias !== record.value.alias && enabled(item.alias))?.alias || record.value.alias;
				else if (action.field === "title" || action.field === "color") update("repository_display", action.field, action.value);
				else update({
					serverPath: Object.hasOwn(mapping("base_dir_alias"), record.value.alias) ? "base_dir_alias" : "asset_base_dir",
					webPath: "web_base_dir",
					windowsPath: "win32_client_repo_dir",
					linuxPath: "linux_client_repo_dir"
				}[action.field], null, action.value);
			} else if (action.type === "close" || action.type === "save" || action.type === "reset") emit(action.type);
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", _hoisted_1$1, [createBaseVNode("div", {
				ref_key: "host",
				ref: host,
				class: "repository-editor-frame"
			}, [createVNode(_sfc_main$9, {
				scene: scene.value,
				models: { repositories: canonical.value },
				"describe-row": row$2,
				onEvent: dispatch
			}, null, 8, ["scene", "models"])], 512), withDirectives(createBaseVNode("section", _hoisted_2$1, [renderSlot(_ctx.$slots, "default")], 512), [[vShow, advanced.value]])]);
		};
	}
};
//#endregion
//#region src/features/configuration/Configuration.vue
var _hoisted_1 = ["aria-busy"];
var _hoisted_2 = {
	id: "configuration-title",
	hidden: ""
};
var _hoisted_3 = {
	key: 0,
	class: "error configuration-feedback",
	role: "alert"
};
var _hoisted_4 = {
	key: 1,
	class: "notice configuration-feedback",
	role: "status"
};
var _hoisted_5 = {
	key: 5,
	class: "configuration-server-tools"
};
var _hoisted_6 = {
	key: 6,
	class: "muted configuration-feedback"
};
var _hoisted_7 = ["aria-label"];
var _hoisted_8 = ["aria-label"];
var _hoisted_9 = ["aria-label"];
var _sfc_main = {
	__name: "Configuration",
	props: {
		ticket: String,
		project: String,
		login: String,
		canAdminister: Boolean,
		openProject: Function,
		reloadCache: Function
	},
	emits: [
		"session-expired",
		"close",
		"help"
	],
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const groups = {
			server: [
				"Services and workers",
				"Network",
				"Database",
				"Security",
				"Directories and logs"
			],
			repository: ["File repository"],
			tasks: ["Task scheduling"]
		};
		const pages$1 = pages.map((page) => ({
			...page,
			groups: groups[page.id]
		}));
		const host = ref(null), viewport = ref({
			width: 1100,
			height: 700
		});
		let observer;
		onMounted(() => {
			observer = observeFrameSizes((entries) => {
				const box = entries.at(-1).contentRect;
				viewport.value = {
					width: box.width,
					height: box.height
				};
			});
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		const scene = computed(() => describe$3({
			product: "TACTIC STREAM",
			page: page.value,
			pages: pages$1,
			dirty: dirty.value,
			currentDirty: pageDirty(page.value),
			dirtyPages: pages$1.filter((item) => pageDirty(item.id)).map((item) => item.id),
			canReset: true,
			busy: busy.value
		}, viewport.value.width, viewport.value.height, appearance.language));
		const pageStyle = computed(() => Object.fromEntries(Object.entries(scene.value.pageBounds).map(([key, value]) => [key === "x" ? "left" : key === "y" ? "top" : key, value + "px"])));
		function dispatch(action) {
			if (action.type === "page") selectPage(action.value);
			else if (action.type === "reset") reset();
			else if (action.type === "apply") apply();
			else if (action.type === "save") apply({ all: true });
			else if (action.type === "close") cancel();
			else if (action.type === "help") emit("help", current.value.help);
		}
		let savedPage;
		try {
			savedPage = localStorage.getItem("tactic_stream.configuration.page");
		} catch {}
		const page = ref(pages$1.some((item) => item.id === savedPage) ? savedPage : "server");
		const origin = location.origin;
		const current = computed(() => pages$1.find((item) => item.id === page.value));
		const server = ref(null), error = ref(""), notice = ref(""), saving = ref(false), clearing = ref(false), confirmClose = ref(null), confirmClear = ref(null);
		const repositoryEditor = ref(null), repositories = ref(null);
		const cacheScope = ref("server");
		const clone = (value) => JSON.parse(JSON.stringify(value));
		const drafts = reactive(clone(preferences)), networkDraft = reactive(clone(networkSettings)), debugDraft = reactive(clone(debugSettings));
		const appearanceBaseline = ref(JSON.stringify(appearance)), networkBaseline = ref(JSON.stringify(networkSettings)), debugBaseline = ref(JSON.stringify(debugSettings)), baselines = ref(clone(preferences));
		const busy = computed(() => saving.value || clearing.value || !!server.value?.loading || !!server.value?.saving);
		function pageDirty(id) {
			if (id === "appearance") return JSON.stringify(appearance) !== appearanceBaseline.value;
			const settingsDirty = id in drafts && JSON.stringify(drafts[id]) !== JSON.stringify(baselines.value[id]);
			const groups = pages$1.find((item) => item.id === id)?.groups || [];
			return settingsDirty || id === "server" && JSON.stringify(networkDraft) !== networkBaseline.value || id === "global" && JSON.stringify(debugDraft) !== debugBaseline.value || (server.value?.configuration?.groups || []).some((group) => groups.includes(group.title) && server.value.groupChanged(group));
		}
		const dirty = computed(() => pages$1.some((item) => pageDirty(item.id)));
		const serverPages = computed(() => pages$1.filter((item) => item.groups).map((item) => item.id));
		const currentGroups = computed(() => current.value.groups || []);
		watch(page, async (value) => {
			try {
				localStorage.setItem("tactic_stream.configuration.page", value);
			} catch {}
			await nextTick();
			if (server.value && currentGroups.value.length && !currentGroups.value.includes(server.value.activeGroup)) {
				server.value.activeGroup = currentGroups.value[0];
				server.value.search = "";
			}
		});
		const pageValues = computed(() => {
			if (page.value === "server") return {
				serverUrl: origin,
				login: props.login,
				serverUpdateMode: networkDraft.updateMode,
				serverUpdateInterval: networkDraft.pollInterval,
				serverUpdateBatchDelay: networkDraft.batchDelay
			};
			if (page.value === "appearance") return {
				...appearance,
				darkTheme: effectiveColorMode.value === "dark",
				themeStyle: appearance.theme,
				lightAccent: appearance.themeAccents[appearance.theme].light,
				darkAccent: appearance.themeAccents[appearance.theme].dark
			};
			const values = { ...drafts[page.value] };
			if (page.value === "global") for (const level of [
				"LOG",
				"INFO",
				"WARNING",
				"MISSING",
				"EXCEPTION",
				"ERROR",
				"CRITICAL",
				"API"
			]) values["debug_" + level] = debugDraft.recordingLevels.includes(level);
			return values;
		});
		const pageOptions = computed(() => ({
			themeStyle: themes,
			language: languages,
			iconSet: iconSets,
			mode: colorModes,
			defaultViewMode: views,
			viewMode: [{
				value: "table",
				label: "Table"
			}, {
				value: "gantt",
				label: "Gantt"
			}],
			sortMode: [
				"due",
				"recent",
				"process",
				"user",
				"status",
				"object",
				"search_type",
				"project",
				"priority",
				"milestone",
				"supervisor"
			].map((value) => ({
				value,
				label: {
					due: "Deadline",
					recent: "Recently changed",
					user: "Assignee",
					search_type: "Search Type"
				}[value] || value[0].toUpperCase() + value.slice(1)
			})),
			groupMode: [
				"none",
				"process",
				"user",
				"status",
				"object"
			].map((value) => ({
				value,
				label: {
					none: "No grouping",
					user: "Assignee"
				}[value] || value[0].toUpperCase() + value.slice(1)
			})),
			serverUpdateMode: updateModes,
			serverUpdateInterval: updateIntervals,
			serverUpdateBatchDelay: updateBatchDelays
		}));
		function editField({ field, value }) {
			if (page.value === "server") networkDraft[{
				serverUpdateMode: "updateMode",
				serverUpdateInterval: "pollInterval",
				serverUpdateBatchDelay: "batchDelay"
			}[field]] = value;
			else if (page.value === "appearance") {
				if (field === "darkTheme") appearance.mode = value ? "dark" : "light";
				else if (field === "themeStyle") appearance.theme = value;
				else if (["lightAccent", "darkAccent"].includes(field)) appearance.themeAccents[appearance.theme][field === "lightAccent" ? "light" : "dark"] = value;
				else appearance[field] = value;
			} else if (field.startsWith("debug_")) {
				const level = field.slice(6);
				debugDraft.recordingLevels = value ? [.../* @__PURE__ */ new Set([...debugDraft.recordingLevels, level])] : debugDraft.recordingLevels.filter((item) => item !== level);
			} else drafts[page.value][field] = value;
		}
		function settingsAction(action) {
			if (action.type === "clearTabs" || action.type === "clearData") {
				cacheScope.value = action.type === "clearTabs" ? "tabs" : "server";
				confirmClear.value.showModal();
			}
		}
		function selectPage(value) {
			error.value = "";
			notice.value = "";
			page.value = value;
		}
		function begin() {
			configurationPreview.value = true;
			appearanceBaseline.value = JSON.stringify(appearance);
			networkBaseline.value = JSON.stringify(networkSettings);
			debugBaseline.value = JSON.stringify(debugSettings);
			baselines.value = clone(preferences);
			Object.assign(drafts, clone(preferences));
			Object.assign(networkDraft, clone(networkSettings));
			Object.assign(debugDraft, clone(debugSettings));
			error.value = "";
			notice.value = "";
			if (server.value && !server.value.hasChanges) server.value.load();
			repositories.value?.load();
			nextTick(() => {
				if (server.value && currentGroups.value.length) server.value.activeGroup = currentGroups.value[0];
			});
		}
		function restore(id) {
			if (id === "appearance") Object.assign(appearance, JSON.parse(appearanceBaseline.value));
			if (id in drafts) drafts[id] = clone(baselines.value[id]);
			if (id === "server") Object.assign(networkDraft, JSON.parse(networkBaseline.value));
			if (id === "global") Object.assign(debugDraft, JSON.parse(debugBaseline.value));
			const groups = pages$1.find((item) => item.id === id)?.groups;
			if (groups && server.value?.configuration) server.value.resetDraft(groups);
		}
		function reset() {
			if (busy.value) return;
			restore(page.value);
			error.value = "";
			notice.value = "";
			if (page.value === "repository") repositories.value?.load();
		}
		function closeRepository() {
			repositoryEditor.value.close();
			repositories.value?.load();
		}
		function discard() {
			if (busy.value) return;
			for (const item of pages$1) restore(item.id);
			confirmClose.value?.close();
			emit("close");
		}
		function cancel() {
			if (busy.value) return;
			if (dirty.value) confirmClose.value.showModal();
			else emit("close");
		}
		function persist(entries) {
			const previous = entries.map(([key]) => [key, localStorage.getItem(key)]);
			try {
				for (const [key, value] of entries) localStorage.setItem(key, JSON.stringify(value));
			} catch (failure) {
				for (const [key, value] of previous) try {
					if (value === null) localStorage.removeItem(key);
					else localStorage.setItem(key, value);
				} catch {}
				throw failure;
			}
		}
		async function applyPage(id) {
			const definition = pages$1.find((item) => item.id === id);
			if (id === "checkin" && (!Number.isInteger(drafts.checkin.displayLimit) || drafts.checkin.displayLimit < 1 || drafts.checkin.displayLimit > 500)) {
				page.value = id;
				error.value = "Result limit must be an integer from 1 to 500.";
				return false;
			}
			if (id === "tasks" && drafts.tasks.columns.some((column) => !Number.isInteger(column.width) || column.width < 40 || column.width > 480)) {
				page.value = id;
				error.value = "Column width must be an integer from 40 to 480.";
				return false;
			}
			if (id === "repository" && (!drafts.repository.defaultAlias || drafts.repository.enabledAliases && !drafts.repository.enabledAliases.includes(drafts.repository.defaultAlias))) {
				page.value = id;
				error.value = "Enable at least one repository and choose its default.";
				return false;
			}
			if (id === "repository") try {
				if (!["asset_base_dir", "base_dir_alias"].flatMap((key) => {
					const raw = server.value?.draft["checkin/" + key] || "";
					return raw.startsWith("{") ? Object.keys(JSON.parse(raw)) : ["default"];
				}).includes(drafts.repository.defaultAlias)) throw new Error();
			} catch {
				page.value = id;
				error.value = "Enable at least one repository and choose its default.";
				return false;
			}
			if (definition.groups && server.value?.hasChanges && !await server.value.save(definition.groups)) {
				page.value = pages$1.find((item) => item.groups?.includes(server.value.activeGroup))?.id || id;
				if (page.value === "repository") {
					await nextTick();
					if (!repositoryEditor.value.open) repositoryEditor.value.show();
				}
				return false;
			}
			try {
				if (id === "appearance") {
					saveAppearance();
					appearanceBaseline.value = JSON.stringify(appearance);
				}
				if (id === "server") {
					persist([["tactic_stream.network", networkDraft]]);
					Object.assign(networkSettings, clone(networkDraft));
					networkBaseline.value = JSON.stringify(networkDraft);
				}
				if (id === "global") {
					const next = normalizePreferences({
						...preferences,
						global: drafts.global
					});
					persist([["tactic_stream.preferences", next], ["tactic_stream.debug_log", debugDraft]]);
					Object.assign(preferences.global, next.global);
					Object.assign(debugSettings, clone(debugDraft));
					debugBaseline.value = JSON.stringify(debugDraft);
					baselines.value.global = clone(drafts.global);
				} else if (id in drafts) {
					savePreferencePage(id, drafts[id]);
					drafts[id] = clone(preferences[id]);
					baselines.value[id] = clone(preferences[id]);
				}
				if (id === "repository") await repositories.value?.load();
				return true;
			} catch {
				page.value = id;
				error.value = "Browser settings could not be saved. Check browser storage permissions and free space.";
				return false;
			}
		}
		async function apply({ all = false, close = false } = {}) {
			if (busy.value) return;
			error.value = "";
			notice.value = "";
			saving.value = true;
			try {
				for (const id of all ? pages$1.map((item) => item.id) : [page.value]) if (!await applyPage(id)) return;
				notice.value = server.value?.configuration?.restart_required ? "Saved to XML. Restart the backend to apply these settings." : "Configuration applied";
				if (close) {
					confirmClose.value?.close();
					emit("close");
				}
			} finally {
				saving.value = false;
			}
		}
		async function applyRepository() {
			if (busy.value) return;
			saving.value = true;
			try {
				if (await applyPage("repository")) notice.value = "Configuration applied";
			} finally {
				saving.value = false;
			}
		}
		async function clearCache() {
			confirmClear.value.close();
			clearing.value = true;
			error.value = "";
			notice.value = "";
			try {
				if (await props.reloadCache(cacheScope.value) === false) throw new Error();
				notice.value = cacheScope.value === "tabs" ? "Tabs cache cleared" : "Cache reloaded";
			} catch {
				error.value = "Cached server data could not be refreshed.";
			} finally {
				clearing.value = false;
			}
		}
		const confirmationWidth = computed(() => Math.max(1, Math.min(430, viewport.value.width - 32)));
		const closeScene = computed(() => confirmation({
			kind: "close",
			busy: busy.value
		}, confirmationWidth.value, 248, appearance.language));
		const clearScene = computed(() => confirmation({
			kind: "clear",
			scope: cacheScope.value,
			busy: busy.value
		}, confirmationWidth.value, 220, appearance.language));
		function confirmationAction(action) {
			confirmClose.value.close();
			if (action.type === "discard") discard();
			else if (action.type === "save") apply({
				all: true,
				close: true
			});
		}
		function beforeUnload(event) {
			if (dirty.value || busy.value) {
				event.preventDefault();
				event.returnValue = "";
			}
		}
		onActivated(() => {
			begin();
			window.addEventListener("beforeunload", beforeUnload);
		});
		onDeactivated(() => {
			Object.assign(appearance, JSON.parse(appearanceBaseline.value));
			configurationPreview.value = false;
			window.removeEventListener("beforeunload", beforeUnload);
		});
		onBeforeUnmount(() => {
			Object.assign(appearance, JSON.parse(appearanceBaseline.value));
			configurationPreview.value = false;
			window.removeEventListener("beforeunload", beforeUnload);
		});
		__expose({
			cancel,
			dirty
		});
		return (_ctx, _cache) => {
			const _directive_window = resolveDirective("window");
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "configuration configuration-native configuration-frame",
				"aria-busy": busy.value
			}, [
				createBaseVNode("span", _hoisted_2, toDisplayString(unref(t)("Configuration")), 1),
				createVNode(_sfc_main$9, {
					scene: scene.value,
					onEvent: dispatch
				}, null, 8, ["scene"]),
				createBaseVNode("div", {
					class: "configuration-pages",
					style: normalizeStyle(pageStyle.value)
				}, [
					error.value ? (openBlock(), createElementBlock("p", _hoisted_3, toDisplayString(unref(t)(error.value)), 1)) : createCommentVNode("", true),
					notice.value ? (openBlock(), createElementBlock("p", _hoisted_4, toDisplayString(unref(t)(notice.value)), 1)) : createCommentVNode("", true),
					[
						"server",
						"appearance",
						"checkin",
						"global",
						"cache",
						"tasks"
					].includes(page.value) ? (openBlock(), createBlock(_sfc_main$6, {
						key: 2,
						page: page.value,
						values: pageValues.value,
						options: pageOptions.value,
						busy: busy.value,
						natural: ["server", "tasks"].includes(page.value) && __props.canAdminister,
						onField: editField,
						onColumns: _cache[0] || (_cache[0] = ($event) => drafts.tasks.columns = $event),
						onAction: settingsAction
					}, null, 8, [
						"page",
						"values",
						"options",
						"busy",
						"natural"
					])) : createCommentVNode("", true),
					page.value === "project" ? (openBlock(), createBlock(_sfc_main$3, {
						key: 3,
						ticket: __props.ticket,
						project: __props.project,
						"can-administer": __props.canAdminister,
						"open-project": __props.openProject,
						onHelp: _cache[1] || (_cache[1] = ($event) => emit("help", $event))
					}, null, 8, [
						"ticket",
						"project",
						"can-administer",
						"open-project"
					])) : createCommentVNode("", true),
					page.value === "repository" && __props.canAdminister ? (openBlock(), createBlock(_sfc_main$2, {
						key: 4,
						ref_key: "repositories",
						ref: repositories,
						ticket: __props.ticket,
						busy: busy.value,
						onEdit: _cache[2] || (_cache[2] = ($event) => repositoryEditor.value.show()),
						onSessionExpired: _cache[3] || (_cache[3] = ($event) => emit("session-expired"))
					}, null, 8, ["ticket", "busy"])) : createCommentVNode("", true),
					__props.canAdminister && ["server", "tasks"].includes(page.value) && server.value?.configuration ? (openBlock(), createElementBlock("section", _hoisted_5, [createVNode(_sfc_main$11, {
						modelValue: server.value.activeGroup,
						"onUpdate:modelValue": _cache[4] || (_cache[4] = ($event) => server.value.activeGroup = $event),
						options: currentGroups.value.map((title) => ({
							value: title,
							label: title
						})),
						label: "Server settings section"
					}, null, 8, ["modelValue", "options"]), createVNode(AppSearchField_default, {
						modelValue: server.value.search,
						"onUpdate:modelValue": _cache[5] || (_cache[5] = ($event) => server.value.search = $event),
						label: "Find a setting",
						placeholder: "Find a setting…"
					}, null, 8, ["modelValue"])])) : createCommentVNode("", true),
					(openBlock(), createBlock(Teleport, {
						defer: "",
						to: "#configuration-repository-editor-body",
						disabled: page.value !== "repository"
					}, [__props.canAdminister ? withDirectives((openBlock(), createBlock(ServerConfiguration_default, {
						key: 0,
						ref_key: "server",
						ref: server,
						"group-titles": currentGroups.value,
						ticket: __props.ticket,
						"show-details": "",
						onSessionExpired: _cache[6] || (_cache[6] = ($event) => emit("session-expired"))
					}, null, 8, ["group-titles", "ticket"])), [[vShow, serverPages.value.includes(page.value)]]) : createCommentVNode("", true)], 8, ["disabled"])),
					!__props.canAdminister && page.value === "repository" ? (openBlock(), createElementBlock("p", _hoisted_6, toDisplayString(unref(t)("Repository configuration requires administrator access.")), 1)) : createCommentVNode("", true)
				], 4),
				withDirectives((openBlock(), createElementBlock("dialog", {
					ref_key: "repositoryEditor",
					ref: repositoryEditor,
					class: "record-dialog configuration-repository-editor",
					"aria-label": unref(t)("Repository Editor")
				}, [createVNode(_sfc_main$1, {
					server: server.value,
					draft: drafts.repository,
					repositories: repositories.value?.records || [],
					busy: busy.value || repositories.value?.checking,
					dirty: pageDirty("repository"),
					onCheck: _cache[7] || (_cache[7] = ($event) => repositories.value.load("check", $event)),
					onClose: closeRepository,
					onReset: _cache[8] || (_cache[8] = ($event) => restore("repository")),
					onSave: applyRepository
				}, {
					default: withCtx(() => [..._cache[10] || (_cache[10] = [createBaseVNode("div", { id: "configuration-repository-editor-body" }, null, -1)])]),
					_: 1
				}, 8, [
					"server",
					"draft",
					"repositories",
					"busy",
					"dirty"
				])], 8, _hoisted_7)), [[_directive_window, { type: "window" }]]),
				createBaseVNode("dialog", {
					ref_key: "confirmClose",
					ref: confirmClose,
					class: "record-dialog configuration-confirmation",
					style: normalizeStyle({ width: confirmationWidth.value + "px" }),
					"aria-label": unref(t)("Unsaved changes")
				}, [createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)("Unsaved changes")), 1)]), createVNode(_sfc_main$9, {
					scene: closeScene.value,
					style: { "height": "248px" },
					onEvent: confirmationAction
				}, null, 8, ["scene"])], 12, _hoisted_8),
				createBaseVNode("dialog", {
					ref_key: "confirmClear",
					ref: confirmClear,
					class: "record-dialog configuration-confirmation",
					style: normalizeStyle({ width: confirmationWidth.value + "px" }),
					"aria-label": unref(t)(cacheScope.value === "tabs" ? "Clear saved branch expansion?" : "Clear cached server data?")
				}, [createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)(cacheScope.value === "tabs" ? "Clear saved branch expansion?" : "Clear cached server data?")), 1)]), createVNode(_sfc_main$9, {
					scene: clearScene.value,
					style: { "height": "220px" },
					onEvent: _cache[9] || (_cache[9] = ($event) => $event.type === "accept" ? clearCache() : confirmClear.value.close())
				}, null, 8, ["scene"])], 12, _hoisted_9)
			], 8, _hoisted_1);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=Configuration.js.map