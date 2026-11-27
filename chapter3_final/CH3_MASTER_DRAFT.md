# CHƯƠNG 3. MÔ HÌNH VÀ PHÂN TÍCH THAO TÚNG BIỂU QUYẾT TẠI DECENTRALAND DAO

Chương này xây dựng mô hình quyết định của tác tử, phân tích các kịch bản tác động tới biểu quyết và sử dụng dữ liệu Decentraland DAO để đo độ nhạy của kết quả. Lập luận đi từ động cơ và tính khả thi tới cân bằng chiến lược, sau đó mới xem xét những thay đổi quyền biểu quyết có thể làm kết quả chuyển trạng thái. Trình tự này phân biệt một phương án có tác động về toán học với một hành động có thể thực hiện và có lợi về kinh tế.

Chương 3 phục vụ trực tiếp RQ2 về động lực kinh tế vi mô của thao túng biểu quyết. Các trạng thái, ràng buộc và kết quả định lượng đồng thời chuẩn bị đầu vào cho RQ3 về động lực học quy mô lớn và RQ4 về hiệu năng phòng thủ. Chương này chưa đưa ra kết quả mô phỏng hành vi hoặc thử nghiệm cơ chế phòng thủ.

Dữ liệu cung cấp địa chỉ ví, trọng số, lựa chọn và thời điểm của các phiếu còn được lưu. Những thông tin này không trực tiếp xác định sở thích, ngân sách, động cơ thao túng hoặc danh tính người điều khiển. Vì vậy, chương phân biệt quan sát dữ liệu, mô hình lý thuyết có điều kiện và phép tính phản thực tế trên quy tắc ứng viên. Mọi kết luận phải được đọc theo đúng lớp bằng chứng đó.

## 3.1. Thiết lập mô hình cơ sở

### 3.1.1. Không gian tác tử và Hàm lợi ích.

**Tác tử và môi trường.** Ký hiệu \(i\) là đơn vị quyết định mô hình và \(j\) là đề xuất được nhận diện bằng Snapshot ID. Khi liên kết dữ liệu, đơn vị quan sát là ví. Một ví chưa chắc là một cá nhân; nhiều ví cùng chủ hoặc một ví do tổ chức quản lý chưa được nhận diện. Mô hình tối thiểu sử dụng một lớp tác tử biểu quyết. Vai trò thao túng là nhãn giả định về mục tiêu và tập hành động, còn VP lớn là thuộc tính nguồn lực, không tự tạo thành một lớp có động cơ khác.

Môi trường giữ thời gian, nội dung đề xuất, các lựa chọn, snapshot và quy tắc kiểm phiếu. Giám sát trước hết là quy trình của môi trường. Chỉ khi phân tích quyết định giám sát có chi phí, nguồn lực và thẩm quyền riêng mới bổ sung tác tử giám sát tự chủ. Không suy nhãn thao túng từ VP lớn, ủy quyền, lựa chọn thiểu số hoặc sai khác với trạng thái chính thức.

Trạng thái tác tử gồm VP hợp lệ tại snapshot \(w_{ij}\), lựa chọn hiện hành hoặc chưa có phiếu, thông tin \(\mathcal I_{ij}(t)\), các tham số đánh giá chưa quan sát, ngân sách khả dụng và vai trò kịch bản. Danh sách lựa chọn \(\mathcal K_j\) giữ nguyên metadata. Không tham gia khác với chọn abstain; FINISHED là outcome của quy tắc, không phải một lựa chọn biểu quyết.

Các hành động cơ sở gồm chờ, tham gia bằng một lựa chọn hợp lệ và giữ phiếu hiện hành. Thay phiếu chỉ khả thi nếu quyền, thời hạn và cách tính trọng số được xác minh. Huy động hoặc tác động phiếu của người khác phải được đặc tả riêng; không mặc định có thể kiểm soát các ví đã quan sát.

**Tính khả thi và thông tin.** Mỗi hành động \(a\) có trạng thái \(F_{ij}(a,t)\) thuộc ba mức: hợp lệ, không hợp lệ và chưa xác minh. Chỉ hành động hợp lệ được đánh giá như phương án có thể thực hiện. Một điều kiện đã sai làm hành động không hợp lệ trong mô hình; dữ liệu còn thiếu làm kết quả chưa xác minh, không chứng minh hành động bị cấm ngoài thực tế.

Tập thông tin chỉ chứa dữ liệu được phép biết tại thời điểm quyết định và thông tin riêng đã khai báo. Không cho tác tử biết trước tổng VP cuối, những ví sẽ tham gia, lựa chọn tương lai hoặc kết quả thực thi. Phiếu cùng giây được xử lý theo lô nếu không có bằng chứng thứ tự chi tiết hơn. Dữ liệu chưa bao phủ mọi lần thay phiếu, nên sắp các phiếu còn lưu theo thời gian chưa phải tái dựng đầy đủ bảng điểm lịch sử.

**Hàm lợi ích.** Gọi \(z\in\Omega_j\) là trạng thái cuối, gồm outcome biểu quyết, thực thi và các biến kinh tế cần thiết. Mỗi tác tử sử dụng một đơn vị lợi ích \(\chi_i\), nhất quán trong mọi so sánh của chính tác tử đó:

$$
\bar U_{ij}(a\mid\mathcal I_{ij}(t),\mathfrak m)
=\sum_{z\in\Omega_j}\mu_{ij}(z\mid a,\mathcal I_{ij}(t),\mathfrak m)
\left[v_{ij}(z)+\mathcal T^{in}_{ij}(a,z)-\mathcal T^{out}_{ij}(a,z)
-C_{ij}(a,z)-D_{ij}(a,z)\right].
\tag{3.1}
$$

\(\mu_{ij}\) là niềm tin chủ quan không âm, tổng bằng một; \(\mathfrak m\) là nhãn cơ chế; \(v_{ij}\) là giá trị gộp của trạng thái; \(\mathcal T^{in/out}\) là chuyển giao đã quy về \(\chi_i\); \(C_{ij}\) là chi phí nguồn lực; \(D_{ij}\) là tổn thất còn lại chưa ghi ở khoản khác. Chuyển giao, chi phí và tổn thất không âm theo quy ước hạch toán. Giá trị \(v_{ij}\) có thể âm, không chứa các khoản đã trừ riêng. Nếu chuyển giao bằng tiền \(\tau\) được quy đổi tuyến tính thì \(\mathcal T=\lambda_i\tau\), với \(\lambda_i>0\) có đơn vị \(\chi_i\) trên một đơn vị tiền.

