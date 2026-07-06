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
            model="llama3-8b-8192",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Thinking... please try again!"
      
