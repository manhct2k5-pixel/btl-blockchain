# Ký hiệu và công thức thống nhất

Đây là quy ước biên tập cho bản CH3_MASTER_DRAFT. Không đổi tên cột dữ liệu hay sửa mã nguồn cũ. Ký hiệu trong nguồn được ánh xạ khi viết báo cáo; người chạy lại vẫn sử dụng schema gốc.

## 1. Bảng ký hiệu

| Ký hiệu bản thống nhất | Nghĩa | Miền, đơn vị | Ánh xạ hoặc giới hạn |
| --- | --- | --- | --- |
| i, j, k | Tác tử, đề xuất, lựa chọn | Chỉ số | Ví là đơn vị quan sát, chưa phải người |
| t, u, H | Thời điểm quyết định, thời điểm trong lịch tiền, chân trời | Cùng hệ thời gian đã công bố | Không chọn H để bỏ nghĩa vụ cuối kỳ |
| mathcal K_j | Danh sách lựa chọn đúng metadata | Tập/chỉ số lựa chọn | K_j cũ ở 3.1; khác vốn K_cap |
| mathcal R | Tập người nhận trong trò chơi | Hữu hạn | N cũ là tập ở 3.2, không dùng N cho cả tập và số phiếu |
| n_j | Số phiếu hợp lệ | Số nguyên không âm | count/N của mô hình VP |
| w_ij | VP phiếu hoặc quyền đã xác minh | VP không âm | Không bằng tiền hoặc mọi tài sản ví |
| S_jk, V_j | VP từng lựa chọn gốc; tổng đã tham gia | VP | V_j là tổng, không payoff nền |
| omega_j | VP winner theo phép chiếu Governance | VP | Có thể khác max raw khi quy tắc chiếu khác |
| Theta_j | Ngưỡng thông qua | VP không âm nếu xác minh | T_j/threshold trước đây |
| r_j, mathfrak m | Quy tắc ứng viên; nhãn cơ chế | Nhãn/commit | Không dùng m cho cả cơ chế và margin |
| y_j, e_j | Outcome phiếu; kết quả thực thi | Trạng thái | Không đồng nhất |
| a, a0 | Hành động; không dùng thao túng đang xét | Phần tử tập hành động | a0 có thể vẫn vote cơ sở |
| mathcal I_ij(t) | Thông tin được biết | Tập thông tin | I cũ, khác I_cash |
| z, mu_ij | Trạng thái cuối; niềm tin trên trạng thái | z thuộc Omega; mu>=0, tổng=1 | Bao gồm danh mục/nợ nếu hạch toán tài sản |
| chi_i, lambda_i | Đơn vị lợi ích riêng; hệ số đổi tiền tuyến tính | chi_i; chi_i/tiền | Chưa gán giá trị thực nghiệm |
| v, C, D | Giá trị gộp; chi phí nguồn lực; tổn thất còn lại | chi_i; C,D>=0 | C không phải mẫu C; D không lặp phần đã trong thu hồi |
| tau_in/out, mathcal T_in/out | Chuyển giao bằng tiền; chuyển giao utility | Tiền; chi_i | mathcal T=lambda_i tau nếu tuyến tính |
| b_i(t), ell_i | Ngân sách tiền tự có; tiền tự do | Đồng thanh toán cụ thể | Không dùng block snapshot làm b |
| O_i, I_cash, L_loan, E_lock | Chi lũy kế, thu không vay, vay giải ngân, tiền khóa | Tiền không âm | L_loan không phải tổn thất L ở công thức rút gọn |
| K_cap | Vốn tự có đỉnh cần thiết | Tiền không âm | K_i của BUDGET_MODEL |
| P_l, R_l | Tiền mua mới; thu hồi cuối kỳ | Cùng tiền | R chưa trừ phí được ghi riêng |
| c_asset, g_asset | Mất ròng và lãi tài sản | Tiền không âm | Tổng hợp chi phí phải quy đổi |
| epsilon_i | Ngưỡng cải thiện cảm nhận | chi_i, không âm | Không phải phí; khác Nash chính xác |
| h, mathcal H_F | Hợp đồng; menu đã xác minh hữu hạn | Nhãn/tập hữu hạn | Gồm không đề nghị |
| eta_i, x_i | Tiền đề nghị mới; hành động nhận | Tiền không âm; {0,1} | x không dùng cho trạng thái thực thi |
| mathcal V_i, d_i | Payoff trước tiền mới; phần đánh đổi của người nhận | chi_i | V_i,d_i của PAYOFF_MODEL; không phải VP |
| g_A, f_A, Gamma_A | Tăng giá trị trước tiền, phí mở, payoff tăng thêm bên A | chi_A | f_A khác f_cash có đơn vị tiền |
| nu | Lượng VP thay đổi trong S1/S2 | VP không âm | x cũ của margins.py |
| zeta_i | Chọn phiếu nguyên vẹn trong S3 | {0,1} | Không dùng z vì z là trạng thái cuối |
| M_js | Tối thiểu/infimum/cận trên theo trạng thái | VP | m trước đây; status quyết định cách đọc |
| q_js, h_js | M/V; M/Theta khi áp dụng | Không đơn vị | q không phải xác suất rủi ro của công thức sơ khởi |
| delta_j | (Theta−omega)/Theta | Có dấu, không đơn vị | Không dùng d_i của người nhận |
| p_ij | w/V khi V>0 | Tỷ trọng | Không phải xác suất thành công |
| A, B, C viết “mẫu” | Mức chứng cứ và mẫu chọn | Tập đề xuất | Khác người A, lợi ích B_i hoặc chi phí C_ij |

