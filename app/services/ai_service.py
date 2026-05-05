from __future__ import annotations

from flask import current_app
from openai import AzureOpenAI


class AzureAIService:
    def __init__(self):
        self.endpoint = current_app.config.get("AZURE_OPENAI_ENDPOINT")
        self.api_key = current_app.config.get("AZURE_OPENAI_KEY")
        self.deployment = current_app.config.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

    def _client(self):
        if not self.endpoint or not self.api_key:
            return None
        return AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version="2024-02-01",
        )

    def complete(self, prompt: str, max_tokens: int = 350) -> str:
        client = self._client()
        if not client:
            return "تعذر إنشاء ملخص ذكي بسبب عدم تهيئة Azure OpenAI."

        response = client.chat.completions.create(
            model=self.deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()



def generate_smart_reminder_text(session_obj):
    service = AzureAIService()
    prompt = f"""
Generate a concise, professional Arabic reminder notification for a lawyer.
Session details:
- Case: {session_obj.case_subject if hasattr(session_obj, 'case_subject') else ''}
- Court: {session_obj.court} - Circuit {session_obj.court_circuit}
- Date/Time: {session_obj.session_date} at {session_obj.session_time}
- Session type: {session_obj.session_type}
Generate ONLY the notification body text. Max 2 sentences. Professional Arabic.
"""
    return service.complete(prompt, max_tokens=120)


def summarize_legal_text(text: str) -> str:
    service = AzureAIService()
    prompt = f"""
أنت مساعد قانوني متخصص. لخص هذا المستند القانوني بالنقاط الرئيسية التالية:
- الأطراف المذكورة
- التواريخ المهمة
- المبالغ المالية
- الموضوع الجوهري
- أي مواعيد أو التزامات

المستند:
{text[:8000]}

الملخص (بالعربية، نقاط واضحة):
"""
    return service.complete(prompt, max_tokens=500)
