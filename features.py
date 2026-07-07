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
        
def get_ai_generated_quiz_from_image(base64_image):
    prompt = (
        "Analyze this educational image/diagram and generate exactly ONE high-quality multiple-choice question (MCQ) based on it. "
        "The question should test the student's understanding of the diagram. Include 4 options (A, B, C, D).\n"
        "IMPORTANT: You MUST format the correct answer at the very end exactly like this on a new line: \n\nANSWER: (Correct Option)"
    )
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }],
            model="meta-llama/llama-4-scout-17b-16e-instruct",
        )
        text = chat_completion.choices[0].message.content.strip()
        
        # पाइथन मैजिक: ANSWER: वाले हिस्से को ढूंढकर छुपाना (Spoiler पट्टी)
        if "ANSWER:" in text:
            question_part, answer_part = text.split("ANSWER:", 1)
            return f"{question_part.strip()}\n\n||ANSWER: {answer_part.strip()}||"
        else:
            lines = [line for line in text.split("\n") if line.strip() != ""]
            if len(lines) > 0:
                lines[-1] = f"||{lines[-1]}||"
            return "\n".join(lines)
            
    except Exception as e:
        return f"⚠️ Quiz Generation Error: {str(e)}"
            
        

