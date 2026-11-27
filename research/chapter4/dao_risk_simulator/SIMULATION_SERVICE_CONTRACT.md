# Hợp đồng dịch vụ mô phỏng

## Request một world

`schema=dao-risk-request-v1`, với đúng các trường: config, information_condition, grant, block_rule, allocation_strategy, source. `config` theo schema4.3-attack-v1 của parse_config, gồm proposal, voters, principals, attacker, attack, mechanism, cap_vp, seed và ve. `source` ghi template, master seed, replicate, generator version/contract, overrides và nhãn giả định. Source của JSON nhập là khai báo đi kèm; đầu vào thực thi có hash riêng, không được coi khai báo đó là chứng cứ lịch sử đã xác minh.

`build_scenario` nạp hợp đồng4.3 và chỉ điều kiện hóa family theo mẫu được chọn. Không lọc bỏ world vì không thuận lợi/không đủ điều kiện. Batch dùng replicate0..n−1. Mỗi world được sinh thật; việc dùng lại seed có thể tái tạo world đã xuất hiện ở4.3, không tự tạo tính độc lập thống kê với thí nghiệm cũ.

Tham số số cần hữu hạn và không âm; VP tổng, cap, hệ số MANA và tỷ lệ khóa phải dương. Tỷ lệ khóa≤1. Các seed/timestamp/replicate cần số nguyên, không nhận bool như số. Request nhập≤1MB,≤100 ví/chủ thể; các phần tử JSON quá lớn/sâu bị từ chối. Đầu vào sai schema hoặc ngoài miền trả ValueError, không dựng kết quả dự phòng.

Các hàm chính:

| Hàm | Kết quả/điều kiện |
|---|---|
| build_scenario(template_id,seed,replicate,overrides) | Request đầy đủ, kiểm tra qua parse_config và policy |
| import_scenario(text) | Kiểm tra schema, duplicate key và số không hữu hạn; không thực thi |
| run_scenario(request,mechanisms) | Gọi model một lần/cơ chế, trả bundle |
| run_batch(template_id,seed,count,overrides,mechanisms,progress) |1–30 world, phản hồi tiến trình thật, giữ vector cơ chế theo world |
| run_sensitivity(request,parameter,values) |2–8 giá trị khác nhau; chạy lại từng ô; không gộp các ô thành một xác suất |
| type_a(p) | Hỗn hợp tỷ lệ từ vector4.4 V2; khoảng chênh lệch pointwise từ10.000 bootstrap draw cũ; không chạy world mới |
| export_bundle(bundle) | Bytes JSON/CSV/Markdown/SVG, không ghi vào thư mục nghiên cứu cũ |

## Quyền SPLIT

Nhãn informed không tự cấp quyền. Chỉ tạo grant khi người dùng đánh dấu cấp quyền ngoại sinh; đối tượng được truyền vào validator4.4 V2. Validator ràng buộc principal/role/role_bindings, issuer/source/scope, content/hash và thứ tự known≤published<decision≤allocation<snapshot<created<start. Grant là giả định tổng hợp, identity_verified=False; không là chứng cứ proposer thực hay tác tử tối ưu kế hoạch từ nội dung thông tin riêng.

UNINFORMED với kế hoạch cần biết proposal trước không đủ điều kiện. Grant còn tồn tại trong cấu hình UNINFORMED tạo xung đột và NOT_READY, không âm thầm sửa quyền. BLOCKED cần đối tượng quy tắc cấm đúng scope/principal/thời gian. Grant chỉ áp dụng nhánh informed và block_rule chỉ áp dụng nhánh BLOCKED; có thể khai báo cả hai làm đầu vào khảo sát điều kiện, không có nghĩa quy tắc cấm toàn cục được áp dụng trong mọi nhánh. GENERAL_PREALLOCATION trả NOT_READY vì chưa triển khai.

## So sánh và chuẩn hóa

MAIN cho TW/QV/CAP trên cùng bản sao cấu hình, khác mechanism. VE bắt buộc danh sách chỉ gồm VE, có MANA/lịch sử khóa riêng. Không chuyển VP lịch sử thành MANA thiếu. Sự kiện khóa tương lai được đưa vào ledger đúng phiên bản, snapshot không đọc tương lai. Đổi duration trong sensitivity giữ amount; đổi amount giữ duration. Hai tỷ lệ trong build cùng dùng quy tắc phần thời gian tối đa còn lại khả thi.

| Trạng thái cuối | Quy ước |
|---|---|
| NOT_READY | eligible=null; không đủ đặc tả, success/policy_success=null |
| INFEASIBLE | eligible=False; không thực hiện, success/policy_success=null |
| DECLINED | eligible=True; attempted=False; success=null; policy_success=False |
| ATTEMPTED_SUCCESS/FAILURE | eligible=True; attempted=True; success True/False |
| OUTCOME_UNKNOWN | attempted=True nhưng success=null; tỷ lệ liên quan giữ null |

Bước khả thi có validation_state=ELIGIBLE trước phân loại kết quả. Tỷ lệ policy success dùng eligible; tỷ lệ trên attempted dùng attempted. Mẫu số0 hoặc có attempted outcome chưa biết thì không công bố tỷ lệ bằng0. Các paired comparison chỉ dùng world cùng đủ điều kiện/cùng biết policy success, báo số cặp và hai loại bất đồng, không coi cơ chế là các mẫu độc lập.

Mỗi kết quả có module/version, nguồn/hợp đồng, seed, hash đầu vào, nhãn giả định, state/reason, outcomes hai nhánh, điểm/đơn vị, resources/responses/views và thời gian. Sổ tiền kiểm từng principal; alias không có ngân sách riêng. Chi phí TEST_COIN, VP, MANA và utility không bị cộng lẫn. `elapsed_seconds` đo thời gian đồng hồ phần mềm bằng perf_counter, khác thời gian sự kiện của hành động.

## Xuất và tái lập

scenario.json chứa một request đầy đủ. CSV từng lượt giữ dict/list ở dạng JSON, null thành ô rỗng; không đổi thành False/0. summary.csv dùng đúng mẫu số. manifest.json có code hashes/fingerprint, source contract, seeds, input hash, thời gian và danh sách request của batch/lưới. report.md giữ giới hạn; chart.svg vẽ đúng tỷ lệ đã tính, không tạo outcome.

Với batch/lưới, scenario.json là cấu hình nguồn/một lượt; toàn bộ request nằm trong manifest. Có thể lấy từng request từ manifest để nhập lại chạy một world. Tái tạo cả batch cần dùng seed/count/overrides ở giao diện hoặc API run_batch; chưa có nút nhập nguyên manifest để chạy lại cả batch. Không khẳng định thời gian thực thi hay file manifest chứa timing sẽ giống byte giữa hai lần; các đầu ra khoa học có tính xác định.
