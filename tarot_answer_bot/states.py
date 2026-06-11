from aiogram.fsm.state import State, StatesGroup


class TarotFlow(StatesGroup):
    waiting_for_message = State()
    waiting_for_question_confirmation = State()
    waiting_for_question_edit = State()
    waiting_for_additional_context = State()
    waiting_for_client_choice = State()
    waiting_for_new_client_name = State()
    waiting_for_new_client_age = State()
    waiting_for_new_client_context = State()
    generating_reading = State()
    waiting_after_generation = State()
