"""Sidebar draft algorithms from Handler sidebar_editor.py, without Qt/runtime imports.

Native TACTIC owns persistence, permissions and revisions. Vue owns the draft.
"""
from copy import deepcopy
import re
from xml.etree import ElementTree

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.search import Search, SearchType
from pyasm.security.security import _require_admin
from tactic_stream.server.widget_configuration import WidgetConfigConflict

_LINK_CLASS = "LinkWdg"
_SECTION_CLASS = "SideBarSectionLinkWdg"
_SEPARATOR_CLASS = "SeparatorWdg"
_WIDGET_TYPE_VALUES = {"view_panel", "custom_layout", "edit_layout", "tile_layout", "fast_layout", "__class__"}
_RESULT_VIEW_VALUES = {"continious", "tiles", "compact", "splitted_vertical", "splitted_horizontal", "table"}

_TACTIC_ICON_PREFIXES = {"FA", "FAR", "FAS", "FAB", "MDI"}

def icon_name_from_tactic(value: object) -> str:
    """Return the glyph name expected by ``MaterialIcon``.

    TACTIC sidebar XML stores values such as ``FAS_FOLDER_OPEN``. Handler
    ``get_icon(tactic_icon=...)`` which removed the family prefix and changed
    removes the family prefix and changes remaining underscores to hyphens at
    the server-data boundary while still accepting unprefixed project icons.
    """
    raw = str(value or "").strip()
    prefix, separator, name = raw.partition("_")
    if separator and prefix.upper() in _TACTIC_ICON_PREFIXES and name:
        return name.replace("_", "-").lower()
    return raw

def icon_name_for_tactic(value: object) -> str:
    """Encode an Icon Manager glyph for TACTIC sidebar XML."""
    clean = icon_name_from_tactic(value).strip()
    if not clean:
        return ""
    return "FAS_" + clean.replace("-", "_").upper()

def _slug(value: object, fallback: str = "sidebar_item") -> str:
    value = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower())
    return value.strip("_") or fallback

def _children(root: ElementTree.Element) -> list[ElementTree.Element]:
    if root.tag == "element":
        return [root]
    return [child for child in list(root) if child.tag == "element"]

def _all_elements(root: ElementTree.Element) -> list[ElementTree.Element]:
    """Match ``ViewsConfig.get_view``: every element belongs to the view."""
    if root.tag == "element":
        return [root]
    return list(root.iter("element"))

def _view_elements(root: ElementTree.Element) -> list[ElementTree.Element]:
    """Return only the ordered elements owned by one SideBarWdg view.

    TACTIC stores a folder's children in another named SideBarWdg view.  Using
    ``iter('element')`` here destroys that boundary and turns the native tree
    into a flat catalog.  Configs may have a ``config/view`` wrapper, so locate
    the first container which directly owns elements and keep only its direct
    children.
    """
    if root.tag == "element":
        return [root]
    direct = [child for child in list(root) if child.tag == "element"]
    if direct:
        return direct
    for container in root.iter():
        direct = [child for child in list(container) if child.tag == "element"]
        if direct:
            return direct
    return []

def _nested_elements(element: ElementTree.Element) -> list[ElementTree.Element]:
    """Return inline children when a definition uses nested element nodes."""
    return [child for child in list(element) if child.tag == "element"]

def _element_parent(
        root: ElementTree.Element,
        element: ElementTree.Element) -> ElementTree.Element | None:
    for parent in root.iter():
        if element in list(parent):
            return parent
    return None

def _element_container(root: ElementTree.Element) -> ElementTree.Element:
    """Append beside existing view references, preserving wrapper elements."""
    elements = _view_elements(root)
    if elements:
        parent = _element_parent(root, elements[0])
        return parent if parent is not None else root
    if root.tag == 'config' and len(root) == 1 and root[0].tag != 'element':
        return root[0]
    return root

def _parse_document(value: object) -> ElementTree.Element:
    text = str(value or "").strip()
    if re.search(r'<!DOCTYPE|<!ENTITY', text, re.I):
        raise ValueError('Document types and XML entities are not supported')
    if not text:
        return ElementTree.Element("config")
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        root = ElementTree.fromstring(f"<config>{text}</config>")
    if root.tag == "element":
        wrapper = ElementTree.Element("config")
        wrapper.append(root)
        return wrapper
    return root

