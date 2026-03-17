#!/usr/bin/env python3
"""
测试规则检查器
从TOML配置读取测试规则并验证输出
"""

import argparse
import sys
import re
from pathlib import Path

# 兼容Python 3.10和3.11+
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print("Error: tomli library is necessary")
        print("Try to run: pip install tomli")
        sys.exit(1)


def load_test_rules(toml_file: str = "test_rules.toml") -> dict:
    toml_path = Path(__file__).parent / toml_file
    with open(toml_path, 'rb') as f:
        return tomllib.load(f)


def resolve_rules(chapter: str, all_rules: dict) -> tuple:
    """
    解析章节的完整测试规则（处理继承和排除）
    返回: (expected, not_expected)
    """
    if chapter not in all_rules:
        raise ValueError(f"Chapter {chapter} test rule does not exist")
    
    rules = all_rules[chapter]
    expected = []
    not_expected = []
    
    if 'inherit_from' in rules:
        parent_expected, parent_not_expected = resolve_rules(
            rules['inherit_from'], all_rules
        )
        expected.extend(parent_expected)
        not_expected.extend(parent_not_expected)
    
    if 'expected' in rules:
        expected.extend(rules['expected'])
    
    if 'not_expected' in rules:
        not_expected.extend(rules['not_expected'])
    
    if 'exclude' in rules:
        exclude_set = set(rules['exclude'])
        expected = [e for e in expected if e not in exclude_set]
    
    # dedup
    expected = list(dict.fromkeys(expected))
    not_expected = list(dict.fromkeys(not_expected))    

    return expected, not_expected


def parse_pattern(pattern: str) -> str:
    """
    解析模式字符串
    如果是 r"..." 格式，返回正则表达式
    否则返回转义后的普通字符串
    """
    pattern = pattern.strip()
    
    if pattern.startswith('r"') and pattern.endswith('"'):
        return pattern[2:-1]  # r" and "
    elif pattern.startswith("r'") and pattern.endswith("'"):
        return pattern[2:-1]  # r' and '
    else:
        return re.escape(pattern)


def check_stride_fairness(output: str) -> tuple:
    """
    校验 stride 调度结果是否合理。
    规则：
    1) 必须拿到 priority 5..10 共6组结果；
    2) count 应随 priority 增大而明显增大（count10/count5 >= 1.5）；
    3) count/priority 的归一化值应大致一致（最大相对偏差 <= 30%）。
    """
    line_re = re.compile(r"priority\s*=\s*(\d+)\s*,\s*exitcode\s*=\s*(\d+)\s*,\s*ratio\s*=\s*(\d+)")
    matches = line_re.findall(output)

    if not matches:
        return False, "stride output lines not found"

    # Keep the latest count for each priority.
    by_prio = {}
    for prio_s, count_s, _ratio_s in matches:
        prio = int(prio_s)
        count = int(count_s)
        by_prio[prio] = count

    required = [5, 6, 7, 8, 9, 10]
    missing = [p for p in required if p not in by_prio]
    if missing:
        return False, f"missing stride priorities: {missing}"

    c5 = by_prio[5]
    c10 = by_prio[10]
    if c5 <= 0:
        return False, "invalid stride sample: priority 5 count <= 0"

    growth = c10 / c5
    if growth < 1.5:
        return False, f"stride scaling too weak: count10/count5 = {growth:.3f} (< 1.5)"

    normalized = [by_prio[p] / p for p in required]
    mean_norm = sum(normalized) / len(normalized)
    if mean_norm <= 0:
        return False, "invalid normalized mean <= 0"

    max_rel_dev = max(abs(v - mean_norm) / mean_norm for v in normalized)
    if max_rel_dev > 0.30:
        return False, f"stride ratio unstable: max relative deviation = {max_rel_dev:.3f} (> 0.30)"

    return True, (
        f"stride fairness OK: count10/count5={growth:.3f}, "
        f"max_rel_dev={max_rel_dev:.3f}"
    )


def test(chapter: str, expected: list, not_expected: list = None):
    """
    测试输出是否符合预期
    
    Args:
        expected: 期望出现的模式列表
        not_expected: 不应该出现的模式列表
    """
    if not_expected is None:
        not_expected = []
    
    print(f"Expected: {expected}")
    print(f"Not expected: {not_expected}")
    
    # read 1MB until EOF
    output = sys.stdin.read(1000000)
    
    count = 0
    total = len(expected) + len(not_expected)
    
    for pattern in expected:
        parsed_pattern = parse_pattern(pattern)
        if re.search(parsed_pattern, output):
            count += 1
            print(f'\033[92m[PASS]\033[0m found <{pattern}>')
        else:
            print(f'\033[91m[FAIL]\033[0m not found <{pattern}>')
    
    for pattern in not_expected:
        parsed_pattern = parse_pattern(pattern)
        if not re.search(parsed_pattern, output):
            count += 1
            print(f'\033[92m[PASS]\033[0m not found <{pattern}>')
        else:
            print(f'\033[91m[FAIL]\033[0m found <{pattern}>')

    # Extra semantic check for stride scheduling tests.
    has_stride_pattern = 'r"priority = \\d+, exitcode = \\d+, ratio = \\d+"' in expected
    if has_stride_pattern and chapter in "ch5":
        total += 1
        ok, msg = check_stride_fairness(output)
        if ok:
            count += 1
            print(f'\033[92m[PASS]\033[0m {msg}')
        else:
            print(f'\033[91m[FAIL]\033[0m {msg}')
    
    print(f'\nTest passed: {count}/{total}')
    
    if count != total:
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_checker.py <chapter>")
        print("Such as: python3 test_checker.py ch3")
        sys.exit(1)
    
    chapter = sys.argv[1]
    
    all_rules = load_test_rules()
    expected, not_expected = resolve_rules(chapter, all_rules)
    
    test(chapter, expected, not_expected)


if __name__ == "__main__":
    main()
