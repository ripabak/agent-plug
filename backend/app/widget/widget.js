/**
 * Agent-Plug Widget — self-contained floating chat bot.
 *
 * No build step, no dependencies, no modules. Reads its own <script> tag
 * attributes:
 *   data-agent-id    : agent identifier
 *   data-token       : public token (authentication for widget endpoints)
 *   data-base-url    : backend base URL (defaults to script origin)
 *   data-page-url    : current-page context. Default = window.location.href
 *                      (the agent can read this page via read_current_page).
 *                      Set to a URL to override (SPA routes), or "off" to
 *                      disable sending page context entirely.
 *
 * Optional theming attributes (all of them; defaults keep the legacy look):
 *   data-theme-name  : preset palette name (indigo|emerald|rose|amber|slate|ocean)
 *   data-theme       : JSON object with partial token overrides
 *   data-chat-<token>: single token override, e.g. data-chat-header-bg="#f00"
 *                      (token list mirrors frontend/src/utils/themes.ts)
 *
 * Renders a floating button (bottom-right) that opens a chat panel, and
 * talks to the backend via the public SSE endpoints.
 */
(function () {
  'use strict';

  var script = document.currentScript;
  if (!script) {
    var all = document.querySelectorAll('script[data-agent-id]');
    script = all[all.length - 1];
  }
  if (!script) return;

  var agentId = script.getAttribute('data-agent-id');
  var token = script.getAttribute('data-token');
  var baseUrl = (script.getAttribute('data-base-url') || '').replace(/\/+$/, '');
  if (!agentId || !token || !baseUrl) return;

  // ---------------------------------------------------------------- helpers
  function el(tag, attrs, parent) {
    var node = document.createElement(tag);
    for (var key in attrs || {}) {
      if (key === 'text') node.textContent = attrs[key];
      else if (key === 'html') node.innerHTML = attrs[key];
      else node.setAttribute(key, attrs[key]);
    }
    if (parent) parent.appendChild(node);
    return node;
  }

  function genId() {
    return 'c' + Math.random().toString(36).slice(2) + Date.now().toString(36);
  }

  function apiFetch(path, options) {
    var opts = options || {};
    var headers = Object.assign({ 'X-Agent-Token': token }, opts.headers || {});
    if (opts.body) headers['Content-Type'] = 'application/json';
    return fetch(baseUrl + path, {
      method: opts.method || 'GET',
      headers: headers,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
  }

  // Widget conversations are ephemeral: a fresh thread id per page load
  // means no server-side history is carried over when the page refreshes.
  var threadId =
    'thr_' + Math.random().toString(36).slice(2) + Date.now().toString(36);

  var config = null;
  var streaming = false;
  var assistantEl = null; // current streaming assistant text element
  var assistantBuf = '';
  var assistantThinking = '';
  var sourcesShown = false;
  var currentSources = []; // structured sources from the backend `sources` event
  var currentTools = []; // { callId, name, chip, status }
  var thinkingBlock = null; // <details> element of the streaming message
  var thinkingPre = null;
  var toolsBox = null;

  // Display settings (Thinking / Tools) — come from the agent config fetched
  // via /config (set from the dashboard preview). The widget has no ⚙ menu:
  // everything is configured in the preview panel only.
  var opts = { showThinking: false, showTools: true };

  // ------------------------------------------------------------------ themes
  // Color tokens shared with the dashboard preview
  // (frontend/src/utils/themes.ts + --chat-* defaults in main.css). Keep keys,
  // presets and default values in sync across the three files.
  var THEME_TOKENS = [
    'headerBg', 'headerText', 'msgsBg', 'aiBubbleBg', 'aiBubbleText', 'aiBubbleBorder',
    'userBubbleBg', 'userBubbleText', 'thinkingBg', 'thinkingText', 'thinkingBorder',
    'toolsBg', 'toolsText', 'toolsBorder', 'toolBg', 'btnBg', 'btnText',
    'inputBg', 'inputBorder', 'inputText', 'toolbarBg', 'toolbarBorder',
    'accent', 'accentSoft', 'muted', 'link', 'codeBg', 'preBg', 'preBorder',
    'tableBorder', 'blockquoteText', 'sourcesLabel',
    'toolSuccessText', 'toolSuccessBg', 'toolSuccessBorder',
    'toolErrorText', 'toolErrorBg', 'toolErrorBorder',
    'errBg', 'errText', 'errBorder'
  ];

  var DEFAULT_THEME = {
    headerBg: '#211f1b', headerText: '#f6f5f1', msgsBg: '#f1efe9',
    aiBubbleBg: '#ffffff', aiBubbleText: '#211f1b', aiBubbleBorder: '#e6e3da',
    userBubbleBg: '#211f1b', userBubbleText: '#f6f5f1',
    thinkingBg: '#f6f5f1', thinkingText: '#6f6b64', thinkingBorder: '#e6e3da',
    toolsBg: '#f6f5f1', toolsText: '#211f1b', toolsBorder: '#e6e3da', toolBg: '#ffffff',
    btnBg: '#211f1b', btnText: '#f6f5f1',
    inputBg: '#ffffff', inputBorder: '#d6d2c6', inputText: '#211f1b',
    toolbarBg: '#ffffff', toolbarBorder: '#e6e3da',
    accent: '#a9502a', accentSoft: '#f4e8de', muted: '#6f6b64', link: '#a9502a',
    codeBg: '#f1efe9', preBg: '#f6f5f1', preBorder: '#e6e3da', tableBorder: '#e6e3da',
    blockquoteText: '#45423b', sourcesLabel: '#211f1b',
    toolSuccessText: '#3c5a39', toolSuccessBg: '#edf3ec', toolSuccessBorder: '#cfe0cc',
    toolErrorText: '#a3321f', toolErrorBg: '#fdecec', toolErrorBorder: '#f5d0cc',
    errBg: '#fdecec', errText: '#8d3f1e', errBorder: '#f5d0cc'
  };

  function buildPreset(overrides) {
    var t = {};
    for (var k in DEFAULT_THEME) t[k] = DEFAULT_THEME[k];
    if (overrides) for (var k2 in overrides) t[k2] = overrides[k2];
    return t;
  }

  var THEME_PRESETS = {
    platform: buildPreset({}),
    indigo: buildPreset({ headerBg: '#4f46e5', userBubbleBg: '#4f46e5', btnBg: '#4f46e5', accent: '#4f46e5', accentSoft: '#eef2ff', link: '#2563eb' }),
    emerald: buildPreset({ headerBg: '#059669', userBubbleBg: '#059669', btnBg: '#059669', accent: '#059669', accentSoft: '#d1fae5' }),
    rose: buildPreset({ headerBg: '#e11d48', userBubbleBg: '#e11d48', btnBg: '#e11d48', accent: '#e11d48', accentSoft: '#ffe4e6' }),
    amber: buildPreset({ headerBg: '#d97706', userBubbleBg: '#d97706', btnBg: '#d97706', accent: '#d97706', accentSoft: '#fef3c7' }),
    slate: buildPreset({
      headerBg: '#0f172a', msgsBg: '#1e293b', aiBubbleBg: '#334155', aiBubbleText: '#e2e8f0',
      aiBubbleBorder: '#475569', userBubbleBg: '#0ea5e9', thinkingBg: '#334155', thinkingText: '#94a3b8',
      thinkingBorder: '#475569', toolsBg: '#334155', toolsText: '#cbd5e1', toolsBorder: '#475569',
      toolBg: '#475569', btnBg: '#0ea5e9', inputBg: '#0f172a', inputBorder: '#475569', inputText: '#e2e8f0',
      toolbarBg: '#1e293b', toolbarBorder: '#334155', accent: '#38bdf8', accentSoft: '#0c4a6e',
      muted: '#94a3b8', link: '#38bdf8', codeBg: '#1e293b', preBg: '#1e293b', preBorder: '#334155',
      tableBorder: '#334155', blockquoteText: '#94a3b8', sourcesLabel: '#cbd5e1',
      toolSuccessText: '#4ade80', toolSuccessBg: '#14532d', toolSuccessBorder: '#166534',
      toolErrorText: '#f87171', toolErrorBg: '#7f1d1d', toolErrorBorder: '#b91c1c',
      errBg: '#7f1d1d', errText: '#fecaca', errBorder: '#b91c1c'
    }),
    ocean: buildPreset({ headerBg: '#0d9488', userBubbleBg: '#0d9488', btnBg: '#0d9488', accent: '#0d9488', accentSoft: '#ccfbf1' })
  };

  function tokenToAttr(key) {
    return 'data-chat-' + key.replace(/[A-Z]/g, function (c) { return '-' + c.toLowerCase(); });
  }

  /**
   * Resolve the effective theme from OPTIONAL script attributes and the
   * agent's saved chat config (set from the dashboard preview):
   *   data-theme-name="emerald"          → preset palette
   *   data-theme='{"headerBg":"#f00"}'   → JSON partial overrides
   *   data-chat-header-bg="#f00"         → single-token override
   * Priority: script attributes > agent config chat_theme (from /config) >
   * defaults. Fresh agents are created with chat_theme baked to the
   * `platform` preset, so the platform theme is the default look.
   */
  function resolveTheme() {
    var name = script.getAttribute('data-theme-name');
    var json = script.getAttribute('data-theme');
    var overrides = {};
    if (json) {
      try { overrides = JSON.parse(json) || {}; } catch (e) { overrides = {}; }
    }
    for (var i = 0; i < THEME_TOKENS.length; i++) {
      var v = script.getAttribute(tokenToAttr(THEME_TOKENS[i]));
      if (v) overrides[THEME_TOKENS[i]] = v;
    }
    var hasThemeAttrs = !!name || !!json || Object.keys(overrides).length > 0;

    // Agent-level theme saved from the dashboard preview (/config chat_theme):
    // a JSON {preset, custom, touched} mirroring the frontend ChatThemeState.
    var saved = null;
    if (config && config.chat_theme) {
      try { saved = JSON.parse(config.chat_theme) || null; } catch (e) { saved = null; }
    }

    var base = hasThemeAttrs
      ? (THEME_PRESETS[name] || DEFAULT_THEME)
      : (saved && saved.preset && THEME_PRESETS[saved.preset] ? THEME_PRESETS[saved.preset] : DEFAULT_THEME);
    var theme = {};
    for (var k in base) theme[k] = base[k];
    if (saved && saved.custom) {
      for (var ck in saved.custom) theme[ck] = saved.custom[ck];
    }
    for (var k2 in overrides) theme[k2] = overrides[k2];
    return theme;
  }

  // ------------------------------------------------------------------ state
  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /**
   * Minimal, safe markdown → HTML for assistant messages. Mirrors the
   * dashboard preview (marked + DOMPurify): we escape FIRST, then apply a
   * conservative block/inline pass, so raw HTML can never reach the DOM.
   * Supports what LLMs actually emit: headings, bold/italic, inline + fenced
   * code, links, images (as links), lists, tables, blockquotes, hr, and soft
   * line breaks (GFM `breaks`).
   */
  function mdInline(s) {
    return s
      .replace(/!\[([^\]]*)\]\(([^)\s]+)(?:\s+&quot;[^&]*&quot;)?\)/g, function (m, alt, href) {
        return '<a href="' + href + '" target="_blank" rel="noopener noreferrer">' + (alt || href) + '</a>';
      })
      .replace(/\[([^\]]+)\]\(([^)\s]+)(?:\s+&quot;[^&]*&quot;)?\)/g, function (m, label, href) {
        return '<a href="' + href + '" target="_blank" rel="noopener noreferrer">' + label + '</a>';
      })
      .replace(/(^|[^*])\*\*([^*\n]+)\*\*/g, '$1<strong>$2</strong>')
      .replace(/(^|[^_])__([^_\n]+)__/g, '$1<strong>$2</strong>')
      .replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>')
      .replace(/(^|[^_])_([^_\n]+)_/g, '$1<em>$2</em>')
      .replace(/~~([^~\n]+)~~/g, '<del>$1</del>')
      .replace(/`([^`\n]+)`/g, '<code>$1</code>');
  }

  function markdownToHtml(text) {
    var src = String(text == null ? '' : text);
    if (!src) return '';
    var lines = escapeHtml(src).split('\n');
    var out = [];
    var para = [];
    var i = 0;

    function flushPara() {
      if (!para.length) return;
      out.push('<p>' + mdInline(para.join('<br>')) + '</p>');
      para = [];
    }

    function listItem(line) {
      var m = line.match(/^(\s*)([-*+]|\d+[.)])\s+(.*)$/);
      if (!m) return null;
      return { indent: m[1].length, ordered: /^\d/.test(m[2]), text: m[3] };
    }

    function isTableSep(line) {
      var t = line.replace(/\|/g, '').trim();
      return t.length > 0 && /^[: -]+$/.test(t) && t.indexOf('-') !== -1;
    }

    function splitRow(line) {
      var cells = line.split('|').map(function (c) { return c.trim(); });
      if (cells.length && cells[0] === '') cells.shift();
      if (cells.length && cells[cells.length - 1] === '') cells.pop();
      return cells;
    }

    function cellAlign(sep) {
      if (sep.charAt(0) === ':') return sep.charAt(sep.length - 1) === ':' ? 'center' : 'left';
      return sep.charAt(sep.length - 1) === ':' ? 'right' : '';
    }

    while (i < lines.length) {
      var line = lines[i];

      // fenced code block
      var fm = line.match(/^```\s*([\w.+-]*)\s*$/);
      if (fm) {
        flushPara();
        var code = [];
        i++;
        while (i < lines.length && !/^```/.test(lines[i])) { code.push(lines[i]); i++; }
        i++; // skip closing fence (or EOF)
        out.push('<pre><code' + (fm[1] ? ' class="lang-' + fm[1] + '"' : '') + '>' + code.join('\n') + '</code></pre>');
        continue;
      }

      // horizontal rule
      if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {
        flushPara();
        out.push('<hr>');
        i++;
        continue;
      }

      // ATX headings
      var hm = line.match(/^(#{1,6})\s+(.*)$/);
      if (hm) {
        flushPara();
        var h = hm[1].length;
        out.push('<h' + h + '>' + mdInline(hm[2]) + '</h' + h + '>');
        i++;
        continue;
      }

      // blockquote (escaped `>`)
      if (/^\s*&gt;\s?/.test(line)) {
        flushPara();
        var q = [];
        while (i < lines.length && /^\s*&gt;\s?/.test(lines[i])) {
          q.push(lines[i].replace(/^\s*&gt;\s?/, ''));
          i++;
        }
        out.push('<blockquote>' + mdInline(q.join('<br>')) + '</blockquote>');
        continue;
      }

      // GFM table: header row + separator row
      if (line.indexOf('|') !== -1 && i + 1 < lines.length && isTableSep(lines[i + 1])) {
        flushPara();
        var header = splitRow(line);
        var aligns = splitRow(lines[i + 1]);
        i += 2;
        var body = [];
        while (i < lines.length && lines[i].indexOf('|') !== -1) {
          body.push(splitRow(lines[i]));
          i++;
        }
        out.push('<table><thead><tr>' +
          header.map(function (c, idx) {
            var a = cellAlign(aligns[idx] || '');
            return '<th' + (a ? ' style="text-align:' + a + '"' : '') + '>' + mdInline(c) + '</th>';
          }).join('') + '</tr></thead><tbody>' +
          body.map(function (row) {
            return '<tr>' + row.map(function (c, idx) {
              var a = cellAlign(aligns[idx] || '');
              return '<td' + (a ? ' style="text-align:' + a + '"' : '') + '>' + mdInline(c) + '</td>';
            }).join('') + '</tr>';
          }).join('') + '</tbody></table>');
        continue;
      }

      // lists (same marker/indent runs; deeper nesting keeps browser margins)
      var li = listItem(line);
      if (li) {
        flushPara();
        var items = [];
        while (i < lines.length) {
          var cur = listItem(lines[i]);
          if (!cur || cur.indent !== li.indent || cur.ordered !== li.ordered) break;
          items.push(cur.text);
          i++;
        }
        out.push('<' + (li.ordered ? 'ol' : 'ul') + '>' +
          items.map(function (t) { return '<li>' + mdInline(t) + '</li>'; }).join('') +
          '</' + (li.ordered ? 'ol' : 'ul') + '>');
        continue;
      }

      // blank line → paragraph break
      if (/^\s*$/.test(line)) { flushPara(); i++; continue; }

      para.push(line);
      i++;
    }
    flushPara();
    return out.join('');
  }

  function isValidHttpUrl(value) {
    if (!/^https?:\/\//.test(value)) return false;
    try {
      var parsed = new URL(value);
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return false;
      var host = parsed.hostname;
      if (host.indexOf('://') !== -1 || host.indexOf('/') !== -1) return false;
      return host.indexOf('.') !== -1 && host[0] !== '.' && host[host.length - 1] !== '.';
    } catch (e) {
      return false;
    }
  }

  function isFileSource(value) {
    return value.indexOf('file://') === 0 && value.length > 7 && value.indexOf('/') !== -1 && value.indexOf('..') === -1;
  }

  function isTextSource(value) {
    return value.indexOf('text://') === 0 && value.length > 7;
  }

  function extractSources(text) {
    var re = /\[Source:\s*((?:https?:|file:|text:)\/\/[^\s|\]]+)(?:\s*\|\s*([^\]]*))?\]/g;
    var found = [];
    var m;
    while ((m = re.exec(text)) !== null) {
      var url = m[1];
      if (!isValidHttpUrl(url) && !isFileSource(url) && !isTextSource(url)) continue; // never render mangled URLs as links
      found.push({ url: url, title: (m[2] || url).trim() });
    }
    return found;
  }

  // ---------------------------------------------------------------------- UI
  var uid = 'apw-' + Math.random().toString(36).slice(2, 8);

  function buildStyleText(t) {
    return (      '.' + uid + '-launcher{' +
      'position:fixed;right:24px;bottom:24px;z-index:2147483000;' +
      'width:60px;height:60px;border-radius:50%;border:none;cursor:pointer;' +
      'background:' + t.headerBg + ';color:' + t.headerText + ';font-size:26px;' +
      'box-shadow:0 6px 20px rgba(0,0,0,.25);display:flex;align-items:center;justify-content:center;' +
      'transition:transform .15s ease;' +
      '}' +
      '.' + uid + '-launcher:hover{transform:scale(1.06);}' +
      '.' + uid + '-panel{' +
      'position:fixed;right:24px;bottom:96px;z-index:2147483000;' +
      'width:380px;max-width:calc(100vw - 32px);height:560px;max-height:calc(100vh - 140px);' +
      'background:' + t.aiBubbleBg + ';border-radius:16px;overflow:hidden;display:flex;flex-direction:column;' +
      'box-shadow:0 12px 40px rgba(0,0,0,.28);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;' +
      '}' +
      '.' + uid + '-panel.apw-hidden{display:none;}' +
      '.' + uid + '-header{background:' + t.headerBg + ';color:' + t.headerText + ';padding:12px 16px;display:flex;align-items:center;gap:10px;}' +
      '.' + uid + '-avatar{width:30px;height:30px;border-radius:50%;background:rgba(255,255,255,.22);display:flex;align-items:center;justify-content:center;font-size:16px;flex:none;}' +
      '.' + uid + '-title{font-weight:600;font-size:15px;min-width:0;}' +
      '.' + uid + '-subtitle{font-size:11px;opacity:.85;}' +
      '.' + uid + '-close{background:none;border:none;color:' + t.headerText + ';font-size:18px;cursor:pointer;padding:2px 6px;}' +
      '.' + uid + '-msgs{flex:1;overflow-y:auto;padding:14px;background:' + t.msgsBg + ';display:flex;flex-direction:column;gap:8px;}' +
      '.' + uid + '-msg{max-width:82%;padding:9px 12px;border-radius:14px;font-size:14px;line-height:1.45;word-break:break-word;}' +
      '.' + uid + '-msg.user{align-self:flex-end;background:' + t.userBubbleBg + ';color:' + t.userBubbleText + ';border-bottom-right-radius:4px;white-space:pre-wrap;}' +
      '.' + uid + '-msg.bot{align-self:flex-start;background:' + t.aiBubbleBg + ';color:' + t.aiBubbleText + ';border:1px solid ' + t.aiBubbleBorder + ';border-bottom-left-radius:4px;}' +
      '.' + uid + '-thinking{color:' + t.muted + ';font-style:italic;}' +
      '.' + uid + '-text{word-break:break-word;}' +
      '.' + uid + '-text p{margin:.25em 0;}' +
      '.' + uid + '-text p:first-child{margin-top:0;}' +
      '.' + uid + '-text p:last-child{margin-bottom:0;}' +
      '.' + uid + '-text pre{overflow-x:auto;max-width:100%;margin:.4em 0;padding:.5rem;font-size:.75rem;line-height:1.5;background:' + t.preBg + ';border:1px solid ' + t.preBorder + ';border-radius:6px;}' +
      '.' + uid + '-text code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.85em;background:' + t.codeBg + ';padding:.1em .35em;border-radius:4px;}' +
      '.' + uid + '-text pre code{display:block;background:transparent;padding:0;border:0;font-size:inherit;white-space:pre;}' +
      '.' + uid + '-text a{color:' + t.link + ';text-decoration:underline;text-underline-offset:2px;word-break:break-all;}' +
      '.' + uid + '-text strong{font-weight:700;}' +
      '.' + uid + '-text ul,' + uid + '-text ol{padding-left:1.4em;margin:.25em 0;}' +
      '.' + uid + '-text h1,' + uid + '-text h2,' + uid + '-text h3,' + uid + '-text h4,' + uid + '-text h5,' + uid + '-text h6{margin:.5em 0 .25em;line-height:1.3;font-weight:700;}' +
      '.' + uid + '-text h1{font-size:1.2em;}' +
      '.' + uid + '-text h2{font-size:1.1em;}' +
      '.' + uid + '-text h3{font-size:1.02em;}' +
      '.' + uid + '-text h4,' + uid + '-text h5,' + uid + '-text h6{font-size:1em;}' +
      '.' + uid + '-text table{border-collapse:collapse;margin:.4em 0;font-size:.85em;max-width:100%;display:block;overflow-x:auto;}' +
      '.' + uid + '-text th,' + uid + '-text td{border:1px solid ' + t.tableBorder + ';padding:4px 8px;text-align:left;}' +
      '.' + uid + '-text th{background:' + t.preBg + ';font-weight:600;}' +
      '.' + uid + '-text blockquote{margin:.4em 0;padding:0 0 0 .8em;border-left:3px solid ' + t.tableBorder + ';color:' + t.blockquoteText + ';}' +
      '.' + uid + '-text hr{border:none;border-top:1px solid ' + t.tableBorder + ';margin:.6em 0;}' +
      '.' + uid + '-text img{max-width:100%;border-radius:8px;}' +
      '.' + uid + '-thinking-block{align-self:flex-start;max-width:82%;background:' + t.thinkingBg + ';border:1px solid ' + t.thinkingBorder + ';border-radius:8px;padding:6px 10px;font-size:12px;}' +
      '.' + uid + '-thinking-label{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:9.5px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:' + t.thinkingText + ';margin-bottom:2px;}' +
      '.' + uid + '-thinking-block pre{margin:0;white-space:pre-wrap;word-break:break-word;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:11.5px;color:' + t.thinkingText + ';font-style:italic;max-height:220px;overflow-y:auto;}' +
      '.' + uid + '-tools{align-self:flex-start;max-width:82%;display:flex;flex-wrap:wrap;gap:6px;}' +
      '.' + uid + '-tool{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:600;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;padding:3px 9px;border-radius:999px;border:1px solid ' + t.toolSuccessBorder + ';background:' + t.toolSuccessBg + ';color:' + t.toolSuccessText + ';}' +
      '.' + uid + '-tool.tool-running{border-color:' + t.toolSuccessBorder + ';color:' + t.toolSuccessText + ';background:' + t.toolSuccessBg + ';}' +
      '.' + uid + '-tool.tool-success{border-color:' + t.toolSuccessBorder + ';color:' + t.toolSuccessText + ';background:' + t.toolSuccessBg + ';}' +
      '.' + uid + '-tool.tool-error{border-color:' + t.toolErrorBorder + ';color:' + t.toolErrorText + ';background:' + t.toolErrorBg + ';}' +
      '.' + uid + '-sources{margin-top:6px;font-size:11.5px;line-height:1.6;}' +
      '.' + uid + '-sources-title{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:9.5px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:' + t.muted + ';margin-bottom:2px;}' +
      '.' + uid + '-sources-file{display:block;color:' + t.sourcesLabel + ';}' +
      '.' + uid + '-sources a{color:' + t.link + ';text-decoration:underline;text-underline-offset:2px;display:block;margin-top:2px;}' +
      '.' + uid + '-toolbar{display:flex;align-items:flex-end;gap:8px;padding:10px 12px;border-top:1px solid ' + t.toolbarBorder + ';background:' + t.toolbarBg + ';}' +
      '.' + uid + '-input{flex:1;border:1px solid ' + t.inputBorder + ';border-radius:10px;padding:9px 12px;font-size:14px;resize:none;outline:none;font-family:inherit;max-height:96px;background:' + t.inputBg + ';color:' + t.inputText + ';}' +
      '.' + uid + '-input:focus{border-color:' + t.accent + ';}' +
      '.' + uid + '-send{background:' + t.btnBg + ';color:' + t.btnText + ';border:none;border-radius:10px;padding:9px 14px;font-size:14px;cursor:pointer;}' +
      '.' + uid + '-send:disabled{opacity:.5;cursor:default;}' +
      '.' + uid + '-err{padding:8px 12px;background:' + t.errBg + ';color:' + t.errText + ';font-size:13px;border-top:1px solid ' + t.errBorder + ';display:none;}' +
      // Mobile: the chat panel fills the whole screen (overlay style).
      '@media (max-width:480px){.' + uid + '-panel{top:0;left:0;right:0;bottom:0;width:100%;max-width:100%;height:100%;max-height:100%;border-radius:0;}' +
      '.' + uid + '-launcher{right:16px;bottom:16px;}}');
  }

  function injectStyles(theme) {
    // Idempotent: (re)create or update the <style> element so the theme can
    // be swapped live by the dashboard preview bridge (window.__apwWidgets).
    var style = document.getElementById(uid + '-style');
    if (!style) {
      style = el('style', { id: uid + '-style' });
      document.head.appendChild(style);
    }
    style.textContent = buildStyleText(theme || DEFAULT_THEME);
  }

  function addMessage(role, text, isTyping) {
    var msgs = document.getElementById(uid + '-msgs');
    if (!msgs) return null;
    var node = el('div', { class: uid + '-msg ' + role + (isTyping ? ' ' + uid + '-thinking' : '') });
    if (role === 'bot') {
      // Bot messages are markdown — mirrors the dashboard preview.
      var body = el('div', { class: uid + '-text' }, node);
      body.innerHTML = markdownToHtml(text);
    } else {
      node.textContent = text;
    }
    msgs.appendChild(node);
    msgs.scrollTop = msgs.scrollHeight;
    return node;
  }

  /**
   * Create the structured assistant message as SEPARATE bubbles, appended in
   * order: thinking → tools → text. Each is a sibling in the message list
   * (agent-side left); `applyOpts()` shows/hides the thinking & tools bubbles
   * independently, while sources are attached at the end of the text bubble
   * by `renderSources`.
   */
  function beginAssistantMessage() {
    var msgs = document.getElementById(uid + '-msgs');
    if (!msgs) return null;
    thinkingBlock = el('div', { class: uid + '-thinking-block', style: 'display:none' });
    el('div', { class: uid + '-thinking-label', text: 'Reasoning' }, thinkingBlock);
    thinkingPre = el('pre', {}, thinkingBlock);
    toolsBox = el('div', { class: uid + '-tools', style: 'display:none' });
    var textEl = el('div', { class: uid + '-msg bot' });
    var textInner = el('div', { class: uid + '-text' }, textEl);
    msgs.appendChild(thinkingBlock);
    msgs.appendChild(toolsBox);
    msgs.appendChild(textEl);
    msgs.scrollTop = msgs.scrollHeight;
    return textInner;
  }

  function renderSources(sources) {
    var msgs = document.getElementById(uid + '-msgs');
    if (!sources || !sources.length || !msgs) return;
    var wrap = el('div', { class: uid + '-sources' });
    el('div', { class: uid + '-sources-title', text: 'Sources' }, wrap);
    sources.forEach(function (s, i) {
      var safe = s && typeof s === 'object' && (isValidHttpUrl(s.url) || isFileSource(s.url) || isTextSource(s.url)) ? s : null;
      if (!safe) return;
      if (s.url.indexOf('file://') === 0 || s.url.indexOf('text://') === 0) {
        // uploaded PDF / pasted text: not a clickable link, just a label
        el('span', { class: uid + '-sources-file', text: '[' + (i + 1) + '] ' + safe.title }, wrap);
        return;
      }
      el('a', { href: safe.url, target: '_blank', rel: 'noopener noreferrer', text: '[' + (i + 1) + '] ' + safe.title }, wrap);
    });
    if (!wrap.children.length) return;
    msgs.appendChild(wrap);
    msgs.scrollTop = msgs.scrollHeight;
  }

  function showSources(text) {
    renderSources(extractSources(text));
  }

  // ---- tool chips ----
  function addToolChip(callId, name) {
    if (!toolsBox) return;
    toolsBox.setAttribute('data-has', '1');
    var chip = el('span', { class: uid + '-tool tool-running' }, toolsBox);
    el('span', { class: uid + '-toolspin', text: '◌' }, chip);
    el('span', { text: name }, chip);
    currentTools.push({ callId: callId, name: name, chip: chip });
    applyOpts();
  }

  function updateToolChip(callId, status) {
    for (var i = 0; i < currentTools.length; i++) {
      var t = currentTools[i];
      if (t.callId !== callId) continue;
      t.status = status;
      t.chip.className = uid + '-tool tool-' + (status === 'error' ? 'error' : 'success');
      t.chip.innerHTML = '';
      el('span', { text: status === 'error' ? '✕' : '✓' }, t.chip);
      el('span', { text: t.name }, t.chip);
    }
  }

  // ---- display settings ----
  function applyOpts() {
    document.querySelectorAll('.' + uid + '-thinking-block').forEach(function (b) {
      var has = b.getAttribute('data-has') === '1';
      b.style.display = opts.showThinking && has ? '' : 'none';
    });
    document.querySelectorAll('.' + uid + '-tools').forEach(function (b) {
      var has = b.getAttribute('data-has') === '1';
      b.style.display = opts.showTools && has ? 'flex' : 'none';
    });
  }

  // Avatar element: photo/template (img) when uploaded, otherwise the emoji
  // fallback. The 30x30 size comes from the CSS class only — setting
  // width/height inline would blow the img up to the header width.
  // Every avatar (uploaded photo or GIF template) keeps the circle background
  // (translucent white on the header), so transparent PNGs/GIFs sit on the
  // header-colored header exactly like the emoji avatar.
  function avatarEl() {
    if (config.avatar_url) {
      var img = el('img', { class: uid + '-avatar', alt: '', 'aria-hidden': 'true' });
      img.src = config.avatar_url;
      img.style.objectFit = 'contain';
      img.style.borderRadius = '50%';
      return img;
    }
    return el('div', { class: uid + '-avatar', text: config.avatar_emoji || '🤖' });
  }

  function renderPanel() {
    var panel = document.getElementById(uid + '-panel');
    if (panel) return panel;

    panel = el('div', { class: uid + '-panel apw-hidden', id: uid + '-panel' });

    var header = el('div', { class: uid + '-header' });
    header.appendChild(avatarEl());
    var titleBox = el('div', {});
    el('div', { class: uid + '-title', text: config.name }, titleBox);
    if (config.description) el('div', { class: uid + '-subtitle', text: config.description }, titleBox);
    header.appendChild(titleBox);
    el('div', { style: 'flex:1' }, header); // spacer (mirrors preview header)
    el('button', { class: uid + '-close', text: '✕', 'aria-label': 'Close chat' }, header).addEventListener('click', toggle);
    panel.appendChild(header);

    el('div', { class: uid + '-msgs', id: uid + '-msgs' }, panel);
    el('div', { class: uid + '-err', id: uid + '-err' }, panel);

    var toolbar = el('div', { class: uid + '-toolbar' });
    var input = el('textarea', { class: uid + '-input', id: uid + '-input', placeholder: 'Type your message…', rows: '1' }, toolbar);
    var send = el('button', { class: uid + '-send', id: uid + '-send', text: 'Send' }, toolbar);
    send.disabled = true;
    panel.appendChild(toolbar);

    function resize() { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 96) + 'px'; }
    input.addEventListener('input', function () { send.disabled = !input.value.trim(); resize(); });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
    });
    send.addEventListener('click', submit);

    document.body.appendChild(panel);
    return panel;
  }

  function launcher() {
    var btn = document.getElementById(uid + '-launcher');
    if (btn) return btn;
    btn = el('button', { class: uid + '-launcher', id: uid + '-launcher', 'aria-label': 'Open chat' });
    if (config.avatar_url) {
      // The button keeps the header-color background from the CSS class and
      // draws the avatar on top, so transparent PNGs/GIFs follow the header
      // color (like the emoji avatar) instead of floating colorless — this
      // also means live theme changes (setTheme) reach the button, since no
      // inline background overrides the stylesheet.
      btn.style.backgroundImage = "url('" + config.avatar_url + "')";
      btn.style.backgroundSize = 'contain';
      btn.style.backgroundPosition = 'center';
      btn.style.backgroundRepeat = 'no-repeat';
    } else {
      btn.textContent = config.avatar_emoji || '💬';
    }
    btn.addEventListener('click', toggle);
    document.body.appendChild(btn);
    return btn;
  }

  var isOpen = false;
  function setOpen(open) {
    var panel = renderPanel();
    isOpen = open;
    panel.classList.toggle('apw-hidden', !isOpen);
    if (isOpen && !panel.getAttribute('data-loaded')) {
      panel.setAttribute('data-loaded', '1');
      loadHistory();
    }
  }

  function toggle() {
    setOpen(!isOpen);
  }

  /**
   * Optional auto-open for the dashboard preview: data-auto-open="desktop"
   * opens the panel on desktop viewports (>= 768px) but keeps it closed on
   * mobile (launcher button only) — like the live widget elsewhere.
   * data-auto-open="always" opens regardless; absent → current behavior.
   */
  function maybeAutoOpen() {
    var mode = script.getAttribute('data-auto-open');
    if (!mode || mode === 'false') return;
    var desktop = !window.matchMedia || window.matchMedia('(min-width: 768px)').matches;
    if (mode === 'always' || (mode === 'desktop' && desktop)) setOpen(true);
  }

  // ---------------------------------------------------------------- history
  function loadHistory() {
    var msgs = document.getElementById(uid + '-msgs');
    addMessage('bot', config.welcome_message || 'Hi! How can I help you?');
    apiFetch('/api/public/agents/' + agentId + '/history?thread_id=' + encodeURIComponent(threadId))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        (data.messages || []).forEach(function (m) {
          var role = m.type === 'human' ? 'user' : 'bot';
          addMessage(role, m.content || '');
          if (role === 'bot') showSources(m.content || '');
        });
        msgs.scrollTop = msgs.scrollHeight;
      })
      .catch(function () { /* history is best-effort */ });
  }

  // ------------------------------------------------------------------- chat
  function submit() {
    var input = document.getElementById(uid + '-input');
    var text = (input.value || '').trim();
    if (!text || streaming) return;
    input.value = '';
    input.dispatchEvent(new Event('input'));
    addMessage('user', text);
    sendMessage(text);
  }

  function sendMessage(text) {
    streaming = true;
    setSendDisabled(true);
    assistantBuf = '';
    assistantThinking = '';
    sourcesShown = false;
    currentSources = [];
    currentTools = [];
    assistantEl = beginAssistantMessage();
    if (assistantEl) assistantEl.innerHTML = '<span class="' + uid + '-thinking">…</span>';

    // Current-page context: default to the page the widget is embedded on.
    // data-page-url="off" (or empty) disables it; a URL value overrides it
    // (e.g. when the widget lives on a JS-rendered SPA whose real content URL
    // differs from window.location). Sent on every message so SPA navigation
    // stays current; the backend stores it on the thread and the agent's
    // read_current_page tool uses it only when the visitor asks.
    var runInput = { thread_id: threadId, messages: [{ role: 'user', content: text }] };
    var pageUrlAttr = script.getAttribute('data-page-url');
    if (pageUrlAttr === null) runInput.page_url = window.location.href;
    else if (pageUrlAttr !== 'off' && pageUrlAttr !== '') runInput.page_url = pageUrlAttr;

    apiFetch('/api/public/agents/' + agentId + '/commands', {
      method: 'POST',
      body: { method: 'run.start', id: genId(), params: { input: runInput } },
    })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res.type !== 'success') throw new Error((res.message || 'Failed to start chat'));
        return stream();
      })
      .catch(function (err) {
        showError(err.message || 'Connection error');
        finishStream();
      });
  }

  function stream() {
    return apiFetch('/api/public/agents/' + agentId + '/stream', {
      method: 'POST',
      body: { thread_id: threadId, channels: ['*'], since: 0 },
    }).then(function (res) {
      if (!res.body) throw new Error('Streaming not supported');
      var reader = res.body.getReader();
      var decoder = new TextDecoder();
      var buffer = '';

      function pump() {
        return reader.read().then(function (chunk) {
          if (chunk.done) { finishStream(); return; }
          buffer += decoder.decode(chunk.value, { stream: true });
          var frames = buffer.split('\n\n');
          buffer = frames.pop();
          frames.forEach(processFrame);
          return pump();
        });
      }
      return pump();
    });
  }

  function processFrame(frame) {
    var eventType = 'message';
    var dataLines = [];
    frame.split('\n').forEach(function (line) {
      if (line.startsWith('event:')) eventType = line.slice(6).trim();
      else if (line.startsWith('data:')) dataLines.push(line.slice(5));
    });
    var data = dataLines.join('\n');
    if (!data.trim()) return;
    var parsed;
    try { parsed = JSON.parse(data); } catch (e) { return; }

    switch (eventType) {
      case 'lifecycle':
        // lifecycle 'running' does NOT imply a tool call — the typing label
        // is only set when a real tool_start event arrives.
        break;
      case 'tool_start': {
        var tData = parsed.params && parsed.params.data;
        if (tData && tData.tool_call_id) {
          addToolChip(tData.tool_call_id, (tData && tData.name) || 'tool');
        }
        // No hardcoded "Calling …" typing label: the tool's own progress
        // message (tool_progress) drives the typing text; the chip shows the
        // tool name from the backend event.
        break;
      }
      case 'tool_progress':
        // Typing text comes from the tool's own progress message (no
        // client-side hardcoded labels). Gated on Show tools: when hidden,
        // the bubble stays '…'. Mirrors the preview.
        if (parsed.params && parsed.params.data && parsed.params.data.message && opts.showTools) {
          setTyping(parsed.params.data.message);
        }
        break;
      case 'text_delta': {
        var delta = parsed.params && parsed.params.data;
        if (delta && delta.delta) {
          if (delta.kind === 'reasoning') {
            // Reasoning: accumulate into the thinking block (always visible
            // when the Show thinking toggle is on). The text bubble keeps its
            // own typing indicator until the first text token arrives — it is
            // NOT cleared here (thinking lives in its own block now,
            // mirroring the preview).
            assistantThinking += delta.delta;
            if (thinkingBlock && thinkingPre) {
              thinkingBlock.setAttribute('data-has', '1');
              thinkingPre.textContent = assistantThinking;
              applyOpts();
            }
          } else if (delta.kind === 'text') {
            if (assistantEl) assistantEl.classList.remove(uid + '-thinking');
            assistantBuf += delta.delta;
            if (assistantEl) assistantEl.innerHTML = markdownToHtml(assistantBuf);
          }
          scrollToBottom();
        }
        break;
      }
      case 'tool_end': {
        var teData = parsed.params && parsed.params.data;
        if (teData && teData.tool_call_id) {
          updateToolChip(teData.tool_call_id, teData.error ? 'error' : 'success');
        }
        break;
      }
      case 'sources': {
        // Authoritative source list resolved server-side from tool outputs.
        var srcData = parsed.params && parsed.params.data;
        if (srcData && Array.isArray(srcData.sources)) {
          currentSources = srcData.sources;
          renderSources(currentSources);
          sourcesShown = true;
        }
        break;
      }
      case 'message_end':
        if (assistantEl && !sourcesShown) {
          if (currentSources.length) renderSources(currentSources);
          else showSources(assistantBuf);
          sourcesShown = true;
        }
        break;
      default:
        break;
    }
  }

  function scrollToBottom() {
    var msgs = document.getElementById(uid + '-msgs');
    if (msgs) msgs.scrollTop = msgs.scrollHeight;
  }

  function setTyping(text) {
    if (!assistantEl) return;
    if (!assistantBuf) { assistantEl.classList.add(uid + '-thinking'); assistantEl.textContent = text; }
    scrollToBottom();
  }

  function setSendDisabled(v) {
    var send = document.getElementById(uid + '-send');
    if (send) send.disabled = v;
  }

  function showError(msg) {
    var err = document.getElementById(uid + '-err');
    if (err) { err.textContent = '⚠ ' + msg; err.style.display = 'block'; }
  }

  function finishStream() {
    streaming = false;
    setSendDisabled(false);
    var input = document.getElementById(uid + '-input');
    if (input) input.focus();
    if (assistantEl && !sourcesShown && assistantBuf) {
      if (currentSources.length) renderSources(currentSources);
      else showSources(assistantBuf);
      sourcesShown = true;
    }
    assistantEl = null;
  }

  // ------------------------------------------------------------------- init
  function init() {
    // Display toggles come from the agent config (set in the preview panel).
    opts = {
      showThinking: config.show_thinking === true,
      showTools: config.show_tools !== false,
    };
    injectStyles(resolveTheme());
    launcher();
    renderPanel();
    applyOpts();
    maybeAutoOpen();

    // Bridge for the dashboard preview: live theme/opts updates + cleanup.
    window.__apwWidgets = window.__apwWidgets || {};
    window.__apwWidgets[agentId] = {
      setTheme: function (theme) { injectStyles(theme); },
      setOpts: function (showThinking, showTools) {
        opts.showThinking = showThinking !== false;
        opts.showTools = showTools !== false;
        applyOpts();
      },
      destroy: function () {
        var l = document.getElementById(uid + '-launcher');
        var p = document.getElementById(uid + '-panel');
        var s = document.getElementById(uid + '-style');
        if (l) l.remove();
        if (p) p.remove();
        if (s) s.remove();
        delete window.__apwWidgets[agentId];
      },
    };
  }

  // Cache-bust: the config (theme, avatar URL) must be fresh on every load;
  // the backend also sends Cache-Control: no-cache for this endpoint.
  apiFetch('/api/public/agents/' + agentId + '/config?t=' + Date.now())
    .then(function (r) {
      if (!r.ok) throw new Error('Agent config unavailable (check token?)');
      return r.json();
    })
    .then(function (cfg) {
      config = cfg;
      if (document.body) init();
      else document.addEventListener('DOMContentLoaded', init);
    })
    .catch(function (err) {
      // Render a launcher that shows the error when clicked (fail gracefully).
      config = { name: 'Assistant', avatar_emoji: '💬', welcome_message: 'Unable to load assistant.', description: '' };
      injectStyles(resolveTheme());
      var btn = launcher();
      btn.addEventListener('click', function () { alert('Assistant unavailable: ' + err.message); });
    });
})();
