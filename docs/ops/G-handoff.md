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
- [x] B｜CLAUDE.md 重構 → `/CLAUDE.md`（37 行，索引 11 項）
- [x] E｜五份任務交辦範本 → `docs/ops/E-templates/{search,implement,refactor,research,review}.md`
- [x] 收尾 1：對抗審查（fresh-context Sonnet subagent）— 完成，找到並修正 5 類問題，詳見「3.6」。
- [x] 收尾 2：行為測試（Haiku 4.5 subagent 實跑範本）— 完成，通過，詳見「3.7」。
- [x] 收尾 3：read-back 驗證每個檔案 — 全部 12 個檔案 `wc -l` 確認非空、行數皆在上限內
  （CLAUDE.md 37 行 ≤150；`docs/ops/*.md` 各 47–96 行，皆 ≤500）；Haiku 行為測試已獨立驗證
  CLAUDE.md 索引表 11 個路徑全部存在。
- [x] 收尾 4：一頁總結 → 見本檔「5. 收尾三部分」；對使用者的精簡版總結見這次對話最後一則回覆
- [x] commit + push（全部完成）

## 3. 放棄/延後項

（尚無）

## 3.6 對抗審查結果（fresh-context Sonnet subagent，已抽查其修正屬實）

找到並直接修正：(1) A 診斷第1項第3點教弱模型用 `Explore` 做跨檔案比對，與 `Explore` 自身
說明文字矛盾，已改派 `general-purpose`；(2) F 文件懸空引用不存在的「B 文件」，已改指
`CLAUDE.md`本身；(3) G 檔行數誤植（實測 36 行，一度被改成「37 行」，我又修正一次為 36）；
(4) D 文件「本次 session」指涉不清，未來任何 session 讀到會誤以為指自己，已改「建置本套
制度那次 session」；(5) 五份 E-templates 的「本任務指定」留白欄補上後果說明（留白＝落到
Agent 呼叫當下預設值）。未動：G 檔裡 4 項未經使用者確認的預設假設，判斷屬架構選擇不該代拍板。

## 3.5 派工結果（已驗收）

- B（CLAUDE.md）：Sonnet subagent 完成，37 行，索引 11 項。我讀過全文，內容
  正確、索引齊全，語氣對 Haiku 友善。移除了原本「E-templates 若還沒寫完先照路徑用」的過渡性
  提示（E 完成後這句話已經沒必要）。
- E（五份範本）：Sonnet subagent 完成，search/implement/refactor/research/review 各 58–64 行。
  我親自全文讀過 implement.md 與 review.md（風險判斷最重的兩份），欄位設計一致、與 C/D 呼應
  正確、範例具體可執行，判定合格；另外三份用 `wc -l` + 開頭確認非空且格式一致，未逐字全讀。
  subagent 自己指出的風險：五份範本裡「本任務指定：＿＿＿」這格容易被漏填，等於看起來合法
  卻沒真的指定模型——已記錄，見下方「待辦追蹤」新增一項給 F 維護協議或未來 review 時檢查。

## 3.7 行為測試結果（Haiku 4.5 subagent，只給新文件、不給這次對話背景，實跑一個代表性任務）

任務：扮演全新 session，照 CLAUDE.md 流程確認 evidence/ 檔案數、A 診斷三項的標記狀態、
CLAUDE.md 索引表 11 個路徑是否都存在，並套用 `search.md` 範本重新表述這個任務。

結果：**通過**。三項查核全對（evidence/ 只有 1 個 README、A 診斷三項都正確標記「推測」、
11 個索引路徑全部存在）；套用 search.md 範本時正確處理了範本沒明講的邊界情況（任務由自己
執行、非派工時，「本任務指定」欄位填「N/A」並說明原因，判斷合理）。

唯一回饋：CLAUDE.md 原文「動手前先讀 G-handoff.md」與測試指令「不要讀這次對話之外的背景」
一度讓它猶豫（G-handoff 是「制度本身」還是「對話背景」不夠直觀），但自己想清楚後正確處理。
已採納建議，在 CLAUDE.md 該句後加註「（這份檔在 repo 內，是制度本身的一部分，不算舊對話）」。
這是本次唯一因行為測試而做的文件修正；判定為錦上添花的小澄清，不代表制度本身有結構性缺陷。

## 4. 中斷時必看

若中斷發生，先看本節最新的一條，再看「待辦追蹤」勾選狀態，直接從第一個未勾選項繼續，不必重讀對話紀錄。

---

## 5. 收尾三部分（任務規定格式）

**三件我沒被問但認為最重要的事：**

