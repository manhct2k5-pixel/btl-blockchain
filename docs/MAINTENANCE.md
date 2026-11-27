# Sắp xếp dự án và sửa lỗi

Kết quả cuối: **535 kiểm thử đạt** (505 kiểm thử mô hình/ứng dụng trước đây, 8 kiểm thử hành vi UI V2 và 22 kiểm thử bảo trì). Các ca trùng lặp đã được gộp; nhóm bảo trì được chạy lại sau khi gộp và cập nhật chứng nhận tổng hợp. Một kiểm tra bất biến service của đợt UI V2 cũ được tách khỏi gate hiện hành vì nhiệm vụ này sửa service; xem lý do trong `artifacts/maintenance/VERIFICATION.json`.

## Sắp xếp

Gom 41 mục nghiên cứu/bàn giao từ gốc vào `research/`; xác minh 2.119 mã băm ngay sau di chuyển. Bổ sung điểm chạy ứng dụng, CLI, bản đồ dự án và bộ kiểm chứng hiện hành. Không xóa tệp nguồn hoặc ZIP; cache được dọn bằng công cụ giới hạn phạm vi.

## Các lỗi đã sửa

1. JSON chứa `voters`/`principals` sai kiểu hoặc phần tử không phải object từng gây `AttributeError`/`TypeError`. Nay kiểm tra cấu trúc trước khi truy cập và trả lỗi đầu vào dễ hiểu; có kiểm thử UI nhập lại dữ liệu hợp lệ sau lỗi.
2. Truyền danh sách cơ chế rỗng từng bị coi như không truyền và âm thầm chạy mặc định. Nay chỉ `None` sử dụng mặc định; danh sách rỗng hoặc sai kiểu bị từ chối.
3. Giới hạn nhập 1 MB từng đếm ký tự, cho phép văn bản tiếng Việt vượt giới hạn byte. Nay đếm byte UTF-8 và chuẩn hóa lỗi JSON quá sâu thành lỗi xác thực.
4. Trạng thái xác minh từng chỉ xét `failures=0`. Nay cũng yêu cầu không lỗi, không bỏ qua, số kiểm thử dương, có thu thập kiểm thử và fingerprint đúng; hồ sơ hỏng không làm ứng dụng văng lỗi.

Tái hiện trước sửa: 8 lỗi kiểm thử trong 11 trường hợp ban đầu. Sau sửa, thêm các ca hồ sơ xác minh hỏng, UI phục hồi sau JSON lỗi, lệnh chạy ngoài cwd và ranh giới dọn cache. Kết quả cuối nằm trong `artifacts/maintenance/VERIFICATION.json`.

## Chạy lại

Từ gốc mới, dùng `python project.py test`. Các runner cũ có thể ghi đè kết quả nghiên cứu nên không chạy tự động trong công cụ bảo trì. Bộ kiểm chứng hiện hành chỉ gọi test và viết chứng nhận/log ở vị trí được chỉ định.
