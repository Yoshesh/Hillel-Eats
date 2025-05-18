import socket
import threading
import json
import sqlite3
import hashlib
from database import Database
import bcrypt
import time
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import base64

db = Database()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def decrypt_field(encrypted_base64):
    with open("rsa_private.pem", "rb") as f:
        key = RSA.import_key(f.read())
        cipher = PKCS1_OAEP.new(key)
    raw = base64.b64decode(encrypted_base64)
    return cipher.decrypt(raw).decode()

def signup(encrypted_username, encrypted_password):
    try:
        print("(DEBUG) sign  up activated")
        username = decrypt_field(encrypted_username)
        password = decrypt_field(encrypted_password)

        print(f"(DEBUG) decryp username: {username} decryp pass: {password} ")


        # Step 4: Do the hashing + DB insert in a background thread
        def add_user():
            try:
                hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
                db.insert_user(username, hashed_password)
            except Exception as e:
                print(f"[ERROR] adding user failed")

        threading.Thread(target=add_user).start()
        return "OK"
    except sqlite3.IntegrityError:
        return "FAIL"
    except Exception as e:
        print("Signup error:", e)
        return "FAIL"
def login(username, entered_password):
    print("entered password =", entered_password)
    stored_hash = db.get_user_password(username)

    if stored_hash:
        print("stored hash =", stored_hash)
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode()  # 🔧 convert str to bytes

        if bcrypt.checkpw(entered_password.encode(), stored_hash):
            print("Login successful")
            return True
        else:
            print("Invalid password")
            return False
    else:
        print("User not found")
        return False

def recieve_data(sock):
    data = b""
    while True:
        part = sock.recv(1024)
        if not part:
            break
        data += part
        if b"!END" in data:
            break
    return data.decode().replace("!END", "")
def handle_client(client_socket):
    print("[DEBUG] handle_client started")
    try:
        raw_data = recieve_data(client_socket)
        print(f"[DEBUG] Full raw data: {raw_data}")

        if "|" in raw_data:
            parts = raw_data.strip().split("|")
            op = parts[0]
            args = parts[1:]
        else:
            op = raw_data.strip()
            args = []

        print(f"[DEBUG] Operation: {op}, Args: {args}")

        if op == "login":
            if len(args) == 2:
                encrypted_username = args[0]
                encrypted_password = args[1]

                try:
                    username = decrypt_field(encrypted_username)
                    password = decrypt_field(encrypted_password)
                except Exception as e:
                    print("[ERROR] Failed to decrypt login fields:", e)
                    client_socket.send(b"FAIL")
                    return

                if login(username, password):  # raw password passed here
                    balance = db.get_user_balance(username)
                    client_socket.send(f"OK|{balance}".encode())
                else:
                    client_socket.send(b"FAIL")
            else:
                client_socket.send(b"FAIL")

        elif op == "signup":
            if len(args) == 2:
                username = parts[1]
                password = parts[2]
                if signup(username,password):
                    client_socket.send(b"OK")
                else:
                    client_socket.send(b"FAIL")
            else:
                client_socket.send(b"FAIL")

        elif op == "add_money":
            if len(args) == 2:
                username = args[0]
                try:
                    amount = float(args[1])
                    new_balance = db.update_balance(username, amount)
                    client_socket.send(f"OK|{new_balance}".encode())
                except:
                    client_socket.send(b"FAIL")
            else:
                client_socket.send(b"FAIL")

        elif op == "get_restaurants":
            try:
                restaurants = db.get_all_restaurants()
                joined = "|".join(restaurants)
                client_socket.send(f"OK|{joined}".encode())
            except:
                client_socket.send(b"FAIL")


        elif op == "get_restaurant_category":

            if len(args) == 1:
                name = args[0]
                try:
                    conn = sqlite3.connect("hilleleats.db")
                    c = conn.cursor()
                    c.execute("SELECT category FROM restaurants WHERE name = ?", (name,))
                    result = c.fetchone()
                    if result:
                        client_socket.send(f"OK|{result[0]}".encode())
                    else:
                        client_socket.send(b"FAIL")
                    conn.close()
                except:
                    client_socket.send(b"FAIL")
            else:
                client_socket.send(b"FAIL")



        elif op == "get_menu":

            if len(args) == 1:

                rest_name = args[0]

                try:
                    meals = db.get_meals_for_restaurant(rest_name)
                    delivery_time = db.get_delivery_time(rest_name)
                    meal_data = "|".join([f"{name},{price}" for name, price in meals])
                    client_socket.send(f"OK|{delivery_time}|{meal_data}".encode())

                except:

                    client_socket.send(b"FAIL")

        elif op == "get_restaurant_delivery":
            if len(args) == 1:
                name = args[0]
                try:
                    delivery_time = db.get_delivery_time(name)
                    client_socket.send(f"OK|{delivery_time}".encode())
                except:
                    client_socket.send(b"FAIL")
            else:
                client_socket.send(b"FAIL")

        elif op == "toggle_fav_rest":
            if len(args) == 2:
                db.toggle_favorite_restaurant(args[0], args[1])
                client_socket.send(b"OK")

        elif op == "get_fav_rest":
            if len(args) == 1:
                favs = db.get_favorite_restaurants(args[0])
                joined = "|".join(favs)
                client_socket.send(f"OK|{joined}".encode())

        elif op == "toggle_fav_food":
            if len(args) == 3:
                db.toggle_favorite_food(args[0], args[1], args[2])
                client_socket.send(b"OK")

        elif op == "get_fav_food":
            if len(args) == 2:
                favs = db.get_favorite_foods(args[0], args[1])
                joined = "|".join(favs)
                client_socket.send(f"OK|{joined}".encode())

        elif op == "log_order":
            if len(args) == 2:
                db.add_order_history(args[0], args[1])
                client_socket.send(b"OK")

        elif op == "get_order_history":
            if len(args) == 1:
                records = db.get_order_history(args[0])
                joined = "|".join([f"{rest},{ts}" for rest, ts in records])
                client_socket.send(f"OK|{joined}".encode())



    except Exception as e:
        print("[ERROR]", str(e))
        client_socket.send(f"ERROR|{str(e)}!END".encode())
    finally:
        client_socket.close()


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("localhost", 12345))
    server.listen(5)
    print("Server listening on port 12345...")
    while True:
        client_socket, _ = server.accept()
        threading.Thread(target=handle_client, args=(client_socket,)).start()

if __name__ == "__main__":
    start_server()
