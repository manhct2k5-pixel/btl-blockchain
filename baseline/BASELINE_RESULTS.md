# Kết quả xây dựng và kiểm chứng Baseline

Phạm vi: kiểm phiếu xác định từ phiếu quan sát và quy tắc Governance ứng viên; chuẩn bị dữ liệu ABM. Chạy hoàn toàn offline. Không có tấn công, phòng thủ, Monte Carlo hoặc mô hình hành vi được fit.

## 1. Kết quả chính

| Phép kiểm tra / phạm vi | Kết quả |
|---|---:|
| Đề xuất / phiếu đã đọc và xử lý đầy đủ | 2.852 / 177.729 |
| Tổng VP, số phiếu và từng lựa chọn khớp Snapshot | 2.852/2.852 |
| Mức A với trạng thái final | 2.850; 2 đề xuất còn 18 phiếu pending |
| B: đủ điều kiện trước khi nhìn kết quả khớp | 1.667 đề xuất, 101.268 phiếu |
| B: khớp Governance | **1.276/1.667 = 76,54%** |
| B: không khớp Governance | 391 |
| B riêng các loại binding, trước lọc outcome | 1.016/1.023 = 99,32% |
| C: mẫu binding đã chọn có điều kiện | 1.006; 1.006 khớp, không dùng làm độ chính xác tổng thể |

Độ khớp headline là **76,54% trên toàn bộ B**, không phải 100% trên C. Mẫu C đã được chọn theo outcome từ bước enrichment; báo cáo 100% trên C như một kiểm định độc lập sẽ gây thiên lệch lựa chọn.

Đã xử lý 1.841 đề xuất/104.878 phiếu lịch sử và 1.011 đề xuất/72.851 phiếu recent riêng. Trong phần lịch sử, 152 đề xuất thiếu metadata Governance lưu trữ, 20 chưa đóng tại ảnh lưu cũ, 2 còn VP pending; còn 1.667 trong B. Không áp mã 2023 cho bộ 2023–2026. B có đủ nhãn đối chiếu ở mọi trường hợp; reference coverage là 100%. Nếu có nhãn thiếu trong đợt sau, mẫu số chính vẫn là toàn B, đồng thời báo coverage.

## 2. Tính độc lập của phép kiểm phiếu

Chương trình không nhập hàm enrichment. Mỗi phiếu được liên kết qua Snapshot ID, kiểm vote ID/cặp ví–đề xuất duy nhất, kiểm choice index theo từng danh sách choices, VP không âm/hữu hạn, tổng component, số strategy và cửa sổ thời gian. VP được cộng **từ từng phiếu** bằng Decimal; không dùng scores_json hoặc cột tổng đã tính sẵn làm đầu vào tally. VP ủy quyền chỉ là thành phần trong Total VP, không được cộng lần hai.

Chỉ sau khi tính độc lập mới so số phiếu, tổng VP và từng option với Snapshot. Sai số option tuyệt đối lớn nhất: **2.53831937E-8 VP**. Dung sai tham chiếu: atol=1e-6, rtol=1e-9; so thắng/thua, hòa và ngưỡng dùng bất đẳng thức chính xác trên VP quan sát, không thêm epsilon để thay kết quả.

Các bộ Yes/No, Accept/Reject, For/Against, invalid, abstain và cách xử lý hòa thay đổi theo source/version. Ngưỡng dùng đại lượng trong mã nguồn, không mặc định là tổng VP tham gia. Loại grant/poll/poi không tự áp một ngưỡng toàn cục; lấy required_to_pass có nguồn của proposal.

Hai đề xuất lịch sử trùng nhãn, trước đây enrichment chưa tính outcome, nay được xử lý theo phép ánh xạ literal của mã nguồn: cộng nhãn ở bản cũ hoặc lấy index đầu ở getVotingResults. Tầng Snapshot vẫn giữ các choice index riêng. Không sửa choices hoặc lấy nhãn chính thức để quyết định phép ánh xạ.

