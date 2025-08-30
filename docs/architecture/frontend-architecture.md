# Frontend Architecture

## Component Architecture

### Component Organization
```
src/
├── ui/
│   ├── main_window.py          # Primary application window
│   ├── components/
│   │   ├── folder_selector.py  # Folder browsing widget
│   │   ├── file_preview.py     # Before/after file list
│   │   ├── progress_dialog.py  # Operation progress modal
│   │   ├── settings_panel.py   # Configuration interface
│   │   └── status_bar.py       # Status và help information
│   ├── dialogs/
│   │   ├── error_dialog.py     # Error display và recovery
│   │   ├── confirm_dialog.py   # Operation confirmation
│   │   └── about_dialog.py     # Application information
│   └── styles/
│       ├── themes.py           # Windows 10/11 styling
│       └── constants.py        # UI constants và colors
```

### Component Template
```python
from tkinter import ttk
from typing import Protocol, Callable
from dataclasses import dataclass

class UIComponent(Protocol):
    def initialize(self, parent: ttk.Widget) -> None: ...
    def update_data(self, data: Any) -> None: ...
    def get_user_input(self) -> Any: ...
    def handle_error(self, error: Exception) -> None: ...

@dataclass
class ComponentState:
    is_loading: bool = False
    has_error: bool = False
    error_message: str = ""
    data: Any = None

class BaseComponent:
    def __init__(self, parent: ttk.Widget, state_changed_callback: Callable):
        self.parent = parent
        self.state = ComponentState()
        self.on_state_changed = state_changed_callback
        self.setup_ui()
    
    def setup_ui(self) -> None:
        """Override trong subclasses để create UI elements"""
        pass
    
    def update_state(self, **kwargs) -> None:
        """Update component state và trigger re-render"""
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
        self.render()
        self.on_state_changed(self.state)
```

## State Management Architecture

### State Structure
```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

class AppState(Enum):
    IDLE = "idle"
    LOADING = "loading"
    PREVIEW = "preview"
    EXECUTING = "executing"
    ERROR = "error"

@dataclass
class ApplicationState:
    # UI State
    current_state: AppState = AppState.IDLE
    selected_folder: Optional[str] = None
    files_preview: List[Dict] = field(default_factory=list)
    
    # Operation State  
    current_operation_id: Optional[str] = None
    progress_percentage: float = 0.0
    current_file_being_processed: Optional[str] = None
    
    # Settings State
    normalization_rules: Dict[str, bool] = field(default_factory=dict)
    ui_preferences: Dict[str, Any] = field(default_factory=dict)
    
    # Error State
    last_error: Optional[Exception] = None
    error_recovery_options: List[str] = field(default_factory=list)

class StateManager:
    def __init__(self):
        self.state = ApplicationState()
        self.subscribers: List[Callable] = []
    
    def subscribe(self, callback: Callable) -> None:
        self.subscribers.append(callback)
    
    def update_state(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
        self._notify_subscribers()
    
    def _notify_subscribers(self) -> None:
        for callback in self.subscribers:
            callback(self.state)
```

### State Management Patterns
- **Centralized State**: Single ApplicationState object managed by StateManager
- **Observer Pattern**: Components subscribe to state changes
- **Immutable Updates**: State changes through dedicated update methods
- **Error Boundaries**: Error state isolated và recoverable
