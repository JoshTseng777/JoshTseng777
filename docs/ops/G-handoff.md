# G｜交接檔（本制度的唯一真相來源）

> 30 秒摘要：這份檔案記錄本次「Fable 5 建制度」任務的即時進度、假設、放棄項與風險。
> 中斷後接手的任何 session（不論模型），**先讀這份檔，不要重讀舊對話**。

最後更新：2026-07-04（session 進行中，持續 append）

---

## 0. 開場決策（AskUserQuestion 兩次呼叫皆因串流錯誤失敗，視同使用者未回覆，依指示採預設值）

| # | 問題 | 採用值（預設） | 理由 |
|---|---|---|---|
| 1 | evidence/ 缺失時 A 診斷怎麼辦 | 用通用知識寫「推測」診斷 + 建立 evidence/ 蒐集範本 | 使用者原 prompt 預設選項第一項；空白 A 對弱模型無立即價值 |
| 2 | 制度服務範圍 | 通用範本，此 repo（JoshTseng777/JoshTseng777）作主控中心 | repo 目前只是 profile README，無專案內容，通用化才有意義 |
| 3 | 最弱消費者 | Haiku 4.5（`claude-haiku-4-5-20251001`） | 使用者原留空「Sonnet 或 Haiku」，取更低下限，Sonnet 自動涵蓋 |
| 4 | 停損門檻 | 純用 context 用量 60%/80%，不另設輪數/時間上限 | 使用者原 prompt 預設選項第一項；本環境無可靠輪數計時介面 |
| 5（未列入 4 題上限，直接依標準流程處理） | 完成後是否 push | commit + push 到 `claude/fable-5-system-design-l3yrey` | 系統層 Git 規則已預設此流程為標準收尾動作 |

**風險標記**：以上 1–4 項是「未經使用者確認的預設假設」，不是使用者親自選擇。若使用者之後回來，第一件事應該是請他們確認/覆核這 4 項，尤其是「最弱消費者=Haiku」會影響所有文件的用詞簡化程度。

---

## 1. 盤點結果（inventory）

**查到什麼：**
- repo `JoshTseng777/JoshTseng777` 是 GitHub profile README repo，只有一個 `README.md`（自我介紹，提到對 data analytics / data science 有興趣），git log 只有一個 commit "Create README.md"。
- 分支：`main`（含 README）、`claude/fable-5-system-design-l3yrey`（本次工作分支，已切換）。
- repo 內完全沒有 `evidence/`、`drafts/`、`CLAUDE.md`、`.claude/agents/`。
- 環境內 `~/.claude/` 存在，但沒有 `agents/` 子目錄（尚未建立過任何 subagent 定義檔），故無法直接讀到一份真實的 frontmatter 範例來核對「reasoning effort 逐 agent 指定」的確切 YAML 欄位名稱。
- **Agent 工具本身的 schema 說明文字**（本 session 系統層工具定義，非猜測）明確寫："Each agent type's model, reasoning effort, and tool access are set in its definition (`.claude/agents/*.md` frontmatter, or the SDK `agents` option)" → 這是本 session 內可直接查證的一手依據，證實「reasoning effort 可逐 agent 設定」為真，但**確切 frontmatter 鍵名未見過真實檔案樣本**，标记為「機制存在已證實、鍵名待實測」。
- Agent 工具的 `model` 參數 enum 只接受：`sonnet`、`opus`、`haiku`、`fable`（通用別名，非完整 API 字串），省略則沿用 agent 定義的 model 或繼承父層。
- **模型 ID 字串**：本 session 系統提示（環境注入，非我方猜測）明確列出：
  - Fable 5 → `claude-fable-5`
  - Opus 4.8 → `claude-opus-4-8`
  - Sonnet 5 → `claude-sonnet-5`
  - Haiku 4.5 → `claude-haiku-4-5-20251001`
  - **與使用者原 prompt 的「已查證起手值」不一致**：使用者寫的是 `claude-sonnet-4-6`、`claude-haiku-4-5`（無日期後綴）。本 session 系統注入值時間戳更新（今日 2026-07-04），判定為目前較可信的來源，**採用系統注入值**，並在 C 文件中明確標註此落差，提醒使用者之後若發現失效要重新查證。
