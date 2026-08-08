#!/usr/bin/env python3
"""Audit Claude Code plugins for structural validity, name collisions, and dangling references.

Usage:
    audit_plugin.py <path> [--json]

<path> is either:
  - a marketplace root containing .claude-plugin/marketplace.json
    (every plugin with a local relative "source" is audited), or
  - a single plugin directory (with or without .claude-plugin/plugin.json).

This complements `claude plugin validate`, which checks plugin.json and
component frontmatter against the official schema. This script adds checks
that validator does not cover: cross-component name collisions, dangling
file references from skill/command bodies, and plugin-agent fields that are
silently ignored (hooks/mcpServers/permissionMode) rather than rejected.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml

    def parse_frontmatter(text: str) -> dict[str, Any]:
        match = re.match(r"^---\n(.*?\n)---\n?", text, re.DOTALL)
        if not match:
            return {}
        try:
            data = yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            return {}
        return data if isinstance(data, dict) else {}

except ImportError:

    def parse_frontmatter(text: str) -> dict[str, Any]:
        match = re.match(r"^---\n(.*?\n)---\n?", text, re.DOTALL)
        if not match:
            return {}
        data: dict[str, Any] = {}
        for line in match.group(1).splitlines():
            if not line.strip() or line.strip().startswith("#"):
                continue
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            data[key.strip()] = value.strip().strip('"').strip("'")
        return data


SEVERITY_ERROR = "ERROR"
SEVERITY_WARN = "WARN"

RESERVED_MARKETPLACE_NAMES = {
    "claude-code-marketplace",
    "claude-code-plugins",
    "claude-plugins-official",
    "claude-plugins-community",
    "claude-community",
    "anthropic-marketplace",
    "anthropic-plugins",
    "agent-skills",
    "anthropic-agent-skills",
    "knowledge-work-plugins",
    "life-sciences",
    "claude-for-legal",
    "claude-for-financial-services",
    "financial-services-plugins",
    "first-party-plugins",
    "healthcare",
}

KNOWN_PLUGIN_JSON_FIELDS = {
    "$schema", "name", "displayName", "version", "description", "author",
    "homepage", "repository", "license", "keywords", "metadata", "skills",
    "commands", "agents", "workflows", "hooks", "mcpServers", "outputStyles",
    "lspServers", "experimental", "dependencies", "userConfig", "channels",
    "defaultEnabled",
}

# Plugin-shipped agents silently drop these fields rather than erroring.
DISALLOWED_AGENT_FIELDS = {"hooks", "mcpServers", "permissionMode"}
ALLOWED_AGENT_FIELDS = {
    "name", "description", "model", "effort", "maxTurns", "tools",
    "disallowedTools", "skills", "memory", "background", "isolation",
}

KEBAB_CASE_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
REFERENCE_RE = re.compile(r"[`\"']((?:\./)?(?:references|scripts|assets)/[\w./-]+)[`\"']")


@dataclass
class Issue:
    severity: str
    location: str
    message: str


@dataclass
class PluginReport:
    path: Path
    name: str
    issues: list[Issue] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    agents: list[str] = field(default_factory=list)

    def error(self, location: str, message: str) -> None:
        self.issues.append(Issue(SEVERITY_ERROR, location, message))

    def warn(self, location: str, message: str) -> None:
        self.issues.append(Issue(SEVERITY_WARN, location, message))

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == SEVERITY_ERROR)


def load_json(path: Path, report: PluginReport | None = None) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        if report is not None:
            report.error(str(path), f"invalid JSON: {exc}")
        return None


def check_dangling_references(md_path: Path, base_dir: Path, report: PluginReport) -> None:
    text = md_path.read_text(errors="replace")
    for m in REFERENCE_RE.finditer(text):
        ref = m.group(1).lstrip("./")
        if not (base_dir / ref).exists():
            report.warn(str(md_path), f"references '{ref}' but that file does not exist under {base_dir}")


def audit_skills(plugin_dir: Path, manifest: dict[str, Any], report: PluginReport) -> None:
    skill_dirs: list[Path] = []
    skills_field = manifest.get("skills")
    if isinstance(skills_field, str):
        skill_dirs.append(plugin_dir / skills_field)
    elif isinstance(skills_field, list):
        skill_dirs.extend(plugin_dir / s for s in skills_field)

    default_skills_dir = plugin_dir / "skills"
    if default_skills_dir.is_dir():
        skill_dirs.append(default_skills_dir)

    root_skill = plugin_dir / "SKILL.md"
    if not skill_dirs and root_skill.is_file():
        fm = parse_frontmatter(root_skill.read_text(errors="replace"))
        if not fm.get("description"):
            report.warn(str(root_skill), "root-level SKILL.md has no 'description' in frontmatter")
        if not fm.get("name"):
            report.warn(
                str(root_skill),
                "root-level SKILL.md has no 'name' in frontmatter; invocation name falls back to "
                "the install directory, which is a version string for marketplace installs",
            )
        report.skills.append(fm.get("name") or plugin_dir.name)
        return

    seen_names: dict[str, Path] = {}
    for skills_dir in skill_dirs:
        if not skills_dir.is_dir():
            report.warn(str(skills_dir), "skills path from plugin.json does not exist")
            continue
        for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
            skill_name = skill_md.parent.name
            fm = parse_frontmatter(skill_md.read_text(errors="replace"))
            if not fm.get("description"):
                report.error(str(skill_md), "missing required 'description' in frontmatter")
            if skill_name in seen_names:
                report.error(
                    str(skill_md),
                    f"duplicate skill name '{skill_name}' also defined at {seen_names[skill_name]}",
                )
            else:
                seen_names[skill_name] = skill_md
                report.skills.append(fm.get("name") or skill_name)
            check_dangling_references(skill_md, skill_md.parent, report)


def audit_commands(plugin_dir: Path, manifest: dict[str, Any], report: PluginReport) -> None:
    command_paths: list[Path] = []
    commands_field = manifest.get("commands")
    if isinstance(commands_field, str):
        commands_field = [commands_field]
    if isinstance(commands_field, list):
        for entry in commands_field:
            p = plugin_dir / entry
            command_paths.extend(sorted(p.glob("*.md")) if p.is_dir() else [p])
    else:
        default_commands_dir = plugin_dir / "commands"
        if default_commands_dir.is_dir():
            command_paths.extend(sorted(default_commands_dir.glob("*.md")))

    seen_names: dict[str, Path] = {}
    for cmd_md in command_paths:
        if not cmd_md.is_file():
            report.warn(str(cmd_md), "command path from plugin.json does not exist")
            continue
        name = cmd_md.stem
        fm = parse_frontmatter(cmd_md.read_text(errors="replace"))
        if not fm.get("description"):
            report.warn(str(cmd_md), "command has no 'description' in frontmatter")
        if name in seen_names:
            report.error(str(cmd_md), f"duplicate command name '{name}' also defined at {seen_names[name]}")
        else:
            seen_names[name] = cmd_md
            report.commands.append(name)
        check_dangling_references(cmd_md, plugin_dir, report)


def audit_agents(plugin_dir: Path, manifest: dict[str, Any], report: PluginReport) -> None:
    agent_paths: list[Path] = []
    agents_field = manifest.get("agents")
    if isinstance(agents_field, str):
        agents_field = [agents_field]
    if isinstance(agents_field, list):
        for entry in agents_field:
            p = plugin_dir / entry
            agent_paths.extend(sorted(p.glob("*.md")) if p.is_dir() else [p])
    else:
        default_agents_dir = plugin_dir / "agents"
        if default_agents_dir.is_dir():
            agent_paths.extend(sorted(default_agents_dir.glob("*.md")))

    seen_names: dict[str, Path] = {}
    for agent_md in agent_paths:
        if not agent_md.is_file():
            report.warn(str(agent_md), "agent path from plugin.json does not exist")
            continue
        fm = parse_frontmatter(agent_md.read_text(errors="replace"))
        name = fm.get("name") or agent_md.stem
        if not fm.get("name"):
            report.error(str(agent_md), "missing required 'name' in frontmatter")
        if not fm.get("description"):
            report.error(str(agent_md), "missing required 'description' in frontmatter")
        for bad_field in DISALLOWED_AGENT_FIELDS & fm.keys():
            report.error(
                str(agent_md),
                f"'{bad_field}' is not supported for plugin-shipped agents and is silently ignored at runtime",
            )
        unknown = fm.keys() - ALLOWED_AGENT_FIELDS - DISALLOWED_AGENT_FIELDS
        for field_name in unknown:
            report.warn(str(agent_md), f"unrecognized agent frontmatter field '{field_name}'")
        isolation = fm.get("isolation")
        if isolation is not None and isolation != "worktree":
            report.error(str(agent_md), f"'isolation: {isolation}' is invalid; the only valid value is 'worktree'")
        if name in seen_names:
            report.error(str(agent_md), f"duplicate agent name '{name}' also defined at {seen_names[name]}")
        else:
            seen_names[name] = agent_md
            report.agents.append(name)


def audit_json_config(plugin_dir: Path, filename: str, report: PluginReport) -> None:
    path = plugin_dir / filename
    if path.is_file():
        load_json(path, report)


def audit_plugin_dir(plugin_dir: Path) -> PluginReport:
    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
    manifest: dict[str, Any] = {}
    name = plugin_dir.name

    report = PluginReport(path=plugin_dir, name=name)

    if not plugin_dir.is_dir():
        report.error(str(plugin_dir), "plugin directory does not exist")
        return report

    claude_plugin_dir = plugin_dir / ".claude-plugin"
    if claude_plugin_dir.is_dir():
        stray = [p.name for p in claude_plugin_dir.iterdir() if p.name != "plugin.json"]
        for entry in stray:
            report.warn(
                str(claude_plugin_dir / entry),
                "only plugin.json belongs in .claude-plugin/; other component directories must be at the plugin root",
            )

    if manifest_path.is_file():
        loaded = load_json(manifest_path, report)
        if loaded is not None:
            manifest = loaded
            if "name" not in manifest:
                report.error(str(manifest_path), "missing required field 'name'")
            else:
                name = manifest["name"]
                if not KEBAB_CASE_RE.match(name):
                    report.warn(str(manifest_path), f"name '{name}' is not kebab-case")
            unknown_fields = manifest.keys() - KNOWN_PLUGIN_JSON_FIELDS
            for f_name in unknown_fields:
                report.warn(str(manifest_path), f"unrecognized top-level field '{f_name}'")
    report.name = name

    audit_skills(plugin_dir, manifest, report)
    audit_commands(plugin_dir, manifest, report)
    audit_agents(plugin_dir, manifest, report)

    hooks_field = manifest.get("hooks")
    if isinstance(hooks_field, str):
        audit_json_config(plugin_dir, hooks_field, report)
    elif hooks_field is None:
        audit_json_config(plugin_dir, "hooks/hooks.json", report)
    # dict/list means the config is inline in plugin.json already validated above.

    audit_json_config(plugin_dir, ".mcp.json", report)
    audit_json_config(plugin_dir, ".lsp.json", report)

    combined: dict[str, str] = {}
    for kind, names in (("skill", report.skills), ("command", report.commands)):
        for n in names:
            if n in combined and combined[n] != kind:
                report.warn(plugin_dir.name, f"'{n}' is defined as both a {combined[n]} and a {kind}; both share the /{name}:{n} namespace")
            combined[n] = kind

    return report


def find_marketplace_plugins(marketplace_root: Path) -> list[Path] | None:
    marketplace_path = marketplace_root / ".claude-plugin" / "marketplace.json"
    if not marketplace_path.is_file():
        return None
    data = load_json(marketplace_path)
    if data is None:
        return []
    if "name" in data and data["name"] in RESERVED_MARKETPLACE_NAMES:
        print(f"WARN  {marketplace_path}: marketplace name '{data['name']}' is reserved for Anthropic use", file=sys.stderr)
    plugin_dirs = []
    for entry in data.get("plugins", []):
        source = entry.get("source")
        if isinstance(source, str) and source.startswith((".", "/")):
            plugin_dirs.append((marketplace_root / source).resolve())
    return plugin_dirs


def format_report(report: PluginReport) -> str:
    lines = [f"## {report.name}  ({report.path})"]
    lines.append(
        f"skills={len(report.skills)} commands={len(report.commands)} agents={len(report.agents)}"
    )
    if not report.issues:
        lines.append("  no issues found")
    for issue in report.issues:
        lines.append(f"  [{issue.severity}] {issue.location}: {issue.message}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", type=Path, help="marketplace root or single plugin directory")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON instead of text")
    args = parser.parse_args()

    root = args.path.resolve()
    plugin_dirs = find_marketplace_plugins(root)
    if plugin_dirs is None:
        plugin_dirs = [root]

    reports = [audit_plugin_dir(p) for p in plugin_dirs]

    if args.json:
        payload = [
            {
                "name": r.name,
                "path": str(r.path),
                "skills": r.skills,
                "commands": r.commands,
                "agents": r.agents,
                "issues": [
                    {"severity": i.severity, "location": i.location, "message": i.message}
                    for i in r.issues
                ],
            }
            for r in reports
        ]
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for r in reports:
            print(format_report(r))
            print()

    total_errors = sum(r.error_count for r in reports)
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
