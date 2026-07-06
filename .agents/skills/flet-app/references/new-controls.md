# Flet 1.0+ New Controls Reference

> 19+ new controls introduced in Flet 1.0+ (>= 0.83.0), plus new features in 0.83.0 and 0.85.0.

---

## Flet 0.85.0 Additions

### `ft.Router` — Declarative Routing

```python
import flet as ft


@ft.component
def App():
    return ft.Router(
        [
            ft.Route(index=True, component=Home),
            ft.Route(path="about", component=About),
            ft.Route(path="products/:pid", component=ProductDetails),
            ft.Route(path="users/:uid(\\d+)", component=UserPage,
                     loader=lambda p: fetch_user(p["uid"])),
        ],
        not_found=NotFound,
        manage_views=False,  # True for mobile view-stack
    )


@ft.component
def ProductDetails():
    params = ft.use_route_params()   # {"pid": "42"}
    location = ft.use_route_location()  # "/products/42"
    return ft.Text(f"Product {params['pid']}")
```

Hooks: `use_route_params`, `use_route_location`, `use_view_path`,
`use_route_outlet`, `use_route_loader_data`, `is_route_active(path, exact)`.

### `ft.use_dialog()` — Reactive Dialogs

```python
@ft.component
def MyForm():
    show, set_show = ft.use_state(False)

    ft.use_dialog(
        ft.AlertDialog(title=ft.Text("Hello!")) if show else None
    )

    return ft.FilledButton("Open", on_click=lambda _: set_show(True))
```

Frozen diff preserves `TextField` cursor/focus across re-renders.

### `page.navigate(route)` — Sync Navigation

```python
ft.FilledButton("Go", on_click=lambda _: page.navigate("/products"))
```

Equivalent to `asyncio.create_task(page.push_route(route))`.

### `page.pop_views_until(route, result=...)` + `on_views_pop_until`

```python
async def go_back(ev):
    await page.pop_views_until("/", result="Done!")

page.on_views_pop_until = lambda e: print(e.result, e.view.route)
```

### `Screenshot` control + `page.take_animation()`

```python
sc = ft.Screenshot(content=ft.Container(...))

page.enable_screenshots = True

# Single screenshot of subtree
png = await sc.capture(pixel_ratio=2.0)

# Full-page animated sequence (one round-trip)
frames = await page.take_animation(
    name="loading",
    frame_delays_ms=[0, 100, 200, 300, 400],
    pixel_ratio=2.0,
)
```

---

## Material Design 3 Buttons (4)

### FilledIconButton
```python
ft.FilledIconButton(icon=ft.Icons.SAVE, tooltip="Save", on_click=handle_save)
```

### FilledTonalButton
```python
ft.FilledTonalButton(content=ft.Text("Settings"), icon=ft.Icons.SETTINGS_OUTLINED)
```

### FilledTonalIconButton
```python
ft.FilledTonalIconButton(icon=ft.Icons.FAVORITE, tooltip="Favorite", on_click=toggle)
```

### OutlinedIconButton
```python
ft.OutlinedIconButton(icon=ft.Icons.DELETE_OUTLINE, tooltip="Delete", on_click=handle)
```

---

## Input Controls (5)

### SearchBar
```python
ft.SearchBar(
    bar_hint_text="Search...",
    view_hint_text="Choose from suggestions...",
    on_change=handle_change,
    on_submit=handle_submit,
    controls=[
        ft.ListTile(title=ft.Text("Result 1"), on_click=lambda e: print("selected")),
    ],
)
```

### AutoComplete
```python
ft.AutoComplete(
    value="One",
    width=200,
    on_select=handle_select,
    suggestions=[
        ft.AutoCompleteSuggestion(key="one", value="One"),
        ft.AutoCompleteSuggestion(key="two", value="Two"),
    ],
)
```

