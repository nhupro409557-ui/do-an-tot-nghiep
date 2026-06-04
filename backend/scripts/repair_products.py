import asyncio
import asyncpg
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

RAM_MAPPING = {
    # Laptops
    'ACAL15': lambda storage: '16GB',
    'ACGA7': lambda storage: '16GB',
    'ACNPP15': lambda storage: '16GB',
    'ASGV16': lambda storage: '16GB',
    'HPOB5AI16': lambda storage: '16GB',
    'HPOBXF14': lambda storage: '16GB',
    'LNLOQ15': lambda storage: '16GB',
    'MSIP13AIU': lambda storage: '32GB',
    'MBAIRM3': lambda storage: '16GB' if '512' in storage else '8GB',
    'MBNEOA18P': lambda storage: '8GB',
    # Tablets
    'HONORPAD10': lambda storage: '8GB',
    'MATEPAD12X': lambda storage: '12GB' if '512' in storage else '8GB',
    'MATEPADSE': lambda storage: '4GB',
    'IPADA16': lambda storage: '6GB',
    'IPADM4': lambda storage: '8GB',
    'YOGATAB': lambda storage: '8GB' if '256' in storage else '4GB',
    'TABS11': lambda storage: '8GB',
    'MIPADMINI': lambda storage: '6GB' if '256' in storage else '4GB',
    'POCOPADM1': lambda storage: '6GB' if '128' in storage else '4GB',
    'POCOPADX1': lambda storage: '8GB',
}

async def main():
    conn = await asyncpg.connect("postgresql://postgres:anhnhu057@localhost:5432/postgres")
    
    print("Starting Product Configuration Repair...")
    print("=" * 60)
    
    for sku, get_ram in RAM_MAPPING.items():
        # 1. Fetch the product ID, name, colors, and options
        p = await conn.fetchrow("SELECT id, name, colors FROM products WHERE sku = $1 AND deleted_at IS NULL;", sku)
        if not p:
            print(f"Warning: Product SKU {sku} not found or deleted!")
            continue
            
        p_id = p['id']
        name = p['name']
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
            # Fallback if colors is empty
            color_names = ["Mặc định"]
            
        # 2. Fetch all active variants for this product
        variants = await conn.fetch("""
            SELECT id, sku, color_name, storage 
            FROM product_variants 
            WHERE product_id = $1 AND deleted_at IS NULL;
        """, p_id)
        
        if not variants:
            print(f"Product: {name} ({sku}) has no active variants. Skipping options/variants update.")
            continue
            
        print(f"\nProcessing Product: {name} ({sku}) | ID: {p_id}")
        
        unique_colors = sorted(list(set([v['color_name'] for v in variants if v['color_name']])))
        if not unique_colors:
            unique_colors = color_names
            
        unique_storages = []
        # Keep the original order of storages as they appear in the variants
        for v in variants:
            storage = v['storage']
            if storage and storage not in unique_storages:
                unique_storages.append(storage)
                
        if not unique_storages:
            unique_storages = ["Default"]
            
        # Calculate RAM values for all active variants to build the options list
        unique_rams = []
        for v in variants:
            storage = v['storage'] or ""
            ram_val = get_ram(storage)
            if ram_val not in unique_rams:
                unique_rams.append(ram_val)
                
        # 3. Build options structure
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
        
        # 4. Update variants
        for v in variants:
            v_id = v['id']
            v_sku = v['sku']
            color = v['color_name'] or unique_colors[0]
            storage = v['storage'] or unique_storages[0]
            ram_val = get_ram(storage)
            
            new_specs = {
                "storage": storage,
                "ram": ram_val
            }
            
            new_attributes = {
                "Màu sắc": color,
                "Dung lượng": storage,
                "RAM": ram_val
            }
            
            await conn.execute("""
                UPDATE product_variants
                SET ram = $1,
                    specs = $2,
                    attributes = $3,
                    updated_at = NOW()
                WHERE id = $4;
            """, ram_val, json.dumps(new_specs), json.dumps(new_attributes), v_id)
            print(f"    * Updated Variant SKU: {v_sku} | RAM: {ram_val} | Storage: {storage} | Color: {color}")
            
    print("\n" + "=" * 60)
    print("Configuration Repair Completed Successfully!")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
