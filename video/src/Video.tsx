import { AbsoluteFill, Sequence, interpolate, useCurrentFrame, useVideoConfig } from 'remotion'
import { scenes, sceneDuration } from './edl'
import { AppFont } from './AppFont'
import { ScreenScene } from './components/ScreenScene'
import { OutroScene } from './components/OutroScene'
import { theme } from './theme'

/**
 * Montaż bez przenikań: rozdziały stykają się cięciem, więc między dwiema
 * różnymi stronami nie ma mętnej klatki pośredniej. Tylko początek wychodzi z czerni.
 */
function layout(fps: number) {
  const items: { scene: (typeof scenes)[number]; from: number; duration: number }[] = []
  let cursor = 0
  for (const scene of scenes) {
    const duration = sceneDuration(scene, fps)
    items.push({ scene, from: cursor, duration })
    cursor += duration
  }
  return { items, total: cursor }
}

export function Video() {
  const { fps } = useVideoConfig()
  const frame = useCurrentFrame()
  const { items, total } = layout(fps)

  const fadeIn = interpolate(frame, [0, 7], [1, 0], { extrapolateRight: 'clamp' })

  return (
    <AbsoluteFill style={{ backgroundColor: theme.deep }}>
      <AppFont />
      {items.map(({ scene, from, duration }) => (
        <Sequence key={scene.id} from={from} durationInFrames={duration} name={scene.id}>
          {scene.kind === 'outro' ? <OutroScene /> : <ScreenScene scene={scene} />}
        </Sequence>
      ))}
      {total > 0 && (
        <AbsoluteFill style={{ backgroundColor: '#000', opacity: fadeIn, pointerEvents: 'none' }} />
      )}
    </AbsoluteFill>
  )
}

export const totalFrames = (fps: number) => layout(fps).total
