#!/usr/bin/env python3
"""
主测试运行器
整合了备份、编译、运行、检查的完整流程
"""

import argparse
import glob
import os
import random
import re
import shlex
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

        self.cargo_cmd, self.rustc_cmd, self.toolchain_issue = self._resolve_toolchain()
        if self.cargo_cmd is None or self.rustc_cmd is None:
            raise RuntimeError(self.toolchain_issue or "No usable cargo/rustc toolchain")
        self.qemu_cmd = self._resolve_qemu_binary()
        self.exec_env = os.environ.copy()
        self._prepare_exec_env()
        
        print(f"\n{'=' * 30}")
        print(f"ustb-os-checker - chapter {chapter}")
        print(f"{'=' * 30}\n")

    def _prepare_exec_env(self):
        path_parts = [p for p in self.exec_env.get("PATH", "").split(":") if p]
        prepend_dirs = []

        qemu_bin_dir = str(Path(self.qemu_cmd).parent)
        prepend_dirs.append(qemu_bin_dir)

        cargo_bin_dir = str(Path(self.cargo_cmd).parent)
        prepend_dirs.append(cargo_bin_dir)

        # Ensure selected bins have highest priority.
        for d in reversed(prepend_dirs):
            if d in path_parts:
                path_parts.remove(d)
            path_parts.insert(0, d)
        self.exec_env["PATH"] = ":".join(path_parts)
        self.exec_env["CARGO_NET_OFFLINE"] = "true"

        self.exec_env["RUSTC"] = self.rustc_cmd

        rustdoc_path = str(Path(cargo_bin_dir) / "rustdoc")
        if os.path.exists(rustdoc_path):
            self.exec_env["RUSTDOC"] = rustdoc_path

    def _probe_exec(self, args, env=None):
        try:
            result = subprocess.run(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=8,
                env=env,
            )
            return result.returncode == 0, (result.stderr or result.stdout or "").strip()
        except Exception as e:
            return False, str(e)

    def _resolve_toolchain(self):
        home = os.environ.get("HOME", "/root")
        cargo_candidates = []

        for c in ["/usr/bin/cargo", "/usr/local/bin/cargo", "/bin/cargo"]:
            if os.path.isfile(c) and os.access(c, os.X_OK):
                cargo_candidates.append(c)

        for pattern in [
            f"{home}/.rustup/toolchains/*/bin/cargo",
            "/usr/local/rustup/toolchains/*/bin/cargo",
            "/opt/rustup/toolchains/*/bin/cargo",
        ]:
            cargo_candidates.extend(sorted(glob.glob(pattern)))

        which_cargo = shutil.which("cargo")
        if which_cargo:
            cargo_candidates.append(which_cargo)

        # dedup while preserving order
        seen = set()
        uniq_candidates = []
        for c in cargo_candidates:
            if c not in seen:
                seen.add(c)
                uniq_candidates.append(c)

        probe_errors = []
        for cargo in uniq_candidates:
            cargo_dir = str(Path(cargo).parent)
            rustc = str(Path(cargo_dir) / "rustc")

            if not (os.path.isfile(cargo) and os.access(cargo, os.X_OK)):
                continue
            if not (os.path.isfile(rustc) and os.access(rustc, os.X_OK)):
                continue

            env = os.environ.copy()
            path_parts = [p for p in env.get("PATH", "").split(":") if p]
            if cargo_dir in path_parts:
                path_parts.remove(cargo_dir)
            path_parts.insert(0, cargo_dir)
            env["PATH"] = ":".join(path_parts)
            env["RUSTC"] = rustc

            ok_rustc, err_rustc = self._probe_exec([rustc, "-vV"], env=env)
            if not ok_rustc:
                probe_errors.append(f"rustc blocked: {rustc} => {err_rustc[:120]}")
                continue

            ok_cargo, err_cargo = self._probe_exec([cargo, "-V"], env=env)
            if not ok_cargo:
                probe_errors.append(f"cargo blocked: {cargo} => {err_cargo[:120]}")
                continue

            return cargo, rustc, None

        details = "; ".join(probe_errors[-6:]) if probe_errors else "no candidates discovered"
        return None, None, f"No usable cargo/rustc pair found under sandbox policy: {details}"

    def _resolve_qemu_binary(self):
        candidates = [
            shutil.which("qemu-system-riscv64"),
            "/root/qemu-9.2.1/build/qemu-system-riscv64",
            "/usr/bin/qemu-system-riscv64",
            "/usr/local/bin/qemu-system-riscv64",
            "/opt/qemu/bin/qemu-system-riscv64",
        ]
        for c in candidates:
            if c and os.path.isfile(c) and os.access(c, os.X_OK):
                return c
        raise RuntimeError("qemu-system-riscv64 not found. Please install it or provide absolute path.")
    
    def run(self):
        try:
            self.create_work_copy()
            self.overwrite_test_programs()
            self.copy_initproc()
            self.setup_environment()
            self.randomize_strings()
            self.overwrite_configs()
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
        
        temp_dirs = [self.work_kernel_dir, self.work_user_dir, 
                     config.TEMP_EASY_FS_LIB_DIR, config.TEMP_EASY_FS_FUSE_DIR,
                     config.TEMP_BOOTLOADER_DIR]
        for temp_dir in temp_dirs:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        
        shutil.copytree(config.KERNEL_DIR, self.work_kernel_dir)
        shutil.copytree(config.USER_DIR, self.work_user_dir)
        
        if config.EASY_FS_LIB_DIR.exists():
            shutil.copytree(config.EASY_FS_LIB_DIR, config.TEMP_EASY_FS_LIB_DIR)
        if config.EASY_FS_FUSE_DIR.exists():
            shutil.copytree(config.EASY_FS_FUSE_DIR, config.TEMP_EASY_FS_FUSE_DIR)
        if config.BOOTLOADER_DIR.exists():
            shutil.copytree(config.BOOTLOADER_DIR, config.TEMP_BOOTLOADER_DIR)
        
        self._run_command(f"make -C {self.work_kernel_dir} clean", check=False)
        self._run_command(f"make -C {self.work_user_dir} clean", check=False)
        
        print("  ✓ Work copy created")
    
    def cleanup(self):
        print("\n→ Cleaning up temp directories...")
        
        temp_dirs = [self.work_kernel_dir, self.work_user_dir,
                     config.TEMP_EASY_FS_LIB_DIR, config.TEMP_EASY_FS_FUSE_DIR,
                     config.TEMP_BOOTLOADER_DIR]
        for temp_dir in temp_dirs:
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
        print(f"  Using qemu binary: {self.qemu_cmd}")
        print(f"  Using cargo binary: {self.cargo_cmd}")
        print(f"  Using rustc binary: {self.rustc_cmd}")

        if not os.path.exists(self.rustc_cmd):
            raise RuntimeError(f"Configured RUSTC not found: {self.rustc_cmd}")

        # Avoid rustup operations in restricted sandbox.
        # Assume image already contains required toolchain/targets.
        print("  Skipping rustup setup in sandbox environment")
        
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
            ("test_file", f"test_file{self.rand_suffix}"),
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
            config.OVERWRITE_DIR / self.chapter_config.get("makefile_user_main", "Makefile-user"),
            self.work_user_dir / "Makefile"
        )
        shutil.copy(
            config.OVERWRITE_DIR / self.chapter_config.get("makefile_user_rust", "Makefile-user-rust"),
            self.work_user_dir / "rust" / "Makefile"
        )
        shutil.copy(
            config.OVERWRITE_DIR / self.chapter_config.get("makefile_user_c", "Makefile-user-c"),
            self.work_user_dir / "c" / "Makefile"
        )
        
        # Overwrite easy-fs-fuse
        if self.chapter_config["easy_fs_fuse"] and config.TEMP_EASY_FS_FUSE_DIR.exists():
            shutil.copy(
                config.OVERWRITE_DIR / self.chapter_config["easy_fs_fuse"],
                config.TEMP_EASY_FS_FUSE_DIR / "src" / "main.rs"
            )
        
        cmd = f"make -C {self.work_user_dir} build"
        
        self._run_command(cmd)
        print("  ✓ User programs built")
    
    def copy_initproc(self):
        print("→ Copying initproc...")
        
        if self.chapter_config["initproc"]:
            src = config.OVERWRITE_DIR / self.chapter_config["initproc"]
            dst = self.work_user_dir / "rust" / "src" / "bin" / "initproc.rs"
            shutil.copy(src, dst)
            print(f"  ✓ {self.chapter_config['initproc']} → initproc.rs")
        else:
            print("  (no initproc override)")

        print("  ✓ initproc copied")
    
    def run_os(self):
        print("→ Running OS...")
        
        stdout_file = config.CHECKER_DIR / f"stdout-ch{self.chapter}"

        # Build kernel directly instead of `make run` to avoid platform sandbox
        # restrictions on spawning shell commands inside Makefile recipes.
        build_cmd = [
            self.cargo_cmd, "build",
            "--release",
            "--target", config.RUST_TARGET,
            "--offline",
        ]
        build_result = subprocess.run(
            build_cmd,
            cwd=self.work_kernel_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=self.exec_env,
        )
        print(build_result.stdout)

        if build_result.returncode != 0:
            build_log = build_result.stdout or ""
            # Offline cache fallback: locked bitflags version may not exist in image cache.
            if (
                "failed to select a version for the requirement `bitflags" in build_log
                and "locked to 2.11.0" in build_log
                and "--offline" in build_log
            ):
                print("  ! Retry kernel build: downgrade locked bitflags to cached 2.10.0")
                update_cmd = [
                    self.cargo_cmd,
                    "update",
                    "-p",
                    "bitflags",
                    "--precise",
                    "2.10.0",
                    "--offline",
                ]
                update_result = subprocess.run(
                    update_cmd,
                    cwd=self.work_kernel_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=self.exec_env,
                )
                print(update_result.stdout)

                if update_result.returncode == 0:
                    build_result = subprocess.run(
                        build_cmd,
                        cwd=self.work_kernel_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        env=self.exec_env,
                    )
                    print(build_result.stdout)

        if build_result.returncode != 0:
            raise RuntimeError("Kernel build failed")

        kernel_bin = self.work_kernel_dir / "target" / config.RUST_TARGET / config.BUILD_MODE / "kernel"
        if not kernel_bin.exists():
            raise RuntimeError(f"Kernel binary not found: {kernel_bin}")

        qemu_cmd = [
            self.qemu_cmd,
            "-machine", "virt",
            "-accel", "tcg,thread=single",
            "-kernel", str(kernel_bin),
            "-nographic",
            "-smp", "1",
        ]

        if self.chapter_config["build_type"] == "elf":
            fs_img = self.work_user_dir / "build" / "fs.img"
            if config.TEMP_EASY_FS_FUSE_DIR.exists():
                fs_cmd = ["cargo", "run", "--release", "--", "-t", "../temp-user/build/"]
                fs_cmd[0] = self.cargo_cmd
                fs_cmd.insert(3, "--offline")
                fs_result = subprocess.run(
                    fs_cmd,
                    cwd=config.TEMP_EASY_FS_FUSE_DIR,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=self.exec_env,
                )
                print(fs_result.stdout)
                if fs_result.returncode != 0:
                    raise RuntimeError("Build fs.img failed")

            if not fs_img.exists():
                raise RuntimeError(f"fs image not found: {fs_img}")

            bios_path = config.TEMP_BOOTLOADER_DIR / "rustsbi-qemu.bin"
            if bios_path.exists():
                qemu_cmd.extend(["-bios", str(bios_path)])
            else:
                qemu_cmd.extend(["-bios", "default"])

            qemu_cmd.extend([
                "-drive", f"file={fs_img},if=none,format=raw,id=x0",
                "-device", "virtio-blk-device,drive=x0,bus=virtio-mmio-bus.0",
            ])
        else:
            qemu_cmd.extend(["-bios", "default"])
        
        with open(stdout_file, "w") as f:
            result = subprocess.run(
                qemu_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=config.QEMU_TIMEOUT_SECONDS,
                env=self.exec_env,
            )
            
            output = result.stdout
            print(output)
            f.write(output)

        if result.returncode != 0:
            raise RuntimeError(f"QEMU run failed with exit code {result.returncode}")
        
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
        if isinstance(cmd, str):
            args = shlex.split(cmd)
        else:
            args = cmd
        result = subprocess.run(args, capture_output=True, text=True, env=self.exec_env)
        
        if check and result.returncode != 0:
            print(result.stdout)
            print(result.stderr)
            raise RuntimeError(f"Command failed: {' '.join(args)}")
        
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
    
    try:
        runner = TestRunner(args.chapter)
        runner.run()
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
