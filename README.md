# l1reborn-zh-userscript

[Lineage 1 Reborn](https://lineage1reborn.com/) 與瀏覽器客戶端 [play.lineage1reborn.com](https://play.lineage1reborn.com/) 的中文介面 Tampermonkey userscript。

翻譯不覆寫原文：英文字永遠留在 DOM 原位，中文只透過 CSS（`::before` + `attr()`）疊上去。右下角 **中 / EN** 按鈕可隨時切回英文，偏好存 `localStorage`。

## 安裝

1. 先裝 [Tampermonkey](https://www.tampermonkey.net/)。
2. **Chrome / Edge**：Manifest V3 起 userscript 預設不會執行，右鍵 Tampermonkey 圖示 → **Manage Extension** → 打開 **Allow User Scripts**（[官方說明](https://www.tampermonkey.net/faq.php?locale=en&q=Q209)）。
3. 點以下連結，Tampermonkey 會跳出安裝對話框：

   <https://raw.githubusercontent.com/rangerz/l1reborn-zh-userscript/main/dist/l1reborn-zh.user.js>

之後新版本會自動透過 `@updateURL` 拉更新。

## 運作方式

| 站 | 做法 | 原因 |
| --- | --- | --- |
| `lineage1reborn.com` | 文字節點包成 `<l1r-zh data-zh="…"><l1r-en>English</l1r-en></l1r-zh>`，`l1r-en` 隱藏、中文由外層 `::before` 畫出 | 傳統 PHP 頁 + 局部換頁，可以安全動 DOM；字級、行高完全繼承原樣式。用自訂元素而非 span，站方針對 `span` 的 CSS 才不會打到 |
| `play.lineage1reborn.com` | 只在「元素內只有一個文字節點」時掛 `data-l1r-zh`，元素 `font-size:0`、中文由 `::before` 以原字級畫出 | React 客戶端，搬動文字節點會讓 React 之後的 `removeChild` / `insertBefore` 炸掉；混合內容（如 `<label>Account<input>`）目前先留英文 |

兩站都用 `MutationObserver` 跟著動態載入的內容翻；站方 JS 原地改字時會同步更新或撤掉中文。`<option>` 是例外：原生下拉選單不畫 `::before`，改用 `label` 屬性顯示中文，英文仍留在 textContent。

## 開發

```bash
npm run build   # 產出 dist/l1reborn-zh.user.js
npm run watch   # 監看 src/ 與 data/ 自動重建
npm test        # build + 檢查產物是合法 userscript
```

- `src/main.js`：執行入口，build 時包進 IIFE，`__DICT__` 由字典填入。
- `src/lookup.js`：字典查詢，build 時內嵌進產物，`npm test` 直接測。
- `data/translations/*.json`：字典，key 是頁面上的英文原文（trim、連續空白收成一個），value 是中文。
  - `common.json` 兩站共用，`site.json` 只給主站，`play.json` 只給 play 子站。
  - 主站各頁的字串放 `pages/<page>.json`（檔名對應 `?page=`），build 時合併進 site；同一個英文在兩個檔譯得不一樣會擋下來。
  - key 可帶 `{n}` 代表一串數字，譯文裡的 `{n}` 會換成比對到的數字：`"Show all {n} updates": "顯示全部 {n} 則更新"`。
  - key 可帶 `{*}` 代表任意片段，抓到的片段會再用字典完全相符查一次：`"Lv {n} · {*}"` 搭配 `"Mainland Aden": "亞丁大陸"`，Boss 卡片的「Lv 60 · Mainland Aden」就會變「Lv 60 · 亞丁大陸」。
- `scripts/build-userscript.js`：組 header + 字典 + `src/main.js`，輸出到 `dist/`。
- `dist/` 是建置產物，不要手動編輯。

### 加翻譯

1. 在對應的 json 加一行 `"English text": "中文"`。
2. `npm run build`，到 Tampermonkey 重新安裝 `dist/l1reborn-zh.user.js`（或開發時改用 Tampermonkey 的 file:// 載入）。

### 加新頁面

`scripts/pagetool.py` 把「抓頁面 → 列出沒翻的字串 → 寫進 `pages/<page>.json`」串起來；`scripts/dopage.sh` 再接 build、test、commit、push，一頁一個 commit。

```bash
python3 scripts/pagetool.py fetch dev-team        # 抓 ?page=dev-team 到 .cache/pages/（已 gitignore）
python3 scripts/pagetool.py list dev-team         # 列出這頁還沒翻的文字節點，查表能自動翻的標 [auto]
python3 scripts/pagetool.py apply dev-team my.py  # 套字典寫入 pages/dev-team.json，印出剩下沒翻的
scripts/dopage.sh dev-team my.py                  # 同上 + build + test + commit + push
```

- 字典 `my.py` 是普通 Python 檔，放哪裡都行（不用進 repo，JSON 才是正本）。`M` 放完全相符的譯文，`PATTERNS` 放含 `{n}`／`{*}` 的 key；`EMO` 是去掉開頭 emoji 的 key，套用時會把 emoji 補回去。其他選項（`EXTRA_PAGES`、`USE_MAPS`、`USE_MONSTERS`、`USE_SKILLS`、`ITEMS`、`FORCE`）見檔頭說明。
- 道具、怪物、技能、地圖名稱會自動查 [l1justice-zh-userscript](https://github.com/rangerz/l1justice-zh-userscript) 的對照表（預設在同層目錄，或用 `L1JUSTICE_DIR` 指定）；表上錯配的統一在 `pagetool.py` 的 `ITEM_FIX` 覆寫。日期時間會轉成「10/9（五）13:00 ET」。
- 抓頁面要帶瀏覽器 UA，連抓二十幾頁會被站方限流（「Too many anonymous requests」），等幾分鐘再抓。需要登入的頁只抓得到登入表單。
- 跨頁共用的字串放第一個碰到的頁檔就好，build 會合併；但同一英文在兩個檔譯法不同會讓 build 擋下，`dopage.sh` 會印出是哪一條。
- 以「…」結尾的 key 是官網目錄預覽（英文切在 180 字），譯文也要在對應位置截斷並加「…」。
