CREATE TABLE IF NOT EXISTS "general" (
    id TEXT PRIMARY KEY NOT NULL,
    value bytea not null
);

CREATE TABLE IF NOT EXISTS "trader" (
    id TEXT PRIMARY KEY NOT NULL,
    instance_id UUID
);

CREATE TABLE IF NOT EXISTS "account" (
  id TEXT PRIMARY KEY NOT NULL
);

CREATE TABLE IF NOT EXISTS "client" (
    id TEXT PRIMARY KEY NOT NULL
);

CREATE TABLE IF NOT EXISTS "strategy" (
  id TEXT PRIMARY KEY NOT NULL,
  order_id_tag TEXT,
  oms_type TEXT,
  manage_contingent_orders BOOLEAN,
  manage_gtd_expiry BOOLEAN
);

CREATE TABLE IF NOT EXISTS "currency" (
    id TEXT PRIMARY KEY NOT NULL,
    precision INTEGER,
    iso4217 INTEGER,
    name TEXT,
    currency_type CURRENCY_TYPE
);

CREATE TABLE IF NOT EXISTS "instrument" (
    id TEXT PRIMARY KEY NOT NULL,
    kind TEXT,
    raw_symbol TEXT NOT NULL,
    asset_class ASSET_CLASS,
    underlying TEXT,
    base_currency TEXT REFERENCES currency(id),
    quote_currency TEXT REFERENCES currency(id),
    settlement_currency TEXT REFERENCES currency(id),
    isin TEXT,
    exchange TEXT,
    option_kind TEXT,
    strike_price TEXT,
    activation_ns TEXT,
    expiration_ns TEXT,
    price_precision INTEGER NOT NULL ,
    size_precision INTEGER,
    price_increment TEXT NOT NULL,
    size_increment TEXT,
    is_inverse BOOLEAN DEFAULT FALSE,
    multiplier TEXT,
    lot_size TEXT,
    max_quantity TEXT,
    min_quantity TEXT,
    max_notional TEXT,
    min_notional TEXT,
    max_price TEXT,
    min_price TEXT,
    margin_init TEXT NOT NULL,
    margin_maint TEXT NOT NULL,
    maker_fee TEXT NULL,
    taker_fee TEXT NULL,
    ts_event TEXT NOT NULL,
    ts_init TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "order" (
    id TEXT PRIMARY KEY NOT NULL,
    trader_id TEXT REFERENCES trader(id) ON DELETE CASCADE,
    strategy_id TEXT NOT NULL,
    instrument_id TEXT REFERENCES instrument(id) ON DELETE CASCADE,
    client_order_id TEXT NOT NULL,
    venue_order_id TEXT,
    position_id TEXT,
    account_id TEXT,  -- REFERENCES account(id) ON DELETE CASCADE,
    last_trade_id TEXT,
    order_type TEXT NOT NULL,
    order_side TEXT NOT NULL,
    quantity TEXT NOT NULL,
    price TEXT,
    trigger_price TEXT,
    trigger_type TEXT,
    limit_offset TEXT,
    trailing_offset TEXT,
    trailing_offset_type TEXT,
    time_in_force TEXT NOT NULL,
    expire_time TEXT,
    filled_qty TEXT DEFAULT '0',
    liquidity_side TEXT,
    avg_px DOUBLE PRECISION,
    slippage DOUBLE PRECISION,
    commissions TEXT[],
    status TEXT NOT NULL,
    is_post_only BOOLEAN,
    is_reduce_only BOOLEAN,
    is_quote_quantity BOOLEAN,
    display_qty TEXT,
    emulation_trigger TEXT,
    trigger_instrument_id TEXT,
    contingency_type TEXT,
    order_list_id TEXT,
    linked_order_ids TEXT[],
    parent_order_id TEXT,
    exec_algorithm_id TEXT,
    exec_algorithm_params JSONB,
    exec_spawn_id TEXT,
    tags TEXT[],
    init_id TEXT NOT NULL,
    ts_init TEXT NOT NULL,
    ts_last TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "order_event" (
    id TEXT PRIMARY KEY NOT NULL,
    kind TEXT NOT NULL,
    trader_id TEXT REFERENCES trader(id) ON DELETE CASCADE,
    strategy_id TEXT NOT NULL,
    instrument_id TEXT REFERENCES instrument(id) ON DELETE CASCADE,
    client_order_id TEXT NOT NULL,
    client_id TEXT REFERENCES client(id) ON DELETE CASCADE,
    reason TEXT,
    trade_id TEXT,
    currency TEXT REFERENCES currency(id),
    order_type TEXT,
    order_side TEXT,
    quantity TEXT,
    time_in_force TEXT,
    liquidity_side TEXT,
    post_only BOOLEAN DEFAULT FALSE,
    reduce_only BOOLEAN DEFAULT FALSE,
    quote_quantity BOOLEAN DEFAULT FALSE,
    reconciliation BOOLEAN DEFAULT FALSE,
    price TEXT,
    last_px TEXT,
    last_qty TEXT,
    trigger_price TEXT,
    trigger_type TEXT,
    limit_offset TEXT,
    trailing_offset TEXT,
    trailing_offset_type TRAILING_OFFSET_TYPE,
    expire_time TEXT,
    display_qty TEXT,
    emulation_trigger TEXT,
    trigger_instrument_id TEXT,
    contingency_type TEXT,
    order_list_id TEXT,
    linked_order_ids TEXT[],
    parent_order_id TEXT,
    exec_algorithm_id TEXT,
    exec_algorithm_params JSONB,
    exec_spawn_id TEXT,
    venue_order_id TEXT,
    account_id TEXT,
    position_id TEXT,
    commission TEXT,
    tags TEXT[],
    ts_event TEXT NOT NULL,
    ts_init TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "position"(
    id TEXT PRIMARY KEY NOT NULL,
    trader_id TEXT REFERENCES trader(id) ON DELETE CASCADE,
    strategy_id TEXT NOT NULL,
    instrument_id TEXT REFERENCES instrument(id) ON DELETE CASCADE,
    account_id TEXT NOT NULL,
    opening_order_id TEXT NOT NULL,
    closing_order_id TEXT,  -- REFERENCES TBD
    entry TEXT NOT NULL,
    side TEXT NOT NULL,
    signed_qty DOUBLE PRECISION NOT NULL,
    quantity TEXT NOT NULL,
    peak_qty TEXT NOT NULL,
    quote_currency TEXT NOT NULL,
    base_currency TEXT,
    settlement_currency TEXT NOT NULL,
    avg_px_open DOUBLE PRECISION NOT NULL,
    avg_px_close DOUBLE PRECISION,
    realized_return DOUBLE PRECISION,
    realized_pnl TEXT,
    unrealized_pnl TEXT,
    commissions TEXT[],
    duration_ns TEXT,
    ts_opened TEXT NOT NULL,
    ts_closed TEXT,
    ts_init TEXT NOT NULL,
    ts_last TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "account_event"(
    id TEXT PRIMARY KEY NOT NULL,
    kind TEXT NOT NULL,
    account_id TEXT REFERENCES account(id) ON DELETE CASCADE,
    base_currency TEXT REFERENCES currency(id),
    balances JSONB,
    margins JSONB,
    is_reported BOOLEAN DEFAULT FALSE,
    ts_event TEXT NOT NULL,
    ts_init TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "trade" (
    id BIGSERIAL PRIMARY KEY NOT NULL,
    instrument_id TEXT REFERENCES instrument(id) ON DELETE CASCADE,
    price TEXT NOT NULL,
    quantity TEXT NOT NULL,
    aggressor_side AGGRESSOR_SIDE,
    venue_trade_id TEXT,
    ts_event TEXT NOT NULL,
    ts_init TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "quote" (
    id BIGSERIAL PRIMARY KEY NOT NULL,
    instrument_id TEXT REFERENCES instrument(id) ON DELETE CASCADE,
    bid_price TEXT NOT NULL,
    ask_price TEXT NOT NULL,
    bid_size TEXT NOT NULL,
    ask_size TEXT NOT NULL,
    ts_event TEXT NOT NULL,
    ts_init TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "bar" (
    id BIGSERIAL PRIMARY KEY NOT NULL,
    instrument_id TEXT REFERENCES instrument(id) ON DELETE CASCADE,
    step INTEGER NOT NULL,
    bar_aggregation BAR_AGGREGATION NOT NULL,
    price_type PRICE_TYPE NOT NULL,
    aggregation_source AGGREGATION_SOURCE NOT NULL,
    open TEXT NOT NULL,
    high TEXT NOT NULL,
    low TEXT NOT NULL,
    close TEXT NOT NULL,
    volume TEXT NOT NULL,
    ts_event TEXT NOT NULL,
    ts_init TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "signal" (
    id BIGSERIAL PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    ts_event TEXT NOT NULL,
    ts_init TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "custom" (
    id BIGSERIAL PRIMARY KEY NOT NULL,
    data_type TEXT NOT NULL,
    metadata JSONB NOT NULL,
    identifier TEXT NOT NULL,
    value JSONB NOT NULL,
    ts_event TEXT NOT NULL,
    ts_init TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

------------------- BLOCKCHAIN -------------------

CREATE TABLE IF NOT EXISTS "chain" (
    chain_id INTEGER PRIMARY KEY NOT NULL,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS "block" (
    chain_id INTEGER NOT NULL REFERENCES chain(chain_id) ON DELETE CASCADE,
    number BIGINT NOT NULL,
    hash TEXT,
    parent_hash TEXT,
    miner TEXT,
    gas_limit BIGINT,
    gas_used BIGINT,
    timestamp TEXT,
    base_fee_per_gas TEXT,
    blob_gas_used TEXT,
    excess_blob_gas TEXT,
    l1_gas_price TEXT,
    l1_gas_used BIGINT,
    l1_fee_scalar BIGINT,
    PRIMARY KEY (chain_id, number)
) PARTITION BY LIST (chain_id);
CREATE TABLE IF NOT EXISTS "block_default" PARTITION OF "block" DEFAULT;

CREATE TABLE IF NOT EXISTS "token"(
    chain_id INTEGER NOT NULL REFERENCES chain(chain_id) ON DELETE CASCADE,
    address TEXT NOT NULL,
    symbol TEXT,
    name TEXT,
    decimals INTEGER,
    error TEXT,
    PRIMARY KEY (chain_id, address)
) PARTITION BY LIST (chain_id);
CREATE TABLE IF NOT EXISTS "token_default" PARTITION OF "token" DEFAULT;

CREATE TABLE IF NOT EXISTS "dex" (
    chain_id INTEGER NOT NULL REFERENCES chain(chain_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    factory_address TEXT NOT NULL,
    creation_block BIGINT NOT NULL,
    last_full_sync_pools_block_number BIGINT,
    PRIMARY KEY (chain_id, name),
    UNIQUE (chain_id, factory_address)
);

CREATE TABLE IF NOT EXISTS "pool" (
    chain_id INTEGER NOT NULL REFERENCES chain(chain_id) ON DELETE CASCADE,
    dex_name TEXT NOT NULL,
    address TEXT NOT NULL,
    pool_identifier TEXT NOT NULL,
    creation_block BIGINT NOT NULL,
    token0_chain INTEGER NOT NULL,
    token0_address TEXT NOT NULL,
    token1_chain INTEGER NOT NULL,
    token1_address TEXT NOT NULL,
    fee INTEGER,
    tick_spacing INTEGER,
    initial_tick INTEGER,
    initial_sqrt_price_x96 TEXT,
    hook_address TEXT,
    last_full_sync_block_number BIGINT,
    PRIMARY KEY (chain_id, dex_name, pool_identifier),
    FOREIGN KEY (token0_chain, token0_address) REFERENCES token(chain_id, address),
    FOREIGN KEY (token1_chain, token1_address) REFERENCES token(chain_id, address),
    FOREIGN KEY (chain_id, dex_name) REFERENCES dex(chain_id, name)
);

CREATE TABLE IF NOT EXISTS "pool_swap_event" (
    id BIGSERIAL PRIMARY KEY,
    chain_id INTEGER NOT NULL REFERENCES chain(chain_id) ON DELETE CASCADE,
    pool_identifier TEXT NOT NULL,
    dex_name TEXT NOT NULL,
    block BIGINT NOT NULL,
    transaction_hash TEXT NOT NULL,
    transaction_index INTEGER NOT NULL,
    log_index INTEGER NOT NULL,
    sender TEXT NOT NULL,
    recipient TEXT NOT NULL,
    sqrt_price_x96 U160 NOT NULL,
    liquidity U128 NOT NULL,
    tick INTEGER NOT NULL,
    amount0 I256 NOT NULL,
    amount1 I256 NOT NULL,
    order_side TEXT,
    base_quantity NUMERIC,
    quote_quantity NUMERIC,
    spot_price NUMERIC,
    execution_price NUMERIC,
    FOREIGN KEY (chain_id, dex_name, pool_identifier) REFERENCES pool(chain_id, dex_name, pool_identifier),
--     FOREIGN KEY (chain_id, block) REFERENCES block(chain_id, number), // TODO temporarily disabled not to be blocked by full block sync
    UNIQUE(chain_id, transaction_hash, log_index)
);
CREATE INDEX IF NOT EXISTS idx_pool_swap_event_lookup
    ON pool_swap_event(chain_id, pool_identifier, block, transaction_index, log_index);

CREATE TABLE IF NOT EXISTS "pool_liquidity_event" (
    id BIGSERIAL PRIMARY KEY,
    chain_id INTEGER NOT NULL REFERENCES chain(chain_id) ON DELETE CASCADE,
    pool_identifier TEXT NOT NULL,
    dex_name TEXT NOT NULL,
    block BIGINT NOT NULL,
    transaction_hash TEXT NOT NULL,
    transaction_index INTEGER NOT NULL,
    log_index INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    sender TEXT,
    owner TEXT NOT NULL,
    position_liquidity U128 NOT NULL,
    amount0 U160 NOT NULL,
    amount1 U160 NOT NULL,
    tick_lower INTEGER NOT NULL,
    tick_upper INTEGER NOT NULL,
    FOREIGN KEY (chain_id, dex_name, pool_identifier) REFERENCES pool(chain_id, dex_name, pool_identifier),
--     FOREIGN KEY (chain_id, block) REFERENCES block(chain_id, number),  // TODO temporarily disabled not to be blocked by full block sync
    UNIQUE(chain_id, transaction_hash, log_index)
);
CREATE INDEX IF NOT EXISTS idx_pool_liquidity_event_lookup
    ON pool_liquidity_event(chain_id, pool_identifier, block, transaction_index, log_index);

CREATE TABLE IF NOT EXISTS "pool_collect_event" (
    id BIGSERIAL PRIMARY KEY,
    chain_id INTEGER NOT NULL REFERENCES chain(chain_id) ON DELETE CASCADE,
    pool_identifier TEXT NOT NULL,
    dex_name TEXT NOT NULL,
    block BIGINT NOT NULL,
    transaction_hash TEXT NOT NULL,
    transaction_index INTEGER NOT NULL,
    log_index INTEGER NOT NULL,
    owner TEXT NOT NULL,
    amount0 U256 NOT NULL,
    amount1 U256 NOT NULL,
    tick_lower INTEGER NOT NULL,
    tick_upper INTEGER NOT NULL,
    FOREIGN KEY (chain_id, dex_name, pool_identifier) REFERENCES pool(chain_id, dex_name, pool_identifier),
--     FOREIGN KEY (chain_id, block) REFERENCES block(chain_id, number),  // TODO temporarily disabled not to be blocked by full block sync
    UNIQUE(chain_id, transaction_hash, log_index)
);
CREATE INDEX IF NOT EXISTS idx_pool_collect_event_lookup
    ON pool_collect_event(chain_id, pool_identifier, block, transaction_index, log_index);

CREATE TABLE IF NOT EXISTS "pool_flash_event" (
    id BIGSERIAL PRIMARY KEY,
    chain_id INTEGER NOT NULL REFERENCES chain(chain_id) ON DELETE CASCADE,
    pool_identifier TEXT NOT NULL,
    dex_name TEXT NOT NULL,
    block BIGINT NOT NULL,
    transaction_hash TEXT NOT NULL,
    transaction_index INTEGER NOT NULL,
    log_index INTEGER NOT NULL,
    sender TEXT NOT NULL,
    recipient TEXT NOT NULL,
    amount0 U256 NOT NULL,
    amount1 U256 NOT NULL,
    paid0 U256 NOT NULL,
    paid1 U256 NOT NULL,
    FOREIGN KEY (chain_id, dex_name, pool_identifier) REFERENCES pool(chain_id, dex_name, pool_identifier),
--     FOREIGN KEY (chain_id, block) REFERENCES block(chain_id, number),  // TODO temporarily disabled not to be blocked by full block sync
    UNIQUE(chain_id, transaction_hash, log_index)
);
CREATE INDEX IF NOT EXISTS idx_pool_flash_event_lookup
    ON pool_flash_event(chain_id, pool_identifier, block, transaction_index, log_index);

CREATE TABLE IF NOT EXISTS "pool_snapshot" (
    chain_id INTEGER NOT NULL REFERENCES chain(chain_id) ON DELETE CASCADE,
    pool_identifier TEXT NOT NULL,
    dex_name TEXT NOT NULL,
    block BIGINT NOT NULL,
    transaction_index INTEGER NOT NULL,
    log_index INTEGER NOT NULL,
    transaction_hash TEXT NOT NULL,
    current_tick INTEGER NOT NULL,
    price_sqrt_ratio_x96 U160 NOT NULL,
    liquidity U128 NOT NULL,
    protocol_fees_token0 U256 NOT NULL,
    protocol_fees_token1 U256 NOT NULL,
    fee_protocol SMALLINT NOT NULL,
    fee_growth_global_0 U256 NOT NULL,
    fee_growth_global_1 U256 NOT NULL,
    total_amount0_deposited U256 NOT NULL,
    total_amount1_deposited U256 NOT NULL,
    total_amount0_collected U256 NOT NULL,
    total_amount1_collected U256 NOT NULL,
    total_swaps INTEGER NOT NULL DEFAULT 0,
    total_mints INTEGER NOT NULL DEFAULT 0,
    total_burns INTEGER NOT NULL DEFAULT 0,
    total_flashes INTEGER NOT NULL DEFAULT 0,
    total_fee_collects INTEGER NOT NULL,
    liquidity_utilization_rate  DOUBLE PRECISION DEFAULT 0,
    is_valid BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (chain_id, pool_identifier, block, transaction_index, log_index),
    FOREIGN KEY (chain_id, dex_name, pool_identifier) REFERENCES pool(chain_id, dex_name, pool_identifier)
);

CREATE TABLE IF NOT EXISTS "pool_position" (
    chain_id INTEGER NOT NULL,
    pool_identifier TEXT NOT NULL,
    snapshot_block BIGINT NOT NULL,
    snapshot_transaction_index INTEGER NOT NULL,
    snapshot_log_index INTEGER NOT NULL,
    owner TEXT NOT NULL,
    tick_lower INTEGER NOT NULL,
    tick_upper INTEGER NOT NULL,
    liquidity U128 NOT NULL,
    fee_growth_inside_0_last U256 NOT NULL,
    fee_growth_inside_1_last U256 NOT NULL,
    tokens_owed_0 U128 NOT NULL,
    tokens_owed_1 U128 NOT NULL,
    total_amount0_deposited U256,
    total_amount1_deposited U256,
    total_amount0_collected U128,
    total_amount1_collected U128,
    is_consistent BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (chain_id, pool_identifier, snapshot_block, snapshot_transaction_index, snapshot_log_index, owner, tick_lower, tick_upper),
    FOREIGN KEY (chain_id, pool_identifier, snapshot_block, snapshot_transaction_index, snapshot_log_index)
        REFERENCES pool_snapshot(chain_id, pool_identifier, block, transaction_index, log_index) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "pool_tick" (
    chain_id INTEGER NOT NULL,
    pool_identifier TEXT NOT NULL,
    snapshot_block BIGINT NOT NULL,
    snapshot_transaction_index INTEGER NOT NULL,
    snapshot_log_index INTEGER NOT NULL,
    tick_value INTEGER NOT NULL,
    liquidity_gross U128 NOT NULL,
    liquidity_net I128 NOT NULL,
    fee_growth_outside_0 U256 NOT NULL,
    fee_growth_outside_1 U256 NOT NULL,
    initialized BOOLEAN NOT NULL,
    last_updated_block BIGINT NOT NULL,
    PRIMARY KEY (chain_id, pool_identifier, snapshot_block, snapshot_transaction_index, snapshot_log_index, tick_value),
    FOREIGN KEY (chain_id, pool_identifier, snapshot_block, snapshot_transaction_index, snapshot_log_index)
        REFERENCES pool_snapshot(chain_id, pool_identifier, block, transaction_index, log_index) ON DELETE CASCADE
);

-- =================================================================================================
--  表和字段注释 (中文说明)
-- =================================================================================================

-- general 表：通用键值存储
COMMENT ON TABLE "general" IS '通用键值存储表';
COMMENT ON COLUMN "general".id IS '键名（主键）';
COMMENT ON COLUMN "general".value IS '值（二进制数据）';

-- trader 表：交易员实例
COMMENT ON TABLE "trader" IS '交易员实例表';
COMMENT ON COLUMN "trader".id IS '交易员唯一标识（主键）';
COMMENT ON COLUMN "trader".instance_id IS '实例UUID';

-- account 表：交易账户
COMMENT ON TABLE "account" IS '交易账户表';
COMMENT ON COLUMN "account".id IS '账户唯一标识（主键）';

-- client 表：客户端连接
COMMENT ON TABLE "client" IS '客户端连接表';
COMMENT ON COLUMN "client".id IS '客户端唯一标识（主键）';

-- strategy 表：策略实例
COMMENT ON TABLE "strategy" IS '策略实例表';
COMMENT ON COLUMN "strategy".id IS '策略唯一标识（主键）';
COMMENT ON COLUMN "strategy".order_id_tag IS '订单ID标签，用于生成唯一订单ID';
COMMENT ON COLUMN "strategy".oms_type IS '订单管理系统类型';
COMMENT ON COLUMN "strategy".manage_contingent_orders IS '是否自动管理OTO/OCO/OUO条件单';
COMMENT ON COLUMN "strategy".manage_gtd_expiry IS '是否自动管理GTD订单过期';

-- currency 表：货币信息
COMMENT ON TABLE "currency" IS '货币信息表';
COMMENT ON COLUMN "currency".id IS '货币代码（主键，如CNY、USD）';
COMMENT ON COLUMN "currency".precision IS '货币精度（小数位数）';
COMMENT ON COLUMN "currency".iso4217 IS 'ISO 4217货币数字代码';
COMMENT ON COLUMN "currency".name IS '货币名称';
COMMENT ON COLUMN "currency".currency_type IS '货币类型（法币/加密货币等）';

-- instrument 表：交易标的/合约
COMMENT ON TABLE "instrument" IS '交易标的/合约表（股票、期货、期权等）';
COMMENT ON COLUMN "instrument".id IS '标的唯一标识（主键，如 600519.SSE）';
COMMENT ON COLUMN "instrument".kind IS '品种类型（EQUITY/FUTURE/OPTION等）';
COMMENT ON COLUMN "instrument".raw_symbol IS '原始交易代码';
COMMENT ON COLUMN "instrument".asset_class IS '资产类别（股票/外汇/大宗商品等）';
COMMENT ON COLUMN "instrument".underlying IS '标的资产（期权/期货的底层标的）';
COMMENT ON COLUMN "instrument".base_currency IS '基础货币（外汇交易对的基础货币）';
COMMENT ON COLUMN "instrument".quote_currency IS '报价货币';
COMMENT ON COLUMN "instrument".settlement_currency IS '结算货币';
COMMENT ON COLUMN "instrument".isin IS '国际证券识别码（ISIN）';
COMMENT ON COLUMN "instrument".exchange IS '交易所';
COMMENT ON COLUMN "instrument".option_kind IS '期权类型（看涨/看跌）';
COMMENT ON COLUMN "instrument".strike_price IS '行权价（期权）';
COMMENT ON COLUMN "instrument".activation_ns IS '激活时间（纳秒时间戳）';
COMMENT ON COLUMN "instrument".expiration_ns IS '到期时间（纳秒时间戳）';
COMMENT ON COLUMN "instrument".price_precision IS '价格精度（小数位数）';
COMMENT ON COLUMN "instrument".size_precision IS '数量精度（小数位数）';
COMMENT ON COLUMN "instrument".price_increment IS '最小价格变动单位';
COMMENT ON COLUMN "instrument".size_increment IS '最小数量变动单位';
COMMENT ON COLUMN "instrument".is_inverse IS '是否为反向合约';
COMMENT ON COLUMN "instrument".multiplier IS '合约乘数';
COMMENT ON COLUMN "instrument".lot_size IS '每手数量（A股为100股）';
COMMENT ON COLUMN "instrument".max_quantity IS '最大下单数量';
COMMENT ON COLUMN "instrument".min_quantity IS '最小下单数量';
COMMENT ON COLUMN "instrument".max_notional IS '最大名义价值';
COMMENT ON COLUMN "instrument".min_notional IS '最小名义价值';
COMMENT ON COLUMN "instrument".max_price IS '最高价格限制';
COMMENT ON COLUMN "instrument".min_price IS '最低价格限制';
COMMENT ON COLUMN "instrument".margin_init IS '初始保证金';
COMMENT ON COLUMN "instrument".margin_maint IS '维持保证金';
COMMENT ON COLUMN "instrument".maker_fee IS '挂单手续费率';
COMMENT ON COLUMN "instrument".taker_fee IS '吃单手续费率';
COMMENT ON COLUMN "instrument".ts_event IS '事件时间戳（纳秒）';
COMMENT ON COLUMN "instrument".ts_init IS '初始化时间戳（纳秒）';
COMMENT ON COLUMN "instrument".created_at IS '记录创建时间';
COMMENT ON COLUMN "instrument".updated_at IS '记录更新时间';

-- order 表：订单
COMMENT ON TABLE "order" IS '订单表（全生命周期）';
COMMENT ON COLUMN "order".id IS '订单唯一标识（主键）';
COMMENT ON COLUMN "order".trader_id IS '所属交易员ID';
COMMENT ON COLUMN "order".strategy_id IS '所属策略ID';
COMMENT ON COLUMN "order".instrument_id IS '关联交易标的ID';
COMMENT ON COLUMN "order".client_order_id IS '客户端订单ID';
COMMENT ON COLUMN "order".venue_order_id IS '交易所订单ID';
COMMENT ON COLUMN "order".position_id IS '关联持仓ID';
COMMENT ON COLUMN "order".account_id IS '关联账户ID';
COMMENT ON COLUMN "order".last_trade_id IS '最近成交ID';
COMMENT ON COLUMN "order".order_type IS '订单类型（LIMIT/MARKET/STOP等）';
COMMENT ON COLUMN "order".order_side IS '买卖方向（BUY/SELL）';
COMMENT ON COLUMN "order".quantity IS '委托数量';
COMMENT ON COLUMN "order".price IS '委托价格';
COMMENT ON COLUMN "order".trigger_price IS '触发价格（止损/止盈单）';
COMMENT ON COLUMN "order".trigger_type IS '触发类型';
COMMENT ON COLUMN "order".limit_offset IS '限价偏移量';
COMMENT ON COLUMN "order".trailing_offset IS '追踪偏移量（追踪止损）';
COMMENT ON COLUMN "order".trailing_offset_type IS '追踪偏移类型';
COMMENT ON COLUMN "order".time_in_force IS '有效期类型（GTC/IOC/FOK/GTD等）';
COMMENT ON COLUMN "order".expire_time IS '过期时间（GTD订单）';
COMMENT ON COLUMN "order".filled_qty IS '已成交数量';
COMMENT ON COLUMN "order".liquidity_side IS '流动性方向（MAKER/TAKER）';
COMMENT ON COLUMN "order".avg_px IS '平均成交价格';
COMMENT ON COLUMN "order".slippage IS '滑点';
COMMENT ON COLUMN "order".commissions IS '手续费列表';
COMMENT ON COLUMN "order".status IS '订单状态（SUBMITTED/ACCEPTED/FILLED/CANCELED等）';
COMMENT ON COLUMN "order".is_post_only IS '是否为Post-Only订单（只做挂单）';
COMMENT ON COLUMN "order".is_reduce_only IS '是否为只减仓订单';
COMMENT ON COLUMN "order".is_quote_quantity IS '是否以报价货币计价下单';
COMMENT ON COLUMN "order".display_qty IS '展示数量（冰山单可见部分）';
COMMENT ON COLUMN "order".emulation_trigger IS '模拟触发类型';
COMMENT ON COLUMN "order".trigger_instrument_id IS '触发标的ID（用其他标的触发）';
COMMENT ON COLUMN "order".contingency_type IS '条件单类型（OTO/OCO/OUO）';
COMMENT ON COLUMN "order".order_list_id IS '订单列表ID（条件单组）';
COMMENT ON COLUMN "order".linked_order_ids IS '关联订单ID列表';
COMMENT ON COLUMN "order".parent_order_id IS '父订单ID';
COMMENT ON COLUMN "order".exec_algorithm_id IS '执行算法ID';
COMMENT ON COLUMN "order".exec_algorithm_params IS '执行算法参数（JSON）';
COMMENT ON COLUMN "order".exec_spawn_id IS '执行拆分ID';
COMMENT ON COLUMN "order".tags IS '自定义标签列表';
COMMENT ON COLUMN "order".init_id IS '初始化ID';
COMMENT ON COLUMN "order".ts_init IS '初始化时间戳（纳秒）';
COMMENT ON COLUMN "order".ts_last IS '最后更新时间戳（纳秒）';
COMMENT ON COLUMN "order".created_at IS '记录创建时间';
COMMENT ON COLUMN "order".updated_at IS '记录更新时间';

-- order_event 表：订单事件流
COMMENT ON TABLE "order_event" IS '订单事件表（订单生命周期事件记录）';
COMMENT ON COLUMN "order_event".id IS '事件唯一标识（主键）';
COMMENT ON COLUMN "order_event".kind IS '事件类型（SUBMITTED/ACCEPTED/REJECTED/FILLED/CANCELED等）';
COMMENT ON COLUMN "order_event".trader_id IS '所属交易员ID';
COMMENT ON COLUMN "order_event".strategy_id IS '所属策略ID';
COMMENT ON COLUMN "order_event".instrument_id IS '关联交易标的ID';
COMMENT ON COLUMN "order_event".client_order_id IS '客户端订单ID';
COMMENT ON COLUMN "order_event".client_id IS '客户端ID';
COMMENT ON COLUMN "order_event".reason IS '事件原因（如拒绝原因）';
COMMENT ON COLUMN "order_event".trade_id IS '成交ID';
COMMENT ON COLUMN "order_event".currency IS '手续费货币';
COMMENT ON COLUMN "order_event".order_type IS '订单类型';
COMMENT ON COLUMN "order_event".order_side IS '买卖方向';
COMMENT ON COLUMN "order_event".quantity IS '委托数量';
COMMENT ON COLUMN "order_event".time_in_force IS '有效期类型';
COMMENT ON COLUMN "order_event".liquidity_side IS '流动性方向';
COMMENT ON COLUMN "order_event".post_only IS '是否为Post-Only';
COMMENT ON COLUMN "order_event".reduce_only IS '是否只减仓';
COMMENT ON COLUMN "order_event".quote_quantity IS '是否以报价货币计价';
COMMENT ON COLUMN "order_event".reconciliation IS '是否为对账事件';
COMMENT ON COLUMN "order_event".price IS '委托价格';
COMMENT ON COLUMN "order_event".last_px IS '最新成交价';
COMMENT ON COLUMN "order_event".last_qty IS '最新成交量';
COMMENT ON COLUMN "order_event".trigger_price IS '触发价格';
COMMENT ON COLUMN "order_event".trigger_type IS '触发类型';
COMMENT ON COLUMN "order_event".limit_offset IS '限价偏移量';
COMMENT ON COLUMN "order_event".trailing_offset IS '追踪偏移量';
COMMENT ON COLUMN "order_event".trailing_offset_type IS '追踪偏移类型';
COMMENT ON COLUMN "order_event".expire_time IS '过期时间';
COMMENT ON COLUMN "order_event".display_qty IS '展示数量';
COMMENT ON COLUMN "order_event".emulation_trigger IS '模拟触发类型';
COMMENT ON COLUMN "order_event".trigger_instrument_id IS '触发标的ID';
COMMENT ON COLUMN "order_event".contingency_type IS '条件单类型';
COMMENT ON COLUMN "order_event".order_list_id IS '订单列表ID';
COMMENT ON COLUMN "order_event".linked_order_ids IS '关联订单ID列表';
COMMENT ON COLUMN "order_event".parent_order_id IS '父订单ID';
COMMENT ON COLUMN "order_event".exec_algorithm_id IS '执行算法ID';
COMMENT ON COLUMN "order_event".exec_algorithm_params IS '执行算法参数（JSON）';
COMMENT ON COLUMN "order_event".exec_spawn_id IS '执行拆分ID';
COMMENT ON COLUMN "order_event".venue_order_id IS '交易所订单ID';
COMMENT ON COLUMN "order_event".account_id IS '账户ID';
COMMENT ON COLUMN "order_event".position_id IS '持仓ID';
COMMENT ON COLUMN "order_event".commission IS '手续费';
COMMENT ON COLUMN "order_event".tags IS '自定义标签列表';
COMMENT ON COLUMN "order_event".ts_event IS '事件时间戳（纳秒）';
COMMENT ON COLUMN "order_event".ts_init IS '初始化时间戳（纳秒）';
COMMENT ON COLUMN "order_event".created_at IS '记录创建时间';
COMMENT ON COLUMN "order_event".updated_at IS '记录更新时间';

-- position 表：持仓
COMMENT ON TABLE "position" IS '持仓表';
COMMENT ON COLUMN "position".id IS '持仓唯一标识（主键）';
COMMENT ON COLUMN "position".trader_id IS '所属交易员ID';
COMMENT ON COLUMN "position".strategy_id IS '所属策略ID';
COMMENT ON COLUMN "position".instrument_id IS '关联交易标的ID';
COMMENT ON COLUMN "position".account_id IS '关联账户ID';
COMMENT ON COLUMN "position".opening_order_id IS '开仓订单ID';
COMMENT ON COLUMN "position".closing_order_id IS '平仓订单ID';
COMMENT ON COLUMN "position".entry IS '入场类型（开仓方向）';
COMMENT ON COLUMN "position".side IS '持仓方向（LONG/SHORT/FLAT）';
COMMENT ON COLUMN "position".signed_qty IS '带符号持仓数量（正=多头，负=空头）';
COMMENT ON COLUMN "position".quantity IS '持仓数量（绝对值）';
COMMENT ON COLUMN "position".peak_qty IS '持仓峰值数量';
COMMENT ON COLUMN "position".quote_currency IS '报价货币';
COMMENT ON COLUMN "position".base_currency IS '基础货币';
COMMENT ON COLUMN "position".settlement_currency IS '结算货币';
COMMENT ON COLUMN "position".avg_px_open IS '开仓均价';
COMMENT ON COLUMN "position".avg_px_close IS '平仓均价';
COMMENT ON COLUMN "position".realized_return IS '已实现收益率';
COMMENT ON COLUMN "position".realized_pnl IS '已实现盈亏';
COMMENT ON COLUMN "position".unrealized_pnl IS '未实现盈亏';
COMMENT ON COLUMN "position".commissions IS '手续费列表';
COMMENT ON COLUMN "position".duration_ns IS '持仓持续时间（纳秒）';
COMMENT ON COLUMN "position".ts_opened IS '开仓时间（纳秒）';
COMMENT ON COLUMN "position".ts_closed IS '平仓时间（纳秒）';
COMMENT ON COLUMN "position".ts_init IS '初始化时间戳（纳秒）';
COMMENT ON COLUMN "position".ts_last IS '最后更新时间戳（纳秒）';
COMMENT ON COLUMN "position".created_at IS '记录创建时间';
COMMENT ON COLUMN "position".updated_at IS '记录更新时间';

-- account_event 表：账户事件
COMMENT ON TABLE "account_event" IS '账户事件表（余额变化、保证金变化等）';
COMMENT ON COLUMN "account_event".id IS '事件唯一标识（主键）';
COMMENT ON COLUMN "account_event".kind IS '事件类型';
COMMENT ON COLUMN "account_event".account_id IS '关联账户ID';
COMMENT ON COLUMN "account_event".base_currency IS '基础货币';
COMMENT ON COLUMN "account_event".balances IS '余额列表（JSON）';
COMMENT ON COLUMN "account_event".margins IS '保证金列表（JSON）';
COMMENT ON COLUMN "account_event".is_reported IS '是否为账户报告事件';
COMMENT ON COLUMN "account_event".ts_event IS '事件时间戳（纳秒）';
COMMENT ON COLUMN "account_event".ts_init IS '初始化时间戳（纳秒）';
COMMENT ON COLUMN "account_event".created_at IS '记录创建时间';
COMMENT ON COLUMN "account_event".updated_at IS '记录更新时间';

-- trade 表：成交明细
COMMENT ON TABLE "trade" IS '成交明细表（逐笔成交）';
COMMENT ON COLUMN "trade".id IS '自增主键';
COMMENT ON COLUMN "trade".instrument_id IS '关联交易标的ID';
COMMENT ON COLUMN "trade".price IS '成交价格';
COMMENT ON COLUMN "trade".quantity IS '成交数量';
COMMENT ON COLUMN "trade".aggressor_side IS '主动方向（BUY/SELL）';
COMMENT ON COLUMN "trade".venue_trade_id IS '交易所成交ID';
COMMENT ON COLUMN "trade".ts_event IS '事件时间戳（纳秒）';
COMMENT ON COLUMN "trade".ts_init IS '初始化时间戳（纳秒）';
COMMENT ON COLUMN "trade".created_at IS '记录创建时间';
COMMENT ON COLUMN "trade".updated_at IS '记录更新时间';

-- quote 表：报价
COMMENT ON TABLE "quote" IS '报价表（买卖盘快照）';
COMMENT ON COLUMN "quote".id IS '自增主键';
COMMENT ON COLUMN "quote".instrument_id IS '关联交易标的ID';
COMMENT ON COLUMN "quote".bid_price IS '买一价';
COMMENT ON COLUMN "quote".ask_price IS '卖一价';
COMMENT ON COLUMN "quote".bid_size IS '买一量';
COMMENT ON COLUMN "quote".ask_size IS '卖一量';
COMMENT ON COLUMN "quote".ts_event IS '事件时间戳（纳秒）';
COMMENT ON COLUMN "quote".ts_init IS '初始化时间戳（纳秒）';
COMMENT ON COLUMN "quote".created_at IS '记录创建时间';
COMMENT ON COLUMN "quote".updated_at IS '记录更新时间';

-- bar 表：K线
COMMENT ON TABLE "bar" IS 'K线表（OHLCV）';
COMMENT ON COLUMN "bar".id IS '自增主键';
COMMENT ON COLUMN "bar".instrument_id IS '关联交易标的ID';
COMMENT ON COLUMN "bar".step IS 'K线步长（如1分钟K线的步长为1）';
COMMENT ON COLUMN "bar".bar_aggregation IS 'K线聚合方式（TICK/SECOND/MINUTE/HOUR/DAY等）';
COMMENT ON COLUMN "bar".price_type IS '价格类型（LAST/MID/BID/ASK等）';
COMMENT ON COLUMN "bar".aggregation_source IS '聚合来源（INTERNAL/EXTERNAL）';
COMMENT ON COLUMN "bar".open IS '开盘价';
COMMENT ON COLUMN "bar".high IS '最高价';
COMMENT ON COLUMN "bar".low IS '最低价';
COMMENT ON COLUMN "bar".close IS '收盘价';
COMMENT ON COLUMN "bar".volume IS '成交量';
COMMENT ON COLUMN "bar".ts_event IS '事件时间戳（纳秒）';
COMMENT ON COLUMN "bar".ts_init IS '初始化时间戳（纳秒）';
COMMENT ON COLUMN "bar".created_at IS '记录创建时间';
COMMENT ON COLUMN "bar".updated_at IS '记录更新时间';

-- signal 表：交易信号
COMMENT ON TABLE "signal" IS '交易信号表';
COMMENT ON COLUMN "signal".id IS '自增主键';
COMMENT ON COLUMN "signal".name IS '信号名称';
COMMENT ON COLUMN "signal".value IS '信号值';
COMMENT ON COLUMN "signal".ts_event IS '事件时间戳（纳秒）';
COMMENT ON COLUMN "signal".ts_init IS '初始化时间戳（纳秒）';
COMMENT ON COLUMN "signal".created_at IS '记录创建时间';
COMMENT ON COLUMN "signal".updated_at IS '记录更新时间';

-- custom 表：自定义数据
COMMENT ON TABLE "custom" IS '自定义数据表';
COMMENT ON COLUMN "custom".id IS '自增主键';
COMMENT ON COLUMN "custom".data_type IS '数据类型标识';
COMMENT ON COLUMN "custom".metadata IS '元数据（JSON）';
COMMENT ON COLUMN "custom".identifier IS '数据标识符';
COMMENT ON COLUMN "custom".value IS '数据值（JSON）';
COMMENT ON COLUMN "custom".ts_event IS '事件时间戳（纳秒）';
COMMENT ON COLUMN "custom".ts_init IS '初始化时间戳（纳秒）';
COMMENT ON COLUMN "custom".created_at IS '记录创建时间';
COMMENT ON COLUMN "custom".updated_at IS '记录更新时间';

-- chain 表：区块链网络
COMMENT ON TABLE "chain" IS '区块链网络表';
COMMENT ON COLUMN "chain".chain_id IS '链ID（主键）';
COMMENT ON COLUMN "chain".name IS '链名称';

-- block 表：区块
COMMENT ON TABLE "block" IS '区块表（按链分区）';
COMMENT ON COLUMN "block".chain_id IS '所属链ID';
COMMENT ON COLUMN "block".number IS '区块号';
COMMENT ON COLUMN "block".hash IS '区块哈希';
COMMENT ON COLUMN "block".parent_hash IS '父区块哈希';
COMMENT ON COLUMN "block".miner IS '矿工地址';
COMMENT ON COLUMN "block".gas_limit IS 'Gas上限';
COMMENT ON COLUMN "block".gas_used IS '已用Gas';
COMMENT ON COLUMN "block".timestamp IS '区块时间戳';
COMMENT ON COLUMN "block".base_fee_per_gas IS '基础Gas费';
COMMENT ON COLUMN "block".blob_gas_used IS 'Blob Gas已用';
COMMENT ON COLUMN "block".excess_blob_gas IS '超额Blob Gas';
COMMENT ON COLUMN "block".l1_gas_price IS 'L1 Gas价格（L2用）';
COMMENT ON COLUMN "block".l1_gas_used IS 'L1 Gas用量（L2用）';
COMMENT ON COLUMN "block".l1_fee_scalar IS 'L1费率系数（L2用）';

-- token 表：代币
COMMENT ON TABLE "token" IS '代币表（按链分区）';
COMMENT ON COLUMN "token".chain_id IS '所属链ID';
COMMENT ON COLUMN "token".address IS '代币合约地址';
COMMENT ON COLUMN "token".symbol IS '代币符号（如ETH、USDT）';
COMMENT ON COLUMN "token".name IS '代币名称';
COMMENT ON COLUMN "token".decimals IS '代币精度（小数位数）';
COMMENT ON COLUMN "token".error IS '错误信息';

-- dex 表：去中心化交易所
COMMENT ON TABLE "dex" IS '去中心化交易所表';
COMMENT ON COLUMN "dex".chain_id IS '所属链ID';
COMMENT ON COLUMN "dex".name IS 'DEX名称';
COMMENT ON COLUMN "dex".factory_address IS '工厂合约地址';
COMMENT ON COLUMN "dex".creation_block IS '创建区块号';
COMMENT ON COLUMN "dex".last_full_sync_pools_block_number IS '最近一次全量同步池子的区块号';

-- pool 表：流动性池
COMMENT ON TABLE "pool" IS '流动性池表';
COMMENT ON COLUMN "pool".chain_id IS '所属链ID';
COMMENT ON COLUMN "pool".dex_name IS '所属DEX名称';
COMMENT ON COLUMN "pool".address IS '池子合约地址';
COMMENT ON COLUMN "pool".pool_identifier IS '池子标识符';
COMMENT ON COLUMN "pool".creation_block IS '创建区块号';
COMMENT ON COLUMN "pool".token0_chain IS '代币0所属链ID';
COMMENT ON COLUMN "pool".token0_address IS '代币0合约地址';
COMMENT ON COLUMN "pool".token1_chain IS '代币1所属链ID';
COMMENT ON COLUMN "pool".token1_address IS '代币1合约地址';
COMMENT ON COLUMN "pool".fee IS '手续费率（基点）';
COMMENT ON COLUMN "pool".tick_spacing IS 'Tick间距';
COMMENT ON COLUMN "pool".initial_tick IS '初始Tick';
COMMENT ON COLUMN "pool".initial_sqrt_price_x96 IS '初始sqrt价格（X96格式）';
COMMENT ON COLUMN "pool".hook_address IS 'Hook合约地址（Uniswap V4）';
COMMENT ON COLUMN "pool".last_full_sync_block_number IS '最近一次全量同步区块号';

-- pool_swap_event 表：池子交换事件
COMMENT ON TABLE "pool_swap_event" IS '流动性池交换事件表';
COMMENT ON COLUMN "pool_swap_event".id IS '自增主键';
COMMENT ON COLUMN "pool_swap_event".chain_id IS '所属链ID';
COMMENT ON COLUMN "pool_swap_event".pool_identifier IS '池子标识符';
COMMENT ON COLUMN "pool_swap_event".dex_name IS 'DEX名称';
COMMENT ON COLUMN "pool_swap_event".block IS '区块号';
COMMENT ON COLUMN "pool_swap_event".transaction_hash IS '交易哈希';
COMMENT ON COLUMN "pool_swap_event".transaction_index IS '交易在区块中的索引';
COMMENT ON COLUMN "pool_swap_event".log_index IS '日志索引';
COMMENT ON COLUMN "pool_swap_event".sender IS '发送方地址';
COMMENT ON COLUMN "pool_swap_event".recipient IS '接收方地址';
COMMENT ON COLUMN "pool_swap_event".sqrt_price_x96 IS '交换后sqrt价格（X96格式）';
COMMENT ON COLUMN "pool_swap_event".liquidity IS '交换后流动性';
COMMENT ON COLUMN "pool_swap_event".tick IS '交换后Tick值';
COMMENT ON COLUMN "pool_swap_event".amount0 IS '代币0变化量（带符号）';
COMMENT ON COLUMN "pool_swap_event".amount1 IS '代币1变化量（带符号）';
COMMENT ON COLUMN "pool_swap_event".order_side IS '买卖方向（NO_AGGRESSOR/BUY/SELL）';
COMMENT ON COLUMN "pool_swap_event".base_quantity IS '基础代币数量';
COMMENT ON COLUMN "pool_swap_event".quote_quantity IS '报价代币数量';
COMMENT ON COLUMN "pool_swap_event".spot_price IS '现货价格';
COMMENT ON COLUMN "pool_swap_event".execution_price IS '执行价格';

-- pool_liquidity_event 表：流动性事件
COMMENT ON TABLE "pool_liquidity_event" IS '流动性池流动性事件表（铸造/销毁）';
COMMENT ON COLUMN "pool_liquidity_event".id IS '自增主键';
COMMENT ON COLUMN "pool_liquidity_event".chain_id IS '所属链ID';
COMMENT ON COLUMN "pool_liquidity_event".pool_identifier IS '池子标识符';
COMMENT ON COLUMN "pool_liquidity_event".dex_name IS 'DEX名称';
COMMENT ON COLUMN "pool_liquidity_event".block IS '区块号';
COMMENT ON COLUMN "pool_liquidity_event".transaction_hash IS '交易哈希';
COMMENT ON COLUMN "pool_liquidity_event".transaction_index IS '交易索引';
COMMENT ON COLUMN "pool_liquidity_event".log_index IS '日志索引';
COMMENT ON COLUMN "pool_liquidity_event".event_type IS '事件类型（MINT/BURN）';
COMMENT ON COLUMN "pool_liquidity_event".sender IS '发送方地址';
COMMENT ON COLUMN "pool_liquidity_event".owner IS '所有者地址（LP提供者）';
COMMENT ON COLUMN "pool_liquidity_event".position_liquidity IS '仓位流动性';
COMMENT ON COLUMN "pool_liquidity_event".amount0 IS '代币0数量';
COMMENT ON COLUMN "pool_liquidity_event".amount1 IS '代币1数量';
COMMENT ON COLUMN "pool_liquidity_event".tick_lower IS '下限Tick';
COMMENT ON COLUMN "pool_liquidity_event".tick_upper IS '上限Tick';

-- pool_collect_event 表：手续费收取事件
COMMENT ON TABLE "pool_collect_event" IS '流动性池手续费收取事件表';
COMMENT ON COLUMN "pool_collect_event".id IS '自增主键';
COMMENT ON COLUMN "pool_collect_event".chain_id IS '所属链ID';
COMMENT ON COLUMN "pool_collect_event".pool_identifier IS '池子标识符';
COMMENT ON COLUMN "pool_collect_event".dex_name IS 'DEX名称';
COMMENT ON COLUMN "pool_collect_event".block IS '区块号';
COMMENT ON COLUMN "pool_collect_event".transaction_hash IS '交易哈希';
COMMENT ON COLUMN "pool_collect_event".transaction_index IS '交易索引';
COMMENT ON COLUMN "pool_collect_event".log_index IS '日志索引';
COMMENT ON COLUMN "pool_collect_event".owner IS '所有者地址';
COMMENT ON COLUMN "pool_collect_event".amount0 IS '收取的代币0数量';
COMMENT ON COLUMN "pool_collect_event".amount1 IS '收取的代币1数量';
COMMENT ON COLUMN "pool_collect_event".tick_lower IS '下限Tick';
COMMENT ON COLUMN "pool_collect_event".tick_upper IS '上限Tick';

-- pool_flash_event 表：闪电贷事件
COMMENT ON TABLE "pool_flash_event" IS '流动性池闪电贷事件表';
COMMENT ON COLUMN "pool_flash_event".id IS '自增主键';
COMMENT ON COLUMN "pool_flash_event".chain_id IS '所属链ID';
COMMENT ON COLUMN "pool_flash_event".pool_identifier IS '池子标识符';
COMMENT ON COLUMN "pool_flash_event".dex_name IS 'DEX名称';
COMMENT ON COLUMN "pool_flash_event".block IS '区块号';
COMMENT ON COLUMN "pool_flash_event".transaction_hash IS '交易哈希';
COMMENT ON COLUMN "pool_flash_event".transaction_index IS '交易索引';
COMMENT ON COLUMN "pool_flash_event".log_index IS '日志索引';
COMMENT ON COLUMN "pool_flash_event".sender IS '发送方地址';
COMMENT ON COLUMN "pool_flash_event".recipient IS '接收方地址';
COMMENT ON COLUMN "pool_flash_event".amount0 IS '借出的代币0数量';
COMMENT ON COLUMN "pool_flash_event".amount1 IS '借出的代币1数量';
COMMENT ON COLUMN "pool_flash_event".paid0 IS '归还的代币0数量';
COMMENT ON COLUMN "pool_flash_event".paid1 IS '归还的代币1数量';

-- pool_snapshot 表：池子快照
COMMENT ON TABLE "pool_snapshot" IS '流动性池状态快照表';
COMMENT ON COLUMN "pool_snapshot".chain_id IS '所属链ID';
COMMENT ON COLUMN "pool_snapshot".pool_identifier IS '池子标识符';
COMMENT ON COLUMN "pool_snapshot".dex_name IS 'DEX名称';
COMMENT ON COLUMN "pool_snapshot".block IS '快照区块号';
COMMENT ON COLUMN "pool_snapshot".transaction_index IS '交易索引';
COMMENT ON COLUMN "pool_snapshot".log_index IS '日志索引';
COMMENT ON COLUMN "pool_snapshot".transaction_hash IS '交易哈希';
COMMENT ON COLUMN "pool_snapshot".current_tick IS '当前Tick';
COMMENT ON COLUMN "pool_snapshot".price_sqrt_ratio_x96 IS 'sqrt价格比率（X96格式）';
COMMENT ON COLUMN "pool_snapshot".liquidity IS '当前流动性';
COMMENT ON COLUMN "pool_snapshot".protocol_fees_token0 IS '代币0协议费';
COMMENT ON COLUMN "pool_snapshot".protocol_fees_token1 IS '代币1协议费';
COMMENT ON COLUMN "pool_snapshot".fee_protocol IS '协议费率';
COMMENT ON COLUMN "pool_snapshot".fee_growth_global_0 IS '代币0全局费率增长';
COMMENT ON COLUMN "pool_snapshot".fee_growth_global_1 IS '代币1全局费率增长';
COMMENT ON COLUMN "pool_snapshot".total_amount0_deposited IS '代币0总存入量';
COMMENT ON COLUMN "pool_snapshot".total_amount1_deposited IS '代币1总存入量';
COMMENT ON COLUMN "pool_snapshot".total_amount0_collected IS '代币0总收取量';
COMMENT ON COLUMN "pool_snapshot".total_amount1_collected IS '代币1总收取量';
COMMENT ON COLUMN "pool_snapshot".total_swaps IS '总交换次数';
COMMENT ON COLUMN "pool_snapshot".total_mints IS '总铸造次数';
COMMENT ON COLUMN "pool_snapshot".total_burns IS '总销毁次数';
COMMENT ON COLUMN "pool_snapshot".total_flashes IS '总闪电贷次数';
COMMENT ON COLUMN "pool_snapshot".total_fee_collects IS '总手续费收取次数';
COMMENT ON COLUMN "pool_snapshot".liquidity_utilization_rate IS '流动性利用率';
COMMENT ON COLUMN "pool_snapshot".is_valid IS '快照数据是否有效';
COMMENT ON COLUMN "pool_snapshot".created_at IS '记录创建时间';

-- pool_position 表：LP持仓
COMMENT ON TABLE "pool_position" IS '流动性提供者LP持仓表';
COMMENT ON COLUMN "pool_position".chain_id IS '所属链ID';
COMMENT ON COLUMN "pool_position".pool_identifier IS '池子标识符';
COMMENT ON COLUMN "pool_position".snapshot_block IS '快照区块号';
COMMENT ON COLUMN "pool_position".snapshot_transaction_index IS '快照交易索引';
COMMENT ON COLUMN "pool_position".snapshot_log_index IS '快照日志索引';
COMMENT ON COLUMN "pool_position".owner IS 'LP持有者地址';
COMMENT ON COLUMN "pool_position".tick_lower IS '仓位下限Tick';
COMMENT ON COLUMN "pool_position".tick_upper IS '仓位上限Tick';
COMMENT ON COLUMN "pool_position".liquidity IS '仓位流动性';
COMMENT ON COLUMN "pool_position".fee_growth_inside_0_last IS '上次代币0区间费率增长';
COMMENT ON COLUMN "pool_position".fee_growth_inside_1_last IS '上次代币1区间费率增长';
COMMENT ON COLUMN "pool_position".tokens_owed_0 IS '应付代币0';
COMMENT ON COLUMN "pool_position".tokens_owed_1 IS '应付代币1';
COMMENT ON COLUMN "pool_position".total_amount0_deposited IS '总存入代币0';
COMMENT ON COLUMN "pool_position".total_amount1_deposited IS '总存入代币1';
COMMENT ON COLUMN "pool_position".total_amount0_collected IS '总收取代币0';
COMMENT ON COLUMN "pool_position".total_amount1_collected IS '总收取代币1';
COMMENT ON COLUMN "pool_position".is_consistent IS '仓位数据是否一致';

-- pool_tick 表：Tick数据
COMMENT ON TABLE "pool_tick" IS '流动性池Tick数据表';
COMMENT ON COLUMN "pool_tick".chain_id IS '所属链ID';
COMMENT ON COLUMN "pool_tick".pool_identifier IS '池子标识符';
COMMENT ON COLUMN "pool_tick".snapshot_block IS '快照区块号';
COMMENT ON COLUMN "pool_tick".snapshot_transaction_index IS '快照交易索引';
COMMENT ON COLUMN "pool_tick".snapshot_log_index IS '快照日志索引';
COMMENT ON COLUMN "pool_tick".tick_value IS 'Tick值';
COMMENT ON COLUMN "pool_tick".liquidity_gross IS '总流动性（所有LP在该Tick的流动性之和）';
COMMENT ON COLUMN "pool_tick".liquidity_net IS '净流动性变化（穿过该Tick时的流动性变化）';
COMMENT ON COLUMN "pool_tick".fee_growth_outside_0 IS '代币0区间外费率增长';
COMMENT ON COLUMN "pool_tick".fee_growth_outside_1 IS '代币1区间外费率增长';
COMMENT ON COLUMN "pool_tick".initialized IS '是否已初始化';
COMMENT ON COLUMN "pool_tick".last_updated_block IS '最后更新区块号';
