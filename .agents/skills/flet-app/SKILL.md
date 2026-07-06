---
name: flet-app
description: "Expert knowledge for building multi-platform Python apps with Flet's declarative UI. Covers state management, hooks, navigation, theming, async patterns, component architecture, 85+ breaking changes, API traps, 19+ new controls, declarative field validation (Annotated + V rules), customizable scrollbars, 6.7x faster diffing, ft.Router (nested routes, outlets, loaders, mobile view stacks), ft.use_dialog hook, Screenshot/take_animation. Flet 0.85.x+."
---

# Flet App Development — Complete Reference

> Flet 0.85.x | Declarative mode | Validated against real production apps and Flet 0.85.0 source

---

## What's New in Flet 0.85.x

| Feature | Details |
|---------|---------|
| **`ft.Router`** | Declarative router with nested routes, layout `outlet`s, dynamic/optional/splat segments, regex constraints, per-route data `loader`s, hooks (`use_route_params`, `use_route_location`, `use_view_path`, `use_route_outlet`, `use_route_loader_data`, `is_route_active`), and mobile view-stack mode (`manage_views=True`) with swipe-back, system back button, and implicit `AppBar` back arrow |
| **`ft.use_dialog(dialog)`** | Reactive dialog hook — portals a `DialogControl` to the page's dialog overlay. Pass `None` to dismiss. Preserves Flutter widget identity (e.g., `TextField` cursor) across re-renders via frozen diff |
| **`page.navigate(route, **kwargs)`** | Sync wrapper for `page.push_route()` — use in `on_click` and other sync callbacks where awaiting is impossible |
| **`page.pop_views_until(route, result=None)`** | Pops views from the navigation stack until a view with the given `route`. Result delivered via new `on_views_pop_until` (`ViewsPopUntilEvent`) |
| **`page.take_animation(...)`** | Captures animated PNG frame sequence in a single round-trip (no Python↔Flutter RPC latency between frames). Requires `page.enable_screenshots = True` |
| **`Screenshot` control** | New control with `content` + `capture(pixel_ratio, delay)` method for subtree screenshots |
| **`DragTargetEvent` migration** | `.x`, `.y`, `.offset` deprecated in 0.85.0 (removal in 0.88.0) — use `local_position` (target-relative) or `global_position` (global) |

## Flet 0.83.x Foundations (still applicable)

| Feature | Details |
|---------|---------|
| **6.7x faster diffing** | `Prop` descriptor tracks only modified properties; `@value` decorator enables content-based comparison for ~150 data types |
| **Smart update()** | Framework tracks explicit `.update()` calls during handlers — skips auto-update to avoid redundant renders |
| **Field validation** | `Annotated[type, V.rule()]` for declarative field constraints (e.g., `V.between(0, 1)`, `V.ge(0)`, `V.instance_of(...)`) |
| **Customizable scrollbars** | `Scrollbar(thumb_visibility=, track_visibility=, thickness=, radius=, interactive=, orientation=)` on any scrollable control |
| **Scrollable ExpansionPanelList** | Now inherits `ScrollableControl` — supports `scroll`, `auto_scroll`, `on_scroll`, `scroll_to()` |
| **SharedPreferences expanded** | Now supports `int`, `float`, `bool`, `list[str]` (not just `str`) |
| **Padding functions removed** | `ft.padding.all()` / `.symmetric()` / `.only()` removed — use `ft.Padding.all()` class methods |
| **Desktop packaging** | Desktop binaries moved from PyPI to GitHub Releases, cached at `~/.flet/client/` |

---

## Fundamentals

### Philosophy: UI = f(state)

```
State changes → components re-render automatically
No manual page.update()
No explicit setState()
No control references for mutation
```

### Entry Point

```python
# CORRECT — Flet 0.80.x+
import flet as ft

def main(page: ft.Page):
    page.title = "My App"
    page.render_views(App, state)

if __name__ == "__main__":
    ft.run(main)

# WRONG — deprecated
ft.app(target=main)  # Never use this
```

### Rendering Modes

```python
# page.render(Component) — updates views[0].controls
page.render(MyApp)

# page.render_views(Component, ...args) — replaces entire page.views
# Use this when you need AppBar, Drawer, or custom View
page.render_views(App, state, service)

# IMPORTANT: pass the function reference, NOT the result
page.render(Counter)      # CORRECT — Flet calls it internally
page.render(Counter())    # WRONG — RuntimeError: No current renderer
```

### Directory Structure

Clean Architecture layout — same separation of concerns as Flutter's
recommended `lib/` structure (`core/`, `data/`, `domain/`, `presentation/`,
`services/`, `utils/`), with `main.py` and `app.py` **inside `src/`** (the Flet
equivalent of `lib/`). Validated on a production Flet declarative app.

```
my_app/
├── assets/                    # fonts/, icons/, images/
├── config.py                  # Project-root config (Flutter's pubspec parallel)
├── pyproject.toml             # [tool.flet.app] path = "src"
├── tests/                     # conftest.py, unit/, widget/, integration/
└── src/
    ├── __init__.py
    ├── main.py                # ft.run(create_app, assets_dir="assets")
    ├── app.py                 # create_app(page): theme, DI, page.render_views(...)
    │
    ├── core/                  # Shared base (no Flet, no I/O)
    │   ├── constants.py
    │   ├── enums.py
    │   ├── exceptions.py
    │   └── logger.py
    │
    ├── data/                  # Implements domain interfaces
    │   ├── sources/           # api_source.py, local_source.py
    │   ├── models/            # DTOs
    │   └── repositories/      # *_repository_impl.py
    │
    ├── domain/                # Pure business rules (no Flet imports)
    │   ├── entities/          # Dataclasses
    │   ├── repositories/      # Abstract contracts
    │   ├── services/          # Domain services
    │   └── usecases/          # Orchestrate entities + repositories
    │
    ├── presentation/          # Flet UI layer
    │   ├── components/        # common/, dialogs/ — reusable widgets
    │   ├── pages/             # Feature-grouped screens (auth/, home/, settings/)
    │   ├── navigation/        # app_router.py, navigation_service.py
    │   ├── themes/            # app_theme.py, colors.py
    │   ├── hooks/             # use_auth.py, use_theme.py — reusable hooks
    │   └── state_management/  # global_providers.py, *_state.py
    │
    ├── services/              # Infrastructure (api_service, storage, paths, exports)
    └── utils/                 # Pure helpers (validators, datetime_utils, text_utils)
```

See `references/architecture.md` for the full layered breakdown and dependency
rules. For tiny apps (one or two pages), a flat `src/{main.py, pages/, components/}`
is fine — adopt the full structure when the project crosses ~5 pages or has any
real business logic.

### pyproject.toml

```toml
[project]
name = "my-app"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["flet>=0.80.0"]

[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

# REQUIRED when using src/ layout
[tool.flet.app]
path = "src"
```

---

## State Management

### Three Types of State

| Type | Mechanism | When to Use |
|------|-----------|-------------|
| **Global/Shared** | `@ft.observable @dataclass` | App state shared across pages |
| **Local** | `ft.use_state(initial)` | Form fields, toggles, local counters |
| **Injected via context** | `ft.create_context` + `ft.use_context` | Services, configuration, themes |

### 1. Global State: @ft.observable

```python
from dataclasses import dataclass, field
import flet as ft


# IMPORTANT: @ft.observable BEFORE @dataclass (order matters!)
@ft.observable
@dataclass
class AppState:
    # Scalars: any assignment triggers re-render
    current_page: str = "home"
    is_loading: bool = False
    user_id: str | None = None

    # Lists: .append()/.clear()/.remove() trigger re-render
    # The list becomes an ObservableList automatically
    items: list[str] = field(default_factory=list)

    # Methods that modify state
    def navigate(self, page_id: str) -> None:
        self.current_page = page_id  # Notifies all listeners

    def set_loading(self, loading: bool) -> None:
        self.is_loading = loading

    def add_item(self, item: str) -> None:
        self.items.append(item)  # ObservableList notifies

    def clear_items(self) -> None:
        self.items.clear()  # Also notifies
```

