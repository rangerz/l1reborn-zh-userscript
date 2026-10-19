// 字典查詢。key 可帶兩種佔位：
//   {n}  一串數字（含 , .），例 "Show all {n} updates" → "顯示全部 {n} 則更新"
//   {*}  任意文字，抓到的那段會再用字典「完全相符」查一次（查不到就原樣放回），
//        例 "Lv {n} · {*}" 搭配 "Mainland Aden": "亞丁大陸" → "Lv 60 · 亞丁大陸"
// 先查完全相符，再逐條試 pattern；build 會把這支內嵌進產物，test 直接 import。
// 「Oct 18, 2026 11:06 PM ET」→「2026/10/18 23:06 ET」：月份名與 AM/PM 沒辦法用 {n} pattern 表達，字典查不到時才走這裡。
// 時間與 ET 可省略（只有日期時 → 2026/10/18）。
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const DATE_RE = new RegExp(`^(${MONTHS.join('|')}) (\\d{1,2}), (\\d{4})(?: (\\d{1,2}):(\\d{2}) (AM|PM)( ET)?)?$`);
function dateZh(text) {
  const m = text.match(DATE_RE);
  if (!m) return;
  const date = `${m[3]}/${MONTHS.indexOf(m[1]) + 1}/${+m[2]}`;
  if (!m[4]) return date;
  const hour = (+m[4] % 12) + (m[6] === 'PM' ? 12 : 0);
  return `${date} ${String(hour).padStart(2, '0')}:${m[5]}${m[7] ?? ''}`;
}

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
    return dateZh(text);
  };
}
