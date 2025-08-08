@echo off
echo 🚀 启动USTB教务助手前端...
echo.

cd client

echo 📦 检查依赖...
if not exist node_modules (
    echo 📥 安装依赖包...
    npm install
)

echo 🌐 启动开发服务器...
echo 前端地址: http://localhost:3000
echo RAG系统地址: http://localhost:8000
echo.
echo 💡 请确保RAG系统已启动 (端口8000)
echo.

npm start
