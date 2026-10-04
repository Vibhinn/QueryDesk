import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { initializeAuth } from './authClient'
import './styles.css'

const root = ReactDOM.createRoot(document.getElementById('root')!)

void initializeAuth().catch(() => undefined).finally(() => {
  root.render(<React.StrictMode><App /></React.StrictMode>)
})
