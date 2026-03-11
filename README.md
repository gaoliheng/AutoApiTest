# AutoApiTest

一个基于AI的接口自动化测试平台

## 项目简介

AutoApiTest 是一个基于 PyQt6 的桌面应用程序，集成了 AI 功能，用于自动化接口测试。支持测试用例管理、测试脚本生成、AI 模型配置等功能。

## 功能特性

- 测试用例管理：创建、编辑、删除测试用例
- 测试脚本生成：基于测试用例自动生成测试脚本
- AI 模型配置：支持配置和管理多个 AI 模型
- 数据导出：支持导出测试用例数据
- 本地数据库：使用 SQLite 存储测试数据

## 环境要求

- Python 3.8+
- Windows 操作系统

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行项目

### 开发模式运行

```bash
python src/main.py
```

## 打包成 EXE

项目提供了完整的打包脚本，可以将项目打包成独立的 Windows 可执行文件。

详细的打包说明请参考：[build_scripts/BUILD.md](build_scripts/BUILD.md)

### 快速打包

```bash
cd build_scripts
python build.py
```

打包完成后，可执行文件位于 `dist/AutoApiTest.exe`。

## 项目结构

```
AutoApiTest/
├── src/                    # 源代码目录
│   ├── ai/                # AI 相关模块
│   ├── core/              # 核心业务逻辑
│   ├── models/            # 数据模型
│   ├── ui/                # UI 界面
│   └── utils/             # 工具模块
├── build_scripts/         # 打包脚本目录
│   ├── build.py          # 打包脚本
│   └── AutoApiTest.spec  # PyInstaller 配置文件
├── data/                  # 数据目录（运行时生成）
├── exports/               # 导出文件目录
├── doc/                   # 文档目录
├── tests/                 # 测试目录
├── requirements.txt       # 依赖列表
└── README.md             # 项目说明文档
```

## 开发说明

### 代码规范

- 使用 Python 类型提示
- 遵循 PEP 8 代码风格
- 使用 PyQt6 进行界面开发

### 数据库

项目使用 SQLite 数据库，数据库文件位于 `data/autotest.db`。

### 配置文件

配置文件位于 `data/config.yaml`，包含：
- 数据库路径
- 默认 AI 模型 ID
- 其他用户设置

## 许可证

MIT License
