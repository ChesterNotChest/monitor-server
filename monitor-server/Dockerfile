# ---- 构建阶段 ----
FROM python:3.12-alpine AS builder

WORKDIR /app

# 安装构建依赖
RUN apk add --no-cache gcc musl-dev libffi-dev

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- 运行阶段 ----
FROM python:3.12-alpine

WORKDIR /app

# 从构建阶段复制已安装的包
COPY --from=builder /root/.local /root/.local

# 复制源码
COPY src/ ./src/

# 确保 PATH 包含用户安装的包
ENV PATH=/root/.local/bin:$PATH

EXPOSE 8000

CMD ["python", "-m", "src.run"]
