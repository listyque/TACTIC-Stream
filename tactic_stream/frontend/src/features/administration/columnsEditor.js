// Handler catalog_wizard / update_catalog_wizard and tactic_definition helpers.
export const displayWidgets = [
  ['', 'Automatic'],
  ['format', 'Format'],
  ['expression', 'Expression'],
  ['link', 'Link'],
  ['pyasm.widget.ThumbWdg', 'Thumbnail'],
  ['tactic.ui.widget.DiscussionElementWdg', 'Notes'],
  ['tactic.ui.table.SObjectDetailElementWdg', 'SObject details'],
  ['tactic.ui.table.CheckinButtonElementWdg', 'Check-in'],
  ['tactic.ui.table.TaskElementWdg', 'Tasks'],
  ['tactic.ui.table.TaskCompletionWdg', 'Task completion'],
  ['tactic.ui.table.ExploreElementWdg', 'Explorer'],
  ['tactic.ui.table.SObjectFilesElementWdg', 'Files'],
  ['tactic.ui.table.MetadataElementWdg', 'Metadata'],
  ['tactic.ui.table.DeleteElementWdg', 'Delete']
].map(([value, label]) => ({ value, label }));

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

export function tableDefinition(configuration) {
  const source =
    configuration.sources[0]?.xml ||
    configuration.layers.find((layer) => layer.view === configuration.view)
      ?.xml;
  const document = source ? parse(source) : parse('<config/>');
  const root = document.documentElement;
  let view =
    root.tagName === configuration.view
      ? root
      : [...root.children].find((node) => node.tagName === configuration.view);
  if (!view) {
    view = document.createElement(configuration.view);
    view.setAttribute('layout', 'TableLayoutWdg');
    root.appendChild(view);
  }
  // A generated table may inherit its entire list; materialize references only.
  if (![...view.children].some((node) => node.tagName === 'element'))
    for (const element of configuration.resolved.elements) {
      const node = document.createElement('element');
      node.setAttribute('name', element.name);
      for (const [key, value] of Object.entries(element.attributes || {}))
        node.setAttribute(key, String(value));
      view.appendChild(node);
    }
  return new XMLSerializer().serializeToString(document);
}

export function changeTable(source, viewName, action, name, value) {
  const document = parse(source),
    root = document.documentElement;
  const view =
    root.tagName === viewName
      ? root
      : [...root.children].find((node) => node.tagName === viewName);
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

export function definitionWizard(source) {
  const root = parse(source).documentElement;
  let view = null,
    viewPath = '';
  function find(node, path = '') {
    if (node.nodeType !== 1 || view) return;
    if (
      ['table', 'definition', 'edit', 'edit_definition'].includes(
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
  const elements = view
    ? children(view).flatMap((node, index) => {
        if (node.nodeType !== 1 || node.tagName !== 'element') return [];
        const display = [...node.children].find(
            (child) => child.tagName === 'display'
          ),
          name = node.getAttribute('name') || '';
        return [
          {
            path: viewPath ? `${viewPath}/${index}` : String(index),
            name,
            title: node.getAttribute('title') || name,
            visible: !flag(node.getAttribute('hidden')),
            width: width(node.getAttribute('width')),
            widget:
              display?.getAttribute('class') ||
              display?.getAttribute('widget') ||
              ''
          }
        ];
      })
    : [];
  return {
    supported: !!view,
    view: view?.tagName || '',
    layout: view?.getAttribute('layout') || '',
    elements
  };
}

export function changeDefinition(source, path, field, value) {
  const document = parse(source);
  let node = document.documentElement;
  for (const part of path.split('/').filter(Boolean)) {
    if (!/^\d+$/.test(part) || !children(node)[Number(part)])
      throw new Error('Definition XML path no longer exists.');
    node = children(node)[Number(part)];
  }
  if (node.tagName !== 'element')
    throw new Error('Definition XML path no longer points to a column.');
  if (field === 'title') {
    if (!String(value).trim()) throw new Error('Column label cannot be empty.');
    node.setAttribute('title', String(value).trim());
  } else if (field === 'visible')
    node.setAttribute('hidden', value ? 'false' : 'true');
  else if (field === 'width') node.setAttribute('width', String(width(value)));
  else if (field === 'widget') {
    let display = [...node.children].find(
      (child) => child.tagName === 'display'
    );
    if (!display) {
      display = document.createElement('display');
      node.appendChild(display);
    }
    display.removeAttribute('widget');
    display.removeAttribute('class');
    const widget = String(value || '').trim();
    if (widget)
      display.setAttribute(
        widget.includes('.') || widget.endsWith('Wdg') ? 'class' : 'widget',
        widget
      );
  } else throw new Error('This column setting is only available in XML mode.');
  return new XMLSerializer().serializeToString(document);
}
