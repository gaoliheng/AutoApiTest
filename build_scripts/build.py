#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], cwd: Path | None = None) -> bool:
    print(f"执行命令: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            capture_output=False,
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")
        return False


def clean_build_files(project_root: Path) -> None:
    print("清理临时文件...")
    dirs_to_clean = ["build", "dist", "__pycache__"]
    for dir_name in dirs_to_clean:
        dir_path = project_root / dir_name
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"  已删除: {dir_path}")
    
    for pycache in project_root.rglob("__pycache__"):
        if pycache.is_dir():
            shutil.rmtree(pycache)
            print(f"  已删除: {pycache}")


def install_dependencies(project_root: Path) -> bool:
    print("\n安装依赖...")
    requirements_path = project_root / "requirements.txt"
    return run_command([sys.executable, "-m", "pip", "install", "-r", str(requirements_path), "-U"])


def build_executable(project_root: Path) -> bool:
    print("\n开始打包...")
    spec_file = project_root / "build_scripts" / "AutoApiTest.spec"
    if not spec_file.exists():
        print(f"错误: 找不到 spec 文件: {spec_file}")
        return False
    
    return run_command(
        [sys.executable, "-m", "PyInstaller", str(spec_file), "--clean"],
        cwd=project_root,
    )


def print_build_result(project_root: Path) -> None:
    dist_dir = project_root / "dist"
    exe_path = dist_dir / "AutoApiTest.exe"
    
    print("\n" + "=" * 50)
    print("打包完成!")
    print("=" * 50)
    
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"可执行文件: {exe_path}")
        print(f"文件大小: {size_mb:.2f} MB")
    else:
        print(f"输出目录: {dist_dir}")
        if dist_dir.exists():
            for item in dist_dir.iterdir():
                print(f"  - {item.name}")


def main() -> int:
    build_scripts_dir = Path(__file__).parent.resolve()
    project_root = build_scripts_dir.parent.resolve()
    
    print("=" * 50)
    print("AutoApiTest 打包脚本")
    print("=" * 50)
    print(f"项目目录: {project_root}")
    print(f"脚本目录: {build_scripts_dir}")
    
    clean_build_files(project_root)
    
    if not install_dependencies(project_root):
        print("错误: 依赖安装失败")
        return 1
    
    if not build_executable(project_root):
        print("错误: 打包失败")
        return 1
    
    print_build_result(project_root)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
