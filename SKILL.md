---
name: sci-workspace
description: 搭建、检查和补齐 SCI 论文工作区，默认建立文献、整稿、章节、数据、结果五个目录和 Abstract、Introduction、Methods、Results、Discussion、Conclusions 六章，约定整稿与章节的 Word 版本保存方式。用于开始写论文、新建或接续论文项目、补齐目录，以及说明稿件和其他文件放在哪里。
---

# SCI 论文工作区

围绕整篇 manuscript 的写作与修订，为每篇论文维护一份简短的 `WORKSPACE_GUIDE.md`，记录实际目录和稿件版本约定。

## 工作流程

1. 确定用户指定或当前已明确选定的论文根目录。将论文项目与技能安装目录分开；需要写入而目标仍不明确时再询问。
2. 读取适用的 `AGENTS.md`、已有 `WORKSPACE_GUIDE.md`，浅层查看目录。仅回答“放哪里”或检查结构时保持只读。
3. 新项目或标准布局用脚本初始化、补缺。旧项目采用其他目录名时，先复用现有布局，在指南中登记实际路径，再补需要的目录。
4. 保留已有稿件、数据、自定义章节和手写指南。需要更新已有说明时基于原文局部修改。
5. 核对实际创建或保留的项目，简短报告结果及尚未解决的路径冲突。

## 默认结构

| 路径 | 用途 |
| --- | --- |
| `01_reference/` | 文献及阅读材料 |
| `02_manuscript/` | 完整 Word 稿件及其版本：`manuscript_v1.docx`、`manuscript_v2.docx` 等 |
| `03_chapter/` | 分章节稿件 |
| `04_data/` | 实验数据、原始照片、记录及数据说明 |
| `05_results/` | 分析输出、结果表和稿件图片 |

初始化时在 `03_chapter/` 建立 **Abstract、Introduction、Methods、Results、Discussion、Conclusions** 六章，同时生成 `WORKSPACE_GUIDE.md` 和 `AGENTS.md`。Conclusions 是否独立写入整稿由目标期刊决定。

按需增加 `04_data/{raw,processed,metadata}` 和 `05_results/{statistics,tables,figures}`，其余目录随任务添加。`03_chapter/Results` 存正文，`05_results` 存结果材料。

## 稿件版本

- 将整稿保存在 `02_manuscript/manuscript_vN.docx`，将各章节保存在 `03_chapter/<Section>/<Section>_vN.docx`。
- 首稿从 `v1` 开始。交付新修订稿前检查同类文件，按现有最大数字版本号加一另存，保留旧版；整稿和每个章节独立编号。
- 保留已有的 `manuscript.docx` 等旧文件，不自动改名或覆盖。新稿默认使用 Word，用户指定的命名、格式或覆盖要求优先。
- 在实际写作或合稿时生成稿件。初始化只创建目录和说明；将上述保存约定交给执行写作或合稿的任务。

## 工具

定位本 skill 的 `scripts/workspace.py`，用可用的 Python 3.10+ 解释器运行；脚本只依赖标准库。为含空格的路径加引号。

```text
python "<skill目录>/scripts/workspace.py" init --root "<论文根目录>"
python "<skill目录>/scripts/workspace.py" init --root "<论文根目录>" --with-subdirs
python "<skill目录>/scripts/workspace.py" init --root "<论文根目录>" --sections Acknowledgments
python "<skill目录>/scripts/workspace.py" init --root "<论文根目录>" --dry-run
python "<skill目录>/scripts/workspace.py" status --root "<论文根目录>"
```

- `init` 补齐默认结构，已有文件保留。可用 `--project-name` 指定新指南的项目名。
- `--sections` 在默认六章基础上增加指定章节；`--with-subdirs` 增加六个材料子目录。
- `--dry-run` 零写入预览；`status` 只读检查默认结构、已有章节和材料子目录。可选材料子目录尚未创建属于正常情况。
- 遇到路径类型冲突或越出项目的符号链接，报告具体位置并保留现状。
- 没有 Python 时，按同样的结构、预检和不覆盖约定使用现有文件工具完成搭建。

## 后续任务

将论文根目录、指南及指定的输入输出位置交给当前写作、文献或分析任务。整稿进入 `02_manuscript`，章节进入 `03_chapter`，分析输出进入 `05_results`。

保留原始输入，处理结果另存。大型数据或独立分析项目可在指南中记录真实路径。项目事实写入本项目指南；未知信息保持待补充，实际稿件、索引和记录在任务需要时创建。目录搭建完成后，准确说明创建和保存状态。
