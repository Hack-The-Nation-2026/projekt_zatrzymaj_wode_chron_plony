import { useState, useEffect } from "react";

const FONT_SIZES = { sm: "87.5%", md: "100%", lg: "118.75%" };

export function useFontSize() {
  const [fontSize, setFontSize] = useState(() => {
    try { return localStorage.getItem("wodnik-font") || "md"; } catch { return "md"; }
  });

  const ZOOM = { sm: 0.9, md: 1, lg: 1.2 };

    useEffect(() => {
      document.documentElement.style.zoom = ZOOM[fontSize];
      try { localStorage.setItem("wodnik-font", fontSize); } catch {}
    }, [fontSize]);

  return [fontSize, setFontSize];
}