def _serialize(root: ElementTree.Element) -> str:
    try:
        ElementTree.indent(root, space="  ")
    except AttributeError:
        pass
    return ElementTree.tostring(root, encoding="unicode")

def _serialize_element(element: ElementTree.Element) -> str:
    """Serialize one effective sidebar definition without mutating it."""
    return _serialize(deepcopy(element))

def _parse_element(value: object) -> ElementTree.Element:
    if re.search(r'<!DOCTYPE|<!ENTITY', str(value), re.I):
        raise ValueError('Document types and XML entities are not supported')
    element = ElementTree.fromstring(str(value or "").strip())
    if element.tag != "element":
        raise ElementTree.ParseError("The root node must be <element>")
    return element

def _security_document(value: object) -> ElementTree.Element:
    """Parse a complete TACTIC access_rules value or one rule fragment."""
    text = str(value or "").strip()
    if re.search(r'<!DOCTYPE|<!ENTITY', text, re.I):
        raise ValueError('Document types and XML entities are not supported')
    if not text:
        return ElementTree.Element("rules")
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        root = ElementTree.fromstring(f"<rules>{text}</rules>")
    if root.tag == "rule":
        wrapper = ElementTree.Element("rules")
        wrapper.append(root)
        return wrapper
    return root

def _sidebar_rule_allowed(
        access_rules: object, element_name: str, project_code: str) -> bool:
    """Return the explicit project link permission used by check_security."""
    try:
        root = _security_document(access_rules)
    except ElementTree.ParseError:
        return False
    for rule in root.iter("rule"):
        if (
            str(rule.get("group") or "") == "link"
            and str(rule.get("element") or "") == str(element_name or "")
            and str(rule.get("project") or "") == str(project_code or "")
        ):
            return str(rule.get("access") or "").lower() == "allow"
    return False

def _direct_text(element: ElementTree.Element, name: str) -> str:
    node = element.find(f"./{name}")
    if node is None:
        node = element.find(f"./display/{name}")
    return str(node.text or "").strip() if node is not None else ""

def _set_direct_text(
        element: ElementTree.Element, name: str, value: object) -> None:
    text = str(value or "").strip()
    node = element.find(f"./{name}")
    parent = element
    if node is None:
        node = element.find(f"./display/{name}")
        if node is not None:
            display_parent = element.find("./display")
            parent = display_parent if display_parent is not None else element
    if not text:
        if node is not None:
            parent.remove(node)
        return
    if node is None:
        display = element.find("./display")
        if display is None:
            display = ElementTree.SubElement(element, "display")
            display.set("class", _LINK_CLASS)
        node = ElementTree.SubElement(display, name)
    node.text = text

def _display_class(element: ElementTree.Element) -> str:
    display = element.find("./display")
    return str(display.get("class") or _LINK_CLASS) if display is not None else _LINK_CLASS

def _set_display_class(element: ElementTree.Element, value: str) -> None:
    display = element.find("./display")
    if display is None:
        display = ElementTree.SubElement(element, "display")
    display.set("class", value)

def _display_option(element: ElementTree.Element, name: str) -> str:
    node = element.find(f"./display/{name}")
    return str(node.text or "").strip() if node is not None else ""

def _set_display_option(
        element: ElementTree.Element, name: str, value: object) -> None:
    display = element.find("./display")
    text = str(value or "").strip()
    node = display.find(f"./{name}") if display is not None else None
    if not text:
        if display is not None and node is not None:
            display.remove(node)
        return
    if display is None:
        display = ElementTree.SubElement(element, "display")
        display.set("class", _LINK_CLASS)
    if node is None:
        node = ElementTree.SubElement(display, name)
    node.text = text

def _widget_type(element: ElementTree.Element) -> str:
    if element.find("./display/class_name") is not None:
        return "__class__"
    value = _display_option(element, "widget_key")
    return value if value in _WIDGET_TYPE_VALUES else "view_panel"

