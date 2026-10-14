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
| `lineage1reborn.com` | 文字節點包成 `<span class="l1r-zh" data-zh="…"><span class="l1r-en">English</span></span>`，`.l1r-en` 隱藏、中文由外層 `::before` 畫出 | 傳統 PHP 頁 + 局部換頁，可以安全動 DOM；字級、行高完全繼承原樣式 |
| `play.lineage1reborn.com` | 只在「元素內只有一個文字節點」時掛 `data-l1r-zh`，元素 `font-size:0`、中文由 `::before` 以原字級畫出 | React 客戶端，搬動文字節點會讓 React 之後的 `removeChild` / `insertBefore` 炸掉；混合內容（如 `<label>Account<input>`）目前先留英文 |

兩站都用 `MutationObserver` 跟著動態載入的內容翻；站方 JS 原地改字時會同步更新或撤掉中文。

## 開發

```bash
npm run build   # 產出 dist/l1reborn-zh.user.js
npm run watch   # 監看 src/ 與 data/ 自動重建
npm test        # build + 檢查產物是合法 userscript
```

- `src/main.js`：執行入口，build 時包進 IIFE，`__DICT__` 由字典填入。
- `data/translations/*.json`：字典，key 是頁面上的英文原文（trim、連續空白收成一個），value 是中文。
  - `common.json` 兩站共用，`site.json` 只給主站，`play.json` 只給 play 子站。
- `scripts/build-userscript.js`：組 header + 字典 + `src/main.js`，輸出到 `dist/`。
- `dist/` 是建置產物，不要手動編輯。

### 加翻譯

1. 在對應的 json 加一行 `"English text": "中文"`。
2. `npm run build`，到 Tampermonkey 重新安裝 `dist/l1reborn-zh.user.js`（或開發時改用 Tampermonkey 的 file:// 載入）。

目前先做按鈕、連結、短標題；長句之後再補。
