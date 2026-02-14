"""
Telegram Adapter - Telegram bot implementation of ChatAdapter
"""

import logging
import asyncio
from telegram import Update, BotCommand, MenuButtonCommands, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from src.chat.base import ChatAdapter
from src.stock_manager import StockManager
from src.locale import t

logger = logging.getLogger(__name__)


class TelegramAdapter(ChatAdapter):
    """Telegram bot adapter."""

    def __init__(self, token: str, stock_manager: StockManager, **kwargs):
        super().__init__(stock_manager=stock_manager)
        self.token = token
        self.app = None

    # ── Command handlers ──

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(t("welcome"), parse_mode='Markdown')

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(t("help"), parse_mode='Markdown')

    async def cmd_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(t("add_usage"))
            return

        ticker = context.args[0].upper()

        if self.stock_manager.add_stock(ticker):
            await update.message.reply_text(t("add_ok", ticker=ticker))

            if self.fetch_ticker_callback:
                success = await self.fetch_ticker_callback(ticker)
                if success:
                    brief = self.cached_summaries_ref.get(ticker, {}).get('brief', '')
                    await update.message.reply_text(t("add_done", ticker=ticker, brief=brief))
                else:
                    await update.message.reply_text(t("add_fail", ticker=ticker))
        else:
            await update.message.reply_text(t("add_exists", ticker=ticker))

    async def cmd_remove(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(t("remove_usage"))
            return

        ticker = context.args[0].upper()

        if self.stock_manager.remove_stock(ticker):
            if self.cached_summaries_ref and ticker in self.cached_summaries_ref:
                del self.cached_summaries_ref[ticker]
            await update.message.reply_text(t("remove_ok", ticker=ticker))
        else:
            await update.message.reply_text(t("remove_not_found", ticker=ticker))

    async def cmd_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        stocks = self.stock_manager.list_stocks()

        if not stocks:
            await update.message.reply_text(t("list_empty"))
            return

        msg = t("list_header", count=len(stocks))

        keyboard = []
        for stock in stocks:
            msg += f"• ${stock.ticker}"
            if stock.name:
                msg += f" - {stock.name}"
            msg += "\n"

            keyboard.append([
                InlineKeyboardButton(f"📊 ${stock.ticker}", url=f"https://finance.yahoo.com/quote/{stock.ticker}"),
                InlineKeyboardButton(t("list_btn_remove"), callback_data=f"remove_{stock.ticker}")
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')

    async def cmd_summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.summary_callback:
            try:
                await self.summary_callback()
            except Exception as e:
                await update.message.reply_text(t("summary_fail", error=str(e)))
                logger.error(f"Summary generation failed: {e}")
        else:
            await update.message.reply_text(t("summary_unavailable"))

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if query.data.startswith("remove_"):
            ticker = query.data.replace("remove_", "")
            if self.stock_manager.remove_stock(ticker):
                if self.cached_summaries_ref and ticker in self.cached_summaries_ref:
                    del self.cached_summaries_ref[ticker]
                await query.edit_message_text(t("btn_remove_ok", ticker=ticker))
            else:
                await query.edit_message_text(t("btn_remove_fail", ticker=ticker))

        elif query.data.startswith("detail_"):
            ticker = query.data.replace("detail_", "")
            await self._send_ticker_detail(query.message.chat_id, ticker)

    async def _send_ticker_detail(self, chat_id, ticker: str):
        if not self.cached_summaries_ref:
            await self.send_message(chat_id, t("detail_no_data", ticker=ticker))
            return

        data = self.cached_summaries_ref.get(ticker)
        if not data:
            await self.send_message(chat_id, t("detail_no_data", ticker=ticker))
            return

        msg = t("detail_header", ticker=ticker)
        msg += t("detail_link", ticker=ticker)
        msg += t("detail_news_count", count=data.get('news_count', 0))
        msg += data.get('detail', '')

        if len(msg) > 4000:
            msg = msg[:3990] + "\n\n..."

        await self.send_message(chat_id, msg, disable_web_page_preview=True)

    # ── ChatAdapter interface ──

    async def send_message(self, chat_id: str, text: str, parse_mode: str = 'Markdown',
                          disable_web_page_preview: bool = False, retries: int = 3, **kwargs):
        for attempt in range(retries):
            try:
                await self.app.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=parse_mode,
                    disable_web_page_preview=disable_web_page_preview
                )
                logger.info(f"Sent message to {chat_id}")
                return
            except Exception as e:
                logger.warning(f"Send message attempt {attempt + 1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"Failed to send message after {retries} attempts: {e}")

    async def _send_with_markup(self, chat_id: str, text: str,
                                reply_markup=None, retries: int = 3):
        for attempt in range(retries):
            try:
                await self.app.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup,
                    disable_web_page_preview=True
                )
                logger.info(f"Sent markup message to {chat_id}")
                return
            except Exception as e:
                logger.warning(f"Send markup attempt {attempt + 1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"Failed to send markup message after {retries} attempts: {e}")

    async def send_daily_summary(self, chat_id: str, summaries: dict):
        if not summaries:
            await self.send_message(chat_id, t("summary_empty"))
            return

        timestamp = summaries.get('timestamp', 'N/A')
        msg = t("summary_header", timestamp=timestamp)

        keyboard = []
        for ticker, data in summaries.items():
            if ticker == 'timestamp':
                continue

            msg += t("summary_row",
                      ticker=ticker,
                      brief=data.get('brief', ''),
                      news_count=data.get('news_count', 0))

            keyboard.append([
                InlineKeyboardButton(
                    t("summary_btn", ticker=ticker),
                    callback_data=f"detail_{ticker}"
                )
            ])

        msg += t("summary_footer")
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self._send_with_markup(chat_id, msg, reply_markup)

    async def send_breaking_news(self, chat_id: str, ticker: str,
                                news_title: str, news_url: str, analysis: dict):
        sentiment_emoji = {
            'bullish': '📈', 'bearish': '📉', 'neutral': '➡️'
        }.get(analysis.get('sentiment', 'neutral'), '📰')

        msg = t("breaking_header", emoji=sentiment_emoji)
        msg += f"**${ticker}**\n"
        msg += t("detail_link", ticker=ticker) + "\n"
        msg += f"**{news_title}**\n\n"
        msg += f"💡 {analysis.get('summary', '')}\n\n"
        msg += t("breaking_impact", impact=analysis.get('impact', 'N/A').upper())
        msg += t("breaking_link", url=news_url)

        await self.send_message(chat_id, msg, disable_web_page_preview=False)

    def setup(self):
        self.app = Application.builder().token(self.token).build()

        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("add", self.cmd_add))
        self.app.add_handler(CommandHandler("remove", self.cmd_remove))
        self.app.add_handler(CommandHandler("list", self.cmd_list))
        self.app.add_handler(CommandHandler("summary", self.cmd_summary))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))

        logger.info("Telegram handlers setup complete")

    async def start(self):
        await self.app.initialize()
        await self.app.start()

        commands = [
            BotCommand("summary", t("cmd_summary")),
            BotCommand("list", t("cmd_list")),
            BotCommand("add", t("cmd_add")),
            BotCommand("remove", t("cmd_remove")),
            BotCommand("help", t("cmd_help")),
        ]
        await self.app.bot.delete_my_commands()
        await self.app.bot.set_my_commands(commands)
        await self.app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        logger.info("Telegram commands registered")

        await self.app.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram adapter started")

    async def stop(self):
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
        logger.info("Telegram adapter stopped")
