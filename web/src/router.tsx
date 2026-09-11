import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { Dashboard } from './pages/Dashboard'
import { Landing } from './pages/Landing'

export function Router() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/app" element={<Dashboard />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
