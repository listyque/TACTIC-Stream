import { N as openBlock, P as renderList, _ as createElementBlock, it as toDisplayString, m as createBaseVNode, nt as normalizeClass, p as computed, u as Fragment } from "./vue.js";
import { f as javascriptTokens, m as xmlTokens, p as pythonTokens } from "./resize.js";
//#region src/controls/CodeBlock.vue
var _hoisted_1 = {
	class: "code-block",
	tabindex: "0"
};
var _sfc_main = {
	__name: "CodeBlock",
	props: {
		code: {
			type: String,
			default: ""
		},
		language: {
			type: String,
			default: "python"
		}
	},
	setup(__props) {
		const props = __props;
		const tokens = computed(() => props.language === "text" ? [{ text: props.code }] : props.language === "xml" ? xmlTokens(props.code) : props.language === "javascript" ? javascriptTokens(props.code) : pythonTokens(props.code));
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("pre", _hoisted_1, [createBaseVNode("code", null, [(openBlock(true), createElementBlock(Fragment, null, renderList(tokens.value, (token, index) => {
				return openBlock(), createElementBlock("span", {
					key: index,
					class: normalizeClass(token.role ? "syntax-" + token.role : void 0)
				}, toDisplayString(token.text), 3);
			}), 128))])]);
		};
	}
};
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=CodeBlock.js.map