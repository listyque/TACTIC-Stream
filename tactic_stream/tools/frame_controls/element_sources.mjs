// Read-only source census; use the installed compilers rather than parsing HTML with regex.
import { readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import assert from 'node:assert/strict';

const require = createRequire(
  new URL('../../frontend/package.json', import.meta.url)
);
const { parse: sfc } = require('@vue/compiler-sfc');
const { parse: template } = require('@vue/compiler-dom');
const { parse: script } = require('@babel/parser');
const postcss = require('postcss');
const root = path.resolve(process.argv[2]);
const files = [],
  uses = [],
  styles = [];
const relative = (file) => path.relative(root, file).replaceAll('\\', '/');

function walkFiles(directory, extensions) {
  return readdirSync(directory, { withFileTypes: true })
    .flatMap((entry) => {
      const file = path.join(directory, entry.name);
      return entry.isDirectory()
        ? walkFiles(file, extensions)
        : extensions.includes(path.extname(file))
          ? [file]
          : [];
    })
    .sort();
}

function elements(source) {
  const result = [];
  function visit(node, parent = '') {
    if (node.type === 1) {
      result.push({
        tag: node.tag,
        parent,
        line: node.loc.start.line,
        props: Object.fromEntries(
          node.props.map((prop) =>
            prop.type === 6
              ? [prop.name, prop.value?.content || '']
              : [
                  (prop.name === 'bind' ? ':' : '@' + prop.name + ':') +
                    (prop.arg?.content || ''),
                  prop.exp?.content || ''
                ]
          )
        )
      });
      parent = node.tag;
    }
    for (const child of node.children || []) visit(child, parent);
  }
  visit(template(source));
  return result;
}

function css(source, file, offset = 0) {
  postcss.parse(source, { from: file }).walkRules((rule) => {
    const declarations = {};
    rule.each((node) => {
      if (
        node.type === 'decl' &&
        /(?:width|height|padding|margin|gap|radius|font|line-height|color|background|align|display|overflow|outline|border)/.test(
          node.prop
        )
      )
        declarations[node.prop] = node.value;
    });
    if (!Object.keys(declarations).length) return;
    const conditions = [];
    for (let owner = rule.parent; owner; owner = owner.parent)
      if (owner.type === 'atrule')
        conditions.push('@' + owner.name + ' ' + owner.params);
    styles.push({
      file,
      line: rule.source.start.line + offset,
      tag: rule.selector,
      props: declarations,
      parent: conditions.join(' / ')
    });
  });
}

assert.deepEqual(
  elements(
    '<!-- <Bogus/> --><AppButton :disabled="count > 1"><span>x</span></AppButton>'
  ).map((row) => row.tag),
  ['AppButton', 'span']
);
assert.equal(
  elements('<input :value="a > b ? a : b"/>')[0].props[':value'],
  'a > b ? a : b'
);

for (const target of walkFiles(path.join(root, 'frontend/src'), [
  '.vue',
  '.css'
])) {
  const source = readFileSync(target, 'utf8'),
    file = relative(target);
  if (target.endsWith('.css')) {
    files.push({ file, kind: 'style', name: path.basename(target) });
    css(source, file);
    continue;
  }
  const { descriptor, errors } = sfc(source, { filename: target });
  assert.equal(errors.length, 0, `${file}: ${errors}`);
  const imports = {};
  for (const block of [descriptor.script, descriptor.scriptSetup].filter(
    Boolean
  )) {
    const ast = script(block.content, {
      sourceType: 'module',
      plugins: block.lang === 'ts' ? ['typescript'] : []
    });
    for (const item of ast.program.body.filter(
      (node) => node.type === 'ImportDeclaration'
    )) {
      for (const binding of item.specifiers) {
        imports[binding.local.name] = item.source.value.startsWith('.')
          ? relative(path.resolve(path.dirname(target), item.source.value))
          : item.source.value;
      }
    }
  }
  files.push({
    file,
    kind: 'component',
    name: path.basename(target, '.vue'),
    imports
  });
  if (descriptor.template) {
    for (const row of elements(descriptor.template.content))
      uses.push({
        ...row,
        file,
        line: row.line + descriptor.template.loc.start.line - 1,
        resolved: imports[row.tag] || ''
      });
  }
  for (const block of descriptor.styles)
    css(block.content, file, block.loc.start.line - 1);
}

// Helpers are infrastructure, not extra visual controls. Include all twenty house helpers.
for (const target of walkFiles(path.join(root, 'frontend/src/controls'), [
  '.js'
]))
  files.push({
    file: relative(target),
    name: path.basename(target),
    kind: 'helper'
  });

const frames = [];
function walkAst(node, visit) {
  if (!node || typeof node !== 'object') return;
  if (node.type) visit(node);
  for (const [key, value] of Object.entries(node)) {
    if (['loc', 'start', 'end', 'extra', 'comments', 'tokens'].includes(key))
      continue;
    if (Array.isArray(value)) value.forEach((child) => walkAst(child, visit));
    else if (value && typeof value === 'object') walkAst(value, visit);
  }
}
for (const target of walkFiles(path.join(root, 'src/tactic_stream/shared_ui'), [
  '.mjs'
])) {
  const source = readFileSync(target, 'utf8'),
    file = relative(target);
  const ast = script(source, { sourceType: 'module' });
  const builders = new Map();
  for (const item of ast.program.body.filter(
    (node) =>
      node.type === 'ImportDeclaration' &&
      node.source.value.endsWith('/frame.mjs')
  ))
    for (const binding of item.specifiers)
      if (binding.type === 'ImportSpecifier')
        builders.set(binding.local.name, binding.imported.name);
  files.push({ file, name: path.basename(target), kind: 'frame-module' });
  walkAst(ast, (node) => {
    if (
      node.type !== 'CallExpression' ||
      node.callee.type !== 'Identifier' ||
      !builders.has(node.callee.name)
    )
      return;
    const builder = builders.get(node.callee.name);
    if (!['node', 'button', 'label', 'rect'].includes(builder)) return;
    const first = node.arguments[0];
    frames.push({
      file,
      line: node.loc.start.line,
      tag: builder === 'node' ? first?.value || 'computed-kind' : builder,
      parent: 'Frame builder',
      props: {
        declaration: source.slice(
          node.start,
          Math.min(node.end, node.start + 260)
        )
      },
      resolved: 'core/frame.mjs'
    });
  });
}
process.stdout.write(JSON.stringify({ files, uses, styles, frames }));
