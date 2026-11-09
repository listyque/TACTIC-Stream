// Handler catalog_wizard / update_catalog_wizard and tactic_definition helpers.
import widgetCatalog from '../../../../src/tactic_stream/shared_ui/features/table/widgets.json';

const WIZARD_WIDGET_VALUES = new Set([
  '',
  'format',
  'expression',
  'tactic.ui.table.expression_element_wdg.ExpressionValueElementWdg',
  'link',
  'pyasm.widget.ThumbWdg',
  'tactic.ui.widget.DiscussionElementWdg',
  'tactic.ui.table.TaskElementWdg',
  'tactic.ui.table.TaskCompletionWdg',
  'tactic.ui.table.gantt_element_wdg.GanttElementWdg',
  'tactic.ui.table.hidden_row_element_wdg.HiddenRowElementWdg',
  'tactic.ui.table.DropElementWdg',
  'tactic.ui.table.ButtonElementWdg',
  'tactic.ui.table.CustomLayoutElementWdg',
  'tactic.ui.table.SObjectDetailElementWdg',
  'tactic.ui.table.CheckinButtonElementWdg',
  'tactic.ui.table.ExploreElementWdg',
  'tactic.ui.table.SObjectFilesElementWdg',
  'tactic.ui.table.MetadataElementWdg',
  'tactic.ui.table.DeleteElementWdg',
  'tactic.ui.common.base_table_element_wdg.RawTableElementWdg'
]);

const LEGACY_DUPLICATE_WIDGET_VALUES = new Set([
  'pyasm.widget.statistic_wdg.TaskCompletionWdg',
  'tactic.ui.table.explorer_wdg.ExplorerTableElementWdg',
  'tactic.ui.widget.discussion_wdg.DiscussionWdg',
  'pyasm.widget.discussion_wdg.DiscussionWdg',
  'pyasm.widget.task_wdg.SObjectTaskTableElement',
  'HiddenRowToggleWdg',
  'GanttWdg'
]);

const curatedCatalog = widgetCatalog.filter((row) =>
  WIZARD_WIDGET_VALUES.has(row.value)
);

const extendedCatalog = [
  ...curatedCatalog,
  ...widgetCatalog.filter(
    (row) =>
      !WIZARD_WIDGET_VALUES.has(row.value) &&
      !LEGACY_DUPLICATE_WIDGET_VALUES.has(row.value)
  )
];

export const displayWidgets = curatedCatalog.map(({ value, label }) => ({
  value,
  label
}));

export const allDisplayWidgets = extendedCatalog.map(({ value, label }) => ({
  value,
  label
}));

export function widgetOptionsFor(widget, showAll = false) {
  const value = String(widget || '').trim(),
    activeCatalog = showAll ? extendedCatalog : curatedCatalog,
    activeList = showAll ? allDisplayWidgets : displayWidgets;
  if (!value || activeList.some((row) => row.value === value))
    return activeList;
  const activeMatch = activeCatalog.find((row) =>
    (row.aliases || []).includes(value)
  );
  if (activeMatch)
    return activeList.map((row) =>
      row.value === activeMatch.value ? { value, label: row.label } : row
    );
  const catalogMatch = widgetCatalog.find(
    (row) => row.value === value || (row.aliases || []).includes(value)
  );
  return [
    {
      value,
      label: catalogMatch ? catalogMatch.label : value,
      translate: Boolean(catalogMatch)
    },
    ...activeList
  ];
}

function parse(source) {
  if (/<!DOCTYPE|<!ENTITY/i.test(source))
    throw new Error('Document types and XML entities are not supported');
  const document = new DOMParser().parseFromString(
    source.trim() || '<config/>',
    'application/xml'
  );
  if (document.querySelector('parsererror'))
    throw new Error('Invalid configuration XML');
  return document;
}

function tableView(root, name) {
  return [root, ...root.children].find(
    (node) =>
      node.tagName === name ||
      (node.tagName === 'view' && node.getAttribute('name') === name)
  );
}

