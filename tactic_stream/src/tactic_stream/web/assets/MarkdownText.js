import { t as MarkdownItCallable } from "./markdown-it.js";
import { N as openBlock, m as computed, v as createElementBlock } from "./vue.js";
import { c as xmlTokens, o as javascriptTokens, s as pythonTokens } from "./clipboard.js";
import { n as escapeHtml } from "./richText.js";
//#region src/controls/markdown.js
var markdown = new MarkdownItCallable({
	html: false,
	highlight(source, language) {
		const tokenize = {
			python: pythonTokens,
			py: pythonTokens,
			javascript: javascriptTokens,
			js: javascriptTokens,
			xml: xmlTokens
		}[language];
		return tokenize ? tokenize(source).map((token) => token.role ? "<span class=\"syntax-" + token.role + "\">" + escapeHtml(token.text) + "</span>" : escapeHtml(token.text)).join("") : escapeHtml(source);
	}
});
markdown.validateLink = (href) => /^(https?:\/\/|mailto:|#[\w\p{L}-]+$|[a-z][a-z0-9_.-]*\.(?:en|ru)\.md(?:#[\w\p{L}-]+)?$|(?:\.\/)?media\/[\w.-]+\.(?:png|jpe?g|webp)$)/iu.test(href);
markdown.renderer.rules.link_open = (tokens, index, options, env, self) => {
	const href = tokens[index].attrGet("href");
	if (/^https?:/i.test(href)) {
		tokens[index].attrSet("target", "_blank");
		tokens[index].attrSet("rel", "noopener noreferrer");
	}
	return self.renderToken(tokens, index, options);
};
var renderImage = markdown.renderer.rules.image;
markdown.renderer.rules.image = (tokens, index, options, env, self) => {
	const token = tokens[index], source = token.attrGet("src");
	if (!/^(?:\.\/)?media\/[\w.-]+\.(?:png|jpe?g|webp)$/i.test(source)) return escapeHtml(token.content);
	token.attrSet("src", "/ui/help/" + source.replace(/^\.\//, ""));
	token.attrSet("loading", "lazy");
	return renderImage(tokens, index, options, env, self);
};
markdown.renderer.rules.heading_open = (tokens, index, options, env, self) => {
	const name = tokens[index + 1].content.toLocaleLowerCase().replace(/[^\p{L}\p{N}_ -]/gu, "").trim().replace(/\s+/g, "-");
	env.headings ||= /* @__PURE__ */ new Map();
	const count = env.headings.get(name) || 0;
	env.headings.set(name, count + 1);
	tokens[index].attrSet("id", name + (count ? "-" + count : ""));
	return self.renderToken(tokens, index, options);
};
function renderMarkdown(text) {
	return markdown.render(text);
}
//#endregion
//#region src/controls/MarkdownText.vue
var _hoisted_1 = ["innerHTML"];
var _sfc_main = {
	__name: "MarkdownText",
	props: { text: {
		type: String,
		default: ""
	} },
	emits: ["topic"],
	setup(__props, { emit: __emit }) {
		const props = __props;
		const emit = __emit;
		function activate(event) {
			const href = event.target.closest("a")?.getAttribute("href");
			const topic = href?.match(/^([a-z][a-z0-9_.-]*)\.(?:en|ru)\.md(?:#.*)?$/i)?.[1];
			if (topic && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey && !event.button) {
				event.preventDefault();
				emit("topic", topic);
			}
			if (href?.startsWith("#")) {
				event.preventDefault();
				event.currentTarget.closest("article")?.querySelector("#" + CSS.escape(decodeURIComponent(href.slice(1))))?.scrollIntoView({ block: "start" });
			}
		}
		const html = computed(() => renderMarkdown(props.text));
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("div", {
				class: "markdown-text",
				innerHTML: html.value,
				onClick: activate
			}, null, 8, _hoisted_1);
		};
	}
};
//#endregion
export { _sfc_main as default };

//# sourceMappingURL=MarkdownText.js.map