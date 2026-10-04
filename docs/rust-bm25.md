# 可选 Rust BM25 内核

Python 主包和默认行为保持原样。Rust 仅驻留词频倒排、长度统计、BM25 评分与 Top-k；分词、来源、时间、强化、遗忘、睡眠和数据库操作仍由 Python 执行。

```python
from mnemosis import MemoryEngine
engine = MemoryEngine("memory.db", bm25_backend="rust", auto_warmup=False)
results = engine.recall_bm25("tea coffee", top_k=5)
# 也适用于会调用 BM25 的融合召回。返回分数仍表示相关性。
engine.bm25_backend = "python"  # 明确回退；下一次查询重建单个缓存
engine.close()
```

默认 `bm25_backend="python"`，无需 Rust 或扩展包。显式请求 Rust 而扩展缺失/版本不兼容时抛出含回退办法的 ImportError，避免将 Python 运行误计为 Rust。

## 构建和安装

扩展单独打包，不改变主项目的 setuptools 安装。需要 Rust 工具链、Python 和 maturin：

```text
python -m maturin build --release --manifest-path native/bm25/Cargo.toml
python -m pip install <生成的 wheel 路径>
```

本机从 E 盘使用源码与扩展：

```powershell
$env:PYTHONPATH = "E:\Mnemosis\repo\src;E:\Mnemosis\tools\python"
& C:\Python314\python.exe your_script.py
```

本机可重复构建脚本：`native/bm25/build-local.ps1`。它使用已安装的 E 盘工具链，锁定 Cargo 依赖并设置 `PYO3_USE_RAW_DYLIB=0`，采用现有 CPython 导入库；GNU 最小工具链未提供独立汇编器，此链接选项已通过 release 打包与实际加载验证。[PyO3 变更说明](https://pyo3.rs/v0.29.2/changelog.html)

本机工具链、打包工具、wheel 和评测均置于 `E:\Mnemosis`，不修改系统 PATH。具体构建命令与工具版本记录在同日评测日志；其他用户按自己平台准备编译环境。只有当前 Windows x64 / CPython 3.14 环境经过实测；不声称已提供其他平台或 Python 版本的 wheel。

## 等价和边界

词项由现有 `tokenize(content) + cues` 计数。查询词去重后排序；idf、平均长度、参数、逐词累加顺序与 Python 一致。排序按分数降序、seq 升序、id 字符序。Unicode ID 顺序与 Python Unicode 标量字符序一致。缓存仍跟踪词法版本和有界变化日志，回收/恢复、其他连接和回滚沿用原机制；后端切换会重建缓存，最多保留一种 kind。

原生序号使用有符号 64 位，词频/长度使用无符号 64 位；异常输入明确报错，不静默截断。原生参数限定有限 k1>0 与 0≤b≤1；普通引擎沿用 k1=1.5、b=0.75。扩展模块版本号防止加载不匹配接口。源码不含自写 unsafe；PyO3 管理 Python 绑定和 Rust 借用，评分时释放 GIL。

验证扩展已加载：

```text
python -c "import _mnemosis_rust; print(_mnemosis_rust.__file__, _mnemosis_rust.BUILD_PROFILE)"
```

默认测试在扩展未安装时跳过原生用例。原生交付检查设置 `MNEMOSIS_TEST_RUST=1`，使缺失扩展变成测试失败，不能用跳过代替通过。

性能对照脚本：`benchmarks/rust_bm25_eval.py --database <已有合成SQLite> --output <新目录>`。七轮交替计时包含边界转换；完整查询还包含令牌检查与读取最新 MemoryItem。Rust 内部 `search_timed` 单独记录评分、Top-k 与 Rust 输出分配，开始/结束时刻位于类型转换以内；生产查询不启用此计时。冷建每后端仅一次探索性观测，不能据此称冷启动加速。进程内存数字包括同时存活的两份索引，不等于 Rust 堆或单索引内存。准确率、独立盲测和市场排名不属于本轮结论。
