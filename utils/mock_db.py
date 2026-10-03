import sqlite3
import os
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from config import MOCK_DB_PATH


def get_db(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Returns a SQLite connection with row_factory configured."""
    target_path = db_path or MOCK_DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None, force_seed: bool = False):
    """Initializes tables and seeds test data if empty or force_seed is True."""
    target_path = db_path or MOCK_DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)

    with get_db(target_path) as conn:
        cursor = conn.cursor()
        
        # 1. users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                is_verified INTEGER NOT NULL DEFAULT 1
            )
        """)

        # 2. orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'INR',
                status TEXT NOT NULL,
                purchase_date TEXT NOT NULL,
                delivery_date TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)

        # 3. refunds table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS refunds (
                refund_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                amount REAL NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL,
                approved_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(order_id) REFERENCES orders(order_id),
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)

        # 4. audit_log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session TEXT NOT NULL,
                action TEXT NOT NULL,
                input TEXT NOT NULL,
                decision TEXT NOT NULL,
                reason TEXT NOT NULL
            )
        """)

        cursor.execute("SELECT COUNT(*) as count FROM users")
        user_count = cursor.fetchone()["count"]

        if user_count == 0 or force_seed:
            _seed_data(conn)


def _seed_data(conn: sqlite3.Connection):
    """Seeds exactly 6 users and 12 orders covering required scenarios."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM audit_log")
    cursor.execute("DELETE FROM refunds")
    cursor.execute("DELETE FROM orders")
    cursor.execute("DELETE FROM users")

    now = datetime.now(timezone.utc)
    fmt = "%Y-%m-%d"

    # Seed 6 users: 4 verified, 2 unverified
    users = [
        ("user_1", "Alice Johnson", "alice@example.com", 1),
        ("user_2", "Bob Smith", "bob@example.com", 1),
        ("user_3", "Charlie Davis", "charlie@example.com", 0),  # unverified user
        ("user_4", "Diana Prince", "diana@example.com", 1),
        ("user_5", "Evan Wright", "evan@example.com", 1),
        ("user_6", "Fiona Gallagher", "fiona@example.com", 0),  # unverified user
    ]
    cursor.executemany(
        "INSERT INTO users (user_id, name, email, is_verified) VALUES (?, ?, ?, ?)",
        users
    )

    # 12 orders covering all edge cases
    orders = [
        # 1. Delivered 3 days ago, eligible (<= 2000)
        ("ORD-1001", "user_1", "Wireless Noise-Cancelling Headphones", 1499.0, "INR", "delivered",
         (now - timedelta(days=6)).strftime(fmt), (now - timedelta(days=3)).strftime(fmt)),
        
        # 2. Delivered 30 days ago, expired window (> 14 days)
        ("ORD-1002", "user_1", "Ergonomic Mechanical Keyboard", 1800.0, "INR", "delivered",
         (now - timedelta(days=35)).strftime(fmt), (now - timedelta(days=30)).strftime(fmt)),
        
        # 3. Already refunded
        ("ORD-1003", "user_2", "Trail Running Shoes", 1200.0, "INR", "refunded",
         (now - timedelta(days=8)).strftime(fmt), (now - timedelta(days=5)).strftime(fmt)),
        
        # 4. Cancelled order (never delivered)
        ("ORD-1004", "user_2", "Smart Fitness Tracker", 2500.0, "INR", "cancelled",
         (now - timedelta(days=2)).strftime(fmt), None),
        
        # 5. High-value order: Rs 15,000 (delivered 4 days ago)
        ("ORD-1005", "user_1", "Ultra-Wide 4K Gaming Monitor", 15000.0, "INR", "delivered",
         (now - timedelta(days=6)).strftime(fmt), (now - timedelta(days=4)).strftime(fmt)),
        
        # 6. Unverified user order (delivered 3 days ago)
        ("ORD-1006", "user_3", "Portable Bluetooth Speaker", 999.0, "INR", "delivered",
         (now - timedelta(days=5)).strftime(fmt), (now - timedelta(days=3)).strftime(fmt)),
        
        # 7. Belongs to user_2 (delivered 2 days ago, for testing cross-user access by user_1)
        ("ORD-1007", "user_2", "7-in-1 USB-C Hub", 750.0, "INR", "delivered",
         (now - timedelta(days=4)).strftime(fmt), (now - timedelta(days=2)).strftime(fmt)),
        
        # 8. High value order (> 2000, delivered 7 days ago) for user_4
        ("ORD-1008", "user_4", "Ergonomic Mesh Office Chair", 4500.0, "INR", "delivered",
         (now - timedelta(days=9)).strftime(fmt), (now - timedelta(days=7)).strftime(fmt)),
        
        # 9. Small eligible order (delivered 10 days ago) for user_4
        ("ORD-1009", "user_4", "Non-Slip Desk Mat", 499.0, "INR", "delivered",
         (now - timedelta(days=12)).strftime(fmt), (now - timedelta(days=10)).strftime(fmt)),
        
        # 10. Borderline limit order Rs 1999 (delivered 1 day ago) for user_5
        ("ORD-1010", "user_5", "1080p Streaming Webcam", 1999.0, "INR", "delivered",
         (now - timedelta(days=3)).strftime(fmt), (now - timedelta(days=1)).strftime(fmt)),
        
        # 11. Processing order (not yet delivered) for user_5
        ("ORD-1011", "user_5", "Adjustable Aluminum Laptop Stand", 850.0, "INR", "processing",
         (now - timedelta(days=1)).strftime(fmt), None),
        
        # 12. Minor eligible order (delivered 2 days ago) for user_1
        ("ORD-1012", "user_1", "Silicone Smartphone Case", 350.0, "INR", "delivered",
         (now - timedelta(days=4)).strftime(fmt), (now - timedelta(days=2)).strftime(fmt)),
    ]
    cursor.executemany(
        """INSERT INTO orders 
           (order_id, user_id, item_name, amount, currency, status, purchase_date, delivery_date) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        orders
    )

    # Seed the refund record for ORD-1003
    cursor.execute(
        """INSERT INTO refunds 
           (refund_id, order_id, user_id, amount, reason, status, approved_by, created_at) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("REF-1001", "ORD-1003", "user_2", 1200.0, "Defective product on delivery", "completed", "system",
         (now - timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()


def reset_db(db_path: Optional[str] = None):
    """Resets and re-seeds database cleanly."""
    init_db(db_path=db_path, force_seed=True)


def log_audit(
    session: str,
    action: str,
    input_data: Any,
    decision: str,
    reason: str,
    db_path: Optional[str] = None
) -> int:
    """Appends an immutable audit record to the audit_log table."""
    target_path = db_path or MOCK_DB_PATH
    init_db(target_path)
    
    timestamp = datetime.now(timezone.utc).isoformat()
    serialized_input = json.dumps(input_data) if not isinstance(input_data, str) else input_data

    with get_db(target_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO audit_log (timestamp, session, action, input, decision, reason)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (timestamp, session, action, serialized_input, decision, reason)
        )
        conn.commit()
        return cursor.lastrowid


def get_user(user_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetches user record as dict."""
    target_path = db_path or MOCK_DB_PATH
    init_db(target_path)
    with get_db(target_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_order(order_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetches order record as dict."""
    target_path = db_path or MOCK_DB_PATH
    init_db(target_path)
    with get_db(target_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_orders_for_user(user_id: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches all orders associated with a user."""
    target_path = db_path or MOCK_DB_PATH
    init_db(target_path)
    with get_db(target_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY purchase_date DESC", (user_id,))
        return [dict(r) for r in cursor.fetchall()]


def get_refunds_for_order(order_id: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches all refunds associated with an order."""
    target_path = db_path or MOCK_DB_PATH
    init_db(target_path)
    with get_db(target_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM refunds WHERE order_id = ?", (order_id,))
        return [dict(r) for r in cursor.fetchall()]


def record_refund(
    refund_id: str,
    order_id: str,
    user_id: str,
    amount: float,
    reason: str,
    approved_by: str,
    status: str = "completed",
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Records a refund and updates order status to 'refunded' atomically."""
    target_path = db_path or MOCK_DB_PATH
    init_db(target_path)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    with get_db(target_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO refunds 
               (refund_id, order_id, user_id, amount, reason, status, approved_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (refund_id, order_id, user_id, amount, reason, status, approved_by, now_str)
        )
        cursor.execute(
            "UPDATE orders SET status = 'refunded' WHERE order_id = ?",
            (order_id,)
        )
        conn.commit()

    return {
        "refund_id": refund_id,
        "order_id": order_id,
        "user_id": user_id,
        "amount": amount,
        "reason": reason,
        "status": status,
        "approved_by": approved_by,
        "created_at": now_str
    }


def get_audit_logs(limit: int = 100, session: Optional[str] = None, action: Optional[str] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches recent audit log entries."""
    target_path = db_path or MOCK_DB_PATH
    init_db(target_path)
    with get_db(target_path) as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        if session:
            query += " AND session = ?"
            params.append(session)
        if action:
            query += " AND action = ?"
            params.append(action)
        query += " ORDER BY log_id DESC LIMIT ?"
        params.append(limit)
        cursor.execute(query, tuple(params))
        return [dict(r) for r in cursor.fetchall()]


# Ensure database and seed data are ready on initial load
init_db()
