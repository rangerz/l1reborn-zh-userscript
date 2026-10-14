// Lineage 1 Reborn 中文化 — userscript 入口。
// build 會把這支包進 IIFE，字典常數由 data/translations/*.json 填入。
//
// 原則：英文原文永遠留在 DOM 原位，中文只透過 CSS（::before + attr()）疊上去，
// 所以切回英文只是拿掉 <html data-l1r-lang> 的一個屬性。
const DICT = __DICT__;

const IS_PLAY = location.hostname === 'play.lineage1reborn.com';
const TABLE = { ...DICT.common, ...(IS_PLAY ? DICT.play : DICT.site) };
const LANG_KEY = 'l1r-zh-lang';
const SKIP = 'head,script,style,noscript,textarea,code,pre,[contenteditable],l1r-zh,[data-l1r-zh],#l1r-zh-toggle';

const CSS = `
html:not([data-l1r-lang="en"]) l1r-en { display: none; }
html:not([data-l1r-lang="en"]) l1r-zh::before { content: attr(data-zh); }
html:not([data-l1r-lang="en"]) [data-l1r-zh] { font-size: 0 !important; }
html:not([data-l1r-lang="en"]) [data-l1r-zh]::before { content: attr(data-l1r-zh); font-size: var(--l1r-fs); }
#l1r-zh-toggle { position: fixed; right: 8px; bottom: 8px; z-index: 2147483647; padding: 4px 10px; border-radius: 999px;
  border: 1px solid #c9a45c; background: #15130f; color: #ead3a0; font: 12px/1 sans-serif; cursor: pointer; opacity: .7; }
#l1r-zh-toggle:hover { opacity: 1; }
`;

const lookup = makeLookup(TABLE);   // src/lookup.js，build 時內嵌

// 主站沒有 React：把文字節點包成 <l1r-zh><l1r-en>英文</l1r-en></l1r-zh>，英文留在原位，中文走外層 ::before。
// 用自訂元素而不是 span：站方有 `h5 a>span{display:none}` 這種針對 span 的規則，自訂元素不會被打到。
// 前後空白切成獨立節點留在外面，免得 "Welcome, <b>x</b>" 這類文字黏到旁邊的元素。
function wrap(node, zh) {
  const text = node.nodeValue;
  const lead = text.length - text.trimStart().length;
  const core = lead ? node.splitText(lead) : node;
  const len = core.nodeValue.trimEnd().length;
  if (len < core.nodeValue.length) core.splitText(len);
  const outer = document.createElement('l1r-zh');
  outer.dataset.zh = zh;
  const inner = document.createElement('l1r-en');
  core.before(outer);
  outer.append(inner);
  inner.append(core);
}

// play 站是 React：搬動文字節點會讓 React 之後的 removeChild / insertBefore 炸掉（Google 翻譯同款災難），
// 所以只在「元素裡只有這一個文字節點」時掛屬性，元素本身 font-size:0、中文由 ::before 以原字級畫出來。
function mark(el, zh) {
  el.style.setProperty('--l1r-fs', getComputedStyle(el).fontSize);
  el.dataset.l1rZh = zh;
}

function translate(node) {
  const el = node.parentElement;
  if (!el || el.closest(SKIP)) return;
  const zh = lookup(node.nodeValue);
  if (!zh) return;
  if (!IS_PLAY) wrap(node, zh);
  else if (el.childNodes.length === 1) mark(el, zh);
  // ponytail: play 站的混合內容（如 <label>Account<input>）先留英文；要翻就得找不碰文字節點的做法
}

// 站方 JS 原地改字（計數器、React 換 label）時，跟著更新或撤掉中文。
function sync(node) {
  const el = node.parentElement;
  if (!el) return;
  const zh = lookup(node.nodeValue);
  if (el.localName === 'l1r-en') {
    if (zh) el.parentElement.dataset.zh = zh;
    else el.parentElement.replaceWith(node);
  } else if (el.hasAttribute('data-l1r-zh')) {
    if (zh) el.dataset.l1rZh = zh;
    else el.removeAttribute('data-l1r-zh');
  } else translate(node);
}

function walk(root) {
  if (root.nodeType === Node.TEXT_NODE) return translate(root);
  if (root.nodeType !== Node.ELEMENT_NODE) return;
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (w.nextNode()) nodes.push(w.currentNode);   // 先收集再翻，wrap 會改樹
  nodes.forEach(translate);
}

const html = document.documentElement;
html.dataset.l1rLang = localStorage.getItem(LANG_KEY) || 'zh';

const style = document.createElement('style');
style.textContent = CSS;
html.append(style);

const btn = document.createElement('button');
btn.id = 'l1r-zh-toggle';
btn.type = 'button';
btn.textContent = '中 / EN';
btn.title = '切換中英文顯示';
btn.onclick = () => {
  const next = html.dataset.l1rLang === 'en' ? 'zh' : 'en';
  html.dataset.l1rLang = next;
  localStorage.setItem(LANG_KEY, next);
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
