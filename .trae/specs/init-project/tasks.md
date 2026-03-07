# Tasks

- [x] Task 1: 项目初始化与基础架构搭建
  - [x] SubTask 1.1: 创建项目目录结构
  - [x] SubTask 1.2: 创建 requirements.txt 依赖文件
  - [x] SubTask 1.3: 创建应用入口文件 main.py
  - [x] SubTask 1.4: 创建配置管理模块

- [x] Task 2: 数据库与数据模型设计
  - [x] SubTask 2.1: 设计 SQLite 数据库表结构（AI模型配置、测试用例、测试脚本）
  - [x] SubTask 2.2: 创建数据库初始化脚本
  - [x] SubTask 2.3: 创建数据模型类（Model 层）

- [x] Task 3: AI 模型交互模块开发
  - [x] SubTask 3.1: 实现 OpenAI API 兼容的 HTTP 客户端
  - [x] SubTask 3.2: 实现模型连接测试功能
  - [x] SubTask 3.3: 实现测试用例生成的 Prompt 模板
  - [x] SubTask 3.4: 实现测试脚本生成的 Prompt 模板

- [x] Task 4: 核心业务逻辑开发
  - [x] SubTask 4.1: 实现 AI 模型配置管理服务
  - [x] SubTask 4.2: 实现测试用例生成服务
  - [x] SubTask 4.3: 实现测试用例编辑服务
  - [x] SubTask 4.4: 实现测试脚本生成服务
  - [x] SubTask 4.5: 实现导出下载服务

- [x] Task 5: GUI 界面开发
  - [x] SubTask 5.1: 创建主窗口框架
  - [x] SubTask 5.2: 实现 AI 模型配置页面
  - [x] SubTask 5.3: 实现测试用例生成页面
  - [x] SubTask 5.4: 实现测试用例编辑页面
  - [x] SubTask 5.5: 实现测试脚本生成页面
  - [x] SubTask 5.6: 实现导出下载功能界面

- [x] Task 6: 打包与发布配置
  - [x] SubTask 6.1: 创建 PyInstaller 打包配置
  - [x] SubTask 6.2: 编写打包脚本
  - [x] SubTask 6.3: 测试打包后的可执行文件

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 1]
- [Task 4] depends on [Task 2, Task 3]
- [Task 5] depends on [Task 4]
- [Task 6] depends on [Task 5]
