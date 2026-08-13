import json
import time
from google import genai
import asyncio

from src.analyzers.base import BaseAnalyzer
from src.core.config import get_settings
from src.utils.logger import get_logger


class EmailAnalyzer(BaseAnalyzer):

    def __init__(self):
        self.logger = get_logger("analyzer")
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model_name = "gemini-flash-latest"
        self.logger.info("EmailAnalyzer initialized with Gemini")

    @property
    def name(self) -> str:
        return "email_analyzer"

    async def analyze(self, message_body: str, context: dict = None) -> dict:
        context = context or {}
        await asyncio.sleep(2)
        start_time = time.time()

        prompt = f"""You are an expert email intelligence analyst. Your job is to deeply analyze emails and extract precise, actionable insights.

SENDER: {context.get("sender", "unknown")}
SUBJECT: {context.get("subject", "no subject")}
PLATFORM: {context.get("source", "unknown")}
BODY:
{message_body[:3000]}

Analyze this message thoroughly and return a JSON object with the following fields:

1. "category" - Main category. Choose ONE:
   - "work" = job-related, from colleagues, clients, managers, business partners
   - "personal" = from friends, family, personal contacts
   - "finance" = invoices, bank statements, payment confirmations, tax documents
   - "promotion" = marketing emails, sales, discounts, newsletters, product announcements
   - "notification" = automated alerts, account updates, security codes, shipping updates
   - "social" = social media notifications, connection requests, follows
   - "threat" = phishing, scam, suspicious links, fraud attempts, blackmail

2. "subcategory" - Be specific. Examples:
   - work: "meeting", "task", "report", "feedback", "hiring", "project_update"
   - personal: "greeting", "invitation", "family", "chat"
   - finance: "invoice", "payment", "bank_alert", "subscription", "tax"
   - promotion: "discount", "newsletter", "product_launch", "event_promo"
   - notification: "security", "shipping", "account_update", "verification", "reminder"
   - social: "connection_request", "message", "mention", "follow"
   - threat: "phishing", "scam", "malware", "spam", "impersonation"

3. "sentiment" - Emotional tone. Choose ONE:
   - "positive" = good news, appreciation, opportunity, success, congratulations
   - "negative" = complaint, rejection, problem, warning, bad news
   - "neutral" = informational, routine, no emotional charge
   - "urgent" = requires immediate action, deadline, emergency, time-sensitive

4. "sentiment_score" - Float from -1.0 to 1.0:
   - -1.0 = extremely negative (threat, scam, serious complaint)
   - -0.5 = moderately negative (problem, rejection)
   - 0.0 = neutral (notification, routine info)
   - 0.5 = moderately positive (good update, opportunity)
   - 1.0 = extremely positive (job offer, big win, great news)

5. "priority" - How urgently should the user handle this:
   - "critical" = needs action TODAY
   - "normal" = should handle within 1-3 days
   - "low" = can ignore or batch process

6. "priority_score" - Integer 0-100:
   - 90-100 = drop everything and handle this NOW
   - 70-89 = important, handle today
   - 40-69 = normal, handle this week
   - 20-39 = low priority, handle when free
   - 0-19 = noise, can safely ignore

7. "is_threat" - Boolean. true if phishing, scam, impersonation, malware, or social engineering.

8. "threat_type" - If is_threat is true: "phishing", "scam", "malware", "impersonation", "social_engineering". Empty string if safe.

9. "threat_confidence" - Float 0.0 to 1.0.

10. "summary" - Clear, concise summary in Turkish. 2-3 sentences.
    Include: who sent it, what they want, and why it matters.

11. "key_action" - What should the user DO? Write in Turkish. Be specific.
    If no action needed: "Bilgi amaçlı, aksiyon gerekmiyor"

12. "tags" - List of 2-5 short keyword tags for filtering.

13. "response_needed" - Boolean. Does this email require a reply?

14. "deadline" - If time-sensitive, state deadline in Turkish. Otherwise empty string.

Return ONLY valid JSON, no markdown, no explanation."""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "temperature": 0.1,
                    "response_mime_type": "application/json",
                },
            )
            text = response.text.strip()

            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]
                text = text.strip()

            result = json.loads(text)

            elapsed = (time.time() - start_time) * 1000
            result["processing_time_ms"] = elapsed

            self.logger.info(
                f"Analyzed: [{result.get('category')}] "
                f"[{result.get('sentiment')}] "
                f"[priority:{result.get('priority_score')}] "
                f"{'THREAT!' if result.get('is_threat') else 'safe'} "
                f"- {context.get('subject', '')[:50]}"
            )
            return result

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parse failed: {e}")
            return {"summary": "Analiz basarisiz", "errors": [str(e)]}

        except Exception as e:
            self.logger.error(f"Gemini API error: {e}")
            return {"summary": "Analiz basarisiz", "errors": [str(e)]}