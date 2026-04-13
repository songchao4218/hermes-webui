"""
Hermes WebUI - WSL2 Bridge Module
Handles path conversion between Windows and WSL2 environments
"""

import os
import re
import subprocess
import platform
from pathlib import Path
from typing import Optional, Tuple


class WSLBridge:
    """
    WSL2 environment detection and path conversion bridge.
    Ensures seamless file system access between Windows and WSL2.
    """

    def __init__(self):
        self._is_wsl = None
        self._is_wsl1 = None
        self._windows_home = None
        self._wsl_distro = None
        self._windows_build = None

    @property
    def is_wsl(self) -> bool:
        """Detect if running inside WSL2/WSL1 environment"""
        if self._is_wsl is None:
            self._is_wsl = self._detect_wsl()
        return self._is_wsl

    @property
    def is_wsl1(self) -> bool:
        """Detect if running inside WSL1 (not WSL2)"""
        if self._is_wsl1 is None:
            self._is_wsl1 = self._detect_wsl1()
        return self._is_wsl1

    @property
    def is_wsl2(self) -> bool:
        """Detect if running inside WSL2"""
        return self.is_wsl and not self.is_wsl1

    def _detect_wsl(self) -> bool:
        """Detect WSL environment using multiple methods"""
        # Method 1: Check /proc/version for Microsoft/WSL
        try:
            with open("/proc/version", "r") as f:
                content = f.read().lower()
                if "microsoft" in content or "wsl" in content:
                    return True
        except Exception:
            pass

        # Method 2: Check WSL_DISTRO_NAME environment variable
        if os.environ.get("WSL_DISTRO_NAME"):
            return True

        # Method 3: Check WSL_INTEROP
        if os.environ.get("WSL_INTEROP"):
            return True

        # Method 4: Check for WSL-specific paths
        if Path("/mnt/wsl").exists():
            return True

        return False

    def _detect_wsl1(self) -> bool:
        """Detect WSL1 vs WSL2"""
        if not self.is_wsl:
            return False

        try:
            # WSL2 has /proc/sys/kernel/osrelease with WSL2
            with open("/proc/sys/kernel/osrelease", "r") as f:
                content = f.read().lower()
                if "wsl2" in content:
                    return False  # It's WSL2
                if "microsoft" in content:
                    return True   # It's WSL1
        except Exception:
            pass

        # Fallback: Check for WSL2-specific features
        # WSL2 has a real Linux kernel with /proc/version_signature
        if Path("/proc/version_signature").exists():
            return False  # Likely WSL2

        # Check if we can access Windows executables directly (WSL1 behavior)
        try:
            result = subprocess.run(
                ["cmd.exe", "/c", "echo test"],
                capture_output=True,
                timeout=1
            )
            if result.returncode == 0:
                # Could be either, but more likely WSL1
                pass
        except Exception:
            pass

        return False

    @property
    def wsl_distro(self) -> Optional[str]:
        """Get WSL distribution name"""
        if self._wsl_distro is None:
            self._wsl_distro = os.environ.get("WSL_DISTRO_NAME", "Unknown")
        return self._wsl_distro

    @property
    def windows_home(self) -> Optional[str]:
        """Get Windows user home directory in WSL path format"""
        if self._windows_home is None:
            self._windows_home = self._detect_windows_home()
        return self._windows_home

    def _detect_windows_home(self) -> Optional[str]:
        """
        Detect Windows home directory path in WSL format.
        Returns path like: /mnt/c/Users/Username
        """
        if not self.is_wsl:
            return None

        # Method 1: Use USERPROFILE environment variable
        win_userprofile = os.environ.get("USERPROFILE", "")
        if win_userprofile:
            wsl_path = self.windows_path_to_wsl(win_userprofile)
            if wsl_path and Path(wsl_path).exists():
                return wsl_path

        # Method 2: Use Windows cmd.exe to get USERPROFILE
        try:
            result = subprocess.run(
                ["cmd.exe", "/c", "echo %USERPROFILE%"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                win_path = result.stdout.strip()
                wsl_path = self.windows_path_to_wsl(win_path)
                if wsl_path and Path(wsl_path).exists():
                    return wsl_path
        except Exception:
            pass

        # Method 3: Use wslpath utility
        try:
            result = subprocess.run(
                ["wslpath", "-u", "C:\\Users"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                users_path = result.stdout.strip()
                users_dir = Path(users_path)
                if users_dir.exists():
                    # Find the first non-system user directory
                    for user_dir in sorted(users_dir.iterdir()):
                        if user_dir.is_dir() and user_dir.name not in [
                            "Public", "Default", "All Users",
                            "Default User", "Administrator", "system32"
                        ]:
                            return str(user_dir)
        except Exception:
            pass

        # Method 4: Scan /mnt/ for common drives
        for drive in ["c", "C", "d", "D"]:
            mnt_path = Path(f"/mnt/{drive.lower()}")
            if mnt_path.exists():
                users_dir = mnt_path / "Users"
                if users_dir.exists():
                    for user_dir in sorted(users_dir.iterdir()):
                        if user_dir.is_dir() and user_dir.name not in [
                            "Public", "Default", "All Users",
                            "Default User", "Administrator"
                        ]:
                            return str(user_dir)

        return None

    def windows_path_to_wsl(self, win_path: str) -> Optional[str]:
        r"""
        Convert Windows path to WSL path.

        Examples:
            C:\Users\foo\Desktop -> /mnt/c/Users/foo/Desktop
            C:/Users/foo/Desktop -> /mnt/c/Users/foo/Desktop
            \\wsl$\Ubuntu\home\user -> /home/user
            D:\Projects\test -> /mnt/d/Projects/test
        """
        if not win_path:
            return None

        # Normalize path separators
        path = win_path.replace("\\", "/")

        # Handle \\wsl$\Distro\path format (UNC path to WSL)
        wsl_unc_match = re.match(
            r"//wsl\$/(?P<distro>[^/]+)(?P<wsl_path>/.*)?",
            path,
            re.IGNORECASE
        )
        if wsl_unc_match:
            wsl_path = wsl_unc_match.group("wsl_path") or "/"
            return wsl_path

        # Handle drive letter format (C:/path or C:\path)
        drive_match = re.match(r"^([a-zA-Z]):(/.*)?$", path)
        if drive_match:
            drive = drive_match.group(1).lower()
            rest = drive_match.group(2) or ""
            return f"/mnt/{drive}{rest}"

        # Already a WSL/Unix path
        if path.startswith("/"):
            return path

        return None

    def wsl_path_to_windows(self, wsl_path: str) -> Optional[str]:
        r"""
        Convert WSL path to Windows path.

        Examples:
            /mnt/c/Users/foo/Desktop -> C:\Users\foo\Desktop
            /home/user/project -> \\wsl$\Ubuntu\home\user\project
            /mnt/d/Projects/test -> D:\Projects\test
        """
        if not wsl_path:
            return None

        # Normalize path
        path = wsl_path.replace("\\", "/")

        # Handle /mnt/x/path format
        mnt_match = re.match(r"^/mnt/([a-zA-Z])(/.*)?$", path)
        if mnt_match:
            drive = mnt_match.group(1).upper()
            rest = mnt_match.group(2) or ""
            # Convert forward slashes to backslashes
            win_rest = rest.replace("/", "\\")
            return f"{drive}:{win_rest}"

        # Handle WSL internal paths (e.g., /home/user)
        # Use UNC path format: \\wsl$\Distro\path
        if self.wsl_distro and path.startswith("/"):
            distro = self.wsl_distro
            win_path = path.replace("/", "\\")
            return f"\\\\wsl$\\{distro}{win_path}"

        # Already a Windows path
        if re.match(r"^[a-zA-Z]:", path):
            return path.replace("/", "\\")

        return None

    def convert_user_input(self, user_input: str) -> str:
        """
        Smart conversion of user input containing Windows paths.
        Detects Windows paths and converts them to WSL paths.

        Args:
            user_input: User's message that may contain Windows paths

        Returns:
            Converted string with WSL paths
        """
        if not self.is_wsl or not user_input:
            return user_input

        # Pattern to match Windows paths
        # Matches: C:olderile, C:/folder/file, "C:olderile", 'C:olderile'
        win_path_pattern = r"[\"']?[a-zA-Z]:[\\/](?:[^\\/\s\"']+[\\/])*[^\\/\s\"']*[\"']?"

        def replace_path(match):
            full_match = match.group(0)
            # Remove surrounding quotes if present
            win_path = full_match.strip("\"'")
            wsl_path = self.windows_path_to_wsl(win_path)
            if wsl_path:
                return wsl_path
            return full_match

        # Replace all Windows paths with WSL paths
        converted = re.sub(win_path_pattern, replace_path, user_input)
        return converted

    def convert_output(self, output: str) -> str:
        """
        Convert WSL paths in output back to Windows paths for display.
        Useful for showing paths to Windows users.

        Args:
            output: Text that may contain WSL paths

        Returns:
            Converted string with Windows paths
        """
        if not self.is_wsl or not output:
            return output

        # Pattern to match WSL /mnt paths
        wsl_path_pattern = r"/mnt/[a-zA-Z](?:/[^\s\"']+)*"

        def replace_path(match):
            wsl_path = match.group(0)
            win_path = self.wsl_path_to_windows(wsl_path)
            if win_path:
                return win_path
            return wsl_path

        converted = re.sub(wsl_path_pattern, replace_path, output)
        return converted

    def get_working_directory(self) -> str:
        """
        Get the appropriate working directory for Hermes.
        Prefers Windows home directory so Hermes can access Windows files naturally.
        """
        if self.windows_home:
            return self.windows_home
        return str(Path.home())

    def get_context_prompt(self) -> str:
        """
        Generate a context prompt for the LLM about the WSL2 environment.
        This helps the LLM understand how to access Windows files.
        """
        if not self.is_wsl:
            return ""

        context_parts = ["[系统环境信息：正在 WSL2 中运行。]"]

        if self.windows_home:
            desktop = f"{self.windows_home}/Desktop"
            documents = f"{self.windows_home}/Documents"
            downloads = f"{self.windows_home}/Downloads"

            context_parts.append(f"Windows 主目录: {self.windows_home}")
            context_parts.append(f"Windows 桌面: {desktop}")
            context_parts.append(f"Windows 文档: {documents}")
            context_parts.append(f"Windows 下载: {downloads}")
            context_parts.append("提示：访问 Windows 文件时，请使用上述 /mnt/ 路径。")

        return "\n".join(context_parts)

    def get_status(self) -> dict:
        """Get WSL bridge status for debugging"""
        return {
            "is_wsl": self.is_wsl,
            "is_wsl1": self.is_wsl1,
            "is_wsl2": self.is_wsl2,
            "distro": self.wsl_distro,
            "windows_home": self.windows_home,
            "working_directory": self.get_working_directory(),
        }


# Global instance for easy import
wsl_bridge = WSLBridge()


if __name__ == "__main__":
    # Test the bridge
    print("WSL Bridge Test")
    print("=" * 50)

    bridge = WSLBridge()
    status = bridge.get_status()

    for key, value in status.items():
        print(f"{key}: {value}")

    print("\nPath Conversion Tests:")
    print("-" * 50)

    test_paths = [
        "C:\\Users\\test\\Desktop\\file.txt",
        "C:/Users/test/Documents",
        "D:\\Projects\\code",
        "/mnt/c/Users/test/Desktop",
        "/home/user/project",
    ]

    for path in test_paths:
        wsl = bridge.windows_path_to_wsl(path)
        win = bridge.wsl_path_to_windows(path)
        print(f"Original: {path}")
        print(f"  → WSL:  {wsl}")
        print(f"  → Win:  {win}")
        print()
