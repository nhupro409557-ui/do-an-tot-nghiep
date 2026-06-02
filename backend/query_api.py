import urllib.request
import json

def main():
    try:
        url = "http://localhost:8000/api/v1/catalog/products"
        response = urllib.request.urlopen(url, timeout=2)
        data = json.loads(response.read().decode('utf-8'))
        for p in data:
            if "iphone" in p.get("name", "").lower() or "du" in p.get("name", "").lower():
                print("ID:", p.get("id"))
                print("Name:", p.get("name"))
                print("Images:", p.get("images"))
                print("ImageUrl:", p.get("imageUrl"))
                print("-" * 50)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()
