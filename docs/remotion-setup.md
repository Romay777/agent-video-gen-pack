# Remotion setup

Source: the [Remotion README](https://github.com/remotion-dev/remotion) and [Remotion docs → AI skills](https://www.remotion.dev/docs/ai/skills).

Remotion renders React components to video. You write a composition (a React component that reads the current frame), preview it in **Remotion Studio**, and render it to MP4.

## Prerequisites

- Node.js (current LTS) and npm. Check with `node -v`.
- `ffmpeg` is not needed by Remotion itself but is used by this repo's scripts.

## Create a project

This repo already has files, so scaffold into a subfolder (the skill's `remotion-create` part says the same):

```bash
npx create-video@latest --yes --blank --no-tailwind my-video
cd my-video
npm i
```

Plain `npx create-video@latest` (no flags) starts the interactive wizard; it can also offer to install the agent skills. Use `--help` to see other templates.

## Studio and render

```bash
npx remotion studio              # live preview in the browser (add --no-open to skip opening it)
npx remotion render <CompositionId> out/video.mp4
npx remotion still <CompositionId> out/frame.png --frame=30
```

Preview first; render only when the person asks (`remotion-studio/` and `remotion-render/` in the `remotion-best-practices` skill).

## Packages the examples use

```bash
npx remotion add @remotion/media       # <Audio>, <Video>
npx remotion add @remotion/captions    # Caption type, used by the Basic Captions element (only for subtitles)
```

`npx remotion add` installs the version that matches the project's Remotion version.

## Agent skills

One third-party skill is installed: `remotion-best-practices` from `remotion-dev/skills`. It is the self-contained bundle: its subfolders (`remotion-markup/`, `remotion-captions/`, `remotion-create/`, …) carry every other Remotion skill, so those are not installed separately.

```bash
npx --yes skills@1.7.0 add remotion-dev/skills --skill remotion-best-practices --yes   # install or update
```

Files land in `.agents/skills/remotion-best-practices/`, `.claude/skills/remotion-best-practices` is a symlink to it, and `skills-lock.json` records the source and hash. Without `--skill` the command installs all twelve Remotion skills, which duplicates the bundle's content.

- Leave the skill's files unedited, since an update overwrites them. This repo's differences from it live in `AGENTS.md` → "Overrides of the Remotion skill".
- Review a skill before updating; skills run with the agent's permissions.
- Agents started at the repo root see `.agents/skills`. Agents started inside a Remotion subfolder should be pointed at the repo root's `AGENTS.md`.
