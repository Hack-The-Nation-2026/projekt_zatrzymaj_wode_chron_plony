import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from 'remotion'
import { theme } from '../theme'

// Kropla wody: znak Wodnika na karcie końcowej.
const DROP =
  'M12 2.1c3.9 4.7 7.1 8.6 7.1 12.3a7.1 7.1 0 1 1-14.2 0C4.9 10.7 8.1 6.8 12 2.1z'

/** Karta końcowa: adres demo z kodem QR. Jedno wejście, więc uwaga idzie na kod. */
export function OutroScene() {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()

  const enter = interpolate(frame, [0, Math.round(fps * 0.45)], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  })
  const rise = interpolate(frame, [0, Math.round(fps * 0.7)], [26, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  })

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.deep,
        backgroundImage:
          'radial-gradient(1100px 520px at 84% -6%, rgba(74,163,232,0.20), transparent 62%),' +
          'radial-gradient(900px 520px at -6% 108%, rgba(99,179,78,0.18), transparent 60%)',
        fontFamily: theme.font,
        color: theme.ink,
        display: 'flex',
        alignItems: 'center',
        gap: 96,
        padding: '0 132px',
        opacity: enter,
        transform: `translateY(${rise}px)`,
      }}
    >
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <svg viewBox="0 0 24 24" width="58" height="58" aria-hidden>
            <path d={DROP} fill={theme.water} />
          </svg>
          <span style={{ fontSize: 34, fontWeight: 700, letterSpacing: '-0.01em' }}>Wodnik</span>
        </div>
        <div style={{ fontSize: 66, fontWeight: 700, lineHeight: 1.05, marginTop: 38, letterSpacing: '-0.02em' }}>
          Zatrzymaj wodę,
          <br />
          chroń plony
        </div>
        <div style={{ width: 92, height: 6, backgroundColor: theme.water, margin: '32px 0 28px' }} />
        <div style={{ fontSize: 29, color: theme.soft, lineHeight: 1.5, maxWidth: 640 }}>
          Zeskanuj kod albo wejdź na stronę. Numer działki, uprawa i data — a Wodnik powie, gdzie
          zatrzymać wodę i co zrobić najpierw.
        </div>
        <div style={{ fontSize: 20, color: theme.muted, marginTop: 26, letterSpacing: '0.02em' }}>
          HackNation 2026 · zadanie KOWR „Zatrzymaj wodę, chroń plony”
        </div>
      </div>

      <div
        style={{
          backgroundColor: theme.panel,
          border: `1px solid ${theme.line}`,
          padding: 32,
          borderRadius: 18,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 20,
          boxShadow: '0 30px 70px -30px rgba(0,0,0,0.7)',
        }}
      >
        <Img src={staticFile('qr-wodnik.png')} style={{ width: 320, height: 320 }} />
        <span style={{ fontSize: 28, fontWeight: 700, color: theme.water }}>wodnik.vercel.app</span>
      </div>
    </AbsoluteFill>
  )
}
