const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["assets/ApiDocumentation.js","assets/vue.js","assets/clipboard.js","assets/AppSwitch.js","assets/AppSelect.js","assets/AppSelect.css","assets/SettingRow.js","assets/SettingRow.css","assets/clipboard.css","assets/App.js","assets/resize.js","assets/icons.js","assets/AppTextField.js","assets/AppTextField.css","assets/AppDateField.js","assets/AppSlider.js","assets/AppSlider.css","assets/AppMenu.js","assets/AppMenu.css","assets/AppDateField.css","assets/AppCheckbox.js","assets/AppCheckbox.css","assets/ItemPreview.js","assets/ItemPreview.css","assets/AppTextArea.js","assets/AppTextArea.css","assets/UserComboBox.js","assets/AppSearchField.js","assets/AppSearchField.css","assets/UserComboBox.css","assets/AppSplitter.js","assets/ItemSurface.js","assets/ItemSurface.css","assets/resize.css","assets/RecordForm.js","assets/RecordForm.css","assets/links.js","assets/files.js","assets/AppMenuItem.js","assets/AppMenuItem.css","assets/tree.ui.js","assets/previewImage.js","assets/App.css"])))=>i.map(i=>d[i]);
import { C as h, F as renderSlot, G as withCtx, H as watch, K as withDirectives, N as openBlock, P as renderList, R as resolveDynamicComponent, S as defineAsyncComponent, U as watchEffect, X as ref, Y as reactive, Z as shallowReactive, _ as createCommentVNode, d as Fragment, et as unref, g as createBlock, h as createBaseVNode, i as render, j as onMounted, k as onBeforeUnmount, m as computed, nt as normalizeStyle, p as Teleport, r as createApp, rt as toDisplayString, tt as normalizeClass, u as withModifiers, v as createElementBlock } from "./vue.js";
import { n as en_default, t as ru_default } from "./locales.js";
import { n as resolveIcon } from "./icons.js";
//#region \0vite/modulepreload-polyfill.js
(function polyfill() {
	const relList = document.createElement("link").relList;
	if (relList && relList.supports && relList.supports("modulepreload")) return;
	for (const link of document.querySelectorAll("link[rel=\"modulepreload\"]")) processPreload(link);
	new MutationObserver((mutations) => {
		for (const mutation of mutations) {
			if (mutation.type !== "childList") continue;
			for (const node of mutation.addedNodes) if (node.tagName === "LINK" && node.rel === "modulepreload") processPreload(node);
		}
	}).observe(document, {
		childList: true,
		subtree: true
	});
	function getFetchOpts(link) {
		const fetchOpts = {};
		if (link.integrity) fetchOpts.integrity = link.integrity;
		if (link.referrerPolicy) fetchOpts.referrerPolicy = link.referrerPolicy;
		if (link.crossOrigin === "use-credentials") fetchOpts.credentials = "include";
		else if (link.crossOrigin === "anonymous") fetchOpts.credentials = "omit";
		else fetchOpts.credentials = "same-origin";
		return fetchOpts;
	}
	function processPreload(link) {
		if (link.ep) return;
		link.ep = true;
		const fetchOpts = getFetchOpts(link);
		fetch(link.href, fetchOpts);
	}
})();
//#endregion
//#region \0plugin-vue:export-helper
var _plugin_vue_export_helper_default = (sfc, props) => {
	const target = sfc.__vccOpts || sfc;
	for (const [key, val] of props) target[key] = val;
	return target;
};
var BusyIndicator_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "BusyIndicator",
	props: { running: Boolean },
	setup(__props) {
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("span", {
				class: normalizeClass(["busy-indicator", { running: __props.running }]),
				"aria-hidden": "true"
			}, null, 2);
		};
	}
}, [["__scopeId", "data-v-bc754be8"]]);
//#endregion
//#region src/appearanceCatalog.js
var themes = [
	{
		"value": "md3",
		"label": "Material Design 3",
		"description": "Current TACTIC-Handler appearance"
	},
	{
		"value": "material5",
		"label": "Material Design 5 (preview)",
		"description": "Experimental project theme, not an official specification"
	},
	{
		"value": "fluent",
		"label": "Fluent Design",
		"description": "Compact Windows-oriented surfaces and motion"
	}
];
var iconSets = [
	{
		"value": "automatic",
		"label": "Automatic",
		"description": "Material-first icons with safe fallbacks"
	},
	{
		"value": "fontawesome-solid",
		"label": "Font Awesome Solid",
		"description": "Bold, filled application icons"
	},
	{
		"value": "fontawesome-outline",
		"label": "Font Awesome Outline",
		"description": "Lighter outlined icons where available"
	},
	{
		"value": "material-design",
		"label": "Material Design Icons",
		"description": "Material Design icon vocabulary"
	},
	{
		"value": "fluent-regular",
		"label": "Fluent Regular",
		"description": "Modern outlined Fluent System icons"
	},
	{
		"value": "fluent-filled",
		"label": "Fluent Filled",
		"description": "Modern filled Fluent System icons"
	}
];
var accentPresets = [
	{
		"value": "steel",
		"label": "Steel",
		"light": "#3d7599",
		"dark": "#78a6c4",
		"lightBase": "#d4dce1",
		"darkBase": "#292d30"
	},
	{
		"value": "silver",
		"label": "Silver",
		"light": "#67717a",
		"dark": "#b4bec6",
		"lightBase": "#d9dde0",
		"darkBase": "#303336"
	},
	{
		"value": "ash",
		"label": "Ash",
		"light": "#656662",
		"dark": "#adafaa",
		"lightBase": "#d8d8d6",
		"darkBase": "#2e2e2c"
	},
	{
		"value": "graphite",
		"label": "Graphite",
		"light": "#535a60",
		"dark": "#9da5ab",
		"lightBase": "#d2d4d5",
		"darkBase": "#27292b"
	},
	{
		"value": "charcoal",
		"label": "Charcoal",
		"light": "#41494f",
		"dark": "#89939a",
		"lightBase": "#ccd0d2",
		"darkBase": "#202326"
	},
	{
		"value": "blue",
		"label": "Blue",
		"light": "#2563a6",
		"dark": "#6ea8e6",
		"lightBase": "#d6dce8",
		"darkBase": "#272d36"
	},
	{
		"value": "azure",
		"label": "Azure",
		"light": "#0078b8",
		"dark": "#62b3dc",
		"lightBase": "#d2dfe5",
		"darkBase": "#253037"
	},
	{
		"value": "cyan",
		"label": "Cyan",
		"light": "#007c91",
		"dark": "#5bc0d1",
		"lightBase": "#d0dfe1",
		"darkBase": "#253234"
	},
	{
		"value": "teal",
		"label": "Teal",
		"light": "#087f6a",
		"dark": "#5abfa9",
		"lightBase": "#d2dfdc",
		"darkBase": "#263330"
	},
	{
		"value": "emerald",
		"label": "Emerald",
		"light": "#27824c",
		"dark": "#65b982",
		"lightBase": "#d5dfd8",
		"darkBase": "#29332c"
	},
	{
		"value": "green",
		"label": "Green",
		"light": "#4c7d28",
		"dark": "#86b85a",
		"lightBase": "#d9dfd3",
		"darkBase": "#2d3328"
	},
	{
		"value": "lime",
		"label": "Lime",
		"light": "#637a1b",
		"dark": "#a5bd4f",
		"lightBase": "#dde0d2",
		"darkBase": "#303326"
	},
	{
		"value": "amber",
		"label": "Amber",
		"light": "#946500",
		"dark": "#d5ad48",
		"lightBase": "#e3dccb",
		"darkBase": "#373126"
	},
	{
		"value": "orange",
		"label": "Orange",
		"light": "#a65316",
		"dark": "#e08b4e",
		"lightBase": "#e2d7cf",
		"darkBase": "#372d27"
	},
	{
		"value": "coral",
		"label": "Coral",
		"light": "#a4483c",
		"dark": "#de786b",
		"lightBase": "#e2d5d2",
		"darkBase": "#372b2a"
	},
	{
		"value": "red",
		"label": "Red",
		"light": "#a93f4d",
		"dark": "#de7180",
		"lightBase": "#e1d3d5",
		"darkBase": "#36292c"
	},
	{
		"value": "rose",
		"label": "Rose",
		"light": "#a83e78",
		"dark": "#dd75a9",
		"lightBase": "#e2d3db",
		"darkBase": "#362a31"
	},
	{
		"value": "violet",
		"label": "Violet",
		"light": "#76558d",
		"dark": "#b49ac8",
		"lightBase": "#ddd5e1",
		"darkBase": "#322d36"
	},
	{
		"value": "indigo",
		"label": "Indigo",
		"light": "#4f5ea8",
		"dark": "#8b99e0",
		"lightBase": "#d8d8e4",
		"darkBase": "#2d2e38"
	}
];
var defaultThemeAccents = {
	"md3": {
		"light": "steel",
		"dark": "steel"
	},
	"material5": {
		"light": "violet",
		"dark": "violet"
	},
	"fluent": {
		"light": "azure",
		"dark": "azure"
	}
};
//#endregion
//#region src/features/tasks/taskColumns.js
var taskColumns = [
	[
		"object",
		"Object",
		"object"
	],
	[
		"process",
		"Task / Process",
		"process"
	],
	[
		"status",
		"Status",
		"status"
	],
	[
		"assigned",
		"Assignee",
		"user"
	],
	[
		"dates",
		"Start / Deadline",
		"due"
	],
	[
		"progress",
		"Progress",
		""
	],
	[
		"bid_duration",
		"Hours",
		""
	],
	[
		"notes",
		"Notes",
		""
	],
	[
		"priority",
		"Priority",
		"priority"
	],
	[
		"milestone_code",
		"Milestone",
		"milestone"
	],
	[
		"supervisor",
		"Supervisor",
		"supervisor"
	]
].map(([key, label, sort], index) => ({
	key,
	label,
	sort,
	width: [
		210,
		126,
		138,
		154,
		112,
		94,
		86,
		48,
		96,
		132,
		154
	][index],
	visible: index < 8,
	group: {
		object: "object",
		process: "process",
		status: "status",
		assigned: "user"
	}[key] || ""
}));
function normalizeColumns(saved) {
	const ordered = [], seen = /* @__PURE__ */ new Set();
	for (const item of Array.isArray(saved) ? saved : []) {
		const original = taskColumns.find((column) => column.key === item?.key);
		if (!original || seen.has(item.key)) continue;
		const width = Number(item.width);
		ordered.push({
			...original,
			width: Number.isFinite(width) ? Math.max(40, Math.min(480, Math.trunc(width))) : original.width,
			visible: item.key === "object" || (typeof item.visible === "boolean" ? item.visible : original.visible)
		});
		seen.add(item.key);
	}
	return [...ordered, ...taskColumns.filter((column) => !seen.has(column.key)).map((column) => ({ ...column }))];
}
//#endregion
//#region src/features/configuration/preferences.js
var configurationPreview = ref(false);
var preferenceDefaults = {
	checkin: {
		displayLimit: 20,
		defaultViewMode: "continious",
		loadingMode: "pages",
		keepFilename: false,
		groupCheckin: true,
		includeSubfolders: false,
		generatePreviews: true,
		confirmRevision: true,
		commitQueueAutoClean: true
	},
	tasks: {
		workspaceSurface: "browser",
		quickViewMode: "cards",
		viewMode: "table",
		sortMode: "due",
		groupMode: "process",
		inspectorExpanded: false,
		columns: []
	},
	global: {
		activityNotifications: true,
		messageNotifications: true
	},
	cache: { cacheProcessTabs: true },
	repository: {
		enabledAliases: null,
		defaultAlias: "default"
	}
};
function normalizePreferences(value = {}) {
	const result = structuredClone(preferenceDefaults);
	for (const [page, fields] of Object.entries(result)) for (const [key, fallback] of Object.entries(fields)) {
		const saved = value?.[page]?.[key];
		if (typeof fallback === "boolean" && typeof saved === "boolean") fields[key] = saved;
	}
	for (const [page, fields] of Object.entries({
		checkin: {
			defaultViewMode: [
				"continious",
				"tiles",
				"table",
				"compact",
				"splitted_vertical",
				"splitted_horizontal"
			],
			loadingMode: ["pages", "infinite"]
		},
		tasks: {
			workspaceSurface: ["browser", "quick"],
			quickViewMode: ["cards", "compact"],
			viewMode: ["table", "gantt"],
			sortMode: [
				"due",
				"recent",
				"user",
				"process",
				"status",
				"object",
				"search_type",
				"project",
				"priority",
				"milestone",
				"supervisor"
			],
			groupMode: [
				"none",
				"user",
				"process",
				"status",
				"object"
			]
		}
	})) for (const [key, allowed] of Object.entries(fields)) if (allowed.includes(value?.[page]?.[key])) result[page][key] = value[page][key];
	const limit = Number(value?.checkin?.displayLimit);
	if (Number.isFinite(limit) && limit > 0) result.checkin.displayLimit = Math.max(1, Math.min(500, Math.trunc(limit)));
	result.tasks.columns = normalizeColumns(value?.tasks?.columns);
	const alias = (value) => typeof value === "string" && /^[A-Za-z0-9_.-]+$/.test(value) && value !== "plugins";
	if (Array.isArray(value?.repository?.enabledAliases)) result.repository.enabledAliases = [...new Set(value.repository.enabledAliases.filter(alias))];
	if (alias(value?.repository?.defaultAlias)) result.repository.defaultAlias = value.repository.defaultAlias;
	return result;
}
var saved$1;
try {
	saved$1 = JSON.parse(localStorage.getItem("tactic_stream.preferences") || "null");
} catch {}
var preferences = reactive(normalizePreferences(saved$1));
function savePreferencePage(page, value) {
	const next = normalizePreferences({
		...preferences,
		[page]: value
	});
	localStorage.setItem("tactic_stream.preferences", JSON.stringify(next));
	Object.assign(preferences[page], next[page]);
}
//#endregion
//#region ../src/tactic_stream/shared_ui/core/interaction.mjs
function buttonVisual(state = {}) {
	const enabled = state.enabled !== false && !state.loading;
	const active = state.hovered || state.focused;
	let background = "surfaceContainerHigh";
	let content = "primaryText";
	if (state.segmented) {
		background = !enabled ? "transparent" : state.pressed ? "surfaceContainerHighest" : state.checked ? "selected" : active ? "rowHover" : "transparent";
		content = state.checked ? "selectedText" : "secondaryText";
	} else if (enabled) {
		if (state.pressed) background = state.destructive && state.highlighted ? "error" : "selected";
		else if (state.highlighted) background = state.destructive ? "error" : "action";
		else if (active) background = "rowHover";
		else if (state.tonal) background = "secondaryContainer";
		content = state.destructive ? state.highlighted ? "onError" : "error" : state.highlighted ? "selectedText" : "primaryText";
	}
	return {
		background,
		content: enabled ? content : "disabledText",
		border: state.destructive ? "error" : "outlineVariant",
		borderWidth: state.segmented || state.highlighted || state.flat ? 0 : 1,
		pressedMix: enabled && state.pressed && state.destructive && state.highlighted
	};
}
function fieldVisual(state = {}) {
	return {
		background: state.tableCell && !state.focused ? "transparent" : "surfaceContainerHigh",
		content: state.enabled === false ? "disabledText" : "primaryText",
		border: state.error ? "error" : state.focused ? "action" : "outline",
		borderWidth: state.focused ? 2 : state.tableCell ? 0 : 1
	};
}
function checkVisual(state = {}) {
	const selected = state.checked || state.mixed;
	const disabled = state.enabled === false;
	return {
		background: selected ? disabled ? "surfaceContainerHigh" : "action" : state.prominent ? "surfaceContainerHighest" : "transparent",
		content: disabled ? "disabledText" : "primaryText",
		mark: disabled ? "disabledText" : "selectedText",
		border: disabled ? "disabledText" : selected || state.focused ? "action" : state.prominent ? "secondaryText" : "outline",
		borderWidth: state.focused || state.prominent ? 2 : 1
	};
}
function switchVisual(state = {}) {
	const disabled = state.enabled === false;
	return {
		background: disabled ? "surfaceContainerHigh" : state.checked ? "action" : "surfaceContainerHighest",
		border: disabled ? "disabledText" : state.checked || state.focused ? "action" : "outline",
		thumb: disabled ? "disabledText" : state.checked ? "selectedText" : "secondaryText",
		borderWidth: state.focused ? 2 : 1
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/core/foundation.mjs
var typography = {
	micro: 8,
	caption: 8.25,
	label: 8.75,
	body: 9.25,
	bodyLarge: 10,
	title: 12
};
var fontFamily = "Segoe UI";
function fontLineHeight(pixelSize) {
	return Math.ceil(pixelSize * 1.328125);
}
var lineHeights = Object.freeze({
	menuHeading: 14,
	caption: 15,
	secondary: 16,
	body: 18,
	bodyLarge: 19,
	section: 20,
	title: 22,
	heading: 23,
	display: 24,
	hero: 32
});
var textStyles = Object.freeze({
	menuHeading: 10,
	caption: 11,
	secondary: 12,
	body: 13,
	bodyLarge: 14,
	section: 15,
	title: 16,
	heading: 17,
	display: 18,
	hero: 24
});
var controls = {
	document: {
		bodySize: 12,
		lineHeight: 17,
		headingSize: 18,
		headingLineHeight: 22.5,
		paragraphGap: 8,
		headingGap: 14,
		cellPadding: 4
	},
	field: {
		padding: 12,
		areaPadding: 10
	},
	choice: {
		rowHeight: 34,
		visibleRows: 8,
		popupPadding: 4,
		popupGap: 4
	},
	tooltip: {
		delay: 500,
		timeout: 5e3,
		margin: 8,
		paddingX: 12,
		paddingY: 7,
		radius: 6
	},
	userPicker: {
		popupWidth: 294,
		popupHeight: 286,
		rowHeight: 48,
		avatarSize: 32
	},
	calendar: {
		popupWidth: 304,
		padding: 10,
		rowHeight: 30,
		daySize: 28
	},
	colorPicker: {
		popupWidth: 380,
		planeHeight: 190,
		padding: 20
	},
	iconPicker: {
		popupWidth: 560,
		popupHeight: 440
	},
	button: {
		minimumWidth: 72,
		padding: 16,
		iconPadding: 12,
		spacing: 7,
		segmentedSpacing: 6,
		segmentedPaddingStart: 3,
		segmentedPaddingEnd: 7,
		iconSize: 16,
		compactIconSize: 18,
		segmentedIconSize: 15
	},
	iconButton: {
		extent: 28,
		iconSize: 17,
		surfaceInset: 2,
		hoveredOpacity: .08,
		pressedOpacity: .12
	},
	checkBox: {
		height: 36,
		compactHeight: 30,
		spacing: 9,
		compactSpacing: 6,
		indicator: 19,
		compactIndicator: 17,
		prominentIndicator: 22,
		iconSize: 15,
		compactIconSize: 13,
		prominentIconSize: 17,
		radius: 5
	},
	switch: {
		width: 42,
		height: 24,
		thumb: 18,
		inset: 3,
		spacing: 10
	},
	search: {
		padding: 38,
		iconInset: 12,
		iconSize: 18,
		clearInset: 4,
		clearExtent: 30,
		clearIconSize: 17,
		popupMinimumWidth: 240,
		popupPadding: 4,
		popupGap: 6,
		rowHeight: 34
	},
	number: {
		indicatorWidth: 34,
		iconSize: 14
	},
	feedback: {
		progressHeight: 4,
		busyExtent: 24
	},
	slider: {
		height: 26,
		track: 4,
		thumb: 16,
		thumbBorder: 2,
		padding: 6
	},
	identity: {
		avatarSize: 40,
		spacing: 12,
		textSpacing: 3
	},
	summaryChip: {
		height: 30,
		compactHeight: 24,
		spacing: 7,
		padding: 10,
		compactPadding: 8,
		dot: 8
	},
	filterChip: {
		height: 32,
		emphasisHeight: 12,
		iconSize: 11,
		emphasisIconSize: 4,
		emphasisFontSize: 11
	},
	loadingOverlay: {
		spacing: 10,
		surfaceOpacity: .88,
		minimumWidth: 180,
		maximumWidth: 420,
		horizontalMargin: 40
	},
	statusChip: {
		height: 24,
		denseHeight: 20,
		spacing: 5,
		padding: 8,
		densePadding: 5,
		iconSize: 13,
		denseIconSize: 11
	},
	reactionChip: {
		height: 28,
		padding: 8,
		spacing: 5,
		emojiSize: 18,
		tintOpacity: .18,
		checkedTintOpacity: .34
	},
	editorPanel: {
		padding: 14,
		spacing: 12,
		contentSpacing: 10,
		headerSpacing: 10,
		textSpacing: 3,
		actionsSpacing: 6,
		iconSize: 20
	},
	formField: {
		padding: 14,
		labelWidth: 220,
		columnSpacing: 20,
		rowSpacing: 12,
		iconExtent: 34,
		iconSize: 17,
		labelSpacing: 11,
		textSpacing: 2,
		editorSpacing: 5,
		compactBreakpoint: 700
	},
	editorListItem: {
		padding: 12,
		spacing: 10,
		iconSize: 19,
		textSpacing: 4,
		minimumExtraHeight: 12
	},
	emptyState: {
		height: 140,
		iconSize: 30,
		spacing: 8,
		maximumWidth: 440,
		horizontalMargin: 24
	},
	dropTarget: {
		margin: 6,
		borderWidth: 2,
		iconSize: 30,
		spacing: 8,
		textSize: 12,
		surfaceOpacity: .94
	},
	imagePicker: {
		previewSize: 112,
		minimumActionsWidth: 290,
		columnSpacing: 16,
		rowSpacing: 12
	},
	splitter: {
		extent: 10,
		thickness: 3,
		length: 40,
		restingOpacity: .28,
		hoveredOpacity: .85,
		pressedOpacity: 1
	},
	scrollBar: {
		extent: 12,
		restingTrack: 6,
		expandedTrack: 11,
		restingThumb: 5,
		expandedThumb: 8,
		restingTrackOpacity: .055,
		expandedTrackOpacity: .15,
		restingThumbOpacity: .42,
		hoveredThumbOpacity: .72,
		pressedThumbOpacity: .9,
		disabledThumbOpacity: .18
	}
};
var styleMetrics = {
	md3: {
		controlHeight: 36,
		compactControlHeight: 32,
		fieldRadius: 10,
		buttonRadius: 18,
		itemRadius: 9,
		snapshotRadius: 5,
		surfaceRadius: 12,
		sectionRadius: 16,
		dialogRadius: 20,
		menuRadius: 16,
		iconButtonRadius: 4,
		communicationGroupedSpacing: 2,
		communicationGroupTailSize: 10,
		communicationBubbleRadius: 14,
		communicationGroupedBubbleRadius: 8,
		baseMotionInstant: 28,
		baseMotionFast: 48,
		baseMotionMedium: 56,
		baseMotionSlow: 72,
		baseMotionExtended: 104
	},
	material5: {
		controlHeight: 38,
		compactControlHeight: 34,
		fieldRadius: 15,
		buttonRadius: 16,
		itemRadius: 13,
		snapshotRadius: 10,
		surfaceRadius: 18,
		sectionRadius: 22,
		dialogRadius: 28,
		menuRadius: 20,
		iconButtonRadius: 9,
		communicationGroupedSpacing: 3,
		communicationGroupTailSize: 11,
		communicationBubbleRadius: 16,
		communicationGroupedBubbleRadius: 10,
		baseMotionInstant: 36,
		baseMotionFast: 60,
		baseMotionMedium: 76,
		baseMotionSlow: 96,
		baseMotionExtended: 128
	},
	fluent: {
		controlHeight: 34,
		compactControlHeight: 32,
		fieldRadius: 5,
		buttonRadius: 5,
		itemRadius: 5,
		snapshotRadius: 3,
		surfaceRadius: 7,
		sectionRadius: 8,
		dialogRadius: 8,
		menuRadius: 8,
		iconButtonRadius: 4,
		communicationGroupedSpacing: 2,
		communicationGroupTailSize: 10,
		communicationBubbleRadius: 7,
		communicationGroupedBubbleRadius: 4,
		baseMotionInstant: 24,
		baseMotionFast: 36,
		baseMotionMedium: 48,
		baseMotionSlow: 64,
		baseMotionExtended: 88
	}
};
var layout = {
	appBarHeight: 44,
	sectionRailWidth: 48,
	dockTitleHeight: 38,
	dockWorkspaceHeaderHeight: 96,
	dockWorkspaceFooterHeight: 58,
	communicationListSpacing: 10,
	communicationBubblePadding: 10,
	communicationContentSpacing: 6,
	communicationAvatarSpacing: 8,
	scrollbarExtent: 12,
	splitterExtent: 10,
	windowMargin: 16,
	dragThreshold: 5
};
function metrics(style) {
	return Object.assign({}, layout, styleMetrics[style] || styleMetrics.md3);
}
function motion(style, preferences) {
	const values = metrics(style), flags = preferences || {}, result = {};
	for (const duration of [
		"Instant",
		"Fast",
		"Medium",
		"Slow",
		"Extended"
	]) {
		const value = values["baseMotion" + duration];
		result["motion" + duration] = flags.fade === false || flags.reduced ? 0 : value;
		result["clickMotion" + duration] = flags.click === false || flags.reduced ? 0 : value;
		result["hoverMotion" + duration] = flags.hover === false || flags.reduced ? 0 : value;
		result["popupMotion" + duration] = flags.popup === false || flags.reduced ? 0 : value;
	}
	result.scrollMotion = result.motionInstant;
	return result;
}
function blend(first, second, weight) {
	const amount = Math.max(0, Math.min(1, weight));
	return first.map((channel, index) => channel * (1 - amount) + second[index] * amount);
}
function readableText$1(color) {
	return (color[0] * .2126 + color[1] * .7152 + color[2] * .0722) / 255 > .56 ? [
		23,
		32,
		39
	] : [
		246,
		248,
		250
	];
}
function rgb(hex) {
	return [
		1,
		3,
		5
	].map((offset) => parseInt(hex.slice(offset, offset + 2), 16));
}
function palette(style, dark, base, accent) {
	const black = [
		0,
		0,
		0
	], white = [
		255,
		255,
		255
	];
	const material = style === "material5", fluent = style === "fluent";
	const colors = {
		action: accent,
		blackMix: black,
		whiteMix: white
	};
	colors.paletteBase = material ? blend(base, accent, dark ? .07 : .05) : base;
	const surface = colors.paletteBase;
	colors.workspace = blend(surface, dark ? black : white, dark ? fluent ? .23 : .34 : fluent ? .12 : .08);
	colors.topBar = blend(surface, dark ? white : black, dark ? material ? .05 : .03 : .03);
	colors.toolBar = blend(surface, dark ? white : black, dark ? material ? .11 : .08 : .07);
	colors.panel = blend(surface, dark ? black : white, dark ? .04 : .22);
	colors.panelRaised = blend(surface, white, dark ? .08 : .38);
	colors.panelDeep = blend(surface, black, dark ? .19 : .08);
	colors.row = blend(surface, white, dark ? .07 : .32);
	colors.rowHover = blend(colors.row, accent, dark ? .1 : .08);
	colors.selected = blend(accent, colors.panelRaised, dark ? .28 : .3);
	colors.contentSelection = blend(accent, colors.workspace, dark ? .68 : .72);
	colors.primaryText = readableText$1(colors.workspace);
	colors.contentAccent = blend(accent, colors.primaryText, dark ? .12 : .08);
	colors.selectedText = readableText$1(colors.selected);
	colors.contentSelectionText = readableText$1(colors.contentSelection);
	colors.secondaryText = blend(colors.primaryText, surface, dark ? .35 : .42);
	colors.disabledText = blend(colors.secondaryText, surface, .42);
	colors.separator = blend(surface, colors.primaryText, dark ? .11 : .18);
	colors.border = blend(surface, colors.primaryText, dark ? .24 : .3);
	const fixed = {
		green: "#52a86e",
		yellow: "#d5bd51",
		red: "#d65b67",
		missingFile: "#d45b5b",
		violet: "#a06bb4",
		cyan: "#56a7b3"
	};
	for (const name of Object.keys(fixed)) colors[name] = rgb(fixed[name]);
	const syntax = {
		Keyword: ["#d5bd51", "#808000"],
		String: ["#69b77d", "#008000"],
		Comment: ["#70a87a", "#008000"],
		Number: ["#66b8c4", "#000080"],
		Type: ["#bc84cf", "#800080"],
		Function: ["#66b8c4", "#00677c"],
		Definition: ["#d39562", "#7c4800"],
		Self: ["#88aac4", "#092e64"],
		Occurrence: ["#55545a", "#b4b4b4"],
		Search: ["#75651f", "#ffef0b"]
	};
	for (const name of Object.keys(syntax)) colors["syntax" + name] = rgb(syntax[name][dark ? 0 : 1]);
	colors.titleGreen = rgb(dark ? "#4c8700" : "#5f970d");
	colors.ripple = (dark ? white : black).concat((dark ? 52 : 34) / 255);
	colors.rippleStrong = (dark ? white : black).concat((dark ? 56 : 36) / 255);
	colors.popupShadow = black.concat((dark ? 74 : 40) / 255);
	colors.dialogShadow = black.concat((dark ? 82 : 48) / 255);
	colors.scrim = black.concat((dark ? 153 : 115) / 255);
	const aliases = {
		tooltipSurface: "panelRaised",
		tooltipText: "primaryText",
		background: "workspace",
		surface: "panel",
		surfaceContainerLow: "panel",
		surfaceContainer: "toolBar",
		surfaceContainerHigh: "panelRaised",
		surfaceContainerHighest: "rowHover",
		surfaceVariant: "toolBar",
		outline: "border",
		outlineVariant: "separator",
		primary: "action",
		primaryContainer: "selected",
		secondary: "secondaryText",
		secondaryContainer: "rowHover",
		tertiary: "violet",
		tertiaryContainer: "rowHover",
		error: "red",
		errorContainer: "rowHover",
		text: "primaryText",
		muted: "secondaryText",
		accent: "action",
		accentContainer: "selected"
	};
	for (const name of Object.keys(aliases)) colors[name] = colors[aliases[name]];
	colors.onError = readableText$1(colors.error);
	colors.inverseSurface = rgb("#eeeeee");
	colors.inverseOnSurface = rgb("#202020");
	return colors;
}
var cssRoles = {
	workspace: "--page",
	topBar: "--header",
	toolBar: "--surface-container",
	panel: "--surface",
	panelRaised: "--surface-high",
	panelDeep: "--surface-deep",
	row: "--row",
	rowHover: "--hover",
	selected: "--selected",
	selectedText: "--on-selected",
	contentSelection: "--content-selection",
	contentSelectionText: "--on-content-selection",
	contentAccent: "--content-accent",
	primaryText: "--on-surface",
	secondaryText: "--muted",
	disabledText: "--disabled",
	border: "--outline",
	separator: "--outline-variant",
	action: "--primary",
	red: "--error",
	green: "--success",
	yellow: "--yellow",
	cyan: "--cyan",
	violet: "--violet",
	surfaceContainerLow: "--surface",
	surfaceContainer: "--surface-container",
	surfaceContainerHigh: "--surface-high",
	surfaceContainerHighest: "--surface-highest",
	secondaryContainer: "--secondary-container",
	outline: "--outline",
	outlineVariant: "--outline-variant",
	error: "--error",
	errorContainer: "--error-container",
	onError: "--on-error",
	ripple: "--ripple-color",
	popupShadow: "--shadow-color",
	scrim: "--scrim"
};
function cssColor(channels) {
	return "rgba(" + channels.slice(0, 3).join(",") + "," + (channels.length === 4 ? channels[3] : 1) + ")";
}
function cssVariables(style, dark, base, accent, preferences) {
	const colors = palette(style, dark, base, accent), values = metrics(style), result = {};
	for (const role of Object.keys(cssRoles)) result[cssRoles[role]] = cssColor(colors[role]);
	for (const name of Object.keys(values)) {
		const cssName = "--" + name.replace(/[A-Z]/g, (letter) => "-" + letter.toLowerCase());
		result[cssName] = values[name] + (name.indexOf("baseMotion") === 0 ? "ms" : "px");
	}
	for (const name of Object.keys(typography)) {
		const cssName = "--text-" + name.replace(/[A-Z]/g, (letter) => "-" + letter.toLowerCase());
		result[cssName] = typography[name] + "pt";
	}
	result["--control-text-size"] = textStyles.body + "px";
	result["--control-compact-text-size"] = textStyles.secondary + "px";
	for (const role of Object.keys(textStyles)) {
		const name = role.replace(/[A-Z]/g, (letter) => "-" + letter.toLowerCase());
		result["--font-" + name + "-size"] = textStyles[role] + "px";
		result["--font-" + name + "-line-height"] = lineHeights[role] + "px";
	}
	const states = {
		field: {
			idle: fieldVisual(),
			focus: fieldVisual({ focused: true }),
			error: fieldVisual({ error: true }),
			disabled: fieldVisual({ enabled: false })
		},
		check: {
			idle: checkVisual(),
			checked: checkVisual({ checked: true }),
			focus: checkVisual({ focused: true }),
			disabled: checkVisual({ enabled: false }),
			disabledChecked: checkVisual({
				checked: true,
				enabled: false
			})
		},
		switch: {
			idle: switchVisual(),
			checked: switchVisual({ checked: true }),
			focus: switchVisual({ focused: true }),
			disabled: switchVisual({ enabled: false })
		}
	};
	for (const [kind, variants] of Object.entries(states)) for (const [state, paint] of Object.entries(variants)) for (const [part, value] of Object.entries(paint)) {
		const name = ("--" + kind + "-" + state + "-" + part).replace(/[A-Z]/g, (letter) => "-" + letter.toLowerCase());
		result[name] = typeof value === "number" ? value + "px" : value === "transparent" ? value : cssColor(colors[value]);
	}
	for (const kind of Object.keys(controls)) for (const name of Object.keys(controls[kind])) {
		const cssName = "--" + (kind + name[0].toUpperCase() + name.slice(1)).replace(/[A-Z]/g, (letter) => "-" + letter.toLowerCase());
		result[cssName] = controls[kind][name] + (name.endsWith("Opacity") || name === "visibleRows" ? "" : name === "delay" || name === "timeout" ? "ms" : "px");
	}
	const timings = motion(style, preferences);
	for (const name of [
		"Instant",
		"Fast",
		"Medium",
		"Slow",
		"Extended"
	]) result["--motion-" + name.toLowerCase()] = timings["motion" + name] + "ms";
	const feedback = {
		"--motion-click": "clickMotionFast",
		"--motion-click-expansion": "clickMotionMedium",
		"--motion-click-slow": "clickMotionSlow",
		"--motion-click-extended": "clickMotionExtended",
		"--motion-hover": "hoverMotionFast",
		"--motion-hover-medium": "hoverMotionMedium",
		"--motion-fade": "motionMedium",
		"--motion-fade-slow": "motionSlow",
		"--motion-fade-extended": "motionExtended",
		"--motion-popup": "popupMotionMedium",
		"--motion-popup-fast": "popupMotionFast",
		"--motion-popup-slow": "popupMotionSlow"
	};
	for (const name of Object.keys(feedback)) result[name] = timings[feedback[name]] + "ms";
	for (const name of Object.keys(colors)) if (name.indexOf("syntax") === 0) result["--syntax-" + name.slice(6).toLowerCase()] = cssColor(colors[name]);
	result["--on-primary"] = cssColor(readableText$1(accent));
	result["--font-family"] = "\"Segoe UI\", system-ui, sans-serif";
	result["--communication-bubble-radius"] = values.communicationBubbleRadius + "px";
	result["--workspace-footer-height"] = values.dockWorkspaceFooterHeight + "px";
	result["--preview-radius"] = values.snapshotRadius + "px";
	return result;
}
//#endregion
//#region src/appearance.js
var languages = [{
	value: "en",
	label: "English"
}, {
	value: "ru",
	label: "Russian"
}];
var colorModes = [
	{
		value: "system",
		label: "System"
	},
	{
		value: "light",
		label: "Light"
	},
	{
		value: "dark",
		label: "Dark"
	}
];
var storageKey = "tactic_stream.appearance";
for (const [area, suffix] of [["localStorage", "appearance"], ["sessionStorage", "session"]]) try {
	const storage = window[area];
	const previousKey = `tactic_flow.${suffix}`;
	const nextKey = `tactic_stream.${suffix}`;
	const previous = storage.getItem(previousKey);
	if (previous && storage.getItem(nextKey) === null) storage.setItem(nextKey, previous);
	storage.removeItem(previousKey);
} catch {}
function readAppearance() {
	let saved;
	try {
		saved = JSON.parse(localStorage.getItem(storageKey) || "null");
	} catch {}
	const language = typeof saved?.language === "string" ? saved.language.toLowerCase().replace("_", "-").split("-")[0] : "en";
	const themeAccents = {};
	for (const theme of themes) {
		themeAccents[theme.value] = {};
		for (const mode of ["light", "dark"]) {
			const preset = saved?.themeAccents?.[theme.value]?.[mode];
			themeAccents[theme.value][mode] = accentPresets.some((item) => item.value === preset) ? preset : defaultThemeAccents[theme.value][mode];
		}
	}
	return {
		language: languages.some((item) => item.value === language) ? language : "en",
		theme: themes.some((item) => item.value === saved?.theme) ? saved.theme : "md3",
		mode: colorModes.some((item) => item.value === saved?.mode) ? saved.mode : "system",
		iconSet: iconSets.some((item) => item.value === saved?.iconSet) ? saved.iconSet : "material-design",
		discussionView: saved?.discussionView === "notes" ? "notes" : "inspector",
		themeAccents,
		clickAnimations: saved?.clickAnimations !== false,
		hoverAnimations: saved?.hoverAnimations !== false,
		fadeAnimations: saved?.fadeAnimations !== false,
		popupAnimations: saved?.popupAnimations !== false
	};
}
var appearance = reactive(readAppearance());
var hostedPalette = ref(null);
function readableText(color) {
	return "#" + readableText$1(color).map((channel) => channel.toString(16).padStart(2, "0")).join("");
}
function saveAppearance() {
	localStorage.setItem(storageKey, JSON.stringify(appearance));
}
var systemDark = ref(typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches);
var effectiveColorMode = computed(() => appearance.mode === "system" ? systemDark.value ? "dark" : "light" : appearance.mode);
var colorPreset = computed(() => hostedPalette.value || accentPresets.find((item) => item.value === appearance.themeAccents[appearance.theme][effectiveColorMode.value]));
var channels = (hex) => hex.match(/[a-f\d]{2}/gi).map((value) => parseInt(value, 16));
var frameColors = computed(() => {
	const mode = effectiveColorMode.value, preset = colorPreset.value;
	return palette(appearance.theme, mode === "dark", channels(preset[mode + "Base"]), channels(preset[mode]));
});
function initializeAppearance() {
	const media = window.matchMedia("(prefers-color-scheme: dark)");
	const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
	const reducedMotion = ref(motion.matches);
	systemDark.value = media.matches;
	media.addEventListener("change", (event) => {
		systemDark.value = event.matches;
	});
	motion.addEventListener("change", (event) => {
		reducedMotion.value = event.matches;
	});
	watchEffect(() => {
		const root = document.documentElement;
		root.lang = appearance.language;
		root.dataset.theme = appearance.theme;
		const mode = effectiveColorMode.value;
		root.dataset.mode = mode;
		root.dataset.iconSet = appearance.iconSet;
		const palette = colorPreset.value;
		root.style.setProperty("--base", palette[mode + "Base"]);
		root.style.setProperty("--primary", palette[mode]);
		const accent = palette[mode].match(/[a-f\d]{2}/gi).map((value) => parseInt(value, 16));
		const base = palette[mode + "Base"].match(/[a-f\d]{2}/gi).map((value) => parseInt(value, 16));
		const dark = mode === "dark";
		const variables = cssVariables(appearance.theme, dark, base, accent, {
			click: appearance.clickAnimations,
			hover: appearance.hoverAnimations,
			fade: appearance.fadeAnimations,
			popup: appearance.popupAnimations,
			reduced: reducedMotion.value
		});
		for (const [name, value] of Object.entries(variables)) root.style.setProperty(name, value);
		for (const motion of [
			"click",
			"hover",
			"fade",
			"popup"
		]) root.dataset[motion + "Animations"] = String(appearance[motion + "Animations"]);
		try {
			if (!configurationPreview.value) saveAppearance();
		} catch {}
	});
}
//#endregion
//#region src/i18n.js
var catalogs = /* #__PURE__ */ Object.assign({
	"./locales/en.json": en_default,
	"./locales/ru.json": ru_default
});
function t(source, values = {}) {
	const translated = catalogs[`./locales/${appearance.language}.json`]?.[source];
	return (typeof translated === "string" && translated.trim() ? translated : source).replace(/\{(\w+)\}/g, (placeholder, name) => values[name] ?? placeholder);
}
//#endregion
//#region src/controls/asyncComponent.js
function asyncComponent(loader) {
	return defineAsyncComponent({
		loader,
		loadingComponent: () => h("p", {
			role: "status",
			class: "muted"
		}, [h(BusyIndicator_default, { running: true }), " " + t("Loading interface…")]),
		errorComponent: () => h("p", {
			role: "alert",
			class: "error"
		}, t("Unable to load the interface. Check your connection and reload the page."))
	});
}
//#endregion
//#region src/controls/identity.js
function randomId() {
	return [...crypto.getRandomValues(/* @__PURE__ */ new Uint8Array(16))].map((value) => value.toString(16).padStart(2, "0")).join("");
}
//#endregion
//#region src/features/debug/debugLog.js
var levels = [
	"LOG",
	"INFO",
	"WARNING",
	"MISSING",
	"EXCEPTION",
	"ERROR",
	"CRITICAL",
	"API"
];
var sessionFields = {
	eventId: "id",
	timestamp: "t",
	level: "l",
	message: "m",
	module: "o",
	functionName: "f",
	line: "n",
	group: "g",
	source: "s",
	command: "c",
	stacktrace: "x",
	duration: "d",
	sizeKb: "z",
	thread: "h",
	details: "e"
};
var settingsKey = "tactic_stream.debug_log";
var saved = {};
try {
	saved = JSON.parse(localStorage.getItem(settingsKey) || "{}");
} catch {}
var debugSettings = reactive({
	recordingLevels: Array.isArray(saved?.recordingLevels) ? levels.filter((level) => saved.recordingLevels.includes(level)) : ["ERROR", "CRITICAL"],
	groupWidth: Math.max(170, Math.min(520, Number(saved?.groupWidth) || 230)),
	detailHeight: Math.max(110, Math.min(620, Number(saved?.detailHeight) || 220))
});
var debugLog = shallowReactive({
	entries: [],
	sessionId: randomId(),
	started: (/* @__PURE__ */ new Date()).toISOString(),
	storageError: ""
});
var sequence$1 = 0;
var database = null;
var serverContext = null;
var secretKeys = /password|passwd|secret|token|ticket|authorization|cookie|api[_-]?key|private[_-]?key/i;
var secrets = /* @__PURE__ */ new Set();
function setServerDebugContext(scope) {
	serverContext = scope?.ticket ? {
		ticket: scope.ticket,
		project: scope.project || ""
	} : null;
	if (serverContext) remember(serverContext.ticket);
}
function persistError(record, scope) {
	if (!scope?.ticket || !["ERROR", "CRITICAL"].includes(record.level)) return;
	const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 3e3);
	const message = JSON.stringify(redact({
		session: debugLog.sessionId,
		timestamp: record.timestamp,
		path: location.pathname || "",
		viewport: {
			width: globalThis.innerWidth || 0,
			height: globalThis.innerHeight || 0
		},
		group: record.group,
		message: record.message.slice(0, 8192),
		stacktrace: record.stacktrace.slice(0, 8192),
		details: record.details.slice(0, 8192)
	}));
	fetch("/admin/rpc", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		signal: controller.signal,
		body: JSON.stringify({
			method: "log",
			args: [
				scope,
				"error",
				message
			],
			kwargs: { category: record.group || "browser/error" }
		})
	}).catch(() => {}).finally(() => clearTimeout(timer));
}
watch(debugSettings, () => {
	if (configurationPreview.value) return;
	try {
		localStorage.setItem(settingsKey, JSON.stringify(debugSettings));
	} catch {
		debugLog.storageError = "Debug Log settings could not be saved.";
	}
});
function remember(value, active = /* @__PURE__ */ new Set()) {
	if (typeof value === "string" && value && value !== "<REDACTED>") secrets.add(value);
	if (value && typeof value === "object" && !active.has(value)) {
		active.add(value);
		for (const item of Object.values(value)) remember(item, active);
		active.delete(value);
	}
}
function redact(value, active = /* @__PURE__ */ new Set()) {
	if (value && typeof value === "object") {
		if (active.has(value)) return "<recursive reference>";
		active.add(value);
		try {
			if (Array.isArray(value)) return value.map((item) => redact(item, active));
			return Object.fromEntries(Object.entries(value).map(([key, item]) => {
				if (secretKeys.test(key)) {
					remember(item);
					return [key, "<REDACTED>"];
				}
				return [key, redact(item, active)];
			}));
		} finally {
			active.delete(value);
		}
	}
	if (typeof value === "string") for (const secret of secrets) value = value.replaceAll(secret, "<REDACTED>");
	return value;
}
function requestPayload(payload) {
	if (payload?.method === "get_ticket") {
		remember(payload.args?.[1]);
		return redact({
			...payload,
			args: [
				payload.args?.[0],
				"<REDACTED>",
				...payload.args.slice(2)
			]
		});
	}
	return redact(redact(payload));
}
function label() {
	return debugLog.started.replace("T", " ").slice(0, 19);
}
async function db() {
	if (!database) database = new Promise((resolve, reject) => {
		const request = indexedDB.open("tactic_stream.debug_log", 1);
		request.onupgradeneeded = () => {
			request.result.createObjectStore("sessions", { keyPath: "id" });
			request.result.createObjectStore("events", { keyPath: ["session", "eventId"] }).createIndex("session", "session");
		};
		request.onsuccess = () => resolve(request.result);
		request.onerror = () => reject(request.error);
		request.onblocked = () => reject(/* @__PURE__ */ new Error("Debug Log history is unavailable."));
	});
	return database;
}
async function write(callback) {
	const connection = await db();
	return new Promise((resolve, reject) => {
		const transaction = connection.transaction(["sessions", "events"], "readwrite");
		transaction.oncomplete = resolve;
		transaction.onerror = () => reject(transaction.error);
		transaction.onabort = () => reject(transaction.error);
		callback(transaction.objectStore("sessions"), transaction.objectStore("events"));
	});
}
async function read(store, query) {
	const connection = await db();
	return new Promise((resolve, reject) => {
		const request = query(connection.transaction(store).objectStore(store));
		request.onsuccess = () => resolve(request.result);
		request.onerror = () => reject(request.error);
	});
}
function storageFailed() {
	debugLog.storageError = "Debug Log history is unavailable. Live events remain in memory.";
}
async function savedSessions() {
	return (await read("sessions", (store) => store.getAll())).sort((a, b) => b.updated.localeCompare(a.updated));
}
async function sessionRecords(id) {
	return (await read("events", (store) => store.index("session").getAll(id))).map(({ session, ...record }) => record);
}
function logEvent(values, scope = serverContext, persist = true) {
	const record = redact({
		eventId: ++sequence$1,
		timestamp: (/* @__PURE__ */ new Date()).toISOString(),
		level: "LOG",
		message: "",
		module: "",
		functionName: "",
		line: 0,
		group: "",
		source: "Browser",
		command: "",
		stacktrace: "",
		duration: 0,
		sizeKb: 0,
		thread: "Main",
		details: "",
		...values
	});
	if (persist) persistError(record, scope);
	if (!debugSettings.recordingLevels.includes(values.level)) return;
	const old = debugLog.entries.length === 1e4 ? debugLog.entries[0] : null;
	debugLog.entries = [...debugLog.entries.slice(-9999), record];
	const id = debugLog.sessionId;
	write((sessions, events) => {
		sessions.put({
			id,
			label: label(),
			updated: record.timestamp
		});
		events.put({
			session: id,
			...record
		});
		if (old) events.delete([id, old.eventId]);
	}).catch(storageFailed);
}
function logRequest(url, payload, response, error, duration) {
	if (payload?.method === "log") return;
	const safe = requestPayload(payload);
	if (payload?.method === "get_ticket" && response?.result) remember(response.result);
	if (!error && !debugSettings.recordingLevels.includes("API")) return;
	const details = JSON.stringify(redact({
		request: safe,
		response
	}), null, 2);
	const body = JSON.stringify(safe);
	let command = "import json\nfrom urllib.request import Request, urlopen\n\npayload = json.loads(" + JSON.stringify(body) + ")\n# Replace <REDACTED> with your own ticket or credentials.\nrequest = Request(" + JSON.stringify(location.origin + url) + ", data=json.dumps(payload).encode(\"utf-8\"), headers={\"Content-Type\": \"application/json\"})\nwith urlopen(request) as response:\n    print(response.read().decode(\"utf-8\"))";
	if (safe.file && url.endsWith("/UploadServer/")) command = `from pathlib import Path
from uuid import uuid4
from urllib.request import Request, urlopen

# Replace <FILE_PATH> and <REDACTED> with your file and ticket.
file = Path("<FILE_PATH>")
boundary = uuid4().hex
filename = file.name.replace('"', '%22').replace('\\r', '%0D').replace('\\n', '%0A')
body = (f'--{boundary}\\r\\nContent-Disposition: form-data; name="login_ticket"\\r\\n\\r\\n<REDACTED>\\r\\n'
        f'--{boundary}\\r\\nContent-Disposition: form-data; name="file"; filename="{filename}"\\r\\n'
        'Content-Type: application/octet-stream\\r\\n\\r\\n').encode("utf-8")
body += file.read_bytes() + f'\\r\\n--{boundary}--\\r\\n'.encode("ascii")
request = Request(${JSON.stringify(location.origin + url)}, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
with urlopen(request) as response:
    print(response.read().decode("utf-8"))`;
	const scope = payload.ticket ? {
		ticket: payload.ticket,
		project: payload.project || ""
	} : payload.args?.[0]?.ticket ? {
		ticket: payload.args[0].ticket,
		project: payload.args[0].project || ""
	} : null;
	logEvent({
		level: error ? "ERROR" : "API",
		message: error ? error.message : payload.method || url,
		module: "api.js",
		functionName: payload.method || url,
		group: url.slice(1).replaceAll("-", "_"),
		source: "TACTIC API",
		duration,
		sizeKb: new TextEncoder().encode(details).length / 1024,
		details,
		command,
		stacktrace: error?.stack || ""
	}, scope, url !== "/admin/server-updates");
}
async function clearLive() {
	debugLog.entries = [];
	const id = debugLog.sessionId;
	try {
		await write((sessions, events) => {
			events.delete(IDBKeyRange.bound([id, 0], [id, Number.MAX_SAFE_INTEGER]));
			sessions.delete(id);
		});
	} catch {
		storageFailed();
	}
}
async function forgetSessions() {
	debugLog.entries = [];
	sequence$1 = 0;
	secrets.clear();
	debugLog.sessionId = randomId();
	debugLog.started = (/* @__PURE__ */ new Date()).toISOString();
	try {
		await write((sessions, events) => {
			sessions.clear();
			events.clear();
		});
	} catch {
		storageFailed();
	}
}
function parseSession(text) {
	const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/);
	let header;
	try {
		header = JSON.parse(lines.shift());
	} catch {
		throw new Error("Invalid Debug Log session header");
	}
	if (JSON.stringify(header) !== "{\"v\":1}") throw new Error("Unsupported Debug Log session schema");
	const records = [], ids = /* @__PURE__ */ new Set();
	for (const [index, line] of lines.entries()) {
		if (!line.trim()) continue;
		let values;
		try {
			values = JSON.parse(line);
		} catch {
			const error = /* @__PURE__ */ new Error("Invalid JSONL record");
			error.line = index + 2;
			throw error;
		}
		if (!values || Array.isArray(values) || typeof values !== "object") continue;
		const record = Object.fromEntries(Object.entries(sessionFields).map(([field, key]) => [field, values[key] ?? ""]));
		for (const field of [
			"eventId",
			"line",
			"duration",
			"sizeKb"
		]) {
			record[field] = Number(record[field] || (field === "eventId" ? records.length + 1 : 0));
			if (!Number.isFinite(record[field]) || record[field] < 0) throw new Error("Invalid Debug Log event");
		}
		if (!Number.isSafeInteger(record.eventId) || ids.has(record.eventId)) throw new Error("Invalid Debug Log event");
		ids.add(record.eventId);
		for (const field of Object.keys(sessionFields).filter((key) => ![
			"eventId",
			"line",
			"duration",
			"sizeKb"
		].includes(key))) if (typeof record[field] !== "string") throw new Error("Invalid Debug Log event");
		record.level = levels.includes(record.level.toUpperCase()) ? record.level.toUpperCase() : "LOG";
		records.push(redact(record));
	}
	return records.slice(-1e4);
}
async function importSession(file) {
	if (!file.name.toLowerCase().endsWith(".jsonl")) throw new Error("A compact Debug Log session (.jsonl) is required.");
	if (file.size > 33554432) throw new Error("Debug Log session exceeds 32 MB.");
	const records = parseSession(await file.text()), id = randomId();
	await write((sessions, events) => {
		sessions.put({
			id,
			label: file.name,
			updated: (/* @__PURE__ */ new Date()).toISOString()
		});
		for (const record of records) events.put({
			session: id,
			...record
		});
	});
	return {
		id,
		records
	};
}
function exportSession(records) {
	return JSON.stringify({ v: 1 }) + "\n" + records.map((record) => JSON.stringify(Object.fromEntries(Object.entries(sessionFields).filter(([field]) => ![
		void 0,
		null,
		"",
		false,
		0
	].includes(record[field])).map(([field, key]) => [key, record[field]])))).join("\n") + "\n";
}
function formatEvent(record) {
	return `[${record.timestamp}] [${record.level}] [${record.group}]\n${record.message}\n${record.module} / ${record.functionName}():${String(record.line || 0).padStart(4, "0")}` + (record.details ? "\n\nDetails:\n" + record.details : "") + (record.command ? "\n\nRuntime command:\n" + record.command : "") + (record.stacktrace ? "\n\nStacktrace:\n" + record.stacktrace : "");
}
function installDebugLogging() {
	for (const [method, level] of Object.entries({
		log: "LOG",
		info: "INFO",
		warn: "WARNING",
		error: "ERROR",
		debug: "LOG"
	})) {
		const original = console[method].bind(console);
		console[method] = (...args) => {
			original(...args);
			if (level !== "ERROR" && !debugSettings.recordingLevels.includes(level)) return;
			try {
				logEvent({
					level,
					source: "Browser console",
					module: "console",
					functionName: method,
					group: "browser/console",
					message: args.map((value) => value instanceof Error ? value.message : typeof value === "string" ? value : JSON.stringify(redact(value))).join(" "),
					stacktrace: args.find((value) => value instanceof Error)?.stack || ""
				});
			} catch {
				debugLog.storageError = "A message could not be recorded in Debug Log.";
			}
		};
	}
	window.addEventListener("error", (event) => {
		if (event.error) logEvent({
			level: "ERROR",
			source: "Browser",
			module: event.filename,
			line: event.lineno,
			group: "browser/error",
			message: event.message,
			stacktrace: event.error.stack || ""
		});
	});
	window.addEventListener("unhandledrejection", (event) => logEvent({
		level: "ERROR",
		source: "Browser",
		group: "browser/error",
		message: String(event.reason?.message || event.reason),
		stacktrace: event.reason?.stack || ""
	}));
}
//#endregion
//#region src/controls/controlAppearance.js
function buttonVariables(options) {
	const result = {};
	for (const [name, flags] of Object.entries({
		idle: {},
		hover: { hovered: true },
		focus: { focused: true },
		pressed: { pressed: true },
		disabled: { enabled: false }
	})) {
		const paint = buttonVisual({
			...options,
			...flags
		});
		let background = paint.background === "transparent" ? "transparent" : `var(${cssRoles[paint.background]})`;
		if (paint.pressedMix) background = `color-mix(in srgb, ${background} 82%, var(--page))`;
		result[`--button-${name}-background`] = background;
		result[`--button-${name}-color`] = `var(${cssRoles[paint.content]})`;
		result[`--button-${name}-border`] = `var(${cssRoles[paint.border]})`;
		result[`--button-${name}-border-width`] = paint.borderWidth + "px";
	}
	return result;
}
//#endregion
//#region src/controls/AppIcon.vue
var _hoisted_1$2 = ["data-icon"];
var _hoisted_2$1 = { class: "icon-glyph" };
var _sfc_main$2 = {
	__name: "AppIcon",
	props: { name: String },
	setup(__props) {
		const props = __props;
		const icon = computed(() => resolveIcon(props.name, appearance.iconSet) || (props.name ? resolveIcon("fontawesome-solid:exclamation-triangle", appearance.iconSet) : null));
		return (_ctx, _cache) => {
			return icon.value ? (openBlock(), createElementBlock("span", {
				key: 0,
				class: normalizeClass(["app-icon", "icon-" + icon.value[0]]),
				"data-icon": __props.name,
				"aria-hidden": "true"
			}, [createBaseVNode("span", _hoisted_2$1, toDisplayString(icon.value[1]), 1)], 10, _hoisted_1$2)) : createCommentVNode("", true);
		};
	}
};
//#endregion
//#region src/controls/ripple.js
function ripple(event) {
	const button = event.currentTarget;
	if (button.disabled || event.button !== 0) return;
	const style = getComputedStyle(button);
	const fast = parseFloat(style.getPropertyValue("--motion-click")) || 0;
	const extended = parseFloat(style.getPropertyValue("--motion-click-extended")) || 0;
	if (!extended) return;
	button.querySelectorAll(":scope > .control-ripple-clip").forEach((node) => node.remove());
	const inset = parseFloat(style.getPropertyValue("--ripple-inset")) || 0;
	const bounds = button.getBoundingClientRect(), diameter = Math.max(bounds.width - inset * 2, bounds.height - inset * 2) * 2.2;
	const circle = document.createElement("span");
	circle.className = "control-ripple";
	circle.setAttribute("aria-hidden", "true");
	Object.assign(circle.style, {
		width: diameter + "px",
		height: diameter + "px",
		left: event.clientX - bounds.left - inset - diameter / 2 + "px",
		top: event.clientY - bounds.top - inset - diameter / 2 + "px"
	});
	const clip = document.createElement("span");
	clip.className = "control-ripple-clip";
	clip.setAttribute("aria-hidden", "true");
	clip.style.inset = inset + "px";
	clip.append(circle);
	button.append(clip);
	circle.animate([{ transform: "scale(.05)" }, { transform: "scale(1)" }], {
		duration: extended + fast,
		easing: "cubic-bezier(.215,.61,.355,1)",
		fill: "forwards"
	});
	circle.animate([{ opacity: .42 }, { opacity: 0 }], {
		duration: extended,
		delay: 24,
		easing: "ease-out",
		fill: "forwards"
	}).finished.then(() => clip.remove(), () => clip.remove());
}
//#endregion
//#region src/controls/activation.js
function capturePress(event) {
	const control = event.currentTarget;
	if (event.button !== 0 || event.pointerType === "touch" || control.disabled || control.getAttribute("aria-disabled") === "true") return;
	control.setPointerCapture(event.pointerId);
	const listeners = new AbortController(), x = event.clientX, y = event.clientY;
	control.addEventListener("pointermove", (move) => {
		if (move.pointerId === event.pointerId && Math.hypot(move.clientX - x, move.clientY - y) >= 10) {
			if (control.hasPointerCapture(event.pointerId)) control.releasePointerCapture(event.pointerId);
			listeners.abort();
		}
	}, { signal: listeners.signal });
	for (const name of [
		"pointerup",
		"pointercancel",
		"lostpointercapture"
	]) control.addEventListener(name, (end) => {
		if (end.pointerId === event.pointerId) listeners.abort();
	}, { signal: listeners.signal });
}
//#endregion
//#region src/controls/tooltip.js
var active;
var sequence = 0;
var tooltipDirective = {
	mounted(element, binding) {
		let text = binding.value, timer, timeout, popup, describedBy;
		function close(event) {
			if (popup && event?.type === "keydown" && event.key === "Escape") {
				event.preventDefault();
				event.stopPropagation();
			}
			clearTimeout(timer);
			clearTimeout(timeout);
			if (popup) {
				const dismissed = popup;
				dismissed.hidePopover();
				setTimeout(() => dismissed.remove(), parseFloat(getComputedStyle(dismissed).transitionDuration) * 1e3 + 10);
				popup = null;
				if (describedBy === null) element.removeAttribute("aria-describedby");
				else element.setAttribute("aria-describedby", describedBy);
			}
			for (const name of [
				"scroll",
				"resize",
				"pointerdown",
				"keydown",
				"close"
			]) window.removeEventListener(name, close, true);
			if (active === close) active = null;
		}
		function start(event) {
			if (!text || element.disabled || element.getAttribute("aria-disabled") === "true" || event.pointerType === "touch") return;
			active?.();
			active = close;
			for (const name of [
				"scroll",
				"resize",
				"pointerdown",
				"keydown",
				"close"
			]) window.addEventListener(name, close, true);
			timer = setTimeout(() => {
				if (!element.isConnected || element.disabled || element.getAttribute("aria-disabled") === "true" || !element.getClientRects().length) {
					close();
					return;
				}
				popup = document.createElement("div");
				popup.className = "app-tooltip";
				popup.popover = "manual";
				popup.id = "app-tooltip-" + ++sequence;
				popup.role = "tooltip";
				popup.textContent = text;
				(element.closest("dialog") || document.body).append(popup);
				popup.showPopover();
				const anchor = element.getBoundingClientRect(), box = popup.getBoundingClientRect(), margin = controls.tooltip.margin;
				popup.style.left = Math.max(margin, Math.min(innerWidth - box.width - margin, anchor.left + (anchor.width - box.width) / 2)) + "px";
				popup.style.top = Math.max(margin, Math.min(innerHeight - box.height - margin, anchor.bottom + box.height + 2 * margin > innerHeight ? anchor.top - box.height - margin : anchor.bottom + margin)) + "px";
				describedBy = element.getAttribute("aria-describedby");
				element.setAttribute("aria-describedby", [describedBy, popup.id].filter(Boolean).join(" "));
				timeout = setTimeout(close, controls.tooltip.timeout);
			}, controls.tooltip.delay);
		}
		element.addEventListener("pointerenter", start);
		element.addEventListener("focusin", start);
		element.addEventListener("pointerleave", close);
		element.addEventListener("focusout", close);
		element.tooltipUpdate = (value) => {
			text = value;
			close();
		};
		element.tooltipCleanup = () => {
			close();
			element.removeEventListener("pointerenter", start);
			element.removeEventListener("focusin", start);
			element.removeEventListener("pointerleave", close);
			element.removeEventListener("focusout", close);
		};
	},
	updated(element, binding) {
		if (binding.value !== binding.oldValue) element.tooltipUpdate?.(binding.value);
	},
	beforeUnmount(element) {
		element.tooltipCleanup?.();
		delete element.tooltipUpdate;
		delete element.tooltipCleanup;
	}
};
//#endregion
//#region src/controls/AppButton.vue
var _hoisted_1$1 = { key: 0 };
var _hoisted_2 = {
	key: 1,
	class: "app-button-badge",
	"aria-hidden": "true"
};
var _sfc_main$1 = {
	__name: "AppButton",
	props: {
		label: {
			type: String,
			default: ""
		},
		translateLabel: {
			type: Boolean,
			default: true
		},
		tooltip: String,
		icon: String,
		iconOnly: Boolean,
		compact: Boolean,
		highlighted: Boolean,
		destructive: Boolean,
		tonal: Boolean,
		segmented: Boolean,
		checked: Boolean,
		badgeCount: {
			type: Number,
			default: 0
		},
		badgeColor: String,
		showZeroBadge: Boolean,
		type: {
			type: String,
			default: "button"
		},
		href: String
	},
	setup(__props) {
		const props = __props;
		const paint = computed(() => buttonVariables(props));
		return (_ctx, _cache) => {
			return withDirectives((openBlock(), createBlock(resolveDynamicComponent(__props.href ? "a" : "button"), {
				class: normalizeClass(["app-button", {
					"icon-button": __props.iconOnly || __props.compact,
					"compact-button": __props.compact,
					primary: __props.highlighted,
					danger: __props.destructive,
					tonal: __props.tonal
				}]),
				style: normalizeStyle([paint.value, __props.badgeColor ? { "--badge-color": __props.badgeColor } : null]),
				href: __props.href,
				type: __props.href ? void 0 : __props.type,
				"aria-label": __props.label ? __props.translateLabel ? unref(t)(__props.label) : __props.label : void 0,
				onPointerdown: _cache[0] || (_cache[0] = ($event) => {
					unref(capturePress)($event);
					unref(ripple)($event);
				})
			}, {
				default: withCtx(() => [
					__props.icon ? (openBlock(), createBlock(_sfc_main$2, {
						key: 0,
						name: __props.icon
					}, null, 8, ["name"])) : createCommentVNode("", true),
					renderSlot(_ctx.$slots, "default", {}, () => [!__props.iconOnly && !__props.compact ? (openBlock(), createElementBlock("span", _hoisted_1$1, toDisplayString(__props.translateLabel ? unref(t)(__props.label) : __props.label), 1)) : createCommentVNode("", true)]),
					__props.badgeCount > 0 || __props.showZeroBadge ? (openBlock(), createElementBlock("span", _hoisted_2, toDisplayString(__props.badgeCount > 99 ? "99+" : __props.badgeCount), 1)) : createCommentVNode("", true)
				]),
				_: 3
			}, 40, [
				"style",
				"href",
				"type",
				"class",
				"aria-label"
			])), [[unref(tooltipDirective), __props.tooltip ? unref(t)(__props.tooltip) : (__props.iconOnly || __props.compact) && __props.label ? __props.translateLabel ? unref(t)(__props.label) : __props.label : ""]]);
		};
	}
};
//#endregion
//#region src/mobile.js
var mobileLayout = window.matchMedia("(max-width: 700px)");
var mobile = ref(mobileLayout.matches);
mobileLayout.addEventListener("change", (event) => {
	mobile.value = event.matches;
});
function viewportChanged() {
	const viewport = window.visualViewport;
	const keyboardViewport = mobile.value && viewport?.scale === 1;
	document.documentElement.style.setProperty("--phone-height", (keyboardViewport ? viewport.height : innerHeight) + "px");
	document.documentElement.style.setProperty("--phone-top", (keyboardViewport ? viewport.offsetTop : 0) + "px");
}
window.visualViewport?.addEventListener("resize", viewportChanged);
window.visualViewport?.addEventListener("scroll", viewportChanged);
window.addEventListener("resize", viewportChanged);
mobileLayout.addEventListener("change", viewportChanged);
viewportChanged();
//#endregion
//#region ../src/tactic_stream/shared_ui/shell/window.geometry.mjs
var finite = (value, fallback) => Number.isFinite(value) ? value : fallback;
function fit(rectangle, bounds, minimum, sizeMargin) {
	if (![
		bounds.x,
		bounds.y,
		bounds.width,
		bounds.height
	].every(Number.isFinite) || bounds.width <= 0 || bounds.height <= 0) throw Error("Window bounds must be finite and have positive dimensions");
	const limit = minimum || {
		width: 1,
		height: 1
	};
	const margin = Math.max(0, finite(sizeMargin, 0));
	const width = Math.max(limit.width, Math.min(finite(rectangle.width, 280), Math.max(1, bounds.width - margin)));
	const height = Math.max(limit.height, Math.min(finite(rectangle.height, 180), Math.max(1, bounds.height - margin)));
	return {
		x: Math.max(bounds.x, Math.min(finite(rectangle.x, bounds.x), bounds.x + bounds.width - width)),
		y: Math.max(bounds.y, Math.min(finite(rectangle.y, bounds.y), bounds.y + bounds.height - height)),
		width,
		height
	};
}
function moved(rectangle, delta) {
	return Object.assign({}, rectangle, {
		x: rectangle.x + delta.x,
		y: rectangle.y + delta.y
	});
}
function resized(rectangle, edge, delta, bounds, minimum) {
	if ([
		"left",
		"right",
		"top",
		"bottom",
		"top-left",
		"top-right",
		"bottom-left",
		"bottom-right"
	].indexOf(edge) < 0) throw Error("Unknown window resize edge: " + edge);
	const result = Object.assign({}, rectangle);
	const minimumWidth = Math.min(minimum.width, bounds.width);
	const minimumHeight = Math.min(minimum.height, bounds.height);
	if (edge.indexOf("right") >= 0) result.width = Math.max(minimumWidth, Math.min(bounds.x + bounds.width - result.x, result.width + delta.x));
	if (edge.indexOf("bottom") >= 0) result.height = Math.max(minimumHeight, Math.min(bounds.y + bounds.height - result.y, result.height + delta.y));
	if (edge.indexOf("left") >= 0) {
		result.x = Math.max(bounds.x, Math.min(result.x + delta.x, result.x + result.width - minimumWidth));
		result.width += rectangle.x - result.x;
	}
	if (edge.indexOf("top") >= 0) {
		result.y = Math.max(bounds.y, Math.min(result.y + delta.y, result.y + result.height - minimumHeight));
		result.height += rectangle.y - result.y;
	}
	return result;
}
//#endregion
//#region ../src/tactic_stream/shared_ui/shell/window.sizing.mjs
function windowMinimumWidth(kind) {
	if (String(kind).indexOf("dcc.") === 0) return 560;
	const widths = {
		main: 560,
		configuration: 820,
		server: 640,
		project: 640,
		project_wizard: 680,
		project_templates: 680,
		checkin_preferences: 640,
		global_preferences: 560,
		repository_editor: 760,
		commit_queue: 860,
		file_changelist: 520,
		ingest_files: 760,
		script_editor: 720,
		script_shelf_editor: 720,
		script_trigger_editor: 760,
		help: 760,
		messages: 820,
		tasks_workspace: 760,
		handler_server: 820,
		sobject_info: 760,
		debug_log: 680,
		ui_performance: 720,
		error: 560,
		repository_sync: 680,
		repository_sync_editor: 900,
		activity_feed: 680,
		user_profile: 680,
		administration: 900,
		schema_search_type: 600,
		raw_cell: 440,
		process_dependencies: 860,
		sidebar_search_preview: 960,
		server_presets: 720,
		screenshot_maker: 640,
		notifications: 560,
		update: 520,
		create_update: 560,
		matching_templates: 640,
		dcc_options: 520,
		add_sobject: 620,
		task_editor: 620,
		link_sobjects: 620,
		delete_sobject: 720,
		duplicate_sobject: 680,
		process_filter_editor: 440,
		quick_filter_editor: 620,
		advanced_search: 680,
		naming_editor: 840
	};
	return Object.prototype.hasOwnProperty.call(widths, kind) ? widths[kind] : 480;
}
function windowMinimumHeight(kind) {
	if (String(kind).indexOf("dcc.") === 0) return 440;
	const heights = {
		main: 480,
		raw_cell: 340,
		configuration: 600,
		server: 520,
		project: 520,
		project_wizard: 520,
		project_templates: 520,
		checkin_preferences: 520,
		global_preferences: 440,
		repository_editor: 540,
		commit_queue: 600,
		file_changelist: 480,
		ingest_files: 560,
		script_editor: 500,
		script_shelf_editor: 480,
		script_trigger_editor: 520,
		help: 520,
		messages: 560,
		tasks_workspace: 520,
		handler_server: 580,
		sobject_info: 560,
		debug_log: 480,
		ui_performance: 520,
		error: 400,
		repository_sync: 480,
		repository_sync_editor: 620,
		activity_feed: 480,
		user_profile: 480,
		administration: 620,
		schema_search_type: 560,
		process_dependencies: 600,
		sidebar_search_preview: 620,
		server_presets: 520,
		screenshot_maker: 500,
		notifications: 420,
		update: 380,
		create_update: 420,
		matching_templates: 500,
		dcc_options: 420,
		add_sobject: 480,
		task_editor: 480,
		link_sobjects: 480,
		delete_sobject: 520,
		duplicate_sobject: 520,
		process_filter_editor: 360,
		quick_filter_editor: 520,
		advanced_search: 500,
		naming_editor: 600
	};
	return Object.prototype.hasOwnProperty.call(heights, kind) ? heights[kind] : 360;
}
function dockMinimumWidth(kind) {
	const widths = {
		results: 360,
		snapshot: 320,
		tasks: 320,
		task_calendar: 380,
		description: 320,
		notes: 400,
		drop_plate: 480,
		advanced_search: 380,
		watch_folders: 680,
		watch_folder_editor: 520,
		db_table: 620,
		commit_queue: 720
	};
	return Object.prototype.hasOwnProperty.call(widths, kind) ? widths[kind] : 320;
}
function dockMinimumHeight(kind) {
	const heights = {
		results: 260,
		snapshot: 260,
		tasks: 220,
		task_calendar: 360,
		description: 220,
		notes: 300,
		drop_plate: 360,
		advanced_search: 320,
		watch_folders: 420,
		watch_folder_editor: 350,
		db_table: 460,
		commit_queue: 480
	};
	return Object.prototype.hasOwnProperty.call(heights, kind) ? heights[kind] : 220;
}
//#endregion
//#region src/controls/WindowControls.vue
var _hoisted_1 = ["onPointerdown"];
var _sfc_main = {
	__name: "WindowControls",
	props: {
		element: Object,
		header: Object,
		geometry: Object,
		backProvided: Boolean
	},
	setup(__props) {
		const props = __props;
		const previousTitle = props.header.getAttribute("title"), previousTabIndex = props.header.getAttribute("tabindex");
		const maximized = ref(false);
		const minimized = ref(false);
		const edges = ref({});
		function back() {
			if (props.element.dispatchEvent(new Event("cancel", { cancelable: true }))) props.element.close();
		}
		watchEffect(() => {
			props.header.title = t("Drag the title bar to move. Double-click or Alt+F10 to maximize. Alt+arrows moves the focused title bar.");
		});
		let saved = null, placed = null, gesture = null;
		function geometryChanged() {
			resizeEdges();
			props.element.dispatchEvent(new CustomEvent("windowgeometrychange", { detail: {
				...rectangle(),
				maximized: maximized.value,
				restore: saved
			} }));
			window.dispatchEvent(new Event("windowgeometrychange"));
		}
		watch(() => props.geometry, (value) => {
			if (!value) return;
			saved = clamp(value.restore || value.rect);
			placed = clamp(value.rect);
			maximized.value = !!value.maximized;
			for (const [key, value] of Object.entries(placed)) props.element.style.setProperty("--window-" + key, value + "px");
			props.element.classList.add("app-window-positioned");
			props.element.classList.toggle("app-window-maximized", maximized.value);
		}, {
			deep: true,
			immediate: true
		});
		const compact = () => innerWidth <= 700;
		function rectangle() {
			const box = props.element.getBoundingClientRect();
			return {
				x: box.x,
				y: box.y,
				width: box.width,
				height: box.height
			};
		}
		function resizeEdges() {
			const box = rectangle();
			edges.value = {
				"--edge-left": box.x + "px",
				"--edge-top": box.y + "px",
				"--edge-right": innerWidth - box.x - box.width + "px",
				"--edge-bottom": innerHeight - box.y - box.height + "px"
			};
		}
		function clamp(rect) {
			return fit(rect, {
				x: 0,
				y: 0,
				width: innerWidth,
				height: innerHeight
			}, minimum(), layout.windowMargin);
		}
		function minimum() {
			const kind = props.element.dataset.windowKind;
			return {
				width: Math.min(kind ? windowMinimumWidth(kind) : 280, innerWidth - layout.windowMargin),
				height: Math.min(kind ? windowMinimumHeight(kind) : 180, innerHeight - layout.windowMargin)
			};
		}
		function place(rect) {
			placed = clamp(rect);
			for (const [key, value] of Object.entries(placed)) props.element.style.setProperty("--window-" + key, value + "px");
			props.element.classList.add("app-window-positioned");
			geometryChanged();
		}
		function toggle() {
			if (compact()) return;
			if (!maximized.value) {
				saved = rectangle();
				maximized.value = true;
			} else {
				maximized.value = false;
				place(saved);
			}
			props.element.classList.toggle("app-window-maximized", maximized.value);
			geometryChanged();
		}
		function minimize() {
			minimized.value = !minimized.value;
			props.element.classList.toggle("app-window-minimized", minimized.value);
			geometryChanged();
		}
		function shown() {
			if (minimized.value) minimize();
		}
		function start(event) {
			if (gesture || event.isPrimary === false || compact() || maximized.value || event.button !== 0 || event.target.closest("button, a, input, select, textarea, summary, label, [role=\"button\"], [role=\"tab\"]")) return;
			event.preventDefault();
			props.header.setPointerCapture(event.pointerId);
			gesture = {
				pointer: event.pointerId,
				x: event.clientX,
				y: event.clientY,
				before: rectangle()
			};
		}
		function move(event) {
			if (!gesture || gesture.pointer !== event.pointerId) return;
			const delta = {
				x: event.clientX - gesture.x,
				y: event.clientY - gesture.y
			};
			place(gesture.edge ? resized(gesture.before, gesture.edge, delta, {
				x: 0,
				y: 0,
				width: innerWidth,
				height: innerHeight
			}, minimum()) : moved(gesture.before, delta));
		}
		function startResize(event, edge) {
			if (gesture || event.isPrimary === false || compact() || maximized.value || event.button !== 0) return;
			event.preventDefault();
			props.header.setPointerCapture(event.pointerId);
			gesture = {
				pointer: event.pointerId,
				x: event.clientX,
				y: event.clientY,
				before: rectangle(),
				edge
			};
		}
		function stop(event) {
			if (!gesture || event.pointerId !== gesture.pointer) return;
			const current = gesture;
			gesture = null;
			if (["pointercancel", "lostpointercapture"].includes(event.type)) place(current.before);
			if (props.header.hasPointerCapture(current.pointer)) props.header.releasePointerCapture(current.pointer);
		}
		function doubleClick(event) {
			if (!event.target.closest("button, a, input, select, textarea, summary, label")) toggle();
		}
		function resize() {
			if (placed && !maximized.value && !compact()) place(placed);
			resizeEdges();
		}
		function cancelGesture() {
			if (gesture) stop({
				pointerId: gesture.pointer,
				type: "pointercancel"
			});
		}
		function opened() {
			if (!props.element.open || saved || placed || compact()) return;
			if (props.element.offsetWidth < innerWidth - 16 || props.element.offsetHeight < innerHeight - 16) return;
			const width = Math.min(1100, innerWidth * .8), height = Math.min(760, innerHeight * .8);
			saved = {
				width,
				height,
				x: (innerWidth - width) / 2,
				y: (innerHeight - height) / 2
			};
			maximized.value = true;
			props.element.classList.add("app-window-maximized");
		}
		const observer = new MutationObserver(opened);
		const sizeObserver = new ResizeObserver(resizeEdges);
		function key(event) {
			if (event.target.closest(".app-window") !== props.element) return;
			if (event.key === "Escape" && gesture) {
				event.preventDefault();
				event.stopPropagation();
				cancelGesture();
				return;
			}
			if (event.altKey && event.key === "F10") {
				event.preventDefault();
				event.stopPropagation();
				toggle();
			}
			if (event.target !== props.header || !event.altKey || !event.key.startsWith("Arrow") || compact() || maximized.value) return;
			event.preventDefault();
			event.stopPropagation();
			const rect = rectangle(), dx = event.key === "ArrowLeft" ? -10 : event.key === "ArrowRight" ? 10 : 0, dy = event.key === "ArrowUp" ? -10 : event.key === "ArrowDown" ? 10 : 0;
			place(event.shiftKey ? {
				...rect,
				width: Math.max(280, rect.width + dx),
				height: Math.max(180, rect.height + dy)
			} : {
				...rect,
				x: rect.x + dx,
				y: rect.y + dy
			});
		}
		onMounted(() => {
			props.header.classList.add("app-window-titlebar");
			props.header.tabIndex = 0;
			for (const [name, fn] of Object.entries({
				pointerdown: start,
				pointermove: move,
				pointerup: stop,
				pointercancel: stop,
				lostpointercapture: stop,
				dblclick: doubleClick
			})) props.header.addEventListener(name, fn);
			props.element.addEventListener("keydown", key, true);
			window.addEventListener("resize", resize);
			props.element.addEventListener("windowshow", shown);
			window.addEventListener("blur", cancelGesture);
			window.addEventListener("pagehide", cancelGesture);
			observer.observe(props.element, {
				attributes: true,
				attributeFilter: ["open"]
			});
			opened();
			sizeObserver.observe(props.element);
		});
		onBeforeUnmount(() => {
			cancelGesture();
			for (const [name, fn] of Object.entries({
				pointerdown: start,
				pointermove: move,
				pointerup: stop,
				pointercancel: stop,
				lostpointercapture: stop,
				dblclick: doubleClick
			})) props.header.removeEventListener(name, fn);
			props.header.classList.remove("app-window-titlebar");
			for (const [name, value] of [["title", previousTitle], ["tabindex", previousTabIndex]]) if (value === null) props.header.removeAttribute(name);
			else props.header.setAttribute(name, value);
			props.element.classList.remove("app-window-positioned", "app-window-maximized", "app-window-minimized");
			for (const key of [
				"x",
				"y",
				"width",
				"height"
			]) props.element.style.removeProperty("--window-" + key);
			props.element.removeEventListener("keydown", key, true);
			window.removeEventListener("resize", resize);
			props.element.removeEventListener("windowshow", shown);
			window.removeEventListener("blur", cancelGesture);
			window.removeEventListener("pagehide", cancelGesture);
			observer.disconnect();
			sizeObserver.disconnect();
		});
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock(Fragment, null, [
				__props.element.dataset.windowType === "window" ? (openBlock(), createBlock(_sfc_main$1, {
					key: 0,
					"icon-only": "",
					icon: minimized.value ? "window-restore" : "minus",
					label: minimized.value ? "Restore window" : "Minimize window",
					"aria-pressed": minimized.value,
					onClick: minimize
				}, null, 8, [
					"icon",
					"label",
					"aria-pressed"
				])) : createCommentVNode("", true),
				!minimized.value ? (openBlock(), createBlock(_sfc_main$1, {
					key: 1,
					"icon-only": "",
					icon: maximized.value ? "window-restore" : "open-in-full",
					label: maximized.value ? "Restore window" : "Maximize window",
					"aria-pressed": maximized.value,
					onClick: toggle
				}, null, 8, [
					"icon",
					"label",
					"aria-pressed"
				])) : createCommentVNode("", true),
				(openBlock(), createBlock(Teleport, { to: __props.header }, [unref(mobile) && !__props.backProvided ? (openBlock(), createBlock(_sfc_main$1, {
					key: 0,
					class: "app-window-back",
					"icon-only": "",
					icon: "MDI_ARROW_LEFT",
					label: "Back",
					onClick: back
				})) : createCommentVNode("", true)], 8, ["to"])),
				(openBlock(), createBlock(Teleport, { to: __props.element }, [!maximized.value && !minimized.value ? (openBlock(), createElementBlock(Fragment, { key: 0 }, renderList([
					"left",
					"right",
					"top",
					"bottom",
					"top-left",
					"top-right",
					"bottom-left",
					"bottom-right"
				], (edge) => {
					return createBaseVNode("span", {
						key: edge,
						class: normalizeClass(["app-window-resize", edge]),
						style: normalizeStyle(edges.value),
						"aria-hidden": "true",
						onPointerdown: withModifiers(($event) => startResize($event, edge), ["stop"])
					}, null, 46, _hoisted_1);
				}), 64)) : createCommentVNode("", true)], 8, ["to"]))
			], 64);
		};
	}
};
//#endregion
//#region src/controls/window.js
var activeWindow = null;
var windowDirective = {
	mounted(element, binding) {
		if (element.tagName !== "DIALOG") return;
		let configuration = binding.value;
		let header = null, host = null;
		const show = element.show.bind(element), close = element.close.bind(element);
		const home = document.createComment("window owner");
		element.before(home);
		let owner = null, returnFocus = null;
		const nonmodal = () => ["window", "popup"].includes(configuration?.type);
		function closed() {
			if (element.matches(":popover-open")) element.hidePopover();
			owner?.removeEventListener("close", closeChild);
			owner = null;
			if (home.parentNode) home.after(element);
			if (activeWindow === element) activeWindow = null;
		}
		function nativeClosed() {
			if (element.open) return;
			closed();
			if (returnFocus?.isConnected) returnFocus.focus({ preventScroll: true });
			returnFocus = null;
		}
		function closeChild(event) {
			if (event.target === owner) element.close();
		}
		function raise(event) {
			if (!element.open || !element.matches(":popover-open") || activeWindow === element || element.querySelector("dialog:modal")) return;
			if (event && event.target.closest("[popover]") !== element) return;
			const focused = element.contains(document.activeElement) ? document.activeElement : null;
			element.hidePopover();
			element.showPopover();
			focused?.focus({ preventScroll: true });
			activeWindow = element;
		}
		element.show = () => {
			if (!nonmodal()) {
				if (element.matches(":modal")) element.focus();
				else show();
				return;
			}
			if (element.open) {
				element.dispatchEvent(new Event("windowshow"));
				raise();
				return;
			}
			returnFocus = document.activeElement;
			owner = returnFocus?.closest(configuration.type === "popup" ? "dialog[open]" : "dialog:modal") || [...document.querySelectorAll("dialog:modal")].at(-1) || null;
			if (owner === element || element.contains(owner)) owner = null;
			if (owner) {
				owner.append(element);
				owner.addEventListener("close", closeChild);
			}
			element.popover = "manual";
			show();
			element.showPopover();
			activeWindow = element;
			element.dispatchEvent(new Event("windowshow"));
		};
		element.close = (...args) => {
			closed();
			close(...args);
			if (returnFocus?.isConnected) returnFocus.focus({ preventScroll: true });
			returnFocus = null;
		};
		function escape(event) {
			if (event.key !== "Escape" || event.defaultPrevented || !nonmodal() || event.target.closest("dialog") !== element) return;
			event.preventDefault();
			event.stopPropagation();
			if (element.dispatchEvent(new Event("cancel", { cancelable: true }))) element.close();
		}
		element.addEventListener("keydown", escape);
		element.addEventListener("close", nativeClosed);
		element.addEventListener("pointerdown", raise);
		function placeControls() {
			const last = [...header.querySelectorAll("button")].at(-1);
			const anchor = last?.parentElement.tagName === "FORM" ? last.parentElement : last;
			if (anchor) anchor.before(host);
			else header.append(host);
		}
		const attach = () => {
			element.classList.toggle("app-window", configuration !== false && configuration?.type !== "popup");
			element.dataset.windowType = configuration?.type || "dialog";
			element.dataset.windowKind = configuration?.kind || "";
			if (nonmodal()) element.setAttribute("aria-modal", "false");
			else element.removeAttribute("aria-modal");
			const next = configuration === false ? null : [...element.querySelectorAll("header")].find((header) => header.closest(".app-window") === element) || null;
			if (next === header) {
				if (host && !header.contains(host)) placeControls();
				return;
			}
			if (host) {
				render(null, host);
				host.remove();
			}
			header = next;
			host = null;
			if (!header) return;
			host = document.createElement("span");
			host.className = "app-window-controls";
			placeControls();
			render(h(_sfc_main, {
				element,
				header,
				geometry: configuration?.geometry,
				backProvided: !!configuration?.backProvided
			}), host);
		};
		const observer = new MutationObserver(attach);
		observer.observe(element, {
			childList: true,
			subtree: true
		});
		attach();
		element.windowConfigure = (value) => {
			configuration = value;
			attach();
			if (host) render(h(_sfc_main, {
				element,
				header,
				geometry: configuration?.geometry,
				backProvided: !!configuration?.backProvided
			}), host);
		};
		element.windowCleanup = () => {
			closed();
			home.remove();
			element.show = show;
			element.close = close;
			element.removeEventListener("keydown", escape);
			element.removeEventListener("close", nativeClosed);
			element.removeEventListener("pointerdown", raise);
			observer.disconnect();
			if (host) {
				render(null, host);
				host.remove();
			}
		};
	},
	updated(element, binding) {
		element.windowConfigure?.(binding.value);
	},
	beforeUnmount(element) {
		element.windowCleanup?.();
		element.classList.remove("app-window");
		delete element.windowCleanup;
		delete element.windowConfigure;
	}
};
//#endregion
//#region \0vite/preload-helper.js
var scriptRel = "modulepreload";
var assetsURL = function(dep) {
	return "/ui/" + dep;
};
var seen = {};
var isCssPreloadUrl = function isCssPreloadUrl(url) {
	return url.pathname.endsWith(".css");
};
var __vitePreload = function preload(baseModule, deps, importerUrl) {
	let promise = Promise.resolve();
	if (deps && deps.length > 0) {
		let preloadedHrefs;
		const cspNonceMeta = document.querySelector("meta[property=csp-nonce]");
		const cspNonce = cspNonceMeta?.nonce || cspNonceMeta?.getAttribute("nonce");
		function allSettled(promises) {
			return Promise.all(promises.map((p) => Promise.resolve(p).then((value) => ({
				status: "fulfilled",
				value
			}), (reason) => ({
				status: "rejected",
				reason
			}))));
		}
		function importMetaResolve(specifier) {
			if (import.meta.resolve) return new URL(import.meta.resolve(specifier));
			return new URL(
				specifier,
				/** #__KEEP__ */
				import.meta.url
			);
		}
		promise = allSettled(deps.map((depString) => {
			depString = assetsURL(depString, importerUrl);
			const dep = importMetaResolve(depString);
			if (dep.href in seen) return;
			seen[dep.href] = true;
			const isCss = isCssPreloadUrl(dep);
			if (preloadedHrefs === void 0) {
				preloadedHrefs = {
					all: /* @__PURE__ */ new Set(),
					styles: /* @__PURE__ */ new Set()
				};
				const links = document.getElementsByTagName("link");
				for (let i = links.length - 1; i >= 0; i--) {
					const link = links[i];
					preloadedHrefs.all.add(link.href);
					if (link.rel === "stylesheet") preloadedHrefs.styles.add(link.href);
				}
			}
			if ((isCss ? preloadedHrefs.styles : preloadedHrefs.all).has(dep.href)) return;
			const link = document.createElement("link");
			link.rel = isCss ? "stylesheet" : scriptRel;
			if (!isCss) link.as = "script";
			link.crossOrigin = "";
			link.href = dep.href;
			if (cspNonce) link.setAttribute("nonce", cspNonce);
			document.head.appendChild(link);
			if (isCss) return new Promise((res, rej) => {
				link.addEventListener("load", res);
				link.addEventListener("error", () => rej(/* @__PURE__ */ new Error(`Unable to preload CSS for ${dep}`)));
			});
		}).filter((p) => p !== void 0));
	}
	function handlePreloadError(err) {
		const e = new Event("vite:preloadError", { cancelable: true });
		e.payload = err;
		window.dispatchEvent(e);
		if (!e.defaultPrevented) throw err;
	}
	return promise.then((res) => {
		for (const item of res || []) {
			if (item.status !== "rejected") continue;
			handlePreloadError(item.reason);
		}
		return baseModule().catch(handlePreloadError);
	});
};
//#endregion
//#region src/main.js
initializeAppearance();
installDebugLogging();
var documentation = location.pathname === "/docs" || location.pathname === "/docs/";
if (documentation) watchEffect(() => {
	document.title = t("TACTIC Stream — API reference");
});
var screen = asyncComponent(documentation ? () => __vitePreload(() => import("./ApiDocumentation.js"), __vite__mapDeps([0,1,2,3,4,5,6,7,8])) : () => __vitePreload(() => import("./App.js").then((n) => n.t), __vite__mapDeps([9,1,10,11,2,3,4,5,6,7,8,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42])));
createApp({ render: () => h(screen) }).directive("window", windowDirective).mount("#app");
//#endregion
export { themes as $, effectiveColorMode as A, fontLineHeight as B, sessionRecords as C, t as D, asyncComponent as E, blend as F, configurationPreview as G, metrics as H, controls as I, savePreferencePage as J, normalizePreferences as K, cssColor as L, languages as M, readableText as N, appearance as O, saveAppearance as P, iconSets as Q, cssRoles as R, savedSessions as S, randomId as T, readableText$1 as U, layout as V, textStyles as W, taskColumns as X, normalizeColumns as Y, accentPresets as Z, importSession as _, mobileLayout as a, logRequest as b, capturePress as c, clearLive as d, BusyIndicator_default as et, debugLog as f, formatEvent as g, forgetSessions as h, mobile as i, frameColors as j, colorModes as k, ripple as l, exportSession as m, dockMinimumHeight as n, _sfc_main$1 as o, debugSettings as p, preferences as q, dockMinimumWidth as r, tooltipDirective as s, __vitePreload as t, _plugin_vue_export_helper_default as tt, _sfc_main$2 as u, levels as v, setServerDebugContext as w, redact as x, logEvent as y, fontFamily as z };

//# sourceMappingURL=index.js.map