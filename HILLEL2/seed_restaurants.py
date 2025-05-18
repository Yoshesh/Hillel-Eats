from database import Database

db = Database()

restaurants = {
    "Big Bite Grill": ("Burgers", 20, [("Double Cheeseburger", 12.99), ("Fries", 3.99), ("Cola", 2.49)]),
    "Burger Blast": ("Burgers", 15, [("BBQ Burger", 11.49), ("Onion Rings", 4.25), ("Milkshake", 3.75)]),
    "Meaty Madness": ("Burgers", 25, [("Triple Patty", 14.99), ("Sweet Potato Fries", 4.50), ("Lemonade", 2.99)]),

    "Slice Heaven": ("Pizza", 18, [("Pepperoni Pizza", 13.50), ("Garlic Knots", 3.95), ("Soda", 1.99)]),
    "Cheezy Bros": ("Pizza", 22, [("Cheese Pizza", 11.00), ("Caesar Salad", 5.50), ("Iced Tea", 2.79)]),
    "Woodfire Pizza Co.": ("Pizza", 30, [("Margherita", 12.25), ("Breadsticks", 4.00), ("Root Beer", 2.25)]),

    "Tokyo Bites": ("Sushi", 12, [("Salmon Roll", 10.99), ("Miso Soup", 2.99), ("Green Tea", 1.99)]),
    "Sakura Sushi": ("Sushi", 14, [("California Roll", 9.50), ("Edamame", 3.25), ("Sake", 4.99)]),
    "Roll & Go": ("Sushi", 10, [("Tempura Roll", 10.25), ("Seaweed Salad", 4.00), ("Water", 1.00)])
}

for rest_name, (category, time, meals) in restaurants.items():
    db.insert_restaurant(rest_name, category, time)
    for meal_name, price in meals:
        db.insert_meal(rest_name, meal_name, price)

print("✅ Pre-made restaurants and menus added.")
