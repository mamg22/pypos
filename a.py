import sqlite3

db = sqlite3.connect("products.db")
cur = db.cursor()

for x in (
    (f"Fake prod {i}", f"fake prod {i}", 300, "VED", 500, "VED") for i in range(5000)
):
    cur.execute(
        """\
    INSERT INTO Products(name, name_simplified, purchase_value, purchase_currency, sell_value, sell_currency) VALUES
        (?, ?, ?, ?, ?, ?)
    """,
        x,
    )
    i = cur.lastrowid
    cur.execute("INSERT INTO Inventory VALUES (?, ?)", (i, 30))

db.commit()
