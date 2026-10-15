// Handler RulesDocument and security_matrix native-key projection.
export const access = {
  deny: 0,
  false: 0,
  view: 1,
  true: 1,
  edit: 2,
  insert: 3,
  retire: 4,
  delete: 5,
  allow: 5
};
export const matrixScopes = [
  'project',
  'link',
  'gear_menu',
  'search_type',
  'process',
  'tasks'
];
const meta = new Set(['group', 'category', 'access', 'project', 'ruleIndex']);

export function parseRules(xml) {
  if (/<!DOCTYPE|<!ENTITY/i.test(xml))
    throw new Error('Document types and XML entities are not supported');
  const root = new DOMParser().parseFromString(
    xml,
    'application/xml'
  ).documentElement;
  if (root.localName === 'parsererror' || root.querySelector('parsererror'))
    throw new Error('Access rules XML is not well formed.');
  if (root.tagName !== 'rules')
    throw new Error('Access rules must have a rules root');
  return root;
}
export function rules(xml) {
  return [...parseRules(xml).children]
    .filter((node) => node.tagName === 'rule')
    .map((node, ruleIndex) => ({
      ...Object.fromEntries(
        [...node.attributes].map((attr) => [attr.name, attr.value])
      ),
      ruleIndex
    }));
}
export function restoreOriginalXml(original, current) {
  if (!original) return current;
  const serializer = new XMLSerializer();
  return serializer.serializeToString(parseRules(original)) ===
    serializer.serializeToString(parseRules(current))
    ? original
    : current;
}
export function changeRule(xml, index, attributes = null) {
  const root = parseRules(xml),
    nodes = [...root.children].filter((node) => node.tagName === 'rule');
  if (attributes === null) {
    nodes[index]?.remove();
    return new XMLSerializer().serializeToString(root);
  }
  if (!Object.values(attributes).every((value) => typeof value === 'string'))
    throw new Error('Attributes must be a JSON object with string values');
  const scope = attributes.group || attributes.category;
  if (!scope) throw new Error('Enter a security scope');
  if (
    !(scope === 'search_filter' && !Object.hasOwn(attributes, 'access')) &&
    !Object.hasOwn(access, attributes.access)
  )
    throw new Error('Select a valid access level');
  const node =
    index === -1
      ? root.appendChild(root.ownerDocument.createElement('rule'))
      : nodes[index];
  if (!node) throw new Error('Select an access rule');
  for (const attr of [...node.attributes]) node.removeAttribute(attr.name);
  for (const [name, value] of Object.entries(attributes))
    node.setAttribute(name, value);
  return new XMLSerializer().serializeToString(root);
}
function key(scope, attrs, project = '*') {
  return JSON.stringify([
    scope,
    Object.entries(attrs)
      .filter(([name]) => !meta.has(name))
      .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)),
    scope === 'project' ? '*' : project || '*'
  ]);
}
function lookupKeys(scope, attributes, project) {
  const attrs = Object.fromEntries(
    Object.entries(attributes).filter(([name]) => name !== 'project')
  );
  const wildcard = Object.fromEntries(
    Object.keys(attrs).map((name) => [name, '*'])
  );
  if (scope === 'project') return [key(scope, attrs), key(scope, wildcard)];
  if (scope === 'tasks')
    return [
      key('process', { process: '*', pipeline: attrs.pipeline }),
      key('process', wildcard),
      key('process', attrs)
    ];
  if (scope === 'gear_menu')
    return [key(scope, wildcard, project), key(scope, attrs, project)];
  if (scope === 'search_type')
    return [
      key(scope, attrs),
      key(scope, attrs, project),
      key(scope, wildcard),
      key(scope, wildcard, project)
    ];
  return [
    key(scope, attrs, project),
    key(scope, attrs),
    key(scope, wildcard, project),
    key(scope, wildcard)
  ];
}
function compile(document, metadata, identity, omit = []) {
  const result = new Map(),
    visited = new Set(),
    names = new Map(
      metadata.groups.map((group) => [group.label, group.identity])
    );
  function add(records, bound) {
    for (const record of records) {
      const scope = record.group || record.category;
      if (Object.hasOwn(access, record.default)) {
        result.set(JSON.stringify([scope, [], '__DEFAULT__']), record.default);
        continue;
      }
      if (!Object.hasOwn(access, record.access)) continue;
      const identity = key(scope, record, bound || record.project || '*');
      if (
        access[result.get(identity)] === undefined ||
        access[result.get(identity)] < access[record.access]
      )
        result.set(identity, record.access);
    }
  }
  function collect(code) {
    if (visited.has(code) || !document.groups[code]) return;
    visited.add(code);
    const group = document.groups[code];
    add(
      rules(group.xml).filter(
        (record) => code !== identity || !omit.includes(record.ruleIndex)
      ),
      group.project
    );
    let defaults = rules(
      metadata.globalDefaultRulesByLevel[group.accessLevel] || '<rules/>'
    );
    if (group.project) {
      defaults = defaults.filter(
        (record) => (record.group || record.category) !== 'project'
      );
      defaults.push({ group: 'project', code: group.project, access: 'allow' });
    }
    add(defaults, group.project);
    for (const name of group.subGroups.split('|')) {
      if (name === 'admin') result.set(key('__admin__', {}), 'allow');
      else if (names.has(name)) collect(names.get(name));
    }
  }
  collect(identity);
  return result;
}
function resolve(index, keys) {
  if (index.has(key('__admin__', {}))) return 'allow';
  for (const identity of keys) {
    const [scope, attrs, project] = JSON.parse(identity);
    const values = index.has(identity) ? [index.get(identity)] : [];
    const global = JSON.stringify([scope, attrs, '*']);
    if (scope !== 'project' && project !== '*' && index.has(global))
      values.push(index.get(global));
    if (values.length)
      return values.reduce((a, b) => (access[a] >= access[b] ? a : b));
  }
  return keys.length
    ? index.get(
        JSON.stringify([JSON.parse(keys.at(-1))[0], [], '__DEFAULT__'])
      ) || 'deny'
    : 'deny';
}
export function matrix(document, metadata, scope, project, targets, groups) {
  return groups.map((group) => {
    const identity = group.identity,
      settings = document.groups[identity],
      index = compile(document, metadata, identity);
    const records = rules(settings.xml);
    return targets.map((target) => {
      const nativeScope = scope === 'tasks' ? 'process' : scope,
        bound = settings.project;
      const targetKey = key(
        nativeScope,
        target.attributes,
        bound || target.attributes.project || '*'
      );
      const exact = records.filter(
        (record) =>
          key(
            record.group || record.category,
            record,
            bound || record.project || '*'
          ) === targetKey
      );
      const keys = lookupKeys(scope, target.attributes, project),
        level = resolve(index, keys);
      const custom = exact.some(
        (record) => !['allow', 'deny', 'false'].includes(record.access)
      );
      const baseline = exact.length
        ? compile(
            document,
            metadata,
            identity,
            exact.map((record) => record.ruleIndex)
          )
        : index;
      const proposed = new Map(baseline),
        desired = access[level] > 0 ? 'deny' : 'allow';
      proposed.set(
        targetKey,
        access[baseline.get(targetKey) || 'deny'] > access[desired]
          ? baseline.get(targetKey)
          : desired
      );
      return {
        group: identity,
        checked: access[level] > 0,
        inherited: !exact.length,
        explicit: !!exact.length,
        custom,
        access: level,
        locked:
          custom ||
          !!(bound && bound !== project && nativeScope !== 'project') ||
          access[resolve(proposed, keys)] > 0 === access[level] > 0,
        ruleIndices: exact.map((record) => record.ruleIndex)
      };
    });
  });
}