export function tableDefinition(
  configuration,
  elements = configuration.resolved.elements
) {
  const source =
    configuration.sources[0]?.xml ||
    configuration.layers.find((layer) => layer.view === configuration.view)
      ?.xml;
  const document = source ? parse(source) : parse('<config/>');
  const root = document.documentElement;
  let view = tableView(root, configuration.view);
  if (!view) {
    view = document.createElement(
      configuration.view.includes('@') ? 'view' : configuration.view
    );
    if (view.tagName === 'view') view.setAttribute('name', configuration.view);
    view.setAttribute('layout', 'TableLayoutWdg');
    root.appendChild(view);
  }
  // Visible columns may come from the schema before a table definition exists.
  const nodes = new Map(
    [...view.children]
      .filter((node) => node.tagName === 'element')
      .map((node) => [node.getAttribute('name'), node])
  );
  for (const [index, element] of elements.entries()) {
    if (!nodes.has(element.name)) {
      const node = document.createElement('element');
      node.setAttribute('name', element.name);
      for (const [key, value] of Object.entries(element.attributes || {}))
        node.setAttribute(key, String(value));
      const next = elements
        .slice(index + 1)
        .map((element) => nodes.get(element.name))
        .find(Boolean);
      view.insertBefore(node, next || null);
      nodes.set(element.name, node);
    }
  }
  return new XMLSerializer().serializeToString(document);
}

export function changeTable(source, viewName, action, name, value) {
  const document = parse(source),
    root = document.documentElement;
  const view = tableView(root, viewName);
  if (!view) throw new Error('The current table view is missing.');
  const elements = [...view.children].filter(
    (node) => node.tagName === 'element'
  );
  const node = elements.find((node) => node.getAttribute('name') === name);
  if (action === 'copy') {
    const renamed = document.createElement(value.view);
    for (const attr of view.attributes)
      renamed.setAttribute(attr.name, attr.value);
    while (view.firstChild) renamed.appendChild(view.firstChild);
    if (root === view) {
      document.replaceChild(renamed, root);
      renamed.setAttribute('th_table_view_title', value.title);
    } else {
      view.replaceWith(renamed);
      root.setAttribute('th_table_view_title', value.title);
    }
  } else {
    if (!node)
      throw new Error('Definition XML path no longer points to a column.');
    if (action === 'width') node.setAttribute('width', String(width(value)));
    else if (action === 'hide') {
      if (
        elements.filter((node) => !flag(node.getAttribute('hidden'))).length <=
        1
      )
        throw new Error('At least one column must remain visible');
      node.setAttribute('hidden', 'true');
    } else if (action === 'move') {
      const target = elements.find(
        (node) => node.getAttribute('name') === value
      );
      if (!target)
        throw new Error('Definition XML path no longer points to a column.');
      view.insertBefore(
        node,
        elements.indexOf(node) < elements.indexOf(target)
          ? target.nextSibling
          : target
      );
    } else throw new Error('Unknown table operation');
  }
  return new XMLSerializer().serializeToString(document);
}
function children(node) {
  return [...node.childNodes].filter((child) =>
    [1, 7, 8].includes(child.nodeType)
  );
}
function width(value) {
  const number = String(value ?? '')
    .trim()
    .replace(/px$/, '');
  return /^[+-]?\d+$/.test(number)
    ? Math.max(48, Math.min(640, Number(number) || 160))
    : 160;
}
function flag(value) {
  return ['1', 'true', 'yes', 'on'].includes(
    String(value).trim().toLowerCase()
  );
}
function elementXml(node) {
  const clone = node.cloneNode(true);
  function indent(el, depth = 0) {
    const items = [...el.childNodes].filter(
      (child) => child.nodeType !== 3 || child.nodeValue.trim()
    );
    if (!items.some((child) => child.nodeType === 1)) return;
    while (el.firstChild) el.removeChild(el.firstChild);
    const doc = el.ownerDocument,
      pad = '\n' + '  '.repeat(depth + 1);
    for (const child of items) {
      el.appendChild(doc.createTextNode(pad));
      if (child.nodeType === 1) indent(child, depth + 1);
      el.appendChild(child);
    }
    el.appendChild(doc.createTextNode('\n' + '  '.repeat(depth)));
  }
  indent(clone);
  return new XMLSerializer().serializeToString(clone);
}

function childElements(node) {
  return node ? [...node.children].filter((child) => child.nodeType === 1) : [];
}

function childMap(node) {
  const result = {};
  for (const child of childElements(node)) {
    result[child.tagName] = (child.textContent || '').trim();
  }
  return result;
}

