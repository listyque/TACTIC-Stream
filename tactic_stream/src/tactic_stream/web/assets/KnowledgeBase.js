import { A as onMounted, C as inject, E as nextTick, G as withCtx, H as watch, K as withDirectives, M as openBlock, N as renderList, O as onBeforeUnmount, P as renderSlot, X as ref, Y as reactive, _ as createElementBlock, b as createVNode, et as unref, g as createCommentVNode, h as createBlock, l as withModifiers, m as createBaseVNode, nt as normalizeStyle, p as computed, q as isRef, rt as toDisplayString, s as vShow, tt as normalizeClass, u as Fragment, y as createTextVNode } from "./vue.js";
import { D as t, O as appearance, T as randomId, o as _sfc_main$2, u as _sfc_main$3 } from "./index.js";
import { S as messageFileRequest, b as knowledgeRequest, c as xmlTokens, f as _sfc_main$4, n as copyText, o as javascriptTokens, s as pythonTokens, x as linkPreviews } from "./clipboard.js";
import { t as _sfc_main$5 } from "./AppSlider.js";
import { t as _sfc_main$6 } from "./AppTextField.js";
import { t as _sfc_main$7 } from "./AppMenu.js";
import { t as _sfc_main$8 } from "./AppCheckbox.js";
import { l as escapeHtml, n as browserLink, u as extractSkeys } from "./links.js";
import { t as _sfc_main$9 } from "./AppTextArea.js";
import { n as AppSearchField_default } from "./ItemSurface.js";
import { t as _sfc_main$10 } from "./AppMenuItem.js";
import { B as _sfc_main$13, E as _sfc_main$11, c as messageDate, n as MarkdownItCallable, s as _sfc_main$12 } from "./App.js";
//#region src/features/knowledge/markdown.js
var safeUrl = (value) => /^(https?:\/\/|ftp:\/\/|mailto:|skey:\/\/|tactic-search:\/\/|\/assets\/|#)/i.test(value || "") && !/[\u0000-\u001f]/.test(value);
var parser = new MarkdownItCallable({
	html: true,
	breaks: false,
	linkify: true,
	highlight(source, language) {
		const tokenize = {
			python: pythonTokens,
			py: pythonTokens,
			javascript: javascriptTokens,
			js: javascriptTokens,
			xml: xmlTokens
		}[language];
		return tokenize ? tokenize(source).map((token) => token.role ? `<span class="syntax-${token.role}">${escapeHtml(token.text)}</span>` : escapeHtml(token.text)).join("") : escapeHtml(source);
	}
});
parser.validateLink = safeUrl;
parser.linkify.add("skey:", { validate(text, position) {
	return /^\/\/[^\s<>"\[\]]+/.exec(text.slice(position))?.[0].replace(/[.,;:!?)}]+$/, "").length || 0;
} });
parser.core.ruler.after("inline", "knowledge_attributes", (state) => {
	for (let i = 0; i < state.tokens.length; i++) {
		const token = state.tokens[i];
		if (token.type !== "inline" || !token.children?.length) continue;
		const tail = token.children.at(-1), align = tail.type === "text" && tail.content.match(/\s+\{align=(center|right|justify)\}$/);
		if (align) {
			tail.content = tail.content.slice(0, -align[0].length);
			state.tokens[i - 1].attrSet("align", align[1]);
		}
		const first = token.children[0], checklist = first.type === "text" && first.content.match(/^\[([ xX])\]\s/);
		if (checklist && state.tokens[i - 1]?.type === "paragraph_open" && state.tokens[i - 2]?.type === "list_item_open") {
			first.content = first.content.slice(checklist[0].length);
			const box = new state.Token("html_inline", "", 0);
			box.content = `<input type="checkbox" ${checklist[1].trim() ? "checked" : ""} disabled>`;
			token.children.unshift(box);
		}
	}
});
var renderImage = parser.renderer.rules.image;
parser.renderer.rules.image = (tokens, index, options, env, self) => {
	const token = tokens[index], next = tokens[index + 1];
	const size = next?.type === "text" && next.content.match(/^\{width=(\d+)(?: height=(\d+))?(?: fit=(content))?\}/);
	if (size) {
		token.attrSet("width", size[1]);
		if (size[2]) token.attrSet("height", size[2]);
		if (size[3]) token.attrSet("data-fit", "content");
		next.content = next.content.slice(size[0].length);
	}
	return renderImage(tokens, index, options, env, self);
};
parser.renderer.rules.fence = (tokens, index) => {
	const token = tokens[index], language = token.info.trim().split(/\s+/)[0];
	return `<pre data-language="${escapeHtml(language)}"><code>${parser.options.highlight(token.content, language)}</code></pre>`;
};
function sanitize(html, project = "") {
	const root = document.createElement("template");
	root.innerHTML = html;
	const allowed = new Set("P DIV BR H1 H2 H3 H4 H5 H6 STRONG B EM I U S DEL SMALL UL OL LI BLOCKQUOTE PRE CODE HR A IMG TABLE THEAD TBODY TR TH TD SPAN INPUT".split(" "));
	for (const node of [...root.content.querySelectorAll("*")]) {
		if ([
			"SCRIPT",
			"STYLE",
			"IFRAME",
			"OBJECT",
			"SVG",
			"MATH",
			"FORM"
		].includes(node.tagName)) {
			node.remove();
			continue;
		}
		if (!allowed.has(node.tagName)) {
			node.replaceWith(...node.childNodes);
			continue;
		}
		const values = Object.fromEntries([...node.attributes].map((attr) => [attr.name, attr.value]));
		if (node.tagName === "SPAN" && values.style) {
			for (const [pattern, tag] of [
				[/font-weight:\s*(bold|[6-9]00)/i, "strong"],
				[/font-style:\s*italic/i, "em"],
				[/text-decoration[^:]*:\s*[^;]*underline/i, "u"],
				[/text-decoration[^:]*:\s*[^;]*line-through/i, "s"]
			]) if (pattern.test(values.style)) {
				const wrapper = document.createElement(tag);
				wrapper.append(...node.childNodes);
				node.append(wrapper);
			}
		}
		for (const attr of [...node.attributes]) node.removeAttribute(attr.name);
		if (node.tagName === "A" && safeUrl(values.href)) {
			node.setAttribute("href", browserLink(values.href, project));
			node.dataset.link = values.href;
			if (!/^(skey|tactic-search):/i.test(values.href)) {
				node.target = "_blank";
				node.rel = "noopener noreferrer";
			}
		}
		if (node.tagName === "IMG") {
			if (!/^(https?:\/\/|\/assets\/)/i.test(values.src || "")) {
				node.replaceWith(document.createTextNode(values.alt || ""));
				continue;
			}
			node.src = values.src;
			node.alt = values.alt || "";
			node.loading = "lazy";
			for (const name of ["width", "height"]) if (/^\d{1,5}$/.test(values[name] || "")) node.setAttribute(name, values[name]);
			if (values["data-fit"] === "content") node.dataset.fit = "content";
		}
		if (node.tagName === "PRE") node.dataset.language = (values["data-language"] || "").replace(/[^\w+-]/g, "");
		if (node.tagName === "SPAN" && /^syntax-[\w-]+$/.test(values.class || "")) node.className = values.class;
		const align = values.align || values.style?.match(/text-align:\s*(left|right|center|justify)/)?.[1];
		if ([
			"left",
			"center",
			"right",
			"justify"
		].includes(align)) node.setAttribute("align", align);
		if (node.tagName === "INPUT") {
			if (values.type !== "checkbox") {
				node.remove();
				continue;
			}
			node.type = "checkbox";
			node.disabled = true;
			node.defaultChecked = Object.hasOwn(values, "checked");
		}
	}
	return root;
}
function articleHtml(source, project = "") {
	let fence = null;
	const lines = String(source || "").split("\n"), prepared = [];
	for (let i = 0; i < lines.length; i++) {
		const marker = lines[i].match(/^ {0,3}(`{3,}|~{3,})(.*)$/);
		if (marker && (!fence || marker[1][0] === fence[0] && marker[1].length >= fence.length && !marker[2].trim())) fence = fence ? null : marker[1];
		prepared.push(!fence && !lines[i] && i && !lines[i - 1] ? "<br />\n" : lines[i]);
	}
	const root = sanitize(parser.render(prepared.join("\n")), project), counts = /* @__PURE__ */ new Map();
	for (const heading of root.content.querySelectorAll("h1,h2,h3,h4,h5,h6")) {
		const id = heading.textContent.toLowerCase().replace(/[^\p{L}\p{N}_ -]/gu, "").trim().replace(/\s+/g, "-") || "heading";
		const count = counts.get(id) || 0;
		counts.set(id, count + 1);
		heading.id = id + (count ? "-" + count : "");
	}
	return root.innerHTML;
}
function htmlMarkdown(root) {
	function inline(node) {
		if (node.nodeType === Node.TEXT_NODE) return node.textContent.replace(/([\\`*_[\]])/g, "\\$1");
		if (node.nodeType !== Node.ELEMENT_NODE) return "";
		const text = [...node.childNodes].map(inline).join(""), tag = node.tagName;
		if (tag === "BR") return "  \n";
		if (tag === "INPUT") return node.checked ? "[x] " : "[ ] ";
		if (["STRONG", "B"].includes(tag)) return `**${text}**`;
		if (["EM", "I"].includes(tag)) return `*${text}*`;
		if (["S", "DEL"].includes(tag)) return `~~${text}~~`;
		if (tag === "U" || tag === "SMALL") return `<${tag.toLowerCase()}>${text}</${tag.toLowerCase()}>`;
		if (tag === "CODE") {
			const code = node.textContent, fence = "`".repeat(Math.max(1, ...[...code.matchAll(/`+/g)].map((match) => match[0].length + 1)));
			return fence + " " + code + " " + fence;
		}
		if (tag === "A") return `[${text}](${node.dataset.link || node.getAttribute("href") || ""})`;
		if (tag === "IMG") return `![${node.alt || ""}](${node.dataset.original || node.getAttribute("src")})` + (node.getAttribute("width") ? `{width=${node.getAttribute("width")}${node.getAttribute("height") ? " height=" + node.getAttribute("height") : ""}${node.dataset.fit === "content" ? " fit=content" : ""}}` : "");
		if ([
			"P",
			"DIV",
			"H1",
			"H2",
			"H3",
			"H4",
			"H5",
			"H6",
			"UL",
			"OL",
			"LI",
			"BLOCKQUOTE",
			"PRE",
			"HR",
			"TABLE"
		].includes(tag)) return block(node);
		return text;
	}
	function block(node) {
		const tag = node.tagName, text = [...node.childNodes].map(inline).join("");
		const alignment = node.getAttribute("align") && node.getAttribute("align") !== "left" ? ` {align=${node.getAttribute("align")}}` : "";
		if (/^H[1-6]$/.test(tag)) return "#".repeat(Number(tag[1])) + " " + text + alignment + "\n\n";
		if (tag === "PRE") {
			const source = node.textContent.replace(/\n$/, "");
			const fence = "`".repeat(Math.max(3, ...[...source.matchAll(/`+/g)].map((match) => match[0].length + 1)));
			return `${fence}${node.dataset.language || ""}\n${source}\n${fence}\n\n`;
		}
		if (tag === "HR") return "---\n\n";
		if (tag === "BLOCKQUOTE") return text.trim().split("\n").map((line) => "> " + line).join("\n") + "\n\n";
		if (tag === "UL" || tag === "OL") return [...node.children].map((li, index) => {
			const marker = tag === "OL" ? `${index + 1}. ` : "- ";
			return marker + [...li.childNodes].map((child) => child.nodeType === Node.ELEMENT_NODE ? ["UL", "OL"].includes(child.tagName) ? "\n" + block(child).trimEnd() : child.tagName === "P" ? [...child.childNodes].map(inline).join("") : inline(child) : inline(child)).join("").trim().replace(/\n/g, "\n" + " ".repeat(marker.length));
		}).join("\n") + "\n\n";
		if (tag === "TABLE") {
			const rows = [...node.querySelectorAll("tr")].map((row) => "| " + [...row.children].map((cell) => [...cell.childNodes].map(inline).join("").replace(/\|/g, "\\|").replace(/\n/g, "<br>")).join(" | ") + " |");
			if (rows.length) rows.splice(1, 0, "| " + [...node.querySelector("tr").children].map(() => "---").join(" | ") + " |");
			return rows.join("\n") + "\n\n";
		}
		if (tag === "INPUT") return node.checked ? "[x] " : "[ ] ";
		return (text.trim() || "<br />") + alignment + "\n\n";
	}
	return [...root.childNodes].map((node) => node.nodeType === Node.TEXT_NODE ? node.textContent.trim() ? inline(node) : "" : [
		"IMG",
		"A",
		"INPUT"
	].includes(node.tagName) ? inline(node) + "\n\n" : block(node)).join("").trimEnd();
}
function plainText(source) {
	const root = sanitize(parser.render(source || ""));
	for (const node of root.content.querySelectorAll("p,div,h1,h2,h3,h4,h5,h6,li,pre,tr")) node.append(document.createTextNode("\n"));
	return root.content.textContent.trim();
}
//#endregion
//#region src/features/knowledge/KnowledgeEditor.vue
var _hoisted_1$1 = ["contenteditable", "aria-label"];
var _hoisted_2$1 = {
	key: 2,
	class: "knowledge-image-settings"
};
var _hoisted_3$1 = [
	"value",
	"aria-label",
	"disabled"
];
var _hoisted_4$1 = ["aria-label"];
var _hoisted_5$1 = {
	key: 0,
	class: "error"
};
var _hoisted_6$1 = { key: 0 };
var _sfc_main$1 = {
	__name: "KnowledgeEditor",
	props: {
		modelValue: String,
		project: String,
		disabled: Boolean,
		attachments: Array
	},
	emits: [
		"update:modelValue",
		"attachments",
		"upload"
	],
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const host = ref(null), body = ref(null), source = ref(null), mode = ref("visual"), width = ref(0), insertion = ref(null);
		const panel = ref(""), label = ref(""), address = ref(""), content = ref(""), language = ref("python"), failure = ref("");
		const image = ref(null), imageWidth = ref(320), imageNatural = ref(""), formats = reactive({});
		const scroll = ref(null), hoveredLink = ref(null), linkPosition = ref({}), imagePosition = ref({});
		let range = null, editingAnchor = null, emitted = "", observer, resizeStart = null;
		const actions = [
			[
				"bold",
				"bold",
				"Bold · Ctrl+B",
				0
			],
			[
				"italic",
				"italic",
				"Italic · Ctrl+I",
				640
			],
			[
				"underline",
				"underline",
				"Underline",
				650
			],
			[
				"strikeThrough",
				"strikethrough",
				"Strikethrough",
				690
			],
			[
				"small",
				"small-text",
				"Small text",
				730
			],
			[
				"link",
				"link",
				"Insert link · Ctrl+K",
				0
			],
			[
				"attachments",
				"attachments-editor",
				"Show attached files",
				640
			],
			[
				"quote",
				"format-quote",
				"Insert quote",
				770
			],
			[
				"code",
				"code-block",
				"Insert code block",
				810
			],
			[
				"checklist",
				"checkbox-multiple-marked-outline",
				"Checklist",
				850
			]
		];
		const hidden = computed(() => actions.filter((action) => width.value < action[3]));
		function previews() {
			for (const node of body.value?.querySelectorAll("img") || []) {
				const file = props.attachments?.find((file) => file.webUrl === (node.dataset.original || node.getAttribute("src")));
				if (file && file.previewUrl !== file.webUrl) {
					node.dataset.original = file.webUrl;
					node.dataset.preview = file.previewUrl;
				}
			}
		}
		function load() {
			if (body.value) body.value.innerHTML = articleHtml(props.modelValue, props.project);
			previews();
			image.value = null;
		}
		watch(() => props.attachments, previews);
		function imageError(event) {
			const node = event.target;
			if (node.tagName === "IMG" && node.dataset.preview && node.src !== new URL(node.dataset.preview, location.href).href) node.src = node.dataset.preview;
		}
		watch(() => props.modelValue, (value) => {
			if (value !== emitted && mode.value === "visual") load();
		});
		watch(mode, () => nextTick(load));
		function sync() {
			if (mode.value !== "visual") return;
			const value = htmlMarkdown(body.value);
			emitted = value;
			emit("update:modelValue", value);
		}
		function remember() {
			const selection = window.getSelection();
			if (selection?.rangeCount && body.value?.contains(selection.anchorNode) && body.value.contains(selection.focusNode)) range = selection.getRangeAt(0).cloneRange();
			for (const name of [
				"bold",
				"italic",
				"underline",
				"strikeThrough"
			]) formats[name] = !!body.value?.contains(selection?.anchorNode) && document.queryCommandState(name);
		}
		function restore() {
			body.value.focus();
			const selection = window.getSelection();
			selection.removeAllRanges();
			if (range && body.value.contains(range.commonAncestorContainer)) selection.addRange(range);
			else {
				const last = document.createRange();
				last.selectNodeContents(body.value);
				last.collapse(false);
				selection.addRange(last);
			}
		}
		function insert(html) {
			restore();
			document.execCommand("insertHTML", false, html);
			previews();
			sync();
			remember();
		}
		function wrapSource(before, after = "") {
			const field = source.value, start = field.selectionStart, end = field.selectionEnd;
			const value = props.modelValue.slice(0, start) + before + props.modelValue.slice(start, end) + after + props.modelValue.slice(end);
			emitted = value;
			emit("update:modelValue", value);
			nextTick(() => {
				field.focus();
				field.setSelectionRange(start + before.length, end + before.length);
			});
		}
		function action(name, value = "") {
			if (props.disabled) return;
			if (name === "attachments") {
				mode.value = "visual";
				emit("attachments");
				return;
			}
			if ([
				"link",
				"image",
				"quote",
				"pull-quote",
				"code",
				"table"
			].includes(name)) {
				open(name);
				return;
			}
			if (mode.value === "markdown") {
				const syntax = {
					bold: ["**", "**"],
					italic: ["*", "*"],
					underline: ["<u>", "</u>"],
					strikeThrough: ["~~", "~~"],
					small: ["<small>", "</small>"],
					insertUnorderedList: ["- "],
					insertOrderedList: ["1. "],
					checklist: ["- [ ] "],
					divider: ["\n\n---\n\n"],
					formatBlock: [value === "p" ? "" : "#".repeat(Number(value.slice(1))) + " "]
				};
				if (syntax[name]) wrapSource(...syntax[name]);
				else if (name === "undo" || name === "redo") {
					source.value.focus();
					document.execCommand(name);
				}
				return;
			}
			restore();
			if (name === "divider") document.execCommand("insertHTML", false, "<hr><p><br></p>");
			else if (name === "checklist") document.execCommand("insertHTML", false, "<ul><li><input type=\"checkbox\" disabled> </li></ul>");
			else if (name === "small") document.execCommand("insertHTML", false, `<small>${escapeHtml(window.getSelection().toString() || " ")}</small>`);
			else document.execCommand(name, false, value);
			sync();
			remember();
		}
		function open(kind, anchor = null) {
			remember();
			panel.value = kind;
			editingAnchor = anchor;
			failure.value = "";
			label.value = anchor?.textContent || window.getSelection()?.toString() || "";
			address.value = anchor?.dataset.link || anchor?.getAttribute("href") || "";
			content.value = label.value;
			insertion.value.showModal();
		}
		function applyInsertion() {
			if (["link", "image"].includes(panel.value) && (!safeUrl(address.value) || panel.value === "image" && !/^(https?:\/\/|\/assets\/)/i.test(address.value))) {
				failure.value = t("Enter a valid web or skey link.");
				return;
			}
			let html, markdown;
			const text = escapeHtml(label.value), url = escapeHtml(address.value);
			if (panel.value === "link") {
				html = `<a href="${url}" data-link="${url}">${text || url}</a>`;
				markdown = `[${label.value || address.value}](${address.value})`;
			} else if (panel.value === "image") {
				html = `<img src="${url}" alt="${text}" width="560">`;
				markdown = `![${label.value}](${address.value}){width=560}`;
			} else if (panel.value === "code") {
				html = `<pre data-language="${escapeHtml(language.value)}"><code>${escapeHtml(content.value)}</code></pre><p><br></p>`;
				markdown = "\n\n```" + language.value + "\n" + content.value + "\n```\n\n";
			} else if (panel.value === "table") {
				html = "<table><thead><tr><th> </th><th> </th></tr></thead><tbody><tr><td> </td><td> </td></tr></tbody></table><p><br></p>";
				markdown = "\n\n| | |\n| --- | --- |\n| | |\n\n";
			} else {
				const align = panel.value === "pull-quote" ? " align=\"center\"" : "";
				html = `<blockquote><p${align}>${escapeHtml(content.value).replace(/\n/g, "<br>")}</p></blockquote><p><br></p>`;
				markdown = "\n\n" + content.value.split("\n").map((line) => "> " + line).join("\n") + (align ? " {align=center}" : "") + "\n\n";
			}
			insertion.value.close();
			if (mode.value === "markdown") wrapSource(markdown);
			else {
				if (editingAnchor?.isConnected) {
					range = document.createRange();
					range.selectNode(editingAnchor);
				}
				insert(html);
			}
		}
		function insertAttachment(file) {
			const url = file.webUrl, title = file.title.replace(/[\[\]]/g, "");
			if (mode.value === "markdown") wrapSource((file.isImage ? "!" : "") + `[${title}](${url})` + (file.isImage ? "{width=560}" : ""));
			else insert(file.isImage ? `<img src="${escapeHtml(url)}" alt="${escapeHtml(file.title)}" width="560">` : `<a href="${escapeHtml(url)}" data-link="${escapeHtml(url)}">${escapeHtml(file.title)}</a>`);
		}
		function paste(event) {
			event.preventDefault();
			const files = [...event.clipboardData.files];
			if (files.length) {
				emit("upload", files);
				return;
			}
			const html = event.clipboardData.getData("text/html"), text = event.clipboardData.getData("text/plain");
			insert(html ? sanitize(html, props.project).innerHTML : escapeHtml(text).replace(/\n/g, "<br>"));
		}
		function selectImage(event) {
			const target = event.target.closest("img");
			image.value = target || null;
			if (target) {
				imageWidth.value = Math.round(target.width);
				imageNatural.value = `${target.naturalWidth} × ${target.naturalHeight}`;
				range = document.createRange();
				range.selectNode(target);
				positionImage();
			} else if (event.target.closest("a")) event.preventDefault();
		}
		function hoverLink(event) {
			const anchor = event.target.closest("a");
			if (anchor === hoveredLink.value) return;
			hoveredLink.value = anchor;
			if (anchor) {
				const box = anchor.getBoundingClientRect(), host = scroll.value.getBoundingClientRect();
				linkPosition.value = {
					left: Math.max(0, Math.min(host.width - 30, box.right - host.left)) + "px",
					top: Math.max(0, box.top - host.top + scroll.value.scrollTop - 24) + "px"
				};
			}
		}
		function positionImage() {
			if (!image.value?.isConnected) return;
			const box = image.value.getBoundingClientRect(), host = scroll.value.getBoundingClientRect();
			imagePosition.value = {
				left: Math.max(0, box.right - host.left - 20) + "px",
				top: box.bottom - host.top + scroll.value.scrollTop - 20 + "px"
			};
		}
		function setWidth(value, fit = false) {
			const selected = image.value;
			if (!selected?.isConnected) return;
			const width = Math.max(24, Math.round(value)), height = Math.round(width * (selected.naturalHeight || selected.height) / (selected.naturalWidth || selected.width));
			const marker = randomId();
			const html = `<img data-editor-image="${marker}" src="${escapeHtml(selected.getAttribute("src"))}"${selected.dataset.original ? " data-original=\"" + escapeHtml(selected.dataset.original) + "\"" : ""} alt="${escapeHtml(selected.alt)}" width="${width}" height="${height}"${fit ? " data-fit=\"content\"" : ""}>`;
			range = document.createRange();
			range.selectNode(selected);
			insert(html);
			image.value = body.value.querySelector("img[data-editor-image=\"" + marker + "\"]");
			if (image.value) delete image.value.dataset.editorImage;
			imageWidth.value = width;
			positionImage();
		}
		function resizeDown(event) {
			event.preventDefault();
			event.currentTarget.setPointerCapture(event.pointerId);
			resizeStart = {
				x: event.clientX,
				width: image.value.width
			};
		}
		function resizeMove(event) {
			if (resizeStart) {
				imageWidth.value = Math.max(24, Math.round(resizeStart.width + event.clientX - resizeStart.x));
				image.value.style.width = imageWidth.value + "px";
				image.value.style.height = "auto";
				positionImage();
			}
		}
		function resizeEnd(event) {
			if (!resizeStart) return;
			const value = event.type === "pointercancel" ? resizeStart.width : imageWidth.value;
			image.value.style.width = "";
			image.value.style.height = "";
			resizeStart = null;
			setWidth(value);
		}
		function drop(event) {
			if (event.dataTransfer.files.length) {
				event.preventDefault();
				emit("upload", [...event.dataTransfer.files]);
				return;
			}
			if (image.value && event.dataTransfer.types.includes("text/html")) {
				image.value = null;
				return;
			}
			if (event.dataTransfer.getData("text/html")) {
				event.preventDefault();
				insert(sanitize(event.dataTransfer.getData("text/html"), props.project).innerHTML);
			}
		}
		function keys(event) {
			if (!(event.ctrlKey || event.metaKey)) return;
			const name = {
				b: "bold",
				i: "italic",
				u: "underline",
				k: "link"
			}[event.key.toLowerCase()];
			if (name) {
				event.preventDefault();
				action(name);
			}
		}
		onMounted(() => {
			load();
			observer = new ResizeObserver((entries) => {
				width.value = entries[0].contentRect.width;
			});
			observer.observe(host.value);
			document.addEventListener("selectionchange", remember);
		});
		onBeforeUnmount(() => {
			observer?.disconnect();
			document.removeEventListener("selectionchange", remember);
		});
		__expose({
			insertAttachment,
			focus() {
				(mode.value === "visual" ? body.value : source.value)?.focus();
			},
			synchronize: sync
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: "knowledge-editor",
				onKeydown: keys
			}, [
				createBaseVNode("div", { class: normalizeClass(["knowledge-formatting", { minimal: width.value < 640 }]) }, [
					createVNode(_sfc_main$2, {
						"icon-only": "",
						icon: "undo",
						label: "Undo",
						disabled: __props.disabled,
						onMousedown: _cache[0] || (_cache[0] = withModifiers(() => {}, ["prevent"])),
						onClick: _cache[1] || (_cache[1] = ($event) => action("undo"))
					}, null, 8, ["disabled"]),
					createVNode(_sfc_main$2, {
						"icon-only": "",
						icon: "redo",
						label: "Redo",
						disabled: __props.disabled,
						onMousedown: _cache[2] || (_cache[2] = withModifiers(() => {}, ["prevent"])),
						onClick: _cache[3] || (_cache[3] = ($event) => action("redo"))
					}, null, 8, ["disabled"]),
					_cache[29] || (_cache[29] = createBaseVNode("span", { class: "knowledge-format-divider" }, null, -1)),
					createVNode(_sfc_main$7, {
						label: "Text style",
						icon: "format-size",
						overlay: "",
						width: 190
					}, {
						trigger: withCtx(() => [..._cache[28] || (_cache[28] = [createBaseVNode("span", null, toDisplayString("Aa"), -1)])]),
						default: withCtx(() => [createVNode(_sfc_main$10, {
							label: "Normal text",
							onClick: _cache[4] || (_cache[4] = ($event) => action("formatBlock", "p"))
						}), (openBlock(), createElementBlock(Fragment, null, renderList(6, (level) => {
							return createVNode(_sfc_main$10, {
								key: level,
								label: unref(t)("Heading {level}", { level }),
								onClick: ($event) => action("formatBlock", "h" + level)
							}, null, 8, ["label", "onClick"]);
						}), 64))]),
						_: 1
					}),
					(openBlock(), createElementBlock(Fragment, null, renderList(actions, (item) => {
						return openBlock(), createElementBlock(Fragment, { key: item[0] }, [width.value >= item[3] ? (openBlock(), createBlock(_sfc_main$2, {
							key: 0,
							icon: item[1],
							label: item[2],
							"icon-only": "",
							tonal: formats[item[0]],
							disabled: __props.disabled,
							onMousedown: _cache[5] || (_cache[5] = withModifiers(() => {}, ["prevent"])),
							onClick: ($event) => action(item[0])
						}, null, 8, [
							"icon",
							"label",
							"tonal",
							"disabled",
							"onClick"
						])) : createCommentVNode("", true)], 64);
					}), 64)),
					_cache[30] || (_cache[30] = createBaseVNode("span", { class: "knowledge-format-divider" }, null, -1)),
					createVNode(_sfc_main$7, {
						label: "Lists",
						icon: "list-ul",
						overlay: "",
						width: 210
					}, {
						default: withCtx(() => [
							createVNode(_sfc_main$10, {
								label: "Bulleted list",
								icon: "list-ul",
								onClick: _cache[6] || (_cache[6] = ($event) => action("insertUnorderedList"))
							}),
							createVNode(_sfc_main$10, {
								label: "Numbered list",
								icon: "list-ol",
								onClick: _cache[7] || (_cache[7] = ($event) => action("insertOrderedList"))
							}),
							createVNode(_sfc_main$10, {
								label: "Checklist",
								icon: "checkbox-multiple-marked-outline",
								onClick: _cache[8] || (_cache[8] = ($event) => action("checklist"))
							})
						]),
						_: 1
					}),
					createVNode(_sfc_main$7, {
						label: "More formatting",
						overlay: "",
						width: 240
					}, {
						default: withCtx(() => [
							(openBlock(true), createElementBlock(Fragment, null, renderList(hidden.value, (item) => {
								return openBlock(), createBlock(_sfc_main$10, {
									key: item[0],
									label: item[2],
									icon: item[1],
									onClick: ($event) => action(item[0])
								}, null, 8, [
									"label",
									"icon",
									"onClick"
								]);
							}), 128)),
							createVNode(_sfc_main$10, {
								label: "Insert image URL",
								icon: "image",
								onClick: _cache[9] || (_cache[9] = ($event) => action("image"))
							}),
							createVNode(_sfc_main$10, {
								label: "Insert pull quote",
								icon: "format-quote",
								onClick: _cache[10] || (_cache[10] = ($event) => action("pull-quote"))
							}),
							createVNode(_sfc_main$10, {
								label: "Insert divider",
								icon: "minus",
								onClick: _cache[11] || (_cache[11] = ($event) => action("divider"))
							}),
							createVNode(_sfc_main$10, {
								label: "Insert table",
								icon: "table",
								onClick: _cache[12] || (_cache[12] = ($event) => action("table"))
							}),
							(openBlock(), createElementBlock(Fragment, null, renderList([
								"left",
								"center",
								"right",
								"justify"
							], (align) => {
								return createVNode(_sfc_main$10, {
									key: align,
									label: "Align " + align,
									icon: "align-" + align,
									onClick: ($event) => action("justify" + align[0].toUpperCase() + align.slice(1))
								}, null, 8, [
									"label",
									"icon",
									"onClick"
								]);
							}), 64))
						]),
						_: 1
					}),
					createVNode(_sfc_main$11, {
						modelValue: mode.value,
						"onUpdate:modelValue": _cache[13] || (_cache[13] = ($event) => mode.value = $event),
						class: "knowledge-editor-mode",
						"icon-only": width.value < 640,
						options: [{
							value: "visual",
							label: "Visual",
							icon: "edit"
						}, {
							value: "markdown",
							label: "Markdown",
							icon: "code"
						}],
						label: unref(t)("Editor mode")
					}, null, 8, [
						"modelValue",
						"icon-only",
						"label"
					])
				], 2),
				mode.value === "visual" ? renderSlot(_ctx.$slots, "attachments", {}, void 0, void 0, 0) : createCommentVNode("", true),
				withDirectives(createBaseVNode("div", {
					ref_key: "scroll",
					ref: scroll,
					class: "knowledge-visual-scroll",
					onPointerleave: _cache[18] || (_cache[18] = ($event) => hoveredLink.value = null),
					onScroll: _cache[19] || (_cache[19] = ($event) => {
						hoveredLink.value = null;
						positionImage();
					})
				}, [
					createBaseVNode("div", {
						ref_key: "body",
						ref: body,
						class: "knowledge-document knowledge-visual",
						contenteditable: !__props.disabled,
						role: "textbox",
						"aria-multiline": "true",
						"aria-label": unref(t)("Article content"),
						spellcheck: "true",
						onErrorCapture: imageError,
						onInput: sync,
						onPaste: paste,
						onClick: selectImage,
						onPointerover: hoverLink,
						onDragover: _cache[14] || (_cache[14] = withModifiers(() => {}, ["prevent"])),
						onDrop: drop
					}, null, 40, _hoisted_1$1),
					hoveredLink.value ? (openBlock(), createBlock(_sfc_main$2, {
						key: 0,
						"icon-only": "",
						icon: "edit",
						label: "Edit link",
						class: "knowledge-link-edit",
						style: normalizeStyle(linkPosition.value),
						onMousedown: _cache[15] || (_cache[15] = withModifiers(() => {}, ["prevent"])),
						onClick: _cache[16] || (_cache[16] = ($event) => open("link", hoveredLink.value))
					}, null, 8, ["style"])) : createCommentVNode("", true),
					image.value ? (openBlock(), createBlock(_sfc_main$2, {
						key: 1,
						"icon-only": "",
						icon: "MDI_RESIZE_BOTTOM_RIGHT",
						label: "Resize image",
						class: "knowledge-image-handle",
						style: normalizeStyle(imagePosition.value),
						onPointerdown: resizeDown,
						onPointermove: resizeMove,
						onPointerup: resizeEnd,
						onPointercancel: resizeEnd
					}, null, 8, ["style"])) : createCommentVNode("", true),
					image.value ? (openBlock(), createElementBlock("div", _hoisted_2$1, [
						createBaseVNode("small", null, toDisplayString(unref(t)("Image size")) + ": " + toDisplayString(imageWidth.value) + " px · " + toDisplayString(unref(t)("Original")) + ": " + toDisplayString(imageNatural.value), 1),
						createVNode(_sfc_main$5, {
							"model-value": imageWidth.value,
							min: 24,
							max: Math.max(560, body.value?.clientWidth || 560),
							step: 1,
							label: "Fixed image width",
							"onUpdate:modelValue": setWidth
						}, null, 8, ["model-value", "max"]),
						createVNode(_sfc_main$2, {
							label: "Stretch to content width",
							onClick: _cache[17] || (_cache[17] = ($event) => setWidth(body.value.clientWidth, true))
						})
					])) : createCommentVNode("", true)
				], 544), [[vShow, mode.value === "visual"]]),
				withDirectives(createBaseVNode("textarea", {
					ref_key: "source",
					ref: source,
					class: "knowledge-source app-text-area",
					value: __props.modelValue,
					"aria-label": unref(t)("Markdown source"),
					disabled: __props.disabled,
					onInput: _cache[20] || (_cache[20] = ($event) => {
						isRef(emitted) ? emitted.value = $event.target.value : emitted = $event.target.value;
						emit("update:modelValue", unref(emitted));
					}),
					onPaste: _cache[21] || (_cache[21] = (event) => {
						if (event.clipboardData.files.length) {
							event.preventDefault();
							emit("upload", [...event.clipboardData.files]);
						}
					})
				}, null, 40, _hoisted_3$1), [[vShow, mode.value === "markdown"]]),
				createBaseVNode("dialog", {
					ref_key: "insertion",
					ref: insertion,
					class: "record-dialog knowledge-insertion",
					"aria-label": unref(t)("Insert content")
				}, [
					createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)(panel.value === "link" ? "Insert link" : panel.value === "image" ? "Insert image URL" : panel.value === "code" ? "Insert code block" : panel.value === "table" ? "Insert table" : "Insert quote")), 1), createVNode(_sfc_main$2, {
						"icon-only": "",
						icon: "close",
						label: "Close",
						onClick: _cache[22] || (_cache[22] = ($event) => insertion.value.close())
					})]),
					failure.value ? (openBlock(), createElementBlock("p", _hoisted_5$1, toDisplayString(failure.value), 1)) : createCommentVNode("", true),
					panel.value === "link" || panel.value === "image" ? (openBlock(), createElementBlock(Fragment, { key: 1 }, [createBaseVNode("label", null, [createTextVNode(toDisplayString(unref(t)("Label")), 1), createVNode(_sfc_main$6, {
						modelValue: label.value,
						"onUpdate:modelValue": _cache[23] || (_cache[23] = ($event) => label.value = $event),
						label: "Label"
					}, null, 8, ["modelValue"])]), createBaseVNode("label", null, [createTextVNode(toDisplayString(unref(t)("Address")), 1), createVNode(_sfc_main$6, {
						modelValue: address.value,
						"onUpdate:modelValue": _cache[24] || (_cache[24] = ($event) => address.value = $event),
						label: "Address"
					}, null, 8, ["modelValue"])])], 64)) : panel.value !== "table" ? (openBlock(), createElementBlock(Fragment, { key: 2 }, [panel.value === "code" ? (openBlock(), createElementBlock("label", _hoisted_6$1, [createTextVNode(toDisplayString(unref(t)("Language")), 1), createVNode(_sfc_main$4, {
						modelValue: language.value,
						"onUpdate:modelValue": _cache[25] || (_cache[25] = ($event) => language.value = $event),
						options: [
							"python",
							"javascript",
							"xml",
							"text"
						].map((value) => ({
							value,
							label: value
						})),
						label: "Language"
					}, null, 8, ["modelValue", "options"])])) : createCommentVNode("", true), createVNode(_sfc_main$9, {
						modelValue: content.value,
						"onUpdate:modelValue": _cache[26] || (_cache[26] = ($event) => content.value = $event),
						label: "Content"
					}, null, 8, ["modelValue"])], 64)) : createCommentVNode("", true),
					createBaseVNode("footer", null, [createVNode(_sfc_main$2, {
						label: "Cancel",
						onClick: _cache[27] || (_cache[27] = ($event) => insertion.value.close())
					}), createVNode(_sfc_main$2, {
						label: "Insert",
						icon: "plus",
						highlighted: "",
						onClick: applyInsertion
					})])
				], 8, _hoisted_4$1)
			], 544);
		};
	}
};
//#endregion
//#region src/features/knowledge/KnowledgeBase.vue
var _hoisted_1 = { class: "knowledge-heading" };
var _hoisted_2 = {
	key: 0,
	class: "knowledge-error",
	role: "alert"
};
var _hoisted_3 = {
	key: 1,
	class: "knowledge-empty"
};
var _hoisted_4 = {
	key: 2,
	class: "knowledge-layout"
};
var _hoisted_5 = ["aria-label"];
var _hoisted_6 = {
	class: "knowledge-tree",
	role: "tree"
};
var _hoisted_7 = [
	"aria-selected",
	"aria-expanded",
	"data-knowledge-entry",
	"draggable",
	"onDragstart",
	"onDragover",
	"onDrop"
];
var _hoisted_8 = { class: "knowledge-disclosure" };
var _hoisted_9 = { key: 0 };
var _hoisted_10 = {
	key: 1,
	class: "knowledge-draft"
};
var _hoisted_11 = {
	key: 0,
	class: "knowledge-no-entries"
};
var _hoisted_12 = {
	key: 0,
	class: "knowledge-loading",
	role: "status"
};
var _hoisted_13 = {
	key: 1,
	class: "knowledge-empty"
};
var _hoisted_14 = { class: "knowledge-editor-heading" };
var _hoisted_15 = { key: 1 };
var _hoisted_16 = {
	key: 0,
	class: "knowledge-parent"
};
var _hoisted_17 = {
	key: 1,
	class: "knowledge-metadata-fields"
};
var _hoisted_18 = { key: 0 };
var _hoisted_19 = {
	key: 1,
	class: "knowledge-linked-header"
};
var _hoisted_20 = {
	key: 0,
	class: "knowledge-attachment-library"
};
var _hoisted_21 = {
	key: 0,
	class: "error"
};
var _hoisted_22 = { key: 0 };
var _hoisted_23 = { class: "knowledge-viewer-heading" };
var _hoisted_24 = { class: "knowledge-kind-tile" };
var _hoisted_25 = { class: "knowledge-title" };
var _hoisted_26 = { key: 0 };
var _hoisted_27 = { key: 0 };
var _hoisted_28 = { key: 0 };
var _hoisted_29 = {
	key: 0,
	class: "knowledge-history-banner"
};
var _hoisted_30 = {
	key: 1,
	class: "knowledge-section-contents"
};
var _hoisted_31 = { key: 0 };
var _hoisted_32 = { key: 0 };
var _hoisted_33 = { class: "knowledge-reading-scroll" };
var _hoisted_34 = {
	key: 0,
	class: "knowledge-linked-header"
};
var _hoisted_35 = {
	key: 1,
	class: "knowledge-outline"
};
var _hoisted_36 = ["innerHTML"];
var _hoisted_37 = {
	key: 2,
	class: "knowledge-resources"
};
var _hoisted_38 = { class: "knowledge-article-metadata" };
var _hoisted_39 = {
	key: 0,
	class: "knowledge-outline"
};
var _hoisted_40 = ["aria-label"];
var _hoisted_41 = ["aria-label"];
var _hoisted_42 = ["aria-label"];
var _sfc_main = {
	__name: "KnowledgeBase",
	props: {
		ticket: String,
		project: String,
		login: String,
		active: Boolean,
		selection: Array,
		target: String
	},
	emits: [
		"session-expired",
		"changed",
		"open-link",
		"location"
	],
	setup(__props, { expose: __expose, emit: __emit }) {
		const props = __props;
		const emit = __emit;
		const openObjectTab = inject("openObjectTab", null);
		const host = ref(null), width = ref(0), initialized = ref(false), canEdit = ref(false), canInitialize = ref(false);
		const catalog = ref([]), query = ref(""), identity = ref(""), searchKey = ref(""), revision = ref(""), catalogRevision = ref(""), selected = ref("");
		const document = ref(null), metadata = ref({}), files = ref([]), editing = ref(false), step = ref(0), expandedMetadata = ref(false);
		const navigationExpanded = ref(true), navigationPage = ref(true), tocVisible = ref(true), resourcesVisible = ref(false), attachmentsVisible = ref(false);
		const loading = ref(false), saving = ref(false), error = ref(""), storageError = ref(false), loaded = ref(false);
		const drafts = reactive({}), collapsed = reactive(/* @__PURE__ */ new Set()), organization = ref(null), dragging = ref(""), dropTarget = ref("");
		const editor = ref(null), viewer = ref(null), fileInput = ref(null), confirmation = ref(null), historyDialog = ref(null), deletion = ref(null), moveDialog = ref(null);
		const pendingFiles = ref([]), copying = ref(""), deletingFile = ref(null), deleteGroups = ref([]), deleteTypes = ref([]), moveParent = ref(""), moveIdentity = ref("");
		const histories = ref([]), historyPreview = ref(null), references = ref({}), linkedIndex = ref(0);
		const stagedFiles = /* @__PURE__ */ new Map();
		let request = 0, historyRequest = 0, previewRequest = 0, observer, searchTimer, original = "", context = "";
		const scope = computed(() => `tactic_stream.knowledge.${props.login}.${props.project}`);
		const narrow = computed(() => width.value < 720), single = computed(() => narrow.value || !navigationExpanded.value);
		const pageWidth = computed(() => width.value - 16 - (single.value ? 0 : 17 + Math.min(310, (width.value - 16) * .34)));
		const articleNarrow = computed(() => pageWidth.value < 720);
		const creating = computed(() => identity.value.startsWith("local:"));
		const dirty = computed(() => editing.value && JSON.stringify(document.value) !== original);
		const shown = computed(() => historyPreview.value?.document || document.value);
		const html = computed(() => articleHtml(shown.value?.contentMarkdown || "", props.project));
		const toc = computed(() => {
			return [...documentElement(html.value).querySelectorAll("h1,h2,h3,h4,h5,h6")].map((node) => ({
				title: node.textContent,
				level: Number(node.tagName[1]),
				id: node.id
			}));
		});
		const minutes = computed(() => Math.max(1, Math.ceil((shown.value?.contentText || plainText(shown.value?.contentMarkdown)).trim().split(/\s+/).filter(Boolean).length / 200)));
		const entries = computed(() => {
			const rows = new Map(catalog.value.map((row) => [row.identity, row]));
			for (const [id, draft] of Object.entries(drafts)) if (!query.value || `${draft.document.title}\n${draft.document.description}\n${draft.document.contentMarkdown}`.toLowerCase().includes(query.value.toLowerCase())) rows.set(id, {
				identity: id,
				title: draft.document.title || t("Untitled article"),
				description: draft.document.description,
				parentCode: draft.document.parentCode,
				kind: draft.document.kind,
				sortOrder: draft.document.sortOrder || 0,
				draft: draft.document.draft,
				localDraft: true
			});
			const values = [...rows.values()], result = [], seen = /* @__PURE__ */ new Set();
			function append(parent, depth) {
				for (const row of values.filter((row) => row.parentCode === parent).sort(compare)) {
					if (seen.has(row.identity)) continue;
					seen.add(row.identity);
					const children = values.some((child) => child.parentCode === row.identity);
					result.push({
						...row,
						depth,
						hasChildren: children,
						expanded: !collapsed.has(row.identity)
					});
					if (children && !collapsed.has(row.identity)) append(row.identity, depth + 1);
				}
			}
			append("", 0);
			for (const row of values) if (!seen.has(row.identity) && !values.some((parent) => parent.identity === row.parentCode)) {
				result.push({
					...row,
					depth: 0,
					hasChildren: false
				});
				seen.add(row.identity);
			}
			return result;
		});
		const sectionEntries = computed(() => {
			const result = [], seen = /* @__PURE__ */ new Set();
			function append(parent, level) {
				for (const row of catalog.value.filter((row) => row.parentCode === parent).sort(compare)) {
					if (seen.has(row.identity)) continue;
					seen.add(row.identity);
					result.push({
						...row,
						level
					});
					append(row.identity, level + 1);
				}
			}
			append(identity.value, 1);
			return result;
		});
		const parentTitle = computed(() => catalog.value.find((row) => row.identity === document.value?.parentCode)?.title || t("Knowledge Base root"));
		const sectionOptions = computed(() => [{
			value: "",
			label: t("Knowledge Base root")
		}, ...catalog.value.filter((row) => row.kind === "section").map((row) => ({
			value: row.identity,
			label: row.title
		}))]);
		const linked = computed(() => document.value?.linkedSearchKeys || []);
		const linkedObject = computed(() => references.value[linked.value[linkedIndex.value]]);
		const resourceKeys = computed(() => [.../* @__PURE__ */ new Set([...linked.value, ...extractSkeys(shown.value?.contentMarkdown || "")])]);
		const clipboardAvailable = !!navigator.clipboard?.read;
		function documentElement(text) {
			const root = window.document.createElement("div");
			root.innerHTML = text;
			return root;
		}
		function compare(a, b) {
			return a.sortOrder - b.sortOrder || Number(a.kind !== "section") - Number(b.kind !== "section") || a.title.localeCompare(b.title);
		}
		function storeDrafts() {
			try {
				localStorage.setItem(scope.value, JSON.stringify(drafts));
				storageError.value = false;
				return true;
			} catch {
				storageError.value = true;
				error.value = t("Local drafts could not be saved. Keep this page open and save to the server.");
				return false;
			}
		}
		function checkpoint() {
			if (identity.value && scope.value === context) try {
				localStorage.setItem(scope.value + ".state", JSON.stringify({
					identity: identity.value,
					navigationExpanded: navigationExpanded.value,
					tocVisible: tocVisible.value,
					collapsed: [...collapsed]
				}));
			} catch {
				storageError.value = true;
			}
			if (!editing.value || !document.value || !identity.value) return;
			if (dirty.value || creating.value) drafts[identity.value] = {
				document: JSON.parse(JSON.stringify(document.value)),
				revision: revision.value,
				searchKey: searchKey.value,
				step: step.value,
				attachments: files.value,
				metadata: metadata.value
			};
			storeDrafts();
		}
		function clearPage(forget = false) {
			if (forget) {
				try {
					localStorage.removeItem(scope.value + ".state");
				} catch {
					storageError.value = true;
				}
				emit("location", "");
			}
			document.value = null;
			identity.value = "";
			selected.value = "";
			searchKey.value = "";
			revision.value = "";
			editing.value = false;
			files.value = [];
			histories.value = [];
			historyPreview.value = null;
			navigationPage.value = true;
		}
		function applyCommon(result) {
			initialized.value = result.initialized;
			canEdit.value = result.canEdit;
			canInitialize.value = result.canInitialize;
			if (result.catalog) catalog.value = result.catalog;
			if (result.catalogRevision) catalogRevision.value = result.catalogRevision;
		}
		function applyPage(result, edit = false) {
			applyCommon(result);
			if (result.entryMissing) {
				clearPage(true);
				error.value = t("This page is no longer available.");
				return;
			}
			document.value = result.document;
			identity.value = selected.value = result.identity;
			searchKey.value = result.searchKey;
			revision.value = result.revision;
			metadata.value = result.articleMetadata || {};
			files.value = result.attachments || [];
			if (searchKey.value) emit("location", searchKey.value);
			original = JSON.stringify(document.value);
			editing.value = edit;
			step.value = 1;
			expandedMetadata.value = false;
			navigationPage.value = false;
			historyPreview.value = null;
			histories.value = [];
			resourcesVisible.value = false;
			linkedIndex.value = 0;
		}
		async function call(action, values = {}) {
			return knowledgeRequest(action, props.ticket, props.project, values);
		}
		function fail(reason) {
			error.value = t(reason.message);
			if (reason.code === "authentication_failed") emit("session-expired");
		}
		async function reload() {
			if (saving.value || organization.value || !props.ticket || !props.project) return;
			checkpoint();
			const id = ++request;
			loading.value = true;
			error.value = "";
			try {
				const result = await call("list", { query: query.value });
				if (id !== request) return;
				applyCommon(result);
				loaded.value = true;
				if (!identity.value) {
					const state = JSON.parse(localStorage.getItem(scope.value + ".state") || "{}");
					if (state.identity) await select(state.identity);
				}
			} catch (reason) {
				if (id === request) fail(reason);
			} finally {
				if (id === request) loading.value = false;
			}
		}
		async function select(id) {
			if (saving.value) return;
			checkpoint();
			stagedFiles.set(identity.value, pendingFiles.value);
			pendingFiles.value = stagedFiles.get(id) || [];
			selected.value = id;
			navigationPage.value = false;
			const turn = ++request;
			loading.value = true;
			error.value = "";
			const draft = drafts[id];
			if (draft) {
				document.value = JSON.parse(JSON.stringify(draft.document));
				identity.value = id;
				searchKey.value = draft.searchKey;
				revision.value = draft.revision;
				files.value = draft.attachments || [];
				metadata.value = draft.metadata || {};
				editing.value = true;
				step.value = draft.step || 0;
				expandedMetadata.value = step.value === 0 || document.value.kind === "section";
				original = "";
				historyPreview.value = null;
				loading.value = false;
				emit("location", searchKey.value || "");
				return;
			}
			try {
				const result = await call("load", {
					identity: id,
					query: query.value
				});
				if (turn !== request) return;
				if (drafts[result.identity]) {
					applyCommon(result);
					await select(result.identity);
				} else applyPage(result);
			} catch (reason) {
				if (turn === request) fail(reason);
			} finally {
				if (turn === request) loading.value = false;
			}
		}
		function create(kind) {
			if (saving.value || organization.value) return;
			checkpoint();
			stagedFiles.set(identity.value, pendingFiles.value);
			pendingFiles.value = [];
			request++;
			const parent = document.value?.kind === "section" ? identity.value : document.value?.parentCode || "";
			identity.value = selected.value = "local:" + randomId();
			searchKey.value = "";
			revision.value = "";
			metadata.value = {};
			files.value = [];
			document.value = {
				title: "",
				description: "",
				kind,
				parentCode: parent.startsWith("local:") ? "" : parent,
				contentMarkdown: "",
				contentText: "",
				linkedSearchKeys: [],
				sortOrder: 0,
				draft: true
			};
			original = "";
			editing.value = true;
			step.value = 0;
			expandedMetadata.value = true;
			navigationPage.value = false;
			attachmentsVisible.value = false;
			historyPreview.value = null;
			error.value = "";
			checkpoint();
			emit("location", "");
		}
		function beginEdit() {
			if (organization.value) return;
			editing.value = true;
			expandedMetadata.value = document.value.kind === "section";
			step.value = 1;
			original = JSON.stringify(document.value);
		}
		async function save(draft = false, reserve = false) {
			if (saving.value || !document.value) return false;
			if (!document.value.title.trim()) {
				error.value = t("Enter a title");
				expandedMetadata.value = true;
				step.value = 0;
				return false;
			}
			const current = identity.value, turn = request, ticket = props.ticket, project = props.project;
			const values = JSON.parse(JSON.stringify(document.value));
			values.contentText = plainText(values.contentMarkdown);
			saving.value = true;
			error.value = "";
			checkpoint();
			try {
				const result = await knowledgeRequest(reserve ? "reserve" : draft ? "save_draft" : "save", ticket, project, {
					identity: creating.value ? "" : current,
					expected_revision: revision.value,
					document: values
				});
				if (turn !== request || ticket !== props.ticket || project !== props.project) return false;
				delete drafts[current];
				storeDrafts();
				applyPage(result, draft || reserve);
				emit("changed");
				return true;
			} catch (reason) {
				if (turn === request) fail(reason);
				return false;
			} finally {
				saving.value = false;
			}
		}
		async function discard() {
			const id = identity.value;
			delete drafts[id];
			storeDrafts();
			if (creating.value) {
				clearPage(true);
				return;
			}
			editing.value = false;
			await select(id);
		}
		function search() {
			if (organization.value || saving.value) return;
			clearTimeout(searchTimer);
			searchTimer = setTimeout(reload, 220);
		}
		function move(source, target, placement = "inside") {
			if (!canEdit.value || saving.value || editing.value || creating.value) return;
			const rows = JSON.parse(JSON.stringify(catalog.value)), item = rows.find((row) => row.identity === source), to = rows.find((row) => row.identity === target);
			if (!item || !to || item === to) return;
			const parent = placement === "inside" ? to.identity : to.parentCode;
			if (placement === "inside" && to.kind !== "section") return;
			let ancestor = parent;
			const seen = /* @__PURE__ */ new Set([source]);
			while (ancestor) {
				if (seen.has(ancestor)) {
					error.value = t("A section cannot be moved inside its child");
					return;
				}
				seen.add(ancestor);
				ancestor = rows.find((row) => row.identity === ancestor)?.parentCode || "";
			}
			organization.value ||= JSON.parse(JSON.stringify(catalog.value));
			item.parentCode = parent;
			const siblings = rows.filter((row) => row.parentCode === parent && row.identity !== source).sort(compare);
			const index = placement === "inside" ? siblings.length : siblings.findIndex((row) => row.identity === target) + (placement === "after" ? 1 : 0);
			siblings.splice(Math.max(0, index), 0, item);
			siblings.forEach((row, index) => {
				row.sortOrder = index;
			});
			catalog.value = rows;
			dropTarget.value = "";
			if (document.value && identity.value === source) document.value.parentCode = parent;
		}
		function drop(event, row) {
			event.preventDefault();
			const box = event.currentTarget.getBoundingClientRect(), point = (event.clientY - box.top) / box.height;
			move(dragging.value, row.identity, point < .34 ? "before" : point > .66 ? "after" : row.kind === "section" ? "inside" : "after");
			dragging.value = "";
			dropTarget.value = "";
		}
		function reorder(id, direction) {
			const item = catalog.value.find((row) => row.identity === id), siblings = catalog.value.filter((row) => row.parentCode === item.parentCode).sort(compare), target = siblings[siblings.indexOf(item) + direction];
			if (target) move(id, target.identity, direction < 0 ? "before" : "after");
		}
		async function saveOrder() {
			if (!organization.value || saving.value) return;
			saving.value = true;
			error.value = "";
			try {
				applyCommon(await call("organize", {
					organization: catalog.value.map(({ identity, parentCode, sortOrder }) => ({
						identity,
						parentCode,
						sortOrder
					})),
					expected_revision: catalogRevision.value
				}));
				organization.value = null;
				emit("changed");
			} catch (reason) {
				fail(reason);
			} finally {
				saving.value = false;
			}
		}
		function undoOrder() {
			catalog.value = organization.value;
			organization.value = null;
			if (document.value) document.value.parentCode = catalog.value.find((row) => row.identity === identity.value)?.parentCode || "";
		}
		function openMove(id) {
			moveIdentity.value = id;
			moveParent.value = catalog.value.find((row) => row.identity === id)?.parentCode || "";
			moveDialog.value.showModal();
		}
		function applyMove() {
			if (moveParent.value) move(moveIdentity.value, moveParent.value, "inside");
			else {
				const root = catalog.value.find((row) => !row.parentCode && row.identity !== moveIdentity.value);
				if (root) move(moveIdentity.value, root.identity, "after");
				else {
					organization.value ||= JSON.parse(JSON.stringify(catalog.value));
					catalog.value = catalog.value.map((row) => row.identity === moveIdentity.value ? {
						...row,
						parentCode: ""
					} : row);
				}
			}
			moveDialog.value.close();
		}
		async function initialize() {
			confirmation.value.close();
			saving.value = true;
			error.value = "";
			try {
				applyCommon(await call("initialize"));
				loaded.value = true;
			} catch (reason) {
				fail(reason);
			} finally {
				saving.value = false;
			}
		}
		async function history(event) {
			if (!event.target.open) return;
			histories.value = [];
			const id = ++historyRequest;
			try {
				const result = await call("history", { identity: identity.value });
				if (id === historyRequest) histories.value = result.history;
			} catch (reason) {
				if (id === historyRequest) fail(reason);
			}
		}
		async function previewHistory(id) {
			const current = identity.value, turn = ++historyRequest;
			try {
				const result = await call("history_revision", {
					identity: current,
					history_revision: id
				});
				if (current === identity.value && turn === historyRequest) {
					historyPreview.value = result.historyRevision;
					historyDialog.value.close();
				}
			} catch (reason) {
				if (turn === historyRequest) fail(reason);
			}
		}
		async function addFiles(selectedFiles) {
			if (!canEdit.value || saving.value || !selectedFiles.length) return;
			pendingFiles.value.push(...selectedFiles.map((file) => ({
				file,
				status: "ready",
				error: ""
			})));
			attachmentsVisible.value = true;
			if (creating.value && !await save(true, true)) return;
			await uploadPending();
		}
		async function uploadPending() {
			if (saving.value || creating.value) return;
			const current = identity.value, project = props.project, ticket = props.ticket;
			saving.value = true;
			try {
				for (const entry of pendingFiles.value.filter((entry) => entry.status !== "done")) {
					entry.status = "uploading";
					entry.error = "";
					try {
						const result = await messageFileRequest(ticket, project, { identity: current }, entry.file, "knowledge");
						entry.status = "done";
						if (identity.value === current && project === props.project) files.value = result.attachments || [];
					} catch (reason) {
						entry.status = "failed";
						entry.error = reason.message;
					}
				}
				checkpoint();
			} finally {
				saving.value = false;
			}
		}
		async function pasteImage() {
			try {
				const items = await navigator.clipboard.read();
				const selected = [];
				for (const item of items) {
					const type = item.types.find((type) => type.startsWith("image/"));
					if (type) selected.push(new File([await item.getType(type)], "clipboard.png", { type }));
				}
				await addFiles(selected);
			} catch (reason) {
				fail(reason);
			}
		}
		function confirmFile(file) {
			deletingFile.value = file;
			deletion.value.showModal();
		}
		async function removeFile() {
			const file = deletingFile.value;
			deletion.value.close();
			saving.value = true;
			try {
				const result = await call("delete_attachment", {
					identity: identity.value,
					attachment_key: file.snapshotKey
				});
				files.value = result.attachments || [];
				checkpoint();
			} catch (reason) {
				fail(reason);
			} finally {
				saving.value = false;
			}
		}
		async function copy(value, token = "") {
			try {
				await copyText(value);
				copying.value = token;
			} catch (reason) {
				fail(reason);
			}
		}
		async function openDeletion() {
			if (creating.value) {
				await discard();
				return;
			}
			deleteGroups.value = [];
			deleteTypes.value = [];
			deletingFile.value = null;
			deletion.value.showModal();
			loading.value = true;
			try {
				const result = await call("deletion", { identity: identity.value });
				deleteGroups.value = result.groups;
				deleteTypes.value = result.groups.filter((row) => row.selected).map((row) => row.search_type);
			} catch (reason) {
				fail(reason);
				deletion.value.close();
			} finally {
				loading.value = false;
			}
		}
		async function deletePage() {
			saving.value = true;
			error.value = "";
			try {
				applyCommon(await call("delete", {
					identity: identity.value,
					expected_revision: revision.value,
					related_types: deleteTypes.value
				}));
				delete drafts[identity.value];
				storeDrafts();
				deletion.value.close();
				clearPage(true);
				emit("changed");
			} catch (reason) {
				fail(reason);
			} finally {
				saving.value = false;
			}
		}
		function linkSelection() {
			const keys = (props.selection || []).map((row) => "skey://" + row.__search_key__.replace(/^skey:\/\//, ""));
			document.value.linkedSearchKeys = [.../* @__PURE__ */ new Set([...linked.value, ...keys])].slice(0, 128);
			checkpoint();
		}
		function unlink() {
			document.value.linkedSearchKeys = linked.value.filter((_, index) => index !== linkedIndex.value);
			linkedIndex.value = Math.max(0, linkedIndex.value - 1);
			checkpoint();
		}
		async function loadReferences() {
			const turn = ++previewRequest, keys = resourceKeys.value;
			try {
				const result = await linkPreviews(props.ticket, props.project, keys);
				if (turn === previewRequest) references.value = Object.fromEntries(result.previews.map((row) => [row.searchKey, row]));
			} catch (reason) {
				if (turn === previewRequest) fail(reason);
			}
		}
		function activate(event) {
			const anchor = event.target.closest("a"), image = event.target.closest("img");
			if (anchor) {
				const link = anchor.dataset.link || anchor.getAttribute("href");
				if (link?.startsWith("#")) {
					event.preventDefault();
					viewer.value?.querySelector("#" + CSS.escape(link.slice(1)))?.scrollIntoView({ block: "start" });
					return;
				}
				if (/^(skey|tactic-search):/i.test(link) && !event.ctrlKey && !event.metaKey) {
					event.preventDefault();
					openLink(link);
				}
			} else if (image) window.open(image.dataset.original || image.src, "_blank", "noopener");
		}
		function openLink(value) {
			if (openObjectTab) openObjectTab(value, props.project);
			else emit("open-link", value);
		}
		function imageError(event) {
			const image = event.target;
			if (image.tagName !== "IMG") return;
			const file = files.value.find((file) => file.webUrl === (image.dataset.original || image.getAttribute("src")));
			if (file && file.previewUrl !== file.webUrl && image.src !== new URL(file.previewUrl, location.href).href) {
				image.dataset.original = file.webUrl;
				image.src = file.previewUrl;
			}
		}
		function openFile(file) {
			window.open(file.webUrl, "_blank", "noopener");
		}
		function scrollHeading(id) {
			viewer.value?.querySelector("#" + CSS.escape(id))?.scrollIntoView({ block: "start" });
		}
		function date(value) {
			const stamp = messageDate(value);
			return Number.isNaN(stamp.getTime()) ? "" : stamp.toLocaleString(appearance.language);
		}
		function beforeUnload(event) {
			checkpoint();
			if (saving.value || storageError.value && dirty.value || organization.value) {
				event.preventDefault();
				event.returnValue = "";
			}
		}
		function canLeave() {
			checkpoint();
			if (saving.value || organization.value || storageError.value && dirty.value) {
				error.value = t("Finish the current operation or save/discard order changes before leaving.");
				return false;
			}
			return true;
		}
		watch(document, checkpoint, { deep: true });
		watch(resourceKeys, () => {
			references.value = {};
			if (resourceKeys.value.length) loadReferences();
		});
		watch(() => [
			props.ticket,
			props.project,
			props.login
		], () => {
			request++;
			historyRequest++;
			previewRequest++;
			clearTimeout(searchTimer);
			context = scope.value;
			clearPage();
			catalog.value = [];
			query.value = "";
			organization.value = null;
			pendingFiles.value = [];
			stagedFiles.clear();
			loaded.value = false;
			for (const id of Object.keys(drafts)) delete drafts[id];
			try {
				const state = JSON.parse(localStorage.getItem(context + ".state") || "{}");
				navigationExpanded.value = state.navigationExpanded !== false;
				tocVisible.value = state.tocVisible !== false;
				collapsed.clear();
				for (const id of state.collapsed || []) collapsed.add(id);
				const saved = JSON.parse(localStorage.getItem(context) || "{}");
				for (const [id, entry] of Object.entries(saved)) if (entry?.document && typeof entry.document.title === "string" && typeof entry.document.contentMarkdown === "string") drafts[id] = entry;
			} catch {
				error.value = t("Local drafts could not be restored.");
			}
			if (props.active) reload();
		}, { immediate: true });
		watch(() => props.active, (value) => {
			if (value && !loaded.value) reload();
			else if (!value) checkpoint();
		});
		watch(() => [props.target, props.project], ([value, project]) => {
			if (!value) return;
			try {
				const address = new URL(value);
				if ((address.searchParams.get("project") || project) === project) select(address.searchParams.get("id") || address.searchParams.get("code"));
			} catch {
				fail(new Error(t("Invalid TACTIC link")));
			}
		}, { immediate: true });
		onMounted(() => {
			observer = new ResizeObserver((entries) => {
				width.value = entries[0].contentRect.width;
			});
			observer.observe(host.value);
			window.addEventListener("beforeunload", beforeUnload);
		});
		onBeforeUnmount(() => {
			checkpoint();
			request++;
			historyRequest++;
			previewRequest++;
			observer?.disconnect();
			clearTimeout(searchTimer);
			window.removeEventListener("beforeunload", beforeUnload);
		});
		__expose({
			open: select,
			reload,
			canLeave
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				ref_key: "host",
				ref: host,
				class: normalizeClass(["knowledge-base", {
					narrow: narrow.value,
					single: single.value
				}])
			}, [
				createBaseVNode("header", _hoisted_1, [
					createVNode(_sfc_main$3, { name: "book-open" }),
					createBaseVNode("h2", null, toDisplayString(unref(t)("Knowledge Base")), 1),
					initialized.value && !narrow.value ? (openBlock(), createBlock(_sfc_main$2, {
						key: 0,
						"icon-only": "",
						icon: navigationExpanded.value ? "previous" : "next",
						label: navigationExpanded.value ? "Hide article navigation" : "Show article navigation",
						onClick: _cache[0] || (_cache[0] = ($event) => navigationExpanded.value = !navigationExpanded.value)
					}, null, 8, ["icon", "label"])) : createCommentVNode("", true),
					organization.value ? (openBlock(), createElementBlock(Fragment, { key: 1 }, [createVNode(_sfc_main$2, {
						icon: "save",
						label: "Save order",
						highlighted: "",
						disabled: saving.value,
						onClick: saveOrder
					}, null, 8, ["disabled"]), createVNode(_sfc_main$2, {
						"icon-only": "",
						icon: "undo",
						label: "Discard order changes",
						disabled: saving.value,
						onClick: undoOrder
					}, null, 8, ["disabled"])], 64)) : createCommentVNode("", true),
					initialized.value && canEdit.value ? (openBlock(), createElementBlock(Fragment, { key: 2 }, [createVNode(_sfc_main$2, {
						"icon-only": "",
						icon: "create-article",
						label: "Create article",
						disabled: saving.value || !!organization.value,
						onClick: _cache[1] || (_cache[1] = ($event) => create("article"))
					}, null, 8, ["disabled"]), createVNode(_sfc_main$2, {
						"icon-only": "",
						icon: "folder-plus",
						label: "Create section",
						disabled: saving.value || !!organization.value,
						onClick: _cache[2] || (_cache[2] = ($event) => create("section"))
					}, null, 8, ["disabled"])], 64)) : createCommentVNode("", true),
					createVNode(_sfc_main$2, {
						"icon-only": "",
						icon: "refresh",
						label: "Reload articles",
						disabled: loading.value || saving.value || !!organization.value,
						onClick: reload
					}, null, 8, ["disabled"])
				]),
				error.value ? (openBlock(), createElementBlock("div", _hoisted_2, [
					createVNode(_sfc_main$3, { name: "exclamation-circle" }),
					createBaseVNode("span", null, toDisplayString(error.value), 1),
					createVNode(_sfc_main$2, {
						"icon-only": "",
						icon: "close",
						label: "Dismiss error",
						onClick: _cache[3] || (_cache[3] = ($event) => error.value = "")
					})
				])) : createCommentVNode("", true),
				!initialized.value ? (openBlock(), createElementBlock("div", _hoisted_3, [
					createVNode(_sfc_main$3, { name: "book-open" }),
					createBaseVNode("h3", null, toDisplayString(unref(t)("Knowledge Base is not initialized")), 1),
					createBaseVNode("p", null, toDisplayString(unref(t)("An administrator must initialize project articles and collaboration metadata.")), 1),
					canInitialize.value ? (openBlock(), createBlock(_sfc_main$2, {
						key: 0,
						label: "Initialize Knowledge Base",
						icon: "plus",
						disabled: saving.value || loading.value,
						onClick: _cache[4] || (_cache[4] = ($event) => confirmation.value.showModal())
					}, null, 8, ["disabled"])) : createCommentVNode("", true)
				])) : (openBlock(), createElementBlock("div", _hoisted_4, [withDirectives(createBaseVNode("nav", {
					class: "knowledge-navigation",
					"aria-label": unref(t)("Articles")
				}, [createVNode(AppSearchField_default, {
					modelValue: query.value,
					"onUpdate:modelValue": [_cache[5] || (_cache[5] = ($event) => query.value = $event), search],
					class: "knowledge-search",
					label: "Search sections and articles",
					placeholder: unref(t)("Search sections and articles"),
					disabled: saving.value || !!organization.value,
					onSearch: reload
				}, null, 8, [
					"modelValue",
					"placeholder",
					"disabled"
				]), createBaseVNode("div", _hoisted_6, [(openBlock(true), createElementBlock(Fragment, null, renderList(entries.value, (row) => {
					return openBlock(), createElementBlock("div", {
						key: row.identity,
						class: normalizeClass(["knowledge-tree-row", {
							selected: row.identity === selected.value,
							drop: dropTarget.value === row.identity,
							section: row.kind === "section"
						}]),
						style: normalizeStyle({ "--depth": row.depth }),
						role: "treeitem",
						"aria-selected": row.identity === selected.value,
						"aria-expanded": row.hasChildren ? row.expanded : void 0,
						"data-knowledge-entry": row.identity,
						draggable: canEdit.value && !editing.value && !row.localDraft,
						onDragstart: ($event) => dragging.value = row.identity,
						onDragover: withModifiers(($event) => dropTarget.value = row.identity, ["prevent"]),
						onDragleave: _cache[6] || (_cache[6] = ($event) => dropTarget.value = ""),
						onDrop: ($event) => drop($event, row),
						onDragend: _cache[7] || (_cache[7] = ($event) => {
							dragging.value = "";
							dropTarget.value = "";
						})
					}, [
						createBaseVNode("span", _hoisted_8, [row.hasChildren ? (openBlock(), createBlock(_sfc_main$2, {
							key: 0,
							"icon-only": "",
							icon: row.expanded ? "chevron-down" : "next",
							label: row.expanded ? "Collapse section" : "Expand section",
							onClick: ($event) => collapsed.has(row.identity) ? collapsed.delete(row.identity) : collapsed.add(row.identity)
						}, null, 8, [
							"icon",
							"label",
							"onClick"
						])) : createCommentVNode("", true)]),
						createVNode(_sfc_main$2, {
							class: "knowledge-page-link",
							label: row.title,
							onClick: ($event) => select(row.identity)
						}, {
							default: withCtx(() => [createVNode(_sfc_main$3, { name: row.kind === "section" ? row.expanded ? "folder-open" : "folder" : "file" }, null, 8, ["name"]), createBaseVNode("span", null, [
								createBaseVNode("strong", null, toDisplayString(row.title), 1),
								(row.kind === "section" ? row.description : query.value && row.excerpt) ? (openBlock(), createElementBlock("small", _hoisted_9, toDisplayString(row.kind === "section" ? row.description : row.excerpt), 1)) : createCommentVNode("", true),
								row.localDraft || row.draft ? (openBlock(), createElementBlock("small", _hoisted_10, toDisplayString(unref(t)(row.localDraft ? "Local draft" : "Draft")), 1)) : createCommentVNode("", true)
							])]),
							_: 2
						}, 1032, ["label", "onClick"]),
						canEdit.value && !row.localDraft ? (openBlock(), createBlock(_sfc_main$7, {
							key: 0,
							class: "knowledge-row-menu",
							label: "Organize page",
							overlay: "",
							width: 220
						}, {
							default: withCtx(() => [
								createVNode(_sfc_main$10, {
									label: "Move up",
									icon: "arrow-up",
									disabled: editing.value || saving.value,
									onClick: ($event) => reorder(row.identity, -1)
								}, null, 8, ["disabled", "onClick"]),
								createVNode(_sfc_main$10, {
									label: "Move down",
									icon: "arrow-down",
									disabled: editing.value || saving.value,
									onClick: ($event) => reorder(row.identity, 1)
								}, null, 8, ["disabled", "onClick"]),
								createVNode(_sfc_main$10, {
									label: "Move to section",
									icon: "folder",
									disabled: editing.value || saving.value,
									onClick: ($event) => openMove(row.identity)
								}, null, 8, ["disabled", "onClick"])
							]),
							_: 2
						}, 1024)) : createCommentVNode("", true)
					], 46, _hoisted_7);
				}), 128)), !entries.value.length && !loading.value ? (openBlock(), createElementBlock("p", _hoisted_11, toDisplayString(unref(t)(query.value ? "No matching articles" : "No articles yet")), 1)) : createCommentVNode("", true)])], 8, _hoisted_5), [[vShow, !single.value || navigationPage.value]]), withDirectives(createBaseVNode("main", { class: normalizeClass(["knowledge-page", { "article-narrow": articleNarrow.value }]) }, [loading.value ? (openBlock(), createElementBlock("div", _hoisted_12, toDisplayString(unref(t)("Loading…")), 1)) : !document.value ? (openBlock(), createElementBlock("div", _hoisted_13, [
					createVNode(_sfc_main$3, { name: "file" }),
					createBaseVNode("h3", null, toDisplayString(unref(t)("Choose an article")), 1),
					createBaseVNode("p", null, toDisplayString(unref(t)("Sections, full-text search, files, and object links stay together here.")), 1)
				])) : editing.value ? (openBlock(), createElementBlock(Fragment, { key: 2 }, [
					createBaseVNode("header", _hoisted_14, [
						single.value ? (openBlock(), createBlock(_sfc_main$2, {
							key: 0,
							"icon-only": "",
							icon: "previous",
							label: "Back to articles",
							onClick: _cache[8] || (_cache[8] = ($event) => {
								checkpoint();
								navigationPage.value = true;
							})
						})) : createCommentVNode("", true),
						createVNode(_sfc_main$3, { name: document.value.kind === "article" ? "file" : "folder" }, null, 8, ["name"]),
						createBaseVNode("h3", null, toDisplayString(unref(t)(document.value.kind === "article" ? "Edit article" : "Edit section")), 1),
						creating.value && document.value.kind === "article" ? (openBlock(), createElementBlock("small", _hoisted_15, toDisplayString(unref(t)("Step {step} of 2", { step: step.value + 1 })), 1)) : createCommentVNode("", true),
						!creating.value && document.value.kind === "article" ? (openBlock(), createBlock(_sfc_main$2, {
							key: 2,
							"icon-only": "",
							icon: expandedMetadata.value ? "chevron-up" : "chevron-down",
							label: expandedMetadata.value ? "Hide title and summary" : "Show title and summary",
							onClick: _cache[9] || (_cache[9] = ($event) => expandedMetadata.value = !expandedMetadata.value)
						}, null, 8, ["icon", "label"])) : createCommentVNode("", true),
						__props.selection?.length && document.value.kind === "article" ? (openBlock(), createBlock(_sfc_main$2, {
							key: 3,
							"icon-only": "",
							icon: "link",
							label: "Link selected objects to article",
							onClick: linkSelection
						})) : createCommentVNode("", true),
						createVNode(_sfc_main$2, {
							label: "Cancel",
							icon: "close",
							"icon-only": pageWidth.value < 1180,
							disabled: saving.value,
							onClick: discard
						}, null, 8, ["icon-only", "disabled"]),
						!creating.value ? (openBlock(), createBlock(_sfc_main$2, {
							key: 4,
							label: document.value.kind === "article" ? "Delete article" : "Delete section",
							icon: "delete",
							destructive: "",
							"icon-only": pageWidth.value < 1180,
							disabled: saving.value || !!organization.value,
							onClick: openDeletion
						}, null, 8, [
							"label",
							"icon-only",
							"disabled"
						])) : createCommentVNode("", true),
						document.value.kind === "article" && (creating.value || document.value.draft) ? (openBlock(), createBlock(_sfc_main$2, {
							key: 5,
							label: "Save as draft",
							icon: "save",
							"icon-only": narrow.value,
							disabled: saving.value,
							onClick: _cache[10] || (_cache[10] = ($event) => save(true))
						}, null, 8, ["icon-only", "disabled"])) : createCommentVNode("", true),
						createVNode(_sfc_main$2, {
							label: creating.value || document.value.draft ? "Publish" : "Save",
							icon: "save",
							highlighted: "",
							"icon-only": narrow.value,
							disabled: saving.value || !dirty.value && !document.value.draft,
							onClick: _cache[11] || (_cache[11] = ($event) => save())
						}, null, 8, [
							"label",
							"icon-only",
							"disabled"
						])
					]),
					creating.value && step.value === 0 ? (openBlock(), createElementBlock("div", _hoisted_16, [createVNode(_sfc_main$3, { name: "folder" }), createBaseVNode("span", null, [createBaseVNode("small", null, toDisplayString(unref(t)("Parent section")), 1), createTextVNode(toDisplayString(parentTitle.value), 1)])])) : createCommentVNode("", true),
					document.value.kind === "section" || creating.value && step.value === 0 || expandedMetadata.value && !creating.value ? (openBlock(), createElementBlock("div", _hoisted_17, [
						createBaseVNode("label", null, [createTextVNode(toDisplayString(unref(t)("Title")), 1), createVNode(_sfc_main$6, {
							modelValue: document.value.title,
							"onUpdate:modelValue": _cache[12] || (_cache[12] = ($event) => document.value.title = $event),
							label: "Title",
							placeholder: "A short, recognizable title",
							disabled: saving.value
						}, null, 8, ["modelValue", "disabled"])]),
						createBaseVNode("label", null, [createTextVNode(toDisplayString(unref(t)("Summary")), 1), createVNode(_sfc_main$9, {
							modelValue: document.value.description,
							"onUpdate:modelValue": _cache[13] || (_cache[13] = ($event) => document.value.description = $event),
							label: "Summary",
							placeholder: "What this page is about",
							disabled: saving.value
						}, null, 8, ["modelValue", "disabled"])]),
						document.value.kind === "section" ? (openBlock(), createElementBlock("label", _hoisted_18, [createTextVNode(toDisplayString(unref(t)("Parent section")), 1), createVNode(_sfc_main$4, {
							modelValue: document.value.parentCode,
							"onUpdate:modelValue": _cache[14] || (_cache[14] = ($event) => document.value.parentCode = $event),
							options: sectionOptions.value.filter((row) => row.value !== identity.value),
							label: "Parent section"
						}, null, 8, ["modelValue", "options"])])) : createCommentVNode("", true),
						creating.value && document.value.kind === "article" ? (openBlock(), createBlock(_sfc_main$2, {
							key: 1,
							label: "Continue to content",
							icon: "next",
							disabled: !document.value.title.trim(),
							onClick: _cache[15] || (_cache[15] = ($event) => {
								step.value = 1;
								expandedMetadata.value = false;
								checkpoint();
							})
						}, null, 8, ["disabled"])) : createCommentVNode("", true)
					])) : createCommentVNode("", true),
					document.value.kind === "article" && (!creating.value || step.value === 1) ? (openBlock(), createElementBlock(Fragment, { key: 2 }, [
						creating.value ? (openBlock(), createBlock(_sfc_main$2, {
							key: 0,
							class: "knowledge-back-metadata",
							label: "Back to title and summary",
							icon: "previous",
							onClick: _cache[16] || (_cache[16] = ($event) => step.value = 0)
						})) : createCommentVNode("", true),
						linkedObject.value ? (openBlock(), createElementBlock("div", _hoisted_19, [
							linked.value.length > 1 ? (openBlock(), createBlock(_sfc_main$2, {
								key: 0,
								"icon-only": "",
								icon: "previous",
								label: "Previous linked object",
								onClick: _cache[17] || (_cache[17] = ($event) => linkedIndex.value = (linkedIndex.value + linked.value.length - 1) % linked.value.length)
							})) : createCommentVNode("", true),
							createVNode(_sfc_main$12, {
								preview: linkedObject.value,
								compact: "",
								onOpen: openLink
							}, null, 8, ["preview"]),
							linked.value.length > 1 ? (openBlock(), createBlock(_sfc_main$2, {
								key: 1,
								"icon-only": "",
								icon: "next",
								label: "Next linked object",
								onClick: _cache[18] || (_cache[18] = ($event) => linkedIndex.value = (linkedIndex.value + 1) % linked.value.length)
							})) : createCommentVNode("", true),
							createVNode(_sfc_main$2, {
								"icon-only": "",
								icon: "link-off",
								label: "Unlink object",
								onClick: unlink
							})
						])) : createCommentVNode("", true),
						createVNode(_sfc_main$1, {
							ref_key: "editor",
							ref: editor,
							modelValue: document.value.contentMarkdown,
							"onUpdate:modelValue": _cache[25] || (_cache[25] = ($event) => document.value.contentMarkdown = $event),
							project: __props.project,
							attachments: files.value,
							disabled: saving.value,
							onAttachments: _cache[26] || (_cache[26] = ($event) => attachmentsVisible.value = !attachmentsVisible.value),
							onUpload: addFiles
						}, {
							attachments: withCtx(() => [attachmentsVisible.value ? (openBlock(), createElementBlock("section", _hoisted_20, [
								createBaseVNode("header", null, [
									createVNode(_sfc_main$3, { name: "attachments-editor" }),
									createBaseVNode("div", null, [createBaseVNode("h4", null, toDisplayString(unref(t)("Attached files")), 1), createBaseVNode("p", null, toDisplayString(unref(t)("Files are uploaded and attached before you insert their permanent links into the article.")), 1)]),
									createVNode(_sfc_main$2, {
										"icon-only": "",
										label: "Attach files",
										icon: "attachments-editor",
										disabled: saving.value,
										onClick: _cache[19] || (_cache[19] = ($event) => fileInput.value.click())
									}, null, 8, ["disabled"]),
									createVNode(_sfc_main$2, {
										"icon-only": "",
										icon: "close",
										label: "Hide attached files",
										onClick: _cache[20] || (_cache[20] = ($event) => attachmentsVisible.value = false)
									})
								]),
								createBaseVNode("div", {
									class: "knowledge-staging",
									onDragover: _cache[23] || (_cache[23] = withModifiers(() => {}, ["prevent"])),
									onDrop: _cache[24] || (_cache[24] = withModifiers(($event) => addFiles([...$event.dataTransfer.files]), ["prevent"]))
								}, [createBaseVNode("header", null, [
									createVNode(_sfc_main$3, { name: "attachments-editor" }),
									createBaseVNode("small", null, toDisplayString(unref(t)("Attachments")), 1),
									createVNode(_sfc_main$2, {
										"icon-only": "",
										icon: "content-paste",
										label: "Paste image",
										disabled: saving.value || !clipboardAvailable,
										onClick: pasteImage
									}, null, 8, ["disabled"]),
									pendingFiles.value.length ? (openBlock(), createBlock(_sfc_main$2, {
										key: 0,
										"icon-only": "",
										icon: "close",
										label: "Clear staged files",
										disabled: saving.value,
										onClick: _cache[21] || (_cache[21] = ($event) => pendingFiles.value = [])
									}, null, 8, ["disabled"])) : createCommentVNode("", true)
								]), createVNode(_sfc_main$2, {
									class: "knowledge-stage-empty",
									label: "Drop files here or attach them from disk",
									disabled: saving.value,
									onClick: _cache[22] || (_cache[22] = ($event) => fileInput.value.click())
								}, {
									default: withCtx(() => [createVNode(_sfc_main$3, { name: "attachments-editor" }), createBaseVNode("span", null, toDisplayString(unref(t)("Drop files here or attach them from disk")), 1)]),
									_: 1
								}, 8, ["disabled"])], 32),
								(openBlock(true), createElementBlock(Fragment, null, renderList(pendingFiles.value, (entry, index) => {
									return withDirectives((openBlock(), createElementBlock("div", {
										key: index,
										class: "knowledge-pending"
									}, [
										createBaseVNode("span", null, toDisplayString(entry.file.name) + " · " + toDisplayString(unref(t)(entry.status === "failed" ? "Failed" : entry.status === "uploading" ? "Uploading" : "Ready")), 1),
										entry.error ? (openBlock(), createElementBlock("small", _hoisted_21, toDisplayString(entry.error), 1)) : createCommentVNode("", true),
										entry.status === "failed" ? (openBlock(), createBlock(_sfc_main$2, {
											key: 1,
											"icon-only": "",
											icon: "refresh",
											label: "Retry",
											disabled: saving.value,
											onClick: uploadPending
										}, null, 8, ["disabled"])) : createCommentVNode("", true),
										createVNode(_sfc_main$2, {
											"icon-only": "",
											icon: "close",
											label: "Remove staged file",
											disabled: saving.value,
											onClick: ($event) => pendingFiles.value.splice(index, 1)
										}, null, 8, ["disabled", "onClick"])
									])), [[vShow, entry.status !== "done"]]);
								}), 128)),
								(openBlock(true), createElementBlock(Fragment, null, renderList(files.value, (file) => {
									return openBlock(), createElementBlock("div", {
										key: file.token,
										class: "knowledge-library-file"
									}, [
										createVNode(_sfc_main$13, {
											compact: "",
											"activation-icon": file.isImage ? "image" : "link",
											"activation-label": file.isImage ? "Insert image" : "Insert link",
											title: file.title,
											extension: file.extension,
											"preview-url": file.previewUrl,
											"size-text": String(file.size || 0) + " B",
											onActivated: ($event) => editor.value.insertAttachment(file)
										}, null, 8, [
											"activation-icon",
											"activation-label",
											"title",
											"extension",
											"preview-url",
											"size-text",
											"onActivated"
										]),
										createVNode(_sfc_main$2, {
											"icon-only": "",
											icon: copying.value === file.token ? "check" : "copy",
											label: copying.value === file.token ? "Copied" : "Copy web link",
											onClick: ($event) => copy(file.webUrl, file.token)
										}, null, 8, [
											"icon",
											"label",
											"onClick"
										]),
										createVNode(_sfc_main$2, {
											"icon-only": "",
											icon: "delete",
											label: "Delete file",
											disabled: saving.value,
											onClick: ($event) => confirmFile(file)
										}, null, 8, ["disabled", "onClick"])
									]);
								}), 128)),
								!files.value.length ? (openBlock(), createElementBlock("p", _hoisted_22, toDisplayString(unref(t)("No files uploaded to this article yet.")), 1)) : createCommentVNode("", true)
							])) : createCommentVNode("", true)]),
							_: 1
						}, 8, [
							"modelValue",
							"project",
							"attachments",
							"disabled"
						])
					], 64)) : createCommentVNode("", true)
				], 64)) : (openBlock(), createElementBlock(Fragment, { key: 3 }, [
					createBaseVNode("header", _hoisted_23, [
						single.value ? (openBlock(), createBlock(_sfc_main$2, {
							key: 0,
							"icon-only": "",
							icon: "previous",
							label: "Back to articles",
							onClick: _cache[27] || (_cache[27] = ($event) => navigationPage.value = true)
						})) : createCommentVNode("", true),
						createBaseVNode("div", _hoisted_24, [createVNode(_sfc_main$3, { name: shown.value.kind === "section" ? "folder-open" : "file" }, null, 8, ["name"])]),
						createBaseVNode("div", _hoisted_25, [createBaseVNode("h3", null, toDisplayString(shown.value.title), 1), createBaseVNode("small", null, [createTextVNode(toDisplayString(shown.value.description), 1), shown.value.kind === "article" ? (openBlock(), createElementBlock("span", _hoisted_26, [
							shown.value.description ? (openBlock(), createElementBlock("span", _hoisted_27, " • ")) : createCommentVNode("", true),
							createVNode(_sfc_main$3, { name: "schedule" }),
							createTextVNode(toDisplayString(unref(t)("{minutes} min read", { minutes: minutes.value })), 1)
						])) : createCommentVNode("", true)])]),
						createVNode(_sfc_main$2, {
							"icon-only": "",
							icon: "copy",
							label: "Copy search key",
							onClick: _cache[28] || (_cache[28] = ($event) => copy(searchKey.value))
						}),
						shown.value.kind === "article" ? (openBlock(), createBlock(_sfc_main$7, {
							key: 1,
							ref_key: "historyDialog",
							ref: historyDialog,
							icon: "history",
							label: "Change history",
							overlay: "",
							width: 390,
							"close-on-select": false,
							class: "knowledge-history-menu",
							onToggle: history
						}, {
							default: withCtx(() => [
								createBaseVNode("h4", null, [createVNode(_sfc_main$3, { name: "history" }), createTextVNode(toDisplayString(unref(t)("Change history")), 1)]),
								(openBlock(true), createElementBlock(Fragment, null, renderList(histories.value, (row) => {
									return openBlock(), createBlock(_sfc_main$2, {
										key: row.revisionId,
										icon: "history",
										label: row.title,
										onClick: ($event) => previewHistory(row.revisionId)
									}, {
										default: withCtx(() => [createBaseVNode("span", null, [
											createBaseVNode("strong", null, toDisplayString(row.title), 1),
											createBaseVNode("small", null, toDisplayString(row.actor) + " · " + toDisplayString(date(row.timestamp)), 1),
											createBaseVNode("small", null, toDisplayString(row.changedFields.join(", ")), 1)
										])]),
										_: 2
									}, 1032, ["label", "onClick"]);
								}), 128)),
								!histories.value.length ? (openBlock(), createElementBlock("p", _hoisted_28, toDisplayString(unref(t)("Loading…")), 1)) : createCommentVNode("", true)
							]),
							_: 1
						}, 512)) : createCommentVNode("", true),
						toc.value.length && shown.value.kind === "article" ? (openBlock(), createBlock(_sfc_main$2, {
							key: 2,
							"icon-only": "",
							icon: "list-ul",
							label: tocVisible.value ? "Hide table of contents" : "Show table of contents",
							tonal: tocVisible.value,
							onClick: _cache[29] || (_cache[29] = ($event) => tocVisible.value = !tocVisible.value)
						}, null, 8, ["label", "tonal"])) : createCommentVNode("", true),
						files.value.length || resourceKeys.value.length ? (openBlock(), createBlock(_sfc_main$2, {
							key: 3,
							"icon-only": "",
							icon: "attachments-editor",
							label: resourcesVisible.value ? "Hide linked objects and attached files" : "Show linked objects and attached files",
							tonal: resourcesVisible.value,
							onClick: _cache[30] || (_cache[30] = ($event) => resourcesVisible.value = !resourcesVisible.value)
						}, null, 8, ["label", "tonal"])) : createCommentVNode("", true),
						canEdit.value && !historyPreview.value ? (openBlock(), createElementBlock(Fragment, { key: 4 }, [createVNode(_sfc_main$2, {
							label: shown.value.kind === "article" ? "Delete article" : "Delete section",
							icon: "delete",
							destructive: "",
							"icon-only": articleNarrow.value,
							disabled: saving.value || !!organization.value,
							onClick: openDeletion
						}, null, 8, [
							"label",
							"icon-only",
							"disabled"
						]), createVNode(_sfc_main$2, {
							label: "Edit",
							icon: "edit",
							tonal: "",
							"icon-only": articleNarrow.value,
							onClick: beginEdit
						}, null, 8, ["icon-only"])], 64)) : createCommentVNode("", true)
					]),
					historyPreview.value ? (openBlock(), createElementBlock("div", _hoisted_29, [createBaseVNode("span", null, toDisplayString(unref(t)("Previewing an earlier revision")) + " · " + toDisplayString(historyPreview.value.actor) + " · " + toDisplayString(date(historyPreview.value.timestamp)), 1), createVNode(_sfc_main$2, {
						label: "Return to current article",
						icon: "close",
						onClick: _cache[31] || (_cache[31] = ($event) => historyPreview.value = null)
					})])) : createCommentVNode("", true),
					shown.value.kind === "section" ? (openBlock(), createElementBlock("div", _hoisted_30, [(openBlock(true), createElementBlock(Fragment, null, renderList(sectionEntries.value, (row) => {
						return openBlock(), createBlock(_sfc_main$2, {
							key: row.identity,
							style: normalizeStyle({ paddingLeft: 7 + (row.level - 1) * 18 + "px" }),
							label: row.title,
							onClick: ($event) => select(row.identity)
						}, {
							default: withCtx(() => [createVNode(_sfc_main$3, { name: row.kind === "section" ? "folder-open" : "file" }, null, 8, ["name"]), createBaseVNode("span", null, [createTextVNode(toDisplayString(row.title), 1), row.kind === "section" ? (openBlock(), createElementBlock("small", _hoisted_31, toDisplayString(unref(t)("Section")), 1)) : createCommentVNode("", true)])]),
							_: 2
						}, 1032, [
							"style",
							"label",
							"onClick"
						]);
					}), 128)), !sectionEntries.value.length ? (openBlock(), createElementBlock("p", _hoisted_32, toDisplayString(unref(t)("This section has no pages yet.")), 1)) : createCommentVNode("", true)])) : (openBlock(), createElementBlock("div", {
						key: 2,
						class: normalizeClass(["knowledge-reading", { "side-outline": !articleNarrow.value && tocVisible.value && toc.value.length }])
					}, [createBaseVNode("div", _hoisted_33, [
						linkedObject.value && !historyPreview.value ? (openBlock(), createElementBlock("div", _hoisted_34, [
							linked.value.length > 1 ? (openBlock(), createBlock(_sfc_main$2, {
								key: 0,
								"icon-only": "",
								icon: "previous",
								label: "Previous linked object",
								onClick: _cache[32] || (_cache[32] = ($event) => linkedIndex.value = (linkedIndex.value + linked.value.length - 1) % linked.value.length)
							})) : createCommentVNode("", true),
							createVNode(_sfc_main$12, {
								preview: linkedObject.value,
								compact: "",
								onOpen: openLink
							}, null, 8, ["preview"]),
							linked.value.length > 1 ? (openBlock(), createBlock(_sfc_main$2, {
								key: 1,
								"icon-only": "",
								icon: "next",
								label: "Next linked object",
								onClick: _cache[33] || (_cache[33] = ($event) => linkedIndex.value = (linkedIndex.value + 1) % linked.value.length)
							})) : createCommentVNode("", true)
						])) : createCommentVNode("", true),
						articleNarrow.value && tocVisible.value && toc.value.length ? (openBlock(), createElementBlock("aside", _hoisted_35, [createBaseVNode("h4", null, [createVNode(_sfc_main$3, { name: "list-ul" }), createTextVNode(toDisplayString(unref(t)("On this page")), 1)]), (openBlock(true), createElementBlock(Fragment, null, renderList(toc.value, (heading) => {
							return openBlock(), createBlock(_sfc_main$2, {
								key: heading.id,
								label: heading.title,
								style: normalizeStyle({ paddingLeft: 7 + (heading.level - 1) * 11 + "px" }),
								onClick: ($event) => scrollHeading(heading.id)
							}, {
								default: withCtx(() => [createTextVNode(toDisplayString(heading.title), 1)]),
								_: 2
							}, 1032, [
								"label",
								"style",
								"onClick"
							]);
						}), 128))])) : createCommentVNode("", true),
						createBaseVNode("article", {
							ref_key: "viewer",
							ref: viewer,
							class: "knowledge-document",
							innerHTML: html.value,
							onClick: activate,
							onErrorCapture: imageError
						}, null, 40, _hoisted_36),
						resourcesVisible.value && !historyPreview.value ? (openBlock(), createElementBlock("section", _hoisted_37, [
							createBaseVNode("h4", null, toDisplayString(unref(t)("Linked objects and files")), 1),
							(openBlock(true), createElementBlock(Fragment, null, renderList(resourceKeys.value, (key) => {
								return openBlock(), createBlock(_sfc_main$12, {
									key,
									preview: references.value[key] || {
										searchKey: key,
										status: "loading"
									},
									onOpen: openLink,
									onRetry: loadReferences,
									onCopy: copy
								}, null, 8, ["preview"]);
							}), 128)),
							(openBlock(true), createElementBlock(Fragment, null, renderList(files.value, (file) => {
								return openBlock(), createBlock(_sfc_main$13, {
									key: file.token,
									title: file.title,
									extension: file.extension,
									"preview-url": file.previewUrl,
									"size-text": String(file.size || 0) + " B",
									onActivated: ($event) => openFile(file)
								}, null, 8, [
									"title",
									"extension",
									"preview-url",
									"size-text",
									"onActivated"
								]);
							}), 128))
						])) : createCommentVNode("", true),
						createBaseVNode("footer", _hoisted_38, [
							createBaseVNode("span", null, toDisplayString(unref(t)("Author")) + ": " + toDisplayString((historyPreview.value?.articleMetadata || metadata.value).author), 1),
							createBaseVNode("span", null, toDisplayString(unref(t)("Created")) + ": " + toDisplayString(date((historyPreview.value?.articleMetadata || metadata.value).createdAt)), 1),
							createBaseVNode("span", null, toDisplayString(unref(t)("Updated")) + ": " + toDisplayString(date((historyPreview.value?.articleMetadata || metadata.value).updatedAt)), 1)
						])
					]), !articleNarrow.value && tocVisible.value && toc.value.length ? (openBlock(), createElementBlock("aside", _hoisted_39, [createBaseVNode("h4", null, [createVNode(_sfc_main$3, { name: "list-ul" }), createTextVNode(toDisplayString(unref(t)("On this page")), 1)]), (openBlock(true), createElementBlock(Fragment, null, renderList(toc.value, (heading) => {
						return openBlock(), createBlock(_sfc_main$2, {
							key: heading.id,
							label: heading.title,
							style: normalizeStyle({ paddingLeft: 7 + (heading.level - 1) * 11 + "px" }),
							onClick: ($event) => scrollHeading(heading.id)
						}, {
							default: withCtx(() => [createTextVNode(toDisplayString(heading.title), 1)]),
							_: 2
						}, 1032, [
							"label",
							"style",
							"onClick"
						]);
					}), 128))])) : createCommentVNode("", true)], 2))
				], 64))], 2), [[vShow, !single.value || !navigationPage.value]])])),
				createBaseVNode("input", {
					ref_key: "fileInput",
					ref: fileInput,
					type: "file",
					multiple: "",
					hidden: "",
					onChange: _cache[34] || (_cache[34] = ($event) => {
						addFiles([...$event.target.files]);
						$event.target.value = "";
					})
				}, null, 544),
				createBaseVNode("dialog", {
					ref_key: "confirmation",
					ref: confirmation,
					class: "record-dialog knowledge-initialization",
					"aria-label": unref(t)("Initialize Knowledge Base")
				}, [
					createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)("Initialize Knowledge Base")), 1), createVNode(_sfc_main$2, {
						"icon-only": "",
						icon: "close",
						label: "Close",
						onClick: _cache[35] || (_cache[35] = ($event) => confirmation.value.close())
					})]),
					createBaseVNode("p", null, toDisplayString(unref(t)("This creates the project article Search Type and missing content columns, and adds metadata to Messages and Message Log. Existing data is preserved.")), 1),
					createBaseVNode("ul", null, [
						createBaseVNode("li", null, toDisplayString(__props.project) + "/th_knowledge_article: kind, parent_code, content, content_text, sort_order, updated_by, linked_skeys", 1),
						_cache[43] || (_cache[43] = createBaseVNode("li", null, [createBaseVNode("code", null, toDisplayString("sthpw/message: metadata"))], -1)),
						_cache[44] || (_cache[44] = createBaseVNode("li", null, [createBaseVNode("code", null, toDisplayString("sthpw/message_log: metadata"))], -1))
					]),
					createBaseVNode("footer", null, [createVNode(_sfc_main$2, {
						label: "Cancel",
						onClick: _cache[36] || (_cache[36] = ($event) => confirmation.value.close())
					}), createVNode(_sfc_main$2, {
						label: "Initialize",
						highlighted: "",
						onClick: initialize
					})])
				], 8, _hoisted_40),
				createBaseVNode("dialog", {
					ref_key: "deletion",
					ref: deletion,
					class: "record-dialog knowledge-deletion",
					"aria-label": unref(t)(deletingFile.value ? "Delete article file?" : "Delete record")
				}, [
					createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)(deletingFile.value ? "Delete article file?" : "Delete record")), 1), createVNode(_sfc_main$2, {
						"icon-only": "",
						icon: "close",
						label: "Close",
						disabled: saving.value,
						onClick: _cache[37] || (_cache[37] = ($event) => deletion.value.close())
					}, null, 8, ["disabled"])]),
					deletingFile.value ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [createBaseVNode("p", null, toDisplayString(deletingFile.value.title), 1), createBaseVNode("p", null, toDisplayString(unref(t)("The attachment snapshot will be retired. Existing article links are retained.")), 1)], 64)) : (openBlock(), createElementBlock(Fragment, { key: 1 }, [
						createBaseVNode("p", null, toDisplayString(document.value?.title), 1),
						createBaseVNode("p", null, toDisplayString(unref(t)("Review dependencies before deleting this page. Linked project objects are preserved.")), 1),
						(openBlock(true), createElementBlock(Fragment, null, renderList(deleteGroups.value, (group) => {
							return openBlock(), createBlock(_sfc_main$8, {
								key: group.search_type,
								"model-value": deleteTypes.value.includes(group.search_type),
								label: group.title + " · " + group.count,
								"onUpdate:modelValue": (value) => {
									deleteTypes.value = value ? [...deleteTypes.value, group.search_type] : deleteTypes.value.filter((kind) => kind !== group.search_type);
								}
							}, null, 8, [
								"model-value",
								"label",
								"onUpdate:modelValue"
							]);
						}), 128))
					], 64)),
					createBaseVNode("footer", null, [createVNode(_sfc_main$2, {
						label: "Cancel",
						disabled: saving.value,
						onClick: _cache[38] || (_cache[38] = ($event) => deletion.value.close())
					}, null, 8, ["disabled"]), createVNode(_sfc_main$2, {
						label: "Delete",
						destructive: "",
						disabled: saving.value || loading.value,
						onClick: _cache[39] || (_cache[39] = ($event) => deletingFile.value ? removeFile() : deletePage())
					}, null, 8, ["disabled"])])
				], 8, _hoisted_41),
				createBaseVNode("dialog", {
					ref_key: "moveDialog",
					ref: moveDialog,
					class: "record-dialog",
					"aria-label": unref(t)("Move to section")
				}, [
					createBaseVNode("header", null, [createBaseVNode("h2", null, toDisplayString(unref(t)("Move to section")), 1), createVNode(_sfc_main$2, {
						"icon-only": "",
						icon: "close",
						label: "Close",
						onClick: _cache[40] || (_cache[40] = ($event) => moveDialog.value.close())
					})]),
					createVNode(_sfc_main$4, {
						modelValue: moveParent.value,
						"onUpdate:modelValue": _cache[41] || (_cache[41] = ($event) => moveParent.value = $event),
						options: sectionOptions.value.filter((row) => row.value !== moveIdentity.value),
						label: "Parent section"
					}, null, 8, ["modelValue", "options"]),
					createBaseVNode("footer", null, [createVNode(_sfc_main$2, {
						label: "Cancel",
						onClick: _cache[42] || (_cache[42] = ($event) => moveDialog.value.close())
					}), createVNode(_sfc_main$2, {
						label: "Move",
						onClick: applyMove
					})])
				], 8, _hoisted_42)
			], 2);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=KnowledgeBase.js.map