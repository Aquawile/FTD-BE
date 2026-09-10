# LAYER FIVE — MOCK DATA CLEANUP & UI ARTIFACT REMOVAL

**Agent implementation specification.** This document is intentionally strict. It is the operating contract for implementing Major Layer Five after completion of Major Layer Four. The agent must follow these instructions literally unless the developer explicitly changes them.

## **GLOBAL OPERATING RULES**

Major Layer Four is complete. Layer Five is a new architectural phase. The purpose of this phase is to remove rendered mock data elements and unused UI artifacts from the frontend while preserving all source code needed to reproduce or reference the mock behavior. The distinction between "rendered elements shown to the user" and "source code that defines mock data" is critical and must be enforced at all times.

The agent must not delete any mock data constants, helper functions, type definitions, or reproduction source code. Only the code that actively renders or displays mock data to the user must be removed or replaced with conditional rendering that falls back to live data or empty states.

The agent must first inspect the `App.tsx` file and any related component files to identify every mock data constant, every rendered mock element, and every unused UI artifact (unused components, unused imports, dead code paths). The investigation must be comprehensive: no mock element or dead artifact may be overlooked.

The agent must not invent missing architecture. If a mock element is conditionally rendered and already falls back to live data, it must not be removed — only the unconditional mock rendering path must be removed.

The agent must use the repository's existing tools and mechanisms wherever they are suitable. Repository inspection should be performed with the IDE's file search, symbol search, source navigation, test runner, terminal, Git tooling, and existing project documentation. Build verification must use the existing Vite build pipeline.

Error handling is part of implementation, not an afterthought. Removing mock elements must not leave broken conditional rendering, undefined references, or runtime errors. Every removal must be verified by building and testing the application.

The agent is permitted to investigate and try reasonable approaches, but any deviation from the documented implementation route is tightly bounded. If the planned route encounters a concrete obstacle, the agent may spend no more than five minutes investigating an alternative route. If the issue is not resolved within five minutes, all implementation operations must stop and the agent must report the exact obstacle, what was inspected, what was attempted, what evidence was obtained, and what human decision is required. The agent must not silently redesign the architecture because an alternative appears easier.

The agent must not disable tests, mark tests as skipped merely to obtain a green run, weaken validation, hardcode credentials, modify production data, delete source code that reproduces mock behavior, or leave the application in a broken state after cleanup.

The developer is the authority for what constitutes "safe to remove" vs. "must preserve." The IDE agent is responsible for repository inspection, implementation, test construction, execution, and diagnosis within the approved plan.

## **SUBLAYER 5.1 — REMOVE RENDERED MOCK ELEMENTS WHILE PRESERVING SOURCE CODE**

### **Instruction**

The objective of Sublayer 5.1 is to remove all rendered mock data elements from the user-facing UI while preserving the source code constants and helper functions that define them. The agent must first inspect `App.tsx` and identify every mock data constant and every location where it is rendered.

The following mock data constants must have their rendering removed from the active UI (but the constants themselves must be preserved):
- `NEWS_ARTICLES` — mock news articles rendered on the dashboard and ticker detail pages.
- `TIMELINE_EVENTS` — mock timeline events rendered on the timeline page.
- `CHAT_HISTORY` — mock chat messages rendered on the chat page.
- `MAPPING_QUEUE` — mock mapping queue items rendered on the admin mapping page.
- Any other mock data constants that render elements in the active UI.

The replacement strategy is:
1. For data that has a live API endpoint (from Layers Three and Four), replace the mock rendering with live data fetching.
2. For data that does not yet have a live source, replace the mock rendering with an empty state or loading placeholder that does not display fake data to the user.
3. The mock constant must remain in the codebase, clearly commented as fallback/development mock data, and must remain importable or accessible.

### **Tools to use and why**

Use IDE file search to locate all mock data constants and all references to them in rendering code. Use the terminal to verify the Vite build succeeds after removals. Use Git diff to verify only the intended rendering changes are included. Use the existing API endpoints from Layers Three and Four as the replacement data source.

### **Implementation**

1. **Identify all mock rendering locations:**
   - Search for each mock constant name in `App.tsx`.
   - Document every JSX location where the constant is mapped to rendered elements.
   - Categorize each as "has live API" or "no live API yet."

