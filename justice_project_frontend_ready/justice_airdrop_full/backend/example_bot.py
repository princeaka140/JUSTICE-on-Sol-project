"""
Example aiogram v3 bot skeleton showing owner/admin flows and how to call backend admin endpoints.
Replace BOT_TOKEN, BACKEND_URL, and OWNER_ID placeholders with real values or use .env.

This file is a reference and not meant to be run as-is until you replace placeholders.
"""
import os
import asyncio
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

BOT_TOKEN = os.getenv('BOT_TOKEN', 'REPLACE_BOT_TOKEN')
BACKEND = os.getenv('BACKEND_URL', 'http://127.0.0.1:8000')
OWNER_ID = int(os.getenv('OWNER_ID', '0') or 0)


async def send_backend_add_admin(admin_tg_id: str, owner_id: int):
    url = f"{BACKEND}/admin/add_admin"
    async with httpx.AsyncClient() as client:
        headers = {
            'x-owner-id': str(owner_id),
            'x-admin-key': os.getenv('BOT_API_KEY', 'REPLACE_BOT_API_KEY')
        }
        r = await client.post(url, json={'telegram_id': str(admin_tg_id)}, headers=headers, timeout=10)
        return r


async def main():
    if BOT_TOKEN.startswith('REPLACE'):
        print('Please set BOT_TOKEN in env before running the example bot')
        return
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()

    @dp.message(Command('start'))
    async def cmd_start(msg: types.Message):
        await msg.reply('Hello. This bot is a backend integrator example.')

    @dp.message(Command('addadmin'))
    async def cmd_addadmin(msg: types.Message):
        # owner-only command - owner types /addadmin <tg_id>
        if msg.from_user.id != OWNER_ID:
            await msg.reply('Only owner can add admins via this command')
            return
        parts = msg.text.split()
        if len(parts) < 2:
            await msg.reply('Usage: /addadmin <telegram_id>')
            return
        target = parts[1]
        r = await send_backend_add_admin(target, OWNER_ID)
        if r.status_code == 200:
            await msg.reply('Admin added successfully')
        else:
            await msg.reply(f'Failed to add admin: {r.status_code} {r.text}')

    try:
        print('Starting example bot (press Ctrl-C to stop)')
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())
