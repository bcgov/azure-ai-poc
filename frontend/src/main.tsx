import '@bcgov/bc-sans/css/BC_Sans.css'
import { StrictMode } from 'react'
import * as ReactDOM from 'react-dom/client'
import { RouterProvider, createRouter } from '@tanstack/react-router'

// Import bootstrap styles
import '@/scss/styles.scss'

// Import the generated route tree
import { routeTree } from './routeTree.gen'
import UserService from './services/user-service'

// Create a new router instance
const router = createRouter({ routeTree })

// Register the router instance for type safety
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

const onAuthenticatedCallback = () =>
  ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
    <StrictMode>
      <RouterProvider router={router} />
    </StrictMode>,
  )
UserService.initKeycloak(onAuthenticatedCallback)
