# Phạm vi điều đã chứng minh và giới hạn phải công bố

## 1. Kết quả có thể khẳng định

- Hàm lợi ích, sổ ngân sách và chi phí ròng tạo một đặc tả nhất quán đơn vị, có phương án không thao túng và quy tắc tránh tính trùng.
- Trong trò chơi E song phương có menu hữu hạn và các giả định đã nêu, chọn phản ứng tối ưu mọi nhánh rồi chọn đề nghị tối ưu tạo SPNE thuần. Trò chơi hữu hạn nhiều người nhận có cân bằng hỗn hợp trong từng trò chơi con; không bảo đảm luôn thuần hoặc duy nhất.
- Số dư vay tạm đã hoàn trả không tạo VP mới nếu dữ liệu mà scoring đúng snapshot đọc không đổi và không còn quyền khác ảnh hưởng điểm.
- Kết quả 3.3 được tính nhất quán trên 1.023 B binding trước lọc độ khớp, giữ các trạng thái tối thiểu/infimum/cận trên và trường hợp không khả thi.
- 410 trường hợp S1 thiếu tổng VP đạt ngưỡng đều có S2 hữu hạn về toán học; 377 trường hợp có một phiếu nguyên vẹn có thể đổi outcome trong miền đã định nghĩa.

Các mệnh đề trên có điều kiện rõ, không phải kết luận cơ chế triển khai thực tế hoặc hành vi của ví.

## 2. Những điều chưa được chứng minh

| Vấn đề | Điều chưa thể kết luận | Lý do và đầu vào cần thêm |
| --- | --- | --- |
| Danh tính | Một ví là một tác tử độc lập hoặc các ví tạo thành liên minh | Chưa có ánh xạ cùng chủ, quyền điều khiển và tổ chức |
| Quần thể | Tỷ lệ tham gia của toàn bộ eligible hoặc tập tác tử biết trước | Chỉ có retained voters, thiếu eligible nonvoters và toàn bộ quyền tại snapshot |
| Động cơ | Ví lớn/phiếu quyết định là bên thao túng | Chưa có sở thích, utility, chuyển giao và phản thực tế hành vi |
| Ngân sách | Một tác tử đủ vốn hoặc tín dụng | Chưa có sổ nguồn lực và nghĩa vụ theo thời điểm |
| Hối lộ | Hợp đồng E thực tồn tại hoặc công khai đảm bảo trả | E là giả định; P/U có điều kiện chiến lược khác |
| Nash | Hành vi quan sát là cân bằng, epsilon>0 là Nash, mọi trò chơi nhiều người có nghiệm thuần | Kết quả lý thuyết chỉ trong tập chiến lược, thông tin và cam kết đã đặc tả |
| Scoring | Tổng phiếu đúng đồng nghĩa tái dựng đủ số dư/quyền | Tally và runtime scoring là hai lớp; chưa replay mọi state, network, dependency |
| Deployment | Commit gần ngày đóng là code production | Thiếu lịch sử triển khai; mọi kết quả giữ nhãn ứng viên |
| DEFAULT | 49 binding có hằng và nhánh lịch sử chắc chắn đúng | Thiếu chứng cứ định nghĩa tương ứng; nhánh master hiện tại không sửa được quá khứ |
| Flash loan | Mọi đường gián tiếp/mọi phiên bản an toàn, hoặc khoảng trống là exploit đã chứng minh | Thiếu mapping, quyền bền vững, kiểu snapshot, chain mapping và runtime |
| S1/S3 | Không khả thi nghĩa không thể bị mọi chiến lược tấn công | Chỉ một nguồn và một đích, không tối ưu chuyển phối hợp |
| S2 | Có thể huy động mọi ngưỡng hữu hạn | Chưa biết nguồn cung đủ điều kiện chưa dùng và khả năng kiểm soát |
| S3 | 273 cận trên là tối ưu hoặc có tỷ lệ xấp xỉ bảo đảm | Giới hạn tìm kiếm chưa chứng minh tốt nhất; số ví chứng nhân cũng không tối ưu số ví |
| Thực thi | Đổi tally chắc đổi quyết định, ngân sách hoặc lợi ích nhận được | Lớp thủ công/chi ngân sách/thực thi khác outcome |
| Kinh tế | VP là USD, grant là lợi ích riêng hoặc vốn vay là lợi nhuận | Chưa có hàm huy động hợp lệ, giá/liquidity/thu hồi và payoff |
| Hiện tại | Điểm tới hạn toàn Decentraland 2026 | 1.011 recent chưa có quy tắc tương ứng đủ điều kiện; mẫu chính lịch sử |
| Thống kê | Tương quan là nhân quả hoặc xác suất bị tấn công | Ví lặp, thành phần mẫu/quy tắc khác; không có thiết kế nhận diện |

## 3. Những số phải luôn đi cùng định nghĩa

1. 1.276/1.667 là độ khớp toàn B; 1.016/1.023 là B binding; 1.006 C đã chọn có điều kiện. Không dùng tỷ lệ nào làm xác suất thành công.
2. 84 DEFAULT trong B khác 49 trong B binding. 391 mismatch B khác bảy binding. 10 cờ ngân sách không bị bỏ khỏi mẫu.
3. 5.921 ví C khác 6.004 ví B binding. Không số nào là tổng thể đủ điều kiện.
4. 1.018 đề xuất có số hữu hạn trong ít nhất một kịch bản khác 2.233 dòng chứng nhân đã kiểm qua ba kịch bản.
5. V=0 làm tỷ số và tập trung không xác định; giá trị thiếu không được thay bằng 0.

## 4. Thông tin theo thời gian

Tally cuối, Gini/HHI/top-k, ngưỡng đảo outcome và nhãn cuối là kết quả sau đóng trong phân tích này. Không mặc định tác tử biết chúng trước lượt quyết định. Phiếu còn lưu chưa là toàn bộ lịch thay phiếu; dữ liệu tải năm 2026 không chứng minh thông tin được công khai năm 2021.

Giai đoạn development dùng cho hiệu chỉnh theo tiêu chí chốt trước. Bảng mô tả toàn bộ mẫu không phải bộ tham số fit có thể dùng mà không rò rỉ. validation/final_historical là các phần đối chiếu đã có và phải gọi final là hồi cứu khi thích hợp.

## 5. Câu giới hạn bắt buộc trong bản chính

Kết quả định lượng áp dụng có điều kiện trên mẫu B binding lịch sử, với quy tắc ứng viên và một số phụ thuộc chưa xác minh. Chưa xác định điểm tới hạn toàn hệ thống hiện tại, xác suất bị tấn công hoặc chi phí tiền tệ. Những phương án phản thực tế đạt outcome không chứng minh thao túng đã xảy ra hoặc đảo được thực thi.

Không xóa câu này khi rút gọn Chương 3. Chi tiết kỹ thuật có thể chuyển phụ lục, nhưng miền hành động, trạng thái cận, bất định deployment/DEFAULT và giới hạn năm 2026 phải còn ở bản chính.
