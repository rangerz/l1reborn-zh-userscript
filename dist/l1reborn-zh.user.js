// ==UserScript==
// @name         Lineage 1 Reborn 中文化
// @namespace    https://github.com/rangerz/l1reborn-zh-userscript
// @version      0.1.0
// @description  lineage1reborn.com 與 play.lineage1reborn.com 的中文介面：英文原文留在 DOM，中文用 CSS 疊上去，右下角可切回英文。
// @author       Ranger Chan
// @match        https://lineage1reborn.com/*
// @match        https://www.lineage1reborn.com/*
// @match        https://play.lineage1reborn.com/*
// @run-at       document-end
// @grant        none
// @homepageURL  https://github.com/rangerz/l1reborn-zh-userscript
// @supportURL   https://github.com/rangerz/l1reborn-zh-userscript/issues
// @updateURL    https://raw.githubusercontent.com/rangerz/l1reborn-zh-userscript/main/dist/l1reborn-zh.user.js
// @downloadURL  https://raw.githubusercontent.com/rangerz/l1reborn-zh-userscript/main/dist/l1reborn-zh.user.js
// ==/UserScript==

(function () {
'use strict';

// Lineage 1 Reborn 中文化 — userscript 入口。
// build 會把這支包進 IIFE，字典常數由 data/translations/*.json 填入。
//
// 原則：英文原文永遠留在 DOM 原位，中文只透過 CSS（::before + attr()）疊上去，
// 所以切回英文只是拿掉 <html data-l1r-lang> 的一個屬性。
const DICT = {
  "common": {
    "Log in": "登入",
    "Log In": "登入",
    "Log out": "登出",
    "Create Account": "建立帳號",
    "Account": "帳號",
    "Password": "密碼",
    "Close": "關閉",
    "Download": "下載",
    "Menu": "選單",
    "Events": "活動",
    "Search": "搜尋"
  },
  "site": {
    "Why Reborn?": "為什麼選 Reborn？",
    "Server Features": "伺服器特色",
    "Guides": "指南",
    "Player Guides": "玩家指南",
    "Browse all guides →": "瀏覽所有指南 →",
    "Shops": "商店",
    "Auction House": "拍賣所",
    "Lookup": "查詢",
    "Search All": "全站搜尋",
    "Items": "道具",
    "Item Sets": "套裝",
    "Monsters": "怪物",
    "Tameable Monsters": "可馴養怪物",
    "Bosses": "Boss",
    "Maps": "地圖",
    "Treasure Boxes": "寶箱",
    "Leaderboard": "排行榜",
    "General Leaderboard": "綜合排行榜",
    "Event Leaderboard": "活動排行榜",
    "Arena Leaderboards": "競技場排行榜",
    "Arenas": "競技場",
    "Arena Games": "競技場賽事",
    "Arena Guide": "競技場指南",
    "Pledge": "血盟",
    "Pledge Board": "血盟看板",
    "Pledge Guide": "血盟指南",
    "Pledge Management": "血盟管理",
    "Siege Guide": "攻城指南",
    "Siege Stats": "攻城戰績",
    "Skirmish Stats": "遭遇戰戰績",
    "Castle Control": "城堡佔領",
    "Classes (in progress)": "職業（施工中）",
    "Classes & spellbooks": "職業與魔法書",
    "Explore classes & spellbooks →": "探索職業與魔法書 →",
    "Boss cycles": "Boss 週期",
    "Player videos": "玩家影片",
    "Darko’s comic": "Darko 的漫畫",
    "unique visitors": "不重複訪客",
    "Show all updates": "顯示所有更新",
    "Start your blog": "開始寫部落格",
    "Latest from the blogs": "部落格最新文章",
    "Latest videos": "最新影片",
    "News & field notes": "新聞與手記",
    "Choose your world": "選擇你的世界",
    "Gameplay & First Looks": "遊戲實況與初體驗",
    "PvP & Clan Fights": "PvP 與血盟戰",
    "DVC Hardmode": "DVC 困難模式",
    "FI Hardmode": "FI 困難模式",
    "FV Hardmode": "FV 困難模式",
    "TOI Hardmode": "TOI 困難模式",
    "TOI Hardmode BETA": "TOI 困難模式 BETA",
    "Abandonware Disclaimer": "Abandonware 免責聲明",
    "I understand": "我瞭解了",
    "Runes": "符文",
    "Dream Island": "夢幻島",
    "Forgotten Island": "被遺忘之島"
  },
  "play": {
    "Remember me": "記住我",
    "Remember password": "記住密碼",
    "Log in to Reborn": "登入 Reborn",
    "Check connection": "檢查連線",
    "Use your existing Reborn account.": "使用你現有的 Reborn 帳號。",
    "Passwords are remembered only by your browser.": "密碼只會保存在你的瀏覽器裡。"
  }
};

const IS_PLAY = location.hostname === 'play.lineage1reborn.com';
const TABLE = { ...DICT.common, ...(IS_PLAY ? DICT.play : DICT.site) };
const LANG_KEY = 'l1r-zh-lang';
const SKIP = 'head,script,style,noscript,textarea,code,pre,[contenteditable],.l1r-zh,[data-l1r-zh],#l1r-zh-toggle';

const CSS = `
html:not([data-l1r-lang="en"]) .l1r-en { display: none; }
html:not([data-l1r-lang="en"]) .l1r-zh::before { content: attr(data-zh); }
html:not([data-l1r-lang="en"]) [data-l1r-zh] { font-size: 0 !important; }
html:not([data-l1r-lang="en"]) [data-l1r-zh]::before { content: attr(data-l1r-zh); font-size: var(--l1r-fs); }
#l1r-zh-toggle { position: fixed; right: 8px; bottom: 8px; z-index: 2147483647; padding: 4px 10px; border-radius: 999px;
  border: 1px solid #c9a45c; background: #15130f; color: #ead3a0; font: 12px/1 sans-serif; cursor: pointer; opacity: .7; }
#l1r-zh-toggle:hover { opacity: 1; }
`;

const lookup = text => TABLE[text.replace(/\s+/g, ' ').trim()];

// 主站沒有 React：把文字節點包成 .l1r-zh > .l1r-en，英文留在原位，中文走外層 ::before。
// 前後空白切成獨立節點留在外面，免得 "Welcome, <b>x</b>" 這類文字黏到旁邊的元素。
function wrap(node, zh) {
  const text = node.nodeValue;
  const lead = text.length - text.trimStart().length;
  const core = lead ? node.splitText(lead) : node;
  const len = core.nodeValue.trimEnd().length;
  if (len < core.nodeValue.length) core.splitText(len);
  const outer = document.createElement('span');
  outer.className = 'l1r-zh';
  outer.dataset.zh = zh;
  const inner = document.createElement('span');
  inner.className = 'l1r-en';
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
  if (el.classList.contains('l1r-en')) {
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

})();
