#!/bin/bash
# 启动脚本

cd "$(dirname "$0")"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed"
    exit 1
fi

# 安装依赖
echo "Installing dependencies..."
pip3 install flask python-dotenv requests -q --break-system-packages 2>/dev/null || pip3 install flask python-dotenv requests -q

# 创建输出目录
mkdir -p output

# 启动服务
echo "Starting Amazon Packaging Skill..."
python3 app.py