**How notification works:**

```python
@ft.component
def MyPage():
    ctx = ft.use_context(AppCtx)
    state = ctx.state  # Auto-subscribes

    # When state.current_page changes → MyPage re-renders
    return ft.Text(f"Current page: {state.current_page}")
```

**Observable internals (important):**

- `__setattr__` intercepts field changes and calls `_notify(field)` only if `value_equal(old, new)` returns False
- **Setting the same value is a no-op** — no notification fires, no re-render
- Private fields (starting with `_`) are NEVER notified
- Lists/dicts are auto-wrapped as `ObservableList` / `ObservableDict`
- Components subscribe to observables passed as **arguments** via `_subscribe_observable_args`

**Manual notification — `notify()`:**

When you need to force a re-render but the observable value hasn't changed (e.g., after an async operation where sub-fields changed), use `notify()`:

```python
# Force re-render even if no field changed
state.notify()  # Calls _notify(None), triggers all listeners

# Common use case: after async data loading
await load_data(state, api, name)
state.notify()  # Guarantee subscribers re-render
```

> **Why not just set the same value?** `state.field = state.field` is a no-op for `@ft.observable` because `value_equal(old, new)` returns True. Use `notify()` instead.

### 2. Local State: ft.use_state

```python
@ft.component
def LoginPage():
    # Local state: persists between re-renders of the same component
    # NOT shared with other components
    username, set_username = ft.use_state("")
    password, set_password = ft.use_state("")
    is_submitting, set_submitting = ft.use_state(False)

    async def handle_login(e):
        set_submitting(True)
        try:
            await service.login(username)
        finally:
            set_submitting(False)

    return ft.Column([
        ft.TextField(
            label="Username",
            value=username,
            on_change=lambda e: set_username(e.control.value),
        ),
        ft.FilledButton(
            "Login",
            disabled=is_submitting,
            on_click=handle_login,
        ),
    ])
```

**Important rule: use_state for form inputs**

```python
# CORRECT: use_state for input fields
# Avoids re-rendering the entire tree on every keystroke
text, set_text = ft.use_state("")
ft.TextField(value=text, on_change=lambda e: set_text(e.control.value))

# WRONG: using observable for form input
# Would re-render all subscriber components on every key press
```

### 3. Context: ft.create_context + ft.use_context

```python
# context.py — Define the context
from dataclasses import dataclass
import flet as ft
from state import AppState

@dataclass
class AppContext:
    state: AppState
    service: "MyService"
    clipboard: ft.Clipboard

# Create global provider with default value None
AppCtx = ft.create_context(None)
```

```python
# main.py — Provide the context
@ft.component
def App(state, service, clipboard):
    ctx = AppContext(state=state, service=service, clipboard=clipboard)

    def build_view():
        return ft.View(controls=[PageContent()], ...)

    # Provide context: AppCtx(value, builder_function)
    return AppCtx(ctx, build_view)
```

```python
# Any child component — Consume the context
@ft.component
def NotificationsPage():
    ctx = ft.use_context(AppCtx)  # Gets nearest provider value

    # CRITICAL: Guard against None context (see warning below)
    if ctx is None:
        return ft.Container()

    state = ctx.state
    service = ctx.service

    # use_context auto-subscribes: re-renders when AppCtx changes
```

> **CRITICAL — `use_context` can return `None`:**
> When navigating between pages, Flet's updates scheduler may call `update()` on a component that was already replaced/unmounted. At that point, the context provider is no longer in the tree, so `use_context()` returns `None`. Accessing `ctx.anything` without a guard raises `AttributeError`, which **crashes the scheduler** (it only catches `CancelledError`). Once the scheduler dies, ALL subsequent UI updates for that session are lost — the page freezes permanently.
>
> **Always add `if ctx is None: return ft.Container()` immediately after `use_context()`.**

### 4. Pattern: State Created Outside Components

```python
def main(page: ft.Page):
    # Created OUTSIDE because event handlers need access
    # BEFORE the component is mounted
    app_state = AppState()

    service = MyService(
        app_id="...",
        # Lambda captures app_state by closure
        on_event=lambda e: app_state.add_log(f"Event: {e.data}", "info"),
    )
    page.services.append(service)

    # Pass as argument to root component
    page.render_views(App, app_state, service)
```

### State Quick Reference

| Need | Solution |
|------|----------|
| Form field (input) | `ft.use_state("")` |
| Local toggle (expanded, checked) | `ft.use_state(False)` |
| Global app state | `@ft.observable @dataclass` |
| Share services across pages | `ft.create_context` + `AppCtx` |
| Observable list count/mutation | `.append()` / `.clear()` |

---

## Hooks Reference

### Summary Table

| Hook | Signature | Purpose |
|------|-----------|---------|
| `use_state` | `(initial) → (value, setter)` | Persistent local state |
| `use_effect` | `(setup, deps?, cleanup?)` | Side effects and cleanup |
| `on_mounted` | `(fn)` | Run once on mount |
| `on_unmounted` | `(fn)` | Run once on unmount |
| `on_updated` | `(fn, deps?)` | Run on every re-render |
| `use_context` | `(provider) → value` | Read context value |
| `create_context` | `(default) → provider` | Create context provider |
| `use_memo` | `(fn, deps?) → value` | Memoize computed value |
| `use_callback` | `(fn, deps?) → fn` | Memoize function identity |
| `use_ref` | `() → Ref` | Persistent mutable reference |
| `use_dialog` | `(dialog \| None) → None` | Portal a `DialogControl` to page's dialog overlay (0.85.0+) |
| `use_route_params` | `() → dict[str, str]` | Dynamic route segment params (inside `ft.Router`, 0.85.0+) |
| `use_route_location` | `() → str` | Current URL pathname (inside `ft.Router`, 0.85.0+) |
| `use_view_path` | `() → str` | URL resolved up to this view level (`manage_views=True`, 0.85.0+) |
| `use_route_outlet` | `() → Control` | Matched child component, for layout routes (0.85.0+) |
| `use_route_loader_data` | `() → Any` | Result of the route's `loader=` (0.85.0+) |
| `is_route_active` | `(path, exact=False) → bool` | Check if `path` matches current location (0.85.0+) |

### use_state

```python
@ft.component
def Counter():
    count, set_count = ft.use_state(0)

    # Setter with direct value
    def increment(e):
        set_count(count + 1)

    # Setter with updater function (uses latest value — avoids stale closures)
    def increment_safe(e):
        set_count(lambda prev: prev + 1)

    return ft.Row([
        ft.Text(str(count)),
        ft.IconButton(ft.Icons.ADD, on_click=increment),
    ])
```

**Behavior:**
- Value persists between re-renders of the same component
- `set_state(new_value)` only triggers re-render if `new_value != current_value` (shallow equality)
- `set_state(lambda prev: ...)` uses the latest value (avoids stale closure)
- Accepts callable as `initial`: `use_state(lambda: compute_initial())`

### use_effect

```python
@ft.component
def MyComponent():
    data, set_data = ft.use_state(None)

    # Run only on mount (deps=[])
    async def load_data():
        result = await api.fetch()
        set_data(result)

    ft.use_effect(load_data, dependencies=[])

    # Run when `query` changes
    query, set_query = ft.use_state("")

    async def search():
        result = await api.search(query)
        set_data(result)

    ft.use_effect(search, dependencies=[query])

    # With separate cleanup (NOT return value like React!)
    def start_timer():
        timer.start()

    def stop_timer():
        timer.stop()

    ft.use_effect(start_timer, dependencies=[], cleanup=stop_timer)

    return ft.Text(str(data))
```

**CRITICAL — Difference from React:**

```python
# WRONG (React pattern — cleanup as return is IGNORED in Flet)
def setup():
    timer.start()
    return lambda: timer.stop()  # This cleanup is IGNORED

ft.use_effect(setup, [])

# CORRECT (Flet pattern — cleanup is a separate parameter)
ft.use_effect(
    setup=lambda: timer.start(),
    dependencies=[],
    cleanup=lambda: timer.stop(),
)
```

