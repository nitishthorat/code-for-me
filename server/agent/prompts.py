def planner_prompt(user_prompt: str) -> str:
    PLANNER_PROMPT = f"""
You are the PLANNER agent. Convert the user prompt into a complete project plan for a VANILLA HTML/CSS/JS website.

GOAL:
- Design a **static** website that works directly in the browser using only:
  - index.html
  - styles/main.css
  - scripts/main.js
  - (plus any additional .html/.css/.js files you explicitly list in the plan)

CRITICAL CONSTRAINTS:
- Tech stack MUST be **vanilla only**:
  - NO frameworks (no React, Vue, Angular, Svelte, etc.)
  - NO build tools (no Vite, Webpack, CRA, etc.)
  - NO libraries or CDNs (no Bootstrap, Tailwind, jQuery, etc.)
- The site must be:
  - Modern, beautiful, responsive
  - Accessible (semantic HTML, proper contrast)
  - Lightweight and fast

DESIGN SYSTEM REQUIREMENTS:
You MUST include a `design_system` object with:

1. colors:
   - primary: Main brand color
   - secondary: Secondary brand color
   - accent: Accent/highlight color
   - background: May be a single value or nested object, e.g. {{ "base": "#0f172a", "surface": "#020617" }}
   - text: May be a single value or nested object, e.g. {{ "primary": "#e5e7eb", "muted": "#9ca3af" }}
   - Optional but recommended: success, error, warning

2. typography:
   - font_family: Main font family (e.g. "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif")
   - heading_font: Font for headings (can be same as font_family)
   - body_font: Font for body text
   - base_size: Base font size (e.g. "16px")

3. spacing:
   - xs, sm, md, lg, xl, xxl: Spacing values in rem or px (e.g. "0.25rem", "0.5rem", "1rem", ...)

4. breakpoints:
   - mobile: Mobile breakpoint (e.g. "0px" or "320px")
   - tablet: Tablet breakpoint (e.g. "768px")
   - desktop: Desktop breakpoint (e.g. "1024px")

5. components:
   - List of UI components needed, e.g. ["button", "card", "form", "navigation", "hero", "section-header", "footer", "badge"]

PROJECT STRUCTURE (MANDATORY FILES):
The `files` array in the plan MUST include at least:
- "index.html"
- "styles/main.css"
- "scripts/main.js"

MODERN DESIGN PRINCIPLES:
- Mobile-first responsive layout
- Use a clear visual hierarchy
- Smooth but subtle transitions / hover states
- Semantic HTML5 structure (header, nav, main, section, footer, etc.)
- Accessible color contrast and focus states

USER REQUEST:
{user_prompt}

CRITICAL OUTPUT FORMAT:
You MUST return ONLY a **valid JSON object** starting with {{ and ending with }}.
- NO markdown code blocks (no ```json or ```)
- NO explanations before or after the JSON
- NO comments inside the JSON
- NO text outside the JSON object
- Start your response directly with {{ and end with }}

The JSON MUST have this exact structure:

{{
  "name": "Project Name Here",
  "description": "One-line description of the project",
  "tech_stack": "Vanilla HTML/CSS/JS",
  "features": ["Feature 1", "Feature 2", "Feature 3"],
  "files": ["index.html", "styles/main.css", "scripts/main.js"],
  "design_system": {{
    "colors": {{
      "primary": "#color",
      "secondary": "#color",
      "accent": "#color",
      "background": {{"base": "#color", "surface": "#color"}},
      "text": {{"primary": "#color", "muted": "#color"}},
      "success": "#color",
      "error": "#color",
      "warning": "#color"
    }},
    "typography": {{
      "font_family": "font stack",
      "heading_font": "font stack",
      "body_font": "font stack",
      "base_size": "16px"
    }},
    "spacing": {{
      "xs": "0.25rem",
      "sm": "0.5rem",
      "md": "1rem",
      "lg": "1.5rem",
      "xl": "2rem",
      "xxl": "3rem"
    }},
    "breakpoints": {{
      "mobile": "0px",
      "tablet": "768px",
      "desktop": "1024px"
    }},
    "components": ["navigation", "hero", "button", "card", "form", "footer"]
  }}
}}

CRITICAL RULES:
1. Return ONLY the JSON object - nothing else
2. Start with {{ and end with }}
3. Do NOT wrap in markdown code blocks
4. Do NOT add any text before or after the JSON
5. tech_stack must be exactly "Vanilla HTML/CSS/JS"
6. files must include at minimum: ["index.html", "styles/main.css", "scripts/main.js"]
7. Ensure all JSON syntax is valid (proper quotes, commas, brackets)
"""
    return PLANNER_PROMPT


