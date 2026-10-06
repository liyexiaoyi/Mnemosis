# 可选向量加速

主包保持 NumPy 可选。安装方式（项目根目录）：

```text
python -m pip install ".[vectors]"
```

`VectorIndex` 会探测 NumPy；可用时使用原生数组/矩阵运算，否则保留纯 Python 回退。Python 仍处理维度、缓存、锁、精确扫描预算与 LSH，SQLite 持久化向量。BM25 的 Rust 开关是另一条独立路径。

## 本机 E 盘环境

已将 NumPy 2.5.3 的 CPython 3.14 / Windows x64 wheel 和解压安装目录保存在 E 盘，未通过本轮操作修改系统包或系统 PATH。此轮不同权限下用户包目录可见性不同，所以复现时固定 E 盘依赖路径。其他平台/版本按实际环境安装兼容版本；只声明本机实测。

```powershell
$env:PYTHONPATH = "E:\Mnemosis\repo\src;E:\Mnemosis\tools\python;E:\Mnemosis\tools\numpy"
& C:\Python314\python.exe -c "import numpy; print(numpy.__version__, numpy.__file__)"
```

大数组（至少 1024 项）且只取最多四分之一结果时，先分区再排序少量候选。选中分数有并列、截断边界有并列、存在 NaN/无穷值，或者不满足大小条件时，仍使用原来的 `argsort(-scores)[:top_k]`。因此保留历史 NumPy 排名与分数；并列回退可能产生额外扫描开销。

[NumPy argpartition 文档](https://numpy.org/doc/stable/reference/generated/numpy.argpartition.html) 说明分区结果无序且选择不稳定；[argsort 文档](https://numpy.org/doc/stable/reference/generated/numpy.argsort.html) 说明默认排序并不保证并列稳定性，所以不能仅排序所选候选就声称完全兼容。

历史 NumPy 路径使用 float32，纯 Python 流式路径使用 Python 标量计算；近似相等分数/并列时，两条路径原本就可能有不同排名。优化的严格等价契约是本轮 NumPy 前后结果，不是所有输入上 NumPy/Python 完全相同。超过精确扫描预算仍走 LSH，不能把排序优化等同于全规模无遗漏。

## 验证与测量

`MNEMOSIS_TEST_NUMPY=1` 强制 NumPy 用例缺失时报错；默认允许跳过可选模块。另用显式导入屏蔽验证回退，不能凭删去 PYTHONPATH 就断定 NumPy 不存在。

```text
python benchmarks/vector_kernel_eval.py --baseline <可信的本地旧源码 ZIP> --output <结果 JSON>
```

固定 `OPENBLAS_NUM_THREADS=1`、`MKL_NUM_THREADS=1`，默认七轮交替，分别测缓存完整向量查询、未缓存候选重排、选取内核及现有纯 Python/NumPy 两条路径。数据库/向量准备、首次建矩阵和导入屏蔽准备不计时；保留每个 CPU/墙钟样本并核对数据库与返回值。十万条纯 Python 对照强制精确扫描，不能与默认可能使用 LSH 的路径比较为同样的召回模式。后台负载、操作系统缓存未控制，不报告生产 p95 或市场排名。
