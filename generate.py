#!/usr/bin/env python3
"""归墟实验室 · 项目总目录生成器

用法：
    python generate.py

依赖：本机已安装并登录 `gh` CLI（https://cli.github.com/）。
逻辑：拉取 GitHub 仓库元数据（公开/私有、语言、更新时间），
      与 CATEGORIES 里的人工分类和简介合并，重新生成 README.md。
"""

import base64
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta

# ---- 分类配置 ----------------------------------------------------------
# 顺序即 README 中的章节顺序。emoji 为章节标题前缀。
CATEGORIES = [
    ("AI 与智能体", "🧠", [
        ("oneact", "幕 · OneAct — AI 原生演示文档格式 `.act` 与渲染运行时，AI 声明式生成、多 Agent 协作编排"),
        ("Mirror-surface", "AI 角色扮演工作台：单人对话、多人圆桌、完整辩论赛，一键蒸馏角色为 SKILL 文件"),
        ("multimodal-learning-space-agent", "多模态学习空间智能体：一句岗位任务生成可交互网页学习空间，含知识库与评测"),
        ("self-distillation", "自我蒸馏：29,814 条微信聊天记录 → 可运行的人格底座"),
        ("TokenPlan", "AI 编码工具 Token 消耗汇总看板：自动采集、趋势与费用估算，全本地运行"),
        ("fuxi-new-api", "fuxi-new-api：new-api 改造版 LLM API 网关（Go 后端 + React 前端）"),
    ]),
    ("数据与量化", "📊", [
        ("quant-alphalens", "AlphaLens AI · LLM 与量化双引擎的 A股/基金/港股智能投研终端"),
        ("mihealth-api", "小米运动健康数据工具：17 类健康数据同步 SQLite，HTTP 接口与看板"),
        ("wechat-article-exporter", "公众号后台文章导出：扫码登录、Cookie 复用、JSON/CSV 输出"),
        ("WeChat-Moments-scraping-tool", "朋友圈数据多维度分析：社交图谱、情感分析、足迹地图"),
        ("TikTok-user-profile", "抖音数据采集与本地画像分析"),
        ("PDF-Figure-Extractor", "论文 PDF 图片提取，figure 与 caption 一并导出"),
    ]),
    ("网站与全栈应用", "🌐", [
        ("campus-archive", "简册 · 大学生个人电子档案袋：Next.js + Flutter，证件 AES-256-GCM 加密"),
        ("guanlan", "观澜 · 命理研究工作台：八字/紫微/六爻/合婚，人生 K 线与命中率追踪"),
        ("xunji-heritage-trail", "寻迹 · 非遗文化教育平台：收录 1557 项国家级非遗，覆盖 34 个省级行政区"),
        ("Student-Union-Management-System", "学生会部门管理系统：工作流为核心，前后端分离"),
        ("Newland-Full-Stack-Training-Platform", "物联网业务场景全栈训练演示项目（新大陆版）"),
        ("northstar", "北极星 · 五年规划与执行追踪：愿景逐层拆解到日并量化兑现，本地优先"),
        ("blog", "个人博客：Next.js 16 + Velite + better-auth，i18n，Docker 部署"),
        ("xuanchaun", "高校公众号推文辅助工具：AI 写稿、模板推荐、可视化工作流编排"),
    ]),
    ("桌面与实用工具", "🧰", [
        ("KGG-Decryptor", "酷狗 KGG 等加密音乐解密转换（Tauri 2），覆盖酷我/网易云/QQ 音乐"),
        ("RemoteControl", "Windows 远程控制：单会话共享 + 双光标，.NET 8 Agent + WPF + Go 中继"),
        ("lan-file-share", "局域网文件共享站：零依赖 Node.js，断点续传、拖拽上传、文件夹打包下载"),
        ("douyin-fire-desktop", "抖音续火桌面助手：Electron，自动续火 + Qwen-VL 智能回复"),
    ]),
    ("嵌入式与 IoT", "📡", [
        ("nle-emulator-local", "教育云物联网仿真实训平台本地化：前端镜像 + 自建后端，离线运行"),
        ("ipc360-web-monitor", "IPC360 双目摄像头 Web 监控中心（协议逆向全实现）"),
    ]),
    ("内容与文史", "📜", [
        ("maoxuan-wiki", "《毛泽东选集》知识库：五卷 229 篇全文 + AI 问答（PandaWiki）"),
        ("Personal-Workspace", "创作者一站式工作台：选题策划、多平台发布、数据复盘、视频转笔记"),
    ]),
    ("游戏", "🎮", [
        ("iron-commander", "铁血指挥官 · 2.5D 现代战争策略原型（Godot 4.7）"),
    ]),
    ("主页", "🏠", [
        ("Aaron-gx", "归墟实验室 · 个人主页与技能总览"),
    ]),
]

HEADER = """# 🌌 归墟实验室 · 项目总目录

> 「 察万物之联以格物，范数字之魂以拟人，览千秋之史以经略。」

本仓库是 [Aaron-gx](https://github.com/Aaron-gx) 全部仓库的分类索引，与个人主页 [归墟实验室](https://github.com/Aaron-gx/Aaron-gx) 配套。

🔒 表示私有仓库，仅收录名称与简介，不开放源码。

**{total} 个仓库 · {pub} 公开 · {priv} 私有** · 更新于 {date}

---
"""


def gh_json(args: str):
    out = subprocess.run(["gh", *args.split()], capture_output=True)
    if out.returncode != 0:
        sys.exit(f"gh 调用失败: {out.stderr.decode('utf-8', 'replace')}")
    return json.loads(out.stdout)


def main():
    repos = gh_json("repo list --limit 100 --json name,isPrivate,primaryLanguage,url")
    meta = {r["name"]: r for r in repos}

    seen, sections = set(), []
    pub = priv = 0
    for title, emoji, items in CATEGORIES:
        rows = []
        for name, desc in items:
            r = meta.get(name)
            if r is None:
                print(f"警告：CATEGORIES 里的 {name} 在 GitHub 上不存在，已跳过")
                continue
            seen.add(name)
            is_priv = r["isPrivate"]
            if is_priv:
                priv += 1
                cell = f"{name} 🔒"
            else:
                pub += 1
                cell = f"[{name}]({r['url']})"
            lang = (r.get("primaryLanguage") or {}).get("name", "-")
            rows.append(f"| {cell} | {desc} | {lang} |")
        if rows:
            sections.append(f"## {emoji} {title}\n\n"
                            "| 项目 | 简介 | 语言 |\n|---|---|---|\n" + "\n".join(rows))

    missing = set(meta) - seen
    if missing:
        print(f"警告：以下仓库未在 CATEGORIES 里登记，未收录：{sorted(missing)}")

    total = pub + priv
    date = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    body = HEADER.format(total=total, pub=pub, priv=priv, date=date)
    body += "\n\n".join(sections)

    body += """

---

### 维护

索引由 `generate.py` 生成。新增仓库后，在 `generate.py` 的 `CATEGORIES` 里登记名字和一句话简介，然后运行：

```bash
python generate.py
```

脚本会拉取最新的仓库元数据（公开/私有、语言、更新时间），重新生成统计行并覆盖本 README。
"""

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(body)
    print(f"README.md 已生成：{total} 仓库（公开 {pub} / 私有 {priv}）")


if __name__ == "__main__":
    main()
