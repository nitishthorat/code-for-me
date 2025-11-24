# Code For Me

An AI-powered code generator that creates modern, error-free vanilla HTML/CSS/JS websites from natural language descriptions. Built with an agent-based architecture using LangChain and LangGraph.

## 🚀 Features

- **AI-Powered Code Generation**: Describe your website idea in plain English and get a complete, working codebase
- **Vanilla HTML/CSS/JS Only**: Generates clean, framework-free code that works directly in the browser
- **Modern Design**: Automatically creates beautiful, responsive websites with modern UI/UX principles
- **Error-Free Code**: Multi-layered validation and fixing system ensures generated code is syntactically correct
- **Real-Time Preview**: Live preview of generated websites with automatic CSS/JS linking
- **Complete Styling**: Ensures all HTML classes and IDs are properly styled with modern CSS
- **Streaming Updates**: Real-time progress updates during code generation via Server-Sent Events
- **One-Click Download**: Download generated codebase as a ZIP file

## 🏗️ Architecture

The project uses an agent-based architecture with multiple specialized AI agents working together:

```
User Prompt
    ↓
┌─────────────────┐
│  Planner Agent  │ → Creates project plan with design system
└─────────────────┘
    ↓
┌─────────────────┐
│ Architect Agent │ → Breaks down plan into file-by-file tasks
└─────────────────┘
    ↓
┌─────────────────┐
│   Coder Agent   │ → Generates code for each file
└─────────────────┘
    ↓
┌──────────────────────┐
│ Validator/Fixer Agent│ → Validates & fixes errors iteratively
└──────────────────────┘
    ↓
┌─────────────────┐
│ Downloader Agent │ → Packages codebase into ZIP
└─────────────────┘
    ↓
┌─────────────────────┐
│ Preview Server Agent│ → Starts preview server
└─────────────────────┘
```

### Agent Responsibilities

- **Planner**: Converts user prompt into structured project plan with design system (colors, typography, spacing, components)
- **Architect**: Creates implementation tasks for each file with proper import paths and cross-references
- **Coder**: Generates complete code for HTML, CSS, and JavaScript files
- **Validator/Fixer**: Validates syntax, checks CSS coverage, fixes import paths, and iteratively resolves errors
- **Downloader**: Packages all files into a downloadable ZIP archive
- **Preview Server**: Extracts and serves the generated website with live preview

## 🛠️ Tech Stack

### Backend

- **Python 3.13+**
- **FastAPI** - Web framework and API server
- **LangChain** - LLM orchestration framework
- **LangGraph** - Agent workflow management
- **OpenAI/Groq** - LLM providers
- **Pydantic** - Data validation
- **html5lib** & **cssutils** - HTML/CSS validation

### Frontend

- **React 19** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling (for frontend UI only)
- **Server-Sent Events (SSE)** - Real-time streaming

## 📋 Prerequisites

- Python 3.13 or higher
- Node.js 18+ and npm
- OpenAI API key or Groq API key

## 🔧 Installation

### 1. Clone the repository

```bash
git clone https://github.com/nitishthorat/code-for-me.git
cd code-for-me
```

### 2. Backend Setup

```bash
cd server

# Install dependencies (using uv or pip)
uv sync
# OR
pip install -e .

# Create .env file
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
OPENAI_API_KEY=your_openai_api_key_here
# OR
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env file (optional, defaults to http://localhost:8000)
echo "VITE_API_URL=http://localhost:8000" > .env
```

## 🚀 Running the Application

### Start the Backend Server

```bash
cd server
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

### Start the Frontend

```bash
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:5173`

## 💻 Usage

1. **Open the frontend** in your browser (`http://localhost:5173`)
2. **Enter a prompt** describing the website you want to build, for example:
   - "Create a portfolio landing page for a web developer"
   - "Build a restaurant website with menu, reservations, and contact form"
   - "Make a blog homepage with featured posts and categories"
3. **Watch the progress** as agents work through planning, architecture, coding, and validation
4. **Preview the result** in the embedded preview frame
5. **Download the codebase** as a ZIP file

## 📁 Project Structure

```
code-for-me/
├── server/                 # Backend Python application
│   ├── agent/             # AI agent implementations
│   │   ├── graph.py       # Agent graph and workflow
│   │   ├── prompts.py     # LLM prompts for each agent
│   │   ├── states.py      # Pydantic models for data structures
│   │   ├── validators/    # Code validation modules
│   │   └── testers/       # Code execution testers
│   ├── main.py            # FastAPI application and endpoints
│   ├── preview_server.py  # Preview server management
│   └── preview_manager.py # Preview lifecycle management
│
├── frontend/              # React frontend application
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── hooks/        # Custom React hooks
│   │   ├── services/     # API client
│   │   └── types/        # TypeScript types
│   └── package.json
│
└── README.md
```

## 🎨 Generated Code Structure

The generator creates vanilla HTML/CSS/JS projects with this structure:

```
generated-project/
├── index.html          # Main HTML file
├── styles/
│   └── main.css        # All CSS (variables, reset, components)
├── scripts/
│   └── main.js         # All JavaScript functionality
└── assets/             # Images and other assets (if any)
```

## 🔍 Key Features Explained

### CSS Coverage Validation

The system automatically checks that all HTML classes and IDs have corresponding CSS styles, ensuring complete visual styling.

### Import Path Management

Two-layer system ensures correct file paths:

- **Prevention**: Architect agent calculates correct relative paths upfront
- **Verification**: Validator/Fixer agent verifies and corrects any remaining path issues

### Error Prevention & Resolution

- Real linter/parser integration (html5lib, cssutils)
- Iterative debugging with multiple validation passes
- Code execution testing for runtime errors
- Automatic error fixing by the Validator/Fixer agent

### Modern Design System

Every generated project includes:

- Complete color palette with CSS variables
- Typography scale (headings, body, small text)
- Spacing system (xs, sm, md, lg, xl, xxl)
- Responsive breakpoints (mobile, tablet, desktop)
- Component styles (buttons, cards, forms, navigation, etc.)

## 🧪 Development

### Running Tests

```bash
# Backend tests (when implemented)
cd server
pytest

# Frontend tests (when implemented)
cd frontend
npm test
```

### Code Quality

```bash
# Python linting
cd server
ruff check .

# TypeScript linting
cd frontend
npm run lint
```

## 📝 API Endpoints

### POST `/get_app/stream`

Streaming endpoint for code generation with real-time updates via SSE.

**Request:**

```json
{
  "prompt": "Create a portfolio website"
}
```

**Response:** Server-Sent Events stream with status updates

### GET `/preview/{token}`

Serves preview of generated website.

### GET `/preview/{token}/{file_path}`

Serves individual files (CSS, JS, images) from preview.

## 🔐 Environment Variables

### Backend (.env)

- `OPENAI_API_KEY` - OpenAI API key
- `GROQ_API_KEY` - Groq API key (alternative)
- `GROQ_MODEL` - Groq model name (default: `llama-3.3-70b-versatile`)
- `PREVIEW_BASE_URL` - Base URL for preview links (default: `http://localhost:8000`)

### Frontend (.env)

- `VITE_API_URL` - Backend API URL (default: `http://localhost:8000`)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- Built with [LangChain](https://www.langchain.com/) and [LangGraph](https://github.com/langchain-ai/langgraph)
- Uses [FastAPI](https://fastapi.tiangolo.com/) for the backend
- Frontend built with [React](https://react.dev/) and [Vite](https://vitejs.dev/)
