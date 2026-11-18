#!/usr/bin/env python3
"""Install Sock Signal globally and link it from user and project instructions."""

import argparse
import os
import shutil
import stat
import tempfile
from pathlib import Path


START = "<!-- sock-signal-global:start -->"
END = "<!-- sock-signal-global:end -->"
PROJECT_START = "<!-- sock-signal:start -->"
PROJECT_END = "<!-- sock-signal:end -->"
CLAUDE_START = "<!-- sock-signal-claude-import:start -->"
CLAUDE_END = "<!-- sock-signal-claude-import:end -->"
LEGACY_START = "<!-- ai-jiaoqi-global:start -->"
LEGACY_END = "<!-- ai-jiaoqi-global:end -->"
LEGACY_PROJECT_START = "<!-- ai-jiaoqi:start -->"
LEGACY_PROJECT_END = "<!-- ai-jiaoqi:end -->"
LEGACY_CLAUDE_START = "<!-- ai-jiaoqi-claude-import:start -->"
LEGACY_CLAUDE_END = "<!-- ai-jiaoqi-claude-import:end -->"
AGENTS = ("codex", "claude", "opencode", "dsh", "workbuddy", "gemini", "copilot")
HOME = Path.home()


def env_path(name, fallback):
    value = os.environ.get(name)
    return Path(value).expanduser() if value else fallback


def config_paths():
    codex_home = env_path("CODEX_HOME", HOME / ".codex")
    codex_override = codex_home / "AGENTS.override.md"
    codex_default = codex_home / "AGENTS.md"
    if codex_override.is_file() and codex_override.read_text(encoding="utf-8").strip():
        codex_install = codex_override
    else:
        codex_install = codex_default

    xdg = env_path("XDG_CONFIG_HOME", HOME / ".config")
    dsh_home = env_path("DSH_HOME", HOME / ".dsh")
    copilot_home = env_path("COPILOT_HOME", HOME / ".copilot")
    gemini_home = env_path("GEMINI_CLI_HOME", HOME) / ".gemini"
    return {
        "codex": [codex_install],
        "claude": [HOME / ".claude" / "CLAUDE.md"],
        "opencode": [xdg / "opencode" / "AGENTS.md"],
        "dsh": [dsh_home / "AGENTS.md"],
        "workbuddy": [HOME / ".codebuddy" / "CODEBUDDY.md"],
        "gemini": [gemini_home / "GEMINI.md"],
        "copilot": [copilot_home / "copilot-instructions.md"],
        "codex_all": [codex_home / "AGENTS.override.md", codex_default],
    }


def detected_agents(paths):
    executables = {
        "codex": ("codex",),
        "claude": ("claude",),
        "opencode": ("opencode",),
        "dsh": ("dsh",),
        "workbuddy": ("workbuddy", "codebuddy"),
        "gemini": ("gemini",),
        "copilot": ("copilot",),
    }
    result = []
    for name in AGENTS:
        if any(path.parent.exists() for path in paths[name]):
            result.append(name)
        elif any(shutil.which(command) for command in executables[name]):
            result.append(name)
    if not ("workbuddy" in result) and (
        Path("/Applications/WorkBuddy.app").exists()
        or (HOME / "Applications" / "WorkBuddy.app").exists()
    ):
        result.append("workbuddy")
    return [name for name in AGENTS if name in result]


def selected_agents(value, paths):
    if value == "all":
        return list(AGENTS)
    if value == "auto":
        found = detected_agents(paths)
        if not found:
            raise SystemExit(
                "未检测到已安装的 agent。请传 --agents all，或指定名称："
                + ",".join(AGENTS)
            )
        return found
    names = [item.strip().lower() for item in value.split(",") if item.strip()]
    unknown = sorted(set(names) - set(AGENTS))
    if unknown or not names:
        raise SystemExit(f"不支持的 agent 名称：{', '.join(unknown) or value}")
    return list(dict.fromkeys(names))


def newline_for(text):
    return "\r\n" if "\r\n" in text else "\n"


def block_for(skill_root, newline):
    skill_path = (skill_root / "SKILL.md").as_posix()
    script_path = (skill_root / "scripts" / "update_state.py").as_posix()
    lines = [
        START,
        "## Sock Signal",
        "",
        f'Read and follow `{skill_path}`. Resolve this agent\'s canonical product name, then run `python3 "{script_path}" "<AgentName>"` once per session when permitted. Use the existing canonical name in `state.json` if present. Do not count twice if another instruction gives the same command. Stop roleplay whenever the user clearly asks to stop.',
        END,
    ]
    return newline.join(lines)


def project_block(skill_root, newline):
    lines = [
        PROJECT_START,
        "## Sock Signal",
        "",
        f'For this project, read and follow `{skill_root / "SKILL.md"}`. Run `python3 "{skill_root / "scripts" / "update_state.py"}" "<AgentName>"` once per session when permitted, using the canonical product name. Do not count twice if user-level instructions also apply. Stop roleplay whenever the user clearly asks to stop.',
        PROJECT_END,
    ]
    return newline.join(lines)


def update_block(text, block, start_marker, end_marker, uninstall=False):
    starts, ends = text.count(start_marker), text.count(end_marker)
    if starts != ends or starts > 1:
        raise ValueError("发现不完整或重复的受管理标记区块")
    if starts:
        begin = text.index(start_marker)
        finish = text.index(end_marker, begin) + len(end_marker)
        return text[:begin] + ("" if uninstall else block) + text[finish:]
    if uninstall:
        return text
    newline = newline_for(text)
    prefix = text
    if prefix and not prefix.endswith(("\n", "\r")):
        prefix += newline
    if prefix and not prefix.endswith(newline * 2):
        prefix += newline
    return prefix + block + newline


