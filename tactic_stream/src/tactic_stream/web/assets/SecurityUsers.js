import { I as resolveComponent, K as withDirectives, N as openBlock, c as vShow, g as createBlock, h as createBaseVNode, nt as normalizeStyle, p as Teleport, v as createElementBlock, x as createVNode } from "./vue.js";
import { D as t, O as appearance, Y as _plugin_vue_export_helper_default } from "./index.js";
import { d as node, n as _sfc_main$1, t as observeFrameSizes } from "./resize.js";
import { z as securityUsers } from "./clipboard.js";
import { a as translate$1, n as metrics } from "./groups.ui.js";
//#region ../src/tactic_stream/shared_ui/features/administration/users/users.state.mjs
function initial() {
	return {
		page: "profile",
		query: "",
		showRetired: false,
		confirmation: ""
	};
}
function permissions(model) {
	const editable = !!model.ready && !!model.canWrite && !model.busy && !model.uncertain;
	return {
		editable,
		create: editable && !model.dirty,
		select: !!model.ready && !model.busy && !model.dirty && !model.uncertain,
		save: editable && !!model.draft && !!model.dirty,
		discard: !model.busy && !!(model.dirty || model.uncertain),
		reload: !model.busy && !!model.canLoad,
		search: !!model.ready && !model.busy
	};
}
function transition(ui, model, event) {
	const next = Object.assign({}, ui), commands = [], allow = permissions(model);
	switch (event.type) {
		case "page":
			if (!model.busy && [
				"profile",
				"account",
				"groups"
			].indexOf(event.value) >= 0) {
				next.page = event.value;
				commands.push({
					type: "focus",
					id: "segmentedButtonSegment_" + next.page
				});
			}
			break;
		case "query":
			if (allow.search) {
				next.query = String(event.value);
				commands.push({
					type: "query",
					value: next.query
				});
			}
			break;
		case "showRetired":
			if (allow.search) {
				next.showRetired = !!event.value;
				commands.push({
					type: "showRetired",
					value: next.showRetired
				});
			}
			break;
		case "select":
			if (allow.select) {
				next.page = "profile";
				next.confirmation = "";
				commands.push({
					type: "select",
					login: event.login
				});
			}
			break;
		case "create":
			if (allow.create) {
				next.page = "profile";
				next.confirmation = "";
				commands.push({ type: "create" }, {
					type: "focus",
					id: "adminUserLogin"
				});
			}
			break;
		case "field":
			if (allow.editable && model.draft && Object.prototype.hasOwnProperty.call(model.draft, event.field) && event.field !== "groups" && event.field !== "code" && !(event.field === "login" && model.identity)) commands.push({
				type: "field",
				field: event.field,
				value: String(event.value)
			});
			break;
		case "retired":
			if (allow.editable && model.draft) commands.push({
				type: "field",
				field: "s_status",
				value: event.value ? "retired" : ""
			});
			break;
		case "member":
			if (allow.editable && model.draft) commands.push({
				type: "member",
				name: event.name,
				value: !!event.value
			});
			break;
		case "save":
			if (allow.save) {
				if (!String(model.draft.login || "").trim()) commands.push({
					type: "error",
					text: "A login is required"
				});
				else next.confirmation = "save";
			}
			break;
		case "reload":
			if (allow.reload) {
				if (model.dirty || model.uncertain) next.confirmation = "reload";
				else commands.push({
					type: "reload",
					force: false
				});
			}
			break;
		case "discard":
			if (allow.discard) next.confirmation = "discard";
			break;
		case "keep":
			next.confirmation = "";
			break;
		case "confirm":
			if (!model.busy && next.confirmation) {
				const action = next.confirmation;
				next.confirmation = "";
				if (action === "save") {
					if (allow.save) commands.push({ type: "save" });
				} else if (action === "reload" || model.uncertain) commands.push({
					type: "reload",
					force: true
				});
				else commands.push({ type: "discard" });
			}
			break;
		default: throw Error("Unknown Users action: " + event.type);
	}
	return {
		ui: next,
		commands
	};
}
//#endregion
//#region ../src/tactic_stream/shared_ui/features/administration/users/users.ui.mjs
var russian = {
	"User directory": "Каталог пользователей",
	"Create user": "Создать пользователя",
	"New user": "Новый пользователь",
	"Name, login or email": "Имя, логин или почта",
	"Show retired users": "Показать архивных пользователей",
	Profile: "Профиль",
	Account: "Аккаунт",
	Groups: "Группы",
	Login: "Логин",
	"First name": "Имя",
	"Last name": "Фамилия",
	"Display name": "Отображаемое имя",
	Department: "Отдел",
	Email: "Почта",
	"Phone number": "Телефон",
	Address: "Адрес",
	UPN: "UPN",
	Namespace: "Пространство имён",
	"Project code": "Код проекта",
	"License type": "Тип лицензии",
	"Hourly wage": "Почасовая ставка",
	Password: "Пароль",
	"Unique login, without spaces": "Уникальный логин без пробелов",
	"Leave empty to keep the current password": "Оставьте пустым, чтобы сохранить текущий пароль",
	"These details are shown in profiles, messages and user pickers.": "Эти сведения отображаются в профилях, сообщениях и выборе пользователей.",
	"Retiring keeps this user's history. Clear this option to reactivate the account, then save.": "Архивация сохраняет историю пользователя. Снимите отметку и сохраните, чтобы восстановить аккаунт.",
	"Group membership changes affect this user's permissions.": "Состав групп влияет на права этого пользователя.",
	"Select a user or create a new account": "Выберите пользователя или создайте новый аккаунт",
	"Edit group membership": "Изменить состав групп",
	"Retired user": "Архивный пользователь",
	"Default group": "Группа по умолчанию",
	"Project: {project}": "Проект: {project}",
	"These account changes will be saved on the server and affect this user's permissions.": "Изменения аккаунта будут сохранены на сервере и повлияют на права пользователя.",
	"Discard unsaved user changes?": "Сбросить несохранённые изменения пользователя?",
	"Confirm save": "Подтвердить сохранение",
	Save: "Сохранить",
	Cancel: "Отмена",
	"A login is required": "Введите логин",
	"User saved on server": "Пользователь сохранён на сервере",
	"Invalid user document": "Некорректные данные пользователя",
	"Enter a login without spaces or slashes": "Введите логин без пробелов и слешей",
	"An existing login cannot be changed": "Логин существующего аккаунта нельзя изменить",
	"Invalid password or user groups": "Некорректный пароль или список групп",
	"Invalid user profile field": "Некорректное поле профиля пользователя",
	"Hourly wage must be a non-negative number": "Почасовая ставка должна быть неотрицательным числом",
	"Invalid account status": "Некорректный статус учётной записи",
	"You cannot retire the account you are signed in with": "Нельзя отключить учётную запись, под которой вы вошли",
	"The selected user no longer exists. Refresh the list.": "Выбранный пользователь больше не существует. Обновите список.",
	"User details or memberships changed. Reload before saving.": "Данные пользователя или членство в группах изменились. Перезагрузите их перед сохранением.",
	"A user with this login already exists": "Пользователь с таким логином уже существует",
	"The selected user group no longer exists. Refresh the list.": "Выбранная группа больше не существует. Обновите список.",
	"You cannot remove your own administrator membership": "Нельзя удалить собственное членство в группе администраторов",
	"Save or discard user changes before leaving.": "Сохраните или сбросьте изменения пользователя перед выходом.",
	"The save result is unknown. Reload users before trying again.": "Результат сохранения неизвестен. Обновите пользователей перед повторной попыткой."
};
function translate(text, language, values) {
	let result = language === "ru" && russian[text] ? russian[text] : translate$1(text, language);
	for (const key of Object.keys(values || {})) result = result.split("{" + key + "}").join(values[key]);
	return result;
}
var box = (x, y, width, height) => ({
	x,
	y,
	width: Math.max(0, width),
	height: Math.max(0, height)
});
var label = (id, rect, text, extra) => node("Label", id, rect, Object.assign({ text }, extra || {}));
var muted = {
	fontRole: "secondary",
	color: "secondaryText"
};
var profileFields = [
	["first_name", "First name"],
	["last_name", "Last name"],
	["display_name", "Display name"],
	["department", "Department"],
	["email", "Email"],
	["phone_number", "Phone number"],
	["address", "Address"]
];
var accountFields = [
	["upn", "UPN"],
	["namespace", "Namespace"],
	["project_code", "Project code"],
	["license_type", "License type"],
	["hourly_wage", "Hourly wage"]
];
function profile(draft, record) {
	const data = draft || {}, name = String(data.display_name || "").trim() || [data.first_name, data.last_name].filter(Boolean).join(" ").trim() || data.login || "";
	return Object.assign({}, record || {}, {
		login: data.login || "",
		displayName: name,
		initials: name.split(/\s+/).filter(Boolean).slice(0, 2).map((word) => word[0]).join("").toUpperCase() || "?",
		retired: data.s_status === "retired",
		avatarColor: record && record.avatarColor || ""
	});
}
function toolbar(model, ui, width, language) {
	const tr = (text) => translate(text, language), allow = permissions(model), compact = width < (language === "ru" ? 620 : 550);
	const createWidth = compact ? 38 : language === "ru" ? 220 : 156, saveWidth = compact ? 38 : language === "ru" ? 200 : 166, discardWidth = compact ? 38 : 118;
	const saveX = width - saveWidth, discardX = saveX - discardWidth - 8;
	const button = (id, text, icon, x, size, action, enabled, highlighted) => node("Button", id, box(x, 0, size, 38), {
		text: tr(text),
		icon,
		iconOnly: compact,
		enabled,
		highlighted: !!highlighted,
		action: { type: action }
	});
	const nodes = [
		button("adminCreateDocument", "Create user", "person-add", 0, createWidth, "create", allow.create),
		node("Button", "adminReloadDocument", box(createWidth + 6, 0, 38, 38), {
			text: tr("Reload from server"),
			icon: "refresh",
			iconOnly: true,
			enabled: allow.reload,
			action: { type: "reload" }
		}),
		button("adminDiscardDocument", "Discard", "undo", discardX, discardWidth, "discard", allow.discard),
		button("adminSaveDocument", "Save to server", "save", saveX, saveWidth, "save", allow.save, true)
	];
	if (!compact && discardX > createWidth + 62) nodes.push(label("adminUserStatus", box(createWidth + 58, 0, discardX - createWidth - 66, 38), tr(model.busy ? "Working on the server…" : model.dirty ? "Unsaved changes" : !model.canWrite ? "Read-only" : ""), muted));
	return { nodes };
}
function identity(record, x, y, width, size, prefix) {
	const title = record.displayName || record.login || "", secondary = record.login && record.login !== title;
	return [
		node("Preview", prefix + "Avatar_" + record.login, box(x, y, size, size), {
			source: record.avatarUrl || "",
			initials: record.initials || "?",
			accent: record.avatarColor || "",
			opacity: record.retired ? .5 : 1
		}),
		label(prefix + "Title_" + record.login, box(x + size + 12, y + (secondary ? size / 2 - 21 : (size - 22) / 2), width - size - 12, 22), title, {
			weight: 600,
			fontRole: size > 40 ? "section" : "body",
			opacity: record.retired ? .5 : 1
		}),
		label(prefix + "Login_" + record.login, box(x + size + 12, y + size / 2 + 2, width - size - 12, 18), secondary ? record.login : "", Object.assign({ opacity: record.retired ? .5 : 1 }, muted))
	];
}
function describe(model, ui, width, height, language) {
	const tr = (text, values) => translate(text, language, values), allow = permissions(model), pad = metrics.padding, nodes = [];
	let top = 0;
	if (model.error || model.message) {
		const unknown = "The save result is unknown. Reload users before trying again.";
		const notice = model.uncertain ? tr(unknown) + (model.error && model.error !== unknown ? "\n" + tr(model.error) : "") : tr(model.error || model.message);
		nodes.push(node("Area", "adminDocumentError", box(0, top, width, 58), {
			text: notice,
			role: model.error ? "alert" : "status",
			label: tr(model.error ? "Server error" : "Status"),
			color: model.error ? "error" : "secondaryText",
			readOnly: true,
			notice: true
		}));
		top += 66;
	}
	if (ui.confirmation) {
		const saving = ui.confirmation === "save", narrow = width < 520, h = narrow ? 136 : 90;
		nodes.push(node("Box", "adminUserConfirmation", box(0, top, width, h), {
			background: "surfaceContainerHigh",
			children: [
				label("adminUserConfirmationText", box(12, 6, width - 24, narrow ? 72 : 42), tr(saving ? "These account changes will be saved on the server and affect this user's permissions." : "Discard unsaved user changes?"), { wrap: true }),
				node("Button", "adminCancelSave", box(12, h - 44, narrow ? 128 : 164, 36), {
					text: tr(saving ? "Cancel" : "Keep editing"),
					enabled: !model.busy,
					action: { type: "keep" }
				}),
				node("Button", "adminConfirmSave", box(narrow ? 150 : 188, h - 44, narrow ? width - 162 : 220, 36), {
					text: tr(saving ? narrow ? "Save" : "Confirm save" : "Discard changes"),
					highlighted: saving,
					destructive: !saving,
					enabled: !model.busy,
					action: { type: "confirm" }
				})
			]
		}));
		top += h + 8;
	}
	const stacked = width < 600, remaining = Math.max(1, height - top), catalogWidth = stacked ? width : width < 780 ? 220 : 290;
	const catalogHeight = stacked ? Math.min(240, remaining * .37) : remaining;
	const docX = stacked ? 0 : catalogWidth + 12, docY = stacked ? top + catalogHeight + 12 : top;
	const docWidth = stacked ? width : width - docX, docHeight = Math.max(1, height - docY), inner = Math.max(1, docWidth - pad * 2);
	const catalog = [
		node("Icon", "adminUsersIcon", box(pad, 14, 20, 20), {
			icon: "groups",
			color: "action"
		}),
		label("adminUsersTitle", box(44, 12, catalogWidth - 58, 24), tr("User directory"), {
			fontRole: "section",
			weight: 600
		}),
		node("Field", "adminUserSearch", box(pad, 48, catalogWidth - pad * 2, 38), {
			text: ui.query,
			label: tr("Name, login or email"),
			placeholder: tr("Name, login or email"),
			enabled: allow.search,
			action: { type: "query" }
		}),
		node("CheckBox", "adminShowRetiredUsers", box(pad, 92, catalogWidth - pad * 2, 30), {
			text: tr("Show retired users"),
			checked: ui.showRetired,
			enabled: allow.search,
			indicatorX: 0,
			children: [label("adminShowRetiredLabel", box(27, 0, catalogWidth - pad * 2 - 27, 30), tr("Show retired users"))],
			action: { type: "showRetired" }
		}),
		node("List", "adminUsersList", box(pad, 130, catalogWidth - pad * 2, catalogHeight - 130 - pad), {
			source: "users",
			keyField: "login",
			fields: [
				"login",
				"displayName",
				"initials",
				"avatarUrl",
				"avatarColor",
				"retired"
			],
			rowHeight: 68,
			scrollbarId: "adminUsersScrollBar",
			label: tr("User directory")
		})
	];
	if (!model.userCount && !model.busy) catalog.push(label("adminUsersEmpty", box(pad, 130, catalogWidth - pad * 2 - 16, 50), tr("No users match the search"), {
		wrap: true,
		color: "secondaryText"
	}));
	nodes.push(node("Box", "adminUsersPanel", box(0, top, catalogWidth, catalogHeight), {
		background: "surfaceContainerLow",
		border: "outlineVariant",
		children: catalog
	}));
	const content = [];
	if (!model.draft) content.push(label("adminUserEmpty", box(pad, 20, inner, 70), tr("Select a user or create a new account"), {
		wrap: true,
		color: "secondaryText"
	}));
	else {
		const profile = Object.assign({}, model.profile);
		if (!profile.displayName) profile.displayName = tr("New user");
		content.push(...identity(profile, pad, pad, inner - 44, 60, "userIdentity"));
		content.push(node("Button", "adminUserManageGroups", box(docWidth - pad - 38, pad + 11, 38, 38), {
			text: tr("Edit group membership"),
			icon: "groups",
			iconOnly: true,
			enabled: allow.editable,
			action: {
				type: "page",
				value: "groups"
			}
		}));
		const tabs = [
			[
				"profile",
				"Profile",
				"person"
			],
			[
				"account",
				"Account",
				"security"
			],
			[
				"groups",
				"Groups",
				"groups"
			]
		], active = tabs.findIndex((tab) => tab[0] === ui.page);
		const keys = {
			ArrowLeft: {
				type: "page",
				value: tabs[(active + 2) % 3][0]
			},
			ArrowRight: {
				type: "page",
				value: tabs[(active + 1) % 3][0]
			},
			Home: {
				type: "page",
				value: "profile"
			},
			End: {
				type: "page",
				value: "groups"
			}
		};
		content.push(node("Box", "adminUserEditorTabs", box(pad, 86, inner, 38), {
			role: "radiogroup",
			background: "surfaceContainerHigh",
			border: "outlineVariant",
			radius: 9,
			children: tabs.map(([value, text, icon], index) => node("Button", "segmentedButtonSegment_" + value, box(3 + index * (inner - 6) / 3, 3, (inner - 6) / 3, 32), {
				text: tr(text),
				icon,
				radio: true,
				selected: ui.page === value,
				keys,
				enabled: !model.busy,
				action: {
					type: "page",
					value
				}
			}))
		}));
		const formWidth = Math.max(1, inner - 16), fields = [];
		let y = 0;
		const help = (text) => {
			const h = formWidth < 320 ? 56 : 36;
			fields.push(label("adminUserHelp_" + ui.page, box(0, y, formWidth, h), tr(text), Object.assign({ wrap: true }, muted)));
			y += h + 8;
		};
		const field = (key, text, x, top, w, extra) => {
			fields.push(label("adminUserLabel_" + key, box(x, top, w, 22), tr(text), { weight: 600 }));
			fields.push(node("Field", key === "login" ? "adminUserLogin" : key === "password" ? "adminUserPassword" : "adminUserField_" + key, box(x, top + 27, w, 38), Object.assign({
				text: String(model.draft[key] || ""),
				label: tr(text),
				enabled: allow.editable,
				maxLength: key === "login" ? 256 : key === "password" ? 4096 : 65536,
				action: {
					type: "field",
					field: key
				}
			}, extra || {})));
		};
		if (ui.page === "profile") {
			help("These details are shown in profiles, messages and user pickers.");
			field("login", "Login", 0, y, formWidth, {
				readOnly: !!model.identity,
				placeholder: tr("Unique login, without spaces")
			});
			y += 77;
		}
		if (ui.page !== "groups") {
			const availableFields = (ui.page === "profile" ? profileFields : accountFields).filter(([key]) => Object.prototype.hasOwnProperty.call(model.draft, key)), columns = formWidth > 620 ? 2 : 1, cell = (formWidth - (columns - 1) * 12) / columns;
			availableFields.forEach(([key, text], index) => field(key, text, index % columns * (cell + 12), y + Math.floor(index / columns) * 77, cell, { inputMode: key === "hourly_wage" ? "decimal" : "text" }));
			y += Math.ceil(availableFields.length / columns) * 77;
		}
		if (ui.page === "account") {
			field("password", "Password", 0, y, formWidth, {
				password: true,
				placeholder: tr("Leave empty to keep the current password")
			});
			y += 77;
			fields.push(node("CheckBox", "adminUserRetired", box(0, y, formWidth, 32), {
				text: tr("Retired"),
				checked: model.draft.s_status === "retired",
				enabled: allow.editable,
				children: [label("adminUserRetiredLabel", box(27, 0, formWidth - 27, 32), tr("Retired"))],
				action: { type: "retired" }
			}));
			y += 40;
			help("Retiring keeps this user's history. Clear this option to reactivate the account, then save.");
		}
		if (ui.page === "groups") {
			help("Group membership changes affect this user's permissions.");
			fields.push(node("List", "adminUserGroupsList", box(0, y, inner, Math.max(1, docHeight - 136 - pad - y)), {
				source: "groups",
				keyField: "name",
				fields: [
					"name",
					"description",
					"projectCode",
					"isDefault"
				],
				rowHeight: 64,
				scrollbarId: "adminUserGroupsScrollBar",
				label: tr("Groups")
			}));
			if (!model.groupCount) fields.push(label("adminUserGroupsEmpty", box(0, y, formWidth, 50), tr("No user groups yet"), {
				wrap: true,
				color: "secondaryText"
			}));
			y = Math.max(1, docHeight - 136 - pad);
		}
		content.push(node("Scroll", "adminUserForm", box(pad, 136, inner, docHeight - 136 - pad), {
			contentHeight: y,
			scrollbarId: "adminUserFormScrollBar",
			children: fields,
			resetKey: ui.page
		}));
	}
	nodes.push(node("Box", "adminUserDetails", box(docX, docY, docWidth, docHeight), {
		background: "surfaceContainerLow",
		border: "outlineVariant",
		children: content
	}));
	return { nodes };
}
function row(list, record, model, ui, language) {
	const tr = (text, values) => translate(text, language, values), width = list.width - 16, height = list.rowHeight - 4, allow = permissions(model);
	if (list.source === "users") {
		const selected = model.identity === record.login, children = identity(record, 10, (height - 40) / 2, width - 20, 40, "directoryIdentity");
		if (record.retired) children.push(node("Icon", "adminUserRetiredIcon_" + record.login, box(width - 24, height - 20, 16, 16), {
			icon: "archive",
			text: tr("Retired user"),
			color: "secondaryText"
		}));
		return { nodes: [node("Action", "adminUser_" + record.login, box(0, 0, width, height), {
			text: (record.displayName || record.login) + " " + record.login,
			description: record.retired ? tr("Retired user") : "",
			enabled: allow.select,
			selected,
			rail: selected,
			normalColor: "transparent",
			selectedColor: "selected",
			children,
			action: {
				type: "select",
				login: record.login
			}
		})] };
	}
	const info = record.projectCode ? tr("Project: {project}", { project: record.projectCode }) : record.isDefault ? tr("Default group") : "";
	const checked = (model.draft.groups || []).indexOf(record.name) >= 0;
	return { nodes: [node("CheckBox", "userGroupMembership_" + record.name, box(0, 0, width, height), {
		text: record.name,
		checked,
		enabled: allow.editable,
		indicatorX: 10,
		normalColor: "surfaceContainerHigh",
		selectedColor: "surfaceContainerHigh",
		children: [
			label("userGroupTitle_" + record.name, box(39, info ? 3 : 9, width - 49, 22), record.name, { weight: 600 }),
			label("userGroupDescription_" + record.name, box(39, info ? 24 : 31, width - 49, 18), record.description || "", muted),
			label("userGroupScope_" + record.name, box(39, 41, width - 49, 16), info, muted)
		],
		action: {
			type: "member",
			name: record.name
		}
	})] };
}
//#endregion
//#region src/features/administration/SecurityUsers.vue
var _sfc_main = {
	components: { FrameView: _sfc_main$1 },
	props: {
		ticket: String,
		project: String,
		toolbarTarget: String,
		presentationVisible: {
			type: Boolean,
			default: true
		}
	},
	emits: ["saved"],
	data() {
		return {
			catalog: null,
			context: null,
			identity: "",
			revision: "",
			draft: null,
			original: null,
			busy: false,
			uncertain: false,
			error: "",
			message: "",
			ui: initial(),
			request: 0,
			viewport: {
				width: 1,
				height: 1
			},
			toolbarSize: 620,
			observer: null
		};
	},
	computed: {
		dirty() {
			return JSON.stringify(this.draft) !== JSON.stringify(this.original);
		},
		editable() {
			return !!this.catalog && this.catalog.canWrite !== false && this.context?.ticket === this.ticket && !this.busy && !this.uncertain;
		},
		users() {
			const query = this.ui.query.trim().toLowerCase();
			return (this.catalog?.users || []).filter((user) => (this.ui.showRetired || !user.retired) && (!query || [
				user.login,
				user.displayName,
				user.document.email
			].join(" ").toLowerCase().includes(query)));
		},
		models() {
			return {
				users: this.users,
				groups: this.catalog?.groups || []
			};
		},
		frameModel() {
			return {
				draft: this.draft,
				identity: this.identity,
				profile: this.profile,
				ready: !!this.catalog && this.context?.ticket === this.ticket,
				canWrite: !!this.catalog && this.catalog.canWrite !== false,
				canLoad: !!this.ticket,
				busy: this.busy,
				dirty: this.dirty,
				uncertain: this.uncertain,
				error: this.error,
				message: this.message,
				userCount: this.users.length,
				groupCount: this.catalog?.groups.length || 0
			};
		},
		frameScene() {
			return describe(this.frameModel, this.ui, this.viewport.width, this.viewport.height, appearance.language);
		},
		toolbarScene() {
			return toolbar(this.frameModel, this.ui, this.toolbarSize, appearance.language);
		},
		hostStyle() {
			return { gap: metrics.toolbarGap + "px" };
		},
		profile() {
			const row = this.catalog?.users.find((user) => user.login === this.identity) || {};
			return profile(this.draft, row);
		}
	},
	watch: {
		project() {
			if (this.context) this.context.project = this.project;
		},
		ticket() {
			this.request++;
			this.busy = false;
			this.catalog = this.draft = this.original = null;
			this.reload(true);
		}
	},
	mounted() {
		this.reload();
		window.addEventListener("beforeunload", this.beforeUnload);
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
		this.request++;
		this.observer?.disconnect();
		if (this.draft) this.draft.password = "";
		window.removeEventListener("beforeunload", this.beforeUnload);
	},
	methods: {
		t,
		rowScene(node, record) {
			return row(node, record, this.frameModel, this.ui, appearance.language);
		},
		async dispatch(event) {
			const result = transition(this.ui, this.frameModel, event);
			this.ui = result.ui;
			for (const command of result.commands) switch (command.type) {
				case "create":
					this.create();
					break;
				case "select":
					this.select(command.login);
					break;
				case "query":
				case "showRetired": break;
				case "field":
					this.draft[command.field] = command.value;
					this.message = "";
					break;
				case "member":
					this.member(command.name, command.value);
					break;
				case "save":
					await this.save();
					break;
				case "reload":
					await this.reload(command.force);
					break;
				case "discard":
					this.select(this.identity || this.catalog?.users[0]?.login || "", true);
					break;
				case "error":
					this.error = command.text;
					break;
				case "focus":
					await this.$nextTick();
					this.$el.querySelector("[data-frame=\"" + command.id + "\"]")?.focus();
					break;
				default: throw Error("Unsupported Users command: " + command.type);
			}
		},
		beforeUnload(event) {
			if (this.dirty || this.busy || this.uncertain) {
				event.preventDefault();
				event.returnValue = "";
			}
		},
		canLeave() {
			if (this.dirty || this.busy || this.uncertain) {
				this.error = "Save or discard user changes before leaving.";
				return false;
			}
			return true;
		},
		accept(catalog, selected) {
			this.catalog = catalog;
			this.select(selected || catalog.users[0]?.login || "", true);
		},
		select(login, loaded = false) {
			if (!loaded && (!this.editable || this.dirty)) return;
			const row = this.catalog?.users.find((user) => user.login === login);
			const previous = this.identity;
			this.identity = row?.login || "";
			this.revision = row?.revision || "";
			this.draft = row ? {
				...row.document,
				groups: [...row.document.groups]
			} : null;
			this.original = this.draft ? {
				...this.draft,
				groups: [...this.draft.groups]
			} : null;
			this.error = "";
			this.ui.confirmation = "";
			if (previous !== this.identity) this.ui.page = "profile";
		},
		create() {
			if (!this.editable || this.dirty) return;
			this.select("", true);
			this.draft = Object.fromEntries(this.catalog.fields.map((field) => [field, ""]));
			Object.assign(this.draft, {
				login: "",
				password: "",
				groups: []
			});
			this.message = "";
		},
		async reload(force = false) {
			if (this.busy || !this.ticket) return;
			if (!force && (this.dirty || this.uncertain)) {
				this.dispatch({ type: "reload" });
				return;
			}
			const request = ++this.request, selected = this.identity;
			this.context = {
				ticket: this.ticket,
				project: this.project
			};
			this.busy = true;
			this.error = "";
			this.message = "";
			try {
				const result = await securityUsers("read", this.context.ticket);
				if (request === this.request) {
					this.uncertain = false;
					this.accept(result, selected);
				}
			} catch (error) {
				if (request === this.request) this.error = error.message;
			} finally {
				if (request === this.request) this.busy = false;
			}
		},
		member(name, checked) {
			if (this.editable && this.draft) this.draft.groups = checked ? [.../* @__PURE__ */ new Set([...this.draft.groups, name])].sort() : this.draft.groups.filter((group) => group !== name);
		},
		async save() {
			if (!this.editable || !this.dirty || !this.draft) return;
			if (!this.draft.login.trim()) {
				this.error = "A login is required";
				return;
			}
			const request = this.request;
			this.busy = true;
			this.error = "";
			this.message = "";
			try {
				const result = await securityUsers("save", this.context.ticket, {
					identity: this.identity,
					document: this.draft,
					expected_revision: this.revision
				});
				if (request !== this.request) return;
				this.accept(result, result.selected);
				this.message = "User saved on server";
				this.$emit("saved", result);
			} catch (error) {
				if (request !== this.request) return;
				this.uncertain = !error.status || error.status >= 500;
				this.error = this.uncertain ? "The save result is unknown. Reload users before trying again." : error.message;
			} finally {
				if (request === this.request) this.busy = false;
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
		class: "security-users security-groups frame-host",
		style: normalizeStyle($options.hostStyle),
		"aria-label": $options.t("User directory"),
		"aria-busy": $data.busy
	}, [(openBlock(), createBlock(Teleport, {
		defer: "",
		to: $props.toolbarTarget || "body",
		disabled: !$props.toolbarTarget
	}, [withDirectives(createBaseVNode("div", {
		class: "frame-toolbar-host",
		style: normalizeStyle({ width: $data.toolbarSize + "px" })
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
	])], 512)], 12, _hoisted_1);
}
var SecurityUsers_default = /*#__PURE__*/ _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
//#endregion
export { SecurityUsers_default as default };

//# sourceMappingURL=SecurityUsers.js.map