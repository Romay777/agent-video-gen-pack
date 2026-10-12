import { Composition } from "remotion";
import {
  calculateMetadata,
  FPS,
  Narrated,
  type NarratedProps,
  type SceneData,
} from "./Narrated";
import scene01 from "../public/voiceover/scene-01.json";
import scene02 from "../public/voiceover/scene-02.json";

const toScene = (
  id: string,
  t: { audio: string; duration: number; captions: SceneData["captions"] },
): SceneData => ({
  id,
  audio: `voiceover/${id}.mp3`,
  duration: t.duration,
  captions: t.captions,
});

const defaultProps: NarratedProps = {
  scenes: [toScene("scene-01", scene01), toScene("scene-02", scene02)],
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Narrated"
    component={Narrated}
    durationInFrames={300}
    fps={FPS}
    width={1920}
    height={1080}
    defaultProps={defaultProps}
    calculateMetadata={calculateMetadata}
  />
);
