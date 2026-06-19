# ==============================================================================
# File: Dockerfile
# Mục đích: Đóng gói ứng dụng Flask API thành container image để triển khai
#           lên Kubernetes cluster.
#
# Quy trình build:
#   1. Sử dụng Python Alpine (image nhẹ, giảm attack surface)
#   2. Cài đặt dependencies (Flask + Prometheus exporter)
#   3. Tạo user non-root (bảo mật - nguyên tắc least privilege)
#   4. Copy mã nguồn ứng dụng vào image
#   5. Chạy Flask server trên port 8080 với user non-root
#
# Bảo mật:
#   - Base image Alpine: Kích thước nhỏ (~50MB), ít package → ít CVE tiềm ẩn
#   - Non-root user (UID 10001): Ngăn chặn container escape privilege escalation
#   - Không có shell phức tạp, không có package manager thừa
#
# Cách build:
#   docker build -t seckube-api:latest .
#
# Pipeline CI/CD:
#   Image được build bởi GitHub Actions, sau đó:
#   1. Scan lỗ hổng bảo mật bằng Trivy
#   2. Ký xác thực bằng Cosign (supply chain security)
#   3. Push lên container registry
#   4. ArgoCD tự động deploy phiên bản mới lên cluster
# ==============================================================================

# --- Stage 1: Base Image ---
# Sử dụng Python 3.13 trên Alpine Linux - image nhẹ nhất có thể.
# Alpine Linux dựa trên musl libc và BusyBox, kích thước chỉ ~5MB.
# So với python:3.13 (Debian-based, ~900MB), Alpine chỉ ~50MB
# → Giảm thời gian pull image và giảm bề mặt tấn công (attack surface).
FROM python:3.13-alpine

# --- Stage 2: Cài đặt Dependencies ---
# Cài đặt các thư viện Python cần thiết:
#   - flask: Web framework chính cho API
#   - prometheus-flask-exporter: Tích hợp Prometheus metrics (endpoint /metrics)
# Lưu ý: Không dùng requirements.txt ở đây vì chỉ có 2 dependencies đơn giản.
# Trong production nên dùng requirements.txt với version pinning để đảm bảo
# reproducible builds.
RUN pip install flask prometheus-flask-exporter

# --- Stage 3: Tạo User Non-root (Bảo mật) ---
# Tạo user 'appuser' với UID 10001, không có password (-D = no password).
# Lý do sử dụng non-root user:
#   1. Nguyên tắc Least Privilege: Container chỉ có quyền tối thiểu cần thiết
#   2. Nếu attacker exploit được ứng dụng, họ không có quyền root trong container
#   3. Kubernetes PodSecurityPolicy/Standards có thể yêu cầu runAsNonRoot: true
#   4. OPA Gatekeeper policy trong dự án này sẽ chặn container chạy với root
# UID 10001 được chọn vì nằm ngoài range UID hệ thống (0-999) và range
# user thông thường (1000-9999), tránh xung đột.
RUN adduser -D -u 10001 appuser

# --- Stage 4: Copy Mã Nguồn ---
# Copy file app.py vào thư mục /app trong container.
# --chown=10001:10001: Đặt quyền sở hữu file cho appuser (không phải root)
# → Đảm bảo user non-root có quyền đọc file ứng dụng.
COPY --chown=10001:10001 app.py /app/app.py

# --- Stage 5: Cấu hình Working Directory ---
# Đặt thư mục làm việc mặc định là /app.
# Các lệnh tiếp theo (CMD, ENTRYPOINT) sẽ chạy từ thư mục này.
WORKDIR /app

# --- Stage 6: Thiết lập Biến Môi Trường ---
# Cho Flask CLI biết file ứng dụng chính là app.py.
# Biến này được sử dụng bởi lệnh `flask run` trong CMD bên dưới.
ENV FLASK_APP=app.py

# --- Stage 7: Khai báo Port ---
# Khai báo container lắng nghe trên port 8080.
# Lưu ý: EXPOSE chỉ là metadata/documentation, không thực sự mở port.
# Port thực tế được mở bởi lệnh `flask run --port=8080` trong CMD.
# Port 8080 (không phải 80) vì user non-root không có quyền bind port < 1024.
# Port này phải khớp với:
#   - containerPort trong Kubernetes Deployment manifest
#   - targetPort trong Kubernetes Service manifest
EXPOSE 8080

# --- Stage 8: Chuyển sang User Non-root ---
# Chuyển sang chạy với UID 10001 (appuser) thay vì root.
# Mọi lệnh sau dòng này (bao gồm CMD) sẽ chạy với user này.
# QUAN TRỌNG: Dòng USER phải đặt SAU các lệnh RUN cần quyền root
# (như pip install, adduser) và TRƯỚC CMD.
USER 10001

# --- Stage 9: Lệnh Khởi Động ---
# Khởi động Flask development server.
# --host=0.0.0.0: Lắng nghe trên tất cả network interfaces
#   (mặc định Flask chỉ lắng nghe trên 127.0.0.1, không truy cập được từ
#    bên ngoài container)
# --port=8080: Port lắng nghe, phải khớp với EXPOSE ở trên
#
# Sử dụng exec form (JSON array) thay vì shell form để:
#   1. Flask process nhận PID 1 → nhận SIGTERM trực tiếp từ Kubernetes
#      khi Pod bị terminate (graceful shutdown)
#   2. Không tạo shell process trung gian (tiết kiệm tài nguyên)
CMD ["flask", "run", "--host=0.0.0.0", "--port=8080"]
