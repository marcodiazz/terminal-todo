import json
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Input, ListView, ListItem, Static, Label, Checkbox, Collapsible, RadioButton, Tabs, Tab
from textual.containers import VerticalScroll, Container, Center, Middle
from textual.message import Message
from textual.events import Key

# Path for persistent data storage
DATA_DIR = Path.home() / ".terminal-todo"
DATA_FILE = DATA_DIR / "data.json"


class TaskRadioButton(RadioButton):
    """A RadioButton with delete functionality."""
    BUTTON_INNER = "●"
    
    class DeleteRequest(Message):
        """Message to request deletion of this task."""
        def __init__(self, task_widget: "TaskRadioButton") -> None:
            self.task_widget = task_widget
            super().__init__()
    
    BINDINGS = [("q", "delete_task", "Delete")]
    
    def action_delete_task(self) -> None:
        """Request deletion of this task."""
        self.post_message(self.DeleteRequest(self))


class TodoApp(App):
    """A Textual app to manage stopwatches."""

    BINDINGS = [
                ("d", "toggle_dark", "Theme"),
                ("t", "add", "+ tab"),
                ("a", "add_task", "+ task"),
                ("r", "remove", "remove tab"),
                ("escape", "close_modal", "esc"),
                # ("c", "clear", "Clear tabs"),
                # Global navigation
                ("left", "prev_tab", ""),
                ("right", "next_tab", ""),
                ("h", "prev_tab", "<-"),
                ("l", "next_tab", "->"),
                ("up", "prev_task", ""),
                ("down", "next_task", ""),
                ("j", "next_task", "↓"),
                ("k", "prev_task", "↑"),
            ]
    CSS_PATH = "todo.tcss"

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dictionary to store tasks for each tab: {tab_id: {"not_completed": [...], "completed": [...]}}
        self.tasks_by_tab = {}
        self.current_tab_id = None
        # Saved tabs data loaded from disk: [{"name": str, "tasks": {"not_completed": [...], "completed": [...] }}, ...]
        self.saved_tabs = []
        # Load saved data
        self._load_data()
    
    def _get_data_path(self) -> Path:
        """Get the path to the data file, creating directory if needed."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DATA_FILE
    
    def _load_data(self) -> None:
        """Load tasks and tabs from persistent storage."""
        data_path = self._get_data_path()
        self.saved_tabs = []
        if data_path.exists():
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # New format: {"tabs": [{"name": str, "tasks": {...}}, ...]}
                    if "tabs" in data:
                        self.saved_tabs = data.get("tabs", [])
                    # Backwards compatibility with old format using tab_ids
                    elif "tasks_by_tab" in data and "tab_names" in data:
                        tasks_by_tab = data.get("tasks_by_tab", {})
                        tab_names = data.get("tab_names", {})
                        migrated_tabs = []
                        for tab_id, tab_name in tab_names.items():
                            tab_tasks = tasks_by_tab.get(tab_id, {"not_completed": [], "completed": []})
                            migrated_tabs.append(
                                {
                                    "name": tab_name,
                                    "tasks": {
                                        "not_completed": list(tab_tasks.get("not_completed", [])),
                                        "completed": list(tab_tasks.get("completed", [])),
                                    },
                                }
                            )
                        self.saved_tabs = migrated_tabs
            except (json.JSONDecodeError, IOError):
                self.saved_tabs = []
    
    def _save_data(self) -> None:
        """Schedule a save after the next refresh so the DOM is up to date."""
        self.call_after_refresh(self._save_data_after_refresh)

    def _save_data_after_refresh(self) -> None:
        """Save tasks and tabs to persistent storage once the UI has settled."""
        # First save current UI state
        self._save_current_tasks()

        data_path = self._get_data_path()

        tabs_widget = self.query_one(Tabs)
        tabs_data = []
        for tab in tabs_widget.query(Tab):
            tab_id = tab.id
            tab_name = str(tab.label)
            tab_tasks = self.tasks_by_tab.get(tab_id, {"not_completed": [], "completed": []})
            tabs_data.append(
                {
                    "name": tab_name,
                    "tasks": {
                        "not_completed": list(tab_tasks.get("not_completed", [])),
                        "completed": list(tab_tasks.get("completed", [])),
                    },
                }
            )

        data = {"tabs": tabs_data}
        self.saved_tabs = tabs_data
        try:
            with open(data_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except IOError:
            pass
    
    async def on_mount(self) -> None:
        self.query_one(Tabs).focus()
        self.theme = "dracula"
        self.query_one("#tab_modal").visible = False
        
        tabs = self.query_one(Tabs)
        
        # If we have saved tabs, recreate them with new internal IDs
        if self.saved_tabs:
            first_tab_id = None
            for saved in self.saved_tabs:
                name = saved.get("name", "Tab")
                tasks = saved.get("tasks", {})
                await tabs.add_tab(name)
                # Use the last tab as the one we just added
                new_tab = list(tabs.query(Tab))[-1]
                tab_id = new_tab.id
                if first_tab_id is None:
                    first_tab_id = tab_id
                self.tasks_by_tab[tab_id] = {
                    "not_completed": list(tasks.get("not_completed", [])),
                    "completed": list(tasks.get("completed", [])),
                }

            if first_tab_id is not None:
                tabs.active = first_tab_id
                self.current_tab_id = first_tab_id
                self._load_tasks_for_tab(first_tab_id)
        else:
            # No saved data, create a default "Today" tab
            if tabs.tab_count == 0:
                await tabs.add_tab("Today")
            if tabs.active_tab:
                self.current_tab_id = tabs.active_tab.id
                if self.current_tab_id not in self.tasks_by_tab:
                    self.tasks_by_tab[self.current_tab_id] = {"not_completed": [], "completed": []}
        
    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle TabActivated message sent by Tabs."""
        # Save tasks from the current tab before switching
        if self.current_tab_id is not None:
            self._save_current_tasks()
        
        if event.tab is None:
            # When the tabs are cleared, event.tab will be None
            self.current_tab_id = None
        else:
            self.current_tab_id = event.tab.id
            
            # Initialize tasks for this tab if it doesn't exist
            if self.current_tab_id not in self.tasks_by_tab:
                self.tasks_by_tab[self.current_tab_id] = {"not_completed": [], "completed": []}
            
            # Load tasks for the new active tab
            self._load_tasks_for_tab(self.current_tab_id)

    def action_add(self) -> None:
        """Add a new tab."""
        tab_modal = self.query_one("#tab_modal")
        tab_modal.visible = True
        self.query_one("#tab_input", Input).focus()
    
    @on(Input.Submitted, "#tab_input")
    async def add_tab(self, event: Input.Submitted) -> None: 
        tabs = self.query_one(Tabs)
        tab_name = event.value.strip()
        if tab_name:
            await tabs.add_tab(tab_name)
            event.input.value = ""
            self.query_one("#tab_modal").visible = False
            tabs.focus()
            # Initialize empty task list for the new tab (it becomes the active tab)
            if tabs.active_tab:
                tab_id = tabs.active_tab.id
                if tab_id not in self.tasks_by_tab:
                    self.tasks_by_tab[tab_id] = {"not_completed": [], "completed": []}
                self._save_data()
            
    def action_add_task(self) -> None:
        """Focus the task input box to add a new todo item."""
        input_box = self.query_one("#task_input", Input)
        input_box.focus()

    def action_remove(self) -> None:
        """Remove active tab."""
        tabs = self.query_one(Tabs)
        active_tab = tabs.active_tab
        if active_tab is not None:
            tab_id = active_tab.id
            # Remove tasks associated with this tab
            if tab_id in self.tasks_by_tab:
                del self.tasks_by_tab[tab_id]
            tabs.remove_tab(tab_id)
            # Update current_tab_id to the new active tab
            if tabs.active_tab:
                self.current_tab_id = tabs.active_tab.id
            else:
                self.current_tab_id = None
            self._save_data()

    def action_clear(self) -> None:
        """Clear the tabs."""
        self.query_one(Tabs).clear()
    
    def action_close_modal(self) -> None:
        """Close the tab modal if it's visible, or blur task input and focus first task."""
        tab_modal = self.query_one("#tab_modal")
        task_input = self.query_one("#task_input", Input)
        
        if tab_modal.visible:
            # Close tab modal
            tab_modal.visible = False
            self.query_one("#tab_input", Input).value = ""
            self.query_one(Tabs).focus()
        elif self.focused == task_input:
            # If task input is focused, move focus to first uncompleted task
            not_completed = list(self.query_one("#not_completed_tasks").query(TaskRadioButton))
            if not_completed:
                not_completed[0].focus()
                not_completed[0].scroll_visible()
            else:
                # If no tasks, focus tabs
                self.query_one(Tabs).focus()

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        input_box = Input(placeholder=" Enter a new todo item...", id="task_input")
        not_completed_tasks = VerticalScroll(id="not_completed_tasks")
        completed_tasks = VerticalScroll(id="completed_tasks")
        tabs = Tabs()

        yield tabs
        yield Label("󰄱 To-Do", id="not_completed_label")
        yield not_completed_tasks
        yield Label(" Completed", id="completed_label")
        yield completed_tasks
        yield input_box
        # yield Footer()
        
        # Modal for adding new tab
        with Container(id="tab_modal"):
            with Center():
                with Middle():
                    with Container(id="tab_modal_content"):
                        yield Label(" Create New Tab", id="tab_modal_title")
                        yield Input(placeholder="Enter tab name...", id="tab_input")
        
    @on(Input.Submitted, "#task_input")
    def add_todo_item(self) -> None:
        todo_text = self.query_one("#task_input", Input).value.strip()
        if todo_text and self.current_tab_id is not None:
            task = self.task_widget(todo_text)
            self.query_one("#not_completed_tasks").mount(task)
            self.query_one("#task_input", Input).value = ""
            # Add task to the current tab's task list
            if self.current_tab_id in self.tasks_by_tab:
                self.tasks_by_tab[self.current_tab_id]["not_completed"].append(str(todo_text))
            self._save_data()
    
    @on(RadioButton.Changed)
    def on_radio_button_changed(self, event: RadioButton.Changed) -> None:
        task_widget = event.radio_button
        task_text = task_widget.label
        try:
            if self.current_tab_id is not None and self.current_tab_id in self.tasks_by_tab:
                if task_widget.value:  # If the task is marked as completed
                    self.query_one("#completed_tasks").mount(TaskRadioButton(label=task_text, value=True))
                    task_widget.remove()
                    # Move task from not_completed to completed
                    task_str = str(task_text)
                    if task_str in self.tasks_by_tab[self.current_tab_id]["not_completed"]:
                        self.tasks_by_tab[self.current_tab_id]["not_completed"].remove(task_str)
                        self.tasks_by_tab[self.current_tab_id]["completed"].append(task_str)
                else:  # If the task is marked as not completed
                    self.query_one("#not_completed_tasks").mount(TaskRadioButton(label=task_text, value=False))
                    task_widget.remove()
                    # Move task from completed to not_completed
                    task_str = str(task_text)
                    if task_str in self.tasks_by_tab[self.current_tab_id]["completed"]:
                        self.tasks_by_tab[self.current_tab_id]["completed"].remove(task_str)
                        self.tasks_by_tab[self.current_tab_id]["not_completed"].append(task_str)
                self._save_data()
            
        except Exception:
            pass

    
            
    def _save_current_tasks(self) -> None:
        """Save the current tasks displayed in the UI to the tasks dictionary."""
        if self.current_tab_id is None or self.current_tab_id not in self.tasks_by_tab:
            return
        
        # Clear the current stored tasks
        self.tasks_by_tab[self.current_tab_id]["not_completed"] = []
        self.tasks_by_tab[self.current_tab_id]["completed"] = []
        
        # Save not completed tasks
        not_completed_container = self.query_one("#not_completed_tasks")
        for task_widget in not_completed_container.query(TaskRadioButton):
            self.tasks_by_tab[self.current_tab_id]["not_completed"].append(str(task_widget.label))
        
        # Save completed tasks
        completed_container = self.query_one("#completed_tasks")
        for task_widget in completed_container.query(TaskRadioButton):
            self.tasks_by_tab[self.current_tab_id]["completed"].append(str(task_widget.label))
    
    def _load_tasks_for_tab(self, tab_id: str) -> None:
        """Load tasks for the specified tab from the tasks dictionary."""
        if tab_id not in self.tasks_by_tab:
            return
        
        # Clear current UI
        not_completed_container = self.query_one("#not_completed_tasks")
        completed_container = self.query_one("#completed_tasks")
        not_completed_container.remove_children()
        completed_container.remove_children()
        
        # Load not completed tasks
        for task_text in self.tasks_by_tab[tab_id]["not_completed"]:
            task_widget = TaskRadioButton(task_text, value=False)
            not_completed_container.mount(task_widget)
        
        # Load completed tasks
        for task_text in self.tasks_by_tab[tab_id]["completed"]:
            task_widget = TaskRadioButton(task_text, value=True)
            completed_container.mount(task_widget)
    
    def task_widget(self, task: str) -> TaskRadioButton:
        """Create a task widget for a todo task."""
        return TaskRadioButton(task)
    
    @on(TaskRadioButton.DeleteRequest)
    def on_task_delete_request(self, event: TaskRadioButton.DeleteRequest) -> None:
        """Handle task deletion request."""
        task_widget = event.task_widget
        task_text = task_widget.label
        
        # Remove from UI
        task_widget.remove()
        
        # Remove from tasks dictionary
        if self.current_tab_id and self.current_tab_id in self.tasks_by_tab:
            task_str = str(task_text)
            if task_str in self.tasks_by_tab[self.current_tab_id]["not_completed"]:
                self.tasks_by_tab[self.current_tab_id]["not_completed"].remove(task_str)
            elif task_str in self.tasks_by_tab[self.current_tab_id]["completed"]:
                self.tasks_by_tab[self.current_tab_id]["completed"].remove(task_str)
            self._save_data()

    def on_key(self, event: Key) -> None:
        """Handle key events globally to prevent scroll from capturing navigation keys."""
        # Check if we're in the modal input
        focused = self.focused
        if isinstance(focused, Input):
            return  # Let inputs handle their own keys
        
        # Intercept navigation keys before they reach scroll containers
        if event.key in ("up", "down", "k", "j"):
            event.prevent_default()
            event.stop()
            if event.key in ("up", "k"):
                self.action_prev_task()
            else:  # down or j
                self.action_next_task()
        elif event.key in ("left", "right", "h", "l"):
            event.prevent_default()
            event.stop()
            if event.key in ("left", "h"):
                self.action_prev_tab()
            else:  # right or l
                self.action_next_tab()
    
    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "dracula" if self.theme == "catppuccin-latte" else "catppuccin-latte"
        )
    
    def action_prev_tab(self) -> None:
        """Navigate to the previous tab."""
        tabs = self.query_one(Tabs)
        if tabs.tab_count > 0 and tabs.active_tab:
            # Get list of all tab IDs
            tab_ids = [tab.id for tab in tabs.query("Tab")]
            current_index = tab_ids.index(tabs.active_tab.id)
            new_index = (current_index - 1) % len(tab_ids)
            tabs.active = tab_ids[new_index]
    
    def action_next_tab(self) -> None:
        """Navigate to the next tab."""
        tabs = self.query_one(Tabs)
        if tabs.tab_count > 0 and tabs.active_tab:
            # Get list of all tab IDs
            tab_ids = [tab.id for tab in tabs.query("Tab")]
            current_index = tab_ids.index(tabs.active_tab.id)
            new_index = (current_index + 1) % len(tab_ids)
            tabs.active = tab_ids[new_index]
    
    def action_prev_task(self) -> None:
        """Navigate to the previous task."""
        # Get all visible tasks (not completed + completed)
        not_completed = list(self.query_one("#not_completed_tasks").query(TaskRadioButton))
        completed = list(self.query_one("#completed_tasks").query(TaskRadioButton))
        all_tasks = not_completed + completed
        
        if not all_tasks:
            return
        
        # Find currently focused task
        focused = self.focused
        if isinstance(focused, TaskRadioButton) and focused in all_tasks:
            current_index = all_tasks.index(focused)
            prev_index = (current_index - 1) % len(all_tasks)
            all_tasks[prev_index].focus()
            all_tasks[prev_index].scroll_visible()
        else:
            # If no task is focused, focus the last one
            all_tasks[-1].focus()
            all_tasks[-1].scroll_visible()
    
    def action_next_task(self) -> None:
        """Navigate to the next task."""
        # Get all visible tasks (not completed + completed)
        not_completed = list(self.query_one("#not_completed_tasks").query(TaskRadioButton))
        completed = list(self.query_one("#completed_tasks").query(TaskRadioButton))
        all_tasks = not_completed + completed
        
        if not all_tasks:
            return
        
        # Find currently focused task
        focused = self.focused
        if isinstance(focused, TaskRadioButton) and focused in all_tasks:
            current_index = all_tasks.index(focused)
            next_index = (current_index + 1) % len(all_tasks)
            all_tasks[next_index].focus()
            all_tasks[next_index].scroll_visible()
        else:
            # If no task is focused, focus the first one
            all_tasks[0].focus()
            all_tasks[0].scroll_visible()



if __name__ == "__main__":
    app = TodoApp()
    app.run()