Công thức lấy kỳ vọng sau khi xác định lợi ích và chi phí từng trạng thái. Phí đã phát sinh có thể phải chịu dù mục tiêu thất bại. Khoản đã ghi theo \(z\) không được nhân xác suất lần thứ hai. Kỳ vọng tuyến tính là giả định trên thước đo đã chọn, chưa chứng minh mọi tác tử thực tế trung lập rủi ro. Lợi ích của các tác tử cũng không được cộng thành phúc lợi chung khi thiếu đơn vị so sánh.

Outcome từ phiếu và kết quả thực thi được giữ riêng. Nếu lợi ích chỉ phát sinh khi cả thắng phiếu và được thực thi, xác suất phù hợp là xác suất giao của hai sự kiện. Khi xác suất thắng dương, có thể viết giao thành xác suất thắng nhân xác suất thực thi có điều kiện trên thắng, không cần giả định độc lập. Trạng thái enacted hoặc giao dịch thành công chưa tự chứng minh tác tử nhận được lợi ích kinh tế mong muốn.

**Động cơ tăng thêm.** Phương án cơ sở \(a_0\) là không sử dụng hành vi thao túng đang xét; tác tử vẫn có thể bỏ phiếu thông thường. \(a_0\) không đồng nghĩa không tham gia, thất bại hoặc lợi ích bằng không:

$$
\Delta\bar U_{ij}(a;a_0)=\bar U_{ij}(a)-\bar U_{ij}(a_0).
\tag{3.2}
$$

Hai vế sử dụng cùng trạng thái đầu, thời điểm thông tin, đơn vị và chân trời đánh giá. Phản ứng người khác có thể khác khi hành động tạo tín hiệu khác; chúng phải được xác định bằng cùng quy tắc, không bị cố định thuận lợi cho bên thao túng. Chi phí chìm giống nhau ở hai vế triệt tiêu.

Mô hình hành vi sử dụng tập cân nhắc hữu hạn chứa \(a_0\). Tác tử chọn hành động có lợi ích tăng thêm lớn nhất trong các phương án hợp lệ khi giá trị đó vượt \(\epsilon_i\ge0\). Nếu không vượt, giữ cơ sở. Khi nhiều phương án cùng tốt nhất và đều vượt ngưỡng, ưu tiên giữ lựa chọn hiện hành, sau đó theo thứ tự đã công bố. \(\epsilon_i\) có đơn vị \(\chi_i\), không phải khoản chi phí để trừ lần nữa.

Đây là quy tắc hữu trí có giới hạn, chưa chứng minh cân bằng Nash. Khi thiếu utility, niềm tin hoặc chi phí, lựa chọn chưa xác định; không tự gán chi phí bằng không hoặc xác suất bằng một nửa. Phân tích quyết định vì vậy cần tiếp tục bằng ràng buộc nguồn lực.

### 3.1.2. Ràng buộc ngân sách và Hàm chi phí tấn công.

**Ngân sách theo thời điểm.** \(b_i(t)\) là tiền tự có khả dụng tại thời điểm đánh giá, sau nghĩa vụ đã cam kết, khác VP và lợi ích kỳ vọng. Khi một tác tử điều khiển nhiều ví hoặc tham gia nhiều đề xuất, phải dùng chung sổ nguồn lực, không cấp lại toàn bộ ngân sách cho mỗi đơn vị quan sát.

Trên chân trời \([t,H]\), xét lịch hữu hạn các sự kiện thanh toán. \(O_i(u)\) là tiền đã chi lũy kế, \(I_i^{cash}(u)\) là dòng vào không phải vay, \(L_i^{loan}(u)\) là vốn vay đã giải ngân và \(E_i^{lock}(u)\) là tiền còn thuộc tác tử nhưng đang khóa. Tiền tự do và nhu cầu vốn tự có lớn nhất là:

$$
\ell_i(u;a,z)=b_i(t)+I_i^{cash}(u;a,z)+L_i^{loan}(u;a,z)-O_i(u;a,z)-E_i^{lock}(u;a,z),
\qquad
K_i^{cap}(a,z)=\max_{u\in[t,H]}[O_i+E_i^{lock}-I_i^{cash}-L_i^{loan}]_+.
\tag{3.3}
$$

Các đại lượng trong (3.3) cùng đơn vị tiền. Trên một đường diễn biến, tiền tự do không âm mọi thời điểm tương đương \(K_i^{cap}(a,z)\le b_i(t)\). Nếu khẳng định khả thi tài chính có bảo đảm trong một tập đường đã công bố, điều kiện phải đúng với mọi \(z\) trong tập đó. Kỳ vọng dòng tiền không âm chưa bảo đảm thanh toán đúng hạn.

Tiền vay được ghi một lần vào dòng vào và trở thành nghĩa vụ hoàn trả. Khi thanh toán từ bảo chứng, tiền khóa giảm và tiền đã chi tăng cùng số tiền; không coi là hai khoản vốn độc lập. Mở khóa chỉ làm giảm tiền khóa, không tạo thêm dòng thu thứ hai. Thu hồi tài sản hoặc lợi ích dự kiến chỉ tài trợ nghĩa vụ sau khi thực sự sẵn có.

Với nhiều đồng tiền, kiểm lịch thanh toán riêng từng đồng hoặc có giao dịch chuyển đổi khả thi cùng tỷ giá, phí, độ trễ và thanh khoản. Tương đương USD không tự bảo đảm có ETH trả phí. Vay token hoặc NFT đòi hoàn trả đúng loại; tài sản khóa không đồng thời bảo đảm các nghĩa vụ vượt quyền. Khi còn nợ ở \(H\), phải ghi nghĩa vụ cuối kỳ hoặc kéo dài chân trời, không bỏ nợ khỏi phép tính.

**Chi phí ròng.** Vốn ứng trước khác phần mất ròng. Với tài sản mua mới, \(P_l(a)\) là tiền mua và \(R_l(a,z)\) là giá trị có thể thu hồi cuối chân trời, chưa trừ phí ghi riêng. Để giữ chi phí không âm mà không bỏ khả năng có lãi:

$$
c_l^{asset}=[P_l-R_l]_+,\qquad g_l^{asset}=[R_l-P_l]_+,
\qquad g_l^{asset}-c_l^{asset}=R_l-P_l.
\tag{3.4}
$$

