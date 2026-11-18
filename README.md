# AI 脚气模拟器

趣味角色扮演技能。加载后默认进入角色，同时认真回答问题；只有明确说“表演停止”才结束表演。

## 默认安装方式

安装始终以当前项目为落点：技能和状态放进项目的 `.agents/skills/ai-jiaoqi/`，同时在项目指令和已检测到产品的用户级指令中登记入口。用户请求安装这个压缩包时，代为安装的智能体应在同一次任务中运行安装器，不要只把命令交给用户。

从 GitHub 安装时，可以直接对智能体说：

```text
请从 https://github.com/Halucinaut/ai-jiaoqi 获取并安装这个技能到当前项目。以当前项目根目录为工作目录，运行仓库中的 scripts/install_global.py --agents auto，并按 README 的权限范围执行。
```

请让安装器以目标项目根目录为工作目录运行。安装器源码可来自 GitHub 仓库或解压后的压缩包，传入它的实际路径：

```bash
python3 /path/to/skill-source/scripts/install_global.py --agents auto
```

安装器将技能复制到当前项目的 `.agents/skills/ai-jiaoqi/`，在项目 `AGENTS.md` 中添加受标记管理的指令，并确保 `CLAUDE.md` 导入 `@AGENTS.md`。它也会更新检测到的智能体用户级指令文件，让其他项目会话引用这份项目内副本；其他项目目录不会被复制或修改。状态保存在这份项目内副本中，跨项目会话共用同一份状态。从另一个项目再次安装时，全局入口会改指向新项目副本，旧项目副本保留；若项目移动，需从新位置再次运行安装器以更新全局引用。

此安装依赖指令文件，不注册可执行的会话启动钩子，也不会在后台常驻。后续会话能否自动加载，取决于产品是否读取已登记的用户级或项目级指令。

## 权限与改动范围

安装器在当前用户权限下读取安装包、检查产品配置路径和 `PATH`，并读取选定指令文件以保留原文；它只在当前项目和当前用户目录内写入技能及指令，不需要 `sudo` 或管理员权限。它不访问网络、不读取密钥或凭据存储、不启动其他智能体或后台进程、不扫描或修改其他项目，也不修改其他用户账号。

项目内目标为 `.agents/skills/ai-jiaoqi/`、`AGENTS.md` 和 `CLAUDE.md`。默认 `--agents auto` 只处理检测到的产品；`--agents all` 会为完整名单创建或更新用户级入口。用户级目标为：

- Codex：`$CODEX_HOME/AGENTS.override.md`（该文件已有非空内容时），否则 `$CODEX_HOME/AGENTS.md`；未设置 `CODEX_HOME` 时使用 `~/.codex/`。
- Claude Code：`~/.claude/CLAUDE.md`。
- OpenCode：`${XDG_CONFIG_HOME:-~/.config}/opencode/AGENTS.md`。
- DSH：`${DSH_HOME:-~/.dsh}/AGENTS.md`。
- WorkBuddy：`~/.codebuddy/CODEBUDDY.md`。
- Gemini CLI：`${GEMINI_CLI_HOME:-~}/.gemini/GEMINI.md`。
- GitHub Copilot：`${COPILOT_HOME:-~}/.copilot/copilot-instructions.md`。

安装器只改写自己的标记块，保留指令文件其他内容；遇到符号链接或不完整、重复的标记块会停止修改。`--dry-run` 可预览目标；`--uninstall` 会移除项目和用户级指令块及由安装器添加的 `CLAUDE.md` 导入标记，保留技能和状态。若产品要求确认文件写入，应通过产品自身的授权流程处理，不要绕过其安全限制；常规安装不需要提升管理员权限。

## 指定智能体范围

```bash
python3 /path/to/skill-source/scripts/install_global.py --agents codex,claude,opencode
python3 /path/to/skill-source/scripts/install_global.py --agents all --dry-run
python3 /path/to/skill-source/scripts/install_global.py --agents claude --uninstall
```

支持的产品名：`codex`、`claude`、`opencode`、`dsh`、`workbuddy`、`gemini`、`copilot`。自动检测未找到图形界面产品时，可直接指定名称。

压缩包不包含安装者的状态记录。首次安装会在当前项目内新建空状态；更新技能时会保留已有状态。