2. **Replace mock rendering with live data:**
   - For mock data that has a live API endpoint (e.g., `TICKERS` replaced in Layer Four), ensure the component fetches live data and does not fall back to the mock constant in production.
   - For mock data without a live API, replace the rendered mock elements with empty-state components that display a message like "No data available yet" or a loading skeleton.

3. **Preserve mock source code:**
   - Keep all mock data constants in a clearly marked section of `App.tsx` or a dedicated mock data file.
   - Add a comment header: `/* ============================================================
   MOCK DATA - PRESERVED FOR REFERENCE
   These constants are not rendered in the active UI. They are
   preserved as fallback data for development without a backend.
   ============================================================ */`
   - Ensure the constants are not imported or referenced by any active rendering code.

4. **Remove mock conditional paths:**
   - If a component has conditional logic like `const data = liveData || MOCK_DATA`, change it to `const data = liveData` and handle the empty case explicitly.
   - Never silently fall back to mock data in the production code path.

### **Error handling**

If removing a mock constant causes a reference error in an unexpected location, stop and report the missing reference. If the live API is unavailable and the component has no fallback, ensure the empty state is user-friendly. If a mock element is rendered in multiple pages, all occurrences must be addressed.

### **Developer responsibilities**

The developer must approve the list of mock elements to remove and confirm that the preserved source code location is acceptable. The developer must verify that the empty states and loading states are visually acceptable.

### **IDE agent responsibilities**

The IDE agent may remove mock rendering code, replace it with live data fetching or empty states, and reorganize mock constants into a preserved section. It may not delete mock constants, alter the live API response format, or change the visual layout of empty states.

### **Hard stop**

Under no circumstances may the agent delete mock data constants, remove source code that reproduces mock behavior, leave broken references after removal, or continue into UI artifact cleanup before all rendered mock elements are addressed. If a mock element is conditionally rendered and the condition logic is unclear, stop and report.

## **SUBLAYER 5.2 — REMOVE UNUSED SHADCN/UI COMPONENTS AND DEAD CODE**

### **Instruction**

The objective of Sublayer 5.2 is to remove unused shadcn/ui component files and dead code paths from the frontend codebase. The agent must first inspect the `src/app/components/ui/` directory and the `src/app/components/figma/` directory to identify all unused files.

The following categories of unused code must be removed:
1. All 50 shadcn/ui component files in `src/app/components/ui/` that are not imported anywhere in `App.tsx`.
2. The `ImageWithFallback.tsx` file in `src/app/components/figma/` that is not imported anywhere.
3. Any unused import statements in `App.tsx` (e.g., `RechartsPrimitive` if recharts is not used).
4. Any dead code paths in `App.tsx` that are unreachable (e.g., commented-out JSX, unused helper functions).

The agent must verify removal by searching for imports of each file before deleting it. A file must not be deleted if it is imported anywhere in the active codebase.

### **Tools to use and why**

Use IDE file search and symbol search to locate all imports of each component file. Use the terminal to verify the Vite build succeeds after removals. Use Git diff to verify only unused files are removed. Use `rg` (ripgrep) or equivalent to search for component usage across the entire `src/` directory.

### **Implementation**

1. **Audit shadcn/ui components:**
   - List all files in `src/app/components/ui/`.
   - For each file, search the codebase for imports of that component.
   - Delete files that have zero imports.
   - Update `package.json` if any dependencies become unused after component removal (only if the agent has approval to modify package.json).

2. **Remove unused figma components:**
   - Delete `src/app/components/figma/ImageWithFallback.tsx` if it has zero imports.
   - Search for any other files in `src/app/components/figma/` that are unused.

3. **Clean up App.tsx imports:**
   - Remove any import statements for components that no longer exist.
   - Remove any unused local variable declarations or helper functions that are not referenced in the active rendering path.
   - Do not remove mock data constants (handled in Sublayer 5.1).

4. **Verify build:**
   - Run `npm run build` or `npm run dev` to verify the application compiles and runs without errors.
   - Verify the Cloudflare Tunnel serves the updated build correctly.

### **Error handling**

If deleting a component file causes a build error due to an unexpected import, restore the file and report the hidden dependency. If removing an import statement causes a runtime error, restore the import and report. If the build succeeds but the application crashes in the browser, inspect the console for missing component errors.

### **Developer responsibilities**

The developer must approve the removal of each component file and confirm that no hidden dependencies exist. The developer must verify the application functions correctly after cleanup.

### **IDE agent responsibilities**

