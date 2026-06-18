# JLPT Coverage for Anki

[English README](README.md)

JLPT Coverage 是一个 Anki 插件，面向通过沉浸材料挖词的日语学习者，帮助你查看自己已经 mining 的单词对 JLPT N1-N5 词表的覆盖情况。

这个工具的主要使用场景是配合 [Donkuri mining guide](https://donkuri.github.io/learn-japanese/mining/) 中描述的学习方式：你使用 Yomitan 和 Anki，从视觉小说、动画、小说、漫画、游戏或其他原生材料中挖词制卡。JLPT Coverage 不会替代 mining；它解决的是另一个问题：你的 mining 卡片已经覆盖了多少 JLPT 词汇，哪些已经学过，哪些还缺失。

## 功能

- 统计指定 Anki note type 对 JLPT 词表的覆盖率。
- 支持 `Lapis`、`Kaishi 1.5k`、`Kaishi 1.5k zh-CH` 等 mining 常用模板。
- 可以按 note type 配置字形字段和读音字段，字段列表直接从当前 Anki 集合读取。
- 同时统计卡片覆盖率和学习覆盖率。
- 可按源词表频率分档展开统计。
- 可按 Anki interval 口径统计 Young 和 Mature 覆盖率。
- 导出一份词表状态 CSV，包含 missing 和 unlearned 标记。
- 可给匹配到的 Anki notes 添加 `JLPT::N1` 到 `JLPT::N5` 标签，以及 N1-N3 频率标签。
- 插件内置项目本地的 JLPT 词表 CSV，运行时不会读取原始 deck 文件。

覆盖率统计和 CSV 导出只会通过 Anki add-on API 读取当前打开的集合。可选的 `打 JLPT 标签` 操作会向匹配到的 notes 写入标签。

## 适合谁使用

这个工具适合以下学习者：

- 通过沉浸材料把日语单词 mining 到 Anki。
- 使用 Lapis、Kaishi 或其他包含字形和读音字段的 note type。
- 希望继续以 mining 为主，而不是直接改用预制 JLPT 词汇 deck。
- 备考 JLPT 时，希望知道自己的 mining 词汇已经覆盖了哪些 JLPT 项目。
- 想快速找出 JLPT 词表中的缺口，决定后续 mining 或复习重点。

它是覆盖率和报表工具，不是 SRS 调度器、JLPT 课程，也不是替代词汇 deck。

## 安装

从最新 [GitHub Release](https://github.com/L-M-Sherlock/jlpt-coverage/releases) 下载 `jlpt_coverage.ankiaddon`，然后在 Anki 中安装：

1. 打开 Anki。
2. 进入 `Tools -> Add-ons`。
3. 选择 `Install from file...`。
4. 选择 `jlpt_coverage.ankiaddon`。
5. 重启 Anki。
6. 打开 `Tools -> JLPT Coverage`。

GitHub Actions 的 artifact 下载时会被 GitHub 固定包成外层 `.zip`。如果你下载的是 workflow artifact，而不是 Release asset，需要先解压，再安装里面的 `.ankiaddon` 文件。

## 基本用法

在 Anki 中打开 `Tools -> JLPT Coverage`。

1. 勾选要统计的 note type。
2. 为每个 note type 选择字形字段和读音字段。
3. 选择匹配模式。
4. 按需要开启频率分档、Young/Mature 分档或排除暂停卡片。
5. 点击 `Run`。
6. 如果希望以后复用当前配置，点击 `Save Defaults`。
7. 如果只想导出某个等级或目标等级范围，选择导出等级过滤。
8. 点击 `Export CSV` 导出词表状态文件。
9. 点击 `打 JLPT 标签` 给匹配到的 notes 添加 JLPT 等级标签和 N1-N3 频率标签。

界面会直接加载当前 Anki 集合中的 note type 和字段，避免手动输入名称导致错误。

## 默认字段映射

插件内置了本项目主要面向的 note type 默认字段：

| Note type | 字形字段 | 读音字段 |
| --- | --- | --- |
| `Lapis` | `Expression` | `ExpressionReading` |
| `Kaishi 1.5k` | `Word` | `Word Reading` |
| `Kaishi 1.5k zh-CH` | `Word` | `Word Reading` |

你也可以在界面中为任意 note type 选择其他字段。

## 匹配模式

| 模式 | 含义 | 适合场景 |
| --- | --- | --- |
| `word-or-reading` | 字形或读音任一命中，就算覆盖。 | 默认的 mining 覆盖率统计。 |
| `word-and-reading` | 字形和读音都命中，才算覆盖。 | 需要避免只靠读音或只靠字形误命中的严格覆盖率统计。 |
| `reading` | 只比较读音。 | 避免字形、假名/汉字、写法差异导致遗漏。 |
| `word` | 只比较字形。 | 需要更严格统计具体词形时使用。 |

JLPT 词表侧使用 `word_plain` 作为字形字段，`reading` 作为读音字段。

## JLPT note 标签

`打 JLPT 标签` 会使用界面上当前选择的 note type、字段和排除暂停卡片设置。它不使用覆盖率统计的匹配模式下拉框；打标签始终要求同一条 JLPT 词表项的字形和读音都命中当前 note。

生成的等级标签是 `JLPT::N1`、`JLPT::N2`、`JLPT::N3`、`JLPT::N4`、`JLPT::N5`。N1、N2、N3 命中项还会生成频率标签，例如 `JLPT::N2::高频`、`JLPT::N2::中频`、`JLPT::N2::低频`。Anki 标签挂在 note 上，因此同一个 note 生成的所有 cards 都会显示同样的标签。

重复运行只会追加缺失标签，不会删除已有 JLPT 标签。如果之后修改字段、note type 或匹配偏好，过期标签需要手动清理。

## 报表指标

| 指标 | 含义 |
| --- | --- |
| `Total` | 当前 JLPT level 或分档中的词条数。 |
| `Card` / `Card%` | 匹配到至少一条所选 Anki note 的词条数和比例。 |
| `Learned` / `Learn%` | 匹配到所选 Anki note，且至少一张 card 的 `reps > 0` 的词条数和比例。 |
| `Missing` | 没有匹配到任何所选 Anki note 的词条数。 |
| `Unlearned` | 匹配到了 note，但没有任何匹配 card 的 `reps > 0` 的词条数。 |
| `Young` / `Young%` | 至少匹配到一张 `ivl < 21` card 的词条数和比例。 |
| `Mature` / `Mature%` | 至少匹配到一张 `ivl >= 21` card 的词条数和比例。 |

Young 和 Mature 使用 Anki 自己的 interval 口径。

## 频率分档

开启频率分档后，报表会在 JLPT level 内继续按源词表的频率标签展开。

当前源词表的情况：

- N1、N2 和 N3 包含高频、中频、低频分档。
- N4 和 N5 已在内置词表中拆分为独立等级。

## CSV 导出

`Export CSV` 会导出一份词表状态文件，字段如下：

```text
level,frequency,word_plain,reading,missing,unlearned
```

- `missing=1` 表示没有匹配到所选 Anki note。
- `unlearned=1` 表示匹配到了所选 Anki note，但没有任何匹配 card 的 `reps > 0`。

这份 CSV 适合用来排序、筛选，并规划后续 mining 或 JLPT 复习。

导出时可以选择全部等级、单独某个等级，或目标等级范围。例如 `到 N2 为止` 会导出 N2、N3、N4 和 N5 词条。旧的 `N4+N5` 过滤值仍可用于兼容旧版合并词表。

## 语言支持

插件支持英文和简体中文界面，跟随 Anki 默认语言。

本地化使用 `python_i18n` git submodule，并通过 `anki_addon/jlpt_coverage/locale/` 下的 JSON 文件加载翻译。

## 命令行工具

Anki 插件是主要入口。项目也提供命令行工具，方便一次性检查。

不 clone 仓库，直接从 GitHub 运行：

```bash
uvx --from git+https://github.com/L-M-Sherlock/jlpt-coverage.git jlpt-coverage
```

如果本机有多个 Anki profile，请显式传入 profile 路径：

```bash
uvx --from git+https://github.com/L-M-Sherlock/jlpt-coverage.git jlpt-coverage \
  --profile-dir "$HOME/Library/Application Support/Anki2/<ProfileName>"
```

在本地 checkout 中运行安装后的命令：

```bash
uv run jlpt-coverage
```

常用参数：

```bash
uv run jlpt-coverage --reading-only
uv run jlpt-coverage --strict-word
uv run jlpt-coverage --match-mode word-and-reading
uv run jlpt-coverage --by-frequency
uv run jlpt-coverage --by-interval
uv run jlpt-coverage --exclude-suspended
uv run jlpt-coverage --export-level N2
uv run jlpt-coverage --export-up-to N2
uv run jlpt-coverage --language en_US
uv run jlpt-coverage --language zh_CN
```

CLI 会在可行时自动识别本机唯一的 Anki profile。你也可以传入 `--profile-dir`，或设置 `ANKI_PROFILE_DIR`。

CLI 会先复制 `collection.anki2` 和相关 SQLite sidecar 文件，再连接副本；不会直接连接正在使用的 Anki 集合数据库。默认报表目录为当前目录下的 `jlpt_coverage_reports`。

## 开发

先安装 [uv](https://docs.astral.sh/uv/)，然后克隆仓库并初始化 submodule：

```bash
git submodule update --init --recursive
uv sync
```

打包并校验插件：

```bash
uv run scripts/package_anki_addon.py
uv run scripts/validate_anki_addon.py
```

输出文件：

```text
dist/jlpt_coverage.ankiaddon
```

构建并校验 Yomitan JLPT 元数据词典：

```bash
uv run scripts/build_yomitan_jlpt_dict.py
uv run scripts/validate_yomitan_jlpt_dict.py
```

Yomitan 输出文件：

```text
yomitan-eggrolls-jlpt-vocab/
dist/eggrolls-jlpt-yomitan.zip
```

从原始 source deck 中提取项目本地词表：

```bash
uv run scripts/extract_jlpt_vocab.py
```

该命令只会把工具需要的字段写入 `jlpt_coverage/data/jlpt_vocab.csv`。

GitHub Actions 会在 push 和 pull request 时构建并校验插件和 Yomitan 词典。推送 `v*` tag 时，还会把 `jlpt_coverage.ankiaddon` 和 `eggrolls-jlpt-yomitan.zip` 直接上传到 GitHub Release。

## 词表来源与致谢

JLPT 词汇数据来自 [5mdld/anki-jlpt-decks](https://github.com/5mdld/anki-jlpt-decks) 中的 eggrolls JLPT10k deck。

Yomitan 词典是元数据词典：它会给匹配词条添加 `N2高频` 等 JLPT 等级和 eggrolls 频段标签，但不包含释义、例句或音频。源词表数据使用 CC BY-NC 4.0 许可。

本项目只保留覆盖率统计所需字段：

- `level`
- `frequency`
- `word_plain`
- `reading`

感谢该 deck 的维护者，以及日语 mining 社区中相关工具和 note type 的作者。