def update_managed_block(text, block, start, end, legacy_start, legacy_end, uninstall=False):
    text = update_block(text, "", legacy_start, legacy_end, uninstall=True)
    return update_block(text, block, start, end, uninstall=uninstall)


def read_text(path):
    if path.is_symlink():
        raise ValueError(f"目标是符号链接，拒绝修改：{path}")
    if not path.exists():
        return ""
    if not path.is_file():
        raise ValueError(f"目标不是普通文件，拒绝修改：{path}")
    return path.read_bytes().decode("utf-8")


def write_atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as output:
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def copy_skill(source, target):
    if source.resolve() == target.resolve():
        return
    if target.is_symlink():
        raise ValueError(f"技能目标是符号链接，拒绝覆盖：{target}")

    target.mkdir(parents=True, exist_ok=True)
    for relative in ("SKILL.md", "scripts/update_state.py", "scripts/install_global.py"):
        destination = target / relative
        if destination.is_symlink():
            raise ValueError(f"技能文件是符号链接，拒绝覆盖：{destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, destination)



def main():
    parser = argparse.ArgumentParser(description="Install Sock Signal in the current project and link user instructions.")
    parser.add_argument(
        "--agents",
        default="auto",
        help="auto, all, or a comma-separated list: " + ",".join(AGENTS),
    )
    parser.add_argument("--dry-run", action="store_true", help="show target files without writing")
    parser.add_argument("--uninstall", action="store_true", help="remove instruction blocks only")
    args = parser.parse_args()

    source = Path(__file__).resolve().parents[1]
    project_root = Path.cwd().resolve()
    skill_root = HOME / ".agents" / "skills" / "sock-signal"
    previous_roots = [project_root / ".agents" / "skills" / name for name in ("sock-signal", "ai-jiaoqi")]
    paths = config_paths()
    agents = selected_agents(args.agents.strip().lower(), paths)
    operations = []
    project_agents = project_root / "AGENTS.md"
    old_project_agents = read_text(project_agents)
    new_project_agents = update_managed_block(
        old_project_agents,
        project_block(skill_root, newline_for(old_project_agents)),
        PROJECT_START,
        PROJECT_END,
        LEGACY_PROJECT_START,
        LEGACY_PROJECT_END,
        uninstall=args.uninstall,
    )
    if new_project_agents != old_project_agents:
        operations.append((project_agents, new_project_agents))

    claude_project = project_root / "CLAUDE.md"
    old_claude_project = read_text(claude_project)
    has_agents_import = any(
        line.strip() == "@AGENTS.md" for line in old_claude_project.splitlines()
    )
    has_legacy_claude_import = LEGACY_CLAUDE_START in old_claude_project
    if args.uninstall:
        new_claude_project = update_managed_block(
            old_claude_project,
            "",
            CLAUDE_START,
            CLAUDE_END,
            LEGACY_CLAUDE_START,
            LEGACY_CLAUDE_END,
            uninstall=True,
        )
    elif has_legacy_claude_import:
        import_block = "\n".join((CLAUDE_START, "@AGENTS.md", CLAUDE_END))
        new_claude_project = update_managed_block(
            old_claude_project,
            import_block,
            CLAUDE_START,
            CLAUDE_END,
            LEGACY_CLAUDE_START,
            LEGACY_CLAUDE_END,
        )
    elif has_agents_import:
        new_claude_project = old_claude_project
    else:
        import_block = "\n".join((CLAUDE_START, "@AGENTS.md", CLAUDE_END))
        new_claude_project = update_managed_block(
            old_claude_project,
            import_block,
            CLAUDE_START,
            CLAUDE_END,
            LEGACY_CLAUDE_START,
            LEGACY_CLAUDE_END,
        )
    if new_claude_project != old_claude_project:
        operations.append((claude_project, new_claude_project))

    for name in agents:
        target_paths = paths["codex_all"] if args.uninstall and name == "codex" else paths[name]
        for path in target_paths:
            old = read_text(path)
            block = block_for(skill_root, newline_for(old))
            new = update_managed_block(
                old,
                block,
                START,
                END,
                LEGACY_START,
                LEGACY_END,
                uninstall=args.uninstall,
            )
            if new != old:
                operations.append((path, new))

    if args.dry_run:
        if not args.uninstall:
            print(f"Would install skill to: {skill_root}")
            for previous in previous_roots:
                if (previous / "state.json").is_file():
                    print(f"Would preserve previous state if needed: {previous / 'state.json'}")
        for path, _new in operations:
            print(f"Would {'remove block from' if args.uninstall else 'update'}: {path}")
        if not operations and args.uninstall:
            print("No managed instruction blocks found.")
        return

    if not args.uninstall:
        state = skill_root / "state.json"
        previous_states = [p / "state.json" for p in previous_roots if (p / "state.json").is_file()]
        if not state.exists() and len(previous_states) > 1 and previous_states[0].read_bytes() != previous_states[1].read_bytes():
            raise ValueError("旧安装存在不同状态文件，无法自动选择；请先保留并确认状态")
        copy_skill(source, skill_root)
        if not state.exists() and previous_states:
            shutil.copy2(previous_states[0], state)
        elif not state.exists():
            state.write_text('{"version": 1, "agents": {}}\n', encoding="utf-8")
    for path, text in operations:
        write_atomic(path, text)

    if not args.uninstall:
        print(f"Installed global skill: {skill_root}")
    for path, _text in operations:
        print(f"{'Removed managed block from' if args.uninstall else 'Updated'}: {path}")
    if args.uninstall:
        print(f"Skill and state retained at: {skill_root}")


if __name__ == "__main__":
    main()
