// Lineage 1 Reborn 中文化 — userscript 入口。
// build 會把這支包進 IIFE，字典常數由 data/translations/*.json 填入。
//
// 原則：英文原文永遠留在 DOM 原位，中文只透過 CSS（::before + attr()）疊上去，
// 所以切回英文只是拿掉 <html data-l1r-lang> 的一個屬性。
const DICT = __DICT__;

const IS_PLAY = location.hostname === 'play.lineage1reborn.com';
const TABLE = { ...DICT.common, ...(IS_PLAY ? DICT.play : DICT.site) };
const LANG_KEY = 'l1r-zh-lang';
const SKIP = 'head,script,style,noscript,textarea,code,pre,[contenteditable],l1r-zh,[data-l1r-zh],#l1r-zh-toggle,.dhm-name';

// 站方有 `.world-client.client363[...] :is(... button) { font-size: ... !important }` 這種高優先度規則，
// 單一屬性選擇器壓不過去（兩邊都 !important 時比 specificity），所以把屬性選擇器重複疊高 specificity。
const Z = '[data-l1r-zh]'.repeat(12);

const CSS = `
html:not([data-l1r-lang="en"]) l1r-en { display: none; }
html:not([data-l1r-lang="en"]) l1r-zh::before { content: attr(data-zh); }
html:not([data-l1r-lang="en"]) l1r-zh[data-sub] > l1r-en { display: inline; margin-left: .4em; font-size: .65em; font-weight: normal; opacity: .7; }
html:not([data-l1r-lang="en"]) ${Z} { font-size: 0 !important; }
html:not([data-l1r-lang="en"]) [data-l1r-zh]::before { content: attr(data-l1r-zh); font-size: var(--l1r-fs); }
html:not([data-l1r-lang="en"]) [data-l1r-zh][data-l1r-after]::before { content: none; }
html:not([data-l1r-lang="en"]) [data-l1r-zh][data-l1r-after]::after { content: attr(data-l1r-zh); font-size: var(--l1r-fs); }
html:not([data-l1r-lang="en"]) ${Z}[data-l1r-mixed] { gap: 0 !important; line-height: 0 !important; }
html:not([data-l1r-lang="en"]) [data-l1r-zh][data-l1r-mixed]::before { margin-bottom: var(--l1r-gap); line-height: var(--l1r-lh); }
html:not([data-l1r-lang="en"]) [data-l1r-zh][data-l1r-mixed][data-l1r-row]:not([data-l1r-after])::before { margin: 0 var(--l1r-gap) 0 0; }
html:not([data-l1r-lang="en"]) [data-l1r-zh][data-l1r-mixed][data-l1r-after]::after { margin-left: var(--l1r-gap); line-height: var(--l1r-lh); }
html:not([data-l1r-lang="en"]) [data-l1r-zh][data-l1r-mixed][data-l1r-after]::before { margin: 0; }
html:not([data-l1r-lang="en"]) [data-l1r-zh][data-l1r-br]::before,
html:not([data-l1r-lang="en"]) [data-l1r-zh][data-l1r-br]::after { white-space: pre-wrap; }
#l1r-zh-toggle { position: fixed; right: 8px; bottom: 8px; z-index: 2147483647; padding: 4px 10px; border-radius: 999px;
  border: 1px solid #c9a45c; background: #15130f; color: #ead3a0; font: 12px/1 sans-serif; cursor: pointer; opacity: .7; }
#l1r-zh-toggle:hover { opacity: 1; }
`;

// 獨立顯示的技能名與屬性縮寫（STR、DEX…）：中文後面接較小的英文。技能名只在法術書卡片標題這個確定位置才直接查 skills.json
// （單字如 Light、Heal 才不會誤植）；屬性縮寫要整個文字節點剛好是縮寫才會中，內文裡提到的不受影響。
const SKILL_TITLE = '.grimoire-card h4';
function skillZh(text, el) {
  if (IS_PLAY) return;
  text = text.replace(/\s+/g, ' ').trim();
  return (el?.matches(SKILL_TITLE) && DICT.skills[text]) || DICT.stats[text] || undefined;
}

// 法術動畫下拉的 <option>（"Magic Lv 1 · Lesser Heal"）放不了小字，改成「中文 英文」用空白隔開：魔法 Lv 1 · 初級治癒術 Lesser Heal
const SPELL_OPTION = 'select[data-spell-select] > option';
function skillOptionZh(text, el) {
  if (IS_PLAY || !el?.matches(SPELL_OPTION)) return;
  const m = text.replace(/\s+/g, ' ').trim().match(/^(.+?) · (.+)$/);
  const name = m && (DICT.skills[m[2]] ?? lookup(m[2]));
  return name && `${lookup(m[1]) ?? m[1]} · ${name} ${m[2]}`;
}

