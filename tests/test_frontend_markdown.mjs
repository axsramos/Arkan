import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { renderMarkdown } from '../frontend/components/content/markdown.js';

const formatted = renderMarkdown('## Título\n\n**forte** e *ênfase*\n\n- Primeiro\n- Segundo\n\n[Site](https://example.com)');
assert.match(formatted, /<h2/);
assert.match(formatted, /<strong>forte<\/strong>/);
assert.match(formatted, /<em>ênfase<\/em>/);
assert.match(formatted, /<ul/);
assert.match(formatted, /rel="noopener noreferrer"/);

const untrusted = renderMarkdown('<img src=x onerror=alert(1)>\n\n[Arquivo](javascript:alert(1))');
assert.doesNotMatch(untrusted, /<img/);
assert.match(untrusted, /&lt;img/);
assert.doesNotMatch(untrusted, /href="javascript:/);

const indexHtml = await readFile(new URL('../frontend/index.html', import.meta.url), 'utf8');
assert.match(
  indexHtml,
  /\.theme-light \[class~="bg-slate-950"\],\.theme-light \[class~="bg-slate-950\/50"\]\{background-color:#f4f3ec!important\}/,
  'O tema claro deve aplicar um fundo claro ao painel de comentários do Acervo.',
);

console.log('Markdown do frontend validado.');
