import { H as preferences } from "./index.js";
import { M as rpc } from "./clipboard.js";
//#region src/features/checkin/files.js
var sourcePath = (file) => file.webkitRelativePath || file.name;
var descriptors = (files) => files.map((file) => ({
	path: sourcePath(file),
	size: file.size
}));
function prettySize(value) {
	for (const unit of [
		"B",
		"KB",
		"MB",
		"GB",
		"TB"
	]) {
		if (value < 1024 || unit === "TB") return value.toFixed(unit === "B" ? 0 : 1) + " " + unit;
		value /= 1024;
	}
}
async function prepareFiles(scope, files, values = {}) {
	return (await rpc("execute_cmd", [
		scope,
		"tactic.command.browser_checkin_cmd.BrowserCheckinCmd",
		{
			action: "match",
			source_files: descriptors(files),
			...values
		}
	], {}, true)).info.groups;
}
async function repositories(scope) {
	const configured = await rpc("get_base_dirs", [scope], {}, true);
	const paths = (value) => typeof value === "object" && value ? value : value?.startsWith("{") ? JSON.parse(value) : value ? { default: value } : {};
	const aliases = [.../* @__PURE__ */ new Set([
		"default",
		...Object.keys(paths(configured.asset_base_dir)),
		...Object.keys(paths(configured.base_dir_alias))
	])];
	const titles = paths(configured.repository_display);
	return aliases.filter((alias) => alias !== "plugins" && (preferences.repository.enabledAliases === null || preferences.repository.enabledAliases.includes(alias))).map((alias) => ({
		value: alias,
		label: titles[alias]?.title || alias
	}));
}
async function droppedFiles(transfer) {
	const files = [];
	async function visit(entry, path = "") {
		if (entry.isFile) {
			const file = await new Promise((resolve, reject) => entry.file(resolve, reject));
			Object.defineProperty(file, "webkitRelativePath", { value: path + file.name });
			files.push(file);
		} else if (entry.isDirectory) {
			const reader = entry.createReader();
			for (;;) {
				const children = await new Promise((resolve, reject) => reader.readEntries(resolve, reject));
				if (!children.length) break;
				for (const child of children) await visit(child, path + entry.name + "/");
			}
		}
	}
	const entries = [...transfer.items || []].filter((item) => item.kind === "file").map((item) => item.webkitGetAsEntry?.());
	if (entries.length && entries.every(Boolean)) for (const entry of entries) await visit(entry);
	else files.push(...transfer.files);
	return files;
}
//#endregion
export { repositories as a, prettySize as i, droppedFiles as n, sourcePath as o, prepareFiles as r, descriptors as t };

//# sourceMappingURL=files.js.map