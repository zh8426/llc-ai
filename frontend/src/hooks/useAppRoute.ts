import { useEffect, useState } from 'react'

export type AppRoute = 'project' | 'gain-curve' | 'waveform' | 'datasheets'

function routeFromPath(pathname: string): AppRoute {
  if (pathname.startsWith('/gain-curve')) return 'gain-curve'
  if (pathname.startsWith('/waveform')) return 'waveform'
  if (pathname.startsWith('/datasheets')) return 'datasheets'
  return 'project'
}

export function useAppRoute() {
  const [route, setRoute] = useState<AppRoute>(() => routeFromPath(window.location.pathname))

  useEffect(() => {
    const handlePopState = () => setRoute(routeFromPath(window.location.pathname))
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  function navigate(pathname: string) {
    window.history.pushState({}, '', pathname)
    setRoute(routeFromPath(pathname))
  }

  return { route, navigate }
}
