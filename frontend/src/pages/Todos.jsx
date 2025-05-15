import { createSignal, createEffect, For, Show } from 'solid-js';
import { createStore } from "solid-js/store";

export default function Todos() {
    const [todos, setTodos] = createStore([]);
    const [todoForm, setTodoForm] = createStore({
        name: "todo",
        description: "",
        type: "",
        completed: false
    });

    createEffect(() => {

    });

    const handleChange = (e) => {
        setTodoForm(e.target.name, e.target.value); // ✅ updates the correct field
    };

    const addTodo = () => {
        // if(todos.some((todo) => todo.name === todoForm.name)){
        //     alert("There already a todo with that name") 
        //     return;
        // } 
        setTodos([...todos, {...todoForm}]); //  adds the new todo to the list
    }

    return (
        <>
            <div>Todos</div>
            <div>
                Name:{" "} <input
                    name="name" // ✅ needed to tell setTodoForm which key to update
                    value={todoForm.name}
                    onInput={handleChange} // ✅ call it directly, don’t curry unless you need to
                />
            </div>
            <div>
                Description:{" "} <input
                    name="description" // ✅ needed to tell setTodoForm which key to update
                    value={todoForm.description}
                    onInput={handleChange} // ✅ call it directly, don’t curry unless you need to
                />
            </div>
            <div>
                Type:{" "} <input
                    name="type" // ✅ needed to tell setTodoForm which key to update
                    value={todoForm.type}
                    onInput={handleChange} // ✅ call it directly, don’t curry unless you need to
                />
            </div>

            <button onclick={addTodo}>Add Todo</button>

            <For each={todos} fallback={<div>No todos yet...</div>}>
                {(todo, i) => (
                    <div>
                        <h3>{todo.name}</h3>
                        <p>{todo.description}</p>
                        <p>{todo.type}</p>
                        <Show when={todo.completed} fallback={<p>Not Completed</p>}>
                            <p>Completed</p>
                        </Show>
                        <input type='button' value="Toggle Completed" onClick={() => setTodos(i(), "completed", c => !c)}
                        />
                    </div>
                )}
            </For>

        </>
    );
}
