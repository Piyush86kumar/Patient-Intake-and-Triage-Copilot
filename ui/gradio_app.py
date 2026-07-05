# ui/gradio_app.py
import gradio as gr
from triage_copilot.controller.state_machine import process_turn
from triage_copilot.controller.patient_case import PatientCase

def send_message(message, chat_history, conversation_id):
    if conversation_id is None:
        conversation_id = PatientCase.new().conversation_id
    response = process_turn(conversation_id, message)
    chat_history = chat_history + [(message, response.message)]
    return chat_history, conversation_id, ""

def get_clinician_view(conversation_id):
    if conversation_id is None:
        return {}
    return PatientCase.load(conversation_id).model_dump()

with gr.Blocks(title="Patient Intake & Triage Copilot") as demo:
    conversation_id_state = gr.State(None)

    with gr.Tab("Patient Chat"):
        gr.Markdown(
            "**This is a care-navigation tool, not a diagnosis tool. "
            "In a real emergency, call 911 immediately.**"
        )
        chatbot = gr.Chatbot(label="Triage Copilot")
        msg_box = gr.Textbox(label="Describe your symptoms", placeholder="e.g. I've had a sore throat since yesterday...")
        msg_box.submit(
            send_message,
            inputs=[msg_box, chatbot, conversation_id_state],
            outputs=[chatbot, conversation_id_state, msg_box],
        )

    with gr.Tab("Clinician View"):
        gr.Markdown("Structured intake summary — facts, matched protocol, cited rule, disposition.")
        refresh_btn = gr.Button("Refresh")
        state_json = gr.JSON()
        refresh_btn.click(get_clinician_view, inputs=[conversation_id_state], outputs=[state_json])

# demo is imported by api/main.py and mounted via gr.mount_gradio_app