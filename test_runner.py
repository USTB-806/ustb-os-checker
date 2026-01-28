#!/usr/bin/env python3
"""
主测试运行器
整合了备份、编译、运行、检查的完整流程
"""

import argparse
import os
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

import config


class TestRunner:
    def __init__(self, chapter: int):
        self.chapter = chapter
        self.chapter_config = config.get_chapter_config(chapter)
        
        self.rand_suffix = str(random.randint(0, 65535))
        
        self.work_kernel_dir = config.TEMP_KERNEL_DIR
        self.work_user_dir = config.TEMP_USER_DIR
        
        print(f"\n{'=' * 30}")
        print(f"ustb-os-checker - chapter {chapter}")
        print(f"{'=' * 30}\n")
    
    def run(self):
        try:
            self.create_work_copy()
            self.overwrite_test_programs()
            self.setup_environment()
            self.randomize_strings()
            self.overwrite_configs()
            self.copy_initproc() if self.chapter_config["initproc"] else None
            self.run_os()
            self.check_output()
            
            print(f"\n{'=' * 30}")
            print("✓ Test passed!")
            print(f"{'=' * 30}\n")
            
        except Exception as e:
            print(f"\n{'=' * 30}")
            print(f"✗ Test failed: {e}")
            print(f"{'=' * 30}\n")
            raise
        finally:
            self.cleanup()
    
    def create_work_copy(self):
        print("→ Creating work copy...")
        
        for temp_dir in [self.work_kernel_dir, self.work_user_dir]:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        
        shutil.copytree(config.KERNEL_DIR, self.work_kernel_dir)
        shutil.copytree(config.USER_DIR, self.work_user_dir)
        
        self._run_command(f"make -C {self.work_kernel_dir} clean", check=False)
        self._run_command(f"make -C {self.work_user_dir} clean", check=False)
        
        print("  ✓ Work copy created")
    
    def cleanup(self):
        print("\n→ Cleaning up temp directories...")
        
        for temp_dir in [self.work_kernel_dir, self.work_user_dir]:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        
        print("  ✓ Cleanup finished")
    
    def overwrite_test_programs(self):
        test_programs = self.chapter_config.get("test_programs", [])
        
        if not test_programs:
            print("→ No test programs to overwrite")
            return
        
        print(f"→ Overwriting test programs ({len(test_programs)} total)...")
        
        for program_path in test_programs:
            src_file = config.CHECK_DIR / program_path
            
            # Determine target directory
            if program_path.startswith("rust/"):
                dst_file = self.work_user_dir / "rust" / "src" / "bin" / Path(program_path).name
            elif program_path.startswith("c/"):
                dst_file = self.work_user_dir / "c" / "apps" / Path(program_path).name
            else:
                print(f"  ! Warning: Unknown program type: {program_path}")
                continue
            
            if not src_file.exists():
                raise FileNotFoundError(f"Standard test program not found: {src_file}")
            
            # Overwrite
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src_file, dst_file)
            print(f"  ✓ {Path(program_path).name}")
        
        print("  ✓ Test programs overwritten")
    
    def setup_environment(self):
        print("→ Setting up Rust environment...")
        
        print("  Setting nightly toolchain...")
        self._run_command("rustup default nightly")
        
        # Check and install riscv64gc target
        result = subprocess.run(
            ["rustup", "target", "list"],
            capture_output=True,
            text=True
        )
        
        if "riscv64gc-unknown-none-elf (installed)" not in result.stdout:
            print("  Installing riscv64gc-unknown-none-elf target...")
            self._run_command("rustup target add riscv64gc-unknown-none-elf")
        
        # Install cargo-binutils
        print("  Checking cargo-binutils...")
        self._run_command("cargo install cargo-binutils --locked", check=False)
        
        # Add components
        self._run_command("rustup component add rust-src")
        self._run_command("rustup component add llvm-tools-preview")
        
        print("  ✓ Environment setup finished")
    
    def randomize_strings(self):
        print(f"→ Randomizing output strings (suffix: {self.rand_suffix})...")
        
        # Randomize Rust files
        for rs_file in self.work_user_dir.rglob("rust/src/bin/*.rs"):
            self._randomize_file(rs_file)
        
        # Randomize C files
        for c_file in self.work_user_dir.rglob("c/apps/*.c"):
            self._randomize_file(c_file)
        
        print("  ✓ Randomization finished")
    
    def _randomize_file(self, file_path: Path):
        content = file_path.read_text()
        replacements = [
            ("OK", f"OK{self.rand_suffix}"),
            ("passed", f"passed{self.rand_suffix}"),
            ("Success", f"Success{self.rand_suffix}"),
            ("completed", f"completed{self.rand_suffix}"),
        ]
        for old, new in replacements:
            content = content.replace(old, new)
        file_path.write_text(content)
    
    def overwrite_configs(self):
        print("→ Overwriting config files...")
        
        # Overwrite kernel build.rs
        build_file = "build-elf.rs" if self.chapter_config["build_type"] == "elf" else "build-bin.rs"
        shutil.copy(
            config.OVERWRITE_DIR / build_file,
            self.work_kernel_dir / "build.rs"
        )
        
        # Overwrite kernel Makefile
        makefile = self.chapter_config["makefile"]
        shutil.copy(
            config.OVERWRITE_DIR / makefile,
            self.work_kernel_dir / "Makefile"
        )
        
        # Overwrite user Makefiles
        shutil.copy(
            config.OVERWRITE_DIR / "Makefile-user",
            self.work_user_dir / "Makefile"
        )
        shutil.copy(
            config.OVERWRITE_DIR / "Makefile-user-rust",
            self.work_user_dir / "rust" / "Makefile"
        )
        shutil.copy(
            config.OVERWRITE_DIR / "Makefile-user-c",
            self.work_user_dir / "c" / "Makefile"
        )
        
        # Overwrite easy-fs-fuse
        if self.chapter_config["easy_fs_fuse"]:
            work_easy_fs_fuse = self.work_kernel_dir / "easy-fs-fuse"
            shutil.copy(
                config.OVERWRITE_DIR / self.chapter_config["easy_fs_fuse"],
                work_easy_fs_fuse / "src" / "main.rs"
            )
        
        cmd = f"make -C {self.work_user_dir} build"
        
        self._run_command(cmd)
        print("  ✓ User programs built")
    
    def copy_initproc(self):
        print("→ Copying initproc...")
        
        src_elf = (self.work_user_dir / "build" / "elf" / 
                   f"ch{self.chapter}_usertest.elf")
        dst_elf = (self.work_user_dir / "build" / "elf" / 
                   f"ch{self.chapter}b_initproc.elf")
        
        shutil.copy(src_elf, dst_elf)
        print("  ✓ initproc copied")
    
    def run_os(self):
        print("→ Running OS...")
        
        stdout_file = config.CHECKER_DIR / f"stdout-ch{self.chapter}"
        
        cmd = f"make -C {self.work_kernel_dir} run"
        
        with open(stdout_file, "w") as f:
            result = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=config.QEMU_TIMEOUT_SECONDS
            )
            
            output = result.stdout
            print(output)
            f.write(output)
        
        self.stdout_file = stdout_file
        print("  ✓ OS run finished")
    
    def check_output(self):
        """Check if output matches expectations"""
        print("→ Checking output...")
        
        chapter_name = f"ch{self.chapter}"
        
        with open(self.stdout_file, "r") as f:
            result = subprocess.run(
                [sys.executable, "test_checker.py", chapter_name],
                stdin=f,
                capture_output=True,
                text=True,
                cwd=config.CHECKER_DIR
            )
        
        print(result.stdout)
        
        if result.returncode != 0:
            raise RuntimeError("Output check failed")
        
        print("  ✓ Output check passed")
    
    def _run_command(self, cmd: str, check: bool = True):
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if check and result.returncode != 0:
            print(result.stdout)
            print(result.stderr)
            raise RuntimeError(f"Command failed: {cmd}")
        
        return result
    
    def _append_to_file(self, file_path: Path, content: str):
        with open(file_path, "a") as f:
            f.write("\n")
            f.write(content)


def main():
    parser = argparse.ArgumentParser(description="ustb-os-checker test runner")
    parser.add_argument("chapter", type=int, help="chapter number (1-5)")
    args = parser.parse_args()
    
    # Validate paths
    try:
        config.validate_paths()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    runner = TestRunner(args.chapter)
    
    try:
        runner.run()
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
        runner.cleanup()
        sys.exit(1)
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
