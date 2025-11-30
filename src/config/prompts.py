from typing import List, Tuple, Dict

def get_narrator_prompt(mystery_situation: str, hidden_solution: str, qa_history: List[Tuple[str, str]], question: str) -> str:
    """
    Constructs the prompt for the Narrator AI to answer a question.
    """
    history_str = "\n".join([f"Detective: {q}\nNarrador: {a}" for q, a in qa_history])
    if history_str:
        history_str = "\n\nHistorial de preguntas y respuestas:\n" + history_str

    return f"""
    Eres la IA Narrador en un interrogatorio policial formal.
    Conoces la siguiente historia completa:
    Situación misteriosa: {mystery_situation}
    Solución oculta: {hidden_solution}

    Tu rol es responder ESTRICTAMENTE solo con "sí", "no" o "no es relevante" a las preguntas del Detective.
    Mantén un tono profesional y formal. No des pistas adicionales ni explicaciones.

    {history_str}

    Pregunta del Detective: "{question}"
    Tu respuesta (sí/no/no es relevante):
    """

def get_narrator_validation_prompt(mystery_situation: str, hidden_solution: str, detective_solution: str, difficulty: str) -> str:
    """
    Constructs the prompt for the Narrator AI to validate the detective's solution.
    """
    difficulty_criteria = {
        "facil": "La evaluación es flexible; capturar el concepto principal es suficiente.",
        "media": "La evaluación es moderada; debe capturar la esencia de lo que pasó.",
        "dificil": "La evaluación es estricta; debe mencionar todos los elementos clave de la solución.",
        "fight_mode": "La evaluación es moderada; debe capturar la esencia de lo que pasó, similar a la dificultad 'media'."
    }
    
    current_difficulty_criteria = difficulty_criteria.get(difficulty, difficulty_criteria["media"])

    return f"""
    Eres la IA Narrador y tu tarea es validar la solución propuesta por el Detective.
    Conoces la historia completa:
    Situación misteriosa: {mystery_situation}
    Solución oculta: {hidden_solution}

    El Detective ha propuesto la siguiente solución:
    "{detective_solution}"

    Criterio de dificultad para la validación ({difficulty}): {current_difficulty_criteria}

    Por favor, evalúa la solución del Detective y proporciona tu veredicto y un análisis detallado en formato JSON:
    {{
        "veredicto": "Correcto" o "Incorrecto",
        "analisis": "Explicación detallada de por qué la solución es correcta o incorrecta,
                        incluyendo elementos que acertó, elementos que falló,
                        elementos que le faltaron, y cómo se aplica el criterio de dificultad."
    }}
    """

def get_detective_prompt(mystery_situation: str, qa_history: List[Tuple[str, str]]) -> str:
    """
    Constructs the prompt for the Detective AI to ask a question or attempt a solution.
    """
    history_str = "\n".join([f"Detective: {q}\nNarrador: {a}" for q, a in qa_history])
    if history_str:
        history_str = "\n\nHistorial de preguntas y respuestas:\n" + history_str

    return f"""
    Eres la IA Detective en un interrogatorio policial formal.
    Tu objetivo es descubrir la solución a la siguiente situación misteriosa:
    Situación misteriosa: {mystery_situation}

    Mantén un tono profesional como un investigador experimentado.
    Puedes hacer preguntas al Narrador, quien solo responderá "sí", "no" o "no es relevante".
    Asegúrate de que tus preguntas estén formuladas de tal manera que la respuesta pueda ser un simple "sí", "no" o "no es relevante".
    Cuando creas que tienes la solución, indica explícitamente que estás listo para resolver
    usando frases como "Creo que ya lo tengo", "Voy a resolver", "Tengo la solución", etc.
    Después de indicar que estás listo, tu siguiente turno será para dar la solución final.
    Tienes UNA única oportunidad para dar la solución final.

    {history_str}

    Tu siguiente acción (pregunta o indicación de que estás listo para resolver).
    Asegúrate de que tu respuesta sea una pregunta directa o una de las frases para resolver.
    NO incluyas "Detective:" al inicio de tu pregunta.
    """

def get_detective_final_solution_prompt(mystery_situation: str, qa_history: List[Tuple[str, str]]) -> str:
    """
    Constructs a prompt specifically for the Detective to provide the final solution.
    """
    history_str = "\n".join([f"Detective: {q}\nNarrador: {a}" for q, a in qa_history])
    if history_str:
        history_str = "\n\nHistorial de preguntas y respuestas:\n" + history_str

    return f"""
    Eres la IA Detective. Has indicado que estás listo para resolver la situación misteriosa.
    Esta es tu ÚNICA oportunidad para dar la solución final.
    Basado en la siguiente situación misteriosa y el historial de preguntas y respuestas:
    Situación misteriosa: {mystery_situation}
    {history_str}

    Por favor, proporciona tu solución final de manera clara y concisa:
    """

def get_story_generation_prompt(difficulty: str) -> str:
    """
    Returns the prompt for generating a Black Story based on difficulty.
    """
    difficulty_description = {
        "facil": "con lógica directa, menos elementos rebuscados, causas evidentes.",
        "media": "con una combinación de elementos lógicos y algunos giros inesperados.",
        "dificil": "muy rebuscada, con causas no obvias y múltiples elementos engañosos.",
        "fight_mode": "balanceada y apta para dos detectives compitiendo.",
    }

    return f"""
    Eres un experto creador de Black Stories. Tu tarea es generar una historia de Black Stories
    con el siguiente formato JSON. Es IMPERATIVO que tu respuesta sea ÚNICAMENTE el objeto JSON, sin ningún texto adicional, preámbulo o explicación.

    {{
        "situacion_misteriosa": "Una breve descripción de la situación inicial que se presenta al detective.",
        "solucion_oculta": "La explicación completa y detallada de lo que realmente sucedió."
    }}

    La historia debe ser {difficulty_description.get(difficulty, difficulty_description['media'])}.
    Asegúrate de que la "solucion_oculta" sea la verdad completa y que la "situacion_misteriosa"
    sea intrigante pero no revele la solución directamente.
    La historia debe ser concisa y clara.
    """