### on_mounted / on_unmounted / on_updated

Convenience shortcuts for `use_effect`:

```python
from flet.components.hooks.use_effect import on_mounted, on_unmounted, on_updated

@ft.component
def MyComponent():
    status, set_status = ft.use_state("idle")

    # Run ONCE on mount
    async def on_mount():
        set_status("mounted")
        await connect()

    on_mounted(on_mount)

    # Run ONCE on unmount
    def on_unmount():
        disconnect()

    on_unmounted(on_unmount)

    # Run after every re-render
    def on_update():
        logger.debug(f"Re-render: status={status}")

    on_updated(on_update)

    return ft.Text(f"Status: {status}")
```

**Equivalences:**

```python
on_mounted(fn)              # = use_effect(fn, dependencies=[])
on_unmounted(fn)            # = use_effect(lambda: None, dependencies=[], cleanup=fn)
on_updated(fn)              # = use_effect(fn, dependencies=None)
on_updated(fn, deps=[x,y]) # = use_effect(fn, dependencies=[x,y])
```

### use_context / create_context

```python
# Definition — typically in context.py
from dataclasses import dataclass
import flet as ft

@dataclass
class AppContext:
    state: AppState
    service: MyService

AppCtx = ft.create_context(None)  # None = default when no provider
```

```python
# Provider — in App component
@ft.component
def App(state, service):
    ctx = AppContext(state=state, service=service)
    # AppCtx(value, builder) — provides to entire subtree
    return AppCtx(ctx, lambda: ft.View(controls=[PageContent()]))
```

```python
# Consumer — in any child component
@ft.component
def MyPage():
    ctx = ft.use_context(AppCtx)  # Gets value from nearest provider
    state = ctx.state
    service = ctx.service
    # Auto-subscribes: if ctx is Observable, component re-renders
```

### use_memo

```python
@ft.component
def FilteredList(items: list[str], filter_text: str):
    # Recomputes ONLY when items or filter_text change
    filtered = ft.use_memo(
        lambda: [i for i in items if filter_text.lower() in i.lower()],
        [items, filter_text],
    )

    # No deps = compute only on mount
    initial_config = ft.use_memo(lambda: compute_expensive_config())

    return ft.Column([ft.Text(item) for item in filtered])
```

### use_callback

```python
@ft.component
def MyComponent(on_change):
    value, set_value = ft.use_state("")

    # Memoize function identity — useful when passing to child components
    # that only re-render when their props change
    handler = ft.use_callback(
        lambda e: set_value(e.control.value),
        [set_value],
    )

    return ft.TextField(value=value, on_change=handler)
```

**Implementation:** `use_callback(fn, deps)` = `use_memo(lambda: fn, deps)`

### use_ref

```python
@ft.component
def MyComponent():
    # Mutable reference that does NOT trigger re-render when changed
    click_count = ft.use_ref()
    click_count.current = 0

    def silent_increment(e):
        click_count.current += 1
        print(f"Clicks: {click_count.current}")

    return ft.IconButton(ft.Icons.ADD, on_click=silent_increment)
```

**Lazy initialization (0.81.0):**

```python
@ft.component
def MyComponent():
    config_ref = ft.use_ref(lambda: load_expensive_config())
    print(config_ref.current)  # Result of the callable
```

### use_dialog (0.85.0+)

Reactive hook that portals a `DialogControl` to the page's dialog overlay. Call it on
**every render** with either a dialog instance (to show) or `None` (to hide).

```python
@ft.component
def DeleteConfirmation():
    show, set_show = ft.use_state(False)

    def confirm(e):
        set_show(False)
        # ... perform delete

    def cancel(e):
        set_show(False)

    # Build dialog only when showing; pass None to dismiss
    ft.use_dialog(
        ft.AlertDialog(
            title=ft.Text("Delete?"),
            content=ft.Text("This cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=cancel),
                ft.FilledButton("Delete", on_click=confirm),
            ],
        ) if show else None
    )

    return ft.FilledButton("Delete", on_click=lambda _: set_show(True))
```

**Behavior:**

- The hook sets `open=True` automatically when adding to overlay
- Passing `None` or unmounting the component dismisses with `open=False`
- Re-rendering with a new dialog of the **same type** runs a frozen diff that
  preserves Flutter widget identity (e.g., `TextField` keeps cursor/focus,
  selection, scroll position) across re-renders
- Re-rendering with a different dialog type creates a fresh entry — no state
  carries over

**Use vs. imperative API:**

| Context | Use |
|---------|-----|
| Inside `@ft.component` declarative tree | `ft.use_dialog(dialog)` |
| Imperative `main(page)` body / event handler outside component | `page.show_dialog(dialog)` / `page.pop_dialog()` |

### Hook Rules

1. **Only inside `@ft.component`** — never in regular functions
2. **Fixed order between re-renders** — never inside `if` / `for`
3. **`use_effect` cleanup is a separate parameter** — not return value
4. **`use_state` setter accepts lambda** — to avoid stale closure in async
5. **`use_context` auto-subscribes if Observable** — no extra code needed
6. **`use_ref` accepts callable** (0.81.0) — for lazy initialization
7. **`@ft.component` accepts `key`** (0.81.0) — `MyComp(key="id")` for reconciliation
8. **`use_dialog` must be called every render** (0.85.0) — pass `None` to dismiss; do NOT wrap in `if`

```python
# WRONG: hook inside conditional
@ft.component
def Comp(show):
    if show:
        value, set_value = ft.use_state(0)  # Order breaks between renders

# WRONG: hook outside @ft.component
def regular_function():
    value, set_value = ft.use_state(0)  # RuntimeError
```

---

## Component Patterns

### @ft.component — Functional Component

```python
import flet as ft

@ft.component
def MyComponent(title: str, subtitle: str = ""):
    """
    Functional declarative component.
    - Receives props as parameters
    - Returns Flet controls
    - Re-renders automatically when props or dependent state changes
    """
    return ft.Column([
        ft.Text(title, size=24, weight=ft.FontWeight.BOLD),
        ft.Text(subtitle, size=14, color=ft.Colors.GREY_700),
    ])

# Usage
MyComponent(title="Hello", subtitle="World")
```

### Page Component Pattern

```python
# pages/login.py
import flet as ft
from context import AppCtx


@ft.component
def LoginPage():
    """
    Page with local state for form fields.
    Pattern:
    1. use_context for state + services
    2. use_state for form fields (avoids global re-render)
    3. Async handlers for service operations
    4. Return ft.Column with scroll
    """
    ctx = ft.use_context(AppCtx)
    state = ctx.state
    service = ctx.service

    # LOCAL state (not observable) for input fields
    username, set_username = ft.use_state("")

    async def handle_login(e):
        if not username:
            state.add_log("Please enter username", "warning")
            return
        try:
            await service.login(username)
            state.add_log(f"Login successful: {username}", "success")
        except Exception as ex:
            state.add_log(f"Login error: {ex}", "error")

    async def handle_logout(e):
        try:
            await service.logout()
            set_username("")
            state.add_log("Logged out", "success")
        except Exception as ex:
            state.add_log(f"Logout error: {ex}", "error")

    return ft.Column(
        [
            ft.Text("Login / Logout", size=24, weight=ft.FontWeight.BOLD),
            ft.Text(
                "Associate device with user via External ID.",
                size=14,
                color=ft.Colors.GREY_700,
            ),
            ft.Divider(height=20),
            ft.TextField(
                label="Username",
                hint_text="e.g., user-123",
                value=username,
                on_change=lambda e: set_username(e.control.value),
            ),
            ft.Row(
                [
                    ft.FilledButton("Login", icon=ft.Icons.LOGIN, on_click=handle_login),
                    ft.OutlinedButton("Logout", icon=ft.Icons.LOGOUT, on_click=handle_logout),
                ],
                spacing=10,
            ),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
```

### Reusable Component with Context

