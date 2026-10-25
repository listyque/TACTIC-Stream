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
export { sameSearchKey as a, workspaceAddress as c, projectPath as i, browserLink as n, savedSearchLink as o, linkProject as r, searchLink as s, addressProject as t };

//# sourceMappingURL=links.js.map