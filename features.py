import random
from groq import Groq

# अपनी API Key यहाँ रखना मत भूलना
client = Groq(api_key="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") 

def get_ai_generated_quiz(student_class):
    prompt = (f"Generate one short and objective multiple-choice question "
              f"for a {student_class} CBSE student. Include 4 options (A, B, C, D). "
              f"IMPORTANT: Write the correct answer on the very last line.")
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        # AI का पूरा मैसेज लो
        text = chat_completion.choices[0].message.content.strip()
        
        # Python Magic: अगर AI ने खुद || लगाया है तो उसे हटाओ
        text = text.replace("||", "") 
        
        # मैसेज को लाइनों में तोड़ो
        lines = text.split("\n")
        
        # सबसे आखिरी लाइन (आंसर) को || के बीच में पैक कर दो
        if len(lines) > 1:
            lines[-1] = f"||{lines[-1]}||"
            
        # वापस लाइनों को जोड़कर भेज दो
        return "\n".join(lines)
        
    except Exception as e:
        return "Thinking... please try again!"
    
