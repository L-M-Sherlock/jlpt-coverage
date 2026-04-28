# JLPT Coverage Checker

检查 Anki 集合里日语卡片对 eggrolls JLPT10k 词表的覆盖率。

## 项目结构

- `jlpt_converge/`: CLI 和 Anki 插件共用的统计逻辑。
- `scripts/`: 命令行脚本和 Anki 插件打包脚本。
- `anki_addon/jlpt_coverage/`: Anki 插件源代码。
- `data/`: 项目内的精简 JLPT 词表。
- `reports/`: CLI 生成的词表状态 CSV。
- `dist/`: 打包出的 `.ankiaddon` 文件。

默认行为:

- 先复制 Anki profile 下的 `collection.anki2` 及同名 `-wal`/`-shm`，只连接副本。
- 默认统计 `Lapis`、`Kaishi 1.5k` 和 `Kaishi 1.5k zh-CH` 三个 note type。
- 匹配字段只使用:
  - `Kaishi 1.5k`: 字形 `Word`，读音 `Word Reading`
  - `Kaishi 1.5k zh-CH`: 字形 `Word`，读音 `Word Reading`
  - `Lapis`: 字形 `Expression`，读音 `ExpressionReading`
  - JLPT 词表: 字形 `word_plain`，读音 `reading`
- 只读取项目内的 `data/jlpt_vocab.csv`，不会在覆盖率检查时读取原始 JLPT `notes.csv`。
- 同时输出卡片覆盖率和学习覆盖率。学习覆盖表示命中的 Anki note 至少有一张 card 的 `reps > 0`。
- 可选输出 Young/Mature 覆盖率。Young 使用 Anki 的 interval 口径 `ivl < 21`；Mature 使用 `ivl >= 21`。
- 控制台输出覆盖率汇总；CSV 导出只写一份 `jlpt_vocab_status_*.csv`，包含 JLPT 词表和 `missing` / `unlearned` 状态。

## 第一次准备词表

首次克隆仓库后先初始化本地化依赖:

```bash
git submodule update --init --recursive
```

```bash
python3 scripts/extract_jlpt_vocab.py
```

这会从原始 eggrolls `notes.csv` 中提取必要字段到 `data/jlpt_vocab.csv`。

## 检查覆盖率

```bash
python3 scripts/check_jlpt_coverage.py
```

常用参数:

```bash
python3 scripts/check_jlpt_coverage.py --reading-only
python3 scripts/check_jlpt_coverage.py --strict-word
python3 scripts/check_jlpt_coverage.py --match-mode word-or-reading
python3 scripts/check_jlpt_coverage.py --by-frequency
python3 scripts/check_jlpt_coverage.py --by-interval
python3 scripts/check_jlpt_coverage.py --exclude-suspended
python3 scripts/check_jlpt_coverage.py --language en_US
python3 scripts/check_jlpt_coverage.py --language zh_CN
python3 scripts/check_jlpt_coverage.py --note-type Lapis --note-type "Kaishi 1.5k" --note-type "Kaishi 1.5k zh-CH"
```

匹配模式:

- 默认 `word-or-reading`: 字形或读音任一命中就算覆盖。
- `--reading-only`: 只比较读音，适合避免字形差异造成遗漏。
- `--strict-word` / `--word-only`: 只比较字形，统计更严格。

频率分档:

- `--by-frequency`: 在 JLPT 级别内继续按源词表频率分档展开。
- 源词表里 N1 是 `高频` / `中频` / `低频`；N2 和 N3 是 `高频` / `中低频`；N4+N5 没有频率分档，会显示为 `未分频`。

Young/Mature:

- `--by-interval`: 每个 level 额外显示 Young 和 Mature 词条数及比例。
- Young 为命中至少一张 `ivl < 21` 的 card；Mature 为命中至少一张 `ivl >= 21` 的 card。比例分母是该 level 的 JLPT 总词条数。

说明: 这份 eggrolls 源词表把 N4 和 N5 合并在 `N4+N5` 牌组里，没有额外字段可稳定拆分，所以脚本会报告 `N4+N5` 合并覆盖率。

## Anki 插件

打包插件:

```bash
python3 scripts/package_anki_addon.py
```

输出文件:

```text
dist/jlpt_coverage.ankiaddon
```

安装到 Anki 后，菜单入口是 `Tools -> JLPT Coverage`。插件使用当前打开的 Anki 集合，通过 Anki add-on API 读取 note/card 信息，不写入集合；导出 CSV 时会让你选择输出目录。

导出的 CSV 字段为 `level,frequency,word_plain,reading,missing,unlearned`。`missing=1` 表示没有匹配到卡片；`unlearned=1` 表示已经匹配到卡片，但还没有命中任何 `reps > 0` 的 card。

插件支持中文和英文界面，语言跟随 Anki 的默认语言。CLI 可通过 `--language auto|en_US|zh_CN` 指定输出语言。项目使用 `python_i18n` git submodule 加载本地化 JSON。

## 致谢

JLPT 词汇数据来自 [5mdld/anki-jlpt-decks](https://github.com/5mdld/anki-jlpt-decks)。