def _result_view_mode(element: ElementTree.Element) -> str:
    value = _display_option(element, "view_mode")
    if value in _RESULT_VIEW_VALUES:
        return value
    widget_type = _widget_type(element)
    if widget_type == "tile_layout":
        return "tiles"
    if widget_type == "fast_layout":
        return "compact"
    return "continious"


def _empty_document(view):
    root = ElementTree.Element('config')
    ElementTree.SubElement(root, 'view', name=view) if '@' in view else ElementTree.SubElement(root, view)
    return root

class SidebarDraft:
    canEdit = True

    def __init__(self, documents, groups, project, source='handler', selected=-1, collapsed=(), updates=(), preview_group=''):
        if not isinstance(documents, dict) or len(documents) > 128:
            raise ValueError('Invalid sidebar documents')
        if source not in ('handler', 'tactic'):
            raise ValueError('Invalid sidebar source')
        if type(selected) is not int or selected < -1 or selected > 255:
            raise ValueError('Invalid sidebar selection')
        if not isinstance(collapsed, (list, tuple, set)) or len(collapsed) > 256 or any(not isinstance(key, str) or len(key) > 4096 for key in collapsed):
            raise ValueError('Invalid folded sidebar items')
        if not isinstance(updates, (list, tuple)) or len(updates) > 8192 or not isinstance(preview_group, str):
            raise ValueError('Invalid sidebar permissions')
        self._documents = {}
        for view, xml in documents.items():
            if not re.fullmatch(r'[A-Za-z_][\w.@-]{0,127}', view) or not isinstance(xml, str) or len(xml.encode()) > 512 * 1024:
                raise ValueError('Invalid sidebar view or XML')
            root = _parse_document(xml)
            if root.tag != 'config':
                raise ValueError('The document must have a config root')
            if not len(root) or any(child.tag == 'element' for child in root):
                wrapped = _empty_document(view)
                wrapped[0].extend(list(root))
                root = wrapped
            self._documents[view] = root
        self._security_objects = {group['code'] or group['login_group']: group for group in groups}
        self._security_pending = {}
        for update in updates:
            if not isinstance(update, dict) or update.get('group_code') not in self._security_objects or not isinstance(update.get('element'), str) or type(update.get('allowed')) is not bool:
                raise ValueError('Invalid sidebar group permission')
            self._security_pending[(update['element'], update['group_code'])] = update['allowed']
        if preview_group and preview_group not in self._security_objects:
            raise ValueError('Unknown preview group')
        self._project_code = project
        self._sidebar_source = source
        self._root_view = 'tactic_handler' if source == 'handler' else 'project_view'
        self._preview_group = preview_group
        self._collapsed_folders = set(collapsed)
        self._selected_row = selected
        self._xml_view = self._root_view
        self._error = ''
        self._rebuild_entries()

    def _accent_for_search_type(self, search_type):
        return ''

    def _group_rule_allowed(self, group, element_name):
        return _sidebar_rule_allowed(group.get('access_rules'), element_name, self._project_code)

    def _group_allowed(self, element_name, group_code):
        return self._security_pending.get((element_name, group_code), self._group_rule_allowed(self._security_objects[group_code], element_name))

    def result(self):
        selected = self.entries[self._selected_row] if self._selected_row >= 0 else {}
        return dict(documents={view: _serialize(root) for view, root in self._documents.items()}, entries=self.entries,
            selected=self._selected_row, xml=self._xml_text, source=self._sidebar_source, collapsed=sorted(self._collapsed_folders),
            previewGroup=self._preview_group,
            updates=[dict(element=name, group_code=code, allowed=allowed) for (name, code), allowed in sorted(self._security_pending.items())],
            groups=[dict(code=code, label=group.get('description') or group.get('login_group') or code,
                         allowed=self._group_allowed(selected.get('name', ''), code)) for code, group in self._security_objects.items()])

    def _apply_xml_text(self) -> bool:
        if not self.canEdit or not 0 <= self._selected_row < len(self._flat_refs):
            return False
        try:
            replacement = _parse_element(self._xml_text)
        except ElementTree.ParseError as error:
            self._error = f"Invalid sidebar XML: {error}"
    
            return False
        owner, selector, element = self._flat_refs[self._selected_row]
        containing_root = None
        parent = None
        for document in self._documents.values():
            candidate = _element_parent(document, element)
            if candidate is not None:
                containing_root = document
                parent = candidate
                break
        if containing_root is None or parent is None:
            self._error = "Selected sidebar element no longer exists"
    
            return False
        previous_name = str(element.get("name") or "")
        replacement_name = str(replacement.get("name") or "").strip()
        if not replacement_name:
            self._error = "Sidebar element name is required"
    
            return False
        self.check_name(replacement_name, element)
        index = list(parent).index(element)
        parent.remove(element)
        parent.insert(index, replacement)
        if replacement_name != previous_name:
            self.rename_permissions(previous_name, replacement_name)
            for view, document in self._documents.items():
                if document is containing_root:
                    continue
                for reference in _all_elements(document):
                    if str(reference.get("name") or "") == previous_name:
                        reference.set("name", replacement_name)
            if selector is not None and selector is not element:
                selector.set("name", replacement_name)
        self._error = ""
        selected_id = (
            id(selector) if selector is not None and selector is not element
            else id(replacement)
        )
        self._rebuild_entries(selected_element_id=selected_id)
        return True

    def update_selected(self, field: str, value) -> None:
        if not self.canEdit or not 0 <= self._selected_row < len(self._flat_refs):
            return
        _view, selector, element = self._flat_refs[self._selected_row]
        field = str(field or "")
        text = str(value or "")
        if field in {"name", "title", "icon"}:
            if field == "name":
                previous = str(element.get("name") or "")
                text = _slug(text)
                self.check_name(text, element)
            elif field == "icon":
                text = icon_name_for_tactic(text)
            if text:
                element.set(field, text)
            else:
                element.attrib.pop(field, None)
            if field == "name" and text != previous:
                self.rename_permissions(previous, text)
                for view, document in self._documents.items():
                    if view == "definition":
                        continue
                    for reference in _all_elements(document):
                        if str(reference.get("name") or "") == previous:
                            reference.set("name", text)
                if selector is not None:
                    selector.set("name", text)
        elif field == "entryType":
            classes = {
                "link": _LINK_CLASS,
                "section": _SECTION_CLASS,
                "separator": _SEPARATOR_CLASS,
            }
            if text not in classes:
                return
            _set_display_class(element, classes[text])
            if text != "link":
                _set_direct_text(element, "search_type", "")
                _set_direct_text(element, "search_view", "")
            if text != "section":
                _set_direct_text(element, "view", "")
        elif field == "searchType":
            _set_direct_text(element, "search_type", text)
        elif field == "searchView":
            _set_direct_text(element, "search_view", text)
        elif field == "targetView":
            _set_direct_text(element, "view", _slug(text, "sidebar_section"))
        elif field == "isVisible":
            element.set("is_visible", "on" if bool(value) else "off")
        elif field == "widgetType":
            if text not in _WIDGET_TYPE_VALUES:
                return
            _set_display_class(element, _LINK_CLASS)
            _set_display_option(element, "widget_key", "")
            _set_display_option(element, "class_name", "")
            if text == "__class__":
                display = element.find("./display")
                if display is None:
                    display = ElementTree.SubElement(element, "display")
                    display.set("class", _LINK_CLASS)
                ElementTree.SubElement(display, "class_name")
            else:
                _set_display_option(element, "widget_key", text)
        elif field == "displayView":
            _set_display_option(element, "view", text)
        elif field == "displayClassName":
            _set_display_option(element, "widget_key", "")
            _set_display_option(element, "class_name", text)
        elif field == "resultViewMode":
            if text not in _RESULT_VIEW_VALUES:
                return
            _set_display_option(element, "view_mode", text)
        elif field == "layoutPreset":
            _set_display_option(element, "layout_preset", text)
        elif field == "scriptShelf":
            _set_display_option(element, "script_shelf", text)
        else:
            return
        self._error = ""
        selected_key = id(selector if selector is not None else element)
        self._rebuild_entries(selected_element_id=selected_key)

    def add_entry(self, entry_type: str) -> None:
        if not self.canEdit:
            return
        entry_type = str(entry_type or "link")
        owner = self._root_view
        if 0 <= self._selected_row < len(self._flat_refs):
            owner, _selector, selected = self._flat_refs[self._selected_row]
            if _display_class(selected) == _SECTION_CLASS:
                owner = _direct_text(selected, "view") or owner
        if owner not in self._documents:
            self._documents[owner] = _empty_document(owner)
        if "definition" not in self._documents:
            self._documents["definition"] = _empty_document('definition')
        definition_root = self._documents["definition"]
        definition_names = {
            str(item.get("name") or "")
            for item in _all_elements(definition_root)
        }
        number = len(definition_names) + 1
        name = f"sidebar_item_{number}"
        while name in definition_names:
            number += 1
            name = f"sidebar_item_{number}"
        element = ElementTree.SubElement(
            _element_container(definition_root),
            "element",
            {
                "name": name,
                "title": "New sidebar item",
                "icon": icon_name_for_tactic("link"),
            },
        )
        if entry_type == "section":
            element.set("title", "New section")
            element.set("icon", icon_name_for_tactic("folder"))
            _set_display_class(element, _SECTION_CLASS)
            view_name = self._unique_view_name("sidebar_section")
            _set_direct_text(element, "view", view_name)
            self._documents[view_name] = _empty_document(view_name)
        elif entry_type == "separator":
            element.attrib.update({"title": "", "icon": ""})
            _set_display_class(element, _SEPARATOR_CLASS)
        else:
            _set_display_class(element, _LINK_CLASS)
            _set_direct_text(element, "search_type", "")
        if self._sidebar_source == "handler" and self._preview_group:
            for group_code, group in self._security_objects.items():
                allowed = group_code == self._preview_group
                if allowed != self._group_rule_allowed(group, name):
                    self._security_pending[(name, group_code)] = allowed
        selector = element if owner == "definition" else ElementTree.SubElement(
            _element_container(self._documents[owner]),
            "element",
            {"name": name},
        )
        self._rebuild_entries(selected_element_id=id(selector))

    def delete_selected(self) -> None:
        if not self.canEdit or not 0 <= self._selected_row < len(self._flat_refs):
            return
        owner, selector, _element = self._flat_refs[self._selected_row]
        if selector is None:
            return
        root = self._documents.get(owner)
        if root is None:
            return
        parent = _element_parent(root, selector)
        if parent is not None:
            parent.remove(selector)
        self._selected_row = -1
        self._rebuild_entries()

    def move_selected(self, offset: int) -> None:
        if not self.canEdit or not 0 <= self._selected_row < len(self._flat_refs):
            return
        owner, selector, _element = self._flat_refs[self._selected_row]
        if selector is None:
            return
        root = self._documents.get(owner)
        if root is None:
            return
        parent = _element_parent(root, selector)
        if parent is None:
            return
        items = [item for item in list(parent) if item.tag == "element"]
        try:
            row = items.index(selector)
        except ValueError:
            return
        target = row + (-1 if offset < 0 else 1)
        if not 0 <= target < len(items):
            return
        target_element = items[target]
        target_index = list(parent).index(target_element)
        parent.remove(selector)
        parent.insert(target_index, selector)
        self._rebuild_entries(selected_element_id=id(selector))

    def _unique_view_name(self, prefix: str) -> str:
        index = 1
        while True:
            name = f"{prefix}_{index}"
            if name not in self._documents:
                return name
            index += 1

    def _sync_xml_text(self) -> None:
        if 0 <= self._selected_row < len(self._flat_refs):
            self._xml_text = _serialize_element(
                self._flat_refs[self._selected_row][2]
            )
        else:
            self._xml_text = ""

    def _rebuild_entries(self, selected_element_id: int | None = None) -> None:
        records: list[dict] = []
        refs: list[
            tuple[str, ElementTree.Element | None, ElementTree.Element]
        ] = []
        definition_document = self._documents.get("definition")
        definitions = {
            str(element.get("name") or ""): element
            for element in (
                _all_elements(definition_document)
                if definition_document is not None else []
            )
            if element.get("name")
        }

        def walk_elements(
                owner: str,
                selectors: list[ElementTree.Element],
                depth: int,
                path: str,
                view_ancestors: tuple[str, ...]) -> None:
            if depth > 8 or len(records) + len(selectors) > 256:
                raise ValueError('Sidebar nesting or entry limit exceeded')
            for index, selector in enumerate(selectors):
                name = str(selector.get("name") or "")
                element = definitions.get(name, selector)
                display = _display_class(element)
                entry_type = (
                    "section" if display == _SECTION_CLASS
                    else "separator" if display == _SEPARATOR_CLASS
                    else "link"
                )
                target = _direct_text(element, "view")
                selector_children = _nested_elements(selector)
                definition_children = (
                    _nested_elements(element) if element is not selector else []
                )
                target_children = (
                    _view_elements(self._documents[target])
                    if target in self._documents else []
                )
                has_children = bool(
                    selector_children or definition_children or target_children
                )
                is_selected = (
                    id(selector) == selected_element_id
                    if selected_element_id is not None
                    else len(refs) == self._selected_row
                )
                key = f"{path}/{index}:{name or 'separator'}"
                records.append({
                    "key": key,
                    "name": str(element.get("name") or "untitled"),
                    "title": str(element.get("title") or element.get("name") or "Untitled"),
                    "entryType": entry_type,
                    "icon": str(element.get("icon") or (
                        "folder" if entry_type == "section" else "link"
                    )),
                    "searchType": _direct_text(element, "search_type"),
                    "searchView": _direct_text(element, "search_view"),
                    "targetView": target,
                    "ownerView": owner,
                    "depth": depth,
                    "displayDepth": depth,
                    "selected": is_selected,
                    "glyph": icon_name_from_tactic(str(element.get("icon") or "link")),
                    "accent": self._accent_for_search_type(
                        _direct_text(element, "search_type")
                    ),
                    "included": True,
                    "expanded": key not in self._collapsed_folders,
                    "entryVisible": True,
                    "hasChildren": has_children,
                    "isVisible": str(
                        element.get("is_visible") or "on"
                    ).strip().lower() not in {"off", "false", "no", "0"},
                    "widgetType": _widget_type(element),
                    "displayView": _display_option(element, "view"),
                    "displayClassName": _display_option(
                        element, "class_name"
                    ),
                    "resultViewMode": _result_view_mode(element),
                    "layoutPreset": _display_option(
                        element, "layout_preset"
                    ),
                    "scriptShelf": _display_option(
                        element, "script_shelf"
                    ),
                })
                refs.append((owner, selector, element))
                if entry_type != "section":
                    continue
                if selector_children:
                    walk_elements(
                        owner, selector_children, depth + 1, key,
                        view_ancestors,
                    )
                elif definition_children:
                    walk_elements(
                        "definition", definition_children, depth + 1, key,
                        view_ancestors,
                    )
                elif target_children and target not in view_ancestors:
                    walk_elements(
                        target, target_children, depth + 1, key,
                        (*view_ancestors, target),
                    )
                elif target_children:
                    raise ValueError('Cyclic sidebar view reference: ' + target)

        root_document = self._documents.get(self._root_view)
        if root_document is not None:
            walk_elements(
                self._root_view,
                _view_elements(root_document),
                0,
                self._root_view,
                (self._root_view,),
            )

        preview_group = (
            self._preview_group
            if self._sidebar_source == "handler" else ""
        )
        expanded_by_depth: dict[int, bool] = {}
        for record in records:
            depth = int(record.get("depth") or 0)
            for ancestor_depth in tuple(expanded_by_depth):
                if ancestor_depth >= depth:
                    del expanded_by_depth[ancestor_depth]
            preview_visible = (
                not preview_group
                or self._group_allowed(record["name"], preview_group)
            )
            record["entryVisible"] = bool(
                preview_visible and all(expanded_by_depth.values())
            )
            if record.get("entryType") == "section":
                expanded_by_depth[depth] = bool(
                    preview_visible and record.get("expanded")
                )
        selected_row = next((
            index for index, record in enumerate(records)
            if record["selected"] and record["entryVisible"]
        ), -1)
        if selected_row < 0:
            for record in records:
                record["selected"] = False
            selected_row = next((
                index for index, record in enumerate(records)
                if record["entryVisible"]
            ), -1)
            if selected_row >= 0:
                records[selected_row]["selected"] = True
        self._flat_refs = refs
        self._selected_row = selected_row
        self.entries = records
        if self._selected_row >= 0:
            self._xml_view = refs[self._selected_row][0]
        elif self._xml_view not in self._documents:
            self._xml_view = self._root_view
        self._sync_xml_text()

    def check_name(self, name, current):
        if not re.fullmatch(r'[A-Za-z_][\w.@-]{0,127}', name):
            raise ValueError('Invalid sidebar element name')
        definitions = self._documents.get('definition')
        if definitions is not None and any(element is not current and element.get('name') == name for element in _all_elements(definitions)):
            raise ValueError('Sidebar element name already exists')

    def rename_permissions(self, old, new):
        for code, group in self._security_objects.items():
            allowed = self._group_allowed(old, code)
            self._security_pending[(old, code)] = False
            self._security_pending[(new, code)] = allowed