Một proposal recent có timestamp block sau created 3 giây; giữ nguyên cờ chưa xác minh. Điều này không thay phép cộng VP quan sát ở A, nhưng không được coi là chốt VP hợp lệ cho replay Governance. Tally không đồng nghĩa đã kiểm chứng lại số dư hợp đồng, trạng thái Polygon hoặc mọi phiên bản strategy.

## 3. Kiểm chứng quy tắc và giới hạn còn lại

- Đã đối chiếu bản chuyển Python với thực thi hàm TypeScript gốc đã lưu: **1.667/1.667 đề xuất B khớp**.
- Kiểm thử vi sai ca biên của cả 20 phiên bản: **380/380 khớp**.
- Các lời gọi cơ sở dữ liệu/Snapshot trong oracle được thay bằng stub in-memory, nhận **tổng đã tính từ phiếu**, không nhận scores công bố hay nhãn Governance. Mã nguồn được kiểm checksum; không gọi mạng.
- Có **84 đề xuất B** dùng phiên bản nhập DEFAULT_CHOICES mà gói offline thiếu file định nghĩa. Giữ ứng viên [yes,no,abstain] như hồ sơ trước và cờ thiếu chứng cứ. Parity dùng cùng ứng viên, nên **không xác nhận được hằng bị thiếu**.
- Bỏ toàn bộ các phiên bản thiếu định nghĩa DEFAULT khỏi B: **1.221/1.583 = 77,13%**. Đây là phân tích phạm vi bằng chứng, không phải cách sửa bộ lọc để tối đa tỷ lệ khớp. Chưa chứng nhận deployment production cho tập nào.
- Việc sửa 9 khác biệt ban đầu ở ca biên trước 23/05/2021 dựa trên lỗi khóa số/khóa nhãn trong source gốc; không có proposal B nào dùng ba commit đó. Xem FORMULA_REVIEW_LOG.md. Không điều chỉnh công thức theo official label.

## 4. Những trường hợp không khớp

Tổng 391 sai lệch Governance đều có tally Snapshot khớp. Không được đồng nhất chúng với lỗi cộng VP.

| Nhóm bằng chứng | Số đề xuất B không khớp | Kết luận được phép |
|---|---:|---|
| Có passed_by/rejected_by trong API hiện tại | 382 | Có dấu vết lớp quản trị ngoài tally; chưa đủ chứng minh nguyên nhân và thời điểm điều chỉnh ở ảnh cũ |
| Không có những trường quản trị trên | 9 | Chưa đủ bằng chứng; cần lịch sử deployment, phiên bản cấu hình và nhật ký quyết định |
| Lỗi chuyển nghĩa còn lại được oracle phát hiện | 0 | Không có trên tập đã kiểm; không mở rộng kết luận này thành xác nhận production |

Phần lớn chênh nằm ở poll nhiều lựa chọn: hàm biểu quyết có thể trả FINISHED, trong khi nhãn quản trị là passed/rejected/enacted. Có 10 grant trong B đi qua nhánh chấp nhận nhưng còn phụ thuộc ngân sách; **vẫn nằm trong mẫu số B**, không được loại vì khó giải thích. Không dùng trạng thái tài trợ hay receipt để đổi kết quả biểu quyết.

| Loại | Đề xuất B | Khớp | Không khớp | Tỷ lệ |
|---|---|---|---|---|
| ban_name | 62 | 62 | 0 | 100,00% |
| catalyst | 2 | 2 | 0 | 100,00% |
| draft | 46 | 45 | 1 | 97,83% |
| governance | 44 | 44 | 0 | 100,00% |
| grant | 451 | 445 | 6 | 98,67% |
| linked_wearables | 73 | 72 | 1 | 98,63% |
| poi | 391 | 391 | 0 | 100,00% |
| poll | 598 | 215 | 383 | 35,95% |

Ma trận outcome (passed/enacted chỉ quy về ACCEPTED khi đối chiếu kết quả biểu quyết, không xác nhận thực thi):

| Nhãn quan sát quy về outcome | Outcome từ phiếu | Đề xuất |
|---|---|---|
| ACCEPTED | ACCEPTED | 477 |
| ACCEPTED | FINISHED | 177 |
| FINISHED | FINISHED | 2 |
| REJECTED | ACCEPTED | 2 |
| REJECTED | FINISHED | 212 |
| REJECTED | REJECTED | 797 |

