# Installation

Map Skill supports two distribution paths:

1. the all-in-one skills-only plugin, which contains Universal plus all city editions;
2. a standalone skill ZIP for Universal or one city.

## Recommended: Git-backed plugin marketplace

Add the public GitHub repository as a marketplace source:

```bash
codex plugin marketplace add yigityildiz0/map-skill
```

Then:

1. restart the ChatGPT desktop app;
2. open **Plugins**;
3. choose the **Map Skill** source;
4. install **Map Skill**;
5. start a new chat for a clean activation test.

Inspect configured sources with:

```bash
codex plugin marketplace list
```

Refresh a later release with:

```bash
codex plugin marketplace upgrade map-skill
```

This follows OpenAI's current [plugin marketplace documentation](https://developers.openai.com/plugins/build/plugins). Local/repo marketplace availability can vary by product surface or workspace policy.

## Standalone Universal skill

### Windows PowerShell

```powershell
$mapZip = Join-Path $env:TEMP 'map-skill-universal.zip'
Invoke-WebRequest 'https://github.com/yigityildiz0/map-skill/releases/latest/download/map-skill-universal.zip' -OutFile $mapZip
New-Item -ItemType Directory -Force (Join-Path $env:USERPROFILE '.agents\skills') | Out-Null
Expand-Archive $mapZip (Join-Path $env:USERPROFILE '.agents\skills') -Force
```

Expected file:

```text
%USERPROFILE%\.agents\skills\plan-smart-routes\SKILL.md
```

### macOS / Linux

```bash
curl -L -o /tmp/map-skill-universal.zip \
  https://github.com/yigityildiz0/map-skill/releases/latest/download/map-skill-universal.zip
mkdir -p ~/.agents/skills
unzip -o /tmp/map-skill-universal.zip -d ~/.agents/skills
```

Expected file:

```text
~/.agents/skills/plan-smart-routes/SKILL.md
```

Codex detects skill changes automatically; restart if it does not appear. OpenAI's current [skill guide](https://learn.chatgpt.com/docs/build-skills) documents the user skill location and ChatGPT/Codex activation syntax.

## About the direct plugin ZIP

`map-skill-plugin.zip` contains the plugin manifest and all 17 skills (Universal + 16 city editions). It is provided for offline inspection, advanced local marketplace setups, and supported skills-only plugin upload/import surfaces. Product/workspace import controls can vary.

Prefer the Git-backed marketplace command at the top of this guide. Do not overwrite an existing personal `marketplace.json` merely to use the ZIP; merge or generate a marketplace entry with the official plugin tooling.

## Standalone İstanbul skill

Use the same steps with this file:

```text
https://github.com/yigityildiz0/map-skill/releases/latest/download/map-skill-istanbul.zip
```

It installs as `plan-smart-routes-istanbul`, so it can coexist with Universal.

## Other city editions

Each release ZIP contains exactly one self-contained skill folder. For example:

```text
map-skill-london.zip       → plan-smart-routes-london/
map-skill-hong-kong.zip    → plan-smart-routes-hong-kong/
map-skill-toronto.zip      → plan-smart-routes-toronto/
```

Install only the editions you use. Universal already carries the complete city-source registry; city editions primarily improve triggering and force the matching profile to load.

## Verify the download

Download `SHA256SUMS.txt`, then compare:

Windows PowerShell:

```powershell
Get-FileHash .\map-skill-universal.zip -Algorithm SHA256
```

macOS / Linux:

```bash
sha256sum map-skill-universal.zip
```

## Activation test

Implicit:

```text
I need to get from King's Cross to Heathrow tomorrow and arrive by 08:30.
Compare the reliable public-transport options and give me valid map links.
```

Explicit:

```text
$plan-smart-routes Compare the reliable ways to reach Heathrow by 08:30 tomorrow.
```

The skill should ask for any missing origin/date/time before calculating. That is expected behavior.

## Remove

For a standalone user skill, remove only the exact installed folder:

```text
~/.agents/skills/plan-smart-routes
```

For a marketplace source:

```bash
codex plugin marketplace remove map-skill
```

Review the resolved target before deleting a local folder.
