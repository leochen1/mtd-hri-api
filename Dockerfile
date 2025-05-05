# 第一階段：建構階段
FROM python:3.8.10-slim AS builder

WORKDIR /app
COPY . /app

# 安裝依賴並清理暫存檔案
RUN pip install --upgrade pip --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org && \
    pip install --no-cache-dir -r requirements.txt --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org

# 第二階段：執行階段
FROM python:3.8.10-slim

WORKDIR /app
COPY --from=builder /app /app

# 安裝必要的工具
RUN apt-get update && apt-get install -y curl dnsutils && rm -rf /var/lib/apt/lists/*

# 確保基底映像檔乾淨，並安裝必要的依賴
RUN pip install --upgrade pip --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org && \
    pip install --no-cache-dir -r requirements.txt --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org

ENTRYPOINT ["python"]
CMD ["app.py"]