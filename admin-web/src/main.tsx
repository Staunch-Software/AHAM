import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App, { makeQueryClient } from './app/App'
import '@fontsource-variable/inter'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App client={makeQueryClient()} />
    </BrowserRouter>
  </React.StrictMode>,
)