Các chữ thường/hoa và chỉ số không được bỏ khi chuyển sang Word/LaTeX vì chúng mang ý nghĩa phân biệt. Trong văn xuôi luôn viết “mẫu B”, “chi phí C”, “bên A” khi có thể nhầm.

## 2. Công thức cốt lõi và kiểm đơn vị

| Số bản chính | Nội dung | Kiểm toán |
| --- | --- | --- |
| 3.1 | Kỳ vọng v+T_in−T_out−C−D | Mọi hạng trong ngoặc là chi_i; mu không đơn vị |
| 3.2 | Delta U=U(a)−U(a0) | Cùng thời điểm, thông tin, đơn vị, chân trời; không đặt U(a0)=0 |
| 3.3 | ell=b+I+L−O−E; K_cap=max[O+E−I−L]_+ | Tiền cùng đồng; K_cap<=b tương đương ell>=0 trên một đường |
| 3.4 | c=[P−R]_+, g=[R−P]_+; g−c=R−P | Hai phần không âm, có cùng đơn vị; lãi vào v, lỗ vào C |
| 3.5 | Payoff E bằng payoff nền cộng/trừ lambda eta x | Tiền đi một lần giữa hai bên, quy đổi utility riêng |
| 3.6 | Hiệu người nhận=lambda eta−d | Ngưỡng d/lambda chỉ cố định nếu d,lambda không phụ thuộc tiền |
| 3.7 | Không có lệch đơn phương sinh lợi | Chỉ trò chơi con sau h; chưa là toàn bộ SPNE |
| 3.8 | Gamma_A theo phản ứng ở menu hữu hạn | f_A đã là utility; không trừ lại phí trong payoff nền |
| 3.9 | Trạng thái scoring không đổi suy Delta w=0 | Điều kiện kỹ thuật, không khẳng định mọi runtime |
| 3.10 | Min theo hướng của inf miền đạt outcome | Tập rỗng không được gán 0; S3 là bài toán rời rạc riêng |

## 3. Dạng đầy đủ cần giữ ở phụ lục kỹ thuật

Một dạng chi phí đúng đơn vị là:

$$
C_{ij}=\lambda_i\left[\sum_l c_l^{asset}
+F^{trade}+F^{net}+F^{loan}+F^{hire}+F^{coord}+O^{opp}\right]+C^{effort}_{ij}.
$$

Các nhóm không trùng; các F và O_opp bằng tiền, C_effort bằng chi_i. Lãi tài sản là \(\lambda_i\sum_l g_l^{asset}\) trong v. Không tính cơ hội vốn hai lần qua lợi ích phương án a0 hoặc chiết khấu. Các công thức lãi theo tích phân chỉ dùng nếu đúng đơn vị thời gian và hợp đồng, xem COST_MODEL C5–C6.

