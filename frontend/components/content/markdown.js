const escapeHtml = (value) => String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');

const renderInline = (value) => {
    const code = [];
    let html = escapeHtml(value).replace(/`([^`]+)`/g, (_, content) => {
        const token = `@@ARKAN_CODE_${code.length}@@`;
        code.push(`<code class="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[0.9em] text-cyan-200">${content}</code>`);
        return token;
    });
    html = html
        .replace(/\[([^\]]+)]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-cyan-400 underline decoration-cyan-700 underline-offset-2 hover:text-cyan-300">$1</a>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/__([^_]+)__/g, '<strong>$1</strong>')
        .replace(/~~([^~]+)~~/g, '<del>$1</del>')
        .replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>')
        .replace(/(?<!_)_([^_]+)_(?!_)/g, '<em>$1</em>');
    return html.replace(/@@ARKAN_CODE_(\d+)@@/g, (_, index) => code[Number(index)] ?? '');
};

/** Renderiza apenas o subconjunto Markdown suportado, sem aceitar HTML do conteúdo. */
export const renderMarkdown = (value) => {
    const lines = String(value ?? '').replaceAll('\r\n', '\n').split('\n');
    const output = [];
    let paragraph = [];
    let listType = null;
    let quote = [];
    let codeLines = null;
    const flushParagraph = () => {
        if (paragraph.length) output.push(`<p class="my-3">${paragraph.join('<br>')}</p>`);
        paragraph = [];
    };
    const closeList = () => {
        if (listType) output.push(`</${listType}>`);
        listType = null;
    };
    const flushQuote = () => {
        if (quote.length) output.push(`<blockquote class="my-4 border-l-4 border-cyan-800 pl-4 text-slate-300">${quote.map(renderInline).join('<br>')}</blockquote>`);
        quote = [];
    };

    for (const line of lines) {
        if (codeLines) {
            if (/^```\s*$/.test(line)) {
                output.push(`<pre class="my-4 overflow-x-auto rounded-xl bg-slate-950 p-4 text-sm leading-6 text-slate-200"><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`);
                codeLines = null;
            } else codeLines.push(line);
            continue;
        }
        if (/^```\s*$/.test(line)) {
            flushParagraph(); closeList(); flushQuote(); codeLines = [];
            continue;
        }
        const heading = line.match(/^(#{1,6})\s+(.+)$/);
        const unordered = line.match(/^[-*+]\s+(.+)$/);
        const ordered = line.match(/^\d+[.)]\s+(.+)$/);
        const quoted = line.match(/^>\s?(.*)$/);
        if (!line.trim()) { flushParagraph(); closeList(); flushQuote(); continue; }
        if (heading) {
            flushParagraph(); closeList(); flushQuote();
            const level = heading[1].length;
            const sizes = ['text-2xl', 'text-xl', 'text-lg', 'text-base', 'text-sm', 'text-sm'];
            output.push(`<h${level} class="mt-6 mb-3 font-bold ${sizes[level - 1]} text-slate-100">${renderInline(heading[2])}</h${level}>`);
            continue;
        }
        if (/^(---|\*\*\*|___)\s*$/.test(line)) { flushParagraph(); closeList(); flushQuote(); output.push('<hr class="my-5 border-slate-700">'); continue; }
        if (quoted) { flushParagraph(); closeList(); quote.push(quoted[1]); continue; }
        flushQuote();
        if (unordered || ordered) {
            flushParagraph();
            const wanted = unordered ? 'ul' : 'ol';
            if (listType && listType !== wanted) closeList();
            if (!listType) { output.push(`<${wanted} class="my-3 ${wanted === 'ul' ? 'list-disc' : 'list-decimal'} space-y-1 pl-6">`); listType = wanted; }
            output.push(`<li>${renderInline((unordered || ordered)[1])}</li>`);
            continue;
        }
        closeList();
        paragraph.push(renderInline(line));
    }
    if (codeLines) output.push(`<pre class="my-4 overflow-x-auto rounded-xl bg-slate-950 p-4 text-sm leading-6 text-slate-200"><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`);
    flushParagraph(); closeList(); flushQuote();
    return output.join('');
};
