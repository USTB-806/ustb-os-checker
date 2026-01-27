"""
ustb-os-checker 统一配置文件
所有路径、章节配置、测试规则都在这里定义
"""

import os
from pathlib import Path

RUST_TARGET = "riscv64gc-unknown-none-elf"
BUILD_MODE = "release"

QEMU_TIMEOUT_SECONDS = 30

# /path/to/ustb-os-kernel/ustb-os-checker/
CHECKER_DIR = Path(__file__).parent.absolute()

# /path/to/ustb-os-kernel/
KERNEL_ROOT_DIR = CHECKER_DIR.parent
KERNEL_DIR = KERNEL_ROOT_DIR / "kernel"
USER_DIR = KERNEL_ROOT_DIR / "user"

OVERWRITE_DIR = CHECKER_DIR / "overwrite"
CHECK_DIR = CHECKER_DIR / "check"

TEMP_KERNEL_DIR = CHECKER_DIR / "temp-os"
TEMP_USER_DIR = CHECKER_DIR / "temp-user"

# - build_type: 用户程序构建类型 ("bin" 或 "elf")
# - makefile: 使用的 Makefile 文件名 (位于 overwrite/ 目录)
# - initproc: 是否需要复制 initproc (初始进程，ch5+ 进程管理需要)
# - test_programs: 需要从 check/ 覆盖的测试程序列表

CHAPTER_CONFIG = {
    1: {
        "build_type": "bin",              
        "makefile": "Makefile-ch3",       
        "initproc": False,              
        "test_programs": [],              
    },
    2: {
        "build_type": "bin",
        "makefile": "Makefile-ch3",
        "initproc": False,
        "test_programs": [],
    },
    3: {
        "build_type": "bin",
        "makefile": "Makefile-ch3",
        "initproc": False,
        "test_programs": [
            "rust/ch3_usertest.rs",
        ],
    },
    4: {
        "build_type": "elf",
        "makefile": "Makefile-ch3",
        "initproc": False,
        "test_programs": [
            "rust/ch4_usertest.rs",
        ],
    },
    5: {
        "build_type": "elf",
        "makefile": "Makefile-ch3",
        "initproc": True,
        "test_programs": [
            "rust/ch5_usertest.rs",
        ],
    },
}

def get_chapter_config(chapter: int) -> dict:
    if chapter not in CHAPTER_CONFIG:
        raise ValueError(f"Unsupported chapter: {chapter}")
    return CHAPTER_CONFIG[chapter].copy()


def validate_paths():
    errors = []
    
    if not KERNEL_DIR.exists():
        errors.append(f"OS directory does not exist: {KERNEL_DIR}")
    
    if not USER_DIR.exists():
        errors.append(f"User program directory does not exist: {USER_DIR}")
    
    if not OVERWRITE_DIR.exists():
        errors.append(f"Checker overwrite directory does not exist: {OVERWRITE_DIR}")
    
    if errors:
        raise FileNotFoundError("\n".join(errors))


if __name__ == "__main__":
    print(f"Checker directory: {CHECKER_DIR}")
    print(f"OS directory: {KERNEL_DIR}")
    print(f"User program directory: {USER_DIR}")
    
    print("\nChapter Configuration:")
    for ch, cfg in CHAPTER_CONFIG.items():
        print(f"  ch{ch}: build={cfg['build_type']}, "
              f"makefile={cfg['makefile']}, initproc={cfg['initproc']}")
    
    print("\nPath validity:")
    try:
        validate_paths()
        print("  ✓ All paths are correct!")
    except FileNotFoundError as e:
        print(f"  ✗ Wrong paths:\n{e}")
