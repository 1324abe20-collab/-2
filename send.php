<?php
/**
 * Скрипт обробки замовлення та відправки в Telegram Bot
 * Працює на будь-якому PHP хостингу (PHP 7.4 - 8.3+)
 */

header('Content-Type: application/json; charset=utf-8');

// Дозволяємо запити (CORS)
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

// НАЛАШТУВАННЯ ТЕЛЕГРАМ БОТА
$botToken = 'YOUR_TELEGRAM_BOT_TOKEN_HERE';
$chatId   = 'YOUR_TELEGRAM_CHAT_ID_HERE';

// Отримуємо вхідні дані JSON або звичайний POST
$rawInput = file_get_contents('php://input');
$data = json_decode($rawInput, true);

if (!$data) {
    $data = $_POST;
}

$name         = isset($data['name']) ? trim($data['name']) : '';
$phone        = isset($data['phone']) ? trim($data['phone']) : '';
$city         = isset($data['city']) ? trim($data['city']) : '';
$delivery     = isset($data['delivery']) ? trim($data['delivery']) : '';
$payment      = isset($data['payment']) ? trim($data['payment']) : '';
$comment      = isset($data['comment']) && !empty($data['comment']) ? trim($data['comment']) : '—';
$selectedPack = isset($data['selectedPack']) ? trim($data['selectedPack']) : 'Не вказано';
$price        = isset($data['price']) ? trim($data['price']) : '0';
$date         = isset($data['date']) ? trim($data['date']) : date('d.m.Y H:i');

if (empty($name) || empty($phone)) {
    http_response_code(400);
    echo json_encode([
        'success' => false,
        'message' => "Ім'я та номер телефону є обов'язковими полями"
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

// Формуємо красивий текст повідомлення
$message  = "🔥 <b>НОВЕ ЗАМОВЛЕННЯ — ТЕПЛОПАК</b> 🔥\n";
$message .= "━━━━━━━━━━━━━━━━━━━━\n";
$message .= "📦 <b>Комплект:</b> " . htmlspecialchars($selectedPack, ENT_QUOTES, 'UTF-8') . "\n";
$message .= "💰 <b>До сплати:</b> <b>" . htmlspecialchars($price, ENT_QUOTES, 'UTF-8') . " грн</b>\n";
$message .= "━━━━━━━━━━━━━━━━━━━━\n";
$message .= "👤 <b>Клієнт:</b> " . htmlspecialchars($name, ENT_QUOTES, 'UTF-8') . "\n";
$message .= "📞 <b>Телефон:</b> <a href=\"tel:" . preg_replace('/\D/', '', $phone) . "\">" . htmlspecialchars($phone, ENT_QUOTES, 'UTF-8') . "</a>\n";
$message .= "📍 <b>Місто:</b> " . htmlspecialchars($city, ENT_QUOTES, 'UTF-8') . "\n";
$message .= "🚚 <b>Доставка:</b> " . htmlspecialchars($delivery, ENT_QUOTES, 'UTF-8') . "\n";
$message .= "💳 <b>Оплата:</b> " . htmlspecialchars($payment, ENT_QUOTES, 'UTF-8') . "\n";
$message .= "💬 <b>Коментар:</b> " . htmlspecialchars($comment, ENT_QUOTES, 'UTF-8') . "\n";
$message .= "⏰ <b>Час заявки:</b> " . htmlspecialchars($date, ENT_QUOTES, 'UTF-8') . "\n";
$message .= "━━━━━━━━━━━━━━━━━━━━\n";
$message .= "🌐 <i>Заявка через PHP Backend</i>";

// Якщо токен не вказано - повертаємо успіх для тестування
if ($botToken === 'YOUR_TELEGRAM_BOT_TOKEN_HERE') {
    echo json_encode([
        'success' => true,
        'message' => 'Тестовий режим: повідомлення сформовано (введіть токен у send.php)'
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

$url = "https://api.telegram.org/bot{$botToken}/sendMessage";
$postFields = [
    'chat_id'                  => $chatId,
    'text'                     => $message,
    'parse_mode'               => 'HTML',
    'disable_web_page_preview' => true,
];

// Відправка запиту через cURL
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($postFields));
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);
curl_setopt($ch, CURLOPT_TIMEOUT, 10);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$curlError = curl_error($ch);
curl_close($ch);

if ($curlError) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'message' => 'Помилка з\'єднання cURL: ' . $curlError
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

$tgResult = json_decode($response, true);

if ($httpCode === 200 && isset($tgResult['ok']) && $tgResult['ok'] === true) {
    echo json_encode([
        'success' => true,
        'message' => 'Замовлення успішно відправлено в Telegram'
    ], JSON_UNESCAPED_UNICODE);
} else {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'message' => 'Помилка Telegram API',
        'details' => $tgResult
    ], JSON_UNESCAPED_UNICODE);
}
