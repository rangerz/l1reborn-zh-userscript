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
  const dict = JSON.parse(read(`data/translations/${file}`));
  for (const [en, zh] of Object.entries(dict)) {
    if (en !== en.replace(/\s+/g, ' ').trim()) throw new Error(`${file}: key "${en}" 要先 trim 並把連續空白收成一個`);
    if (typeof zh !== 'string' || !zh.trim()) throw new Error(`${file}: "${en}" 的譯文是空的`);
  }
  return dict;
}

const dict = {
  common: loadDict('common.json'),
  site: loadDict('site.json'),
  play: loadDict('play.json'),
};

const header = `// ==UserScript==
// @name         Lineage 1 Reborn 中文化
// @namespace    ${REPO}
// @version      ${pkg.version}
// @description  lineage1reborn.com 與 play.lineage1reborn.com 的中文介面：英文原文留在 DOM，中文用 CSS 疊上去，右下角可切回英文。
// @author       Ranger Chan
// @match        https://lineage1reborn.com/*
// @match        https://www.lineage1reborn.com/*
// @match        https://play.lineage1reborn.com/*
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