```python
# components/log_viewer.py
import flet as ft
from context import AppCtx


LOG_COLORS = {
    "success": ft.Colors.GREEN_700,
    "error": ft.Colors.RED_700,
    "warning": ft.Colors.ORANGE_700,
    "info": ft.Colors.BLUE_700,
    "debug": ft.Colors.GREY_600,
}


@ft.component
def LogViewer():
    """Reusable log viewer. Re-renders when state.logs changes."""
    ctx = ft.use_context(AppCtx)
    state = ctx.state

    async def copy_logs(e):
        text = "\n".join(
            f"[{log.time}] [{log.level.upper()}] {log.message}"
            for log in state.logs
        )
        if text:
            await ctx.clipboard.set(text)
            state.add_log("Logs copied", "success")

    def clear_logs(e):
        state.clear_logs()

    entries = [
        ft.Text(
            f"[{log.time}] {log.message}",
            size=12,
            color=LOG_COLORS.get(log.level, ft.Colors.GREY_800),
            selectable=True,
        )
        for log in state.logs
    ]

    return ft.Column([
        ft.Row(
            [
                ft.Text("Output", weight=ft.FontWeight.W_600),
                ft.Row(
                    [
                        ft.IconButton(icon=ft.Icons.COPY, tooltip="Copy", on_click=copy_logs),
                        ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, tooltip="Clear", on_click=clear_logs),
                    ],
                    spacing=0,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        ft.Container(
            content=ft.Column(
                controls=entries if entries else [
                    ft.Text("No logs.", size=12, italic=True, color=ft.Colors.GREY_500),
                ],
                scroll=ft.ScrollMode.AUTO,
                auto_scroll=True,
                spacing=4,
            ),
            border=ft.Border.all(1, ft.Colors.GREY_300),
            border_radius=8,
            padding=12,
            height=200,
            bgcolor=ft.Colors.GREY_50,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            expand=True,
        ),
    ])
```

### Factory Function for Handlers in Loops

```python
# WRONG: Closure captures mutable variable
for item in items:
    btn = ft.Button(item["label"], on_click=lambda e: print(item["id"]))
    # All buttons print the LAST item["id"]

# CORRECT: Factory function captures value by parameter
def make_handler(page_id: str):
    def handler(e):
        state.navigate(page_id)
    return handler

for item in items:
    btn = ft.Button(item["label"], on_click=make_handler(item["id"]))
    # Each button has its own page_id captured
```

### Async Operation Pattern

```python
@ft.component
def OperationPage():
    ctx = ft.use_context(AppCtx)
    state = ctx.state
    service = ctx.service

    field_a, set_field_a = ft.use_state("")
    field_b, set_field_b = ft.use_state("")

    async def handle_submit(e):
        if not field_a:
            state.add_log("Field A is required", "warning")
            return
        try:
            result = await service.operation(field_a, field_b)
            state.add_log(f"Result: {result}", "success")
        except Exception as ex:
            state.add_log(f"Error: {ex}", "error")

    return ft.Column(
        [
            ft.Text("Operation", size=24, weight=ft.FontWeight.BOLD),
            ft.TextField(
                label="Field A",
                value=field_a,
                on_change=lambda e: set_field_a(e.control.value),
            ),
            ft.TextField(
                label="Field B",
                value=field_b,
                on_change=lambda e: set_field_b(e.control.value),
            ),
            ft.Row(
                [
                    ft.FilledButton("Execute", on_click=handle_submit),
                ],
                spacing=10,
                wrap=True,
            ),
            ft.Divider(height=20),
            LogViewer(),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
```

---

## Navigation

### State-Based Routing (Mobile Apps)

Best for mobile apps with drawers/tabs where URLs are not needed.

```python
# state.py
@ft.observable
@dataclass
class AppState:
    current_page: str = "login"

    def navigate(self, page_id: str) -> None:
        self.current_page = page_id


# pages/__init__.py
PAGE_BUILDERS = {
    "login":         LoginPage,
    "notifications": NotificationsPage,
    "settings":      SettingsPage,
}


# main.py
@ft.component
def PageContent():
    ctx = ft.use_context(AppCtx)
    state = ctx.state
    builder = PAGE_BUILDERS.get(state.current_page, PAGE_BUILDERS["login"])
    return ft.Container(content=builder(), expand=True, padding=20)
```

### `ft.Router` — Declarative Router (Recommended for 0.85.x+)

Flet 0.85.0 introduced **`ft.Router`**, a React Router–style declarative router with
nested routes, layout outlets, dynamic segments, per-route data loaders, and a mobile
view-stack mode for swipe-back gestures and system back-button.

```python
import flet as ft


# Route components — plain @ft.component functions
@ft.component
def Home():
    return ft.Column([
        ft.Text("Home", size=24),
        ft.FilledButton("Products", on_click=lambda _: ft.context.page.navigate("/products")),
    ])


@ft.component
def ProductDetails():
    params = ft.use_route_params()
    return ft.Text(f"Product {params['pid']}")


@ft.component
def NotFound():
    return ft.Text("404 — Not Found")


@ft.component
def App():
    return ft.Router(
        [
            ft.Route(index=True, component=Home),
            ft.Route(path="about", component=About),
            ft.Route(path="products/:pid", component=ProductDetails),
        ],
        not_found=NotFound,
    )


def main(page: ft.Page):
    page.title = "Router Demo"
    page.render(App)


ft.run(main)
```

#### Route definition

```python
ft.Route(
    path="users/:uid(\\d+)",  # dynamic + regex constraint
    component=UserPage,
    loader=lambda params: fetch_user(params["uid"]),  # data loader
    children=[                                           # nested routes
        ft.Route(index=True, component=UserOverview),
        ft.Route(path="posts/:post_id?", component=PostList),  # optional segment
        ft.Route(path="files/:rest*", component=FileBrowser),   # splat
    ],
)
```

Segment forms:

| Form | Example | Matches |
|------|---------|---------|
| Dynamic | `:id` | `42`, `abc` |
| Optional | `:id?` | present or absent |
| Splat | `:rest*` | rest of path |
| Regex | `:id(\\d+)` | digits only |

#### Router hooks

| Hook | Purpose |
|------|---------|
| `use_route_params()` | Dict of dynamic segment values |
| `use_route_location()` | Current URL pathname |
| `use_view_path()` | Resolved URL for the current view level (use as `View.route` in `manage_views=True`) |
| `use_route_outlet()` | Returns the matched child component — call inside a layout route's component |
| `use_route_loader_data()` | Returns the value returned by this route's `loader` |
| `is_route_active(path, exact=False)` | True if `path` matches current location (prefix match by default) |

All hooks return safe defaults (`{}`, `""`, `None`, `False`) when called outside a
`Router` tree — useful during stale re-renders.

#### Layout routes with outlets

```python
@ft.component
def Layout():
    return ft.Column([
        ft.AppBar(title=ft.Text("App")),
        ft.use_route_outlet(),  # renders the matched child
    ])


ft.Router([
    ft.Route(component=Layout, children=[
        ft.Route(index=True, component=Home),
        ft.Route(path="about", component=About),
    ]),
])
```

#### Mobile view-stack mode (`manage_views=True`)

Produces a list of `View`s (one per path level) instead of a single component tree.
Enables native swipe-back gesture, system back button, and `AppBar` implicit back arrow.
**Must be used with `page.render_views(App)`** (not `page.render(App)`).

Route components must return `ft.View(...)` with `route` set (use `use_view_path()` for
a unique Navigator key per stack level).

```python
@ft.component
def ProductDetailsView():
    params = ft.use_route_params()
    return ft.View(
        route=ft.use_view_path(),
        appbar=ft.AppBar(title=ft.Text(f"Product {params['pid']}")),
        controls=[ft.Text("Details here")],
    )


@ft.component
def App():
    return ft.Router(
        [
            ft.Route(index=True, component=HomeView),
            ft.Route(path="products/:pid", component=ProductDetailsView),
        ],
        manage_views=True,
    )


def main(page: ft.Page):
    page.render_views(App)
```

