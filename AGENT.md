# AGENT.md

給在此 repo 工作的 AI agent 或協作者。

## 不能破壞的原則

- **英文原文必須留在 DOM 原位**，中文只能透過 CSS 疊上去。不要改成直接改 `textContent`。
- **play 子站是 React**，不要把文字節點包進新元素、不要搬動 React 建的節點；只能加屬性、加 sibling。
- `dist/` 是建置產物，改 `src/` 或 `data/` 後跑 `npm run build`，不要手改。

## 目錄

```text
src/main.js                  userscript 入口（翻譯、切換按鈕、MutationObserver）
data/translations/*.json     字典：common（兩站）、site（主站）、play（play 子站）
scripts/build-userscript.js  組 header + 字典 + src → dist/l1reborn-zh.user.js
test/build.test.mjs          build 後檢查產物合法
```

## 指令

```bash
npm run build / npm run watch / npm test
```

## 字典規則

- key = 頁面上的英文原文，先 trim、連續空白收成一個；build 會擋不合規的 key。
- HTML entity 以解碼後為準（`&amp;` → `&`）。
- 同一個英文在兩站意思不同時，分別放 `site.json` / `play.json`。
