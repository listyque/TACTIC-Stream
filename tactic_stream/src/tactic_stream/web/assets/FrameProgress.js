import { M as openBlock, h as createBlock } from "./vue.js";
import { E as AppProgress_default } from "./FrameView.js";
//#region src/frame/controls/display/FrameProgress.vue
var _sfc_main = {
	__name: "FrameProgress",
	props: { frameNode: Object },
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createBlock(AppProgress_default, {
				label: __props.frameNode.label,
				value: __props.frameNode.indeterminate ? void 0 : __props.frameNode.value,
				min: __props.frameNode.min,
				max: __props.frameNode.max
			}, null, 8, [
				"label",
				"value",
				"min",
				"max"
			]);
		};
	}
};
//#endregion
export { _sfc_main as t };

//# sourceMappingURL=FrameProgress.js.map