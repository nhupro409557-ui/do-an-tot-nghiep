ALTER TABLE store_info ADD COLUMN lat DOUBLE PRECISION;
ALTER TABLE store_info ADD COLUMN lng DOUBLE PRECISION;

-- Thiết lập tọa độ mặc định tại TP. Hồ Chí Minh cho bản ghi hiện tại
UPDATE store_info 
SET lat = 10.762622, 
    lng = 106.660172 
WHERE id = 'a53a99eb-047b-4ecf-a0ff-0f9c2d1bdfd9';