function findViewNode(root, viewName = '') {
  let view = null,
    viewPath = '';
  function find(node, path = '') {
    if (node.nodeType !== 1 || view) return;
    if (
      viewName
        ? node.tagName === viewName ||
          (node.tagName === 'view' && node.getAttribute('name') === viewName)
        : ['table', 'definition', 'edit', 'edit_definition'].includes(
            node.tagName
          ) ||
          ['TableLayoutWdg', 'tactic.ui.panel.TableLayoutWdg'].includes(
            node.getAttribute('layout')
          )
    ) {
      view = node;
      viewPath = path;
      return;
    }
    children(node).forEach((child, index) =>
      find(child, path ? `${path}/${index}` : String(index))
    );
  }
  find(root);
  return { view, viewPath };
}

function parseElementNode(node, path) {
  const display = childElements(node).find(
      (child) => child.tagName === 'display'
    ),
    editNode = childElements(node).find((child) => child.tagName === 'edit'),
    actionNode = childElements(node).find(
      (child) => child.tagName === 'action'
    ),
    name = node.getAttribute('name') || '',
    rawTitle = node.getAttribute('title') || '',
    rawWidth = node.getAttribute('width') || '',
    displayClass = display?.getAttribute('class') || '',
    widgetKey = display?.getAttribute('widget') || '',
    widget = displayClass || widgetKey || '',
    editClass = editNode?.getAttribute('class') || '',
    editWidgetKey = editNode?.getAttribute('widget') || '',
    editWidget = editClass || editWidgetKey || '',
    actionClass = actionNode?.getAttribute('class') || '';
  return {
    path,
    name,
    rawTitle,
    title: rawTitle || name,
    visible: !flag(node.getAttribute('hidden')),
    rawWidth,
    width: width(rawWidth),
    color: node.getAttribute('color') !== 'false',
    editable: node.getAttribute('edit') !== 'false',
    ...(node.hasAttribute('value_icon')
      ? { valueIcon: node.getAttribute('value_icon') }
      : display?.querySelector('icon')
        ? { valueIcon: display.querySelector('icon').textContent }
        : {}),
    ...(node.hasAttribute('value_style')
      ? { valueStyle: node.getAttribute('value_style') }
      : {}),
    ...(node.hasAttribute('value_text_style')
      ? { valueTextStyle: node.getAttribute('value_text_style') }
      : {}),
    ...(node.hasAttribute('value_align')
      ? { valueAlign: node.getAttribute('value_align') }
      : {}),
    widget,
    widgetKey,
    displayClass,
    displayOptions: childMap(display),
    editWidget,
    editWidgetKey,
    editClass,
    editOptions: childMap(editNode),
    actionClass,
    actionOptions: childMap(actionNode),
    xml: elementXml(node)
  };
}

function parseRecordElements(xmlText, viewName = '') {
  const map = new Map();
  if (!xmlText || !String(xmlText).trim()) return map;
  try {
    const root = parse(String(xmlText)).documentElement;
    const { view, viewPath } = findViewNode(root, viewName);
    if (!view) return map;
    children(view).forEach((node, index) => {
      if (node.nodeType !== 1 || node.tagName !== 'element') return;
      const parsed = parseElementNode(
        node,
        viewPath ? `${viewPath}/${index}` : String(index)
      );
      if (parsed.name) map.set(parsed.name, parsed);
    });
  } catch (_err) {
    // Ignore malformed sibling config
  }
  return map;
}

function parseColorRecord(xmlText) {
  const map = new Map();
  if (!xmlText || !String(xmlText).trim()) return map;
  try {
    const root = parse(String(xmlText)).documentElement;
    const { view } = findViewNode(root, 'color');
    const container = view || root;
    for (const el of childElements(container)) {
      if (el.tagName !== 'element') continue;
      const name = el.getAttribute('name') || '';
      if (!name) continue;
      const colorsNode =
        childElements(el).find((c) => c.tagName === 'colors') ||
        childElements(el).find((c) => c.tagName === 'display') ||
        el;
      const entries = [];
      for (const child of childElements(colorsNode)) {
        if (child.tagName === 'color') {
          entries.push({
            label:
              child.getAttribute('name') ||
              child.getAttribute('value') ||
              (child.textContent || '').trim(),
            color:
              child.getAttribute('color') ||
              child.getAttribute('bg') ||
              (child.textContent || '').trim()
          });
        } else {
          entries.push({
            label: child.tagName,
            color: (child.textContent || '').trim()
          });
        }
      }
      if (entries.length) map.set(name, entries);
    }
  } catch (_err) {
    // Ignore malformed color config
  }
  return map;
}

