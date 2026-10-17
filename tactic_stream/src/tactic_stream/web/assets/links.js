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
	const match = /^\/projects\/([^/]+)\/?$/.exec(address.pathname);
	if (match) try {
		return decodeURIComponent(match[1]);
	} catch {
		return "";
	}
	return "";
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
export { sameSearchKey as a, workspaceAddress as c, extractSkeys as d, linkifyPlainText as f, projectPath as i, activateRichLink as l, browserLink as n, savedSearchLink as o, withoutSkeys as p, linkProject as r, searchLink as s, addressProject as t, escapeHtml as u };

//# sourceMappingURL=links.js.map