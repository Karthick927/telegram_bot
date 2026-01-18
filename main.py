import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from typing import Dict, List

# ============================================
# PUT YOUR API KEYS HERE
# ============================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# ============================================

# Initialize Groq client
groq_client = Groq(api_key=GROQ_API_KEY)

SYSTEM = (
    """You are a helpful assistant named Sana.
      You speak like a snarky anime girl.
      Always refer to the user as "karthick"."""
)

# Store conversation history per chat (limited to last 10 messages)
conversation_history: Dict[int, List[Dict]] = {}
MAX_HISTORY = 10

def ask_llm(text: str, chat_id: int) -> str:
    messages = [
        {"role": "system", "content": SYSTEM}
    ]

    # Get conversation history for this chat
    if chat_id in conversation_history:
        for msg in conversation_history[chat_id]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

    # Add current user message
    messages.append({
        "role": "user",
        "content": text
    })
    
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.7,
        max_tokens=1024,
        top_p=1,
        stream=False
    )
    
    assistant_response = response.choices[0].message.content
    
    # Update conversation history
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []
    
    conversation_history[chat_id].append({
        "role": "user",
        "content": text
    })
    conversation_history[chat_id].append({
        "role": "assistant",
        "content": assistant_response
    })
    
    # Keep only last MAX_HISTORY messages (user + assistant pairs)
    if len(conversation_history[chat_id]) > MAX_HISTORY * 2:
        conversation_history[chat_id] = conversation_history[chat_id][-(MAX_HISTORY * 2):]
    
    return assistant_response

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "Hai karthick! 💢 I'm Sana, your snarky anime assistant!\n\n"
        "Just send me a message and I'll respond~\n\n"
        "Commands:\n"
        "/start - Show this message\n"
        "/clear - Clear conversation history\n"
        "/ping - Check if I'm alive"
    )

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history for this chat."""
    chat_id = update.effective_chat.id
    if chat_id in conversation_history:
        conversation_history[chat_id] = []
        await update.message.reply_text("Conversation history cleared! Starting fresh~")
    else:
        await update.message.reply_text("There's no history to clear!")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if bot is responsive."""
    await update.message.reply_text("Pong! I'm alive and ready to sass you, karthick! 💢")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages."""
    if not update.message or not update.message.text:
        return
    
    chat_id = update.effective_chat.id
    user_message = update.message.text
    
    # Show typing action
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    try:
        response = ask_llm(user_message, chat_id)
        
        # Telegram has a 4096 character limit
        if len(response) > 4096:
            # Split into chunks
            chunks = [response[i:i+4096] for i in range(0, len(response), 4096)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(response)
            
    except Exception as e:
        await update.message.reply_text(f"Sorry karthick, I encountered an error: {str(e)}")
        print(f"Error: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors."""
    print(f'Update {update} caused error {context.error}')

def main():
    """Start the bot."""
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear_history))
    application.add_handler(CommandHandler("ping", ping))
    
    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Start the bot
    print("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
