import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# Configuración de logs para ver qué pasa en la consola
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Definición de los Estados de la Máquina de Estados (FSM)
PEDIR_NOMBRE, MENU_PRINCIPAL, ELEGIR_SERVICIO, ELEGIR_FECHA, ELEGIR_HORA, CONFIRMAR = range(6)

   # Simulación de Base de Datos en Memoria (Tratamientos de Eudermy)
SERVICIOS = {
    "facial": {"nombre": "Tratamiento Facial", "duracion": "60 min", "precio": "$45000", "cupos": 4},
    "capilar": {"nombre": "Tratamiento Capilar", "duracion": "45 min", "precio": "$55000", "cupos": 5}
}
TURNOS_REGISTRADOS = []

# --- Funciones de la Máquina de Estados ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Estado Inicial: Saludo y bienvenida."""
    await update.message.reply_text(
        "¡Bienvenido/a a Eudermy Estética! Por favor, decinos tu nombre para empezar:"
    )
    return PEDIR_NOMBRE

async def pedir_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Valida el nombre e ingresa al Menú Principal."""
    nombre = update.message.text.strip()
    
    # Validación del Camino Infeliz (solo letras y mínimo 2 caracteres)
    if any(char.isdigit() for char in nombre) or len(nombre) < 2:
        await update.message.reply_text("Por favor, ingresá un nombre válido (solo letras, mínimo 2 caracteres):")
        return PEDIR_NOMBRE
    
    # Guardamos el nombre en el contexto del usuario
    context.user_data['nombre'] = nombre
    
    # Creamos los botones nativos de Telegram para el menú
    reply_keyboard = [['Sacar turno', 'Ver mis turnos'], ['Cancelar turno', 'Salir']]
    await update.message.reply_text(
        f"Hola {nombre}. ¿Qué deseas hacer hoy?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return MENU_PRINCIPAL

async def menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la opción elegida en el menú principal."""
    opcion = update.message.text
    
    if opcion == 'Sacar turno':
        reply_keyboard = [[SERVICIOS['facial']['nombre']], [SERVICIOS['capilar']['nombre']]]
        await update.message.reply_text(
            "Seleccioná el servicio deseado:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ELEGIR_SERVICIO
        
    elif opcion == 'Ver mis turnos':
        nombre = context.user_data['nombre']
        mis_turnos = [t for t in TURNOS_REGISTRADOS if t['nombre'] == nombre]
        if not mis_turnos:
            await update.message.reply_text("No tenés turnos registrados actualmente.")
        else:
            msg = "Tus turnos agendados:\n" + "\n".join([f"- {t['servicio']} el {t['fecha']} a las {t['hora']}" for t in mis_turnos])
            await update.message.reply_text(msg)
        
        # Volvemos a mostrar el menú para que no quede trabado el bot
        reply_keyboard = [['Sacar turno', 'Ver mis turnos'], ['Cancelar turno', 'Salir']]
        await update.message.reply_text("¿Deseas realizar otra consulta?", reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True))
        return MENU_PRINCIPAL
        
    elif opcion == 'Salir' or opcion == 'Cancelar turno':
        await update.message.reply_text(" Turno cancelado. ¡Gracias por comunicarte con EUDERMY Estética!", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

async def elegir_servicio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el servicio seleccionado y pasa a pedir la fecha."""
    servicio_elegido = update.message.text
    id_servicio = "facial" if "facial" in servicio_elegido.lower() else "capilar"
    
    # Validación de Camino Infeliz: Control de Cupos
    if SERVICIOS[id_servicio]['cupos'] <= 0:
        await update.message.reply_text("Lo sentimos, no hay cupos disponibles para este servicio. Elegí otro:")
        return ELEGIR_SERVICIO
        
    context.user_data['servicio'] = SERVICIOS[id_servicio]['nombre']
    context.user_data['id_servicio'] = id_servicio
    
    await update.message.reply_text("Ingresá la fecha en formato DD/MM (ejemplo: 20/07):", reply_markup=ReplyKeyboardRemove())
    return ELEGIR_FECHA

async def elegir_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Valida el formato de la fecha y pide la hora."""
    fecha = update.message.text.strip()
    
    # Validación de formato básico (Camino infeliz)
    if "/" not in fecha or len(fecha) != 5:
        await update.message.reply_text("Formato incorrecto. Por favor ingresá la fecha como DD/MM (ej: 20/07):")
        return ELEGIR_FECHA
        
    context.user_data['fecha'] = fecha
    
    reply_keyboard = [['10:00', '11:00', '16:00', '17:00']]
    await update.message.reply_text(
        "Elegí un horario disponible:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ELEGIR_HORA

async def elegir_hora(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra el resumen completo y pasa al estado de confirmación."""
    context.user_data['hora'] = update.message.text
    
    resumen = (
        f"📋 *RESUMEN DE TU TURNO* 📋\n\n"
        f"👤 paciente: {context.user_data['nombre']}\n"
        f"💆‍♀️ Servicio: {context.user_data['servicio']}\n"
        f"📅 Fecha: {context.user_data['fecha']}\n"
        f"⏰ Hora: {context.user_data['hora']}\n\n"
        f"¿Confirmás el turno? (Sí/No)"
    )
    reply_keyboard = [['Sí', 'No']]
    await update.message.reply_text(resumen, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True), parse_mode="Markdown")
    return CONFIRMAR

async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el turno definitivamente si la respuesta es afirmativa."""
    respuesta = update.message.text.lower()
    
    if respuesta in ['sí', 'si']:
        id_serv = context.user_data['id_servicio']
        SERVICIOS[id_serv]['cupos'] -= 1  # Restamos un cupo del servicio
        
        # Guardamos el turno en nuestra lista ("Base de datos")
        TURNOS_REGISTRADOS.append({
            "nombre": context.user_data['nombre'],
            "servicio": context.user_data['servicio'],
            "fecha": context.user_data['fecha'],
            "hora": context.user_data['hora']
        })
        
        await update.message.reply_text("¡Turno confirmado con éxito! Te esperamos en el local.", reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text("Turno cancelado. Volviendo a empezar.", reply_markup=ReplyKeyboardRemove())
        
    return ConversationHandler.END

def main():
    # === REEMPLAZÁ ACÁ TU TOKEN ===
    TOKEN = "8785300510:AAHxGgYPOuocQEXaCYz89pDwfs2OnRkQEHs" 
    
    application = Application.builder().token(TOKEN).build()

    # Configuración del ConversationHandler que maneja los estados del Bot
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), MessageHandler(filters.TEXT & ~filters.COMMAND, start)],
        states={
            PEDIR_NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, pedir_nombre)],
            MENU_PRINCIPAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_principal)],
            ELEGIR_SERVICIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, elegir_servicio)],
            ELEGIR_FECHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, elegir_fecha)],
            ELEGIR_HORA: [MessageHandler(filters.TEXT & ~filters.COMMAND, elegir_hora)],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar)],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    application.add_handler(conv_handler)
    
    # Enciende el bot y se queda escuchando mensajes (polling)
    application.run_polling()

if __name__ == '__main__':
    main()