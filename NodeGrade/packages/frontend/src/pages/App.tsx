/* eslint-disable simple-import-sort/imports */
import {
  createTheme,
  CssBaseline,
  GlobalStyles,
  ThemeProvider,
  useMediaQuery
} from '@mui/material'
import { createContext, useEffect, useMemo, useState } from 'react'
import { Box, Link as MuiLink, Stack, Typography } from '@mui/material'
import {
  createBrowserRouter,
  createRoutesFromElements,
  Link,
  Outlet,
  Route,
  RouterProvider
} from 'react-router-dom'

import ErrorBoundary from '@/components/ErrorBoundary'
import Editor from '@/pages/Editor'
import ValidationDashboard from '@/pages/ValidationDashboard'
import { LtiRegister } from './lti/LtiRegister'
import StudentView from './StudentView'
import InstructorDashboard from './InstructorDashboard'

const LogRouteAccess = () => {
  console.log('Current route: ', window.location.pathname)
  return null
}

const TEMPLATES = [
  {
    label: 'Starter skeleton',
    desc: 'Blank canvas with input nodes and one output — wire them yourself',
    file: 'starter.json'
  },
  {
    label: 'ConceptGrade pipeline',
    desc: 'Knowledge-graph based grading via ConceptGradeNode',
    file: 'concept-grade.json'
  },
  {
    label: 'LLM grader',
    desc: 'Rubric via prompt — builds a message chain and calls the LLM node',
    file: 'llm-grader.json'
  }
]

/** Local dev landing: how to open the graph editor / student view */
const DevHome = () => (
  <Box sx={{ p: 3, maxWidth: 640 }}>
    <Typography variant="h5" gutterBottom>
      NodeGrade — local testing
    </Typography>
    <Typography variant="body1" color="text.secondary" paragraph>
      The app is driven by the URL path. The segment after the domain identifies your graph in the
      database (same path when you save).
    </Typography>
    <Typography variant="subtitle1" sx={{ mt: 2 }}>
      Quick links
    </Typography>
    <Stack spacing={1} sx={{ mt: 1 }}>
      <MuiLink component={Link} to="/ws/editor/local/1/1" variant="body1">
        Open editor — <code>/ws/editor/local/1/1</code>
      </MuiLink>
      <MuiLink component={Link} to="/ws/student/local/1/1" variant="body1">
        Open student view — <code>/ws/student/local/1/1</code>
      </MuiLink>
      <MuiLink component={Link} to="/validation" variant="body1">
        Validation dashboard — <code>/validation</code>
      </MuiLink>
      <MuiLink component={Link} to="/dashboard" variant="body1">
        Instructor analytics dashboard — <code>/dashboard</code>
      </MuiLink>
    </Stack>
    <Typography variant="subtitle1" sx={{ mt: 3 }}>
      Starter templates
    </Typography>
    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 1 }}>
      Open the editor, then use the <strong>Load template</strong> button (folder icon) to load one
      of these starting points:
    </Typography>
    <Stack spacing={1} sx={{ mt: 1 }}>
      {TEMPLATES.map((t) => (
        <Box key={t.file}>
          <Typography variant="body2" fontWeight={600}>
            {t.label}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t.desc}
          </Typography>
        </Box>
      ))}
    </Stack>
    <Typography variant="subtitle1" sx={{ mt: 3 }}>
      Before it works
    </Typography>
    <Typography component="ul" variant="body2" sx={{ pl: 2, mt: 1 }}>
      <li>
        Backend (Nest + Socket.IO) on the port in{' '}
        <code>public/config/env.development.json</code> → <code>API</code> (default{' '}
        <code>http://localhost:5001/</code>)
      </li>
      <li>PostgreSQL running and <code>DATABASE_URL</code> set in <code>packages/backend/.env</code></li>
      <li>Optional: LLM worker at <code>MODEL_WORKER_URL</code> if you use LLM nodes</li>
    </Typography>
  </Box>
)

export const ColorModeContext = createContext({ toggleColorMode: () => {} })
// Pathless layout route must render <Outlet /> or nested routes never appear (blank page).
const router = createBrowserRouter(
  createRoutesFromElements(
    <Route element={<Outlet />}>
      {/* /ke.moodle/2/2 */}
      <Route
        path="ws/editor/:domain/:courseId/:elementId"
        element={
          <ErrorBoundary>
            <Editor />
          </ErrorBoundary>
        }
      />
      <Route
        path="ws/student/:domain/:courseId/:elementId"
        element={
          <ErrorBoundary>
            <StudentView />
          </ErrorBoundary>
        }
      />
      <Route index element={<DevHome />} />
      <Route path="validation" element={<ValidationDashboard />} />
      <Route path="dashboard" element={<InstructorDashboard />} />
      <Route path="lti/register" element={<LtiRegister />} />
      <Route path="lti/login" element={<LogRouteAccess />} />
      <Route path="lti/deeplink" element={<LogRouteAccess />} />
      <Route path="*" element={<LogRouteAccess />} />
    </Route>
  )
)
export const BasicApp = () => {
  return <RouterProvider router={router} />
}

const COLOR_MODE_KEY = 'ng-color-mode'

export const App = () => {
  const [mode, setMode] = useState<'light' | 'dark' | null>(() => {
    const stored = localStorage.getItem(COLOR_MODE_KEY)
    return stored === 'light' || stored === 'dark' ? stored : null
  })
  const prefersDarkMode = useMediaQuery('(prefers-color-scheme: dark)')

  useEffect(() => {
    if (mode !== null) {
      localStorage.setItem(COLOR_MODE_KEY, mode)
    }
  }, [mode])

  const colorMode = useMemo(
    () => ({
      toggleColorMode: () => {
        setMode((prevMode) => {
          const current = prevMode ?? (prefersDarkMode ? 'dark' : 'light')
          return current === 'light' ? 'dark' : 'light'
        })
      }
    }),
    [prefersDarkMode]
  )

  const theme = useMemo(
    () =>
      createTheme({
        palette: {
          mode: mode ?? (prefersDarkMode ? 'dark' : 'light')
        }
      }),
    [mode, prefersDarkMode]
  )

  return (
    <ColorModeContext.Provider value={colorMode}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <GlobalStyles
          styles={{
            '.lgraphcanvas': {
              color: '#121212'
            }
          }}
        />
        <BasicApp />
      </ThemeProvider>
    </ColorModeContext.Provider>
  )
}

export default App