### DropdownM2
```python
from flet import dropdownm2

ft.DropdownM2(
    width=220,
    value="Alice",
    label="Select user",
    on_change=lambda e: print(e.control.value),
    options=[
        dropdownm2.Option(key="Alice", text="Alice"),
        dropdownm2.Option(key="Bob", text="Bob"),
    ],
)
```

### RangeSlider
```python
ft.RangeSlider(
    min=0, max=100,
    start_value=10, end_value=80,
    divisions=10,
    label="{value}%",
    on_change=handle_change,
)
```

### TimePicker
```python
from datetime import time

time_picker = ft.TimePicker(
    value=time(hour=19, minute=30),
    confirm_text="OK",
    cancel_text="Cancel",
    on_change=handle_change,
)
page.overlay.append(time_picker)
time_picker.open = True
page.update()
```

---

## List Controls (2)

### ReorderableListView
```python
ft.ReorderableListView(
    show_default_drag_handles=True,
    on_reorder=handle_reorder,  # e.old_index, e.new_index
    controls=[
        ft.ListTile(
            title=ft.Text(f"Item {i}"),
            leading=ft.ReorderableDragHandle(content=ft.Icon(ft.Icons.DRAG_INDICATOR)),
        )
        for i in range(10)
    ],
)
```

### Dismissible
```python
ft.Dismissible(
    content=ft.ListTile(title=ft.Text("Swipe to delete")),
    dismiss_direction=ft.DismissDirection.HORIZONTAL,
    background=ft.Container(
        content=ft.Icon(ft.Icons.DELETE, color=ft.Colors.WHITE),
        bgcolor=ft.Colors.GREEN,
        alignment=ft.Alignment.CENTER_LEFT,
    ),
    secondary_background=ft.Container(
        content=ft.Icon(ft.Icons.DELETE_FOREVER, color=ft.Colors.WHITE),
        bgcolor=ft.Colors.RED,
        alignment=ft.Alignment.CENTER_RIGHT,
    ),
    on_dismiss=handle_dismiss,
)
```

---

## Menu Controls (3)

### MenuBar
```python
ft.MenuBar(
    expand=True,
    controls=[
        ft.SubmenuButton(
            content=ft.Text("File"),
            controls=[
                ft.MenuItemButton(content=ft.Text("New"), leading=ft.Icon(ft.Icons.NEW_LABEL), on_click=handle),
                ft.MenuItemButton(content=ft.Text("Open"), leading=ft.Icon(ft.Icons.FOLDER_OPEN), on_click=handle),
                ft.Divider(),
                ft.MenuItemButton(content=ft.Text("Exit"), on_click=lambda e: page.window.close()),
            ],
        ),
    ],
)
```

### PopupMenuButton
```python
ft.PopupMenuButton(
    icon=ft.Icon(ft.Icons.MORE_VERT),
    items=[
        ft.PopupMenuItem(content=ft.Text("Item 1"), on_click=handle),
        ft.PopupMenuItem(),  # Divider
        ft.PopupMenuItem(content=ft.Text("Delete", color=ft.Colors.RED), on_click=handle),
    ],
)
```

---

## Effect & Utility Controls (5)

### Shimmer (Skeleton loading)
```python
ft.Shimmer(
    base_color=ft.Colors.with_opacity(0.3, ft.Colors.GREY_400),
    highlight_color=ft.Colors.WHITE,
    content=ft.Column(controls=[
        ft.Container(height=80, bgcolor=ft.Colors.GREY_300, border_radius=8),
        ft.Container(height=80, bgcolor=ft.Colors.GREY_300, border_radius=8),
    ], spacing=10),
)
```

### Screenshot
```python
screenshot = ft.Screenshot(ft.Container(ft.Text("Capture me"), padding=10))
image = await screenshot.capture()  # Returns base64 data
```

### KeyboardListener (Scoped key events with keydown + keyup)
```python
ft.KeyboardListener(
    content=ft.Container(content=ft.Text("Press keys here"), padding=50),
    autofocus=True,
    on_key_down=lambda e: print(f"Down: {e.key}"),
    on_key_up=lambda e: print(f"Up: {e.key}"),
)
```

