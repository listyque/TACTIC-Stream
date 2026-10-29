import { L as button, R as label, V as rect, v as translate } from "./resize.js";
//#region ../src/tactic_stream/shared_ui/controls/feedback/confirmation.ui.mjs
function describe(model, width, height, language) {
	const text = (key) => translate(key, language), compact = width < 380, margin = 16, inner = width - 32;
	const rows = compact ? 2 : 1, buttonHeight = 38, gap = 8, footer = rows * 46 + margin;
	const nodes = [label("confirmationMessage", rect(margin, 12, inner, Math.max(40, height - footer - 20)), model.message, { wrap: true })];
	[{
		id: model.rejectId || "confirmationReject",
		text: model.reject || "Cancel",
		type: "reject"
	}, {
		id: model.acceptId || "confirmationAccept",
		text: model.accept || "Continue",
		type: "accept"
	}].forEach((action, index) => nodes.push(button(action.id, rect(margin + (compact ? 0 : index * (inner + gap) / 2), height - footer + (compact ? index * 46 : 0), compact ? inner : (inner - gap) / 2, buttonHeight), text(action.text), "", { type: action.type }, !model.busy, {
		highlighted: index === 1 && !model.destructive,
		destructive: index === 1 && model.destructive
	})));
	return { nodes };
}
//#endregion
export { describe as t };

//# sourceMappingURL=confirmation.ui.js.map