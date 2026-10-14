// 字典查詢。key 可帶兩種佔位：
//   {n}  一串數字（含 , .），例 "Show all {n} updates" → "顯示全部 {n} 則更新"
//   {*}  任意文字，抓到的那段會再用字典「完全相符」查一次（查不到就原樣放回），
//        例 "Lv {n} · {*}" 搭配 "Mainland Aden": "亞丁大陸" → "Lv 60 · 亞丁大陸"
// 先查完全相符，再逐條試 pattern；build 會把這支內嵌進產物，test 直接 import。
export function makeLookup(table) {
  const exact = text => (Object.hasOwn(table, text) ? table[text] : undefined);
  const patterns = Object.keys(table).filter(k => /\{[n*]\}/.test(k)).map(k => ({
    re: new RegExp('^' + k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      .replace(/\\\{n\\\}/g, '(\\d[\\d,.]*)')
      .replace(/\\\{\\\*\\\}/g, '(.+?)') + '$'),
    zh: table[k],
  }));
  return text => {
    text = text.replace(/\s+/g, ' ').trim();
    const hit = exact(text);
    if (hit !== undefined) return hit;
    for (const { re, zh } of patterns) {
      const m = text.match(re);
      if (m) { let i = 0; return zh.replace(/\{[n*]\}/g, () => { const v = m[++i]; return exact(v) ?? v; }); }
    }
  };
}
