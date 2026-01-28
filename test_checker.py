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


def test(expected: list, not_expected: list = None):
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
    
    test(expected, not_expected)


if __name__ == "__main__":
    main()
