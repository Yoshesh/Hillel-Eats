import customtkinter as ctk
import socket
import time
from user import User
import tkinter as tk
from tkinter import messagebox
import base64
import threading
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

SERVER_HOST = "localhost"
SERVER_PORT = 12345

global_active_orders = {}  # shared across all app instances

class HillelApp:
    def __init__(self, root):

        self.username = ""
        self.balance = 0.0
        self.cart = []
        self.cart_total = 0.0
        self.active_restaurant = None  # Used to lock ordering to one restaurant
        self.all_active_orders = global_active_orders



        self.root = root
        self.root.title("Login")
        self.root.geometry("300x300")
        self.center_window(root, 300,300)

        ctk.CTkLabel(root, text="Username").pack(pady=5)
        self.username_entry = ctk.CTkEntry(root)
        self.username_entry.pack(pady=5)

        ctk.CTkLabel(root, text="Password").pack(pady=5)
        self.password_entry = ctk.CTkEntry(root, show="*")
        self.password_entry.pack(pady=5)

        self.result_label = ctk.CTkLabel(root, text="")
        self.result_label.pack(pady=10)

        ctk.CTkButton(root, text="Login", command=self.try_login).pack(pady=10)

        ctk.CTkButton(root, text="Sign Up", command=self.register).pack(pady=10)

    def open_dashboard(self, username):
        self.clear_root()
        self.root.geometry("600x600")  # expand the window

        ctk.CTkLabel(self.root, text=f"Welcome, {username}!", font=ctk.CTkFont(size=20)).pack(pady=20)

        ctk.CTkButton(self.root, text="View Profile", command=self.open_profile_view).pack(pady=10)

        ctk.CTkButton(self.root, text="Browse Restaurants", command=self.open_restaurant_list).pack(pady=5)

        ctk.CTkButton(self.root, text="Browse by Category", command=self.open_category_list).pack(pady=5)

        ctk.CTkLabel(self.root, text="Search Restaurants or Categories").pack(pady=5)

        self.search_entry = ctk.CTkEntry(self.root, placeholder_text="e.g. Pizza or Sakura")
        self.search_entry.pack(pady=5)

        ctk.CTkButton(self.root, text="Search", command=self.handle_search).pack(pady=5)

        ctk.CTkButton(self.root, text="View Orders", command=self.open_order_window).pack(pady=30)

        ctk.CTkButton(
            self.root,
            text="Logout",
            command=self.show_login_screen,
            fg_color="#e74c3c",  # red
            hover_color="#c0392b",  # darker red on hover
            text_color="white"
        ).pack(pady=10)

    def handle_search(self):
        query = self.search_entry.get().strip().lower()
        # === Show favorites if query is "fav", "favorite", or "❤️"
        if query in ["fav", "favorite", "❤️"]:
            self.clear_root()
            self.root.geometry("600x400")
            ctk.CTkLabel(self.root, text="Your Favorite Restaurants", font=ctk.CTkFont(size=20)).pack(pady=10)

            fav_response = self.send_request(f"get_fav_rest|{self.username}!END")
            if fav_response.startswith("OK|"):
                favorites = fav_response.split("|")[1:]
                if favorites:
                    user_orders = self.all_active_orders.get(self.username, {})
                    for name in favorites:
                        state = "disabled" if name in user_orders else "normal"
                        ctk.CTkButton(self.root, text=f"❤️ {name}", command=lambda n=name: self.open_menu_view(n),
                                      state=state).pack(pady=3)

                else:
                    ctk.CTkLabel(self.root, text="No favorite restaurants yet.").pack(pady=10)
            else:
                ctk.CTkLabel(self.root, text="Failed to fetch favorites.").pack(pady=10)

            ctk.CTkButton(self.root, text="Back to Dashboard", command=lambda: self.open_dashboard(self.username)).pack(
                pady=20)
            return

        if not query:
            messagebox.showinfo("Info", "Please enter a search term.")
            return

        self.clear_root()
        self.root.geometry("600x400")

        ctk.CTkLabel(self.root, text=f"Search Results for '{query}'", font=ctk.CTkFont(size=20)).pack(pady=10)

        response = self.send_request("get_restaurants!END")
        if response.startswith("OK|"):
            all_restaurants = response.split("|")[1:]

            found = False
            for name in all_restaurants:
                rest_category = self.get_restaurant_category(name)
                if query in name.lower() or query in rest_category.lower():
                    found = True
                    state = "disabled" if name in self.all_active_orders.get(self.username, {}) else "normal"
                    ctk.CTkButton(self.root, text=name, command=lambda n=name: self.open_menu_view(n),
                                  state=state).pack(pady=3)

            if not found:
                ctk.CTkLabel(self.root, text="No results found.").pack(pady=10)
        else:
            ctk.CTkLabel(self.root, text="Failed to search restaurants.").pack(pady=10)

        ctk.CTkButton(self.root, text="Back to Dashboard", command=lambda: self.open_dashboard(self.username)).pack(
            pady=20)

    def update_order_labels(self):
        user_orders = self.all_active_orders.get(self.username, {})
        if not user_orders:
            if hasattr(self, "empty_order_label"):
                self.empty_order_label.configure(text="No orders placed")
            return

        user_orders = self.all_active_orders.get(self.username, {})
        for rest in list(user_orders.keys()):
            time_left = user_orders[rest]
            if time_left > 0:
                if rest in self.order_labels:
                    self.order_labels[rest].configure(text=f"{rest} | {time_left} mins left")
                else:
                    if rest in self.order_labels:
                        self.order_labels[rest].configure(text=f"{rest} | Delivered")
                    self.root.after(0,
                                    lambda r=rest: messagebox.showinfo("Order Ready", f"Your order from {r} is ready!"))
                    del user_orders[rest]

        self.root.after(60000, self.update_order_labels)

    def open_order_window(self):
        self.clear_root()
        self.root.geometry("400x400")

        self.order_labels = {}  # for live updates

        ctk.CTkLabel(self.root, text="Active Orders", font=ctk.CTkFont(size=20)).pack(pady=15)

        user_orders = self.all_active_orders.get(self.username, {})
        if not user_orders:
            self.empty_order_label = ctk.CTkLabel(self.root, text="No orders placed")
            self.empty_order_label.pack(pady=10)
        else:
            for rest, time_left in user_orders.items():
                label = ctk.CTkLabel(self.root, text=f"{rest} | {time_left} mins left")
                label.pack(pady=5)
                self.order_labels[rest] = label

        ctk.CTkButton(self.root, text="Back to Dashboard", command=lambda: self.open_dashboard(self.username)).pack(
            pady=20)

        self.update_order_labels()

    def open_category_list(self):
        self.clear_root()
        self.root.geometry("600x400")

        ctk.CTkLabel(self.root, text="Select a Category", font=ctk.CTkFont(size=20)).pack(pady=15)

        categories = ["Burgers", "Pizza", "Sushi"]

        for cat in categories:
            ctk.CTkButton(self.root, text=cat, command=lambda c=cat: self.open_restaurant_list_by_category(c)).pack(
                pady=5)

        ctk.CTkButton(self.root, text="Back to Dashboard", command=lambda: self.open_dashboard(self.username)).pack(
            pady=20)

    def open_restaurant_list_by_category(self, category):
        self.clear_root()
        self.root.geometry("600x400")
        user_orders = self.all_active_orders.get(self.username, {})

        ctk.CTkLabel(self.root, text=f"{category} Restaurants", font=ctk.CTkFont(size=20)).pack(pady=10)

        response = self.send_request("get_restaurants!END")
        if response.startswith("OK|"):
            all_restaurants = response.split("|")[1:]
            for name in all_restaurants:
                rest_category = self.get_restaurant_category(name)
                if rest_category == category:
                    state = "normal" if self.active_restaurant in [None, name] else "disabled"
                    state = "disabled" if name in user_orders else "normal"
                    ctk.CTkButton(self.root, text=name, command=lambda n=name: self.open_menu_view(n),
                                  state=state).pack(pady=5)

        ctk.CTkButton(self.root, text="Back to Categories", command=self.open_category_list).pack(pady=20)

    def get_restaurant_category(self, name):
        # Small trick — use a special server call if needed
        response = self.send_request(f"get_restaurant_category|{name}!END")
        if response.startswith("OK|"):
            return response.split("|")[1]
        return None

    def open_profile_view(self):
        self.clear_root()
        self.root.geometry("600x500")

        ctk.CTkLabel(self.root, text="User Profile", font=ctk.CTkFont(size=20)).pack(pady=10)
        ctk.CTkLabel(self.root, text=f"Username: {self.username}").pack(pady=5)
        self.balance_label = ctk.CTkLabel(self.root, text=f"Balance: ${self.balance:.2f}")
        self.balance_label.pack(pady=5)

        ctk.CTkLabel(self.root, text="Add Money").pack(pady=5)
        self.amount_entry = ctk.CTkEntry(self.root, placeholder_text="Enter amount")
        self.amount_entry.pack(pady=5)

        ctk.CTkButton(self.root, text="Add Funds", command=self.add_money).pack(pady=5)

        # === Toggleable Scrollable Order History ===
        toggle_state = {"open": False}

        toggle_button = ctk.CTkButton(self.root, text="▶ Order History")
        toggle_button.pack(pady=(10, 5))

        scroll_container = ctk.CTkFrame(self.root)
        canvas = tk.Canvas(scroll_container, height=150, bg="#2b2b2b", highlightthickness=0)
        scrollbar = tk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)
        history_frame = ctk.CTkFrame(canvas)

        canvas.create_window((0, 0), window=history_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 🔧 Enable mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Load order history from server
        hist_response = self.send_request(f"get_order_history|{self.username}!END")
        if hist_response.startswith("OK|"):
            orders = hist_response.split("|")[1:]
            if orders:
                for entry in orders:
                    try:
                        rest, ts = entry.split(",")
                        readable_time = time.strftime('%Y-%m-%d %H:%M', time.localtime(int(ts)))
                        ctk.CTkLabel(history_frame, text=f"{rest} — {readable_time}", anchor="w").pack(anchor="w",
                                                                                                       padx=10)
                    except:
                        pass
            else:
                ctk.CTkLabel(history_frame, text="No past orders.", anchor="w").pack(anchor="w", padx=10)
        else:
            ctk.CTkLabel(history_frame, text="Failed to load history.", anchor="w").pack(anchor="w", padx=10)

        # Hide history by default
        scroll_container.pack_forget()

        def toggle_history():
            if toggle_state["open"]:
                scroll_container.pack_forget()
                toggle_button.configure(text="▶ Order History")
                toggle_state["open"] = False
            else:
                scroll_container.pack(pady=5, fill="both", expand=False, padx=10)
                toggle_button.configure(text="▼ Order History")
                toggle_state["open"] = True

        toggle_button.configure(command=toggle_history)

        # Back to dashboard
        ctk.CTkButton(self.root, text="Back to Dashboard", command=lambda: self.open_dashboard(self.username)).pack(
            pady=15)

    def toggle_food_favorite(self, meal_name, restaurant_name, label_widget):
        self.send_request(f"toggle_fav_food|{self.username}|{meal_name}|{restaurant_name}!END")
        fav_response = self.send_request(f"get_fav_food|{self.username}|{restaurant_name}!END")
        if fav_response.startswith("OK|"):
            fav_foods = set(fav_response.split("|")[1:])
            heart = "❤️" if meal_name in fav_foods else "🤍"
            label_widget.configure(text=f"{heart} {meal_name}")

    def toggle_rest_favorite(self, restaurant_name, button_label):
        self.send_request(f"toggle_fav_rest|{self.username}|{restaurant_name}!END")

        # עדכון מצב הלב מחדש לאחר לחיצה
        fav_response = self.send_request(f"get_fav_rest|{self.username}!END")
        if fav_response.startswith("OK|"):
            favorites = set(fav_response.split("|")[1:])
            heart = "❤️" if restaurant_name in favorites else "🤍"
            button_label.configure(text=f"{heart} {restaurant_name}")

    def open_restaurant_list(self):
        self.clear_root()
        self.root.geometry("600x500")
        user_orders = self.all_active_orders.get(self.username, {})

        ctk.CTkLabel(self.root, text="Choose a Restaurant", font=ctk.CTkFont(size=20)).pack(pady=10)

        response = self.send_request("get_restaurants!END")
        fav_response = self.send_request(f"get_fav_rest|{self.username}!END")
        favorites = set()
        if fav_response.startswith("OK|"):
            favorites = set(fav_response.split("|")[1:])

        if response.startswith("OK|"):
            restaurants = response.split("|")[1:]  # remove "OK"
            for name in restaurants:
                # --- Block if already has active order OR a different restaurant is locked
                if name in user_orders:
                    state = "disabled"
                elif self.active_restaurant is not None and self.active_restaurant != name:
                    state = "disabled"
                else:
                    state = "normal"

                heart = "❤️" if name in favorites else "🤍"
                row = ctk.CTkFrame(self.root)
                row.pack(pady=3)

                name_label = ctk.CTkLabel(row, text=f"{heart} {name}", width=200, anchor="w")
                name_label.pack(side="left")

                ctk.CTkButton(row, text="🖤", width=30,
                              command=lambda n=name, lbl=name_label: self.toggle_rest_favorite(n, lbl)).pack(
                    side="left")

                ctk.CTkButton(row, text="Open", command=lambda n=name: self.open_menu_view(n), state=state).pack(
                    side="right")

        else:
            ctk.CTkLabel(self.root, text="Could not load restaurants.").pack(pady=10)

        ctk.CTkButton(self.root, text="Back to Dashboard", command=lambda: self.open_dashboard(self.username)).pack(
            pady=20)

    def schedule_order_countdown(self, username, restaurant):
        def countdown():
            if username in self.all_active_orders and restaurant in self.all_active_orders[username]:
                time_left = self.all_active_orders[username][restaurant]
                if time_left > 0:
                    self.all_active_orders[username][restaurant] -= 1
                    self.root.after(60000, countdown)
                else:
                    self.root.after(0, lambda r=restaurant: messagebox.showinfo("Order Ready",
                                                                                f"Your order from {r} is ready!"))
                    del self.all_active_orders[username][restaurant]

        self.root.after(60000, countdown)

    def confirm_order(self):
        user_orders = self.all_active_orders.get(self.username, {})

        if self.cart_total > self.balance:
            messagebox.showerror("Error", "Not enough balance.")
            return

        # מניעת הזמנה כפולה מאותה מסעדה
        if self.last_restaurant in user_orders:
            messagebox.showwarning("Warning", "You already have an active order from this restaurant.")
            return

        # הורדת סכום מהמאזן המקומי
        self.balance -= self.cart_total

        # עדכון היתרה בשרת
        message = f"add_money|{self.username}|{-self.cart_total}!END"
        response = self.send_request(message)
        if not response.startswith("OK|"):
            messagebox.showerror("Error", "Failed to update balance on server.")
            return

        # שליחת ההזמנה להיסטוריה
        log_msg = f"log_order|{self.username}|{self.last_restaurant}!END"
        self.send_request(log_msg)

        # בקשת זמן משלוח מהשרת
        response = self.send_request(f"get_restaurant_delivery|{self.last_restaurant}!END")
        if response.startswith("OK|"):
            delivery_time = int(response.split("|")[1])
        else:
            delivery_time = 20  # ברירת מחדל אם אין תגובה תקינה

        # התחלת טיימר משלוח
        if self.username not in self.all_active_orders:
            self.all_active_orders[self.username] = {}

        self.all_active_orders[self.username][self.last_restaurant] = delivery_time
        self.schedule_order_countdown(self.username, self.last_restaurant)

        # הודעה למשתמש
        messagebox.showinfo("Order Confirmed", f"{self.last_restaurant} is on the way!")

        # ניקוי סל קניות
        self.cart.clear()
        self.cart_total = 0.0
        self.active_restaurant = None

        # חזרה ללוח הבקרה
        self.open_dashboard(self.username)

    def open_checkout_window(self):
        self.clear_root()
        self.root.geometry("400x400")

        ctk.CTkLabel(self.root, text="Your Order", font=ctk.CTkFont(size=20)).pack(pady=10)

        if not self.cart:
            ctk.CTkLabel(self.root, text="Your cart is empty.").pack(pady=10)
            return

        for item, price in self.cart:
            ctk.CTkLabel(self.root, text=f"{item} - ${price:.2f}").pack()

        ctk.CTkLabel(self.root, text=f"Total: ${self.cart_total:.2f}", font=ctk.CTkFont(size=14, weight="bold")).pack(
            pady=10)

        ctk.CTkButton(self.root, text="Confirm Order", command=self.confirm_order).pack(pady=5)
        ctk.CTkButton(self.root, text="Back to Menu", command=lambda: self.open_menu_view(self.last_restaurant)).pack(
            pady=10)

    def add_to_cart(self, item_name, price):
        if self.active_restaurant is None:
            self.active_restaurant = self.last_restaurant  # lock to the first restaurant used

        self.cart.append((item_name, price))
        self.cart_total += price
        messagebox.showinfo("Added to Cart", f"{item_name} added (${price:.2f})")

        if hasattr(self, "checkout_button"):
            self.checkout_button.configure(state="normal")

    def open_menu_view(self, restaurant_name):
        self.clear_root()
        self.root.geometry("600x400")
        self.last_restaurant = restaurant_name  # Store for return/back logic
        fav_response = self.send_request(f"get_fav_food|{self.username}|{restaurant_name}!END")
        fav_foods = set()
        if fav_response.startswith("OK|"):
            fav_foods = set(fav_response.split("|")[1:])

        response = self.send_request(f"get_menu|{restaurant_name}!END")
        if response.startswith("OK|"):
            parts = response.split("|")
            delivery_time = parts[1]
            meals = parts[2:]

            ctk.CTkLabel(self.root, text=f"{restaurant_name} Menu", font=ctk.CTkFont(size=20)).pack(pady=10)
            ctk.CTkLabel(self.root, text=f"Estimated Delivery Time: {delivery_time} min").pack(pady=5)

            for item in meals:
                try:
                    name, price = item.split(",")
                    price = float(price)
                    heart = "❤️" if name in fav_foods else "🤍"
                    row = ctk.CTkFrame(self.root)
                    row.pack(pady=2)

                    name_label = ctk.CTkLabel(row, text=f"{heart} {name} - ${price:.2f}", anchor="w", width=250)
                    name_label.pack(side="left")

                    ctk.CTkButton(row, text="Add", command=lambda n=name, p=price: self.add_to_cart(n, p)).pack(
                        side="right")
                    ctk.CTkButton(row, text="🖤", width=30, command=lambda n=name, lbl=name_label: self.toggle_food_favorite(n, restaurant_name, lbl)).pack(side="right")

                except Exception as e:
                    print("[ERROR parsing meal item]:", item, e)

            # Checkout button - disabled by default
            initial_state = "normal" if self.cart and self.last_restaurant == self.active_restaurant else "disabled"

            self.checkout_button = ctk.CTkButton(
                self.root,
                text="Checkout",
                state=initial_state,
                command=self.open_checkout_window
            )

            self.checkout_button.pack(pady=15)

        else:
            ctk.CTkLabel(self.root, text="Failed to load menu").pack()

        ctk.CTkButton(self.root, text="Back to Restaurants", command=self.open_category_list).pack(pady=10)

    def add_money(self):
        try:
            amount = float(self.amount_entry.get())
            if amount <= 0:
                raise ValueError("Amount must be positive")

            # Send request to server
            message = f"add_money|{self.username}|{amount}!END"
            response = self.send_request(message)

            if response.startswith("OK|"):
                new_balance = float(response.split("|")[1])
                self.balance = new_balance
                self.balance_label.configure(text=f"Balance: ${self.balance:.2f}")
                messagebox.showinfo("Success", f"Added ${amount:.2f} to your balance!")
                self.amount_entry.delete(0, 'end')
            else:
                messagebox.showerror("Error", "Failed to add funds.")
        except ValueError:
            messagebox.showerror("Error", "Invalid amount.")

    def show_login_screen(self):
        self.active_restaurant = None
        self.cart = []
        self.cart_total = 0.0
        self.clear_root()
        self.__init__(self.root)

    def clear_root(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def send_request(self, message):
        try:
            print("(DEBUG) send_request activated")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((SERVER_HOST, SERVER_PORT))
                sock.sendall(message.encode())
                response = sock.recv(1024).decode()
                print(f"response = {response} ")
                return response
        except Exception as e:
            messagebox.showerror("Error", f"Server error: {e}")
        return "FAIL"
    def center_window(self, window, width, height):
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")

    def register(self):
        self.clear_root()

        self.root.title("Sign up")
        self.root.geometry("300x300")
        self.center_window(self.root, 300, 300)

        ctk.CTkLabel(self.root, text="Username").pack(pady=5)
        self.username_CTkEntry = ctk.CTkEntry(self.root)
        self.username_CTkEntry.pack(pady=5)

        ctk.CTkLabel(self.root, text="Password").pack(pady=5)
        self.password_CTkEntry = ctk.CTkEntry(self.root, show="*")
        self.password_CTkEntry.pack(pady=5)

        self.result_label = ctk.CTkLabel(root, text="")
        self.result_label.pack(pady=10)


        def submit_signup():
            username = self.username_CTkEntry.get().strip()
            password = self.password_CTkEntry.get().strip()

            if not username or not password:
                messagebox.showerror("Error", "All fields are required.")
                return

            # Load public key for RSA
            try:
                with open("rsa_public.pem", "rb") as f:
                    key = RSA.import_key(f.read())
                    cipher = PKCS1_OAEP.new(key)
            except Exception as e:
                messagebox.showerror("Error", f"Could not load public key:\n{e}")
                return

            try:
                encrypted_username = base64.b64encode(cipher.encrypt(username.encode())).decode()
                encrypted_password = base64.b64encode(cipher.encrypt(password.encode())).decode()

                print("[DEBUG] Encrypted username:", encrypted_username)
                print("[DEBUG] Encrypted password:", encrypted_password)
                print("[DEBUG] Total message length:",
                      len(f"register|{encrypted_username}|{encrypted_password}"))
            except Exception as e:
                messagebox.showerror("Error", f"Encryption failed:\n{e}")
                return

            message = f"signup|{encrypted_username}|{encrypted_password}!END"
            print("[DEBUG] Final message sending to server:", message)

            def handle_response():
                response = self.send_request(message)

                if response == "OK":
                    self.username = username
                    self.root.after(0, lambda: [
                        messagebox.showinfo("Success", "Account created successfully!"),
                        self.open_dashboard(username)
                    ])
                    print("Working as intended")
                elif response == "FAIL":
                    self.root.after(0, lambda: messagebox.showerror("Error", "Username already exists."))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Unexpected response: {response}"))

            threading.Thread(target=handle_response).start()

        ctk.CTkButton(root, text="Create Account", command=lambda: threading.Thread(target=submit_signup).start()).pack(
            pady=10)
        ctk.CTkButton(self.root, text="Back to Login", command=self.show_login_screen).pack(pady=10)

    def try_login(self):
        # Encrypt username and password
        encrypted_username = User.encrypt_rsa(self.username_entry.get())
        encrypted_password = User.encrypt_rsa(self.password_entry.get())
        message = f"login|{encrypted_username}|{encrypted_password}!END"
        response = self.send_request(message)

        if response.startswith("OK|"):
            self.username = self.username_entry.get()
            self.balance = float(response.split("|")[1])
            self.result_label.configure(text="✅ Login successful", text_color="green")
            self.open_dashboard(self.username)
        elif response == "FAIL":
            self.result_label.configure(text="❌ Login Failed", text_color="red")
        else:
            self.result_label.configure(text=f"⚠ {response}", text_color="orange")

if __name__ == "__main__":
    root = ctk.CTk()
    app = HillelApp(root)
    root.mainloop()