Toàn bộ tiền mua thuộc lịch dòng tiền, nhưng chỉ phần mất ròng \(c_l^{asset}\) thuộc chi phí. Phần lãi \(g_l^{asset}\), sau quy đổi, thuộc giá trị tài sản trong \(v_{ij}\). Khi dùng cách này, \(z\) gồm cả danh mục và nghĩa vụ liên quan. Không cộng lại tiền bán vào chuyển giao hoặc cùng tổn thất tài sản vào \(D_{ij}\). Tài sản đã có trước hành động phải so với cùng tài sản ở \(a_0\); giá mua quá khứ không phải chi phí biên mới.

Chi phí nguồn lực có thể gồm phần mất ròng tài sản, phí thị trường, phí mạng thực có, lãi và phí vay, phí thuê quyền hợp lệ, dịch vụ phối hợp và chi phí cơ hội vốn tự có. Các khoản tiền được quy về \(\chi_i\) trước khi cộng với công sức cùng đơn vị. Vốn gốc vay rồi hoàn trả không phải lợi ích hay chi phí mất ròng. Không tính chồng chi phí cơ hội lên phần vốn đã ghi đủ lãi vay hoặc lên lợi ích thay thế đã nằm trong \(v(a_0)\).

Chuyển giao giữa tác tử nằm ở \(\mathcal T^{out}\) của bên trả và \(\mathcal T^{in}\) của bên nhận theo cùng sự kiện. Không thêm “chi phí hối lộ” vào \(C\) cho chính khoản đó. \(D\) chỉ chứa tổn thất chưa hạch toán ở khoản khác; chế tài và danh tiếng cần căn cứ, không thêm mức phạt tùy ý cho Decentraland.

**Quyền biểu quyết và định giá.** Khả thi tài chính chỉ là một phần của \(F\). Quyền vote phụ thuộc sở hữu, ủy quyền, strategy, chain, block và thời hạn. Mua tài sản sau snapshot không tự làm tăng VP hiện tại. Chuyển phiếu của ví đang có quyền là thay phân bổ, khác tạo thêm VP hợp lệ. Tổng VP đã bao gồm các component scoring; không cộng ủy quyền lần nữa.

Chỉ tính chi phí tiền khi đồng thời biết đúng tài sản hoặc quyền tạo VP, kênh huy động khả thi, giá và đơn vị, thanh khoản, chi phí cùng thu hồi, và sự phù hợp snapshot. Hồ sơ chưa thỏa đủ cho cuộc tấn công cụ thể. Giá MANA không phải giá chung của một VP; sổ lệnh năm 2026 không định giá thanh khoản năm 2021–2023. Các hàm chi phí được giữ ký hiệu, không gán mức USD thực nghiệm [DL1, DL2].

Một hành động có lợi ích kỳ vọng dương vẫn có thể thiếu vốn; đủ vốn cũng chưa bảo đảm quyền hợp lệ. Đây là cơ sở xây dựng trò chơi tác động phiếu.

## 3.2. Phân tích cân bằng

### 3.2.1. Cân bằng Nash trong kịch bản hối lộ công khai.

**Cấu trúc trò chơi.** Đây là mô hình lý thuyết có điều kiện, không phải giao dịch đã được xác nhận tại Decentraland. Bên đề nghị \(A\) chọn không đề nghị hoặc hợp đồng \(h\) trong menu hữu hạn \(\mathcal H_F\) đã kiểm nguồn lực và quyền. Người nhận \(i\in\mathcal R\) cùng quan sát hợp đồng rồi chọn \(x_i\in\{0,1\}\): giữ hành vi cơ sở hoặc thực hiện hành động được đề nghị. Người ngoài phản ứng theo quy tắc công bố trước. Vì chưa kiểm phản ứng tối ưu của toàn bộ người ngoài, cân bằng thuộc trò chơi rút gọn, không phải toàn DAO.

Mô hình chính, chế độ E, giả định tiền được bảo chứng và không thể đơn phương hủy. \(\eta_i\ge0\) được trả khi hành động cá nhân hợp lệ được kiểm chứng, kể cả khi outcome chung không đạt mục tiêu. Xác minh phải dựa phiếu có hiệu lực cuối cùng theo hợp đồng. Trả chỉ khi proposal thắng là trò chơi khác.

Với mỗi \(h\), tập hành động cá nhân được chốt, hữu hạn, không rỗng và tạo trò chơi hữu hạn thông thường. Ràng buộc nghĩa vụ chung phải kiểm trước khi hợp đồng vào menu; không tùy tiện loại một cấu hình sau khi người khác đã chọn rồi vẫn áp định lý Nash thông thường. Cấu trúc và payoff là thông tin chung trong mô hình chuẩn. Giả định này không cho phép dùng số liệu cuối kỳ làm thông tin lịch sử.

**Phản ứng người nhận.** \(\mathcal V_i(h,\mathbf x)\) là payoff kỳ vọng gồm giá trị chính sách, chuyển giao nền, chi phí và tổn thất, chưa gồm hối lộ mới. Theo E:

$$
U_i(h,\mathbf x)=\mathcal V_i(h,\mathbf x)+\lambda_i\eta_i x_i,
\qquad
U_A(h,\mathbf x)=\mathcal V_A(h,\mathbf x)-\lambda_A\sum_{i\in\mathcal R}\eta_i x_i.
\tag{3.5}
$$

Giữ \(h,\mathbf x_{-i}\) cố định, đặt \(d_i=\mathcal V_i(h,0,\mathbf x_{-i})-\mathcal V_i(h,1,\mathbf x_{-i})\). Lợi ích khi đổi từ 0 sang 1 là:

$$
U_i(h,1,\mathbf x_{-i})-U_i(h,0,\mathbf x_{-i})=\lambda_i\eta_i-d_i(h,\mathbf x_{-i}).
\tag{3.6}
$$

Hành động 1 là phản ứng tối ưu khi vế phải không âm; hành động 0 tối ưu khi không dương; tại bằng nhau cả hai tối ưu. \(d_i\) có đơn vị lợi ích, không phải VP, chưa được suy từ lựa chọn quan sát. Chỉ khi \(d_i,\lambda_i\) không đổi theo tiền mới diễn giải \(d_i/\lambda_i\) như ngưỡng tiền có điều kiện trên hành động người khác. Với \(d_i<0\), người nhận vốn đã thích hành động mục tiêu, nên tiền trả chưa chứng minh tạo thay đổi hành vi.