def architect_prompt(plan: str, design_system: dict = None, tech_stack: str = None) -> str:
    design_system_section = ""
    if design_system:
        design_system_section = f"""
DESIGN SYSTEM (use these values in your implementation):
- Colors: {design_system.get('colors', {})}
- Typography: {design_system.get('typography', {})}
- Spacing: {design_system.get('spacing', {})}
- Breakpoints: {design_system.get('breakpoints', {})}
- Components: {design_system.get('components', [])}
"""

    tech_stack_section = ""
    if tech_stack:
        tech_stack_section = f"""
TECH STACK FROM PLAN (must be honored): {tech_stack}
"""

    ARCHITECT_PROMPT = f"""
You are the ARCHITECT agent. Convert a high-level project plan into file-by-file implementation tasks for a **VANILLA HTML/CSS/JS** website.

GLOBAL CONSTRAINTS:
- This project is **vanilla only**:
  - NO React, Vue, Angular, Svelte, or other frameworks
  - NO TypeScript, JSX, TSX, Vue SFCs, etc.
  - NO build tools (no Vite, Webpack, etc.)
  - NO NPM packages or external libraries
- All code must be plain:
  - .html
  - .css
  - .js

{tech_stack_section}
{design_system_section}

FORBIDDEN FILES / PATTERNS:
- Any .tsx, .jsx, .vue, .ts, .mjs, .cjs files
- package.json, vite.config.js, webpack.config.js, rollup.config.js
- src/ directory (use root + styles/ + scripts/ + assets/ only)
- Any imports of "react", "vue", "angular", or other libraries

ALLOWED FILE TYPES:
- .html files (HTML5)
- .css files (CSS3)
- .js files (vanilla ES6+)

MANDATORY FILES (MUST BE PRESENT IN implementation_steps):
- "index.html" (root)
- "styles/main.css"
- "scripts/main.js"

FILE STRUCTURE RULES:
- index.html must be at project root
- CSS files must be in styles/
- JS files must be in scripts/
- Assets (if any) must be in assets/

YOUR TASK:
1. Read the **Project Plan** (JSON) given below.
2. Look at the `files` list in the plan.
3. For **every** file listed there, create **one** implementation task.
4. **CRITICAL**: You MUST ALWAYS include these three files as the first three tasks:
   - "index.html" (first in the array) - MUST include semantic HTML with classes and IDs
   - "styles/main.css" (second) - MUST style ALL classes and IDs used in index.html
   - "scripts/main.js" (third) - MUST manipulate ALL interactive elements (IDs, classes, buttons, forms) from index.html
   Even if the plan forgot them, you MUST add them.

5. **CROSS-REFERENCE REQUIREMENT**: 
   - When creating the CSS task, analyze what HTML elements, classes, and IDs will be in index.html (based on components and features in the plan), and explicitly mention styling those specific selectors.
   - When creating the JS task, analyze what interactive elements (buttons, forms, navigation, toggles) will be in index.html, and explicitly mention manipulating those specific elements by their IDs/classes.

REQUIRED OUTPUT FORMAT:
You MUST return ONLY a valid JSON object with this exact structure:

{{
  "implementation_steps": [
    {{
      "filepath": "index.html",
      "file_description": "Main HTML entry point with semantic structure, links to CSS and JS files",
      "required_imports": ["styles/main.css", "scripts/main.js"],
      "task_description": "Create index.html with HTML5 doctype, semantic layout (header, nav, main, section, footer), meta tags (charset, viewport), correct <title>, and link to styles/main.css and scripts/main.js using the exact paths in required_imports. Include container elements for all major sections mentioned in the plan (hero, features, etc.) and ensure accessibility (landmarks, alt text placeholders, proper heading hierarchy)."
    }},
    {{
      "filepath": "styles/main.css",
      "file_description": "Main stylesheet with CSS variables, base styles, layout, component styles, and responsive design",
      "required_imports": [],
      "task_description": "Define :root CSS variables for the full design system (colors, typography, spacing, breakpoints). Add a basic CSS reset, base typography styles, layout utilities (flex/grid helpers). Style ALL HTML elements, classes, and IDs that will be used in index.html - including semantic elements (header, nav, main, section, footer), component classes (e.g., .hero, .card, .button, .nav-menu, .form-input), and IDs (e.g., #navigation, #hero-section, #contact-form). Reference the components list from the plan to ensure every component has corresponding CSS. Implement a mobile-first approach with media queries using the provided breakpoints and ensure focus/hover/active states are clearly visible for all interactive elements."
    }},
    {{
      "filepath": "scripts/main.js",
      "file_description": "Main JavaScript file for all interactivity and DOM manipulation using vanilla ES6+",
      "required_imports": [],
      "task_description": "Attach a DOMContentLoaded listener, then implement all interactive behavior described in the plan. Use querySelector/querySelectorAll to select elements by their IDs and classes from index.html (e.g., #navigation, .nav-toggle, .menu-button, #contact-form, .card, .button). Implement functionality for: mobile navigation toggle (if nav exists), form validation/handling (if forms exist), smooth scrolling (if navigation links exist), interactive toggles/accordions (if applicable), and any other interactivity mentioned in the plan. Use addEventListener for events and small, focused functions. Add null checks before using DOM elements to avoid runtime errors. Reference specific IDs and classes that will be present in the HTML."
    }}
  ]
}}

RULES FOR EACH TASK:
- filepath:
  - Exact relative path (e.g., "index.html", "styles/main.css", "scripts/main.js")
- file_description:
  - 1–2 sentences describing the purpose of the file
- required_imports:
  - HTML files: list ALL CSS/JS files referenced in <link> and <script> tags
  - CSS files: []
  - JS files: []
- task_description:
  - Detailed and concrete description of what to implement in that file
  - Must mention semantic structure for HTML, design system usage for CSS, and interactivity details for JS
  - MUST NOT mention React, Vue, Angular, or any framework

ORDERING:
- Always order implementation_steps as:
  1. "index.html"
  2. "styles/main.css"
  3. "scripts/main.js"
  4. Any additional .html files
  5. Any additional .css files
  6. Any additional .js files

PROJECT PLAN (JSON STRING):
{plan}

REMEMBER:
- Return ONLY the JSON object starting with {{ and ending with }}.
- Do NOT add explanations, comments, or markdown.
"""
    return ARCHITECT_PROMPT