`Route(outlet=True)` makes a layout route wrap its child as an outlet within a single
`View` (instead of each child producing its own `View`).

---

### Page navigation methods (0.85.x)

```python
# Async — push a new route
await page.push_route("/products/42")

# Sync wrapper — use in on_click and other sync callbacks
page.navigate("/products/42")

# Pop until a target view + deliver result
await page.pop_views_until("/", result="Done!")
# Listen for the result on the destination view:
page.on_views_pop_until = lambda e: print(e.result, e.view)
```

`page.go()` is **deprecated since 0.80.0** (removal in 0.90.0) — use `push_route` /
`navigate` instead.

---

### Imperative Router-Based Routing (legacy / fine-grained control)

If `ft.Router` doesn't fit (e.g., dynamic route table from a database), the old
`page.views` + `on_route_change` pattern still works.

```python
import flet as ft


def main(page: ft.Page):
    page.title = "Router Demo"

    def route_change(e: ft.RouteChangeEvent):
        """Rebuild page.views based on new route."""
        page.views.clear()

        # Root — always present in stack
        page.views.append(
            ft.View(
                route="/",
                controls=[
                    ft.AppBar(title=ft.Text("Home")),
                    ft.Text("Welcome!", size=24),
                    ft.FilledButton(
                        "Go to Store",
                        on_click=lambda _: page.navigate("/store"),
                    ),
                ],
            )
        )

        if page.route == "/store":
            page.views.append(
                ft.View(
                    route="/store",
                    controls=[
                        ft.AppBar(title=ft.Text("Store")),
                        ft.Text("Available products"),
                    ],
                )
            )

        page.update()

    def view_pop(e: ft.ViewPopEvent):
        """Called when user presses Back."""
        page.views.pop()
        top_view = page.views[-1]
        page.navigate(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.navigate(page.route)


ft.run(main)
```

### TemplateRoute — Routes with Parameters

```python
def route_change(e: ft.RouteChangeEvent):
    page.views.clear()
    troute = ft.TemplateRoute(page.route)

    if troute.match("/"):
        page.views.append(HomeView())
    elif troute.match("/books/:id"):
        book_id = troute.id  # Extracted automatically
        page.views.append(BookDetailView(book_id=book_id))
    elif troute.match("/accounts/:account_id/orders/:order_id"):
        page.views.append(OrderDetailView(troute.account_id, troute.order_id))
    else:
        page.views.append(NotFoundView())

    page.update()
```

### Declarative Router with Observable State

```python
import flet as ft
from dataclasses import dataclass


@ft.observable
@dataclass
class RouterState:
    route: str = "/"

    def go(self, route: str) -> None:
        self.route = route


RouterCtx = ft.create_context(None)


@ft.component
def HomePage():
    state = ft.use_context(RouterCtx)
    return ft.Column([
        ft.Text("Home", size=24, weight=ft.FontWeight.BOLD),
        ft.FilledButton("Go to About", on_click=lambda _: state.go("/about")),
    ], spacing=12, padding=20)


@ft.component
def AboutPage():
    state = ft.use_context(RouterCtx)
    return ft.Column([
        ft.Text("About", size=24, weight=ft.FontWeight.BOLD),
        ft.OutlinedButton("Back", icon=ft.Icons.ARROW_BACK, on_click=lambda _: state.go("/")),
    ], spacing=12, padding=20)


@ft.component
def RouterApp(router_state):
    ROUTES = {"/": HomePage, "/about": AboutPage}
    builder = ROUTES.get(router_state.route, HomePage)

    def build_view():
        return ft.View(
            controls=[
                ft.AppBar(title=ft.Text("Router Demo"), bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
                ft.Container(content=builder(), expand=True),
            ],
            padding=0,
        )

    return RouterCtx(router_state, build_view)


def main(page: ft.Page):
    page.title = "Router Demo"
    page.route_url_strategy = "path"  # "path" for clean URLs, "hash" for static hosting

    router_state = RouterState()

    def on_route_change(e: ft.RouteChangeEvent):
        router_state.route = e.route

    page.on_route_change = on_route_change
    router_state.route = page.route

    page.render_views(RouterApp, router_state)


ft.run(main)
```

### NavigationDrawer on View

```python
@ft.component
def App(state, service, clipboard):
    ctx = AppContext(state=state, service=service, clipboard=clipboard)

    # Mutable list as ref — needed for async closures
    view_ref = [None]

    async def on_menu_click(e):
        # BUG: page.show_drawer() fails with render_views()
        # page.views becomes a Component (no len()) → TypeError
        # SOLUTION: call show_drawer() directly on the View
        if view_ref[0]:
            await view_ref[0].show_drawer()

    def build_view():
        view_ref[0] = ft.View(
            controls=[PageContent()],
            appbar=ft.AppBar(
                leading=ft.IconButton(
                    icon=ft.Icons.MENU,
                    on_click=on_menu_click,
                ),
                title=ft.Text("My App"),
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
            ),
            drawer=ft.NavigationDrawer(
                controls=[AppDrawer()],
                on_dismiss=lambda e: None,
            ),
            padding=0,
            bgcolor=ft.Colors.WHITE,
        )
        return view_ref[0]

    return AppCtx(ctx, build_view)
```

### AppDrawer with Navigation Groups

```python
# config.py
NAVIGATION_GROUPS = [
    {
        "title": "Account",
        "items": [
            {"id": "login", "label": "Login / Logout", "icon": ft.Icons.PERSON},
        ],
    },
    {
        "title": "Features",
        "items": [
            {"id": "notifications", "label": "Notifications", "icon": ft.Icons.NOTIFICATIONS},
            {"id": "settings", "label": "Settings", "icon": ft.Icons.SETTINGS},
        ],
    },
]


# components/drawer.py
@ft.component
def AppDrawer():
    ctx = ft.use_context(AppCtx)
    state = ctx.state

    def create_handler(page_id: str):
        """Factory to avoid incorrect closure in loop."""
        def handler(e):
            state.navigate(page_id)
        return handler

    items = []
    for group in NAVIGATION_GROUPS:
        items.append(
            ft.Container(
                content=ft.Text(
                    group["title"],
                    size=12,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.GREY_600,
                ),
                padding=ft.Padding.only(left=16, top=16, bottom=4),
            )
        )
        for item in group["items"]:
            selected = state.current_page == item["id"]
            items.append(
                ft.ListTile(
                    leading=ft.Icon(
                        item["icon"],
                        color=ft.Colors.BLUE_700 if selected else ft.Colors.GREY_700,
                    ),
                    title=ft.Text(
                        item["label"],
                        weight=ft.FontWeight.W_500 if selected else ft.FontWeight.NORMAL,
                        color=ft.Colors.BLUE_700 if selected else None,
                    ),
                    selected=selected,
                    on_click=create_handler(item["id"]),
                )
            )

    items.append(ft.Divider())
    return ft.Column(controls=items, scroll=ft.ScrollMode.AUTO, spacing=0)
```

---

## Core Controls Quick Reference

### Layout Controls

| Control | Description | Key Props |
|---------|-------------|-----------|
| `ft.Column` | Vertical stack | `spacing`, `scroll`, `expand`, `alignment` |
| `ft.Row` | Horizontal stack | `spacing`, `wrap`, `alignment`, `vertical_alignment` |
| `ft.Stack` | Z-axis stacking | `controls` (positioned with `ft.Positioned`) |
| `ft.Container` | Box with styling | `content`, `padding`, `bgcolor`, `border`, `border_radius` |
| `ft.ListView` | Scrollable list | `controls`, `spacing`, `auto_scroll` |
| `ft.GridView` | Grid layout | `controls`, `runs_count`, `spacing`, `run_spacing` |
| `ft.Wrap` | Flow layout | `controls`, `spacing`, `run_spacing` |
| `ft.ResponsiveRow` | Responsive grid | `controls` with `col` property for breakpoints |
| `ft.Divider` | Horizontal line | `height`, `thickness`, `color` |
| `ft.Card` | Material card | `content`, `elevation` |