def _records():
    search = Search('config/widget_config')
    search.add_filter('search_type', 'SideBarWdg')
    search.add_order_by('priority desc')
    search.add_order_by('id desc')
    return [item for item in search.get_sobjects() if item.get_value('category', no_exception=True) not in ('workspace_layout', 'script_shelf')]


def _groups():
    search = Search('sthpw/login_group')
    search.add_order_by('login_group')
    return search.get_sobjects()


def _revision(records, groups):
    import hashlib
    import json
    # Include the native journal marker so A -> B -> A cannot bypass revision checks.
    log = Search('sthpw/sobject_log')
    log.add_filters('search_type', list(dict.fromkeys([Search('config/widget_config').get_search_type(),
        Project.get_full_search_type('config/widget_config'), 'config/widget_config?project=' + Project.get_project_code(), 'sthpw/login_group'])))
    log.add_order_by('id desc')
    log.add_limit(1)
    latest = log.get_sobject()
    data = [Project.get_project_code(), [item.get_data() for item in records],
            [item.get_data() for item in groups], latest.get_id() if latest else None]
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


def read_sidebar():
    _require_admin()
    records, groups = _records(), _groups()
    documents = {}
    for item in records:
        documents.setdefault(item.get_value('view') or 'definition', item.get_value('config'))
    draft = SidebarDraft(documents, [item.get_data() for item in groups], Project.get_project_code())
    result = draft.result()
    result['revision'] = _revision(records, groups)
    result['project'] = Project.get_project_code()
    result['projectTitle'] = Project.get().get_value('title', no_exception=True) or result['project']
    types = Search('sthpw/search_object')
    result['searchTypes'] = sorted([dict(value=item.get_value('search_type'), label=item.get_value('title') or item.get_value('search_type'), color=item.get_value('color', no_exception=True) or '')
                                   for item in types.get_sobjects()], key=lambda row: row['label'].lower())
    library = Search('config/widget_config')
    result['library'] = [dict(code=item.get_code(), view=item.get_value('view'), title=item.get_value('title'),
                             search_type=item.get_value('search_type'), category=item.get_value('category', no_exception=True), config=item.get_value('config'))
                         for item in library.get_sobjects() if item.get_value('category', no_exception=True) in ('workspace_layout', 'script_shelf') or item.get_value('view').startswith('link_search:')]
    return result


