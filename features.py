import random
from groq import Groq

# अपनी API Key यहाँ डालो
client = Groq(api_key="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")   

def get_ai_generated_quiz(student_class):
    prompt = (f"Generate one important, short, and objective multiple-choice question "
              f"for a {student_class} CBSE student. Include 4 options (A, B, C, D). "
              f"IMPORTANT: Write the correct answer at the very end starting exactly with 'Correct Answer:'.")
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        text = chat_completion.choices[0].message.content
        
        # Python Magic: आंसर को खुद ही छुपा दो (Spoiler बना दो)
        if "Correct Answer:" in text:
            text = text.replace("Correct Answer:", "||Correct Answer:") + "||"
        elif "Answer:" in text:
            text = text.replace("Answer:", "||Answer:") + "||"
            
        return text
    except Exception as e:
        return "Thinking... please try again!"
        
