# Code Generator Frontend

A modern React + TypeScript frontend for the Code Generator agent, providing a ChatGPT-like interface for generating web application codebases.

## Features

- 🎨 Modern, intuitive ChatGPT-like UI
- 📡 Real-time streaming updates during code generation
- 📊 Visual progress indicators for each agent stage
- 📦 One-click download of generated codebase
- 🌙 Dark mode support
- 📱 Responsive design

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend server running (see server README)

### Installation

1. Install dependencies:

```bash
npm install
```

2. Create a `.env` file (optional, defaults to `http://localhost:8000`):

```bash
cp .env.example .env
```

3. Update `.env` if your backend runs on a different URL:

```
VITE_API_URL=http://localhost:8000
```

### Development

Start the development server:

```bash
npm run dev
```

The app will be available at `http://localhost:5173` (or the port shown in terminal).

### Build

Build for production:

```bash
npm run build
```

The built files will be in the `dist` folder.

### Preview Production Build

Preview the production build:

```bash
npm run preview
```

## Project Structure

```
src/
├── components/          # React components
│   ├── ChatInterface.tsx    # Main chat UI
│   ├── MessageBubble.tsx    # Individual message component
│   ├── StatusIndicator.tsx  # Progress indicator
│   └── DownloadButton.tsx   # Download button component
├── hooks/               # Custom React hooks
│   └── useCodeGeneration.ts # Code generation state management
├── services/            # API services
│   └── api.ts              # API client and SSE handling
├── types/               # TypeScript type definitions
│   └── index.ts
├── App.tsx              # Main app component
└── main.tsx             # Entry point
```

## Usage

1. Enter a prompt describing the web application you want to build
2. Watch real-time progress updates as the agent:
   - Plans your application
   - Designs the architecture
   - Generates code files
   - Packages everything into a zip file
3. Download the generated codebase when ready

## Technologies

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling
- **Server-Sent Events (SSE)** - Real-time streaming
