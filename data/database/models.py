import sqlite3
from pathlib import Path
from config.settings import DATABASE_PATH


def get_connection():
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user' CHECK(role IN ('admin', 'user')),
            telegram_id INTEGER UNIQUE,
            telegram_username TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS stock_master (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            company_name TEXT NOT NULL DEFAULT '',
            sector TEXT DEFAULT '',
            exchange TEXT DEFAULT 'BIST',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS stock_market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id INTEGER NOT NULL,
            source TEXT DEFAULT 'system',
            last_price REAL,
            change_pct REAL,
            volume INTEGER,
            market_cap REAL,
            net_debt REAL,
            total_shares REAL,
            float_rate REAL,
            floating_shares REAL,
            pe REAL,
            pb REAL,
            calculated_value REAL,
            ratio REAL,
            signal TEXT,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (stock_id) REFERENCES stock_master(id) ON DELETE CASCADE,
            UNIQUE(stock_id, source)
        );

        CREATE TABLE IF NOT EXISTS stock_company_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id INTEGER NOT NULL,
            company_name TEXT,
            sector TEXT,
            market_cap REAL,
            net_debt REAL,
            total_shares REAL,
            float_rate REAL,
            floating_shares REAL,
            pe REAL,
            pb REAL,
            calculated_value REAL,
            ratio REAL,
            signal TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (stock_id) REFERENCES stock_master(id) ON DELETE CASCADE,
            UNIQUE(stock_id)
        );

        CREATE TABLE IF NOT EXISTS stock_user_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id INTEGER NOT NULL UNIQUE,
            opinion TEXT DEFAULT '',
            personal_signal TEXT DEFAULT 'Izle',
            price_target REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (stock_id) REFERENCES stock_master(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS user_portfolios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            stock_code TEXT NOT NULL,
            buy_date DATE,
            buy_price REAL,
            quantity INTEGER,
            sell_date DATE,
            sell_price REAL,
            transaction_type TEXT CHECK(transaction_type IN ('BUY', 'SELL')),
            fees REAL DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            stock_code TEXT,
            snapshot_date DATE,
            current_price REAL,
            market_cap REAL,
            pe_ratio REAL,
            pb_ratio REAL,
            calculated_value REAL,
            signal TEXT,
            unrealized_pnl REAL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS user_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            stock_code TEXT NOT NULL,
            alert_type TEXT CHECK(alert_type IN (
                'PRICE_ABOVE', 'PRICE_BELOW', 'VOLUME_SPIKE',
                'RSI_OVERSOLD', 'RSI_OVERBOUGHT'
            )),
            target_value REAL,
            is_active INTEGER DEFAULT 1,
            triggered INTEGER DEFAULT 0,
            triggered_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS user_watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            stock_code TEXT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, stock_code)
        );
    """)

    conn.commit()
    conn.close()

    # Eski tablolara role sutunu ekle (eger yoksa)
    try:
        conn2 = get_connection()
        conn2.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        conn2.commit()
        conn2.close()
    except Exception:
        pass  # Sutun zaten var


if __name__ == "__main__":
    init_db()
    print("Veritabani basariyla olusturuldu.")
