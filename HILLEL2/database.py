import sqlite3
import time

class Database:
    def __init__(self, db_name="hilleleats.db"):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_name, timeout=5) as conn:
            c = conn.cursor()

            # משתמשים רגילים
            c.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password TEXT,
                    balance REAL DEFAULT 0.0
                )
            """)

            # מסעדות
            c.execute("""
                CREATE TABLE IF NOT EXISTS restaurants (
                    name TEXT PRIMARY KEY,
                    category TEXT,
                    delivery_time INTEGER
                )
            """)

            c.execute("""
                       CREATE TABLE IF NOT EXISTS favorites_restaurants (
                           username TEXT,
                           restaurant TEXT,
                           PRIMARY KEY (username, restaurant),
                           FOREIGN KEY (username) REFERENCES users(username),
                           FOREIGN KEY (restaurant) REFERENCES restaurants(name)
                       )
                   """)

            c.execute("""
                CREATE TABLE IF NOT EXISTS favorites_food (
                    username TEXT,
                    meal_name TEXT,
                    restaurant TEXT,
                    PRIMARY KEY (username, meal_name, restaurant),
                    FOREIGN KEY (username) REFERENCES users(username),
                    FOREIGN KEY (restaurant) REFERENCES restaurants(name)
                )
            """)

            # מנות - לפי שם מסעדה + שם המנה
            c.execute("""
                CREATE TABLE IF NOT EXISTS food_items (
                    restaurant_name TEXT,
                    meal_name TEXT,
                    price REAL,
                    FOREIGN KEY (restaurant_name) REFERENCES restaurants(name)
                )
            """)

            # Order history table
            c.execute("""
                CREATE TABLE IF NOT EXISTS order_history (
                    username TEXT,
                    restaurant TEXT,
                    timestamp INTEGER,
                    FOREIGN KEY (username) REFERENCES users(username),
                    FOREIGN KEY (restaurant) REFERENCES restaurants(name)
                )
            """)

            conn.commit()

    # ========== משתמשים רגילים ==========

    def add_order_history(self, username, restaurant):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO order_history (username, restaurant, timestamp) VALUES (?, ?, ?)",
                      (username, restaurant, int(time.time())))
            conn.commit()

    def get_order_history(self, username):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("SELECT restaurant, timestamp FROM order_history WHERE username = ? ORDER BY timestamp DESC",
                      (username,))
            return c.fetchall()

    def insert_user(self, username, password):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()

    def get_delivery_time(self, restaurant_name):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("SELECT delivery_time FROM restaurants WHERE name = ?", (restaurant_name,))
            result = c.fetchone()
            return result[0] if result else 0

    def get_all_restaurants(self):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM restaurants")
            return [row[0] for row in c.fetchall()]

    def get_user_password(self, username):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("SELECT password FROM users WHERE username = ?", (username,))
            result = c.fetchone()
            return result[0] if result else None

    def get_user_balance(self, username):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("SELECT balance FROM users WHERE username = ?", (username,))
            result = c.fetchone()
            return result[0] if result else None

    def update_balance(self, username, amount):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET balance = balance + ? WHERE username = ?", (amount, username))
            conn.commit()
            c.execute("SELECT balance FROM users WHERE username = ?", (username,))
            return c.fetchone()[0]

    # ========== בעלי עסקים ==========

    def insert_restaurant(self, name, category, delivery_time):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO restaurants (name, category, delivery_time) VALUES (?, ?, ?)",
                      (name, category, delivery_time))
            conn.commit()

    def get_restaurant_password(self, name):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("SELECT password FROM restaurants WHERE name = ?", (name,))
            result = c.fetchone()
            return result[0] if result else None

    def insert_meal(self, restaurant_name, meal_name, price):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO food_items (restaurant_name, meal_name, price) VALUES (?, ?, ?)",
                      (restaurant_name, meal_name, price))
            conn.commit()

    def get_meals_for_restaurant(self, restaurant_name):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("SELECT meal_name, price FROM food_items WHERE restaurant_name = ?", (restaurant_name,))
            return c.fetchall()

    def delete_meal(self, restaurant_name, meal_name):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM food_items WHERE restaurant_name = ? AND meal_name = ?",
                      (restaurant_name, meal_name))
            conn.commit()

    # Add/remove favorite restaurant
    def toggle_favorite_restaurant(self, username, restaurant):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("SELECT 1 FROM favorites_restaurants WHERE username = ? AND restaurant = ?",
                      (username, restaurant))
            if c.fetchone():
                c.execute("DELETE FROM favorites_restaurants WHERE username = ? AND restaurant = ?",
                          (username, restaurant))
            else:
                c.execute("INSERT INTO favorites_restaurants (username, restaurant) VALUES (?, ?)",
                          (username, restaurant))
            conn.commit()

    def get_favorite_restaurants(self, username):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("SELECT restaurant FROM favorites_restaurants WHERE username = ?", (username,))
            return [row[0] for row in c.fetchall()]

    # Add/remove favorite food
    def toggle_favorite_food(self, username, meal_name, restaurant):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("SELECT 1 FROM favorites_food WHERE username = ? AND meal_name = ? AND restaurant = ?",
                      (username, meal_name, restaurant))
            if c.fetchone():
                c.execute("DELETE FROM favorites_food WHERE username = ? AND meal_name = ? AND restaurant = ?",
                          (username, meal_name, restaurant))
            else:
                c.execute("INSERT INTO favorites_food (username, meal_name, restaurant) VALUES (?, ?, ?)",
                          (username, meal_name, restaurant))
            conn.commit()

    def get_favorite_foods(self, username, restaurant):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute("SELECT meal_name FROM favorites_food WHERE username = ? AND restaurant = ?",
                      (username, restaurant))
            return [row[0] for row in c.fetchall()]
