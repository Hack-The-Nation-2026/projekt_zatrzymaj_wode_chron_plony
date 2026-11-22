import { continueRender, delayRender, staticFile } from 'remotion'
import { useEffect, useState } from 'react'
import { FONT_FACES, FONT_FAMILY } from './font-faces'

/**
 * Krój serwisu, ten sam co w aplikacji, wpięty z lokalnych plików. Bez czekania
 * na wczytanie pierwsza klatka tekstu wyszłaby zapasowym krojem, a wideo jest
 * renderowane bez sieci.
 */
const CSS = FONT_FACES.map(
  (face) => `@font-face {
  font-family: '${FONT_FAMILY}';
  font-style: normal;
  font-weight: 100 700;
  font-display: block;
  src: url('${staticFile(face.file)}') format('woff2');
  unicode-range: ${face.range};
}`,
).join('\n')

export function AppFont() {
  const [handle] = useState(() => delayRender('Wczytuję IBM Plex Sans'))
  useEffect(() => {
    Promise.all([
      document.fonts.load(`400 1em '${FONT_FAMILY}'`),
      document.fonts.load(`600 1em '${FONT_FAMILY}'`),
      document.fonts.load(`700 1em '${FONT_FAMILY}'`),
    ])
      .catch(() => {})
      .finally(() => continueRender(handle))
  }, [handle])
  return <style dangerouslySetInnerHTML={{ __html: CSS }} />
}
