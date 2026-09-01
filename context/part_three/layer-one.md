# LAYER ONE — AUTHENTICATION & LANDING PAGE RECONSTRUCTION

**Agent implementation specification.** This document is intentionally strict. It is the operating contract for implementing Major Layer One after completion of the staging environment deployment. The agent must follow these instructions literally unless the developer explicitly changes them.

## **GLOBAL OPERATING RULES**

The staging environment is operational. The React frontend is currently served as static assets via nginx on `ftd-staging-web:8080`, with the built bundle at `context/figma_prototype/dist/`. The backend FastAPI service runs on `ftd-staging-api:8000`. Public access is via Cloudflare Tunnel at `https://specification-frog-parliamentary-turns.trycloudflare.com`.

The purpose of this phase is to replace the public marketing-style landing page with a login-first entry point, eliminate all placeholder text and pre-checked form state, and restructure the sign-up flow so that new users create an account before being prompted to log in. The existing Figma aesthetic must be preserved — this is a functional and behavioral change, not a visual redesign.

The agent must preserve the existing landing page source code in a safe location before modifying anything. The old landing page components, styles, and structure must remain accessible for reference or future restoration. The agent must not delete the original landing page code.

The agent must not invent missing architecture when existing repository code already establishes the intended mechanism. Before changing a component, inspect the relevant existing implementation and determine whether the requirement is already partially or fully satisfied. Prefer the smallest change that establishes the required behavior.

The agent must use the repository's existing tools and mechanisms wherever they are suitable. Repository inspection should be performed with the IDE's file search, symbol search, source navigation, test runner, terminal, Git tooling, and existing project documentation. Build and deployment should use the existing Vite build pipeline and deployment script.

Error handling is part of implementation, not an afterthought. Form validation, authentication failures, and navigation edge cases must be handled according to the project's existing conventions. Where the correct behavior is uncertain, stop and report rather than guessing.

The agent is permitted to investigate and try reasonable approaches, but any deviation from the documented implementation route is tightly bounded. If the planned route encounters a concrete obstacle, the agent may spend no more than five minutes investigating an alternative route. If the issue is not resolved within five minutes, all implementation operations must stop and the agent must report the exact obstacle, what was inspected, what was attempted, what evidence was obtained, and what human decision is required. The agent must not silently redesign the architecture because an alternative appears easier.

The agent must not disable tests, mark tests as skipped merely to obtain a green run, weaken validation, hardcode credentials, modify production data, delete existing application behavior to simplify implementation, or create mock authentication behavior in place of required integration verification.

The developer is the authority for visual design approval, authentication flow decisions, and form behavior. The IDE agent is responsible for repository inspection, implementation, test construction, execution, and diagnosis within the approved plan.

## **SUBLAYER 1.1 — PRESERVE EXISTING LANDING PAGE AND ESTABLISH LOGIN-FIRST ENTRY POINT**

### **Instruction**

The objective of Sublayer 1.1 is to safely preserve the existing marketing-style landing page and replace the application's entry point with a login-first view. The agent must first inspect the existing routing mechanism in `App.tsx`, identify the `LandingPage` component and its associated navigation targets, and determine how the initial page state is established.

The existing landing page must be moved to a safe location within the codebase where it remains accessible but is no longer rendered by default. The recommended approach is to rename the exported component to `LegacyLandingPage` and store it in a dedicated preserved-components section or file. The original routing entry point must be changed to render a new `LoginPage` as the default public view instead of the marketing landing page.

The new login-first entry point must maintain the same Figma aesthetic as the rest of the application. No visual redesign is permitted — only the content and behavior change. The login page must present email and password fields with no pre-filled values, no placeholder text masquerading as values, and no pre-checked "Remember me" checkbox.

### **Tools to use and why**

Use IDE file search and symbol navigation to locate the `LandingPage` component, the `Page` type union, the initial `useState` default, and the `renderPage` switch statement. Use the terminal to verify the Vite build succeeds after changes and to test the deployed result via the Cloudflare Tunnel. Use Git to commit the preservation step before making functional changes. Use the existing CSS/styling conventions in `App.tsx` to ensure visual consistency.

