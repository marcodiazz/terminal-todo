import json
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Header, Input, ListView, ListItem, RadioSet, Static, Label, Checkbox, Collapsible, RadioButton, Tabs, Tab
from textual.containers import VerticalScroll, Container, Center, Middle, Vertical
from textual.message import Message
from textual.events import Key

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
                ("t", "add", "New tab"),
                ("a", "add_task", "New task"),
                ("r", "remove", "Remove tab"),
                ("escape", "close_modal", ""),
                # ("c", "toggle_compact", "Compact"),
                ("left", "prev_tab", ""),
                ("right", "next_tab", ""),
                ("h", "prev_tab", ""),
                ("l", "next_tab", ""),
                ("up", "prev_task", ""),
                ("down", "next_task", ""),
                ("j", "next_task", ""),
                ("k", "prev_task", ""),
            ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tasks_by_tab = {}
        self.current_tab_id = None
        self.saved_tabs = []
        self.compact = True
        self._load_data()
    
    @property
    def CSS_PATH(self):
        """Return the path to the CSS file."""
        return Path(__file__).parent / "todo.tcss"
    
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
                    if "tabs" in data:
                        self.saved_tabs = data.get("tabs", [])
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
        
        if self.saved_tabs:
            first_tab_id = None
            for saved in self.saved_tabs:
                name = saved.get("name", "Tab")
                tasks = saved.get("tasks", {})
                await tabs.add_tab(name)
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
            if tabs.tab_count == 0:
                await tabs.add_tab("Today")
            if tabs.active_tab:
                self.current_tab_id = tabs.active_tab.id
                if self.current_tab_id not in self.tasks_by_tab:
                    self.tasks_by_tab[self.current_tab_id] = {"not_completed": [], "completed": []}
        
    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle TabActivated message sent by Tabs."""
        if self.current_tab_id is not None:
            self._save_current_tasks()
        
        if event.tab is None:
            self.current_tab_id = None
        else:
            self.current_tab_id = event.tab.id
            
            if self.current_tab_id not in self.tasks_by_tab:
                self.tasks_by_tab[self.current_tab_id] = {"not_completed": [], "completed": []}
            
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
            if tab_id in self.tasks_by_tab:
                del self.tasks_by_tab[tab_id]
            tabs.remove_tab(tab_id)
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
            tab_modal.visible = False
            self.query_one("#tab_input", Input).value = ""
            self.query_one(Tabs).focus()
        elif self.focused == task_input:
            not_completed = list(self.query_one("#not_completed_tasks").query(TaskRadioButton))
            if not_completed:
                not_completed[0].focus()
                not_completed[0].scroll_visible()
            else:
                self.query_one(Tabs).focus()

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        input_box = Input(placeholder=" Enter a new todo item...", id="task_input")
        not_completed_tasks = VerticalScroll(id="not_completed_tasks")
        not_completed_tasks.border_title = "󰄱 To-Do"
        completed_tasks = VerticalScroll(id="completed_tasks")
        completed_tasks.border_title = " Completed"
        tabs = Tabs()

        yield tabs
        yield not_completed_tasks
        yield completed_tasks
        yield input_box
        yield Footer()
        
        with Container(id="tab_modal"):
            with Center():
                with Middle():
                    with Container(id="tab_modal_content"):
                        yield Label(" Create New Tab", id="tab_modal_title")
                        yield Input(placeholder="Enter tab name...", id="tab_input")
        
    @on(Input.Submitted, "#task_input")
    def add_todo_item(self) -> None:
        todo_text = self.query_one("#task_input", Input).value.strip()
        if todo_text and self.current_tab_id is not None:
            task = self.task_widget(todo_text)
            self.query_one("#not_completed_tasks").mount(task)
            self.query_one("#task_input", Input).value = ""
            if self.current_tab_id in self.tasks_by_tab:
                self.tasks_by_tab[self.current_tab_id]["not_completed"].append(str(todo_text))
            self._save_data()
    
    @on(RadioButton.Changed)
    def on_radio_button_changed(self, event: RadioButton.Changed) -> None:
        task_widget = event.radio_button
        task_text = task_widget.label
        try:
            if self.current_tab_id is not None and self.current_tab_id in self.tasks_by_tab:
                if task_widget.value:
                    self.query_one("#completed_tasks").mount(TaskRadioButton(label=task_text, value=True, compact=True))
                    task_widget.remove()
                    task_str = str(task_text)
                    if task_str in self.tasks_by_tab[self.current_tab_id]["not_completed"]:
                        self.tasks_by_tab[self.current_tab_id]["not_completed"].remove(task_str)
                        self.tasks_by_tab[self.current_tab_id]["completed"].append(task_str)
                else:
                    self.query_one("#not_completed_tasks").mount(TaskRadioButton(label=task_text, value=False, compact=self.compact))
                    task_widget.remove()
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
        
        self.tasks_by_tab[self.current_tab_id]["not_completed"] = []
        self.tasks_by_tab[self.current_tab_id]["completed"] = []
        
        not_completed_container = self.query_one("#not_completed_tasks")
        for task_widget in not_completed_container.query(TaskRadioButton):
            self.tasks_by_tab[self.current_tab_id]["not_completed"].append(str(task_widget.label))
        
        completed_container = self.query_one("#completed_tasks")
        for task_widget in completed_container.query(TaskRadioButton):
            self.tasks_by_tab[self.current_tab_id]["completed"].append(str(task_widget.label))
    
    def _load_tasks_for_tab(self, tab_id: str) -> None:
        """Load tasks for the specified tab from the tasks dictionary."""
        if tab_id not in self.tasks_by_tab:
            return
        
        not_completed_container = self.query_one("#not_completed_tasks")
        completed_container = self.query_one("#completed_tasks")
        not_completed_container.remove_children()
        completed_container.remove_children()
        
        for task_text in self.tasks_by_tab[tab_id]["not_completed"]:
            task_widget = TaskRadioButton(task_text, value=False, compact=self.compact)
            not_completed_container.mount(task_widget)
        
        for task_text in self.tasks_by_tab[tab_id]["completed"]:
            task_widget = TaskRadioButton(task_text, value=True, compact=True)
            completed_container.mount(task_widget)
    
    def task_widget(self, task: str) -> TaskRadioButton:
        """Create a task widget for a todo task."""
        return TaskRadioButton(task, value=False, compact=self.compact)
    
    @on(TaskRadioButton.DeleteRequest)
    def on_task_delete_request(self, event: TaskRadioButton.DeleteRequest) -> None:
        """Handle task deletion request."""
        task_widget = event.task_widget
        task_text = task_widget.label
        
        task_widget.remove()
        
        if self.current_tab_id and self.current_tab_id in self.tasks_by_tab:
            task_str = str(task_text)
            if task_str in self.tasks_by_tab[self.current_tab_id]["not_completed"]:
                self.tasks_by_tab[self.current_tab_id]["not_completed"].remove(task_str)
            elif task_str in self.tasks_by_tab[self.current_tab_id]["completed"]:
                self.tasks_by_tab[self.current_tab_id]["completed"].remove(task_str)
            self._save_data()

    def on_key(self, event: Key) -> None:
        """Handle key events globally to prevent scroll from capturing navigation keys."""
        focused = self.focused
        if isinstance(focused, Input):
            return
        
        if event.key in ("up", "down", "k", "j"):
            event.prevent_default()
            event.stop()
            if event.key in ("up", "k"):
                self.action_prev_task()
            else:
                self.action_next_task()
        elif event.key in ("left", "right", "h", "l"):
            event.prevent_default()
            event.stop()
            if event.key in ("left", "h"):
                self.action_prev_tab()
            else:
                self.action_next_tab()
    
    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "dracula" if self.theme == "catppuccin-latte" else "catppuccin-latte"
        )
    
    def action_toggle_compact(self) -> None:
        """Toggle compact mode for not completed tasks."""
        self.compact = not self.compact
        if self.current_tab_id is not None:
            self._load_tasks_for_tab(self.current_tab_id)
    
    def action_prev_tab(self) -> None:
        """Navigate to the previous tab."""
        tabs = self.query_one(Tabs)
        if tabs.tab_count > 0 and tabs.active_tab:
            tab_ids = [tab.id for tab in tabs.query("Tab")]
            current_index = tab_ids.index(tabs.active_tab.id)
            new_index = (current_index - 1) % len(tab_ids)
            tabs.active = tab_ids[new_index]
    
    def action_next_tab(self) -> None:
        """Navigate to the next tab."""
        tabs = self.query_one(Tabs)
        if tabs.tab_count > 0 and tabs.active_tab:
            tab_ids = [tab.id for tab in tabs.query("Tab")]
            current_index = tab_ids.index(tabs.active_tab.id)
            new_index = (current_index + 1) % len(tab_ids)
            tabs.active = tab_ids[new_index]
    
    def action_prev_task(self) -> None:
        """Navigate to the previous task."""
        not_completed = list(self.query_one("#not_completed_tasks").query(TaskRadioButton))
        completed = list(self.query_one("#completed_tasks").query(TaskRadioButton))
        all_tasks = not_completed + completed
        
        if not all_tasks:
            return
        
        focused = self.focused
        if isinstance(focused, TaskRadioButton) and focused in all_tasks:
            current_index = all_tasks.index(focused)
            prev_index = (current_index - 1) % len(all_tasks)
            all_tasks[prev_index].focus()
            all_tasks[prev_index].scroll_visible()
        else:
            all_tasks[-1].focus()
            all_tasks[-1].scroll_visible()
    
    def action_next_task(self) -> None:
        """Navigate to the next task."""
        not_completed = list(self.query_one("#not_completed_tasks").query(TaskRadioButton))
        completed = list(self.query_one("#completed_tasks").query(TaskRadioButton))
        all_tasks = not_completed + completed
        
        if not all_tasks:
            return
        
        focused = self.focused
        if isinstance(focused, TaskRadioButton) and focused in all_tasks:
            current_index = all_tasks.index(focused)
            next_index = (current_index + 1) % len(all_tasks)
            all_tasks[next_index].focus()
            all_tasks[next_index].scroll_visible()
        else:
            all_tasks[0].focus()
            all_tasks[0].scroll_visible()


def main():
    """Entry point for the terminal-todo command."""
    app = TodoApp()
    app.run()


if __name__ == "__main__":
    main()
