import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { initializeAuth } from './authClient'
import './styles.css'

const root = ReactDOM.createRoot(document.getElementById('root')!)

void initializeAuth().then(() => {
  root.render(<React.StrictMode><App /></React.StrictMode>)
}).catch(() => {
  root.render(<main className="auth-start-error">Could not connect to the sign-in service. Check that Keycloak is running, then reload.</main>)
})
