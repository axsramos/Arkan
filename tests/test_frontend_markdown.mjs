import assert from 'node:assert/strict';
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

console.log('Markdown do frontend validado.');