### Input Controls

| Control | Description | Key Props |
|---------|-------------|-----------|
| `ft.TextField` | Text input | `label`, `value`, `on_change`, `hint_text`, `password` |
| `ft.Dropdown` | Select dropdown | `options`, `value`, `on_change`, `label` |
| `ft.Checkbox` | Checkbox | `value`, `on_change`, `label` |
| `ft.Switch` | Toggle switch | `value`, `on_change`, `label` |
| `ft.Slider` | Range slider | `value`, `min`, `max`, `on_change`, `divisions` |
| `ft.DatePicker` | Date selector | `value`, `on_change` |
| `ft.Radio` + `ft.RadioGroup` | Radio buttons | `value`, `on_change` |

### Button Controls

| Control | Description | Key Props |
|---------|-------------|-----------|
| `ft.FilledButton` | Primary button | `text`, `on_click`, `icon`, `disabled` |
| `ft.OutlinedButton` | Secondary button | `text`, `on_click`, `icon` |
| `ft.TextButton` | Text-only button | `text`, `on_click`, `icon` |
| `ft.IconButton` | Icon-only button | `icon`, `on_click`, `tooltip` |
| `ft.FloatingActionButton` | FAB | `icon`, `on_click` |

### Display Controls

| Control | Description | Key Props |
|---------|-------------|-----------|
| `ft.Text` | Text display | `value`, `size`, `weight`, `color`, `selectable` |
| `ft.Icon` | Material icon | `name` (ft.Icons.NAME), `size`, `color` |
| `ft.Image` | Image display | `src`, `width`, `height`, `fit` |
| `ft.ProgressBar` | Linear progress | `value` (0-1), `color` |
| `ft.ProgressRing` | Circular progress | `value` (0-1 or None for indeterminate) |

### Navigation Controls

| Control | Description | Key Props |
|---------|-------------|-----------|
| `ft.AppBar` | Top app bar | `title`, `leading`, `actions`, `bgcolor` |
| `ft.NavigationDrawer` | Side drawer | `controls`, `on_dismiss` |
| `ft.BottomNavigationBar` | Bottom tabs | `destinations`, `selected_index`, `on_change` |
| `ft.Tabs` | Tab bar | `tabs`, `selected_index`, `on_change` |

---

## Styling & Theming

### Theme Configuration

```python
def main(page: ft.Page):
    # Color scheme from seed color
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE)

    # Or explicit color scheme
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=ft.Colors.BLUE,
            secondary=ft.Colors.AMBER,
        )
    )

    # Theme mode
    page.theme_mode = ft.ThemeMode.LIGHT  # LIGHT, DARK, SYSTEM
```

### Colors (Uppercase Constants)

```python
# CORRECT (0.80.x+)
ft.Colors.BLUE
ft.Colors.RED_700
ft.Colors.GREY_50

# WRONG (old style)
ft.colors.BLUE  # Lowercase — deprecated
```

### Container Styling

```python
ft.Container(
    content=ft.Text("Styled box"),
    width=300,
    height=200,
    padding=20,
    margin=10,
    bgcolor=ft.Colors.BLUE_50,
    border=ft.Border.all(2, ft.Colors.BLUE_200),
    border_radius=12,
    alignment=ft.Alignment.CENTER,
    gradient=ft.LinearGradient(
        begin=ft.Alignment.TOP_LEFT,
        end=ft.Alignment.BOTTOM_RIGHT,
        colors=[ft.Colors.BLUE_100, ft.Colors.PURPLE_100],
    ),
    shadow=ft.BoxShadow(
        spread_radius=1,
        blur_radius=10,
        color=ft.Colors.with_opacity(0.3, ft.Colors.GREY),
        offset=ft.Offset(2, 2),
    ),
)
```

### Text Styling

```python
ft.Text(
    "Hello World",
    size=24,
    weight=ft.FontWeight.BOLD,  # W_100..W_900, BOLD, NORMAL
    color=ft.Colors.BLUE_700,
    italic=True,
    text_align=ft.TextAlign.CENTER,
    selectable=True,
    style=ft.TextStyle(
        decoration=ft.TextDecoration.UNDERLINE,
        letter_spacing=1.5,
    ),
)
```

---

## Async Patterns

### Async Main

```python
async def main(page: ft.Page):
    page.title = "Async App"

    # Await service initialization
    data = await fetch_initial_data()

    page.add(ft.Text(f"Loaded: {len(data)} items"))

ft.run(main)
```

### Background Tasks

```python
@ft.component
def DataLoader():
    data, set_data = ft.use_state(None)
    loading, set_loading = ft.use_state(True)

    async def load():
        set_loading(True)
        result = await api.fetch_data()
        set_data(result)
        set_loading(False)

    ft.use_effect(load, [])  # Run on mount

    if loading:
        return ft.Column([
            ft.ProgressRing(),
            ft.Text("Loading..."),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    return ft.Column([
        ft.Text(f"Loaded {len(data)} items"),
        *[ft.Text(item) for item in data],
    ])
```

### Progress During Operations

```python
@ft.component
def UploadPage():
    ctx = ft.use_context(AppCtx)
    progress, set_progress = ft.use_state(0.0)
    uploading, set_uploading = ft.use_state(False)

    async def handle_upload(e):
        set_uploading(True)
        for i in range(100):
            await asyncio.sleep(0.05)
            set_progress((i + 1) / 100)
        set_uploading(False)
        ctx.state.add_log("Upload complete!", "success")

    return ft.Column([
        ft.FilledButton("Upload", on_click=handle_upload, disabled=uploading),
        ft.ProgressBar(value=progress if uploading else 0),
        ft.Text(f"{int(progress * 100)}%" if uploading else "Ready"),
    ])
```

---

## Anti-Patterns

### Entry Point & Rendering

```python
# WRONG: old entry point
ft.app(target=main)
# CORRECT:
ft.run(main)

# WRONG: calling component when passing to render
page.render(Counter())   # RuntimeError: No current renderer
# CORRECT: pass reference
page.render(Counter)

# WRONG: imperative mode
page.add(btn)
btn.text = "Changed"
page.update()
# CORRECT: declarative mode
@ft.component
def MyApp():
    clicked, set_clicked = ft.use_state(False)
    return ft.FilledButton(
        "Clicked" if clicked else "Click",
        on_click=lambda _: set_clicked(True),
    )
page.render(MyApp)

# WRONG: manual page.update() in declarative mode
state.current_page = "home"
page.update()  # Unnecessary, may cause issues
# CORRECT: observable handles it
state.current_page = "home"  # Auto re-render
```

### State

```python
# WRONG: @dataclass before @ft.observable
@dataclass
@ft.observable
class AppState:
    count: int = 0
# CORRECT:
@ft.observable
@dataclass
class AppState:
    count: int = 0

# WRONG: observable for form input (global re-render per keystroke)
@ft.observable
@dataclass
class FormState:
    text: str = ""
# CORRECT: use_state for form fields
text, set_text = ft.use_state("")

# WRONG: direct element mutation (no notification)
state.items[0] = "new"
# CORRECT: use methods that trigger notification
state.items.clear()
state.items.append("new")
# or reassign entirely
state.items = ["new"]
```

### Hooks

```python
# WRONG: hook inside conditional
@ft.component
def Comp(show):
    if show:
        v, set_v = ft.use_state(0)  # Order breaks
# CORRECT: all hooks at top
@ft.component
def Comp(show):
    v, set_v = ft.use_state(0)
    if not show:
        return ft.Text("Hidden")
    return ft.Text(str(v))

# WRONG: cleanup as return (React pattern — IGNORED in Flet)
def setup():
    timer.start()
    return lambda: timer.stop()
ft.use_effect(setup, [])
# CORRECT: cleanup as separate parameter
ft.use_effect(
    setup=lambda: timer.start(),
    dependencies=[],
    cleanup=lambda: timer.stop(),
)
```

### Navigation

