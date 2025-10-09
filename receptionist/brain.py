import openai

class ReceptionistBrain:
    def __init__(self, model="gpt-4o-mini"):
        self.model = model

    def analyze_message(self, text):
        if not text:
            return "Could you repeat that?"

        prompt = f"""
        You are an AI receptionist. Analyze this message and respond professionally.

        Message: {text}
        Reply with: [Intent] + [Response]
        """

        resp = openai.ChatCompletion.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp["choices"][0]["message"]["content"]
