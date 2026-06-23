# Piper TTS — Web App

Ứng dụng chuyển văn bản thành giọng nói (offline) sử dụng **Piper TTS** + **FastAPI** + **Alpine.js**.  
Không dùng AI cloud hay API bên ngoài. Toàn bộ xử lý trên máy cục bộ.

---

## Checklist cấu hình & chạy

> **Lưu ý Windows:** `piper-tts` Python package không có wheel cho Windows.  
> App này dùng **piper.exe** (binary standalone) gọi qua subprocess — không cần cài piper-tts qua pip.

### 1. Yêu cầu hệ thống

- [ ] **Python 3.10+** — [tải tại python.org](https://www.python.org/downloads/)
- [ ] **pip** đi kèm Python
- [ ] Đủ RAM để load model (thường 200–500 MB tùy model)

### 2. Cấu trúc thư mục

```
code/
├── backend/
│   ├── app.py          # FastAPI server + API routes
│   ├── worker.py       # Background job worker (polling SQLite)
│   ├── database.py     # SQLite helpers
│   └── requirements.txt
├── frontend/
│   └── index.html      # Giao diện Alpine.js + Tailwind
├── models/             # ← ĐẶT FILE .onnx + .onnx.json VÀO ĐÂY
├── piper/              # ← ĐẶT piper.exe VÀO ĐÂY (giải nén từ zip)
├── output/             # File WAV sinh ra (tự tạo)
├── tts.db              # SQLite database (tự tạo)
├── start.bat           # Chạy trên Windows
└── start.sh            # Chạy trên Linux/macOS
```

### 3. Tải Piper executable (bắt buộc trên Windows)

- [ ] Vào trang release: **https://github.com/rhasspy/piper/releases**
- [ ] Tải file **`piper_windows_amd64.zip`** (hoặc `piper_linux_x86_64.tar.gz` trên Linux)
- [ ] Giải nén, lấy file `piper.exe` (và các file DLL đi kèm) đặt vào thư mục **`piper/`**:

  ```
  piper/
  ├── piper.exe
  ├── espeak-ng-data/       # thư mục dữ liệu phoneme (có trong zip)
  ├── onnxruntime.dll       # DLL đi kèm (Windows)
  └── ...
  ```

  > **Quan trọng:** Giải nén **toàn bộ nội dung** của zip vào `piper/`, không chỉ mình `piper.exe`.  
  > Piper cần thư mục `espeak-ng-data/` bên cạnh để hoạt động.

### 4. Thêm model Piper TTS

- [ ] Tải file model `.onnx` và file config `.onnx.json` tương ứng từ:  
  **[rhasspy/piper-voices (HuggingFace)](https://huggingface.co/rhasspy/piper-voices/tree/main)**  
  Hoặc tải thẳng từ release của Piper:  
  **[github.com/rhasspy/piper/releases](https://github.com/rhasspy/piper/releases)**

- [ ] Sao chép cả **hai file** vào thư mục `models/`:

  ```
  models/
  ├── vi_VN-vivos-medium.onnx
  ├── vi_VN-vivos-medium.onnx.json
  ├── en_US-lessac-medium.onnx
  └── en_US-lessac-medium.onnx.json
  ```

  > **Bắt buộc:** file `.onnx.json` phải có tên khớp với `.onnx`, thiếu file này sẽ báo lỗi.

- [ ] Kiểm tra tên file **không có khoảng trắng**

#### Gợi ý model tiếng Việt

| Model | Chất lượng | Size |
|-------|-----------|------|
| `vi_VN-vivos-medium` | Tốt | ~63 MB |
| `vi_VN-vinhvd8-low` | Nhanh, nhẹ | ~15 MB |

### 4. Khởi động

#### Windows

```bat
start.bat
```
> Script tự tạo venv, cài packages, rồi chạy server.

#### Linux / macOS

```bash
chmod +x start.sh
./start.sh
```

#### Thủ công (nếu cần)

```bash
cd code
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r backend/requirements.txt
python backend/app.py
```

### 5. Truy cập ứng dụng

- [ ] Mở trình duyệt tại: **http://localhost:8000**

---

## Luồng hoạt động

```
[Người dùng nhập text]
        ↓
  POST /api/jobs      → Tạo job trạng thái "pending" trong SQLite
        ↓
  Worker (thread)     → Poll mỗi 2 giây, lấy job pending
        ↓
  Piper TTS           → Xử lý text → file WAV trong output/
        ↓
  Cập nhật DB         → status = "done", lưu tên file
        ↓
  [Người dùng bấm "Tải WAV" hoặc "Nghe"]
        ↓
  GET /api/download/{id} → Trả file WAV
```

---

## API Endpoints

| Method | URL | Mô tả |
|--------|-----|-------|
| `GET` | `/api/models` | Danh sách model có sẵn |
| `POST` | `/api/jobs` | Tạo job mới |
| `GET` | `/api/jobs` | Danh sách jobs (mới nhất trước) |
| `GET` | `/api/jobs/{id}` | Chi tiết 1 job |
| `DELETE` | `/api/jobs/{id}` | Xóa job + file WAV |
| `GET` | `/api/download/{id}` | Tải file WAV |

### Ví dụ tạo job qua curl

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Xin chào, đây là thử nghiệm giọng nói.",
    "model_name": "vi_VN-vivos-medium",
    "speaker_id": 0,
    "speed": 1.0
  }'
```

---

## Xử lý sự cố

| Triệu chứng | Nguyên nhân | Giải pháp |
|------------|------------|-----------|
| Không có model trong dropdown | Thiếu file `.onnx` trong `models/` | Tải model, đặt đúng thư mục |
| Job báo lỗi "Model config not found" | Thiếu file `.onnx.json` | Tải cả 2 file `.onnx` và `.onnx.json` |
| Server không khởi động | Port 8000 đã dùng | Đổi port: `uvicorn app:app --port 8001` |
| `pip install` lỗi piper-tts | Thiếu build tools | Cài Visual C++ Build Tools (Windows) hoặc `build-essential` (Linux) |
| Job kẹt ở "Đang xử lý" | Worker crash | Xem log terminal, restart server |

---

## Ghi chú

- File WAV đầu ra nằm trong `output/`, tên file = `{job_id}.wav`
- Database SQLite nằm tại `tts.db` (cùng cấp với thư mục `code/`)
- Giao diện tự làm mới mỗi 3 giây khi bật "Tự động làm mới"
- Tốc độ đọc: `0.25×` (rất chậm) → `1.0×` (bình thường) → `4.0×` (rất nhanh)
