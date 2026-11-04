import { N as openBlock, P as renderList, d as Fragment, h as createBaseVNode, it as toDisplayString, m as computed, nt as normalizeClass, v as createElementBlock } from "./vue.js";
import { y as syntaxTokens } from "./FrameView.js";
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
			default: "auto"
		}
	},
	setup(__props) {
		const props = __props;
		const tokens = computed(() => syntaxTokens(props.code, props.language));
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