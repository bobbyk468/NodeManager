import { createTheme, PaletteMode, ThemeOptions } from '@mui/material'

// Brand palette — indigo/teal, distinct from MUI's default blue.
const BRAND = {
  primary: '#4F46E5',
  primaryLight: '#818CF8',
  primaryDark: '#3730A3',
  secondary: '#0D9488',
  secondaryLight: '#5EEAD4'
}

// MUI's palette colors only ship {light, main, dark, contrastText} by default.
// The app's inline sx styles reference tinted shades like `primary.50` /
// `success.200` (a common Tailwind-esque convention) for subtle tinted
// panels — those keys don't exist out of the box, so every box using them
// silently rendered with no background and a default (black) border. These
// shade maps fill in the missing keys so that convention actually resolves.
// (MUI's palette types don't declare these extra keys, hence the `any`.)
const LIGHT_SHADES: Record<string, Record<string, string>> = {
  primary: { 50: '#EEF2FF', 100: '#E0E7FF', 200: '#C7D2FE' },
  secondary: { 50: '#F0FDFA', 100: '#CCFBF1', 200: '#99F6E4' },
  success: { 50: '#F0FDF4', 100: '#DCFCE7', 200: '#BBF7D0' },
  warning: { 50: '#FFFBEB', 100: '#FEF3C7', 200: '#FDE68A' },
  error: { 50: '#FEF2F2', 100: '#FEE2E2', 200: '#FECACA' }
}

const DARK_SHADES: Record<string, Record<string, string>> = {
  primary: { 50: '#1E1B4B', 100: '#312E81', 200: '#3730A3' },
  secondary: { 50: '#042F2E', 100: '#134E4A', 200: '#115E59' },
  success: { 50: '#052E16', 100: '#14532D', 200: '#166534' },
  warning: { 50: '#451A03', 100: '#78350F', 200: '#92400E' },
  error: { 50: '#450A0A', 100: '#7F1D1D', 200: '#991B1B' }
}

export const getAppTheme = (mode: PaletteMode) => {
  const isLight = mode === 'light'
  const shades = isLight ? LIGHT_SHADES : DARK_SHADES

  const palette: Record<string, unknown> = {
    mode,
    primary: {
      main: isLight ? BRAND.primary : BRAND.primaryLight,
      dark: BRAND.primaryDark,
      light: BRAND.primaryLight,
      ...shades.primary
    },
    secondary: {
      main: isLight ? BRAND.secondary : BRAND.secondaryLight,
      ...shades.secondary
    },
    success: { main: '#2E7D32', ...shades.success },
    warning: { main: '#ED6C02', ...shades.warning },
    error: { main: '#D32F2F', ...shades.error },
    background: {
      default: isLight ? '#F5F6FB' : '#0F1115',
      paper: isLight ? '#FFFFFF' : '#171A21'
    }
  }

  const options: ThemeOptions = {
    palette: palette as ThemeOptions['palette'],
    shape: {
      borderRadius: 10
    },
    typography: {
      fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
      h4: { fontWeight: 700, letterSpacing: '-0.01em' },
      h5: { fontWeight: 700 },
      h6: { fontWeight: 600 },
      subtitle1: { fontWeight: 600 },
      subtitle2: { fontWeight: 700 },
      button: { fontWeight: 600, textTransform: 'none' }
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            backgroundColor: isLight ? '#F5F6FB' : '#0F1115'
          }
        }
      },
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            paddingLeft: 20,
            paddingRight: 20
          },
          contained: {
            boxShadow: 'none',
            '&:hover': { boxShadow: '0 4px 12px rgba(79, 70, 229, 0.25)' }
          }
        }
      },
      MuiPaper: {
        styleOverrides: {
          root: { backgroundImage: 'none' }
        }
      },
      MuiChip: {
        styleOverrides: {
          root: { fontWeight: 600, borderRadius: 8 }
        }
      },
      MuiAppBar: {
        styleOverrides: {
          root: { boxShadow: '0 1px 3px rgba(0,0,0,0.12)' }
        }
      },
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: 16,
            boxShadow: isLight
              ? '0 1px 2px rgba(16,24,40,0.06), 0 1px 3px rgba(16,24,40,0.10)'
              : '0 1px 2px rgba(0,0,0,0.3), 0 1px 3px rgba(0,0,0,0.4)'
          }
        }
      }
    }
  }

  return createTheme(options)
}

export default getAppTheme
