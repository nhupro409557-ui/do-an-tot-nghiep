# AGENTS.md

## CodeGraph

Project nay da duoc khoi tao CodeGraph trong thu muc `.codegraph/`.

Dung CodeGraph cho cau hoi cau truc code:

- Tim symbol, function, class: `codegraph_search`
- Xem ngu canh mot tinh nang: `codegraph_context`
- Xem source nhieu symbol lien quan: `codegraph_explore`
- Xem file tree theo index: `codegraph_files`
- Xem caller/callee/impact: `codegraph_callers`, `codegraph_callees`, `codegraph_impact`

Khi can doc text thuong, log, noi dung hien thi UI, van dung `rg`/doc file truc tiep.

Neu can index lai, tranh de CodeGraph quet cac thu muc sinh tu dong nhu:

- `backend/.venv`
- `backend/venv`
- `**/__pycache__`
- `.codegraph`
- `*.log`

## Maintenance Notes

- Truoc khi sua product/category/inventory/service, doc cac file:
  - `backend/PRODUCT_MANAGEMENT_NOTES.md`
  - `backend/CATEGORY_MANAGEMENT_NOTES.md`
  - `backend/INVENTORY_MANAGEMENT_NOTES.md`
- Moi lan sua logic quan trong, cap nhat file notes tuong ung de lan sau de tiep tuc.
