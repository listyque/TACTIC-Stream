import { r as fileIcon } from "./snapshot.ui.js";
//#region ../src/tactic_stream/shared_ui/features/files/file_values.mjs
function fileName(path) {
	return String(path || "").replace(/\\/g, "/").split("/").pop();
}
function extension(path) {
	const name = fileName(path), index = name.lastIndexOf(".");
	return index > 0 ? name.slice(index + 1).toUpperCase() : "FILE";
}
function sourceIcon(path) {
	const type = /\.(apng|avif|png|jpe?g|webp|gif|tiff?|bmp|svg)$/i.test(path) ? "image" : /\.(mov|mp4|avi|mkv|webm)$/i.test(path) ? "movie" : "";
	return fileIcon("file", type, "", path);
}
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
//#endregion
export { sourceIcon as i, fileName as n, prettySize as r, extension as t };

//# sourceMappingURL=file_values.js.map