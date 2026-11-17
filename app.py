"""Gradio app for the Coworker. Run with: uv run app.py"""

import html

import gradio as gr

import styles
from coworker import Coworker

LAUNCH_STYLE = {"theme": styles.THEME, "css": styles.CSS, "head": styles.JS}

HEADER = """
<div id="header">
    <div class="context-label">Your personal co-worker</div>
    <h1>Coworker</h1>
    <div class="brand-bar"></div>
</div>
"""


def render_todos(todos):
    if not todos:
        items = '<div class="placeholder">The Coworker will write its plan here as it works</div>'
    else:
        items = "<ul>" + "".join(
            f'<li class="{todo["status"]}"><span class="mark"></span>{html.escape(todo["content"])}</li>'
            for todo in todos
        ) + "</ul>"
    return f"<h3>Plan</h3>{items}"


async def setup():
    coworker = Coworker()
    await coworker.setup()
    return coworker, gr.update(interactive=True)


async def process_message(coworker, message, success_criteria, history):
    if coworker is None:  # the user clicked before setup finished bringing up the MCP servers
        return history, gr.update(visible=False), coworker
    results = await coworker.run_turn(message, success_criteria, history)
    return results, gr.update(visible=coworker.paused), coworker


async def approve(coworker, history):
    results = await coworker.resume(history)
    return results, gr.update(visible=coworker.paused), coworker


def watch_todos(coworker):
    """Called by the timer. The timer is the plan panel's only writer: if a long-running
    event owned the panel as an output, Gradio would lock it as pending and live updates
    would not render while the Coworker works."""
    return render_todos(coworker.todos) if coworker else render_todos([])


async def reset(coworker):
    if coworker:
        coworker.cleanup()
    new_coworker = Coworker()
    await new_coworker.setup()
    return "", "", None, gr.update(visible=False), new_coworker


def free_resources(coworker):
    if coworker:
        coworker.cleanup()


with gr.Blocks(title="Coworker") as ui:
    gr.HTML(HEADER)
    coworker = gr.State(delete_callback=free_resources)

    with gr.Row():
        chatbot = gr.Chatbot(label="Coworker", height=320, scale=3, elem_id="chat")
        with gr.Column(scale=1):
            todos_panel = gr.HTML(render_todos([]), elem_id="plan-panel")
    with gr.Group(elem_id="ask-panel"):
        with gr.Row():
            message = gr.Textbox(show_label=False, placeholder="Your request to the Coworker")
        with gr.Row():
            success_criteria = gr.Textbox(show_label=False, placeholder="What are your success criteria?")
    with gr.Row():
        reset_button = gr.Button("Reset", elem_id="reset-button")
        approve_button = gr.Button("Approve and continue", visible=False, elem_id="approve-button")
        go_button = gr.Button("Go!", elem_id="go-button", interactive=False)

    timer = gr.Timer(1)

    ui.load(setup, [], [coworker, go_button])
    timer.tick(watch_todos, [coworker], [todos_panel], show_progress="hidden")
    message.submit(process_message, [coworker, message, success_criteria, chatbot],
                   [chatbot, approve_button, coworker])
    success_criteria.submit(process_message, [coworker, message, success_criteria, chatbot],
                            [chatbot, approve_button, coworker])
    go_button.click(process_message, [coworker, message, success_criteria, chatbot],
                    [chatbot, approve_button, coworker])
    approve_button.click(approve, [coworker, chatbot], [chatbot, approve_button, coworker])
    reset_button.click(reset, [coworker], [message, success_criteria, chatbot, approve_button, coworker])


if __name__ == "__main__":
    ui.launch(inbrowser=True, **LAUNCH_STYLE)
