import test from 'node:test';
import assert from 'node:assert/strict';
import { makeLookup } from '../src/lookup.js';

test('lookup：完全相符與 {n} 數字 pattern', () => {
  const lookup = makeLookup({ 'Log in': '登入', 'Show all {n} updates': '顯示全部 {n} 則更新', '{n} of {n} (beta)': '第 {n} / {n} 個（beta）' });
  assert.equal(lookup('  Log\n in '), '登入');
  assert.equal(lookup('Show all 17 updates'), '顯示全部 17 則更新');
  assert.equal(lookup('Show all 18,822 updates'), '顯示全部 18,822 則更新');
  assert.equal(lookup('3 of 10 (beta)'), '第 3 / 10 個（beta）');
  assert.equal(lookup('Show all updates'), undefined);
  assert.equal(lookup('constructor'), undefined);
});

test('lookup：{n} 後面接單位字面（In 3d、Reign · 13d、18m 02s）', () => {
  const lookup = makeLookup({ 'In {n}d': '{n} 天後', 'Reign · {n}d': '在位 {n} 天', '{n}m {n}s': '{n} 分 {n} 秒' });
  assert.equal(lookup('In 3d'), '3 天後');
  assert.equal(lookup('In 0d'), '0 天後');
  assert.equal(lookup('Reign · 13d'), '在位 13 天');
  assert.equal(lookup('18m 02s'), '18 分 02 秒');
  assert.equal(lookup('In d'), undefined);      // 沒數字不翻
  assert.equal(lookup('3d'), undefined);        // 要整串相符，不吃子字串
});

test('lookup：{*} 抓到的片段再用字典完全相符查一次', () => {
  const lookup = makeLookup({ 'Lv {n} · {*}': 'Lv {n} · {*}', 'Lv {n}–{n} · {*}': 'Lv {n}–{n} · {*}', '{*} only (self-cast)': '僅限{*}（自己施放）', 'Mainland Aden': '亞丁大陸', 'Knight': '騎士' });
  assert.equal(lookup('Lv 60 · Mainland Aden'), 'Lv 60 · 亞丁大陸');
  assert.equal(lookup('Lv 60 · Act II Desert'), 'Lv 60 · Act II Desert');   // 片段查不到就原樣放回
  assert.equal(lookup('Lv 60–70 · Mainland Aden'), 'Lv 60–70 · 亞丁大陸');
  assert.equal(lookup('Knight only (self-cast)'), '僅限騎士（自己施放）');
  assert.equal(lookup('Mainland Aden'), '亞丁大陸');
});

test('lookup：英文日期時間轉 24 小時制（Oct 18, 2026 11:06 PM ET）', () => {
  const lookup = makeLookup({});
  assert.equal(lookup('Oct 18, 2026 11:06 PM ET'), '2026/10/18 23:06 ET');
  assert.equal(lookup('Oct 9, 2026 12:05 AM ET'), '2026/10/9 00:05 ET');
  assert.equal(lookup('Dec 1, 2026 12:30 PM ET'), '2026/12/1 12:30 ET');
  assert.equal(lookup('Oct 11, 2026'), '2026/10/11');
  assert.equal(lookup('Foo 11, 2026'), undefined);
});
