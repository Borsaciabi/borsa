import sqlite3
from datetime import datetime
from data.database.models import get_connection, init_db


class DBManager:
    def __init__(self):
        init_db()

    def _get_conn(self):
        return get_connection()

    def create_user(self, username, email, password_hash):
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash),
            )
            conn.commit()
            user = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
            return dict(user)
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()

    def get_user_by_username(self, username):
        conn = self._get_conn()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()
        return dict(user) if user else None

    def get_user_by_email(self, email):
        conn = self._get_conn()
        user = conn.execute(
            "SELECT * FROM users WHERE lower(email) = lower(?)", (email,)
        ).fetchone()
        conn.close()
        return dict(user) if user else None

    def get_user_by_id(self, user_id):
        conn = self._get_conn()
        user = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        conn.close()
        return dict(user) if user else None

    def get_user_by_telegram_id(self, telegram_id):
        conn = self._get_conn()
        user = conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        conn.close()
        return dict(user) if user else None

    def link_telegram(self, user_id, telegram_id, telegram_username):
        conn = self._get_conn()
        linked = conn.execute(
            "SELECT id FROM users WHERE telegram_id = ? AND id != ?",
            (telegram_id, user_id),
        ).fetchone()
        if linked:
            conn.close()
            return False
        conn.execute(
            "UPDATE users SET telegram_id = ?, telegram_username = ? WHERE id = ?",
            (telegram_id, telegram_username, user_id),
        )
        conn.commit()
        conn.close()
        return True

    def update_last_login(self, user_id):
        conn = self._get_conn()
        conn.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now().isoformat(), user_id),
        )
        conn.commit()
        conn.close()

    def add_trade(self, user_id, stock_code, buy_date, buy_price, quantity,
                  transaction_type, fees=0, notes=""):
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO user_portfolios
               (user_id, stock_code, buy_date, buy_price, quantity,
                transaction_type, fees, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, stock_code, buy_date, buy_price, quantity,
             transaction_type, fees, notes),
        )
        conn.commit()
        conn.close()

    def sell_stock(self, user_id, stock_code, sell_date, sell_price, quantity, fees=0):
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO user_portfolios
               (user_id, stock_code, sell_date, sell_price, quantity,
                transaction_type, fees)
               VALUES (?, ?, ?, ?, ?, 'SELL', ?)""",
            (user_id, stock_code, sell_date, sell_price, quantity, fees),
        )
        conn.commit()
        conn.close()

    def get_portfolio(self, user_id):
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM user_portfolios WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_active_positions(self, user_id):
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT stock_code,
                      SUM(CASE WHEN transaction_type='BUY' THEN quantity ELSE 0 END)
                      - SUM(CASE WHEN transaction_type='SELL' THEN quantity ELSE 0 END)
                      as net_quantity,
                      SUM(CASE WHEN transaction_type='BUY' THEN buy_price * quantity ELSE 0 END)
                      / SUM(CASE WHEN transaction_type='BUY' THEN quantity ELSE 1 END)
                      as avg_buy_price
               FROM user_portfolios
               WHERE user_id = ?
               GROUP BY stock_code
               HAVING net_quantity > 0""",
            (user_id,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_alert(self, user_id, stock_code, alert_type, target_value):
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO user_alerts (user_id, stock_code, alert_type, target_value)
               VALUES (?, ?, ?, ?)""",
            (user_id, stock_code, alert_type, target_value),
        )
        conn.commit()
        conn.close()

    def get_active_alerts(self, user_id=None):
        conn = self._get_conn()
        if user_id:
            rows = conn.execute(
                "SELECT * FROM user_alerts WHERE user_id = ? AND is_active = 1",
                (user_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM user_alerts WHERE is_active = 1"
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def trigger_alert(self, alert_id):
        conn = self._get_conn()
        conn.execute(
            "UPDATE user_alerts SET triggered = 1, triggered_at = ? WHERE id = ?",
            (datetime.now().isoformat(), alert_id),
        )
        conn.commit()
        conn.close()

    def delete_alert(self, alert_id, user_id):
        conn = self._get_conn()
        conn.execute(
            "DELETE FROM user_alerts WHERE id = ? AND user_id = ?",
            (alert_id, user_id),
        )
        conn.commit()
        conn.close()

    def add_to_watchlist(self, user_id, stock_code):
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO user_watchlist (user_id, stock_code) VALUES (?, ?)",
                (user_id, stock_code),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_watchlist(self, user_id):
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM user_watchlist WHERE user_id = ?", (user_id,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_all_portfolio(self, user_id):
        conn = self._get_conn()
        conn.execute("DELETE FROM user_portfolios WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

    def upsert_stock(self, symbol, company_name="", sector="", exchange="BIST"):
        conn = self._get_conn()
        normalized = (symbol or "").strip().upper()
        existing = conn.execute(
            "SELECT * FROM stock_master WHERE symbol = ?",
            (normalized,),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE stock_master SET company_name = ?, sector = ?, exchange = ?, updated_at = CURRENT_TIMESTAMP WHERE symbol = ?",
                (company_name or existing["company_name"], sector or existing["sector"], exchange, normalized),
            )
            conn.commit()
            conn.close()
            return dict(conn.execute("SELECT * FROM stock_master WHERE symbol = ?", (normalized,)).fetchone()) if False else self.get_stock_by_symbol(normalized)
        conn.execute(
            "INSERT INTO stock_master (symbol, company_name, sector, exchange) VALUES (?, ?, ?, ?)",
            (normalized, company_name, sector, exchange),
        )
        conn.commit()
        stock = conn.execute("SELECT * FROM stock_master WHERE symbol = ?", (normalized,)).fetchone()
        conn.close()
        return dict(stock) if stock else None

    def get_stock_by_symbol(self, symbol):
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM stock_master WHERE symbol = ?",
            (str(symbol or "").strip().upper(),),
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_stocks(self):
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM stock_master ORDER BY symbol ASC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_stock_user_view(self, symbol):
        conn = self._get_conn()
        row = conn.execute(
            """
            SELECT v.* FROM stock_user_views v
            JOIN stock_master s ON s.id = v.stock_id
            WHERE s.symbol = ?
            """,
            (str(symbol or "").strip().upper(),),
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def save_stock_user_view(self, symbol, opinion, personal_signal, price_target):
        stock = self.get_stock_by_symbol(symbol)
        if not stock:
            stock = self.upsert_stock(symbol)
        if not stock:
            return None
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO stock_user_views (stock_id, opinion, personal_signal, price_target)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(stock_id) DO UPDATE SET
                opinion = excluded.opinion,
                personal_signal = excluded.personal_signal,
                price_target = excluded.price_target,
                updated_at = CURRENT_TIMESTAMP
            """,
            (stock["id"], opinion or "", personal_signal or "Izle", price_target),
        )
        conn.commit()
        conn.close()
        return self.get_stock_user_view(symbol)

    def seed_default_stocks(self, symbols=None, company_names=None):
        from config.constants import BIST_100, BIST_30
        all_symbols = list(symbols or BIST_100)
        if not all_symbols:
            return []
        default_company_names = company_names or {}
        inserted = []
        for symbol in all_symbols:
            code = str(symbol or "").strip().upper()
            if not code:
                continue
            company_name = default_company_names.get(code, "")
            stock = self.upsert_stock(code, company_name=company_name, sector="", exchange="BIST")
            if stock:
                inserted.append(stock)
        return inserted

    def upsert_stock_market_data(self, symbol, source="system", **data):
        stock = self.get_stock_by_symbol(symbol)
        if not stock:
            stock = self.upsert_stock(symbol)
        if not stock:
            return None
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO stock_market_data (
                stock_id, source, last_price, change_pct, volume, market_cap, net_debt,
                total_shares, float_rate, floating_shares, pe, pb, calculated_value, ratio, signal,
                financial_period, total_equity, paid_in_capital, net_income, financial_periods
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(stock_id, source) DO UPDATE SET
                last_price = excluded.last_price,
                change_pct = excluded.change_pct,
                volume = excluded.volume,
                market_cap = excluded.market_cap,
                net_debt = excluded.net_debt,
                total_shares = excluded.total_shares,
                float_rate = excluded.float_rate,
                floating_shares = excluded.floating_shares,
                pe = excluded.pe,
                pb = excluded.pb,
                calculated_value = excluded.calculated_value,
                ratio = excluded.ratio,
                signal = excluded.signal,
                financial_period = excluded.financial_period,
                total_equity = excluded.total_equity,
                paid_in_capital = excluded.paid_in_capital,
                net_income = excluded.net_income,
                financial_periods = excluded.financial_periods,
                recorded_at = CURRENT_TIMESTAMP
            """,
            (
                stock["id"],
                source,
                data.get("last_price"),
                data.get("change_pct"),
                data.get("volume"),
                data.get("market_cap"),
                data.get("net_debt"),
                data.get("total_shares"),
                data.get("float_rate"),
                data.get("floating_shares"),
                data.get("pe"),
                data.get("pb"),
                data.get("calculated_value"),
                data.get("ratio"),
                data.get("signal"),
                data.get("financial_period"),
                data.get("total_equity"),
                data.get("paid_in_capital"),
                data.get("net_income"),
                data.get("financial_periods"),
            ),
        )
        conn.commit()
        conn.close()
        return self.get_stock_by_symbol(symbol)

    def get_all_users(self):
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, username, email, role, is_active, created_at, last_login, telegram_username FROM users ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_all_stock_market_data(self):
        """Return the latest persisted market data together with its source."""
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT
                sm.symbol,
                sm.company_name,
                sm.sector,
                smd.source,
                smd.last_price,
                smd.change_pct,
                smd.volume,
                smd.market_cap,
                smd.net_debt,
                smd.total_shares,
                smd.float_rate,
                smd.floating_shares,
                smd.pe,
                smd.pb,
                smd.calculated_value,
                smd.ratio,
                smd.signal,
                smd.financial_period,
                smd.total_equity,
                smd.paid_in_capital,
                smd.net_income,
                smd.financial_periods,
                smd.recorded_at
            FROM stock_master sm
            LEFT JOIN stock_market_data smd ON smd.stock_id = sm.id
            ORDER BY sm.symbol
            """
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_database_tables(self):
        """Return application tables that are safe to inspect in the admin UI."""
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
        conn.close()
        return [row["name"] for row in rows]

    def get_table_rows(self, table_name, limit=200):
        """Read a bounded table sample for the admin data browser."""
        allowed = set(self.get_database_tables())
        if table_name not in allowed:
            raise ValueError("Gecersiz veritabani tablosu")
        safe_limit = max(1, min(int(limit), 500))
        conn = self._get_conn()
        rows = conn.execute(
            f'SELECT * FROM "{table_name}" LIMIT ?', (safe_limit,)
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_user_count(self):
        conn = self._get_conn()
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        return count

    def set_user_role(self, user_id, role):
        conn = self._get_conn()
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        conn.commit()
        conn.close()

    def set_user_active(self, user_id, is_active):
        conn = self._get_conn()
        conn.execute("UPDATE users SET is_active = ? WHERE id = ?", (is_active, user_id))
        conn.commit()
        conn.close()

    def delete_user(self, user_id):
        conn = self._get_conn()
        conn.execute("DELETE FROM users WHERE id = ? AND role != 'admin'", (user_id,))
        conn.commit()
        conn.close()

    def update_user_profile(self, user_id, email=None, telegram_id=None, telegram_username=None):
        conn = self._get_conn()
        if email:
            conn.execute("UPDATE users SET email = ? WHERE id = ?", (email, user_id))
        if telegram_id is not None:
            conn.execute(
                "UPDATE users SET telegram_id = ?, telegram_username = ? WHERE id = ?",
                (telegram_id, telegram_username, user_id),
            )
        conn.commit()
        conn.close()

    def change_password(self, user_id, new_password_hash):
        conn = self._get_conn()
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_password_hash, user_id))
        conn.commit()
        conn.close()

    def ensure_admin(self, username="admin", password="admin123", email="admin@borsa.local"):
        """Admin kullanici yoksa olusturur."""
        existing = self.get_user_by_username(username)
        if existing:
            return existing
        from auth.password import hash_password
        pw_hash = hash_password(password)
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
            (username, email, pw_hash),
        )
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        return dict(user) if user else None