Dấu max trong vốn đỉnh của bản chính dùng lịch hữu hạn các sự kiện thanh toán. Nếu mở rộng sang lịch liên tục tổng quát chưa chứng minh đạt cực trị, phải dùng supremum và kiểm điều kiện hữu hạn trước khi áp dụng. Đây là giới hạn toán học của việc mở rộng, không thay lịch hay kết quả đã có.

Với E, một điều kiện bảo chứng đơn giản khi không có tài trợ khác là \(f^{cash}+\sum_i\eta_i\le b_A\). Không thay tổng nghĩa vụ đồng thời bằng kỳ vọng tiền trả. Đây không thay thế kiểm lịch tiền đầy đủ.

Nash hỗn hợp của ví dụ E6 có:

$$
u_1=v_1x_1x_2-k_1x_1,\quad
u_2=-L_2x_1x_2+k_2x_2,\quad
0<k_1<v_1,\quad0<k_2<L_2,
$$

$$
\alpha_1^*=k_2/L_2,\qquad \alpha_2^*=k_1/v_1.
$$

Kiểm bốn góc đều có lệch sinh lợi; ở hỗn hợp, người 1 thờ ơ vì alpha_2 v_1−k_1=0, người 2 vì k_2−alpha_1 L_2=0. Đây là trò chơi con minh họa, không là SPNE toàn trò chơi nếu chưa kiểm A; các tham số và xác suất không được gán cho ví thật. Ví dụ phối hợp E5 có hai cân bằng thuần theo điều kiện đã nêu ở nguồn, chứng minh không duy nhất.

Phản ví dụ tiền liên tục của 3.2.1 cần đủ \(d>0,f_A=0,g_A>\lambda_A d/\lambda_R\), trần tiền lớn hơn \(d/\lambda_R\) và cách chọn từ chối tại hòa. Với mọi đề nghị được nhận, tồn tại mức thấp hơn vẫn được nhận; với mọi đề nghị bị từ chối có một mức được nhận đem giá trị dương. Vì vậy không có cực đại dưới cách chọn đó. Nếu nhận tại hòa, kết luận không tồn tại này không áp dụng.

Gini và HHI của người đã tham gia:

$$
\mathrm{Gini}_j=\frac{2\sum_{i=1}^{n_j}i\,w_{(i)j}}{n_jV_j}
-\frac{n_j+1}{n_j},\qquad
\mathrm{HHI}_j=\sum_i(w_{ij}/V_j)^2.
$$

Gini dùng toàn bộ trọng số không âm, gồm số 0, không hiệu chỉnh về 1; HHI dùng thang 0–1. Khi V=0, cả hai không xác định. Không cộng cùng một ví qua snapshot rồi gọi là quyền tại một thời điểm.

Đường năng lực S1/S2 theo hạn mức b VP tương đối đạt mục tiêu nếu \(b>q_{js}\), hoặc \(b=q_{js}\) và ngưỡng được đạt. Ký hiệu b trong diễn giải này phải gọi rõ là hạn mức tương đối; nếu đưa công thức vào bản chính nên đổi thành \(\beta^{VP}\) để không nhầm ngân sách tiền b_i(t). Đường S2 chưa ràng buộc nguồn cung. Tại V=0 không có q; không gán trường hợp đó là an toàn.

## 4. Những khác biệt không được “thống nhất” bằng thay toán học

- Nghĩa vụ tiền dùng giá trị danh nghĩa đúng thời điểm; utility có quy đổi. Không ép thành cùng số.
- Bất đẳng thức yếu của phản ứng Nash khác dấu nghiêm ngặt của quy tắc giữ cơ sở khi hòa.
- Threshold equality khác hòa giữa lựa chọn, và cả hai khác dung sai đối chiếu Snapshot.
- Infimum không đạt không biến thành tối thiểu chỉ vì làm tròn để trình bày.
- Cận trên S3 không biến thành tối ưu hoặc tỷ lệ xấp xỉ có bảo đảm.
- Tối ưu lượng VP không phải tối ưu số ví. Chỉ sự tồn tại một phiếu hợp lệ đổi outcome mới chứng minh số ví tối thiểu bằng một.

Nguồn chi tiết: UTILITY_MODEL (1)–(6), BUDGET_MODEL B1–B4, COST_MODEL C1–C11, PAYOFF_MODEL P1–P8, EQUILIBRIUM E1–E8, margins.py và wallet_solver.py, analysis.py của 3.3.2.