- 現有 subagent 類型（本 session 可用列表）：`claude`（catch-all）、`claude-code-guide`、`Explore`、`general-purpose`、`Plan`、`statusline-setup`。**沒有觀察到內建 "opus"/"haiku"/"sonnet" 專屬 catch-all agent type**——model 覆寫是透過 `Agent` 工具的 `model` 參數（sonnet/opus/haiku/fable），套用在上述任一 subagent_type 上，而不是靠選不同 agent 類型來換模型。這點對 C 文件很重要：**指定模型的方法是 `Agent({model: "haiku", subagent_type: "general-purpose", ...})`，不是尋找一個叫 "Haiku agent" 的東西。**
- 可用 skills 列表（本 session）：session-start-hook、dataviz、artifact-design、update-config、keybindings-help、verify、code-review、simplify、fewer-permission-prompts、loop、claude-api、run、init、review、security-review。
- MCP：GitHub MCP 一度連線／斷線（此 session 內不穩定，出現斷線系統提醒）；`claude-code-remote`（bf7c680d-... 前綴）用於 trigger/schedule/repo 管理。

**假設什麼（未驗證，已依規則 6 標記，不當事實寫入 A/C/D/B/E/F 本文）：**
- reasoning effort 的 frontmatter 確切鍵名（例如是否叫 `effort` 或其他名稱）——未見真實檔案，C 文件內會寫「待使用者以一份真實 agent 檔案實測確認鍵名」。
- Opus 4.8 額度計算方式、是否/如何被安全機制導向——依使用者前提，全文一律標「未確認，建議到 usage 儀表板實測」，不寫死任何數字。

**查不到什麼：**
- 沒有任何 evidence/（過往失敗片段、CLAUDE.md 本體）可供一手研讀，因此 A 診斷無法引用「檔案:行號」等級的真實案例。
- 沒有 drafts/，因此不適用「你是審稿人」模式，本次是從零產出（作者模式）。

---

## 2. 待辦追蹤（隨做隨勾）

- [x] 盤點環境
- [x] 建立 G 骨架
- [x] A｜快速診斷（推測性，標註清楚）→ `docs/ops/A-diagnosis.md`
- [x] evidence/ 蒐集範本（配合 A 的缺口）→ `evidence/README.md`
- [x] C｜模型調度守則 → `docs/ops/C-model-dispatch.md`
- [x] D｜判斷力外化（rubric/checklist）→ `docs/ops/D-judgment-rubrics.md`
- [x] F｜維護協議 → `docs/ops/F-maintenance.md`
- [x] B｜CLAUDE.md 重構 → `/CLAUDE.md`（39 行，索引 11 項）
- [x] E｜五份任務交辦範本 → `docs/ops/E-templates/{search,implement,refactor,research,review}.md`
- [ ] 收尾 1：對抗審查（fresh-context Sonnet subagent）
- [ ] 收尾 2：行為測試（Haiku subagent 實跑範本）
- [ ] 收尾 3：read-back 驗證每個檔案
- [ ] 收尾 4：一頁總結
- [ ] commit + push（第一批已完成，還需再 push 這批 B/E 完成的變更）

## 3. 放棄/延後項

（尚無）

## 3.5 派工結果（已驗收）

- B（CLAUDE.md）：Sonnet subagent 完成，39 行（限 150 行內），索引 11 項。我讀過全文，內容
  正確、索引齊全，語氣對 Haiku 友善。移除了原本「E-templates 若還沒寫完先照路徑用」的過渡性
  提示（E 完成後這句話已經沒必要）。
- E（五份範本）：Sonnet subagent 完成，search/implement/refactor/research/review 各 58–64 行。
  我親自全文讀過 implement.md 與 review.md（風險判斷最重的兩份），欄位設計一致、與 C/D 呼應
  正確、範例具體可執行，判定合格；另外三份用 `wc -l` + 開頭確認非空且格式一致，未逐字全讀。
  subagent 自己指出的風險：五份範本裡「本任務指定：＿＿＿」這格容易被漏填，等於看起來合法
  卻沒真的指定模型——已記錄，見下方「待辦追蹤」新增一項給 F 維護協議或未來 review 時檢查。

## 4. 中斷時必看

若中斷發生，先看本節最新的一條，再看「待辦追蹤」勾選狀態，直接從第一個未勾選項繼續，不必重讀對話紀錄。