const siteLookup = makeLookup(TABLE);   // src/lookup.js，build 時內嵌
// 主站每頁有 #site-page-content[data-page]；pages/<page>.local.json 只在那一頁查得到，站方局部換頁時 data-page 會跟著變，所以每次查都重讀。
const localLookups = {};
function lookup(text) {
  const page = IS_PLAY ? null : document.querySelector('#site-page-content')?.dataset.page;
  const table = page && DICT.local[page];
  const hit = table && (localLookups[page] ||= makeLookup(table))(text);
  return hit ?? siteLookup(text);
}
const html = document.documentElement;
const systemLanguages = navigator.languages?.length ? navigator.languages : [navigator.language];
const defaultLang = /^en(?:-|$)/i.test(systemLanguages[0] || '') ? 'en' : 'zh';
html.dataset.l1rLang = localStorage.getItem(LANG_KEY) || defaultLang;

// 主站沒有 React：把文字節點包成 <l1r-zh><l1r-en>英文</l1r-en></l1r-zh>，英文留在原位，中文走外層 ::before。
// 用自訂元素而不是 span：站方有 `h5 a>span{display:none}` 這種針對 span 的規則，自訂元素不會被打到。
// 前後空白切成獨立節點留在外面，免得 "Welcome, <b>x</b>" 這類文字黏到旁邊的元素。
function wrap(node, zh, sub) {
  const text = node.nodeValue;
  const lead = text.length - text.trimStart().length;
  const core = lead ? node.splitText(lead) : node;
  const len = core.nodeValue.trimEnd().length;
  if (len < core.nodeValue.length) core.splitText(len);
  const outer = document.createElement('l1r-zh');
  outer.dataset.zh = zh;
  if (sub) outer.dataset.sub = '';
  const inner = document.createElement('l1r-en');
  core.before(outer);
  outer.append(inner);
  inner.append(core);
}

// play 站是 React：搬動文字節點會讓 React 之後的 removeChild / insertBefore 炸掉（Google 翻譯同款災難），
// 所以只在「元素裡只有這一個文字節點」時掛屬性，元素本身 font-size:0、中文由 ::before 以原字級畫出來。
function mark(el, zh) {
  // 已經掛過就不要重量：此時字級已被壓成 0，量到的會是 0px，中文就看不見了
  if (!el.hasAttribute('data-l1r-zh')) el.style.setProperty('--l1r-fs', getComputedStyle(el).fontSize);
  el.dataset.l1rZh = zh;
}

// 混合內容（<label>Account<input></label>）：文字節點不動，元素 font-size:0 藏起英文，
// 子元素先把自己的字級固定下來才不會跟著變 0；文字在子元素之後就改用 ::after 以維持順序。
function markMixed(el, node, zh) {
  if (el.hasAttribute('data-l1r-zh')) { el.dataset.l1rZh = zh; return; }
  const cs = getComputedStyle(el);
  for (const c of el.children) {
    const ccs = getComputedStyle(c);
    if (!c.style.fontSize) c.style.fontSize = ccs.fontSize;
    if (!c.style.lineHeight) c.style.lineHeight = ccs.lineHeight;
  }
  el.style.setProperty('--l1r-fs', cs.fontSize);
  el.style.setProperty('--l1r-lh', cs.lineHeight);
  // 橫向 flex（按鈕裡的 文字<small>）要用 margin-right 補 gap，grid / 直向才是 margin-bottom
  const row = /flex/.test(cs.display) && cs.flexDirection.startsWith('row');
  const g = row ? cs.columnGap : cs.rowGap;
  el.style.setProperty('--l1r-gap', g === 'normal' ? '0px' : g);
  if (row) el.dataset.l1rRow = '';
  el.dataset.l1rMixed = '';
  if (node.previousSibling && node.previousSibling.nodeType === Node.ELEMENT_NODE) {
    el.dataset.l1rAfter = '';
    // 文字後面還有元素（<svg>文字<small>2 / 6</small>）：讓後面的元素 order 排到 ::after 之後，gap 改成 margin 補回。
    const gap = cs.columnGap === 'normal' ? '0px' : cs.columnGap;
    for (let n = node.nextSibling; n; n = n.nextSibling) {
      if (n.nodeType !== Node.ELEMENT_NODE) continue;
      if (!n.style.order) n.style.order = '1';
      if (!n.style.marginLeft) n.style.marginLeft = gap;
    }
  }
  el.dataset.l1rZh = zh;
}

// 以 <br> 分行的段落（站方登入頁的詩句）：把各行文字用空白串成一個 key，譯文裡的 \n 以 pre-line 換行。
function brText(el) {
  if (!el.querySelector(':scope > br')) return null;
  const parts = [];
  for (const c of el.childNodes) {
    if (c.nodeType === Node.TEXT_NODE) parts.push(c.nodeValue);
    else if (c.localName !== 'br') return null;
  }
  return parts.join(' ');
}

// <option> 是特例：原生下拉選單不畫 ::before，CSS 疊不上去。改用 label 屬性顯示中文，
// 英文仍留在 textContent；切回英文時把 label 拿掉（見 setLang）。
function markOption(el, zh) {
  el.dataset.l1rOpt = zh;
  if (html.dataset.l1rLang !== 'en') el.label = zh;
}

