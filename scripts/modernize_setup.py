#!/usr/bin/env python3
"""
Web Modernization Setup Script - Fixed Version

This script automates the initial setup for modernizing the n8n AI Knowledge System
from Streamlit to Next.js with monitoring, Discord bot, and Chrome extension.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional

class ModernizationSetup:
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.frontend_dir = self.project_root / "frontend"
        self.discord_dir = self.project_root / "discord-bot"
        self.extension_dir = self.project_root / "chrome-extension"
        self.monitoring_dir = self.project_root / "monitoring"
        
    def run_command(self, command: List[str], cwd: Optional[Path] = None, check: bool = True, interactive: bool = False) -> subprocess.CompletedProcess:
        """Run a shell command with error handling"""
        try:
            print(f"Running: {' '.join(command)}")
            if interactive:
                # For interactive commands, don't capture output
                result = subprocess.run(
                    command,
                    cwd=cwd or self.project_root,
                    check=check
                )
                return result
            else:
                result = subprocess.run(
                    command,
                    cwd=cwd or self.project_root,
                    check=check,
                    capture_output=True,
                    text=True
                )
                if result.stdout:
                    print(f"Output: {result.stdout}")
                return result
        except subprocess.CalledProcessError as e:
            print(f"Error running command: {e}")
            if hasattr(e, 'stderr') and e.stderr:
                print(f"Error output: {e.stderr}")
            if check:
                raise
            return e
    
    def check_prerequisites(self) -> bool:
        """Check if required tools are installed"""
        print("🔍 Checking prerequisites...")
        
        required_tools = {
            'node': ['node', '--version'],
            'npm': ['npm', '--version'],
            'python': ['python3', '--version'],
            'docker': ['docker', '--version'],
            'docker-compose': ['docker-compose', '--version']
        }
        
        missing_tools = []
        
        for tool, command in required_tools.items():
            try:
                result = self.run_command(command, check=False)
                if result.returncode == 0:
                    print(f"✅ {tool}: {result.stdout.strip()}")
                else:
                    missing_tools.append(tool)
                    print(f"❌ {tool}: Not found")
            except Exception:
                missing_tools.append(tool)
                print(f"❌ {tool}: Not found")
        
        if missing_tools:
            print(f"\n❌ Missing required tools: {', '.join(missing_tools)}")
            print("Please install the missing tools and run this script again.")
            return False
        
        print("✅ All prerequisites satisfied!")
        return True
    
    def setup_frontend_manual(self) -> bool:
        """Setup Next.js frontend manually without interactive prompts"""
        print("\n🚀 Setting up Next.js frontend (manual approach)...")
        
        if self.frontend_dir.exists():
            print(f"Frontend directory already exists at {self.frontend_dir}")
            response = input("Do you want to recreate it? (y/N): ")
            if response.lower() != 'y':
                return True
            
            # Remove existing directory
            import shutil
            shutil.rmtree(self.frontend_dir)
        
        # Create directory structure
        self.frontend_dir.mkdir(exist_ok=True)
        (self.frontend_dir / 'src' / 'app').mkdir(parents=True, exist_ok=True)
        (self.frontend_dir / 'public').mkdir(exist_ok=True)
        
        # Create package.json
        package_json = {
            "name": "n8n-frontend",
            "version": "0.1.0",
            "private": True,
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "start": "next start",
                "lint": "next lint"
            },
            "dependencies": {
                "next": "14.0.4",
                "react": "^18",
                "react-dom": "^18",
                "@tanstack/react-query": "^5.0.0",
                "zustand": "^4.4.0",
                "socket.io-client": "^4.7.0",
                "recharts": "^2.8.0",
                "lucide-react": "^0.300.0"
            },
            "devDependencies": {
                "typescript": "^5",
                "@types/node": "^20",
                "@types/react": "^18",
                "@types/react-dom": "^18",
                "autoprefixer": "^10.0.1",
                "postcss": "^8",
                "tailwindcss": "^3.3.0",
                "eslint": "^8",
                "eslint-config-next": "14.0.4"
            }
        }
        
        with open(self.frontend_dir / 'package.json', 'w') as f:
            json.dump(package_json, f, indent=2)
        
        # Create configuration files
        self.create_frontend_config()
        
        # Install dependencies
        print("📦 Installing frontend dependencies...")
        try:
            self.run_command(['npm', 'install'], cwd=self.frontend_dir)
        except subprocess.CalledProcessError:
            print("Warning: Some dependencies failed to install. You can install them manually later.")
        
        print("✅ Frontend setup complete!")
        return True
    
    def create_frontend_config(self):
        """Create frontend configuration files"""
        
        # Next.js config
        next_config = '''/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true,
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ]
  },
}

module.exports = nextConfig
'''
        
        with open(self.frontend_dir / 'next.config.js', 'w') as f:
            f.write(next_config)
        
        # TypeScript config
        tsconfig = {
            "compilerOptions": {
                "target": "es5",
                "lib": ["dom", "dom.iterable", "es6"],
                "allowJs": True,
                "skipLibCheck": True,
                "strict": True,
                "noEmit": True,
                "esModuleInterop": True,
                "module": "esnext",
                "moduleResolution": "bundler",
                "resolveJsonModule": True,
                "isolatedModules": True,
                "jsx": "preserve",
                "incremental": True,
                "plugins": [
                    {
                        "name": "next"
                    }
                ],
                "baseUrl": ".",
                "paths": {
                    "@/*": ["./src/*"]
                }
            },
            "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
            "exclude": ["node_modules"]
        }
        
        with open(self.frontend_dir / 'tsconfig.json', 'w') as f:
            json.dump(tsconfig, f, indent=2)
        
        # Tailwind config
        tailwind_config = '''/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic':
          'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
      },
    },
  },
  plugins: [],
}
'''
        
        with open(self.frontend_dir / 'tailwind.config.js', 'w') as f:
            f.write(tailwind_config)
        
        # PostCSS config
        postcss_config = '''module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
'''
        
        with open(self.frontend_dir / 'postcss.config.js', 'w') as f:
            f.write(postcss_config)
        
        # Environment variables
        env_local = '''NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
'''
        
        with open(self.frontend_dir / '.env.local', 'w') as f:
            f.write(env_local)
        
        # Create basic app structure
        app_dir = self.frontend_dir / 'src' / 'app'
        
        # Global CSS
        globals_css = '''@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --foreground-rgb: 0, 0, 0;
  --background-start-rgb: 214, 219, 220;
  --background-end-rgb: 255, 255, 255;
}

@media (prefers-color-scheme: dark) {
  :root {
    --foreground-rgb: 255, 255, 255;
    --background-start-rgb: 0, 0, 0;
    --background-end-rgb: 0, 0, 0;
  }
}

body {
  color: rgb(var(--foreground-rgb));
  background: linear-gradient(
      to bottom,
      transparent,
      rgb(var(--background-end-rgb))
    )
    rgb(var(--background-start-rgb));
}
'''
        
        with open(app_dir / 'globals.css', 'w') as f:
            f.write(globals_css)
        
        # Basic layout
        layout_tsx = '''import './globals.css'
import { Inter } from 'next/font/google'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'n8n AI Knowledge System',
  description: 'Modern AI-powered n8n documentation and workflow assistant',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  )
}
'''
        
        with open(app_dir / 'layout.tsx', 'w') as f:
            f.write(layout_tsx)
        
        # Basic page
        page_tsx = '''export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm lg:flex">
        <h1 className="text-4xl font-bold mb-4">n8n AI Knowledge System</h1>
      </div>
      <div className="mb-32 grid text-center lg:max-w-5xl lg:w-full lg:mb-0 lg:grid-cols-4 lg:text-left">
        <div className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100">
          <h2 className="mb-3 text-2xl font-semibold">Documentation</h2>
          <p className="m-0 max-w-[30ch] text-sm opacity-50">
            Browse and search n8n documentation with AI assistance.
          </p>
        </div>
        <div className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100">
          <h2 className="mb-3 text-2xl font-semibold">Workflows</h2>
          <p className="m-0 max-w-[30ch] text-sm opacity-50">
            Create and manage n8n workflows with intelligent suggestions.
          </p>
        </div>
        <div className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100">
          <h2 className="mb-3 text-2xl font-semibold">Analytics</h2>
          <p className="m-0 max-w-[30ch] text-sm opacity-50">
            Monitor system performance and usage analytics.
          </p>
        </div>
        <div className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100">
          <h2 className="mb-3 text-2xl font-semibold">Chat</h2>
          <p className="m-0 max-w-[30ch] text-sm opacity-50">
            Interactive AI chat for n8n support and guidance.
          </p>
        </div>
      </div>
    </main>
  )
}
'''
        
        with open(app_dir / 'page.tsx', 'w') as f:
            f.write(page_tsx)
    
    def setup_discord_bot(self) -> bool:
        """Setup Discord bot"""
        print("\n🤖 Setting up Discord bot...")
        
        self.discord_dir.mkdir(exist_ok=True)
        
        # Create package.json
        package_json = {
            "name": "n8n-discord-bot",
            "version": "1.0.0",
            "description": "Discord bot for n8n AI Knowledge System",
            "main": "src/index.js",
            "scripts": {
                "start": "node src/index.js",
                "dev": "nodemon src/index.js",
                "deploy": "node src/deploy-commands.js"
            },
            "dependencies": {
                "discord.js": "^14.14.1",
                "axios": "^1.6.2",
                "dotenv": "^16.3.1"
            },
            "devDependencies": {
                "nodemon": "^3.0.2"
            }
        }
        
        with open(self.discord_dir / 'package.json', 'w') as f:
            json.dump(package_json, f, indent=2)
        
        # Create directory structure
        (self.discord_dir / 'src').mkdir(exist_ok=True)
        (self.discord_dir / 'src' / 'commands').mkdir(exist_ok=True)
        
        # Create .env template
        env_template = '''# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_CLIENT_ID=your_discord_client_id_here
DISCORD_GUILD_ID=your_discord_guild_id_here

# API Configuration
API_BASE_URL=http://localhost:8000
API_KEY=your_api_key_here
'''
        
        with open(self.discord_dir / '.env.example', 'w') as f:
            f.write(env_template)
        
        print("✅ Discord bot setup complete!")
        return True
    
    def setup_chrome_extension(self) -> bool:
        """Setup Chrome extension"""
        print("\n🌐 Setting up Chrome extension...")
        
        self.extension_dir.mkdir(exist_ok=True)
        
        # Create directory structure
        dirs = ['popup', 'content', 'background', 'icons']
        for dir_name in dirs:
            (self.extension_dir / dir_name).mkdir(exist_ok=True)
        
        # Create manifest.json
        manifest = {
            "manifest_version": 3,
            "name": "n8n AI Assistant",
            "version": "1.0.0",
            "description": "AI-powered n8n documentation and workflow assistant",
            "permissions": [
                "activeTab",
                "storage",
                "scripting"
            ],
            "host_permissions": [
                "https://docs.n8n.io/*",
                "https://n8n.io/*",
                "http://localhost:8000/*"
            ],
            "action": {
                "default_popup": "popup/index.html",
                "default_title": "n8n AI Assistant"
            },
            "content_scripts": [{
                "matches": ["https://docs.n8n.io/*", "https://n8n.io/*"],
                "js": ["content/content.js"],
                "css": ["content/content.css"]
            }],
            "background": {
                "service_worker": "background/background.js"
            },
            "icons": {
                "16": "icons/icon16.png",
                "48": "icons/icon48.png",
                "128": "icons/icon128.png"
            }
        }
        
        with open(self.extension_dir / 'manifest.json', 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print("✅ Chrome extension setup complete!")
        return True
    
    def setup_monitoring(self) -> bool:
        """Setup monitoring stack"""
        print("\n📊 Setting up monitoring stack...")
        
        self.monitoring_dir.mkdir(exist_ok=True)
        (self.monitoring_dir / 'prometheus').mkdir(exist_ok=True)
        
        # Create Prometheus config
        prometheus_config = '''global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'n8n-api'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
'''
        
        with open(self.monitoring_dir / 'prometheus' / 'prometheus.yml', 'w') as f:
            f.write(prometheus_config)
        
        print("✅ Monitoring setup complete!")
        return True
    
    def update_backend_requirements(self) -> bool:
        """Update backend requirements for new features"""
        print("\n🔧 Updating backend requirements...")
        
        new_requirements = [
            "prometheus-client==0.19.0",
            "websockets==12.0",
            "redis==5.0.1"
        ]
        
        requirements_file = self.project_root / 'requirements.txt'
        
        if requirements_file.exists():
            with open(requirements_file, 'r') as f:
                existing_requirements = f.read()
            
            # Add new requirements if not already present
            for req in new_requirements:
                package_name = req.split('==')[0]
                if package_name not in existing_requirements:
                    existing_requirements += f"\n{req}"
            
            with open(requirements_file, 'w') as f:
                f.write(existing_requirements)
        
        print("✅ Backend requirements updated!")
        return True
    
    def run_setup(self) -> bool:
        """Run the complete setup process"""
        print("🚀 Starting n8n Web Modernization Setup (Fixed Version)...\n")
        
        steps = [
            ("Prerequisites", self.check_prerequisites),
            ("Backend Requirements", self.update_backend_requirements),
            ("Frontend (Manual)", self.setup_frontend_manual),
            ("Discord Bot", self.setup_discord_bot),
            ("Chrome Extension", self.setup_chrome_extension),
            ("Monitoring", self.setup_monitoring)
        ]
        
        for step_name, step_func in steps:
            try:
                print(f"\n{'='*50}")
                print(f"Setting up: {step_name}")
                print(f"{'='*50}")
                
                if not step_func():
                    print(f"❌ Failed to setup {step_name}")
                    return False
                    
            except KeyboardInterrupt:
                print(f"\n❌ Setup interrupted during {step_name}")
                return False
            except Exception as e:
                print(f"❌ Error during {step_name}: {e}")
                response = input(f"Continue with remaining steps? (y/N): ")
                if response.lower() != 'y':
                    return False
        
        self.print_next_steps()
        return True
    
    def print_next_steps(self):
        """Print next steps for the user"""
        print("\n" + "="*60)
        print("🎉 SETUP COMPLETE!")
        print("="*60)
        
        print("\n📁 Created directories:")
        print(f"  • Frontend: {self.frontend_dir}")
        print(f"  • Discord Bot: {self.discord_dir}")
        print(f"  • Chrome Extension: {self.extension_dir}")
        print(f"  • Monitoring: {self.monitoring_dir}")
        
        print("\n🚀 Next steps:")
        print("\n1. Start development servers:")
        print("   cd frontend && npm run dev")
        print("   python3 -m uvicorn src.n8n_scraper.api.main:app --reload")
        
        print("\n2. Configure Discord bot (optional):")
        print("   cd discord-bot")
        print("   cp .env.example .env")
        print("   # Edit .env with your Discord bot tokens")
        print("   npm install && npm run dev")
        
        print("\n3. Load Chrome extension (optional):")
        print("   • Open Chrome -> Extensions -> Developer mode")
        print(f"   • Load unpacked: {self.extension_dir}")
        
        print("\n4. Start monitoring (optional):")
        print("   cd monitoring")
        print("   docker-compose up -d")
        
        print("\n📚 Documentation:")
        print("   • MODERNIZATION_README.md - Quick start guide")
        print("   • docs/WEB_MODERNIZATION_PLAN.md - Detailed plan")
        print("   • docs/IMPLEMENTATION_GUIDE.md - Implementation details")

def main():
    """Main entry point"""
    try:
        setup = ModernizationSetup()
        success = setup.run_setup()
        
        if success:
            print("\n✅ Modernization setup completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Modernization setup failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n❌ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()