def sidebar_request(action, payload):
    _require_admin()
    if action == 'read':
        return read_sidebar()
    state = payload.get('state')
    if not isinstance(state, dict) or set(state) - {'documents', 'selected', 'source', 'collapsed', 'updates', 'previewGroup'}:
        raise ValueError('Invalid sidebar draft')
    groups = _groups()
    draft = SidebarDraft(state.get('documents'), [item.get_data() for item in groups], Project.get_project_code(),
                         state.get('source', 'handler'), state.get('selected', -1), state.get('collapsed', []),
                         state.get('updates', []), state.get('previewGroup', ''))
    if action == 'save':
        return save_sidebar(draft, payload.get('revision'))
    operation = payload.get('operation')
    if operation == 'field':
        field, value = payload.get('field'), payload.get('value')
        if field not in {'name', 'title', 'icon', 'entryType', 'searchType', 'searchView', 'targetView', 'isVisible', 'widgetType', 'displayView', 'displayClassName', 'resultViewMode', 'layoutPreset', 'scriptShelf'}:
            raise ValueError('Invalid sidebar field')
        if field == 'isVisible' and type(value) is not bool or field != 'isVisible' and (not isinstance(value, str) or len(value) > 4096):
            raise ValueError('Invalid sidebar field value')
        draft.update_selected(field, value)
    elif operation == 'add':
        if payload.get('value') not in ('link', 'section', 'separator'):
            raise ValueError('Invalid sidebar item type')
        draft.add_entry(payload['value'])
    elif operation == 'delete':
        draft.delete_selected()
    elif operation == 'move':
        if payload.get('value') not in (-1, 1):
            raise ValueError('Invalid move direction')
        draft.move_selected(payload['value'])
    elif operation == 'xml':
        draft._xml_text = payload.get('xml') or ''
        if not draft._apply_xml_text():
            raise ValueError(draft._error or 'Select a sidebar element first')
    elif operation == 'group':
        code, value = payload.get('field'), payload.get('value')
        if code not in draft._security_objects or type(value) is not bool or draft._selected_row < 0:
            raise ValueError('Invalid sidebar group permission')
        element = draft._flat_refs[draft._selected_row][2]
        draft._security_pending[(element.get('name'), code)] = value
        draft._rebuild_entries()
    elif operation == 'toggle':
        if draft._selected_row >= 0:
            row = draft.entries[draft._selected_row]
            key = row['key']
            if key in draft._collapsed_folders:
                draft._collapsed_folders.remove(key)
            else:
                draft._collapsed_folders.add(key)
            draft._rebuild_entries()
    elif operation != 'select':
        raise ValueError('Invalid sidebar operation')
    return draft.result()


