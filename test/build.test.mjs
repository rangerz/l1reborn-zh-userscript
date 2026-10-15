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
  const dict = JSON.parse(out.match(/const DICT = ([\s\S]*?);\n\nconst IS_PLAY/)[1]);
  assert.equal(dict.local['auction-house'].Buy, '購買');
  assert.ok(!('Buy' in dict.site), 'local key 漏進全站字典');
});
