# Decentraland DAO Risk Simulator

Ứng dụng kiểm lại kết quả biểu quyết lịch sử và so sánh các cơ chế biểu quyết của DAO trong mô phỏng.

## Chạy trên Windows

Cài Python 3.12 và mở PowerShell tại thư mục đã giải nén hoặc clone.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Mở [localhost:8501](http://localhost:8501). Ứng dụng dùng dữ liệu cục bộ và không cần kết nối ví.

## Thử demo

1. Vào **Dữ liệu DAO** để xem các đề xuất lịch sử.
2. Vào **Tái lập & xuất** và nạp [cấu hình minh họa](research/chapter4/dao_risk_simulator/demos/demo2_qv_split/scenario.json).
3. Vào **So sánh cơ chế**, bấm **Chạy đối chứng** để so sánh Token-Weighted, Quadratic Voting và Capping trên cùng kịch bản.

## Cấu trúc

| Đường dẫn | Nội dung |
| --- | --- |
| `app.py` | Điểm chạy Streamlit |
| `research/` | Mã ứng dụng, mô hình và dữ liệu phục vụ demo |
| `tests/` | Kiểm thử bộ dữ liệu, mô phỏng và nhập cấu hình |

Chạy kiểm thử bằng `python -m pytest tests research/chapter4/dao_risk_simulator/tests/test_ui.py -q` sau khi cài thư viện.
