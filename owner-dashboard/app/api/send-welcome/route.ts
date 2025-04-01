import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const { phone, storeName, storeId } = await request.json()
    
    const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN
    
    if (!BOT_TOKEN) {
      return NextResponse.json({ error: 'Bot token not configured' }, { status: 500 })
    }

    // Send welcome message directly to phone number via Telegram
    const message = `🎉 *Welcome to BazaarOps!* 🎉

Hello ${storeName}! 👋

Your store has been successfully registered!

🔔 *You'll now receive:*
• Real-time low stock alerts
• Daily sales reports at 9 PM
• Credit analysis
• Order notifications

📱 *To activate notifications:*
Open this bot and send: /start

Let's grow your business together! 🚀`

    // Note: Bot can only send messages to users who have started the bot
    // So we return the message to show on screen
    
    return NextResponse.json({
      success: true,
      message: 'Registration successful',
      telegramInstructions: {
        botUsername: '@BazaarOpsAdminBot',
        message: 'Please open @BazaarOpsAdminBot on Telegram and send /start to activate notifications'
      }
    })
  } catch (error) {
    console.error('Error sending welcome:', error)
    return NextResponse.json({ error: 'Failed to send welcome' }, { status: 500 })
  }
}