### **Implementation**

1. **Preserve the existing landing page:**
   - Rename the `LandingPage` component export to `LegacyLandingPage` within `App.tsx`.
   - Move the component definition to a clearly marked "Preserved Components" section at the end of the file or in a separate preserved file.
   - Ensure `LegacyLandingPage` is no longer referenced in the `renderPage` switch or any navigation handler.
   - Commit this preservation step before proceeding.

2. **Establish login-first entry:**
   - Change the initial `useState<Page>` default from `"landing"` to `"login"`.
   - Ensure the `login` case in `renderPage` renders the existing `LoginPage` component without the `AppShell` wrapper (public page).
   - Verify that navigating to any unauthenticated route defaults to `login` rather than `landing`.

3. **Update navigation targets:**
   - Audit all `navigate("landing")` calls in the codebase and replace them with `navigate("login")` where appropriate.
   - Ensure `Sign In` buttons throughout the app navigate to `login`.
   - Ensure `Sign Out` navigates to `login` (not to a non-existent landing page).

### **Error handling**

If the `Page` type union or routing mechanism differs from the assumed structure, stop and report the exact discrepancy before making changes. If preserving the landing page would require creating a new file and the project conventions do not establish a clear location, ask the developer for the preferred preserved-components location.

### **Developer responsibilities**

The developer must approve the new default entry point and confirm that the preserved landing page location is acceptable. The developer must verify the visual consistency of the login page after the landing page is removed.

### **IDE agent responsibilities**

The IDE agent may inspect the routing code, rename and relocate the landing page component, update navigation targets, and verify the build. It may not redesign the login page visual layout or alter the existing authentication mechanism.

### **Hard stop**

Under no circumstances may the agent delete the original landing page code, redesign the login page visual appearance, modify the Firebase authentication implementation, or continue into form field fixes before the landing page preservation is committed. If the routing structure differs materially from the assumed pattern, stop and report.

## **SUBLAYER 1.2 — ELIMINATE PLACEHOLDER TEXT AND PRE-CHECKED FORM STATE**

### **Instruction**

The objective of Sublayer 1.2 is to remove all placeholder text that appears as pre-filled values and all pre-checked form elements from the authentication and onboarding flows. The agent must first inspect the `LoginPage`, `RegisterPage`, `ForgotPasswordPage`, and `OnboardingPage` components to identify every instance of placeholder-as-value, pre-checked checkboxes, and pre-selected form state.

The distinction between placeholder text and actual values must be strictly enforced. A placeholder is visual hint text displayed inside an empty input field. A value is actual data bound to the input's `value` prop. Placeholder text must never be stored as a component state default or passed as a `value` prop. Pre-checked checkboxes must be changed to unchecked defaults. Pre-selected dropdowns must be changed to empty or neutral defaults.

### **Tools to use and why**

Use IDE symbol search to locate all `useState` declarations with string defaults, all `defaultChecked` attributes, all `value=` props on inputs, and all `placeholder=` props in the authentication and onboarding components. Use the terminal to test form submission behavior after changes. Use Git diff to verify only the intended form state changes are included.

### **Implementation**

1. **LoginPage fixes:**
   - Change `useState("isabella@research.co")` to `useState("")` for the email field.
   - Change `useState("••••••••")` to `useState("")` for the password field. The placeholder attribute already provides visual guidance.
   - Remove `defaultChecked` from the "Remember me" checkbox and replace with controlled state defaulting to `false`.
   - Ensure all inputs have appropriate `placeholder` attributes that remain visible only when the field is empty.

2. **RegisterPage fixes:**
   - Audit all three steps of the register form for pre-filled values or pre-checked state.
   - Ensure all `useState` defaults are empty strings or `false` booleans.
   - Ensure the password validation checklist does not display checkmarks for criteria that have not been met.

3. **ForgotPasswordPage fixes:**
   - Ensure the email field starts empty with a placeholder, not with a pre-filled value.

