# 接任意 LLM（记忆检索 + 强模型回答）

Mnemosis 是记忆层：检索由它负责，回答可以交给任何更强的模型。

## 原理

1. `recall_fused(question, top_k=5)` 用融合检索（关键词 + ngram + 可选向量）找出最相关的记忆；
2. 把记忆拼进提示词，只要求 LLM“依据这些记忆回答”；
3. 记忆里没有答案时，模型应回答 unknown，而不是编造。

这样记忆能力与模型能力解耦：换模型不用换记忆层，换记忆层不用换模型。

## 示例

```bash
# 本地 Ollama（默认）
python examples/demo_llm.py --db memory.db --question "用户喜欢什么语言？"

# 任意 OpenAI 兼容云端模型
set LLM_BASE_URL=https://your-endpoint/v1
set LLM_MODEL=your-model
set LLM_API_KEY=your-key
python examples/demo_llm.py --db memory.db --question "用户喜欢什么语言？"
```

## 实测上限参考（LongMemEval-S，20 题，同一套检索上下文）

| 回答模型 | 准确率 |
| --- | ---: |
| DeepSeek V4 Flash（强模型） | 90-95% |
| qwen3.7-plus（云端） | 55% |
| gemma3:12b（本地） | 65% |
| qwen2.5:3b（本地小模型） | 45% |

结论：检索上下文给越强的模型，收益越大；小模型也能用，但上限受模型本身能力限制。
