# Ghi chú xác thực frontend

## Cookie refresh trên Vercel

- Frontend Vercel dùng `API_BASE_URL=/api` để các yêu cầu xác thực đi cùng origin.
- `frontend/vercel.json` chuyển tiếp `/api/*` đến backend production; refresh cookie vì vậy được lưu như cookie first-party.
- `/uploads/*` cũng được chuyển tiếp để các URL media cũ dạng localhost tiếp tục hiển thị sau khi API chuyển sang cùng origin.
- Localhost và các hosting không thuộc Vercel vẫn dùng `VITE_API_BASE_URL` như trước.
