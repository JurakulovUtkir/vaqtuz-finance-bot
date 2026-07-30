"""Chek o'qish moduli — tarmoqqa chiqmaydigan testlar (klient soxta)."""

import json
import types

import pytest

from app.ai.vision import ReceiptData, ReceiptReader

EFFORT_ERROR = "Error code: 400 - This model does not support the effort parameter."

PAYLOAD = {
    "summa": 700000,
    "valyuta": "UZS",
    "qabul_qiluvchi": "Soxiba Nazarova",
    "muvaffaqiyatli": True,
    "ishonch": "yuqori",
}


class _FakeClient:
    """messages.create ni taqlid qiladi; effort bo'lsa xato berishi mumkin."""

    def __init__(self, *, reject_effort: bool = False, stop_reason: str = "end_turn"):
        self.reject_effort = reject_effort
        self.stop_reason = stop_reason
        self.calls: list[dict] = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.reject_effort and "effort" in kwargs["output_config"]:
            raise RuntimeError(EFFORT_ERROR)
        block = types.SimpleNamespace(type="text", text=json.dumps(PAYLOAD))
        return types.SimpleNamespace(stop_reason=self.stop_reason, content=[block])


def _reader(client) -> ReceiptReader:
    reader = ReceiptReader("", "test-model")
    reader._client = client
    return reader


@pytest.mark.asyncio
async def test_disabled_without_api_key():
    reader = ReceiptReader("", "test-model")
    assert reader.enabled is False
    assert await reader.read(b"x") is None


@pytest.mark.asyncio
async def test_reads_amount():
    reader = _reader(_FakeClient())
    result = await reader.read(b"fake-jpeg")
    assert result == ReceiptData(
        summa=700000,
        valyuta="UZS",
        qabul_qiluvchi="Soxiba Nazarova",
        muvaffaqiyatli=True,
        ishonch="yuqori",
    )


@pytest.mark.asyncio
async def test_effort_is_sent_by_default():
    client = _FakeClient()
    await _reader(client).read(b"x")
    assert client.calls[0]["output_config"]["effort"] == "low"


@pytest.mark.asyncio
async def test_falls_back_when_model_rejects_effort():
    """Haiku 4.5 effort ni qo'llamaydi — usiz qayta urinishi kerak."""
    client = _FakeClient(reject_effort=True)
    reader = _reader(client)

    result = await reader.read(b"x")
    assert result is not None and result.summa == 700000
    assert len(client.calls) == 2
    assert "effort" in client.calls[0]["output_config"]
    assert "effort" not in client.calls[1]["output_config"]

    # Ikkinchi chaqiruvda boshqa urinmaydi — effort qo'llanmasligi eslab qolingan
    client.calls.clear()
    await reader.read(b"x")
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_refusal_returns_none():
    assert await _reader(_FakeClient(stop_reason="refusal")).read(b"x") is None


@pytest.mark.asyncio
async def test_api_error_returns_none_instead_of_raising():
    class _Broken:
        messages = None

        def __getattr__(self, name):
            raise RuntimeError("tarmoq yiqildi")

    reader = ReceiptReader("", "test-model")
    reader._client = _Broken()
    assert await reader.read(b"x") is None


def test_reliability_gate():
    high = ReceiptData(700000, "UZS", None, True, "yuqori")
    low = ReceiptData(700000, "UZS", None, True, "past")
    none = ReceiptData(None, None, None, False, "past")
    assert high.is_reliable is True
    assert low.is_reliable is False
    assert none.is_reliable is False


def test_summary_mentions_confidence_and_failure():
    data = ReceiptData(700000, "UZS", "Soxiba", False, "orta")
    summary = data.summary()
    assert "ishonch: orta" in summary
    assert "Soxiba" in summary
    assert "muvaffaqiyat belgisi yo'q" in summary
