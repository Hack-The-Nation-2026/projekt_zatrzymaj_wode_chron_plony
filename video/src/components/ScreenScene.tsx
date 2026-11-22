import { AbsoluteFill, OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig, interpolate } from 'remotion'
import type { CSSProperties } from 'react'
import type { CameraKey, Scene } from '../edl'
import { ease, theme } from '../theme'

const WIDTH = 1920
const HEIGHT = 1080

/** Ruch kamery: powiększenie i punkt kadru, zawsze wewnątrz nagrania. */
function useCamera(keys: CameraKey[], frame: number, fps: number) {
  const times = keys.map((key) => key.t * fps)
  const read = (pick: (key: CameraKey) => number) =>
    interpolate(frame, times, keys.map(pick), {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: ease.inOut,
    })
  const z = read((key) => key.z)
  // Kamera nie może wyjechać poza nagranie, inaczej w kadrze pojawia się tło kompozycji.
  const halfW = WIDTH / 2 / z
  const halfH = HEIGHT / 2 / z
  const x = Math.min(Math.max(read((key) => key.x), halfW), WIDTH - halfW)
  const y = Math.min(Math.max(read((key) => key.y), halfH), HEIGHT - halfH)
  return { z, x, y }
}

/**
 * Napisy na dole kadru. Część jury ogląda film bez dźwięku, więc zdanie lektora
 * idzie także na ekran. Pas jest wyciemniony u dołu, żeby tekst był czytelny nad
 * dowolnym ekranem aplikacji.
 */
function Caption({ title, caption, fps }: { title?: string; caption?: string; fps: number }) {
  const frame = useCurrentFrame()
  if (!caption && !title) return null
  const rise = interpolate(frame, [8, 22], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: ease.smooth,
  })
  return (
    <AbsoluteFill style={{ justifyContent: 'flex-end', pointerEvents: 'none', fontFamily: theme.font }}>
      <div
        style={{
          padding: '150px 96px 52px',
          background:
            'linear-gradient(180deg, rgba(9,20,30,0) 0%, rgba(9,20,30,0.72) 34%, rgba(9,20,30,0.94) 62%, rgba(9,20,30,0.97) 100%)',
          opacity: rise,
          transform: `translateY(${(1 - rise) * 24}px)`,
        }}
      >
        {title ? (
          <div
            style={{
              color: theme.water,
              fontSize: 21,
              fontWeight: 700,
              letterSpacing: '0.16em',
              textTransform: 'uppercase',
              marginBottom: 12,
            }}
          >
            {title}
          </div>
        ) : null}
        {caption ? (
          <div
            style={{
              color: theme.ink,
              fontSize: 39,
              fontWeight: 600,
              lineHeight: 1.3,
              letterSpacing: '-0.005em',
              maxWidth: 1560,
              textShadow: '0 2px 14px rgba(0,0,0,0.55)',
            }}
          >
            {caption}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  )
}

/** Nagranie pulpitu: całe okno serwisu z powolnym ruchem kamery i napisem lektora. */
export function ScreenScene({ scene }: { scene: Scene }) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const camera = scene.camera?.length ? scene.camera : [{ t: 0, z: 1, x: 960, y: 540 }]
  const { z, x, y } = useCamera(camera, frame, fps)

  const transform: CSSProperties = {
    transform: `scale(${z}) translate(${WIDTH / 2 - x}px, ${HEIGHT / 2 - y}px)`,
    transformOrigin: '50% 50%',
  }

  // Karta końcowa nie ma nagrania, więc ta scena zostaje pusta.
  if (!scene.clip) return <AbsoluteFill style={{ backgroundColor: theme.deep }} />

  return (
    <AbsoluteFill style={{ backgroundColor: theme.deep, overflow: 'hidden' }}>
      <AbsoluteFill style={transform}>
        <OffthreadVideo
          src={staticFile(`clips/${scene.clip}.mp4`)}
          startFrom={Math.round(scene.from * fps)}
          playbackRate={scene.rate ?? 1}
          muted
          style={{ width: WIDTH, height: HEIGHT }}
        />
      </AbsoluteFill>
      <Caption title={scene.title} caption={scene.caption} fps={fps} />
    </AbsoluteFill>
  )
}

export { WIDTH, HEIGHT }
