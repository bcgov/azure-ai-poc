import '@bcgov/bc-sans/css/BC_Sans.css'
import { StrictMode } from 'react'
import * as ReactDOM from 'react-dom/client'
import { RouterProvider, createRouter } from '@tanstack/react-router'

// Import bootstrap styles
import '@/scss/styles.scss'

// Import BC Gov themed chat styles (applies global color overrides)
import '@/styles/chat.css'

// Import the generated route tree
import { routeTree } from './routeTree.gen'
import { AuthProvider } from '@/components/AuthProvider'
import { initializeMsal } from '@/service/auth-service'

// Create a new router instance
const router = createRouter({ routeTree })

// Register the router instance for type safety
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

const renderApp = () => {
  ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
    <StrictMode>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </StrictMode>,
  )
}

// Initialize MSAL before rendering routes (avoids redirect race conditions)
initializeMsal()
  .catch((err) => {
    console.error('Failed to initialize MSAL:', err)
  })
  .finally(() => {
    renderApp()
  })
