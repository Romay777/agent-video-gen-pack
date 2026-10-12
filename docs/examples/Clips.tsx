import { Video } from "@remotion/media";
import {
  AbsoluteFill,
  interpolate,
  Sequence,
  Series,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BasicCaptions } from "./basic-captions";

// One video made of two clips. For separate videos, make one composition like this per video.
// Register in Root.tsx (durationInFrames = sum of the sequences below):
//   <Composition id="Clips" component={Clips} durationInFrames={330} fps={30} width={1080} height={1920} />

// Horizontal footage in a vertical frame: the whole picture, over a blurred copy of itself.
const Footage: React.FC<{ src: string }> = ({ src }) => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <Video
        src={staticFile(src)}
        muted
        premountFor={fps}
        objectFit="cover"
        style={{
          width: "100%",
          height: "100%",
          filter: "blur(40px) brightness(0.6)",
          scale: "1.2",
        }}
      />
      <AbsoluteFill>
        <Video
          src={staticFile(src)}
          premountFor={fps}
          objectFit="contain"
          style={{ width: "100%", height: "100%" }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Title: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 200 } });
  return (
    <div
      style={{
        position: "absolute",
        top: 260,
        left: 80,
        right: 80,
        textAlign: "center",
        fontFamily: "sans-serif",
        fontSize: 84,
        fontWeight: 800,
        color: "white",
        textShadow: "0 6px 24px rgba(0,0,0,0.7)",
        opacity: pop,
        scale: String(interpolate(pop, [0, 1], [0.85, 1])),
      }}
    >
      {text}
    </div>
  );
};

const ProgressBar: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        bottom: 0,
        height: 12,
        width: `${(frame / (durationInFrames - 1)) * 100}%`,
        backgroundColor: "#ffd400",
      }}
    />
  );
};

export const Clips: React.FC = () => {
  const { fps, width } = useVideoConfig();
  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <Series>
        {/* One hand-written sequence per clip: video, captions and overlays share its timing. */}
        <Series.Sequence name="Clip 01" durationInFrames={180} premountFor={fps}>
          <Footage src="clips/clip-01.mp4" />
          <Sequence name="Title" durationInFrames={2 * fps} premountFor={fps}>
            <Title text="Nobody tells you this" />
          </Sequence>
          <BasicCaptions
            name="Clip 01 captions"
            premountFor={fps}
            width={width * 0.8}
            style={{ position: "absolute", bottom: 420, left: width * 0.1 }}
            // Paste the `captions` array from public/clips/clip-01.json here.
            captions={[
              { text: "Nobody", startMs: 160, endMs: 480, timestampMs: 320, confidence: 0.99 },
              { text: " tells", startMs: 480, endMs: 720, timestampMs: 600, confidence: 0.99 },
              { text: " you", startMs: 720, endMs: 880, timestampMs: 800, confidence: 0.99 },
              { text: " this.", startMs: 880, endMs: 1280, timestampMs: 1080, confidence: 0.98 },
            ]}
          />
        </Series.Sequence>
        <Series.Sequence name="Clip 02" durationInFrames={150} premountFor={fps}>
          <Footage src="clips/clip-02.mp4" />
          <BasicCaptions
            name="Clip 02 captions"
            premountFor={fps}
            width={width * 0.8}
            style={{ position: "absolute", bottom: 420, left: width * 0.1 }}
            captions={[
              { text: "And", startMs: 80, endMs: 240, timestampMs: 160, confidence: 0.99 },
              { text: " here", startMs: 240, endMs: 480, timestampMs: 360, confidence: 0.99 },
              { text: " is", startMs: 480, endMs: 640, timestampMs: 560, confidence: 0.99 },
              { text: " why.", startMs: 640, endMs: 1040, timestampMs: 840, confidence: 0.97 },
            ]}
          />
        </Series.Sequence>
      </Series>
      <ProgressBar />
    </AbsoluteFill>
  );
};
