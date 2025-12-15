from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Input, ListView, ListItem, Static, Label, Checkbox, Collapsible, RadioButton, Tabs
from textual.containers import VerticalScroll, Container, Center, Middle
from textual.message import Message


class TaskRadioButton(RadioButton):
    """A RadioButton with delete functionality."""
    BUTTON_INNER = "󰄴"
    
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
                ("t", "add", "Add tab"),
                ("a", "add_task", "Add task"),
                ("r", "remove", "Remove active tab"),
                ("escape", "close_modal", "Close"),
                # ("c", "clear", "Clear tabs"),
            ]
    CSS_PATH = "todo.tcss"

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dictionary to store tasks for each tab: {tab_id: {"not_completed": [...], "completed": [...]}}
        self.tasks_by_tab = {}
        self.current_tab_id = None
    
    def on_mount(self) -> None:
        self.query_one(Tabs).focus()
        self.theme = "tokyo-night"
        self.query_one("#tab_modal").visible = False
        # Initialize tasks for the default tab
        tabs = self.query_one(Tabs)
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
            if tabs.active_tab and tabs.active_tab.id not in self.tasks_by_tab:
                self.tasks_by_tab[tabs.active_tab.id] = {"not_completed": [], "completed": []}
            
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

    def action_clear(self) -> None:
        """Clear the tabs."""
        self.query_one(Tabs).clear()
    
    def action_close_modal(self) -> None:
        """Close the tab modal if it's visible."""
        tab_modal = self.query_one("#tab_modal")
        if tab_modal.visible:
            tab_modal.visible = False
            self.query_one("#tab_input", Input).value = ""
            self.query_one(Tabs).focus()

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        input_box = Input(placeholder=" Enter a new todo item...", id="task_input")
        not_completed_tasks = VerticalScroll(id="not_completed_tasks")
        completed_tasks = VerticalScroll(id="completed_tasks")
        tabs = Tabs("Today")
        
        yield tabs
        yield Label("󰄱 To-Do", id="not_completed_label")
        yield not_completed_tasks
        yield Label(" Completed", id="completed_label")
        yield completed_tasks
        yield input_box
        yield Footer()
        
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
                self.tasks_by_tab[self.current_tab_id]["not_completed"].append(todo_text)
    
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
                    if task_text in self.tasks_by_tab[self.current_tab_id]["not_completed"]:
                        self.tasks_by_tab[self.current_tab_id]["not_completed"].remove(task_text)
                        self.tasks_by_tab[self.current_tab_id]["completed"].append(task_text)
                else:  # If the task is marked as not completed
                    self.query_one("#not_completed_tasks").mount(TaskRadioButton(label=task_text, value=False))
                    task_widget.remove()
                    # Move task from completed to not_completed
                    if task_text in self.tasks_by_tab[self.current_tab_id]["completed"]:
                        self.tasks_by_tab[self.current_tab_id]["completed"].remove(task_text)
                        self.tasks_by_tab[self.current_tab_id]["not_completed"].append(task_text)
            
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
            self.tasks_by_tab[self.current_tab_id]["not_completed"].append(task_widget.label)
        
        # Save completed tasks
        completed_container = self.query_one("#completed_tasks")
        for task_widget in completed_container.query(TaskRadioButton):
            self.tasks_by_tab[self.current_tab_id]["completed"].append(task_widget.label)
    
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
            if task_text in self.tasks_by_tab[self.current_tab_id]["not_completed"]:
                self.tasks_by_tab[self.current_tab_id]["not_completed"].remove(task_text)
            elif task_text in self.tasks_by_tab[self.current_tab_id]["completed"]:
                self.tasks_by_tab[self.current_tab_id]["completed"].remove(task_text)

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "tokyo-night" if self.theme == "textual-light" else "textual-light"
        )



if __name__ == "__main__":
    app = TodoApp()
    app.run()