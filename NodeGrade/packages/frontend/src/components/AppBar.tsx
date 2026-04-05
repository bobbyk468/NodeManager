import { GraphSchema } from '@haski/ta-lib'
import { DownloadForOffline, UploadFile } from '@mui/icons-material'
import Brightness4Icon from '@mui/icons-material/Brightness4'
import Brightness7Icon from '@mui/icons-material/Brightness7'
import FolderOpenIcon from '@mui/icons-material/FolderOpen'
import MenuIcon from '@mui/icons-material/Menu'
import ReplayIcon from '@mui/icons-material/Replay'
import SaveIcon from '@mui/icons-material/Save'
import TelegramIcon from '@mui/icons-material/Telegram'
import {
  FormControl,
  IconButton,
  Menu,
  MenuItem,
  Select,
  Stack,
  styled,
  Toolbar,
  Typography,
  useTheme
} from '@mui/material'
import MuiAppBar, { AppBarProps as MuiAppBarProps } from '@mui/material/AppBar'
import Tooltip from '@mui/material/Tooltip'
import { useContext, useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'

import { ColorModeContext } from '@/pages/App'
import { drawerWidth } from '@/pages/Editor'
import { getConfig } from '@/utils/config'

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

interface AppBarProps extends MuiAppBarProps {
  currentPath?: string
  open?: boolean
  handleDrawerOpen?: () => void
  handleSaveGraph?: () => void
  handleClickChangeSocketUrl?: () => void
  handleDownloadGraph?: () => void
  handleUploadGraph?: () => void
  handleWorkflowChange?: (workflow: string) => void
  handlePublishGraph?: () => void
  handleLoadTemplate?: (graph: object) => void
}

const AppBarStyled = styled(MuiAppBar, {
  shouldForwardProp: (prop) => prop !== 'open'
})<AppBarProps>(({ theme, open }) => ({
  transition: theme.transitions.create(['margin', 'width'], {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.leavingScreen
  }),
  ...(open && {
    width: `calc(100% - ${drawerWidth}px)`,
    transition: theme.transitions.create(['margin', 'width'], {
      easing: theme.transitions.easing.easeOut,
      duration: theme.transitions.duration.enteringScreen
    }),
    marginRight: drawerWidth
  })
}))

export const AppBar = (props: AppBarProps) => {
  const location = useLocation()
  const theme = useTheme()
  const colorMode = useContext(ColorModeContext)
  const [workflows, setWorkflows] = useState<GraphSchema[]>([])
  const [selectedWorkflow, setSelectedWorkflow] = useState<GraphSchema>()
  const [templateMenuAnchor, setTemplateMenuAnchor] = useState<null | HTMLElement>(null)

  const workflowChange = (workflow: string) => {
    setSelectedWorkflow(workflows.find((graph) => graph.path === workflow))
    props.handleWorkflowChange?.(workflow)
  }

  const loadTemplate = (file: string) => {
    setTemplateMenuAnchor(null)
    fetch(`/templates/${file}`)
      .then((res) => res.json())
      .then((data: object) => props.handleLoadTemplate?.(data))
      .catch((err) => console.error('Failed to load template:', err))
  }

  useEffect(() => {
    fetch((getConfig().API || '').replace(/\/$/, '/') + 'graphs', {
      credentials: 'include'
    })
      .then((res) => {
        if (!res.ok) {
          // If response is not OK (e.g., 404 Not Found)
          if (res.status === 404) {
            // Handle 404 case specifically
            console.log('No graphs found')
            setWorkflows([])
            setSelectedWorkflow(undefined)
            return []
          }
          // For other error statuses
          throw new Error(`Error fetching graphs: ${res.status}`)
        }
        return res.json()
      })
      .then((graphs: Array<GraphSchema>) => {
        if (graphs && graphs.length > 0) {
          setWorkflows(graphs)
          console.log('graphs', graphs)
          // set the selected workflow
          setSelectedWorkflow(
            graphs.find((graph) => graph.path === props.currentPath) || graphs[0]
          )
        }
      })
      .catch((error) => {
        console.error('Failed to fetch graphs:', error)
        setWorkflows([])
        setSelectedWorkflow(undefined)
      })
  }, [location.pathname])

  return (
    <AppBarStyled position="fixed" open={props.open}>
      <Toolbar>
        <Typography variant="h6" noWrap sx={{ flexGrow: 1 }} component="div">
          Node Grade
        </Typography>
        <FormControl>
          <Stack direction="column" padding={1} spacing={1}>
            <Typography variant="body1">Workflow:</Typography>
            <Select
              value={selectedWorkflow?.path || ''}
              sx={{ minWidth: 200 }}
              onChange={(e) => workflowChange(e.target.value)}
            >
              {workflows.map((workflow) => (
                <MenuItem key={workflow.id} value={workflow.path}>
                  {
                    workflow.path // actual name of the graph from db
                  }
                </MenuItem>
              ))}
            </Select>
          </Stack>
        </FormControl>
        <Tooltip title="Load template">
          <IconButton
            color="inherit"
            onClick={(e) => setTemplateMenuAnchor(e.currentTarget)}
            aria-label="load template"
          >
            <FolderOpenIcon />
          </IconButton>
        </Tooltip>
        <Menu
          anchorEl={templateMenuAnchor}
          open={Boolean(templateMenuAnchor)}
          onClose={() => setTemplateMenuAnchor(null)}
        >
          {TEMPLATES.map((t) => (
            <MenuItem key={t.file} onClick={() => loadTemplate(t.file)} sx={{ flexDirection: 'column', alignItems: 'flex-start' }}>
              <Typography variant="body2" fontWeight={600}>{t.label}</Typography>
              <Typography variant="caption" color="text.secondary">{t.desc}</Typography>
            </MenuItem>
          ))}
        </Menu>
        <Tooltip title={theme.palette.mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}>
          <IconButton color="inherit" onClick={colorMode.toggleColorMode} aria-label="toggle color mode">
            {theme.palette.mode === 'dark' ? <Brightness7Icon /> : <Brightness4Icon />}
          </IconButton>
        </Tooltip>
        <Tooltip title="Reconnect to websocket">
          <IconButton
            aria-label="change socket url"
            aria-controls="menu-appbar"
            aria-haspopup="true"
            color="inherit"
            onClick={props.handleClickChangeSocketUrl}
          >
            <ReplayIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Upload graph">
          <IconButton
            onClick={props.handleUploadGraph}
            aria-label="upload"
            aria-controls="menu-appbar"
            aria-haspopup="true"
            color="inherit"
          >
            <UploadFile />
          </IconButton>
        </Tooltip>
        <Tooltip title="Download graph">
          <IconButton
            onClick={props.handleDownloadGraph}
            aria-label="download"
            aria-controls="menu-appbar"
            aria-haspopup="true"
            color="inherit"
          >
            <DownloadForOffline />
          </IconButton>
        </Tooltip>
        <Tooltip title="Save graph">
          <IconButton
            onClick={props.handleSaveGraph}
            aria-label="save"
            aria-controls="menu-appbar"
            aria-haspopup="true"
            color="inherit"
          >
            <SaveIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Publish to students">
          <IconButton
            onClick={props.handlePublishGraph}
            aria-label="publish"
            aria-controls="menu-appbar"
            aria-haspopup="true"
            color="inherit"
          >
            <TelegramIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Task assessment preview">
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="end"
            onClick={props.handleDrawerOpen}
            sx={{ ...(props.open && { display: 'none' }) }}
          >
            <MenuIcon />
          </IconButton>
        </Tooltip>
      </Toolbar>
    </AppBarStyled>
  )
}

export default AppBar
