CREATE TABLE IF NOT EXISTS users (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT    NOT NULL UNIQUE,
    password TEXT    NOT NULL,
    role     TEXT    NOT NULL DEFAULT 'salesperson'
);

CREATE TABLE IF NOT EXISTS customers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_no   TEXT    NOT NULL UNIQUE,
    first_name    TEXT    NOT NULL,
    last_name     TEXT    NOT NULL,
    phone         TEXT,
    email         TEXT,
    address       TEXT,
    city          TEXT,
    state         TEXT,
    zip           TEXT,
    customer_type TEXT    NOT NULL DEFAULT 'Retail',
    salesperson   TEXT
);

CREATE TABLE IF NOT EXISTS vehicles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_no    TEXT    NOT NULL UNIQUE,
    vin         TEXT    NOT NULL,
    year        INTEGER NOT NULL,
    make        TEXT    NOT NULL,
    model       TEXT    NOT NULL,
    trim        TEXT,
    color       TEXT,
    mileage     INTEGER NOT NULL DEFAULT 0,
    price       REAL    NOT NULL DEFAULT 0,
    status      TEXT    NOT NULL DEFAULT 'In Stock',
    customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS repair_orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ro_number       TEXT    NOT NULL UNIQUE,
    customer_id     INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    vehicle_id      INTEGER REFERENCES vehicles(id) ON DELETE SET NULL,
    date            TEXT    NOT NULL,
    type            TEXT    NOT NULL DEFAULT 'Maintenance',
    advisor         TEXT,
    mileage         INTEGER,
    status          TEXT    NOT NULL DEFAULT 'Open',
    concern         TEXT,
    cause           TEXT,
    correction      TEXT,
    recommendations TEXT,
    total           REAL    DEFAULT 0
);

CREATE TABLE IF NOT EXISTS deals (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_number  TEXT    NOT NULL UNIQUE,
    customer_id  INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    vehicle_id   INTEGER REFERENCES vehicles(id) ON DELETE SET NULL,
    date         TEXT    NOT NULL,
    salesperson  TEXT,
    deal_type    TEXT    NOT NULL DEFAULT 'Finance',
    sale_price   REAL    NOT NULL DEFAULT 0,
    trade_in     TEXT,
    status       TEXT    NOT NULL DEFAULT 'Quote',
    notes        TEXT
);

CREATE TABLE IF NOT EXISTS appointments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    datetime    TEXT    NOT NULL,
    advisor     TEXT,
    reason      TEXT,
    dept        TEXT    NOT NULL DEFAULT 'Service',
    status      TEXT    NOT NULL DEFAULT 'Scheduled',
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS chaos_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '0'
);