**Note**: Unlike `page.on_keyboard_event`, `KeyboardListener` supports separate `on_key_down` and `on_key_up`.

### SelectionArea
```python
ft.SelectionArea(
    content=ft.Column([
        ft.Text("This text is selectable"),
        ft.Text("This too"),
    ])
)
```

### TransparentPointer (Event pass-through)
```python
ft.TransparentPointer(
    content=ft.Container(content=ft.Text("Events pass through me"), padding=50)
)
```

---

## Summary Table

| Category | Controls |
|----------|----------|
| MD3 Buttons (4) | `FilledIconButton`, `FilledTonalButton`, `FilledTonalIconButton`, `OutlinedIconButton` |
| Input (5) | `SearchBar`, `AutoComplete`, `DropdownM2`, `RangeSlider`, `TimePicker` |
| Lists (2) | `ReorderableListView`, `Dismissible` |
| Menus (3) | `MenuBar`, `SubmenuButton`, `PopupMenuButton` |
| Effects (5) | `Shimmer`, `Screenshot`, `KeyboardListener`, `SelectionArea`, `TransparentPointer` |

---

## New in Flet 0.83.0

### Customizable Scrollbars

All scrollable controls (`Column`, `Row`, `ListView`, `GridView`, `ExpansionPanelList`) now accept a `Scrollbar` instance:

```python
from flet.controls.scrollable_control import Scrollbar, ScrollbarOrientation

ft.ListView(
    scroll=Scrollbar(
        thumb_visibility=True,
        track_visibility=True,
        thickness=8,
        radius=4,
        interactive=True,
        orientation=ScrollbarOrientation.RIGHT,
    ),
    controls=[ft.Text(f"Item {i}") for i in range(100)],
)
```

**Scrollbar properties**: `thumb_visibility`, `track_visibility`, `thickness`, `radius`, `interactive`, `orientation` (LEFT/RIGHT/TOP/BOTTOM).

### Scrollable ExpansionPanelList

`ExpansionPanelList` now inherits from `ScrollableControl` — supports `scroll`, `auto_scroll`, `scroll_interval`, `on_scroll`, and `scroll_to()`.

```python
ft.ExpansionPanelList(
    scroll=Scrollbar(thumb_visibility=True),
    controls=[ft.ExpansionPanel(...) for _ in range(20)],
)
```

### SharedPreferences Type Expansion

Now supports `int`, `float`, `bool`, and `list[str]` in addition to `str`:

```python
prefs = ft.SharedPreferences()
page.services.append(prefs)

await prefs.set("count", 42)              # int
await prefs.set("ratio", 3.14)            # float
await prefs.set("dark_mode", True)         # bool
await prefs.set("tags", ["py", "flet"])    # list[str]
```

### Declarative Field Validation (Annotated + V Rules)

Controls now use `typing.Annotated` with `V` validation rules for compile-time-like field constraints:

```python
from typing import Annotated
from flet.utils.validation import V

# Used internally by controls — example:
opacity: Annotated[Number, V.between(0.0, 1.0)] = 1.0
elevation: Annotated[Number, V.ge(0)] = 2

# Available V rules: instance_of, gt, ge, lt, le, between, factor_of,
# multiple_of, eq, ne, one_of, non_empty, length_ge, length_eq,
# length_between, visible_control, visible_controls, gt_field, ge_field,
# lt_field, le_field, or_, deprecated, field, ensure
```

### Performance: Up to 6.7x Faster Diffing

- **Prop descriptor**: Tracks only modified properties (sparse `_values` dict)
- **@value decorator**: ~150 data types use content-based comparison
- **Smart update()**: Framework skips automatic update if explicit `.update()` was called

---

**Version**: Flet >= 0.83.0
**New Controls**: 19 (+ scrollbar customization, expanded SharedPreferences, field validation)
