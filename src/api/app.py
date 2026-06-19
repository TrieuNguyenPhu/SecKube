# ==============================================================================
# File: app.py
# Mục đích: Ứng dụng Flask chính của dự án SecKube - đóng vai trò là API
#           backend phục vụ cho việc demo và kiểm thử bảo mật trên Kubernetes.
#
# Kiến trúc:
#   - Đây là microservice chính được đóng gói thành container image và triển
#     khai lên Kubernetes cluster thông qua ArgoCD (GitOps).
#   - Ứng dụng tích hợp sẵn Prometheus metrics để hỗ trợ giám sát (monitoring)
#     và cảnh báo (alerting) trong pipeline Observability.
#   - Hỗ trợ canary deployment bằng cách cho phép inject lỗi có kiểm soát
#     thông qua biến môi trường ERROR_RATE.
#
# Các endpoint:
#   GET /         - Endpoint chính, trả về trạng thái OK hoặc lỗi (canary test)
#   GET /healthz  - Health check cho Kubernetes liveness/readiness probes
#   GET /metrics  - (Tự động thêm bởi PrometheusMetrics) Export metrics cho
#                   Prometheus scrape
# ==============================================================================

# --- Import các thư viện cần thiết ---

# os: Đọc biến môi trường (environment variables) để cấu hình ứng dụng
#     mà không cần hardcode giá trị - tuân thủ nguyên tắc 12-Factor App.
import os

# random: Sinh số ngẫu nhiên để mô phỏng lỗi (error injection) trong
#         canary deployment. Dùng để quyết định request nào sẽ trả về lỗi 500.
import random

# flask: Framework web chính. Flask được chọn vì nhẹ, phù hợp cho microservice.
#   - Flask: Class chính để tạo ứng dụng web
#   - jsonify: Chuyển đổi Python dict thành JSON response với Content-Type phù hợp
from flask import Flask, jsonify

# prometheus_flask_exporter: Thư viện tích hợp Prometheus vào Flask.
#   - Tự động tạo endpoint GET /metrics để Prometheus server scrape dữ liệu
#   - Tự động đo lường: request count, request latency, response size cho mỗi endpoint
#   - Dữ liệu metrics này được Grafana dashboard sử dụng để hiển thị biểu đồ
from prometheus_flask_exporter import PrometheusMetrics

# --- Khởi tạo ứng dụng Flask ---
app = Flask(__name__)

# Kích hoạt Prometheus metrics cho ứng dụng.
# Sau dòng này, endpoint GET /metrics sẽ tự động được tạo ra.
# Prometheus server (được cấu hình trong k8s-monitoring/) sẽ định kỳ gọi
# endpoint này để thu thập metrics như:
#   - flask_http_request_total: Tổng số request theo method, status, endpoint
#   - flask_http_request_duration_seconds: Thời gian xử lý request
#   - flask_http_request_exceptions_total: Số lượng exception
PrometheusMetrics(app)  # Tự thêm /metrics

# --- Biến cấu hình từ Environment Variables ---

# ERROR_RATE: Tỷ lệ lỗi giả lập (0.0 đến 1.0) dùng cho canary deployment.
#   - Giá trị 0 (mặc định): Không có lỗi, ứng dụng hoạt động bình thường
#   - Giá trị 0.5: 50% request sẽ trả về lỗi 500
#   - Giá trị 1.0: 100% request sẽ trả về lỗi 500
#
# Cách sử dụng trong canary deployment:
#   1. Phiên bản canary (mới) được deploy với ERROR_RATE > 0
#   2. Argo Rollouts theo dõi tỷ lệ lỗi qua Prometheus metrics
#   3. Nếu tỷ lệ lỗi vượt ngưỡng cho phép → tự động rollback
#   4. Nếu tỷ lệ lỗi trong giới hạn → tiếp tục promote canary
ERROR_RATE = float(os.getenv("ERROR_RATE", "0"))

# VERSION: Nhãn phiên bản của ứng dụng, được trả về trong mọi response.
#   - Giúp xác nhận phiên bản nào đang chạy trong cluster
#   - Hữu ích khi debug canary deployment (phân biệt v1 vs v2)
#   - Được set trong Kubernetes Deployment manifest qua env vars
VERSION = os.getenv("VERSION", "v1")

# --- Định nghĩa các API Endpoints ---

@app.get("/")
def index():
    """
    Endpoint chính của ứng dụng (GET /).

    Logic xử lý:
      1. Sinh một số ngẫu nhiên từ 0.0 đến 1.0
      2. Nếu số đó < ERROR_RATE → trả về HTTP 500 (lỗi giả lập)
      3. Ngược lại → trả về HTTP 200 với trạng thái OK

    Response luôn bao gồm trường 'version' để hỗ trợ phân biệt
    traffic giữa phiên bản stable và canary trong quá trình rollout.

    Prometheus sẽ tự động ghi nhận status code (200 vs 500) của mỗi request,
    cho phép Argo Rollouts AnalysisTemplate query tỷ lệ lỗi để quyết định
    promote hay rollback canary.
    """
    if random.random() < ERROR_RATE:
        return jsonify(error="injected", version=VERSION), 500
    return jsonify(ok=True, version=VERSION)

@app.get("/healthz")
def healthz():
    """
    Endpoint health check cho Kubernetes probes (GET /healthz).

    Kubernetes sử dụng endpoint này cho:
      - livenessProbe: Kiểm tra ứng dụng còn sống không.
        Nếu thất bại → Kubernetes tự động restart container.
      - readinessProbe: Kiểm tra ứng dụng sẵn sàng nhận traffic chưa.
        Nếu thất bại → Pod bị loại khỏi Service endpoints (không nhận request).

    Trả về HTTP 200 "ok" đơn giản vì ứng dụng không có dependency phức tạp
    (không cần kiểm tra DB connection, cache, v.v.).
    """
    return "ok", 200

# --- Entrypoint khi chạy trực tiếp bằng Python ---
# Khối này chỉ chạy khi file được thực thi trực tiếp (python app.py),
# KHÔNG chạy khi Flask CLI khởi động (flask run) - đó là cách Dockerfile sử dụng.
# host="0.0.0.0": Lắng nghe trên tất cả network interfaces (cần thiết trong container)
# port=8080: Port mặc định, phải khớp với EXPOSE trong Dockerfile và
#            containerPort trong Kubernetes Deployment manifest.
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
