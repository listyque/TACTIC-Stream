import { A as onDeactivated, B as useId, D as nextTick, F as renderSlot, G as withCtx, H as watch, I as resolveComponent, K as withDirectives, L as resolveDirective, N as openBlock, O as onActivated, P as renderList, X as ref, Y as reactive, _ as createCommentVNode, b as createTextVNode, c as vShow, d as Fragment, et as unref, g as createBlock, h as createBaseVNode, j as onMounted, k as onBeforeUnmount, m as computed, p as Teleport, rt as toDisplayString, s as vModelText, tt as normalizeClass, v as createElementBlock, x as createVNode } from "./vue.js";
import { E as appearance, F as savePreferencePage, H as _plugin_vue_export_helper_default, M as configurationPreview, N as normalizePreferences, P as preferences, T as t, c as _sfc_main$8, d as debugSettings, g as levels, i as _sfc_main$9, j as saveAppearance, n as mobile } from "./index.js";
import { B as serverConfiguration, M as rpc, N as saveServerConfiguration, T as projectCatalog, u as _sfc_main$10 } from "./clipboard.js";
import { t as _sfc_main$11 } from "./AppSwitch.js";
import { t as _sfc_main$12 } from "./AppSelect.js";
import { t as _sfc_main$13 } from "./SettingRow.js";
import { t as RecordForm_default } from "./RecordForm.js";
import { t as _sfc_main$14 } from "./AppTextField.js";
import { t as _sfc_main$15 } from "./AppColorInput.js";
import { t as _sfc_main$16 } from "./AppMenu.js";
import { t as _sfc_main$17 } from "./AppCheckbox.js";
import { f as timestampFullLabel } from "./activity.js";
import { t as AppSearchField_default } from "./AppSearchField.js";
import { H as _sfc_main$18, V as resultViews, a as updateModes, d as ProjectChooser_default, f as ProjectCreation_default, i as updateIntervals, n as networkSettings, r as updateBatchDelays } from "./App.js";
//#region src/features/configuration/ServerConfiguration.vue
var _sfc_main$7 = {
	components: {
		AppSwitch: _sfc_main$11,
		AppSelect: _sfc_main$12,
		SettingRow: _sfc_main$13,
		AppIcon: _sfc_main$8,
		AppButton: _sfc_main$9
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
			baseline: {}
		};
	},
	computed: {
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
	mounted() {
		window.addEventListener("beforeunload", this.beforeUnload);
		this.load();
	},
	beforeUnmount() {
		window.removeEventListener("beforeunload", this.beforeUnload);
	},
	methods: {
		t,
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
			this.loading = true;
			this.error = "";
			this.notice = "";
			try {
				this.configuration = await serverConfiguration(this.ticket);
				this.resetDraft();
			} catch (error) {
				if (error.code === "authentication_failed") this.$emit("session-expired");
				this.error = error instanceof TypeError ? "Unable to reach the server." : error.message;
			} finally {
				this.loading = false;
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
			this.clientsLoading = true;
			this.clientsError = "";
			try {
				const result = await serverConfiguration(this.ticket);
				this.configuration.event_clients = result.event_clients;
			} catch (error) {
				if (error.code === "authentication_failed") this.$emit("session-expired");
				this.clientsError = error instanceof TypeError ? "Unable to reach the server." : error.message;
			} finally {
				this.clientsLoading = false;
			}
		},
		connectedTime(value) {
			return timestampFullLabel(new Date(value).toISOString());
		},
		async save(groupTitles) {
			if (this.loading || this.saving) return false;
			const changes = Object.fromEntries(Object.entries(this.changes).filter(([path]) => !groupTitles || this.configuration.groups.some((group) => groupTitles.includes(group.title) && group.settings.some((setting) => setting.path === path))));
			if (!Object.keys(changes).length) return true;
			const pending = { ...this.changes };
			this.saving = true;
			this.error = "";
			this.errorField = null;
			try {
				this.configuration = await saveServerConfiguration(this.ticket, changes, this.configuration.revision);
				this.resetDraft();
				for (const [path, value] of Object.entries(pending)) if (!Object.hasOwn(changes, path)) this.draft[path] = value;
				this.notice = this.configuration.restart_required ? "Saved to XML. Restart the backend to apply these settings." : this.configuration.saved ? "Saved to XML. New requests use the updated settings." : "No configuration changes were needed.";
				return true;
			} catch (error) {
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
				this.saving = false;
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
var _hoisted_1$7 = ["aria-busy"];
var _hoisted_2$7 = {
	key: 0,
	class: "error",
	role: "alert"
};
var _hoisted_3$7 = { key: 0 };
var _hoisted_4$6 = {
	key: 1,
	class: "notice",
	role: "status"
};
var _hoisted_5$5 = {
	key: 2,
	class: "muted",
	role: "status"
};
var _hoisted_6$5 = {
	key: 0,
	class: "settings-section event-clients"
};
var _hoisted_7$5 = { class: "muted" };
var _hoisted_8$5 = {
	key: 0,
	class: "error",
	role: "alert"
};
var _hoisted_9$5 = { class: "event-clients-scroll" };
var _hoisted_10$5 = { key: 0 };
var _hoisted_11$3 = {
	key: 1,
	class: "muted"
};
var _hoisted_12$1 = {
	key: 1,
	class: "configuration-source"
};
var _hoisted_13$1 = ["disabled"];
var _hoisted_14$1 = { class: "muted" };
var _hoisted_15$1 = { class: "muted" };
var _hoisted_16$1 = { class: "muted" };
var _hoisted_17$1 = {
	key: 0,
	class: "muted"
};
var _hoisted_18$1 = { class: "configuration-groups" };
var _hoisted_19$1 = { class: "configuration-group" };
var _hoisted_20$1 = {
	key: 0,
	class: "setting-details"
};
var _hoisted_21$1 = { key: 0 };
var _hoisted_22$1 = { key: 1 };
var _hoisted_23$1 = { key: 2 };
var _hoisted_24$1 = { key: 3 };
var _hoisted_25$1 = {
	key: 1,
	class: "muted"
};
var _hoisted_26$1 = {
	key: 0,
	class: "setting-toggle",
	style: { "flex-wrap": "wrap" }
};
var _hoisted_27$1 = {
	key: 1,
	class: "setting-toggle"
};
var _hoisted_28$1 = [
	"aria-label",
	"title",
	"disabled",
	"onClick"
];
var _hoisted_29$1 = [
	"id",
	"type",
	"value",
	"min",
	"step",
	"placeholder",
	"disabled",
	"aria-invalid",
	"aria-describedby",
	"onInput"
];
var _hoisted_30$1 = ["disabled", "onClick"];
var _hoisted_31$1 = {
	key: 5,
	class: "configuration-services"
};
var _hoisted_32$1 = { key: 6 };
var _hoisted_33 = {
	key: 0,
	class: "muted"
};
var _hoisted_34 = {
	key: 1,
	class: "configuration-group"
};
var _hoisted_35 = { class: "muted" };
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_AppButton = resolveComponent("AppButton");
	const _component_AppIcon = resolveComponent("AppIcon");
	const _component_AppSwitch = resolveComponent("AppSwitch");
	const _component_AppSelect = resolveComponent("AppSelect");
	const _component_SettingRow = resolveComponent("SettingRow");
	return openBlock(), createElementBlock("section", {
		class: "content server-configuration",
		"aria-busy": $data.loading || $data.saving
	}, [
		$data.error ? (openBlock(), createElementBlock("p", _hoisted_2$7, [$options.failedSetting ? (openBlock(), createElementBlock("strong", _hoisted_3$7, toDisplayString($options.t($options.failedSetting)) + ": ", 1)) : createCommentVNode("", true), createTextVNode(toDisplayString($options.t($data.error)), 1)])) : createCommentVNode("", true),
		$data.notice && !$options.hasChanges ? (openBlock(), createElementBlock("p", _hoisted_4$6, toDisplayString($options.t($data.notice)), 1)) : createCommentVNode("", true),
		$data.loading ? (openBlock(), createElementBlock("p", _hoisted_5$5, toDisplayString($options.t("Loading data…")), 1)) : createCommentVNode("", true),
		$data.configuration ? (openBlock(), createElementBlock(Fragment, { key: 3 }, [
			$data.activeGroup === "Services and workers" && !$data.search ? (openBlock(), createElementBlock("section", _hoisted_6$5, [
				createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString($options.t("SSE connections")) + " · " + toDisplayString($data.configuration.event_clients?.length || 0), 1), createVNode(_component_AppButton, {
					icon: "refresh",
					label: "Refresh connections",
					disabled: $data.clientsLoading || $data.loading || $data.saving,
					onClick: $options.refreshClients
				}, null, 8, ["disabled", "onClick"])]),
				createBaseVNode("p", _hoisted_7$5, toDisplayString($options.t("Open SSE connections across all web workers. This is a connection list, not user presence. Refresh to update the snapshot; closed connections disappear within the collection interval, crashed workers within 45 seconds.")), 1),
				$data.clientsError ? (openBlock(), createElementBlock("p", _hoisted_8$5, toDisplayString($options.t($data.clientsError)), 1)) : createCommentVNode("", true),
				createBaseVNode("div", _hoisted_9$5, [$data.configuration.event_clients?.length ? (openBlock(), createElementBlock("table", _hoisted_10$5, [createBaseVNode("thead", null, [createBaseVNode("tr", null, [
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
				}), 128))])])) : (openBlock(), createElementBlock("p", _hoisted_11$3, toDisplayString($options.t("No open SSE connections")), 1))])
			])) : createCommentVNode("", true),
			$props.showDetails ? (openBlock(), createElementBlock("details", _hoisted_12$1, [
				createBaseVNode("summary", null, toDisplayString($options.t("Configuration source")), 1),
				createBaseVNode("button", {
					disabled: $data.loading || $data.saving || $options.hasChanges,
					onClick: _cache[0] || (_cache[0] = (...args) => $options.load && $options.load(...args))
				}, [createVNode(_component_AppIcon, { name: "refresh" }), createTextVNode(toDisplayString($options.t("Refresh")), 1)], 8, _hoisted_13$1),
				createBaseVNode("span", _hoisted_14$1, toDisplayString($options.t("Configuration file")), 1),
				createBaseVNode("code", null, toDisplayString($data.configuration.config_path), 1),
				createBaseVNode("span", _hoisted_15$1, toDisplayString($options.t("Data directory")), 1),
				createBaseVNode("code", null, toDisplayString($data.configuration.data_dir), 1),
				createBaseVNode("p", _hoisted_16$1, toDisplayString($options.t("Supported settings can be saved to XML. Values come from the configuration file; startup overrides may differ.")), 1),
				!$data.configuration.writable ? (openBlock(), createElementBlock("p", _hoisted_17$1, toDisplayString($options.t("The configuration file is missing or not writable. Editing is unavailable.")), 1)) : createCommentVNode("", true)
			])) : createCommentVNode("", true),
			createBaseVNode("div", _hoisted_18$1, [
				(openBlock(true), createElementBlock(Fragment, null, renderList($options.groups, (group) => {
					return openBlock(), createElementBlock("section", {
						key: group.title,
						class: "settings-section"
					}, [createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString($options.t($options.groupHeading(group.title))), 1)]), createBaseVNode("div", _hoisted_19$1, [(openBlock(true), createElementBlock(Fragment, null, renderList(group.settings, (setting) => {
						return openBlock(), createBlock(_component_SettingRow, {
							key: setting.path,
							"control-id": setting.path,
							title: setting.editable && setting.input_type === "services" ? "Background jobs" : setting.label,
							description: setting.description
						}, {
							description: withCtx(() => [$props.showDetails ? (openBlock(), createElementBlock("details", _hoisted_20$1, [
								createBaseVNode("summary", null, toDisplayString($options.t("Details")), 1),
								createBaseVNode("code", null, toDisplayString(setting.path), 1),
								setting.editable ? (openBlock(), createElementBlock("small", _hoisted_21$1, toDisplayString($options.t("Saved value: {value}", { value: $options.value(setting) })), 1)) : createCommentVNode("", true),
								!setting.configured && setting.default !== null ? (openBlock(), createElementBlock("small", _hoisted_22$1, toDisplayString($options.t("Default when empty: {value}", { value: setting.default })), 1)) : createCommentVNode("", true),
								setting.environment_override ? (openBlock(), createElementBlock("small", _hoisted_23$1, toDisplayString($options.t("Environment override: {value}", { value: setting.environment_override })), 1)) : createCommentVNode("", true),
								setting.note ? (openBlock(), createElementBlock("small", _hoisted_24$1, toDisplayString($options.t(setting.note)), 1)) : createCommentVNode("", true)
							])) : createCommentVNode("", true), setting.restart ? (openBlock(), createElementBlock("small", _hoisted_25$1, toDisplayString($options.t("Restart required after changes")), 1)) : createCommentVNode("", true)]),
							default: withCtx(() => [
								setting.editable && setting.input_type === "services" ? (openBlock(), createElementBlock("div", _hoisted_26$1, [createVNode(_component_AppSwitch, {
									id: setting.path,
									"model-value": $options.serviceEnabled(setting, { name: "queue" }),
									disabled: $data.loading || $data.saving,
									label: "Background jobs",
									"aria-describedby": setting.path + "-help",
									"onUpdate:modelValue": ($event) => $options.editService(setting, "queue", $event)
								}, null, 8, [
									"id",
									"model-value",
									"disabled",
									"aria-describedby",
									"onUpdate:modelValue"
								]), createVNode(_component_AppSwitch, {
									id: setting.path + "-files",
									"model-value": $options.serviceEnabled(setting, { name: "files" }),
									disabled: $data.loading || $data.saving,
									label: "Bulk file transfers",
									"aria-describedby": setting.path + "-help",
									"onUpdate:modelValue": ($event) => $options.editService(setting, "files", $event)
								}, null, 8, [
									"id",
									"model-value",
									"disabled",
									"aria-describedby",
									"onUpdate:modelValue"
								])])) : setting.editable && setting.input_type === "boolean" ? (openBlock(), createElementBlock("div", _hoisted_27$1, [createVNode(_component_AppSwitch, {
									id: setting.path,
									"model-value": $options.booleanValue(setting),
									label: setting.label,
									disabled: $data.loading || $data.saving,
									"aria-invalid": $data.errorField === setting.path,
									"aria-describedby": setting.path + "-help",
									"onUpdate:modelValue": ($event) => $options.editSetting(setting.path, $event ? "true" : "false")
								}, null, 8, [
									"id",
									"model-value",
									"label",
									"disabled",
									"aria-invalid",
									"aria-describedby",
									"onUpdate:modelValue"
								]), createBaseVNode("button", {
									class: "icon-button",
									"aria-label": $options.t("Use default"),
									title: $options.t("Use default"),
									disabled: $data.loading || $data.saving || $data.draft[setting.path] === "",
									onClick: ($event) => $options.editSetting(setting.path, "")
								}, [createVNode(_component_AppIcon, { name: "undo" })], 8, _hoisted_28$1)])) : setting.editable && setting.choices ? (openBlock(), createBlock(_component_AppSelect, {
									key: 2,
									id: setting.path,
									"model-value": $data.draft[setting.path],
									options: setting.choices,
									label: setting.label,
									disabled: $data.loading || $data.saving,
									"aria-invalid": $data.errorField === setting.path,
									"aria-describedby": setting.path + "-help",
									"onUpdate:modelValue": ($event) => $options.editSetting(setting.path, $event)
								}, null, 8, [
									"id",
									"model-value",
									"options",
									"label",
									"disabled",
									"aria-invalid",
									"aria-describedby",
									"onUpdate:modelValue"
								])) : setting.editable ? (openBlock(), createElementBlock("input", {
									key: 3,
									id: setting.path,
									type: setting.secret ? "password" : [
										"integer",
										"padding",
										"number"
									].includes(setting.input_type) ? "number" : "text",
									value: $data.draft[setting.path] ?? "",
									min: setting.input_type === "integer" ? 1 : 0,
									step: setting.input_type === "integer" ? 1 : "any",
									placeholder: setting.secret ? $options.t("Leave empty to keep the stored secret") : setting.default,
									maxlength: "4096",
									autocomplete: "off",
									disabled: $data.loading || $data.saving,
									"aria-invalid": $data.errorField === setting.path,
									"aria-describedby": setting.path + "-help",
									onInput: ($event) => $options.editSetting(setting.path, setting.secret && !$event.target.value ? null : $event.target.value)
								}, null, 40, _hoisted_29$1)) : createCommentVNode("", true),
								setting.editable && setting.secret && setting.configured ? (openBlock(), createElementBlock("button", {
									key: 4,
									disabled: $data.loading || $data.saving || $data.draft[setting.path] === "",
									onClick: ($event) => $options.editSetting(setting.path, "")
								}, toDisplayString($options.t("Clear stored secret")), 9, _hoisted_30$1)) : createCommentVNode("", true),
								setting.services ? (openBlock(), createElementBlock("div", _hoisted_31$1, [(openBlock(true), createElementBlock(Fragment, null, renderList(setting.services, (service) => {
									return openBlock(), createElementBlock("span", {
										key: service.name,
										class: normalizeClass({ enabled: $options.serviceEnabled(setting, service) })
									}, toDisplayString($options.t(service.name === "tactic" ? "Web and API" : service.name === "files" ? "Bulk file transfers" : "Background jobs")) + " · " + toDisplayString($options.t($options.serviceEnabled(setting, service) ? "Enabled" : "Disabled")), 3);
								}), 128))])) : createCommentVNode("", true),
								!setting.editable ? (openBlock(), createElementBlock("code", _hoisted_32$1, toDisplayString($options.value(setting)), 1)) : createCommentVNode("", true)
							]),
							_: 2
						}, 1032, [
							"control-id",
							"title",
							"description"
						]);
					}), 128))])]);
				}), 128)),
				!$options.groups.length ? (openBlock(), createElementBlock("p", _hoisted_33, toDisplayString($options.t("No settings found")), 1)) : createCommentVNode("", true),
				$data.configuration.undocumented.length ? (openBlock(), createElementBlock("details", _hoisted_34, [
					createBaseVNode("summary", null, toDisplayString($options.t("Other configured options")) + " · " + toDisplayString($data.configuration.undocumented.length), 1),
					createBaseVNode("p", _hoisted_35, toDisplayString($options.t("These options still need documentation and a support check. Their values are not exposed.")), 1),
					createBaseVNode("ul", null, [(openBlock(true), createElementBlock(Fragment, null, renderList($data.configuration.undocumented, (path) => {
						return openBlock(), createElementBlock("li", { key: path }, [createBaseVNode("code", null, toDisplayString(path), 1)]);
					}), 128))])
				])) : createCommentVNode("", true)
			])
		], 64)) : createCommentVNode("", true)
	], 8, _hoisted_1$7);
}
var ServerConfiguration_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main$7, [["render", _sfc_render]]);
//#endregion
//#region src/features/debug/DebugSettings.vue
var _hoisted_1$6 = { class: "content debug-recording-settings" };
var _hoisted_2$6 = { class: "muted" };
var _hoisted_3$6 = { class: "configuration-group" };
var _hoisted_4$5 = { class: "muted" };
var _sfc_main$6 = {
	__name: "DebugSettings",
	props: { settings: {
		type: Object,
		default: () => debugSettings
	} },
	setup(__props) {
		const props = __props;
		function toggle(level, checked) {
			props.settings.recordingLevels = checked ? levels.filter((item) => item === level || props.settings.recordingLevels.includes(item)) : props.settings.recordingLevels.filter((item) => item !== level);
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", _hoisted_1$6, [
				createBaseVNode("h2", null, toDisplayString(unref(t)("Debug Log")), 1),
				createBaseVNode("p", _hoisted_2$6, toDisplayString(unref(t)("Choose which events are recorded. Level filters in Debug Log only hide recorded events. Errors and critical events are recorded by default.")), 1),
				createBaseVNode("div", _hoisted_3$6, [(openBlock(true), createElementBlock(Fragment, null, renderList(unref(levels), (level) => {
					return openBlock(), createBlock(_sfc_main$13, {
						key: level,
						"control-id": "record-debug-" + level,
						title: level,
						description: {
							LOG: "General application messages.",
							INFO: "Informational application events.",
							WARNING: "Recoverable issues and warnings.",
							MISSING: "Missing files and resources.",
							EXCEPTION: "Unhandled exceptions.",
							ERROR: "Failed requests and application errors.",
							CRITICAL: "Critical application failures.",
							API: "Successful API calls, including arguments, results and duration."
						}[level]
					}, {
						default: withCtx(() => [createVNode(_sfc_main$17, {
							"control-id": "record-debug-" + level,
							"model-value": __props.settings.recordingLevels.includes(level),
							label: unref(t)("Record {level}", { level }),
							"onUpdate:modelValue": ($event) => toggle(level, $event)
						}, null, 8, [
							"control-id",
							"model-value",
							"label",
							"onUpdate:modelValue"
						])]),
						_: 2
					}, 1032, [
						"control-id",
						"title",
						"description"
					]);
				}), 128))]),
				createBaseVNode("p", _hoisted_4$5, toDisplayString(unref(t)("Debug sessions are stored in this browser. Download a session to share it. Signing out clears local sessions. Tickets and credentials are redacted.")), 1)
			]);
		};
	}
};
//#endregion
//#region src/features/configuration/NetworkSettings.vue
var _hoisted_1$5 = { class: "content" };
var _hoisted_2$5 = { class: "muted" };
var _hoisted_3$5 = { class: "configuration-group" };
var _sfc_main$5 = {
	__name: "NetworkSettings",
	props: { settings: {
		type: Object,
		default: () => networkSettings
	} },
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", _hoisted_1$5, [
				createBaseVNode("h2", null, toDisplayString(unref(t)("Background checks")), 1),
				createBaseVNode("p", _hoisted_2$5, toDisplayString(unref(t)("Committed changes are coalesced by one server worker. Only subscribed data is refreshed; presence and authentication keep their own heartbeat.")), 1),
				createBaseVNode("div", _hoisted_3$5, [
					createVNode(_sfc_main$13, {
						title: "Update delivery",
						description: "Choose periodic checks or a persistent server push connection. Commands and file uploads use the same API.",
						"control-id": "server-update-mode"
					}, {
						default: withCtx(() => [createVNode(_sfc_main$12, {
							id: "server-update-mode",
							modelValue: __props.settings.updateMode,
							"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => __props.settings.updateMode = $event),
							label: "Update delivery",
							options: unref(updateModes)
						}, null, 8, ["modelValue", "options"])]),
						_: 1
					}),
					__props.settings.updateMode === "poll" ? (openBlock(), createBlock(_sfc_main$13, {
						key: 0,
						title: "Server updates",
						description: "Interval for the shared server request. Changing it also updates the Connection menu.",
						"control-id": "server-update-interval"
					}, {
						default: withCtx(() => [createVNode(_sfc_main$12, {
							id: "server-update-interval",
							modelValue: __props.settings.pollInterval,
							"onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => __props.settings.pollInterval = $event),
							label: "Server updates",
							options: unref(updateIntervals)
						}, null, 8, ["modelValue", "options"])]),
						_: 1
					})) : createCommentVNode("", true),
					__props.settings.updateMode === "sse" ? (openBlock(), createBlock(_sfc_main$13, {
						key: 1,
						title: "Update batching delay",
						description: "Combine arriving changes before reading data. A longer delay reduces requests during bursts; it also delays visible updates.",
						"control-id": "server-update-batch-delay"
					}, {
						default: withCtx(() => [createVNode(_sfc_main$12, {
							id: "server-update-batch-delay",
							modelValue: __props.settings.batchDelay,
							"onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => __props.settings.batchDelay = $event),
							label: "Update batching delay",
							options: unref(updateBatchDelays)
						}, null, 8, ["modelValue", "options"])]),
						_: 1
					})) : createCommentVNode("", true)
				])
			]);
		};
	}
};
//#endregion
//#region src/features/configuration/PreferenceSettings.vue
var _hoisted_1$4 = { class: "content preference-settings" };
var _hoisted_2$4 = { class: "muted" };
var _hoisted_3$4 = { class: "configuration-group" };
var _hoisted_4$4 = [
	"id",
	"onUpdate:modelValue",
	"min",
	"max",
	"aria-label",
	"aria-describedby",
	"disabled"
];
var _hoisted_5$4 = {
	key: 0,
	class: "settings-section"
};
var _hoisted_6$4 = { class: "muted" };
var _hoisted_7$4 = { class: "configuration-group task-default-columns" };
var _hoisted_8$4 = [
	"onUpdate:modelValue",
	"aria-label",
	"disabled"
];
var _hoisted_9$4 = { class: "muted" };
var _hoisted_10$4 = {
	key: 1,
	class: "muted"
};
var _sfc_main$4 = {
	__name: "PreferenceSettings",
	props: {
		page: String,
		draft: Object,
		busy: Boolean
	},
	setup(__props) {
		const props = __props;
		const uid = useId();
		const options = (values, labels) => values.map((value, index) => ({
			value,
			label: labels[index]
		}));
		const sections = computed(() => props.page === "checkin" ? [{
			title: "Search results",
			description: "Choose how result items are loaded and initially presented.",
			fields: [
				{
					key: "displayLimit",
					title: "Result limit",
					description: "Maximum number of sObjects requested for one search result page.",
					kind: "number",
					min: 1,
					max: 500
				},
				{
					key: "loadingMode",
					title: "Loading mode",
					description: "Use explicit result pages or load the next page when scrolling reaches the end.",
					options: options(["pages", "infinite"], ["Pages", "Infinite scroll"])
				},
				{
					key: "defaultViewMode",
					title: "Default result view",
					description: "Initial presentation used when a search tab has no saved view state.",
					options: resultViews
				}
			]
		}, {
			title: "File matching and naming",
			description: "Defaults used when preparing a new browser check-in.",
			fields: [
				{
					key: "groupCheckin",
					title: "Group selected files",
					description: "Combine the selected files into one snapshot instead of preparing a snapshot for each file."
				},
				{
					key: "keepFilename",
					title: "Keep original filename",
					description: "Preserve source filenames instead of applying the active naming template."
				},
				{
					key: "generatePreviews",
					title: "Generate previews",
					description: "Create web and icon images on the server during check-in."
				},
				{
					key: "confirmRevision",
					title: "Confirm revision replacement",
					description: "Require explicit confirmation before replacing files in an existing revision."
				},
				{
					key: "commitQueueAutoClean",
					title: "Clean completed check-ins",
					description: "Remove successful rows from Commit Queue after each completed batch. Failed and uncertain rows remain available."
				}
			]
		}] : props.page === "tasks" ? [{
			title: "Task workspace defaults",
			description: "Initial task surface, presentation, ordering and grouping.",
			fields: [
				{
					key: "workspaceSurface",
					title: "Initial task surface",
					description: "Open Quick Tasks or the detailed Task Browser first.",
					options: options(["quick", "browser"], ["Quick Tasks", "Task Browser"])
				},
				{
					key: "quickViewMode",
					title: "Quick Tasks presentation",
					description: "Show editable process cards or a compact task list.",
					options: options(["cards", "compact"], ["Cards", "Compact list"])
				},
				{
					key: "viewMode",
					title: "Initial view",
					description: "View opened first when Task Browser has no saved local state.",
					options: options(["table", "gantt"], ["Table", "Gantt"])
				},
				{
					key: "sortMode",
					title: "Initial sorting",
					description: "Default order used before the user applies a table or column sort.",
					options: options([
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
					], [
						"Deadline",
						"Recently changed",
						"Process",
						"Assignee",
						"Status",
						"Object",
						"Search Type",
						"Project",
						"Priority",
						"Milestone",
						"Supervisor"
					])
				},
				{
					key: "groupMode",
					title: "Initial grouping",
					description: "Default task groups before a workspace preference is saved.",
					options: options([
						"none",
						"process",
						"user",
						"status",
						"object"
					], [
						"No grouping",
						"Process",
						"Assignee",
						"Status",
						"Object"
					])
				},
				{
					key: "inspectorExpanded",
					title: "Expand task details",
					description: "Initial state of task details in Task Inspector. Saved account preferences take priority."
				}
			]
		}] : props.page === "global" ? [{
			title: "Notifications",
			description: "Choose which incoming events show a notification. Their history remains available.",
			fields: [{
				key: "activityNotifications",
				title: "Activity feed notifications",
				description: "Show notifications for incoming project activity."
			}, {
				key: "messageNotifications",
				title: "Message notifications",
				description: "Show notifications for incoming messages."
			}]
		}] : [{
			title: "Workspace cache",
			description: "Control retained presentation state independently of server records.",
			fields: [{
				key: "cacheProcessTabs",
				title: "Remember process expansion",
				description: "Restore expanded objects, processes and version branches when reopening saved search tabs."
			}]
		}]);
		function move(index, direction) {
			const target = index + direction;
			if (target < 0 || target >= props.draft.columns.length) return;
			const column = props.draft.columns.splice(index, 1)[0];
			props.draft.columns.splice(target, 0, column);
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", _hoisted_1$4, [
				(openBlock(true), createElementBlock(Fragment, null, renderList(sections.value, (section) => {
					return openBlock(), createElementBlock("section", {
						key: section.title,
						class: "settings-section"
					}, [createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)(section.title)), 1), createBaseVNode("p", _hoisted_2$4, toDisplayString(unref(t)(section.description)), 1)]), createBaseVNode("div", _hoisted_3$4, [(openBlock(true), createElementBlock(Fragment, null, renderList(section.fields, (field) => {
						return openBlock(), createBlock(_sfc_main$13, {
							key: field.key,
							"control-id": unref(uid) + "-" + field.key,
							title: field.title,
							description: field.description
						}, {
							default: withCtx(() => [field.options ? (openBlock(), createBlock(_sfc_main$12, {
								key: 0,
								id: unref(uid) + "-" + field.key,
								modelValue: __props.draft[field.key],
								"onUpdate:modelValue": ($event) => __props.draft[field.key] = $event,
								options: field.options,
								label: field.title,
								disabled: __props.busy,
								"aria-describedby": unref(uid) + "-" + field.key + "-help"
							}, null, 8, [
								"id",
								"modelValue",
								"onUpdate:modelValue",
								"options",
								"label",
								"disabled",
								"aria-describedby"
							])) : field.kind === "number" ? withDirectives((openBlock(), createElementBlock("input", {
								key: 1,
								id: unref(uid) + "-" + field.key,
								"onUpdate:modelValue": ($event) => __props.draft[field.key] = $event,
								type: "number",
								min: field.min,
								max: field.max,
								"aria-label": unref(t)(field.title),
								"aria-describedby": unref(uid) + "-" + field.key + "-help",
								disabled: __props.busy
							}, null, 8, _hoisted_4$4)), [[
								vModelText,
								__props.draft[field.key],
								void 0,
								{ number: true }
							]]) : (openBlock(), createBlock(_sfc_main$11, {
								key: 2,
								id: unref(uid) + "-" + field.key,
								modelValue: __props.draft[field.key],
								"onUpdate:modelValue": ($event) => __props.draft[field.key] = $event,
								label: field.title,
								disabled: __props.busy,
								"aria-describedby": unref(uid) + "-" + field.key + "-help"
							}, null, 8, [
								"id",
								"modelValue",
								"onUpdate:modelValue",
								"label",
								"disabled",
								"aria-describedby"
							]))]),
							_: 2
						}, 1032, [
							"control-id",
							"title",
							"description"
						]);
					}), 128))])]);
				}), 128)),
				__props.page === "tasks" ? (openBlock(), createElementBlock("section", _hoisted_5$4, [
					createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)("Task Browser columns")), 1), createBaseVNode("p", _hoisted_6$4, toDisplayString(unref(t)("Default order, visibility and width. Saved project layouts take priority.")), 1)]),
					createBaseVNode("div", _hoisted_7$4, [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.draft.columns, (column, index) => {
						return openBlock(), createElementBlock("div", {
							key: column.key,
							class: "task-default-column"
						}, [
							createVNode(_sfc_main$17, {
								modelValue: column.visible,
								"onUpdate:modelValue": ($event) => column.visible = $event,
								label: column.label,
								disabled: column.key === "object" || __props.busy
							}, {
								default: withCtx(() => [createBaseVNode("span", null, toDisplayString(unref(t)(column.label)), 1)]),
								_: 2
							}, 1032, [
								"modelValue",
								"onUpdate:modelValue",
								"label",
								"disabled"
							]),
							withDirectives(createBaseVNode("input", {
								"onUpdate:modelValue": ($event) => column.width = $event,
								type: "number",
								min: "40",
								max: "480",
								"aria-label": unref(t)("Width of {column}", { column: unref(t)(column.label) }),
								disabled: __props.busy
							}, null, 8, _hoisted_8$4), [[
								vModelText,
								column.width,
								void 0,
								{ number: true }
							]]),
							createVNode(_sfc_main$9, {
								"icon-only": "",
								icon: "up",
								label: "Move column up",
								disabled: index === 0 || __props.busy,
								onClick: ($event) => move(index, -1)
							}, null, 8, ["disabled", "onClick"]),
							createVNode(_sfc_main$9, {
								"icon-only": "",
								icon: "down",
								label: "Move column down",
								disabled: index === __props.draft.columns.length - 1 || __props.busy,
								onClick: ($event) => move(index, 1)
							}, null, 8, ["disabled", "onClick"])
						]);
					}), 128))]),
					createBaseVNode("p", _hoisted_9$4, toDisplayString(unref(t)("Task scope, filters, collapsed groups, calendar position and the selected task resume separately for each project. Checked tasks and unsaved edits are never restored.")), 1)
				])) : createCommentVNode("", true),
				__props.page === "checkin" ? (openBlock(), createElementBlock("p", _hoisted_10$4, toDisplayString(unref(t)("Browser check-in uploads files to the server. Local move/copy, opening associated desktop applications and directory scanning require a desktop client.")), 1)) : createCommentVNode("", true)
			]);
		};
	}
};
//#endregion
//#region src/features/configuration/ProjectSettings.vue
var _hoisted_1$3 = ["aria-busy"];
var _hoisted_2$3 = {
	key: 0,
	class: "error",
	role: "alert"
};
var _hoisted_3$3 = { class: "settings-section project-catalog-section" };
var _hoisted_4$3 = { class: "muted" };
var _hoisted_5$3 = { class: "configuration-group" };
var _hoisted_6$3 = { class: "settings-section project-selection-section" };
var _hoisted_7$3 = { class: "configuration-group" };
var _hoisted_8$3 = { class: "muted" };
var _hoisted_9$3 = { key: 0 };
var _hoisted_10$3 = { class: "project-settings-actions" };
var _sfc_main$3 = {
	__name: "ProjectSettings",
	props: {
		ticket: String,
		project: String,
		canAdminister: Boolean,
		openProject: Function
	},
	emits: ["changed"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const projects = ref([]), selected = ref(""), editor = ref(null), creator = ref(null), busy = ref(false), error = ref("");
		const item = computed(() => projects.value.find((item) => item.code === selected.value));
		const editable = computed(() => props.canAdminister && item.value && !item.value.__builtin__ && !busy.value);
		async function load() {
			busy.value = true;
			error.value = "";
			try {
				projects.value = await projectCatalog(props.ticket);
			} catch (failure) {
				error.value = failure.message;
			} finally {
				busy.value = false;
			}
		}
		async function activate(code) {
			if (busy.value) return;
			busy.value = true;
			error.value = "";
			try {
				if (await props.openProject(code) === false) error.value = "The project could not be activated.";
			} catch (failure) {
				error.value = failure.message;
			} finally {
				busy.value = false;
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
				const link = document.createElement("a");
				link.href = "/assets/_cache/" + encodeURIComponent(props.ticket) + "/" + encodeURIComponent(result.info.filename);
				link.download = result.info.filename;
				link.click();
			} catch (failure) {
				error.value = failure.message;
			} finally {
				busy.value = false;
			}
		}
		onMounted(load);
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				class: "content configuration-projects",
				"aria-busy": busy.value
			}, [
				error.value ? (openBlock(), createElementBlock("p", _hoisted_2$3, toDisplayString(unref(t)(error.value)), 1)) : createCommentVNode("", true),
				createBaseVNode("section", _hoisted_3$3, [createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)("Available projects")), 1), createBaseVNode("p", _hoisted_4$3, toDisplayString(unref(t)("Select a project to make it active in the workspace.")), 1)]), createBaseVNode("div", _hoisted_5$3, [createVNode(ProjectChooser_default, {
					inline: "",
					projects: projects.value,
					selected: selected.value,
					onSelected: _cache[0] || (_cache[0] = ($event) => selected.value = $event)
				}, null, 8, ["projects", "selected"])])]),
				createBaseVNode("section", _hoisted_6$3, [createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)("Project actions")), 1)]), createBaseVNode("div", _hoisted_7$3, [
					createBaseVNode("small", _hoisted_8$3, toDisplayString(unref(t)("CURRENT")), 1),
					createBaseVNode("h3", null, toDisplayString(projects.value.find((item) => item.code === __props.project)?.title || unref(t)("No active project")), 1),
					createBaseVNode("p", null, [createTextVNode(toDisplayString(item.value?.title || unref(t)("Select a project")) + " ", 1), item.value ? (openBlock(), createElementBlock("code", _hoisted_9$3, toDisplayString(item.value.code), 1)) : createCommentVNode("", true)]),
					createBaseVNode("div", _hoisted_10$3, [
						createVNode(_sfc_main$9, {
							label: "Activate selected project",
							icon: "check",
							disabled: !item.value || busy.value || item.value.code === __props.project,
							onClick: _cache[1] || (_cache[1] = ($event) => activate(item.value.code))
						}, null, 8, ["disabled"]),
						createVNode(_sfc_main$9, {
							label: "Edit selected project",
							icon: "edit",
							disabled: !editable.value,
							onClick: _cache[2] || (_cache[2] = ($event) => editor.value.open(item.value.__search_key__))
						}, null, 8, ["disabled"]),
						createVNode(_sfc_main$9, {
							label: "Deactivate current project",
							icon: "close",
							disabled: !__props.project || busy.value,
							onClick: _cache[3] || (_cache[3] = ($event) => activate(""))
						}, null, 8, ["disabled"]),
						createVNode(_sfc_main$9, {
							label: "Create template archive",
							icon: "download",
							disabled: !editable.value,
							onClick: archive
						}, null, 8, ["disabled"]),
						createVNode(_sfc_main$9, {
							label: "Create new project",
							icon: "add",
							disabled: !__props.canAdminister || busy.value,
							onClick: _cache[4] || (_cache[4] = ($event) => creator.value.open())
						}, null, 8, ["disabled"]),
						createVNode(_sfc_main$9, {
							label: "Refresh projects",
							icon: "refresh",
							disabled: busy.value,
							onClick: load
						}, null, 8, ["disabled"])
					])
				])]),
				createVNode(RecordForm_default, {
					ref_key: "editor",
					ref: editor,
					ticket: __props.ticket,
					project: "admin",
					"search-type": "sthpw/project",
					onSaved: changed
				}, null, 8, ["ticket"]),
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
//#region src/features/configuration/RepositorySettings.vue
var _hoisted_1$2 = ["aria-busy"];
var _hoisted_2$2 = {
	key: 0,
	class: "error",
	role: "alert"
};
var _hoisted_3$2 = { class: "settings-section" };
var _hoisted_4$2 = { class: "muted" };
var _hoisted_5$2 = { class: "configuration-group" };
var _hoisted_6$2 = { class: "repository-definition-actions" };
var _hoisted_7$2 = { class: "settings-section" };
var _hoisted_8$2 = { class: "muted" };
var _hoisted_9$2 = { class: "configuration-group" };
var _hoisted_10$2 = { class: "repository-chips" };
var _hoisted_11$2 = { class: "muted" };
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
		async function load(action = "load", paths) {
			if (checking.value) return;
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
				records.value = result.info.repositories;
				platform.value = result.info.platform;
				return true;
			} catch (failure) {
				if (failure.code === "authentication_failed") emit("session-expired");
				error.value = failure.message;
				return false;
			} finally {
				checking.value = false;
			}
		}
		onMounted(() => load());
		__expose({
			load,
			records,
			checking
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				class: "content repository-settings",
				"aria-busy": checking.value
			}, [
				error.value ? (openBlock(), createElementBlock("p", _hoisted_2$2, toDisplayString(unref(t)(error.value)), 1)) : createCommentVNode("", true),
				createBaseVNode("section", _hoisted_3$2, [createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)("Repository storage")), 1), createBaseVNode("p", _hoisted_4$2, toDisplayString(unref(t)("Snapshots, previews, check-in and check-out depend on a valid repository path.")), 1)]), createBaseVNode("div", _hoisted_5$2, [createVNode(_sfc_main$13, {
					title: current.value?.title || "Repository configuration is loading",
					description: current.value?.path
				}, {
					default: withCtx(() => [createVNode(_sfc_main$18, {
						label: unref(t)(current.value ? "Configured" : "Loading"),
						"show-count": false,
						accent: current.value ? "var(--success)" : void 0
					}, null, 8, ["label", "accent"])]),
					_: 1
				}, 8, ["title", "description"]), createVNode(_sfc_main$13, {
					title: "Repository definitions",
					description: "Configure server roots, repository aliases, labels and client paths."
				}, {
					default: withCtx(() => [createBaseVNode("div", _hoisted_6$2, [createVNode(_sfc_main$9, {
						label: "Open Repository Editor",
						icon: "database",
						disabled: __props.busy || checking.value,
						onClick: _cache[0] || (_cache[0] = ($event) => emit("edit"))
					}, null, 8, ["disabled"]), createVNode(_sfc_main$9, {
						label: checking.value ? "Checking…" : "Check paths",
						icon: "check",
						disabled: __props.busy || checking.value || !records.value.length,
						onClick: _cache[1] || (_cache[1] = ($event) => load("check"))
					}, null, 8, ["label", "disabled"])])]),
					_: 1
				})])]),
				createBaseVNode("section", _hoisted_7$2, [
					createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)("Active repositories")), 1), createBaseVNode("p", _hoisted_8$2, toDisplayString(unref(t)("The default repository is used when an operation does not choose another destination explicitly.")), 1)]),
					createBaseVNode("div", _hoisted_9$2, [(openBlock(true), createElementBlock(Fragment, null, renderList(records.value.filter((item) => item.alias !== "plugins" && (unref(preferences).repository.enabledAliases === null || unref(preferences).repository.enabledAliases.includes(item.alias))), (item) => {
						return openBlock(), createBlock(_sfc_main$13, {
							key: item.alias,
							title: item.title,
							description: item.path
						}, {
							default: withCtx(() => [createBaseVNode("div", _hoisted_10$2, [createVNode(_sfc_main$18, {
								label: item.alias === current.value?.alias ? unref(t)("Default") : item.alias,
								accent: /^#[a-f\d]{6}$/i.test(item.color) ? item.color : void 0,
								"show-count": false
							}, null, 8, ["label", "accent"]), item.status !== "unchecked" ? (openBlock(), createBlock(_sfc_main$18, {
								key: 0,
								label: unref(t)(item.status === "available" ? "Available" : "Folder not found or inaccessible"),
								"show-count": false,
								accent: item.status === "available" ? "var(--success)" : "var(--error)"
							}, null, 8, ["label", "accent"])) : createCommentVNode("", true)])]),
							_: 2
						}, 1032, ["title", "description"]);
					}), 128))]),
					createBaseVNode("p", _hoisted_11$2, toDisplayString(unref(t)("Paths are checked by the server account ({platform}). Missing configured folders are created; existing files are preserved.", { platform: platform.value })), 1)
				])
			], 8, _hoisted_1$2);
		};
	}
};
//#endregion
//#region src/features/configuration/RepositoryEditor.vue
var _hoisted_1$1 = { class: "repository-editor-native" };
var _hoisted_2$1 = ["aria-label"];
var _hoisted_3$1 = { class: "muted" };
var _hoisted_4$1 = { class: "repository-editor-details" };
var _hoisted_5$1 = {
	key: 0,
	class: "error",
	role: "alert"
};
var _hoisted_6$1 = { class: "muted" };
var _hoisted_7$1 = {
	key: 0,
	class: "error",
	role: "alert"
};
var _hoisted_8$1 = { class: "repository-editor-color" };
var _hoisted_9$1 = { class: "repository-editor-path-policy" };
var _hoisted_10$1 = { class: "repository-editor-status" };
var _hoisted_11$1 = { class: "repository-editor-advanced" };
var _sfc_main$1 = {
	__name: "RepositoryEditor",
	props: {
		server: Object,
		repositories: Array,
		draft: Object,
		busy: Boolean
	},
	emits: ["check"],
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
			return mapping("base_dir_alias")[alias] || mapping("asset_base_dir")[alias] || props.repositories?.find((item) => item.alias === alias)?.path || "";
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
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", _hoisted_1$1, [createBaseVNode("nav", {
				class: "repository-editor-catalog",
				"aria-label": unref(t)("Repositories")
			}, [createBaseVNode("header", null, [createBaseVNode("strong", null, toDisplayString(unref(t)("REPOSITORIES")), 1), createVNode(_sfc_main$9, {
				icon: "add",
				"icon-only": "",
				label: "Add custom repository",
				disabled: __props.busy || invalid.value,
				onClick: add
			}, null, 8, ["disabled"])]), (openBlock(true), createElementBlock(Fragment, null, renderList(entries.value, (item) => {
				return openBlock(), createBlock(_sfc_main$9, {
					key: item.alias,
					label: title(item),
					"translate-label": false,
					"aria-pressed": record.value?.alias === item.alias,
					onClick: ($event) => selected.value = item.alias
				}, {
					default: withCtx(() => [createBaseVNode("i", { class: normalizeClass({ inactive: !enabled(item.alias) }) }, null, 2), createBaseVNode("span", null, [createBaseVNode("strong", null, toDisplayString(title(item)), 1), createBaseVNode("small", _hoisted_3$1, toDisplayString(item.alias), 1)])]),
					_: 2
				}, 1032, [
					"label",
					"aria-pressed",
					"onClick"
				]);
			}), 128))], 8, _hoisted_2$1), createBaseVNode("section", _hoisted_4$1, [
				__props.server?.error ? (openBlock(), createElementBlock("p", _hoisted_5$1, toDisplayString(unref(t)(__props.server.error)), 1)) : createCommentVNode("", true),
				record.value ? (openBlock(), createElementBlock(Fragment, { key: 1 }, [
					createBaseVNode("header", null, [
						createBaseVNode("div", null, [createBaseVNode("h3", null, toDisplayString(title(record.value)), 1), createBaseVNode("p", _hoisted_6$1, toDisplayString(unref(t)("Paths are stored in the server configuration")), 1)]),
						createVNode(_sfc_main$17, {
							"model-value": enabled(record.value.alias),
							disabled: __props.busy || record.value.alias === "plugins",
							label: "Enabled",
							"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => enable(record.value.alias, $event))
						}, {
							default: withCtx(() => [createTextVNode(toDisplayString(unref(t)("Enabled")), 1)]),
							_: 1
						}, 8, ["model-value", "disabled"]),
						createVNode(_sfc_main$17, {
							"model-value": __props.draft.defaultAlias === record.value.alias,
							disabled: __props.busy || !enabled(record.value.alias),
							label: "Default",
							"onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => __props.draft.defaultAlias = $event ? record.value.alias : entries.value.find((item) => item.alias !== record.value.alias && enabled(item.alias))?.alias || record.value.alias)
						}, {
							default: withCtx(() => [createTextVNode(toDisplayString(unref(t)("Default")), 1)]),
							_: 1
						}, 8, ["model-value", "disabled"]),
						record.value.alias.startsWith("custom_") ? (openBlock(), createBlock(_sfc_main$9, {
							key: 0,
							icon: "delete",
							"icon-only": "",
							label: "Remove custom repository",
							disabled: __props.busy || invalid.value,
							onClick: remove
						}, null, 8, ["disabled"])) : createCommentVNode("", true)
					]),
					invalid.value ? (openBlock(), createElementBlock("p", _hoisted_7$1, toDisplayString(unref(t)("Fix the repository JSON in Advanced settings before editing these fields.")), 1)) : createCommentVNode("", true),
					createVNode(_sfc_main$14, {
						"model-value": presentation(record.value).title || "",
						label: "Display name",
						placeholder: "Display name",
						maxlength: "100",
						disabled: __props.busy || invalid.value,
						"onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => update("repository_display", "title", $event))
					}, null, 8, ["model-value", "disabled"]),
					createVNode(_sfc_main$14, {
						"model-value": root(record.value.alias),
						label: "Server repository path",
						placeholder: "Server repository path",
						readonly: record.value.alias === "plugins",
						disabled: __props.busy || invalid.value,
						"onUpdate:modelValue": _cache[3] || (_cache[3] = ($event) => update(Object.hasOwn(mapping("base_dir_alias"), record.value.alias) ? "base_dir_alias" : "asset_base_dir", null, $event))
					}, null, 8, [
						"model-value",
						"readonly",
						"disabled"
					]),
					createVNode(_sfc_main$14, {
						"model-value": path("web_base_dir"),
						label: "Repository web URL",
						placeholder: "Repository web URL",
						disabled: __props.busy || invalid.value,
						"onUpdate:modelValue": _cache[4] || (_cache[4] = ($event) => update("web_base_dir", null, $event))
					}, null, 8, ["model-value", "disabled"]),
					createVNode(_sfc_main$14, {
						"model-value": path("win32_client_repo_dir"),
						label: "Windows client path",
						placeholder: "Windows client path",
						disabled: __props.busy || invalid.value,
						"onUpdate:modelValue": _cache[5] || (_cache[5] = ($event) => update("win32_client_repo_dir", null, $event))
					}, null, 8, ["model-value", "disabled"]),
					createVNode(_sfc_main$14, {
						"model-value": path("linux_client_repo_dir"),
						label: "Linux client path",
						placeholder: "Linux client path",
						disabled: __props.busy || invalid.value,
						"onUpdate:modelValue": _cache[6] || (_cache[6] = ($event) => update("linux_client_repo_dir", null, $event))
					}, null, 8, ["model-value", "disabled"]),
					createBaseVNode("div", _hoisted_8$1, [createBaseVNode("span", null, toDisplayString(unref(t)("Color")), 1), createVNode(_sfc_main$15, {
						"model-value": color(),
						disabled: __props.busy || invalid.value,
						label: "Repository color",
						"onUpdate:modelValue": _cache[7] || (_cache[7] = ($event) => update("repository_display", "color", $event))
					}, null, 8, ["model-value", "disabled"])]),
					createBaseVNode("div", _hoisted_9$1, [createBaseVNode("strong", null, toDisplayString(unref(t)("SERVER STORAGE")), 1), createBaseVNode("p", null, toDisplayString(unref(t)("Enabled and Default apply to new browser check-ins. Changing server paths requires existing files at the new location and a server restart. Empty client paths fall back to the server root.")), 1)]),
					createBaseVNode("div", _hoisted_10$1, [
						createVNode(_sfc_main$8, { name: record.value.status === "available" ? "check-circle" : "info" }, null, 8, ["name"]),
						createBaseVNode("span", null, toDisplayString(unref(t)(record.value.status === "available" ? "Available" : record.value.status === "inaccessible" ? "Folder not found or inaccessible" : "Not checked")), 1),
						createVNode(_sfc_main$9, {
							label: "Check paths",
							disabled: __props.busy,
							onClick: _cache[8] || (_cache[8] = ($event) => emit("check", Object.fromEntries(entries.value.filter((item) => item.alias !== "plugins").map((item) => [item.alias, root(item.alias)]))))
						}, null, 8, ["disabled"])
					])
				], 64)) : createCommentVNode("", true),
				createBaseVNode("details", _hoisted_11$1, [createBaseVNode("summary", null, toDisplayString(unref(t)("Advanced settings")), 1), renderSlot(_ctx.$slots, "default")])
			])]);
		};
	}
};
//#endregion
//#region src/features/configuration/Configuration.vue
var _hoisted_1 = ["aria-busy"];
var _hoisted_2 = { class: "configuration-header" };
var _hoisted_3 = { class: "configuration-brand" };
var _hoisted_4 = { id: "configuration-title" };
var _hoisted_5 = { class: "muted" };
var _hoisted_6 = { class: "configuration-page-heading" };
var _hoisted_7 = { class: "muted" };
var _hoisted_8 = { class: "configuration-actions" };
var _hoisted_9 = ["aria-label"];
var _hoisted_10 = [
	"aria-label",
	"aria-pressed",
	"onClick"
];
var _hoisted_11 = ["aria-label"];
var _hoisted_12 = { class: "configuration-pages" };
var _hoisted_13 = {
	key: 0,
	class: "error configuration-feedback",
	role: "alert"
};
var _hoisted_14 = {
	key: 1,
	class: "notice configuration-feedback",
	role: "status"
};
var _hoisted_15 = {
	key: 2,
	class: "configuration-server-overview"
};
var _hoisted_16 = { class: "content" };
var _hoisted_17 = { class: "settings-section" };
var _hoisted_18 = { class: "muted" };
var _hoisted_19 = { class: "configuration-group" };
var _hoisted_20 = {
	key: 3,
	class: "content appearance-page"
};
var _hoisted_21 = {
	key: 8,
	class: "content"
};
var _hoisted_22 = { class: "muted" };
var _hoisted_23 = {
	key: 9,
	class: "content"
};
var _hoisted_24 = { class: "settings-section" };
var _hoisted_25 = { class: "muted" };
var _hoisted_26 = { class: "configuration-group" };
var _hoisted_27 = {
	key: 10,
	class: "configuration-server-tools"
};
var _hoisted_28 = {
	key: 11,
	class: "muted configuration-feedback"
};
var _hoisted_29 = ["aria-label"];
var _hoisted_30 = { class: "muted" };
var _hoisted_31 = ["aria-label"];
var _hoisted_32 = ["aria-label"];
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
		const pages = [
			{
				id: "server",
				title: "Server",
				icon: "cloud",
				description: "Connection, sign-in status and server presets",
				help: "server_configuration",
				groups: [
					"Services and workers",
					"Network",
					"Database",
					"Security",
					"Directories and logs"
				]
			},
			{
				id: "repository",
				title: "Repositories",
				icon: "database",
				description: "Repository locations, availability and default storage",
				help: "repository_configuration",
				groups: ["File repository"]
			},
			{
				id: "project",
				title: "Projects",
				icon: "project-diagram",
				description: "Active project and workspace context",
				help: "configuration.projects"
			},
			{
				id: "checkin",
				title: "Check-in Options",
				icon: "tune",
				description: "Naming and file handling defaults",
				help: "configuration.checkin"
			},
			{
				id: "global",
				title: "Global",
				icon: "settings",
				description: "Application behavior and diagnostics",
				help: "configuration.global"
			},
			{
				id: "appearance",
				title: "Appearance",
				icon: "palette",
				description: "Themes, animations, language and rendering",
				help: "appearance"
			},
			{
				id: "cache",
				title: "Cache",
				icon: "cached",
				description: "Persistent server data and cache policy",
				help: "configuration.cache"
			},
			{
				id: "tasks",
				title: "Tasks",
				icon: "briefcase",
				description: "Task Browser layout and Notes inspector defaults",
				help: "configuration.tasks",
				groups: ["Task scheduling"]
			}
		];
		let savedPage;
		try {
			savedPage = localStorage.getItem("tactic_stream.configuration.page");
		} catch {}
		const page = ref(pages.some((item) => item.id === savedPage) ? savedPage : "server");
		const origin = location.origin;
		const current = computed(() => pages.find((item) => item.id === page.value));
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
			const groups = pages.find((item) => item.id === id)?.groups || [];
			return settingsDirty || id === "server" && JSON.stringify(networkDraft) !== networkBaseline.value || id === "global" && JSON.stringify(debugDraft) !== debugBaseline.value || (server.value?.configuration?.groups || []).some((group) => groups.includes(group.title) && server.value.groupChanged(group));
		}
		const dirty = computed(() => pages.some((item) => pageDirty(item.id)));
		const serverPages = computed(() => pages.filter((item) => item.groups).map((item) => item.id));
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
			if (server.value?.configuration && !server.value.hasChanges) server.value.load();
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
			const groups = pages.find((item) => item.id === id)?.groups;
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
			for (const item of pages) restore(item.id);
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
			const definition = pages.find((item) => item.id === id);
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
				page.value = pages.find((item) => item.groups?.includes(server.value.activeGroup))?.id || id;
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
				for (const id of all ? pages.map((item) => item.id) : [page.value]) if (!await applyPage(id)) return;
				notice.value = server.value?.configuration?.restart_required ? "Saved to XML. Restart the backend to apply these settings." : "Configuration applied";
				if (close) {
					confirmClose.value?.close();
					emit("close");
				}
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
				class: "configuration-shell configuration configuration-native",
				"aria-busy": busy.value
			}, [
				createBaseVNode("header", _hoisted_2, [createBaseVNode("div", _hoisted_3, [createBaseVNode("h2", _hoisted_4, toDisplayString(unref(t)("Configuration")), 1), createBaseVNode("small", _hoisted_5, "TACTIC STREAM · " + toDisplayString(unref(t)("Preferences")), 1)]), createBaseVNode("div", _hoisted_6, [createBaseVNode("div", null, [createBaseVNode("h1", null, toDisplayString(unref(t)(current.value.title)), 1), createBaseVNode("p", _hoisted_7, toDisplayString(unref(t)(current.value.description)), 1)]), createBaseVNode("div", _hoisted_8, [
					!unref(mobile) ? (openBlock(), createBlock(_sfc_main$9, {
						key: 0,
						label: "Reset",
						icon: "undo",
						disabled: busy.value || !pageDirty(page.value),
						title: unref(t)("Reset"),
						onClick: reset
					}, null, 8, ["disabled", "title"])) : createCommentVNode("", true),
					!unref(mobile) ? (openBlock(), createBlock(_sfc_main$9, {
						key: 1,
						label: "Apply",
						icon: "check",
						disabled: busy.value || !pageDirty(page.value),
						title: unref(t)("Apply"),
						onClick: _cache[0] || (_cache[0] = ($event) => apply())
					}, null, 8, ["disabled", "title"])) : createCommentVNode("", true),
					createVNode(_sfc_main$9, {
						label: "Save",
						icon: "save",
						disabled: busy.value || !dirty.value,
						"aria-label": unref(t)("Save configuration"),
						onClick: _cache[1] || (_cache[1] = ($event) => apply({ all: true }))
					}, null, 8, ["disabled", "aria-label"]),
					!unref(mobile) ? (openBlock(), createBlock(_sfc_main$9, {
						key: 2,
						label: "Configuration help",
						icon: "help",
						"icon-only": "",
						onClick: _cache[2] || (_cache[2] = ($event) => emit("help", current.value.help))
					})) : createCommentVNode("", true),
					unref(mobile) ? (openBlock(), createBlock(_sfc_main$16, {
						key: 3,
						label: "Configuration actions",
						overlay: ""
					}, {
						default: withCtx(() => [
							createVNode(_sfc_main$9, {
								label: "Reset",
								icon: "undo",
								disabled: busy.value || !pageDirty(page.value),
								onClick: reset
							}, null, 8, ["disabled"]),
							createVNode(_sfc_main$9, {
								label: "Apply",
								icon: "check",
								disabled: busy.value || !pageDirty(page.value),
								onClick: _cache[3] || (_cache[3] = ($event) => apply())
							}, null, 8, ["disabled"]),
							createVNode(_sfc_main$9, {
								label: "Configuration help",
								icon: "help",
								onClick: _cache[4] || (_cache[4] = ($event) => emit("help", current.value.help))
							})
						]),
						_: 1
					})) : createCommentVNode("", true),
					createVNode(_sfc_main$9, {
						label: "Close",
						icon: "close",
						"icon-only": "",
						disabled: busy.value,
						onClick: cancel
					}, null, 8, ["disabled"])
				])])]),
				createBaseVNode("nav", {
					class: "configuration-navigation",
					"aria-label": unref(t)("Configuration sections")
				}, [unref(mobile) ? (openBlock(), createBlock(_sfc_main$12, {
					key: 0,
					"model-value": page.value,
					options: pages.map((item) => ({
						value: item.id,
						label: item.title
					})),
					label: "Configuration sections",
					"onUpdate:modelValue": selectPage
				}, null, 8, ["model-value", "options"])) : (openBlock(), createElementBlock(Fragment, { key: 1 }, renderList(pages, (item) => {
					return createBaseVNode("button", {
						key: item.id,
						"aria-label": unref(t)(item.title),
						"aria-pressed": page.value === item.id,
						onClick: ($event) => selectPage(item.id)
					}, [
						createVNode(_sfc_main$8, { name: item.icon }, null, 8, ["name"]),
						createBaseVNode("span", null, toDisplayString(unref(t)(item.title)), 1),
						pageDirty(item.id) ? (openBlock(), createElementBlock("i", {
							key: 0,
							class: "configuration-dirty",
							"aria-label": unref(t)("Unsaved changes")
						}, null, 8, _hoisted_11)) : createCommentVNode("", true)
					], 8, _hoisted_10);
				}), 64))], 8, _hoisted_9),
				createBaseVNode("div", _hoisted_12, [
					error.value ? (openBlock(), createElementBlock("p", _hoisted_13, toDisplayString(unref(t)(error.value)), 1)) : createCommentVNode("", true),
					notice.value ? (openBlock(), createElementBlock("p", _hoisted_14, toDisplayString(unref(t)(notice.value)), 1)) : createCommentVNode("", true),
					page.value === "server" ? (openBlock(), createElementBlock("section", _hoisted_15, [createBaseVNode("section", _hoisted_16, [createBaseVNode("section", _hoisted_17, [createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)("Connection")), 1), createBaseVNode("p", _hoisted_18, toDisplayString(unref(t)("The browser uses the server that hosts this application.")), 1)]), createBaseVNode("div", _hoisted_19, [createVNode(_sfc_main$13, { title: "Server address" }, {
						default: withCtx(() => [createBaseVNode("code", null, toDisplayString(unref(origin)), 1)]),
						_: 1
					}), createVNode(_sfc_main$13, { title: "Current account" }, {
						default: withCtx(() => [createBaseVNode("span", null, toDisplayString(__props.login), 1)]),
						_: 1
					})])])]), createVNode(_sfc_main$5, { settings: networkDraft }, null, 8, ["settings"])])) : createCommentVNode("", true),
					page.value === "appearance" ? (openBlock(), createElementBlock("section", _hoisted_20, [createVNode(_sfc_main$10)])) : createCommentVNode("", true),
					page.value === "project" ? (openBlock(), createBlock(_sfc_main$3, {
						key: 4,
						ticket: __props.ticket,
						project: __props.project,
						"can-administer": __props.canAdminister,
						"open-project": __props.openProject
					}, null, 8, [
						"ticket",
						"project",
						"can-administer",
						"open-project"
					])) : createCommentVNode("", true),
					page.value === "repository" && __props.canAdminister ? (openBlock(), createBlock(_sfc_main$2, {
						key: 5,
						ref_key: "repositories",
						ref: repositories,
						ticket: __props.ticket,
						busy: busy.value,
						onEdit: _cache[5] || (_cache[5] = ($event) => repositoryEditor.value.show()),
						onSessionExpired: _cache[6] || (_cache[6] = ($event) => emit("session-expired"))
					}, null, 8, ["ticket", "busy"])) : createCommentVNode("", true),
					page.value in drafts && page.value !== "repository" ? (openBlock(), createBlock(_sfc_main$4, {
						key: 6,
						page: page.value,
						draft: drafts[page.value],
						busy: busy.value
					}, null, 8, [
						"page",
						"draft",
						"busy"
					])) : createCommentVNode("", true),
					page.value === "global" ? (openBlock(), createBlock(_sfc_main$6, {
						key: 7,
						settings: debugDraft
					}, null, 8, ["settings"])) : createCommentVNode("", true),
					page.value === "global" ? (openBlock(), createElementBlock("section", _hoisted_21, [createBaseVNode("p", _hoisted_22, toDisplayString(unref(t)("System tray, local worker threads, Handler Server and DCC connections belong to the desktop application. Browser requests use the server worker configuration.")), 1)])) : createCommentVNode("", true),
					page.value === "cache" ? (openBlock(), createElementBlock("section", _hoisted_23, [createBaseVNode("section", _hoisted_24, [createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)("Cache maintenance")), 1), createBaseVNode("p", _hoisted_25, toDisplayString(unref(t)("Authenticated server records stay in session memory. Project layouts and preferences are stored separately in this browser.")), 1)]), createBaseVNode("div", _hoisted_26, [createVNode(_sfc_main$13, {
						title: "Clear tabs cache",
						description: "Clear saved object, process and version expansion without closing search tabs."
					}, {
						default: withCtx(() => [createVNode(_sfc_main$9, {
							label: "Clear tabs cache",
							icon: "refresh",
							disabled: busy.value,
							onClick: _cache[7] || (_cache[7] = ($event) => {
								cacheScope.value = "tabs";
								confirmClear.value.showModal();
							})
						}, null, 8, ["disabled"])]),
						_: 1
					}), createVNode(_sfc_main$13, {
						title: "Clear all cached server data",
						description: "Search tabs will keep their layout, but server records will be loaded again when needed."
					}, {
						default: withCtx(() => [createVNode(_sfc_main$9, {
							label: "Clear cache",
							icon: "refresh",
							disabled: busy.value,
							onClick: _cache[8] || (_cache[8] = ($event) => {
								cacheScope.value = "server";
								confirmClear.value.showModal();
							})
						}, null, 8, ["disabled"])]),
						_: 1
					})])])])) : createCommentVNode("", true),
					__props.canAdminister && ["server", "tasks"].includes(page.value) && server.value?.configuration ? (openBlock(), createElementBlock("section", _hoisted_27, [createVNode(_sfc_main$12, {
						modelValue: server.value.activeGroup,
						"onUpdate:modelValue": _cache[9] || (_cache[9] = ($event) => server.value.activeGroup = $event),
						options: currentGroups.value.map((title) => ({
							value: title,
							label: title
						})),
						label: "Server settings section"
					}, null, 8, ["modelValue", "options"]), createVNode(AppSearchField_default, {
						modelValue: server.value.search,
						"onUpdate:modelValue": _cache[10] || (_cache[10] = ($event) => server.value.search = $event),
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
						onSessionExpired: _cache[11] || (_cache[11] = ($event) => emit("session-expired"))
					}, null, 8, ["group-titles", "ticket"])), [[vShow, serverPages.value.includes(page.value)]]) : createCommentVNode("", true)], 8, ["disabled"])),
					!__props.canAdminister && page.value === "repository" ? (openBlock(), createElementBlock("p", _hoisted_28, toDisplayString(unref(t)("Repository configuration requires administrator access.")), 1)) : createCommentVNode("", true)
				]),
				withDirectives((openBlock(), createElementBlock("dialog", {
					ref_key: "repositoryEditor",
					ref: repositoryEditor,
					class: "record-dialog configuration-repository-editor",
					"aria-label": unref(t)("Repository Editor")
				}, [
					createBaseVNode("header", null, [createBaseVNode("div", null, [createBaseVNode("h2", null, toDisplayString(unref(t)("Repository Editor")), 1), createBaseVNode("small", _hoisted_30, toDisplayString(unref(t)("Repository definitions")), 1)]), createVNode(_sfc_main$9, {
						"icon-only": "",
						icon: "close",
						label: "Close",
						disabled: busy.value,
						onClick: closeRepository
					}, null, 8, ["disabled"])]),
					createVNode(_sfc_main$1, {
						server: server.value,
						draft: drafts.repository,
						repositories: repositories.value?.records || [],
						busy: busy.value || repositories.value?.checking,
						onCheck: _cache[12] || (_cache[12] = ($event) => repositories.value.load("check", $event))
					}, {
						default: withCtx(() => [..._cache[17] || (_cache[17] = [createBaseVNode("div", { id: "configuration-repository-editor-body" }, null, -1)])]),
						_: 1
					}, 8, [
						"server",
						"draft",
						"repositories",
						"busy"
					]),
					createBaseVNode("footer", null, [
						createVNode(_sfc_main$9, {
							label: "Cancel",
							disabled: busy.value || !pageDirty("repository"),
							onClick: reset
						}, null, 8, ["disabled"]),
						createVNode(_sfc_main$9, {
							label: "Close",
							onClick: closeRepository
						}),
						createVNode(_sfc_main$9, {
							label: "Save",
							highlighted: "",
							disabled: busy.value || !pageDirty("repository"),
							onClick: _cache[13] || (_cache[13] = ($event) => apply())
						}, null, 8, ["disabled"])
					])
				], 8, _hoisted_29)), [[_directive_window, { type: "window" }]]),
				createBaseVNode("dialog", {
					ref_key: "confirmClose",
					ref: confirmClose,
					class: "record-dialog",
					"aria-label": unref(t)("Unsaved changes")
				}, [
					createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)("Unsaved changes")), 1)]),
					createBaseVNode("p", null, toDisplayString(unref(t)("Save changes before closing Configuration?")), 1),
					createBaseVNode("footer", null, [
						createVNode(_sfc_main$9, {
							label: "Continue editing",
							onClick: _cache[14] || (_cache[14] = ($event) => confirmClose.value.close())
						}),
						createVNode(_sfc_main$9, {
							label: "Discard changes",
							disabled: busy.value,
							onClick: discard
						}, null, 8, ["disabled"]),
						createVNode(_sfc_main$9, {
							label: "Save",
							icon: "save",
							disabled: busy.value,
							onClick: _cache[15] || (_cache[15] = ($event) => apply({
								all: true,
								close: true
							}))
						}, null, 8, ["disabled"])
					])
				], 8, _hoisted_31),
				createBaseVNode("dialog", {
					ref_key: "confirmClear",
					ref: confirmClear,
					class: "record-dialog",
					"aria-label": unref(t)(cacheScope.value === "tabs" ? "Clear saved branch expansion?" : "Clear cached server data?")
				}, [
					createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)(cacheScope.value === "tabs" ? "Clear saved branch expansion?" : "Clear cached server data?")), 1)]),
					createBaseVNode("p", null, toDisplayString(unref(t)(cacheScope.value === "tabs" ? "Object, process and version branches will collapse. Search tabs, filters and dock layouts remain unchanged." : "Projects, Search Types, search results and navigation will be downloaded again. Saved layouts and preferences remain unchanged.")), 1),
					createBaseVNode("footer", null, [createVNode(_sfc_main$9, {
						label: "Cancel",
						onClick: _cache[16] || (_cache[16] = ($event) => confirmClear.value.close())
					}), createVNode(_sfc_main$9, {
						label: cacheScope.value === "tabs" ? "Clear tabs cache" : "Clear cache",
						icon: "refresh",
						onClick: clearCache
					}, null, 8, ["label"])])
				], 8, _hoisted_32)
			], 8, _hoisted_1);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=Configuration.js.map