export function definitionWizard(
  source,
  viewName = '',
  searchType = '',
  records = []
) {
  const root = parse(source).documentElement;
  const { view, viewPath } = findViewNode(root, viewName);
  const rawElements = view
    ? children(view).flatMap((node, index) => {
        if (node.nodeType !== 1 || node.tagName !== 'element') return [];
        return [
          parseElementNode(
            node,
            viewPath ? `${viewPath}/${index}` : String(index)
          )
        ];
      })
    : [];
  if (!searchType || !Array.isArray(records) || !records.length) {
    return {
      supported: !!view,
      view: view?.tagName || '',
      layout: view?.getAttribute('layout') || '',
      elements: rawElements,
      definitionElements: []
    };
  }
  const baseStype = String(searchType).split('?')[0];
  const stypeRecords = records.filter(
    (row) => String(row.searchType || '').split('?')[0] === baseStype
  );
  const findConfig = (v) =>
    stypeRecords.find((row) => row.view === v && !row.login) ||
    stypeRecords.find((row) => row.view === v);
  const isEditView = viewName === 'edit' || viewName === 'edit_definition';
  const defRec = findConfig('definition');
  const defDefaultRec = findConfig('default_definition');
  const editDefRec = findConfig('edit_definition');
  const editRec = findConfig('edit');
  const colorRec = findConfig('color');

  const defMap =
    viewName === 'definition'
      ? new Map(rawElements.map((e) => [e.name, e]))
      : parseRecordElements(defRec?.config, 'definition');
  const defaultDefMap = parseRecordElements(
    defDefaultRec?.config,
    'default_definition'
  );
  const editDefMap =
    viewName === 'edit_definition'
      ? new Map(rawElements.map((e) => [e.name, e]))
      : parseRecordElements(editDefRec?.config, 'edit_definition');
  const editMap =
    viewName === 'edit'
      ? new Map(rawElements.map((e) => [e.name, e]))
      : parseRecordElements(editRec?.config, 'edit');
  const colorMaps = parseColorRecord(colorRec?.config);
  const activeViewName = viewName || view?.tagName || 'table';

  function enrichElement(base, inView) {
    const name = base.name;
    const defEl = defMap.get(name);
    const defDefaultEl = defaultDefMap.get(name);
    const editDefEl = editDefMap.get(name);
    const editViewEl = editMap.get(name);
    const inheritedDef = defEl || defDefaultEl;

    const widget = isEditView
      ? defEl?.widget || defDefaultEl?.widget || ''
      : base.widget || inheritedDef?.widget || '';
    const displayClass = isEditView
      ? defEl?.displayClass || defDefaultEl?.displayClass || ''
      : base.displayClass || inheritedDef?.displayClass || '';
    const widgetKey = isEditView
      ? defEl?.widgetKey || defDefaultEl?.widgetKey || ''
      : base.widgetKey || inheritedDef?.widgetKey || '';
    const displayOptions = Object.assign(
      {},
      defDefaultEl?.displayOptions || {},
      defEl?.displayOptions || {},
      isEditView ? {} : base.displayOptions || {}
    );

    const editWidget = isEditView
      ? base.editWidget ||
        base.widget ||
        editViewEl?.editWidget ||
        editViewEl?.widget ||
        editDefEl?.editWidget ||
        editDefEl?.widget ||
        ''
      : base.editWidget ||
        defEl?.editWidget ||
        editViewEl?.editWidget ||
        editViewEl?.widget ||
        editDefEl?.editWidget ||
        editDefEl?.widget ||
        '';
    const editClass = isEditView
      ? base.editClass ||
        base.displayClass ||
        editViewEl?.editClass ||
        editViewEl?.displayClass ||
        editDefEl?.editClass ||
        editDefEl?.displayClass ||
        ''
      : base.editClass ||
        defEl?.editClass ||
        editViewEl?.editClass ||
        editViewEl?.displayClass ||
        editDefEl?.editClass ||
        editDefEl?.displayClass ||
        '';
    const editOptions = Object.assign(
      {},
      editDefEl?.displayOptions || {},
      editDefEl?.editOptions || {},
      editViewEl?.displayOptions || {},
      editViewEl?.editOptions || {},
      defEl?.editOptions || {},
      isEditView ? base.displayOptions || {} : {},
      base.editOptions || {}
    );
    const actionClass =
      base.actionClass ||
      defEl?.actionClass ||
      editViewEl?.actionClass ||
      editDefEl?.actionClass ||
      '';
    const actionOptions = Object.assign(
      {},
      editDefEl?.actionOptions || {},
      editViewEl?.actionOptions || {},
      defEl?.actionOptions || {},
      base.actionOptions || {}
    );

    const configLayers = [];
    if (
      activeViewName !== 'definition' &&
      activeViewName !== 'default_definition'
    ) {
      configLayers.push({
        key: 'view_db',
        label: `${activeViewName} - [database]`,
        defined: inView,
        xml: inView ? base.xml : ''
      });
    }
    configLayers.push({
      key: 'def_db',
      label: 'definition - [database]',
      defined: !!defEl,
      xml: defEl ? defEl.xml : ''
    });
    if (
      activeViewName !== 'definition' &&
      activeViewName !== 'default_definition'
    ) {
      configLayers.push({
        key: 'view_gen',
        label: `${activeViewName} - [generated]`,
        defined: false,
        xml: ''
      });
    }
    configLayers.push({
      key: 'def_default',
      label: 'default_definition - [predefined]',
      defined: !!defDefaultEl,
      xml: defDefaultEl ? defDefaultEl.xml : ''
    });

    const editConfigLayers = [
      {
        key: 'edit_db',
        label: 'edit - [database]',
        defined: !!editViewEl,
        xml: editViewEl ? editViewEl.xml : ''
      },
      {
        key: 'edit_def_db',
        label: 'edit_definition - [database]',
        defined: !!editDefEl,
        xml: editDefEl ? editDefEl.xml : ''
      }
    ];

    return Object.assign({}, base, {
      inView,
      rawTitle: base.rawTitle || inheritedDef?.rawTitle || '',
      title: base.rawTitle || inheritedDef?.rawTitle || name,
      width: base.rawWidth
        ? base.width
        : inheritedDef?.rawWidth
          ? inheritedDef.width
          : base.width,
      widget,
      widgetKey,
      displayClass,
      displayOptions,
      editWidget,
      editClass,
      editOptions,
      actionClass,
      actionOptions,
      colorMap: colorMaps.get(name) || [],
      configLayers,
      editConfigLayers
    });
  }

  const elements = rawElements.map((el) => enrichElement(el, true));
  const viewByName = new Map(elements.map((el) => [el.name, el]));
  const allNames = [];
  const seen = new Set();
  for (const map of [
    defMap,
    defaultDefMap,
    editDefMap,
    editMap,
    new Map(rawElements.map((e) => [e.name, e]))
  ]) {
    for (const key of map.keys()) {
      if (key && !seen.has(key)) {
        seen.add(key);
        allNames.push(key);
      }
    }
  }
  const definitionElements = allNames.map((name) => {
    const viewEl = viewByName.get(name);
    if (viewEl) return viewEl;
    const base =
      defMap.get(name) ||
      defaultDefMap.get(name) ||
      editDefMap.get(name) ||
      editMap.get(name);
    const enriched = enrichElement(base, false);
    enriched.path = 'def:' + name;
    return enriched;
  });

  return {
    supported: !!view,
    view: view?.tagName || '',
    layout: view?.getAttribute('layout') || '',
    elements,
    definitionElements
  };
}

