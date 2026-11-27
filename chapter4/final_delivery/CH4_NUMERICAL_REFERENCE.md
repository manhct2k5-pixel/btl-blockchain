# Số liệu chuẩn và nguồn

Nguồn ưu tiên là JSON/CSV đã chốt, được tổng hợp lại bằng numerical_audit.py. NUMERICAL_AUDIT.json ghi kết quả kiểm và hash nguồn. Ba CSV MC_NUMERICAL_RECONCILIATION, MC_FAMILY_COUNTS và MC_COST_RECONCILIATION giữ số liệu máy đọc được. Đợt này không chạy Monte Carlo hoặc tạo thí nghiệm mới.

| Nội dung | Giá trị chuẩn | Nguồn và mẫu số |
|---|---|---|
| Lịch sử B binding | 1.023 đề xuất, 63.662 phiếu, 6.004 ví | initialization/outputs/SUMMARY.json, nhóm counts |
| Baseline và nhãn | 1.023/1.023 trùng Baseline; 1.016/1.023 khớp nhãn; 7 mismatch, 49 DEFAULT, 10 cờ ngân sách | token_weighted/BASELINE_METRICS.csv và SUMMARY; các cờ có thể chồng nhau |
| Đối chứng trọng số | 943 được đánh giá, 80 chưa đánh giá | QV_RESULTS.csv: HISTORICAL_B_BINDING; QV/CAP status ASSESSED |
| Outcome chính sách chung | TW/QV/CAP chấp nhận 520/535/534, từ chối 423/408/409 | CAPPING_RESULTS.csv trên đúng 943 đề xuất |
| Đổi trọng số so TW chung | QV 37; CAP 40 | Không gọi 169/176 thay đổi so lịch sử là hiệu ứng trọng số thuần |
| MAIN | 1.000 world, 709 eligible, 388 attempted, 321 declined | MC_MAIN_RESULTS.csv theo từng cơ chế |
| Policy success MAIN | TW 17, QV 35, CAP 36 | Mẫu số eligible 709 hoặc attempted 388 phải nêu rõ |
| Attempted có baseline REJECTED | TW 155, QV 150, CAP 168 | Mẫu số của chỉ tiêu conditional flip |
| Attempted đã đạt mục tiêu ở baseline | TW 233, QV 238, CAP 220 | Không tính là thành công do can thiệp |
| VE 4.3 | 200 world, 128 eligible, 61 attempted, 6 success; 27 attempted có baseline REJECTED | MC_MAIN_RESULTS.csv, nhóm VE riêng |
| Eligible từng họ MAIN | SWITCH 177, BRIBE_E 95, MOBILIZE 180, SPLIT 257 | MC_FAMILY_COUNTS.csv, tổng 709 |
| Success SPLIT | TW/QV/CAP: 0/19/19 trên 257 eligible | Không dùng 282 world được sinh làm mẫu số |
| Success không SPLIT | TW/QV/CAP: 17/16/17 trên 452 eligible | Ba họ còn lại |
| SPLIT được sinh | 282 world, 257 eligible, 138 attempted | Các ô thông tin và số ví trong sensitivity |
| Budget 2× | 733 eligible, 401 attempted, 20/38/39 success | ATTACK_BUDGET_RESULTS.json khóa 2.0, CSV factor 2.0x; văn bản 745 sai |
| Cap 25k/50k/100k/200k | 75/59/36/22 success | Mỗi ô 709 eligible |
| Alias 1/2/4/8 | QV 0/10/19/29; CAP 0/18/19/19; TW đều 0 | Mỗi ô 257 eligible |
| Type B 4.4 | 56 ô, 27.034 dòng world–cấu hình | Tổng hợp lại khớp toàn bộ 56 khóa CSV gốc |
| VE thời hạn 4.4 | Mỗi ô f=0,25/0,5/1 có 7/128 success | Amount giữ nguyên |
| VE bổ sung riêng | 6 ô, 1.200 dòng; mỗi ô 128 eligible, 61 attempted, 7 success | Không nhập vào 56 ô cũ |
| Điểm giao QV–TW | 257/8845 ≈ 2,9056% | CROSSOVER_BOOTSTRAP_RESULTS.json, công thức 4.5 |
| Nghiệm bootstrap | 7.565 trong miền, 2.435 ngoài miền, 10.000 draw | 75,65% có nghiệm trong [0,1] |
| Percentile nghiệm trên trục thực | [−12,1456%; 15,3198%] | Không cắt để gọi CI vật lý |
| Percentile chỉ nghiệm hợp lệ | [0%; 15,9330%] | Có điều kiện, không phải CI 95% vô điều kiện |
| Seed | World 4302027; bootstrap 4.4 dùng 4302029 | Seed đăng ký 4302028 không thực đi vào generator |
| Kiểm chứng cuối | 505 bài/15 phạm vi; 24 lượt runtime/UI riêng | Không gọi 529 là số bài khác nhau |

## Đơn vị và làm tròn

Tỷ lệ tính từ tử/mẫu gốc rồi mới làm tròn. Chênh lệch hai tỷ lệ dùng điểm phần trăm, không nhầm phần trăm tăng tương đối. Mẫu số 0 làm tỷ lệ không xác định. Success của không hành động là null; policy_success=False trong tập eligible không đồng nghĩa attempted failure.

Tiền ròng trung bình trên success bằng 32/17≈1,88 TEST_COIN ở TW, 43/35≈1,23 ở QV và 44/36≈1,22 ở CAP. Các tập ca khác nhau, không phải chi phí tối ưu cho cùng proposal hoặc USD. Thời gian quyết định 1–3 giây là lịch mô phỏng, không phải blockchain hoặc CPU.

## Nguồn đầy đủ

Các thư mục nghiên cứu gốc giữ nguồn JSON/CSV và bảng world. Manifest ghi đường dẫn tương đối và SHA. Runtime ZIP không chứa mọi bảng nghiên cứu vì app không cần toàn bộ chúng để chạy. Bộ bàn giao nghiên cứu đầy đủ là repository cùng final_delivery; ZIP là gói ứng dụng tối thiểu, có nguồn cắt dữ liệu và kiểm chứng riêng.