4. **OnboardingPage fixes:**
   - Ensure workspace name and tickers inputs start empty with placeholders.
   - Ensure sector checkboxes start unchecked unless the existing flow explicitly requires defaults.
   - Ensure all form state is properly controlled or uncontrolled — never a `value` prop without an `onChange` handler.

### **Error handling**

If any form field uses a value prop without an onChange handler, React will emit a warning and render the field as read-only. This must be resolved, not suppressed. If placeholder text is required for visual design, it must be passed as the `placeholder` attribute only, never as a default state value.

### **Developer responsibilities**

The developer must approve the removal of any pre-filled values that were intentionally seeded for demonstration purposes. The developer must verify that the login flow still functions correctly with empty default values.

### **IDE agent responsibilities**

The IDE agent may modify form state defaults, add missing `onChange` handlers, and remove `defaultChecked` attributes. It may not alter the visual layout, styling, or validation logic of the forms.

### **Hard stop**

Under no circumstances may the agent redesign the authentication forms, add new form fields, change the validation rules, modify the Firebase authentication calls, or continue into the sign-up flow restructuring before all placeholder and pre-checked state is eliminated. If a form field's current behavior depends on a pre-filled value for non-obvious reasons, stop and report.

## **SUBLAYER 1.3 — RESTRUCTURE SIGN-UP FLOW AND NAVIGATION TARGETS**

### **Instruction**

The objective of Sublayer 1.3 is to restructure the sign-up flow so that new users are guided through account creation before being prompted to log in, and to ensure all navigation targets throughout the application correctly reference the restored routing structure. The agent must first inspect the `RegisterPage` component, the `LoginPage` component, and all navigation elements (buttons, links, sidebar items) that reference authentication actions.

The current flow appears to have a "Get Started" or sign-up button that immediately navigates to the login page. This must be changed so that the sign-up button navigates to the registration flow, and the login page presents an option for existing users to navigate to the login form. The exact wording and layout must match the existing Figma design — only the navigation targets change.

### **Tools to use and why**

Use IDE symbol search to locate all `navigate("login")`, `navigate("register")`, and similar calls. Use the terminal to verify navigation behavior in the built application. Use Git diff to confirm only navigation targets and routing logic are changed.

### **Implementation**

1. **Restructure the login page header:**
   - Ensure the login page presents a clear "Sign In" heading for existing users.
   - Add a visible link or button for "Create an account" that navigates to `register`.
   - Ensure the visual hierarchy matches the existing Figma design.

2. **Restructure the register page:**
   - Ensure the register page is the target of the "Get Started" / "Create Account" / "Sign Up" CTAs.
   - Verify the three-step registration flow (name, email/password, review) is accessible and functional.
   - Ensure the register page does not redirect to login before the user has completed registration.

3. **Audit all navigation targets:**
   - Search the entire `App.tsx` for all `navigate()` calls that reference authentication pages.
   - Verify that `Sign In` buttons navigate to `login`.
   - Verify that `Get Started`, `Create Account`, `Sign Up` buttons navigate to `register`.
   - Verify that `Sign Out` navigates to `login` (not `landing`).
   - Verify that any "Forgot password" links navigate to `forgot-password`.

4. **Update the preserved landing page references:**
   - If `LegacyLandingPage` contains any navigation buttons, ensure they are updated to reference the correct new entry points.

### **Error handling**

If navigation targets are inconsistent (e.g., some buttons navigate to `landing` while others navigate to `login`), all references must be unified. If the register flow contains steps that depend on the old landing page context, stop and report the dependency.

### **Developer responsibilities**

The developer must approve the new navigation flow and confirm that the wording on the login and register pages matches the intended user experience. The developer must verify the complete navigation map after changes.

### **IDE agent responsibilities**

The IDE agent may update navigation targets, restructure the login page header, and verify routing consistency. It may not alter the registration form steps, validation logic, or Firebase authentication calls.

### **Hard stop**

Under no circumstances may the agent modify the Firebase authentication implementation, change the registration form fields, alter the email verification flow, or continue into profile page restructuring before the authentication navigation is fully consistent. If the register flow depends on the old landing page for any step, stop and report.

(End of file - total 203 lines)