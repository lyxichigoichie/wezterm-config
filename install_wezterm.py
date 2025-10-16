#!/usr/bin/env python3

import platform
import urllib.request
from pathlib import Path
import subprocess
import sys
import zipfile
import tempfile
import shutil

# WezTerm软件包URL字典
wezterm_package_urls = {
    "macos": {
        "arm64": "https://github.com/wezterm/wezterm/releases/download/20240203-110809-5046fc22/WezTerm-macos-20240203-110809-5046fc22.zip",
    },
    "Ubuntu": {
        "22": {
            "amd64": "https://github.com/wezterm/wezterm/releases/download/20240203-110809-5046fc22/wezterm-20240203-110809-5046fc22.Ubuntu22.04.deb",
            "arm64": "https://github.com/wezterm/wezterm/releases/download/20240203-110809-5046fc22/wezterm-20240203-110809-5046fc22.Ubuntu22.04.arm64.deb"
        },
        "20": {
            "amd64": "https://github.com/wezterm/wezterm/releases/download/20240203-110809-5046fc22/wezterm-20240203-110809-5046fc22.Ubuntu20.04.deb",
        },
    },
    "Debian": {
        "12": {
            "amd64": "https://github.com/wezterm/wezterm/releases/download/20240203-110809-5046fc22/wezterm-20240203-110809-5046fc22.Debian12.deb",
            "arm64": "https://github.com/wezterm/wezterm/releases/download/20240203-110809-5046fc22/wezterm-20240203-110809-5046fc22.Debian12.arm64.deb"
        },
        "11": {
            "amd64": "https://github.com/wezterm/wezterm/releases/download/20240203-110809-5046fc22/wezterm-20240203-110809-5046fc22.Debian11.deb"
        }
    }
}

def get_system_info():
    """检测操作系统、版本和CPU架构。"""
    system = platform.system()
    architecture = platform.machine()
    if architecture in ("x86_64", "AMD64"):
        arch_key = "amd64"
    elif architecture in ("aarch64", "arm64"):
        arch_key = "arm64"
    else:
        arch_key = None

    if system == "Darwin":
        return "macos", None, arch_key
    elif system == "Linux":
        try:
            with open("/etc/os-release") as f:
                lines = f.readlines()
            os_release = {key: value.strip('"') for key, value in (line.strip().split("=", 1) for line in lines if "=" in line)}
            return os_release.get("ID").capitalize(), os_release.get("VERSION_ID", "").split('.')[0], arch_key
        except (FileNotFoundError, IOError):
            return "Linux", None, arch_key
    else:
        return system, None, arch_key

def find_download_url(os_name, os_version, arch, packages_dict):
    """根据系统信息在字典中查找对应的下载URL。"""
    print(f"正在为您的系统查找软件包: 系统={os_name}, 版本={os_version}, 架构={arch}")
    if os_name == "macos":
        return packages_dict.get("macos", {}).get(arch)
    elif os_name in ("Ubuntu", "Debian"):
        return packages_dict.get(os_name, {}).get(os_version, {}).get(arch)
    else:
        return None

