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
EASY_FS_LIB_DIR = KERNEL_ROOT_DIR / "easy-fs"
EASY_FS_FUSE_DIR = KERNEL_ROOT_DIR / "easy-fs-fuse"

OVERWRITE_DIR = CHECKER_DIR / "overwrite"
CHECK_DIR = CHECKER_DIR / "check"

TEMP_KERNEL_DIR = CHECKER_DIR / "temp-os"
TEMP_USER_DIR = CHECKER_DIR / "temp-user"
TEMP_EASY_FS_LIB_DIR = CHECKER_DIR / "easy-fs"
TEMP_EASY_FS_FUSE_DIR = CHECKER_DIR / "temp-easy-fs-fuse"

# - build_type: 用户程序构建类型 ("bin" 或 "elf")
# - makefile: 使用的 Makefile 文件名 (位于 overwrite/ 目录)
# - makefile_user_main: user/Makefile
# - makefile_user_rust: user/rust/Makefile
# - makefile_user_c: user/c/Makefile
# - initproc: 是否需要复制 initproc (初始进程，ch5+ 进程管理需要)
# - test_programs: 需要从 check/ 覆盖的测试程序列表

CHAPTER_CONFIG = {
    2: {
        "build_type": "bin",
        "makefile": "Makefile-ch2",
        "makefile_user_c": "Makefile-user-c-ch2",
        "makefile_user_rust": "Makefile-user-rust-ch2",
        "initproc": None,
        "easy_fs_fuse": None,
        "test_programs": [
            "rust/bad_address.rs",
            "rust/hello_world.rs",
            "rust/power.rs",
            "c/hello.c",
            "c/read.c",
        ],
    },
    3: {
        "build_type": "bin",
        "makefile": "Makefile-ch2",
        "makefile_user_c": "Makefile-user-c-ch3",
        "makefile_user_rust": "Makefile-user-rust-ch2",
        "initproc": None,
        "easy_fs_fuse": None,
        "test_programs": [
            "rust/ch3b_yield0.rs",
            "rust/ch3b_yield1.rs",
            "rust/ch3b_yield2.rs",
            "c/trace_simple.c",
            "c/trace.c"
        ],
    },
    4: {
        "build_type": "elf",
        "makefile": "Makefile-ch4",
        "makefile_user_c": "Makefile-user-c-ch4",
        "makefile_user_rust": "Makefile-user-rust-ch4",
        "initproc": None,
        "easy_fs_fuse": "easy-fs-fuse.rs",
        "test_programs": [
            "rust/initproc_stage1.rs",
            "rust/ch4b_sbrk.rs",
            "rust/ch4_mmap0.rs",
            "rust/ch4_mmap1.rs",
            "rust/ch4_mmap2.rs",
            "rust/ch4_mmap3.rs",
            "rust/ch4_ummap0.rs",
            "rust/ch4_ummap1.rs",
        ],
    },
    5: {
        "build_type": "elf",
        "makefile": "Makefile-ch2",
        "initproc": True,
        "easy_fs_fuse": None,
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
