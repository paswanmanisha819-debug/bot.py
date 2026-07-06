import random
from groq import Groq

# अपनी API Key यहाँ डालो
client = Groq(api_key="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") 

def get_ai_generated_quiz(student_class):
    prompt = (f"Generate one important, short, and objective multiple-choice question "
              f"for a {student_class} CBSE student. Include 4 options (A, B, C, D) "
              f"and indicate the correct answer at the end. Keep it professional.")
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return "Thinking... please try again!"    
    