def download_and_install(url):
    """从给定的URL下载文件，并根据文件类型尝试自动安装。"""
    if not url:
        print("错误：未提供有效的下载链接。")
        return False
    download_path = None
    try:
        file_name = Path(url).name
        download_path = Path.cwd() / file_name
        print(f"准备下载: {file_name}")
        urllib.request.urlretrieve(url, str(download_path))
        print(f"下载成功！文件已保存为: {download_path}")
        if file_name.endswith(".deb"):
            print("\n检测到 .deb 软件包，将尝试使用 apt-get 进行安装...")
            subprocess.run(["sudo", "apt-get", "install", "-y", f"./{file_name}"], check=True)
            print(f"软件包 '{file_name}' 安装成功！")
        elif file_name.endswith(".zip") and platform.system() == "Darwin":
            print("\n检测到 .zip 压缩包，将尝试自动解压并移动到 /Applications...")
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(download_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                app_path = next(Path(temp_dir).glob("*.app"), None)
                if not app_path:
                    raise FileNotFoundError("在压缩包中未能找到 .app 文件。")
                dest_app_path = Path("/Applications") / app_path.name
                if dest_app_path.exists():
                    print(f"发现已存在的应用，将先进行移除: {dest_app_path}")
                    subprocess.run(["sudo", "rm", "-rf", str(dest_app_path)], check=True)
                print(f"正在移动 {app_path.name} 到 {dest_app_path}...")
                subprocess.run(["sudo", "mv", str(app_path), str(dest_app_path)], check=True)
                print("应用程序安装成功！")
        return True
    except Exception as e:
        print(f"安装过程中发生错误: {e}")
        return False
    finally:
        if download_path and download_path.exists():
            print(f"清理已下载的临时文件: {download_path}")
            download_path.unlink()

def apply_wezterm_configuration():
    """
    下载并安装推荐的字体和配置文件。
    """
    print("\n--- 开始配置 WezTerm ---")
    
    # 1. 确定用户字体目录
    system = platform.system()
    if system == "Linux":
        font_dir = Path.home() / ".local" / "share" / "fonts"
    elif system == "Darwin":  # macOS
        font_dir = Path.home() / "Library" / "Fonts"
    else:
        print(f"不支持的操作系统 '{system}'，跳过字体安装。")
        font_dir = None

    if font_dir:
        print(f"字体将安装到: {font_dir}")
        font_dir.mkdir(parents=True, exist_ok=True)

        # 2. 创建下载目录
        download_dir = Path.home() / "Downloads" / "wezterm"
        download_dir.mkdir(parents=True, exist_ok=True)
        print(f"下载目录: {download_dir}")

        try:
            # 3. 安装 JetBrainsMono Nerd Font
            print("\n正在下载 JetBrainsMono Nerd Font...")
            jetbrains_url = "https://github.com/ryanoasis/nerd-fonts/releases/download/v3.4.0/JetBrainsMono.zip"
            jetbrains_zip_path = download_dir / "JetBrainsMono.zip"
            urllib.request.urlretrieve(jetbrains_url, jetbrains_zip_path)
            
            extract_dir = download_dir / "JetBrainsMono"
            with zipfile.ZipFile(jetbrains_zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            print("正在安装 JetBrainsMono 字体...")
            for font_file in extract_dir.glob("*.ttf"):
                shutil.move(str(font_file), font_dir)
            print("JetBrainsMono 字体安装成功。")
            
            # 清理
            shutil.rmtree(extract_dir)
            jetbrains_zip_path.unlink()

            # 4. 安装 Fandol 中文字体
            print("\n正在下载 Fandol 中文字体...")
            fandol_dir = download_dir / "Fando"
            fandol_dir.mkdir(exist_ok=True)
            fandol_urls = [
                "https://mirrors.ctan.org/fonts/fandol/FandolBraille-Display.otf",
                "https://mirrors.ctan.org/fonts/fandol/FandolBraille-Regular.otf",
                "https://mirrors.ctan.org/fonts/fandol/FandolFang-Regular.otf",
                "https://mirrors.ctan.org/fonts/fandol/FandolHei-Bold.otf",
                "https://mirrors.ctan.org/fonts/fandol/FandolHei-Regular.otf",
                "https://mirrors.ctan.org/fonts/fandol/FandolKai-Regular.otf",
                "https://mirrors.ctan.org/fonts/fandol/FandolSong-Bold.otf",
                "https://mirrors.ctan.org/fonts/fandol/FandolSong-Regular.otf"
            ]
            for url in fandol_urls:
                filename = fandol_dir / Path(url).name
                print(f"  - 下载 {filename.name}")
                urllib.request.urlretrieve(url, filename)
            
            print("正在安装 Fandol 字体...")
            for font_file in fandol_dir.glob("*.otf"):
                shutil.move(str(font_file), font_dir)
            print("Fandol 字体安装成功。")
            
            # 清理
            shutil.rmtree(fandol_dir)

        except Exception as e:
            print(f"字体安装过程中发生错误: {e}")

    # 5. 克隆 Wezterm 配置
    if shutil.which("git"):
        print("\n正在克隆 wezterm-config 配置文件...")
        repo_url = "https://github.com/lyxichigoichie/wezterm-config.git"
        config_dir = Path.home() / ".config" / "wezterm"
        
        try:
            if config_dir.exists():
                print(f"警告: 发现已存在的配置目录 '{config_dir}'。")
                backup_dir = config_dir.with_suffix(".bak")
                if backup_dir.exists():
                    shutil.rmtree(backup_dir)
                shutil.move(str(config_dir), str(backup_dir))
                print(f"已将其备份到 '{backup_dir}'。")
            
            subprocess.run(["git", "clone", repo_url, str(config_dir)], check=True)
            print("配置文件克隆成功！")
        except Exception as e:
            print(f"克隆配置文件时发生错误: {e}")
    else:
        print("\n警告: 未找到 'git' 命令，跳过配置文件克隆。")
    
    print("\n--- WezTerm 配置完成 ---")
    print("请重启您的 WezTerm 实例以使所有更改生效。")

if __name__ == "__main__":
    os_name, os_version, arch = get_system_info()

    if not arch:
        print(f"错误: 无法识别您的系统架构 ({platform.machine()})。")
        sys.exit(1)

    url = find_download_url(os_name, os_version, arch, wezterm_package_urls)

    if not url:
        print("抱歉，在列表中没有找到适合您系统的 WezTerm 软件包。")
        sys.exit(1)

    install_successful = download_and_install(url)
    
    if install_successful:
        try:
            choice = input("\nWezTerm 安装成功。是否要继续进行字体和配置文件的自动配置？(y/N): ").lower()
            if choice == 'y':
                apply_wezterm_configuration()
            else:
                print("跳过自动配置。脚本执行完毕。")
        except KeyboardInterrupt:
            print("\n操作已取消。跳过自动配置。")