# 打包说明文档

本文档详细说明如何将 AutoApiTest 项目打包成独立的 Windows 可执行文件。

## 环境要求

- Python 3.8+
- Windows 操作系统
- 已安装所有项目依赖

## 打包步骤

### 1. 安装依赖

确保已安装所有项目依赖：

```bash
pip install -r requirements.txt
```

### 2. 进入打包脚本目录

```bash
cd build_scripts
```

### 3. 运行打包脚本

```bash
python build.py
```

## 打包脚本说明

`build.py` 脚本会自动完成以下操作：

1. **清理旧的构建文件**
   - 删除 `build/` 目录
   - 删除 `dist/` 目录
   - 删除所有 `__pycache__` 目录

2. **安装/更新项目依赖**
   - 使用 `pip install -r requirements.txt -U` 更新所有依赖

3. **使用 PyInstaller 打包项目**
   - 读取 `AutoApiTest.spec` 配置文件
   - 执行打包命令
   - 生成独立的 EXE 文件

## 打包后的文件结构

打包完成后，会在项目根目录下生成 `dist` 文件夹，结构如下：

```
dist/
├── AutoApiTest.exe    # 主程序（约 90MB）
└── data/              # 数据目录（首次运行时自动生成）
    └── autotest.db    # 数据库文件
```

## 使用打包后的程序

### 运行程序

1. 直接双击 `dist/AutoApiTest.exe` 运行程序
2. 或在命令行中运行：`dist\AutoApiTest.exe`

### 数据存储

1. 首次运行时会在程序所在目录下自动创建 `data` 文件夹
2. 数据库文件 `autotest.db` 会自动创建在 `data/` 目录中
3. 所有数据（测试用例、AI 模型配置等）都存储在 `data/autotest.db` 中
4. 配置文件 `config.yaml` 也会存储在 `data/` 目录中

### 移动程序

如果需要移动程序到其他位置：
- 整个 `dist/` 文件夹可以一起移动
- 或者只移动 `AutoApiTest.exe`，程序会在新位置自动创建 `data/` 目录

## 打包配置详解

### 配置文件位置

打包配置文件位于 `build_scripts/AutoApiTest.spec`

### 主要配置项

```python
# 入口文件
['src/main.py']

# 模块搜索路径
pathex=['src']

# 数据文件
datas=[
    ('data', 'data'),                    # 数据目录
    ('src/ui/styles.py', 'src/ui'),    # UI 样式文件
]

# 隐式导入（确保所有模块都被正确打包）
hiddenimports=[
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'httpx',
    'openai',
    'yaml',
    'pytest',
    'allure',
    # ... 所有项目模块
]

# 单文件打包
exe = EXE(
    ...
    name='AutoApiTest',
    console=False,        # 无控制台窗口
    ...
)
```

### 配置说明

- **入口文件**：`src/main.py` 是程序的入口点
- **模块搜索路径**：`pathex=['src']` 确保能找到所有模块
- **数据文件**：打包时包含必要的资源文件
- **隐式导入**：显式列出所有需要打包的模块
- **单文件打包**：所有依赖打包在一个 EXE 文件中
- **无控制台窗口**：GUI 应用程序不显示控制台窗口

## 常见问题

### 1. 打包失败

**问题**：打包过程中出现错误

**解决方案**：
- 确保所有依赖都已正确安装
- 检查 `AutoApiTest.spec` 文件是否正确
- 查看错误日志，根据错误信息排查问题

### 2. 运行 EXE 时找不到模块

**问题**：运行打包后的 EXE 时提示找不到某个模块

**解决方案**：
- 在 `AutoApiTest.spec` 的 `hiddenimports` 中添加该模块
- 重新运行打包脚本

### 3. 数据库文件找不到

**问题**：程序启动时提示找不到数据库文件

**解决方案**：
- 确保程序有写入权限
- 检查 `data/` 目录是否正确创建
- 查看 `src/utils/config.py` 中的路径配置

### 4. EXE 文件太大

**问题**：打包后的 EXE 文件大小约为 90MB

**说明**：
- 这是正常的，因为包含了所有依赖库（PyQt6、httpx、openai 等）
- PyInstaller 会将所有依赖打包到一个文件中
- 可以通过排除不需要的模块来减小体积，但可能会影响功能

### 5. 首次运行慢

**问题**：首次运行 EXE 时启动较慢

**说明**：
- 这是正常的，因为需要解压临时文件
- 后续运行会快一些
- 如果使用杀毒软件，可能会影响启动速度

## 高级配置

### 修改打包选项

如果需要修改打包配置，编辑 `build_scripts/AutoApiTest.spec` 文件：

#### 启用控制台窗口

将 `console=False` 改为 `console=True`，可以看到调试信息。

#### 添加图标

在 `EXE` 配置中添加 `icon='path/to/icon.ico'`。

#### 排除不需要的模块

在 `excludes=[]` 中添加不需要的模块，可以减小文件大小。

### 单文件 vs 目录模式

当前配置使用单文件模式（所有内容在一个 EXE 中）。

如果需要使用目录模式（多个文件），修改 `EXE` 配置：

```python
exe = EXE(
    ...
    onefile=False,    # 改为 False
    ...
)
```

目录模式的优点：
- 启动更快
- 更容易调试
- 文件更新更方便

目录模式的缺点：
- 需要分发多个文件
- 用户需要保持文件结构完整

## 打包脚本代码说明

### build.py 主要函数

- `run_command()`: 执行命令并返回结果
- `clean_build_files()`: 清理旧的构建文件
- `install_dependencies()`: 安装/更新依赖
- `build_executable()`: 执行 PyInstaller 打包
- `print_build_result()`: 打印打包结果信息

### 自定义打包脚本

如果需要自定义打包流程，可以修改 `build.py` 文件。例如：

- 添加版本号到 EXE 文件名
- 自动复制文件到发布目录
- 生成安装程序
- 执行自动化测试

## 版本控制

以下文件应该提交到 Git：

- `build_scripts/build.py` - 打包脚本
- `build_scripts/AutoApiTest.spec` - 打包配置
- `build_scripts/BUILD.md` - 本文档

以下文件不应该提交到 Git（已在 `.gitignore` 中）：

- `build/` - 临时构建文件
- `dist/` - 打包输出
- `*.spec` - 其他生成的 spec 文件

## 参考资料

- [PyInstaller 官方文档](https://pyinstaller.org/)
- [PyQt6 官方文档](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [Python 打包最佳实践](https://packaging.python.org/)

## 更新日志

- 2026-03-11: 创建打包脚本和文档
- 2026-03-11: 修复打包后的路径问题
- 2026-03-11: 整理打包文件到 build_scripts 目录
