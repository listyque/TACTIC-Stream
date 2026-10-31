const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["assets/Timesheet.js","assets/ObjectFieldFrame.js","assets/vue.js","assets/AppButton.js","assets/locales.js","assets/icons.js","assets/AppButton.css","assets/FrameView.js","assets/FrameView.css","assets/ObjectFieldFrame.css","assets/Timesheet.css","assets/RelatedObjects.js","assets/textMetrics.js","assets/admin.document.js","assets/file_values.js","assets/files.js","assets/files2.js","assets/admin.css","assets/ConfiguredView.js","assets/sections.ui.js","assets/RecordForm.js","assets/previewImage.js","assets/RecordForm.css","assets/CodeBlock.js","assets/confirmation.ui.js","assets/AppDialog.js","assets/VirtualCollection.js","assets/VirtualCollection.css","assets/ContentLoadingOverlay.js","assets/ContentLoadingOverlay.css","assets/ConfiguredView.css","assets/RelatedObjects.css","assets/ProcessRules.js","assets/ProcessRules.css","assets/DuplicateSObject.js","assets/DuplicateSObject.css","assets/IngestFiles.js","assets/IngestFiles.css","assets/ObjectCheckin.js","assets/toggle.ui.js","assets/ObjectCheckin.css","assets/ProjectTemplates.js","assets/ProjectTemplates.css","assets/MilestoneManager.js","assets/MilestoneManager.css","assets/SnapshotCheckout.js","assets/FrameProgress.js","assets/SnapshotCheckout.css","assets/ApiDocumentation.js","assets/AppearanceControls.js","assets/AppearanceControls.css","assets/ApiDocumentation.css","assets/App.js","assets/tree.ui.js","assets/App.css"])))=>i.map(i=>d[i]);
import { $ as toRaw, A as onMounted, E as nextTick, H as watch, J as markRaw, M as openBlock, N as renderList, O as onBeforeUnmount, S as h, U as watchEffect, X as ref, Y as reactive, Z as shallowReactive, _ as createElementBlock, b as createVNode, et as unref, f as Teleport, g as createCommentVNode, h as createBlock, l as withModifiers, m as createBaseVNode, n as createApp, nt as normalizeStyle, r as render, rt as toDisplayString, tt as normalizeClass, u as Fragment, x as defineAsyncComponent } from "./vue.js";
import { C as layout, R as BusyIndicator_default, d as initializeAppearance, k as configurationPreview, o as t, t as _sfc_main$1 } from "./AppButton.js";
//#region \0vite/modulepreload-polyfill.js
(function polyfill() {
	const relList = document.createElement("link").relList;
	if (relList && relList.supports && relList.supports("modulepreload")) return;
	for (const link of document.querySelectorAll("link[rel=\"modulepreload\"]")) processPreload(link);
	new MutationObserver((mutations) => {
		for (const mutation of mutations) {
			if (mutation.type !== "childList") continue;
			for (const node of mutation.addedNodes) if (node.tagName === "LINK" && node.rel === "modulepreload") processPreload(node);
		}
	}).observe(document, {
		childList: true,
		subtree: true
	});
	function getFetchOpts(link) {
		const fetchOpts = {};
		if (link.integrity) fetchOpts.integrity = link.integrity;
		if (link.referrerPolicy) fetchOpts.referrerPolicy = link.referrerPolicy;
		if (link.crossOrigin === "use-credentials") fetchOpts.credentials = "include";
		else if (link.crossOrigin === "anonymous") fetchOpts.credentials = "omit";
		else fetchOpts.credentials = "same-origin";
		return fetchOpts;
	}
	function processPreload(link) {
		if (link.ep) return;
		link.ep = true;
		const fetchOpts = getFetchOpts(link);
		fetch(link.href, fetchOpts);
	}
})();
//#endregion
//#region src/controls/asyncComponent.js
function asyncComponent(loader) {
	return defineAsyncComponent({
		loader,
		loadingComponent: () => h("p", {
			role: "status",
			class: "muted"
		}, [h(BusyIndicator_default, { running: true }), " " + t("Loading interface…")]),
		errorComponent: () => h("p", {
			role: "alert",
			class: "error"
		}, t("Unable to load the interface. Check your connection and reload the page."))
	});
}
//#endregion
//#region src/controls/identity.js
function randomId() {
	return [...crypto.getRandomValues(/* @__PURE__ */ new Uint8Array(16))].map((value) => value.toString(16).padStart(2, "0")).join("");
}
function randomUuid() {
	const bytes = crypto.getRandomValues(/* @__PURE__ */ new Uint8Array(16));
	bytes[6] = bytes[6] & 15 | 64;
	bytes[8] = bytes[8] & 63 | 128;
	const value = [...bytes].map((byte) => byte.toString(16).padStart(2, "0")).join("");
	return [
		value.slice(0, 8),
		value.slice(8, 12),
		value.slice(12, 16),
		value.slice(16, 20),
		value.slice(20)
	].join("-");
}
//#endregion
//#region src/features/debug/debugLog.js
var levels = [
	"LOG",
	"INFO",
	"WARNING",
	"MISSING",
	"EXCEPTION",
	"ERROR",
	"CRITICAL",
	"API"
];
var sessionFields = {
	eventId: "id",
	timestamp: "t",
	level: "l",
	message: "m",
	module: "o",
	functionName: "f",
	line: "n",
	group: "g",
	source: "s",
	command: "c",
	stacktrace: "x",
	duration: "d",
	sizeKb: "z",
	thread: "h",
	details: "e"
};
var settingsKey = "tactic_stream.debug_log";
var saved = {};
try {
	saved = JSON.parse(localStorage.getItem(settingsKey) || "{}");
} catch {}
var debugSettings = reactive({
	recordingLevels: Array.isArray(saved?.recordingLevels) ? levels.filter((level) => saved.recordingLevels.includes(level)) : ["ERROR", "CRITICAL"],
	groupWidth: Math.max(170, Math.min(520, Number(saved?.groupWidth) || 230)),
	detailHeight: Math.max(110, Math.min(620, Number(saved?.detailHeight) || 220))
});
var debugLog = shallowReactive({
	entries: [],
	sessionId: randomId(),
	started: (/* @__PURE__ */ new Date()).toISOString(),
	storageError: ""
});
var sequence$1 = 0;
var database = null;
var serverContext = null;
var secretKeys = /password|passwd|secret|token|ticket|authorization|cookie|api[_-]?key|private[_-]?key/i;
var secrets = /* @__PURE__ */ new Set();
function setServerDebugContext(scope) {
	serverContext = scope?.ticket ? {
		ticket: scope.ticket,
		project: scope.project || ""
	} : null;
	if (serverContext) remember(serverContext.ticket);
}
function persistError(record, scope) {
	if (!scope?.ticket || !["ERROR", "CRITICAL"].includes(record.level)) return;
	const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 3e3);
	const message = JSON.stringify(redact({
		session: debugLog.sessionId,
		timestamp: record.timestamp,
		path: location.pathname || "",
		viewport: {
			width: globalThis.innerWidth || 0,
			height: globalThis.innerHeight || 0
		},
		group: record.group,
		message: record.message.slice(0, 8192),
		stacktrace: record.stacktrace.slice(0, 8192),
		details: record.details.slice(0, 8192)
	}));
	fetch("/admin/rpc", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		signal: controller.signal,
		body: JSON.stringify({
			method: "log",
			args: [
				scope,
				"error",
				message
			],
			kwargs: { category: record.group || "browser/error" }
		})
	}).catch(() => {}).finally(() => clearTimeout(timer));
}
watch(debugSettings, () => {
	if (configurationPreview.value) return;
	try {
		localStorage.setItem(settingsKey, JSON.stringify(debugSettings));
	} catch {
		debugLog.storageError = "Debug Log settings could not be saved.";
	}
});
function remember(value, active = /* @__PURE__ */ new Set()) {
	if (typeof value === "string" && value && value !== "<REDACTED>") secrets.add(value);
	if (value && typeof value === "object" && !active.has(value)) {
		active.add(value);
		for (const item of Object.values(value)) remember(item, active);
		active.delete(value);
	}
}
function redact(value, active = /* @__PURE__ */ new Set()) {
	if (value && typeof value === "object") {
		if (active.has(value)) return "<recursive reference>";
		active.add(value);
		try {
			if (Array.isArray(value)) return value.map((item) => redact(item, active));
			return Object.fromEntries(Object.entries(value).map(([key, item]) => {
				if (secretKeys.test(key)) {
					remember(item);
					return [key, "<REDACTED>"];
				}
				return [key, redact(item, active)];
			}));
		} finally {
			active.delete(value);
		}
	}
	if (typeof value === "string") for (const secret of secrets) value = value.replaceAll(secret, "<REDACTED>");
	return value;
}
function requestPayload(payload) {
	if (payload?.method === "get_ticket") {
		remember(payload.args?.[1]);
		return redact({
			...payload,
			args: [
				payload.args?.[0],
				"<REDACTED>",
				...payload.args.slice(2)
			]
		});
	}
	return redact(redact(payload));
}
function label() {
	return debugLog.started.replace("T", " ").slice(0, 19);
}
async function db() {
	if (!database) database = new Promise((resolve, reject) => {
		const request = indexedDB.open("tactic_stream.debug_log", 1);
		request.onupgradeneeded = () => {
			request.result.createObjectStore("sessions", { keyPath: "id" });
			request.result.createObjectStore("events", { keyPath: ["session", "eventId"] }).createIndex("session", "session");
		};
		request.onsuccess = () => resolve(request.result);
		request.onerror = () => reject(request.error);
		request.onblocked = () => reject(/* @__PURE__ */ new Error("Debug Log history is unavailable."));
	});
	return database;
}
async function write(callback) {
	const connection = await db();
	return new Promise((resolve, reject) => {
		const transaction = connection.transaction(["sessions", "events"], "readwrite");
		transaction.oncomplete = resolve;
		transaction.onerror = () => reject(transaction.error);
		transaction.onabort = () => reject(transaction.error);
		callback(transaction.objectStore("sessions"), transaction.objectStore("events"));
	});
}
async function read(store, query) {
	const connection = await db();
	return new Promise((resolve, reject) => {
		const request = query(connection.transaction(store).objectStore(store));
		request.onsuccess = () => resolve(request.result);
		request.onerror = () => reject(request.error);
	});
}
function storageFailed() {
	debugLog.storageError = "Debug Log history is unavailable. Live events remain in memory.";
}
async function savedSessions() {
	return (await read("sessions", (store) => store.getAll())).sort((a, b) => b.updated.localeCompare(a.updated));
}
async function sessionRecords(id) {
	return (await read("events", (store) => store.index("session").getAll(id))).map(({ session, ...record }) => record);
}
function logEvent(values, scope = serverContext, persist = true) {
	const record = redact({
		eventId: ++sequence$1,
		timestamp: (/* @__PURE__ */ new Date()).toISOString(),
		level: "LOG",
		message: "",
		module: "",
		functionName: "",
		line: 0,
		group: "",
		source: "Browser",
		command: "",
		stacktrace: "",
		duration: 0,
		sizeKb: 0,
		thread: "Main",
		details: "",
		...values
	});
	if (persist) persistError(record, scope);
	if (!debugSettings.recordingLevels.includes(values.level)) return;
	const old = debugLog.entries.length === 1e4 ? debugLog.entries[0] : null;
	debugLog.entries = [...debugLog.entries.slice(-9999), record];
	const id = debugLog.sessionId;
	write((sessions, events) => {
		sessions.put({
			id,
			label: label(),
			updated: record.timestamp
		});
		events.put({
			session: id,
			...record
		});
		if (old) events.delete([id, old.eventId]);
	}).catch(storageFailed);
}
function logRequest(url, payload, response, error, duration) {
	if (payload?.method === "log") return;
	const safe = requestPayload(payload);
	if (payload?.method === "get_ticket" && response?.result) remember(response.result);
	if (!error && !debugSettings.recordingLevels.includes("API")) return;
	const details = JSON.stringify(redact({
		request: safe,
		response
	}), null, 2);
	const body = JSON.stringify(safe);
	let command = "import json\nfrom urllib.request import Request, urlopen\n\npayload = json.loads(" + JSON.stringify(body) + ")\n# Replace <REDACTED> with your own ticket or credentials.\nrequest = Request(" + JSON.stringify(location.origin + url) + ", data=json.dumps(payload).encode(\"utf-8\"), headers={\"Content-Type\": \"application/json\"})\nwith urlopen(request) as response:\n    print(response.read().decode(\"utf-8\"))";
	if (safe.file && url.endsWith("/UploadServer/")) command = `from pathlib import Path
from uuid import uuid4
from urllib.request import Request, urlopen

# Replace <FILE_PATH> and <REDACTED> with your file and ticket.
file = Path("<FILE_PATH>")
boundary = uuid4().hex
filename = file.name.replace('"', '%22').replace('\\r', '%0D').replace('\\n', '%0A')
body = (f'--{boundary}\\r\\nContent-Disposition: form-data; name="login_ticket"\\r\\n\\r\\n<REDACTED>\\r\\n'
        f'--{boundary}\\r\\nContent-Disposition: form-data; name="file"; filename="{filename}"\\r\\n'
        'Content-Type: application/octet-stream\\r\\n\\r\\n').encode("utf-8")
body += file.read_bytes() + f'\\r\\n--{boundary}--\\r\\n'.encode("ascii")
request = Request(${JSON.stringify(location.origin + url)}, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
with urlopen(request) as response:
    print(response.read().decode("utf-8"))`;
	const scope = payload.ticket ? {
		ticket: payload.ticket,
		project: payload.project || ""
	} : payload.args?.[0]?.ticket ? {
		ticket: payload.args[0].ticket,
		project: payload.args[0].project || ""
	} : null;
	logEvent({
		level: error ? "ERROR" : "API",
		message: error ? error.message : payload.method || url,
		module: "api.js",
		functionName: payload.method || url,
		group: url.slice(1).replaceAll("-", "_"),
		source: "TACTIC API",
		duration,
		sizeKb: new TextEncoder().encode(details).length / 1024,
		details,
		command,
		stacktrace: error?.stack || ""
	}, scope, url !== "/admin/server-updates");
}
async function clearLive() {
	debugLog.entries = [];
	const id = debugLog.sessionId;
	try {
		await write((sessions, events) => {
			events.delete(IDBKeyRange.bound([id, 0], [id, Number.MAX_SAFE_INTEGER]));
			sessions.delete(id);
		});
	} catch {
		storageFailed();
	}
}
async function forgetSessions() {
	debugLog.entries = [];
	sequence$1 = 0;
	secrets.clear();
	debugLog.sessionId = randomId();
	debugLog.started = (/* @__PURE__ */ new Date()).toISOString();
	try {
		await write((sessions, events) => {
			sessions.clear();
			events.clear();
		});
	} catch {
		storageFailed();
	}
}
function parseSession(text) {
	const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/);
	let header;
	try {
		header = JSON.parse(lines.shift());
	} catch {
		throw new Error("Invalid Debug Log session header");
	}
	if (JSON.stringify(header) !== "{\"v\":1}") throw new Error("Unsupported Debug Log session schema");
	const records = [], ids = /* @__PURE__ */ new Set();
	for (const [index, line] of lines.entries()) {
		if (!line.trim()) continue;
		let values;
		try {
			values = JSON.parse(line);
		} catch {
			const error = /* @__PURE__ */ new Error("Invalid JSONL record");
			error.line = index + 2;
			throw error;
		}
		if (!values || Array.isArray(values) || typeof values !== "object") continue;
		const record = Object.fromEntries(Object.entries(sessionFields).map(([field, key]) => [field, values[key] ?? ""]));
		for (const field of [
			"eventId",
			"line",
			"duration",
			"sizeKb"
		]) {
			record[field] = Number(record[field] || (field === "eventId" ? records.length + 1 : 0));
			if (!Number.isFinite(record[field]) || record[field] < 0) throw new Error("Invalid Debug Log event");
		}
		if (!Number.isSafeInteger(record.eventId) || ids.has(record.eventId)) throw new Error("Invalid Debug Log event");
		ids.add(record.eventId);
		for (const field of Object.keys(sessionFields).filter((key) => ![
			"eventId",
			"line",
			"duration",
			"sizeKb"
		].includes(key))) if (typeof record[field] !== "string") throw new Error("Invalid Debug Log event");
		record.level = levels.includes(record.level.toUpperCase()) ? record.level.toUpperCase() : "LOG";
		records.push(redact(record));
	}
	return records.slice(-1e4);
}
async function importSession(file) {
	const session = debugLog.sessionId;
	if (!file.name.toLowerCase().endsWith(".jsonl")) throw new Error("A compact Debug Log session (.jsonl) is required.");
	if (file.size > 33554432) throw new Error("Debug Log session exceeds 32 MB.");
	const records = parseSession(await file.text()), id = randomId();
	if (session !== debugLog.sessionId) throw new DOMException("Session ended", "AbortError");
	await write((sessions, events) => {
		if (session !== debugLog.sessionId) return;
		sessions.put({
			id,
			label: file.name,
			updated: (/* @__PURE__ */ new Date()).toISOString()
		});
		for (const record of records) events.put({
			session: id,
			...record
		});
	});
	if (session !== debugLog.sessionId) throw new DOMException("Session ended", "AbortError");
	return {
		id,
		records
	};
}
function exportSession(records) {
	return JSON.stringify({ v: 1 }) + "\n" + records.map((record) => JSON.stringify(Object.fromEntries(Object.entries(sessionFields).filter(([field]) => ![
		void 0,
		null,
		"",
		false,
		0
	].includes(record[field])).map(([field, key]) => [key, record[field]])))).join("\n") + "\n";
}
function formatEvent(record) {
	return `[${record.timestamp}] [${record.level}] [${record.group}]\n${record.message}\n${record.module} / ${record.functionName}():${String(record.line || 0).padStart(4, "0")}` + (record.details ? "\n\nDetails:\n" + record.details : "") + (record.command ? "\n\nRuntime command:\n" + record.command : "") + (record.stacktrace ? "\n\nStacktrace:\n" + record.stacktrace : "");
}
function installDebugLogging() {
	for (const [method, level] of Object.entries({
		log: "LOG",
		info: "INFO",
		warn: "WARNING",
		error: "ERROR",
		debug: "LOG"
	})) {
		const original = console[method].bind(console);
		console[method] = (...args) => {
			original(...args);
			if (level !== "ERROR" && !debugSettings.recordingLevels.includes(level)) return;
			try {
				logEvent({
					level,
					source: "Browser console",
					module: "console",
					functionName: method,
					group: "browser/console",
					message: args.map((value) => value instanceof Error ? value.message : typeof value === "string" ? value : JSON.stringify(redact(value))).join(" "),
					stacktrace: args.find((value) => value instanceof Error)?.stack || ""
				});
			} catch {
				debugLog.storageError = "A message could not be recorded in Debug Log.";
			}
		};
	}
	window.addEventListener("error", (event) => {
		if (event.error) logEvent({
			level: "ERROR",
			source: "Browser",
			module: event.filename,
			line: event.lineno,
			group: "browser/error",
			message: event.message,
			stacktrace: event.error.stack || ""
		});
	});
	window.addEventListener("unhandledrejection", (event) => logEvent({
		level: "ERROR",
		source: "Browser",
		group: "browser/error",
		message: String(event.reason?.message || event.reason),
		stacktrace: event.reason?.stack || ""
	}));
}
//#endregion
//#region src/mobile.js
var mobileLayout = window.matchMedia("(max-width: 700px)");
var mobile = ref(mobileLayout.matches);
mobileLayout.addEventListener("change", (event) => {
	mobile.value = event.matches;
});
function viewportChanged() {
	const viewport = window.visualViewport;
	const keyboardViewport = mobile.value && viewport?.scale === 1;
	document.documentElement.style.setProperty("--phone-height", (keyboardViewport ? viewport.height : innerHeight) + "px");
	document.documentElement.style.setProperty("--phone-top", (keyboardViewport ? viewport.offsetTop : 0) + "px");
}
window.visualViewport?.addEventListener("resize", viewportChanged);
window.visualViewport?.addEventListener("scroll", viewportChanged);
window.addEventListener("resize", viewportChanged);
mobileLayout.addEventListener("change", viewportChanged);
viewportChanged();
//#endregion
//#region ../src/tactic_stream/shared_ui/shell/window.geometry.mjs
var finite = (value, fallback) => Number.isFinite(value) ? value : fallback;
function fit(rectangle, bounds, minimum, sizeMargin) {
	if (![
		bounds.x,
		bounds.y,
		bounds.width,
		bounds.height
	].every(Number.isFinite) || bounds.width <= 0 || bounds.height <= 0) throw Error("Window bounds must be finite and have positive dimensions");
	const limit = minimum || {
		width: 1,
		height: 1
	};
	const margin = Math.max(0, finite(sizeMargin, 0));
	const width = Math.max(limit.width, Math.min(finite(rectangle.width, 280), Math.max(1, bounds.width - margin)));
	const height = Math.max(limit.height, Math.min(finite(rectangle.height, 180), Math.max(1, bounds.height - margin)));
	return {
		x: Math.max(bounds.x, Math.min(finite(rectangle.x, bounds.x), bounds.x + bounds.width - width)),
		y: Math.max(bounds.y, Math.min(finite(rectangle.y, bounds.y), bounds.y + bounds.height - height)),
		width,
		height
	};
}
function moved(rectangle, delta) {
	return Object.assign({}, rectangle, {
		x: rectangle.x + delta.x,
		y: rectangle.y + delta.y
	});
}
function resized(rectangle, edge, delta, bounds, minimum) {
	if ([
		"left",
		"right",
		"top",
		"bottom",
		"top-left",
		"top-right",
		"bottom-left",
		"bottom-right"
	].indexOf(edge) < 0) throw Error("Unknown window resize edge: " + edge);
	const result = Object.assign({}, rectangle);
	const minimumWidth = Math.min(minimum.width, bounds.width);
	const minimumHeight = Math.min(minimum.height, bounds.height);
	if (edge.indexOf("right") >= 0) result.width = Math.max(minimumWidth, Math.min(bounds.x + bounds.width - result.x, result.width + delta.x));
	if (edge.indexOf("bottom") >= 0) result.height = Math.max(minimumHeight, Math.min(bounds.y + bounds.height - result.y, result.height + delta.y));
	if (edge.indexOf("left") >= 0) {
		result.x = Math.max(bounds.x, Math.min(result.x + delta.x, result.x + result.width - minimumWidth));
		result.width += rectangle.x - result.x;
	}
	if (edge.indexOf("top") >= 0) {
		result.y = Math.max(bounds.y, Math.min(result.y + delta.y, result.y + result.height - minimumHeight));
		result.height += rectangle.y - result.y;
	}
	return result;
}
//#endregion
//#region ../src/tactic_stream/shared_ui/shell/window.sizing.mjs
function windowMinimumWidth(kind) {
	if (String(kind).indexOf("dcc.") === 0) return 560;
	const widths = {
		main: 560,
		configuration: 820,
		server: 640,
		project: 640,
		project_wizard: 680,
		project_templates: 680,
		checkin_preferences: 640,
		global_preferences: 560,
		repository_editor: 760,
		commit_queue: 860,
		file_changelist: 520,
		ingest_files: 760,
		script_editor: 720,
		agent_request: 520,
		script_shelf_editor: 720,
		script_trigger_editor: 760,
		help: 760,
		messages: 820,
		tasks_workspace: 760,
		handler_server: 820,
		sobject_info: 760,
		related_objects: 760,
		debug_log: 680,
		ui_performance: 720,
		system_info: 320,
		error: 560,
		repository_sync: 680,
		repository_sync_editor: 900,
		activity_feed: 680,
		user_profile: 680,
		administration: 900,
		schema_search_type: 600,
		raw_cell: 440,
		table_document: 480,
		process_dependencies: 860,
		sidebar_search_preview: 960,
		server_presets: 720,
		screenshot_maker: 640,
		notifications: 560,
		update: 520,
		create_update: 560,
		matching_templates: 640,
		dcc_options: 520,
		add_sobject: 620,
		task_editor: 620,
		link_sobjects: 620,
		delete_sobject: 720,
		duplicate_sobject: 680,
		process_filter_editor: 440,
		quick_filter_editor: 620,
		advanced_search: 680,
		naming_editor: 840
	};
	return Object.prototype.hasOwnProperty.call(widths, kind) ? widths[kind] : 480;
}
function windowMinimumHeight(kind) {
	if (String(kind).indexOf("dcc.") === 0) return 440;
	const heights = {
		main: 480,
		raw_cell: 340,
		table_document: 340,
		configuration: 600,
		server: 520,
		project: 520,
		project_wizard: 520,
		project_templates: 520,
		checkin_preferences: 520,
		global_preferences: 440,
		repository_editor: 540,
		commit_queue: 600,
		file_changelist: 480,
		ingest_files: 560,
		script_editor: 500,
		agent_request: 560,
		script_shelf_editor: 480,
		script_trigger_editor: 520,
		help: 520,
		messages: 560,
		tasks_workspace: 520,
		handler_server: 580,
		sobject_info: 560,
		related_objects: 560,
		debug_log: 480,
		ui_performance: 520,
		system_info: 320,
		error: 400,
		repository_sync: 480,
		repository_sync_editor: 620,
		activity_feed: 480,
		user_profile: 480,
		administration: 620,
		schema_search_type: 560,
		process_dependencies: 600,
		sidebar_search_preview: 620,
		server_presets: 520,
		screenshot_maker: 500,
		notifications: 420,
		update: 380,
		create_update: 420,
		matching_templates: 500,
		dcc_options: 420,
		add_sobject: 480,
		task_editor: 480,
		link_sobjects: 480,
		delete_sobject: 520,
		duplicate_sobject: 520,
		process_filter_editor: 360,
		quick_filter_editor: 520,
		advanced_search: 500,
		naming_editor: 600
	};
	return Object.prototype.hasOwnProperty.call(heights, kind) ? heights[kind] : 360;
}
function dockMinimumWidth(kind) {
	const widths = {
		results: 360,
		snapshot: 320,
		tasks: 320,
		task_calendar: 380,
		description: 320,
		notes: 400,
		drop_plate: 480,
		advanced_search: 380,
		watch_folders: 680,
		watch_folder_editor: 520,
		db_table: 620,
		commit_queue: 720
	};
	return Object.prototype.hasOwnProperty.call(widths, kind) ? widths[kind] : 320;
}
function dockMinimumHeight(kind) {
	const heights = {
		results: 260,
		snapshot: 260,
		tasks: 220,
		task_calendar: 360,
		description: 220,
		notes: 300,
		drop_plate: 360,
		advanced_search: 320,
		watch_folders: 420,
		watch_folder_editor: 350,
		db_table: 460,
		commit_queue: 480
	};
	return Object.prototype.hasOwnProperty.call(heights, kind) ? heights[kind] : 220;
}
//#endregion
//#region src/controls/WindowControls.vue
var _hoisted_1 = { class: "app-window-caption" };
var _hoisted_2 = { class: "app-window-titlebar app-window-minimized-titlebar" };
var _hoisted_3 = ["onPointerdown"];
var _sfc_main = {
	__name: "WindowControls",
	props: {
		element: Object,
		header: Object,
		geometry: Object,
		backProvided: Boolean,
		title: String,
		closeButton: Object,
		closeRequired: Boolean,
		closeDisabled: Boolean,
		helpButton: Object,
		helpLabel: String,
		helpDisabled: Boolean,
		pageRoot: Boolean,
		openSeparate: Function
	},
	setup(__props) {
		const props = __props;
		const previousTitle = props.header.getAttribute("title"), previousTabIndex = props.header.getAttribute("tabindex");
		const maximized = ref(false);
		const minimized = ref(false);
		const edges = ref({});
		function back() {
			if (props.element.dispatchEvent(new Event("cancel", { cancelable: true }))) props.element.close();
		}
		watchEffect(() => {
			props.header.title = t("Drag the title bar to move. Double-click or Alt+F10 to maximize. Alt+arrows moves the focused title bar.");
		});
		let saved = null, placed = null, gesture = null;
		function geometryChanged() {
			resizeEdges();
			props.element.dispatchEvent(new CustomEvent("windowgeometrychange", { detail: {
				...rectangle(),
				maximized: maximized.value,
				restore: saved
			} }));
			window.dispatchEvent(new Event("windowgeometrychange"));
		}
		watch(() => props.geometry, (value) => {
			if (!value) return;
			saved = clamp(value.restore || value.rect);
			placed = clamp(value.rect);
			maximized.value = !!value.maximized;
			for (const [key, value] of Object.entries(placed)) props.element.style.setProperty("--window-" + key, value + "px");
			props.element.classList.add("app-window-positioned");
			props.element.classList.toggle("app-window-maximized", maximized.value);
		}, {
			deep: true,
			immediate: true
		});
		const compact = () => innerWidth <= 700;
		function rectangle() {
			const box = props.element.getBoundingClientRect();
			return {
				x: box.x,
				y: box.y,
				width: box.width,
				height: box.height
			};
		}
		function resizeEdges() {
			const box = rectangle();
			edges.value = {
				"--edge-left": box.x + "px",
				"--edge-top": box.y + "px",
				"--edge-right": innerWidth - box.x - box.width + "px",
				"--edge-bottom": innerHeight - box.y - box.height + "px"
			};
		}
		function syncHeaderPadding() {
			const style = getComputedStyle(props.element);
			for (const side of [
				"top",
				"left",
				"right"
			]) props.header.style.setProperty("--window-padding-" + side, props.header.parentElement === props.element ? style.getPropertyValue("padding-" + side) : "0px");
		}
		function clamp(rect) {
			return fit(rect, {
				x: 0,
				y: 0,
				width: innerWidth,
				height: innerHeight
			}, minimum(), layout.windowMargin);
		}
		function minimum() {
			const kind = props.element.dataset.windowKind;
			return {
				width: Math.min(kind ? windowMinimumWidth(kind) : 280, innerWidth - layout.windowMargin),
				height: Math.min(kind ? windowMinimumHeight(kind) : 180, innerHeight - layout.windowMargin)
			};
		}
		function place(rect) {
			placed = clamp(rect);
			for (const [key, value] of Object.entries(placed)) props.element.style.setProperty("--window-" + key, value + "px");
			props.element.classList.add("app-window-positioned");
			geometryChanged();
		}
		function toggle() {
			if (compact()) return;
			if (!maximized.value) {
				saved = rectangle();
				maximized.value = true;
			} else {
				maximized.value = false;
				props.element.classList.remove("app-window-maximized");
				place(saved);
				return;
			}
			props.element.classList.toggle("app-window-maximized", maximized.value);
			geometryChanged();
		}
		function minimize() {
			minimized.value = !minimized.value;
			props.element.classList.toggle("app-window-minimized", minimized.value);
			geometryChanged();
		}
		function shown() {
			syncHeaderPadding();
			if (minimized.value) minimize();
		}
		function restoreBeforeClose(event) {
			if (minimized.value && event.target.closest("button")?.querySelector("[data-icon=\"close\"], [data-icon=\"MDI_CLOSE\"]")) minimize();
		}
		function start(event) {
			if (props.pageRoot) return;
			if (gesture || event.isPrimary === false || compact() || maximized.value || event.button !== 0 || event.target.closest("button, a, input, select, textarea, summary, label, [role=\"button\"], [role=\"tab\"]")) return;
			event.preventDefault();
			props.header.setPointerCapture(event.pointerId);
			gesture = {
				pointer: event.pointerId,
				x: event.clientX,
				y: event.clientY,
				before: rectangle()
			};
		}
		function move(event) {
			if (!gesture || gesture.pointer !== event.pointerId) return;
			const delta = {
				x: event.clientX - gesture.x,
				y: event.clientY - gesture.y
			};
			place(gesture.edge ? resized(gesture.before, gesture.edge, delta, {
				x: 0,
				y: 0,
				width: innerWidth,
				height: innerHeight
			}, minimum()) : moved(gesture.before, delta));
		}
		function startResize(event, edge) {
			if (props.pageRoot) return;
			if (gesture || event.isPrimary === false || compact() || maximized.value || event.button !== 0) return;
			event.preventDefault();
			props.header.setPointerCapture(event.pointerId);
			gesture = {
				pointer: event.pointerId,
				x: event.clientX,
				y: event.clientY,
				before: rectangle(),
				edge
			};
		}
		function stop(event) {
			if (!gesture || event.pointerId !== gesture.pointer) return;
			const current = gesture;
			gesture = null;
			if (["pointercancel", "lostpointercapture"].includes(event.type)) place(current.before);
			if (props.header.hasPointerCapture(current.pointer)) props.header.releasePointerCapture(current.pointer);
		}
		function doubleClick(event) {
			if (props.pageRoot) return;
			if (!event.target.closest("button, a, input, select, textarea, summary, label")) toggle();
		}
		function resize() {
			syncHeaderPadding();
			if (placed && !maximized.value && !compact()) place(placed);
			resizeEdges();
		}
		function cancelGesture() {
			if (gesture) stop({
				pointerId: gesture.pointer,
				type: "pointercancel"
			});
		}
		function opened() {
			if (props.element.open) syncHeaderPadding();
			if (!props.element.open || saved || placed || compact()) return;
			if (props.element.offsetWidth < innerWidth - 16 || props.element.offsetHeight < innerHeight - 16) return;
			const width = Math.min(1100, innerWidth * .8), height = Math.min(760, innerHeight * .8);
			saved = {
				width,
				height,
				x: (innerWidth - width) / 2,
				y: (innerHeight - height) / 2
			};
			maximized.value = true;
			props.element.classList.add("app-window-maximized");
			geometryChanged();
		}
		const observer = new MutationObserver(opened);
		const sizeObserver = new ResizeObserver(resizeEdges);
		function key(event) {
			if (props.pageRoot) return;
			if (event.target.closest(".app-window") !== props.element || event.target.closest("dialog") !== props.element) return;
			if (event.key === "Escape" && gesture) {
				event.preventDefault();
				event.stopPropagation();
				cancelGesture();
				return;
			}
			if (event.altKey && event.key === "F10") {
				event.preventDefault();
				event.stopPropagation();
				toggle();
			}
			if (event.target !== props.header || !event.altKey || !event.key.startsWith("Arrow") || compact() || maximized.value) return;
			event.preventDefault();
			event.stopPropagation();
			const rect = rectangle(), dx = event.key === "ArrowLeft" ? -10 : event.key === "ArrowRight" ? 10 : 0, dy = event.key === "ArrowUp" ? -10 : event.key === "ArrowDown" ? 10 : 0;
			place(event.shiftKey ? {
				...rect,
				width: Math.max(280, rect.width + dx),
				height: Math.max(180, rect.height + dy)
			} : {
				...rect,
				x: rect.x + dx,
				y: rect.y + dy
			});
		}
		onMounted(() => {
			syncHeaderPadding();
			props.header.addEventListener("click", restoreBeforeClose, true);
			props.header.classList.add("app-window-titlebar");
			props.header.tabIndex = 0;
			for (const [name, fn] of Object.entries({
				pointerdown: start,
				pointermove: move,
				pointerup: stop,
				pointercancel: stop,
				lostpointercapture: stop,
				dblclick: doubleClick
			})) props.header.addEventListener(name, fn);
			props.element.addEventListener("keydown", key, true);
			window.addEventListener("resize", resize);
			props.element.addEventListener("windowshow", shown);
			window.addEventListener("blur", cancelGesture);
			window.addEventListener("pagehide", cancelGesture);
			observer.observe(props.element, {
				attributes: true,
				attributeFilter: ["open"]
			});
			opened();
			sizeObserver.observe(props.element);
		});
		onBeforeUnmount(() => {
			props.header.removeEventListener("click", restoreBeforeClose, true);
			cancelGesture();
			for (const [name, fn] of Object.entries({
				pointerdown: start,
				pointermove: move,
				pointerup: stop,
				pointercancel: stop,
				lostpointercapture: stop,
				dblclick: doubleClick
			})) props.header.removeEventListener(name, fn);
			props.header.classList.remove("app-window-titlebar");
			for (const [name, value] of [["title", previousTitle], ["tabindex", previousTabIndex]]) if (value === null) props.header.removeAttribute(name);
			else props.header.setAttribute(name, value);
			props.element.classList.remove("app-window-positioned", "app-window-maximized", "app-window-minimized");
			for (const key of [
				"x",
				"y",
				"width",
				"height"
			]) props.element.style.removeProperty("--window-" + key);
			props.element.removeEventListener("keydown", key, true);
			window.removeEventListener("resize", resize);
			props.element.removeEventListener("windowshow", shown);
			window.removeEventListener("blur", cancelGesture);
			window.removeEventListener("pagehide", cancelGesture);
			observer.disconnect();
			sizeObserver.disconnect();
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock(Fragment, null, [
				__props.title ? (openBlock(), createBlock(Teleport, {
					key: 0,
					to: __props.header
				}, [createBaseVNode("strong", _hoisted_1, toDisplayString(__props.title), 1)], 8, ["to"])) : createCommentVNode("", true),
				__props.openSeparate && !minimized.value ? (openBlock(), createBlock(_sfc_main$1, {
					key: 1,
					round: "",
					class: "app-window-separate",
					"icon-only": "",
					icon: "open-in-new",
					label: "Open in separate page",
					onClick: __props.openSeparate
				}, null, 8, ["onClick"])) : createCommentVNode("", true),
				__props.helpButton && !minimized.value ? (openBlock(), createBlock(_sfc_main$1, {
					key: 2,
					round: "",
					class: "app-window-help",
					"icon-only": "",
					icon: "help",
					label: __props.helpLabel,
					translate: false,
					disabled: __props.helpDisabled,
					onClick: _cache[0] || (_cache[0] = ($event) => __props.helpButton.click())
				}, null, 8, ["label", "disabled"])) : createCommentVNode("", true),
				__props.element.dataset.windowType === "window" && !__props.pageRoot ? (openBlock(), createBlock(_sfc_main$1, {
					key: 3,
					round: "",
					"icon-only": "",
					icon: minimized.value ? "window-restore" : "minus",
					label: minimized.value ? "Restore window" : "Minimize window",
					"aria-pressed": minimized.value,
					onClick: minimize
				}, null, 8, [
					"icon",
					"label",
					"aria-pressed"
				])) : createCommentVNode("", true),
				!minimized.value && !__props.pageRoot ? (openBlock(), createBlock(_sfc_main$1, {
					key: 4,
					round: "",
					"icon-only": "",
					icon: maximized.value ? "window-restore" : "open-in-full",
					label: maximized.value ? "Restore window" : "Maximize window",
					"aria-pressed": maximized.value,
					onClick: toggle
				}, null, 8, [
					"icon",
					"label",
					"aria-pressed"
				])) : createCommentVNode("", true),
				__props.closeRequired ? (openBlock(), createBlock(_sfc_main$1, {
					key: 5,
					round: "",
					"icon-only": "",
					icon: "close",
					label: "Close",
					disabled: __props.closeDisabled,
					onClick: _cache[1] || (_cache[1] = ($event) => __props.closeButton ? __props.closeButton.click() : back())
				}, null, 8, ["disabled"])) : createCommentVNode("", true),
				(openBlock(), createBlock(Teleport, { to: __props.header }, [unref(mobile) && !__props.backProvided ? (openBlock(), createBlock(_sfc_main$1, {
					key: 0,
					round: "",
					class: "app-window-back",
					"icon-only": "",
					icon: "MDI_ARROW_LEFT",
					label: "Back",
					onClick: back
				})) : createCommentVNode("", true)], 8, ["to"])),
				minimized.value && __props.header.parentElement !== __props.element ? (openBlock(), createBlock(Teleport, {
					key: 6,
					to: __props.element
				}, [createBaseVNode("header", _hoisted_2, [
					createBaseVNode("strong", null, toDisplayString(__props.element.getAttribute("aria-label") || __props.header.querySelector("[role=\"heading\"]")?.textContent || unref(t)("Restore window")), 1),
					createVNode(_sfc_main$1, {
						round: "",
						"icon-only": "",
						icon: "window-restore",
						label: "Restore window",
						onClick: minimize
					}),
					createVNode(_sfc_main$1, {
						round: "",
						"icon-only": "",
						icon: "close",
						label: "Close",
						onClick: _cache[2] || (_cache[2] = ($event) => {
							minimize();
							back();
						})
					})
				])], 8, ["to"])) : createCommentVNode("", true),
				(openBlock(), createBlock(Teleport, { to: __props.element }, [!__props.pageRoot && !maximized.value && !minimized.value ? (openBlock(), createElementBlock(Fragment, { key: 0 }, renderList([
					"left",
					"right",
					"top",
					"bottom",
					"top-left",
					"top-right",
					"bottom-left",
					"bottom-right"
				], (edge) => {
					return createBaseVNode("span", {
						key: edge,
						class: normalizeClass(["app-window-resize", edge]),
						style: normalizeStyle(edges.value),
						"aria-hidden": "true",
						onPointerdown: withModifiers(($event) => startResize($event, edge), ["stop"])
					}, null, 46, _hoisted_3);
				}), 64)) : createCommentVNode("", true)], 8, ["to"]))
			], 64);
		};
	}
};
//#endregion
//#region src/serverClock.js
function serverTimestamp(value) {
	const text = String(value || "").trim().replace(" ", "T");
	return new Date(/(?:Z|[+-]\d{2}:?\d{2})$/i.test(text) ? text : text + "Z");
}
var ServerClock = class {
	constructor() {
		this.anchor = {
			utc: null,
			received: -Infinity,
			bestDelay: Infinity
		};
		this.revision = 0;
	}
	now() {
		this.revision;
		const { utc, received } = this.anchor;
		return utc === null ? Date.now() : utc + performance.now() - received;
	}
	observe(sample, started, received) {
		if (![sample?.utcStarted, sample?.utcEnded].every((value) => typeof value === "string" && /(?:Z|[+-]\d{2}:\d{2})$/i.test(value))) return false;
		const anchor = this.anchor;
		const begin = Date.parse(sample.utcStarted), end = Date.parse(sample.utcEnded);
		const delay = received - started - (end - begin);
		if (![
			begin,
			end,
			started,
			received
		].every(Number.isFinite) || end < begin || received < started || delay < -2 || received < anchor.received) return false;
		if (anchor.utc !== null && delay > anchor.bestDelay * 1.5 + 20 && received - anchor.received < 3e5) return false;
		const utc = end + Math.max(0, delay) / 2;
		const changed = anchor.utc === null || Math.abs(utc - anchor.utc - (received - anchor.received)) >= 500;
		anchor.utc = utc;
		anchor.received = received;
		anchor.bestDelay = Math.min(anchor.bestDelay, Math.max(0, delay));
		if (changed) this.revision++;
		return true;
	}
	observeResponse(response, started, received = performance.now()) {
		return this.observe({
			utcStarted: response.headers.get("X-Tactic-UTC-Started"),
			utcEnded: response.headers.get("X-Tactic-UTC-Ended")
		}, started, received);
	}
};
var serverClock = shallowReactive(new ServerClock());
var localTimeZone = () => Intl.DateTimeFormat().resolvedOptions().timeZone;
//#endregion
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
		timestamp: new Date(serverClock.now()).toISOString(),
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
		...values,
		time_zone: localTimeZone()
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
function resolveCustomUrl(ticket, project, path, parameters) {
	return post("/admin/custom-url", {
		ticket,
		project,
		path,
		parameters
	});
}
function tableDependencies(context, values, signal) {
	return post("/admin/rpc", {
		method: "execute_cmd",
		args: [
			context,
			"tactic.ui.table.TableDependencyReadCmd",
			values
		],
		kwargs: {}
	}, signal, true);
}
function tableDependencyFile(context, values, signal) {
	return post("/admin/rpc", {
		method: "execute_cmd",
		args: [
			context,
			"tactic.ui.table.TableSnapshotFilesCmd",
			values
		],
		kwargs: {}
	}, signal, true);
}
function tableParentGroup(context, values, signal) {
	const timeout = AbortSignal.any([AbortSignal.timeout(3e4), ...signal ? [signal] : []]);
	return post("/admin/rpc", {
		method: "execute_cmd",
		args: [
			context,
			"tactic.ui.table.TableParentGroupCmd",
			values
		],
		kwargs: {}
	}, timeout, true);
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
function restartServer(ticket, revision, instance_id, request_id) {
	return post("/admin/configuration/restart", {
		ticket,
		revision,
		instance_id,
		request_id
	}, void 0, true);
}
function serverRuntime(ticket) {
	return post("/admin/configuration/runtime", { ticket }, AbortSignal.timeout(3e3), true);
}
function databaseResources(action, ticket, values = {}) {
	return post("/admin/configuration/database-resources/" + action, {
		ticket,
		...values
	});
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
async function uploadFormFile(ticket, project, file, { signal, filename, subdir } = {}) {
	const body = new FormData();
	body.append("login_ticket", ticket);
	body.append("file", file, filename || file.name);
	if (subdir) body.append("subdir", subdir);
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
		serverClock.observeResponse(response, started);
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
//#region src/features/objects/previewFiles.js
async function fileBlob(file, { signal } = {}) {
	if (!file?.href) throw new Error(t("No web path is configured for this file."));
	const response = await fetch(file.href, { signal });
	if (!response.ok) throw new Error(t("File Offline"));
	return response.blob();
}
//#endregion
//#region \0vite/preload-helper.js
var scriptRel = "modulepreload";
var assetsURL = function(dep) {
	return "/ui/" + dep;
};
var seen = {};
var isCssPreloadUrl = function isCssPreloadUrl(url) {
	return url.pathname.endsWith(".css");
};
var __vitePreload = function preload(baseModule, deps, importerUrl) {
	let promise = Promise.resolve();
	if (deps && deps.length > 0) {
		let preloadedHrefs;
		const cspNonceMeta = document.querySelector("meta[property=csp-nonce]");
		const cspNonce = cspNonceMeta?.nonce || cspNonceMeta?.getAttribute("nonce");
		function allSettled(promises) {
			return Promise.all(promises.map((p) => Promise.resolve(p).then((value) => ({
				status: "fulfilled",
				value
			}), (reason) => ({
				status: "rejected",
				reason
			}))));
		}
		function importMetaResolve(specifier) {
			if (import.meta.resolve) return new URL(import.meta.resolve(specifier));
			return new URL(
				specifier,
				/** #__KEEP__ */
				import.meta.url
			);
		}
		promise = allSettled(deps.map((depString) => {
			depString = assetsURL(depString, importerUrl);
			const dep = importMetaResolve(depString);
			if (dep.href in seen) return;
			seen[dep.href] = true;
			const isCss = isCssPreloadUrl(dep);
			if (preloadedHrefs === void 0) {
				preloadedHrefs = {
					all: /* @__PURE__ */ new Set(),
					styles: /* @__PURE__ */ new Set()
				};
				const links = document.getElementsByTagName("link");
				for (let i = links.length - 1; i >= 0; i--) {
					const link = links[i];
					preloadedHrefs.all.add(link.href);
					if (link.rel === "stylesheet") preloadedHrefs.styles.add(link.href);
				}
			}
			if ((isCss ? preloadedHrefs.styles : preloadedHrefs.all).has(dep.href)) return;
			const link = document.createElement("link");
			link.rel = isCss ? "stylesheet" : scriptRel;
			if (!isCss) link.as = "script";
			link.crossOrigin = "";
			link.href = dep.href;
			if (cspNonce) link.setAttribute("nonce", cspNonce);
			document.head.appendChild(link);
			if (isCss) return new Promise((res, rej) => {
				link.addEventListener("load", res);
				link.addEventListener("error", () => rej(/* @__PURE__ */ new Error(`Unable to preload CSS for ${dep}`)));
			});
		}).filter((p) => p !== void 0));
	}
	function handlePreloadError(err) {
		const e = new Event("vite:preloadError", { cancelable: true });
		e.payload = err;
		window.dispatchEvent(e);
		if (!e.defaultPrevented) throw err;
	}
	return promise.then((res) => {
		for (const item of res || []) {
			if (item.status !== "rejected") continue;
			handlePreloadError(item.reason);
		}
		return baseModule().catch(handlePreloadError);
	});
};
//#endregion
//#region src/features/windows/windowPages.js
var windowPages = {
	messages: { ref: "messages" },
	work_hours: { load: () => __vitePreload(() => import("./Timesheet.js").then((n) => n.n), __vite__mapDeps([0,1,2,3,4,5,6,7,8,9,10])) },
	snapshot_browser: { open: async (app, context) => {
		app.snapshotTarget = {
			project: context.project,
			...context.route.target
		};
		app.snapshotMounted = app.snapshotActive = true;
		await nextTick();
		app.$refs.snapshotPage.show();
	} },
	sobject_info: { open: (app, context) => app.inspect({ __search_key__: context.route.key }) },
	file_preview: { open: async (app, context) => {
		if (context.state) {
			const { record, cell, download } = context.state;
			app.$refs.linkPreview.open(record, {
				...cell,
				...download ? { loadFile: fileBlob } : {}
			});
		} else {
			const result = await navigationLink(app.session.ticket, context.project, "skey://" + context.route.key);
			if (!result.preview) throw Error("No preview available");
			app.$refs.linkPreview.open(result.object, {
				...result.preview,
				fileCode: context.route.fileCode,
				loadFile: fileBlob
			});
		}
	} },
	related_objects: { load: () => __vitePreload(() => import("./RelatedObjects.js"), __vite__mapDeps([11,1,2,3,4,5,6,7,8,9,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,0,10,28,29,30,31])) },
	link_sobjects: { load: () => __vitePreload(() => import("./RelatedObjects.js"), __vite__mapDeps([11,1,2,3,4,5,6,7,8,9,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,0,10,28,29,30,31])) },
	add_sobject: { load: () => __vitePreload(() => import("./RecordForm.js"), __vite__mapDeps([20,1,2,3,4,5,6,7,8,9,21,12,19,22])) },
	task_editor: { load: () => __vitePreload(() => import("./RecordForm.js"), __vite__mapDeps([20,1,2,3,4,5,6,7,8,9,21,12,19,22])) },
	process_dependencies: { load: () => __vitePreload(() => import("./ProcessRules.js"), __vite__mapDeps([32,2,3,4,5,6,7,8,19,13,12,14,15,16,17,33])) },
	duplicate_sobject: {
		load: () => __vitePreload(() => import("./DuplicateSObject.js"), __vite__mapDeps([34,1,2,3,4,5,6,7,8,9,19,28,29,35])),
		args: (context) => [{ __search_key__: context.route.key }, false]
	},
	ingest_files: { load: () => __vitePreload(() => import("./IngestFiles.js"), __vite__mapDeps([36,2,3,4,5,6,7,8,19,24,25,26,27,37])) },
	snapshot_append: {
		load: () => __vitePreload(() => import("./ObjectCheckin.js"), __vite__mapDeps([38,2,3,4,5,6,7,8,19,14,15,24,25,39,40])),
		args: (context) => [{ __search_key__: context.route.key }, { append: true }]
	},
	project_templates: { load: () => __vitePreload(() => import("./ProjectTemplates.js").then((n) => n.n), __vite__mapDeps([41,1,2,3,4,5,6,7,8,9,24,42])) },
	milestone_manager: { load: () => __vitePreload(() => import("./MilestoneManager.js").then((n) => n.n), __vite__mapDeps([43,1,2,3,4,5,6,7,8,9,44])) },
	snapshot_checkout: { load: () => __vitePreload(() => import("./SnapshotCheckout.js"), __vite__mapDeps([45,2,3,4,5,6,7,8,19,14,16,24,46,47])) },
	task_manager: {
		ref: "taskManager",
		open: (app, context) => app.$refs.taskManager.open(...context.args || context.route.args || [])
	},
	user_profile: { ref: "userProfile" },
	activity_feed: { ref: "activityFeed" },
	notifications: { ref: "systemActivity" },
	debug_log: { ref: "debugLog" },
	ui_performance: { ref: "uiPerformance" },
	system_info: { ref: "systemInfo" },
	help: { ref: "help" },
	script_shelf_editor: { ref: "scriptShelf" },
	project_wizard: { ref: "projectCreation" },
	configuration: {
		open: async (app) => {
			await app.$options.components.Configuration.__asyncLoader();
			await app.showConfiguration();
		},
		ref: "configuration"
	},
	administration: { open: (app, context) => app.showAdministration(context.route?.section || null) },
	script_editor: {
		open: (app, context) => app.openScriptEditor(context.route?.path || ""),
		ref: "scriptEditor"
	},
	agent_request: {
		open: (app, context) => app.openAgentRequest(null, context.project),
		ref: "agentRequest"
	},
	agent_providers: {
		open: (app) => app.openAgentProviders(),
		ref: "agentProviders"
	},
	agent_mcp: {
		open: (app, context) => app.openAgentMcp(context.args?.[0] || context.route.args?.[0] || app.agentContext(), context.args?.[1] || context.route.args?.[1] || ""),
		ref: "agentMcp"
	}
};
function windowPageAddress(kind, project = "", route = {}) {
	if (!Object.hasOwn(windowPages, kind)) throw Error("This window cannot be opened separately.");
	const encoded = JSON.stringify(route);
	if (!route || typeof route !== "object" || Array.isArray(route) || encoded.length > 8192) throw Error("This window cannot be opened separately.");
	const url = new URL(project ? "/projects/" + encodeURIComponent(project) + "/" : "/", location.origin);
	url.searchParams.set("window", kind);
	if (Object.keys(route).length) url.searchParams.set("context", encoded);
	return url;
}
function readWindowPage(address = location) {
	const params = new URLSearchParams(address.search);
	if (!params.has("window")) return null;
	const kind = params.get("window"), encoded = params.get("context") || "{}";
	const match = address.pathname.match(/^\/projects\/([^/]+)\/$/);
	let route, project = "";
	try {
		project = match ? decodeURIComponent(match[1]) : "";
		route = encoded.length <= 8192 ? JSON.parse(encoded) : null;
	} catch {
		route = null;
	}
	return {
		kind,
		project,
		route,
		launch: params.get("launch") || ""
	};
}
function snapshot(value) {
	const raw = toRaw(value);
	if (raw instanceof Blob) return raw;
	if (Array.isArray(raw)) return raw.map(snapshot);
	if (raw && typeof raw === "object") return Object.fromEntries(Object.entries(raw).map(([key, item]) => [key, snapshot(item)]));
	if (typeof raw === "function") throw Error("Window context must contain data only.");
	return raw;
}
function receiveContext(page, login) {
	if (!page.launch) return Promise.resolve(page);
	return new Promise((resolve, reject) => {
		const channel = new BroadcastChannel("tactic-window:" + page.launch);
		const done = (value, error) => {
			clearInterval(retry);
			clearTimeout(deadline);
			channel.close();
			if (error) reject(Error(error));
			else resolve(value);
		};
		channel.onmessage = (event) => {
			if (event.data?.type === "context") {
				const value = event.data.value;
				if (value.user !== login || value.kind !== page.kind || value.project !== page.project) return done(null, "The window session or project changed. Reopen it from the original window.");
				channel.postMessage({ type: "accepted" });
				done(value);
			} else if (event.data?.type === "error") done(null, event.data.message);
		};
		const ready = () => channel.postMessage({
			type: "ready",
			login
		});
		const retry = setInterval(ready, 500);
		const deadline = setTimeout(() => done(null, "The original window is unavailable. Reopen this page from the application."), 15e3);
		ready();
	});
}
async function openWindowPageTarget(app, context) {
	const spec = windowPages[context.kind];
	if (!spec || !context.route || typeof context.route !== "object" || Array.isArray(context.route)) throw Error("This window cannot be opened separately.");
	if (spec.load) {
		const session = app.session;
		const module = await spec.load();
		if (app.session !== session) return;
		if (context.kind === "project_templates") app.windowPagePackages = (await projectCreationCatalog(session.ticket)).installedTemplates;
		if (app.session !== session) return;
		app.windowPageTool = markRaw(module.default);
		const values = {
			ticket: session.ticket,
			project: app.workspaceProject,
			currentUser: session.login,
			searchType: context.route.searchType || app.type,
			editView: context.route.editView || "edit",
			insertView: context.route.insertView || "insert",
			packages: app.windowPagePackages,
			dockMode: context.kind === "work_hours" ? context.route.mode || "week" : void 0
		};
		app.windowPageToolProps = Object.fromEntries(Object.entries(values).filter(([key]) => Object.hasOwn(module.default.props || {}, key)));
		await nextTick();
		await app.$refs.windowPageTool.open(...spec.args ? spec.args(context) : context.args || context.route.args || []);
		if (context.state) await app.$refs.windowPageTool.restoreWindowContext?.(context.state);
	} else if (spec.open) await spec.open(app, context);
	else await app.$refs[spec.ref].open(...context.args || context.route.args || []);
	await nextTick();
	if (context.kind === "configuration" && context.route.page) await app.$refs.configuration.restoreWindowContext({ page: context.route.page });
	if (context.kind === "agent_request" && context.route.request && !context.state) context.state = { selected: context.route.request };
	if (spec.ref && context.state) await app.$refs[spec.ref]?.restoreWindowContext?.(context.state);
}
async function bootstrapWindowPage(app) {
	const page = app.windowPage;
	if (!Object.hasOwn(windowPages, page.kind) || !page.route || typeof page.route !== "object" || Array.isArray(page.route)) throw Error("This window cannot be opened separately.");
	if (page.project && !app.projects.some((project) => project.code === page.project)) throw Error("Project is not available");
	const session = app.session;
	const context = await receiveContext(page, session.login);
	if (app.session !== session) return;
	app.windowPageContext = context;
	app.project = app.workspaceProject = page.project;
	app.type = context.workspace?.search_type || context.route.searchType || "";
	app.selectedKeys = [...context.workspace?.search_keys || []];
	app.view = context.workspace?.view || "table";
	await app.loadNavigation();
	if (app.session !== session) return;
	app.busy = false;
	app.restoringSession = false;
	app.routeReady = true;
	history.replaceState(null, "", windowPageAddress(page.kind, page.project, context.route));
	app.windowPage = {
		...page,
		route: context.route,
		launch: ""
	};
	await nextTick();
	await openWindowPageTarget(app, context);
	app.windowPageClosed = false;
}
function installWindowPages(app) {
	const channels = /* @__PURE__ */ new Set();
	let alive = true;
	const launch = (event) => {
		const { kind } = event.detail;
		if (!Object.hasOwn(windowPages, kind) || !app.session) return;
		try {
			const spec = windowPages[kind];
			const view = spec.ref ? app.$refs[spec.ref] : null;
			const supplied = event.detail.context;
			const values = (typeof supplied === "function" ? supplied() : supplied) || view?.windowContext?.() || {};
			if (kind === "sobject_info" && !values.route) values.route = { key: app.detail?.__search_key__ };
			if (kind === "administration") {
				if (app.administrationLocked) throw Error("Apply or discard unsaved changes first");
				values.route = { section: app.administrationSection };
			}
			const context = snapshot({
				...values,
				kind,
				project: values.project ?? app.workspaceProject ?? app.project ?? "",
				user: app.session.login,
				route: values.route || {},
				workspace: app.agentContext()
			});
			structuredClone(context);
			const ownerSession = app.session;
			const id = randomUuid(), channel = new BroadcastChannel("tactic-window:" + id);
			const close = () => {
				clearTimeout(timer);
				channel.close();
				channels.delete(close);
			};
			const timer = setTimeout(close, 12e4);
			channels.add(close);
			channel.onmessage = (message) => {
				if (message.data?.type === "ready") {
					if (!alive || app.session !== ownerSession || message.data.login !== context.user) {
						channel.postMessage({
							type: "error",
							message: "The window session or project changed. Reopen it from the original window."
						});
						close();
					} else channel.postMessage({
						type: "context",
						value: context
					});
				} else if (message.data?.type === "accepted") close();
			};
			const url = windowPageAddress(kind, context.project, context.route);
			url.searchParams.set("launch", id);
			window.open(url.href, "_blank", "noopener");
		} catch (error) {
			notify("error", error.message);
		}
	};
	const closed = (event) => {
		if (app.windowPage?.kind !== event.detail.kind) return;
		app.windowPageClosed = true;
		window.close();
	};
	const sessionChanged = (event) => {
		if (!app.windowPage || event.key !== "tactic_stream.session") return;
		let saved;
		try {
			saved = JSON.parse(event.newValue);
		} catch {
			saved = null;
		}
		if (saved?.ticket === app.session?.ticket && saved?.login === app.session?.login) return;
		app.sessionRequest++;
		app.session = null;
		app.windowPageTool = null;
		app.error = "Session ended. Sign in again.";
	};
	window.addEventListener("storage", sessionChanged);
	window.addEventListener("tactic-window-page", launch);
	window.addEventListener("tactic-window-page-closed", closed);
	return () => {
		alive = false;
		window.removeEventListener("tactic-window-page", launch);
		window.removeEventListener("tactic-window-page-closed", closed);
		for (const close of [...channels]) close();
		window.removeEventListener("storage", sessionChanged);
	};
}
//#endregion
//#region src/controls/window.js
var activeWindow = null;
var windowDirective = {
	mounted(element, binding) {
		if (element.tagName !== "DIALOG") return;
		let configuration = binding.value;
		const pageKind = readWindowPage()?.kind;
		let rootOwner = false;
		let header = null, host = null, retainedGeometry = null, hostedGeometry = null;
		let chrome = null, frameContent = null, contentClose = null, contentHelp = null;
		const show = element.show.bind(element), close = element.close.bind(element);
		const home = document.createComment("window owner");
		element.before(home);
		let owner = null, returnFocus = null;
		const nonmodal = () => ["window", "popup"].includes(configuration?.type);
		function closed() {
			if (element.matches(":popover-open")) element.hidePopover();
			owner?.removeEventListener("close", closeChild);
			owner = null;
			if (home.parentNode && (element.parentNode !== home.parentNode || element.previousSibling !== home)) home.after(element);
			if (activeWindow === element) activeWindow = null;
		}
		function nativeClosed() {
			if (element.open) return;
			closed();
			if (element.classList.contains("window-page-root")) window.dispatchEvent(new CustomEvent("tactic-window-page-closed", { detail: { kind: configuration?.kind } }));
			if (returnFocus?.isConnected) returnFocus.focus({ preventScroll: true });
			returnFocus = null;
		}
		function closeChild(event) {
			if (event.target === owner) element.close();
		}
		function raise(event) {
			if (!element.open || !element.matches(":popover-open") || activeWindow === element || element.querySelector("dialog:modal")) return;
			if (event && event.target.closest("[popover]") !== element) return;
			const focused = element.contains(document.activeElement) ? document.activeElement : null;
			element.hidePopover();
			element.showPopover();
			focused?.focus({ preventScroll: true });
			activeWindow = element;
		}
		element.show = () => {
			if (!nonmodal()) {
				if (element.matches(":modal")) element.focus();
				else show();
				return;
			}
			if (element.open) {
				element.dispatchEvent(new Event("windowshow"));
				raise();
				return;
			}
			returnFocus = document.activeElement;
			owner = returnFocus?.closest(configuration.type === "popup" ? "dialog[open]" : "dialog:modal") || [...document.querySelectorAll("dialog:modal")].at(-1) || null;
			if (owner === element || element.contains(owner)) owner = null;
			if (owner) {
				owner.append(element);
				owner.addEventListener("close", closeChild);
			}
			element.popover = "manual";
			show();
			element.showPopover();
			activeWindow = element;
			element.dispatchEvent(new Event("windowshow"));
		};
		element.close = (...args) => {
			closed();
			close(...args);
			if (returnFocus?.isConnected) returnFocus.focus({ preventScroll: true });
			returnFocus = null;
		};
		function escape(event) {
			if (event.key !== "Escape" || event.defaultPrevented || !nonmodal() || event.target.closest("dialog") !== element) return;
			event.preventDefault();
			event.stopPropagation();
			if (element.dispatchEvent(new Event("cancel", { cancelable: true }))) element.close();
		}
		function rememberGeometry(event) {
			if (event.target !== element || !element.open) return;
			const { x, y, width, height, maximized, restore } = event.detail;
			retainedGeometry = {
				rect: {
					x,
					y,
					width,
					height
				},
				maximized,
				restore
			};
		}
		element.addEventListener("windowgeometrychange", rememberGeometry);
		element.addEventListener("keydown", escape);
		element.addEventListener("close", nativeClosed);
		element.addEventListener("pointerdown", raise);
		function placeControls() {
			const last = [...header.querySelectorAll("button")].at(-1);
			const anchor = last?.parentElement.tagName === "FORM" ? last.parentElement : last;
			if (anchor) anchor.before(host);
			else header.append(host);
		}
		const attach = () => {
			const windowed = configuration !== false && configuration?.type !== "popup";
			element.classList.toggle("app-window", windowed);
			element.dataset.windowType = configuration?.type || "dialog";
			element.dataset.windowKind = configuration?.kind || "";
			if (element.open && !!pageKind && !rootOwner && configuration?.kind === pageKind && !document.querySelector(".window-page-root")) rootOwner = true;
			const pageRoot = rootOwner;
			element.classList.toggle("window-page-root", pageRoot);
			if (pageRoot) document.title = (element.getAttribute("aria-label") || configuration.kind) + " — TACTIC Stream";
			if (nonmodal()) element.setAttribute("aria-modal", "false");
			else element.removeAttribute("aria-modal");
			const featureHeader = !windowed ? null : [...element.querySelectorAll("header:not([data-window-chrome])")].find((header) => header.closest("dialog") === element) || null;
			const frameView = [...element.querySelectorAll(".frame-view")].find((view) => view.closest("dialog") === element);
			const frameHeader = windowed && (featureHeader?.classList.contains("frame-titlebar") || !featureHeader && !!frameView && (frameView.parentElement === element || frameView.parentElement?.parentElement === element && frameView.parentElement.matches(".frame-host, .frame-host-body")));
			if (frameHeader && !chrome) {
				chrome = document.createElement("header");
				chrome.dataset.windowChrome = "";
				chrome.className = "app-dialog-titlebar";
				element.prepend(chrome);
				element.classList.add("app-window-frame-host");
			} else if (!frameHeader && chrome) {
				chrome.remove();
				chrome = null;
				frameContent?.classList.remove("app-window-frame-content");
				frameContent = null;
				element.classList.remove("app-window-frame-host");
			}
			if (frameHeader) {
				let content = featureHeader || frameView;
				while (content.parentElement !== element) content = content.parentElement;
				if (frameContent !== content) {
					frameContent?.classList.remove("app-window-frame-content");
					frameContent = content;
					frameContent.classList.add("app-window-frame-content");
				}
			}
			const closeButton = featureHeader ? [...featureHeader.querySelectorAll("button")].find((button) => !button.closest(".app-window-controls") && button.querySelector("[data-icon=\"close\"], [data-icon=\"MDI_CLOSE\"]")) : null;
			const hiddenClose = frameHeader ? closeButton : null;
			if (contentClose !== hiddenClose) {
				contentClose?.classList.remove("app-window-content-close");
				contentClose = hiddenClose;
				contentClose?.classList.add("app-window-content-close");
			}
			const helpButton = frameHeader && featureHeader ? [...featureHeader.querySelectorAll("button")].find((button) => !button.closest(".app-window-controls") && button.querySelector("[data-icon=\"help\"], [data-icon=\"MDI_HELP_CIRCLE\"]")) : null;
			if (contentHelp !== helpButton) {
				contentHelp?.classList.remove("app-window-content-help");
				contentHelp = helpButton;
				contentHelp?.classList.add("app-window-content-help");
			}
			const next = chrome || featureHeader;
			const properties = () => ({
				element,
				header,
				geometry: hostedGeometry,
				backProvided: !!configuration?.backProvided,
				title: chrome ? element.getAttribute("aria-label") || element.dataset.windowKind : "",
				closeButton: contentClose,
				closeRequired: !!chrome || !closeButton,
				closeDisabled: !!contentClose?.disabled,
				helpButton: contentHelp,
				helpLabel: contentHelp?.getAttribute("aria-label") || "",
				helpDisabled: !!contentHelp?.disabled,
				pageRoot,
				openSeparate: !pageRoot && Object.hasOwn(windowPages, configuration?.kind || "") ? () => window.dispatchEvent(new CustomEvent("tactic-window-page", { detail: {
					kind: configuration.kind,
					context: configuration.page
				} })) : null
			});
			if (next === header) {
				if (host && !header.contains(host)) placeControls();
				if (host) render(h(_sfc_main, properties()), host);
				return;
			}
			if (host) {
				render(null, host);
				host.remove();
			}
			header = next;
			host = null;
			if (!header) return;
			hostedGeometry = configuration?.geometry || retainedGeometry;
			host = document.createElement("span");
			host.className = "app-window-controls";
			placeControls();
			render(h(_sfc_main, properties()), host);
		};
		const observer = new MutationObserver(attach);
		observer.observe(element, {
			childList: true,
			subtree: true,
			attributes: true,
			attributeFilter: [
				"aria-label",
				"disabled",
				"open"
			]
		});
		attach();
		element.windowConfigure = (value) => {
			if (value?.geometry) hostedGeometry = value.geometry;
			configuration = value;
			attach();
		};
		element.windowCleanup = () => {
			closed();
			home.remove();
			element.show = show;
			element.close = close;
			element.removeEventListener("windowgeometrychange", rememberGeometry);
			element.removeEventListener("keydown", escape);
			element.removeEventListener("close", nativeClosed);
			element.removeEventListener("pointerdown", raise);
			observer.disconnect();
			if (host) {
				render(null, host);
				host.remove();
			}
			chrome?.remove();
			frameContent?.classList.remove("app-window-frame-content");
			contentClose?.classList.remove("app-window-content-close");
			contentHelp?.classList.remove("app-window-content-help");
			element.classList.remove("app-window-frame-host");
		};
	},
	updated(element, binding) {
		element.windowConfigure?.(binding.value);
	},
	beforeUnmount(element) {
		element.windowCleanup?.();
		element.classList.remove("app-window");
		delete element.windowCleanup;
		delete element.windowConfigure;
	}
};
//#endregion
//#region src/main.js
initializeAppearance();
installDebugLogging();
var documentation = location.pathname === "/docs" || location.pathname === "/docs/";
if (documentation) watchEffect(() => {
	document.title = t("TACTIC Stream — API reference");
});
var screen = asyncComponent(documentation ? () => __vitePreload(() => import("./ApiDocumentation.js"), __vite__mapDeps([48,2,3,4,5,6,7,8,49,50,23,51])) : () => __vitePreload(() => import("./App.js").then((n) => n.t), __vite__mapDeps([52,1,2,3,4,5,6,7,8,9,49,50,12,19,20,21,22,13,14,15,16,17,18,23,24,25,26,27,0,10,28,29,11,31,30,53,46,39,43,44,41,42,54])));
createApp({ render: () => h(screen) }).directive("window", windowDirective).mount("#app");
//#endregion
export { workspaceLayouts as $, resultItems as A, logEvent as At, serverRuntime as B, projectCreationCatalog as C, debugLog as Ct, resetRequestActivity as D, formatEvent as Dt, requestActivity as E, forgetSessions as Et, searchConfiguration as F, setServerDebugContext as Ft, tableDependencies as G, sessionAction as H, securityGroups as I, randomId as It, transactionDetails as J, tableDependencyFile as K, securityRules as L, randomUuid as Lt, saveServerConfiguration as M, redact as Mt, scriptEditor as N, savedSessions as Nt, resolveCustomUrl as O, importSession as Ot, scriptShelf as P, sessionRecords as Pt, widgetConfiguration as Q, securityUsers as R, asyncComponent as Rt, projectCatalog as S, clearLive as St, rawDatabase as T, exportSession as Tt, sidebarRequest as U, serverUpdates as V, tableCells as W, userAvatar as X, uploadFormFile as Y, userProfile as Z, messagesRequest as _, dockMinimumHeight as _t, __vitePreload as a, cancelNotificationReply as at, objectRelations as b, mobile as bt, beginActivity as c, editNotificationReply as ct, endActivity as d, notify as dt, setUpdatesAvailable as et, formDefinition as f, resetNotifications as ft, messageFileRequest as g, serverTimestamp as gt, linkPreviews as h, serverClock as ht, readWindowPage as i, beginNotificationReply as it, rpc as j, logRequest as jt, restartServer as k, levels as kt, columnsEditor as l, failNotificationReply as lt, knowledgeRequest as m, submitNotificationReply as mt, bootstrapWindowPage as n, updatesAvailable as nt, fileBlob as o, clearNotificationHistory as ot, interfaceDefinition as p, setNotificationProgress as pt, tableParentGroup as q, installWindowPages as r, activeNotifications as rt, activityFeed as s, dismissNotification as st, windowDirective as t, updateDelay as tt, databaseResources as u, notificationHistory as ut, navigationLink as v, dockMinimumWidth as vt, projectNavigation as w, debugSettings as wt, objectStatus as x, mobileLayout as xt, objectDeletion as y, fit as yt, serverConfiguration as z };

//# sourceMappingURL=index.js.map