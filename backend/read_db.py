import psycopg2

def main():
    conn = psycopg2.connect("postgresql://postgres:anhnhu057@localhost:5432/postgres")
    cur = conn.cursor()
    cur.execute("SELECT id, name, images, image_url FROM products WHERE name LIKE '%iPhone%';")
    rows = cur.fetchall()
    for row in rows:
        print("Product ID:", row[0])
        print("Name:", row[1])
        print("Images:", row[2])
        print("Image URL:", row[3])
        print("-" * 40)
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
