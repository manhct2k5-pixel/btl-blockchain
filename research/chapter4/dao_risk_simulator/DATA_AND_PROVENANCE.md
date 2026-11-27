# Nguồn và ranh giới bằng chứng

| Lớp | Nguồn cục bộ | Cách hiển thị |
|---|---|---|
| Quan sát lịch sử | data_enrichment/proposal_metadata.csv, votes_recovered.csv và cohort recent tương ứng | Metadata, phiếu được giữ, VP, trạng thái được quan sát; không gán vai trò attacker |
| Tính lại Baseline | baseline/BASELINE_VALIDATION.csv và các trường nguồn TW trong kết quả QV/Capping | Tally/outcome theo phiên bản quy tắc ứng viên và cờ thiếu bằng chứng |
| Phản thực tế cơ học | QV_RESULTS.csv, CAPPING_RESULTS.csv của4.2 | Trọng số/strict majority giả định trên phiếu quan sát; không phải lịch sử DAO đã áp dụng QV/cap |
| Tổng hợp giả định | main_generator, MC_MAIN_CONTRACT và overrides được người dùng khai báo | Thế giới mô phỏng Cấp A; không hiệu chuẩn xác suất thực tế |
| Tái trọng số đã kiểm toán |4.4 V2 BOOTSTRAP_PAIRED_INPUT và CROSSOVER_BOOTSTRAP_DRAWS | Type A, không nhận là vừa mô phỏng world mới |

Phạm vi chính lấy khóa từ toàn bộ QV HISTORICAL_B_BINDING: **1.023 đề xuất,63.662 phiếu,6.004 ví từng tham gia**. Chỉ **943 đề xuất** đủ điều kiện đối chứng QV/Capping,80 bị loại có lý do được giữ. Không dùng riêng tập C1.006 đã chọn theo độ khớp để thay B binding; không coi6.004 ví là toàn bộ quần thể eligible hoặc6.004 người.

historical_data nối1–1 theo snapshot_id, giữ toàn bộ181 cột gồm Baseline, QV, Capping và metadata. Giao diện chọn các cột dễ đọc và cung cấp đầy đủ bảng audit. historical_detail đọc phiếu đúng snapshot_id từ hai cohort, không nối chồng với bộ phiếu legacy để cộng đôi. Tổng VP đã gồm chiến lược/delegation trong phiếu được giữ; không thêm delegation hiện tại lần nữa.

Các cờ như production_deployment_verified, default_dependency_gap, budget_layer_unverified, rights/identity/eligible_universe và governance mismatch/exclusion được bảo toàn. official_status_observed không đồng nhất computed_governance_outcome. Quy tắc ứng viên và nguồn có thể chưa xác minh triển khai thực tế; ứng dụng không áp quy tắc đã biết ở kỳ khác để “điền” phần thiếu. Historical explorer không tự tái chạy một quy tắc hiện tại lên mọi năm.

`READING_INDEX.json` ghi byte/hash của các tệp nghiên cứu đã đọc; `PROTECTED_INPUTS.json` đóng băng **1.854 tệp cũ** trước lập trình. Hash được kiểm trước/sau từng phạm vi test và khi chốt giao. Không sửa tệp4.4 V2 để thêm ứng dụng vào manifest của nó. Toàn bộ file mới nằm trong dao_risk_simulator, không sao chép cả repository hay bộ177.729 phiếu làm dữ liệu mới.

`MODEL_MANIFEST.json` ghi code/hợp đồng thực dùng, bao gồm baseline/khởi tạo/hành vi/cơ chế/attack/generator/sensitivity. Kết quả4.5 có source contract, seed, input hash và evidence. Cùng seed/cấu hình tái tạo đầu ra mô hình; seed khác không được giả định tạo cơ chế ngẫu nhiên hành vi mới nếu module chỉ dùng seed cho sinh world. Không lấy outcome cuối để cấp niềm tin trước quyết định.

Không có dòng dữ liệu on-chain trực tiếp, ví kết nối, danh sách tấn công thực hay xác suất gian lận lịch sử. Trường actual_usd_cost và thực thi quản trị vẫn chưa biết. Grant SPLIT là quyền được cấp trong thế giới tổng hợp, không phục hồi sự thật lịch sử về proposer.
