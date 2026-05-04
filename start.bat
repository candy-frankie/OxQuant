@echo off
REM OxQuant 一键启动脚本 (Windows)

setlocal enabledelayedexpansion

:show_help
echo OxQuant 一键启动脚本
echo.
echo 用法: %~nx0 [选项]
echo.
echo 选项:
echo   --help, -h          显示帮助信息
echo   --local, -l         本地直接启动（推荐）
echo   --install, -i       安装依赖
echo   --test, -t          运行测试
echo.
echo 示例:
echo   %~nx0 --local       本地启动API服务
echo   %~nx0 --install     安装依赖
goto :eof

:install_dependencies
echo 正在安装依赖...
pip install -r requirements.slim.txt
echo 依赖安装完成！
goto :eof

:run_local
echo 正在启动OxQuant本地服务...

REM 检查依赖
python -c "import fastapi" 2>nul || (
    echo 依赖未安装，请先运行: %~nx0 --install
    exit /b 1
)

REM 创建数据目录
if not exist data mkdir data

REM 设置环境变量
set ENVIRONMENT=development
set DATABASE_URL=sqlite:///./data/oxquant.db
set API_HOST=0.0.0.0
set API_PORT=8000

REM 启动API服务
echo 启动API服务，访问地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
goto :eof

:run_tests
echo 正在运行测试...
pytest tests/ -v
echo 测试完成！
goto :eof

REM 解析参数
if "%1"=="" goto show_help

if "%1"=="--help" goto show_help
if "%1"=="-h" goto show_help

if "%1"=="--local" goto run_local
if "%1"=="-l" goto run_local

if "%1"=="--install" goto install_dependencies
if "%1"=="-i" goto install_dependencies

if "%1"=="--test" goto run_tests
if "%1"=="-t" goto run_tests

echo 未知选项: %1
goto show_help
@echo off
REM OxQuant 一键启动脚本 (Windows)

setlocal enabledelayedexpansion

:show_help
echo OxQuant 一键启动脚本
echo.
echo 用法: %~nx0 [选项]
echo.
echo 选项:
echo   --help, -h          显示帮助信息
echo   --local, -l         本地直接启动（推荐）
echo   --install, -i       安装依赖
echo   --test, -t          运行测试
echo.
echo 示例:
echo   %~nx0 --local       本地启动API服务
echo   %~nx0 --install     安装依赖
goto :eof

:install_dependencies
echo 正在安装依赖...
pip install -r requirements.slim.txt
echo 依赖安装完成！
goto :eof

:run_local
echo 正在启动OxQuant本地服务...

REM 检查依赖
python -c "import fastapi" 2>nul || (
    echo 依赖未安装，请先运行: %~nx0 --install
    exit /b 1
)

REM 创建数据目录
if not exist data mkdir data

REM 设置环境变量
set ENVIRONMENT=development
set DATABASE_URL=sqlite:///./data/oxquant.db
set API_HOST=0.0.0.0
set API_PORT=8000

REM 启动API服务
echo 启动API服务，访问地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
goto :eof

:run_tests
echo 正在运行测试...
pytest tests/ -v
echo 测试完成！
goto :eof

REM 解析参数
if "%1"=="" goto show_help

if "%1"=="--help" goto show_help
if "%1"=="-h" goto show_help

if "%1"=="--local" goto run_local
if "%1"=="-l" goto run_local

if "%1"=="--install" goto install_dependencies
if "%1"=="-i" goto install_dependencies

if "%1"=="--test" goto run_tests
if "%1"=="-t" goto run_tests

echo 未知选项: %1
goto show_help