Theo quy tắc hành vi 3.1.1, điều kiện chuyển là \(\lambda_i\eta_i-d_i>\epsilon_i\). Với \(\epsilon_i>0\), giữ cơ sở dù có lợi ích lệch nhỏ dương có thể không là phản ứng Nash chính xác. Phần cân bằng dùng mốc tối ưu chính xác; giữ cơ sở khi hòa ở \(\epsilon_i=0\) là một lựa chọn phản ứng tối ưu.

**Nash và tính hoàn hảo theo trò chơi con.** Sau một hợp đồng, \(\mathbf x^*\) là Nash nếu không người nhận nào cải thiện bằng lệch đơn phương:

$$
U_i(h,x_i^*,\mathbf x_{-i}^*)\ge U_i(h,x_i,\mathbf x_{-i}^*),
\quad \forall i,\ \forall x_i\text{ hợp lệ}.
\tag{3.7}
$$

Cân bằng hoàn hảo theo trò chơi con, viết tắt SPNE, còn đòi chiến lược tiếp diễn là Nash sau mọi đề nghị, kể cả đề nghị không xảy ra và nhánh không đề nghị. Cố định toàn bộ bản đồ tiếp diễn đó, \(A\) phải chọn hợp đồng tối ưu ở bước đầu. Không chỉ kiểm người nhận đồng ý rồi gọi toàn trò chơi là SPNE [LT2].

**Một người nhận.** Giả sử phần đánh đổi \(d>0\) không phụ thuộc tiền, người ngoài cố định, E thực thi chắc và menu đã đủ vốn. \(g_A\) là phần tăng giá trị phi chuyển giao của \(A\) nếu người nhận chọn 1; \(f_A(\eta)\ge0\) là chi phí mở đề nghị, đều có đơn vị \(\chi_A\). Chọn giữ cơ sở khi hòa, nghĩa là nhận khi \(\lambda_R\eta>d\). Payoff tăng thêm của \(A\):

$$
\Gamma_A(\eta)=
\begin{cases}
g_A-f_A(\eta)-\lambda_A\eta,&\lambda_R\eta>d,\\
-f_A(\eta),&\lambda_R\eta\le d,
\end{cases}
\qquad \Gamma_A(\varnothing)=0.
\tag{3.8}
$$

Menu hữu hạn có không đề nghị nên có lựa chọn đạt cực đại. Chọn cực đại cùng phản ứng tối ưu sau mọi đề nghị tạo SPNE thuần: người nhận không có lệch sinh lợi ở mỗi nhánh, còn \(A\) đã so toàn bộ payoff tiếp diễn ở gốc. Nếu một đề nghị được nhận đem giá trị dương, lựa chọn tốt nhất phải đem giá trị dương. Nếu mọi đề nghị được nhận đều âm, không đề nghị là một lựa chọn cân bằng. Giá trị bằng không có thể tạo nhiều lựa chọn cân bằng.

Nếu \(f_A\) không giảm theo tiền, mức nhỏ nhất trong menu vượt \(d/\lambda_R\) là đề nghị được nhận tốt nhất cho \(A\). Điều đó không bảo đảm nên đưa tiền và không xác định giá thực tế, vì \(d,g_A,f_A\) và ngân sách chưa được ước lượng.

Tính hữu hạn có ý nghĩa ở biên. Nếu tiền biến thiên liên tục, buộc từ chối tại hòa, không phí mở và lợi ích đủ lớn, mọi đề nghị được nhận đều có thể giảm mà vẫn được nhận. Không có mức tối ưu tuân quy tắc từ chối tại hòa trong trường hợp này. Không suy toàn trò chơi liên tục không có SPNE: chấp nhận tại hòa có thể hỗ trợ cân bằng khác. Điều kiện và chứng minh chi tiết được giữ trong tài liệu kỹ thuật.

**Nhiều người nhận và cam kết.** Với trò chơi con hữu hạn có payoff hữu hạn, định lý Nash bảo đảm cân bằng hỗn hợp, không bảo đảm cân bằng thuần [LT1]. Chọn cân bằng tại từng nhánh rồi chọn hợp đồng tối ưu của \(A\) trong menu hữu hạn tạo SPNE, có thể cần hỗn hợp. Nếu nhiều cân bằng tiếp diễn, không mặc định \(A\) điều khiển cân bằng có lợi nhất. Xác suất chiến lược thuộc trò chơi giả định, không phải tỷ lệ nhận hối lộ ước lượng từ blockchain.

Cam kết làm thay đổi trò chơi. Ở chế độ P, lời hứa còn quyền bội ước, nếu sau phiếu việc trả không tạo lợi ích khác và không có chế tài hay giá trị uy tín, không trả khoản dương là tối ưu ở lượt cuối. Người có \(d>0\) không đổi chỉ nhờ lời hứa đó. Ở chế độ U, trả trước không ràng buộc hành vi, tiền đã nhận như nhau ở hai hành động nên triệt tiêu; nếu \(d>0\), người nhận giữ cơ sở. Không áp kết luận cho mô hình có nghĩa vụ mới, trả đũa, quan hệ lặp hoặc sở thích khác.

Chấp nhận, đủ vốn và đạt mục tiêu là ba điều kiện riêng. E có thể phải trả dù outcome không đổi; người nhận có thể nhận tiền cho điều vốn định làm. Trò chơi cung cấp cấu trúc phân tích động cơ, chưa chứng minh thỏa thuận thao túng hoặc giá hối lộ trong dữ liệu.

### 3.2.2. Tấn công khai thác vay chớp nhoáng.

Khoản vay chớp nhoáng thuần túy được xét là khoản vay hoàn trả trong cùng giao dịch theo điều kiện giao thức. Nhánh mở nợ kéo dài phải phân tích riêng. Mã Aave đã lưu dùng để kiểm cấu trúc giải ngân và hoàn trả, không chứng minh Decentraland có nguồn vay tương ứng hoặc mức phí chung mọi thời kỳ [KT3].

Câu hỏi kỹ thuật là số dư hoặc quyền tạm thời có đi vào dữ liệu scoring ở snapshot không. Gọi \(\mathcal S_j\) là ánh xạ từ trạng thái scoring đọc sang VP. Nếu trạng thái được đọc ở đúng block chốt không đổi sau vay rồi trả:

$$
\mathcal S_j(\text{trạng thái chốt sau hành động})
=\mathcal S_j(\text{trạng thái chốt cơ sở})
\quad\Longrightarrow\quad \Delta w_{ij}=0.
\tag{3.9}
$$

