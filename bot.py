import logging
import random
import io
import json
import csv
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN", "8087989542:AAGRb-mmNl5B5J0nCdxGrhPwg1V_4TWt7FY")

BINS_DB = {
    "visa": ["4", "411111", "401288", "422222", "400005"],
    "mastercard": ["5", "510510", "555555", "545454", "536678"],
    "amex": ["3", "378282", "371449", "378734493671", "341111"],
    "discover": ["6", "601111", "601100", "601198"],
    "jcb": ["35", "353011", "356600"],
    "diners": ["30", "36", "38", "305693"]
}

class NamsoGen:
    def __init__(self):
        self.cards = []
        self.history = []
    
    def luhn_checksum(self, num):
        digits = [int(d) for d in str(num)]
        checksum = 0
        reverse_digits = digits[::-1]
        for i, d in enumerate(reverse_digits):
            if i % 2 == 1:
                d *= 2
                if d > 9:
                    d -= 9
            checksum += d
        return checksum % 10
    
    def is_valid(self, num):
        return self.luhn_checksum(num) == 0
    
    def generate_card(self, bin_input, length=16):
        prefix = "".join(str(random.randint(0,9)) if c.upper()=='X' else c for c in bin_input)
        number = prefix
        while len(number) < length - 1:
            number += str(random.randint(0, 9))
        check = self.luhn_checksum(int(number) * 10)
        check_digit = (10 - check) % 10
        return int(number + str(check_digit))
    
    def generate_full(self, bin_input, qty=10, month=None, year=None, cvv=None):
        self.cards = []
        length = 15 if str(bin_input).startswith('3') else 16
        
        for _ in range(qty):
            num = self.generate_card(bin_input, length)
            
            if month is None:
                mm = str(random.randint(1,12)).zfill(2)
            else:
                mm = str(month).zfill(2)
            
            if year is None:
                yy = str(random.randint(25,30))
            else:
                yy = str(year)[-2:]
            
            if cvv is None:
                cvv_len = 4 if str(bin_input).startswith('3') else 3
                cv = str(random.randint(0, 10**cvv_len-1)).zfill(cvv_len)
            else:
                cv = cvv
            
            card = {
                'number': str(num),
                'month': mm,
                'year': yy,
                'cvv': cv,
                'bin': bin_input,
                'date': datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            self.cards.append(card)
        
        self.history.extend(self.cards)
        return self.cards
    
    def detect_card_type(self, number):
        num = str(number)
        if num.startswith('4'):
            return "Visa"
        elif num.startswith(('51', '52', '53', '54', '55')):
            return "Mastercard"
        elif num.startswith(('34', '37')):
            return "American Express"
        elif num.startswith('6011'):
            return "Discover"
        elif num.startswith('35'):
            return "JCB"
        elif num.startswith(('30', '36', '38')):
            return "Diners Club"
        else:
            return "Unknown"
    
    def to_txt(self, format_type="pipe"):
        if format_type == "pipe":
            return '\n'.join(f"{c['number']}|{c['month']}|{c['year']}|{c['cvv']}" for c in self.cards)
        elif format_type == "csv":
            return '\n'.join(f"{c['number']},{c['month']},{c['year']},{c['cvv']}" for c in self.cards)
        elif format_type == "space":
            return '\n'.join(f"{c['number']} {c['month']}/{c['year']} {c['cvv']}" for c in self.cards)
        elif format_type == "full":
            lines = []
            for c in self.cards:
                tipo = self.detect_card_type(c['number'])
                lines.append(f"Número: {c['number']}")
                lines.append(f"Tipo: {tipo}")
                lines.append(f"Expira: {c['month']}/{c['year']}")
                lines.append(f"CVV: {c['cvv']}")
                lines.append(f"BIN: {c['bin']}")
                lines.append("-" * 30)
            return '\n'.join(lines)
    
    def to_json(self):
        return json.dumps(self.cards, indent=2)
    
    def to_csv(self):
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=['number', 'month', 'year', 'cvv', 'bin'])
        writer.writeheader()
        writer.writerows(self.cards)
        return output.getvalue()

