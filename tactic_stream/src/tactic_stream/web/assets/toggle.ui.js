import { _ as controls } from "./AppButton.js";
import { K as label, X as rect, Y as node } from "./FrameView.js";
//#region ../src/tactic_stream/shared_ui/controls/forms/toggle.ui.mjs
function captionedSwitch(id, bounds, properties) {
	const enabled = properties.enabled !== false, textX = controls.switch.width + controls.switch.spacing;
	return node("Box", id + "Row", bounds, { children: [node("Switch", id, rect(0, 0, bounds.width, bounds.height), properties), label(id + "Text", rect(textX, 0, Math.max(0, bounds.width - textX), bounds.height), properties.text, {
		pointerTransparent: true,
		color: enabled ? "primaryText" : "disabledText"
	})] });
}
//#endregion
export { captionedSwitch as t };

//# sourceMappingURL=toggle.ui.js.map