"""Hisobotga Claude orqali qisqa tahlil qo'shish (ixtiyoriy).

ANTHROPIC_API_KEY sozlanmagan bo'lsa yoki so'rov xato bersa, bo'sh matn
qaytariladi va hisobot AI izohisiz yuboriladi — bot to'xtamaydi.
"""

from __future__ import annotations

import asyncio
import logging

try:
    import anthropic
except ImportError:  # kutubxona o'rnatilmagan bo'lsa ham bot ishlayveradi
    anthropic = None

logger = logging.getLogger(__name__)

MAX_TOKENS = 400

PROMPT_TEMPLATE = (
    "Quyida to'lovlar hisobotining raqamlari berilgan. "
    "Buni o'qib, 3-4 gapda oddiy o'zbek tilida qisqa tahlil "
    "va muhim kuzatuvlar yoz (masalan, qaysi loyiha eng ko'p "
    "xarajat qilgani, kutilmoqda holatidagi to'lovlar ko'p "
    "bo'lsa ogohlantirish va h.k.). Faqat tahlil matnini yoz, "
    "sarlavha yoki qo'shimcha izohsiz:\n\n{report}"
)


class InsightProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._model = model
        self._client = None
        if not api_key:
            logger.info("ANTHROPIC_API_KEY yo'q — hisobotlar AI tahlilisiz yuboriladi.")
        elif anthropic is None:
            logger.warning("anthropic kutubxonasi o'rnatilmagan — AI tahlil o'chirilgan.")
        else:
            self._client = anthropic.Anthropic(api_key=api_key)

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def analyse(self, report_text: str) -> str:
        """Hisobot bo'yicha qisqa tahlil. Xatolikda bo'sh satr qaytaradi."""
        if self._client is None:
            return ""
        try:
            # anthropic SDK sinxron — event loop'ni bloklamaslik uchun alohida oqimda
            return await asyncio.to_thread(self._analyse_sync, report_text)
        except Exception as error:  # noqa: BLE001 - AI xatoligi hisobotni to'xtatmasligi kerak
            logger.warning("AI tahlil olishda xatolik: %s", error)
            return ""

    def _analyse_sync(self, report_text: str) -> str:
        assert self._client is not None
        response = self._client.messages.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(report=report_text)}],
        )
        parts = [block.text for block in response.content if block.type == "text"]
        return "\n".join(parts).strip()
