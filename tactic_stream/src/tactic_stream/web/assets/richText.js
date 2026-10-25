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
export { withoutSkeys as a, linkifyPlainText as i, escapeHtml as n, extractSkeys as r, activateRichLink as t };

//# sourceMappingURL=richText.js.map