import { A as onMounted, F as resolveComponent, M as openBlock, N as renderList, O as onBeforeUnmount, X as ref, _ as createElementBlock, b as createVNode, g as createCommentVNode, m as createBaseVNode, nt as normalizeStyle, p as computed, rt as toDisplayString, tt as normalizeClass, u as Fragment, y as createTextVNode } from "./vue.js";
import { F as accentPresets, a as _sfc_main$2, o as t, s as appearance, t as _sfc_main$3, z as _plugin_vue_export_helper_default } from "./AppButton.js";
import { It as randomUuid, O as restartServer, R as serverConfiguration, j as saveServerConfiguration, z as serverRuntime } from "./index.js";
import { G as node, H as label, K as rect, R as observeFrameSizes, S as translate, V as button, t as _sfc_main$4 } from "./FrameView.js";
import { n as _sfc_main$5 } from "./AppearanceControls.js";
import { _ as timestampFullLabel } from "./admin.document.js";
import { t as describe$1 } from "./confirmation.ui.js";
import { f as change, g as fieldsFor, h as editColumn, m as describe$2 } from "./App.js";
//#region src/features/configuration/FrameSettings.vue
var _sfc_main$1 = {
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
			component: _sfc_main$5,
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
			}, [createVNode(_sfc_main$4, {
				scene: scene.value,
				views: views.value,
				onEvent: dispatch
			}, null, 8, ["scene", "views"])], 6);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/features/configuration/server_control.ui.mjs