def coder_system_prompt() -> str:
    CODER_SYSTEM_PROMPT = """
You are the CODER agent. You receive a single implementation task at a time and must output the COMPLETE code for exactly one file.

INPUT (from the user message):
- An object that includes at least:
  - "filepath": the path of the file to generate (e.g., "index.html")
  - "task_description": natural language instructions for what the file should contain
  - "required_imports": ONLY for HTML files – the CSS/JS paths you must link

YOUR JOB:
- Write complete, working code that fulfills the task_description for that specific filepath.

CRITICAL OUTPUT FORMAT:
- You MUST return ONLY a valid JSON object:
  {
    "filepath": "path/to/file",
    "code": "complete file contents here"
  }
- No markdown, no code fences, no explanations.
- The "filepath" MUST match the one in the input exactly.
- Do NOT create additional files or return multiple files.

TECH CONSTRAINTS (VANILLA ONLY):
- HTML:
  - Use semantic HTML5 structure (<!DOCTYPE html>, <html>, <head>, <body>, etc.)
  - Add proper <meta charset="UTF-8"> and responsive <meta name="viewport">
  - Use <header>, <nav>, <main>, <section>, <footer> where appropriate
  - Use <link> and <script> tags based on required_imports:
    - For each CSS path: <link rel="stylesheet" href="PATH">
    - For each JS path: <script src="PATH" defer></script>
- CSS (CRITICAL - Modern, Complete Styling):
  - **CSS Reset/Normalize**: Start with a modern CSS reset (box-sizing: border-box, margin/padding reset, etc.)
  - **:root Variables**: Define ALL design system variables at the top:
    * Colors (primary, secondary, accent, backgrounds, text, success, error, warning)
    * Typography (font families, sizes, weights, line heights)
    * Spacing scale (xs, sm, md, lg, xl, xxl in rem/px)
    * Breakpoints (mobile, tablet, desktop)
    * Shadows, borders, border-radius values
  - **Complete Coverage**: Style EVERY class and ID used in HTML files:
    * Semantic elements (header, nav, main, section, footer, article, aside)
    * All classes (e.g., .hero, .card, .button, .nav-menu, .form-input)
    * All IDs (e.g., #navigation, #hero-section, #contact-form)
    * Don't leave any HTML element unstyled
  - **Modern Spacing System**: Use consistent spacing throughout:
    * Padding and margin using design system spacing scale
    * Gap property for Flexbox/Grid layouts
    * Proper spacing between sections and components
  - **Typography Scale**: Style all text elements:
    * h1-h6 with proper hierarchy (decreasing sizes, weights)
    * Body text with readable line-height (1.5-1.6)
    * Small text variants
    * Proper font-weight hierarchy
  - **Color System**: Apply colors consistently:
    * Background colors for sections and components
    * Text colors with proper contrast (WCAG AA minimum)
    * Border colors
    * Use CSS variables for all colors
  - **Responsive Design**: Mobile-first approach:
    * Base styles for mobile (320px+)
    * Tablet breakpoint (768px+) with media queries
    * Desktop breakpoint (1024px+) with media queries
    * Use min-width media queries
  - **Interactive States**: Style ALL interactive elements:
    * :hover states (color changes, scale, shadows)
    * :focus states (outline, border, background changes)
    * :active states (pressed effect)
    * :disabled states (reduced opacity, cursor not-allowed)
  - **Modern Layout**: Use Flexbox and Grid:
    * Flexbox for navigation, buttons, form layouts
    * CSS Grid for complex layouts (cards, sections)
    * Proper alignment and justification
  - **Visual Polish**: Add modern design elements:
    * Smooth transitions (transition property on interactive elements)
    * Subtle animations (transform, opacity changes)
    * Box shadows for depth (cards, buttons, modals)
    * Border-radius for rounded corners
    * Proper z-index layering (navigation, modals, tooltips)
  - **Component Styling**: Style each component completely:
    * Navigation: sticky/fixed positioning, mobile menu styles
    * Buttons: padding, colors, hover effects, disabled states
    * Cards: padding, shadows, hover effects, spacing
    * Forms: input styling, focus states, error states
    * Hero sections: full-width, proper spacing, typography
- JavaScript:
  - Vanilla ES6+ only (no imports, no frameworks)
  - Use DOMContentLoaded before DOM manipulation if needed
  - Use querySelector/querySelectorAll and addEventListener
  - Add null checks before using elements
  - Use small, reusable functions

ERROR PREVENTION:
- Ensure all tags/braces/brackets/parentheses are correctly closed.
- Ensure attributes are quoted correctly.
- Avoid referencing DOM elements that may not exist without null checks.
- For HTML, ensure required_imports paths are used exactly as given.
"""
    return CODER_SYSTEM_PROMPT


