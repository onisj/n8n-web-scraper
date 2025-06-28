import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { useRouter } from 'next/navigation'
import LoginPage from '../../frontend/src/app/login/page'

// Mock components
jest.mock('../../frontend/src/components/auth/LoginForm', () => {
  return function MockLoginForm({ onSuccess, onSwitchToRegister, isDarkMode }: any) {
    return (
      <div data-testid="login-form">
        <button onClick={onSuccess} data-testid="login-success">
          Login Success
        </button>
        <button onClick={onSwitchToRegister} data-testid="switch-to-register">
          Switch to Register
        </button>
        <div data-testid="dark-mode">{isDarkMode ? 'dark' : 'light'}</div>
      </div>
    )
  }
})

jest.mock('../../frontend/src/components/auth/RegisterForm', () => {
  return function MockRegisterForm({ onSuccess, onSwitchToLogin, isDarkMode }: any) {
    return (
      <div data-testid="register-form">
        <button onClick={onSuccess} data-testid="register-success">
          Register Success
        </button>
        <button onClick={onSwitchToLogin} data-testid="switch-to-login">
          Switch to Login
        </button>
        <div data-testid="dark-mode">{isDarkMode ? 'dark' : 'light'}</div>
      </div>
    )
  }
})



describe('LoginPage Component', () => {
  const mockPush = jest.fn()
  const mockUseRouter = useRouter as jest.MockedFunction<typeof useRouter>

  beforeEach(() => {
    jest.clearAllMocks()
    
    mockUseRouter.mockReturnValue({
      push: mockPush,
      replace: jest.fn(),
      prefetch: jest.fn(),
      back: jest.fn(),
      forward: jest.fn(),
      refresh: jest.fn(),
    })
    
    
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  describe('Rendering Tests', () => {

    it('renders the login page with correct title', () => {
      render(<LoginPage />)
      
      expect(screen.getByText('n8n AI Knowledge')).toBeInTheDocument()
      expect(screen.getByText('Welcome back!')).toBeInTheDocument()
    })

    it('renders login form by default', () => {
      render(<LoginPage />)
      
      expect(screen.getByTestId('login-form')).toBeInTheDocument()
      expect(screen.queryByTestId('register-form')).not.toBeInTheDocument()
    })

    it('renders theme toggle button', () => {
      render(<LoginPage />)
      
      const themeToggle = screen.getByLabelText(/switch to.*theme/i)
      expect(themeToggle).toBeInTheDocument()
      expect(themeToggle).toHaveTextContent('🌙')
    })

    it('renders footer text', () => {
      render(<LoginPage />)
      
      expect(screen.getByText('Experience the power of long-term memory with AI')).toBeInTheDocument()
    })

    it('applies correct CSS classes for light mode', () => {
      render(<LoginPage />)
      
      const darkModeStatus = screen.getByTestId('dark-mode')
      expect(darkModeStatus).toHaveTextContent('light')
    })

    it('switches to register form when switch button is clicked', () => {
      render(<LoginPage />)
      
      const switchButton = screen.getByTestId('switch-to-register')
      fireEvent.click(switchButton)
      
      expect(screen.getByTestId('register-form')).toBeInTheDocument()
      expect(screen.queryByTestId('login-form')).not.toBeInTheDocument()
    })

    it('switches back to login form from register form', () => {
      render(<LoginPage />)
      
      // Switch to register
      fireEvent.click(screen.getByTestId('switch-to-register'))
      expect(screen.getByTestId('register-form')).toBeInTheDocument()
      
      // Switch back to login
      fireEvent.click(screen.getByTestId('switch-to-login'))
      expect(screen.getByTestId('login-form')).toBeInTheDocument()
      expect(screen.queryByTestId('register-form')).not.toBeInTheDocument()
    })

    it('toggles dark mode when theme button is clicked', () => {
      render(<LoginPage />)
      
      const themeToggle = screen.getByLabelText(/switch to.*theme/i)
      
      // Initially light mode
      expect(themeToggle).toHaveTextContent('🌙')
      
      // Click to switch to dark mode
      fireEvent.click(themeToggle)
      expect(themeToggle).toHaveTextContent('☀️')
    })

    it('redirects to home page on successful login', async () => {
      render(<LoginPage />)
      
      fireEvent.click(screen.getByTestId('login-success'))
      
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/')
      })
    })

    it('redirects to home page on successful registration', async () => {
      render(<LoginPage />)
      
      // Switch to register form
      fireEvent.click(screen.getByTestId('switch-to-register'))
      
      // Trigger successful registration
      fireEvent.click(screen.getByTestId('register-success'))
      
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/')
      })
    })

    it('applies correct CSS classes for light mode', () => {
      render(<LoginPage />)
      
      const container = screen.getByText('n8n AI Knowledge').closest('div')
      expect(container).toHaveClass('bg-white')
    })

    it('applies correct CSS classes for dark mode', () => {
      render(<LoginPage />)
      
      const themeToggle = screen.getByLabelText('Switch to dark theme')
      fireEvent.click(themeToggle)
      
      const container = screen.getByText('n8n AI Knowledge').closest('div')
      expect(container).toHaveClass('bg-black')
    })
  })

  describe('when user is authenticated', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: { id: '1', email: 'test@example.com', name: 'Test User' },
        login: jest.fn(),
        logout: jest.fn(),
        register: jest.fn(),
        loading: false,
      })
    })

    it('redirects to home page immediately', () => {
      render(<LoginPage />)
      
      expect(mockPush).toHaveBeenCalledWith('/')
    })

    it('returns null when user is authenticated', () => {
      const { container } = render(<LoginPage />)
      
      expect(container.firstChild).toBeNull()
    })
  })

  describe('accessibility', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: null,
        login: jest.fn(),
        logout: jest.fn(),
        register: jest.fn(),
        loading: false,
      })
    })

    it('has proper aria-label for theme toggle button', () => {
      render(<LoginPage />)
      
      const themeToggle = screen.getByRole('button', { name: /switch to.*theme/i })
      expect(themeToggle).toBeInTheDocument()
    })

    it('updates aria-label when theme changes', () => {
      render(<LoginPage />)
      
      const themeToggle = screen.getByLabelText('Switch to dark theme')
      fireEvent.click(themeToggle)
      
      expect(screen.getByLabelText('Switch to light theme')).toBeInTheDocument()
    })
  })

  describe('responsive design', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: null,
        login: jest.fn(),
        logout: jest.fn(),
        register: jest.fn(),
        loading: false,
      })
    })

    it('applies responsive padding classes', () => {
      render(<LoginPage />)
      
      const mainContainer = screen.getByText('n8n AI Knowledge').closest('.px-4')
      expect(mainContainer).toHaveClass('px-4', 'sm:px-6', 'lg:px-8')
    })

    it('applies responsive width classes', () => {
      render(<LoginPage />)
      
      const formContainer = screen.getByText('n8n AI Knowledge').closest('.max-w-md')
      expect(formContainer).toHaveClass('max-w-md', 'w-full')
    })
  })
})