The IDE agent may delete unused component files, remove unused imports, and clean up dead code paths. It may not modify the project's `package.json` dependencies without explicit approval, remove files that are dynamically imported or referenced in configuration, or alter the build configuration.

### **Hard stop**

Under no circumstances may the agent delete files that are dynamically imported, referenced in configuration files, or used by build tooling. The agent must verify zero imports before deleting any file. If a file appears unused but is referenced in an unexpected way (e.g., via a string-based import, a plugin system, or a test file), stop and report. If the build fails after cleanup, stop and report the error rather than silently restoring files.

## **SUBLAYER 5.3 — CLEAN UP PLACEHOLDER DATA REMNANTS AND UNUSED STATE**

### **Instruction**

The objective of Sublayer 5.3 is to remove any remaining placeholder data remnants and unused state variables from the application after the mock element removal in Sublayer 5.1. The agent must first inspect `App.tsx` for any remaining placeholder text in input fields, unused `useState` declarations, unused `useEffect` hooks, and any other dead state that serves no purpose in the live application.

The cleanup must be surgical: only state and placeholders that are genuinely unused must be removed. State that is used for conditional rendering, form handling, or UI toggles must be preserved even if its current value is a placeholder.

### **Tools to use and why**

Use IDE symbol search to locate all `useState` and `useEffect` declarations in `App.tsx`. Use the terminal to verify the application still functions after cleanup. Use Git diff to review all changes before committing.

### **Implementation**

1. **Audit placeholder text:**
   - Search for any remaining placeholder text that could be mistaken for pre-filled values.
   - Ensure all input fields have appropriate `placeholder` attributes that are visually distinct from actual values.
   - Remove any placeholder text stored in state variables.

2. **Audit unused state:**
   - For each `useState` declaration, verify it is referenced in the component's render output or event handlers.
   - Remove state variables that are declared but never read.
   - Remove `useEffect` hooks that have no dependencies and perform no side effects.

3. **Audit unused event handlers:**
   - Search for `onClick`, `onChange`, `onSubmit`, and other event handlers that are defined but never attached to any element.
   - Remove unused handler functions.

4. **Audit conditional rendering paths:**
   - Search for ternary expressions or conditional blocks that always evaluate to the same branch (e.g., `condition ? <A /> : <A />`).
   - Simplify or remove dead conditional paths.

5. **Final verification:**
   - Run the application and verify all interactive elements function correctly.
   - Verify no React warnings appear in the browser console.
   - Verify the Cloudflare Tunnel serves the cleaned application correctly.

### **Error handling**

If removing a state variable causes a runtime error because it was referenced in an unexpected location (e.g., a deeply nested component, a dynamic prop), stop and report. If removing a placeholder text causes a visual regression, restore it and report.

### **Developer responsibilities**

The developer must approve the removal of any state or placeholder text. The developer must verify the application's visual appearance and interactive behavior after cleanup.

### **IDE agent responsibilities**

The IDE agent may remove unused state, unused effect hooks, unused event handlers, and dead conditional paths. It may not remove state that is used for form handling, conditional rendering, or UI toggles. It may not alter the visual design or layout of any component.

### **Hard stop**

Under no circumstances may the agent remove state that is referenced by any rendering logic, delete mock data constants, alter component props or layout, or continue into documentation before all placeholder remnants and unused state are addressed. If a state variable's usage is ambiguous, stop and report.

## **FINAL LAYER FIVE DEFINITION OF DONE**

Layer Five is complete only when all rendered mock data elements have been replaced with live data, empty states, or loading placeholders; all mock data source code constants are preserved in a clearly marked section; all unused shadcn/ui component files and figma components have been removed; all unused imports, state variables, and dead code paths have been cleaned up; the application builds without errors; and the Cloudflare Tunnel serves the cleaned application without runtime errors or React warnings.

The completion of Layer Five does not authorize work on Layer Six. Any subsequent development must be treated as a separate architectural phase and planned independently.

Most importantly, the agent must stop rather than improvise. If the documented route becomes impossible because the repository differs materially from the assumptions in this specification, the agent may investigate for no more than five minutes. If it cannot resolve the discrepancy within that limit, it must stop all operations and return a concise human-review report containing the exact discrepancy, relevant files and symbols, commands or tests attempted, observed evidence, and the decision that must be made by the developer. It must not continue searching indefinitely, consume context investigating unrelated possibilities, or silently substitute a different architecture.

(End of file - total 233 lines)