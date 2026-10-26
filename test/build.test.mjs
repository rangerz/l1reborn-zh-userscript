import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { spawnSync } from 'node:child_process';

const OUT = 'dist/l1reborn-zh.user.js';
const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));

test('build 產物是合法的 userscript', () => {
  assert.equal(spawnSync(process.execPath, ['scripts/build-userscript.js'], { stdio: 'inherit' }).status, 0, 'build 失敗');
  const out = fs.readFileSync(OUT, 'utf8');
  assert.ok(out.startsWith('// ==UserScript=='));
  assert.ok(out.includes(`// @version      ${pkg.version}`));
  assert.ok(!out.includes('__DICT__'), '字典沒有被填進去');
  assert.equal(spawnSync(process.execPath, ['--check', OUT]).status, 0, '產物有語法錯誤');
});

test('pages/<page>.local.json 只進 dict.local，不混進全站字典', () => {
  const out = fs.readFileSync(OUT, 'utf8');
  const dict = JSON.parse(out.match(/const DICT = ([\s\S]*?);\n\nconst TABLE/)[1]);
  assert.equal(dict.local['auction-house'].Buy, '購買');
  assert.ok(!('Buy' in dict.site), 'local key 漏進全站字典');
});

test('local key 與全站譯文不同時，build 只印警告不中斷', () => {
  const file = 'data/translations/pages/clan.local.json';
  const orig = fs.readFileSync(file, 'utf8');
  try {
    // "Expand / Collapse" 在 clan.json（全站）已是「展開／收合」，這裡用不同譯文蓋掉
    fs.writeFileSync(file, JSON.stringify({ ...JSON.parse(orig), 'Expand / Collapse': '展開／收合（測試）' }, null, 2) + '\n');
    const r = spawnSync(process.execPath, ['scripts/build-userscript.js'], { encoding: 'utf8' });
    assert.equal(r.status, 0, `build 不該中斷：${r.stderr}`);
    assert.match(r.stderr, /clan\.local\.json: "Expand \/ Collapse" 在 clan 頁譯「展開／收合（測試）」，全站是「展開／收合」/);
  } finally {
    fs.writeFileSync(file, orig);
    spawnSync(process.execPath, ['scripts/build-userscript.js']);   // 把 dist 重建回乾淨狀態
  }
});