Đây là bất biến của đầu vào scoring, áp dụng cho đường trực tiếp chỉ tạo số dư tạm đã hoàn trả, không để lại quyền hoặc dữ liệu khác ảnh hưởng điểm. Vay sau snapshot cũng không sửa số dư block quá khứ trong nhánh đọc đúng block đó.

Mã đã đối chiếu cho thấy ở nhánh nhận snapshot dạng số, ERC20/ERC721 truyền block đó khi đọc số dư. ESTATE, wearables và rental sử dụng dữ liệu quyền hoặc entity theo truy vấn riêng. Delegation cần quyền ủy quyền và underlying strategies; multichain cần ánh xạ block mạng phụ. Các checkpoint được lưu bằng commit và checksum, nhưng chưa nối đầy đủ runtime, kiểu snapshot và trạng thái từng nhánh với mọi phiếu lịch sử [KT2, DL2].

**Bảng 3.1. Phạm vi kết luận về vay chớp nhoáng**

| Đường tác động | Kết luận trong điều kiện đã kiểm | Chứng cứ còn thiếu |
| --- | --- | --- |
| Chỉ tăng số dư ERC20/ERC721 tạm rồi trả, trạng thái đọc đã khôi phục | Không tạo VP mới trong nhánh chốt đúng trạng thái | Deployment, kiểu snapshot và phụ thuộc thực dùng |
| Để lại quyền delegation hoặc entity sau hoàn trả | Chưa xác minh đường tăng VP khả thi | Hợp đồng, mapping, quyền và trạng thái lịch sử |
| Scoring qua mạng phụ | Chỉ suy bất biến khi từng mạng dùng đúng block chốt | Block mapping, fallback và runtime |
| Giữ tài sản vay qua snapshot rồi trả ở block sau | Là vay kéo dài, không phải đường vay thuần túy đang xét | Nguồn vay, quyền, kỳ hạn, vốn và chi phí |

Nguồn: [KT2, KT3, DL2], hồ sơ FEASIBILITY và SOURCE_MANIFEST 3.2.2. Bảng phân loại phạm vi kỹ thuật, không thống kê số vụ tấn công.

Hồ sơ chưa xác minh đường flash-loan governance attack khả thi tại Decentraland. Kết luận không chứng nhận mọi deployment hoặc loại mọi đường gián tiếp. Không đưa “vay tạm rồi cộng toàn lượng vay thành VP” vào tập hành động hợp lệ. Đường còn thiếu bằng chứng giữ chưa xác minh, không gán xác suất thành công tùy ý. Sau khi xác định giới hạn hành động, phần tiếp theo đo độ nhạy outcome trong những miền phản thực tế được định nghĩa rõ.

## 3.3. Định lượng hóa rủi ro từ dữ liệu thực

### 3.3.1. Tính toán chi phí cận biên để lật ngược kết quả biểu quyết thực tế.

**Mẫu và đại lượng.** “Chi phí cận biên” ở đây trước hết là lượng VP thay đổi ít nhất hoặc infimum của lượng đó, không phải đạo hàm và không mang đơn vị USD. Outcome tính bằng Governance ứng viên, tách khỏi lựa chọn dẫn đầu theo VP và trạng thái chính thức. Đổi outcome không tự đảo quyết định thủ công, điều kiện ngân sách hoặc thực thi.

**Bảng 3.2. Phạm vi dữ liệu và mức chứng cứ**

| Phạm vi | Đề xuất | Phiếu hoặc đối chiếu | Ý nghĩa |
| --- | ---: | --- | --- |
| Toàn bộ | 2.852 | 177.729 phiếu | Tái dựng tổng và đối chiếu Snapshot |
| Mức A final | 2.850 | Hai đề xuất còn lại có 18 phiếu pending | Khớp tổng chưa đồng nghĩa final |
| Mức B trước lọc độ khớp | 1.667 | 101.268 phiếu; 1.276 outcome khớp | Đủ điều kiện quy tắc lịch sử ứng viên |
| B binding, mẫu chính 3.3 | 1.023 | 63.662 phiếu; 1.016 outcome khớp | Giữ bảy trường hợp không khớp |
| Mẫu C chọn có điều kiện | 1.006 | 60.804 phiếu; 5.921 ví | Không là kiểm định độc lập |

Nguồn: [DL1, DL3, DL4]. Đơn vị là đề xuất hoặc phiếu như ghi; các tập bao hàm nhau, không cộng thành tổng.

Toàn B khớp 1.276/1.667, bằng 76,54%; B binding khớp 1.016/1.023, bằng 99,32%. Đây là độ khớp outcome ứng viên với nhãn lưu, không phải xác suất thành công của tác tử. C được chọn một phần theo outcome nên độ khớp 100% của C không là bằng chứng độc lập.

Tally được cộng từ phiếu trước khi đối chiếu Snapshot, giữ choice index, component và trạng thái nguồn. Dung sai đối chiếu điểm tham chiếu không được dùng như epsilon khi quyết định hòa hoặc ngưỡng. Quy tắc được chọn theo mã lịch sử; commit ứng viên chưa chứng minh production. Toàn B có 84 đề xuất thiếu chứng cứ DEFAULT, trong đó 49 thuộc B binding. Còn 10 đề xuất binding có cờ lớp ngân sách chưa xác minh. Các trường hợp này được giữ và gắn cờ [DL1, KT1].

**Ba kịch bản.** \(\mathbf S_j\) là vector VP theo lựa chọn gốc, \(n_j\) là số phiếu, \(\Theta_j\) là ngưỡng và \(r_j\) là quy tắc ứng viên. \(\mathsf{Gov}_{r_j}\) giữ cách chiếu nhãn, abstain, invalid và hòa đúng phiên bản. Mục tiêu là ACCEPTED sang REJECTED, REJECTED sang ACCEPTED, FINISHED sang REJECTED. Năm trường hợp FINISHED không bị đổi đầu vào thành REJECTED. Poll không binding chưa có mục tiêu chung, không bị ép thành Yes/No.

S1 chuyển lượng VP chia được \(\nu\) từ một lựa chọn \(k_s\) sang \(k_d\), với \(0\le\nu\le S_{jk_s}\), giữ tổng VP và \(n_j\). S2 thêm \(\nu>0\) VP đã đủ điều kiện nhưng chưa dùng vào một lựa chọn, tăng tổng VP. Phép tính dùng một phiếu bổ sung đại diện khi lượng thêm dương, không ước lượng số người chưa tham gia. S2 không áp trần cung vì chưa biết đủ nguồn cung, nên là miền nới lỏng. S3 chọn tập ví từ cùng lựa chọn nguồn, chuyển toàn bộ trọng số từng ví tới một đích.

