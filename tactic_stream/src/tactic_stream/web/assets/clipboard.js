import { G as withCtx, N as openBlock, P as renderList, T as mergeModels, V as useModel, Z as shallowReactive, _ as createCommentVNode, d as Fragment, et as unref, g as createBlock, h as createBaseVNode, m as computed, nt as normalizeStyle, rt as toDisplayString, tt as normalizeClass, v as createElementBlock, x as createVNode } from "./vue.js";
import { A as effectiveColorMode, D as t, M as languages, N as readableText, O as appearance, Q as themes, X as accentPresets, Z as iconSets, b as logRequest, f as debugLog, k as colorModes, o as _sfc_main$4, u as _sfc_main$5, x as redact } from "./index.js";
import { t as _sfc_main$6 } from "./AppSwitch.js";
import { t as _sfc_main$7 } from "./AppSelect.js";
import { t as _sfc_main$8 } from "./SettingRow.js";
//#region src/features/activity/notifications.js
var notificationHistory = shallowReactive({ records: [] });
var activeNotifications = shallowReactive({ records: [] });
var recent = /* @__PURE__ */ new Map();
var timers = /* @__PURE__ */ new Map();
var sequence = 0;
function notify(kind, message, detail = "", group = "client", key = "", source = {}) {
	if (![
		"info",
		"warning",
		"error",
		"progress",
		"complete"
	].includes(kind)) kind = "info";
	message = String(redact(message || "")).trim();
	if (!message) return;
	const now = Date.now(), signature = key || `${kind}:${message}`;
	if (activeNotifications.records.some((row) => row.dedupeKey === signature) || recent.has(signature) && now - recent.get(signature) < 5e3) return;
	recent.set(signature, now);
	for (const [value, stamp] of recent) if (now - stamp >= 3e4) recent.delete(value);
	const row = {
		notificationId: ++sequence,
		kind,
		group,
		message,
		detail: String(redact(detail || "")),
		timestamp: new Date(now).toISOString(),
		dedupeKey: signature,
		dismissible: true,
		sourceType: source.sourceType || "",
		sourceTitle: source.sourceTitle || "",
		previewUrl: source.previewUrl || "",
		avatarText: source.avatarText || "",
		avatarColor: source.avatarColor || "",
		sourceIcon: source.sourceIcon || "",
		action: source.action || "",
		actionData: source.actionData || "",
		canReply: source.canReply !== false,
		replyOpen: false,
		replySending: false,
		replyError: "",
		replyText: ""
	};
	notificationHistory.records = [row, ...notificationHistory.records].slice(0, 200);
	activeNotifications.records = [...activeNotifications.records, row];
	limitActive();
	startTimer(row.notificationId, row.sourceType === "messages" ? 15e3 : row.sourceType === "activity" ? 8e3 : ["error", "warning"].includes(kind) ? 5e3 : 3200);
	return row.notificationId;
}
function startTimer(id, duration) {
	clearTimeout(timers.get(id));
	const timer = setTimeout(() => dismissNotification(id), duration);
	timer.unref?.();
	timers.set(id, timer);
}
function limitActive() {
	while (activeNotifications.records.length > 3) dismissNotification((activeNotifications.records.find((row) => !row.replyOpen) || activeNotifications.records.at(-1)).notificationId);
}
function updateReply(id, values) {
	activeNotifications.records = activeNotifications.records.map((row) => row.notificationId === id ? {
		...row,
		...values
	} : row);
}
function beginNotificationReply(id) {
	const row = activeNotifications.records.find((row) => row.notificationId === id);
	if (!row || row.sourceType !== "messages" || !row.actionData || !row.canReply) return false;
	clearTimeout(timers.get(id));
	timers.delete(id);
	updateReply(id, { replyOpen: true });
	return true;
}
function cancelNotificationReply(id) {
	const row = activeNotifications.records.find((row) => row.notificationId === id);
	if (!row?.replyOpen || row.replySending) return;
	updateReply(id, {
		replyOpen: false,
		replyError: ""
	});
	startTimer(id, 15e3);
}
function editNotificationReply(id, text) {
	updateReply(id, { replyText: text });
}
function submitNotificationReply(id) {
	const row = activeNotifications.records.find((row) => row.notificationId === id);
	if (!row?.replyOpen || !row.canReply || row.replySending || !row.replyText.trim()) return false;
	updateReply(id, {
		replySending: true,
		replyError: ""
	});
	return true;
}
function failNotificationReply(id, error) {
	updateReply(id, {
		replySending: false,
		replyError: error || "Unable to send message"
	});
}
function dismissNotification(id) {
	clearTimeout(timers.get(id));
	timers.delete(id);
	activeNotifications.records = activeNotifications.records.filter((row) => row.notificationId !== id);
}
function setNotificationProgress(message) {
	const id = "application-progress";
	if (!message) {
		dismissNotification(id);
		return;
	}
	const row = {
		notificationId: id,
		kind: "progress",
		message,
		detail: "",
		dismissible: false
	};
	if (activeNotifications.records.findIndex((row) => row.notificationId === id) >= 0) activeNotifications.records = activeNotifications.records.map((item) => item.notificationId === id ? row : item);
	else {
		activeNotifications.records = [...activeNotifications.records, row];
		limitActive();
	}
}
function clearNotificationHistory() {
	notificationHistory.records = [];
}
function resetNotifications() {
	for (const timer of timers.values()) clearTimeout(timer);
	timers.clear();
	recent.clear();
	activeNotifications.records = [];
	clearNotificationHistory();
}
//#endregion
//#region src/features/connection/updateRequests.js
var available = true;
var pending = /* @__PURE__ */ new Map();
var unavailable = () => Object.assign(/* @__PURE__ */ new Error("Unable to reach the server."), { code: "updates_unavailable" });
function setUpdatesAvailable(value) {
	available = value;
	if (!value) for (const { controller } of pending.values()) controller.abort(unavailable());
}
function updatesAvailable() {
	return available;
}
function backgroundRequest(key, request) {
	if (!available) return Promise.reject(unavailable());
	if (pending.has(key)) return pending.get(key).promise;
	const controller = new AbortController();
	const entry = { controller };
	pending.set(key, entry);
	entry.promise = Promise.resolve().then(() => {
		if (controller.signal.aborted) throw controller.signal.reason;
		return request(AbortSignal.any([controller.signal, AbortSignal.timeout(3e4)]));
	}).finally(() => {
		if (pending.get(key) === entry) pending.delete(key);
	});
	return entry.promise;
}
function updateDelay(interval, failures = 0, random = Math.random) {
	if (!failures) return Math.round(interval * 1e3 * (.85 + random() * .3));
	const base = failures < 5 ? 2e3 * 2 ** (failures - 1) : failures === 5 ? 3e4 : 6e4;
	return Math.round(base * (1 + random() * .25));
}
//#endregion
//#region src/api.js
var requestActivity = shallowReactive({ pending: [] });
function resetRequestActivity() {
	requestActivity.pending = [];
}
function beginActivity(ticket, message = "Working…") {
	if (!ticket) return;
	const entry = {
		ticket,
		message
	};
	requestActivity.pending = [...requestActivity.pending, entry];
	return entry;
}
function endActivity(entry) {
	if (entry) requestActivity.pending = requestActivity.pending.filter((item) => item !== entry);
}
async function rpc(method, args = [], kwargs = {}, quiet = false, background = false) {
	const payload = {
		method,
		args,
		kwargs
	};
	return background ? backgroundPost("/admin/rpc", payload) : post("/admin/rpc", payload, void 0, quiet);
}
function scriptEditor(action, ticket, project, values = {}) {
	return post(`/admin/script-editor/${action}`, {
		ticket,
		project,
		...values
	}, void 0, action === "analyse");
}
function activityFeed(ticket, project, values = {}, quiet = false) {
	const payload = {
		ticket,
		project,
		...values
	};
	return quiet ? backgroundPost("/admin/activity-feed", payload) : post("/admin/activity-feed", payload);
}
function serverUpdates(ticket, project, values = {}, signal) {
	return post("/admin/server-updates", {
		ticket,
		project,
		...values
	}, AbortSignal.any([AbortSignal.timeout(3e4), ...signal ? [signal] : []]), true);
}
function navigationLink(ticket, project, link) {
	return post("/admin/navigation-link", {
		ticket,
		project,
		link
	});
}
function linkPreviews(ticket, project, keys) {
	return backgroundPost("/admin/navigation-link", {
		ticket,
		project,
		keys
	});
}
async function sessionAction(action, ticket) {
	return post(`/admin/session/${action}`, { ticket });
}
async function serverConfiguration(ticket) {
	return post("/admin/configuration", { ticket });
}
function rawDatabase(action, ticket, project, values = {}) {
	return post("/admin/raw-database/" + action, {
		ticket,
		project,
		...values
	});
}
async function interfaceDefinition(ticket, project, search_type, view = "table") {
	return post("/admin/interface", {
		ticket,
		project,
		search_type,
		view
	});
}
function tableCells(ticket, project, search_type, view, search_keys) {
	return post("/admin/table-cells", {
		ticket,
		project,
		search_type,
		view,
		search_keys
	});
}
function resultItems(ticket, project, search_type, search_keys, values = {}) {
	return post("/admin/result-items", {
		ticket,
		project,
		search_type,
		search_keys,
		...values
	});
}
async function projectNavigation(ticket, project) {
	return post("/admin/navigation", {
		ticket,
		project
	});
}
async function projectCatalog(ticket) {
	return post("/admin/project-catalog", {
		ticket,
		project: "admin"
	});
}
async function projectCreationCatalog(ticket) {
	return post("/admin/project-creation", {
		ticket,
		project: "admin"
	});
}
async function formDefinition(ticket, project, search_type, view, search_key, source_key, relation = {}) {
	return post("/admin/form", {
		ticket,
		project,
		search_type,
		view,
		...Array.isArray(search_key) ? { search_keys: search_key } : { search_key },
		source_key,
		...relation
	});
}
async function objectRelations(ticket, project, search_type, search_key) {
	return post("/admin/object-relations", {
		ticket,
		project,
		search_type,
		search_key
	});
}
async function objectDeletion(action, ticket, project, search_type, view, search_key, related_types) {
	const selection = Array.isArray(search_key) ? { search_keys: search_key } : { search_key };
	return post(`/admin/object-deletion/${action}`, {
		ticket,
		project,
		search_type,
		view,
		...selection,
		related_types
	});
}
async function objectStatus(ticket, project, search_type, view, search_keys, operation) {
	return post("/admin/object-status", {
		ticket,
		project,
		search_type,
		view,
		search_keys,
		operation
	});
}
async function widgetConfiguration(action, ticket, project, search_type, view, values = {}) {
	return post(`/admin/widget-configuration/${action}`, {
		ticket,
		project,
		search_type,
		view,
		...values
	});
}
async function uploadFormFile(ticket, project, file, { signal, filename } = {}) {
	const body = new FormData();
	body.append("login_ticket", ticket);
	body.append("file", file, filename || file.name);
	const url = `/tactic/${encodeURIComponent(project)}/UploadServer/`;
	const started = performance.now(), session = debugLog.sessionId;
	const activity = beginActivity(ticket, "Uploading");
	let data, failure;
	try {
		const response = await fetch(url, {
			method: "POST",
			body,
			cache: "no-store",
			signal
		});
		data = await response.json().catch(() => null);
		if (!response.ok || !Array.isArray(data) || data.length !== 1 || typeof data[0] !== "string") {
			const error = new Error(data?.error || "File upload failed.");
			error.status = response.ok ? 502 : response.status;
			throw error;
		}
		return data[0].replaceAll("\\", "/").split("/").pop();
	} catch (error) {
		failure = error;
		throw error;
	} finally {
		endActivity(activity);
		recordRequest(url, {
			ticket,
			project,
			file: {
				name: file.name,
				type: file.type,
				size: file.size
			}
		}, data, failure, started, session);
	}
}
async function messageFileRequest(ticket, project, values, file, channel = "messages") {
	const upload = !!file, url = "/admin/" + channel + "/" + (upload ? "upload" : "file");
	const payload = {
		ticket,
		project,
		...values
	}, started = performance.now(), session = debugLog.sessionId;
	const activity = beginActivity(ticket, upload ? "Uploading" : "Downloading");
	let data, failure;
	try {
		const body = upload ? new FormData() : JSON.stringify(payload);
		if (upload) {
			for (const [key, value] of Object.entries(payload)) body.append(key, value);
			body.append("file", file);
		}
		const response = await fetch(url, {
			method: "POST",
			body,
			headers: upload ? void 0 : { "Content-Type": "application/json" },
			cache: "no-store"
		});
		if (!response.ok) {
			data = await response.json();
			const error = new Error(data.error || "File request failed.");
			error.code = data.error_code;
			error.status = response.status;
			throw error;
		}
		if (upload) {
			data = await response.json();
			return data.result;
		}
		const blob = await response.blob();
		data = {
			size: blob.size,
			type: blob.type
		};
		return blob;
	} catch (error) {
		failure = error;
		throw error;
	} finally {
		endActivity(activity);
		recordRequest(url, {
			...payload,
			...upload ? { file: {
				name: file.name,
				size: file.size
			} } : {}
		}, data, failure, started, session, true);
	}
}
async function saveServerConfiguration(ticket, changes, revision) {
	return post("/admin/configuration/save", {
		ticket,
		changes,
		revision
	});
}
function backgroundPost(url, payload) {
	return backgroundRequest(JSON.stringify([url, payload]), (signal) => post(url, payload, signal, true));
}
async function post(url, payload, signal, quiet = false) {
	const started = performance.now(), session = debugLog.sessionId;
	const activity = quiet ? void 0 : beginActivity(payload.ticket || payload.args?.[0]?.ticket);
	let data, failure;
	try {
		const response = await fetch(url, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(payload),
			cache: "no-store",
			signal
		});
		data = await response.json();
		if (!response.ok) {
			const error = new Error(data.error || "Request failed.");
			error.status = response.status;
			error.code = data.error_code;
			error.field = data.error_field;
			throw error;
		}
		return data.result;
	} catch (error) {
		failure = error;
		throw error;
	} finally {
		endActivity(activity);
		recordRequest(url, payload, data, failure, started, session, quiet);
	}
}
function recordRequest(url, payload, data, failure, started, session, quiet = false) {
	if (session === debugLog.sessionId) {
		try {
			logRequest(url, payload, data, failure, (performance.now() - started) / 1e3);
		} catch {
			debugLog.storageError = "A request could not be recorded in Debug Log.";
		}
		if (url === "/admin/server-updates" || url.includes("/UploadServer/") || payload.method === "simple_checkin") return;
		if (quiet && failure && (failure instanceof TypeError || ["TimeoutError", "AbortError"].includes(failure.name) || failure.code === "updates_unavailable")) return;
		if (failure) notify("error", failure instanceof TypeError ? "Unable to reach the server." : failure.message, "", "server");
		else if (!quiet && ([
			"execute_cmd",
			"execute_python_script",
			"insert",
			"update",
			"delete_sobject",
			"retire_sobject",
			"reactivate_sobject"
		].includes(payload.method) || /\/(save|apply|create|delete|commit|activate|run|execute)$/.test(url))) notify("complete", "Server operation completed", payload.method || url, "server");
	}
}
function sidebarRequest(action, ticket, project, values = {}) {
	return post("/admin/sidebar/" + action, {
		ticket,
		project,
		...values
	});
}
function workspaceLayouts(action, ticket, project, values = {}) {
	return post("/admin/workspace-layout/" + action, {
		ticket,
		project,
		...values
	});
}
function scriptShelf(action, ticket, project, values = {}) {
	return post("/admin/script-shelf/" + action, {
		ticket,
		project,
		...values
	});
}
function searchConfiguration(action, ticket, project, search_type, values = {}, quiet = false) {
	return post("/admin/search-configuration/" + action, {
		ticket,
		project,
		search_type,
		...values
	}, void 0, quiet);
}
function securityGroups(action, ticket, values = {}) {
	return post("/admin/security-groups/" + action, {
		ticket,
		project: "sthpw",
		...values
	});
}
function securityRules(action, ticket, project, values = {}) {
	return post("/admin/security-rules/" + action, {
		ticket,
		project,
		...values
	});
}
function securityUsers(action, ticket, values = {}) {
	return post("/admin/security-users/" + action, {
		ticket,
		project: "sthpw",
		...values
	});
}
function columnsEditor(action, ticket, project, values = {}) {
	return post("/admin/columns-editor/" + action, {
		ticket,
		project,
		...values
	});
}
function transactionDetails(ticket, project, searchKey) {
	return post("/admin/transaction-log/details", {
		ticket,
		project,
		search_key: searchKey
	});
}
function messagesRequest(action, ticket, project, values = {}) {
	const url = "/admin/messages/" + action, payload = {
		ticket,
		project,
		...values
	};
	return ["list", "history"].includes(action) ? backgroundPost(url, payload) : post(url, payload, void 0, true);
}
function knowledgeRequest(action, ticket, project, values = {}) {
	return post("/admin/knowledge/" + action, {
		ticket,
		project,
		...values
	}, void 0, true);
}
function userProfile(action, ticket, project, values = {}) {
	return post("/admin/user-profile/" + action, {
		ticket,
		project,
		...values
	});
}
async function userAvatar(ticket, project, login, revision, token, file) {
	const url = "/admin/user-profile/avatar", payload = {
		ticket,
		project,
		login,
		revision,
		token
	};
	const activity = beginActivity(ticket, "Uploading"), started = performance.now(), session = debugLog.sessionId;
	let data, failure;
	try {
		const body = new FormData();
		for (const [key, value] of Object.entries(payload)) body.append(key, value);
		body.append("file", file);
		const response = await fetch(url, {
			method: "POST",
			body,
			cache: "no-store"
		});
		data = await response.json();
		if (!response.ok) {
			const error = new Error(data.error?.message || data.error || "Unable to upload avatar");
			error.status = response.status;
			error.code = data.error_code;
			throw error;
		}
		return data.result;
	} catch (error) {
		failure = error;
		throw error;
	} finally {
		endActivity(activity);
		recordRequest(url, {
			...payload,
			file: {
				name: file.name,
				size: file.size
			}
		}, data, failure, started, session);
	}
}
//#endregion
//#region src/controls/AccentPresetPicker.vue
var _hoisted_1$3 = ["aria-label"];
var _sfc_main$3 = {
	__name: "AccentPresetPicker",
	props: /*@__PURE__*/ mergeModels({
		options: Array,
		mode: String,
		label: String
	}, {
		"modelValue": {},
		"modelModifiers": {}
	}),
	emits: ["update:modelValue"],
	setup(__props) {
		const model = useModel(__props, "modelValue");
		function foreground(hex) {
			return readableText([
				1,
				3,
				5
			].map((index) => parseInt(hex.slice(index, index + 2), 16)));
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				class: "accent-preset-picker",
				role: "group",
				"aria-label": __props.label
			}, [(openBlock(true), createElementBlock(Fragment, null, renderList(__props.options, (preset) => {
				return openBlock(), createBlock(_sfc_main$4, {
					key: preset.value,
					label: preset.label,
					title: preset.label,
					"aria-pressed": model.value === preset.value,
					style: normalizeStyle({
						"--preset-base": preset[__props.mode + "Base"],
						"--preset-accent": preset[__props.mode],
						"--preset-text": foreground(preset[__props.mode])
					}),
					onClick: ($event) => model.value = preset.value
				}, {
					default: withCtx(() => [createBaseVNode("span", null, [model.value === preset.value ? (openBlock(), createBlock(_sfc_main$5, {
						key: 0,
						name: "check"
					})) : createCommentVNode("", true)])]),
					_: 2
				}, 1032, [
					"label",
					"title",
					"aria-pressed",
					"style",
					"onClick"
				]);
			}), 128))], 8, _hoisted_1$3);
		};
	}
};
//#endregion
//#region src/features/configuration/AppearanceSettings.vue
var _hoisted_1$2 = { key: 0 };
var _hoisted_2$1 = { class: "muted" };
var _hoisted_3$1 = {
	key: 0,
	class: "settings-section"
};
var _hoisted_4$1 = { class: "muted" };
var _hoisted_5 = { class: "configuration-group" };
var _hoisted_6 = {
	key: 1,
	class: "settings-section"
};
var _hoisted_7 = { class: "muted" };
var _hoisted_8 = { class: "configuration-group" };
var _hoisted_9 = ["aria-label"];
var _hoisted_10 = { class: "muted" };
var _sfc_main$2 = {
	__name: "AppearanceSettings",
	props: { compact: Boolean },
	setup(__props) {
		const prefix = __props.compact ? "quick-" : "settings-";
		const darkMode = computed({
			get: () => effectiveColorMode.value === "dark",
			set: (value) => {
				appearance.mode = value ? "dark" : "light";
			}
		});
		const animations = [
			{
				key: "clickAnimations",
				label: "Click animations",
				description: "Animate press feedback, ripples, switches, and disclosure controls."
			},
			{
				key: "hoverAnimations",
				label: "Hover animations",
				description: "Animate pointer hover feedback. When disabled, hover states change instantly."
			},
			{
				key: "fadeAnimations",
				label: "Fades and transitions",
				description: "Animate appearing content, view transitions, expansion, and other interface fades."
			},
			{
				key: "popupAnimations",
				label: "Menu and popup animations",
				description: "Animate opening and closing menus, dropdowns, and popups."
			}
		];
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", { class: normalizeClass(["appearance-settings", { "compact-settings": __props.compact }]) }, [
				createBaseVNode("section", { class: normalizeClass({ "settings-section": !__props.compact }) }, [!__props.compact ? (openBlock(), createElementBlock("header", _hoisted_1$2, [createBaseVNode("h2", null, toDisplayString(unref(t)("Appearance")), 1), createBaseVNode("p", _hoisted_2$1, toDisplayString(unref(t)("Choose the interface style, color mode, palettes, and semantic icon set.")), 1)])) : createCommentVNode("", true), createBaseVNode("div", { class: normalizeClass({ "configuration-group": !__props.compact }) }, [
					__props.compact ? (openBlock(), createBlock(_sfc_main$8, {
						key: 0,
						"control-id": unref(prefix) + "language",
						title: "Interface language",
						description: "Changes application labels and help text while project-defined names remain unchanged."
					}, {
						default: withCtx(() => [createVNode(_sfc_main$7, {
							id: unref(prefix) + "language",
							modelValue: unref(appearance).language,
							"onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => unref(appearance).language = $event),
							options: unref(languages),
							label: "Interface language",
							"aria-describedby": unref(prefix) + "language-help"
						}, null, 8, [
							"id",
							"modelValue",
							"options",
							"aria-describedby"
						])]),
						_: 1
					}, 8, ["control-id"])) : createCommentVNode("", true),
					!__props.compact ? (openBlock(), createBlock(_sfc_main$8, {
						key: 1,
						"control-id": unref(prefix) + "dark",
						title: "Dark color mode",
						description: "Use dark surfaces and the dark palette assigned to the selected interface style."
					}, {
						default: withCtx(() => [createVNode(_sfc_main$6, {
							id: unref(prefix) + "dark",
							modelValue: darkMode.value,
							"onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => darkMode.value = $event),
							label: "Dark color mode",
							"aria-describedby": unref(prefix) + "dark-help"
						}, null, 8, [
							"id",
							"modelValue",
							"aria-describedby"
						])]),
						_: 1
					}, 8, ["control-id"])) : createCommentVNode("", true),
					createVNode(_sfc_main$8, {
						"control-id": unref(prefix) + "theme",
						title: "Interface style",
						description: unref(themes).find((item) => item.value === unref(appearance).theme).description
					}, {
						default: withCtx(() => [createVNode(_sfc_main$7, {
							id: unref(prefix) + "theme",
							modelValue: unref(appearance).theme,
							"onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => unref(appearance).theme = $event),
							options: unref(themes),
							label: "Interface style",
							"aria-describedby": unref(prefix) + "theme-help"
						}, null, 8, [
							"id",
							"modelValue",
							"options",
							"aria-describedby"
						])]),
						_: 1
					}, 8, ["control-id", "description"]),
					__props.compact ? (openBlock(), createBlock(_sfc_main$8, {
						key: 2,
						"control-id": unref(prefix) + "mode",
						title: "Color mode",
						description: "Choose light or dark surfaces, or follow the system preference."
					}, {
						default: withCtx(() => [createVNode(_sfc_main$7, {
							id: unref(prefix) + "mode",
							modelValue: unref(appearance).mode,
							"onUpdate:modelValue": _cache[3] || (_cache[3] = ($event) => unref(appearance).mode = $event),
							options: unref(colorModes),
							label: "Color mode",
							"aria-describedby": unref(prefix) + "mode-help"
						}, null, 8, [
							"id",
							"modelValue",
							"options",
							"aria-describedby"
						])]),
						_: 1
					}, 8, ["control-id"])) : createCommentVNode("", true),
					!__props.compact ? (openBlock(), createElementBlock(Fragment, { key: 3 }, renderList(["light", "dark"], (mode) => {
						return createVNode(_sfc_main$8, {
							key: mode,
							class: "appearance-palette-row",
							"control-id": unref(prefix) + mode + "-palette",
							title: mode === "light" ? "Light mode palette" : "Dark mode palette",
							description: mode === "light" ? "Base surface and accent used when the application is in light mode." : "Base surface and accent used when the application is in dark mode."
						}, {
							default: withCtx(() => [createVNode(_sfc_main$3, {
								id: unref(prefix) + mode + "-palette",
								modelValue: unref(appearance).themeAccents[unref(appearance).theme][mode],
								"onUpdate:modelValue": ($event) => unref(appearance).themeAccents[unref(appearance).theme][mode] = $event,
								options: unref(accentPresets),
								mode,
								label: unref(t)(mode === "light" ? "Light mode palette" : "Dark mode palette"),
								"aria-describedby": unref(prefix) + mode + "-palette-help"
							}, null, 8, [
								"id",
								"modelValue",
								"onUpdate:modelValue",
								"options",
								"mode",
								"label",
								"aria-describedby"
							])]),
							_: 2
						}, 1032, [
							"control-id",
							"title",
							"description"
						]);
					}), 64)) : createCommentVNode("", true),
					createVNode(_sfc_main$8, {
						"control-id": unref(prefix) + "icons",
						title: "Icon set",
						description: unref(iconSets).find((item) => item.value === unref(appearance).iconSet).description
					}, {
						default: withCtx(() => [createVNode(_sfc_main$7, {
							id: unref(prefix) + "icons",
							modelValue: unref(appearance).iconSet,
							"onUpdate:modelValue": _cache[4] || (_cache[4] = ($event) => unref(appearance).iconSet = $event),
							options: unref(iconSets),
							label: "Icon set",
							"aria-describedby": unref(prefix) + "icons-help"
						}, null, 8, [
							"id",
							"modelValue",
							"options",
							"aria-describedby"
						])]),
						_: 1
					}, 8, ["control-id", "description"]),
					!__props.compact ? (openBlock(), createElementBlock(Fragment, { key: 4 }, renderList(animations, (animation) => {
						return createVNode(_sfc_main$8, {
							key: animation.key,
							"control-id": unref(prefix) + animation.key,
							title: animation.label,
							description: animation.description
						}, {
							default: withCtx(() => [createVNode(_sfc_main$6, {
								id: unref(prefix) + animation.key,
								modelValue: unref(appearance)[animation.key],
								"onUpdate:modelValue": ($event) => unref(appearance)[animation.key] = $event,
								label: animation.label,
								"aria-describedby": unref(prefix) + animation.key + "-help"
							}, null, 8, [
								"id",
								"modelValue",
								"onUpdate:modelValue",
								"label",
								"aria-describedby"
							])]),
							_: 2
						}, 1032, [
							"control-id",
							"title",
							"description"
						]);
					}), 64)) : createCommentVNode("", true)
				], 2)], 2),
				!__props.compact ? (openBlock(), createElementBlock("section", _hoisted_3$1, [createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)("Language")), 1), createBaseVNode("p", _hoisted_4$1, toDisplayString(unref(t)("Choose the language used by the application interface.")), 1)]), createBaseVNode("div", _hoisted_5, [createVNode(_sfc_main$8, {
					"control-id": unref(prefix) + "language",
					title: "Interface language",
					description: "Changes application labels and help text while project-defined names remain unchanged."
				}, {
					default: withCtx(() => [createVNode(_sfc_main$7, {
						id: unref(prefix) + "language",
						modelValue: unref(appearance).language,
						"onUpdate:modelValue": _cache[5] || (_cache[5] = ($event) => unref(appearance).language = $event),
						options: unref(languages),
						label: "Interface language",
						"aria-describedby": unref(prefix) + "language-help"
					}, null, 8, [
						"id",
						"modelValue",
						"options",
						"aria-describedby"
					])]),
					_: 1
				}, 8, ["control-id"])])])) : createCommentVNode("", true),
				!__props.compact ? (openBlock(), createElementBlock("section", _hoisted_6, [
					createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)("Browser preferences")), 1), createBaseVNode("p", _hoisted_7, toDisplayString(unref(t)("Additional browser features remain available alongside the Handler layout.")), 1)]),
					createBaseVNode("div", _hoisted_8, [
						createVNode(_sfc_main$8, {
							"control-id": unref(prefix) + "mode",
							title: "Color mode",
							description: "Choose light or dark surfaces, or follow the system preference."
						}, {
							default: withCtx(() => [createVNode(_sfc_main$7, {
								id: unref(prefix) + "mode",
								modelValue: unref(appearance).mode,
								"onUpdate:modelValue": _cache[6] || (_cache[6] = ($event) => unref(appearance).mode = $event),
								options: unref(colorModes),
								label: "Color mode",
								"aria-describedby": unref(prefix) + "mode-help"
							}, null, 8, [
								"id",
								"modelValue",
								"options",
								"aria-describedby"
							])]),
							_: 1
						}, 8, ["control-id"]),
						createVNode(_sfc_main$8, {
							"control-id": unref(prefix) + "discussion",
							title: "Object notes",
							description: "Open object and process notes in the Task Inspector, or use a separate notes-only window."
						}, {
							default: withCtx(() => [createVNode(_sfc_main$7, {
								id: unref(prefix) + "discussion",
								modelValue: unref(appearance).discussionView,
								"onUpdate:modelValue": _cache[7] || (_cache[7] = ($event) => unref(appearance).discussionView = $event),
								options: [{
									value: "inspector",
									label: "Task Inspector"
								}, {
									value: "notes",
									label: "Standalone notes"
								}],
								label: "Object notes",
								"aria-describedby": unref(prefix) + "discussion-help"
							}, null, 8, [
								"id",
								"modelValue",
								"aria-describedby"
							])]),
							_: 1
						}, 8, ["control-id"]),
						createBaseVNode("div", {
							class: "icon-preview",
							"aria-label": unref(t)("Icon preview")
						}, [(openBlock(), createElementBlock(Fragment, null, renderList([
							"menu",
							"edit",
							"link",
							"activity",
							"connection",
							"queue",
							"history",
							"appearance",
							"settings",
							"search",
							"add"
						], (name) => {
							return createVNode(_sfc_main$5, {
								key: name,
								name
							}, null, 8, ["name"]);
						}), 64))], 8, _hoisted_9)
					]),
					createBaseVNode("p", _hoisted_10, toDisplayString(unref(t)("The system reduced-motion preference takes priority over animation settings.")) + " " + toDisplayString(unref(t)("Graphics backend selection belongs to Qt. The browser controls web rendering.")), 1)
				])) : createCommentVNode("", true)
			], 2);
		};
	}
};
//#endregion
//#region src/features/configuration/AppearanceControls.vue
var _hoisted_1$1 = { class: "appearance-controls" };
var _hoisted_2 = ["aria-label", "title"];
var _hoisted_3 = {
	key: 0,
	class: "appearance-title"
};
var _hoisted_4 = { class: "appearance-options" };
var _sfc_main$1 = {
	__name: "AppearanceControls",
	props: { compact: Boolean },
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("details", _hoisted_1$1, [createBaseVNode("summary", {
				class: normalizeClass({ "icon-button": __props.compact }),
				"aria-label": unref(t)("Appearance"),
				title: unref(t)("Appearance")
			}, [createVNode(_sfc_main$5, { name: "appearance" }), !__props.compact ? (openBlock(), createElementBlock("span", _hoisted_3, toDisplayString(unref(t)("Appearance")), 1)) : createCommentVNode("", true)], 10, _hoisted_2), createBaseVNode("div", _hoisted_4, [createVNode(_sfc_main$2, { compact: "" })])]);
		};
	}
};
//#endregion
//#region src/controls/pythonSyntax.js
var keywords = new Set("False None True and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield".split(" "));
function xmlTokens(source) {
	const tokens = [];
	let end = 0;
	for (const match of source.matchAll(/<!--[\s\S]*?(?:-->|$)|<!\[CDATA\[[\s\S]*?(?:\]\]>|$)|<\/?[\w:.-]+|\/?>|"[^"\n]*"|'[^'\n]*'|[\w:.-]+(?=\s*=)|&(?:#\w+|\w+);/g)) {
		if (match.index > end) tokens.push({
			text: source.slice(end, match.index),
			role: ""
		});
		const text = match[0], role = text.startsWith("<!--") ? "comment" : /^["']/.test(text) || text.startsWith("<![CDATA[") ? "string" : text.startsWith("<") || text.endsWith(">") ? "keyword" : text.startsWith("&") ? "number" : "type";
		tokens.push({
			text,
			role
		});
		end = match.index + text.length;
	}
	if (end < source.length) tokens.push({
		text: source.slice(end),
		role: ""
	});
	return tokens;
}
var builtins = new Set("abs all any bool bytes callable chr dict enumerate filter float format getattr hasattr int isinstance issubclass iter len list map max min next object open ord print property range repr reversed round set setattr slice sorted staticmethod str sum super tuple type zip Exception ValueError TypeError RuntimeError KeyError".split(" "));
var pattern = /#[^\n]*|(?<!\w)(?:[furb]{1,2})?(?:"""(?:\\[\s\S]|(?!""")[^\\])*?(?:"""|$)|'''(?:\\[\s\S]|(?!''')[^\\])*?(?:'''|$)|"(?:\\[^\n]|[^"\\\n])*(?:"|$)|'(?:\\[^\n]|[^'\\\n])*(?:'|$))|\b(?:0x[\da-f_]+|0b[01_]+|0o[0-7_]+|\d[\d_]*(?:\.[\d_]*)?(?:e[+-]?[\d_]+)?j?)\b|\.[\d_]+(?:e[+-]?[\d_]+)?j?\b|@[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*|\b[A-Za-z_]\w*\b/gi;
function pythonTokens(source, moduleNames = []) {
	const tokens = [];
	let end = 0;
	let previous = "";
	for (const match of source.matchAll(pattern)) {
		if (match.index > end) tokens.push({
			text: source.slice(end, match.index),
			role: ""
		});
		const text = match[0];
		const role = text.startsWith("#") ? "comment" : /^(?:[furb]{0,2})["']/i.test(text) ? "string" : /^[\d.]/.test(text) ? "number" : text.startsWith("@") ? "decorator" : keywords.has(text) ? "keyword" : ["def", "class"].includes(previous) ? "definition" : moduleNames?.includes(text) ? "module" : ["self", "cls"].includes(text) ? "self" : builtins.has(text) ? "type" : /^\s*\(/.test(source.slice(match.index + text.length)) ? "function" : "";
		tokens.push({
			text,
			role
		});
		previous = text;
		end = match.index + text.length;
	}
	if (end < source.length) tokens.push({
		text: source.slice(end),
		role: ""
	});
	return tokens;
}
var jsKeywords = new Set("async await break case catch class const continue debugger default delete do else export extends finally for function if import in instanceof let new of return static super switch this throw try typeof var void while with yield true false null undefined".split(" "));
function javascriptTokens(source) {
	const tokens = [];
	let end = 0, previous = "";
	for (const match of source.matchAll(/\/\/[^\n]*|\/\*[\s\S]*?(?:\*\/|$)|"(?:\\[\s\S]|[^"\\])*(?:"|$)|'(?:\\[\s\S]|[^'\\])*(?:'|$)|`(?:\\[\s\S]|[^`\\])*(?:`|$)|\b(?:0x[\da-f]+|\d+(?:\.\d+)?(?:e[+-]?\d+)?)\b|\b[$A-Za-z_][$\w]*\b/gi)) {
		if (match.index > end) tokens.push({
			text: source.slice(end, match.index),
			role: ""
		});
		const text = match[0], role = text.startsWith("//") || text.startsWith("/*") ? "comment" : /^["'`]/.test(text) ? "string" : /^\d/.test(text) ? "number" : jsKeywords.has(text) ? "keyword" : ["function", "class"].includes(previous) ? "definition" : /^\s*\(/.test(source.slice(match.index + text.length)) ? "function" : "";
		tokens.push({
			text,
			role
		});
		previous = text;
		end = match.index + text.length;
	}
	if (end < source.length) tokens.push({
		text: source.slice(end),
		role: ""
	});
	return tokens;
}
//#endregion
//#region src/controls/CodeBlock.vue
var _hoisted_1 = {
	class: "code-block",
	tabindex: "0"
};
var _sfc_main = {
	__name: "CodeBlock",
	props: {
		code: {
			type: String,
			default: ""
		},
		language: {
			type: String,
			default: "python"
		}
	},
	setup(__props) {
		const props = __props;
		const tokens = computed(() => props.language === "text" ? [{ text: props.code }] : props.language === "xml" ? xmlTokens(props.code) : props.language === "javascript" ? javascriptTokens(props.code) : pythonTokens(props.code));
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("pre", _hoisted_1, [createBaseVNode("code", null, [(openBlock(true), createElementBlock(Fragment, null, renderList(tokens.value, (token, index) => {
				return openBlock(), createElementBlock("span", {
					key: index,
					class: normalizeClass(token.role ? "syntax-" + token.role : void 0)
				}, toDisplayString(token.text), 3);
			}), 128))])]);
		};
	}
};
//#endregion
//#region src/controls/clipboard.js
async function copyText(text) {
	if (navigator.clipboard?.writeText) try {
		await navigator.clipboard.writeText(text);
		return;
	} catch {}
	const previous = document.activeElement, input = document.createElement("textarea");
	input.value = text;
	input.readOnly = true;
	input.style.cssText = "position:fixed;inset:0;width:1px;height:1px;opacity:0";
	(document.querySelector("dialog:modal") || document.body).append(input);
	try {
		input.focus();
		input.select();
		if (!document.execCommand("copy")) throw new Error("Clipboard access failed");
	} finally {
		input.remove();
		previous?.focus();
	}
}
async function readClipboard() {
	if (!navigator.clipboard?.readText) throw new Error("Paste with Ctrl+V or the browser menu on HTTP.");
	return navigator.clipboard.readText();
}
async function readClipboardImages() {
	const files = [];
	for (const item of await navigator.clipboard.read()) {
		const type = item.types.includes("image/png") ? "image/png" : item.types.find((type) => type.startsWith("image/"));
		if (!type) continue;
		const extension = type === "image/jpeg" ? "jpg" : type.split("/")[1].split("+")[0];
		files.push(new File([await item.getType(type)], "clipboard" + (files.length ? "-" + (files.length + 1) : "") + "." + extension, { type }));
	}
	return files;
}
async function copyImage(blob) {
	if (!navigator.clipboard?.write || !globalThis.ClipboardItem) throw new Error("Copying an image requires HTTPS or localhost and clipboard permission.");
	let png = blob;
	if (blob.type !== "image/png") {
		const image = await createImageBitmap(blob), canvas = document.createElement("canvas");
		try {
			canvas.width = image.width;
			canvas.height = image.height;
			canvas.getContext("2d").drawImage(image, 0, 0);
			png = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
		} finally {
			image.close();
		}
		if (!png) throw new Error("Unable to copy image");
	}
	await navigator.clipboard.write([new ClipboardItem({ "image/png": png })]);
}
//#endregion
export { updatesAvailable as $, resetRequestActivity as A, serverConfiguration as B, objectRelations as C, projectNavigation as D, projectCreationCatalog as E, scriptShelf as F, transactionDetails as G, sessionAction as H, searchConfiguration as I, userProfile as J, uploadFormFile as K, securityGroups as L, rpc as M, saveServerConfiguration as N, rawDatabase as O, scriptEditor as P, updateDelay as Q, securityRules as R, objectDeletion as S, projectCatalog as T, sidebarRequest as U, serverUpdates as V, tableCells as W, workspaceLayouts as X, widgetConfiguration as Y, setUpdatesAvailable as Z, knowledgeRequest as _, _sfc_main as a, editNotificationReply as at, messagesRequest as b, xmlTokens as c, notify as ct, activityFeed as d, submitNotificationReply as dt, activeNotifications as et, beginActivity as f, interfaceDefinition as g, formDefinition as h, readClipboardImages as i, dismissNotification as it, resultItems as j, requestActivity as k, _sfc_main$1 as l, resetNotifications as lt, endActivity as m, copyText as n, cancelNotificationReply as nt, javascriptTokens as o, failNotificationReply as ot, columnsEditor as p, userAvatar as q, readClipboard as r, clearNotificationHistory as rt, pythonTokens as s, notificationHistory as st, copyImage as t, beginNotificationReply as tt, _sfc_main$2 as u, setNotificationProgress as ut, linkPreviews as v, objectStatus as w, navigationLink as x, messageFileRequest as y, securityUsers as z };

//# sourceMappingURL=clipboard.js.map