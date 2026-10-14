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