Với \(F_{js\alpha}\) là tập lượng VP đạt mục tiêu trong hướng \(\alpha\) của kịch bản \(s\), ngưỡng liên tục là:

$$
M_{js}=\min_{\alpha:F_{js\alpha}\ne\varnothing}\inf F_{js\alpha},
\qquad
F_{j1\alpha}=\{\nu:\mathsf{Gov}_{r_j}(\mathcal K_j,\mathbf S_j-\nu\mathbf e_{k_s}+\nu\mathbf e_{k_d},n_j,\Theta_j)=y_j^*\}.
\tag{3.10}
$$

Trong tập S1 ở (3.10), \(\nu\) còn thỏa miền đã nêu; \(\mathbf e_k\) là vector đơn vị của lựa chọn \(k\). S2 thay vector bằng \(\mathbf S_j+\nu\mathbf e_{k_d}\), dùng \(n_j+1\) khi \(\nu>0\), xét riêng \(\nu=0\). Nếu không hướng nào đạt mục tiêu, kết quả là không khả thi trong miền, không gán ngưỡng bằng không.

Nếu \(M_{js}\) thuộc miền đích ở một hướng tốt nhất thì là tối thiểu đạt được. Nếu mọi hướng tốt nhất mở tại biên thì chỉ có infimum không đạt. Chứng nhân đạt outcome được lưu riêng, không gọi là lượng nhỏ nhất. Không cộng 1 VP hoặc epsilon tùy ý để tạo nghiệm tối ưu giả.

S3 tối thiểu hóa \(\sum_iw_{ij}\zeta_i\), với \(\zeta_i\in\{0,1\}\), trong từng nhóm cùng nguồn và một đích. S1 là cận dưới S3 trong cùng miền. Chỉ công nhận tối ưu khi có chứng minh; tập ví đạt mục tiêu chưa chứng minh tối ưu chỉ tạo cận trên. Mục tiêu tối ưu là VP, không phải số ví. S1/S3 chưa tối ưu chuyển phối hợp nhiều nguồn hoặc nhiều đích.

Phân hoạch khoảng, số học hữu tỷ, thuật toán tập con và chứng nhận tìm kiếm ở tài liệu kỹ thuật [DL3]. Bộ 3.3.1 có 27 kiểm thử đạt, chứng nhân được tính lại bằng Governance và bốn CSV tái lập giống từng byte. Các phép kiểm xác nhận kết quả trong quy tắc ứng viên, không xác minh deployment.

**Bảng 3.3. Trạng thái ngưỡng trên 1.023 đề xuất B binding**

| Kịch bản | Tối thiểu đạt được đã chứng minh | Infimum không đạt | Cận trên khả thi | Không khả thi trong miền |
| --- | ---: | ---: | ---: | ---: |
| S1: chuyển VP liên tục | 307 | 301 | 0 | 415 |
| S2: thêm VP đủ điều kiện | 850 | 167 | 0 | 6 |
| S3: chuyển ví nguyên vẹn | 335 | 0 | 273 | 415 |

Nguồn: [DL3], CSV theo Snapshot ID và scenario. Đơn vị: đề xuất; mỗi hàng có mẫu số 1.023, không cộng các hàng thành số đề xuất độc lập.

Có 1.018 đề xuất có giá trị VP hữu hạn ở ít nhất một kịch bản; năm không có phương án đạt mục tiêu trong cả ba miền. S1/S3 cùng có chứng nhân ở 608 đề xuất; S2 có 1.017 ngưỡng toán học hữu hạn. Chỉ 335 S3 được chứng minh tối ưu; 273 phương án còn lại không được dùng như tối ưu.

**Bảng 3.4. Phân bố ngưỡng VP, tách trạng thái nghiệm**

| Kịch bản và trạng thái | n | Q25, VP | Trung vị, VP | Q75, VP |
| --- | ---: | ---: | ---: | ---: |
| S1 tối thiểu đạt được | 307 | 499.271,72 | 850.012,00 | 1.837.905,67 |
| S1 infimum không đạt | 301 | 178.043,29 | 620.911,98 | 1.486.942,20 |
| S2 tối thiểu đạt được | 850 | 500.000,00 | 1.211.308,38 | 3.796.507,42 |
| S2 infimum không đạt | 167 | 769.794,04 | 1.704.317,75 | 3.142.881,92 |
| S3 tối thiểu đạt được | 335 | 336.304,82 | 860.731,80 | 2.026.000,00 |
| S3 cận trên khả thi | 273 | 451.949,19 | 993.168,09 | 1.895.615,95 |

Nguồn: [DL3], SUMMARY.json. Phân vị nội suy tại \((n-1)p\); làm tròn hai chữ số để trình bày, không để quyết định biên. Các nhóm khác nhau, không dùng bảng để xếp hạng chi phí tối ưu chung.

Trên 607 đề xuất có ngưỡng hữu hạn ở cả S1/S2, trung vị tỷ số S2/S1 bằng 2; 189 trường hợp lớn hơn 2. So sánh dùng tối thiểu hoặc infimum đúng trạng thái, không phải giá tiền. Chuyển phiếu thay chênh lệch hai lựa chọn khác thêm phiếu, nhưng ngưỡng và nhãn khiến công thức một nửa chênh lệch không áp dụng cho mọi phiên bản.

Trong 2.852 đề xuất, 1.829 không thuộc mẫu chính: 1.011 chưa có quy tắc lịch sử phù hợp, 644 thuộc B nhưng không binding và chưa có mục tiêu chung, 152 thiếu metadata Governance lưu trữ, 20 chưa đóng tại ảnh lưu và hai chưa final hoặc chưa đầy đủ. Lý do được giữ trong kết quả, không chỉ chọn trường hợp dễ tính hoặc khớp nhãn.

Không trường hợp nào đủ chứng cứ quy đổi thành USD. Các ngưỡng đo yêu cầu VP trong miền phản thực tế, chưa chứng minh nguồn cung, sự đồng ý chủ ví hoặc thỏa thuận có lợi. Ý nghĩa các yêu cầu này đối với hệ thống được phân tích tiếp.

