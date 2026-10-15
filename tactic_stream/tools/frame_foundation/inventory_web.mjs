import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(
  new URL('../../frontend/package.json', import.meta.url)
);
const { parse: parseSfc } = require('@vue/compiler-sfc');
const { parse: parseTemplate } = require('@vue/compiler-dom');
const { parse: parseScript } = require('@babel/parser');

const root = path.resolve(process.argv[2]);
const files = [];
const surfaces = [];
const dynamic = [];
async function scan(directory) {
  for (const item of await readdir(directory, { withFileTypes: true })) {
    const target = path.join(directory, item.name);
    if (item.isDirectory()) await scan(target);
    else if (item.name.endsWith('.vue')) {
      const source = await readFile(target, 'utf8');
      const { descriptor, errors } = parseSfc(source, { filename: target });
      if (errors.length) throw Error(errors.join('\n'));
      const file = path.relative(root, target).replaceAll('\\', '/');
      files.push({
        file,
        frameView: /<FrameView\b/.test(source),
        sharedRules: source.includes('shared_ui/')
      });
      if (!descriptor.template) continue;
      const offset = source.indexOf(
        descriptor.template.content,
        descriptor.template.loc.start.offset
      );
      function walk(node) {
        if (node.type === 1) {
          if (
            node.tag === 'component' ||
            node.props.some((prop) => prop.type === 7 && prop.name === 'html')
          )
            dynamic.push({
              file,
              line: source.slice(0, offset + node.loc.start.offset).split('\n')
                .length,
              type: 'dynamic-component/content',
              entry: node.tag
            });
          const window = node.props.find(
            (prop) => prop.type === 7 && prop.name === 'window'
          );
          const popover = node.props.find((prop) => prop.name === 'popover');
          if (
            node.tag === 'dialog' ||
            window ||
            popover ||
            /(?:Menu|Popup|Popover|Dialog)$/.test(node.tag)
          ) {
            const expression = window?.exp?.content || '';
            const kind =
              expression.match(/\bkind:\s*['"]([^'"]+)['"]/)?.[1] || null;
            const name =
              node.props.find(
                (prop) => prop.type === 6 && ['id', 'ref'].includes(prop.name)
              )?.value?.content || '';
            surfaces.push({
              file,
              line: source.slice(0, offset + node.loc.start.offset).split('\n')
                .length,
              type: window
                ? 'window-directive'
                : node.tag === 'dialog'
                  ? 'dialog'
                  : 'menu/popover',
              tag: node.tag,
              name,
              kind
            });
          }
        }
        for (const child of node.children || []) walk(child);
      }
      walk(parseTemplate(descriptor.template.content));
    }
  }
}
await scan(path.join(root, 'frontend/src'));
const dockFile = 'frontend/src/features/workspace/docks.js';
const dockModule = parseScript(
  await readFile(path.join(root, dockFile), 'utf8'),
  { sourceType: 'module' }
);
const declaration = dockModule.program.body.find(
  (statement) =>
    statement.type === 'ExportNamedDeclaration' &&
    statement.declaration?.declarations?.some(
      (variable) => variable.id.name === 'dockPanels'
    )
);
const catalog = declaration.declaration.declarations.find(
  (variable) => variable.id.name === 'dockPanels'
).init;
const docks = catalog.elements.map((record) => ({
  ...Object.fromEntries(
    record.properties.map((property) => {
      if (!['StringLiteral', 'BooleanLiteral'].includes(property.value.type))
        throw Error('Unsupported dock inventory value');
      return [property.key.name, property.value.value];
    })
  ),
  entry: dockFile,
  line: record.loc.start.line
}));
process.stdout.write(JSON.stringify({ files, surfaces, docks, dynamic }));
