import { A as onMounted, M as openBlock, O as onBeforeUnmount, X as ref, _ as createElementBlock, b as createVNode, et as unref, p as computed } from "./vue.js";
import { D as textStyles, R as _plugin_vue_export_helper_default, s as appearance, w as lineHeights } from "./AppButton.js";
import { H as node, R as button, U as rect, n as observeFrameSizes, r as _sfc_main$1, v as describe$2, y as translate, z as label } from "./resize.js";
import { t as listAction } from "./tree.ui.js";
//#region ../src/tactic_stream/shared_ui/controls/catalog.ui.mjs
var users = [{
	value: "admin",
	login: "admin",
	label: "Administrator",
	displayName: "Administrator",
	initials: "A",
	groups: ["Artists"],
	primaryGroup: "Artists"
}, {
	value: "test",
	login: "test",
	label: "Test Artist",
	displayName: "Test Artist",
	initials: "TA",
	groups: ["Artists"],
	primaryGroup: "Artists"
}];
var choices = [
	{
		value: "model",
		label: "Model"
	},
	{
		value: "rig",
		label: "Rig"
	},
	{
		value: "publish",
		label: "Publish"
	}
];
//#endregion
//#region ../src/tactic_stream/shared_ui/controls/showcase.examples.mjs
function describe$1(model, family, width, language) {
	const tr = (text) => translate(text, language), nodes = [];
	const enabled = !["disabled", "readonly"].includes(model.state);
	const text = model.state === "long" ? "A much longer component label / Длинное название компонента" : model.text;
	const flags = {
		enabled: model.state !== "disabled",
		readOnly: model.state === "readonly",
		error: model.state === "error"
	};
	let y = 0, example = null;
	function add(item) {
		nodes.push(item);
		if (!example && !["Label", "Box"].includes(item.kind)) example = item;
	}
	function caption(title) {
		add(label("sampleCaption_" + y, rect(0, y, width, 24), tr(title), {
			fontRole: "section",
			weight: 600,
			role: "heading",
			level: 3
		}));
		y += 32;
	}
	function field(kind, id, properties, height = 36) {
		add(node(kind, id, rect(0, y, Math.min(width, 440), height), properties));
		y += height + 16;
	}
	if (family === "typography") {
		const roles = [
			"headline",
			"hero",
			"heading",
			"title",
			"bodyLarge",
			"body",
			"secondary",
			"caption"
		];
		for (const role of roles) {
			const h = Math.max(32, lineHeights[role] + 12);
			add(label("type_" + role, rect(0, y, width, h), role === "caption" ? "Caption · 0123456789" : text, {
				fontRole: role,
				weight: [
					"headline",
					"hero",
					"title"
				].includes(role) ? 600 : 400,
				role: family === "headers" ? "heading" : void 0,
				level: roles.indexOf(role) + 1
			}));
			y += h;
			add(label("typeToken_" + role, rect(0, y, width, 18), role + " · " + textStyles[role] + " px / " + lineHeights[role] + " px", {
				fontRole: "caption",
				color: "secondaryText"
			}));
			y += 32;
		}
		example = nodes[0];
	} else if (family === "headers") {
		caption("Section heading");
		add(label("sampleHeading", rect(0, y, width, 36), text, {
			fontRole: "hero",
			weight: 600,
			role: "heading",
			level: 2
		}));
		y += 44;
		add(label("sampleSubtitle", rect(0, y, width, 28), tr("Description"), { color: "secondaryText" }));
		y += 64;
		caption("Panel heading");
		add(node("Box", "samplePanelHeader", rect(0, y, width, 72), {
			background: "surfaceContainerLow",
			radius: 0,
			children: [
				node("Icon", "sampleHeadingIcon", rect(12, 18, 24, 24), {
					icon: "folder",
					color: "contentAccent"
				}),
				label("samplePanelTitle", rect(48, 8, Math.max(0, width - 100), 28), text, {
					fontRole: "title",
					weight: 600,
					role: "heading",
					level: 3
				}),
				label("samplePanelSubtitle", rect(48, 38, Math.max(0, width - 100), 20), tr("Description"), {
					fontRole: "secondary",
					color: "secondaryText"
				}),
				button("sampleHeadingAction", rect(Math.max(0, width - 44), 16, 36, 36), tr("Refresh"), "refresh", { type: "demo-header" }, enabled, { iconOnly: true })
			]
		}));
		y += 92;
		example = nodes.find((n) => n.id === "sampleHeading");
	} else if (family === "colors") {
		const roles = [
			"workspace",
			"panel",
			"surfaceContainerLowest",
			"surfaceContainerLow",
			"surfaceContainerHigh",
			"tableHeader",
			"contentSelection",
			"action",
			"green",
			"yellow",
			"error",
			"secondaryText"
		];
		const columns = Math.max(1, Math.floor(width / 220)), cell = width / columns;
		roles.forEach((role, i) => {
			const x = i % columns * cell, top = Math.floor(i / columns) * 64;
			add(node("Box", "color_" + role, rect(x, top, 40, 40), {
				background: role,
				radius: 6,
				border: "outlineVariant"
			}));
			add(label("colorName_" + role, rect(x + 52, top, cell - 60, 40), role, {
				fontRole: "secondary",
				wrap: true
			}));
		});
		y = Math.ceil(roles.length / columns) * 64;
		example = nodes[0];
	} else if (family === "buttons") {
		const w = Math.min(200, (width - 12) / 2);
		[
			[
				"Save",
				"save",
				{ highlighted: true }
			],
			[
				"Cancel",
				"close",
				{}
			],
			[
				"Delete",
				"delete",
				{ destructive: true }
			],
			[
				"Help",
				"help",
				{}
			]
		].forEach(([title, icon, options], i) => {
			add(button("sampleButton_" + i, rect(i % 2 * (w + 12), Math.floor(i / 2) * 52, w, 36), tr(title), icon, { type: "demo-" + title }, enabled, options));
		});
		y = 112;
		add(button("sampleIconButton", rect(0, y, 36, 36), tr("Refresh"), "refresh", { type: "demo-refresh" }, enabled, { iconOnly: true }));
		y += 52;
	} else if (family === "toggles") {
		field("CheckBox", "sampleCheckbox", {
			text: tr("Enabled"),
			checked: model.checked,
			enabled,
			action: { type: "checked" }
		});
		field("CheckBox", "sampleMixed", {
			text: tr("Selection"),
			checked: true,
			mixed: true,
			enabled,
			action: { type: "checked" }
		});
		field("Switch", "sampleSwitch", {
			text: tr("Notifications"),
			checked: model.checked,
			enabled,
			action: { type: "checked" }
		});
	} else if (family === "text-fields" || family === "numbers") {
		caption(family === "numbers" ? "Number" : "Name");
		field("Field", "sampleField", Object.assign({}, flags, {
			text: family === "numbers" ? model.number : text,
			label: tr("Name"),
			inputMode: family === "numbers" ? "decimal" : "text",
			action: { type: family === "numbers" ? "number" : "text" }
		}));
		if (family === "text-fields") {
			caption("Description");
			field("Area", "sampleArea", Object.assign({}, flags, {
				text: model.area,
				label: tr("Description"),
				action: { type: "area" }
			}), 100);
		}
	} else if (family === "choices") {
		caption("Process");
		field("Choice", "sampleChoice", {
			value: model.choice,
			options: choices,
			label: tr("Process"),
			enabled,
			action: { type: "choice" }
		});
	} else if (family === "dates") {
		caption("Start date");
		field("DateChoice", "sampleDate", Object.assign({}, flags, {
			text: model.date,
			language,
			label: tr("Start date"),
			action: { type: "date" },
			commitAction: { type: "date" }
		}));
	} else if (family === "user-choice") {
		caption("Assigned to");
		field("UserChoice", "sampleUser", {
			value: model.user,
			options: users,
			label: tr("Assigned to"),
			enabled,
			action: { type: "user" }
		});
	} else if (family === "pickers") {
		caption("Color");
		field("ColorChoice", "sampleColor", {
			value: model.color,
			text: tr("Color"),
			enabled,
			action: { type: "color" }
		});
		caption("Icon");
		field("IconChoice", "sampleIcon", {
			value: model.icon,
			enabled,
			action: { type: "icon" }
		});
	} else if (family === "icons") {
		const icons = [
			"save",
			"refresh",
			"search",
			"help",
			"person",
			"groups",
			"calendar",
			"folder",
			"table",
			"note",
			"workflow",
			"extension"
		];
		const columns = Math.max(1, Math.floor(width / 116)), cell = width / columns;
		icons.forEach((icon, i) => {
			const x = i % columns * cell, top = Math.floor(i / columns) * 92;
			add(node("Icon", "sampleIcon_" + i, rect(x + 10, top, 28, 28), {
				icon,
				color: "contentAccent"
			}));
			add(label("sampleIconName_" + i, rect(x, top + 36, cell - 8, 28), icon, { fontRole: "caption" }));
		});
		y = Math.ceil(icons.length / columns) * 92;
	} else if (family === "badges") {
		caption("Semantic colors");
		const colors = [
			"action",
			"cyan",
			"green",
			"yellow",
			"error",
			"secondaryText"
		];
		const columns = Math.max(1, Math.min(4, Math.floor((width + 12) / 148))), w = Math.min(140, (width - (columns - 1) * 12) / columns);
		colors.forEach((accent, i) => add(node("StatusChip", "sampleBadge_" + i, rect(i % columns * (w + 12), y + Math.floor(i / columns) * 40, w, 24), {
			text: model.state === "long" ? text : accent,
			accent,
			enabled,
			icon: i === 0 ? "clipboard-check" : ""
		})));
		y += Math.ceil(colors.length / columns) * 40 + 16;
		caption("Sizes and icons");
		add(node("StatusChip", "sampleBadgeNormal", rect(0, y, Math.min(width, 140), 24), {
			text: tr("Ready"),
			accent: "green",
			enabled
		}));
		y += 40;
		add(node("StatusChip", "sampleBadgeDense", rect(0, y, Math.min(width, 140), 20), {
			text: tr("Ready"),
			accent: "green",
			dense: true,
			icon: "clipboard-check",
			enabled
		}));
		y += 48;
		caption("Counters");
		for (const [i, count] of [
			0,
			1,
			125
		].entries()) add(node("SummaryChip", "sampleCounter_" + i, rect(i % columns * (w + 12), y + Math.floor(i / columns) * 44, w, 32), {
			text: tr("Notes"),
			count,
			icon: "note",
			accent: "action",
			enabled,
			action: { type: "demo-counter-" + count }
		}));
		y += Math.ceil(3 / columns) * 44 + 16;
	} else if (family === "tabs") {
		field("Segmented", "sampleTabs", {
			label: tr("Display"),
			value: model.tab,
			enabled,
			options: [
				{
					value: "overview",
					label: tr("Overview")
				},
				{
					value: "details",
					label: tr("Details")
				},
				{
					value: "activity",
					label: tr("Activity")
				}
			],
			action: { type: "tab" }
		});
		add(label("sampleTabValue", rect(0, y, width, 28), model.tab, { color: "secondaryText" }));
		y += 40;
	} else if (family === "lists") {
		caption("List");
		for (const [i, key] of [
			"assets",
			"shots",
			"tasks"
		].entries()) {
			const row = listAction("sampleList_" + key, rect(0, y, width, 56), key[0].toUpperCase() + key.slice(1), [
				"box",
				"film",
				"clipboard-check"
			][i], {
				type: "row",
				value: key
			}, enabled, {
				selected: model.row === key,
				endInset: 64
			});
			row.children.push(node("StatusChip", "sampleListCount_" + key, rect(Math.max(0, width - 60), 16, 48, 24), {
				text: String([
					12,
					8,
					24
				][i]),
				accent: "secondaryText",
				enabled: true
			}));
			add(row);
			y += 60;
		}
		y += 20;
		caption("Two-line list");
		for (const [i, title] of [
			"Model",
			"Rig",
			"Publish"
		].entries()) {
			const row = listAction("sampleDetailRow_" + i, rect(0, y, width, 60), title, "clipboard-check", {
				type: "row",
				value: title
			}, enabled, { selected: model.row === title });
			row.children.find((n) => n.kind === "Label").height = 28;
			row.children.push(label("sampleDetailSubtitle_" + i, rect(34, 30, Math.max(0, width - 46), 22), tr("Description"), {
				fontRole: "secondary",
				color: "secondaryText"
			}));
			add(row);
			y += 64;
		}
	} else if (family === "charts") for (const type of [
		"line",
		"bar",
		"donut"
	]) {
		caption(type === "line" ? "Line chart" : type === "bar" ? "Bar chart" : "Donut chart");
		const scene = describe$2({
			type,
			labels: [
				"Mon",
				"Tue",
				"Wed",
				"Thu",
				"Fri"
			],
			values: [
				4,
				8,
				5,
				12,
				9
			]
		}, "sampleChart_" + type, width, 220, language);
		add(node("Box", "sampleChartBox_" + type, rect(0, y, width, 220), {
			background: "transparent",
			clip: false,
			children: scene.nodes
		}));
		y += 244;
	}
	const properties = {};
	if (example) {
		for (const key of Object.keys(example)) if (![
			"kind",
			"id",
			"x",
			"y",
			"width",
			"height",
			"fontSize"
		].includes(key)) {
			if (key !== "children" || example.children.length) properties[key] = example[key];
		}
	}
	const code = family === "charts" ? "import { describe } from './controls/charts/chart.ui.mjs';\n\ndescribe({ type: 'line', labels: ['Mon', 'Tue', 'Wed'], values: [4, 8, 5] },\n  'chart', 600, 220, 'en');" : example ? `import { node, rect } from './core/frame.mjs';\n\nnode(${JSON.stringify(example.kind)}, 'example',\n  rect(0, 0, ${Math.round(example.width)}, ${Math.round(example.height)}),\n  ${JSON.stringify(properties, null, 2)}\n);` : "";
	return {
		nodes,
		height: y,
		code
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/controls/catalog.data.mjs
var catalogue = {
	levels: {
		primitive: "Базовый визуальный элемент или одно действие/значение; без проекта, бизнес-объекта и серверной операции.",
		composite: "Базовый составной контрол: собирает примитивы, имеет нейтральные данные и события, подходит разным формам.",
		infrastructure: "Механика ввода, позиционирования, окон, рендеринга или жизненного цикла; не отдельный визуальный контрол.",
		feature: "Форма, экран или предметный фрагмент: знает конкретный сценарий, предметную модель или операцию.",
		review: "Исходник учтён; его ответственность требует отдельного разбора. Это не подтверждённый базовый контрол."
	},
	families: [
		{
			id: "buttons",
			title: "Кнопки и действия",
			level: "primitive",
			native: [
				"Button",
				"CompactIconButton",
				"FilledActionButton",
				"DisclosureButton",
				"ItemCountActionButton",
				"PreviewNavigationButton",
				"RefreshIconButton",
				"MessageSendButton"
			],
			vue: [
				"AppButton",
				"DisclosureButton",
				"PreviewNavigationButton"
			],
			tokens: [
				"button",
				"action-count",
				"disclosure",
				"reveal"
			],
			variants: [
				"Обычная",
				"Primary / заполненная",
				"Tonal",
				"Destructive",
				"Текстовая / плоская",
				"Круглая иконка",
				"Прямоугольная toolbar action",
				"Счётчик поверх кнопки",
				"Раскрытие ветки",
				"Навигация превью",
				"Отправка / sending"
			],
			coverage: "contract",
			example: "button",
			gaps: ["Команда формы и доступность операции остаются у владельца. Native PopupAction не активируется повторно от autorepeat-release."],
			rule: "Общий Button + именованные варианты. Геометрия hit target, поверхности, иконки и бейджа задаётся отдельно; предметная команда остаётся у формы.",
			examples: [
				"button",
				"button-primary",
				"button-tonal",
				"button-danger",
				"button-filled-danger",
				"button-icon",
				"button-badge-zero",
				"button-badge",
				"button-badge-overflow",
				"button-disclosure",
				"button-preview",
				"button-send"
			],
			label: "Buttons and actions",
			category: "controls"
		},
		{
			id: "toggles",
			title: "Чекбоксы, radio, переключатели",
			level: "primitive",
			native: [
				"CheckBox",
				"Switch",
				"SegmentedButton"
			],
			vue: [
				"AppCheckbox",
				"AppSwitch",
				"AppSegmentedButton"
			],
			tokens: [
				"checkbox",
				"switch",
				"radio",
				"toggle",
				"segment"
			],
			variants: [
				"Checkbox обычный / compact / prominent",
				"Unchecked / checked / mixed",
				"Switch",
				"Radio",
				"Сегменты с текстом",
				"Сегменты с иконками",
				"Outlined segments",
				"Недоступный отдельный вариант"
			],
			coverage: "contract",
			example: "checkbox",
			gaps: ["Radio — именованный вариант выбора SegmentedButton, а не отдельный предметный редактор. Disabled-опции пропускаются клавиатурой."],
			rule: "Один смысл выбора и клавиатурной навигации; явные варианты плотности и вида, а не локальные CSS-копии.",
			examples: [
				"checkbox",
				"checkbox-checked",
				"checkbox-mixed",
				"checkbox-compact",
				"checkbox-prominent",
				"switch-off",
				"switch-on",
				"segments",
				"segments-icons",
				"segments-outline",
				"segments-disabled-option"
			],
			label: "Checkboxes and switches",
			category: "controls"
		},
		{
			id: "text-fields",
			title: "Текстовые поля",
			level: "primitive",
			native: ["TextField", "TextArea"],
			vue: ["AppTextField", "AppTextArea"],
			tokens: [
				"text-field",
				"textarea",
				"textinput",
				"textedit",
				"input",
				"field"
			],
			variants: [
				"Однострочное",
				"Многострочное",
				"Placeholder",
				"Password / reveal",
				"Readonly",
				"Ошибка и helper text",
				"Prefix / suffix / trailing action",
				"Табличный inline editor"
			],
			coverage: "contract",
			example: "field",
			gaps: ["IME, selection, undo и потеря focus проверяются настоящими вводами платформенного стенда. Предметная валидация не является частью базового поля.", "У оригинального TextField нет общего prefix/suffix API: такие подписи и кнопки собираются формой из базовых контролов. Это не отдельный недописанный контрол для переноса."],
			rule: "Общий ввод/selection/IME/validation presentation. Значение и предметная валидация принадлежат владельцу формы.",
			examples: [
				"field",
				"field-empty",
				"field-password",
				"field-readonly",
				"field-error",
				"field-inline",
				"text-area"
			],
			label: "Text fields",
			category: "controls"
		},
		{
			id: "search",
			title: "Поиск и подсказки",
			level: "composite",
			native: ["SearchField", "SearchSuggestionsPopup"],
			vue: ["AppSearchField"],
			tokens: [
				"search",
				"suggest",
				"completer",
				"autocomplete"
			],
			variants: [
				"Поиск с иконкой",
				"Очистка",
				"Загрузка",
				"Подсказки",
				"Поиск в меню / picker",
				"Компактный",
				"Поиск с trailing actions"
			],
			coverage: "contract",
			gaps: ["Подсказки получают нейтральные записи; TacticSearchField оставляет запрос, debounce и открытие результата своему controller."],
			rule: "SearchField не знает TSQL, проект или HTTP. Поисковая форма собирает его с фильтрами и владеет запросом.",
			examples: [
				"search",
				"search-empty",
				"search-suggestions"
			],
			example: "search",
			label: "Search and suggestions",
			category: "controls"
		},
		{
			id: "choices",
			title: "Комбобоксы и выбор из списка",
			level: "composite",
			native: ["ComboBox", "QuickFilterOptions"],
			vue: [
				"AppSelect",
				"StatusSelect",
				"QuickFilterOptions",
				"AppEditableSelect"
			],
			tokens: [
				"combo",
				"select",
				"choice",
				"dropdown"
			],
			variants: [
				"Обычный",
				"Пустой / not assigned",
				"Иконки",
				"Цветовые swatches",
				"Группы",
				"Поиск",
				"Multi-select + chips",
				"Статус с цветом",
				"Action field",
				"Длинные названия"
			],
			coverage: "contract",
			example: "choice",
			gaps: ["1000 локальных записей проверяют packing/виртуализацию. Системный fallback select в браузерах без base-select сохраняет нативное оформление ОС."],
			rule: "Нейтральная модель options/value и одинаковые события. Загрузка проектов/процессов/статусов не входит в контрол.",
			examples: [
				"choice",
				"choice-empty",
				"choice-disabled-option",
				"choice-icons",
				"choice-status",
				"packed-choices"
			],
			label: "Selection controls",
			category: "controls"
		},
		{
			id: "numbers",
			title: "Числа, spinbox, sliders",
			level: "composite",
			native: ["SpinBox", "Slider"],
			vue: ["AppSlider", "AppSpinBox"],
			tokens: [
				"spin",
				"slider",
				"range",
				"number"
			],
			variants: [
				"Integer / decimal",
				"Min / max / step",
				"Ввод и стрелки",
				"Slider horizontal / vertical",
				"Текущее значение",
				"Клавиатура и колесо"
			],
			coverage: "contract",
			example: "integer",
			gaps: ["Публичный QML SpinBox сохраняет scaled-int API Qt (32-bit); JS number не расширяет его диапазон. EN/RU grouping, decimal, clamp и external-model binding проверяются отдельно."],
			rule: "Общие range/step/clamp/commit правила. Не считать центральное положение thumb проверкой поведения.",
			examples: [
				"integer",
				"decimal",
				"integer-min",
				"integer-max",
				"slider",
				"slider-step",
				"slider-fixed"
			],
			label: "Numeric controls",
			category: "controls"
		},
		{
			id: "dates",
			title: "Дата, время, календари",
			level: "composite",
			native: ["DateField", "ActivityCalendarPopup"],
			vue: ["AppDateField", "ActivityCalendar"],
			tokens: [
				"date",
				"time",
				"calendar",
				"month",
				"day"
			],
			variants: [
				"Date only",
				"Date + time",
				"Time only",
				"Месяц и дни",
				"Сегодня / очистить",
				"Високосный год",
				"Год до 100",
				"Неверная дата",
				"Readonly / disabled",
				"Диапазон дат"
			],
			coverage: "contract",
			example: "date",
			gaps: ["ActivityCalendarPopup — фильтр истории активности, а не базовый календарь DateField; его полный экран относится к B11."],
			rule: "Календарь выбора даты — базовый составной контрол. Планировщик задач с загрузкой/сохранением — форма/панель.",
			examples: [
				"date",
				"datetime",
				"date-early-year",
				"date-invalid",
				"date-empty"
			],
			label: "Date and time",
			category: "controls"
		},
		{
			id: "identity",
			title: "Аватары, имя пользователя, группы",
			level: "composite",
			native: [
				"UserAvatar",
				"UserIdentity",
				"UserGroupSection",
				"ProfileInfoRow"
			],
			vue: [
				"UserIdentity",
				"UserGroupSection",
				"ProfileInfoRow"
			],
			tokens: [
				"avatar",
				"identity",
				"user-badge",
				"profile-row",
				"presence"
			],
			variants: [
				"Фото",
				"Один / два инициала",
				"Fallback person",
				"Круг / квадрат",
				"Имя + login",
				"Retired",
				"Presence dot",
				"Размеры строки / шапки / профиля",
				"Группа пользователей"
			],
			coverage: "contract",
			gaps: ["UserAvatar обращается к profile/userModel и является адаптером предметных данных; нейтральный avatar — ItemPreview. Отдельного готового presence-dot контрола в оригинале нет."],
			rule: "Identity принимает нейтральные данные профиля; редактор пользователя и операции членства — отдельные формы.",
			examples: [
				"avatar-initials",
				"avatar-two-initials",
				"avatar-fallback",
				"identity",
				"identity-retired",
				"identity-emphasized",
				"user-group",
				"user-group-compact",
				"user-group-empty",
				"profile-info",
				"avatar-photo"
			],
			example: "avatar-initials",
			label: "Avatars and identity",
			category: "display"
		},
		{
			id: "user-choice",
			title: "Выбор пользователя",
			level: "composite",
			native: [
				"UserComboBox",
				"UserPicker",
				"UserFilter"
			],
			vue: ["UserComboBox", "UserPicker"],
			tokens: [
				"user-combo",
				"user-picker",
				"assignee",
				"member-picker"
			],
			variants: [
				"Single select",
				"Not assigned",
				"Поиск по имени/login/group",
				"Multi-select",
				"Selected chips",
				"Группировка",
				"Клавиатурный выбор"
			],
			coverage: "contract",
			example: "user",
			gaps: ["Поиск/выбор сохраняют скрытые выбранные записи. Данные пользователя, ACL и сохранение назначения не принадлежат пикеру."],
			rule: "Контрол получает готовую модель пользователей и возвращает identity; он не меняет ACL и не выполняет серверный поиск самостоятельно.",
			examples: [
				"user",
				"user-empty",
				"users-multiple"
			],
			label: "User selection",
			category: "controls"
		},
		{
			id: "pickers",
			title: "Цвет, иконка, emoji, изображение",
			level: "composite",
			native: [
				"ColorField",
				"ColorPickerDialog",
				"IconPickerButton",
				"EmojiPicker",
				"ImagePicker",
				"AccentPresetPicker"
			],
			vue: [
				"AppColorInput",
				"ColorPicker",
				"IconPicker",
				"EmojiPicker",
				"ImagePicker",
				"AccentPresetPicker"
			],
			tokens: [
				"picker",
				"swatch",
				"palette",
				"emoji",
				"icon-library"
			],
			variants: [
				"Color swatch",
				"Plane / hue / hex / alpha",
				"Icon search / set / virtual grid",
				"Emoji categories / recent / search",
				"Image choose / clear / preview",
				"Accent presets"
			],
			coverage: "contract",
			example: "color",
			gaps: ["Выбор локального файла остаётся системной возможностью хоста. Browser File и native URL/path не подменяются одним фиктивным API."],
			rule: "Picker выбирает значение; загрузка/сохранение файла или изменение настройки выполняется владельцем сценария.",
			examples: [
				"color",
				"icon-choice",
				"emoji",
				"image-picker",
				"accent-presets"
			],
			label: "Color, icon and emoji pickers",
			category: "controls"
		},
		{
			id: "icons",
			title: "Иконки и служебные глифы",
			level: "primitive",
			native: ["IconFontData", "MaterialIcon"],
			vue: ["AppIcon"],
			tokens: ["icon", "glyph"],
			variants: [
				"Пять наборов",
				"Semantic alias",
				"Точный set:name",
				"Force solid",
				"Оптический размер",
				"Цвет роли",
				"Иконка внутри контрола"
			],
			coverage: "contract",
			example: "icon-material",
			gaps: ["Проверяются реальные Unicode-глифы и шрифтовые наборы. Разная растеризация шрифта ОС не означает разные имена иконок."],
			rule: "Один семантический словарь и fallback. Разница выбора глифа — дефект; сглаживание растеризаторов учитывается отдельно.",
			examples: [
				"icon-material",
				"icon-solid",
				"icon-outline",
				"icon-fluent",
				"icon-fluent-filled",
				"icon-small",
				"icon-large"
			],
			label: "Icons",
			category: "foundations"
		},
		{
			id: "tabs",
			title: "Табы и полосы вкладок",
			level: "composite",
			native: [
				"TabButton",
				"WorkspaceTabVisual",
				"SectionTabRail"
			],
			vue: [
				"AppTabButton",
				"WorkspaceTabs",
				"SectionTabRail",
				"WorkspaceTabVisual",
				"SectionTabVisual"
			],
			tokens: [
				"tab",
				"tabbar",
				"tab-rail",
				"workspace-tab"
			],
			variants: [
				"Section tabs",
				"Workspace tabs",
				"Dock tabs",
				"Closable",
				"Dirty / count",
				"Overflow",
				"Reorder / drag",
				"Контекстное меню",
				"Текущая / disabled / mobile"
			],
			coverage: "contract",
			gaps: ["Поиск/section tabs имеют отдельные свежие B01 сценарии drag, close, reopen и сохранения; standalone tab показывает нейтральную поверхность."],
			rule: "Разделить выбор вкладки, её содержимое и host docking. Общая вкладка не должна знать задачи/проекты.",
			examples: ["tab", "tab-current"],
			example: "tab",
			label: "Tabs",
			category: "navigation"
		},
		{
			id: "badges",
			title: "Бейджи, chips, счётчики и точки",
			level: "composite",
			native: [
				"SummaryChip",
				"StatusChip",
				"CompletionStrip",
				"QuickFilterChip",
				"MessageReactionChip"
			],
			vue: [
				"SummaryChip",
				"StatusChip",
				"ReactionChip",
				"QuickFilterChip"
			],
			tokens: [
				"badge",
				"chip",
				"count",
				"unread",
				"status-dot",
				"completion"
			],
			variants: [
				"Badge count 0 / 1 / 99+",
				"Unread",
				"Notification/error",
				"Status dot",
				"Status chip",
				"Filter chip + remove",
				"Clickable / passive",
				"Selected",
				"Compact",
				"Completion strip"
			],
			coverage: "contract",
			gaps: ["CompletionStrip/TacticCompletionCell знают задачи/снимки и переходы: предметные фрагменты B07/B08. Базовые StatusChip и счётчики не сохраняют данные."],
			rule: "Badge (наложение), Chip (элемент потока) и status indicator (состояние) — разные роли. У каждой один контракт и именованные варианты.",
			examples: [
				"chip",
				"chip-clickable",
				"chip-compact",
				"status-chip",
				"status-chip-dense",
				"status-chip-action",
				"reaction",
				"reaction-count",
				"reaction-checked",
				"filter-chip",
				"filter-chip-checked",
				"filter-chip-subtle",
				"filter-chip-marker",
				"filter-chip-emphasis"
			],
			example: "chip",
			label: "Badges, chips and counters",
			category: "display"
		},
		{
			id: "headers",
			title: "Заголовки, toolbar, переключатели вида",
			level: "composite",
			native: [
				"ColumnHeaderGrip",
				"EditorPanel",
				"SectionLabel",
				"InfoValueStrip",
				"ConfigurationSection",
				"SObjectFieldFrame"
			],
			vue: [
				"EditorPanel",
				"SectionLabel",
				"InfoValueStrip",
				"ConfigurationSection",
				"FormFieldFrame"
			],
			tokens: [
				"header",
				"heading",
				"titlebar",
				"toolbar",
				"view-switch",
				"mode-switch",
				"surface-switch"
			],
			variants: [
				"Заголовок раздела",
				"Панель: icon + title + subtitle + actions",
				"Toolbar",
				"Title + count",
				"Header с tabs",
				"List / cards / table switcher",
				"Back / collapse",
				"Sticky"
			],
			coverage: "contract",
			gaps: ["EditorPanel, section, strip и FormFieldFrame — нейтральные компоновки. Поля, операции и серверная валидация задаются формой."],
			rule: "Нейтральная шапка/toolbar — базовая композиция. TaskInspectorHeader и управление конкретной рабочей областью — фрагмент формы.",
			examples: [
				"header",
				"header-back",
				"header-actions",
				"editor-panel",
				"configuration-section",
				"section-label",
				"info-values",
				"field-frame",
				"field-frame-required",
				"field-frame-error",
				"field-frame-readonly"
			],
			example: "header",
			label: "Headings and toolbars",
			category: "foundations"
		},
		{
			id: "menus",
			title: "Меню, popover и списки действий",
			level: "composite",
			native: [
				"Menu",
				"ScrollablePopup",
				"TextContextMenu",
				"ActionMenu",
				"ActionMenuRow"
			],
			vue: [
				"AppMenu",
				"AppMenuItem",
				"ActionRow",
				"ActionRows"
			],
			tokens: [
				"menu",
				"popover",
				"context",
				"submenu",
				"account-panel"
			],
			variants: [
				"Anchored",
				"Context menu",
				"Submenu",
				"Checkable item",
				"Icon + label + shortcut",
				"Separator / heading",
				"Scrollable",
				"Searchable",
				"Disabled",
				"Escape / outside click / restore focus"
			],
			coverage: "contract",
			example: "menu",
			gaps: ["Меню, check/radio rows, separators, submenus, tooltips и закрытие/focus проверяются каталогом и существующими menu/platform сценариями."],
			rule: "Меню — базовый составной контрол. Его команды передаются снаружи; ObjectActionsMenu с ACL и запросами — предметная композиция.",
			examples: ["menu", "menu-checks"],
			label: "Menus and popovers",
			category: "navigation"
		},
		{
			id: "popups",
			title: "Popup, dialog и оконная механика",
			level: "infrastructure",
			native: [
				"Popup",
				"Dialog",
				"DialogActions",
				"PopupBackground",
				"PopupScrim",
				"PopupCoordinator",
				"HoverReleaseCoordinator"
			],
			vue: [
				"WindowControls",
				"MobilePage",
				"AppDialog"
			],
			tokens: [
				"popup",
				"dialog",
				"modal",
				"window",
				"scrim",
				"backdrop"
			],
			variants: [
				"Non-modal",
				"Modal",
				"Anchored",
				"Floating",
				"Docked",
				"Close/minimize/maximize",
				"Drag / resize",
				"Stacking / focus / owner"
			],
			coverage: "contract",
			gaps: ["Позиционирование, scrim, ownership и native Popup.Window — инфраструктура. Полная предметная форма внутри окна проверяется в своём batch."],
			rule: "Host решает ownership/lifecycle, форма — свой сценарий, DialogActions — нейтральная строка действий.",
			examples: [],
			label: "Dialogs and windows",
			category: "navigation"
		},
		{
			id: "feedback",
			title: "Tooltip, loading, progress, empty/error",
			level: "composite",
			native: [
				"ToolTip",
				"BusyIndicator",
				"EmptyState",
				"InitialBatchPresentation",
				"ContentLoadingOverlay",
				"TacticCompletionCell",
				"ErrorDialog",
				"ProgressBar"
			],
			vue: [
				"BusyIndicator",
				"AppProgress",
				"CompletionCell",
				"EmptyState",
				"ContentLoadingOverlay"
			],
			tokens: [
				"tooltip",
				"progress",
				"busy",
				"spinner",
				"empty",
				"skeleton",
				"error",
				"notice",
				"warning",
				"alert"
			],
			variants: [
				"Tooltip",
				"Busy inline / block",
				"Determinate / indeterminate",
				"Progress + cancel",
				"Empty state",
				"Error + retry",
				"Skeleton",
				"Inline validation"
			],
			coverage: "contract",
			example: "busy",
			gaps: ["Нет готового отдельного skeleton-контрола в оригинале: InitialBatchPresentation управляет появлением делегатов, а не рисует skeleton."],
			rule: "Сообщение об ошибке и retry action поступают снаружи; контрол не перезапускает серверную операцию сам.",
			examples: [
				"busy",
				"progress",
				"progress-empty",
				"progress-complete",
				"progress-indeterminate",
				"loading-overlay",
				"loading-cancellable",
				"empty",
				"error-retry"
			],
			label: "Feedback and progress",
			category: "feedback"
		},
		{
			id: "lists",
			title: "Списки, дерево, строки",
			level: "composite",
			native: [
				"SmoothListView",
				"EditorListItem",
				"HierarchyGuide",
				"HierarchyReveal",
				"TreeExpansionMotion",
				"NavigationRow"
			],
			vue: [
				"ItemSurface",
				"NavigationRow",
				"EditorListItem",
				"VirtualCollection"
			],
			tokens: [
				"list",
				"tree",
				"hierarchy",
				"row",
				"selection"
			],
			variants: [
				"Обычная / selected / hover строка",
				"Одно / двухстрочная",
				"Tree indent / guide / disclosure",
				"Checkbox row",
				"Virtualized",
				"Variable-height collections and tiles; retained offscreen focus (tools/frame_search)",
				"Loading / empty",
				"Keyboard selection",
				"Navigation drawer: mouse/touch, off-screen keys, focus and reserved scrollbar gutter"
			],
			coverage: "contract",
			example: "tree",
			gaps: ["Нейтральный list/tree контракт покрывает virtual rows, selection, раскрытие и keyboard. ProcessSelectionTree остаётся предметной формой."],
			rule: "Tree row и navigation — базовый контрол; загрузка и смысл веток принадлежат форме.",
			examples: [
				"tree",
				"list-item",
				"list-item-selected",
				"list-item-badge",
				"list-item-long"
			],
			label: "Lists and trees",
			category: "display"
		},
		{
			id: "tables",
			title: "Табличная база и ячейки",
			level: "composite",
			native: ["FrameGrid", "FrameGridBranch"],
			vue: ["FrameGrid"],
			tokens: [
				"grid",
				"table",
				"cell",
				"column",
				"sort"
			],
			variants: [
				"Header / row header",
				"Sort / resize / reorder columns",
				"Selection",
				"Text / checkbox / icon cell",
				"Inline edit",
				"Frozen / scroll",
				"Virtualized"
			],
			coverage: "contract",
			example: "table",
			gaps: ["Это контракт Grid (virtual cells, selection/focus, resize, drafts, readonly). Production Table View и его виджеты остаются B07."],
			rule: "Grid нейтрален к Search Type; widget-config renderer и сохранение SObject — отдельный уровень.",
			examples: ["table", "table-readonly"],
			label: "Tables and cells",
			category: "display"
		},
		{
			id: "scroll-layout",
			title: "Прокрутка, splitters, layout",
			level: "composite",
			native: [
				"ScrollBar",
				"SplitterHandle",
				"ResizeGripVisual",
				"ResponsiveFlow",
				"DockDragGrip",
				"DockWorkspaceFooter",
				"SettingsRow",
				"SettingsNavigationItem",
				"AdminSaveBar"
			],
			vue: [
				"AppSplitter",
				"ResponsiveFlow",
				"DockGrip",
				"SettingRow",
				"AdminSaveBar",
				"DockWorkspaceFooter"
			],
			tokens: [
				"scroll",
				"splitter",
				"resize",
				"grip",
				"flow",
				"settings-row",
				"footer"
			],
			variants: [
				"Vertical / horizontal scrollbar",
				"Rest / hover / pressed / disabled",
				"Splitter",
				"Keyboard resize",
				"Grip",
				"Responsive flow",
				"Label-help-control row",
				"Footer actions"
			],
			coverage: "contract",
			example: "setting-row",
			gaps: ["Оба направления overflow, keyboard splitter и drag проверяются реальным вводом. Физический touch/OS compositor не заменяются synthetic input."],
			rule: "Layout-кирпичики знают размеры/слоты, а не сохранение настроек проекта.",
			examples: [
				"setting-row",
				"flow",
				"scroll-vertical",
				"scroll-horizontal",
				"scroll-both",
				"splitter-vertical",
				"splitter-horizontal"
			],
			label: "Scroll, splitters and layout",
			category: "navigation"
		},
		{
			id: "typography",
			title: "Текст, elide, markdown, кодовые блоки",
			level: "primitive",
			native: [
				"Typography",
				"SelectableText",
				"DocumentPane",
				"MessageBodyText"
			],
			vue: [
				"MiddleElide",
				"MarkdownText",
				"DocumentPane",
				"CodeBlock"
			],
			tokens: [
				"label",
				"text",
				"elide",
				"markdown",
				"code-block",
				"typography"
			],
			variants: [
				"Именованные text roles",
				"Single / wrap / elide",
				"Middle elide",
				"Selectable",
				"Links",
				"Markdown",
				"Monospace / code block",
				"Пустой / длинный / mixed script"
			],
			coverage: "contract",
			gaps: ["DocumentPane использует реальные Qt Markdown и browser Markdown renderer; сложный rich text и растеризация имеют явные платформенные границы. Сохранение/ссылки принадлежат владельцу."],
			rule: "Текстовые роли не заменяют контракты wrapping/selection/links. Rich renderer не должен владеть предметными запросами.",
			examples: ["markdown", "middle-elide"],
			example: "markdown",
			label: "Typography",
			category: "foundations"
		},
		{
			id: "previews",
			title: "Preview, thumbnail, карточки файлов",
			level: "composite",
			native: [
				"ItemPreview",
				"ItemSurface",
				"AttachmentCard",
				"MessageTimelineFrame",
				"MessageForwardPreview",
				"MessageReplyPreview",
				"SnapshotPreviewLayers"
			],
			vue: [
				"ItemPreview",
				"ItemSurface",
				"AttachmentCard"
			],
			tokens: [
				"preview",
				"thumbnail",
				"attachment",
				"image",
				"surface",
				"card"
			],
			variants: [
				"Photo / initials / icon",
				"Round / square",
				"Outlined",
				"Fit / crop",
				"Loading / failure / retry",
				"File card",
				"Image card",
				"Selected surface / accent rail"
			],
			coverage: "contract",
			gaps: ["Фото, contain/crop, broken/loading и selected border показаны отдельно. Rounded mask проверяется Windows/OpenGL; Qt software не подтверждает маску. AttachmentCard/forward/reply/snapshot layers — предметные компоненты."],
			rule: "Карточка нейтральных данных — составной контрол; ObjectCard с командами/ACL — предметный фрагмент.",
			examples: [
				"preview-square",
				"preview-outline",
				"preview-broken",
				"preview-loading",
				"preview-photo",
				"preview-contain",
				"preview-selected"
			],
			example: "preview-square",
			label: "Image and file previews",
			category: "display"
		},
		{
			id: "drag-files",
			title: "Drop zones, файлы, clipboard",
			level: "infrastructure",
			native: [
				"AttachmentDropArea",
				"DropTargetOverlay",
				"ImageFileDialog",
				"FileInput"
			],
			vue: ["DropTargetOverlay", "AppFileInput"],
			tokens: [
				"drop",
				"upload",
				"file-dialog",
				"clipboard",
				"drag"
			],
			variants: [
				"Drag enter / valid / invalid / busy",
				"File choose",
				"Clipboard image/text",
				"Paste",
				"Native filesystem capability",
				"Browser file input"
			],
			coverage: "contract",
			gaps: ["DropTargetOverlay — нейтральное состояние drop target. AttachmentDropArea исполняет attachmentController.add_files; фактический перенос/загрузка относится к B11/B12."],
			rule: "Обратиться к файловой системе — адаптер платформы; политика check-in/upload — предметный сценарий.",
			examples: ["drop-target", "drop-rejected"],
			example: "drop-target",
			label: "Files, clipboard and drop zones",
			category: "specialized"
		},
		{
			id: "editors",
			title: "Редакторы текста/кода",
			level: "composite",
			native: [
				"ScriptCodeEditor",
				"FrameCode",
				"FrameCodeBranch",
				"ScriptOutline",
				"KnowledgeTableOfContents",
				"TableTextEditor"
			],
			vue: ["CodeEditor", "FrameCode"],
			tokens: [
				"code-editor",
				"source-editor",
				"completion",
				"syntax",
				"document"
			],
			variants: [
				"Plain code",
				"Highlight",
				"Line numbers",
				"Search / replace",
				"Undo / redo",
				"IME",
				"Completion",
				"Readonly / error / dirty"
			],
			coverage: "contract",
			gaps: ["Контракт FrameCode: текст, readonly, undo, search/replace, selection и clipboard. ScriptCodeEditor/ScriptOutline и выполнение скриптов остаются B13."],
			rule: "CodeEditor не знает Script Editor, Batch Manager и выполнение Python. Эти формы используют редактор.",
			examples: ["code", "code-readonly"],
			example: "code",
			label: "Text and code editors",
			category: "specialized"
		},
		{
			id: "graphs",
			title: "Графы и соединения",
			level: "composite",
			native: [
				"NodeGraph",
				"NodeGraphSelectionArea",
				"GraphPort",
				"FrameGraph",
				"FrameGraphBranch"
			],
			vue: ["FrameGraph"],
			tokens: [
				"graph",
				"edge",
				"port",
				"connection",
				"node"
			],
			variants: [
				"Node / port / edge",
				"Single / multi select",
				"Drag",
				"Connect",
				"Zoom / pan",
				"Readonly",
				"Keyboard delete",
				"Marquee"
			],
			coverage: "contract",
			gaps: ["FrameGraph — нейтральные nodes/edges/selection/move. NodeGraph и XML pipeline controller — отдельный существующий предметный редактор B03/B10."],
			rule: "Нейтральный graph control не владеет XML schema/pipeline, ACL или сохранением.",
			examples: ["graph", "graph-readonly"],
			example: "graph",
			label: "Graphs and connections",
			category: "specialized"
		},
		{
			id: "input-runtime",
			title: "Ввод, focus, ripple, координация",
			level: "infrastructure",
			native: [
				"ActivationHandler",
				"PopupAction",
				"MaterialRipple"
			],
			vue: [],
			tokens: [
				"activation",
				"ripple",
				"pointer",
				"focus",
				"gesture"
			],
			variants: [
				"Mouse / touch / pen",
				"Press / release / cancel",
				"Dedup synthesized click",
				"Keyboard activation",
				"IME",
				"Focus return",
				"Destroy while open"
			],
			coverage: "contract",
			gaps: ["Настоящие мышь/touch/keyboard, отмена, одна активация и три DPI выполняются platform gate. OS IME composition и физический pen требуют аппаратной проверки."],
			rule: "Одна активация на один пользовательский жест; событийная механика не исполняет бизнес-команды сама.",
			examples: [],
			label: "Input and focus infrastructure",
			category: "specialized"
		},
		{
			id: "domain-fragments",
			title: "Предметные формы и фрагменты — отдельно от базы",
			level: "feature",
			native: [
				"ProjectCard",
				"ProjectFilterToggles",
				"ProcessSelectionTree",
				"TaskWorkspaceModeSwitcher",
				"TaskWorkspaceSurfaceSwitcher",
				"ScriptSavedHistoryButton",
				"TacticSearchField",
				"MessageComposerField",
				"UserGroupMembershipEditor"
			],
			vue: ["TaskInspectorHeader", "TaskWorkspaceSurfaceSwitcher"],
			tokens: [],
			variants: [
				"Project selection/filter",
				"Process selector",
				"Task header/view switcher",
				"Script history",
				"Tactic search",
				"Message composer",
				"Membership editor"
			],
			coverage: "not-base",
			gaps: ["Расположение в controls/ не делает ProjectFilterToggles или ProjectCard базовым контролом.", "Существующие forms/fragments входят в полный индекс исходников, но не завышают число базовых контролов."],
			rule: "Если компонент знает Search Type, задачи, script token, членство/ACL или вызывает предметный controller, это композиция сценария. Вынести из неё можно нейтральную часть.",
			label: "Domain components",
			category: "specialized"
		},
		{
			id: "colors",
			title: "Цвета и поверхности",
			label: "Colors and surfaces",
			category: "foundations",
			level: "primitive",
			native: [],
			vue: [],
			tokens: [
				"palette",
				"surface",
				"semantic"
			],
			variants: [
				"Semantic roles",
				"Light and dark surfaces",
				"Contrast pairs"
			]
		},
		{
			id: "charts",
			title: "Диаграммы",
			label: "Charts",
			category: "display",
			level: "primitive",
			native: ["FrameChart"],
			vue: ["FrameChart"],
			tokens: ["chart"],
			variants: [
				"Bar",
				"Line",
				"Donut"
			]
		}
	],
	reviewedFeatureRoots: {
		native: [
			"ActivityEventCard",
			"ActivityFeedView",
			"AdvancedSearchView",
			"AttachmentComposerControls",
			"AttachmentStagingPanel",
			"CheckinDialogs",
			"CheckinOptionsPage",
			"CollaborationInitializationState",
			"CommitQueueView",
			"CommitWorkspaceView",
			"CommunicationView",
			"ConfigurationAppearancePage",
			"ConfigurationCachePage",
			"ConfigurationDccPage",
			"ConfigurationGlobalPreferencesPage",
			"ConfigurationPage",
			"ConfigurationProjectPage",
			"ConfigurationRepositoryPage",
			"ConfigurationServerPage",
			"ConfigurationTaskPreferencesPage",
			"ConfigurationView",
			"CostReportsView",
			"DatabaseBatchEditorView",
			"DatabaseEditorView",
			"DccOptionsView",
			"DebugLogView",
			"DeleteSObjectView",
			"DemoThinClientWindow",
			"DescriptionEditor",
			"DropPlateView",
			"DuplicateSObjectView",
			"FileWorkspaceCatalog",
			"FileWorkspaceChangelistFiles",
			"FileWorkspaceChangelistView",
			"FileWorkspaceComparisonDialog",
			"FileWorkspaceDepots",
			"FileWorkspaceFileRow",
			"FileWorkspaceGetRevisionDialog",
			"FileWorkspaceHistory",
			"FileWorkspaceInspector",
			"FileWorkspaceLog",
			"FileWorkspaceMappings",
			"FileWorkspaceNavigation",
			"FileWorkspaceRevertDialog",
			"FileWorkspaceReviewDialog",
			"FileWorkspaceShelfDialog",
			"FileWorkspaceStorage",
			"FileWorkspaceStreamEditor",
			"FileWorkspaceStreamGraph",
			"FileWorkspaceStreams",
			"FileWorkspaceSubmitDialog",
			"FileWorkspaceTargetDialog",
			"FileWorkspaceTreeRow",
			"FileWorkspaceView",
			"HandlerServerView",
			"HelpView",
			"IngestConflictDialog",
			"IngestFileList",
			"IngestFilesView",
			"IngestRuleEditor",
			"ItemCheckinDialogs",
			"ItemQuickActions",
			"KnowledgeArticleAttachments",
			"KnowledgeArticleContent",
			"KnowledgeArticleEditor",
			"KnowledgeArticleViewer",
			"KnowledgeAttachmentLibrary",
			"KnowledgeBaseView",
			"KnowledgeEditorImageOverlay",
			"KnowledgeImageSelectionOverlay",
			"KnowledgeLinkedObjectHeader",
			"KnowledgeNavigation",
			"KnowledgeRevisionHistoryPopup",
			"KnowledgeRichTextBlockDecorations",
			"KnowledgeRichTextToolbar",
			"LinkList",
			"LinkSObjectsView",
			"LoginDialog",
			"MatchingTemplatesView",
			"MessageReactionPicker",
			"MessagesConversationList",
			"MessagesTimeline",
			"MessagesView",
			"MilestoneManagerView",
			"NotesTimelinePosition",
			"NotificationStack",
			"NotificationsView",
			"ProcessFilterEditorView",
			"ProjectChooser",
			"ProjectEditorView",
			"ProjectTemplatesView",
			"ProjectWizardView",
			"QueueView",
			"QuickFilterEditorView",
			"RepositoryEditorView",
			"RepositorySetupPrompt",
			"RepositorySyncEditorView",
			"RepositorySyncView",
			"RevisionHistoryPopup",
			"SKeyPreviewCard",
			"SObjectFieldDelegate",
			"SObjectFieldEditor",
			"SObjectFieldGrid",
			"SObjectInfoView",
			"SObjectSnapshotTree",
			"SObjectValueEditor",
			"ScreenshotMakerView",
			"ScreenshotView",
			"ScriptEditorView",
			"ScriptShelfBar",
			"ScriptShelfEditorView",
			"ScriptTree",
			"ScriptTreePicker",
			"ScriptTriggerEditorView",
			"SearchAssigneeFilterPopup",
			"SearchPresetBar",
			"SearchQuickFilterPopup",
			"SearchResultMenus",
			"SearchResultSurface",
			"SearchResultTable",
			"SearchResultTableHeader",
			"SearchResultsPane",
			"SearchWorkspaceView",
			"ServerPresetsView",
			"SidebarSearchPreview",
			"SnapshotBrowser",
			"SnapshotBrowserOptionsMenu",
			"SnapshotBrowserToolbar",
			"SnapshotSummary",
			"SyncEditorView",
			"SyncQueueView",
			"TableViewPresetMenu",
			"TacticStructuredTableCell",
			"TacticTableActionCell",
			"TacticTableCellDisplay",
			"TacticTableInlineEditor",
			"TacticTaskCards",
			"TacticTaskCell",
			"TagCloudPopup",
			"TaskBrowserTable",
			"TaskBulkBar",
			"TaskCalendarView",
			"TaskDockView",
			"TaskGanttProgressHandle",
			"TaskGanttView",
			"TaskHiddenDetails",
			"TaskInspector",
			"TaskPendingChangesBar",
			"TaskProcessPanel",
			"TaskQuickFilterPopup",
			"TaskTableEditorCell",
			"TaskWorkspaceSummary",
			"TasksWorkspaceView",
			"TimesheetView",
			"UiPerformanceView",
			"UpdatePrompt",
			"UpdateView",
			"UserProfileEditorDialog",
			"UserProfileView",
			"UserWorkSummary",
			"WatchFolderDeleteDialog",
			"WatchFolderEditorView",
			"WatchFoldersView",
			"WorkHourEditorDialog",
			"WorkHoursSummary",
			"WorkReportsView",
			"WorkspaceCard",
			"WorkspaceChangeBranch",
			"WorkspaceChangeFile",
			"WorkspaceDetails",
			"WorkspaceDialogs",
			"WorkspaceFileDropTarget",
			"WorkspaceFilters",
			"WorkspaceFooter",
			"WorkspaceLayoutPresetMenuSection",
			"WorkspaceResultItem",
			"WorkspaceToolbar",
			"WorkspaceTreePane",
			"WorkspaceView"
		],
		vue: [
			"QueueDialogs",
			"QueuePreview",
			"QueueWorkspace",
			"StreamGraph",
			"StreamGraphEdges",
			"WorkspaceCatalog",
			"WorkspaceInspectorView",
			"WorkspaceLogEntries",
			"WorkspaceLogMessage",
			"WorkspaceTable",
			"WorkspaceToolbar",
			"WorkspaceTreePaint",
			"WorkspaceTreePane"
		]
	},
	levelOverrides: {
		IconFontData: "infrastructure",
		ColumnHeaderGrip: "primitive",
		SegmentedButton: "composite",
		AppSegmentedButton: "composite",
		TabButton: "primitive",
		AppTabButton: "primitive",
		UserAvatar: "feature",
		BusyIndicator: "primitive",
		AppProgress: "primitive",
		ScrollBar: "primitive",
		SplitterHandle: "primitive",
		HierarchyGuide: "primitive",
		HierarchyReveal: "primitive",
		AppMenuItem: "primitive",
		ActionMenuRow: "primitive",
		DialogActions: "composite",
		CodeBlock: "composite",
		MarkdownText: "composite",
		DocumentPane: "composite",
		Typography: "infrastructure",
		NavigationRow: "composite",
		SidebarTreeRow: "composite",
		ActionRow: "primitive",
		ActivityCalendarPopup: "feature",
		ActivityCalendar: "feature",
		CompletionStrip: "feature",
		TacticCompletionCell: "feature",
		CompletionCell: "feature",
		InitialBatchPresentation: "infrastructure",
		AttachmentDropArea: "feature",
		ImageFileDialog: "infrastructure",
		AttachmentCard: "feature",
		MessageTimelineFrame: "feature",
		MessageForwardPreview: "feature",
		MessageReplyPreview: "feature",
		SnapshotPreviewLayers: "feature",
		NodeGraph: "feature",
		NodeGraphSelectionArea: "feature",
		GraphPort: "feature",
		ScriptOutline: "feature",
		KnowledgeTableOfContents: "feature",
		TableTextEditor: "feature",
		ComponentShowcase: "feature",
		ComponentShowcaseView: "feature"
	},
	excludedVariants: [
		{
			name: "Standalone presence indicator",
			reason: "No completed standalone control in the original; avatar/status in domain cards stay domain-owned."
		},
		{
			name: "Skeleton loader",
			reason: "Original InitialBatchPresentation is delegate lifecycle infrastructure, not a finished skeleton control."
		},
		{
			name: "Emoji recents/favorites",
			reason: "Not implemented as a finished house control in the original."
		},
		{
			name: "Generic range date / multi combo / vertical slider",
			reason: "No completed corresponding original neutral variant; do not invent a port from wishlist names."
		}
	],
	categories: [
		{
			id: "foundations",
			title: {
				en: "Foundations",
				ru: "Основа"
			}
		},
		{
			id: "controls",
			title: {
				en: "Controls",
				ru: "Управление"
			}
		},
		{
			id: "display",
			title: {
				en: "Data display",
				ru: "Отображение данных"
			}
		},
		{
			id: "navigation",
			title: {
				en: "Navigation and layout",
				ru: "Навигация и компоновка"
			}
		},
		{
			id: "feedback",
			title: {
				en: "Feedback",
				ru: "Обратная связь"
			}
		},
		{
			id: "specialized",
			title: {
				en: "Specialized components",
				ru: "Специальные компоненты"
			}
		}
	]
};
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/showcase.ui.mjs
var live = [
	"typography",
	"headers",
	"colors",
	"icons",
	"buttons",
	"toggles",
	"text-fields",
	"choices",
	"numbers",
	"dates",
	"user-choice",
	"pickers",
	"tabs",
	"badges",
	"lists",
	"charts"
];
var states = [
	"default",
	"disabled",
	"readonly",
	"error",
	"long"
];
var stateLabels = [
	"Default",
	"Disabled",
	"Read only",
	"Error",
	"Long text"
];
function initial() {
	return {
		family: "typography",
		query: "",
		category: "",
		state: "default",
		code: false,
		text: "Robot Arm",
		area: "A local example",
		checked: true,
		choice: "model",
		user: "admin",
		date: "2026-11-02",
		color: "#78a6c4",
		icon: "save",
		number: "42",
		row: "assets",
		tab: "overview",
		last: ""
	};
}
function transition(model, event, catalog) {
	const next = Object.assign({}, model);
	if (event.type === "family" && catalog.families.some((f) => f.id === event.value)) next.family = event.value;
	else if (event.type === "category" && (event.value === "" || catalog.categories.some((c) => c.id === event.value))) next.category = event.value;
	else if (event.type === "state" && states.includes(event.value)) next.state = event.value;
	else if (event.type === "query") next.query = String(event.value || "").slice(0, 200);
	else if (event.type === "code") next.code = !model.code;
	else if (event.type === "reset") return Object.assign(initial(), {
		family: model.family,
		query: model.query,
		category: model.category
	});
	else if ([
		"text",
		"area",
		"checked",
		"choice",
		"user",
		"date",
		"color",
		"icon",
		"number",
		"row",
		"tab"
	].includes(event.type)) next[event.type] = event.value;
	else next.last = event.type;
	return next;
}
function families(catalog, model, language) {
	const query = model.query.trim().toLocaleLowerCase();
	const groups = catalog.categories.map((c) => c.id);
	const foundations = [
		"typography",
		"colors",
		"headers",
		"icons"
	];
	return catalog.families.filter((f) => (!model.category || f.category === model.category) && (!query || [
		f.id,
		f.title,
		f.label,
		...f.native,
		...f.vue,
		...f.tokens
	].join(" ").toLocaleLowerCase().includes(query))).sort((a, b) => groups.indexOf(a.category) - groups.indexOf(b.category) || (a.category === "foundations" ? foundations.indexOf(a.id) - foundations.indexOf(b.id) : catalog.families.indexOf(a) - catalog.families.indexOf(b))).map((f) => ({
		id: f.id,
		title: language === "ru" ? f.title : f.label,
		level: f.level,
		available: live.includes(f.id),
		count: f.native.length + f.vue.length
	}));
}
function row(list, record, model, language) {
	const tr = (text) => translate(text, language);
	const result = listAction("showcaseFamily_" + record.id, rect(0, 0, list.width, 48), record.title, "", {
		type: "family",
		value: record.id
	}, true, { selected: model.family === record.id });
	result.children[0].height = 27;
	result.children.push(label("showcaseFamilyState_" + record.id, rect(12, 27, list.width - 24, 16), tr(record.available ? "Live example" : "Catalogue entry"), {
		fontRole: "caption",
		color: "secondaryText"
	}));
	return {
		nodes: [result],
		width: list.width,
		height: 48
	};
}
function describe(model, catalog, width, height, language = "en") {
	const tr = (text) => translate(text, language), narrow = width < 740, nav = narrow ? 0 : 228;
	const x = nav + (narrow ? 0 : 20), w = Math.max(0, width - x), top = narrow ? 96 : 48;
	const visible = families(catalog, model, language), family = catalog.families.find((f) => f.id === model.family) || catalog.families[0];
	const nodes = [];
	nodes.push(node("Field", "showcaseSearch", rect(0, 0, narrow ? width : nav, 36), {
		text: model.query,
		label: tr("Search components"),
		placeholder: tr("Search components"),
		enabled: true,
		action: { type: "query" }
	}));
	const groupOptions = [{
		value: "",
		label: tr("All component groups")
	}, ...catalog.categories.map((c) => ({
		value: c.id,
		label: c.title[language === "ru" ? "ru" : "en"]
	}))];
	if (!narrow) {
		nodes.push(node("Choice", "showcaseCategory", rect(0, 44, nav, 36), {
			value: model.category,
			options: groupOptions,
			enabled: true,
			label: tr("Category"),
			action: { type: "category" }
		}));
		nodes.push(node("List", "showcaseFamilies", rect(0, 88, nav, Math.max(0, height - 88)), {
			source: "families",
			fields: [
				"id",
				"title",
				"available",
				"count",
				"level"
			],
			rowHeight: 52,
			selectedKey: model.family,
			keyField: "id",
			resetKey: model.query + "|" + model.category
		}));
	} else nodes.push(node("Choice", "showcaseFamilyChoice", rect(0, 44, Math.max(0, width - 168), 36), {
		value: model.family,
		options: visible.map((f) => ({
			value: f.id,
			label: f.title
		})),
		enabled: true,
		label: tr("Component showcase"),
		action: { type: "family" }
	}));
	const controlsX = narrow ? Math.max(0, width - 160) : x;
	nodes.push(node("Choice", "showcaseState", rect(controlsX, narrow ? 44 : 0, narrow ? 120 : 160, 36), {
		value: model.state,
		options: states.map((value, i) => ({
			value,
			label: tr(stateLabels[i])
		})),
		label: tr("Component state"),
		enabled: true,
		action: { type: "state" }
	}));
	nodes.push(button("showcaseReset", rect(narrow ? width - 36 : x + 168, narrow ? 44 : 0, 36, 36), tr("Reset"), "refresh", { type: "reset" }, true, { iconOnly: true }));
	if (!narrow) nodes.push(button("showcaseCode", rect(Math.max(x + 212, width - 136), 0, 136, 36), tr(model.code ? "Preview" : "Code example"), "code", { type: "code" }, true, {
		selected: model.code,
		radio: true
	}));
	const content = [], inner = Math.max(0, w - 32);
	content.push(label("showcaseTitle", rect(16, 12, inner, 46), language === "ru" ? family.title : family.label, {
		fontRole: "hero",
		weight: 600,
		wrap: true,
		role: "heading",
		level: 2
	}));
	content.push(label("showcaseScope", rect(16, 62, inner, 32), tr(live.includes(family.id) ? "Local demo; project data stays unchanged" : "Standalone example not added yet"), {
		fontRole: "secondary",
		color: "secondaryText",
		wrap: true
	}));
	let y = 110;
	if (!visible.length) {
		content.push(label("showcaseNoResults", rect(16, y, inner, 48), tr("No matching components"), { wrap: true }));
		y += 64;
	} else if (live.includes(family.id)) {
		const p = describe$1(model, family.id, inner, language);
		if (p.code) {
			if (narrow) content.push(button("showcaseCode", rect(16, y, Math.min(inner, 160), 36), tr(model.code ? "Preview" : "Code example"), "code", { type: "code" }, true, {
				selected: model.code,
				radio: true
			}));
			if (narrow) y += 48;
			if (model.code) {
				content.push(node("Code", "showcaseCodeSource", rect(16, y, inner, 260), {
					text: p.code,
					language: "javascript",
					readOnly: true,
					enabled: true
				}));
				y += 276;
			}
		}
		if (!model.code || !p.code) {
			content.push(node("Box", "showcasePreview", rect(16, y, inner, p.height), {
				background: "transparent",
				children: p.nodes,
				clip: false
			}));
			y += p.height + 12;
		}
	}
	for (const [title, values] of [["Native controls", family.native], ["Vue controls", family.vue]]) {
		content.push(label("showcaseOwner_" + title, rect(16, y, inner, 22), tr(title), {
			fontRole: "secondary",
			weight: 600
		}));
		y += 26;
		const text = values.join(" · ") || "—", h = Math.max(24, Math.ceil(text.length / Math.max(12, inner / 7)) * 18);
		content.push(label("showcaseNames_" + title, rect(16, y, inner, h), text, {
			wrap: true,
			fontRole: "secondary",
			color: "secondaryText"
		}));
		y += h + 20;
	}
	if (model.last) {
		content.push(label("showcaseEvent", rect(16, y, inner, 28), tr("Action") + ": " + model.last, {
			fontRole: "caption",
			color: "secondaryText"
		}));
		y += 40;
	}
	nodes.push(node("Box", "showcaseSurface", rect(x, top, w, Math.max(0, height - top)), {
		background: "surfaceContainerLowest",
		radius: 8
	}));
	nodes.push(node("Scroll", "showcaseContent", rect(x, top, Math.max(0, w - (y + 8 > height - top ? 12 : 0)), Math.max(0, height - top)), {
		contentHeight: y + 8,
		resetKey: model.family,
		children: content
	}));
	return { nodes };
}
var ComponentShowcase_default = /*#__PURE__*/ _plugin_vue_export_helper_default({
	__name: "ComponentShowcase",
	setup(__props, { expose: __expose }) {
		const host = ref(null), view = ref(null), size = ref({
			width: 1,
			height: 1
		}), model = ref(initial());
		const scene = computed(() => describe(model.value, catalogue, size.value.width, size.value.height, appearance.language));
		const models = computed(() => ({ families: families(catalogue, model.value, appearance.language) }));
		function dispatch(event) {
			model.value = transition(model.value, event, catalogue);
		}
		__expose({
			dispatch,
			model,
			scene
		});
		let observer;
		onMounted(() => {
			observer = observeFrameSizes(([entry]) => size.value = {
				width: Math.max(1, entry.contentRect.width),
				height: Math.max(1, entry.contentRect.height)
			});
			observer.observe(host.value);
		});
		onBeforeUnmount(() => observer?.disconnect());
		return (_ctx, _cache) => {
			return openBlock(), createElementBlock("section", {
				ref_key: "host",
				ref: host,
				class: "component-showcase"
			}, [createVNode(_sfc_main$1, {
				ref_key: "view",
				ref: view,
				scene: scene.value,
				models: models.value,
				"describe-row": (list, record) => row(list, record, model.value, unref(appearance).language),
				onEvent: dispatch
			}, null, 8, [
				"scene",
				"models",
				"describe-row"
			])], 512);
		};
	}
}, [["__scopeId", "data-v-c64e6f20"]]);
//#endregion
export { ComponentShowcase_default as default };

//# sourceMappingURL=ComponentShowcase.js.map