### 3.3.2. Điểm tới hạn của hệ thống Decentraland hiện tại.

Phạm vi định lượng là mẫu lịch sử 2021–2023 và đánh giá khả năng suy rộng. Giữ tên mục theo đề cương, nhưng hồ sơ chưa xác định điểm tới hạn của toàn Decentraland năm 2026.

Điểm tới hạn là biên chuyển outcome gắn miền hành động và ràng buộc đề xuất. Để so quy mô, dùng \(q_{js}=M_{js}/V_j\), với \(V_j=\sum_iw_{ij}\) là tổng VP đã tham gia. Khoảng cách có dấu là \(\delta_j=(\Theta_j-\omega_j)/\Theta_j\), trong đó \(\omega_j\) là VP winner theo đúng phép chiếu Governance. Chỉ dùng mẫu số dương và quy tắc thật sự áp ngưỡng; trường hợp không xác định giữ trống có lý do.

\(q\) mô tả lượng thay đổi so với quyền đã dùng, không phải xác suất thành công. \(\delta>0\) nghĩa winner thiếu ngưỡng, \(\delta<0\) nghĩa vượt ngưỡng; gần ngưỡng vẫn chưa đủ nếu nhãn hoặc hòa không thỏa. Không chia cao, trung bình, thấp bằng phần trăm tùy ý. Thay vào đó dùng phân bố và đường bao số outcome có thể đổi theo hạn mức VP giả định, tách điểm biên đạt/không đạt [DL4].

**Bảng 3.5. Điều kiện tới hạn trong mẫu lịch sử**

| Điều kiện | Đề xuất | Kết luận trong phạm vi |
| --- | ---: | --- |
| S1 có ngưỡng hữu hạn | 608 | Có phương án khi VP chia được giữa một cặp lựa chọn |
| S1 không khả thi và tổng VP dưới ngưỡng | 410 | Giữ tổng không tạo đủ ngưỡng trong quy tắc tương ứng |
| S1 vướng điều kiện khác | 5 | Cả năm có khoảng trống DEFAULT |
| S2 có ngưỡng hữu hạn | 1.017 | Nhu cầu toán học, nguồn cung thực chưa biết |
| Tồn tại phiếu nguyên vẹn đổi outcome | 377 | Ảnh hưởng của một phiếu, chưa chứng minh quyền điều khiển |

Nguồn: [DL4], RESULTS và S1_OTHER_OBSTRUCTIONS. Đơn vị: đề xuất. Các nhóm có thể giao nhau, không cộng thành tổng rủi ro.

Trong 415 trường hợp S1 không khả thi, 410 có \(V_j<\Theta_j\). Mỗi lựa chọn không vượt tổng VP nên tái phân bổ không đủ ngưỡng trong các quy tắc này. Cả 410 có ngưỡng S2 hữu hạn. Giới hạn giữ tổng không phải bất khả xâm phạm trước miền khác; nguồn VP hợp lệ chưa dùng vẫn chưa được xác minh.

Năm trường hợp còn lại đều dùng nhánh abstain_default ứng viên và lựa chọn yes/no. Bốn grant có outcome FINISHED, mục tiêu REJECTED và tổng VP không nhỏ hơn hai lần ngưỡng, nên phân bổ lại không đưa winner dưới ngưỡng. Trường hợp linked_wearables có mục tiêu ACCEPTED nhưng cặp hai lựa chọn chưa được nhánh ứng viên nhận diện để trả ACCEPTED. Thiếu chứng cứ DEFAULT và deployment khiến kết luận này không phải thuộc tính production đã xác nhận.

**Tập trung quyền đã sử dụng.** Chỉ tiêu được tính lại từ 63.662 phiếu đúng B binding, với 6.004 ví từng xuất hiện. Đây không phải tổng thể đủ điều kiện. Với \(p_{ij}=w_{ij}/V_j\), HHI bằng \(\sum_ip_{ij}^2\). Gini tính trên trọng số sắp tăng, giữ cả số 0; top-k là tỷ trọng k ví lớn nhất từng đề xuất. Một đề xuất tổng VP bằng 0 làm tập trung và chuẩn hóa theo \(V_j\) không xác định.

Trung vị S1 \(M/V\) khoảng 0,4999 ở nhóm tối thiểu và 0,3028 ở nhóm infimum; trung vị S3 ở nhóm tối ưu đã chứng minh là 0,5626. Các nhóm có thành phần khác nhau, không so như tác động nhân quả của chuyển nguyên ví. Trong cùng đề xuất, S1 mới là cận dưới cùng miền; chênh từ cận trên S3 chỉ là cận trên khoảng cách tối ưu.

**Bảng 3.6. S1 hữu hạn theo loại đề xuất và thời kỳ**

| Nhóm | Đề xuất trong nhóm | S1 hữu hạn | Tỷ phần trên nhóm |
| --- | ---: | ---: | ---: |
| ban_name | 62 | 38 | 61,29% |
| catalyst | 2 | 1 | 50,00% |
| governance | 44 | 35 | 79,55% |
| grant | 451 | 246 | 54,55% |
| linked_wearables | 73 | 24 | 32,88% |
| poi | 391 | 264 | 67,52% |
| development | 257 | 129 | 50,19% |
| validation | 652 | 386 | 59,20% |
| final_historical | 114 | 93 | 81,58% |

Nguồn: [DL4], RESULTS và GROUP_METRICS. S1 hữu hạn gồm tối thiểu/infimum, không phải vụ tấn công. Hai cách nhóm cùng chia 1.023 đề xuất, không cộng toàn bộ hàng. development đóng trước 01/01/2022 UTC, validation là 2022, final_historical là phần lịch sử từ 01/01/2023.

Tỷ phần khác nhau nhưng còn chịu thành phần mẫu và quy tắc; catalyst chỉ có hai quan sát. Chênh lệch theo thời gian không chứng minh hệ thống ngày càng dễ bị tấn công. Phân vị đầy đủ tiếp tục tách tối thiểu, infimum và cận trên ở tài liệu hỗ trợ [DL4].

Spearman giữa HHI và \(M/V\) trong S1 khoảng 0,254 ở nhóm tối thiểu, 0,118 ở nhóm infimum. Trong 335 nghiệm S3 tối ưu đã chứng minh, hệ số khoảng 0,741; nhóm chỉ có cận trên khoảng −0,039. Phiếu lớn vừa tăng ảnh hưởng cá nhân vừa có thể làm lượng VP phải chuyển nguyên vẹn lớn hơn. Không gộp thành hệ số về chi phí tối ưu, không suy tập trung gây an toàn hoặc thao túng. Đây là quan hệ mô tả; ví lặp, quy tắc và loại khác nhau chưa được xử lý bằng mô hình nhân quả. Không báo p-value theo giả định quan sát độc lập.