def save_sidebar(draft, revision):
    command = Command()
    def execute():
        # Same table locks as the native XML editor, shared by all processes/vendors.
        for search_type in ('config/widget_config', 'sthpw/login_group'):
            sql = Search(search_type).get_sql()
            sql.get_database_impl().lock_collection_table(sql, SearchType.get(search_type).get_table())
        records, groups = _records(), _groups()
        if not isinstance(revision, str) or revision != _revision(records, groups):
            raise WidgetConfigConflict('Interface configuration changed. Reload before saving.')
        for source in ('handler', 'tactic'):
            SidebarDraft(draft.result()['documents'], [item.get_data() for item in groups], Project.get_project_code(), source)
        current = {}
        for record in records:
            current.setdefault(record.get_value('view') or 'definition', record)
        documents = draft.result()['documents']
        for view, xml in documents.items():
            item = current.get(view)
            if item is not None and _serialize(_parse_document(item.get_value('config'))) == xml:
                continue
            if item is None:
                item = SearchType.create('config/widget_config')
                item.set_value('search_type', 'SideBarWdg')
                item.set_value('view', view)
                item.set_value('title', view.replace('_', ' ').title())
            item.set_value('config', xml)
            item.commit()
        for group in groups:
            code = group.get_code() or group.get_value('login_group')
            changes = [(element, allowed) for (element, group_code), allowed in draft._security_pending.items() if group_code == code]
            if not changes:
                continue
            root = _security_document(group.get_value('access_rules', no_exception=True))
            # Handler mutate_sidebar_security: merge only exact project/link rules.
            for name, allowed in changes:
                for parent in root.iter():
                    for rule in list(parent):
                        if rule.tag == 'rule' and rule.get('group') == 'link' and rule.get('element') == name and rule.get('project') == Project.get_project_code():
                            parent.remove(rule)
                if allowed:
                    ElementTree.SubElement(root, 'rule', group='link', element=name, access='allow', project=Project.get_project_code())
            group.set_value('access_rules', ElementTree.tostring(root, encoding='unicode'))
            group.commit()
        command.add_description('Save project sidebar and link permissions')
    command.execute = execute
    command.get_transaction().set_sync(False)
    Command.execute_cmd(command)
    result = read_sidebar()
    result.update(SidebarDraft(result['documents'], [item.get_data() for item in _groups()], Project.get_project_code(), draft._sidebar_source,
                              draft._selected_row, draft._collapsed_folders, preview_group=draft._preview_group).result())
    return result


