# LAYER TWO — PROFILE PAGE UI RESTRUCTURING & FORM FIXES

**Agent implementation specification.** This document is intentionally strict. It is the operating contract for implementing Major Layer Two after completion of Major Layer One. The agent must follow these instructions literally unless the developer explicitly changes them.

## **GLOBAL OPERATING RULES**

Major Layer One is complete. Layer Two is a new architectural phase. The purpose of this phase is to fix the `AccountPage` component (to be renamed `ProfilePage`), restructure the sidebar navigation, repair broken controlled input fields, enable profile picture upload, and move the sign-out button into the profile dropdown. The desired outcome is a fully functional profile management interface that preserves the existing Figma aesthetic while correcting all underlying form and navigation defects.

The agent must begin by renaming `AccountPage` to `ProfilePage` throughout the codebase. All references, navigation targets, and routing cases must be updated atomically. The rename is a prerequisite for all subsequent sublayers.

The agent must not invent missing architecture when existing repository code already establishes the intended mechanism. Before changing a component, inspect the relevant existing implementation and determine whether the requirement is already partially or fully satisfied. Prefer the smallest change that establishes the required behavior.

The agent must use the repository's existing tools and mechanisms wherever they are suitable. Repository inspection should be performed with the IDE's file search, symbol search, source navigation, test runner, terminal, Git tooling, and existing project documentation. Build and deployment should use the existing Vite build pipeline and deployment script.

Error handling is part of implementation, not an afterthought. Form validation, image upload failures, and navigation edge cases must be handled according to the project's existing conventions. Where the correct behavior is uncertain, stop and report rather than guessing.

The agent is permitted to investigate and try reasonable approaches, but any deviation from the documented implementation route is tightly bounded. If the planned route encounters a concrete obstacle, the agent may spend no more than five minutes investigating an alternative route. If the issue is not resolved within five minutes, all implementation operations must stop and the agent must report the exact obstacle, what was inspected, what was attempted, what evidence was obtained, and what human decision is required. The agent must not silently redesign the architecture because an alternative appears easier.

The agent must not disable tests, mark tests as skipped merely to obtain a green run, weaken validation, hardcode credentials, modify production data, delete existing application behavior to simplify implementation, or create mock authentication behavior in place of required integration verification.

The developer is the authority for visual design approval, form behavior decisions, and navigation structure. The IDE agent is responsible for repository inspection, implementation, test construction, execution, and diagnosis within the approved plan.

## **SUBLAYER 2.1 — RENAME ACCOUNTPAGE TO PROFILEPAGE AND RESTRUCTURE SIDEBAR NAVIGATION**

### **Instruction**

The objective of Sublayer 2.1 is to rename the `AccountPage` component to `ProfilePage` and restructure the sidebar navigation so that the Admin link is positioned with the main navigation items rather than separated near the Sign Out button. The agent must first inspect the `Sidebar` component, the navigation items array, and all references to `AccountPage` / `"account"` in the routing and navigation code.

The current sidebar layout places the Admin link in a bottom section near the Sign Out button. The desired layout places Admin directly under the last main navigation item (Alerts), before the bottom separator. The Sign Out button must remain in the bottom section but will be moved into a profile dropdown in a later sublayer — for now, it remains in place.

### **Tools to use and why**

Use IDE file search and symbol navigation to locate the `Sidebar` component, the `navItems` array, all `navigate("account")` calls, and the `case "account"` in the `renderPage` switch. Use the terminal to verify the Vite build succeeds after the rename. Use Git to commit the rename step before proceeding to functional fixes.

### **Implementation**

1. **Rename AccountPage to ProfilePage:**
   - Rename the component definition from `AccountPage` to `ProfilePage`.
   - Update the `Page` type union value from `"account"` to `"profile"`.
   - Update all `navigate("account")` calls to `navigate("profile")`.
   - Update the `case "account"` in `renderPage` to `case "profile"`.
   - Update the Sidebar nav item that navigates to the profile page.
   - Verify no references to `"account"` remain in routing or navigation code.