// 公告 <pre> 內容每天會換，整段完全相符不實際：逐行查字典，查不到的行原樣保留英文，換行用 pre-wrap 畫出來。
// 譯文會是整個 <pre> 的中文版，所以這裡直接 mark，不走一般的單一文字節點流程。
const NOTICE = '.mobile-server-notice pre';
function translateNotice(el) {
  const lines = el.textContent.split('\n');
  let hit = false;
  const out = lines.map(l => {
    const zh = l.trim() && lookup(l);
    if (zh) hit = true;
    return zh || l;
  });
  if (!hit) { el.removeAttribute('data-l1r-zh'); return; }
  mark(el, out.join('\n'));
  el.dataset.l1rBr = '';
}

function translate(node) {
  const el = node.parentElement;
  if (IS_PLAY && el && el.matches(NOTICE)) return translateNotice(el);
  if (!el || el.closest(SKIP)) return;
  if (IS_PLAY && el.localName !== 'option') {
    const joined = brText(el);
    if (joined !== null) {
      const zhBr = lookup(joined);
      if (zhBr) { mark(el, zhBr); el.dataset.l1rBr = ''; }
      return;
    }
  }
  const sub = skillZh(node.nodeValue, el);
  const zh = sub ?? skillOptionZh(node.nodeValue, el) ?? lookup(node.nodeValue);
  if (!zh) return;
  if (el.localName === 'option') markOption(el, zh);
  else if (!IS_PLAY) wrap(node, zh, sub !== undefined);
  else if (el.childNodes.length === 1) mark(el, zh);
  else if ([...el.childNodes].filter(c => c.nodeType === Node.TEXT_NODE && c.nodeValue.trim()).length === 1) markMixed(el, node, zh);
}

// 站方 JS 原地改字（計數器、React 換 label）時，跟著更新或撤掉中文。
function sync(node) {
  const el = node.parentElement;
  if (!el) return;
  if (IS_PLAY && el.matches(NOTICE)) return translateNotice(el);
  const zh = skillZh(node.nodeValue, el.localName === 'l1r-en' ? el.parentElement.parentElement : el) ?? skillOptionZh(node.nodeValue, el) ?? lookup(node.nodeValue);
  if (el.localName === 'l1r-en') {
    if (zh) el.parentElement.dataset.zh = zh;
    else el.parentElement.replaceWith(node);
  } else if (el.hasAttribute('data-l1r-zh')) {
    if (zh) el.dataset.l1rZh = zh;
    else el.removeAttribute('data-l1r-zh');
  } else if (el.hasAttribute('data-l1r-opt')) {
    if (zh) markOption(el, zh);
    else { el.removeAttribute('data-l1r-opt'); el.removeAttribute('label'); }
  } else translate(node);
}

// placeholder 是屬性不是文字節點，CSS 疊不上去：直接換屬性，英文存在 data-l1r-ph 切回英文時還原。
// 這是會改動原頁屬性的做法，只用在官網；play 是獨立的遊戲客戶端（React），不碰。
function translatePlaceholders(root) {
  if (IS_PLAY) return;
  for (const el of root.querySelectorAll('[placeholder]:not([data-l1r-ph])')) {
    const en = el.getAttribute('placeholder');
    const zh = lookup(en);
    if (!zh) continue;
    el.dataset.l1rPh = en;
    if (html.dataset.l1rLang !== 'en') el.placeholder = zh;
  }
}

function walk(root) {
  if (root.nodeType === Node.TEXT_NODE) return translate(root);
  if (root.nodeType !== Node.ELEMENT_NODE) return;
  translatePlaceholders(root);
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (w.nextNode()) nodes.push(w.currentNode);   // 先收集再翻，wrap 會改樹
  nodes.forEach(translate);
}


const style = document.createElement('style');
style.textContent = CSS;
html.append(style);

const btn = document.createElement('button');
btn.id = 'l1r-zh-toggle';
btn.type = 'button';
btn.textContent = '中文/EN';
btn.title = '切換中英文顯示';
btn.onclick = () => {
  const next = html.dataset.l1rLang === 'en' ? 'zh' : 'en';
  html.dataset.l1rLang = next;
  localStorage.setItem(LANG_KEY, next);
  for (const o of document.querySelectorAll('option[data-l1r-opt]')) {
    if (next === 'en') o.removeAttribute('label');
    else o.label = o.dataset.l1rOpt;
  }
  for (const el of document.querySelectorAll('[data-l1r-ph]')) {
    el.placeholder = next === 'en' ? el.dataset.l1rPh : lookup(el.dataset.l1rPh);
  }
};
document.body.append(btn);

new MutationObserver(records => {
  for (const r of records) {
    if (r.type === 'characterData') sync(r.target);
    else r.addedNodes.forEach(walk);
  }
  // play 站 React hydration 可能把它不認識的節點清掉，掉了就放回去
  if (!style.isConnected) html.append(style);
  if (!btn.isConnected) document.body.append(btn);
}).observe(html, { childList: true, subtree: true, characterData: true });

walk(document.body);
