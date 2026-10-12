import type { Caption } from "@remotion/captions";
import { Audio } from "@remotion/media";
import type { CalculateMetadataFunction } from "remotion";
import { AbsoluteFill, Series, staticFile, useVideoConfig } from "remotion";
import { BasicCaptions } from "./basic-captions";

export const FPS = 30;
const PAD_SECONDS = 0.6; // breathing room after each line of narration

export type SceneData = {
  id: string;
  audio: string; // path inside public/, e.g. "voiceover/scene-01.mp3"
  duration: number; // seconds, from the timings JSON
  captions: Caption[]; // from the timings JSON, relative to this scene's start
};
export type NarratedProps = { scenes: SceneData[] };

const sceneFrames = (scene: SceneData) =>
  Math.ceil((scene.duration + PAD_SECONDS) * FPS);

export const calculateMetadata: CalculateMetadataFunction<NarratedProps> = ({
  props,
}) => ({
  durationInFrames: props.scenes.reduce((sum, s) => sum + sceneFrames(s), 0),
});

export const Narrated: React.FC<NarratedProps> = ({ scenes }) => {
  const { fps, width } = useVideoConfig();
  return (
    <AbsoluteFill style={{ backgroundColor: "#0b1020" }}>
      <Series>
        {/* Scenes are mapped from the timings JSON so a re-take resizes its scene by itself.
            Write a sequence out by hand when a scene needs its own visuals or Studio editing. */}
        {scenes.map((scene) => (
          <Series.Sequence
            key={scene.id}
            name={scene.id}
            durationInFrames={sceneFrames(scene)}
            premountFor={fps}
          >
            <Audio src={staticFile(scene.audio)} premountFor={fps} />
            {/* ...visuals for this scene go here... */}
            <BasicCaptions
              captions={scene.captions}
              width={width * 0.8}
              style={{ position: "absolute", bottom: 120, left: width * 0.1 }}
            />
          </Series.Sequence>
        ))}
      </Series>
    </AbsoluteFill>
  );
};
