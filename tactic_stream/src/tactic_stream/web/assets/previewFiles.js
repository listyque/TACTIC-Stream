import { k as t } from "./index.js";
//#region src/features/objects/previewFiles.js
async function fileBlob(file, { signal } = {}) {
	if (!file?.href) throw new Error(t("No web path is configured for this file."));
	const response = await fetch(file.href, { signal });
	if (!response.ok) throw new Error(t("File Offline"));
	return response.blob();
}
//#endregion
export { fileBlob as t };

//# sourceMappingURL=previewFiles.js.map