"""Chek (skrinshot) rasmidan o'tkazilgan summani o'qish.

ANTHROPIC_API_KEY sozlanmagan bo'lsa yoki so'rov xato bersa None qaytariladi
va bot eski yo'l bilan ishlaydi — admin summani rasm izohiga yozadi.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from dataclasses import dataclass

try:
    import anthropic
except ImportError:
    anthropic = None

logger = logging.getLogger(__name__)

MAX_TOKENS = 2000

PROMPT = (
    "Bu bank ilovasidan olingan to'lov cheki (skrinshot). Rasmni diqqat bilan o'qib, "
    "HAQIQATDA O'TKAZILGAN summani aniqla.\n\n"
    "Muhim qoidalar:\n"
    "- summa faqat butun raqam bo'lsin, probel va valyuta belgisisiz "
    "(masalan '700 000 сум' -> 700000)\n"
    "- rasmda bir nechta raqam bo'lsa, o'tkazilgan summani tanla "
    "(balans, komissiya yoki sana emas)\n"
    "- rasm to'lov cheki bo'lmasa yoki summa aniq o'qilmasa: summa uchun null qaytar "
    "va ishonch darajasini 'past' qil\n"
    "- taxmin qilma. Ishonching komil bo'lmasa 'past' deb belgila."
)

RECEIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "summa": {
            "anyOf": [{"type": "integer"}, {"type": "null"}],
            "description": "O'tkazilgan summa, butun raqam. O'qilmasa null.",
        },
        "valyuta": {
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "description": "Masalan: UZS, USD. Aniqlanmasa null.",
        },
        "qabul_qiluvchi": {
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "description": "Pul o'tkazilgan shaxs ismi, ko'rinsa.",
        },
        "muvaffaqiyatli": {
            "type": "boolean",
            "description": "Chekda to'lov muvaffaqiyatli bajarilgani ko'rsatilganmi.",
        },
        "ishonch": {
            "type": "string",
            "enum": ["yuqori", "orta", "past"],
            "description": "Summani o'qishdagi ishonch darajasi.",
        },
    },
    "required": ["summa", "valyuta", "qabul_qiluvchi", "muvaffaqiyatli", "ishonch"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class ReceiptData:
    summa: int | None
    valyuta: str | None
    qabul_qiluvchi: str | None
    muvaffaqiyatli: bool
    ishonch: str

    @property
    def is_reliable(self) -> bool:
        """Past ishonchli natijani avtomatik qabul qilmaymiz."""
        return self.summa is not None and self.ishonch in ("yuqori", "orta")

    def summary(self) -> str:
        parts = [f"ishonch: {self.ishonch}"]
        if self.qabul_qiluvchi:
            parts.append(self.qabul_qiluvchi)
        if not self.muvaffaqiyatli:
            parts.append("chekda muvaffaqiyat belgisi yo'q")
        return ", ".join(parts)


class ReceiptReader:
    def __init__(self, api_key: str, model: str) -> None:
        self._model = model
        self._client = None
        if not api_key:
            logger.info("ANTHROPIC_API_KEY yo'q — chek rasmi avtomatik o'qilmaydi.")
        elif anthropic is None:
            logger.warning("anthropic kutubxonasi o'rnatilmagan — chek o'qish o'chirilgan.")
        else:
            self._client = anthropic.Anthropic(api_key=api_key)

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def read(self, image_bytes: bytes, media_type: str = "image/jpeg") -> ReceiptData | None:
        """Chekdan summani o'qiydi. Xatolikda None — bot to'xtamaydi."""
        if self._client is None:
            return None
        try:
            return await asyncio.to_thread(self._read_sync, image_bytes, media_type)
        except Exception as error:  # noqa: BLE001 - AI xatoligi to'lovni to'xtatmasligi kerak
            logger.warning("Chekni o'qishda xatolik: %s", error)
            return None

    def _read_sync(self, image_bytes: bytes, media_type: str) -> ReceiptData | None:
        assert self._client is not None
        response = self._client.messages.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": RECEIPT_SCHEMA},
            },
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64.standard_b64encode(image_bytes).decode(),
                            },
                        },
                        {"type": "text", "text": PROMPT},
                    ],
                }
            ],
        )

        if response.stop_reason == "refusal":
            logger.warning("Chekni o'qish rad etildi (safety).")
            return None

        text = next((block.text for block in response.content if block.type == "text"), "")
        if not text:
            return None

        data = json.loads(text)
        return ReceiptData(
            summa=data.get("summa"),
            valyuta=data.get("valyuta"),
            qabul_qiluvchi=data.get("qabul_qiluvchi"),
            muvaffaqiyatli=bool(data.get("muvaffaqiyatli")),
            ishonch=data.get("ishonch", "past"),
        )
