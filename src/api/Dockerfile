# Lab 2 buá»•i chiá»u: Dockerfile
FROM python:3.13-alpine
RUN pip install flask prometheus-flask-exporter
RUN adduser -D -u 10001 appuser
COPY --chown=10001:10001 app.py /app/app.py
WORKDIR /app
ENV FLASK_APP=app.py
EXPOSE 8080
USER 10001
CMD ["flask", "run", "--host=0.0.0.0", "--port=8080"]
