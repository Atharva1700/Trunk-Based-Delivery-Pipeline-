# NOT BUILT here: the sandbox Docker daemon was not running and Docker Hub was unreachable.
FROM python:3.12-slim
WORKDIR /app
COPY sample_app ./sample_app
ENV PYTHONDONTWRITEBYTECODE=1
CMD ["python", "-c", "from sample_app.app import health; print(health())"]
