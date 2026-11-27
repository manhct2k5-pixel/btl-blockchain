"""Render Vietnamese 4.1.2 documentation from verified small synthetic runs."""
import json
from collections import Counter
from pathlib import Path
from behavior import ROOT
from run_behavior import dump
from scenarios import fixture_bundle


def write(name,text):
    (ROOT/name).write_text(text.strip()+'\n',encoding='utf-8')


def main():
    verification=json.loads((ROOT/'VERIFICATION.json').read_text(encoding='utf-8'))
    summary=json.loads((ROOT/'outputs/SUMMARY.json').read_text(encoding='utf-8'))
    substitutions={'@@NEW_TESTS@@':str(verification['behavior_tests']),
                   '@@OLD_TESTS@@':str(verification['initialization_regression_tests']),
                   '@@FILES@@':str(verification['identical_output_files']),
                   '@@PROTECTED@@':str(verification['protected_prior_files_unchanged']),
                   '@@DECISIONS@@':str(summary['decision_count'])}
    def render(name,text):
        for key,value in substitutions.items():
            text=text.replace(key,value)
        write(name,text)
    render('BEHAVIOR_MODEL.md',r'''
# 4.1.2. Mô hình hành vi biểu quyết cơ sở

## Phạm vi

Đã triển khai tham gia/chờ, chọn lựa chọn, thời điểm đánh giá và giữ/thay phiếu. Chỉ chạy trường hợp tổng hợp nhỏ có nhãn SYNTHETIC_TEST_ONLY; không mô phỏng hành vi của 6.004 ví thật, không hối lộ, flash loan, tấn công, phòng thủ hoặc Monte Carlo. Đạt kiểm thử không chứng minh động cơ thật.

Kế thừa [Chương 3](../../chapter3_final/CH3_MASTER_DRAFT.md) và [bộ khởi tạo](../initialization/README.md). Không viết lại hoặc sửa API 4.1.1. BehaviorSession nhận một InitializedWorld B và cấu hình theo từng ví–đề xuất. CLI mặc định chỉ dựng fixture tổng hợp qua chính build_world của 4.1.1.

## Hai lớp dữ liệu

Lớp bằng chứng lưu trạng thái đầu và nhãn physical_rights=UNVERIFIED; không tự bổ sung quyền, ngân sách hoặc sở thích thật. Lớp kịch bản khai báo VP, components, quyền GRANTED/DENIED, cửa sổ hành động, thay phiếu, utility và lịch.

GRANTED chỉ được sử dụng khi allow_assumed_rights=true và basis=SCENARIO_ASSUMPTION. Điều đó cho phép hành động trong thế giới giả định, không xác nhận quyền thực. Mọi phiếu và lịch sử quyết định mới giữ nhãn giả định. Khác biệt giữa VP có sẵn trong bộ khởi tạo và VP mới khai báo phải được giải quyết trước, không ghi đè ngầm.

Quần thể hành vi là contexts theo proposal và thời gian có hiệu lực, không tự lấy toàn bộ registry 6.004 làm eligible ở mọi snapshot. Ví không nằm trong scope không có quyết định và đề xuất không nằm trong scope không được báo kết quả hành vi. Thiếu đầu vào thiết yếu tạo NotReady, không tự chuyển thành 0 hoặc lựa chọn chờ.

## Bốn quyết định

| Quyết định | Thông tin và đầu vào | Luật | Cập nhật |
| --- | --- | --- | --- |
| Tham gia | Quyền/VP kịch bản, lựa chọn, thời gian, utility, chi phí và ngân sách nếu cần | So VOTE:k với WAIT bằng Delta U>epsilon | Thêm đúng một phiếu nếu khả thi |
| Chọn phương án | Giá trị và niềm tin theo từng choice của chính proposal | Cực đại trong tập cân nhắc hợp lệ; hòa theo thứ tự metadata | Không ép Yes/No hoặc chọn theo official outcome |
| Thời điểm | decision_times công bố trước; tín hiệu đã nhận | Lịch xác định trong cửa sổ; có thể thêm lượt review sau tín hiệu | Không hành động trước start/sau end |
| Giữ/đánh giá lại | Choice hiện hành và profile đang biết | KEEP:k là cơ sở; REPLACE chỉ khi được phép và cải thiện vượt ngưỡng | Trừ phiếu cũ trước, không tăng số phiếu khi thay |

Ngưỡng epsilon phải được khai báo, không là phí. Mô hình không dùng VP để suy sở thích hoặc xác suất tham gia. Quy tắc hiện yêu cầu VP dương cho hành động bỏ phiếu, được công bố bằng positive_vp_policy; không phải kết luận giao thức thật cấm mọi phiếu VP=0. Replay 4.1.1 vẫn giữ phiếu 0 VP quan sát được.

## Cách đánh giá tối thiểu

Có thể khai báo giá trị biểu đạt của việc thể hiện lựa chọn, với phân phối trạng thái chủ quan xác định hoặc có nhiều trạng thái. Cách này chạy được mà không gán xác suất thực thi quản trị chưa quan sát. Nếu dùng niềm tin về outcome, đó phải là giả định riêng; không thay bằng kết quả cuối đã biết.

Mỗi profile liệt kê đủ WAIT, KEEP:k, VOTE:k và REPLACE:k theo số lựa chọn của proposal. Chỉ những hành động đúng trạng thái hiện hành mới vào tập cân nhắc. Không tham gia là WAIT, khác Abstain nếu Abstain nằm trong metadata.

## Tương tác tối thiểu

Mọi tác tử trong scope có thể nhận cùng một nhãn tín hiệu ngoại sinh theo lịch giả định và chuyển sang belief profile đã khai báo. Không tự suy mạng xã hội, không nhìn choice của nhau, không phát sinh hối lộ. Người khác đánh giá theo lịch/quy tắc của họ, không bị cố định để bảo đảm một tác tử thắng.

Hiện chưa có phản ứng nội sinh theo tally công khai. Thêm cơ chế đó cần một kênh công bố/nhận thông tin có độ trễ, không đưa toàn bộ tally trong world vào hàm quyết định. strategic_extension là đầu mối chưa triển khai và luôn báo NotImplementedError.

## Cập nhật ODD

Purpose/patterns bổ sung kiểm tra luật trên fixture; entities bổ sung lớp kịch bản và view quyết định; process bổ sung lịch đồng thời; design concepts bổ sung tối ưu trong tập cân nhắc và phản ứng profile. Initialization vẫn do 4.1.1. Input data thêm cấu hình giả định, submodels thêm decide/utility/scheduler. Chưa có mô hình học, dự báo đã kiểm định hoặc kết quả phòng thủ. Không sửa ODD_FRAMEWORK gốc thành một tuyên bố ABM hoàn chỉnh.
''')
    render('DECISION_RULES.md',r'''
# Quy tắc quyết định

## Tập hành động và phương án cơ sở

Nếu chưa có phiếu, cơ sở là WAIT và lựa chọn thay thế là VOTE:k. Nếu đang chọn k0, cơ sở là KEEP:k0, các lựa chọn khác là REPLACE:k với k khác k0. Không thêm VOTE:k0 như một phiếu mới. Không có thao tác rút phiếu hoặc thao tác chiến lược chưa đặc tả.

WAIT khác choice Abstain. Mọi k phải thuộc danh sách gốc, có profile utility riêng theo vị trí và ngữ nghĩa khai báo. Quy tắc so sánh có thể dùng chung, nhưng giá trị và niềm tin không tự dùng chung cho mọi đề xuất.

## Khả thi

Một phiếu mới phải đúng cửa sổ proposal và valid_from/valid_until; có quyền kịch bản GRANTED được chính sách cho phép; VP dương theo chính sách đã chốt; đúng chain/block; và không vượt ngân sách đã biết của từng đồng nếu có tiền phải chi. Thay phiếu còn cần can_replace=true.

DENIED, không đủ tiền đã biết hoặc bị cấm thay là INVALID. Quyền/budget thiết yếu chưa biết là UNKNOWN, không phải 0 hay INVALID. Chuẩn bị kịch bản từ chối trường hợp UNKNOWN trước chạy. Hàm decide cũng không tự chọn cơ sở khi gặp đầu vào thiết yếu chưa giải quyết.

Giữ phiếu không là một lần bỏ mới và không trả lại phí cũ. Cửa sổ hiệu lực ở đây là quyền thực hiện hành động, không tự thu hồi VP của phiếu đã hợp lệ trong kịch bản.

## Utility và quy tắc chọn

Từ các tham số đã cung cấp, tính \(U_i(a)\), sau đó:

$$
\Delta U_i(a;a_0)=U_i(a)-U_i(a_0).
$$

Tác tử chọn một hành động có utility lớn nhất trong tập cân nhắc hợp lệ chỉ khi cải thiện tốt nhất lớn hơn epsilon_i. Nếu không vượt, giữ a0. Tại Delta U=epsilon_i vẫn giữ cơ sở. Nếu nhiều phương án cùng cao nhất vượt ngưỡng, chọn chỉ số metadata nhỏ nhất. Khi cơ sở hòa với mức tốt nhất, không đổi.

Các phép so sánh utility dùng Fraction chính xác, không epsilon số học. Epsilon_i của hành vi là tham số giả định khác với dung sai đối chiếu nguồn. Không trừ epsilon thêm vào C.

Đây là tối ưu trong tập cân nhắc và dưới niềm tin đã khai báo, không tự chứng minh Nash hoặc tính đúng của dự báo chủ quan. Với epsilon dương, tác tử có thể giữ hành động chưa tối ưu tuyệt đối theo chuẩn Nash chính xác.

## Thời điểm

decision_times là đầu vào công bố trước, không lấy timestamp phiếu thật để dự báo phiếu đó. Lịch ngoài cửa sổ hoặc trùng thời điểm của cùng context bị từ chối.

Nếu review_on_signal=true, nhận nhãn thông tin lúc r sẽ tạo lượt đánh giá ở r+1 giây nếu còn trong cửa sổ. Nếu đã có lượt đó thì chỉ quyết định một lần. Nếu không bật, chỉ đánh giá vào lịch đã khai báo. Không mặc định mọi tín hiệu đều thay lựa chọn.

## Cập nhật phiếu

VOTE thêm VP một lần và tăng số phiếu một. REPLACE trừ VP khỏi choice cũ, cộng cùng VP vào choice mới và giữ số phiếu. Components chỉ mô tả nguồn, không được cộng thêm. KEEP/WAIT không sửa tally.

Trọng số snapshot không tự thay khi nhận tín hiệu. Nếu lớp khởi tạo đã có VP khác cấu hình, từ chối thay vì sửa ngầm. Bộ này chưa mô hình hóa việc mua quyền, vay, thay scoring hoặc ủy quyền mới.

## Tài khoản và lô đồng thời

Từng quyết định dùng số dư trước lô. Nếu nhiều ví cùng principal đều chọn hành động cần tiền nhưng tổng vượt một đồng khả dụng, hủy toàn bộ hành động cần tiền của principal đó trong lô; các bên giữ cơ sở. Không dùng thứ tự CSV hoặc xếp hạng utility giữa người khác đơn vị để ưu tiên.

Đây là chính sách xử lý xung đột có công bố, không chứng minh tối ưu phân bổ ngân sách. Trường proposed_action khác committed_action được lưu rõ. Nếu đủ tiền, trừ chi phí đúng một lần; tiền đã chi không tự được tạo lại ở lượt sau.
''')
    render('UTILITY_INTEGRATION.md',r'''
# Kết nối hàm lợi ích

Kế thừa công thức trạng thái của Chương 3. Phiên bản cơ sở sử dụng dạng:

$$
U_i(a)=\sum_z\mu_i(z\mid a,\mathcal I_i(t))v_i(z)
-C_i^{resource}(a)-D_i(a)-\sum_c\lambda_i^c f_i^c(a).
$$

Các profile cung cấp mu cho từng hành động, tổng chính xác bằng một. v có thể âm, mang đơn vị chi_i; resource_cost_utility và risk_loss_utility không âm, cùng đơn vị chi_i. Tiền f theo từng đồng c, lambda có đơn vị chi_i/đồng. Trong phiên bản này C và D là hằng theo trạng thái cho một hành động. Đây là trường hợp riêng của kỳ vọng tổng quát, không viết lại mô hình kinh tế.

resource_cost_utility không chứa lại khoản phí đã đưa vào cash_outflow. Tổng hai phần mới là chi phí nguồn lực của hành động theo quy ước Chương 3; không cộng cùng phí hai lần.

transfers_policy=NONE_BASELINE quy định T_in=T_out=0 do không có chuyển giao chiến lược trong tập hành động. Không nhận thêm khoản hối lộ hoặc trả thưởng vào cấu hình. Tiền ở cash_outflow là phí/chi tiêu nguồn lực không thu hồi ngay của hành động cơ sở, không phải T_out giữa các tác tử.

## Hai cách diễn giải

DECLARED_EXPRESSIVE_STATES_NO_EXECUTION_CLAIM định giá việc thể hiện lựa chọn hoặc tiếp tục chưa tham gia. Niềm tin có thể là một phân phối tập trung hoàn toàn vào trạng thái được khai báo. Nó không cần một xác suất thực thi proposal chưa được quan sát.

DECLARED_SUBJECTIVE_OUTCOME_BELIEFS cho phép đưa các trạng thái quản trị chủ quan vào v và mu. Nếu lợi ích chỉ có khi thực thi, trạng thái và phân phối phải diễn tả đúng sự kiện đó. Mô-đun không tự nhân độ khớp Baseline, không suy mu từ official outcome và không ước lượng xác suất tác động quyết định của VP.

## Thiếu khác 0

Mọi giá trị v, mu, C, D, epsilon và cash_outflow phải được khai báo. cash_outflow={} là tuyên bố cấu trúc không có khoản tiền mới, nên ngân sách có thể chưa biết mà hành động đó vẫn đánh giá được trong thế giới giả định. Thiếu trường không được hiểu là {} hay 0.

Nếu cần chi tiền, từng đồng phải có số dư đã khai báo và hệ số đổi utility dương. Không biết ngân sách khác với ngân sách bằng 0. Ngân sách đã biết nhưng thiếu làm hành động không khả thi; ngân sách chưa biết làm kịch bản chưa sẵn sàng.

Không nhận VP làm đơn vị tiền hoặc utility. Không cộng trực tiếp utility cá nhân để quyết định ưu tiên ngân sách. Bộ kiểm dùng số liệu tiền minh họa, không báo giá tấn công USD tại Decentraland.

## Chân trời và chi phí chìm

Utility so sánh tại cùng lượt, cùng trạng thái cơ sở và cùng thước đo. Phí đã trả ở lượt trước không bị trừ lại trong KEEP; cash_outflow của WAIT/KEEP buộc rỗng trong phạm vi này. resource_cost_utility nếu khai báo là chi phí đánh giá cho hành động hiện tại, không phải ghi lại toàn bộ chi phí quá khứ.

Chưa có vay, thu hồi tài sản, ký quỹ, thu nhập tương lai hoặc vốn đỉnh đa thời điểm. Giao diện tài khoản/chuyển đổi cho phép phát triển tiếp nhưng các quy tắc lịch tiền tổng quát vẫn phải tuân Chương 3 khi bổ sung. Không dùng kỳ vọng lợi ích để tự tài trợ một khoản chi hiện tại.

## Kiểm tra đại số

Ví dụ thuần kiểm thử: v(good)=8, v(bad)=−4; mu=(1/4,3/4); C=1, D=2; phí một đơn vị tiền và lambda=2. Utility bằng −6. Số này chỉ kiểm đơn vị và kỳ vọng, không mô tả ví thật. Các phép utility dùng hữu tỷ, các số dư dùng Decimal; kết quả làm tròn hiển thị không quyết định lựa chọn.
''')
    render('INFORMATION_AND_SCHEDULING.md',r'''
# Thông tin và lịch quyết định

## Giao diện kiểm soát

decide chỉ nhận một decision_view, không nhận world, raw metadata, archive hoặc retained votes. View lấy thông tin cơ bản từ agent_view của 4.1.1, rồi thêm quyền/VP, utility, epsilon, tiền và chính sách đã khai báo trong lớp kịch bản.

View gồm lựa chọn của proposal, cửa sổ, thời gian hiện tại, choice riêng hiện hành, số dư chung trước lô, tham số cá nhân và belief profile đang nhận biết. Không có danh sách người sẽ tham gia, scores cuối, official outcome, kết quả thực thi, Gini/HHI hoặc lịch phiếu thật. Chỉ profile hiện hành được cung cấp, không phải các profile tín hiệu tương lai.

VP và quyền kịch bản chỉ dùng trong scope thời gian đã kiểm. Dữ liệu retained trong A không được dùng làm đầu vào hành vi B. 6.004 địa chỉ hồi cứu chưa là quần thể dự báo; kịch bản phải liệt kê context và giai đoạn riêng.

## Tín hiệu chung tối thiểu

Signal có signal_id, snapshot_id, published_at, received_at, priority, tag, source_id và basis=SCENARIO_ASSUMPTION. Tag không chứa một bảng điểm hay outcome đã biết. Mỗi context trong scope phải có profile phản ứng cho tag đó.

Để dùng ở giây t phải có published_at<=received_at<t. Nhận đúng giây quyết định chưa đủ; tác tử nhìn trạng thái trước lô. Nhận mới có thể tạo lượt review ở giây kế tiếp nếu bật chính sách.

Signal là giả định ngoại sinh, không tuyên bố lịch công khai lịch sử đã xác minh. Nếu cần phản ứng với tally tương lai, phải bổ sung cơ chế phát/nhận có độ trễ đúng, không đọc trực tiếp world.totals hoặc dùng final labels.

## Nhiều tín hiệu

Profile hiện hành theo tín hiệu đã nhận mới nhất, rồi priority khai báo. Hai tag xung đột cùng thời điểm và cùng priority bị từ chối, không để thứ tự CSV chọn ngầm. Tín hiệu cùng tag không tạo hai lần chi phí ở cùng giây.

Không có học tham số tự động. Thông tin mới chỉ chọn một belief profile được khai báo trước; không suy sở thích từ phiếu đã thấy và không điều chỉnh xác suất theo nhãn cuối.

## Lịch xử lý

1. Tạo hợp decision_times và các lượt review hợp lệ; loại trùng theo context–giây.
2. Đặt đồng hồ, kiểm môi trường đang mở trong scope.
3. Chụp view cho mọi context của giây đó, trước mọi cập nhật phiếu và tiền.
4. Gọi hàm quyết định thuần từ những view đã chụp.
5. Kiểm tổng chi theo principal và đồng tiền; xử lý xung đột bằng chính sách công bố.
6. Commit cả lô, lưu hành động đề nghị/thực hiện và nguyên nhân; kiểm bất biến.
7. Sau hạn đóng của tập scope, tính outcome bằng govern của Baseline; execution vẫn chưa biết.

Sắp mã ví để xuất trace ổn định không tạo ưu thế thông tin. Thay cấu trúc dòng context không đổi kết quả. Không có tác tử nhìn hành động của tác tử khác trong cùng giây. Khi hành động đã commit ở giây trước, actor có thể biết choice riêng và số dư tài khoản chung mới; không mặc định biết toàn bộ các phiếu khác.

## Mức bảo đảm

Đây là hợp đồng kiến trúc và kiểm thử, không phải sandbox bảo mật chống người viết Python truy cập thuộc tính nội bộ. API khởi tạo không đổi; adapter quản lý đồng hồ của mode B và chỉ cập nhật phiếu giả định trong scope. advance_before của mode A vẫn giữ nguyên ngữ nghĩa replay.
''')
    render('BEHAVIOR_INPUT_CONTRACT.md',r'''
# Hợp đồng dữ liệu và cấu hình

## Hai đầu vào

BehaviorSession nhận một InitializedWorld B chưa có phiếu và không có hàng đợi retained events, cùng một behavior config. Không nhận mode A, không dùng registry như bằng chứng eligible và không đọc archive để sinh sở thích.

CLI mặc định chỉ dựng một bundle tổng hợp qua build_world cũ. source_label=SYNTHETIC_TEST_ONLY; các proposal/agent của bundle là fixture, không phải proposal/ví được nhận diện là thao túng. Để gắn một world B khác, dùng API và cấu hình scope đầy đủ; nhiệm vụ này chưa chạy world của 6.004 ví.

## Schema gốc của behavior config

scenario_id, data_label, seed, allow_assumed_rights, information_policy, budget_conflict_policy, transfers_policy, positive_vp_policy, contexts, signals là các khóa bắt buộc, không nhận khóa ngoài.

data_label phải là SYNTHETIC_TEST_ONLY hoặc DECLARED_SCENARIO_NOT_FORECAST. Seed là số nguyên và khớp world, nhưng chưa có RNG. information_policy là EXOGENOUS_TAGS_STRICT_RECEIPT; transfers_policy là NONE_BASELINE; budget_conflict_policy là CANCEL_ALL_SPENDING_OF_OVERBOOKED_PRINCIPAL.

positive_vp_policy phải là REQUIRE_POSITIVE_VP_FOR_ACTIVE_BALLOT. Đây là giả định hành vi của bộ cơ sở, không sửa điều kiện replay cho phiếu 0 VP lịch sử.

## Mỗi context ví–đề xuất

| Nhóm | Trường bắt buộc |
| --- | --- |
| Định danh và nguồn | wallet_id, snapshot_id, basis=SCENARIO_ASSUMPTION |
| VP và quyền | vp, components, network, snapshot_block, scenario_rights, can_replace |
| Thời gian | valid_from, valid_until, decision_times, review_on_signal |
| Đánh giá | epsilon, utility_unit, utility_scope, values, cash_to_utility, profiles |

Wallet/proposal phải tồn tại và cặp duy nhất. Network/block đúng metadata; components kịch bản cộng chính xác thành VP. UNKNOWN ở quyền là đầu vào thiết yếu còn thiếu, DENIED là biết không được thực hiện. GRANTED cần allow_assumed_rights=true. Mọi quyền vật lý vẫn UNVERIFIED.

Quyền hiện có trong layer bằng chứng không bị nâng cấp bởi config. Nếu VP của trạng thái đã khởi tạo khác VP kịch bản thì từ chối. Không tự suy VP từ retained votes hoặc cộng thêm delegation.

## Profiles và utility

Mỗi profile cung cấp đủ WAIT, KEEP:k, VOTE:k, REPLACE:k cho mọi k. Mỗi action có đúng beliefs, resource_cost_utility, risk_loss_utility, cash_outflow. Beliefs phủ mọi state trong values, không âm và tổng chính xác bằng 1. C/D không âm. Giá trị state có thể âm.

utility_scope là một trong hai diễn giải đã công bố ở UTILITY_INTEGRATION. Đơn vị utility phải khai báo; không được là VP. cash_outflow={} là tuyên bố không có tiền mới; nếu có tiền dương cần số dư và cash_to_utility từng đồng, không giả đồng thiếu bằng 0. WAIT/KEEP không có dòng tiền mới trong bộ cơ sở.

Có thể nhập hữu tỷ như "1/3" cho xác suất/utility. VP, tiền và tài khoản cần thập phân hữu hạn; tín hiệu/choice không nhận số thực làm timestamp hoặc index. Không có ngầm định epsilon, C, D hoặc mu.

## Sẵn sàng và từ chối

Sai schema, thiếu utility/epsilon/quyền, sai thời gian/chain/block, thiếu tiền cho khoản cần biết hoặc thiếu profile tín hiệu làm NotReady. Số dư đã biết nhưng không đủ không làm biến mất cả kịch bản: hành động cần tiền đó INVALID, vẫn có thể đánh giá cơ sở hoặc phương án khác.

READINESS.json ghi ready và issues. CLI không chạy khi blocked. Khi kiểm lại một cấu hình lỗi, các kết quả dẫn xuất của lần chạy cũ trong đúng output folder được dọn để tránh hiểu nhầm là kết quả mới. Không đụng dữ liệu các chương trước.

## Đầu ra và giới hạn

CONFIG giữ khai báo; EVIDENCE_LAYER giữ lớp chứng cứ; DECISION_VIEWS là view đã cấp; DECISION_HISTORY có mọi U/Delta U/F, candidate/committed action và lý do; FINAL_BALLOTS và SUMMARY là kết quả fixture; OUTPUT_MANIFEST kiểm hash.

Mọi đầu ra có data_label, physical_rights và empirically_validated phù hợp. Không báo tỷ lệ dự báo, tỷ lệ tấn công hoặc chi phí tấn công USD. Source audit đọc hồ sơ cũ để kiểm truy xuất, không làm chúng trở thành thông tin tác tử.
''')
    render('BEHAVIOR_VALIDATION.md',r'''
# Kiểm chứng luật hành vi

## Phạm vi

Đã chạy @@NEW_TESTS@@ kiểm thử hành vi và @@OLD_TESTS@@ kiểm thử hồi quy khởi tạo, không lỗi/thất bại. Không sửa module/API, dữ liệu hoặc báo cáo cũ. Xem VERIFICATION.json và hai TEST_LOG/INITIALIZATION_REGRESSION_LOG.

Có ba mức phải phân biệt: kiểm logic toán học và điều kiện; kiểm tích hợp với engine/khởi tạo; kiểm phù hợp thực nghiệm. Hai mức đầu đã thực hiện trong phạm vi bên dưới. Mức thực nghiệm về động cơ ví thật chưa thực hiện.

## Fixture tổng hợp

Chỉ có bốn tác tử tổng hợp, hai proposal và năm context. Tất cả quyền, VP, utility, epsilon, lịch và tín hiệu là khai báo kiểm thử. Không lấy choice thực để tạo sở thích.

| Kết quả fixture | Giá trị |
| --- | ---: |
| Lượt quyết định | @@DECISIONS@@ |
| Bỏ phiếu lần đầu | 3 |
| Thay phiếu | 1 |
| Giữ phiếu | 2 |
| Chờ/không tham gia | 3 |

Proposal SYNTHETIC_BINARY có vector cuối [10,3], hai phiếu và ngưỡng 10. SYNTHETIC_MULTI có ba lựa chọn for/against/invalid, vector [6,0,0], một phiếu và ngưỡng 5. Cả hai cho ACCEPTED theo đúng rule ứng viên lấy từ catalog. Đây là kết quả kiểm phần mềm, không phải hai proposal Decentraland hoặc đánh giá token-weighted voting ở 4.2.1.

## Những trường hợp được kiểm

Lợi ích dương/âm; hòa giữa lựa chọn; Delta U đúng epsilon; quyền bị từ chối hoặc thiếu; VP 0; chính sách không cho dùng quyền giả định; thiếu budget so với budget không đủ; nhận tín hiệu và không nhận sớm; thay phiếu được phép/bị cấm; ba choices; threshold equality; nhiều ví dùng chung tiền; input order; thiếu cấu hình, sai network/block và dấu đơn vị.

Một kiểm hand calculation cho utility bằng −6 từ phân phối và chi phí đã khai báo. Trace được kiểm không chứa nhãn cuối hoặc retained oracle để chọn hành động. Thay scores/nhãn hành chính không đổi lựa chọn cơ sở. VP khi thay được trừ trước/cộng sau và số phiếu giữ nguyên.

## Đồng thời và tài khoản

Khi hai ví cùng principal cùng muốn chi vượt tiền trước lô, cả hai hành động cần tiền bị hủy theo chính sách. Khi đủ tiền, chi đúng tổng thực hiện, không nhân ngân sách. Các view của một giây đều chụp trước commit; đảo thứ tự contexts không đổi kết quả.

Ngân sách thiếu giữ null khi hành động không cần tiền theo khai báo. Nếu cần tiền mà thiếu đồng hoặc không có số dư, readiness từ chối. Không lấy VP làm tiền.

## Tái lập và toàn vẹn

Chạy lại fixture với socket bị chặn cho @@FILES@@ tệp giống byte. @@PROTECTED@@ tệp trước nhiệm vụ giữ nguyên hash. Seed 19 được lưu; không sử dụng RNG, không Monte Carlo. INPUT_AUDIT ghi hồ sơ đã đọc.

## Những giới hạn chưa được kiểm chứng thực nghiệm

Chưa biết sở thích, ngân sách, quyền mới, niềm tin hoặc phản ứng thật. Chính sách tín hiệu, lịch, epsilon và điều kiện VP dương đều là giả định. Chưa có mạng xã hội, phản ứng nội sinh theo tally, tín dụng hoặc giao dịch chiến lược. Không báo accuracy, causal effect hoặc xác suất tấn công.

Có thể chuyển sang thiết kế 4.2.1 có điều kiện sau khi chốt cohort, rule, quyền và cấu hình; chưa thực hiện thí nghiệm so sánh của mục đó. Trước mô phỏng tấn công còn cần payoff, nguồn lực, kênh huy động, cam kết, thông tin, phản ứng và định nghĩa thành công riêng.
''')
    render('CH4_4_1_2_REPORT_DRAFT.md',r'''
# 4.1.2. Luật hành vi của các tác tử

Mục này nối bộ khởi tạo với quy tắc ra quyết định biểu quyết cơ sở. Bốn nội dung được đặc tả là tham gia hay chờ, lựa chọn phương án, thời điểm quyết định và đánh giá lại khi nhận thông tin. Các quy tắc có thể thực thi và được kiểm trên dữ liệu tổng hợp nhỏ; kết quả chưa xác nhận động cơ của ví thật tại Decentraland.

### Lớp bằng chứng và lớp kịch bản

Khung khởi tạo có 6.004 ví từng xuất hiện nhưng chưa xác định toàn bộ quyền và sở thích trước từng cuộc bỏ phiếu. Vì vậy mô hình giữ nguyên lớp bằng chứng, đồng thời bổ sung lớp kịch bản khai báo theo ví, proposal và khoảng thời gian. Quyền được cho phép trong kịch bản không tự trở thành quyền thực tế đã xác minh. Thiếu VP, utility hoặc quyền thiết yếu làm kịch bản chưa sẵn sàng, không được tự thay bằng 0.

Mỗi kịch bản phải công bố quần thể và lịch đánh giá riêng. Bộ luật không tự dùng danh sách người từng tham gia làm quần thể eligible biết trước. Cũng không suy vai trò tấn công hoặc sở thích từ lượng VP và choice quan sát.

### Hành động và lợi ích tăng thêm

Tác tử chưa có phiếu so sánh chờ với việc bỏ phiếu cho một lựa chọn hợp lệ. Tác tử đã có phiếu so giữ hiện trạng với thay sang lựa chọn khác nếu được phép. Không tham gia khác chọn Abstain; không mặc định mọi proposal chỉ có Yes và No.

Kế thừa Chương 3, tác tử đánh giá:

$$
\Delta U_i(a;a_0)=U_i(a)-U_i(a_0).
$$

Trong đó a0 là chờ hoặc giữ phiếu hiện hành tại cùng thời điểm. Utility được tính từ giá trị trạng thái và niềm tin chủ quan đã khai báo, trừ chi phí và tổn thất theo đúng đơn vị. Bản cơ sở không có chuyển giao chiến lược; chi phí tiền nếu có được đổi sang đơn vị lợi ích riêng bằng hệ số công bố, không dùng VP như tiền.

Tác tử chỉ chọn một hành động tốt nhất trong tập khả thi nếu cải thiện vượt epsilon_i. Tại bằng ngưỡng, giữ cơ sở. Nếu nhiều lựa chọn cùng tốt nhất và đều vượt ngưỡng, dùng thứ tự choices trong metadata. Epsilon_i là ngưỡng cảm nhận, không bị trừ thêm như một khoản chi. Các giá trị bằng 0 trong fixture được khai báo là giả định kiểm thử, không được gọi là ước lượng thực nghiệm.

Một mô hình cơ sở có thể định giá giá trị biểu đạt của lựa chọn, nhờ đó không cần tự gán xác suất thực thi khi dữ liệu chưa đủ. Nếu dùng niềm tin về outcome hoặc thực thi, cấu hình phải định nghĩa trạng thái và phân phối tương ứng. Chương trình không lấy kết quả đã biết để tạo xác suất hay xác nhận chính lựa chọn đó.

### Khả thi và nguồn lực

Hành động phải đúng cửa sổ, choices, snapshot và quyền kịch bản; thay phiếu còn cần cho phép riêng. Bộ cơ sở yêu cầu VP dương cho hành động bỏ phiếu mới theo chính sách đã khai báo, không khẳng định đây là quy tắc cấm phiếu 0 VP của hệ thống thật. Khi quyền hoặc tiền còn thiếu, kịch bản phải giải quyết trước chạy.

Ngân sách được quản lý chung theo principal, không cấp lại theo ví hoặc proposal. Chi phí tiền được kiểm từng đồng. Nếu một hành động không có dòng tiền mới, cấu hình phải nói rõ; ngân sách chưa biết vẫn giữ trống. Khi nhiều ví cùng dùng một tài khoản và tổng chi đồng thời vượt tiền, toàn bộ hành động cần tiền của chủ thể đó trong lô được hủy theo chính sách công bố. Việc này tránh dùng thứ tự xử lý để tạo ưu tiên ngầm và không phải một nghiệm tối ưu phân bổ vốn.

### Thời gian và phản ứng thông tin

Tác tử quyết định ở các thời điểm đã khai báo, không sớm hơn start hoặc muộn hơn end. Tín hiệu chỉ được dùng sau thời điểm nhận. Các quyết định cùng giây cùng dựa trạng thái trước lô; sau khi tất cả chọn mới cập nhật phiếu và tiền.

Phản ứng tối thiểu là chuyển sang một belief profile đã khai báo khi nhận tín hiệu chung giả định. Nếu bật đánh giá lại, một lượt được tạo ở giây kế tiếp khi còn trong cửa sổ. Đây chưa là mô hình học hoặc mạng ảnh hưởng thực. Chưa có phản ứng nội sinh với tally công khai, nên không cho luật đọc toàn bộ bảng điểm trong môi trường.

Hàm quyết định chỉ nhận giao diện thông tin được kiểm soát. Không có lịch phiếu tương lai, danh sách người sẽ tham gia, nhãn Governance cuối hoặc kết quả thực thi trong giao diện đó. Lựa chọn đã quan sát không được dùng để suy sở thích rồi đánh giá dự báo trên cùng lựa chọn.

### Cập nhật và kiểm chứng

Một phiếu mới thêm Total VP đúng một lần. Khi thay phiếu, đóng góp cũ bị trừ trước khi thêm đóng góp mới; số phiếu không tăng và component delegation không cộng thêm. Outcome cuối được tính bằng lõi Governance ứng viên của Baseline, còn thực thi giữ trạng thái chưa biết.

Trên fixture bốn tác tử và hai proposal, hệ thống ghi @@DECISIONS@@ lượt quyết định, gồm ba bỏ phiếu lần đầu, một thay phiếu, hai giữ và ba chờ. Đây chỉ là kiểm phần mềm tổng hợp, không là dữ liệu hành vi thực hoặc kết quả so sánh ở 4.2. Có @@NEW_TESTS@@ kiểm thử hành vi và @@OLD_TESTS@@ kiểm thử hồi quy khởi tạo đạt. Chạy lại có cùng cấu hình và seed cho @@FILES@@ tệp giống byte, không sử dụng Monte Carlo.

Khung hiện cho phép tác tử tự chọn và cập nhật phiếu trong thế giới giả định đã khai báo. Có thể tiếp tục thiết kế baseline ở 4.2.1, nhưng trước khi chạy cần chốt quần thể, quyền VP, utility, ngân sách, tín hiệu, lịch và quy tắc cơ chế phù hợp. Các giao diện hành vi chiến lược còn để trống; chưa mô phỏng tấn công, hối lộ, vay chớp nhoáng hoặc phòng thủ. Kiểm thử thành công chưa đủ để gọi mô hình hành vi được kiểm chứng thực nghiệm.
''')
    render('README.md',r'''
# Mục 4.1.2: luật biểu quyết cơ sở

Python 3.10 trở lên, chỉ thư viện chuẩn và module của 4.1.1/Baseline. Chạy từ D:\BTL_Blockchain.

~~~powershell
python chapter4/behavior/run_behavior.py
python chapter4/behavior/verify.py
python chapter4/behavior/render_reports.py
~~~

Lệnh đầu chạy duy nhất fixture SYNTHETIC_TEST_ONLY nhỏ; không nạp hành vi từ retained votes. verify chạy kiểm thử mới và hồi quy 4.1.1, chạy lại có mạng bị chặn vào replay_outputs và đối chiếu byte. render_reports tạo lại tài liệu từ kết quả đã kiểm.

~~~powershell
python chapter4/behavior/run_behavior.py --config chapter4/behavior/outputs/CONFIG.json --check-only --output chapter4/behavior/readiness_only
~~~

CONFIG.json có đủ tham số minh họa để xem schema. Không dùng các giá trị minh họa làm tham số ước lượng Decentraland. Output phải trong thư mục nhiệm vụ. --check-only chỉ kiểm chuẩn bị, không tạo kết quả hành vi. READINESS.ready=false nghĩa chưa chạy; kết quả dẫn xuất cũ trong đúng output folder được xóa để tránh nhầm lần chạy.

## API với bộ khởi tạo

BehaviorSession(initialized_world_B,behavior_config) nối world B đã có; API 4.1.1 không thay đổi. Cấu hình scopes phải đầy đủ, không mặc định tất cả 6.004 ví có quyền. run chỉ thực hiện một lần; decide là hàm thuần nhận decision_view, không nhận world hoặc archive.

CLI hiện chỉ dựng thế giới tổng hợp qua build_world cũ. Chưa có CLI chạy hàng loạt ví lịch sử, chưa đánh giá dự báo hoặc chạy các nhóm thí nghiệm 4.2. Adapter dùng được cho một world B khác khi có cấu hình scope đầy đủ, nhưng không tự điền những quyền/utility còn thiếu.

## Tệp bàn giao

- BEHAVIOR_MODEL, DECISION_RULES và UTILITY_INTEGRATION mô tả động cơ, hành động và đơn vị.
- INFORMATION_AND_SCHEDULING mô tả cửa sổ thông tin và commit đồng thời.
- BEHAVIOR_INPUT_CONTRACT là schema và tiêu chí ready.
- BEHAVIOR_VALIDATION và VERIFICATION.json ghi bằng chứng, không chứng nhận thực nghiệm.
- CH4_4_1_2_REPORT_DRAFT là bản thảo khoa học.

outputs có CONFIG, READINESS, INPUT_AUDIT, SUMMARY, DECISION_HISTORY, DECISION_VIEWS, EVIDENCE_LAYER và FINAL_BALLOTS; OUTPUT_MANIFEST khóa @@FILES@@ tệp. Rational utility được lưu dạng phân số khi cần; tiền/VP giữ thập phân, null vẫn là thiếu.

PROTECTED_INPUTS khóa @@PROTECTED@@ tệp cũ. Không sửa dữ liệu hoặc báo cáo Chương 3, module khởi tạo hay kết quả cũ. Hai log kiểm thử là TEST_LOG.txt và INITIALIZATION_REGRESSION_LOG.txt.

## Những phần chưa triển khai

Không có hành vi tấn công/phòng thủ, chuyển giao, vay, mua quyền, mạng xã hội hoặc Monte Carlo. strategic_extension chỉ là điểm mở và báo NotImplementedError. Tham số sở thích, epsilon, lịch, niềm tin và quyền của fixture là giả định. Muốn mô phỏng tấn công cần một đặc tả và kiểm riêng, không chỉ đổi nhãn vai trò.
''')
    print('Rendered eight behavior Markdown deliverables.')


if __name__=='__main__':
    main()
