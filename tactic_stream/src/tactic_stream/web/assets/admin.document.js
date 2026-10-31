import { A as onMounted, C as inject, E as nextTick, F as resolveComponent, G as withCtx, H as watch, I as resolveDirective, K as withDirectives, L as resolveDynamicComponent, M as openBlock, N as renderList, O as onBeforeUnmount, S as h, W as watchPostEffect, X as ref, _ as createElementBlock, b as createVNode, et as unref, f as Teleport, g as createCommentVNode, h as createBlock, l as withModifiers, m as createBaseVNode, nt as normalizeStyle, p as computed, rt as toDisplayString, tt as normalizeClass, u as Fragment, y as createTextVNode } from "./vue.js";
import { T as metrics, a as _sfc_main$8, o as t, s as appearance, t as _sfc_main$7, z as _plugin_vue_export_helper_default } from "./AppButton.js";
import { ht as serverTimestamp, k as resultItems, mt as serverClock, o as fileBlob, yt as mobile } from "./index.js";
import { A as _sfc_main$10, G as node, H as label, K as rect, R as observeFrameSizes, S as translate, T as ItemPreview_default, V as button, W as muted, t as _sfc_main$9 } from "./FrameView.js";
import { n as qtLabelTextWidth } from "./textMetrics.js";
import { r as prettySize } from "./file_values.js";
import "./files.js";
import { t as downloadBlob } from "./files2.js";
//#region src/controls/richText.js
function escapeHtml(value) {
	return String(value ?? "").replace(/[&<>"']/g, (char) => ({
		"&": "&amp;",
		"<": "&lt;",
		">": "&gt;",
		"\"": "&quot;",
		"'": "&#39;"
	})[char]);
}
function extractSkeys(value) {
	return [...new Set([...String(value ?? "").matchAll(/skey:\/\/[^\s<>"]+/g)].map((match) => match[0].replace(/[.,;:!?\)\]}]+$/, "")))];
}
function withoutSkeys(value) {
	return String(value ?? "").replace(/skey:\/\/[^\s<>"]+/g, (raw) => raw.slice(raw.replace(/[.,;:!?\)\]}]+$/, "").length)).trim();
}
function linkifyPlainText(value, linkHref = (value) => value) {
	const text = String(value ?? "");
	let result = "", offset = 0;
	for (const match of text.matchAll(/(?:skey|tactic-search|https?|ftp):\/\/[^\s<>"]+/gi)) {
		const target = match[0].replace(/[.,;:!?\)\]}]+$/, "");
		const internal = /^(skey|tactic-search):/i.test(target);
		result += escapeHtml(text.slice(offset, match.index));
		result += "<a href=\"" + escapeHtml(linkHref(target)) + "\"" + (internal ? " data-rich-link=\"" + escapeHtml(target) + "\"" : " target=\"_blank\" rel=\"noopener noreferrer\"") + ">" + escapeHtml(target) + "</a>";
		result += escapeHtml(match[0].slice(target.length));
		offset = match.index + match[0].length;
	}
	return (result + escapeHtml(text.slice(offset))).replace(/\r?\n/g, "<br>");
}
function activateRichLink(event, open) {
	const anchor = event.target.closest("a[data-rich-link]");
	if (!anchor || event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return false;
	event.preventDefault();
	open(anchor.dataset.richLink);
	return true;
}
//#endregion
//#region src/features/workspace/links.js
function projectPath(project) {
	return project ? "/projects/" + encodeURIComponent(project) + "/" : "/";
}
function addressProject(address) {
	const match = /^\/projects\/([^/]+)(?:\/.*)?$/.exec(address.pathname) || /^\/tactic\/([^/]+)\/.+$/.exec(address.pathname);
	if (match) try {
		return decodeURIComponent(match[1]);
	} catch {
		return "";
	}
	return "";
}
function customUrlLocation(address) {
	const match = /^\/(?:projects|tactic)\/[^/]+(\/.+)$/.exec(address.pathname);
	const hash = address.hash?.startsWith("#/") ? address.hash.slice(1) : "";
	if (!match && !hash) return null;
	const [hashPath, hashQuery = ""] = hash.split("?");
	const parameters = new URLSearchParams(address.search);
	for (const [key, value] of new URLSearchParams(hashQuery)) parameters.set(key, value);
	let path = hash ? hashPath : match[1];
	try {
		path = decodeURIComponent(path);
	} catch {}
	return {
		path,
		parameters: Object.fromEntries(parameters),
		address: address.pathname + address.search + (address.hash || "")
	};
}
function customPageLink(value, origin) {
	if (typeof value !== "string" || value.length > 16384 || /[\r\n\0\\]/.test(value)) return null;
	try {
		const address = new URL(value, origin);
		return address.origin === origin && !address.username && !address.password && addressProject(address) && customUrlLocation(address) ? address : null;
	} catch {
		return null;
	}
}
function browserLink(value, project = "") {
	if (!/^(skey|tactic-search):\/\//i.test(value)) return value;
	try {
		project = linkProject(value, project);
	} catch {}
	return projectPath(project) + "?" + new URLSearchParams({ link: value });
}
function linkProject(value, fallback) {
	if (typeof value !== "string" || value.length > 16384 || /[\r\n\0]/.test(value)) throw new Error("Invalid TACTIC link");
	const url = new URL(value);
	if (!["skey:", "tactic-search:"].includes(url.protocol)) throw new Error("Invalid TACTIC link");
	return url.searchParams.get("project") || url.searchParams.get("project_code") || fallback;
}
function searchLink(value) {
	const text = String(value || "").trim();
	if (/^(skey|tactic-search):\/\//i.test(text)) return text;
	if (/^[\w.-]+\/[\w.-]+\?/.test(text) && /[?&](code|id)=[^&]+/.test(text)) return "skey://" + text;
	return "";
}
function workspaceAddress(project, searchType, view, link = "") {
	if (link) return browserLink(link, project);
	const params = new URLSearchParams({
		search_type: searchType,
		view
	});
	return projectPath(project) + "?" + params;
}
function savedSearchLink(project, searchType, view) {
	return "tactic-search://open?" + new URLSearchParams({
		project,
		search_type: searchType,
		view
	});
}
function sameSearchKey(left, right, project = "") {
	if (!left || !right) return false;
	try {
		const a = new URL(searchLink(left)), b = new URL(searchLink(right));
		if (a.host + a.pathname !== b.host + b.pathname) return false;
		if (a.host !== "sthpw" && (a.searchParams.get("project") || project) !== (b.searchParams.get("project") || project)) return false;
		const field = a.searchParams.has("code") && b.searchParams.has("code") ? "code" : "id";
		return a.searchParams.has(field) && b.searchParams.has(field) && a.searchParams.get(field) === b.searchParams.get(field);
	} catch {
		return false;
	}
}
//#endregion
//#region src/features/activity/activity.js
function dateKey(date) {
	return [
		date.getFullYear(),
		String(date.getMonth() + 1).padStart(2, "0"),
		String(date.getDate()).padStart(2, "0")
	].join("-");
}
function dateLabel(value, options = {
	day: "numeric",
	month: "short",
	year: "numeric"
}) {
	if (!value) return t("All history");
	const date = /* @__PURE__ */ new Date(value.slice(0, 10) + "T12:00:00");
	return Number.isNaN(date.getTime()) ? t("No date") : date.toLocaleDateString(appearance.language, options);
}
function dayLabel(value) {
	if (!value) return t("No date");
	const today = new Date(serverClock.now()), yesterday = new Date(today);
	yesterday.setDate(today.getDate() - 1);
	const prefix = value === dateKey(today) ? t("Today") : value === dateKey(yesterday) ? t("Yesterday") : "";
	const suffix = dateLabel(value, {
		weekday: "long",
		day: "numeric",
		month: "long",
		year: "numeric"
	});
	return prefix ? prefix + "  ·  " + suffix : suffix;
}
function timestampLabel(timestamp, now = new Date(serverClock.now())) {
	const value = serverTimestamp(timestamp);
	if (Number.isNaN(value.getTime())) return "";
	const seconds = (now - value) / 1e3;
	if (seconds >= 0 && seconds < 60) return t("Just now");
	if (seconds >= 0 && seconds < 3600) return t("{count} min ago", { count: Math.floor(seconds / 60) });
	if (seconds >= 0 && seconds < 86400) return t("{count} h ago", { count: Math.floor(seconds / 3600) });
	if (seconds >= 0 && seconds < 172800) return t("Yesterday");
	if (seconds >= 0 && seconds < 604800) return t("{count} days ago", { count: Math.floor(seconds / 86400) });
	if (seconds >= 0 && seconds < 2629800) return t("{count} wk ago", { count: Math.floor(seconds / 604800) });
	return timestampFullLabel(timestamp);
}
function timestampFullLabel(timestamp) {
	const value = serverTimestamp(timestamp);
	return Number.isNaN(value.getTime()) ? "" : value.toLocaleString(appearance.language, {
		day: "numeric",
		month: "long",
		year: "numeric",
		hour: "2-digit",
		minute: "2-digit",
		second: "2-digit",
		hour12: false
	});
}
function matchesSearch(record, text) {
	const haystack = [
		"actorLabel",
		"actor",
		"title",
		"detail",
		"targetTitle",
		"targetTypeTitle",
		"itemTitle",
		"itemTypeTitle",
		"process",
		"context",
		"statusBefore",
		"statusAfter",
		"version",
		"workDay",
		"workHourCategory",
		"workHourStatus",
		"workHourOwner"
	].map((key) => record[key] || "").join("\n").toLocaleLowerCase();
	return text.toLocaleLowerCase().trim().split(/\s+/).every((word) => haystack.includes(word));
}
function uniqueRecords(records) {
	return [...new Map(records.slice().reverse().map((row) => [row.eventId, row])).values()].reverse();
}
function safeColor(value) {
	return /^#[0-9a-f]{6}([0-9a-f]{2})?$/i.test(value || "") ? value : "";
}
function compactText(value) {
	const text = String(value || "").replace(/\s+/g, " ").trim();
	return text.length > 80 ? text.slice(0, 80).trimEnd() + "…" : text;
}
function needsExpansion(value) {
	return /[\r\n]/.test(value || "") || String(value || "").replace(/\s+/g, " ").trim().length > 80;
}
function changeValue(record, change) {
	if (change.valuesKnown === false) return t("Changed");
	const before = String(change.before || ""), after = String(change.after || "");
	if (record.kind === "create" && after) return after;
	if (record.kind === "delete" && before) return t("Previous value: {value}", { value: before });
	return before || after ? (before || t("empty")) + " → " + (after || t("empty")) : t("Changed");
}
function eventSentence(row, expanded) {
	const html = (value) => escapeHtml(value).replace(/\r?\n/g, "<br>");
	const link = (value, action, enabled) => enabled ? "<a href=\"#" + action + "\" data-action=\"" + action + "\">" + html(value) + "</a>" : html(value);
	const colored = (value, color) => safeColor(color) ? "<span data-color=\"" + safeColor(color) + "\">" + html(value) + "</span>" : html(value);
	const semantic = (value, color) => colored((safeColor(color) ? "● " : "") + value, color);
	const shortType = (value) => String(value || "").split("/").at(-1).replaceAll("_", " ");
	const reference = (item = false) => {
		const title = (item ? row.itemTitle : row.targetTitle) || t("the related object");
		const type = item ? row.itemTypeTitle || {
			"sthpw/task": t("Task"),
			"sthpw/note": t("Note"),
			"sthpw/snapshot": t("Snapshot")
		}[row.itemType] || shortType(row.itemType) : row.targetTypeTitle || (row.relationAction ? "" : shortType(row.targetType));
		return (type ? semantic(type, item ? row.itemTypeColor : row.typeColor) + " / " : "") + link(title, item ? "activity" : "target", item ? !!row.searchKey : !!row.targetSearchKey);
	};
	const target = reference(), processName = row.process || String(row.context || "").split("/")[0];
	const process = processName ? t(" in process {process}", { process: "<b>" + semantic(processName, row.processColor) + "</b>" }) : "";
	const context = row.context && row.context !== processName ? t(", context {context}", { context: "<b>" + html(row.context) + "</b>" }) : "";
	const detail = linkifyPlainText(expanded ? row.detail : compactText(row.detail), browserLink);
	const action = link(t(row.kind === "note" ? "Open note" : row.kind === "task" ? "Open task" : "Open details"), "activity", !!row.searchKey);
	if (row.relationAction) return t(row.relationAction === "link" ? "Linked {item} to {target}." : "Removed the link between {item} and {target}.", {
		item: reference(true),
		target
	});
	if (row.kind === "publication") {
		const raw = String(row.version ?? ""), version = /^\d+$/.test(raw) ? "v" + raw.padStart(3, "0") : raw;
		return t("Committed snapshot {item} to {target}{process}{context}{version}.{comment}", {
			item: link(row.itemTitle || row.itemCode || t("snapshot"), "activity", !!row.searchKey),
			target,
			process,
			context,
			version: version ? t(", version {version}", { version: "<b>" + html(version) + "</b>" }) : "",
			comment: detail ? t(" Comment: “{detail}”", { detail }) : ""
		});
	}
	if (row.kind === "note") return t("Added a note to {target}{process}{context}: {detail} {action}", {
		target,
		process,
		context,
		detail: detail || t("No text"),
		action
	});
	if (row.kind === "task") return t(row.serverGenerated ? "Created task for {target}{process}{context}: {status}" : "Updated task for {target}{process}{context}: {status}", {
		target,
		process,
		context,
		status: row.statusAfter ? "<b>" + colored(row.statusAfter, row.statusAfterColor) + "</b>" : detail || action
	});
	if (row.kind === "status") return row.statusBefore || row.statusAfter ? t("Changed status for {target}{process}{context}: {before} → {after}.", {
		target,
		process,
		context,
		before: "<b>" + colored(row.statusBefore || "—", row.statusBeforeColor) + "</b>",
		after: "<b>" + colored(row.statusAfter || "—", row.statusAfterColor) + "</b>"
	}) : t("Updated the status of {target}{process}{context}: {detail}", {
		target,
		process,
		context,
		detail: detail || action
	});
	if (row.kind === "create" || row.kind === "delete") return row.itemType ? t(row.kind === "create" ? "Created {item} for {target}." : "Deleted {item} from {target}.", {
		item: reference(true),
		target
	}) : t(row.kind === "create" ? "Created object: {target}." : "Deleted object: {target}.", { target });
	if (row.kind === "change") return t("Updated {target}.{detail}", {
		target,
		detail: (row.changes || []).length || !detail ? "" : " " + detail
	});
	if (row.kind === "work_hour") {
		const hours = t("{hours} h", { hours: Number(row.hours || 0).toLocaleString(appearance.language, { maximumFractionDigits: 2 }) });
		const owner = row.workHourOwner && row.workHourOwner !== row.actor ? t(" for user {user}", { user: "<b>" + html(row.workHourOwner) + "</b>" }) : "";
		const sentence = row.workHourAction === "delete" ? "Deleted a {hours} work-hours entry{owner} for {target}{process} on {date} ({category})." : row.workHourAction === "change" ? "Updated work hours to {hours}{owner} for {target}{process} on {date} ({category}, {status})." : "Logged {hours}{owner} for {target}{process} on {date} ({category}, {status}).";
		return t(sentence, {
			hours,
			owner,
			target,
			process,
			date: html(dateLabel(row.workDay)),
			category: t(row.workHourCategory === "overtime" ? "Overtime" : "Regular"),
			status: t(String(row.workHourStatus || "").toLowerCase() === "approved" ? "Approved" : "Pending")
		}) + (detail ? t(" Comment: “{detail}”", { detail }) : "");
	}
	return detail || html(expanded ? row.title : compactText(row.title));
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/objects/report.ui.mjs
var sections = [
	{
		value: "tasks",
		label: "Tasks",
		icon: "task"
	},
	{
		value: "notes",
		label: "Notes",
		icon: "notes"
	},
	{
		value: "children",
		label: "Children",
		icon: "account-tree"
	},
	{
		value: "snapshots",
		label: "Snapshots",
		icon: "snapshot"
	},
	{
		value: "activity",
		label: "Activity",
		icon: "activity-feed"
	}
];
function metric(id, title, value, bounds, color, language) {
	return node("Box", id, bounds, {
		background: "transparent",
		children: [label(id + "Value", rect(0, 0, bounds.width, 28), String(value ?? 0), {
			fontRole: "statistic",
			weight: 600,
			color: color || "primaryText"
		}), label(id + "Label", rect(0, 29, bounds.width, 15), translate(title, language), {
			fontRole: "caption",
			weight: 600,
			color: "secondaryText"
		})]
	});
}
function header(model, width, language, measure = (text, size) => String(text).length * size * .55) {
	const tr = (text) => translate(text, language), summary = model.summary || {}, metrics = model.metrics || {};
	const preview = width >= 700 ? 142 : width >= 420 ? 116 : 82;
	const left = 14 + preview + (width >= 560 ? 18 : 10), textWidth = Math.max(0, width - left - 14);
	const columns = width >= 1040 ? 4 : width >= 560 ? 2 : 1;
	const fields = [
		[
			"Code",
			summary.code,
			"code"
		],
		[
			"Search Type",
			summary.searchType,
			"sobject"
		],
		[
			"Project",
			summary.project,
			"project-diagram"
		],
		[
			"Pipeline",
			summary.pipeline,
			"workflow"
		]
	].filter((row) => row[1]);
	function gridWidths(rows, count, available, gap, preferred) {
		const hints = Array.from({ length: count }, (_, column) => Math.max(1, ...rows.filter((_, index) => index % count === column).map(preferred)));
		const total = hints.reduce((sum, hint) => sum + hint, 0), room = Math.max(0, available - gap * (count - 1));
		return hints.map((hint) => room * hint / total);
	}
	const fieldWidths = gridWidths(fields, columns, textWidth, 14, ([title, value]) => 24 + Math.max(Math.ceil(measure(tr(title), 11)), Math.ceil(measure(String(value), 13))));
	const description = summary.description || tr("No description provided");
	const descriptionHeight = Math.min(42, Math.max(1, Math.ceil(measure(description, 13) / Math.max(1, textWidth))) * 17);
	const infoY = 80 + descriptionHeight, infoHeight = fields.length ? Math.ceil(fields.length / columns) * 38 - 5 : 0;
	const topHeight = Math.max(preview, infoY - 14 + infoHeight + 40);
	const metricColumns = width >= 1040 ? 8 : width >= 560 ? 4 : width >= 340 ? 2 : 1;
	const values = [
		["TASKS", metrics.tasks || 0],
		["NOTES", metrics.notes || 0],
		["CHILDREN", metrics.children || 0],
		["PEOPLE", metrics.participants || 0],
		["WORK HOURS", Number(metrics.workHours || 0).toFixed(1) + " " + tr("h")],
		["FILES", metrics.files || 0],
		["SNAPSHOTS", metrics.snapshots || 0],
		[metrics.canViewCosts ? "TOTAL COST" : "TOTAL SIZE", metrics.canViewCosts ? Number(metrics.totalCost || 0).toFixed(2) : metrics.totalSize || "0 B"]
	];
	const metricRows = Math.ceil(8 / metricColumns), metricHeight = width >= 1040 ? 50 : width >= 560 ? 86 : metricRows * 44 + (metricRows - 1) * 5;
	const height = Math.max(256, 28 + topHeight + 21 + metricHeight), extra = height - (28 + topHeight + 21 + metricHeight);
	const nodes = [
		node("Box", "objectReportHeaderSurface", rect(0, 0, width, height), {
			background: "surfaceContainerHigh",
			border: "outlineVariant"
		}),
		node("Preview", "objectReportPreview", rect(14, 14 + (topHeight - preview) / 2, preview, preview), {
			source: summary.previewUrl || "",
			initials: String(summary.title || "?").slice(0, 2).toUpperCase(),
			icon: "sobject",
			accent: summary.accent || "action",
			outlined: true,
			radius: 12,
			round: false
		}),
		label("objectReportTitle", rect(left, 14, textWidth, 24), summary.title || tr("No sObject selected"), {
			fontRole: "display",
			weight: 600
		}),
		node("StatusChip", "objectReportType", rect(left, 44, Math.min(textWidth, Math.ceil(measure(summary.typeTitle || "", 11, 600)) + 34), 24), {
			text: summary.typeTitle || "",
			icon: "sobject",
			accent: summary.accent || "action"
		}),
		node("View", "objectReportDescription", rect(left, 74, textWidth, descriptionHeight), {
			view: "reportDescription",
			text: description,
			empty: !summary.description
		})
	];
	fields.forEach(([title, value, icon], index) => {
		const column = index % columns, x = left + fieldWidths.slice(0, column).reduce((sum, value) => sum + value + 14, 0), y = infoY + Math.floor(index / columns) * 38, cell = fieldWidths[column];
		nodes.push(node("Icon", "objectReportFieldIcon_" + index, rect(x, y + 9, 15, 15), {
			icon,
			color: "secondaryText",
			iconSize: 15
		}));
		nodes.push(label("objectReportFieldLabel_" + index, rect(x + 24, y, cell - 24, 15), tr(title), Object.assign({}, muted, { fontRole: "caption" })));
		nodes.push(label("objectReportFieldValue_" + index, rect(x + 24, y + 15, cell - 24, 18), String(value), {
			fontRole: "body",
			elide: "middle"
		}));
	});
	nodes.push(label("objectReportUpdated", rect(left, 14 + topHeight - 28, textWidth - 66, 28), summary.updatedPretty ? tr("Updated") + ": " + summary.updatedPretty : "", Object.assign({}, muted, {
		fontRole: "caption",
		tooltip: summary.updatedFull || ""
	})));
	[[
		"open",
		"Open sObject",
		"open-in-new"
	], [
		"refresh",
		"Refresh report",
		"refresh"
	]].forEach(([type, text, icon], index) => nodes.push(button("objectReport_" + type, rect(width - 74 + index * 33, topHeight - 14, 28, 28), tr(text), icon, { type }, !!summary.searchKey && (type !== "refresh" || !model.busy), {
		iconOnly: true,
		iconAction: true,
		iconSize: 16
	})));
	nodes.push(node("Box", "objectReportHeaderDivider", rect(14, 24 + topHeight, width - 28, 1), {
		background: "separator",
		radius: 0
	}));
	const widths = gridWidths(values, metricColumns, width - 28, 12, ([title, value]) => Math.max(Math.ceil(measure(tr(title), 11, 600) + tr(title).length * .25), Math.ceil(measure(String(value), 21, 600))));
	values.forEach(([title, value], index) => {
		const column = index % metricColumns;
		nodes.push(metric("objectReportMetric_" + index, title, value, rect(14 + widths.slice(0, column).reduce((sum, value) => sum + value + 12, 0), 35 + topHeight + extra + Math.floor(index / metricColumns) * 49, widths[column], 44), "", language));
	});
	return {
		nodes,
		height
	};
}
function tabs$1(page, width, language) {
	const gap = 2, cell = Math.max(0, (width - 8) / 5), narrow = width < 420;
	return {
		height: 36,
		nodes: sections.map((section, index) => button("objectReportTab_" + section.value, rect(index * (cell + gap), 0, cell, 36), translate(section.label, language), section.icon, {
			type: "page",
			value: section.value
		}, true, {
			radio: true,
			selected: page === section.value,
			iconOnly: narrow,
			iconSize: 16
		}))
	};
}
function status(id, text, x, y, maximum, accent, icon) {
	const width = Math.min(Math.max(0, maximum), String(text || "").length * 6 + 30);
	return node("StatusChip", id, rect(x, y, width, 24), {
		text,
		icon,
		accent: accent || "secondaryText",
		fontRole: "caption",
		weight: 600
	});
}
function row(kind, record, width, index, language) {
	const tr = (text) => translate(text, language), children = [];
	const accent = record.processColor || record.authorColor || record.accent || "action";
	let height = kind === "person" ? 76 : kind === "child" ? 68 : 72;
	let title = record.title || "", subtitle = record.subtitle || "";
	function text(id, x, y, w, h, value, options) {
		children.push(label(id, rect(x, y, w, h), value || "", options));
	}
	function preview(size, x, y, source, initials, round) {
		children.push(node("Preview", "objectReportRowPreview", rect(x, y, size, size), {
			source: source || "",
			initials: initials || "",
			icon: kind === "child" ? "sobject" : "person",
			accent: kind === "person" ? record.avatarColor || accent : accent,
			round,
			radius: round ? size / 2 : 12,
			outlined: round
		}));
	}
	if (kind === "person") {
		title = record.displayName;
		preview(42, 10, 17, record.avatarUrl, record.initials, true);
		text("objectReportRowTitle", 61, 17, width - 161, 22, title, { weight: 600 });
		subtitle = translate("{tasks} tasks · {notes} notes · {snapshots} snapshots", language, {
			tasks: record.taskCount,
			notes: record.noteCount,
			snapshots: record.snapshotCount
		});
		text("objectReportRowSubtitle", 61, 42, width - 161, 17, subtitle, {
			fontRole: "caption",
			color: "secondaryText"
		});
		text("objectReportRowHours", width - 92, 27, 62, 22, Number(record.hours || 0).toFixed(1) + " " + tr("h"), {
			align: "right",
			color: record.hours > 0 ? record.accent || "action" : "secondaryText",
			weight: 600
		});
		if (record.cost > 0) text("objectReportRowCost", width - 130, 42, 100, 17, tr("Cost") + " " + Number(record.cost).toFixed(2), {
			fontRole: "caption",
			align: "right",
			color: "secondaryText"
		});
	} else if (kind === "task") {
		title = record.processLabel;
		children.push(node("Box", "objectReportTaskIconSurface", rect(12, 17, 38, 38), {
			background: "panelRaised",
			radius: 12,
			children: [node("Icon", "taskProcessIcon", rect(11, 11, 16, 16), {
				icon: "workflow",
				color: accent
			})]
		}));
		let right = width - 30;
		if (width >= 760) {
			text("taskNotes", right - 20, 26, 20, 18, String(record.notesCount || 0), {
				fontRole: "caption",
				color: "secondaryText"
			});
			right -= 30;
			children.push(node("Icon", "taskNotesIcon", rect(right - 14, 29, 14, 14), {
				icon: "notes",
				color: "secondaryText"
			}));
			right -= 24;
			text("taskProgress", right - 38, 26, 38, 18, (record.progress || 0) + "%", {
				fontRole: "secondary",
				weight: 600
			});
			right -= 48;
			if (record.endPretty) {
				const extent = Math.min(110, String(record.endPretty).length * 6 + 4);
				text("taskDeadline", right - extent, 26, extent, 18, record.endPretty, {
					fontRole: "caption",
					color: record.dueState === "overdue" ? "error" : "secondaryText",
					tooltip: record.endFull || ""
				});
				right -= extent + 10;
			}
			text("taskHours", right - 84, 26, 84, 18, Number(record.loggedHours || 0).toFixed(1) + " / " + Number(record.plannedHours || 0).toFixed(1) + " " + tr("h"), {
				fontRole: "caption",
				color: "secondaryText"
			});
			right -= 94;
			const assignedWidth = 140;
			children.push(node("Preview", "taskAssigneeAvatar", rect(right - assignedWidth, 23, 26, 26), {
				source: record.assignedAvatar || "",
				initials: String(record.assignedLabel || "").slice(0, 2).toUpperCase(),
				icon: "person",
				accent: record.assignedColor || "action",
				round: true,
				outlined: false
			}));
			text("taskAssignee", right - assignedWidth + 32, 26, 108, 18, record.assignedLabel, {
				fontRole: "caption",
				color: "secondaryText"
			});
			right -= 150;
			const chip = status("taskStatus", record.status || "", Math.max(60, right - 110), 13, 110, record.statusColor, "system-activity");
			children.push(chip);
			text("objectReportRowTitle", 60, 13, Math.max(0, right - 60 - chip.width - 8), 22, title, {
				fontRole: "bodyLarge",
				weight: 600
			});
			text("objectReportRowSubtitle", 60, 39, right - 60, 18, record.description || record.assignedLabel, {
				fontRole: "caption",
				color: "secondaryText"
			});
		} else {
			text("objectReportRowTitle", 60, 7, width - 90, 22, title, {
				fontRole: "bodyLarge",
				weight: 600
			});
			text("objectReportRowSubtitle", 60, 30, width - 90, 17, record.description || record.assignedLabel, {
				fontRole: "caption",
				color: "secondaryText"
			});
			const detail = [
				record.status,
				record.assignedLabel,
				Number(record.loggedHours || 0).toFixed(1) + " / " + Number(record.plannedHours || 0).toFixed(1) + " " + tr("h"),
				record.endPretty,
				(record.progress || 0) + "%"
			].filter(Boolean).join(" · ");
			text("objectReportRowMeta", 60, 50, width - 90, 17, detail, {
				fontRole: "caption",
				color: record.dueState === "overdue" ? "error" : "secondaryText"
			});
		}
	} else if (kind === "note") {
		title = record.authorLabel;
		const available = Math.max(1, width - 90);
		let lines = 0;
		for (const paragraph of String(record.body || "").split("\n")) lines += Math.max(1, Math.ceil(paragraph.length * 7 / available));
		height = Math.max(84, lines * 18 + 54);
		preview(34, 11, 11, record.avatarUrl, record.initials, true);
		const chip = status("noteContext", record.isTaskNote ? record.taskTitle || tr("Task note") : tr("Object note"), Math.max(55, width - 220), 10, 116, accent, record.isTaskNote ? "task" : "sobject");
		children.push(chip);
		text("noteTimestamp", width - 96, 13, 70, 18, record.timestampPretty, {
			fontRole: "caption",
			color: "secondaryText",
			tooltip: record.timestampFull || ""
		});
		text("objectReportRowTitle", 55, 10, Math.max(0, chip.x - 61), 22, title, { weight: 600 });
		text("objectReportRowSubtitle", 55, 40, width - 85, height - 54, record.body, { wrap: true });
	} else {
		preview(44, 9, 12, record.previewUrl, String(title).slice(0, 2).toUpperCase(), false);
		const wide = width >= 600, extent = wide ? 270 : 0;
		text("objectReportRowTitle", 63, 14, width - 93 - extent, 22, title, { weight: 600 });
		text("objectReportRowSubtitle", 63, 39, width - 93 - extent, 17, subtitle, {
			fontRole: "caption",
			color: "secondaryText"
		});
		if (wide) {
			children.push(status("childType", record.typeTitle, width - 285, 22, 100, accent, "sobject"));
			if (record.status) children.push(status("childStatus", record.status, width - 177, 22, 100, "secondaryText", "system-activity"));
			text("childRelationship", width - 70, 25, 40, 18, record.relationship, {
				fontRole: "caption",
				color: "secondaryText"
			});
		}
	}
	children.push(node("Icon", "objectReportRowArrow", rect(Math.max(0, width - 25), (height - 15) / 2, 15, 15), {
		icon: "arrow-forward",
		color: "secondaryText"
	}));
	if (kind !== "person" || record.hours > 0) children.push(node("Box", "objectReportRowRail", rect(0, 5, 3, height - 10), {
		background: accent,
		radius: 0
	}));
	return {
		height,
		nodes: [node("Action", "objectReportRow_" + kind + "_" + index, rect(0, 0, width, height), {
			text: title || subtitle || "",
			normalColor: "transparent",
			radius: 0,
			action: {
				type: kind,
				index,
				key: record.searchKey || record.login || "",
				process: record.process || "",
				taskCode: record.taskCode || ""
			},
			children
		})]
	};
}
function page(model, width, language) {
	const tr = (text) => translate(text, language), nodes = [], metrics = model.metrics || {};
	let y = 0;
	function panel(id, title, icon, children, height, x = 0, panelWidth = width, detail = "") {
		nodes.push(node("Box", id, rect(x, y, panelWidth, height), {
			background: "panel",
			border: "outlineVariant",
			children: [
				node("Icon", id + "Icon", rect(14, 14, 15, 15), {
					icon,
					color: "action"
				}),
				label(id + "Title", rect(37, 10, Math.max(0, panelWidth - 51 - (detail ? 144 : 0)), 24), tr(title), { weight: 600 }),
				...detail ? [label(id + "Detail", rect(Math.max(0, panelWidth - 155), 13, 141, 18), detail, {
					align: "right",
					fontRole: "caption",
					color: "secondaryText"
				})] : [],
				...children
			]
		}));
		y += height + 12;
	}
	function rows(id, title, icon, kind, records, empty) {
		const columns = kind === "person" ? width >= 940 ? 3 : width >= 600 ? 2 : 1 : 1;
		const gap = kind === "person" ? 8 : 6, padding = kind === "person" ? 14 : 12;
		const rowWidth = Math.max(0, (width - padding * 2 - gap * (columns - 1)) / columns);
		let top = kind === "person" ? 52 : 44;
		const children = [];
		let rowHeight = 0;
		records.forEach((record, index) => {
			const scene = row(kind, Object.assign({}, record, { accent: record.accent || model.summary?.accent || "action" }), rowWidth, index, language);
			if (index > 0 && index % columns === 0) {
				top += rowHeight + gap;
				rowHeight = 0;
			}
			children.push(node("Box", id + "Row_" + index, rect(padding + index % columns * (rowWidth + gap), top, rowWidth, scene.height), {
				background: "transparent",
				children: scene.nodes
			}));
			rowHeight = Math.max(rowHeight, scene.height);
		});
		if (!records.length) {
			children.push(node("Icon", id + "EmptyIcon", rect(width / 2 - 15, 99, 30, 30), {
				icon,
				color: "secondaryText"
			}));
			children.push(label(id + "Empty", rect(12, 137, Math.max(0, width - 24), 36), tr(empty), Object.assign({}, muted, {
				align: "center",
				wrap: true
			})));
		}
		panel(id, title, icon, children, Math.max(kind === "person" ? 150 : 0, records.length ? top + rowHeight + 14 : 198), 0, width, kind === "person" ? translate("{count} people · {hours} h", language, {
			count: metrics.participants || 0,
			hours: Number(metrics.workHours || 0).toFixed(1)
		}) : kind === "task" ? translate("{count} tasks", language, { count: metrics.tasks || 0 }) : kind === "child" ? translate("{count} children", language, { count: metrics.children || 0 }) : kind === "note" ? translate("{objects} object · {tasks} task notes", language, {
			objects: metrics.objectNotes || 0,
			tasks: metrics.taskNotes || 0
		}) : "");
	}
	function chips(id, title, icon, records, action, x = 0, panelWidth = width, detail = "") {
		let left = 14, top = 44;
		panel(id, title, icon, records.map((record, index) => {
			const chip = status(id + "Chip_" + index, (record.label || record.value || tr("Unspecified")) + "  " + (record.count || 0), 0, 0, Math.max(0, panelWidth - 28), record.accent || "action", icon);
			if (left > 14 && left + chip.width > panelWidth - 14) {
				left = 14;
				top += 31;
			}
			chip.x = left;
			chip.y = top;
			chip.action = action ? {
				type: "filter",
				field: action,
				value: record.value
			} : null;
			left += chip.width + 7;
			return chip;
		}), id === "objectChildTypes" ? records.length ? top + 24 + 12 : 52 : Math.max(150, top + 38), x, panelWidth, id === "objectChildTypes" ? translate("{count} relations", language, { count: metrics.childTypes || records.length }) : detail);
	}
	if (model.page === "tasks") {
		const values = [
			[
				"TOTAL",
				metrics.tasks,
				""
			],
			[
				"ACTIVE TASKS",
				metrics.activeTasks,
				""
			],
			[
				"COMPLETED",
				metrics.completedTasks,
				"green"
			],
			[
				"OVERDUE",
				metrics.overdueTasks,
				metrics.overdueTasks ? "error" : ""
			],
			[
				"UNASSIGNED",
				metrics.unassignedTasks,
				""
			],
			[
				"AVERAGE PROGRESS",
				(metrics.averageProgress || 0) + "%",
				""
			]
		];
		const wideMetrics = width >= 780, panelWidth = wideMetrics ? (width - 20) / 2 : width;
		const cell = Math.max(0, (panelWidth - 32 - 28) / 3);
		for (let group = 0; group < 2; group++) nodes.push(node("Box", "objectTaskMetrics_" + group, rect(wideMetrics ? group * (panelWidth + 20) : 0, y + (wideMetrics ? 0 : group * 122), panelWidth, 110), {
			background: "panel",
			children: [
				node("Box", "metricDivider_" + group + "_0", rect(16 + cell + 6, 34, 1, 42), { background: "separator" }),
				node("Box", "metricDivider_" + group + "_1", rect(16 + 2 * (cell + 14) - 8, 34, 1, 42), { background: "separator" }),
				...values.slice(group * 3, group * 3 + 3).map(([title, value, color], index) => metric("objectTaskMetric_" + (group * 3 + index), title, value, rect(16 + index * (cell + 14), 30, cell, 50), color, language))
			]
		}));
		y += (wideMetrics ? 110 : 232) + 12;
		const groupY = y, groupWidth = width >= 860 ? (width - 12) / 2 : width;
		chips("objectStatusGroups", "TASKS BY STATUS", "system-activity", model.task_statuses || [], "status", 0, groupWidth);
		const statusBottom = y;
		if (width >= 860) y = groupY;
		chips("objectProcessGroups", "TASKS BY PROCESS", "workflow", model.task_processes || [], "process", width >= 860 ? groupWidth + 12 : 0, groupWidth);
		y = Math.max(y, statusBottom);
		rows("objectParticipants", "PEOPLE AND WORK HOURS", "group", "person", (model.participants || []).map((record) => {
			const value = Object.assign({}, record);
			if (!metrics.canViewCosts) delete value.cost;
			return value;
		}), "No participants found");
		rows("objectTasks", "TASKS", "task", "task", model.tasks || [], "No tasks for this sObject");
	} else if (model.page === "notes") rows("objectNotes", "OBJECT AND TASK NOTES", "notes", "note", model.notes || [], "No object or task notes");
	else if (model.page === "children") {
		chips("objectChildTypes", "CHILD TYPES", "account-tree", model.child_types || []);
		rows("objectChildren", "CHILDREN", "account-tree", "child", model.children || [], "No related children");
	}
	return {
		nodes,
		height: Math.max(0, y - 12)
	};
}
//#endregion
//#region src/features/objects/ObjectReportSurface.vue
var _sfc_main$6 = {
	__name: "ObjectReportSurface",
	props: {
		model: Object,
		part: {
			type: String,
			default: "header"
		}
	},
	emits: ["event"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const host = ref(null), width = ref(0);
		function measure(text, size, weight = 400) {
			return qtLabelTextWidth(text, `${weight} ${size}px Segoe UI`);
		}
		const descriptionView = {
			nodeProps: true,
			props: ["frameNode"],
			setup: (props) => () => h("div", {
				class: "report-description-value",
				style: { color: props.frameNode.empty ? "var(--muted)" : "var(--on-surface)" },
				innerHTML: linkifyPlainText(props.frameNode.text),
				onClick: (event) => activateRichLink(event, (link) => emit("event", {
					type: "link",
					value: link
				}))
			})
		};
		const scene = computed(() => props.part === "header" ? header(props.model, width.value, appearance.language, measure) : page(props.model, width.value, appearance.language));
		let observer;
		onMounted(() => {
			const measure = () => {
				width.value = host.value.clientWidth;
			};
			measure();
			observer = observeFrameSizes(measure);
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				ref_key: "host",
				ref: host,
				class: "object-report-surface",
				style: normalizeStyle({ height: scene.value.height + "px" })
			}, [createVNode(_sfc_main$9, {
				scene: scene.value,
				views: { reportDescription: {
					component: descriptionView,
					nodeProps: true
				} },
				onEvent: _cache[0] || (_cache[0] = ($event) => emit("event", $event))
			}, null, 8, ["scene", "views"])], 4);
		};
	}
};
//#endregion
//#region src/controls/pagination.js
function usePagination(viewport, content, enabled, requestMore) {
	let armed = false, blocked = false, pointer = null, frame = 0, releaseFrame = 0, cleanup;
	function check() {
		const element = viewport.value;
		if (!element?.checkVisibility() || !element.clientHeight || blocked || !enabled()) return;
		const underfilled = element.scrollHeight <= element.clientHeight + 1;
		const atEnd = element.scrollTop + element.clientHeight >= element.scrollHeight - 2;
		if (!underfilled && (!atEnd || !armed)) return;
		armed = false;
		requestMore();
	}
	function schedule() {
		cancelAnimationFrame(frame);
		frame = requestAnimationFrame(check);
	}
	function arm() {
		if (!blocked) armed = true;
	}
	function wheel(event) {
		if (event.deltaY > 0) {
			arm();
			check();
			schedule();
		}
	}
	function key(event) {
		if (event.target !== viewport.value || ![
			"ArrowDown",
			"PageDown",
			"End",
			" "
		].includes(event.key) || event.key === " " && event.shiftKey) return;
		arm();
		check();
		schedule();
	}
	function press(event) {
		const element = viewport.value, box = element.getBoundingClientRect();
		if (!(event.clientX >= box.left && event.clientX <= box.right && event.clientY >= box.top && event.clientY <= box.bottom)) return;
		const gutter = event.clientX >= box.left + element.clientLeft + element.clientWidth || event.clientX < box.left + element.clientLeft;
		armed = false;
		if (gutter) {
			blocked = true;
			pointer = event.pointerId;
			cancelAnimationFrame(releaseFrame);
		} else if (event.pointerType === "touch") arm();
	}
	function release(event) {
		if (event.pointerId !== pointer) return;
		pointer = null;
		releaseFrame = requestAnimationFrame(() => {
			releaseFrame = requestAnimationFrame(() => {
				blocked = false;
				check();
			});
		});
	}
	watch([viewport, content], ([element, body]) => {
		cleanup?.();
		armed = false;
		blocked = false;
		pointer = null;
		if (!element || !body) return;
		const observer = new ResizeObserver(check);
		observer.observe(element);
		observer.observe(body);
		element.addEventListener("scroll", check, { passive: true });
		element.addEventListener("wheel", wheel, { passive: true });
		element.addEventListener("keydown", key);
		document.addEventListener("pointerdown", press, true);
		document.addEventListener("pointerup", release, true);
		document.addEventListener("pointercancel", release, true);
		cleanup = () => {
			observer.disconnect();
			cancelAnimationFrame(frame);
			cancelAnimationFrame(releaseFrame);
			element.removeEventListener("scroll", check);
			element.removeEventListener("wheel", wheel);
			element.removeEventListener("keydown", key);
			document.removeEventListener("pointerdown", press, true);
			document.removeEventListener("pointerup", release, true);
			document.removeEventListener("pointercancel", release, true);
		};
	}, { flush: "post" });
	onBeforeUnmount(() => cleanup?.());
	return {
		check,
		reset: () => {
			armed = false;
		}
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/activity/event.ui.mjs
function icon(model) {
	return model.relationAction ? "link" : {
		publication: "snapshot",
		note: "notes",
		task: "task",
		work_hour: "schedule",
		status: "system-activity",
		create: "add",
		delete: "delete",
		change: "edit"
	}[model.kind] || "activity-feed";
}
function accent(model) {
	return model.processColor || model.typeColor || {
		publication: "green",
		work_hour: "cyan",
		task: "yellow"
	}[model.kind] || "action";
}
function geometry(width, style = "md3") {
	const avatar = width < 380 ? 34 : 40, gap = metrics(style).communicationAvatarSpacing;
	const bubble = Math.max(0, Math.min(760, width - avatar - gap - 8));
	return {
		avatar,
		bubble,
		x: 4 + avatar + gap,
		inner: Math.max(0, bubble - 20)
	};
}
function card(model, width, heights = {}, language, style = "md3") {
	const tr = (text) => translate(text, language), g = geometry(width, style), compact = g.bubble < 520, timeWidth = Math.min(140, g.inner * .35), headerHeight = compact ? 33 : 16, nodes = [], sentenceHeight = Math.max(18, heights.sentence || 18), color = accent(model);
	let y = 14 + headerHeight + 6;
	const content = [
		label("activityActorLabel", rect(10, 10, compact ? g.inner : Math.max(0, g.inner - timeWidth - 8), 16), model.serverGenerated ? tr("Server trigger") : model.actorLabel || model.actor || tr("Unknown user"), {
			fontRole: "secondary",
			weight: 600,
			color: "action"
		}),
		label("activityTimestamp", rect(compact ? 10 : g.bubble - 10 - timeWidth, compact ? 28 : 10, compact ? g.inner : timeWidth, 15), model.time || "", {
			fontRole: "caption",
			color: "secondaryText",
			align: compact ? "left" : "right",
			toolTip: model.fullTime || ""
		}),
		node("Icon", "activityKind", rect(10, y - 4, 20, 20), {
			icon: icon(model),
			color
		}),
		node("View", "activitySentencePort", rect(38, y - 4, Math.max(0, g.inner - 28), sentenceHeight), { view: "sentence" })
	];
	y += Math.max(20, sentenceHeight) + 6;
	const changes = model.changes || [], changeNodes = [], changeTop = y - 4;
	for (let i = 0; i < changes.length; i++) {
		const rowHeight = Math.max(16, heights["change_" + i] || 16) + 10, labelWidth = Math.min(116, Math.max(60, g.inner * .25)), rowY = y - 4 - changeTop;
		changeNodes.push(node("Box", "activityChangeRow_" + i, rect(0, rowY, g.inner, rowHeight), {
			background: "surfaceContainer",
			radius: 9,
			border: "outlineVariant",
			borderWidth: 1
		}));
		changeNodes.push(label("activityChangeLabel_" + i, rect(10, rowY + 5, labelWidth, 15), changes[i].label || changes[i].field || "", {
			fontRole: "caption",
			color: "secondaryText",
			toolTip: changes[i].label || changes[i].field || ""
		}));
		changeNodes.push(node("View", "activityChangePort_" + i, rect(20 + labelWidth, rowY + 5, Math.max(0, g.inner - labelWidth - 30), rowHeight - 10), {
			view: "change",
			index: i
		}));
		y += rowHeight + 4;
	}
	content.push(node("Box", "activityChangeList", rect(10, changeTop, g.inner, Math.max(0, y - 4 - changeTop)), {
		visible: !!changes.length,
		background: "transparent",
		children: changeNodes
	}));
	if (changes.length) y += 2;
	if (model.expandable) {
		const w = 120;
		content.push(button("activityTextExpandButton", rect(Math.max(10, g.bubble - 10 - w), y - 4, w, 32), tr(model.expanded ? "Collapse" : "Expand"), model.expanded ? "chevron-up" : "chevron-down", { type: "expand" }, true, { tonal: true }));
		y += 38;
	}
	const bubbleHeight = y - 4 + 4, height = Math.max(72, bubbleHeight + 8);
	nodes.push(node("Preview", "activityActorPreview", rect(4, 4, g.avatar, g.avatar), {
		source: model.actorAvatar || "",
		initials: model.serverGenerated ? "" : model.actorInitials || "?",
		icon: model.serverGenerated ? "system-activity" : "person",
		round: true,
		outlined: true,
		accent: model.actorColor || "action"
	}));
	nodes.push(node("Box", "activityEventBubble", rect(g.x, 4, g.bubble, bubbleHeight), {
		background: model.hovered ? { mix: [
			"surfaceContainerHigh",
			"primaryText",
			.08
		] } : "surfaceContainerHigh",
		radius: metrics(style).communicationBubbleRadius,
		border: "outlineVariant",
		borderWidth: 1,
		children: content
	}));
	return {
		height,
		nodes
	};
}
//#endregion
//#region src/features/activity/ActivityEventCard.vue
var _hoisted_1$4 = ["data-event-id"];
var _sfc_main$5 = {
	__name: "ActivityEventCard",
	props: {
		record: Object,
		now: Number
	},
	emits: [
		"activity",
		"target",
		"open-link"
	],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const expanded = ref(false);
		const sentence = ref(null), root = ref(null), width = ref(500), heights = ref({}), hovered = ref(false);
		let observer;
		const html = computed(() => eventSentence(props.record, expanded.value));
		watchPostEffect(() => {
			html.value;
			sentence.value?.querySelectorAll("[data-color]").forEach((element) => {
				element.style.color = safeColor(element.dataset.color);
			});
		});
		const changes = computed(() => !props.record.relationAction && [
			"create",
			"change",
			"delete"
		].includes(props.record.kind) ? props.record.changes || [] : []);
		const expandable = computed(() => [
			props.record.detail,
			props.record.title,
			...changes.value.map((change) => changeValue(props.record, change))
		].some(needsExpansion));
		const time = computed(() => {
			appearance.language;
			return timestampLabel(props.record.timestamp, props.now ? new Date(props.now) : void 0);
		});
		function activate(event) {
			if (activateRichLink(event, (value) => emit("open-link", value))) return;
			const action = event.target.closest("[data-action]")?.dataset.action;
			if (action) {
				event.preventDefault();
				emit(action);
			}
		}
		const fieldLabel = (value) => t({
			name: "Name",
			title: "Title",
			description: "Description",
			assigned: "Assignee",
			status: "Status",
			priority: "Priority",
			"bid start date": "Start date",
			"bid end date": "Deadline"
		}[String(value).toLowerCase()] || value);
		const model = computed(() => ({
			...props.record,
			time: time.value,
			fullTime: timestampFullLabel(props.record.timestamp),
			expanded: expanded.value,
			expandable: expandable.value,
			hovered: hovered.value,
			changes: changes.value.map((row) => ({
				...row,
				label: fieldLabel(row.field)
			}))
		}));
		const scene = computed(() => card(model.value, width.value, heights.value, appearance.language, appearance.theme));
		const port = {
			props: { frameNode: Object },
			setup(port, { attrs }) {
				const element = ref(null);
				let resize;
				onMounted(() => {
					resize = observeFrameSizes(() => {
						const key = port.frameNode.view === "sentence" ? "sentence" : "change_" + port.frameNode.index, height = element.value.getBoundingClientRect().height;
						if (height > 0 && heights.value[key] !== height) heights.value = {
							...heights.value,
							[key]: height
						};
					});
					resize.observe(element.value);
				});
				onBeforeUnmount(() => resize?.disconnect());
				return () => {
					const body = port.frameNode.view === "sentence", change = changes.value[port.frameNode.index], value = body ? html.value : expanded.value ? linkifyPlainText(changeValue(props.record, change), browserLink) : escapeHtml(compactText(changeValue(props.record, change)));
					return h("div", attrs, [h("div", {
						ref: (node) => {
							element.value = node;
							if (body) sentence.value = node;
						},
						class: body ? "activity-sentence-port" : "activity-change-port",
						style: {
							overflowWrap: "anywhere",
							fontSize: body ? "13px" : "12px",
							lineHeight: body ? "18px" : "16px",
							userSelect: "text"
						},
						innerHTML: value,
						onClick: activate
					})]);
				};
			}
		};
		const views = {
			sentence: {
				component: port,
				nodeProps: true
			},
			change: {
				component: port,
				nodeProps: true
			}
		};
		onMounted(() => {
			observer = observeFrameSizes((entries) => {
				if (entries[0].contentRect.width > 0) width.value = entries[0].contentRect.width;
			});
			observer.observe(root.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("article", {
				ref_key: "root",
				ref: root,
				class: "activity-event-card",
				"data-event-id": __props.record.eventId,
				style: normalizeStyle({ height: scene.value.height + "px" }),
				onMouseenter: _cache[1] || (_cache[1] = ($event) => hovered.value = true),
				onMouseleave: _cache[2] || (_cache[2] = ($event) => hovered.value = false)
			}, [createVNode(_sfc_main$9, {
				scene: scene.value,
				views,
				onEvent: _cache[0] || (_cache[0] = (event) => {
					if (event.type === "expand") expanded.value = !expanded.value;
				})
			}, null, 8, ["scene"])], 44, _hoisted_1$4);
		};
	}
};
//#endregion
//#region src/controls/AttachmentCard.vue
var _hoisted_1$3 = { class: "attachment-info" };
var _sfc_main$4 = {
	__name: "AttachmentCard",
	props: {
		title: String,
		extension: String,
		previewUrl: String,
		sizeText: String,
		compact: Boolean,
		disabled: Boolean,
		local: Boolean,
		webPreview: {
			type: Boolean,
			default: true
		},
		activationIcon: String,
		activationLabel: String
	},
	emits: ["activated"],
	setup(__props) {
		const props = __props;
		const card = ref(null), width = ref(240), pixels = ref(null);
		const extensionLabel = computed(() => (props.extension || "FILE").slice(0, 5).toUpperCase());
		const imageAttachment = computed(() => [
			"JPG",
			"JPEG",
			"PNG",
			"WEBP",
			"GIF",
			"BMP",
			"TIF",
			"TIFF",
			"TGA",
			"EXR",
			"HDR",
			"SVG",
			"HEIC",
			"AVIF"
		].includes((props.extension || "").toUpperCase()));
		const imageWidth = computed(() => Math.round(props.webPreview ? Math.min(Math.max(0, width.value - 16), pixels.value?.width || Infinity) : Math.max(0, width.value - 16)));
		const imageHeight = computed(() => Math.round(Math.min(360, imageWidth.value * (pixels.value ? pixels.value.height / pixels.value.width : .56))));
		let observer, resizeFrame;
		watch(() => props.previewUrl, () => {
			pixels.value = null;
		});
		function loaded(event) {
			if (!props.compact && event.target.tagName === "IMG") pixels.value = {
				width: event.target.naturalWidth,
				height: event.target.naturalHeight
			};
		}
		onMounted(() => {
			observer = new ResizeObserver((entries) => {
				const next = Math.round(entries[0].contentRect.width);
				if (next > 0 && Math.abs(next - width.value) > 1) {
					cancelAnimationFrame(resizeFrame);
					resizeFrame = requestAnimationFrame(() => {
						width.value = next;
					});
				}
			});
			observer.observe(card.value.$el);
		});
		onBeforeUnmount(() => {
			observer?.disconnect();
			cancelAnimationFrame(resizeFrame);
		});
		return (_ctx, _cache) => {
			return openBlock(), createBlock(_sfc_main$7, {
				ref_key: "card",
				ref: card,
				class: normalizeClass(["attachment-card", {
					compact: __props.compact,
					"image-attachment": imageAttachment.value && !__props.compact
				}]),
				label: __props.activationLabel,
				disabled: __props.disabled,
				onLoadCapture: loaded,
				onClick: _cache[0] || (_cache[0] = ($event) => _ctx.$emit("activated"))
			}, {
				default: withCtx(() => [imageAttachment.value && !__props.compact ? (openBlock(), createBlock(ItemPreview_default, {
					key: 0,
					class: "attachment-image",
					style: normalizeStyle({
						width: imageWidth.value + "px",
						height: imageHeight.value + "px"
					}),
					source: __props.previewUrl,
					"fallback-icon": "image",
					outlined: ""
				}, null, 8, ["style", "source"])) : createCommentVNode("", true), createBaseVNode("span", _hoisted_1$3, [
					__props.compact || !imageAttachment.value ? (openBlock(), createBlock(ItemPreview_default, {
						key: 0,
						class: "attachment-badge",
						style: normalizeStyle({
							background: imageAttachment.value && __props.previewUrl ? "var(--surface-highest)" : "var(--primary)",
							color: "var(--on-selected)",
							"--preview-text-size": (extensionLabel.value.length > 4 ? 8 : 9) + "px"
						}),
						source: imageAttachment.value ? __props.previewUrl : "",
						"fallback-text": extensionLabel.value,
						round: !imageAttachment.value
					}, null, 8, [
						"style",
						"source",
						"fallback-text",
						"round"
					])) : createCommentVNode("", true),
					createBaseVNode("span", null, [createBaseVNode("strong", null, toDisplayString(__props.title), 1), createBaseVNode("small", null, toDisplayString(imageAttachment.value && !__props.compact ? [extensionLabel.value, __props.sizeText].filter(Boolean).join(" · ") : __props.sizeText), 1)]),
					createVNode(_sfc_main$8, { name: __props.activationIcon || (__props.local ? "MDI_OPEN_IN_NEW" : "download") }, null, 8, ["name"])
				])]),
				_: 1
			}, 8, [
				"class",
				"label",
				"disabled"
			]);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/features/objects/snapshot_tree.ui.mjs
function describe(model, width, language) {
	const tr = (text) => translate(text, language), groups = model.groups || [], metrics = model.metrics || {}, nodes = [];
	nodes.push(node("Box", "objectSnapshotTreeHeader", rect(0, 0, width, 64), {
		background: "panel",
		border: "separator",
		children: [
			node("Icon", "objectSnapshotTreeIcon", rect(14, 23, 18, 18), {
				icon: "account-tree",
				color: "action"
			}),
			label("objectSnapshotTreeTitle", rect(42, 10, Math.max(0, width - 56), 22), tr("SNAPSHOTS BY PROCESS"), {
				fontRole: "bodyLarge",
				weight: 600
			}),
			label("objectSnapshotTreeCounts", rect(42, 34, Math.max(0, width - 56), 18), translate("{processes} processes · {snapshots} snapshots · {files} files", language, {
				processes: groups.length,
				snapshots: metrics.snapshots || 0,
				files: metrics.files || 0
			}), {
				color: "secondaryText",
				fontRole: "caption"
			})
		]
	}));
	let y = 74;
	groups.forEach((group, index) => {
		const inner = Math.max(0, width - 16), expanded = !!(model.expanded || {})[group.value], children = [];
		children.push(node("Action", "objectSnapshotProcess_" + index, rect(8, 8, inner, 62), {
			text: group.label,
			normalColor: "transparent",
			radius: 12,
			action: {
				type: "expand",
				value: group.value
			},
			children: [
				node("Icon", "processExpand", rect(12, 22, 18, 18), {
					icon: expanded ? "expand-more" : "chevron-right",
					color: "secondaryText"
				}),
				node("Icon", "processIcon", rect(40, 22, 18, 18), {
					icon: "workflow",
					color: group.accent || "action"
				}),
				label("processLabel", rect(70, 8, Math.max(0, inner - 128), 23), group.label, {
					fontRole: "bodyLarge",
					weight: 600
				}),
				label("processCounts", rect(70, 34, Math.max(0, inner - 128), 18), translate("{snapshots} snapshots · {files} files · {size}", language, {
					snapshots: group.snapshotCount,
					files: group.fileCount,
					size: group.sizeText || "0 B"
				}), {
					fontRole: "caption",
					color: "secondaryText"
				}),
				node("StatusChip", "processBadge", rect(Math.max(0, inner - 48), 18, 40, 26), {
					text: String(group.snapshotCount),
					icon: "snapshot",
					accent: group.accent || "action"
				})
			]
		}));
		let top = 78;
		if (expanded) {
			children.push(label("snapshotsHeading", rect(18, top, Math.max(0, width - 36), 24), tr("SNAPSHOTS AND VERSIONS"), {
				fontRole: "secondary",
				weight: 600
			}));
			top += 32;
			(group.snapshots || []).forEach((snapshot, row) => {
				children.push(node("Action", "objectReportSnapshot_" + index + "_" + row, rect(8, top, inner, 72), {
					text: snapshot.title,
					normalColor: "transparent",
					radius: 12,
					action: {
						type: "snapshot",
						index: snapshot.modelIndex,
						key: snapshot.searchKey
					},
					children: [
						node("Preview", "snapshotPreview", rect(8, 9, 54, 54), {
							source: snapshot.previewUrl || "",
							initials: snapshot.version,
							icon: "snapshot",
							outlined: true
						}),
						label("snapshotTitle", rect(72, 7, Math.max(0, inner - 152), 22), snapshot.title, {
							fontRole: "bodyLarge",
							weight: 600
						}),
						label("snapshotContext", rect(72, 31, Math.max(0, inner - 152), 17), [
							snapshot.context,
							snapshot.author,
							snapshot.repository
						].filter(Boolean).join(" · "), {
							fontRole: "caption",
							color: "secondaryText"
						}),
						label("snapshotFiles", rect(72, 50, Math.max(0, inner - 152), 17), translate("{files} files · {size} · {timestamp}", language, {
							files: snapshot.fileCount,
							size: snapshot.sizeText,
							timestamp: snapshot.timestampPretty
						}), {
							fontRole: "caption",
							color: "secondaryText",
							tooltip: snapshot.timestampFull || ""
						}),
						node("StatusChip", "snapshotVersion", rect(Math.max(0, inner - 72), 23, 64, 26), {
							text: snapshot.isVersionless ? tr("Current") : snapshot.version,
							icon: snapshot.isVersionless ? "sync" : "history",
							accent: snapshot.isLatest ? "green" : "action"
						})
					]
				}));
				top += 80;
			});
			if ((group.files || []).length) {
				children.push(label("filesHeading", rect(18, top, Math.max(0, width - 36), 24), tr("FILES"), {
					fontRole: "secondary",
					weight: 600
				}));
				top += 32;
			}
			(group.files || []).forEach((file, row) => {
				const height = (model.fileHeights || {})[file.token] || 64;
				children.push(node("View", "objectReportFile_" + index + "_" + row, rect(8, top, inner, height), {
					view: "attachment",
					record: file
				}));
				top += height + 8;
			});
		}
		const height = expanded ? top + 8 : 78;
		nodes.push(node("Box", "objectSnapshotProcessSurface_" + index, rect(0, y, width, height), {
			background: "panel",
			border: "separator",
			children
		}));
		y += height + 10;
	});
	if (!groups.length) {
		nodes.push(label("objectSnapshotTreeEmpty", rect(0, y, width, 72), tr("No snapshots found"), {
			color: "secondaryText",
			align: "center"
		}));
		y += 72;
	}
	return {
		nodes,
		height: y
	};
}
//#endregion
//#region src/features/objects/ObjectSnapshotTree.vue
var _sfc_main$3 = {
	__name: "ObjectSnapshotTree",
	props: {
		metrics: Object,
		groups: Array
	},
	emits: ["snapshot", "file"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const host = ref(null), width = ref(0), expanded = ref({}), fileHeights = ref({});
		const scene = computed(() => describe({
			metrics: props.metrics,
			groups: props.groups,
			expanded: expanded.value,
			fileHeights: fileHeights.value
		}, width.value, appearance.language));
		let observer;
		const views = { attachment: {
			nodeProps: true,
			component: {
				props: { frameNode: Object },
				setup(props, { attrs }) {
					const element = ref(null);
					let resize;
					onMounted(() => {
						resize = observeFrameSizes(() => {
							const height = element.value.scrollHeight, token = props.frameNode.record.token;
							if (height > 0 && fileHeights.value[token] !== height) fileHeights.value = {
								...fileHeights.value,
								[token]: height
							};
						});
						resize.observe(element.value);
					});
					onBeforeUnmount(() => resize?.disconnect());
					return () => {
						const record = props.frameNode.record;
						return h("div", { ...attrs }, [h("div", { ref: element }, [h(_sfc_main$4, {
							title: record.title,
							extension: record.extension,
							previewUrl: record.previewUrl,
							sizeText: record.sizeText,
							local: !!record.exists,
							webPreview: false,
							activationLabel: "Open attachment",
							onActivated: () => emit("file", record)
						})])]);
					};
				}
			}
		} };
		onMounted(() => {
			const measure = () => {
				width.value = host.value.clientWidth;
			};
			measure();
			observer = observeFrameSizes(measure);
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		function action(event) {
			if (event.type === "expand") expanded.value = {
				...expanded.value,
				[event.value]: !expanded.value[event.value]
			};
			else if (event.type === "snapshot") emit("snapshot", event.key);
		}
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				ref_key: "host",
				ref: host,
				class: "object-snapshot-tree",
				style: normalizeStyle({ height: scene.value.height + "px" })
			}, [createVNode(_sfc_main$9, {
				scene: scene.value,
				views,
				onEvent: action
			}, null, 8, ["scene"])], 4);
		};
	}
};
//#endregion
//#region src/features/objects/FilePreviewContent.vue
var _sfc_main$2 = {
	components: {
		AppButton: _sfc_main$7,
		AppMenu: _sfc_main$10,
		AppIcon: _sfc_main$8,
		ItemPreview: ItemPreview_default
	},
	props: {
		record: Object,
		cell: Object,
		embedded: Boolean,
		actionsTarget: Object,
		description: String
	},
	emits: [
		"session-expired",
		"selected",
		"busy"
	],
	data() {
		return {
			loading: false,
			error: "",
			mediaUrl: "",
			mediaType: "",
			text: "",
			selectedFile: null,
			request: 0
		};
	},
	computed: { mobile() {
		return mobile.value;
	} },
	watch: {
		loading(value) {
			this.$emit("busy", value);
		},
		cell: {
			immediate: true,
			handler(cell) {
				this.reset();
				if (cell?.loadFile && cell.files?.length) this.selectFile(cell.files.find((file) => file.code === cell.fileCode) || cell.files.find((file) => !["web", "icon"].includes(file.type)) || cell.files[0]);
			}
		}
	},
	methods: {
		t,
		fileDetails(file) {
			return [
				file.filename?.includes(".") ? file.filename.split(".").at(-1).toUpperCase() : "",
				file.size != null ? prettySize(Number(file.size)) : "",
				file.type
			].filter(Boolean).join(" · ");
		},
		reset() {
			this.request++;
			if (this.mediaUrl) URL.revokeObjectURL(this.mediaUrl);
			this.mediaUrl = this.mediaType = this.text = this.error = "";
			this.loading = false;
			this.selectedFile = null;
		},
		async selectFile(file) {
			this.reset();
			this.selectedFile = file;
			this.$emit("selected", file);
			this.loading = true;
			const id = this.request;
			try {
				const blob = await this.cell.loadFile(file);
				if (id !== this.request) return;
				this.mediaUrl = URL.createObjectURL(blob);
				this.mediaType = blob.type;
				if (blob.type.startsWith("text/")) {
					const text = await blob.slice(0, 1e5).text();
					if (id === this.request) this.text = text;
				}
			} catch (error) {
				if (id === this.request) {
					this.error = error.message;
					if (error.code === "authentication_failed") this.$emit("session-expired");
				}
			} finally {
				if (id === this.request) this.loading = false;
			}
		},
		async download(file) {
			const id = this.request;
			try {
				const blob = await this.cell.loadFile(file);
				if (id !== this.request) return;
				downloadBlob(blob, file.filename);
			} catch (error) {
				if (id === this.request) {
					this.error = error.message;
					if (error.code === "authentication_failed") this.$emit("session-expired");
				}
			}
		}
	},
	beforeUnmount() {
		this.reset();
	}
};
var _hoisted_1$2 = { class: "file-preview-file-copy" };
var _hoisted_2$2 = { class: "muted" };
var _hoisted_3$1 = { class: "file-preview-file-copy" };
var _hoisted_4$1 = { class: "muted" };
var _hoisted_5$1 = {
	key: 1,
	class: "error",
	role: "alert"
};
var _hoisted_6 = {
	key: 2,
	role: "status"
};
var _hoisted_7 = { class: "file-preview-content" };
var _hoisted_8 = ["src"];
var _hoisted_9 = ["src"];
var _hoisted_10 = ["src", "title"];
var _hoisted_11 = {
	key: 4,
	class: "file-preview-text"
};
var _hoisted_12 = {
	key: 5,
	class: "muted"
};
var _hoisted_13 = {
	key: 6,
	class: "muted"
};
var _hoisted_14 = {
	key: 7,
	class: "file-preview-description"
};
var _hoisted_15 = { class: "file-preview-actions" };
var _hoisted_16 = {
	key: 0,
	class: "configuration-actions file-preview-download"
};
var _hoisted_17 = { key: 0 };
var _hoisted_18 = {
	key: 1,
	class: "file-preview-metadata"
};
var _hoisted_19 = { class: "file-preview-metadata" };
var _hoisted_20 = {
	key: 2,
	class: "file-preview-files"
};
var _hoisted_21 = { class: "muted" };
var _hoisted_22 = { class: "muted" };
var _hoisted_23 = {
	key: 0,
	class: "configuration-actions"
};
var _hoisted_24 = {
	key: 1,
	class: "configuration-actions"
};
var _hoisted_25 = {
	key: 3,
	class: "muted"
};
function _sfc_render$1(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_ItemPreview = resolveComponent("ItemPreview");
	const _component_AppIcon = resolveComponent("AppIcon");
	const _component_AppButton = resolveComponent("AppButton");
	const _component_AppMenu = resolveComponent("AppMenu");
	return $props.cell ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [
		$options.mobile && $props.cell.loadFile && $props.cell.files?.length > 1 ? (openBlock(), createBlock(_component_AppMenu, {
			key: 0,
			class: "file-preview-picker",
			label: "Preview file",
			overlay: "",
			"show-label": "",
			"align-start": "",
			width: 360
		}, {
			trigger: withCtx(() => [
				createVNode(_component_ItemPreview, {
					"fallback-icon": "file",
					"preview-size": 32
				}),
				createBaseVNode("span", _hoisted_1$2, [createBaseVNode("strong", null, toDisplayString($data.selectedFile?.filename), 1), createBaseVNode("small", _hoisted_2$2, toDisplayString($data.selectedFile && $options.fileDetails($data.selectedFile)), 1)]),
				createVNode(_component_AppIcon, { name: "MDI_CHEVRON_DOWN" })
			]),
			default: withCtx(() => [(openBlock(true), createElementBlock(Fragment, null, renderList($props.cell.files, (file, index) => {
				return openBlock(), createBlock(_component_AppButton, {
					key: file.code || index,
					class: "file-preview-choice",
					role: "menuitemradio",
					"aria-checked": file === $data.selectedFile,
					label: file.filename,
					"translate-label": false,
					onClick: ($event) => $options.selectFile(file)
				}, {
					default: withCtx(() => [
						createVNode(_component_ItemPreview, {
							"fallback-icon": "file",
							"preview-size": 32
						}),
						createBaseVNode("span", _hoisted_3$1, [createBaseVNode("strong", null, toDisplayString(file.filename), 1), createBaseVNode("small", _hoisted_4$1, toDisplayString($options.fileDetails(file)), 1)]),
						file === $data.selectedFile ? (openBlock(), createBlock(_component_AppIcon, {
							key: 0,
							name: "check"
						})) : createCommentVNode("", true)
					]),
					_: 2
				}, 1032, [
					"aria-checked",
					"label",
					"onClick"
				]);
			}), 128))]),
			_: 1
		})) : createCommentVNode("", true),
		$data.error ? (openBlock(), createElementBlock("p", _hoisted_5$1, [createTextVNode(toDisplayString($options.t($data.error)) + " ", 1), $data.selectedFile ? (openBlock(), createBlock(_component_AppButton, {
			key: 0,
			label: "Retry",
			onClick: _cache[0] || (_cache[0] = ($event) => $options.selectFile($data.selectedFile))
		})) : createCommentVNode("", true)])) : createCommentVNode("", true),
		$data.loading ? (openBlock(), createElementBlock("p", _hoisted_6, toDisplayString($options.t("Loading file…")), 1)) : createCommentVNode("", true),
		createBaseVNode("div", _hoisted_7, [
			!$props.cell.loadFile || $data.mediaType.startsWith("image/") && $data.mediaType !== "image/svg+xml" ? (openBlock(), createBlock(_component_ItemPreview, {
				key: 0,
				source: $data.mediaUrl || $props.cell.image,
				"fallback-icon": "image"
			}, null, 8, ["source"])) : $data.mediaType.startsWith("video/") ? (openBlock(), createElementBlock("video", {
				key: 1,
				src: $data.mediaUrl,
				controls: "",
				preload: "metadata"
			}, null, 8, _hoisted_8)) : $data.mediaType.startsWith("audio/") ? (openBlock(), createElementBlock("audio", {
				key: 2,
				src: $data.mediaUrl,
				controls: "",
				preload: "metadata"
			}, null, 8, _hoisted_9)) : $data.mediaType === "application/pdf" ? (openBlock(), createElementBlock("iframe", {
				key: 3,
				src: $data.mediaUrl,
				title: $data.selectedFile?.filename
			}, null, 8, _hoisted_10)) : $data.mediaType.startsWith("text/") ? (openBlock(), createElementBlock("pre", _hoisted_11, toDisplayString($data.text), 1)) : !$data.loading ? (openBlock(), createElementBlock("p", _hoisted_12, toDisplayString($options.t("No preview available")), 1)) : createCommentVNode("", true),
			!$props.cell.loadFile && !$props.cell.image ? (openBlock(), createElementBlock("p", _hoisted_13, toDisplayString($options.t("No preview available")), 1)) : createCommentVNode("", true),
			$props.description || $props.record?.description ? (openBlock(), createElementBlock("p", _hoisted_14, toDisplayString($props.description || $props.record.description), 1)) : createCommentVNode("", true)
		]),
		(openBlock(), createBlock(Teleport, {
			to: $props.actionsTarget || "body",
			disabled: !$options.mobile || !$props.actionsTarget
		}, [createBaseVNode("nav", _hoisted_15, [($props.embedded || $options.mobile) && $data.selectedFile ? (openBlock(), createElementBlock("div", _hoisted_16, [$data.selectedFile.href ? (openBlock(), createBlock(_component_AppButton, {
			key: 0,
			href: $data.selectedFile.href,
			label: "Download",
			icon: "download",
			download: $data.selectedFile.filename
		}, null, 8, ["href", "download"])) : (openBlock(), createBlock(_component_AppButton, {
			key: 1,
			label: "Download",
			icon: "download",
			onClick: _cache[1] || (_cache[1] = ($event) => $options.download($data.selectedFile))
		}))])) : createCommentVNode("", true), (openBlock(), createBlock(resolveDynamicComponent($options.mobile ? "AppMenu" : "div"), {
			class: "file-preview-details",
			label: "File details",
			overlay: $options.mobile
		}, {
			default: withCtx(() => [
				$options.mobile ? (openBlock(), createElementBlock("small", _hoisted_17, toDisplayString($props.record?.__search_key__), 1)) : createCommentVNode("", true),
				$props.cell.object ? (openBlock(), createElementBlock("dl", _hoisted_18, [
					createBaseVNode("dt", null, toDisplayString($options.t("Search Type")), 1),
					createBaseVNode("dd", null, toDisplayString($props.cell.object.search_type), 1),
					(openBlock(), createElementBlock(Fragment, null, renderList([
						"code",
						"status",
						"description"
					], (name) => {
						return openBlock(), createElementBlock(Fragment, { key: name }, [createBaseVNode("dt", null, toDisplayString($options.t({
							code: "Code",
							status: "Status",
							description: "Description"
						}[name])), 1), createBaseVNode("dd", null, toDisplayString($props.record?.[name] || "—"), 1)], 64);
					}), 64))
				])) : createCommentVNode("", true),
				createBaseVNode("dl", _hoisted_19, [
					createBaseVNode("dt", null, toDisplayString($options.t("Context")), 1),
					createBaseVNode("dd", null, toDisplayString($props.cell.context || "—"), 1),
					createBaseVNode("dt", null, toDisplayString($options.t("Version")), 1),
					createBaseVNode("dd", null, toDisplayString($props.cell.version ?? "—"), 1)
				]),
				$props.cell.files?.length ? (openBlock(), createElementBlock("ul", _hoisted_20, [(openBlock(true), createElementBlock(Fragment, null, renderList($props.cell.files, (file, index) => {
					return openBlock(), createElementBlock("li", { key: index }, [createBaseVNode("div", null, [
						createBaseVNode("strong", null, toDisplayString(file.filename), 1),
						createBaseVNode("small", _hoisted_21, toDisplayString(file.type) + " · " + toDisplayString(file.size ?? "—") + " " + toDisplayString($options.t("bytes")), 1),
						createBaseVNode("small", _hoisted_22, toDisplayString(file.path), 1)
					]), file.href ? (openBlock(), createElementBlock("div", _hoisted_23, [createVNode(_component_AppButton, {
						href: file.href,
						label: "Open file",
						icon: "link",
						target: "_blank",
						rel: "noopener noreferrer"
					}, null, 8, ["href"]), createVNode(_component_AppButton, {
						href: file.href,
						label: "Download",
						icon: "download",
						download: file.filename
					}, null, 8, ["href", "download"])])) : $props.cell.loadFile ? (openBlock(), createElementBlock("div", _hoisted_24, [createVNode(_component_AppButton, {
						label: "Open file",
						icon: "link",
						disabled: $data.loading,
						onClick: ($event) => $options.selectFile(file)
					}, null, 8, ["disabled", "onClick"]), createVNode(_component_AppButton, {
						label: "Download",
						icon: "download",
						onClick: ($event) => $options.download(file)
					}, null, 8, ["onClick"])])) : createCommentVNode("", true)]);
				}), 128))])) : (openBlock(), createElementBlock("p", _hoisted_25, toDisplayString($options.t("No files")), 1))
			]),
			_: 1
		}, 8, ["overlay"]))])], 8, ["to", "disabled"]))
	], 64)) : createCommentVNode("", true);
}
var FilePreviewContent_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main$2, [["render", _sfc_render$1]]);
//#endregion
//#region src/features/objects/FilePreview.vue
var _sfc_main$1 = {
	components: {
		AppButton: _sfc_main$7,
		FilePreviewContent: FilePreviewContent_default
	},
	props: {
		ticket: String,
		project: String,
		searchType: String
	},
	emits: [
		"session-expired",
		"opened",
		"closed"
	],
	data() {
		return {
			record: null,
			cell: null,
			selectedFile: null,
			loading: false
		};
	},
	computed: { mobile() {
		return mobile.value;
	} },
	watch: {
		ticket() {
			this.close();
		},
		project() {
			this.close();
		},
		searchType() {
			this.close();
		}
	},
	methods: {
		t,
		windowContext() {
			const { loadFile, ...cell } = this.cell || {};
			return {
				project: this.project,
				route: {
					key: this.record.__search_key__,
					fileCode: this.selectedFile?.code || ""
				},
				state: {
					record: this.record,
					cell,
					download: !!loadFile
				}
			};
		},
		open(record, cell) {
			this.record = record;
			this.cell = cell;
			this.$refs.dialog.show();
			this.$emit("opened");
		},
		close() {
			this.$refs.dialog?.close();
			this.record = this.cell = null;
		}
	}
};
var _hoisted_1$1 = ["aria-label", "aria-busy"];
var _hoisted_2$1 = { key: 0 };
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_AppButton = resolveComponent("AppButton");
	const _component_FilePreviewContent = resolveComponent("FilePreviewContent");
	const _directive_window = resolveDirective("window");
	return openBlock(), createBlock(Teleport, { to: "body" }, [withDirectives((openBlock(), createElementBlock("dialog", {
		ref: "dialog",
		class: "record-dialog file-preview",
		"aria-label": $options.t("File preview"),
		"aria-busy": $data.loading,
		onCancel: _cache[3] || (_cache[3] = withModifiers((...args) => $options.close && $options.close(...args), ["prevent"])),
		onClose: _cache[4] || (_cache[4] = ($event) => {
			$data.record = $data.cell = null;
			$data.selectedFile = null;
			$data.loading = false;
			_ctx.$emit("closed");
		})
	}, [$data.cell ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [createBaseVNode("header", null, [createBaseVNode("div", null, [createBaseVNode("h2", null, toDisplayString($options.mobile && $data.selectedFile?.filename || $data.record?.name || $data.record?.title || $data.record?.code || $data.record?.id), 1), !$options.mobile ? (openBlock(), createElementBlock("small", _hoisted_2$1, toDisplayString($data.record?.__search_key__), 1)) : createCommentVNode("", true)]), createVNode(_component_AppButton, {
		label: "Close preview",
		icon: "close",
		"icon-only": "",
		autofocus: "",
		onClick: $options.close
	}, null, 8, ["onClick"])]), createVNode(_component_FilePreviewContent, {
		ref: "content",
		record: $data.record,
		cell: $data.cell,
		onSelected: _cache[0] || (_cache[0] = ($event) => $data.selectedFile = $event),
		onBusy: _cache[1] || (_cache[1] = ($event) => $data.loading = $event),
		onSessionExpired: _cache[2] || (_cache[2] = ($event) => _ctx.$emit("session-expired"))
	}, null, 8, ["record", "cell"])], 64)) : createCommentVNode("", true)], 40, _hoisted_1$1)), [[_directive_window, {
		kind: "file_preview",
		type: "window",
		page: $options.windowContext
	}]])]);
}
var FilePreview_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main$1, [["render", _sfc_render]]);
//#endregion
//#region src/features/objects/ObjectReport.vue
var _hoisted_1 = ["aria-busy"];
var _hoisted_2 = {
	key: 1,
	class: "error",
	role: "alert"
};
var _hoisted_3 = {
	key: 2,
	role: "status"
};
var _hoisted_4 = {
	key: 5,
	class: "object-report-activity"
};
var _hoisted_5 = {
	key: 0,
	class: "muted"
};
var _sfc_main = {
	__name: "ObjectReport",
	props: {
		ticket: String,
		project: String,
		record: Object
	},
	emits: ["open-link", "leave"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const openObjectTab = inject("openObjectTab", null), openTaskInspector = inject("openTaskInspector", null), openTaskManager = inject("openTaskManager", null), openUserProfile = inject("openUserProfile", null);
		const openSnapshotBrowser = inject("openSnapshotBrowser", null);
		const scroll = ref(null), content = ref(null), tabs = ref(null), preview = ref(null), width = ref(0), data = ref(null), dataPage = ref(""), busy = ref(false), error = ref(""), page = ref("tasks"), activity = ref([]);
		let generation = 0, observer;
		const pages = /* @__PURE__ */ new Map();
		const cache = /* @__PURE__ */ new Map();
		const identity = computed(() => JSON.stringify([props.project, props.record?.__search_key__]));
		const snapshotGroups = computed(() => (data.value?.snapshot_processes || []).map((group) => ({
			...group,
			snapshots: group.snapshots.map((row) => ({
				...row,
				timestampPretty: timestampLabel(row.timestamp),
				timestampFull: timestampFullLabel(row.timestamp)
			}))
		})));
		const model = computed(() => {
			const value = data.value || {
				summary: {},
				metrics: {}
			};
			const now = new Date(serverClock.now());
			return {
				...value,
				page: page.value,
				busy: busy.value,
				summary: {
					...value.summary,
					updatedPretty: timestampLabel(value.summary.updatedFull, now)
				},
				tasks: (value.tasks || []).map((row) => ({
					...row,
					endPretty: timestampLabel(row.end, now),
					endFull: timestampFullLabel(row.end)
				})),
				notes: (value.notes || []).map((row) => ({
					...row,
					timestampPretty: timestampLabel(row.timestamp, now),
					timestampFull: timestampFullLabel(row.timestamp)
				}))
			};
		});
		const tabScene = computed(() => tabs$1(page.value, width.value, appearance.language));
		const pageReady = computed(() => dataPage.value === page.value);
		const pagination = usePagination(scroll, content, () => page.value === "activity" && pageReady.value && data.value?.hasMore && !busy.value && !error.value, () => load(true));
		watch([
			pageReady,
			busy,
			activity
		], pagination.check, { flush: "post" });
		async function load(append = false, refresh = false) {
			const key = props.record?.__search_key__;
			if (!key || !props.ticket || !props.project) return;
			const request = ++generation;
			const cacheKey = JSON.stringify([identity.value, page.value]);
			if (!append && !refresh && cache.has(cacheKey)) {
				data.value = cache.get(cacheKey);
				dataPage.value = page.value;
				activity.value = data.value.activity;
				error.value = "";
				busy.value = false;
				return;
			}
			busy.value = true;
			error.value = "";
			try {
				const result = await resultItems(props.ticket, props.project, key.split("?")[0], [key], {
					branch: {
						kind: "object_report",
						path: page.value
					},
					offset: append ? activity.value.length : 0,
					limit: 50
				});
				if (request !== generation) return;
				data.value = result;
				dataPage.value = page.value;
				activity.value = append ? [...activity.value, ...result.activity] : result.activity;
				cache.set(cacheKey, {
					...result,
					activity: activity.value
				});
				if (cache.size > 1e3) cache.delete(cache.keys().next().value);
			} catch (reason) {
				if (request === generation) error.value = reason.message;
			} finally {
				if (request === generation) busy.value = false;
			}
		}
		function selectPage(value) {
			if (!sections.some((row) => row.value === value) || value === page.value) return;
			page.value = value;
			pages.set(identity.value, value);
			activity.value = [];
			scroll.value.scrollTop = 0;
			load();
			pagination.reset();
		}
		function open(key) {
			if (key) {
				emit("leave");
				openObjectTab?.(key.startsWith("skey://") ? key : "skey://" + key, props.project);
			}
		}
		function snapshot(key) {
			const row = data.value.snapshots.find((row) => row.searchKey === key);
			if (row) {
				emit("leave");
				openSnapshotBrowser?.(props.record, row.process, props.project);
			}
		}
		function file(record) {
			const file = {
				...record,
				code: record.token,
				filename: record.title
			};
			preview.value.open({
				name: record.title,
				__search_key__: record.searchKey
			}, {
				files: [file],
				loadFile: fileBlob
			});
		}
		async function inspector(process, taskKey = "", noteKey = "") {
			emit("leave");
			return openTaskInspector?.(props.record, {}, process, taskKey, {
				ticket: props.ticket,
				project: props.project,
				searchType: props.record.__search_key__.split("?")[0],
				noteKey
			});
		}
		async function activityAction(record) {
			emit("leave");
			if (record.taskCode && ([
				"status",
				"task",
				"work_hour"
			].includes(record.kind) || record.itemType === "sthpw/task")) {
				const key = "sthpw/task?project=" + encodeURIComponent(props.project) + "&code=" + encodeURIComponent(record.taskCode);
				if (await inspector(record.process, key) !== false) openTaskManager?.(props.record, "", {}, key);
			} else if (record.kind === "note") inspector(record.process, record.taskCode ? "sthpw/task?project=" + encodeURIComponent(props.project) + "&code=" + encodeURIComponent(record.taskCode) : "", record.searchKey);
			else if (["publication", "snapshot"].includes(record.kind)) openSnapshotBrowser?.(props.record, record.process, props.project);
			else open(record.searchKey || props.record.__search_key__);
		}
		async function action(event) {
			if (event.type === "page") selectPage(event.value);
			else if (event.type === "refresh") load(false, true);
			else if (event.type === "open") open(model.value.summary.searchKey);
			else if (event.type === "link") {
				emit("leave");
				openObjectTab?.(event.value, props.project);
			} else if (event.type === "child") open(event.key);
			else if (event.type === "person") {
				emit("leave");
				openUserProfile?.(event.key);
			} else if (event.type === "task") {
				if (await inspector(event.process, event.key) !== false) openTaskManager?.(props.record, "", {}, event.key);
			} else if (event.type === "note") {
				const row = data.value.notes[event.index];
				await inspector(row.process, row.isTaskNote ? "sthpw/task?project=" + encodeURIComponent(props.project) + "&code=" + encodeURIComponent(row.taskCode) : "", row.searchKey);
			} else if (event.type === "filter") {
				emit("leave");
				openTaskManager?.(props.record, event.field === "process" ? event.value : "", { [event.field]: event.value });
			}
		}
		watch(() => [
			props.ticket,
			props.project,
			props.record
		], async () => {
			generation++;
			data.value = null;
			dataPage.value = "";
			activity.value = [];
			error.value = "";
			busy.value = false;
			page.value = pages.get(identity.value) || "tasks";
			if (pages.size > 200) pages.delete(pages.keys().next().value);
			await nextTick();
			if (tabs.value && !observer) {
				observer = observeFrameSizes(() => {
					width.value = tabs.value.clientWidth;
				});
				observer.observe(tabs.value);
				width.value = tabs.value.clientWidth;
			}
			load(false, true);
		}, { immediate: true });
		watch(() => props.ticket, () => {
			pages.clear();
			cache.clear();
		});
		onBeforeUnmount(() => {
			generation++;
			observer?.disconnect();
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "scroll",
				ref: scroll,
				class: "object-report",
				"aria-busy": busy.value,
				tabindex: "0"
			}, [createBaseVNode("div", {
				ref_key: "content",
				ref: content,
				class: "object-report-content"
			}, [
				data.value ? (openBlock(), createBlock(_sfc_main$6, {
					key: 0,
					model: model.value,
					onEvent: action
				}, null, 8, ["model"])) : createCommentVNode("", true),
				createBaseVNode("div", {
					ref_key: "tabs",
					ref: tabs,
					class: "object-report-tabs"
				}, [createVNode(_sfc_main$9, {
					scene: tabScene.value,
					onEvent: action
				}, null, 8, ["scene"])], 512),
				error.value ? (openBlock(), createElementBlock("p", _hoisted_2, [createTextVNode(toDisplayString(unref(t)(error.value)) + " ", 1), createVNode(_sfc_main$7, {
					label: "Retry",
					disabled: busy.value,
					onClick: _cache[0] || (_cache[0] = ($event) => load(false, true))
				}, null, 8, ["disabled"])])) : createCommentVNode("", true),
				busy.value && !pageReady.value ? (openBlock(), createElementBlock("p", _hoisted_3, toDisplayString(unref(t)("Loading data…")), 1)) : createCommentVNode("", true),
				pageReady.value && [
					"tasks",
					"notes",
					"children"
				].includes(page.value) ? (openBlock(), createBlock(_sfc_main$6, {
					key: 3,
					model: model.value,
					part: "page",
					onEvent: action
				}, null, 8, ["model"])) : pageReady.value && page.value === "snapshots" ? (openBlock(), createBlock(_sfc_main$3, {
					key: identity.value,
					metrics: data.value.metrics,
					groups: snapshotGroups.value,
					onSnapshot: snapshot,
					onFile: file
				}, null, 8, ["metrics", "groups"])) : pageReady.value && page.value === "activity" ? (openBlock(), createElementBlock("section", _hoisted_4, [
					(openBlock(true), createElementBlock(Fragment, null, renderList(activity.value, (record, index) => {
						return openBlock(), createBlock(_sfc_main$5, {
							key: record.eventId || index,
							record,
							onTarget: ($event) => open(record.targetSearchKey),
							onActivity: ($event) => activityAction(record),
							onOpenLink: open
						}, null, 8, [
							"record",
							"onTarget",
							"onActivity"
						]);
					}), 128)),
					!activity.value.length && !busy.value ? (openBlock(), createElementBlock("p", _hoisted_5, toDisplayString(unref(t)("No recent activity")), 1)) : createCommentVNode("", true),
					data.value.hasMore ? (openBlock(), createBlock(_sfc_main$7, {
						key: 1,
						label: "Load more",
						disabled: busy.value,
						onClick: _cache[1] || (_cache[1] = ($event) => load(true))
					}, null, 8, ["disabled"])) : createCommentVNode("", true)
				])) : createCommentVNode("", true),
				createVNode(FilePreview_default, {
					ref_key: "preview",
					ref: preview,
					ticket: __props.ticket,
					project: __props.project,
					"search-type": __props.record?.__search_key__?.split("?")[0]
				}, null, 8, [
					"ticket",
					"project",
					"search-type"
				])
			], 512)], 8, _hoisted_1);
		};
	}
};
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/admin.document.mjs
function policy(model) {
	const editable = !!model.ready && !!model.canWrite && !model.busy && !model.uncertain;
	return {
		editable,
		save: editable && !!model.dirty && !model.pendingText && model.saveAllowed !== false,
		discard: !model.busy && !!(model.dirty || model.uncertain || model.pendingText),
		reload: !model.busy && !!model.canLoad
	};
}
function documentEvent(ui, model, event) {
	const next = Object.assign({}, ui), commands = [], allow = policy(model);
	switch (event.type) {
		case "save":
			if (allow.save) next.confirmation = "save";
			break;
		case "reload":
			if (allow.reload) {
				if (model.dirty || model.uncertain || model.pendingText) next.confirmation = "reload";
				else commands.push({
					type: "reload",
					force: false
				});
			}
			break;
		case "discard":
			if (allow.discard) next.confirmation = "discard";
			break;
		case "keep":
			next.confirmation = "";
			break;
		case "confirm":
			if (!model.busy && next.confirmation) {
				const action = next.confirmation;
				next.confirmation = "";
				if (action === "save") {
					if (allow.save) commands.push({ type: "save" });
				} else if (action === "reload" || model.uncertain) commands.push({
					type: "reload",
					force: true
				});
				else commands.push({ type: "discard" });
			}
			break;
		default: return null;
	}
	return {
		ui: next,
		commands
	};
}
function toolbar(model, ui, width, language) {
	const tr = (text) => translate(text, language), compact = width < 550, allow = policy(model);
	const saveWidth = compact ? 38 : language === "ru" ? 200 : 166, discardWidth = compact ? 38 : 118;
	return { nodes: [
		node("Button", "adminReloadDocument", rect(0, 0, 38, 38), {
			text: tr("Reload from server"),
			icon: "refresh",
			iconOnly: true,
			enabled: allow.reload,
			action: { type: "reload" }
		}),
		label("adminDocumentStatus", rect(48, 0, width - saveWidth - discardWidth - 72, 38), tr(model.busy ? "Working on the server…" : model.dirty ? "Unsaved changes" : !model.canWrite ? "Read-only" : ""), muted),
		node("Button", "adminDiscardDocument", rect(width - saveWidth - discardWidth - 8, 0, discardWidth, 38), {
			text: tr("Discard"),
			icon: "undo",
			iconOnly: compact,
			enabled: allow.discard,
			action: { type: "discard" }
		}),
		node("Button", "adminSaveDocument", rect(width - saveWidth, 0, saveWidth, 38), {
			text: tr("Save to server"),
			icon: "save",
			iconOnly: compact,
			enabled: allow.save,
			highlighted: true,
			action: { type: "save" }
		})
	] };
}
function notices(model, ui, width, language, discardText, confirmText) {
	const tr = (text) => translate(text, language), nodes = [];
	let top = 0;
	if (model.error || model.message) {
		nodes.push(node("Area", "adminDocumentError", rect(0, 0, width, 58), {
			text: tr(model.error || model.message),
			label: tr(model.error ? "Server error" : "Status"),
			notice: true,
			readOnly: true,
			role: model.error ? "alert" : "status",
			color: model.error ? "error" : "secondaryText"
		}));
		top += 66;
	}
	if (ui.confirmation) {
		const saving = ui.confirmation === "save", narrow = width < 520, details = saving && model.confirmationDetails, height = (narrow ? 136 : 90) + (details ? 140 : 0);
		nodes.push(node("Box", "adminDocumentConfirmation", rect(0, top, width, height), {
			background: "surfaceContainerHigh",
			children: [
				label("adminConfirmationText", rect(12, 6, width - 24, narrow ? 72 : 42), tr(model.confirmationText || (saving ? "These changes will be saved on the server and will affect other users of the project." : discardText || "Discard unsaved changes?")), { wrap: true }),
				node("Button", "adminCancelSave", rect(12, height - 44, narrow ? 128 : 164, 36), {
					text: tr(saving ? "Cancel" : "Keep editing"),
					enabled: !model.busy,
					action: { type: "keep" }
				}),
				node("Button", "adminConfirmSave", rect(narrow ? 150 : 188, height - 44, narrow ? width - 162 : 220, 36), {
					text: tr(saving ? "Save" : confirmText || "Discard changes"),
					enabled: !model.busy,
					highlighted: saving,
					destructive: !saving,
					action: { type: "confirm" }
				})
			].concat(details ? [node("Area", "adminConfirmationDetails", rect(12, narrow ? 82 : 48, width - 24, 126), {
				text: details,
				label: tr("Changes"),
				readOnly: true,
				notice: true,
				color: "error"
			})] : [])
		}));
		top += height + 8;
	}
	return {
		nodes,
		top
	};
}
function tabs(id, options, current, bounds, enabled, actionType) {
	const width = bounds.width / options.length;
	const available = options.filter((option) => !option.disabled);
	const keys = {
		Home: {
			type: actionType,
			value: available[0].value
		},
		End: {
			type: actionType,
			value: available[available.length - 1].value
		}
	};
	const selected = Math.max(0, available.findIndex((option) => option.value === current));
	keys.ArrowLeft = {
		type: actionType,
		value: available[(selected + available.length - 1) % available.length].value
	};
	keys.ArrowRight = {
		type: actionType,
		value: available[(selected + 1) % available.length].value
	};
	return node("Box", id, bounds, {
		background: "surfaceContainerHigh",
		border: "outlineVariant",
		radius: 9,
		role: "radiogroup",
		children: options.map((option, index) => node("Button", id + "_" + option.value, rect(index * width + 3, 3, width - 6, bounds.height - 6), {
			text: option.label,
			icon: option.icon || "",
			radio: true,
			selected: current === option.value,
			enabled: enabled && option.disabled !== true,
			keys,
			action: {
				type: actionType,
				value: option.value
			}
		}))
	});
}
function sectionSelector(id, options, current, bounds, enabled, actionType, caption) {
	if (options.some((option) => option.label.length * 6.8 + 32 > bounds.width / options.length)) return node("Choice", id, bounds, {
		label: caption || (options.find((option) => option.value === current) || options[0] || {}).label || "",
		options: options.map((option) => ({
			value: option.value,
			label: option.label
		})),
		value: current,
		enabled,
		action: { type: actionType }
	});
	return tabs(id, options, current, bounds, enabled, actionType);
}
//#endregion
export { activateRichLink as A, customUrlLocation as C, savedSearchLink as D, sameSearchKey as E, extractSkeys as M, linkifyPlainText as N, searchLink as O, withoutSkeys as P, customPageLink as S, projectPath as T, timestampFullLabel as _, tabs as a, addressProject as b, FilePreview_default as c, _sfc_main$5 as d, usePagination as f, matchesSearch as g, dayLabel as h, sectionSelector as i, escapeHtml as j, workspaceAddress as k, FilePreviewContent_default as l, dateLabel as m, notices as n, toolbar as o, dateKey as p, policy as r, _sfc_main as s, documentEvent as t, _sfc_main$4 as u, timestampLabel as v, linkProject as w, browserLink as x, uniqueRecords as y };

//# sourceMappingURL=admin.document.js.map