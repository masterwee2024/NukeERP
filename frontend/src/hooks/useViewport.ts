import { useState, useEffect } from "react";

export interface ViewportInfo {
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
}

export function useViewport(): ViewportInfo {
  const [viewport, setViewport] = useState<ViewportInfo>(() => {
    const w = typeof window !== "undefined" ? window.innerWidth : 1440;
    return {
      isMobile: w < 768,
      isTablet: w >= 768 && w <= 1024,
      isDesktop: w > 1024,
    };
  });

  useEffect(() => {
    function handleResize() {
      const w = window.innerWidth;
      setViewport({
        isMobile: w < 768,
        isTablet: w >= 768 && w <= 1024,
        isDesktop: w > 1024,
      });
    }
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return viewport;
}
