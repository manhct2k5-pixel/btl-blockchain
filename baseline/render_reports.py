"""Render Vietnamese research reports from completed Baseline and verification outputs."""
import json
import platform
from collections import Counter
from decimal import Decimal
from pathlib import Path

from engine import BINDING_TYPES, rows, sha

ROOT = Path(__file__).resolve().parent
def read(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8'))
def yes(row, field):
    return row[field].lower() == 'true'
def n(value):
    return f'{value:,}'.replace(',', '.')
def pct(value):
    return f'{100*value:.2f}%'.replace('.', ',')
def table(header, data):
    return '| '+' | '.join(header)+' |\n|'+'|'.join('---' for _ in header)+'|\n'+'\n'.join('| '+' | '.join(str(c) for c in row)+' |' for row in data)
def save(name, text):
    (ROOT/name).write_text(text.replace('§', chr(96)), encoding='utf-8')

s = read('BASELINE_SUMMARY.json')
checks, oracle, synthetic = read('REPLAY_VERIFICATION.json'), read('SOURCE_PARITY.json'), read('SYNTHETIC_PARITY.json')
for name, digest in checks['sha256'].items():
    if sha(ROOT/name) != digest:
        raise RuntimeError(f'Replay proof is stale; run verify.py first: {name}')
v = rows(ROOT/'BASELINE_VALIDATION.csv')
b = [r for r in v if yes(r, 'level_b_eligible_pre_outcome')]
binding = [r for r in b if r['proposal_type'] in BINDING_TYPES]
binding_matches = sum(yes(r, 'governance_match') for r in binding)
metrics = rows(ROOT/'METRICS_BY_GROUP.csv')
phases = table(['Giai đoạn theo thời điểm đóng UTC', 'Đề xuất B', 'Khớp', 'Không khớp', 'Tỷ lệ trước lọc kết quả'],
               [(r['value'], n(int(r['level_b_eligible_pre_outcome'])), n(int(r['level_b_matches'])),
                 n(int(r['level_b_mismatches'])), pct(float(r['level_b_match_rate'])) if r['level_b_match_rate'] else 'Không áp rule lịch sử')
                for r in metrics if r['group'] == 'phase'])
types = table(['Loại', 'Đề xuất B', 'Khớp', 'Không khớp', 'Tỷ lệ'],
              [(r['value'], n(int(r['level_b_eligible_pre_outcome'])), n(int(r['level_b_matches'])),
                n(int(r['level_b_mismatches'])), pct(float(r['level_b_match_rate'])))
               for r in metrics if r['group'] == 'proposal_type' and int(r['level_b_eligible_pre_outcome'])])
confusion = table(['Nhãn quan sát quy về outcome', 'Outcome từ phiếu', 'Đề xuất'],
                  [(r['observed'], r['calculated'], r['proposals']) for r in rows(ROOT/'GOVERNANCE_CONFUSION.csv')])
unresolved = table(['Snapshot ID', 'Loại', 'Tính từ phiếu', 'Trạng thái quan sát'],
                   [(r['snapshot_id'], r['proposal_type'], r['computed_governance_outcome'], r['official_status_observed'])
                    for r in b if not yes(r, 'governance_match') and not yes(r, 'manual_adjustment_fields_present_current')])
max_error = max(Decimal(r['snapshot_max_option_abs_error']) for r in v)
budget_b = sum(yes(r, 'budget_layer_unverified') for r in b)
unknown_const_b = sum(yes(r, 'default_dependency_gap') for r in b)
unknown_const_c = sum(yes(r, 'default_dependency_gap') and yes(r, 'level_c_source_selected') for r in v)
strict_count, strict_matches = s['b_without_default_definition_gap'], s['b_without_default_definition_gap_matches']
abm = s['abm_inputs']

save('BASELINE_RESULTS.md', f'''# Kết quả xây dựng và kiểm chứng Baseline

Phạm vi: kiểm phiếu xác định từ phiếu quan sát và quy tắc Governance ứng viên; chuẩn bị dữ liệu ABM. Chạy hoàn toàn offline. Không có tấn công, phòng thủ, Monte Carlo hoặc mô hình hành vi được fit.

## 1. Kết quả chính

| Phép kiểm tra / phạm vi | Kết quả |
|---|---:|
| Đề xuất / phiếu đã đọc và xử lý đầy đủ | {n(s['proposals'])} / {n(s['votes'])} |
| Tổng VP, số phiếu và từng lựa chọn khớp Snapshot | {n(s['snapshot_all_checks_match'])}/{n(s['proposals'])} |
| Mức A với trạng thái final | {n(s['level_a_final'])}; 2 đề xuất còn 18 phiếu pending |
| B: đủ điều kiện trước khi nhìn kết quả khớp | {n(s['level_b_eligible_pre_outcome'])} đề xuất, 101.268 phiếu |
| B: khớp Governance | **{n(s['level_b_matches'])}/{n(s['level_b_eligible_pre_outcome'])} = {pct(s['level_b_match_rate'])}** |
| B: không khớp Governance | {n(s['level_b_mismatches'])} |
| B riêng các loại binding, trước lọc outcome | {n(binding_matches)}/{n(len(binding))} = {pct(binding_matches/len(binding))} |
| C: mẫu binding đã chọn có điều kiện | {n(s['level_c_selected'])}; {n(s['level_c_matches'])} khớp, không dùng làm độ chính xác tổng thể |

Độ khớp headline là **{pct(s['level_b_match_rate'])} trên toàn bộ B**, không phải 100% trên C. Mẫu C đã được chọn theo outcome từ bước enrichment; báo cáo 100% trên C như một kiểm định độc lập sẽ gây thiên lệch lựa chọn.

Đã xử lý 1.841 đề xuất/104.878 phiếu lịch sử và 1.011 đề xuất/72.851 phiếu recent riêng. Trong phần lịch sử, 152 đề xuất thiếu metadata Governance lưu trữ, 20 chưa đóng tại ảnh lưu cũ, 2 còn VP pending; còn 1.667 trong B. Không áp mã 2023 cho bộ 2023–2026. B có đủ nhãn đối chiếu ở mọi trường hợp; reference coverage là 100%. Nếu có nhãn thiếu trong đợt sau, mẫu số chính vẫn là toàn B, đồng thời báo coverage.

## 2. Tính độc lập của phép kiểm phiếu

Chương trình không nhập hàm enrichment. Mỗi phiếu được liên kết qua Snapshot ID, kiểm vote ID/cặp ví–đề xuất duy nhất, kiểm choice index theo từng danh sách choices, VP không âm/hữu hạn, tổng component, số strategy và cửa sổ thời gian. VP được cộng **từ từng phiếu** bằng Decimal; không dùng scores_json hoặc cột tổng đã tính sẵn làm đầu vào tally. VP ủy quyền chỉ là thành phần trong Total VP, không được cộng lần hai.

Chỉ sau khi tính độc lập mới so số phiếu, tổng VP và từng option với Snapshot. Sai số option tuyệt đối lớn nhất: **{max_error} VP**. Dung sai tham chiếu: atol=1e-6, rtol=1e-9; so thắng/thua, hòa và ngưỡng dùng bất đẳng thức chính xác trên VP quan sát, không thêm epsilon để thay kết quả.

Các bộ Yes/No, Accept/Reject, For/Against, invalid, abstain và cách xử lý hòa thay đổi theo source/version. Ngưỡng dùng đại lượng trong mã nguồn, không mặc định là tổng VP tham gia. Loại grant/poll/poi không tự áp một ngưỡng toàn cục; lấy required_to_pass có nguồn của proposal.

Hai đề xuất lịch sử trùng nhãn, trước đây enrichment chưa tính outcome, nay được xử lý theo phép ánh xạ literal của mã nguồn: cộng nhãn ở bản cũ hoặc lấy index đầu ở getVotingResults. Tầng Snapshot vẫn giữ các choice index riêng. Không sửa choices hoặc lấy nhãn chính thức để quyết định phép ánh xạ.

Một proposal recent có timestamp block sau created 3 giây; giữ nguyên cờ chưa xác minh. Điều này không thay phép cộng VP quan sát ở A, nhưng không được coi là chốt VP hợp lệ cho replay Governance. Tally không đồng nghĩa đã kiểm chứng lại số dư hợp đồng, trạng thái Polygon hoặc mọi phiên bản strategy.

## 3. Kiểm chứng quy tắc và giới hạn còn lại

- Đã đối chiếu bản chuyển Python với thực thi hàm TypeScript gốc đã lưu: **{n(oracle['matched'])}/{n(oracle['cases'])} đề xuất B khớp**.
- Kiểm thử vi sai ca biên của cả 20 phiên bản: **{n(synthetic['matched'])}/{n(synthetic['cases'])} khớp**.
- Các lời gọi cơ sở dữ liệu/Snapshot trong oracle được thay bằng stub in-memory, nhận **tổng đã tính từ phiếu**, không nhận scores công bố hay nhãn Governance. Mã nguồn được kiểm checksum; không gọi mạng.
- Có **{unknown_const_b} đề xuất B** dùng phiên bản nhập DEFAULT_CHOICES mà gói offline thiếu file định nghĩa. Giữ ứng viên [yes,no,abstain] như hồ sơ trước và cờ thiếu chứng cứ. Parity dùng cùng ứng viên, nên **không xác nhận được hằng bị thiếu**.
- Bỏ toàn bộ các phiên bản thiếu định nghĩa DEFAULT khỏi B: **{n(strict_matches)}/{n(strict_count)} = {pct(strict_matches/strict_count)}**. Đây là phân tích phạm vi bằng chứng, không phải cách sửa bộ lọc để tối đa tỷ lệ khớp. Chưa chứng nhận deployment production cho tập nào.
- Việc sửa 9 khác biệt ban đầu ở ca biên trước 23/05/2021 dựa trên lỗi khóa số/khóa nhãn trong source gốc; không có proposal B nào dùng ba commit đó. Xem FORMULA_REVIEW_LOG.md. Không điều chỉnh công thức theo official label.

## 4. Những trường hợp không khớp

Tổng {n(s['level_b_mismatches'])} sai lệch Governance đều có tally Snapshot khớp. Không được đồng nhất chúng với lỗi cộng VP.

| Nhóm bằng chứng | Số đề xuất B không khớp | Kết luận được phép |
|---|---:|---|
| Có passed_by/rejected_by trong API hiện tại | {n(s['governance_diffs_with_manual_fields'])} | Có dấu vết lớp quản trị ngoài tally; chưa đủ chứng minh nguyên nhân và thời điểm điều chỉnh ở ảnh cũ |
| Không có những trường quản trị trên | {n(s['governance_diffs_unresolved'])} | Chưa đủ bằng chứng; cần lịch sử deployment, phiên bản cấu hình và nhật ký quyết định |
| Lỗi chuyển nghĩa còn lại được oracle phát hiện | {len(oracle['mismatches'])} | Không có trên tập đã kiểm; không mở rộng kết luận này thành xác nhận production |

Phần lớn chênh nằm ở poll nhiều lựa chọn: hàm biểu quyết có thể trả FINISHED, trong khi nhãn quản trị là passed/rejected/enacted. Có {budget_b} grant trong B đi qua nhánh chấp nhận nhưng còn phụ thuộc ngân sách; **vẫn nằm trong mẫu số B**, không được loại vì khó giải thích. Không dùng trạng thái tài trợ hay receipt để đổi kết quả biểu quyết.

{types}

Ma trận outcome (passed/enacted chỉ quy về ACCEPTED khi đối chiếu kết quả biểu quyết, không xác nhận thực thi):

{confusion}

Chín trường hợp chưa có bằng chứng trường điều chỉnh thủ công:

{unresolved}

BASELINE_MISMATCHES.csv chứa cả sai lệch outcome lẫn sự kiện thiếu bằng chứng/phạm vi. Nhiều dòng có thể thuộc cùng proposal. Muốn lấy đúng {s['level_b_mismatches']} sai lệch outcome, lọc issue_code=GOVERNANCE_OUTCOME_DIFF; không dùng tổng số dòng của file.

## 5. Kiểm chứng theo thời gian

Mốc thời gian đã chốt trong BASELINE_DESIGN.md: development trước 01/01/2022; validation là 2022; final_historical từ 01/01/2023 của những proposal đã đóng trong ảnh lưu cũ. Theo **thời điểm đóng UTC**:

{phases}

Đây là kiểm chứng hồi cứu của quy tắc xác định, không phải dự báo học máy. Dữ liệu đã từng được khảo sát trước đó, nên không gọi final là tập hoàn toàn chưa từng nhìn. Không fit công thức vào nhãn của validation/final. Chênh lệch tỷ lệ theo thời gian phản ánh cả loại proposal, source version và lớp quản trị; không tự diễn giải thành thay đổi hành vi.

Các tham số mô tả cho nghiên cứu hành vi về sau chỉ ước lượng trên B-development: **{n(abm['development_fit_proposals'])} đề xuất/{n(abm['development_fit_votes'])} phiếu**. Không dùng C để fit, không lấy validation/final làm mẫu hiệu chỉnh. Kiểm thử có trường hợp thay dữ liệu holdout mà tập hiệu chỉnh không đổi.

## 6. Đầu vào ABM đã chuẩn bị

Mẫu C: **{n(abm['c_proposals'])} proposal, {n(abm['c_votes'])} phiếu, {n(abm['c_wallets'])} ví**, với {n(abm['vp_component_records'])} dòng component theo strategy. Tất cả C được giữ bằng đúng ID chọn trước; không nới mẫu để tăng độ khớp. C vẫn có {unknown_const_c} proposal thuộc phiên bản thiếu định nghĩa DEFAULT; cờ giả định phụ thuộc được xuất kèm.

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

- Python {platform.python_version()}, Node {oracle['node_version']}; Python core chỉ dùng thư viện chuẩn.
- **{checks['unit_tests']['unit_tests']} kiểm thử tự động đạt**, không lỗi/skip. Xem TEST_RESULTS.json và TEST_LOG.txt.
- Phát lại toàn bộ chương trình khi **chặn Python network sockets**, {checks['csv_outputs_byte_identical']} CSV cho SHA-256 giống từng byte. Xem REPLAY_VERIFICATION.json; bản chạy kiểm chứng ở replay/.
- Kiểm checksum 11 file chuẩn hóa và 912 phản hồi nguồn; kiểm 974 thành viên ZIP về đường dẫn an toàn, so 7 file chính với thư mục đã giải nén. Không giải nén đè.
- **{s['input_preservation']['protected_files_verified_unchanged']} file nguồn/báo cáo/mã cũ giữ nguyên SHA-256**. Không chạy lại các script thu thập hoặc chuẩn hóa cũ.

BASELINE_VALIDATION.csv có một dòng/proposal với cờ A/B/C, lý do loại khỏi B, rule/hash, tổng tính độc lập, outcome tham chiếu, cờ ngân sách và bằng chứng quản trị. Các kết quả được tạo lại bằng lệnh trong README.md.
''')

save('ABM_INPUT_SPEC.md', f'''# Đặc tả đầu vào ABM

Đây là dữ liệu replay và hợp đồng đầu vào, chưa có mô hình hành vi/utility. Toàn bộ file dưới abm_inputs/ được sinh từ Baseline độc lập. Mẫu C là mẫu chọn có điều kiện theo outcome; không dùng nó như một quần thể đại diện hay tập kiểm định độc lập.

## 1. Bảng, khóa và đơn vị

| File | Khóa / số dòng | Nội dung và phạm vi |
|---|---|---|
| agents.csv | agent_id; {n(abm['c_wallets'])} ví | Địa chỉ chữ thường; đơn vị ví, không phải người. Quần thể là người đã tham gia trong C, không gồm eligible nonvoters |
| agent_proposal_votes.csv | vote_id; {n(abm['c_votes'])} dòng | agent_id + snapshot_id duy nhất; VP, lựa chọn theo index, timestamp, delay, history trước phiếu, phase, nguồn |
| vp_components.csv | vote_id + strategy_index; {n(abm['vp_component_records'])} dòng | Component VP quan sát; name/symbol/network lấy đúng strategy của proposal. Không cộng lại lên total VP |
| proposals.csv | snapshot_id; {n(abm['c_proposals'])} dòng | Type, choices đầy đủ, block, start/end, candidate rule/threshold, phase, has_unverified_default_constant, deployment_verified=False |
| proposal_features_after_close.csv | snapshot_id | Số voter quan sát, VP đã sử dụng, Gini/HHI/top-k theo ví; chỉ biết sau đóng; eligible_wallet_count/eligible_vp/population_turnout để trống |
| empirical_parameters.csv | parameter; 6 dòng | Q25/median/Q75 của delay và VP tham gia; chỉ B-development, không fit validation/final hoặc C |

VP là đơn vị voting power quan sát, không phải MANA hoặc USD. strategy_index bắt đầu từ 0; choice_index bắt đầu từ 1. Unix timestamps là giây UTC; normalized_delay là (created-start)/(end-start), vô hướng. Gini/HHI/shares dùng phân bố ví tham gia từng proposal; trường undefined khi không có phiếu để trống, không điền 0.

Trong file component, symbol MANA, LAND, ESTATE, NAMES, delegated, wearables hoặc rental là nhãn strategy; tham số gốc còn trong metadata/strategies_json ở data_enrichment và raw nguồn. Không suy token balance hay quyền sở hữu từ một số VP. delegated_vp_component là phần nằm trong total VP, không phải VP thêm vào.

source_raw_file tương đối với thư mục **data_enrichment/**, kể cả khi đang đọc bảng ở baseline/abm_inputs/. Liên kết bằng Snapshot ID để lấy choices, strategies/params, provenance và scores tham chiếu. Không dùng tên proposal làm khóa; Governance UUID và Snapshot ID khác nhau.

## 2. Ba nhóm thông số

| Nhóm | Trường / tham số | Căn cứ và giới hạn |
|---|---|---|
| Đo trực tiếp | voter, vote ID, timestamp, choice, VP và component, Type/choices/start/end, block, ngưỡng được công bố | Quan sát từ nguồn được lưu; không phải bằng chứng danh tính người hoặc scoring version bất biến |
| Tính trực tiếp từ quan sát | Tổng option, Gini/HHI/top-k theo ví tham gia, delay, prior retained votes | Không phải tham số hành vi đã nhận diện; features sau đóng chỉ phục vụ mô tả/replay |
| Ước lượng từ dữ liệu | 6 quantile trong empirical_parameters.csv | {n(abm['development_fit_votes'])} phiếu/{n(abm['development_fit_proposals'])} proposal B-development; quan sát lặp ví theo snapshot, không phải mẫu độc lập về tài sản dân cư |
| Giả định chưa định giá | Utility, chi phí cơ hội, budget/khả dụng VP, phản ứng tham gia, thông tin, mạng ảnh hưởng, ý chí hối lộ | Chưa có giá trị số, chưa có hàm lợi ích hoặc chiến lược. Cần dữ liệu/giả định rõ ở Chương 3 |
| Giả định về phiên bản | Candidate commit theo thời điểm đóng, DEFAULT_CHOICES ứng viên ở các phiên bản thiếu định nghĩa | Không coi là quan sát production; giữ has_unverified_default_constant và deployment_verified |

Không dùng quantile VP để thay cho chi phí huy động VP. Không gọi phân phối delay hay tần suất vote là xác suất tham gia toàn DAO khi chưa có mẫu số eligible.

## 3. Thời gian và chống nhìn trước

- agents.csv là danh sách biết được **sau khi quan sát mẫu C**. Không nạp toàn danh sách này làm quần thể biết trước cho một bài toán dự báo ex ante rồi tuyên bố không có leakage.
- Choice và thời điểm gửi thực tế là các sự kiện cần replay/giải thích, không phải predictor cho lựa chọn chưa diễn ra.
- VP gắn proposal/block; không cộng VP qua các proposal hoặc dùng VP của một snapshot tương lai làm trạng thái quá khứ.
- prior_retained_votes_strictly_before chỉ đếm timestamp nhỏ hơn t. Tất cả sự kiện cùng giây bị loại khỏi lịch sử trước t; không tự dùng thứ tự CSV hoặc vote ID để giả vờ có thứ tự quan sát trong cùng giây.
- Dữ liệu Hub giữ phiên bản phiếu cuối còn được trả; thiếu toàn bộ lịch sử thay phiếu. Một số đặc trưng lịch sử vì thế là đại lượng trên tập retained records, không phải thông tin lịch sử đầy đủ.
- proposal_features_after_close không được làm đầu vào ra quyết định trong cửa sổ vote. Top-k/Gini cuối kỳ khác phân bố toàn bộ eligible VP tại lúc mở.
- Tham số ước lượng chỉ dùng giai đoạn development đóng trước 01/01/2022 UTC. Mốc validation=2022, final_historical từ 01/01/2023 đã chốt trước chạy. Tập cuối là hồi cứu, không quảng bá là hoàn toàn chưa từng khảo sát.

## 4. Điều kiện sử dụng

Baseline C có {n(abm['c_proposals'])} proposal/{n(abm['c_votes'])} vote; {unknown_const_c} proposal còn thiếu định nghĩa DEFAULT trong source archive. Giữ cờ này trong mọi mô hình tiếp theo, không tự xóa để tăng kết quả. Đối với kiểm chứng khả năng khớp kết quả, dùng đầy đủ B trước lọc outcome và báo cáo cả mismatch; C chỉ phục vụ phân tích trường hợp có điều kiện.

Đối với mô phỏng hành vi toàn cộng đồng, trước tiên cần tổng thể eligible wallets, VP tại snapshot và thông tin delegation/network có thời gian hiệu lực. Không suy số ví không tham gia từ hiệu giữa số ví members và số voter của một proposal; members là mẫu được chọn và số dư của thời điểm khác.

Chưa có giả định mặc định cho chiến lược tấn công, money budget, private utility, cơ chế phòng thủ, Sybil identity hoặc xác suất hối lộ. Không có các trường này được điền bằng 0 để giả vờ đã quan sát.
''')

save('README.md', f'''# Baseline Decentraland DAO

Kiểm phiếu độc lập từ {n(s['votes'])} phiếu/{n(s['proposals'])} proposal; quy tắc Governance ứng viên chỉ áp bộ lịch sử đủ điều kiện. Đọc BASELINE_DESIGN.md và BASELINE_RESULTS.md trước khi dùng tỷ lệ khớp. ABM_INPUT_SPEC.md mô tả đầu vào được chuẩn bị, chưa có mô phỏng hành vi.

## Chạy lại từ workspace

§§§powershell
python baseline/run_baseline.py
python baseline/verify.py
python baseline/render_reports.py
§§§

Core dùng Python 3.12+ với thư viện chuẩn, không cần pip hoặc mạng. Đã kiểm tra trên Python {platform.python_version()}. Kiểm chứng thực thi source TypeScript dùng Node {oracle['node_version']} (Node 24 hỗ trợ stripTypeScriptTypes); đây là oracle offline, không phải dependency của core kiểm phiếu.

Các lệnh trên chỉ ghi trong baseline/. Không chạy các script data_enrichment. Mặc định đọc nguyên thư mục enrichment đã có, gồm recent/, raw_downloads/, source_log và replay_verification. ZIP nguồn nếu có được kiểm đường dẫn và file chính, không giải nén đè. SHA nguồn và các báo cáo/mã cũ được giữ trong INPUT_MANIFEST.json.

Có thể chạy riêng unit tests:

§§§powershell
python -m unittest discover -s baseline/tests -v
§§§

Có thể đổi nơi ghi **trong** baseline/, ví dụ:

§§§powershell
python baseline/run_baseline.py --output baseline/replay
§§§

Lỗi khóa trùng, choice/VP sai, malformed CSV, số strategy sai, source hash thay đổi hoặc vote ngoài cửa sổ làm chương trình dừng với mã lỗi và thông báo, không tự sửa nguồn. Pending VP, thiếu rule hay thiếu metadata được giữ trong kết quả với cờ ngoài phạm vi; không chuyển thành thành công hoặc zero giả.

## Đầu ra chính

- BASELINE_VALIDATION.csv: một dòng/proposal, tổng từ phiếu, so Snapshot, outcome tính độc lập, nhãn đối chiếu, cờ A/B/C, nguồn rule và lý do chưa đủ điều kiện.
- BASELINE_CHOICE_VALIDATION.csv: theo Snapshot ID + choice_index; so sánh cả nguồn Snapshot và bảng choice_reconciliation cũ (chỉ tham chiếu).
- BASELINE_MISMATCHES.csv: sự kiện sai lệch và thiếu chứng cứ; có nhiều dòng/proposal. Lọc GOVERNANCE_OUTCOME_DIFF để lấy đúng tập không khớp outcome.
- BASELINE_SUMMARY.json, METRICS_BY_GROUP.csv, GOVERNANCE_CONFUSION.csv: các mẫu số/độ khớp trước outcome filter, theo thời gian/loại/rule.
- RULE_CATALOG.json: bản chuyển nghĩa được review theo commit, checksum, phụ thuộc và giả định còn lại.
- SOURCE_PARITY.json, SYNTHETIC_PARITY.json: kiểm Python so với hàm TypeScript gốc được cô lập I/O; cùng giả định DEFAULT chưa đủ chứng cứ.
- TEST_RESULTS.json, TEST_LOG.txt, REPLAY_VERIFICATION.json: kiểm thử và phát lại chặn socket; replay/ chứa bản dữ liệu dùng đối chiếu byte.
- abm_inputs/: actor-wallet, vote, VP theo strategy, proposal/rule, features sau đóng và quantile fit chỉ development.

Mức B không lọc theo outcome khớp, không loại điều chỉnh thủ công/ngân sách để làm đẹp tỷ lệ. Mức C đã được chọn theo outcome từ trước, nên không dùng tỷ lệ C làm accuracy tổng thể. CORE không truyền scores_json/official labels vào tally hoặc govern; official status chỉ dùng khi đánh giá, riêng source flag C được giữ để tái hiện mẫu đã chọn.

verify.py chạy kiểm thử và hai phép parity, sau đó chạy toàn pipeline với Python socket bị chặn, so SHA của từng CSV với lần chạy gốc. render_reports.py từ chối báo cáo nếu chứng cứ replay không còn khớp file CSV. Khi sửa mã, chạy lại cả ba lệnh để không trộn kết quả cũ/mới.

Không có chiến lược tấn công, phòng thủ, utility hoặc Monte Carlo. Không có tuyên bố tái lập production tuyệt đối; missing DEFAULT definition, deployment, budget ledger và lịch sử vote thay thế được nêu rõ trong báo cáo.
''')

code = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(ROOT.rglob('*'))
        if p.is_file() and p.suffix in {'.py', '.mjs'} and '__pycache__' not in p.parts and 'replay' not in p.parts}
(ROOT/'CODE_MANIFEST.json').write_text(json.dumps(code, indent=2), encoding='utf-8')
print('Created BASELINE_RESULTS.md, ABM_INPUT_SPEC.md, README.md and code checksums.')