```python
# WRONG: page.show_drawer() with render_views()
await page.show_drawer()  # TypeError: len(Component)
# CORRECT: view_ref pattern
view_ref = [None]
# ... build_view sets view_ref[0] = ft.View(...)
if view_ref[0]:
    await view_ref[0].show_drawer()

# WRONG: not clearing views in router
def route_change(e):
    page.views.append(ft.View(...))  # Views accumulate
# CORRECT:
def route_change(e):
    page.views.clear()
    page.views.append(ft.View(route="/", ...))
    if page.route == "/store":
        page.views.append(ft.View(route="/store", ...))
    page.update()
```

### Context & Scheduler

```python
# WRONG: accessing context without guard — crashes scheduler permanently
@ft.component
def MyPage():
    ctx = ft.use_context(AppCtx)
    state = ctx.state  # AttributeError if ctx is None → scheduler dies → UI freezes

# CORRECT: always guard use_context
@ft.component
def MyPage():
    ctx = ft.use_context(AppCtx)
    if ctx is None:
        return ft.Container()  # Stale component, skip safely
    state = ctx.state

# WRONG: force re-render by setting same value (no-op)
state.detail_name = state.detail_name  # value_equal → True → no notification

# CORRECT: use notify() to force re-render
state.notify()  # Always fires _notify(None) → all listeners re-render
```

### Common Errors Table

| Error | Cause | Solution |
|-------|-------|---------|
| `RuntimeError: No current renderer` | `page.render(Counter())` — called component | `page.render(Counter)` — pass reference |
| `TypeError: len(Component)` | `page.show_drawer()` with `render_views()` | `view_ref[0].show_drawer()` |
| All clicks navigate to same item | Closure in loop | Factory function `make_handler(id)` |
| Observable doesn't notify | `items[0] = x` on list | `.append()` / `.clear()` / reassign |
| Hook outside component | `use_state` in regular function | Move to `@ft.component` |
| Global re-render per keystroke | `@ft.observable` for form input | `ft.use_state` for form fields |
| `use_effect` cleanup ignored | Returning cleanup function | Use `cleanup=` parameter |
| **UI freezes permanently** | `use_context()` returns `None` on stale component → `AttributeError` crashes scheduler | `if ctx is None: return ft.Container()` guard after every `use_context()` |
| Observable same-value no-op | `state.x = state.x` — `value_equal` skips it | Use `state.notify()` to force re-render |
| **Scheduler silently dead** | Any uncaught exception in `Component.update()` kills `__updates_scheduler` | Wrap `schedule_update` to auto-restart scheduler on crash |

---

## Complete App Template

### config.py

```python
"""App constants — no logic, only data."""
import flet as ft

APP_TITLE = "My App"

NAVIGATION_GROUPS = [
    {
        "title": "Main",
        "items": [
            {"id": "home", "label": "Home", "icon": ft.Icons.HOME},
            {"id": "counter", "label": "Counter", "icon": ft.Icons.ADD_CIRCLE},
        ],
    },
    {
        "title": "Settings",
        "items": [
            {"id": "settings", "label": "Settings", "icon": ft.Icons.SETTINGS},
        ],
    },
]
```

### state.py

```python
"""Global observable app state."""
from dataclasses import dataclass, field
from datetime import datetime
import flet as ft


@dataclass
class Notification:
    message: str
    level: str  # "success", "error", "info", "warning"
    time: str


@ft.observable
@dataclass
class AppState:
    current_page: str = "home"
    dark_theme: bool = False
    user_name: str = ""
    notifications: list[Notification] = field(default_factory=list)

    def navigate(self, page_id: str) -> None:
        self.current_page = page_id

    def toggle_theme(self) -> None:
        self.dark_theme = not self.dark_theme

    def notify(self, message: str, level: str = "info") -> None:
        self.notifications.append(Notification(
            message=message,
            level=level,
            time=datetime.now().strftime("%H:%M:%S"),
        ))

    def clear_notifications(self) -> None:
        self.notifications.clear()
```

### context.py

```python
"""Shared context via create_context."""
from dataclasses import dataclass
import flet as ft
from state import AppState


@dataclass
class AppContext:
    state: AppState


AppCtx = ft.create_context(None)
```

### pages/__init__.py

```python
"""Page registry."""
from pages.counter import CounterPage
from pages.home import HomePage
from pages.settings import SettingsPage

PAGE_BUILDERS = {
    "home": HomePage,
    "counter": CounterPage,
    "settings": SettingsPage,
}
```

### pages/home.py

```python
"""Home page — demonstrates use_context."""
import flet as ft
from context import AppCtx


@ft.component
def HomePage():
    ctx = ft.use_context(AppCtx)
    state = ctx.state

    name = state.user_name or "visitor"

    return ft.Column(
        [
            ft.Text(f"Hello, {name}!", size=28, weight=ft.FontWeight.BOLD),
            ft.Text(
                "Welcome to the Flet 0.83.x demo app.",
                size=14,
                color=ft.Colors.GREY_700,
            ),
            ft.Divider(height=20),
            ft.Text("Patterns demonstrated:", weight=ft.FontWeight.W_500),
            ft.Column(
                [
                    ft.Text("- @ft.component — functional components"),
                    ft.Text("- @ft.observable — global reactive state"),
                    ft.Text("- ft.use_state — local form state"),
                    ft.Text("- ft.create_context / use_context — dependency injection"),
                    ft.Text("- on_mounted — side effect on mount"),
                    ft.Text("- NavigationDrawer — side navigation"),
                ],
                spacing=6,
            ),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
```

### pages/counter.py

```python
"""Counter page — demonstrates use_state, on_mounted, use_effect."""
import flet as ft
from context import AppCtx
from flet.components.hooks.use_effect import on_mounted


@ft.component
def CounterPage():
    ctx = ft.use_context(AppCtx)
    state = ctx.state

    count, set_count = ft.use_state(0)
    step, set_step = ft.use_state(1)

    def on_mount():
        state.notify("Counter page opened", "info")

    on_mounted(on_mount)

    def check_milestone():
        if count > 0 and count % 10 == 0:
            state.notify(f"Milestone reached: {count}!", "success")

    ft.use_effect(check_milestone, [count])

    def increment(e):
        set_count(lambda prev: prev + step)

    def decrement(e):
        set_count(lambda prev: max(0, prev - step))

    def reset(e):
        set_count(0)
        state.notify("Counter reset", "warning")

    return ft.Column(
        [
            ft.Text("Counter", size=24, weight=ft.FontWeight.BOLD),
            ft.Container(
                content=ft.Text(str(count), size=64, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                alignment=ft.Alignment.CENTER,
                height=100,
            ),
            ft.Row(
                [
                    ft.FilledButton("-", on_click=decrement, style=ft.ButtonStyle(bgcolor=ft.Colors.RED_400)),
                    ft.FilledButton("+", on_click=increment, style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_400)),
                    ft.OutlinedButton("Reset", on_click=reset),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=12,
            ),
            ft.Row(
                [
                    ft.Text("Step:", weight=ft.FontWeight.W_500),
                    ft.TextField(
                        value=str(step),
                        width=80,
                        text_align=ft.TextAlign.CENTER,
                        on_change=lambda e: set_step(
                            int(e.control.value) if e.control.value.isdigit() else 1
                        ),
                    ),
                ],
                spacing=10,
            ),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
```

### pages/settings.py

```python
"""Settings page — demonstrates editing observable state."""
import flet as ft
from context import AppCtx


@ft.component
def SettingsPage():
    ctx = ft.use_context(AppCtx)
    state = ctx.state

    name_input, set_name_input = ft.use_state(state.user_name)

    def save_name(e):
        state.user_name = name_input
        state.notify(f"Name saved: {name_input}", "success")

    return ft.Column(
        [
            ft.Text("Settings", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(height=20),
            ft.Text("Profile", weight=ft.FontWeight.W_500),
            ft.Row(
                [
                    ft.TextField(
                        label="Name",
                        hint_text="Your name",
                        value=name_input,
                        expand=True,
                        on_change=lambda e: set_name_input(e.control.value),
                    ),
                    ft.FilledButton("Save", on_click=save_name),
                ],
                spacing=10,
            ),
            ft.Divider(height=20),
            ft.Text("Appearance", weight=ft.FontWeight.W_500),
            ft.Row(
                [
                    ft.Text("Dark theme"),
                    ft.Switch(
                        value=state.dark_theme,
                        on_change=lambda e: state.toggle_theme(),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
```

