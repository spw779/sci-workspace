<p align="center">
  <img src="./assets/banner.png" alt="sci-workspace：蓝绿色书页标志与手绘字标" width="920">
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Agent Skill](https://img.shields.io/badge/Agent-Skill-64748b.svg)

# sci-workspace

一个轻量的 SCI 论文工作区 skill，以完成并持续修订整篇 manuscript 为目标。告诉 Codex 等 Agent 你要开始写一篇论文，它会搭好目录，让文献、整稿、章节、数据和结果各有位置。

默认创建五个顶层目录和六个常用章节，已有文件保留，材料子目录按需增加。

## 安装

告诉支持 Agent Skills 的工具：

```text
请从这个仓库安装 sci-workspace skill：
https://github.com/spw779/sci-workspace
技能入口是仓库根目录的 SKILL.md。
如果已经安装，请更新原有安装。
完成后报告实际安装位置，核对脚本和模板是否完整，并说明当前工具如何首次调用。
```

安装时保留本仓库的相对目录结构：skill 目录下直接包含 `SKILL.md`、`scripts/workspace.py` 和 `assets/` 中的两个说明模板。可运行脚本的 `--help` 核对入口。每个宿主保留一份可发现的安装；首次启用方式及是否需要新会话，以该宿主的实际支持为准。

更新时先定位已有安装；有本地修改则先核对差异，保留用户改动。论文放在独立项目文件夹中，更新 skill 后，已有项目指南仍由 Agent 基于原文局部补充。

## 使用

在论文文件夹中告诉 Agent：

```text
我要开始写这篇 SCI 论文。
请用 $sci-workspace 初始化当前论文工作区，保留已有文件。
```

也可直接说“使用 sci-workspace 初始化论文工作区”，调用形式按当前宿主支持。

默认结构：

| 目录 | 放什么 |
| --- | --- |
| `01_reference/` | 文献 PDF 和阅读材料 |
| `02_manuscript/` | 整篇论文的 Word 稿件，按 `manuscript_v1.docx`、`manuscript_v2.docx` 等保存 |
| `03_chapter/` | 分章节稿件，默认包含下列六章 |
| `04_data/` | 实验数据、原始照片、记录及数据说明 |
| `05_results/` | 分析输出、结果表和稿件图片 |

`03_chapter/` 默认包含 **Abstract、Introduction、Methods、Results、Discussion、Conclusions**。Methods 和 Results 在第一次初始化时就会创建。Conclusions 是否作为独立章节进入最终整稿，按目标期刊要求处理。

同时生成简短的 `WORKSPACE_GUIDE.md` 和 `AGENTS.md`，供后续任务了解项目约定。初始化只创建目录和说明，实际稿件在写作时生成。

**`03_chapter/Results` 放结果章节正文；`05_results` 放支撑正文的结果文件。**

需要细分数据和结果时再说：

```text
请为当前论文工作区增加常用的数据和结果子目录。
```

这会增加 `04_data/{raw,processed,metadata}` 和 `05_results/{statistics,tables,figures}`。其他章节、实验批次、补充材料或分析代码目录按实际任务添加。

## 整稿与章节版本

`02_manuscript/` 在初始化时就会创建，用来保存整篇论文，与各章节一样保留 Word 版本：

| 稿件 | 文件夹 | 文件名示例 |
| --- | --- | --- |
| 整篇 manuscript | `02_manuscript/` | `manuscript_v1.docx`、`manuscript_v2.docx` |
| Methods 章节 | `03_chapter/Methods/` | `Methods_v1.docx`、`Methods_v2.docx` |
| Results 章节 | `03_chapter/Results/` | `Results_v1.docx`、`Results_v2.docx` |

其他章节使用相同的 `<Section>_vN.docx` 规则。首稿从 `v1` 开始；交付新修订稿时，按该类稿件现有最大数字版本号加一另存，保留旧版。整稿与各章节各自编号，例如 `manuscript_v2.docx` 可以使用 `Methods_v4.docx` 的内容。

已有的 `manuscript.docx` 或其他命名文件保留原样；后续新稿按上述约定保存，用户另有命名或格式要求时遵循用户要求。实际写作或合稿时生成 Word 文件。

## 接着写与合稿

在现有 `WORKSPACE_GUIDE.md` 的项目记录中维护当前整稿、本轮采用的章节、当前任务和下一步。接续时先核对这些文件是否存在；最大版本号用于分配新文件名，本轮输入以用户指定或已核实的记录为准。

```text
请用 sci-workspace 检查当前稿件和项目记录，告诉我上次做到哪里、下一步是什么。
```

检查保持只读。实际写作任务明确输入文件和新 Word 输出路径；保存并核对后，更新指南。每次合稿记录输出整稿、采用的章节版本和主要改动。整稿被单独修改过时，下一次合稿先核对这些修改。

Word 的写作、编辑和排版检查由当前可用的文档能力完成。交付时说明新文件位置、主要修改及待处理事项，涉及排版时检查渲染结果。

## 已有项目

重复初始化只补齐缺失目录和说明，包括缺失的默认章节。已有稿件、数据、手写指南及自定义章节继续保留。原始输入保留，处理后的文件另存。

已有项目使用不同目录名称时，先让 Agent 读取项目指南、登记实际位置，再按该映射检查和补缺。脚本只处理标准布局，不解析指南中的自定义映射；固定目录的缺失报告不能直接作为另建目录的依据。

从章节子目录接续且未指定根目录时，先向上查找最近的 `WORKSPACE_GUIDE.md`，结合实际文件核对论文根目录，再开展任务。

产生关键图表时，按需记录输出、输入数据和生成脚本的路径；手工图表注明来源。大型数据或独立分析项目记录真实位置，已有文献主表和引用库沿用现有格式。

正文写作、文献处理和数据分析由当前可用的相应能力完成，并沿用本项目的目录约定。

## 直接运行

脚本使用 Python 3.10+ 标准库。在仓库根目录运行：

```bash
python scripts/workspace.py init --root ../PaperA
python scripts/workspace.py init --root ../PaperA --with-subdirs
python scripts/workspace.py init --root ../PaperA --sections Acknowledgments
python scripts/workspace.py init --root ../PaperA --dry-run
python scripts/workspace.py status --root ../PaperA
```

- `--project-name`：设置新指南的项目名，省略时使用文件夹名。
- `--sections`：在默认六章基础上增加指定章节，已有章节保留。
- `--with-subdirs`：增加六个常用数据和结果子目录。
- `--dry-run`：仅预览，不创建文件或目录。
- `status`：只读检查五个目录、六章和两份说明，列出已有自定义章及稿件概览；材料子目录未创建、章节尚无稿件属于正常情况。

`status` 的 `drafts.manuscript` 和 `drafts.chapters` 分别列出整稿和各章节的 Word 文件。版本文件按数字排序，`highest_version` 表示最高编号，其他命名的 `.docx` / `.doc` 单独列出；Word 的 `~$` 临时锁文件忽略。概览仅浅层查看文件名和类型，不读取正文，也不决定当前采用稿。路径冲突见顶层结构警告及各稿件组的 `warnings`。

脚本输出 JSON，非 ASCII 字符使用安全转义，解析后仍为原始中文，适用于不同终端输出编码。路径类型冲突会在初始化写入前报告，已有说明不会被模板覆盖。

## 开发检查

```bash
python -m unittest discover -s tests -v
```

CI 检查 Ubuntu / Windows 下的 Python 3.12，并在 Ubuntu 检查最低支持版本 Python 3.10。

## 许可证

本项目采用 [MIT License](./LICENSE)。
