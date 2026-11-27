"""Render the scientific report from verified mechanism outputs."""
import json
from collections import Counter
from mechanism import ROOT
from engine import rows
from run_token_weighted import dump


def table(headers,records):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,r))+' |' for r in records])


def main():
    s=json.loads((ROOT/'SUMMARY.json').read_text(encoding='utf-8'))
    v=json.loads((ROOT/'VERIFICATION.json').read_text(encoding='utf-8'))
    metrics=rows(ROOT/'BASELINE_METRICS.csv')
    mismatch=rows(ROOT/'HISTORICAL_MISMATCHES.csv')
    hist=[r for r in metrics if r['mode']=='A_HISTORICAL_RETAINED']
    mismatch_table=table(['Snapshot ID','Loại','Outcome tính lại','Nhãn quản trị','DEFAULT thiếu','Cờ ngân sách'],
          [[r['snapshot_id'],r['proposal_type'],r['computed_outcome'],r['official_status_observed'],
            r['default_dependency_gap'],r['budget_layer_unverified']] for r in mismatch])
    flag_rows=[]
    for flag in ('False','True'):
        group=[r for r in hist if r['default_dependency_gap']==flag]
        flag_rows.append([flag,len(group),sum(r['original_governance_match']=='True' for r in group),
                          sum(r['original_governance_match']=='False' for r in group)])
    flag_table=table(['Thiếu DEFAULT','Đề xuất','Khớp nhãn','Không khớp nhãn'],flag_rows)
    params={'@@MECH@@':str(v['mechanism_tests']),'@@INIT@@':str(v['initialization_regression_tests']),
            '@@BEHAVIOR@@':str(v['behavior_regression_tests']),'@@PREP@@':str(v['preparation_baseline_regression_tests']),
            '@@FILES@@':str(v['identical_result_files']),'@@PROTECTED@@':str(v['protected_prior_files_unchanged']),
            '@@MISMATCH_TABLE@@':mismatch_table,'@@FLAG_TABLE@@':flag_table}
    def write(name,text):
        for key,value in params.items(): text=text.replace(key,value)
        (ROOT/name).write_text(text.strip()+'\n',encoding='utf-8')
    write('TOKEN_WEIGHTED_MODEL.md',r'''
# Cơ chế cơ sở Token-Weighted Voting

## Định nghĩa và vai trò

Cơ chế sử dụng quyền biểu quyết VP hợp lệ theo cấu hình snapshot, không chỉ số MANA. Metadata có nhiều strategy và nguồn điểm; các component đã nằm trong Total VP. Với tập phiếu cuối hiện hành B_j và choices của đề xuất j:

$$
S_{jk}=\sum_{b\in B_j}w_b\mathbf 1\{c_b=k\},\qquad w_b=VP_b.
$$

Mỗi ví có tối đa một phiếu cuối trong từng proposal. Không cộng trọng số một ví qua nhiều proposal thành nguồn lực tại một snapshot. Không cộng Total VP với components hoặc delegation lần nữa. Phiếu 0 VP quan sát vẫn được đếm trong chế độ lịch sử nếu thuộc nguồn final hợp lệ.

Token-Weighted được chọn làm đối chứng vì giữ nguyên cách tổng hợp VP của dữ liệu/lõi đã kiểm, giúp phân biệt tác động thay trọng số sau này với lỗi xử lý phiếu. Đây không là kết luận cơ chế hiện tại tối ưu hoặc chống thao túng.

## Bốn lớp cần tách

1. Tổng hợp trọng số: TokenWeighted trả đúng source VP.
2. Quy tắc thông qua: HistoricalGovernance gọi engine.govern với đúng labels, count, threshold và candidate rule.
3. Nhãn quản trị quan sát: chỉ đối chiếu sau tính toán.
4. Thực thi: UNKNOWN_NOT_INFERRED_FROM_OUTCOME, không suy từ ACCEPTED.

Việc lựa chọn nguồn lực/scoring không được tái thực thi đầy đủ trong module này. Lịch sử dùng các VP đã đối soát; B dùng quyền/VP khai báo của fixture và giữ nhãn giả định.

## Điều kiện phiếu

Kiểm proposal, ví chuẩn hóa, choices, cửa sổ, network/block, provenance, trạng thái final, VP/component hữu hạn không âm. Historical chấp nhận nhãn quan sát hồi cứu đủ chuẩn, không tự gọi quyền production đã xác minh. Scenario yêu cầu quyền được khai báo, chính sách bật giả định và cơ chế hành vi đã kiểm F.

Batch lỗi bị từ chối toàn bộ, không loại phiếu ngầm hoặc để lại cập nhật nửa chừng. Phiếu cùng ví chỉ thay khi caller cho phép rõ, thuộc scenario, là phiên bản mới hơn và không đổi VP snapshot. Historical retained records không đủ lịch thay nên duplicate bị từ chối, không tự suy lần thay.

## Hai ý nghĩa Baseline

Baseline ở giai đoạn chuẩn bị dữ liệu là hệ thống kiểm phiếu và đối chiếu nguồn trong baseline/. Baseline cơ chế của 4.2.1 là module hiện tại có trạng thái phiếu cuối, giao diện trọng số/outcome và kết nối hành vi. Cả hai dùng cùng engine ứng viên nên khớp giữa chúng kiểm tính nhất quán, không tạo một kiểm định production độc lập.

## Giới hạn

Giữ 49 DEFAULT, bảy mismatch và 10 cờ ngân sách của B binding; toàn bộ deployment chưa xác minh. Không tính eligible turnout từ 6.004 ví hồi cứu; không báo tỷ lệ tấn công hay chi phí USD. Thay trọng số ở cơ chế khác cần kiểm lại đơn vị và quy tắc thông qua, không mặc định ngưỡng VP cũ còn phù hợp.
''')
    write('MECHANISM_DESIGN.md',r'''
# Thiết kế module cơ chế

## Phụ thuộc thực sự được sử dụng

Engine được import từ đúng baseline/engine.py và thực thi trong cả nhánh lịch sử/tổng hợp. SUMMARY lưu đường dẫn và SHA256. Nếu thiếu hoặc không đúng module, dừng; không thay bằng công thức Yes>No để tiếp tục.

Đã kiểm đầy đủ nguồn, schema, khóa và checksum qua load_sources của 4.1.1. Không gọi hàm thu thập hoặc tạo lại dữ liệu. INPUT_AUDIT ghi các tệp đã đọc.

## Giao diện

| Thành phần | Nhận | Trả hoặc trách nhiệm |
| --- | --- | --- |
| Ballot | Proposal, ví, choice, VP/components, timestamp, chain/block, nguồn và quyền | Bản ghi bất biến, phân biệt HISTORICAL_RETAINED và SCENARIO_ASSUMED |
| WeightPolicy | Phiếu đã kiểm và WeightContext gồm as_of, snapshot/network/block, cờ chứng cứ | Effective weight và weight_unit; hiện chỉ TokenWeighted identity |
| OutcomePolicy | Proposal, vector weights, count, threshold, rule và weight policy | Decision; hiện HistoricalGovernance gọi lõi gốc |
| BallotBox.commit | Batch và as_of, cờ thay phiếu | Kiểm nguyên khối rồi cập nhật tập phiếu cuối |
| BallotBox.evaluate | as_of và trạng thái cuối hiện có | MechanismResult, count, weights, outcome, đơn vị, data_status và audit flags |

Đối tượng không chứa sở thích hoặc lựa chọn thay tác tử. Nó nhận phiếu đã được tạo bởi replay hoặc luật hành vi, kiểm điều kiện phiếu rồi xử lý cơ học. Lớp hành vi vẫn chịu trách nhiệm utility, F của hành động, thời gian, quyền scenario và tiền.

## Trạng thái cuối và số học

Mỗi BallotBox thuộc một proposal, khóa ví bên trong không được dùng cho proposal khác. Version cũ được thay thế rõ ràng; evaluate tính lại từ tập phiếu cuối, không tích lũy mọi version. VP giữ Decimal, tổng ở độ chính xác 120; concentration dùng hữu tỷ, xuất tỷ số 40 chữ số có nghĩa. Dung sai component lịch sử theo Baseline; component giả định phải bằng đúng VP.

as_of không được trước các phiếu đang dùng. Kết quả lúc chưa đóng mang nhãn OPEN_ADMINISTRATIVE_COUNTERFACTUAL_NOT_AGENT_SIGNAL. Đây là phép kiểm nội bộ sau lô, không được đưa vào thông tin tác tử. Execution luôn riêng.

## Kết nối 4.1.2

TokenWeightedBehaviorSession kế thừa BehaviorSession, không override decide, utility, decision_view, lịch, tín hiệu hoặc chính sách ngân sách. Tại hook kiểm bất biến sau mỗi lô, adapter chuyển các trạng thái phiếu đã commit thành Ballot, cập nhật BallotBox, đối chiếu rồi dùng tổng của cơ chế làm tổng chuẩn tại biên lô.

Với Token identity, tổng này đúng bằng source VP mà lớp hành vi đang giữ. Ở cuối, outcome qua cơ chế phải trùng outcome ứng viên của môi trường. Các phép tính trước/sau lô chỉ cho bộ kiểm, không tạo tín hiệu mới.

Bridge hiện có các bất biến chuyên biệt Token-Weighted. Không tuyên bố chỉ đổi class là toàn bộ ABM đã hỗ trợ mọi trọng số mới: cơ chế khác còn cần nối bộ tổng hợp nguồn/effective weights, điều kiện outcome, công bố thông tin và cách niềm tin phản ứng với cơ chế. Có thể mở rộng những điểm nối này mà giữ các luật utility và cấu trúc tác tử; chưa triển khai phương án khác.

## Cổng tương thích

HistoricalGovernance chỉ chấp nhận policy TOKEN_WEIGHTED_VP_IDENTITY với đơn vị VP. Policy khác bị từ chối nếu cố dùng trực tiếp ngưỡng cũ. Định nghĩa giao diện không tự xác nhận tính phù hợp của threshold hoặc rule cho đơn vị mới.

## Tái lập và so sánh về sau

BEHAVIOR_BASELINE_CONFIG khóa population scope, VP/quyền, sở thích, epsilon, profiles, ngân sách, lịch, tín hiệu và seed. COMPARISON_CONTRACT lưu hash config, mã nguồn và hai thiết kế khác nhau:

- So cơ học: giữ phiếu cuối, thay chính sách trọng số sau khi đặc tả outcome tương thích. Trả lời về ảnh hưởng trực tiếp của phép tổng hợp.
- So có phản ứng: chạy lại hành vi dưới cơ chế mới với cùng sở thích/nguồn lực ban đầu, công bố cách cơ chế ảnh hưởng F và niềm tin. Trả lời về hệ thống có phản ứng.

Profiles hiện tại được khóa như cấu hình baseline. Chưa có quy tắc niềm tin phụ thuộc cơ chế, nên không gọi chạy lại cùng bảng mu tĩnh là đã mô hình hóa đầy đủ phản ứng với trọng số mới. Thiết kế sau phải cố định quy tắc cập nhật đã công bố, không buộc mọi giá trị mu thực hiện giống nhau khi cơ chế thay đổi và không điều chỉnh chúng sau khi thấy outcome.

Không gộp hai thiết kế. Không chạy phép so sánh phòng thủ trong nhiệm vụ này.

## Lỗi tích hợp đã xử lý

Runner mới ban đầu trùng tên run_baseline với module chuẩn bị dữ liệu, làm suite cũ import nhầm. Đã đổi thành run_token_weighted.py, không sửa runner hoặc tests cũ. Sau đổi tên, toàn bộ @@PREP@@ kiểm thử Baseline chuẩn bị tiếp tục đạt. Đây là lỗi tên module của runner mới, không phải thay đổi quy tắc hay số liệu.
''')
    write('HISTORICAL_VALIDATION.md',r'''
# Kiểm chứng lịch sử: cơ chế cộng và phiếu cuối

## Mẫu và phương pháp

Dùng đúng B binding trước lọc outcome: 1.023 đề xuất, 63.662 phiếu và 6.004 ví từng xuất hiện. C gồm 1.006 đề xuất được chọn có điều kiện, không được dùng thay mẫu chính. 17 đề xuất ngoài C vẫn được giữ.

Metadata, phiếu, nguồn raw/normalized và tính đủ điều kiện B được kiểm qua loader cũ. Module mới tạo Ballot theo Total VP, choice index, snapshot và nguồn từng phiếu. Đọc các phiếu giữ lại như trạng thái final, không giả toàn bộ lịch thay phiếu đã được tái dựng.

BallotBox cộng độc lập rồi gọi đúng Governance ứng viên. Chỉ sau khi có kết quả mới đối chiếu Baseline/nhãn chính thức, không đưa official status vào công thức.

## Kết quả

| Kiểm | Kết quả | Mẫu số/ý nghĩa |
| --- | ---: | --- |
| Vector VP, số phiếu và outcome trùng Baseline | 1.023 | 1.023 B binding |
| Outcome khớp nhãn quản trị quan sát | 1.016 | 1.023, khoảng 99,32% |
| Outcome không khớp nhãn | 7 | Vẫn trong mẫu chính |
| Phụ thuộc DEFAULT thiếu chứng cứ | 49 | Giữ riêng trong DEFAULT_DEPENDENCY.csv |
| Cờ lớp ngân sách chưa xác minh | 10 | Không đổi outcome bằng lớp ngoài tally |
| Total VP=0 | 1 | Gini/HHI/tỷ trọng không xác định |
| Hòa dẫn đầu raw có VP dương | 0 | Không đồng nhất với mọi phép hòa nội bộ Governance |
| Winner đúng bằng threshold | 0 | Hành vi tại dấu bằng được kiểm bằng fixture |

Outcome tính lại gồm 412 ACCEPTED, 606 REJECTED và năm FINISHED, tổng 1.023. Không ép FINISHED thành không thông qua hoặc thực thi. Khớp Baseline không là xác nhận độc lập production.

## Bảy trường hợp còn khác nhãn

@@MISMATCH_TABLE@@

Các issue_codes nguồn và cờ điều chỉnh thủ công được giữ trong BASELINE_METRICS/HISTORICAL_MISMATCHES. Cờ cho biết giới hạn hoặc dấu vết, chưa chứng minh nguyên nhân nhân quả của từng sai khác. Không lấy mã nhánh hiện nay để sửa DEFAULT lịch sử.

## Phân tách chứng cứ DEFAULT

@@FLAG_TABLE@@

Tách nhóm để diễn giải bằng chứng, không thay mẫu chính nhằm tăng độ khớp. Bất kể DEFAULT, deployment/scoring runtime vẫn chưa được xác minh đầy đủ.

## Liên kết Chương 3

1.023 proposal khớp tổng VP và số ví của 3.3.2; Gini, HHI và top-k khớp trong sai số biểu diễn tỷ số. Với mỗi S1/S2/S3 của 3.3.1, kiểm lại tally gốc, số phiếu, threshold, commit và outcome trước khi chép trường margin/status/bound_kind.

Chỉ liên kết các kết quả cũ, không tối ưu lại, không tăng số nghiệm S3 và không chạy phân tích độ nhạy. Các trường cận trên/cận dưới giữ đúng tên.

## Điều không suy được

Lịch sử chỉ có retained records, nên replacement_count và replacement_outcome_change_batches để trống có trạng thái UNKNOWN, không gán bằng 0. Không tính eligible turnout hoặc tỷ lệ tấn công. Thống kê sau đóng chỉ cho đánh giá, không cung cấp trước cho tác tử.
''')
    write('BEHAVIOR_INTEGRATION.md',r'''
# Kết nối luật hành vi 4.1.2

## Không đổi hành vi để đổi kết quả

Dùng nguyên fixture nhỏ đã có, dựng world B bằng build_world 4.1.1 rồi chạy BehaviorSession và TokenWeightedBehaviorSession trên hai bản world độc lập cùng cấu hình. Đây là kiểm bảo toàn hành vi, không phải hai quan sát thực nghiệm.

Lịch quyết định, mọi view đã cung cấp, utility, Delta U, epsilon, hành động đề nghị/commit, ngân sách cuối và kết quả đều trùng. Trace và views còn được đối chiếu với tệp đã khóa của 4.1.2. Không sửa mã trước hoặc điều chỉnh tham số.

## Kết quả fixture

Bốn tác tử tổng hợp, hai proposal, năm context và chín lượt quyết định: ba VOTE, một REPLACE, hai KEEP và ba WAIT. Có ba phiếu cuối, không phải bốn vì một phiếu đã bị thay thế.

| Proposal tổng hợp | Choices | Tổng cuối | Phiếu cuối | Threshold | Outcome ứng viên |
| --- | --- | --- | ---: | ---: | --- |
| SYNTHETIC_BINARY | Yes, No | [10,3] VP | 2 | 10 VP | ACCEPTED |
| SYNTHETIC_MULTI | for, against, invalid | [6,0,0] VP | 1 | 5 VP | ACCEPTED |

Toàn bộ quyền, VP, utility, lịch, tín hiệu và epsilon của fixture là giả định đã khai báo, không mô tả hành vi thật. Phiếu cuối được gắn SCENARIO_ASSUMED/physical_rights_verified=false.

## Thay phiếu và lô

Adapter nhận phiếu sau commit, không tự chọn thay tác tử. Tại lô có thay phiếu, ghi outcome trước/sau và flag thay đổi. Trong fixture chuẩn có một lần thay nhưng không đổi outcome cuối của lô đó. Unit test riêng có trường hợp thay hợp lệ làm ACCEPTED thành REJECTED.

Nếu lô có nhiều hành động, before/after là tác động cả lô, không khẳng định một ví riêng gây đổi kết quả. Không suy số lần thay phiếu lịch sử từ trace tổng hợp.

## Thông tin và tiền

Phép tính mechanism audit chỉ cho bộ kiểm. Không đưa vào decision_view; không thêm public tally hoặc nhãn cuối. Không nạp retained votes vào cơ chế quyết định B.

Cơ chế không sửa tài khoản, cấp tiền hoặc đổi principal. Bất biến ngân sách vẫn do BehaviorSession kiểm; kiểm hồi quy bao gồm hai ví chung tài khoản, thiếu tiền và xung đột cùng giây. Seed 19 được giữ, không sử dụng RNG.

## Đầu vào còn thiếu cho thí nghiệm lớn

Registry 6.004 chưa là quần thể eligible. Muốn chạy kịch bản lớn cần scope, quyền/VP theo snapshot, utility, niềm tin, epsilon, ngân sách, lịch và thông tin đủ chuẩn. Không lấy các choice quan sát để suy sở thích rồi xác nhận trên cùng choice.

Có nền tảng để đặc tả cơ chế khác nhưng chưa chạy QV, escrow, capping, tấn công hoặc phòng thủ. Bridge hiện chuyên Token identity; phải kiểm thêm đơn vị và outcome khi mở rộng.
''')
    write('MECHANISM_TEST_RESULTS.md',r'''
# Kiểm thử và kiểm chứng cơ chế

## Kết quả cuối

| Bộ kiểm | Số bài đạt |
| --- | ---: |
| Cơ chế mới | @@MECH@@ |
| Khởi tạo 4.1.1, mã không đổi | @@INIT@@ |
| Hành vi 4.1.2, mã không đổi | @@BEHAVIOR@@ |
| Baseline chuẩn bị dữ liệu, mã không đổi | @@PREP@@ |

Không lỗi hoặc thất bại trong lần kiểm cuối. Log riêng: TEST_LOG, INITIALIZATION_REGRESSION_LOG, BEHAVIOR_REGRESSION_LOG và PREPARATION_BASELINE_REGRESSION_LOG. Việc từng gặp trùng tên runner được ghi ở MECHANISM_DESIGN; không che bằng sửa tests cũ.

## Các bất biến được kiểm độc lập

Tổng cuối bằng tổng mỗi phiếu hiện hành; component/delegation không cộng thêm; thập phân chính xác; proposal tách biệt; duplicate hoặc batch lỗi không để lại cập nhật; replacement giữ count và chuyển đúng VP; time/network/block và quyền/basis phải đúng; VP/component âm hoặc không hữu hạn bị từ chối.

Kiểm Yes/No, nhiều choices, abstain và invalid theo rule; threshold equality và tie; ACCEPTED khác execution; nhãn chính thức không điều chỉnh outcome. Policy không tương thích đơn vị bị từ chối khi dùng Governance/ngưỡng cũ.

Gini được đối chiếu công thức chênh lệch từng cặp trên fixture, HHI có kết quả tính tay; V=0 để không xác định. Kiểm tích hợp đối chiếu toàn bộ trace/views/tài khoản với hành vi nguyên bản, không chỉ so outcome.

## Kiểm bằng dữ liệu lịch sử

1.023/1.023 khớp tally/count/outcome của Baseline chuẩn bị; 1.016/1.023 khớp nhãn quản trị, bảy mismatch vẫn giữ. 63.662 phiếu được kiểm nguồn và tính lại, không thay rule để tăng số khớp.

## Tái lập

Chạy hai nhánh với socket mạng bị chặn cho @@FILES@@ tệp kết quả giống từng byte. @@PROTECTED@@ tệp có trước nhiệm vụ giữ nguyên hash. Engine import đúng file, có SHA trong SUMMARY.

## Giới hạn

Kiểm module, kiểm tích hợp và kiểm khớp lịch sử không đồng nghĩa kiểm định utility hoặc deployment production. Fixture nhỏ chưa là đánh giá hành vi thực; khớp 100% với cùng engine không phải hai cách triển khai Governance độc lập.

Không có tỷ lệ tấn công, Monte Carlo, cơ chế phòng thủ khác hoặc phân tích độ nhạy trong nhiệm vụ này.
''')
    write('CH4_4_2_1_REPORT_DRAFT.md',r'''
# 4.2.1. Baseline Token-Weighted Voting

Mục này xây dựng cơ chế đối chứng theo trọng số quyền biểu quyết để kiểm tra sự kết nối giữa tác tử, trạng thái phiếu và quy tắc thông qua. Giữ cơ chế có căn cứ trong dữ liệu giúp các nghiên cứu tiếp theo phân biệt thay đổi do thiết kế trọng số với sai khác do mã xử lý hoặc điều kiện đầu vào. Việc chọn cơ chế đối chứng không khẳng định đây là phương án tối ưu hay có khả năng chống thao túng.

### Tổng hợp VP và quy tắc thông qua

Với đề xuất j và lựa chọn k, tổng trọng số là:

$$
S_{jk}=\sum_{i\in B_j}w_{ij}\mathbf 1\{c_{ij}=k\},
$$

trong đó B_j là tập ví có phiếu cuối hợp lệ và w_ij là Total VP tại snapshot tương ứng. Một ví chỉ có một phiếu hiện hành trên từng đề xuất. Khi thay phiếu, đóng góp cũ bị loại trước khi thêm vào lựa chọn mới; số phiếu không tăng. Các nguồn điểm và delegation đã nằm trong Total VP nên không được cộng thêm lần nữa.

Đây là trọng số VP từ nhiều strategy, không đơn thuần trọng số MANA. Danh sách choices giữ riêng từng proposal, gồm abstain hoặc invalid khi có. Sau tổng hợp, outcome được xác định bằng Governance ứng viên đúng phiên bản, ngưỡng và phép chiếu nhãn. Cách cộng trọng số, điều kiện thông qua, trạng thái quản trị quan sát và thực thi là bốn lớp khác nhau.

### Kiểm chứng lịch sử

Chế độ A dùng B binding gồm 1.023 đề xuất, 63.662 phiếu và 6.004 ví từng tham gia, được chọn trước khi lọc theo khớp outcome. Module cộng lại các phiếu cuối và gọi lõi Baseline đã có trong workspace, không thay bằng công thức nhị phân tự tạo.

**Bảng 4.2. Đối chiếu cơ chế trên mẫu B binding**

| Chỉ tiêu | Kết quả | Phạm vi |
| --- | ---: | --- |
| Tally, count và outcome trùng Baseline | 1.023/1.023 | Kiểm cơ học và quy tắc ứng viên |
| Outcome khớp nhãn quản trị | 1.016/1.023 | Khoảng 99,32%, không là xác suất thành công |
| Không khớp nhãn | 7 | Giữ nguyên để phân tích giới hạn |
| Khoảng trống DEFAULT | 49 | Không loại khỏi mẫu |
| Cờ ngân sách chưa xác minh | 10 | Tách khỏi tally |

Nguồn: BASELINE_METRICS, HISTORICAL_MISMATCHES và SUMMARY của module 4.2.1, đối chiếu BASELINE_VALIDATION và nguồn phiếu đã kiểm. Đơn vị đếm là đề xuất. Các nhóm cờ có thể chồng nhau.

Outcome tính lại gồm 412 ACCEPTED, 606 REJECTED và năm FINISHED. Khớp toàn bộ Baseline cho thấy tính nhất quán của cơ chế với lõi ứng viên, không tự chứng nhận phiên bản production. Bảy khác biệt với nhãn quản trị không được sửa bằng cách thay công thức hoặc loại đề xuất. DEFAULT, deployment và lớp ngân sách tiếp tục là giới hạn đã công bố ở Chương 3.

### Kết nối quyết định tác tử

Chế độ B giữ nguyên luật 4.1.2, từ utility và epsilon tới lịch thông tin và nguồn lực chung. Module cơ chế nhận phiếu sau khi tác tử tự chọn và commit; nó không thay thế sở thích hoặc tạo hành động để ép outcome.

Fixture chuẩn có bốn tác tử tổng hợp, hai proposal và chín lượt quyết định. Trace và view giống phiên bản không có adapter cơ chế. Có ba phiếu cuối sau ba bỏ phiếu lần đầu, một thay, hai giữ và ba chờ. Đây là kiểm thử phần mềm với tham số giả định, không là bằng chứng hành vi ví thật.

**Bảng 4.3. Kết quả fixture tổng hợp**

| Proposal kiểm thử | Vector VP cuối | Phiếu cuối | Threshold | Outcome |
| --- | --- | ---: | ---: | --- |
| SYNTHETIC_BINARY | [10,3] | 2 | 10 VP | ACCEPTED |
| SYNTHETIC_MULTI | [6,0,0] | 1 | 5 VP | ACCEPTED |

Nguồn: cấu hình và trace 4.1.2 được giữ cố định, MODE_B_FINAL_BALLOTS và BASELINE_METRICS của 4.2.1. Mọi quyền, VP, sở thích, niềm tin và lịch ở bảng là giả định kiểm thử.

### Chỉ tiêu và cách sử dụng

Module xuất tổng VP, vector theo choice, số ví, phân vị VP, Gini, HHI và tỷ trọng top-k của người đã bỏ phiếu. Một đề xuất lịch sử có tổng VP bằng 0 nên các chỉ tiêu tập trung được để không xác định. Không lấy số ví tham gia chia cho registry 6.004 để gọi là tỷ lệ tham gia toàn DAO.

Hòa dẫn đầu raw và khoảng cách có dấu giữa VP winner với ngưỡng được lưu, nhưng không đồng nhất raw tie với mọi quy tắc hòa nội bộ. Mẫu lịch sử không có hòa raw dương hoặc winner bằng đúng threshold; các trường hợp biên được kiểm bằng fixture. Không tự chọn tỷ lệ phần trăm để phân lớp sát ngưỡng.

Khi có lịch thay phiếu tổng hợp, ghi outcome trước/sau lô có replacement. Fixture chuẩn có một thay phiếu nhưng lô đó không đổi outcome; kiểm thử riêng có trường hợp đổi từ ACCEPTED sang REJECTED. Đối với lịch sử retained votes, số lần thay và tác động chưa xác định, không được ghi bằng 0. Liên kết S1/S2/S3 của Chương 3 chỉ kiểm nguồn gốc và giữ loại cận, không tính lại hoặc coi margin VP là chi phí tiền.

### Điều kiện dùng làm đối chứng

Cấu hình gốc và hash được lưu để giữ quần thể, VP, sở thích, ngân sách, lịch, thông tin và giả định khi nghiên cứu cơ chế khác. So sánh cơ học giữ phiếu rồi thay trọng số khác với so sánh có phản ứng, nơi tác tử đánh giá lại dưới cơ chế mới. Hai thiết kế phải báo riêng.

Giao diện tách WeightPolicy khỏi OutcomePolicy nhằm mở rộng có kiểm soát. Tuy nhiên, ngưỡng VP và Governance hiện tại không tự phù hợp với một đơn vị trọng số khác; adapter hiện vẫn chuyên Token identity. Trước mở rộng cần định nghĩa đơn vị, điều kiện thông qua, giới hạn quyền và cách hành vi phản ứng, rồi kiểm tích hợp tương ứng.

Các kiểm cuối đạt @@MECH@@ bài cơ chế, @@INIT@@ khởi tạo, @@BEHAVIOR@@ hành vi và @@PREP@@ Baseline chuẩn bị; @@FILES@@ tệp kết quả tái lập giống byte. Kết quả lịch sử là kiểm cơ học, kết quả tổng hợp là kiểm phần mềm; chưa có kiểm định utility thực nghiệm hoặc đánh giá phòng thủ. Nhiệm vụ này không triển khai QV, escrow/capping, hành vi tấn công, Monte Carlo hoặc phân tích độ nhạy.

Nguồn kiểm chứng: [dữ liệu đã đối soát](../../../data_enrichment/README.md), [Baseline chuẩn bị](../../../baseline/BASELINE_RESULTS.md), [catalog phiên bản](../../../baseline/RULE_CATALOG.json), [luật hành vi giữ nguyên](../../behavior/BEHAVIOR_MODEL.md), BASELINE_METRICS.csv và VERIFICATION.json của mục này.
''')
    write('README.md',r'''
# 4.2.1 Token-Weighted Voting

Python 3.10 trở lên, thư viện chuẩn và các module workspace. Chạy từ D:\BTL_Blockchain:

~~~powershell
python chapter4/mechanisms/token_weighted/run_token_weighted.py
python chapter4/mechanisms/token_weighted/verify.py
python chapter4/mechanisms/token_weighted/render_reports.py
~~~

Runner tên riêng để không trùng baseline/run_baseline.py. Không chạy collector hoặc ghi đè dữ liệu/kết quả cũ. Engine phải có thật trong baseline/engine.py; đường dẫn và SHA được kiểm, không có fallback Governance tự tạo.

Lệnh đầu chạy A lịch sử và B fixture nhỏ đã có, xuất root module. verify chạy các suite, đối chiếu trace đã khóa của 4.1.2 và chạy lại offline vào replay/. render_reports sinh lại bảy Markdown từ dữ liệu đã xác minh.

## Tệp chính

- BASELINE_METRICS.csv: 1.025 dòng, khóa mode,scenario_id,snapshot_id; 1.023 lịch sử và hai tổng hợp.
- HISTORICAL_MISMATCHES.csv: bảy trường hợp vẫn giữ trong mẫu.
- DEFAULT_DEPENDENCY.csv: 49 trường hợp phụ thuộc hằng thiếu chứng cứ.
- MODE_B_DECISIONS/VIEWS/FINAL_BALLOTS/MECHANISM_AUDIT: trace, view được cấp, phiếu cuối và lô cơ chế; không là dữ liệu lịch sử thật.
- BEHAVIOR_BASELINE_CONFIG và COMPARISON_CONTRACT: cấu hình/hash đối chứng, chưa thực hiện so sánh.
- SUMMARY, VERIFICATION, RESULT_MANIFEST và INPUT_AUDIT: kiểm chứng và nguồn.

## Cách đọc CSV

option_vp_json giữ vector đúng choice index. total_vp là tổng nguồn VP; total_effective_weight trùng tổng đó dưới Token identity. voters gồm cả phiếu VP=0 hợp lệ lịch sử, positive_vp_voters tách riêng.

Gini/HHI/top-k và phân vị chỉ trên người đã tham gia từng proposal. concentration_status báo thiếu do V=0; ô trống không là số 0. raw_leader_tie có thể đúng khi mọi lựa chọn đều 0, nên đọc cùng tie_has_positive_vp. signed_gap_over_threshold không phải xác suất; không có cutoff rủi ro tùy ý.

replacement_count và replacement_outcome_change_batches lịch sử để trống vì chưa đủ lịch. Ở B, change_batches là trước/sau cả lô, không quy nguyên nhân riêng một ví khi có nhiều hành động. S1/S2/S3 được chép có kiểm tra từ 3.3.1, giữ status và bound_kind.

baseline_tally_outcome_match khác original_governance_match. official status chỉ đối chiếu; execution_status vẫn UNKNOWN. physical_rights_verified=false cả hai chế độ. eligible_turnout, attack_success_rate và money_attack_cost_usd không được tính, để trống.

## Giới hạn và mở rộng

TokenWeighted là chính sách trọng số duy nhất được triển khai. HistoricalGovernance từ chối policy/đơn vị khác nếu cố dùng trực tiếp threshold cũ. WeightPolicy/OutcomePolicy là điểm mở, không phải một triển khai QV hoặc capping đã thử.

Bridge hành vi hiện chuyên Token identity, có kiểm nguồn và effective weights ở biên lô. Thay cơ chế cần điều chỉnh điểm nối và xác định outcome/thông tin/niềm tin phù hợp, không sửa tùy tiện luật hành vi để tạo kết quả mong muốn.

@@PROTECTED@@ tệp trước nhiệm vụ được giữ hash. Không Monte Carlo, không phân tích độ nhạy, không mô phỏng tấn công hoặc phòng thủ.
''')
    dump(ROOT/'DEPENDENCY_REVIEW.json',dict(engine_import_verified=True,
        engine_sha256=s['engine_sha256'],engine_file=s['engine_file'],
        initial_issue='New runner initially shadowed preparation run_baseline in regression imports',
        resolution='Renamed new runner to run_token_weighted.py; preparation module and tests unchanged',
        baseline_regression_tests_passed=v['preparation_baseline_regression_tests']))
    print('Rendered seven Markdown documents and dependency review.')


if __name__=='__main__':
    main()
