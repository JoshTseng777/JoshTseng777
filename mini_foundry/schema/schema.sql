-- Mini-Foundry 資料庫結構
-- 三表正規化：lots（lot 主檔）/ route_steps（route 主檔）/ events（事件表）
-- 停留時間、當前狀態、當前站點一律為查詢時推導值，不落地儲存於本檔任何表中

CREATE TYPE lot_type_enum AS ENUM ('normal', 'hot');
CREATE TYPE event_type_enum AS ENUM ('track_in', 'track_out', 'hold', 'release');

-- route_steps：route 主檔，迴圈以展開後的明確步驟存放，不存迴圈邏輯本身
-- 下一站一律由 seq+1 推導，本表不設「下一站」欄位
CREATE TABLE route_steps (
    product_id  VARCHAR(32)  NOT NULL,
    seq         INTEGER      NOT NULL CHECK (seq > 0),
    layer       VARCHAR(16)  NOT NULL,
    loop_code   VARCHAR(16),
    step_name   VARCHAR(100) NOT NULL,
    PRIMARY KEY (product_id, seq)
);

COMMENT ON TABLE route_steps IS 'Route 主檔：每 product 的展開式製程步驟';
COMMENT ON COLUMN route_steps.product_id IS '產品代碼';
COMMENT ON COLUMN route_steps.seq IS '製程順序，嚴格遞增，不可跳號';
COMMENT ON COLUMN route_steps.layer IS '層別，如 L1、L2';
COMMENT ON COLUMN route_steps.loop_code IS '迴圈識別碼，如 02FB（同一迴圈的展開步驟共用此碼）';
COMMENT ON COLUMN route_steps.step_name IS '工序描述，如 Core LTH LDI曝光';

-- lots：lot 主檔，每 lot 一筆
-- product_id 邏輯對應 route_steps.product_id；因 route_steps 主鍵為複合鍵
-- (product_id, seq)，product_id 單獨並非唯一鍵，故不設實體外鍵約束，
-- 改由 simulator / pytest 驗證一致性（見 implementation-notes.md「Deviations」）
CREATE TABLE lots (
    lot_id      VARCHAR(32)   PRIMARY KEY,
    product_id  VARCHAR(32)   NOT NULL,
    lot_type    lot_type_enum NOT NULL,
    qty_initial INTEGER       NOT NULL CHECK (qty_initial > 0),
    module      VARCHAR(50)   NOT NULL,
    section     VARCHAR(50)   NOT NULL,
    created_at  TIMESTAMP     NOT NULL
);

COMMENT ON TABLE lots IS 'Lot 主檔：每 lot 一筆';
COMMENT ON COLUMN lots.lot_id IS 'Lot 編號';
COMMENT ON COLUMN lots.product_id IS '產品代碼（邏輯對應 route_steps.product_id）';
COMMENT ON COLUMN lots.lot_type IS 'Lot 類型：normal（一般）/ hot（急件）';
COMMENT ON COLUMN lots.qty_initial IS '投入片數';
COMMENT ON COLUMN lots.module IS '模組，如 製二部';
COMMENT ON COLUMN lots.section IS '課別，如 線路課';
COMMENT ON COLUMN lots.created_at IS 'Lot 建立時間';

-- events：事件表，僅存事實，不存任何推導值（停留時間 / 當前狀態 / 當前站點皆為查詢時計算）
CREATE TABLE events (
    event_id    BIGSERIAL        PRIMARY KEY,
    lot_id      VARCHAR(32)      NOT NULL REFERENCES lots (lot_id),
    product_id  VARCHAR(32)      NOT NULL,
    seq         INTEGER          NOT NULL,
    event_type  event_type_enum  NOT NULL,
    qty         INTEGER          NOT NULL CHECK (qty >= 0),
    event_time  TIMESTAMP        NOT NULL,
    FOREIGN KEY (product_id, seq) REFERENCES route_steps (product_id, seq)
);

COMMENT ON TABLE events IS '事件表：僅存事實，停留時間/當前狀態/當前站點一律查詢時推導';
COMMENT ON COLUMN events.event_id IS '事件編號';
COMMENT ON COLUMN events.lot_id IS 'Lot 編號';
COMMENT ON COLUMN events.product_id IS '產品代碼（搭配 seq 對應 route_steps）';
COMMENT ON COLUMN events.seq IS '製程順序（對應 route_steps.seq）';
COMMENT ON COLUMN events.event_type IS '事件類型：track_in / track_out / hold / release';
COMMENT ON COLUMN events.qty IS '該事件當下片數（報廢扣片反映於此，僅能遞減）';
COMMENT ON COLUMN events.event_time IS '事件發生時間';

CREATE INDEX idx_events_lot_time ON events (lot_id, event_time);
CREATE INDEX idx_events_product_seq ON events (product_id, seq);
