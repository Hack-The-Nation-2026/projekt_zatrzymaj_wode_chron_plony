import { Composition } from 'remotion'
import { Video, totalFrames } from './Video'

const FPS = 30

export function RemotionRoot() {
  return (
    <Composition
      id="Wodnik"
      component={Video}
      durationInFrames={totalFrames(FPS)}
      fps={FPS}
      width={1920}
      height={1080}
    />
  )
}