function describe(model, width, language) {
	const tr = (text) => translate(text, language);
	const compact = width < 480;
	const height = compact ? 344 : 250;
	if (model.confirm) {
		const scene = describe$1({
			message: tr("Restart TACTIC Stream? Connections and running operations may be interrupted while saved settings are applied. Unsaved changes will not be applied."),
			accept: "Restart TACTIC Stream",
			reject: "Cancel",
			busy: model.busy,
			acceptId: "serverRestartAccept",
			rejectId: "serverRestartCancel"
		}, width, height, language);
		return Object.assign(scene, { height });
	}
	const runtime = model.runtime || {};
	const enabled = !model.busy && !model.restarting;
	const nodes = [
		node("Box", "serverControlSurface", rect(0, 0, width, height), {
			color: "panel",
			border: "outline",
			borderWidth: 1,
			radius: 6
		}),
		label("serverControlTitle", rect(12, 12, width - 112, 24), tr("Server processes"), { bold: true }),
		button("serverControlDiscard", rect(width - 88, 8, 36, 36), tr("Discard changes"), "undo", { type: "discard" }, enabled && model.dirty, { iconOnly: true }),
		button("serverControlRefresh", rect(width - 48, 8, 36, 36), tr("Refresh"), "refresh", { type: "refresh" }, enabled && !model.dirty, { iconOnly: true }),
		label("serverWorkerLabel", rect(12, 50, width - 24, 22), tr("Web workers")),
		node("Field", "serverWorkerCount", rect(12, 76, Math.min(144, width - 24), 38), {
			text: String(model.workers || ""),
			label: tr("Web workers"),
			enabled,
			inputMode: "numeric",
			action: { type: "workers" }
		}),
		label("serverRunningWorkers", rect(compact ? 12 : 172, compact ? 124 : 82, compact ? width - 24 : width - 184, 44), tr("Running web workers") + ": " + (runtime.web_workers ?? "—"), {
			wrap: true,
			color: "secondaryText"
		}),
		label("serverControlNotice", rect(12, compact ? 176 : 132, width - 24, compact ? 64 : 54), tr(model.error || (model.restarting ? "Restarting TACTIC Stream…" : model.dirty ? "Save changes before restarting." : model.notice) || (!runtime.available ? runtime.reason || "The server monitor is unavailable or outdated." : "Saved settings are applied only after restarting the server.")) || "", {
			wrap: true,
			color: model.error ? "red" : "secondaryText",
			role: model.error ? "alert" : "status"
		})
	];
	const buttonWidth = compact ? width - 24 : Math.min(220, (width - 32) / 2);
	nodes.push(button("serverWorkersSave", rect(12, height - (compact ? 88 : 50), buttonWidth, 36), tr("Save"), "save", { type: "save" }, enabled && model.dirty));
	nodes.push(button("serverRestart", rect(compact ? 12 : 20 + buttonWidth, height - 50, buttonWidth, 36), tr("Restart TACTIC Stream"), "refresh", { type: "restart" }, enabled && !model.dirty && runtime.available && runtime.state === "running"));
	return {
		nodes,
		height
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/configuration/server.ui.mjs
function fields(model, language) {
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
var _sfc_main = {
	components: {
		FrameSettings: _sfc_main$1,
		FrameView: _sfc_main$4,
		AppIcon: _sfc_main$2,
		AppButton: _sfc_main$3
	},
	props: {
		ticket: {
			type: String,
			required: true
		},
		showDetails: Boolean,
		groupTitles: Array,
		workersOnly: Boolean
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
			generation: 0,
			restarting: false,
			restartConfirm: false,
			controlWidth: 640
		};
	},
	computed: {
		dirty() {
			return this.hasChanges;
		},
		busy() {
			return this.loading || this.saving || this.restarting;
		},
		showControl() {
			return !this.search && this.groups.some((group) => group.title === "Services and workers");
		},
		controlScene() {
			return describe({
				workers: this.draft["services/process_count"],
				runtime: this.configuration?.runtime,
				dirty: this.hasChanges,
				busy: this.loading || this.saving,
				restarting: this.restarting,
				confirm: this.restartConfirm,
				notice: this.notice,
				error: this.error
			}, this.controlWidth, appearance.language);
		},
		fields() {
			return fields({
				groups: this.groups.map((group) => ({
					...group,
					settings: group.settings.filter((setting) => !this.showControl || setting.path !== "services/process_count")
				})),
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
		this.restarting = this.restartConfirm = false;
		this.error = this.notice = this.clientsError = "";
	} },
	mounted() {
		window.addEventListener("beforeunload", this.beforeUnload);
		this.load();
	},
	beforeUnmount() {
		this.generation++;
		this.controlObserver?.disconnect();
		window.removeEventListener("beforeunload", this.beforeUnload);
	},
	updated() {
		const element = this.$refs.serverControl;
		if (element === this.controlElement) return;
		this.controlObserver?.disconnect();
		this.controlElement = element;
		if (element) {
			this.controlObserver = observeFrameSizes((entries) => {
				this.controlWidth = entries.at(-1).contentRect.width;
			});
			this.controlObserver.observe(element);
		}
	},
	methods: {
		t,
		canLeave() {
			return !this.hasChanges && !this.busy;
		},
		async controlAction(action) {
			if (this.restarting || this.saving || this.loading) return;
			if (action.type === "workers") this.editSetting("services/process_count", action.value);
			else if (action.type === "save") await this.save();
			else if (action.type === "discard") {
				this.resetDraft();
				await this.load();
			} else if (action.type === "refresh" && !this.hasChanges) await this.load();
			else if (action.type === "restart" && !this.hasChanges) this.restartConfirm = true;
			else if (action.type === "reject") this.restartConfirm = false;
			else if (action.type === "accept" && !this.hasChanges) await this.restart();
		},
		async restart() {
			const generation = this.generation;
			const runtime = this.configuration.runtime;
			const id = randomUuid();
			this.restartConfirm = false;
			this.restarting = true;
			this.error = this.notice = "";
			try {
				try {
					await restartServer(this.ticket, this.configuration.revision, runtime.instance_id, id);
				} catch (error) {
					if (!(error instanceof TypeError)) throw error;
				}
				const deadline = performance.now() + 9e4;
				while (generation === this.generation && performance.now() < deadline) {
					try {
						const state = await serverRuntime(this.ticket);
						if (state.restart_id === id && state.restart_error) throw Error(state.restart_error);
						if (state.restart_id === id && state.instance_id !== runtime.instance_id && state.state === "running") {
							this.configuration = await serverConfiguration(this.ticket);
							this.resetDraft();
							this.notice = "TACTIC Stream restarted";
							return;
						}
					} catch (error) {
						if (!(error instanceof TypeError) && error.name !== "TimeoutError" && error.name !== "AbortError") throw error;
					}
					await new Promise((resolve) => setTimeout(resolve, 500));
				}
				if (generation === this.generation) throw Error("The server has not returned yet. Reconnect and check its status.");
			} catch (error) {
				if (generation === this.generation) {
					if (error.code === "authentication_failed") this.$emit("session-expired");
					this.error = error.message;
				}
			} finally {
				if (generation === this.generation) this.restarting = false;
			}
		},
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
			if (this.loading || this.saving || this.restarting) return false;
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
var _hoisted_1 = ["aria-busy"];
var _hoisted_2 = {
	key: 0,
	class: "error",
	role: "alert"
};
var _hoisted_3 = { key: 0 };
var _hoisted_4 = {
	key: 1,
	class: "notice",
	role: "status"
};
var _hoisted_5 = {
	key: 2,
	class: "muted",
	role: "status"
};
var _hoisted_6 = {
	key: 1,
	class: "settings-section event-clients"
};
var _hoisted_7 = { class: "muted" };
var _hoisted_8 = {
	key: 0,
	class: "error",
	role: "alert"
};
var _hoisted_9 = { class: "event-clients-scroll" };
var _hoisted_10 = { key: 0 };
var _hoisted_11 = {
	key: 1,
	class: "muted"
};
var _hoisted_12 = {
	key: 2,
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
var _hoisted_18 = {
	key: 3,
	class: "configuration-groups"
};
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
	const _component_FrameView = resolveComponent("FrameView");
	const _component_AppButton = resolveComponent("AppButton");
	const _component_AppIcon = resolveComponent("AppIcon");
	const _component_FrameSettings = resolveComponent("FrameSettings");
	return openBlock(), createElementBlock("section", {
		class: "content server-configuration",
		"aria-busy": $data.loading || $data.saving
	}, [
		$data.error && (!$props.workersOnly || !$data.configuration) ? (openBlock(), createElementBlock("p", _hoisted_2, [$options.failedSetting ? (openBlock(), createElementBlock("strong", _hoisted_3, toDisplayString($options.t($options.failedSetting)) + ": ", 1)) : createCommentVNode("", true), createTextVNode(toDisplayString($options.t($data.error)), 1)])) : createCommentVNode("", true),
		$data.notice && !$options.hasChanges && !$props.workersOnly ? (openBlock(), createElementBlock("p", _hoisted_4, toDisplayString($options.t($data.notice)), 1)) : createCommentVNode("", true),
		$data.loading ? (openBlock(), createElementBlock("p", _hoisted_5, toDisplayString($options.t("Loading data…")), 1)) : createCommentVNode("", true),
		$data.configuration ? (openBlock(), createElementBlock(Fragment, { key: 3 }, [
			$options.showControl ? (openBlock(), createElementBlock("div", {
				key: 0,
				ref: "serverControl",
				class: "server-process-controls",
				style: normalizeStyle({
					height: $options.controlScene.height + "px",
					position: "relative"
				})
			}, [createVNode(_component_FrameView, {
				scene: $options.controlScene,
				onEvent: $options.controlAction
			}, null, 8, ["scene", "onEvent"])], 4)) : createCommentVNode("", true),
			!$props.workersOnly && $data.activeGroup === "Services and workers" && !$data.search ? (openBlock(), createElementBlock("section", _hoisted_6, [
				createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString($options.t("SSE connections")) + " · " + toDisplayString($data.configuration.event_clients?.length || 0), 1), createVNode(_component_AppButton, {
					icon: "refresh",
					label: "Refresh connections",
					disabled: $data.clientsLoading || $data.loading || $data.saving,
					onClick: $options.refreshClients
				}, null, 8, ["disabled", "onClick"])]),
				createBaseVNode("p", _hoisted_7, toDisplayString($options.t("Open SSE connections across all web workers. This is a connection list, not user presence. Refresh to update the snapshot; closed connections disappear within the collection interval, crashed workers within 45 seconds.")), 1),
				$data.clientsError ? (openBlock(), createElementBlock("p", _hoisted_8, toDisplayString($options.t($data.clientsError)), 1)) : createCommentVNode("", true),
				createBaseVNode("div", _hoisted_9, [$data.configuration.event_clients?.length ? (openBlock(), createElementBlock("table", _hoisted_10, [createBaseVNode("thead", null, [createBaseVNode("tr", null, [
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
			$props.showDetails && !$props.workersOnly ? (openBlock(), createElementBlock("details", _hoisted_12, [
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
			!$props.workersOnly ? (openBlock(), createElementBlock("div", _hoisted_18, [
				createVNode(_component_FrameSettings, {
					fields: $options.fields,
					values: $options.frameValues,
					busy: $data.loading || $data.saving || $data.restarting,
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
			])) : createCommentVNode("", true)
		], 64)) : createCommentVNode("", true)
	], 8, _hoisted_1);
}
var ServerConfiguration_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { ServerConfiguration_default as default, _sfc_main$1 as t };

//# sourceMappingURL=ServerConfiguration.js.map