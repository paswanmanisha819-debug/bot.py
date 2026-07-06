import random
from groq import Groq

# अपनी API Key यहाँ रखना मत भूलना
client = Groq(api_key="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") 

def get_ai_generated_quiz(student_class):
    # AI को एकदम सख्त निर्देश कि फॉर्मेट कैसा होना चाहिए
    prompt = (f"Generate an objective multiple-choice question for a {student_class} CBSE student.\n"
              f"Format it EXACTLY like this:\n\n"
              f"Question Text Here?\n"
              f"A) Option 1\nB) Option 2\nC) Option 3\nD) Option 4\n\n"
              f"||Correct Answer: [Write Answer Here]||")
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        return "⚠️ Server is busy taking a nap! Please try again."
        
    
        

