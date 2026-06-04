import asyncio
import asyncpg
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

def parse_ram_clean(ram_str):
    if not ram_str:
        return []
    rams = re.findall(r'(\d+)\s*GB', ram_str, re.IGNORECASE)
    return [f"{r}GB" for r in rams]

def parse_storage_clean(storage_str):
    if not storage_str:
        return []
    storages = re.findall(r'(\d+)\s*(GB|TB)', storage_str, re.IGNORECASE)
    return [f"{s[0]}{s[1].upper()}" for s in storages]

def get_ram_for_variant(product_sku, storage_val, specs_rams):
    if len(specs_rams) == 0:
        return "8GB"
    if len(specs_rams) == 1:
        return specs_rams[0]
    
    # Custom rules per product SKU:
    if product_sku == 'S26U':
        if '1TB' in storage_val:
            return '16GB'
        else:
            return '12GB'
            
    if product_sku == 'A57-5G':
        if '256' in storage_val:
            return '12GB'
        else:
            return '8GB'
            
    if product_sku == 'A17-5G':
        if '256' in storage_val:
            return '8GB'
        else:
            return '6GB'
            
    # Default heuristic
    if '1TB' in storage_val or '1T' in storage_val:
        return specs_rams[-1]
    if '512' in storage_val:
        return specs_rams[-1]
    if '256' in storage_val:
        return specs_rams[0]
    if '128' in storage_val:
        return specs_rams[0]
        
    return specs_rams[0]

async def main():
    conn = await asyncpg.connect("postgresql://postgres:anhnhu057@localhost:5432/postgres")
    
    # Fetch all active smartphones
    products = await conn.fetch("""
        SELECT p.id, p.name, p.sku, p.options, p.colors, p.specifications
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE p.deleted_at IS NULL AND (c.code LIKE 'điện-thoại%' OR c.code LIKE 'phone%' OR p.category = 'SMARTPHONES')
        ORDER BY p.name;
    """)
    
    print(f"Starting Smartphones Configuration Repair. Total: {len(products)}")
    print("=" * 80)
    
    for p in products:
        p_id = p['id']
        name = p['name']
        sku = p['sku']
        specs = p['specifications']
        colors_json = p['colors']
        
        # Parse colors to get names
        colors_list = []
        if isinstance(colors_json, str):
            try:
                colors_list = json.loads(colors_json)
            except Exception:
                pass
        elif isinstance(colors_json, list):
            colors_list = colors_json
            
        color_names = [c['name'] for c in colors_list if 'name' in c]
        if not color_names:
            color_names = ["Mặc định"]
            
        # Parse specifications
        if isinstance(specs, str):
            try:
                specs = json.loads(specs)
            except Exception:
                specs = {}
        elif not specs:
            specs = {}
            
        specs_ram_str = specs.get('ram', '') or ''
        specs_storage_str = specs.get('storage', '') or ''
        
        specs_rams = parse_ram_clean(specs_ram_str)
        specs_storages = parse_storage_clean(specs_storage_str)
        
        # Fetch active variants
        variants = await conn.fetch("""
            SELECT id, sku, color_name, storage, ram, price
            FROM product_variants
            WHERE product_id = $1 AND deleted_at IS NULL
            ORDER BY sku;
        """, p_id)
        
        if not variants:
            continue
            
        print(f"\nProcessing Product: {name} ({sku})")
        
        unique_colors = sorted(list(set([v['color_name'] for v in variants if v['color_name']])))
        if not unique_colors:
            unique_colors = color_names
            
        unique_storages = []
        unique_rams = []
        
        for v in variants:
            v_id = v['id']
            v_sku = v['sku']
            v_storage = v['storage'] or ""
            color = v['color_name'] or unique_colors[0]
            
            # Check combined format
            combined_match = re.search(r'(?:RAM\s*)?(\d+)\s*GB\s*-\s*(\d+)\s*(GB|TB)', v_storage, re.IGNORECASE)
            
            ram_val = None
            storage_val = None
            
            if combined_match:
                ram_val = f"{combined_match.group(1)}GB"
                storage_val = f"{combined_match.group(2)}{combined_match.group(3).upper()}"
            else:
                # Clean storage
                storage_match = re.search(r'(\d+)\s*(GB|TB)', v_storage, re.IGNORECASE)
                if storage_match:
                    storage_val = f"{storage_match.group(1)}{storage_match.group(2).upper()}"
                else:
                    storage_val = v_storage
                
                ram_val = get_ram_for_variant(sku, storage_val, specs_rams)
                
            if storage_val not in unique_storages:
                unique_storages.append(storage_val)
            if ram_val not in unique_rams:
                unique_rams.append(ram_val)
                
            new_specs = {
                "storage": storage_val,
                "ram": ram_val
            }
            
            new_attributes = {
                "Màu sắc": color,
                "Dung lượng": storage_val,
                "RAM": ram_val
            }
            
            # Update variant
            await conn.execute("""
                UPDATE product_variants
                SET storage = $1,
                    ram = $2,
                    specs = $3,
                    attributes = $4,
                    updated_at = NOW()
                WHERE id = $5;
            """, storage_val, ram_val, json.dumps(new_specs), json.dumps(new_attributes), v_id)
            print(f"  * Updated Variant SKU: {v_sku} | Storage: {storage_val} | RAM: {ram_val} | Color: {color}")
            
        # Build options structure
        new_options = [
            {
                "name": "Màu sắc",
                "values": unique_colors
            },
            {
                "name": "Dung lượng",
                "values": unique_storages
            },
            {
                "name": "RAM",
                "values": unique_rams
            }
        ]
        
        await conn.execute("""
            UPDATE products
            SET options = $1, updated_at = NOW()
            WHERE id = $2;
        """, json.dumps(new_options), p_id)
        print(f"  - Updated product options: {json.dumps(new_options, ensure_ascii=False)}")
        
    print("\n" + "=" * 80)
    print("Smartphones Configuration Repair Completed Successfully!")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