Chín trường hợp chưa có bằng chứng trường điều chỉnh thủ công:

| Snapshot ID | Loại | Tính từ phiếu | Trạng thái quan sát |
|---|---|---|---|
| 0x0a581f2f7ea548cc89c88b4fee8c592ef1612532085d898eb8f1a82d20e02c46 | grant | FINISHED | enacted |
| 0x27e63750163862670336fd6d39478c16a9cb93f4c5d5d56f140dbbb5cca7522d | grant | FINISHED | rejected |
| 0x68586d05532301ce896f26a3fc782a7fc00489afefe2eef844e3400e0eff0f47 | draft | FINISHED | passed |
| 0x84e766eda6d1848e29ac6fda1929b7275446143b63c04684e307eeb6a84dd132 | grant | FINISHED | rejected |
| 0xc6247d22f266f76ea7842117fb2fe6b5c027a1582bc211710908141a5ffc51b5 | grant | FINISHED | rejected |
| QmPSxiVjBuhQq1dgjRwGEeTDhTjgzR4nHtL8BTd5W3TuXa | grant | ACCEPTED | rejected |
| QmT9WrEJh3YCDqBa9mxgZxvzP5sKo1HdZHpZ7NToCvW2Nw | poll | FINISHED | enacted |
| Qmc6fwrpgiMTP8CjSaugqFsa6gXYC7cJKquKYnihKQW9AM | poll | FINISHED | enacted |
| QmfEL7SCah8uB2x16gdvbTBraCk7X1vYHPCuf2KDkkptWV | grant | ACCEPTED | rejected |

BASELINE_MISMATCHES.csv chứa cả sai lệch outcome lẫn sự kiện thiếu bằng chứng/phạm vi. Nhiều dòng có thể thuộc cùng proposal. Muốn lấy đúng 391 sai lệch outcome, lọc issue_code=GOVERNANCE_OUTCOME_DIFF; không dùng tổng số dòng của file.

## 5. Kiểm chứng theo thời gian

Mốc thời gian đã chốt trong BASELINE_DESIGN.md: development trước 01/01/2022; validation là 2022; final_historical từ 01/01/2023 của những proposal đã đóng trong ảnh lưu cũ. Theo **thời điểm đóng UTC**:

| Giai đoạn theo thời điểm đóng UTC | Đề xuất B | Khớp | Không khớp | Tỷ lệ trước lọc kết quả |
|---|---|---|---|---|
| development | 487 | 336 | 151 | 68,99% |
| final_historical | 212 | 144 | 68 | 67,92% |
| recent_tally_only | 0 | 0 | 0 | Không áp rule lịch sử |
| validation | 968 | 796 | 172 | 82,23% |

Đây là kiểm chứng hồi cứu của quy tắc xác định, không phải dự báo học máy. Dữ liệu đã từng được khảo sát trước đó, nên không gọi final là tập hoàn toàn chưa từng nhìn. Không fit công thức vào nhãn của validation/final. Chênh lệch tỷ lệ theo thời gian phản ánh cả loại proposal, source version và lớp quản trị; không tự diễn giải thành thay đổi hành vi.

Các tham số mô tả cho nghiên cứu hành vi về sau chỉ ước lượng trên B-development: **487 đề xuất/15.216 phiếu**. Không dùng C để fit, không lấy validation/final làm mẫu hiệu chỉnh. Kiểm thử có trường hợp thay dữ liệu holdout mà tập hiệu chỉnh không đổi.

## 6. Đầu vào ABM đã chuẩn bị

Mẫu C: **1.006 proposal, 60.804 phiếu, 5.921 ví**, với 414.718 dòng component theo strategy. Tất cả C được giữ bằng đúng ID chọn trước; không nới mẫu để tăng độ khớp. C vẫn có 38 proposal thuộc phiên bản thiếu định nghĩa DEFAULT; cờ giả định phụ thuộc được xuất kèm.

