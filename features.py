import random
from groq import Groq

# अपनी API Key यहाँ रखना मत भूलना
client = Groq(api_key="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") 

def get_ai_generated_quiz(student_class):
    # AI को सख्त निर्देश कि वो 'ANSWER:' ही लिखे
    prompt = (f"Generate one short objective multiple-choice question "
              f"for a {student_class} CBSE student. Include 4 options (A, B, C, D). "
              f"You MUST format the correct answer at the very end exactly like this: \n\nANSWER: (Correct Option)")
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        text = chat_completion.choices[0].message.content.strip()
        
        # Python Magic: 'ANSWER:' से सवाल और जवाब को अलग करो और जवाब छुपा दो
        if "ANSWER:" in text:
            question_part, answer_part = text.split("ANSWER:", 1)
            return f"{question_part.strip()}\n\n||ANSWER: {answer_part.strip()}||"
        else:
            # अगर AI फिर भी गलती करे, तो सबसे आखिरी लाइन को छुपा दो
            lines = text.split("\n")
            if len(lines) > 1:
                lines[-1] = f"||{lines[-1]}||"
            return "\n".join(lines)
            
    except Exception as e:
        return "Thinking... please try again!"
        
    
