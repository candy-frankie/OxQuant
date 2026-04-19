# OxQuant Phase 2 部署指南

## 📦 项目状态

恭喜！OxQuant Phase 2 开发已经完成。以下是已实现的核心功能：

### ✅ 已完成的功能
1. **市场数据管理** - 支持Yahoo Finance和加密货币交易所
2. **AI策略生成** - 集成OpenAI GPT-4的智能策略生成
3. **现代化前端** - React + TypeScript + Tailwind CSS界面
4. **完整测试套件** - 单元测试和集成测试
5. **生产部署配置** - Docker + Nginx + Celery

## 🚀 快速部署

### 选项1: 使用现有代码（推荐）
你已经有了完整的代码库，可以直接使用：

```bash
# 1. 进入项目目录
cd ~/OxQuant

# 2. 设置环境变量
cp .env.example .env
# 编辑.env文件，添加你的配置：
# OPENAI_API_KEY=你的OpenAI密钥
# SECRET_KEY=随机生成的密钥

# 3. 启动服务
docker-compose up -d

# 4. 访问应用
# 前端: http://localhost:3000
# API: http://localhost:8000
# API文档: http://localhost:8000/docs
```

### 选项2: 从GitHub获取最新代码
```bash
# 1. 克隆仓库（如果你还没有）
git clone https://github.com/candy-frankie/OxQuant.git
cd OxQuant

# 2. 切换到Phase 2分支
git checkout phase2-development

# 3. 按照选项1的步骤继续
```

## 🔧 配置说明

### 必需的环境变量
```bash
# .env文件内容示例
DATABASE_URL=postgresql://oxquant:oxquant123@localhost:5432/oxquant
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-你的OpenAI密钥
SECRET_KEY=你的随机密钥（至少32字符）
```

### 可选配置
```bash
# 生产环境设置
ENVIRONMENT=production
DEBUG=false

# CORS设置
BACKEND_CORS_ORIGINS=["http://localhost:3000"]

# 数据源设置
DEFAULT_DATA_SOURCE=yahoo
CACHE_TTL=3600
```

## 📊 验证部署

### 检查服务状态
```bash
docker-compose ps
```

应该看到以下服务运行：
- ✅ postgres (数据库)
- ✅ redis (缓存)
- ✅ api (FastAPI后端)
- ✅ ui (React前端)

### 测试API端点
```bash
# 测试健康检查
curl http://localhost:8000/api/v1/health

# 测试市场数据API
curl -X POST http://localhost:8000/api/v1/data/fetch \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "interval": "1d",
    "start_date": "2024-01-01",
    "end_date": "2024-01-10"
  }'
```

### 访问Web界面
1. 打开浏览器访问 http://localhost:3000
2. 注册新用户
3. 开始使用平台功能

## 🎯 核心功能使用指南

### 1. 市场数据管理
- **获取数据**: 在Market Data页面选择符号和时间范围
- **技术指标**: 自动计算MA、RSI、MACD等指标
- **数据缓存**: 重复请求使用缓存数据，提高性能

### 2. AI策略生成
- **生成策略**: 在AI Strategies页面描述你的需求
- **优化策略**: 对现有策略进行AI优化
- **分析结果**: AI分析回测结果并提供建议

### 3. 策略回测
- **配置参数**: 设置初始资金、手续费等
- **运行回测**: 一键运行策略回测
- **查看结果**: 详细的性能指标和图表

### 4. 投资组合管理
- **创建组合**: 组合多个策略
- **风险管理**: 设置风险参数和止损
- **监控性能**: 实时监控组合表现

## 🔍 故障排除

### 常见问题

#### 1. Docker容器启动失败
```bash
# 查看日志
docker-compose logs

# 重新构建镜像
docker-compose build --no-cache
docker-compose up -d
```

#### 2. 数据库连接问题
```bash
# 检查数据库状态
docker-compose exec postgres psql -U oxquant -d oxquant -c "\l"

# 运行数据库迁移
docker-compose exec api alembic upgrade head
```

#### 3. OpenAI API错误
- 检查 `.env` 文件中的 `OPENAI_API_KEY`
- 确认OpenAI账户有足够的额度
- 检查网络连接

#### 4. 前端无法访问
```bash
# 检查前端服务
docker-compose logs ui

# 重新构建前端
cd src/ui
npm run build
```

## 📈 性能优化

### 生产环境建议
1. **数据库优化**
   ```bash
   # 增加PostgreSQL内存
   shared_buffers = 256MB
   work_mem = 16MB
   ```

2. **Redis缓存**
   ```bash
   # 配置Redis持久化
   save 900 1
   save 300 10
   save 60 10000
   ```

3. **Nginx配置**
   ```nginx
   # 启用Gzip压缩
   gzip on;
   gzip_types text/plain text/css application/json application/javascript;
   ```

### 监控设置
1. **应用监控**
   ```bash
   # 使用Prometheus + Grafana
   docker-compose -f docker-compose.monitoring.yml up -d
   ```

2. **日志管理**
   ```bash
   # 集中日志收集
   docker-compose -f docker-compose.logging.yml up -d
   ```

## 🔄 更新和维护

### 定期维护任务
1. **数据库备份**
   ```bash
   docker-compose exec postgres pg_dump -U oxquant oxquant > backup.sql
   ```

2. **日志清理**
   ```bash
   # 清理旧日志
   find /var/log/oxquant -name "*.log" -mtime +30 -delete
   ```

3. **依赖更新**
   ```bash
   # 更新Python依赖
   docker-compose exec api pip list --outdated
   docker-compose exec api pip install -U package_name
   ```

### 版本升级
```bash
# 1. 备份当前版本
git tag v2.0.0
git push origin v2.0.0

# 2. 拉取最新代码
git pull origin main

# 3. 更新服务
docker-compose down
docker-compose pull
docker-compose up -d
```

## 🆘 获取帮助

### 文档资源
- **API文档**: http://localhost:8000/docs
- **开发文档**: `docs/` 目录
- **代码注释**: 详细的代码注释

### 问题反馈
1. 检查现有问题: GitHub Issues
2. 提交新问题: 提供详细的重现步骤
3. 社区支持: GitHub Discussions

### 紧急联系
- **严重故障**: 立即停止交易
- **数据丢失**: 从备份恢复
- **安全事件**: 重置所有密钥

## 🎉 开始使用

现在你已经成功部署了OxQuant Phase 2！以下是下一步建议：

### 初学者
1. 浏览Web界面，熟悉各个功能
2. 使用示例策略进行回测
3. 阅读教程文档

### 进阶用户
1. 创建自定义策略
2. 使用AI生成新策略
3. 配置自动化交易

### 开发者
1. 阅读架构文档
2. 贡献代码或功能
3. 集成第三方服务

---

**部署成功！** 🚀

你的OxQuant量化交易平台现在已经完全运行。开始探索强大的AI驱动交易策略吧！

如果有任何问题，请参考文档或联系支持。

祝交易顺利！ 📈

---
*最后更新: 2024年*
*版本: 2.0.0*
*状态: 生产环境就绪*