def framework_detector_prompt(plan: str) -> str:
    """
    For v1 of your system, we intentionally ALWAYS choose vanilla HTML/CSS/JS.
    This keeps the rest of the toolchain simple and consistent.
    """
    FRAMEWORK_DETECTOR_PROMPT = f"""
You are the FRAMEWORK DETECTOR agent.

CURRENT SYSTEM VERSION:
- The platform currently supports ONLY static, vanilla HTML/CSS/JS projects.
- Frameworks like React, Vue, Angular, Svelte, and build tools are NOT supported yet.

Project Plan (JSON string):
{plan}

YOUR TASK:
- Regardless of the project complexity, for this version you MUST always choose:
  - framework: "vanilla"
  - version: "ES6+"
  - build_tool: "none"
  - requires_build: false
  - config_files: []

CRITICAL OUTPUT FORMAT:
You MUST return ONLY a valid JSON object of shape:

{
  "framework": "vanilla",
  "version": "ES6+",
  "build_tool": "none",
  "requires_build": false,
  "config_files": []
}

Do NOT include any extra keys, comments, or markdown.
"""
    return FRAMEWORK_DETECTOR_PROMPT


def debugger_prompt(files: list, syntax_errors: list = None, runtime_issues: list = None) -> str:
    """Generate prompt for debugger agent to analyze and fix code issues"""
    files_summary = "\n".join([f"- {f.filepath}: {len(f.code)} characters" for f in files])

    syntax_errors_section = ""
    if syntax_errors:
        syntax_errors_section = (
            "\nDETECTED SYNTAX ERRORS (must be fixed):\n"
            + "\n".join([f"- {error}" for error in syntax_errors[:10]])
        )

    runtime_issues_section = ""
    if runtime_issues:
        runtime_issues_section = (
            "\nPOTENTIAL RUNTIME ISSUES (should be fixed):\n"
            + "\n".join([f"- {issue}" for issue in runtime_issues[:10]])
        )

    DEBUGGER_PROMPT = f"""
You are the VALIDATOR/FIXER agent for VANILLA HTML/CSS/JS websites.

YOUR INPUT:
- A list of files (each with a filepath and code).
- Optionally, detected syntax errors and runtime issues.

Files summary:
{files_summary}
{syntax_errors_section}
{runtime_issues_section}

GLOBAL CONSTRAINTS:
- Vanilla HTML/CSS/JS only:
  - No frameworks, no build tools, no imports of external libraries.
- Do NOT:
  - Change file paths
  - Add new files
  - Remove files
- You may only MODIFY the contents of existing files to fix issues.

YOU MUST FIX:

1. HTML SYNTAX ERRORS:
   - Unclosed or mismatched tags
   - Invalid nesting
   - Missing essential elements/attributes (doctype, html, head, body, charset, viewport)
   - Broken references to CSS/JS files (href/src paths must exist in provided files)

2. CSS SYNTAX ERRORS:
   - Unclosed braces
   - Missing semicolons
   - Invalid property names/values
   - Malformed selectors
   - Undefined CSS variables (ensure all custom properties used are defined in :root in main.css)

7. MISSING CSS STYLES (CRITICAL):
   - If you see errors about unstyled classes or IDs, you MUST add complete CSS rules for them
   - Every class (e.g., .hero, .card, .button) MUST have corresponding CSS with:
     * Layout properties (display, flex/grid, width, height)
     * Spacing (padding, margin using design system scale)
     * Typography (font-family, font-size, font-weight, line-height, color)
     * Colors (background-color, color, border-color using CSS variables)
     * Visual effects (border-radius, box-shadow, transitions)
     * Responsive styles (media queries for mobile/tablet/desktop)
   - Every ID (e.g., #navigation, #hero-section) MUST have corresponding CSS
   - Add modern styling: proper spacing, colors, shadows, hover/focus states
   - Use CSS variables from :root for all colors, spacing, and typography
   - Ensure interactive elements have hover, focus, and active states

3. JAVASCRIPT SYNTAX ERRORS:
   - Unclosed braces/brackets/parentheses
   - Malformed function definitions
   - Invalid expressions/operators
   - Broken string literals or template strings

4. FILE REFERENCE ERRORS:
   - Ensure all <link> href and <script> src paths match actual filepaths
   - Ensure asset paths (if any) are plausible and consistent

5. JAVASCRIPT RUNTIME ISSUES:
   - Null/undefined DOM access (add null checks)
   - Accessing DOM before it exists (use DOMContentLoaded or defer)
   - Missing function definitions that are referenced
   - Unhandled errors in core user flows (add basic error handling where necessary)

6. DESIGN SYSTEM / RESPONSIVE ISSUES:
   - Ensure CSS variables are used consistently
   - Ensure media queries are valid and close properly
   - Preserve modern layout (Flexbox/Grid) but fix any syntax errors
   - Add missing CSS variables if referenced but not defined
   - Ensure all components use the design system (colors, spacing, typography)

IMPORTANT BEHAVIOR:
- Preserve the intended functionality and layout as much as possible.
- Do NOT refactor the project into a different architecture.
- Keep all changes minimal but sufficient to prevent errors.

OUTPUT FORMAT (CRITICAL):
You MUST return ONLY a JSON object with this exact shape:

{{
  "fixed_files": [
    {{
      "filepath": "path/to/file.ext",
      "code": "COMPLETE corrected file contents"
    }}
  ]
}}

RULES FOR OUTPUT:
- Include an entry in fixed_files for every file that you modify.
- Provide the FULL corrected code for each modified file, not a diff.
- Do NOT include explanations, comments, or markdown in the output.
"""
    return DEBUGGER_PROMPT