namso = NamsoGen()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = """
🎴 *Namso Gen Pro Bot*

*Comandos disponibles:*

🎯 */gen* `<BIN>` `<cantidad>` - Generar tarjetas
📋 */check* `<número>` - Verificar tarjeta (Luhn)
📊 */bins* - Ver BINs de prueba comunes
📁 */export* `<formato>` - Exportar últimas tarjetas
📈 */stats* - Estadísticas
❓ */help* - Ayuda detallada

*Ejemplo rápido:*
`/gen 411111 10`

⚠️ *Solo para testing y desarrollo*
"""
    await update.message.reply_text(welcome, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
*Guía completa:*

*1. Generar tarjetas:*
`/gen 411111 20`
`/gen 5XXXXX 50`
`/gen 411111 10 12 2025` (con fecha específica)

*2. Verificar tarjeta:*
`/check 4111111111111111`
Te dice si pasa el algoritmo de Luhn

*3. Exportar formatos:*
`/export txt` - Formato pipe (default)
`/export csv` - Formato CSV
`/export json` - Formato JSON
`/export full` - Formato detallado

*4. BINs disponibles:*
`/bins` - Muestra lista de BINs de prueba

*Formatos de BIN:*
• `411111` - BIN fijo
• `41111X` - Último dígito aleatorio
• `4XXXXX` - Visa aleatoria
• `5XXXXX` - Mastercard aleatoria

*Nota:* Estas tarjetas *NO* tienen fondos reales.
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ *Uso incorrecto*\n\n"
            "Ejemplo: `/gen 411111 10`\n"
            "O con fecha: `/gen 411111 10 12 25`",
            parse_mode='Markdown'
        )
        return
    
    bin_input = context.args[0]
    
    try:
        qty = min(int(context.args[1]), 100) if len(context.args) > 1 else 10
    except:
        qty = 10
    
    month = int(context.args[2]) if len(context.args) > 2 else None
    year = int(context.args[3]) if len(context.args) > 3 else None
    
    await update.message.reply_text(f"⏳ Generando {qty} tarjetas...")
    
    cards = namso.generate_full(bin_input, qty, month, year)
    card_type = namso.detect_card_type(cards[0]['number'])
    
    preview = f"🎴 *{card_type} - {qty} tarjetas*\n\n"
    for i, c in enumerate(cards[:10], 1):
        preview += f"`{c['number']}`\n"
        preview += f"📅 {c['month']}/{c['year']} 🔒 `{c['cvv']}`\n\n"
    
    if len(cards) > 10:
        preview += f"📦 ...y {len(cards)-10} más\n"
    
    preview += f"\n✅ *Válidas por algoritmo de Luhn*"
    
    keyboard = [
        [InlineKeyboardButton("📥 Descargar TXT", callback_data='export_txt')],
        [InlineKeyboardButton("📥 Descargar CSV", callback_data='export_csv')],
        [InlineKeyboardButton("📥 Descargar JSON", callback_data='export_json')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(preview, parse_mode='Markdown', reply_markup=reply_markup)

async def check_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("❌ Usa: `/check <número_de_tarjeta>`", parse_mode='Markdown')
        return
    
    number = context.args[0].replace(" ", "").replace("-", "")
    
    if not number.isdigit():
        await update.message.reply_text("❌ Solo números permitidos")
        return
    
    is_valid = namso.is_valid(number)
    card_type = namso.detect_card_type(number)
    
    if is_valid:
        status = "✅ *VÁLIDA*"
    else:
        status = "❌ *INVÁLIDA*"
    
    result = f"""
{status}

🔢 Número: `{number}`
💳 Tipo: {card_type}
🔍 Algoritmo de Luhn: {"Pasa" if is_valid else "No pasa"}

{"✨ Esta tarjeta tiene formato válido" if is_valid else "⚠️ Esta tarjeta no pasó la validación"}
"""
    await update.message.reply_text(result, parse_mode='Markdown')

async def list_bins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📋 *BINs de prueba comunes:*\n\n"
    
    for tipo, bins in BINS_DB.items():
        text += f"*{tipo.upper()}:*\n"
        for b in bins:
            text += f"`{b}` "
        text += "\n\n"
    
    text += "\n💡 *Usa estos BINs con el comando /gen*"
    await update.message.reply_text(text, parse_mode='Markdown')

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not namso.cards:
        await update.message.reply_text("❌ Primero genera tarjetas con /gen")
        return
    
    format_type = context.args[0].lower() if context.args else "txt"
    
    if format_type == "json":
        content = namso.to_json()
        filename = "tarjetas.json"
    elif format_type == "csv":
        content = namso.to_csv()
        filename = "tarjetas.csv"
    elif format_type == "full":
        content = namso.to_txt("full")
        filename = "tarjetas_detalle.txt"
    else:
        content = namso.to_txt("pipe")
        filename = "tarjetas.txt"
    
    await update.message.reply_document(
        document=io.BytesIO(content.encode()),
        filename=filename,
        caption=f"📁 Exportado en formato: {format_type.upper()}"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = len(namso.history)
    current = len(namso.cards)
    
    if total == 0:
        await update.message.reply_text("📊 No hay estadísticas aún. Genera algunas tarjetas primero.")
        return
    
    text = f"""
📈 *Estadísticas*

🎯 Tarjetas en sesión actual: {current}
📦 Total generadas (historia): {total}

💡 Usa /export para descargar las tarjetas actuales
"""
    await update.message.reply_text(text, parse_mode='Markdown')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not namso.cards:
        await query.edit_message_text("❌ No hay tarjetas para exportar")
        return
    
    if query.data == 'export_txt':
        content = namso.to_txt("pipe")
        filename = "tarjetas.txt"
    elif query.data == 'export_csv':
        content = namso.to_csv()
        filename = "tarjetas.csv"
    elif query.data == 'export_json':
        content = namso.to_json()
        filename = "tarjetas.json"
    
    await query.message.reply_document(
        document=io.BytesIO(content.encode()),
        filename=filename
    )

def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("gen", generate))
    application.add_handler(CommandHandler("check", check_card))
    application.add_handler(CommandHandler("bins", list_bins))
    application.add_handler(CommandHandler("export", export_command))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("🤖 Namso Gen Pro iniciado!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()