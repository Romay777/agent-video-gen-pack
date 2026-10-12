# Remotion setup

Source: the [Remotion README](https://github.com/remotion-dev/remotion) and [Remotion docs → AI skills](https://www.remotion.dev/docs/ai/skills).

Remotion renders React components to video. You write a composition (a React component that reads the current frame), preview it in **Remotion Studio**, and render it to MP4.

## Prerequisites

- Node.js (current LTS) and npm. Check with `node -v`.
- `ffmpeg` is not needed by Remotion itself but is used by this repo's scripts.

## Create a project

This repo already has files, so scaffold into a subfolder (the `remotion-create` skill says the same):

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

Preview first; render only when the person asks (see `remotion-studio` and `remotion-render` skills).

## Packages used by this pipeline

```bash
npx remotion add @remotion/media       # <Audio>, <Video>
npx remotion add @remotion/captions    # Caption type, used by the Basic Captions element
```

`npx remotion add` installs the version that matches the project's Remotion version.

## Agent skills

Skills in this repo were installed with:

```bash
npx --yes skills@1.7.0 add remotion-dev/skills --yes
```

That is what `npx remotion skills add` runs under the hood. Files land in `.agents/skills/<name>/` and `.claude/skills/<name>` are symlinks to them. `skills-lock.json` records the source and hashes.

- Update: `npx remotion skills update` (from a Remotion project) or re-run the command above.
- Added or changed skills are picked up by agents on the next session.
- Review a skill before updating; skills run with the agent's permissions.

If you scaffold a Remotion project in a subfolder and want the skills available inside it too, nothing to do: agents started at the repo root see `.agents/skills` here. Agents started inside the subfolder should be pointed at the repo root's `AGENTS.md`.
