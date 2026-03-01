# USTB-OS-Checker

与 [USTB-OS-Kernel](https://github.com/USTB-806/ustb-os-kernel) 配套的评测系统.

## 本地测试

以执行 Lab3 的测试为例，在本地执行：

```shell
cd /oslab && git clone https://github.com/USTB-806/ustb-os-checker.git
cd ustb-os-checker
make test CHAPTER=3
```

其中运行结果将保存至 `stdout-ch3` 文件中.

## 云端评测

在云端评测系统上将执行

```shell
cd /oslab/ustb-os-checker && make judge CHAPTER=3
```

当输出

```json
{
    "verdict": "AC", 
    "score": 100, 
    "comment": "chapter 3 passed", 
    "detail": "..."
}
```

即为成功.