"""Game-dev spot-check (round 253): brand-new domain and dimensions.

Spot-check memory quality of real installed projects on local game-making
content (a Chinese Godot project's dev notes). All dimensions are new and
unrelated to previous benchmarks:

  版本记忆 / 路径命名 / 数值参数 / 场景结构 / 信号连接 / 资源细节 /
  开发时间线 / 报错修复 / 决策原因 / 更新内容

Projects (real installs, same seed, same memories):
  - Mnemosis (this repo)
  - mem0ai 2.0.17 (official PyPI package, DashScope cloud LLM + embeddings)
  - cognitive-memory 0.5.1 (official PyPI package, hash embedder)

Models:
  - cloud: qwen3.7-plus (user-deployed DashScope)
  - local: qwen2.5:3b (Ollama)
  - DeepSeek V4 Flash (agent answers from the exact contexts, written
    separately into work/gamedev_codex_answers.json)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import urllib.request

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType  # noqa: E402

VISION_CONFIG = r"C:\Users\asus\plugins\image-viewer\scripts\vision_config.json"
OLLAMA_URL = "http://127.0.0.1:11434"


DATASET = [
    {
        "content": "项目《星海拾荒者》使用 Godot 4.3 正式版开发，导出平台为 Windows 与 Web。",
        "kind": "semantic",
        "cues": ["星海拾荒者", "Godot", "版本"],
    },
    {
        "content": "项目的 GDScript 主脚本路径是 scripts/player.gd，资源目录是 assets/，场景目录是 scenes/。",
        "kind": "semantic",
        "cues": ["路径", "player.gd"],
    },
    {
        "content": "玩家节点 Player 的移动速度为 320 像素/秒，重力加速度为 1200 像素/秒²。",
        "kind": "semantic",
        "cues": ["Player", "速度"],
    },
    {
        "content": "跳跃力度 Jump 导出变量默认值为 420，双击跳跃判定窗口为 0.15 秒。",
        "kind": "semantic",
        "cues": ["跳跃", "Jump"],
    },
    {
        "content": "主场景 scenes/Main.tscn 的节点树为：Main → World → Player + Camera2D + UI。",
        "kind": "semantic",
        "cues": ["Main.tscn", "节点树"],
    },
    {
        "content": "发射信号 laser_fired 由 Player 发出，连接到 GameManager 的 on_laser_fired 方法。",
        "kind": "semantic",
        "cues": ["信号", "laser_fired"],
    },
    {
        "content": "版本 v0.3.2 更新内容：修复敌人碰撞箱、加入双摇杆输入、减少加载黑屏。",
        "kind": "semantic",
        "cues": ["v0.3.2", "更新"],
    },
    {
        "content": "美术资源背景图 assets/backgrounds/nebula_01.png 是 1920×1080 分辨率。",
        "kind": "semantic",
        "cues": ["背景图", "nebula_01"],
    },
    {
        "content": "音效 assets/sfx/laser.wav 播放时长为 0.4 秒，音量默认 -6 dB。",
        "kind": "semantic",
        "cues": ["音效", "laser.wav"],
    },
    {
        "content": "项目使用自动图集 atlas_16x16，单个精灵图 16×16，共 24 个格子。",
        "kind": "semantic",
        "cues": ["图集", "atlas_16x16"],
    },
    {
        "content": "2026年7月20日，试玩反馈：新手教程太长，玩家在第2关就流失。",
        "kind": "episodic",
        "cues": ["2026-07-20", "试玩反馈"],
    },
    {
        "content": "2026年7月22日，修复了碰撞检测：把敌人碰撞层从 2 改到 3 后穿透消失。",
        "kind": "episodic",
        "cues": ["2026-07-22", "修复"],
    },
    {
        "content": "2026年7月25日，把背景渲染从每帧重绘改成 CanvasLayer 缓存，帧率从 45 提升到 60。",
        "kind": "episodic",
        "cues": ["2026-07-25", "优化"],
    },
    {
        "content": "2026年8月1日，发布 v0.4.0：加入存档系统，存档文件保存在 user://save.json。",
        "kind": "episodic",
        "cues": ["2026-08-01", "存档"],
    },
    {
        "content": "2026年8月3日，测试发现 Linux 导出缺少 libsteam_api.so，游戏启动崩溃。",
        "kind": "episodic",
        "cues": ["2026-08-03", "Linux"],
    },
    {
        "content": "决定用 GDScript 而不是 C#：团队更熟 GDScript，且热重载更快。",
        "kind": "semantic",
        "cues": ["决策", "GDScript"],
    },
    {
        "content": "决定音效用程序生成而不是买素材包：预算只有 2000 元，且版权更干净。",
        "kind": "semantic",
        "cues": ["决策", "音效"],
    },
    {
        "content": "坑：在 _physics_process 里直接改 transform.position 会漏碰撞，应该用 move_and_slide()。",
        "kind": "semantic",
        "cues": ["坑", "move_and_slide"],
    },
]


QUESTIONS = [
    {
        "dim": "版本记忆",
        "q": "《星海拾荒者》用的是哪个 Godot 版本？",
        "answer": "Godot 4.3",
        "terms": ["Godot", "4.3"],
    },
    {
        "dim": "路径命名",
        "q": "玩家主脚本放在哪个路径？主场景文件叫什么？",
        "answer": "scripts/player.gd",
        "terms": ["scripts/player.gd", "Main.tscn"],
    },
    {
        "dim": "数值参数",
        "q": "玩家移动速度和跳跃力度分别是多少？",
        "answer": "320 和 420",
        "terms": ["320", "420"],
    },
    {
        "dim": "场景结构",
        "q": "主场景里 World 节点下面直接挂了哪几个节点？",
        "answer": "Player、Camera2D、UI",
        "terms": ["Player", "Camera2D", "UI"],
    },
    {
        "dim": "信号连接",
        "q": "玩家发射激光时发出的信号叫什么？连到哪个方法？",
        "answer": "laser_fired 连到 on_laser_fired",
        "terms": ["laser_fired", "on_laser_fired"],
    },
    {
        "dim": "资源细节",
        "q": "背景图 nebula_01.png 的分辨率是多少？",
        "answer": "1920×1080",
        "terms": ["1920", "1080"],
    },
    {
        "dim": "开发时间线",
        "q": "2026年7月22日修复了什么问题？",
        "answer": "碰撞穿透",
        "terms": ["碰撞", "穿透"],
    },
    {
        "dim": "报错修复",
        "q": "Linux 导出后启动崩溃，缺了什么文件？",
        "answer": "libsteam_api.so",
        "terms": ["libsteam_api.so"],
    },
    {
        "dim": "决策原因",
        "q": "团队为什么决定用 GDScript 而不是 C#？",
        "answer": "更熟且热重载更快",
        "terms": ["热重载", "更熟"],
    },
    {
        "dim": "更新内容",
        "q": "v0.3.2 除了修复敌人碰撞箱，还更新了什么？",
        "answer": "双摇杆输入",
        "terms": ["双摇杆", "黑屏"],
    },
]


def _norm(text: str) -> str:
    return "".join(str(text).split()).lower()


def hit(texts: list[str], question: dict) -> bool:
    expected = _norm(question["answer"])
    joined = " ".join(_norm(text) for text in texts)
    if expected and expected in joined:
        return True
    terms = [_norm(term) for term in question["terms"]]
    return all(
        any(term in _norm(text) for text in texts) for term in terms
    )


def score_answer(answer: str, question: dict) -> bool:
    return hit([answer], question)


def cloud_generate(prompt: str, max_tokens: int = 200) -> str:
    with open(VISION_CONFIG, encoding="utf-8") as handle:
        cfg = json.load(handle)
    payload = {
        "model": cfg["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    request = urllib.request.Request(
        cfg["base_url"] + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + cfg["api_key"],
        },
    )
    with urllib.request.urlopen(request, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def local_generate(prompt: str) -> str:
    payload = json.dumps(
        {
            "model": "qwen2.5:3b",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_URL + "/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=300) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("response", "").strip()


def _mnemosis_contexts() -> dict[str, list[str]]:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for memory in DATASET:
        engine.remember(
            memory["content"],
            kind=MemoryKind(memory["kind"]),
            source=user,
            cues=memory.get("cues"),
            importance=0.8 if memory["kind"] == "semantic" else 0.6,
        )
    contexts: dict[str, list[str]] = {}
    for question in QUESTIONS:
        results = engine.recall(question["q"], top_k=4)
        contexts[question["q"]] = [r.item.content for r in results]
    return contexts


def _mem0_contexts() -> dict[str, list[str]]:
    os.environ["MEM0_TELEMETRY"] = "False"
    with open(VISION_CONFIG, encoding="utf-8") as handle:
        cfg = json.load(handle)
    from mem0 import Memory

    db_path = os.path.join(_WORK, "gamedev_mem0db")
    if os.path.isdir(db_path):
        shutil.rmtree(db_path)
    config = {
        "llm": {
            "provider": "openai",
            "config": {
                "model": cfg["model"],
                "api_key": cfg["api_key"],
                "openai_base_url": cfg["base_url"],
                "temperature": 0,
            },
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": "text-embedding-v3",
                "api_key": cfg["api_key"],
                "openai_base_url": cfg["base_url"],
            },
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "gamedev_spot",
                "path": db_path,
                "on_disk": True,
                "embedding_model_dims": 1024,
            },
        },
        "history_db_path": os.path.join(_WORK, "gamedev_mem0_history.db"),
    }
    memory = Memory.from_config(config)
    for entry in DATASET:
        memory.add(entry["content"], user_id="u1", infer=False)
    contexts: dict[str, list[str]] = {}
    for question in QUESTIONS:
        resp = memory.search(
            question["q"], filters={"user_id": "u1"}, top_k=4
        )
        results = resp.get("results", [])
        contexts[question["q"]] = [
            r.get("memory", "") if isinstance(r, dict) else str(r)
            for r in results
        ]
    return contexts


def _cognitive_contexts() -> dict[str, list[str]]:
    from cognitive_memory import SyncCognitiveMemory

    memory = SyncCognitiveMemory(embedder="hash")
    for entry in DATASET:
        memory.add(
            entry["content"],
            category="core" if entry["kind"] == "semantic" else "episodic",
        )
    contexts: dict[str, list[str]] = {}
    for question in QUESTIONS:
        resp = memory.search(question["q"], top_k=4)
        contexts[question["q"]] = [
            r.memory.content for r in resp.results
        ]
    return contexts


def _answer_all(contexts: dict) -> tuple[dict, dict]:
    cloud_answers: dict[str, dict] = {}
    local_answers: dict[str, dict] = {}
    for project, rows in contexts.items():
        cloud_answers[project] = {}
        local_answers[project] = {}
        for question in QUESTIONS:
            prompt = (
                "只根据下面的记忆回答，不要编造。"
                "如果记忆里没有答案，就回答：不知道。\n\n"
                "记忆：\n"
                + "\n".join(f"- {text}" for text in rows[question["q"]])
                + f"\n\n问题：{question['q']}"
            )
            try:
                cloud_answers[project][question["q"]] = cloud_generate(prompt)
            except Exception as exc:  # noqa: BLE001
                cloud_answers[project][question["q"]] = f"<error: {exc}>"
            try:
                local_answers[project][question["q"]] = local_generate(prompt)
            except Exception as exc:  # noqa: BLE001
                local_answers[project][question["q"]] = f"<error: {exc}>"
            print(
                f"  [{project}] {question['q'][:24]} cloud/local done",
                flush=True,
            )
    return cloud_answers, local_answers


def _retrieval_summary(contexts: dict) -> dict:
    summary: dict[str, dict] = {}
    for project, rows in contexts.items():
        by_dim: dict[str, list[int]] = {}
        for question in QUESTIONS:
            by_dim.setdefault(question["dim"], []).append(
                1 if hit(rows[question["q"]], question) else 0
            )
        summary[project] = {
            "total": sum(
                value
                for values in by_dim.values()
                for value in values
            ),
            "per_dim": {
                dim: round(sum(values) / len(values), 3)
                for dim, values in by_dim.items()
            },
        }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-answers",
        action="store_true",
        help="only build contexts and retrieval summary",
    )
    args = parser.parse_args()
    os.makedirs(_WORK, exist_ok=True)
    contexts = {
        "mnemosis": _mnemosis_contexts(),
        "mem0": _mem0_contexts(),
        "cognitive": _cognitive_contexts(),
    }
    retrieval = _retrieval_summary(contexts)
    out: dict = {
        "domain": "本机游戏制作(Godot)",
        "dimensions": [q["dim"] for q in QUESTIONS],
        "contexts": contexts,
        "retrieval": retrieval,
    }
    if not args.skip_answers:
        print("answering with cloud qwen3.7-plus + local qwen2.5:3b ...")
        cloud_answers, local_answers = _answer_all(contexts)
        out["answers_cloud"] = cloud_answers
        out["answers_local"] = local_answers
        out["accuracy_cloud"] = {
            project: {
                "total": sum(
                    1
                    for q in QUESTIONS
                    if score_answer(cloud_answers[project][q["q"]], q)
                ),
                "per_dim": {
                    dim: round(
                        sum(
                            1
                            for q in QUESTIONS
                            if q["dim"] == dim
                            and score_answer(
                                cloud_answers[project][q["q"]], q
                            )
                        )
                        / max(
                            1,
                            sum(1 for q in QUESTIONS if q["dim"] == dim),
                        ),
                        3,
                    )
                    for dim in out["dimensions"]
                },
            }
            for project in contexts
        }
        out["accuracy_local"] = {
            project: {
                "total": sum(
                    1
                    for q in QUESTIONS
                    if score_answer(local_answers[project][q["q"]], q)
                ),
                "per_dim": {
                    dim: round(
                        sum(
                            1
                            for q in QUESTIONS
                            if q["dim"] == dim
                            and score_answer(
                                local_answers[project][q["q"]], q
                            )
                        )
                        / max(
                            1,
                            sum(1 for q in QUESTIONS if q["dim"] == dim),
                        ),
                        3,
                    )
                    for dim in out["dimensions"]
                },
            }
            for project in contexts
        }
    path = os.path.join(_WORK, "gamedev_spot.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(out, handle, ensure_ascii=False, indent=2)
    print(json.dumps(retrieval, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
