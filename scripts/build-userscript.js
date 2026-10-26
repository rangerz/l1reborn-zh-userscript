import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = p => fs.readFileSync(path.join(root, p), 'utf8');
const pkg = JSON.parse(read('package.json'));

const REPO = 'https://github.com/rangerz/l1reborn-zh-userscript';
const OUT = 'dist/l1reborn-zh.user.js';
const RAW = `https://raw.githubusercontent.com/rangerz/l1reborn-zh-userscript/main/${OUT}`;

// key = 頁面上的英文原文（trim、連續空白收成一個），value = 中文。這裡擋掉比對不到的 key。
function loadDict(file) {
  const dict = JSON.parse(read(file.includes('/') && file.startsWith('data/') ? file : `data/translations/${file}`));
  for (const [en, zh] of Object.entries(dict)) {
    if (en !== en.replace(/\s+/g, ' ').trim()) throw new Error(`${file}: key "${en}" 要先 trim 並把連續空白收成一個`);
    if (typeof zh !== 'string' || !zh.trim()) throw new Error(`${file}: "${en}" 的譯文是空的`);
  }
  return dict;
}

// 主站字典 = site.json + pages/*.json（每頁一檔）。同一個英文在不同檔譯得不一樣就擋下來。
const site = loadDict('site.json');
const pageFiles = fs.readdirSync(path.join(root, 'data/translations/pages')).filter(f => f.endsWith('.json')).sort();
for (const f of pageFiles.filter(f => !f.endsWith('.local.json'))) {
  for (const [en, zh] of Object.entries(loadDict(`pages/${f}`))) {
    if (en in site && site[en] !== zh) throw new Error(`pages/${f}: "${en}" 已有不同譯文「${site[en]}」`);
    site[en] = zh;
  }
}

// 技能名以 data/reference/skills.json 為唯一來源：多字的併進全站字典；單字（Light、Slow、Heal…）太容易撞到
// 其他文字，不全站生效，只能留在需要它的 pages/<page>.json，且譯文必須和 skills.json 一致。
// 全站字典裡的技能名若與 skills.json 不同就擋下來（特例請放 .local.json）。
const skills = loadDict('data/reference/skills.json');
for (const [en, zh] of Object.entries(skills)) {
  if (en in site && site[en] !== zh) throw new Error(`"${en}" 與 skills.json 的「${zh}」不同（現為「${site[en]}」），請改成一致或刪除`);
  if (/\s/.test(en)) site[en] = zh;
}

// pages/<page>.local.json 只在 #site-page-content[data-page=<page>] 那一頁生效，放會跟玩家名撞字的短字（Buy、Seller、Bulk…）。
// 和全站字典（common + site）同 key 同譯文就是多餘的，擋下來；譯文不同是刻意蓋掉，只提示。
const common = loadDict('common.json');
const local = {};
for (const f of pageFiles.filter(f => f.endsWith('.local.json'))) {
  const page = f.replace(/\.local\.json$/, '');
  local[page] = loadDict(`pages/${f}`);
  for (const [en, zh] of Object.entries(local[page])) {
    const global = en in site ? site[en] : common[en];
    if (global === undefined) continue;
    if (global === zh) throw new Error(`pages/${f}: "${en}" 全站字典已有相同譯文，刪掉 local 這條`);
    console.warn(`pages/${f}: "${en}" 在 ${page} 頁譯「${zh}」，全站是「${global}」`);
  }
}

const dict = {
  common,
  site,
  skills,
  stats: loadDict('data/reference/stats.json'),
  local,
};

const header = `// ==UserScript==
// @name         Lineage 1 Reborn 中文化
// @namespace    ${REPO}
// @version      ${pkg.version}
// @description  Lineage 1 Reborn 中文化
// @author       Ranger Chan
// @match        https://lineage1reborn.com/*
// @match        https://www.lineage1reborn.com/*
// @run-at       document-end
// @grant        none
// @homepageURL  ${REPO}
// @supportURL   ${REPO}/issues
// @updateURL    ${RAW}
// @downloadURL  ${RAW}
// ==/UserScript==
`;

const lib = read('src/lookup.js').replace(/^export /m, '');
const body = lib + '\n' + read('src/main.js').replace('__DICT__', () => JSON.stringify(dict, null, 2));
fs.mkdirSync(path.join(root, 'dist'), { recursive: true });
fs.writeFileSync(path.join(root, OUT), `${header}\n(function () {\n'use strict';\n\n${body}\n})();\n`);
console.log(`built ${OUT} v${pkg.version}`);