1. **這整套制度目前完全建立在「推測」和「示意例」上，沒有一筆真實案例。** 這不是缺陷，是
   誠實的起點——但它意味著 A 診斷和 D rubric 的價值現在主要來自「通用 agent 常見失效模式」的
   常識，還沒被這個 repo 的真實使用經驗驗證過。第一次真的遇到 Claude Code 犯錯，**務必**存一筆
   到 `evidence/`，這是整套制度從「推測」升級成「有憑有據」的唯一途徑，不會自動發生。
2. **模型 ID／reasoning effort 欄位這類「已查證」內容有效期很短。** 本次查證的
   `claude-haiku-4-5-20251001` 這類字串是今天（2026-07-04）這個環境當下注入的值，跟使用者原始
   prompt 裡的舊草稿值就已經不一致了——下次 session 開工時，第一件事應該是重新核對 C 文件的
   模型對照表是否還準，不要預設它永遠正確。
3. **這套制度目前只在「文件層面」驗證過（read-back + 一次 Haiku 行為測試），沒有經過真實的
   多任務、多 session 壓力測試。** 目前的信心來自「邏輯自洽、一次代表性任務跑得動」，不等於
   「長期高頻使用下不會出現沒預料到的邊界情況」——F 文件裡的「防過度遵循機制」設計了偵測
   手段（同一規則連續三次繞路就標記待刪），但這個機制本身也還沒被真實觸發驗證過。

**這套制度最可能的退化方式與預防法：**

- **退化方式 1：evidence/ 永遠是空的，A/D 永遠停在「推測」。** 沒有人會在忙著做正事的時候
  主動停下來寫案例檔。預防法：F 文件已把「存證據」列為隨時可做、不用先問的低成本動作；
  但真正的預防還是要靠使用者自己養成習慣，或考慮之後設一個定期（例如每週）的自動提醒去問
  「這週有沒有踩雷案例還沒存」。
- **退化方式 2：CLAUDE.md 被逐漸塞入內容，違反「只當索引」的定位。** 每次有新規則，最省事的
  做法就是直接往 CLAUDE.md 裡加一段，久了就會超過 150 行、變回一份大雜燴。預防法：F 文件已
  規定「CLAUDE.md 結構性改動要先問使用者」，且本檔案已經設下 150 行的具體數字上限，任何人
  改完都可以用 `wc -l` 五秒鐘自查，不需要主觀判斷。
- **退化方式 3：「待補」「示意例（非實錄）」這類過渡性標記被長期遺忘，變成永久掛著的免責
  聲明，沒人真的回頭升級成真實內容。** 預防法：F 文件的精簡門檻（`evidence/` 超過 15 個檔案
  或單一條目累積 3 個以上真實案例就該精簡）某種程度上會強迫回頭處理，但這是被動觸發，不是
  主動提醒——如果使用者想要更強的保證，可以之後加一個排程 trigger 定期問「A/D 裡還有幾個
  『推測』『示意例』還沒被真實案例取代」。

**誠實列出信心最低的產出、為什麼：**

1. **C 文件裡「reasoning effort 逐 agent frontmatter 欄位名稱」——信心低。** 只驗證到「機制
   存在」（Agent 工具說明文字寫明），沒有驗證到「確切欄位名稱叫什麼」，因為這個環境裡從頭到
   尾沒有出現過一份真實的 `.claude/agents/*.md` 檔案可以打開來看。C 文件已誠實標「待使用者
   實測」，但這代表 C 文件在「怎麼幫 subagent 設定推理強度」這件事上，目前只能講到機制層次，
   給不出操作層次的確切步驟。
2. **A 診斷的「前三名排序」——信心中低。** 三個診斷本身（token 浪費/失焦/自我認證未驗證）是
   對 coding agent 常見失效模式的合理常識，但「這三個在這個 repo 未來會是最常發生的」這個
   排序判斷，完全沒有這個 repo 自己的資料支撐——換一個排序（例如把「自我認證未驗證」排第一）
   同樣說得通，目前的順序更多是我主觀覺得「哪個後果較嚴重」，不是統計出來的。
3. **G 檔案「0. 開場決策」裡四項未經使用者確認的預設假設（尤其是『最弱消費者＝Haiku』）——
   信心中等。** `AskUserQuestion` 兩次都因串流錯誤沒能真正送達使用者，我是依照任務指示的
   「未回覆一律採預設值」在走，但這終究是我代替使用者做的選擇，不是使用者真正選的。如果
   使用者其實想要「Sonnet 是最低下限」，那麼所有文件目前的簡化程度可能比使用者真正需要的
   更保守（更囉唆、更多重複解釋），這點需要使用者回來親自確認才能解除。
