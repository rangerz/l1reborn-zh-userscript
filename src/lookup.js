// 字典查詢。key 可帶 {n} 代表一串數字（"Show all {n} updates"），譯文裡的 {n} 會換成比對到的數字。
// 先查完全相符，再逐條試 pattern；build 會把這支內嵌進產物，test 直接 import。
export function makeLookup(table) {
  const patterns = Object.keys(table).filter(k => k.includes('{n}')).map(k => ({
    re: new RegExp('^' + k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\\\{n\\\}/g, '(\\d[\\d,.]*)') + '$'),
    zh: table[k],
  }));
  return text => {
    text = text.replace(/\s+/g, ' ').trim();
    if (Object.hasOwn(table, text)) return table[text];
    for (const { re, zh } of patterns) {
      const m = text.match(re);
      if (m) { let i = 0; return zh.replace(/\{n\}/g, () => m[++i]); }
    }
  };
}