**Phạm vi hiện tại.** Bộ recent có 1.011 đề xuất nhưng chưa có ánh xạ Governance lịch sử đủ điều kiện theo cùng chuẩn. Mã nhánh hiện được đọc và tài liệu giới thiệu không chứng minh version production từng giai đoạn. Không dùng source 2023 hoặc hằng hiện nay lấp khoảng trống quá khứ. Cần deployment, cấu hình ngưỡng, scoring, block từng mạng và lớp quyết định ngoài tally trước khi mở rộng [KT1, DL2, DL4].

Ngưỡng VP thấp có thể giảm nhu cầu quyền nhưng chưa bảo đảm chi phí tiền thấp. Lợi ích kỳ vọng dương không bảo đảm đủ vốn; đủ vốn không bảo đảm quyền hợp lệ tại snapshot. Đổi outcome chưa bảo đảm đổi quản trị hoặc thực thi. Chương không công bố điểm tới hạn USD, xác suất tấn công hoặc bằng chứng thao túng đã xảy ra.

**Chuyển tiếp sang Chương 4.** Đầu vào dùng ngay để thiết kế mô hình có điều kiện gồm trọng số và lựa chọn quan sát, loại đề xuất, ngưỡng ứng viên, miền hành động và các mốc kiểm outcome. S1/S2 cung cấp biên liên tục; 335 nghiệm S3 cung cấp tối ưu đã chứng minh, còn 273 phương án chỉ cung cấp cận trên. Thống kê sau đóng là mục tiêu đối chiếu, không là thông tin biết trước. Hiệu chỉnh chỉ dùng development theo phạm vi chốt trước; validation và final_historical dùng đối chiếu, không lấy toàn bảng mô tả làm tham số fit.

Lợi ích riêng, ngân sách, chấp nhận chuyển giao, phối hợp, cùng chủ giữa ví, cung VP chưa tham gia, thị trường huy động và xác suất thực thi vẫn cần dữ liệu hoặc giả định công khai. Với các giới hạn đó, chương cung cấp nền tảng lý thuyết và định lượng lịch sử cho bước sau, chưa phải kết quả động lực học hoặc hiệu năng phòng thủ.

## Tài liệu tham khảo và nguồn dữ liệu của chương

**Nguồn lý thuyết**

- [LT1] Nash, J. F., Jr. (1950). *Equilibrium Points in N-Person Games*. Proceedings of the National Academy of Sciences, 36(1), 48–49. [Bản lưu PMC và DOI đã đối chiếu](https://pmc.ncbi.nlm.nih.gov/articles/PMC1063129/). DOI: 10.1073/pnas.36.1.48. Dùng cho tồn tại Nash hỗn hợp hữu hạn, không cho hành vi thực nghiệm Decentraland.
- [LT2] MIT OpenCourseWare. *Chapter 11: Subgame-Perfect Nash Equilibrium*. [Tài liệu đã đối chiếu](https://ocw.mit.edu/courses/14-12-economic-applications-of-game-theory-fall-2025/mit14_12f12_chapter11_f12.pdf). Không suy năm xuất bản từ đường dẫn khóa học.

**Nguồn kỹ thuật**

- [KT1] Decentraland, *Governance*, phiên bản outcome lịch sử trong [RULE_CATALOG](../baseline/RULE_CATALOG.json). [Repository gốc](https://github.com/decentraland/governance). URL và commit từng tệp là nguồn kỹ thuật, không phải chứng cứ deployment.
- [KT2] Snapshot Labs, mã scoring lịch sử trong [SOURCE_MANIFEST](../ch3_3_2_2_evidence/SOURCE_MANIFEST.json), gồm snapshot.js năm 2021 và [snapshot-strategies tại commit a8555ec5…](https://github.com/snapshot-labs/snapshot-strategies/tree/a8555ec5aa1f7b332f4134b065ffba9de7196c89). Dùng theo từng nhánh, không thay xác minh runtime.
- [KT3] Aave, *protocol-v2*, [LendingPool.sol tại commit ce53c4a8…](https://github.com/aave/protocol-v2/blob/ce53c4a8c8620125063168620eba0a8a92854eb8/contracts/protocol/lendingpool/LendingPool.sol), bản lưu cùng manifest 3.2.2. Dùng cho cơ chế vay, không định giá tấn công.

**Dữ liệu và kết quả của nhóm**

- [DL1] Dữ liệu nhóm khôi phục từ [Decentraland Transparency](https://governance.decentraland.org/transparency/) và Snapshot, gồm metadata, votes_recovered, source_log và raw_downloads trong [data_enrichment](../data_enrichment/README.md); đối chiếu ở [Baseline](../baseline/BASELINE_RESULTS.md) và BASELINE_VALIDATION.csv. Trích theo ảnh đã lưu, không theo trang hiện tại.
- [DL2] Hồ sơ mô hình 3.1–3.2 của nhóm, đặc biệt [FEASIBILITY 3.2.2](../CH3_3_2_2_FEASIBILITY.md) và [xác minh nguồn](../ch3_3_2_2_evidence/VERIFICATION.json). Công thức kinh tế và trò chơi chuyên biệt là đặc tả của nghiên cứu.
- [DL3] [Kết quả VP cận biên 3.3.1](../ch3_3_3_1/CH3_3_3_1_VP_MARGIN_RESULTS.csv), SUMMARY.json, bảng khoảng và chứng nhận ví; [kiểm chứng](../ch3_3_3_1/VERIFICATION.json).
- [DL4] [Kết quả điều kiện tới hạn 3.3.2](../ch3_3_3_2/CH3_3_3_2_RESULTS.csv), GROUP_METRICS, CONCENTRATION_ASSOCIATIONS và [phạm vi hiện tại](../ch3_3_3_2/CH3_3_3_2_CURRENT_SCOPE.md); [kiểm chứng](../ch3_3_3_2/VERIFICATION.json).

Mã nguồn tham khảo cục bộ cho phép nhóm chuyển sang quy định trích dẫn chung mà không mất liên kết. Bản đồ số liệu, ánh xạ ký hiệu và chi tiết kỹ thuật được cung cấp riêng cùng bản thảo.
