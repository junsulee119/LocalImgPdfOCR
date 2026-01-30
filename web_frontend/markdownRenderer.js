// Markdown Rendering Module
// Handles conversion of Markdown to HTML with support for:
// - Math (KaTeX via placeholders)
// - Images (resolving relative paths to backend API)
// - Tables (HTML and Markdown style)
// - Custom tags (<user>, etc.)
// - Formatting (headers, bold, italic with serif font)

/**
 * Renders Markdown to HTML
 * @param {string} md - The markdown content
 * @param {string} jobId - The job ID for resolving relative image paths
 * @param {string} [baseUrl] - Optional base URL for API (default: http://localhost:8000/api)
 * @returns {string} The rendered HTML
 */
function renderMarkdown(md, jobId) {
    if (!md) return '<p style="color:var(--muted);">내용이 없습니다.</p>';

    let html = md;

    // Preserve math blocks ($$...$$ and $...$) by replacing with placeholders
    const mathBlocks = [];
    // Match block math: $$...$$ (multiline, non-greedy)
    html = html.replace(/\$\$([\s\S]+?)\$\$/g, (match) => {
        mathBlocks.push({ type: 'block', content: match });
        return `@@@MATHBLOCK${mathBlocks.length - 1}@@@`;
    });
    // Match inline math: $...$ (no newlines, non-greedy)
    html = html.replace(/\$([^\$\n]+?)\$/g, (match) => {
        mathBlocks.push({ type: 'inline', content: match });
        return `@@@MATHINLINE${mathBlocks.length - 1}@@@`;
    });

    // Handle images FIRST: ![alt](src) and replace with placeholders to protect URLs from italics
    const images = [];
    html = html.replace(/!\[(.*?)\]\((.*?)\)/g, (match, alt, src) => {
        let fullSrc = src;

        // If it's a relative path (not starting with http/https), prepend backend API
        if (jobId && !src.startsWith('http') && !src.startsWith('//')) {
            fullSrc = `http://localhost:8000/api/jobs/${jobId}/results/${src}`;
        } else if (!jobId && !src.startsWith('http')) {
            console.warn('renderMarkdown: Missing jobId for relative image path', src);
        }

        const imgTag = `<img src="${fullSrc}" alt="${alt}" style="max-width:100%;margin:12px 0;border-radius:4px;box-shadow:0 4px 6px rgba(0,0,0,0.1);">`;
        images.push(imgTag);
        return `@@@IMAGE${images.length - 1}@@@`;
    });

    // Preserve HTML tables by replacing with placeholders
    const htmlTables = [];
    html = html.replace(/<table[\s\S]*?<\/table>/gi, (match) => {
        htmlTables.push(match);
        return `@@@HTMLTABLE${htmlTables.length - 1}@@@`;
    });

    // Convert markdown tables (|...|)
    html = html.replace(/\n\|(.+)\|\n\|[-:\s|]+\|\n((?:\|.+\|\n?)+)/g, (match, header, rows) => {
        const headers = header.split('|').map(h => h.trim()).filter(h => h);
        const rowData = rows.trim().split('\n').map(row =>
            row.split('|').map(cell => cell.trim()).filter(cell => cell)
        );

        let table = '<table style="border-collapse: collapse; margin: 16px 0; width: 100%;">';
        table += '<thead><tr>';
        headers.forEach(h => {
            table += `<th style="border: 1px solid #555; padding: 8px; background: rgba(255,255,255,0.1);">${h}</th>`;
        });
        table += '</tr></thead><tbody>';
        rowData.forEach(row => {
            table += '<tr>';
            row.forEach(cell => {
                table += `<td style="border: 1px solid #555; padding: 8px;">${cell}</td>`;
            });
            table += '</tr>';
        });
        table += '</tbody></table>';
        return '\n' + table + '\n';
    });

    // Headers, code, formatting
    html = html
        .replace(/^#### (.*$)/gim, '<h4>$1</h4>')
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        .replace(/^---$/gim, '<hr style="border:0; border-top:1px solid var(--line); margin: 20px 0;">')
        .replace(/```([^`]+)```/g, (match, code) => {
            const escaped = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            return `<pre style="background: rgba(0,0,0,0.3); padding: 12px; border-radius: 6px; overflow-x: auto;"><code>${escaped}</code></pre>`;
        })
        .replace(/`([^`]+)`/g, (match, code) => {
            const escaped = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            return `<code style="background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 3px;">${escaped}</code>`;
        })
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/__([^_]+?)__/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Italics: _text_, requiring boundaries to avoid matching mid-word
        // Use .math-italic class relying on CSS
        .replace(/(^|[^\w])_([^_]+)_(?=[^\w]|$)/g, '$1<em class="math-italic">$2</em>')
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" style="color: #66ccff;">$1</a>')

        // Escape unknown tags (like <user>) so they show up as text
        // Exceptions: standard tags + img/br/hr/pre/code/sup/sub
        // Added negative lookbehind (?<!\\) so "\<tag>" is IGNORED here and handled by unescape step
        .replace(/(?<!\\)<(?!\/?(h1|h2|h3|h4|h5|h6|p|div|span|table|thead|tbody|tr|th|td|ul|ol|li|strong|em|b|i|u|img|a|code|pre|br|hr|sup|sub)\b)([^>]+)>/gi, '&lt;$2&gt;')

        // Unescape standard markdown escapes
        // Added < and > to supported escapes so "\<user\>" becomes "&lt;user&gt;" (visual <user>)
        .replace(/\\([\\`*{}\[\]()#+\-.!_><])/g, (match, char) => {
            if (char === '<') return '&lt;';
            if (char === '>') return '&gt;';
            return char;
        })

        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');

    // Restore images
    images.forEach((img, i) => {
        html = html.replace(`@@@IMAGE${i}@@@`, img);
    });

    // Restore HTML tables
    htmlTables.forEach((table, i) => {
        html = html.replace(`@@@HTMLTABLE${i}@@@`, table);
    });

    // Restore math blocks (KaTeX will render these later)
    mathBlocks.forEach((math, i) => {
        if (math.type === 'block') {
            html = html.replace(`@@@MATHBLOCK${i}@@@`, math.content);
        } else {
            html = html.replace(`@@@MATHINLINE${i}@@@`, math.content);
        }
    });

    return '<div class="markdown-content"><p>' + html + '</p></div>';
}