2. **Restructure the sidebar:**
   - Locate the `navItems` array in the `Sidebar` component.
   - Move the Admin item from the bottom section to the main navigation list, positioned directly after Alerts.
   - Ensure the visual separator between main navigation and bottom actions (Sign Out) remains intact.
   - Verify the Admin link navigates to `admin` and is visually consistent with other nav items.

### **Error handling**

If the sidebar uses a different navigation structure than assumed (e.g., separate arrays for main and bottom items, or a different component hierarchy), stop and report the exact structure before making changes. If renaming `"account"` to `"profile"` would break external references (bookmarks, stored URLs), note this as a consideration for the developer.

### **Developer responsibilities**

The developer must approve the `ProfilePage` rename and confirm the new sidebar layout. The developer must verify that any external references to the old `/account` route are handled (e.g., redirect or update documentation).

### **IDE agent responsibilities**

The IDE agent may rename the component, update routing cases, restructure the sidebar nav items, and verify the build. It may not alter the visual styling of the sidebar or the content of the Admin page.

### **Hard stop**

Under no circumstances may the agent modify the Admin page content, change sidebar styling, or continue into form field fixes before the rename and sidebar restructuring are complete and committed. If the navigation structure differs materially from the assumed pattern, stop and report.

## **SUBLAYER 2.2 — FIX CONTROLLED INPUT FIELDS AND ENABLE PROFILE PICTURE UPLOAD**

### **Instruction**

The objective of Sublayer 2.2 is to fix the controlled input fields on the `ProfilePage` that currently have `value` props without `onChange` handlers, making them read-only, and to add a functional profile picture upload mechanism to the "Edit Photo" button. The agent must first inspect the `ProfilePage` component (formerly `AccountPage`) to identify all controlled inputs missing `onChange` handlers, and inspect the avatar rendering code to understand how the profile picture is currently displayed.

The profile picture upload must use a standard HTML `<input type="file">` triggered by the "Edit Photo" button. The selected image must be read using `FileReader` or `URL.createObjectURL` and displayed in the avatar area. The upload must not require a backend service for the prototype — local preview via object URL is sufficient. The existing gradient-circle-with-initials fallback must be preserved for users who have not uploaded a photo.

### **Tools to use and why**

Use IDE symbol search to locate all `Input` components on the `ProfilePage` that receive a `value` prop. Use source navigation to find the avatar rendering code and the "Edit Photo" button. Use the terminal to test form interaction after fixes. Use Git diff to verify only the intended input and upload changes are included.

### **Implementation**

1. **Fix controlled inputs:**
   - Locate the First name, Last name, and Email input fields on the `ProfilePage` profile tab.
   - Add `useState` declarations for each field if not already present.
   - Add `onChange` handlers that update the corresponding state.
   - Ensure the inputs are fully editable — no read-only behavior.
   - Verify React does not emit the "value prop without onChange handler" warning.

2. **Fix the "Save Profile" button:**
   - Add an `onClick` handler that reads the current state values.
   - For the prototype, the handler may log the values to console or display a success message.
   - A real backend API call is not required for this sublayer.

3. **Enable profile picture upload:**
   - Add a hidden `<input type="file" accept="image/*">` element to the `ProfilePage`.
   - Wire the "Edit Photo" button `onClick` to trigger the file input's `click()` method.
   - Add an `onChange` handler to the file input that reads the selected file using `URL.createObjectURL`.
   - Store the resulting object URL in component state.
   - Conditionally render the uploaded image in the avatar area when state is present, falling back to the initials gradient circle when absent.
   - Add cleanup: revoke the object URL when a new file is selected or the component unmounts.

4. **Preserve Figma aesthetic:**
   - The avatar container size, border radius, and positioning must not change.
   - The gradient fallback must remain identical to the current implementation.
   - The "Edit Photo" button size, position, and icon must remain identical.

### **Error handling**

If the file input is triggered but the user cancels the dialog, the handler must not crash or clear an existing photo. If the selected file is not an image, the handler must reject it gracefully. If the `FileReader` or `URL.createObjectURL` API is unavailable (unlikely but possible in older browsers), fall back to the initials avatar without error.