### components/drawer.py

```python
"""Navigation drawer component."""
import flet as ft
from config import NAVIGATION_GROUPS
from context import AppCtx


@ft.component
def AppDrawer():
    ctx = ft.use_context(AppCtx)
    state = ctx.state

    def create_handler(page_id: str):
        def handler(e):
            state.navigate(page_id)
        return handler

    items = []
    for group in NAVIGATION_GROUPS:
        items.append(ft.Container(
            content=ft.Text(group["title"], size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600),
            padding=ft.Padding.only(left=16, top=16, bottom=4),
        ))
        for item in group["items"]:
            sel = state.current_page == item["id"]
            items.append(ft.ListTile(
                leading=ft.Icon(item["icon"], color=ft.Colors.BLUE_700 if sel else ft.Colors.GREY_700),
                title=ft.Text(
                    item["label"],
                    weight=ft.FontWeight.W_500 if sel else ft.FontWeight.NORMAL,
                    color=ft.Colors.BLUE_700 if sel else None,
                ),
                selected=sel,
                on_click=create_handler(item["id"]),
            ))

    items.append(ft.Divider())
    return ft.Column(controls=items, scroll=ft.ScrollMode.AUTO, spacing=0)
```

### main.py

```python
"""Entry point for the app."""
import flet as ft
from components.drawer import AppDrawer
from config import APP_TITLE
from context import AppContext, AppCtx
from pages import PAGE_BUILDERS
from state import AppState


@ft.component
def PageContent():
    ctx = ft.use_context(AppCtx)
    state = ctx.state
    builder = PAGE_BUILDERS.get(state.current_page, PAGE_BUILDERS["home"])
    return ft.Container(content=builder(), expand=True, padding=20)


@ft.component
def App(state: AppState):
    ctx = AppContext(state=state)
    view_ref = [None]

    async def open_menu(e):
        if view_ref[0]:
            await view_ref[0].show_drawer()

    def build_view():
        view_ref[0] = ft.View(
            controls=[PageContent()],
            appbar=ft.AppBar(
                leading=ft.IconButton(icon=ft.Icons.MENU, on_click=open_menu, tooltip="Menu"),
                title=ft.Text(APP_TITLE),
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
                actions=[
                    ft.IconButton(
                        icon=ft.Icons.DARK_MODE if not state.dark_theme else ft.Icons.LIGHT_MODE,
                        tooltip="Toggle theme",
                        on_click=lambda _: state.toggle_theme(),
                    ),
                ],
            ),
            drawer=ft.NavigationDrawer(controls=[AppDrawer()], on_dismiss=lambda e: None),
            padding=0,
            bgcolor=ft.Colors.WHITE,
        )
        return view_ref[0]

    return AppCtx(ctx, build_view)


def main(page: ft.Page):
    page.title = APP_TITLE
    page.theme_mode = ft.ThemeMode.LIGHT

    app_state = AppState()
    app_state.notify("App started!", "success")

    page.render_views(App, app_state)


if __name__ == "__main__":
    ft.run(main)
```

---

## Building & Deploying

### Development

```bash
# Run the app (from project root)
flet run

# Run with src/ layout
flet run src

# Hot reload is automatic during development
```

### Building for Production

```bash
# Web
flet build web

# Android APK
flet build apk

# iOS
flet build ipa

# macOS
flet build macos

# Windows
flet build windows

# Linux
flet build linux

# iOS Simulator (no signing required — 0.81.0)
flet build ios-simulator

# Custom artifact name (0.81.0)
flet build apk --artifact "my-app-v2"
```

### pyproject.toml for Build

```toml
[project]
name = "my-app"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "flet>=0.80.0",
    # Add your extension dependencies here
    # "flet-onesignal>=0.4.0",
]

[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

# Required for src/ layout
[tool.flet.app]
path = "src"

# Register extensions (if using any)
# [tool.flet.extensions]
# flet_onesignal = "flet_onesignal.Extension"
```

---

## Breaking Changes Reference (0.80.x)

| Before | After |
|--------|-------|
| `ft.app(target=main)` | `ft.run(main)` |
| `page.overlay.append(service)` | `page.services.append(service)` |
| `ft.colors.BLUE` | `ft.Colors.BLUE` |
| `ft.icons.HOME` | `ft.Icons.HOME` |
| `ft.alignment.center` | `ft.Alignment.CENTER` |
| `ft.animation.Animation(...)` | `ft.Animation(...)` |
| `page.client_storage.set_async()` | `page.shared_preferences.set()` |
| `page.open(dialog)` | `await page.show_dialog(dialog)` |
| `ft.ElevatedButton(text=...)` | `ft.FilledButton(...)` |
| `await method_async()` | `await method()` (no `_async` suffix) |
| `ft.Theme(primary_swatch=...)` | `ft.Theme(color_scheme_seed=...)` |
| `page.platform == "android"` | `page.platform == ft.PagePlatform.ANDROID` |

## 0.81.0 Additions

**Zero breaking changes.** All additions are backward compatible.

### New Controls
- **ft.Hero** — Animated transitions between routes (shared element)
- **ft.PageView** — Carousel / swipe between pages
- **ft.RotatedBox** — Rotation by quarter turns before layout
- **Camera** — Preview and capture (Web, iOS, Android)
- **CodeEditor** — Embedded code editor with syntax highlighting
- **Color Pickers** — Multiple color selection widgets

### New LayoutControl Properties
| Property | Type | Description |
|----------|------|-------------|
| `transform` | `Transform` | Generic Matrix4 transform |
| `aspect_ratio` | `Number` | Automatic width/height ratio |
| `animate_size` | `AnimationValue` | Implicit size animation |
| `on_size_change` | `EventHandler` | Event when dimensions change |

### Clipboard Improvements
```python
# Images (0.81.0)
await ft.Clipboard().set_image(image_bytes)
image = await ft.Clipboard().get_image()

# Files (0.81.0 — macOS, Windows, Linux)
await ft.Clipboard().set_files(["/path/file.pdf"])
files = await ft.Clipboard().get_files()
```

### Hook Improvements
- `use_ref`: accepts callable for lazy initialization
- `use_state`: auto-subscribes to Observable values
- `@ft.component`: accepts `key` parameter for reconciliation

### @ft.control New Parameters
```python
@ft.control("MyControl", isolated=True)   # Exclude from parent updates
@ft.control("MyControl", post_init_args=1) # For InitVar support
```

---

## App Checklist

- [ ] `ft.run(main)` — not `ft.app()`
- [ ] `page.render_views(App, ...)` — not `page.add()`
- [ ] State created outside root component when global handlers need access
- [ ] `page.services.append()` for non-UI services
- [ ] `view_ref[0].show_drawer()` — not `page.show_drawer()`
- [ ] `@ft.observable @dataclass` — in this order
- [ ] `ft.use_state` for form fields
- [ ] Factory function in navigation loops
- [ ] `AppCtx(ctx, lambda: View(...))` — not `AppCtx(ctx, View(...))`
- [ ] `ft.Colors.NAME` and `ft.Icons.NAME` — uppercase

---

## Reference Documentation

These references apply to both declarative and imperative modes:

- **[Architecture](references/architecture.md)** — Clean architecture pattern for production Flet apps
- **[API Traps](references/api-traps.md)** — Critical API pitfalls verified with `inspect`
- **[Breaking Changes](references/breaking-changes.md)** — 82+ changes from Flet 0.x to 1.0+
- **[Error Guide](references/error-guide.md)** — Error lookup table with solutions
- **[New Controls](references/new-controls.md)** — 19 new controls in Flet 1.0+

For imperative mode (`page.add`, `page.update`), see the **flet-imperative** skill.