/**
 * НАЛАШТУВАННЯ ВІДПРАВКИ ЗАМОВЛЕНЬ
 *
 * Варіант 1 (рекомендовано) — CRM-бот:
 *   Замовлення створюється в базі бота, отримує номер, ТТН, статуси та статистику.
 *   Увімкніть USE_BOT_API: true і вкажіть адресу API бота та ключ.
 *   Адреса має бути HTTPS (наприклад: https://crm.vashdomen.com/api/order).
 *   Ключ BOT_API_KEY має збігатися з SITE_API_KEY у bot/.env.
 *
 * Варіант 2 — пряма відправка в Telegram (без CRM):
 *   Заявка просто приходить повідомленням у чат. Номер замовлення не створюється.
 *   Заповніть TELEGRAM_BOT_TOKEN і TELEGRAM_CHAT_ID, а USE_BOT_API залиште false.
 *
 * Якщо нічого не налаштовано — працює тестовий режим (форма показує подяку).
 */

window.CONFIG = {
  // --- Варіант 1: CRM-бот ---
  USE_BOT_API: true,
  // Локальний тест. Для продакшену замініть на HTTPS-адресу, наприклад:
  // 'https://crm.vashdomen.com/api/order'
  BOT_API_URL: 'http://127.0.0.1:8080/api/order',
  // Має збігатися з SITE_API_KEY у bot/.env
  BOT_API_KEY: 'sk_live_GDfvs8NIMHiv01-4sXJMNiM6PIp6i1j96FOVC7MdvBA',

  // --- Варіант 2: пряма відправка в Telegram ---
  // ⚠️ Не вставляйте сюди справжній токен бота: його побачать усі відвідувачі сайту.
  TELEGRAM_BOT_TOKEN: '7774900720:AAH8rYQ-your-token-here',
  TELEGRAM_CHAT_ID: '123456789',

  // --- Варіант 3: старий PHP-бекенд (send.php) ---
  USE_PHP_BACKEND: false
};
