#!/bin/bash
# OxQuant 快速启动脚本

set -e

echo "🚀 启动 OxQuant 量化交易平台..."
echo "======================================"

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: Docker未安装"
    echo "请先安装Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ 错误: Docker Compose未安装"
    echo "请先安装Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# 检查环境变量文件
if [ ! -f .env ]; then
    echo "📝 创建环境变量文件..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "⚠️  请编辑 .env 文件，添加你的OpenAI API密钥和其他配置"
        echo "    nano .env  # 或使用其他编辑器"
        read -p "按回车键继续（编辑完成后）..."
    else
        echo "❌ 错误: .env.example 文件不存在"
        exit 1
    fi
fi

# 检查必要的环境变量
if grep -q "OPENAI_API_KEY=your_openai_api_key_here" .env; then
    echo "⚠️  警告: 请设置有效的OpenAI API密钥"
    echo "    获取密钥: https://platform.openai.com/api-keys"
fi

if grep -q "SECRET_KEY=changeme" .env; then
    echo "⚠️  警告: 请设置强密码作为SECRET_KEY"
    echo "    生成命令: openssl rand -hex 32"
fi

# 启动服务
echo "📦 启动Docker服务..."
docker-compose up -d

echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."
if docker-compose ps | grep -q "Up"; then
    echo "✅ 服务启动成功！"
else
    echo "❌ 服务启动失败，查看日志:"
    docker-compose logs --tail=20
    exit 1
fi

# 运行数据库迁移
echo "🗄️  初始化数据库..."
docker-compose exec api alembic upgrade head 2>/dev/null || echo "⚠️  数据库迁移可能已运行"

# 显示访问信息
echo ""
echo "======================================"
echo "🎉 OxQuant 启动完成！"
echo ""
echo "🌐 访问地址:"
echo "   前端界面: http://localhost:3000"
echo "   API服务: http://localhost:8000"
echo "   API文档: http://localhost:8000/docs"
echo "   Flower监控: http://localhost:5555"
echo ""
echo "🔧 管理命令:"
echo "   查看日志: docker-compose logs -f"
echo "   停止服务: docker-compose down"
echo "   重启服务: docker-compose restart"
echo "   查看状态: docker-compose ps"
echo ""
echo "📚 文档:"
echo "   部署指南: cat DEPLOYMENT_GUIDE.md"
echo "   开发总结: cat DEVELOPMENT_SUMMARY.md"
echo ""
echo "💡 提示:"
echo "   1. 首次访问请在前端界面注册账号"
echo "   2. 确保.env文件中的OpenAI API密钥有效"
echo "   3. 查看日志排查问题: docker-compose logs"
echo ""
echo "======================================"
echo "开始你的量化交易之旅吧！ 📈"
echo ""

# 可选：打开浏览器
read -p "是否打开浏览器访问前端界面？ (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v xdg-open &> /dev/null; then
        xdg-open "http://localhost:3000"
    elif command -v open &> /dev/null; then
        open "http://localhost:3000"
    else
        echo "请手动打开浏览器访问: http://localhost:3000"
    fi
fi