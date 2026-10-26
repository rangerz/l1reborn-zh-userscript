# AGENTS.md

給在此 repo 工作的 AI agent 或協作者。

## 不能破壞的原則

- **英文原文必須留在 DOM 原位**，中文只能透過 CSS 疊上去。不要改成直接改 `textContent`。唯一例外是 `<option>`（原生下拉不畫 `::before`），用 `label` 屬性顯示中文。
- **play 子站不處理**：腳本只 `@match` 官網，不要重新加回 play.lineage1reborn.com。
- `dist/` 是建置產物，改 `src/` 或 `data/` 後跑 `npm run build`，不要手改。

## 目錄

```text
src/main.js                  userscript 入口（翻譯、切換按鈕、MutationObserver）
src/lookup.js                字典查詢（完全相符 + {n} 數字 pattern），build 時內嵌
data/translations/*.json     字典：common、site（官網）
data/translations/pages/     主站各頁字典（檔名對應 ?page=），build 時併入 site
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
- key 可帶 `{n}` 比對數字（含 `,` `.`），譯文的 `{n}` 依序換成比對到的數字；`{*}` 比對任意片段，片段再用字典完全相符查一次（查不到原樣放回）。查詢邏輯在 `src/lookup.js`。
- **譯文用台版天堂遊戲內的名詞**，不要一般直譯。技能名以本 repo 的 `data/reference/skills.json` 為準（已人工 review，不要再用 l1justice 的 skills.json）；地圖、物品名以 [l1justice-zh-userscript](https://github.com/rangerz/l1justice-zh-userscript) 的 `data/translations/terms.json`、`maps.json` 為準；查不到的保留英文，不要自己發明。
  - 已確認：karma＝友好度、Lawful＝正義值、Healing Potion＝治癒藥水、buff＝輔助魔法、Cancel＝魔法相消術、pledge leader＝盟主、sub-leader＝副盟主、guardian＝守護騎士、emblem＝盟徽、global chat＝全體頻道、exclude＝拒絕名單、bookmark＝記憶座標、EXP＝經驗值、Giran＝奇岩、Werldern＝威頓、Forgotten Island＝遺忘之島、Dream Island＝夢幻之島、Abyss Lake＝地底湖、Fire Valley＝火龍窟、Einhasad＝殷海薩（Einhasad Blessing＝殷海薩的祝福）。