Trong 1.023 proposal binding của B, có 1.016 khớp; mẫu C 1.006 loại các trường hợp không khớp và 10 trường hợp ngân sách còn chưa tái dựng. Đây là lý do C không dùng để đánh giá độ khớp chung hoặc khả năng dự báo hành vi.

Các file ở abm_inputs/ gồm agents, phiếu/timestamp, component VP, proposal/rule, đặc trưng VP sau đóng và các lượng mô tả ước lượng từ development. Ví không phải người. Chưa có toàn bộ ví eligible, vì vậy không suy người không tham gia, turnout toàn DAO hoặc Gini theo con người. Không cộng VP của một ví qua nhiều snapshot làm tài sản.

Lịch sử trước phiếu chỉ đếm các bản phiếu được lưu có created nhỏ hơn nghiêm ngặt, không gồm phiếu cùng giây hoặc tương lai. Tập dữ liệu thiếu mọi phiên bản phiếu đã bị thay; lịch sử này chưa phải chính xác information set lịch sử. Danh sách voter/choices thực tế và Gini cuối kỳ là dữ liệu replay/hậu nghiệm, không được đưa làm tín hiệu trước quyết định.

## 7. Có thể làm nền tảng ABM và chuyển sang 3.1.1 chưa?

**Có thể chuyển sang đặc tả tác tử và hành vi ở 3.1.1 trên phạm vi đã công bố.** Baseline hiện đủ làm lõi kiểm phiếu quan sát và kiểm thử lại kết quả khi mô hình hành vi được xây sau. Chưa phải một ABM hành vi hoàn chỉnh và chưa đủ để tuyên bố mô phỏng toàn DAO hoặc tái lập production tuyệt đối.

Các tham số Chương 3 cần đặc tả tiếp, chưa gán giá trị thực nghiệm ở đây:

- Sở thích đối với từng outcome, lợi ích riêng/giá trị kinh tế của proposal và chi phí cơ hội.
- Ngân sách và khả năng huy động VP theo từng tài sản/kênh, chi phí mua/vay/thuê và thanh khoản theo thời gian; tách VP khỏi tiền.
- Thông tin tác tử biết tại từng thời điểm, quy tắc tham gia, thời gian phản ứng, ảnh hưởng của tín hiệu và ủy quyền.
- Nếu nghiên cứu trò chơi hối lộ sau này: mức bù tối thiểu, độ tin cậy thanh toán, xác suất chấp nhận và rủi ro, đều phải có dữ liệu riêng hoặc giả định công bố rõ.
- Tổng thể eligible, quan hệ ví–chủ thể và mạng ủy quyền tại snapshot; không tự tạo bằng chứng Sybil.

Chưa xây utility, chiến lược tấn công, QV, escrow/cap hoặc Monte Carlo. Đặc tả dữ liệu và phân nhóm quan sát/ước lượng/giả định nằm ở ABM_INPUT_SPEC.md.

## 8. Bằng chứng tái lập và bảo toàn

- Python 3.12.10, Node v24.11.1; Python core chỉ dùng thư viện chuẩn.
- **45 kiểm thử tự động đạt**, không lỗi/skip. Xem TEST_RESULTS.json và TEST_LOG.txt.
- Phát lại toàn bộ chương trình khi **chặn Python network sockets**, 11 CSV cho SHA-256 giống từng byte. Xem REPLAY_VERIFICATION.json; bản chạy kiểm chứng ở replay/.
- Kiểm checksum 11 file chuẩn hóa và 912 phản hồi nguồn; kiểm 974 thành viên ZIP về đường dẫn an toàn, so 7 file chính với thư mục đã giải nén. Không giải nén đè.
- **1028 file nguồn/báo cáo/mã cũ giữ nguyên SHA-256**. Không chạy lại các script thu thập hoặc chuẩn hóa cũ.

BASELINE_VALIDATION.csv có một dòng/proposal với cờ A/B/C, lý do loại khỏi B, rule/hash, tổng tính độc lập, outcome tham chiếu, cờ ngân sách và bằng chứng quản trị. Các kết quả được tạo lại bằng lệnh trong README.md.
