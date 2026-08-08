#!/usr/bin/env python3
"""Audit OpenAI Codex CLI extension artifacts: skills, legacy custom prompts,
MCP server config, and hooks config.

Usage:
    audit_codex.py [path ...] [--json]

Each <path> is a ".codex" root (e.g. ~/.codex for the personal scope, or
.codex/ inside a project). If no path is given, ~/.codex is used when it
exists.

IMPORTANT — confidence levels differ by section. Codex CLI's authoritative
docs live at developers.openai.com/codex, which was unreachable from the
environment this script was written in. Findings are labeled by severity:

  ERROR  - an objective defect (invalid JSON/TOML, a required field missing)
           or something confirmed via multiple independent secondary
           sources describing the current (skills) or former
           (custom prompts) Codex documentation.
  WARN   - a quality issue on the same well-corroborated ground as ERROR.
  CHECK  - based on secondary-source reporting for areas (MCP server
           config, hooks config) this script's author could not verify
           against the primary docs. Treat these as "worth a manual look",
           not as confirmed defects. Re-verify against
           https://developers.openai.com/codex before trusting them.

Unlike Claude Code, Codex CLI has no single "plugin" manifest bundling
these mechanisms together — they are independent, separately-configured
features. This script audits each one it finds under the given root(s).
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
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

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
SEVERITY_CHECK = "CHECK"  # unverified-schema finding; confirm manually

REFERENCE_RE = re.compile(r"[`\"']((?:\./)?(?:references|scripts|assets)/[\w./-]+)[`\"']")

# Gathered from secondary sources (blog posts, aggregators) describing
# Codex's hooks system, NOT confirmed against developers.openai.com/codex/hooks.
# A hook event outside this list is not necessarily wrong -- this list itself
# may be incomplete or stale. Treat mismatches as CHECK, never ERROR.
UNVERIFIED_CANDIDATE_HOOK_EVENTS = {
    "PreToolUse", "PostToolUse", "PermissionRequest", "PreCompact",
    "PostCompact", "SessionStart", "SessionEnd", "SubagentStart",
    "SubagentStop", "UserPromptSubmit", "Stop",
}


@dataclass
class Issue:
    severity: str
    location: str
    message: str


@dataclass
class CodexReport:
    root: Path
    skills: dict[str, Path] = field(default_factory=dict)
    prompts: dict[str, Path] = field(default_factory=dict)
    mcp_servers: list[str] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    def error(self, location: str, message: str) -> None:
        self.issues.append(Issue(SEVERITY_ERROR, location, message))

    def warn(self, location: str, message: str) -> None:
        self.issues.append(Issue(SEVERITY_WARN, location, message))

    def check(self, location: str, message: str) -> None:
        self.issues.append(Issue(SEVERITY_CHECK, location, message))

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == SEVERITY_ERROR)


def check_dangling_references(md_path: Path, base_dir: Path, report: CodexReport) -> None:
    text = md_path.read_text(errors="replace")
    for m in REFERENCE_RE.finditer(text):
        ref = m.group(1).lstrip("./")
        if not (base_dir / ref).exists():
            report.warn(str(md_path), f"references '{ref}' but that file does not exist under {base_dir}")


def audit_skills(root: Path, report: CodexReport) -> None:
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        return
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        skill_name = skill_md.parent.name
        fm = parse_frontmatter(skill_md.read_text(errors="replace"))
        if not fm.get("description"):
            report.error(str(skill_md), "missing required 'description' in frontmatter")
        if not fm.get("name"):
            report.warn(str(skill_md), "missing 'name' in frontmatter")
        elif fm["name"] != skill_name:
            report.warn(
                str(skill_md),
                f"frontmatter name '{fm['name']}' does not match directory name '{skill_name}'",
            )
        if skill_name in report.skills:
            report.error(
                str(skill_md),
                f"duplicate skill name '{skill_name}' also defined at {report.skills[skill_name]}",
            )
        else:
            report.skills[skill_name] = skill_md
        check_dangling_references(skill_md, skill_md.parent, report)


def audit_prompts(root: Path, report: CodexReport) -> None:
    prompts_dir = root / "prompts"
    if not prompts_dir.is_dir():
        return

    top_level = sorted(p for p in prompts_dir.glob("*.md") if p.is_file())
    nested = sorted(p for p in prompts_dir.rglob("*.md") if p.is_file() and p.parent != prompts_dir)
    if nested:
        report.warn(
            str(prompts_dir),
            f"{len(nested)} markdown file(s) found in subdirectories; Codex only scans "
            "top-level files in prompts/, so these are not registered as commands",
        )

    for prompt_md in top_level:
        name = prompt_md.stem
        report.warn(
            str(prompt_md),
            "custom prompts are deprecated by OpenAI in favor of skills/ — consider migrating",
        )
        if name in report.prompts:
            report.error(str(prompt_md), f"duplicate prompt name '{name}' also defined at {report.prompts[name]}")
        else:
            report.prompts[name] = prompt_md
        check_dangling_references(prompt_md, prompts_dir, report)


def audit_config_toml(root: Path, report: CodexReport) -> None:
    config_path = root / "config.toml"
    if not config_path.is_file():
        return
    if tomllib is None:
        report.check(str(config_path), "no TOML parser available (install tomli on Python <3.11) — skipped")
        return

    try:
        data = tomllib.loads(config_path.read_text())
    except tomllib.TOMLDecodeError as exc:
        report.error(str(config_path), f"invalid TOML: {exc}")
        return

    mcp_servers = data.get("mcp_servers")
    if isinstance(mcp_servers, dict):
        for name, entry in mcp_servers.items():
            report.mcp_servers.append(name)
            if not isinstance(entry, dict):
                continue
            has_command = "command" in entry
            has_url = "url" in entry
            if has_command and has_url:
                report.check(
                    str(config_path),
                    f"mcp_servers.{name} sets both 'command' and 'url' — secondary sources describe these as "
                    "mutually exclusive transport selectors (stdio vs streamable HTTP); confirm against primary docs",
                )
            elif not has_command and not has_url:
                report.check(
                    str(config_path),
                    f"mcp_servers.{name} sets neither 'command' nor 'url' — one is expected to select transport; "
                    "confirm against primary docs",
                )

    hooks = data.get("hooks")
    if isinstance(hooks, dict):
        for event_name in hooks:
            if event_name not in UNVERIFIED_CANDIDATE_HOOK_EVENTS:
                report.check(
                    str(config_path),
                    f"hooks.{event_name}: not in this script's unverified reference list of Codex hook event "
                    "names — may be valid; the reference list itself is not confirmed against primary docs",
                )

    if "allow_managed_hooks_only" in data:
        report.check(
            str(config_path),
            "'allow_managed_hooks_only' found in config.toml — secondary sources describe this key as only "
            "supported in requirements.toml, not config.toml; confirm against primary docs",
        )


def audit_hooks_json(root: Path, report: CodexReport) -> None:
    hooks_path = root / "hooks.json"
    if not hooks_path.is_file():
        return
    try:
        data = json.loads(hooks_path.read_text())
    except json.JSONDecodeError as exc:
        report.error(str(hooks_path), f"invalid JSON: {exc}")
        return
    if isinstance(data, dict):
        for event_name in data:
            if event_name not in UNVERIFIED_CANDIDATE_HOOK_EVENTS:
                report.check(
                    str(hooks_path),
                    f"'{event_name}': not in this script's unverified reference list of Codex hook event names — "
                    "may be valid; confirm against primary docs",
                )


def audit_root(root: Path) -> CodexReport:
    report = CodexReport(root=root)
    if not root.is_dir():
        report.error(str(root), "path does not exist")
        return report
    audit_skills(root, report)
    audit_prompts(root, report)
    audit_config_toml(root, report)
    audit_hooks_json(root, report)
    return report


def format_report(report: CodexReport) -> str:
    lines = [f"## {report.root}"]
    lines.append(
        f"skills={len(report.skills)} prompts={len(report.prompts)} mcp_servers={len(report.mcp_servers)}"
    )
    if not report.issues:
        lines.append("  no issues found")
    for issue in report.issues:
        lines.append(f"  [{issue.severity}] {issue.location}: {issue.message}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", type=Path, help="one or more .codex roots (default: ~/.codex)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON instead of text")
    args = parser.parse_args()

    roots = args.paths or ([Path.home() / ".codex"] if (Path.home() / ".codex").is_dir() else [])
    if not roots:
        parser.error("no path given and ~/.codex does not exist")

    reports = [audit_root(r.expanduser().resolve()) for r in roots]

    # Cross-root: same skill/prompt name defined in more than one scope.
    seen_skills: dict[str, Path] = {}
    seen_prompts: dict[str, Path] = {}
    for report in reports:
        for name, path in report.skills.items():
            if name in seen_skills and seen_skills[name] != path:
                report.warn(
                    str(path),
                    f"skill '{name}' is also defined at {seen_skills[name]} in another scope; "
                    "cross-scope precedence is not verified against primary docs",
                )
            seen_skills[name] = path
        for name, path in report.prompts.items():
            if name in seen_prompts and seen_prompts[name] != path:
                report.warn(
                    str(path),
                    f"prompt '{name}' is also defined at {seen_prompts[name]} in another scope; "
                    "cross-scope precedence is not verified against primary docs",
                )
            seen_prompts[name] = path

    if args.json:
        payload = [
            {
                "root": str(r.root),
                "skills": list(r.skills),
                "prompts": list(r.prompts),
                "mcp_servers": r.mcp_servers,
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