### **Developer responsibilities**

The developer must approve the profile picture upload approach (local preview only, no backend storage in this phase). The developer must verify the avatar area renders correctly with both uploaded images and initials fallback.

### **IDE agent responsibilities**

The IDE agent may add state declarations, onChange handlers, file input logic, and conditional avatar rendering. It may not alter the avatar container styling, change the button appearance, or implement backend image storage.

### **Hard stop**

Under no circumstances may the agent implement Firebase Storage uploads, modify the backend to accept image uploads, change the avatar container dimensions, or continue into sidebar navigation restructuring before all form inputs are editable and the photo upload works. If the avatar rendering depends on external state not present in the component, stop and report.

## **SUBLAYER 2.3 — MOVE SIGN-OUT INTO PROFILE DROPDOWN AND FINALIZE PROFILE PAGE**

### **Instruction**

The objective of Sublayer 2.3 is to move the Sign Out button from the sidebar bottom section into a dropdown menu that appears when the user clicks their profile picture in the top-right corner of the `AppShell`. The agent must first inspect the `TopBar` component to locate the profile picture/avatar button and the `Sidebar` component to locate the Sign Out button.

The dropdown must contain at minimum: the user's display name and email, and a Sign Out option. Clicking Sign Out must navigate to the login page and clear any authenticated user state. Clicking outside the dropdown or pressing Escape must close it. The existing Figma dropdown styling must be preserved.

### **Tools to use and why**

Use IDE symbol search to locate the `TopBar` component, the profile avatar button, the `Sidebar` Sign Out button, and the user state management in `App.tsx`. Use the terminal to test dropdown interaction and sign-out behavior. Use Git diff to verify only the navigation and dropdown changes are included.

### **Implementation**

1. **Create the profile dropdown component:**
   - Add a dropdown state (`isProfileOpen`) to `TopBar` or `AppShell`.
   - Conditionally render a dropdown menu anchored to the profile picture button when `isProfileOpen` is true.
   - Populate the dropdown with the user's display name, email, and a Sign Out button.
   - Add click-outside and Escape-key handlers to close the dropdown.
   - Style the dropdown using the existing Figma design tokens (background, border, shadow, typography).

2. **Wire the profile picture button:**
   - Add an `onClick` handler to the profile avatar button that toggles `isProfileOpen`.
   - Ensure the dropdown does not open when navigating to the Profile page via the sidebar — only the top-right avatar triggers the dropdown.

3. **Move Sign Out logic:**
   - Remove the Sign Out button from the sidebar bottom section.
   - Wire the dropdown's Sign Out button to the same sign-out handler currently used by the sidebar button.
   - Ensure the sign-out handler clears user state, Firebase session, and navigates to `login`.

4. **Finalize the ProfilePage:**
   - Verify all four tabs (profile, security, preferences, api) render correctly.
   - Verify the profile tab shows editable fields with the fixes from Sublayer 2.2.
   - Verify the "Edit Photo" button triggers the file upload.
   - Verify the security, preferences, and api tabs are functional (even if backend calls are mocked).
   - Ensure no placeholder text appears in any input field.

### **Error handling**

If the dropdown open state conflicts with other click handlers (e.g., the Bell notifications button), stop and report the event propagation issue. If the sign-out handler depends on state that is not accessible from the TopBar, refactor the handler to the appropriate scope.

### **Developer responsibilities**

The developer must approve the dropdown content and sign-out behavior. The developer must verify that the sidebar layout still looks correct after the Sign Out button is removed.

### **IDE agent responsibilities**

The IDE agent may create the dropdown component, add state management, wire click handlers, and remove the sidebar Sign Out button. It may not alter the profile page tabs, change the avatar styling, or modify the authentication mechanism.

### **Hard stop**

Under no circumstances may the agent modify the Firebase sign-out implementation, change the TopBar layout beyond the dropdown addition, remove the sidebar Sign Out button before the dropdown is functional, or continue into dashboard real-data integration before the profile page is fully functional. If the user state is not accessible from the TopBar scope, stop and report the required refactor.

(End of file - total 236 lines)