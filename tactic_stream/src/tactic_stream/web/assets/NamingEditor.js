import { r as __exportAll } from "./ObjectFieldFrame.js";
import { I as resolveComponent, N as openBlock, c as vShow, g as createBlock, h as createBaseVNode, p as Teleport, q as withDirectives, rt as normalizeStyle, v as createElementBlock, x as createVNode } from "./vue.js";
import { o as t, s as appearance, z as _plugin_vue_export_helper_default } from "./AppButton.js";
import { j as rpc } from "./index.js";
import { K as button, T as translate, U as observeFrameSizes, X as node, Y as muted, Z as rect, q as label, t as _sfc_main$1 } from "./FrameView.js";
import { n as sections } from "./sections.ui.js";
import { i as sectionSelector, n as notices, o as toolbar$1, r as policy, t as documentEvent } from "./admin.document.js";
//#region ../src/tactic_stream/shared_ui/features/administration/naming/naming.ui.mjs
function toolbar(model, ui, width, language) {
	const tr = (text) => translate(text, language), actions = toolbar$1(model, ui, width, language), edit = !model.busy && !model.uncertain && model.canWrite && !ui.confirmation;
	actions.nodes = actions.nodes.filter((row) => row.id !== "adminDocumentStatus");
	actions.nodes.push(button("namingCreate", rect(46, 0, 38, 38), tr("Create naming rule"), "add", { type: "create" }, edit, { iconOnly: true }), button("namingDuplicate", rect(90, 0, 38, 38), tr("Duplicate selected rule"), "copy", { type: "duplicate" }, edit && model.ready, { iconOnly: true }));
	return actions;
}
function title(row, language) {
	const record = row.document || {}, match = /snapshot\.context\)\s*==\s*['"]?([\w/.-]+)/.exec(record.condition || "");
	return record.context || match && match[1] || record.script_path || translate(record.latest_versionless || record.current_versionless ? "Versionless" : "Default", language);
}
function describe(model, ui, width, height, language) {
	if (width <= 0 || height <= 0) return { nodes: [] };
	const tr = (text) => translate(text, language), local = model.previewMode === "local", noticeModel = Object.assign({}, model, { error: model.error || ui.error });
	if (ui.confirmation === "execute") noticeModel.confirmationText = "Run custom naming code? This uses the normal server environment, not an isolated sandbox. Scripts and classes can change data or files.";
	if (ui.confirmation === "save") noticeModel.confirmationText = "Update project naming rule? This changes future check-ins in the current project. Existing files are kept.";
	const notice = notices(noticeModel, ui, width, language, "Discard unsaved naming changes?", ui.confirmation === "execute" ? "Evaluate with custom code" : void 0), nodes = notice.nodes;
	const y = notice.top, h = height - y, split = width >= 800, catalogVisible = ui.catalogVisible !== false, left = split ? catalogVisible ? Math.min(ui.catalogWidth, width * .4) : 56 : width, editing = split || ui.editing;
	if (h < 220) return { nodes: [node("Scroll", "namingPageScroll", rect(0, 0, width, height), {
		contentHeight: 400 + y,
		children: describe(model, ui, width - 16, 400 + y, language).nodes
	})] };
	if (split || !ui.editing) {
		const catalogChildren = [];
		if (!split || catalogVisible) {
			catalogChildren.push(label("namingCatalogTitle", rect(12, 10, Math.max(0, left - (split ? 62 : 24)), 34), tr("Naming rules"), { weight: 600 }), node("List", "namingRules", rect(12, 52, left - 24, Math.max(0, h - 64)), {
				source: "namingRules",
				keyField: "identity",
				rowHeight: 86,
				scrollbarId: "namingRulesScrollBar"
			}));
			if (!model.rules.length) catalogChildren.push(label("namingRulesEmpty", rect(12, 60, left - 24, 100), tr("No rules for this search type"), Object.assign({ wrap: true }, muted)));
		}
		if (split) catalogChildren.push(button("namingToggleCatalog", rect(catalogVisible ? left - 46 : (left - 34) / 2, 10, 34, 34), tr(catalogVisible ? "Hide naming rules" : "Show naming rules"), catalogVisible ? "chevron-left" : "chevron-right", { type: "catalogVisible" }, true, {
			iconOnly: true,
			iconAction: true,
			round: false
		}));
		nodes.push(node("Box", "namingCatalogPanel", rect(0, y, left, h), {
			background: "surfaceContainerLow",
			border: "outlineVariant",
			children: catalogChildren
		}));
	}
	if (split && catalogVisible) nodes.push(node("Splitter", "namingSplitHandle", rect(left, y, 10, h), {
		text: tr("Naming rules panel width"),
		value: left,
		min: 180,
		max: width * .4,
		action: { type: "split" }
	}));
	if (!editing) return { nodes };
	const bounds = rect(split ? left + 10 : 0, y, split ? width - left - 10 : width, h), w = bounds.width - 40, children = [];
	let top = 12;
	if (!split) {
		children.push(button("namingBack", rect(12, top, 110, 36), tr("Back"), "chevron-left", { type: "back" }, !model.busy && !!model.identity));
		top += 44;
	}
	children.push(label("namingTargetTitle", rect(12, top, w, 26), model.targetTitle || model.searchType || tr("Naming editor"), {
		fontRole: "section",
		weight: 600
	}), label("namingTargetType", rect(12, top + 30, w, 22), model.project + " / " + model.searchType, muted));
	top += 60;
	if (!model.ready) children.push(label("namingSelectHelp", rect(12, top, w, 80), tr("Select a rule or create a new one."), Object.assign({ wrap: true }, muted)));
	else {
		children.push(sectionSelector("namingPages", [{
			value: "rule",
			label: tr("Naming rule"),
			icon: "edit"
		}, {
			value: "preview",
			label: tr("Naming preview"),
			icon: "search"
		}], ui.page === "advanced" ? "rule" : ui.page, rect(12, top, bounds.width - 24, 38), !model.busy, "page", tr("Naming sections")));
		top += 46;
		const fields = [], editable = policy(model).editable && !ui.confirmation, text = (key) => Object.prototype.hasOwnProperty.call(ui.text, key) ? ui.text[key] : String(model.document[key] || "");
		let body = {
			nodes: [],
			height: 0
		};
		if (ui.page === "rule" || ui.page === "advanced") {
			const ruleNodes = [], cardPad = w < 380 ? 10 : 14, innerW = Math.max(1, w - cardPad * 2), twoCol = innerW >= 460, colGap = 12, colW = twoCol ? (innerW - colGap) / 2 : innerW;
			let ry = 0;
			const layoutButtonRows = (items, startY, rowH = 32, gap = 6) => {
				const placed = [];
				let cx = cardPad, cy = startY;
				for (const item of items) {
					const bw = Math.min(innerW, Math.max(item.minW || 76, Math.ceil(String(item.label).length * 9) + (item.icon ? 60 : 42)));
					if (cx > cardPad && cx + bw > cardPad + innerW) {
						cx = cardPad;
						cy += rowH + gap;
					}
					placed.push(button(item.id, rect(cx, cy, bw, rowH), item.label, item.icon || "", item.action, editable, item.selected ? {
						role: "radio",
						selected: true
					} : void 0));
					cx += bw + gap;
				}
				return {
					nodes: placed,
					height: items.length ? cy - startY + rowH : 0
				};
			};
			const checkinVal = model.document.checkin_type || "", checkinBadgeText = checkinVal === "strict" ? tr("Strict") : checkinVal === "auto" ? tr("Auto") : tr("Unspecified"), showBadge = innerW >= 360, badgeW = showBadge ? Math.min(Math.max(96, checkinBadgeText.length * 7 + 34), 180) : 0, ctxVal = text("context"), ctxPresets = [
				{
					id: "namingContextPreset_any",
					label: tr("Default"),
					val: ""
				},
				{
					id: "namingContextPreset_publish",
					label: "publish",
					val: "publish"
				},
				{
					id: "namingContextPreset_publish_wild",
					label: "publish/*",
					val: "publish/*"
				},
				{
					id: "namingContextPreset_icon",
					label: "icon",
					val: "icon"
				},
				{
					id: "namingContextPreset_work",
					label: "work",
					val: "work"
				},
				{
					id: "namingContextPreset_review",
					label: "review",
					val: "review"
				}
			], row1Top = 52, checkinExplainTop = twoCol ? 122 : 194, checkinExplainH = innerW < 560 ? 64 : 46, checkinExplainText = checkinVal === "auto" ? tr("Auto: Automatically creates a Latest versionless copy on every check-in (strips _v{version} and places versioned files into /versions) without needing a separate Versionless rule.") : checkinVal === "strict" ? tr("Strict: Uses the exact Directory and File naming paths as written. Versionless copies are created ONLY if a separate rule has Latest or Current versionless enabled.") : tr("Unspecified (default): Behaves like Strict (exact paths; requires an explicit Versionless rule for versionless copies), while remaining compatible with both strict and auto check-in calls."), row2Top = checkinExplainTop + checkinExplainH + 12, ctxPresetsTop = row2Top + 90, ctxButtons = layoutButtonRows(ctxPresets.map((p) => ({
				id: p.id,
				label: p.label,
				selected: ctxVal === p.val,
				action: {
					type: "preset",
					field: "context",
					value: p.val
				}
			})), ctxPresetsTop, 32, 6), scopeCardH = ctxPresetsTop + ctxButtons.height + 14, scopeChildren = [
				node("Icon", "namingRuleHeadingIcon", rect(cardPad, 13, 18, 18), {
					icon: "tune",
					color: "action"
				}),
				label("namingRuleHeading", rect(cardPad + 26, 10, Math.max(60, innerW - 26 - (showBadge ? badgeW + 10 : 0)), 24), model.identity || tr("New naming rule"), {
					role: "heading",
					level: 3,
					fontRole: "section",
					weight: 600
				}),
				node("Box", "namingScopeDivider", rect(cardPad, 42, innerW, 1), { background: "outlineVariant" }),
				node("Icon", "namingSearchTypeIcon", rect(cardPad, 55, 15, 15), {
					icon: "layers",
					color: "action"
				}),
				label("namingSearchTypeLabel", rect(cardPad + 22, row1Top, Math.max(0, colW - 22), 20), tr("Search Type"), { weight: 600 }),
				node("Field", "namingSearchType", rect(cardPad, 76, colW, 38), {
					label: tr("Search Type"),
					text: model.searchType,
					readOnly: true,
					enabled: editable
				}),
				node("Icon", "namingCheckinIcon", rect(twoCol ? cardPad + colW + colGap : cardPad, (twoCol ? row1Top : 124) + 3, 15, 15), {
					icon: "check",
					color: "action"
				}),
				label("namingCheckinLabel", rect((twoCol ? cardPad + colW + colGap : cardPad) + 22, twoCol ? row1Top : 124, Math.max(0, colW - 22), 20), tr("Check-in type"), { weight: 600 }),
				node("Choice", "namingCheckin", rect(twoCol ? cardPad + colW + colGap : cardPad, (twoCol ? row1Top : 124) + 24, colW, 38), {
					label: tr("Check-in type"),
					options: [
						{
							value: "auto",
							label: tr("Auto")
						},
						{
							value: "strict",
							label: tr("Strict")
						},
						{
							value: "",
							label: tr("Unspecified")
						}
					],
					value: checkinVal,
					enabled: editable,
					action: {
						type: "field",
						field: "checkin_type"
					}
				}),
				node("Box", "namingCheckinInfoBanner", rect(cardPad, checkinExplainTop, innerW, checkinExplainH), {
					background: "surfaceContainerHigh",
					border: "outlineVariant",
					radius: 8,
					children: [node("Icon", "namingCheckinInfoIcon", rect(12, Math.floor((checkinExplainH - 16) / 2), 16, 16), {
						icon: "info",
						color: "action"
					}), label("namingCheckinInfoText", rect(36, 4, Math.max(1, innerW - 48), checkinExplainH - 8), checkinExplainText, Object.assign({ wrap: true }, muted))]
				}),
				node("Icon", "namingContextIcon", rect(cardPad, row2Top + 3, 15, 15), {
					icon: "folder-open",
					color: "action"
				}),
				label("namingContextLabel", rect(cardPad + 22, row2Top, Math.max(0, innerW - 22), 20), tr("Rule context (empty means any)"), { weight: 600 }),
				label("namingContextHint", rect(cardPad, row2Top + 22, innerW, 18), tr("Use a context or a native wildcard such as publish/*."), muted),
				node("Field", "naming_context", rect(cardPad, row2Top + 44, innerW, 38), {
					label: tr("Rule context (empty means any)"),
					placeholder: "publish, publish/*, icon...",
					text: ctxVal,
					enabled: editable,
					action: {
						type: "text",
						field: "context"
					},
					commitAction: { type: "commit" }
				}),
				...ctxButtons.nodes
			];
			if (showBadge) scopeChildren.push(node("Box", "namingCheckinBadge", rect(w - cardPad - badgeW, 9, badgeW, 26), {
				background: "surfaceContainerHigh",
				border: "outlineVariant",
				radius: 13,
				children: [node("Icon", "namingCheckinBadgeIcon", rect(10, 5, 15, 15), {
					icon: "check",
					color: "action"
				}), label("namingCheckinBadgeText", rect(28, 3, Math.max(0, badgeW - 36), 20), checkinBadgeText, {
					fontRole: "secondary",
					weight: 600
				})]
			}));
			ruleNodes.push(node("Box", "namingScopeCard", rect(0, ry, w, scopeCardH), {
				background: "surfaceContainer",
				border: "outlineVariant",
				radius: 10,
				children: scopeChildren
			}));
			ry += scopeCardH + 12;
			const dirVal = text("dir_naming"), dirPresets = [
				{
					id: "namingDirPreset_standard",
					label: "Standard",
					icon: "folder-open",
					val: "{project.code}/{search_type.table_name}/{sobject.code}/{snapshot.context}"
				},
				{
					id: "namingDirPreset_parent",
					label: "By parent",
					icon: "hierarchy",
					val: "{project.code}/{search_type.table_name}/{parent.code}/{sobject.code}/versions"
				},
				{
					id: "namingDirPreset_process",
					label: "By process",
					icon: "workflow",
					val: "{project.code}/{search_type.table_name}/{sobject.code}/{snapshot.process}/{snapshot.context}"
				},
				{
					id: "namingDirPreset_case",
					label: "Playblast / Web (@CASE)",
					icon: "code",
					val: "{project.code}/{search_type.table_name}/{parent.code}/versions{@CASE(@GET(file.type) == 'playblast', '/'+'__preview', @GET(file.type) == 'web', '/'+'__preview/web')}"
				}
			], dirTokens = [
				["project_code", "{project.code}"],
				["table_name", "{search_type.table_name}"],
				["parent_code", "{parent.code}"],
				["sobject_code", "{sobject.code}"],
				["sobject_name", "{sobject.name}"],
				["process", "{snapshot.process}"],
				["context", "{snapshot.context}"],
				["case_type", "{@CASE(@GET(file.type) == 'playblast', '/'+'__preview')}"]
			], dirPresetRow = layoutButtonRows(dirPresets.map((p) => ({
				id: p.id,
				label: p.label,
				icon: p.icon,
				selected: dirVal === p.val,
				action: {
					type: "preset",
					field: "dir_naming",
					value: p.val
				}
			})), 52, 32, 6), dirEditorTop = 52 + dirPresetRow.height + 10, dirEditorH = 128, dirTokensTop = dirEditorTop + dirEditorH + 8, dirTokenRow = layoutButtonRows(dirTokens.map(([key, token]) => ({
				id: "namingDirToken_" + key,
				label: "+ " + (token.length > 26 ? "{@CASE(...)}" : token),
				action: {
					type: "insertToken",
					field: "dir_naming",
					token,
					separator: "/"
				}
			})), dirTokensTop, 30, 6), dirCardH = dirTokensTop + dirTokenRow.height + 14;
			ruleNodes.push(node("Box", "namingDirCard", rect(0, ry, w, dirCardH), {
				background: "surfaceContainer",
				border: "outlineVariant",
				radius: 10,
				children: [
					node("Icon", "namingDirCardIcon", rect(cardPad, 13, 18, 18), {
						icon: "folder-open",
						color: "action"
					}),
					label("namingDirCardTitle", rect(cardPad + 26, 10, innerW - 26, 24), tr("Directory naming"), {
						fontRole: "section",
						weight: 600
					}),
					node("Box", "namingDirCardDivider", rect(cardPad, 42, innerW, 1), { background: "outlineVariant" }),
					...dirPresetRow.nodes,
					node("Area", "naming_dir_naming", rect(cardPad, dirEditorTop, innerW, dirEditorH), {
						label: tr("Directory naming"),
						placeholder: "{project.code}/{search_type.table_name}/{sobject.code}/{snapshot.context}",
						text: dirVal,
						monospace: true,
						syntax: "naming",
						enabled: editable,
						action: {
							type: "text",
							field: "dir_naming"
						},
						commitAction: { type: "commit" }
					}),
					...dirTokenRow.nodes
				]
			}));
			ry += dirCardH + 12;
			const fileVal = text("file_naming"), filePresets = [
				{
					id: "namingFilePreset_name_ver",
					label: "Name + version",
					icon: "description",
					val: "{sobject.name}_v{version}.{ext}"
				},
				{
					id: "namingFilePreset_code_ctx_ver",
					label: "Code + context + version",
					icon: "code",
					val: "{sobject.code}_{snapshot.context}_v{version}.{ext}"
				},
				{
					id: "namingFilePreset_versionless",
					label: tr("Versionless"),
					icon: "history",
					val: "{sobject.name}_{snapshot.context}.{ext}"
				},
				{
					id: "namingFilePreset_basefile",
					label: "Original ({basefile})",
					icon: "file",
					val: "{basefile}_v{version}.{ext}"
				}
			], fileTokens = [
				["sobject_name", "{sobject.name}"],
				["sobject_code", "{sobject.code}"],
				["context", "{snapshot.context}"],
				["file_type", "{file.type}"],
				["version", "_v{version}"],
				["basefile", "{basefile}"],
				["ext", ".{ext}"]
			], filePresetRow = layoutButtonRows(filePresets.map((p) => ({
				id: p.id,
				label: p.label,
				icon: p.icon,
				selected: fileVal === p.val,
				action: {
					type: "preset",
					field: "file_naming",
					value: p.val
				}
			})), 52, 32, 6), fileEditorTop = 52 + filePresetRow.height + 10, fileEditorH = 104, fileTokensTop = fileEditorTop + fileEditorH + 8, fileTokenRow = layoutButtonRows(fileTokens.map(([key, token]) => ({
				id: "namingFileToken_" + key,
				label: "+ " + token,
				action: {
					type: "insertToken",
					field: "file_naming",
					token,
					separator: ""
				}
			})), fileTokensTop, 30, 6), fileCardH = fileTokensTop + fileTokenRow.height + 14;
			ruleNodes.push(node("Box", "namingFileCard", rect(0, ry, w, fileCardH), {
				background: "surfaceContainer",
				border: "outlineVariant",
				radius: 10,
				children: [
					node("Icon", "namingFileCardIcon", rect(cardPad, 13, 18, 18), {
						icon: "description",
						color: "action"
					}),
					label("namingFileCardTitle", rect(cardPad + 26, 10, innerW - 26, 24), tr("File naming"), {
						fontRole: "section",
						weight: 600
					}),
					node("Box", "namingFileCardDivider", rect(cardPad, 42, innerW, 1), { background: "outlineVariant" }),
					...filePresetRow.nodes,
					node("Area", "naming_file_naming", rect(cardPad, fileEditorTop, innerW, fileEditorH), {
						label: tr("File naming"),
						placeholder: "{sobject.name}_v{version}.{ext}",
						text: fileVal,
						monospace: true,
						syntax: "naming",
						enabled: editable,
						action: {
							type: "text",
							field: "file_naming"
						},
						commitAction: { type: "commit" }
					}),
					...fileTokenRow.nodes
				]
			}));
			ry += fileCardH + 12;
			const flagRows = [
				[
					"latest_versionless",
					"Latest versionless",
					"Rule for the auto-updated copy of the newest version (no _v001 in file name). Can be combined with Current versionless."
				],
				[
					"current_versionless",
					"Current versionless",
					"Rule for the copy of the version marked as Current. Can be combined with Latest versionless."
				],
				[
					"manual_version",
					"Manual version",
					"Reads the version number from the uploaded file name (e.g. _v015). Use only on versioned rules (not with versionless)."
				]
			], hasLatest = !!model.document.latest_versionless, hasCurrent = !!model.document.current_versionless, hasManual = !!model.document.manual_version, hasConflict = (hasLatest || hasCurrent) && hasManual, modeStatusText = hasConflict ? tr("Conflict: Manual version does not apply to versionless rules (versionless snapshots always use version -1). Keep Manual version only on regular versioned rules.") : hasLatest && hasCurrent ? tr("Active mode: This rule generates BOTH Latest and Current versionless copies. Regular versioned check-ins (v001, v002…) require a separate rule with versionless OFF.") : hasLatest || hasCurrent ? tr("Active mode: Versionless-only rule. TACTIC uses this rule only for the versionless copy; regular versioned check-ins (v001, v002…) require a separate rule.") : hasManual ? tr("Active mode: Versioned rule with manual version numbering parsed from the uploaded file name.") : tr("Active mode: Standard versioned rule (TACTIC numbers versions automatically: v001, v002, v003…)."), flagCols = innerW >= 680 ? 3 : 1, flagW = (innerW - (flagCols - 1) * 10) / Math.max(1, flagCols), flagTileH = flagCols === 3 ? 108 : 88, flagGridRows = Math.ceil(flagRows.length / Math.max(1, flagCols)), introH = innerW < 560 ? 54 : 38, tilesStartY = 50 + introH + 8, statusTop = tilesStartY + flagGridRows * flagTileH + Math.max(0, flagGridRows - 1) * 8 + 10, statusH = innerW < 560 ? 52 : 38, flagsCardH = statusTop + statusH + 14, flagChildren = [
				node("Icon", "namingFlagsCardIcon", rect(cardPad, 13, 18, 18), {
					icon: "history",
					color: "action"
				}),
				label("namingFlagsCardTitle", rect(cardPad + 26, 10, innerW - 26, 24), tr("Versionless"), {
					fontRole: "section",
					weight: 600
				}),
				node("Box", "namingFlagsCardDivider", rect(cardPad, 42, innerW, 1), { background: "outlineVariant" }),
				label("namingFlagsCardHint", rect(cardPad, 48, innerW, introH), tr("Regular versioned rules (v001, v002…) keep both versionless switches OFF. Enabling Latest or Current versionless makes this rule apply ONLY to versionless copies — create a separate rule for versioned files."), Object.assign({ wrap: true }, muted))
			];
			flagRows.forEach(([fKey, fTitle, fDesc], idx) => {
				const r = Math.floor(idx / flagCols), c = idx % flagCols, fx = cardPad + c * (flagW + 10), fy = tilesStartY + r * (flagTileH + 8), titleText = tr(fTitle), descText = tr(fDesc);
				flagChildren.push(node("Box", "namingFlagTile_" + fKey, rect(fx, fy, flagW, flagTileH), {
					background: "surfaceContainerHigh",
					border: "outlineVariant",
					radius: 8,
					children: [
						node("Switch", "naming_" + fKey, rect(12, 8, 44, 28), {
							text: titleText,
							checked: !!model.document[fKey],
							enabled: editable,
							action: {
								type: "field",
								field: fKey
							}
						}),
						label("namingFlagLabel_" + fKey, rect(64, 8, Math.max(1, flagW - 76), 28), titleText, { weight: 600 }),
						label("namingFlagDesc_" + fKey, rect(12, 38, Math.max(1, flagW - 24), flagTileH - 44), descText, Object.assign({ wrap: true }, muted))
					]
				}));
			});
			flagChildren.push(node("Box", "namingFlagsModeBanner", rect(cardPad, statusTop, innerW, statusH), {
				background: "surfaceContainerHigh",
				border: hasConflict ? "warning" : "outlineVariant",
				radius: 8,
				children: [node("Icon", "namingFlagsModeIcon", rect(12, Math.floor((statusH - 16) / 2), 16, 16), {
					icon: hasConflict ? "warning" : "info",
					color: hasConflict ? "warning" : "action"
				}), label("namingFlagsModeText", rect(36, 4, Math.max(1, innerW - 48), statusH - 8), modeStatusText, Object.assign({ wrap: true }, hasConflict ? {
					fontRole: "secondary",
					color: "warning",
					weight: 600
				} : muted))]
			}));
			ruleNodes.push(node("Box", "namingFlagsCard", rect(0, ry, w, flagsCardH), {
				background: "surfaceContainer",
				border: "outlineVariant",
				radius: 10,
				children: flagChildren
			}));
			ry += flagsCardH + 12;
			const sbVal = text("sandbox_dir_naming"), sbPresets = [
				{
					id: "namingSandboxPreset_inherit",
					label: tr("Default"),
					icon: "folder-open",
					val: ""
				},
				{
					id: "namingSandboxPreset_standard",
					label: "Standard sandbox",
					icon: "folder",
					val: "{project.code}/{search_type.table_name}/{sobject.code}/sandbox/{snapshot.context}"
				},
				{
					id: "namingSandboxPreset_process",
					label: "By process + user",
					icon: "workflow",
					val: "{project.code}/{search_type.table_name}/{sobject.code}/work/{snapshot.process}/{login.login}"
				},
				{
					id: "namingSandboxPreset_parent",
					label: "By parent",
					icon: "hierarchy",
					val: "{project.code}/{search_type.table_name}/{parent.code}/{sobject.code}/sandbox"
				}
			], sbTokens = [
				["project_code", "{project.code}"],
				["table_name", "{search_type.table_name}"],
				["parent_code", "{parent.code}"],
				["sobject_code", "{sobject.code}"],
				["process", "{snapshot.process}"],
				["context", "{snapshot.context}"],
				["login", "{login.login}"]
			], sbPresetRow = layoutButtonRows(sbPresets.map((p) => ({
				id: p.id,
				label: p.label,
				icon: p.icon,
				selected: sbVal === p.val,
				action: {
					type: "preset",
					field: "sandbox_dir_naming",
					value: p.val
				}
			})), 74, 32, 6), sbEditorTop = 74 + sbPresetRow.height + 10, sbEditorH = 104, sbTokensTop = sbEditorTop + sbEditorH + 8, sbTokenRow = layoutButtonRows(sbTokens.map(([key, token]) => ({
				id: "namingSandboxToken_" + key,
				label: "+ " + token,
				action: {
					type: "insertToken",
					field: "sandbox_dir_naming",
					token,
					separator: "/"
				}
			})), sbTokensTop, 30, 6), sbCardH = sbTokensTop + sbTokenRow.height + 14;
			ruleNodes.push(node("Box", "namingSandboxCard", rect(0, ry, w, sbCardH), {
				background: "surfaceContainer",
				border: "outlineVariant",
				radius: 10,
				children: [
					node("Icon", "namingSandboxCardIcon", rect(cardPad, 13, 18, 18), {
						icon: "folder",
						color: "action"
					}),
					label("namingSandboxCardTitle", rect(cardPad + 26, 10, innerW - 26, 24), tr("Sandbox directory naming"), {
						fontRole: "section",
						weight: 600
					}),
					node("Box", "namingSandboxCardDivider", rect(cardPad, 42, innerW, 1), { background: "outlineVariant" }),
					label("namingSandboxCardHint", rect(cardPad, 50, innerW, 18), tr("The sandbox path expression; empty uses Directory naming."), muted),
					...sbPresetRow.nodes,
					node("Area", "naming_sandbox_dir_naming", rect(cardPad, sbEditorTop, innerW, sbEditorH), {
						label: tr("Sandbox directory naming"),
						placeholder: "{project.code}/{search_type.table_name}/{sobject.code}/sandbox/{snapshot.context}",
						text: sbVal,
						monospace: true,
						syntax: "naming",
						enabled: editable,
						action: {
							type: "text",
							field: "sandbox_dir_naming"
						},
						commitAction: { type: "commit" }
					}),
					...sbTokenRow.nodes
				]
			}));
			ry += sbCardH + 12;
			const condVal = text("condition"), condPresets = [
				{
					id: "namingCondPreset_any",
					label: tr("Default"),
					val: ""
				},
				{
					id: "namingCondPreset_publish",
					label: "context == 'publish'",
					icon: "check",
					val: "@GET(snapshot.context) == 'publish'"
				},
				{
					id: "namingCondPreset_playblast",
					label: "file.type == 'playblast'",
					icon: "code",
					val: "@GET(file.type) == 'playblast'"
				},
				{
					id: "namingCondPreset_model",
					label: "process == 'model'",
					icon: "workflow",
					val: "@GET(snapshot.process) == 'model'"
				},
				{
					id: "namingCondPreset_approved",
					label: "status == 'Approved'",
					icon: "check",
					val: "@GET(sobject.status) == 'Approved'"
				}
			], condTokens = [
				["ctx", "@GET(snapshot.context)"],
				["proc", "@GET(snapshot.process)"],
				["ftype", "@GET(file.type)"],
				["status", "@GET(sobject.status)"],
				["code", "@GET(sobject.code)"],
				["eq_publish", "== 'publish'"]
			], condPresetRow = layoutButtonRows(condPresets.map((p) => ({
				id: p.id,
				label: p.label,
				icon: p.icon,
				selected: condVal === p.val,
				action: {
					type: "preset",
					field: "condition",
					value: p.val
				}
			})), 74, 32, 6), condEditorTop = 74 + condPresetRow.height + 10, condEditorH = 96, condTokensTop = condEditorTop + condEditorH + 8, condTokenRow = layoutButtonRows(condTokens.map(([key, token]) => ({
				id: "namingCondToken_" + key,
				label: "+ " + token,
				action: {
					type: "insertToken",
					field: "condition",
					token,
					separator: " "
				}
			})), condTokensTop, 30, 6), condCardH = condTokensTop + condTokenRow.height + 14;
			ruleNodes.push(node("Box", "namingConditionCard", rect(0, ry, w, condCardH), {
				background: "surfaceContainer",
				border: "outlineVariant",
				radius: 10,
				children: [
					node("Icon", "namingConditionCardIcon", rect(cardPad, 13, 18, 18), {
						icon: "code",
						color: "action"
					}),
					label("namingConditionCardTitle", rect(cardPad + 26, 10, innerW - 26, 24), tr("Condition"), {
						fontRole: "section",
						weight: 600
					}),
					node("Box", "namingConditionCardDivider", rect(cardPad, 42, innerW, 1), { background: "outlineVariant" }),
					label("namingConditionCardHint", rect(cardPad, 50, innerW, 18), tr("A native TACTIC expression evaluated on the object and snapshot."), muted),
					...condPresetRow.nodes,
					node("Area", "naming_condition", rect(cardPad, condEditorTop, innerW, condEditorH), {
						label: tr("Condition"),
						placeholder: "@GET(snapshot.context) == 'publish'",
						text: condVal,
						monospace: true,
						syntax: "naming",
						enabled: editable,
						action: {
							type: "text",
							field: "condition"
						},
						commitAction: { type: "commit" }
					}),
					...condTokenRow.nodes
				]
			}));
			ry += condCardH + 12;
			const appendPresetField = (targetChildren, startY, fKey, fIcon, fTitle, fDesc, placeholder, presets) => {
				const curVal = text(fKey), btnRow = layoutButtonRows(presets.map(([pKey, pLabel, pVal]) => ({
					id: "namingPreset_" + fKey + "_" + pKey,
					label: pLabel,
					selected: curVal === pVal,
					action: {
						type: "preset",
						field: fKey,
						value: pVal
					}
				})), startY + 88, 30, 6);
				targetChildren.push(node("Icon", "namingFieldIcon_" + fKey, rect(cardPad, startY + 3, 15, 15), {
					icon: fIcon,
					color: "action"
				}), label("namingFieldLabel_" + fKey, rect(cardPad + 22, startY, Math.max(0, innerW - 22), 20), tr(fTitle), { weight: 600 }), label("namingFieldHint_" + fKey, rect(cardPad, startY + 22, innerW, 18), tr(fDesc), muted), node("Field", "naming_" + fKey, rect(cardPad, startY + 44, innerW, 38), {
					label: tr(fTitle),
					placeholder,
					text: curVal,
					enabled: editable,
					action: {
						type: "text",
						field: fKey
					},
					commitAction: { type: "commit" }
				}), ...btnRow.nodes);
				return startY + 88 + btnRow.height + 16;
			};
			const repoChildren = [
				node("Icon", "namingRepoCardIcon", rect(cardPad, 13, 18, 18), {
					icon: "layers",
					color: "action"
				}),
				label("namingRepoCardTitle", rect(cardPad + 26, 10, innerW - 26, 24), tr("Snapshot type") + " · " + tr("Base directory alias"), {
					fontRole: "section",
					weight: 600
				}),
				node("Box", "namingRepoCardDivider", rect(cardPad, 42, innerW, 1), { background: "outlineVariant" })
			];
			let repoY = 54;
			repoY = appendPresetField(repoChildren, repoY, "snapshot_type", "layers", "Snapshot type", "Empty matches any snapshot type.", "file, sequence, dir, ref...", [
				[
					"any",
					tr("Default"),
					""
				],
				[
					"file",
					"file",
					"file"
				],
				[
					"sequence",
					"sequence",
					"sequence"
				],
				[
					"dir",
					"dir",
					"dir"
				],
				[
					"ref",
					"ref",
					"ref"
				]
			]);
			repoY = appendPresetField(repoChildren, repoY, "base_dir_alias", "folder-open", "Base directory alias", "Repository alias used by native check-in.", "default, assets, shots, publish...", [
				[
					"any",
					tr("Default"),
					""
				],
				[
					"default",
					"default",
					"default"
				],
				[
					"assets",
					"assets",
					"assets"
				],
				[
					"shots",
					"shots",
					"shots"
				],
				[
					"publish",
					"publish",
					"publish"
				]
			]);
			repoY = appendPresetField(repoChildren, repoY, "sandbox_dir_alias", "folder", "Sandbox directory alias", "Sandbox repository alias used by native check-in.", "sandbox, local, work...", [
				[
					"any",
					tr("Default"),
					""
				],
				[
					"sandbox",
					"sandbox",
					"sandbox"
				],
				[
					"local",
					"local",
					"local"
				],
				[
					"work",
					"work",
					"work"
				]
			]);
			repoY = appendPresetField(repoChildren, repoY, "ingest_rule_code", "cloud-upload", "Ingest rule code", "Optional ingest rule associated with this naming rule.", "default, plates, renders, assets...", [
				[
					"any",
					tr("Default"),
					""
				],
				[
					"default",
					"default",
					"default"
				],
				[
					"plates",
					"plates",
					"plates"
				],
				[
					"renders",
					"renders",
					"renders"
				],
				[
					"assets",
					"assets",
					"assets"
				]
			]);
			const repoCardH = repoY - 2;
			ruleNodes.push(node("Box", "namingRepoCard", rect(0, ry, w, repoCardH), {
				background: "surfaceContainer",
				border: "outlineVariant",
				radius: 10,
				children: repoChildren
			}));
			ry += repoCardH + 12;
			const codeChildren = [
				node("Icon", "namingCodeCardIcon", rect(cardPad, 13, 18, 18), {
					icon: "code",
					color: "action"
				}),
				label("namingAdvancedHeading", rect(cardPad + 26, 10, innerW - 26, 24), tr("Script path") + " · " + tr("Class name"), {
					role: "heading",
					level: 3,
					fontRole: "section",
					weight: 600
				}),
				node("Box", "namingCodeCardDivider", rect(cardPad, 42, innerW, 1), { background: "outlineVariant" })
			];
			let codeY = 54;
			codeY = appendPresetField(codeChildren, codeY, "script_path", "code", "Script path", "Existing server script overriding directory and file naming.", "naming/custom_dir, naming/shot_naming...", [
				[
					"none",
					tr("Default"),
					""
				],
				[
					"custom_dir",
					"naming/custom_dir",
					"naming/custom_dir"
				],
				[
					"shot_naming",
					"naming/shot_naming",
					"naming/shot_naming"
				],
				[
					"checkin_naming",
					"pipeline/checkin_naming",
					"pipeline/checkin_naming"
				]
			]);
			codeY = appendPresetField(codeChildren, codeY, "class_name", "tune", "Class name", "Installed naming class implementing get_dir and get_file.", "pyasm.biz.FileNaming, pyasm.biz.CustomFileNaming...", [
				[
					"none",
					tr("Default"),
					""
				],
				[
					"file_naming",
					"pyasm.biz.FileNaming",
					"pyasm.biz.FileNaming"
				],
				[
					"custom_naming",
					"pyasm.biz.CustomFileNaming",
					"pyasm.biz.CustomFileNaming"
				]
			]);
			const codeCardH = codeY - 2;
			ruleNodes.push(node("Box", "namingCodeCard", rect(0, ry, w, codeCardH), {
				background: "surfaceContainer",
				border: "outlineVariant",
				radius: 10,
				children: codeChildren
			}));
			ry += codeCardH + 8;
			body = {
				nodes: ruleNodes,
				height: ry
			};
		} else {
			fields.push({
				kind: "Heading",
				id: "namingPreviewHeading",
				title: "Naming preview",
				description: local ? "Local rule simulation" : "Evaluate the draft on a real object with the native TACTIC engine. Preview does not check in a file."
			});
			if (!local) fields.push({
				kind: "Choice",
				id: "namingSampleObject",
				title: "Search Object",
				options: model.items.map((row) => ({
					value: row.key,
					label: row.label
				})),
				props: {
					value: model.sample.key,
					action: {
						type: "sample",
						field: "key"
					}
				}
			});
			for (const row of [
				["file", "Example file"],
				["process", "Process"],
				["context", "Preview context"],
				["snapshotType", "Snapshot type"],
				["version", "Version"],
				["fileType", "File type"]
			]) {
				if (local && ["process", "snapshotType"].indexOf(row[0]) >= 0 && model.typeMode) continue;
				const version = row[0] === "version";
				fields.push({
					id: "namingSample_" + row[0],
					title: row[1],
					props: {
						text: version && ui.sampleVersion !== null ? ui.sampleVersion : String(model.sample[row[0]] === void 0 ? "" : model.sample[row[0]]),
						inputMode: version ? "numeric" : "text",
						action: version ? { type: "version" } : {
							type: "sample",
							field: row[0]
						},
						commitAction: version ? { type: "commitVersion" } : null
					}
				});
			}
			body = sections(fields, w, language, editable);
		}
		let bottom = body.height;
		if (ui.page === "preview") {
			if (!local) {
				if (model.itemCount > 50) {
					body.nodes.push(button("namingObjectsPrevious", rect(0, bottom, 100, 36), tr("Previous"), "chevron-left", {
						type: "items",
						offset: model.itemOffset - 50
					}, !model.busy && model.itemOffset > 0), label("namingObjectsPage", rect(108, bottom, Math.max(0, w - 216), 36), String(model.itemOffset + 1) + "–" + (model.itemOffset + model.items.length) + " / " + model.itemCount, { align: "center" }), button("namingObjectsNext", rect(w - 100, bottom, 100, 36), tr("Next"), "chevron-right", {
						type: "items",
						offset: model.itemOffset + 50
					}, !model.busy && model.itemOffset + model.items.length < model.itemCount));
					bottom += 44;
				}
				body.nodes.push(button("namingEvaluate", rect(0, bottom, w, 38), tr("Evaluate naming"), "search", { type: "evaluate" }, policy(model).editable && !!model.sample.key), button("namingEvaluateCustom", rect(0, bottom + 46, w, 38), tr("Evaluate with custom code"), "code", {
					type: "evaluate",
					execute: true
				}, policy(model).editable && !!model.sample.key));
				bottom += 96;
			}
			for (const result of model.previewResults || []) {
				body.nodes.push(label("namingResult_" + result.mode, rect(0, bottom, w, 26), tr({
					version: "Version",
					latest: "Latest versionless",
					current: "Current versionless",
					local: "Local rule simulation"
				}[result.mode] || result.mode), { weight: 600 }), node("Area", "namingPath_" + result.mode, rect(0, bottom + 32, w, 100), {
					text: result.path || "",
					label: tr("Naming result"),
					readOnly: true,
					monospace: true
				}));
				bottom += 140;
				const detail = [
					result.status || "",
					result.directory ? tr("Directory naming") + ": " + result.directory : "",
					result.file ? tr("File naming") + ": " + result.file : "",
					result.sandbox ? tr("Sandbox directory naming") + ": " + result.sandbox : "",
					result.matches === false ? tr("This draft is not selected for these parameters by native naming lookup.") + " " + (result.selectedRule || "") : ""
				].filter(Boolean).join("\n");
				if (detail) {
					body.nodes.push(node("Area", "namingResultDetails_" + result.mode, rect(0, bottom, w, 112), {
						text: detail,
						label: tr("Naming result"),
						readOnly: true,
						notice: true
					}));
					bottom += 120;
				}
				if (result.collisions && result.collisions.length) {
					body.nodes.push(node("Area", "namingCollisions_" + result.mode, rect(0, bottom, w, 120), {
						text: tr("Existing files already use this path:") + "\n" + result.collisions.map((row) => row.key + " · " + row.snapshot).join("\n"),
						label: tr("Existing files"),
						readOnly: true,
						color: "error"
					}));
					bottom += 128;
				}
			}
		}
		children.push(node("Scroll", "namingFieldsScroll", rect(12, top, bounds.width - 24, Math.max(1, h - top - 12)), {
			contentHeight: bottom,
			resetKey: ui.page + ":" + model.identity,
			scrollbarId: "namingFieldsScrollBar",
			children: body.nodes
		}));
	}
	nodes.push(node("Box", "namingEditorPanel", bounds, {
		background: "surfaceContainerLow",
		border: "outlineVariant",
		children
	}));
	return { nodes };
}
function row(listNode, record, model, language) {
	const width = listNode.width - 16, doc = record.document || {}, tr = (text) => translate(text, language);
	return { nodes: [node("Action", "namingRule_" + record.identity, rect(0, 0, width, 82), {
		text: title(record, language),
		selected: model.identity === record.identity,
		enabled: !model.busy && (!model.uncertain || model.identity === record.identity),
		normalColor: "transparent",
		selectedColor: "contentSelection",
		children: [
			node("Icon", "namingRuleIcon_" + record.identity, rect(10, 10, 18, 18), {
				icon: doc.latest_versionless || doc.current_versionless ? "history" : doc.script_path ? "code" : "folder-open",
				color: "action"
			}),
			label("namingRuleTitle_" + record.identity, rect(34, 6, Math.max(0, width - 46), 24), title(record, language), { weight: 600 }),
			label("namingRuleSummary_" + record.identity, rect(34, 32, Math.max(0, width - 46), 20), doc.file_naming || doc.script_path || doc.dir_naming || "", Object.assign({ monospace: true }, muted)),
			label("namingRuleIdentity_" + record.identity, rect(34, 56, Math.max(0, width - 46), 20), record.identity + " · " + (doc.checkin_type || tr("Unspecified")), muted)
		],
		action: {
			type: "select",
			identity: record.identity
		}
	})] };
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/naming/naming.state.mjs
var fields$1 = [
	"search_type",
	"dir_naming",
	"file_naming",
	"sandbox_dir_naming",
	"snapshot_type",
	"context",
	"latest_versionless",
	"current_versionless",
	"manual_version",
	"ingest_rule_code",
	"condition",
	"class_name",
	"script_path",
	"checkin_type",
	"base_dir_alias",
	"sandbox_dir_alias"
];
var flags$1 = [
	"latest_versionless",
	"current_versionless",
	"manual_version"
];
function initial() {
	return {
		editing: true,
		catalogVisible: true,
		catalogWidth: 270,
		page: "rule",
		confirmation: "",
		pending: null,
		text: {},
		sampleVersion: null,
		error: ""
	};
}
function pending(ui) {
	return Object.keys(ui.text).length > 0;
}
function transition(ui, model, event) {
	const next = Object.assign({}, ui), commands = [], edit = policy(model).editable;
	const document = documentEvent(ui, model, event);
	if (document && [
		"save",
		"reload",
		"discard"
	].indexOf(event.type) >= 0) return document;
	switch (event.type) {
		case "keep":
			next.confirmation = "";
			next.pending = null;
			break;
		case "confirm":
			if (model.busy || !next.confirmation) break;
			if (next.pending) {
				commands.push({ type: "discard" }, next.pending);
				next.pending = null;
				next.confirmation = "";
			} else if (next.confirmation === "execute") {
				if (edit) commands.push({
					type: "evaluate",
					execute: true
				});
				next.confirmation = "";
			} else return documentEvent(ui, model, event);
			break;
		case "text":
			if (edit && !next.confirmation) next.text = Object.assign({}, next.text, { [event.field]: event.value });
			break;
		case "applied":
			next.text = {};
			break;
		case "commit":
			if (edit && pending(next)) commands.push({ type: "apply" });
			break;
		case "field":
			if (edit && !next.confirmation) commands.push({
				type: "field",
				field: event.field,
				value: event.value
			});
			break;
		case "preset":
			if (edit && !next.confirmation && event.field) {
				const updatedText = Object.assign({}, next.text);
				delete updatedText[event.field];
				next.text = updatedText;
				commands.push({
					type: "field",
					field: event.field,
					value: String(event.value ?? "")
				});
			}
			break;
		case "insertToken":
			if (edit && !next.confirmation && event.field && event.token) {
				const current = Object.prototype.hasOwnProperty.call(next.text, event.field) ? String(next.text[event.field] || "") : String((model.document || {})[event.field] || ""), sep = event.separator && current && !current.endsWith(event.separator) ? event.separator : "", updatedText = Object.assign({}, next.text);
				delete updatedText[event.field];
				next.text = updatedText;
				commands.push({
					type: "field",
					field: event.field,
					value: current + sep + String(event.token)
				});
			}
			break;
		case "sample":
			if (edit && !next.confirmation) commands.push({
				type: "sample",
				field: event.field,
				value: event.value
			});
			break;
		case "version":
			if (edit) next.sampleVersion = event.value;
			break;
		case "commitVersion":
			if (next.sampleVersion !== null) {
				const version = Number(next.sampleVersion);
				if (!/^\d+$/.test(next.sampleVersion) || version < 1 || version > 9999) next.error = "Version must be between 1 and 9999";
				else {
					commands.push({
						type: "sample",
						field: "version",
						value: version
					});
					next.sampleVersion = null;
					next.error = "";
				}
			}
			break;
		case "page":
			next.page = event.value;
			break;
		case "split":
			next.catalogWidth = Math.max(180, Math.min(420, Number(event.value)));
			break;
		case "catalogVisible":
			next.catalogVisible = next.catalogVisible === false;
			break;
		case "back":
			if (model.identity) next.editing = false;
			break;
		case "evaluate":
			if (edit && model.sample.key && !next.confirmation) {
				if (event.execute) next.confirmation = "execute";
				else commands.push({
					type: "evaluate",
					execute: false
				});
			}
			break;
		case "items":
			if (!model.busy && !next.confirmation) commands.push({
				type: "items",
				offset: event.offset
			});
			break;
		case "select":
		case "create":
		case "duplicate":
			if (event.type === "select" && event.identity === model.identity && !model.busy && !next.confirmation) {
				next.editing = true;
				break;
			}
			if (model.busy || model.uncertain || next.confirmation || !model.canWrite && event.type !== "select") break;
			if (model.dirty) {
				next.confirmation = "navigate";
				next.pending = event;
			} else commands.push(event);
	}
	return {
		ui: next,
		commands
	};
}
function completed(ui, command) {
	if ([
		"select",
		"create",
		"duplicate"
	].indexOf(command.type) >= 0) return Object.assign({}, ui, {
		editing: true,
		text: {}
	});
	if (["reload", "discard"].indexOf(command.type) >= 0) return Object.assign({}, ui, {
		text: {},
		confirmation: "",
		pending: null
	});
	return ui;
}
//#endregion
//#region src/features/administration/NamingEditor.vue
var NamingEditor_exports = /* @__PURE__ */ __exportAll({ default: () => NamingEditor_default });
var fields = fields$1;
var flags = flags$1;
var sessionFields = [
	"rules",
	"items",
	"itemCount",
	"itemOffset",
	"identity",
	"document",
	"baseline",
	"revision",
	"uncertain",
	"error",
	"message",
	"context",
	"preview",
	"sample"
];
var _sfc_main = {
	components: { FrameView: _sfc_main$1 },
	props: {
		ticket: String,
		project: String,
		searchType: String,
		targetTitle: String,
		session: Object,
		toolbarTarget: String,
		presentationVisible: {
			type: Boolean,
			default: true
		}
	},
	emits: ["saved"],
	data() {
		const state = {
			restored: false,
			rules: [],
			items: [],
			itemCount: 0,
			itemOffset: 0,
			identity: "",
			document: null,
			baseline: "",
			revision: "",
			busy: false,
			uncertain: false,
			error: "",
			message: "",
			context: null,
			request: 0,
			preview: null,
			ui: initial(),
			viewport: {
				width: 1,
				height: 1
			},
			toolbarSize: 620,
			observer: null,
			sample: {
				key: "",
				file: "example.ma",
				version: 1,
				process: "publish",
				context: "publish",
				fileType: "main",
				snapshotType: "file"
			}
		};
		const saved = this.session?.snapshot;
		if (saved?.context?.ticket === this.ticket && saved.context.project === this.project && saved.context.searchType === this.searchType) Object.assign(state, saved, { restored: true });
		return state;
	},
	computed: {
		dirty() {
			return this.uncertain || this.document !== null && (JSON.stringify(this.document) !== this.baseline || pending(this.ui));
		},
		editable() {
			return !this.busy && !this.uncertain;
		},
		frameModel() {
			return {
				ready: !!this.document,
				canWrite: !!this.searchType,
				canLoad: !!this.ticket,
				busy: this.busy,
				dirty: this.dirty,
				uncertain: this.uncertain,
				error: this.error,
				message: this.message,
				identity: this.identity,
				document: this.document || {},
				rules: this.rules,
				items: this.items,
				itemCount: this.itemCount,
				itemOffset: this.itemOffset,
				sample: this.sample,
				previewMode: "server",
				previewResults: this.preview?.results || [],
				project: this.project,
				searchType: this.searchType,
				targetTitle: this.targetTitle || this.searchType
			};
		},
		frameScene() {
			return describe(this.frameModel, this.ui, this.viewport.width, this.viewport.height, appearance.language);
		},
		toolbarScene() {
			return toolbar(this.frameModel, this.ui, this.toolbarSize, appearance.language);
		},
		models() {
			return { namingRules: this.rules };
		}
	},
	mounted() {
		window.addEventListener("beforeunload", this.beforeUnload);
		if (!this.restored) this.reload();
		this.observer = observeFrameSizes((entries) => {
			for (const entry of entries) if (entry.target === this.$refs.body) this.viewport = {
				width: Math.max(1, entry.contentRect.width),
				height: Math.max(1, entry.contentRect.height)
			};
			else this.toolbarSize = entry.contentRect.width;
		});
		this.observer.observe(this.$refs.body);
		this.observer.observe(this.toolbarTarget ? document.querySelector(this.toolbarTarget) || this.$el : this.$el);
	},
	beforeUnmount() {
		this.applyText();
		if (this.session) this.session.snapshot = Object.fromEntries(sessionFields.map((key) => [key, this[key]]));
		this.observer?.disconnect();
		this.request++;
		window.removeEventListener("beforeunload", this.beforeUnload);
	},
	watch: {
		ticket() {
			this.contextChanged();
		},
		project() {
			this.contextChanged();
		},
		searchType() {
			this.contextChanged();
		},
		document: {
			deep: true,
			handler(value, previous) {
				this.preview = null;
				if (this.dirty && value === previous) this.message = "";
			}
		},
		sample: {
			deep: true,
			handler() {
				this.preview = null;
			}
		}
	},
	methods: {
		t,
		rowScene(node, record) {
			return row(node, record, this.frameModel, appearance.language);
		},
		applyText() {
			for (const [field, value] of Object.entries(this.ui.text)) this.document[field] = value;
			this.ui = transition(this.ui, this.frameModel, { type: "applied" }).ui;
		},
		async dispatch(event) {
			const result = transition(this.ui, this.frameModel, event);
			this.ui = result.ui;
			for (const command of result.commands) {
				if (!["reload", "discard"].includes(command.type)) this.applyText();
				switch (command.type) {
					case "apply": break;
					case "field":
						this.document[command.field] = command.value;
						break;
					case "sample":
						this.sample[command.field] = command.value;
						break;
					case "select":
						this.select(this.rules.find((row) => row.identity === command.identity), true);
						break;
					case "create":
						this.create(false, true);
						break;
					case "duplicate":
						this.create(true, true);
						break;
					case "reload":
						await this.reload(0, false, true);
						break;
					case "discard":
						this.document = this.identity ? { ...this.rules.find((row) => row.identity === this.identity)?.document } : null;
						this.baseline = JSON.stringify(this.document);
						this.preview = null;
						this.ui = {
							...this.ui,
							text: {}
						};
						if (this.uncertain) await this.reload(0, false, true);
						break;
					case "save":
						await this.save(true);
						break;
					case "evaluate":
						await this.evaluate(command.execute, true);
						break;
					case "items":
						await this.reload(command.offset, true, true);
						break;
					default: throw Error("Unsupported Naming command: " + command.type);
				}
				this.ui = completed(this.ui, command);
			}
		},
		beforeUnload(event) {
			if (this.dirty || this.busy || this.uncertain) {
				event.preventDefault();
				event.returnValue = "";
			}
		},
		canLeave() {
			if (this.busy) return false;
			if (this.dirty || this.uncertain) {
				this.error = "";
				this.dispatch({ type: "discard" });
				return false;
			}
			return true;
		},
		title(row) {
			return row.document.context || row.document.script_path || (row.document.latest_versionless || row.document.current_versionless ? t("Versionless") : t("Default"));
		},
		async call(action, values = {}) {
			return (await rpc("execute_cmd", [
				{
					ticket: this.context.ticket,
					project: this.context.project,
					language: "python"
				},
				"tactic.ui.panel.naming_cmd.NamingCmd",
				{
					action,
					project_code: this.context.project,
					search_type: this.context.searchType,
					...values
				}
			])).info;
		},
		contextChanged() {
			this.request++;
			this.busy = false;
			this.document = null;
			this.baseline = "null";
			this.identity = "";
			this.sample.key = "";
			this.uncertain = false;
			this.ui = initial();
			this.reload();
		},
		select(row, confirmed = false) {
			if (row?.identity === this.identity || !confirmed && !this.canLeave()) return;
			this.identity = row?.identity || "";
			this.document = row ? { ...row.document } : null;
			this.baseline = JSON.stringify(this.document);
			this.preview = null;
			this.error = "";
			this.message = "";
		},
		accept(result, preserve = false) {
			this.rules = result.rules;
			this.items = result.items;
			this.itemCount = result.itemCount;
			this.itemOffset = result.itemOffset;
			this.revision = result.revision;
			this.uncertain = false;
			if (!preserve) {
				const row = this.rules.find((item) => item.identity === result.identity) || this.rules[0];
				this.identity = row?.identity || "";
				this.document = row ? { ...row.document } : null;
				this.baseline = JSON.stringify(this.document);
			}
			if (!this.sample.key && this.items.length) this.sample.key = this.items[0].key;
			this.preview = null;
		},
		async reload(offset = 0, preserve = false, confirmed = false) {
			if (this.busy || !preserve && !confirmed && !this.canLeave()) return;
			const id = ++this.request;
			this.context = {
				ticket: this.ticket,
				project: this.project,
				searchType: this.searchType
			};
			this.busy = true;
			this.error = "";
			try {
				const result = await this.call("load", { object_offset: offset });
				if (id === this.request) this.accept(result, preserve);
			} catch (error) {
				if (id === this.request) this.error = error.message;
			} finally {
				if (id === this.request) this.busy = false;
			}
		},
		create(duplicate = false, confirmed = false) {
			if (!this.editable || !confirmed && !this.canLeave()) return;
			const copy = duplicate && this.document ? { ...this.document } : Object.fromEntries(fields.map((key) => [key, flags.includes(key) ? false : ""]));
			if (!duplicate) Object.assign(copy, {
				search_type: this.searchType,
				context: this.sample.context,
				checkin_type: "strict",
				dir_naming: "{project.code}/{search_type.table_name}/{sobject.code}/{snapshot.context}/versions",
				file_naming: "{sobject.name}_v{version}.{ext}"
			});
			this.identity = "";
			this.document = copy;
			this.baseline = "";
			this.preview = null;
			this.error = "";
			this.message = duplicate ? "Duplicated rule is local until Save is pressed." : "New rule is local until Save is pressed.";
		},
		async save(confirmed = false) {
			if (!this.editable || !this.dirty || !this.document) return;
			if (!confirmed && this.identity && !window.confirm(t("Update project naming rule? This changes future check-ins in the current project. Existing files are kept."))) return;
			const id = this.request;
			this.busy = true;
			this.error = "";
			try {
				const result = await this.call("save", {
					identity: this.identity,
					document: this.document,
					expected_revision: this.revision,
					object_offset: this.itemOffset
				});
				if (id === this.request) {
					this.accept(result);
					this.message = "Naming rule saved.";
					this.$emit("saved");
				}
			} catch (error) {
				if (id === this.request) {
					this.uncertain = !error.status || error.status >= 500;
					this.error = this.uncertain ? "The save result is unknown. Refresh before trying again." : error.message;
				}
			} finally {
				if (id === this.request) this.busy = false;
			}
		},
		async evaluate(allowExecution = false, confirmed = false) {
			if (!this.editable || !this.document || !this.sample.key) return;
			if (!confirmed && allowExecution && !window.confirm(t("Run custom naming code? This uses the normal server environment, not an isolated sandbox. Scripts and classes can change data or files."))) return;
			const id = this.request;
			this.busy = true;
			this.error = "";
			this.preview = null;
			try {
				const result = await this.call("preview", {
					identity: this.identity,
					document: this.document,
					sample: this.sample,
					allow_execution: allowExecution
				});
				if (id === this.request) this.preview = result;
			} catch (error) {
				if (id === this.request) this.error = error.message;
			} finally {
				if (id === this.request) this.busy = false;
			}
		}
	}
};
var _hoisted_1 = ["aria-label", "aria-busy"];
var _hoisted_2 = {
	ref: "body",
	class: "frame-host-body"
};
function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
	const _component_FrameView = resolveComponent("FrameView");
	return openBlock(), createElementBlock("section", {
		class: "naming-editor frame-host",
		"aria-label": $options.t("Naming editor"),
		"aria-busy": _ctx.busy
	}, [(openBlock(), createBlock(Teleport, {
		to: $props.toolbarTarget || "body",
		disabled: !$props.toolbarTarget
	}, [withDirectives(createBaseVNode("div", {
		class: "frame-toolbar-host",
		style: normalizeStyle({ width: _ctx.toolbarSize + "px" })
	}, [createVNode(_component_FrameView, {
		scene: $options.toolbarScene,
		onEvent: $options.dispatch
	}, null, 8, ["scene", "onEvent"])], 4), [[vShow, $props.presentationVisible]])], 8, ["to", "disabled"])), createBaseVNode("div", _hoisted_2, [createVNode(_component_FrameView, {
		scene: $options.frameScene,
		models: $options.models,
		"describe-row": $options.rowScene,
		onEvent: $options.dispatch
	}, null, 8, [
		"scene",
		"models",
		"describe-row",
		"onEvent"
	])], 512)], 8, _hoisted_1);
}
var NamingEditor_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { NamingEditor_exports as n, NamingEditor_default as t };

//# sourceMappingURL=NamingEditor.js.map