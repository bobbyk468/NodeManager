// top level import
import '@/utils/css'

import React from 'react'
import { createRoot } from 'react-dom/client'
import { registerSW } from 'virtual:pwa-register'

import { setConfig } from '@/utils/config'

const container = document.getElementById('root')
const root = createRoot(container!)

import { App } from './pages/App'

const configUrl = `${import.meta.env.BASE_URL}config/env.${import.meta.env.MODE}.json`

fetch(configUrl)
  .then((response) => {
    if (!response.ok) {
      throw new Error('Could not load config: ' + response.statusText)
    }
    return response.json()
  })
  .then((config) => {
    setConfig(config)

    root.render(<App />)
  })
  .catch((error) => {
    console.error(error)
    root.render(
      <div style={{ padding: 24, fontFamily: 'system-ui' }}>
        <h1>Config error</h1>
        <p>Could not load {configUrl}</p>
        <pre>{String(error)}</pre>
      </div>
    )
  })

const updateSW = registerSW({
  onNeedRefresh() {
    console.info('New version available; refresh the page to update.')
  },
  onOfflineReady() {
    console.info('App is ready for offline use.')
  },
  onRegisterError(error) {
    console.warn('Service worker registration failed:', error)
  }
})
updateSW()
