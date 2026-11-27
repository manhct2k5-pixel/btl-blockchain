# Giới hạn ứng dụng

1. Kết quả là mô phỏng Cấp A theo giả định. Chưa hiệu chuẩn xác suất tấn công ngoài thực tế, chưa có risk score tổng hợp, dự báo hay giám sát Decentraland thời gian thực.
2. Explorer lịch sử chỉ đọc phiếu giữ lại và kết quả tái dựng đã chốt. Các cờ thiếu quy tắc production, quyền, DEFAULT, ngân sách, eligible và thực thi được bảo toàn. Ví không đồng nghĩa người đã xác minh; không nhận dạng attacker lịch sử.
3. QV là căn bậc hai theo ví với quy tắc nhị phân chung, không đại diện toàn bộ QV cổ điển. Capping là theo ví, không theo chủ thể. Chưa mô phỏng hệ thống định danh hoặc đánh giá triển khai PoH/SBT.
4. VE cần MANA/lịch sử khóa riêng, không được xếp vào đối chứng VP khi nguồn không tương thích. Các điều khiển cơ bản co giãn amount/remaining đồng nhất; chỉnh lịch khác cần JSON hợp lệ. Chưa có phản ứng nội sinh về quyết định khóa dựa trên thị trường.
5. Grant SPLIT là tiền đề ngoại sinh được kiểm tra, không bằng chứng proposer thật biết trước. Grant chỉ xác nhận khả thi của kế hoạch đã cấu hình; chưa có tác tử tối ưu kế hoạch từ nội dung thông tin riêng. Phân bổ tổng quát không nhắm proposal chưa triển khai, hiển thị NOT_READY.
6. HELD_LOAN chưa có hợp đồng nợ/lịch hoàn trả, hiển thị NOT_READY. FLASH chỉ kiểm tình huống số dư chốt không đổi đã đặc tả, không kết luận mọi đường vay tức thời đều bị ngăn.
7. Batch tối đa30world, lưới tối đa8giá trị, chạy tuần tự trên máy cục bộ. Không có hàng đợi nền, hủy tác vụ phân tán, stress test nhiều người dùng hoặc tự mở rộng Monte Carlo lớn.
8. So sánh nhiều cơ chế dùng world ghép cặp. Giao diện báo chênh lệch và bất đồng cặp; chưa bổ sung CI bootstrap mới cho mọi batch nhỏ. Type A giữ khoảng pointwise của bootstrap4.4V2, không dùng CI hẹp đã loại. Seed trùng có thể tái tạo world cũ; không gọi đó là mẫu độc lập mới.
9. Các family tổng hợp hiện phục vụ proposal Yes/No trên network khai báo của model. Không tự khái quát thành mọi loại proposal, mọi tài sản hoặc full DAO governance. Lớp hành vi/cơ chế cũ giữ phạm vi của chúng.
10. Thời gian thực thi đồng hồ có thể khác giữa hai lần; tái lập chỉ đòi cấu hình/đầu ra khoa học nhất quán, không timing giống byte. Quy tắc utility/TEST_COIN/VP/MANA giữ riêng; chi phí USD thực không biết.
11. Nhập JSON hỗ trợ từng kịch bản. Manifest xuất chứa toàn bộ request batch/lưới nhưng chưa có nút nhập nguyên manifest để chạy lại cả nhóm. Có thể tái tạo batch bằng seed/count/overrides hoặc nhập từng request.
12. Chưa có gói cài độc lập khỏi repository. Cần Python3.12 và dependencies đã ghi, cùng các module/dữ liệu cục bộ. Chưa có cơ chế phân quyền đa người dùng; mặc định chỉ lắng nghe127.0.0.1.

Đã kiểm AppTest và trình duyệt desktop/mobile. Đánh giá thiết kế bằng tác tử độc lập cùng nhà cung cấp đã PASS; không có đánh giá chéo nhà cung cấp vì môi trường chỉ có các mô hình cùng nhà cung cấp. Đánh giá giao diện không thay cho kiểm chứng service, bảo toàn nguồn hay hiệu lực khoa học.
