import random
from groq import Groq

# अपनी API Key यहाँ रखना मत भूलना
client = Groq(api_key="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") 

def get_ai_generated_quiz(student_class):
    prompt = (f"Generate one short objective multiple-choice question "
              f"for a {student_class} CBSE student. Include 4 options (A, B, C, D). "
              f"Write the correct answer on the very last line.")
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        text = chat_completion.choices[0].message.content.strip()
        
        # Bulletproof Python Logic: पहले सारी खाली लाइनों को हटाओ
        lines = [line for line in text.split("\n") if line.strip() != ""]
        
        # अब जो सबसे आखिरी लाइन बची है (वही आंसर है), उस पर काली पट्टी लगाओ
        if len(lines) > 0:
            lines[-1] = f"||{lines[-1]}||"
            
        return "\n".join(lines)
            
    except Exception as e:
        return "Thinking... please try again!"
    
        
    
