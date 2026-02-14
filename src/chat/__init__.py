from src.chat.base import ChatAdapter


def create_adapter(platform: str, **kwargs) -> ChatAdapter:
    """Factory: create chat adapter by platform name."""
    if platform == "telegram":
        from src.chat.telegram_adapter import TelegramAdapter
        return TelegramAdapter(**kwargs)
    else:
        raise ValueError(f"Unsupported chat platform: {platform}. Supported: telegram")
