# Decentraland DAO Risk Simulator

Bài tập lớn Blockchain về tái dựng kết quả biểu quyết và mô phỏng trên dữ liệu Decentraland DAO. [Báo cáo Word](docs/Bao_cao_BTL_Decentraland_DAO.docx) trình bày mô hình, giả định, kết quả và lý do chạy ngoài chuỗi.

## Chạy demo

Dùng Python 3.12. Mở PowerShell ở thư mục này:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
```

Mở http://127.0.0.1:8501. Nếu cổng bận, thêm `--server.port 8503`. Sau khi cài thư viện, phần mô phỏng chạy cục bộ và không cần ví hay RPC.

1. Mở **Dữ liệu DAO** và quan sát 1.023 đề xuất binding. Phân biệt kết quả tái dựng và nhãn Governance.
2. Mở **Tái lập & xuất**, tải lên [JSON đã chuẩn bị](chapter4/dao_risk_simulator/demos/demo2_qv_split/scenario.json) rồi bấm **Kiểm tra & nạp cấu hình**. Sang **So sánh cơ chế** và chạy đối chứng TW, QV, Capping.
3. Mở **Độ nhạy** và chạy Type B cho số ví 1 và 4. Trong ca minh họa, QV chuyển từ không đạt sang đạt mục tiêu trong khi TW bất biến với cách chia cùng nguồn VP. Thông tin trước thời điểm chốt là giả định của mô phỏng.
4. Xuất JSON và CSV tại **Tái lập & xuất**. Có thể nạp [JSON Vote-Escrow](chapter4/dao_risk_simulator/demos/demo4_ve/scenario.json) để trình diễn lịch khóa riêng.

## Kiểm thử và nguồn

```powershell
.\.venv\Scripts\python.exe -m pytest release_tests chapter4/dao_risk_simulator/tests/test_ui.py -q -p no:cacheprovider
```

Bộ bàn giao có mã chạy, dữ liệu cắt cho demo, các bài kiểm thử runtime và hồ sơ chọn lọc. [Chứng nhận toàn dự án](docs/FULL_WORKSPACE_VERIFICATION.json) có phạm vi rộng hơn. [Manifest nguồn](RELEASE_SOURCE_MANIFEST.json) truy vết xuất xứ bộ dữ liệu. [Manifest gói nộp](RELEASE_FILE_MANIFEST.json) ghi mã băm các tệp, trừ chính manifest và chứng nhận sinh sau khi kiểm thử.

Xem [baseline](baseline/BASELINE_RESULTS.md), [mô hình chương 3](chapter3_final/CH3_MASTER_DRAFT.md), [thực nghiệm chương 4](chapter4/final_delivery/CH4_INTEGRATED_DRAFT.md), [lịch sử bảo trì](docs/MAINTENANCE.md) và [giới hạn của mô phỏng](chapter4/dao_risk_simulator/APP_LIMITATIONS.md). Giữ kèm [giấy phép MIT](docs/LICENCE_DAO_DELEGATION_MIT.txt) của bộ DAO delegation replication.
