# Flet 1.0+ Error Quick Reference

> Quick diagnosis and solutions for common Flet errors.

---

## Error Lookup Table

| Error Message | Cause | Solution |
|--------------|-------|----------|
| `unexpected keyword argument 'tabs'` | Tabs API rewritten | `Tabs(content=..., length=N)` + `TabBar` + `TabBarView` |
| `unexpected keyword argument 'tl'` | BorderRadius param names | Use `top_left/top_right/bottom_left/bottom_right` |
| `missing required argument 'content'` | Tabs missing params | Tabs needs `content` and `length` |
| `unexpected keyword argument 'content'` (Tab) | Tab has no content param | `ft.Tab(label=..., icon=...)` |
| `unexpected keyword argument 'label_style'` | Badge simplified | `ft.Badge(label="5")` only |
| `unexpected keyword argument 'small'` | Badge simplified | `ft.Badge(label="5")` only |
| `Radio must be enclosed within RadioGroup` | Radio not wrapped | `ft.RadioGroup(content=ft.Radio(...))` |
| `height is unbounded` | TabBarView no height | Set `height=` on TabBarView directly |
| `'super' object has no attribute '__getattr__'` | `ft.Colors.values()` | Define color lists manually |
| `unexpected keyword argument 'text'` | TextButton change | Use `content=` or pass string directly |
| `unexpected keyword argument 'name'` | Icon change | Use `icon=` parameter |
| `ElevatedButton is not defined` | Removed | Use `ft.Button()` or `ft.FilledButton()` |
| `'NavigationDrawer' object has no attribute 'open'` | API changed | `await page.show_drawer()` / `close_drawer()` |
| `'Window' object has no attribute 'transparent'` | Removed | No replacement available |
| `coroutine 'Window.center' was never awaited` | Now async | `await page.window.center()` |
| `coroutine 'Window.close' was never awaited` | Now async | `await page.window.close()` |
| `clipboard is deprecated` | Deprecated | `ft.Clipboard()` service |
| `module 'flet' has no attribute 'Audio'` | Removed | Use third-party libs |
| `unexpected keyword argument 'on_change'` (Dropdown) | Renamed | Use `on_select` |
| `module 'flet' has no attribute 'PaintStyle'` | Renamed | `ft.PaintingStyle` |
| `Unsupported value type` (SharedPreferences) | Wrong type passed | Use `str`, `int`, `float`, `bool`, or `list[str]` only |
| `padding.all is deprecated` | Module-level function removed in 0.83 | Use `Padding.all()` class method |
| `padding.symmetric is deprecated` | Module-level function removed in 0.83 | Use `Padding.symmetric()` class method |
| `FieldValidationError` | Annotated field constraint violated | Check `V.*` rule on the field (e.g., `V.between(0, 1)` for opacity) |
| `module 'flet.canvas' has no attribute 'Polygon'` | Removed | Use `ft.canvas.Path` |
| `unexpected keyword argument 'stroke_dash'` | Renamed | `stroke_dash_pattern` |
| `'Path' object has no attribute 'move_to'` | API changed | `elements=[Path.MoveTo(...)]` |
| `missing 2 required positional arguments` (BorderRadius) | Need all 4 | Provide all: `top_left, top_right, bottom_left, bottom_right` |
| `unexpected keyword argument 'on_drag_end'` | Renamed | `on_drag_complete` |
| `'DragUpdateEvent' object has no attribute 'local_x'` | Renamed | `e.local_position.x` |
| `unsupported operand type(s) for -: 'NoneType'` | Nullable window props | `page.window.max_width or 1920` |
| `AttributeError: ROBOT` | Icon missing | Use `ft.Icons.ANDROID` |
| `'Page' object has no attribute 'open'` | API changed | `page.show_dialog()` |
| `'Page' object has no attribute 'close'` | API changed | `page.pop_dialog()` |
| `DeprecationWarning: symmetric() is deprecated` | Uppercase form | `ft.Padding.symmetric()` (uppercase P) |
| `DeprecationWarning: all() is deprecated ... Use Border.all` | Uppercase form | `ft.Border.all()` (uppercase B) |
| `dictionary changed size during iteration` | Thread UI mutation | `page.run_task(async_fn)` for UI updates |
| `handler must be a coroutine function` | `page.run_task` needs async | Pass `async def` function |
| `'Page' has no attribute 'snack_bar'` | Deprecated | `page.overlay.append(snackbar)` |
| `'Page' has no attribute 'bottom_sheet'` | Deprecated | `page.overlay.append(sheet)` |
| `'Page' has no attribute 'client_storage'` | Deprecated | `ft.SharedPreferences()` service |
| `'NoneType' object has no attribute '...'` (in component) | `use_context()` returns `None` on stale/unmounted component — **crashes scheduler permanently** | Add `if ctx is None: return ft.Container()` guard after every `use_context()` call |
| UI freezes after navigation (loading forever) | Scheduler crash from above error — `__updates_scheduler` only catches `CancelledError` | Fix the `use_context` guard + add scheduler restart patch to `schedule_update` |

---

## Quick Diagnosis by Keyword

| Error Keyword | Likely Cause |
|--------------|-------------|
| `unexpected keyword argument` | Parameter renamed or removed |
| `missing required argument` | Missing mandatory parameter |
| `has no attribute` | Attribute removed or renamed |
| `coroutine was never awaited` | Async method needs `await` |
| `must be a coroutine function` | Needs `async def` |
| `height is unbounded` | TabBarView needs height |
| `is not defined` | Control removed or renamed |

---

## Verification Commands

```bash
# Check constructor signature
python -c "import inspect; import flet as ft; print(inspect.signature(ft.BorderRadius.__init__))"

# Check if attribute exists
python -c "import flet as ft; print(hasattr(ft.Icons, 'ROBOT'))"

# List all public methods
python -c "import flet as ft; print([m for m in dir(ft.Page) if not m.startswith('_')])"
```

---

**Version**: Flet >= 0.83.0