function ensureChildOption(container, doc, key, val) {
  let child = [...container.children].find((c) => c.tagName === key);
  const text = String(val ?? '').trim();
  if (!text) {
    if (child) container.removeChild(child);
    return;
  }
  if (!child) {
    child = doc.createElement(key);
    container.appendChild(child);
  }
  child.textContent = text;
}

export function changeDefinition(
  source,
  path,
  field,
  value,
  fallbackElement = null
) {
  const document = parse(source);
  let node = document.documentElement,
    parent = null;
  if (String(path || '').startsWith('def:') || field === 'addElement') {
    const colName = String(path || '').startsWith('def:')
      ? String(path).slice(4)
      : String(value || '').trim();
    if (!colName) throw new Error('Column name is required.');
    const { view } = findViewNode(document.documentElement);
    if (!view) throw new Error('The current table view is missing.');
    parent = view;
    node = [...view.children].find(
      (child) =>
        child.tagName === 'element' && child.getAttribute('name') === colName
    );
    if (!node) {
      node = document.createElement('element');
      node.setAttribute('name', colName);
      view.appendChild(node);
    }
    if (field === 'addElement')
      return new XMLSerializer().serializeToString(document);
  } else {
    for (const part of String(path || '')
      .split('/')
      .filter(Boolean)) {
      if (!/^\d+$/.test(part) || !children(node)[Number(part)])
        throw new Error('Definition XML path no longer exists.');
      parent = node;
      node = children(node)[Number(part)];
    }
  }
  if (node.tagName !== 'element')
    throw new Error('Definition XML path no longer points to a column.');
  if (field === 'removeElement') {
    if (!parent) throw new Error('Invalid column removal');
    const elements = [...parent.children].filter(
      (child) => child.tagName === 'element'
    );
    if (elements.length <= 1)
      throw new Error('At least one column must remain in the view');
    parent.removeChild(node);
    return new XMLSerializer().serializeToString(document);
  }
  if (field === 'move') {
    const offset = String(value);
    if (!['-1', '1'].includes(offset) || !parent)
      throw new Error('Invalid column move');
    const elements = [...parent.children].filter(
      (child) => child.tagName === 'element'
    );
    const target = elements[elements.indexOf(node) + Number(offset)];
    if (!target) throw new Error('The column cannot be moved further.');
    parent.insertBefore(node, offset === '1' ? target.nextSibling : target);
  } else if (field === 'title') {
    const text = String(value ?? '').trim();
    if (!text) node.removeAttribute('title');
    else node.setAttribute('title', text);
  } else if (field === 'visible')
    node.setAttribute('hidden', value ? 'false' : 'true');
  else if (field === 'color') {
    if (flag(value)) node.removeAttribute('color');
    else node.setAttribute('color', 'false');
  } else if (field === 'editable') {
    if (flag(value)) node.setAttribute('edit', 'true');
    else node.setAttribute('edit', 'false');
  } else if (field === 'width')
    node.setAttribute('width', String(width(value)));
  else if (field === 'valueIcon' || field === 'valueStyle') {
    const text = String(value || '').trim();
    if (field === 'valueStyle' && !['', 'text', 'badge'].includes(text))
      throw new Error('Invalid value appearance');
    if (
      field === 'valueIcon' &&
      (text.length > 128 || !/^[\w:.-]*$/.test(text))
    )
      throw new Error('Invalid icon name');
    node.setAttribute(
      field === 'valueIcon' ? 'value_icon' : 'value_style',
      text
    );
  } else if (field === 'valueTextStyle') {
    const text = String(value || '').trim();
    if (!['', 'heading', 'small'].includes(text))
      throw new Error('Invalid cell text style');
    node.setAttribute('value_text_style', text);
  } else if (field === 'valueAlign') {
    const text = String(value || '').trim();
    if (!['', 'left', 'center', 'right'].includes(text))
      throw new Error('Invalid cell alignment');
    node.setAttribute('value_align', text);
  } else if (field === 'widget' || field === 'displayClass') {
    let display = [...node.children].find(
      (child) => child.tagName === 'display'
    );
    if (!display) {
      display = document.createElement('display');
      node.appendChild(display);
      if (fallbackElement?.displayOptions) {
        for (const [k, v] of Object.entries(fallbackElement.displayOptions)) {
          ensureChildOption(display, document, k, v);
        }
      }
    }
    display.removeAttribute('widget');
    display.removeAttribute('class');
    const widget = String(value || '').trim();
    if (widget)
      display.setAttribute(
        field === 'displayClass' ||
          widget.includes('.') ||
          widget.endsWith('Wdg')
          ? 'class'
          : 'widget',
        widget
      );
  } else if (field.startsWith('option:')) {
    const optKey = field.slice(7).trim();
    if (!optKey || !/^[\w:.-]+$/.test(optKey))
      throw new Error('Invalid option name');
    let display = [...node.children].find(
      (child) => child.tagName === 'display'
    );
    if (!display) {
      display = document.createElement('display');
      if (fallbackElement?.widget) {
        const w = fallbackElement.widget;
        display.setAttribute(
          w.includes('.') || w.endsWith('Wdg') ? 'class' : 'widget',
          w
        );
      }
      node.appendChild(display);
      if (fallbackElement?.displayOptions) {
        for (const [k, v] of Object.entries(fallbackElement.displayOptions)) {
          ensureChildOption(display, document, k, v);
        }
      }
    }
    ensureChildOption(display, document, optKey, value);
  } else if (field === 'extraOptionAdd') {
    const raw = String(value || '').trim();
    if (!raw) return new XMLSerializer().serializeToString(document);
    const eq = raw.indexOf('=');
    const optKey = (eq >= 0 ? raw.slice(0, eq) : raw).trim();
    const optVal = eq >= 0 ? raw.slice(eq + 1).trim() : 'true';
    if (!optKey || !/^[A-Za-z_][\w.-]*$/.test(optKey))
      throw new Error(
        'Option name must be a valid XML tag (e.g. my_option=value)'
      );
    return changeDefinition(
      source,
      path,
      'option:' + optKey,
      optVal,
      fallbackElement
    );
  } else if (field === 'editWidget' || field === 'editClass') {
    const isEditConfig =
      parent && ['edit', 'edit_definition'].includes(parent.tagName);
    const tagName = isEditConfig ? 'display' : 'edit';
    let editNode = [...node.children].find(
      (child) => child.tagName === tagName
    );
    if (!editNode) {
      editNode = document.createElement(tagName);
      node.appendChild(editNode);
    }
    editNode.removeAttribute('widget');
    editNode.removeAttribute('class');
    const widget = String(value || '').trim();
    if (widget)
      editNode.setAttribute(
        field === 'editClass' || widget.includes('.') || widget.endsWith('Wdg')
          ? 'class'
          : 'widget',
        widget
      );
  } else if (field.startsWith('editOption:')) {
    const optKey = field.slice(11).trim();
    if (!optKey || !/^[\w:.-]+$/.test(optKey))
      throw new Error('Invalid edit option name');
    const isEditConfig =
      parent && ['edit', 'edit_definition'].includes(parent.tagName);
    const tagName = isEditConfig ? 'display' : 'edit';
    let editNode = [...node.children].find(
      (child) => child.tagName === tagName
    );
    if (!editNode) {
      editNode = document.createElement(tagName);
      if (fallbackElement?.editWidget) {
        const w = fallbackElement.editWidget;
        editNode.setAttribute(
          w.includes('.') || w.endsWith('Wdg') ? 'class' : 'widget',
          w
        );
      }
      node.appendChild(editNode);
    }
    ensureChildOption(editNode, document, optKey, value);
  } else if (field === 'actionClass') {
    let actionNode = [...node.children].find(
      (child) => child.tagName === 'action'
    );
    const cls = String(value || '').trim();
    if (!cls) {
      if (actionNode && !actionNode.children.length)
        node.removeChild(actionNode);
      else if (actionNode) actionNode.removeAttribute('class');
    } else {
      if (!actionNode) {
        actionNode = document.createElement('action');
        node.appendChild(actionNode);
      }
      actionNode.setAttribute('class', cls);
    }
  } else if (field.startsWith('actionOption:')) {
    const optKey = field.slice(13).trim();
    if (!optKey || !/^[\w:.-]+$/.test(optKey))
      throw new Error('Invalid action option name');
    let actionNode = [...node.children].find(
      (child) => child.tagName === 'action'
    );
    if (!actionNode) {
      actionNode = document.createElement('action');
      node.appendChild(actionNode);
    }
    ensureChildOption(actionNode, document, optKey, value);
  } else if (field === 'xml') {
    const snippet = String(value || '').trim();
    if (!snippet) throw new Error('Invalid configuration XML');
    const parsed = parse(snippet).documentElement;
    if (
      parsed.tagName !== 'element' ||
      !(parsed.getAttribute('name') || '').trim() ||
      !parent
    )
      throw new Error('Invalid configuration XML');
    parent.replaceChild(document.importNode(parsed, true), node);
  } else throw new Error('This column setting is only available in XML mode.');
  return new XMLSerializer().serializeToString(document);
}
